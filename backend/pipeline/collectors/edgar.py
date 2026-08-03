import asyncio
from edgar import set_identity, Company
from backend.config import settings
from ..rate_limiter import sync_retry

class EdgarCollector:
    def __init__(self):
        set_identity(settings.edgar_identity)

    async def collect(self, ticker: str, company_name: str = None) -> dict:
        """
        Collects SEC data via edgartools.
        Runs in an executor because edgartools is synchronous.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_edgar_data, ticker)

    @sync_retry(max_retries=3, base_delay=2.0)
    def _fetch_edgar_data(self, ticker: str) -> dict:
        try:
            import re
            
            # We filter for 10-K, 10-Q, 8-K, and SD (Conflict Minerals)
            filings = Company(ticker).get_filings(form=["10-K", "10-Q", "8-K", "SD"])
            recent_filings = []
            
            # Get latest 5 filings metadata
            for filing in filings[:5]:
                recent_filings.append({
                    "form": filing.form,
                    "filing_date": str(filing.filing_date),
                    "accession_no": filing.accession_no
                })
            
            xbrl_highlights = {}
            
            # Get latest 10-K or 10-Q to extract actual XBRL markdown
            latest_periodic = next((f for f in filings if f.form in ["10-K", "10-Q"]), None)
            
            if latest_periodic:
                try:
                    xbrl = latest_periodic.xbrl()
                    if xbrl:
                        # Skip extracting primary statements (Income, Balance, Cash Flow) 
                        # to prevent redundancy with yfinance data.
                        
                        if hasattr(xbrl, 'notes') and callable(xbrl.notes):
                            notes = xbrl.notes()
                            if notes:
                                notes_text = []
                                # Extract up to 3 major notes to preserve context size
                                for i, n in enumerate(notes):
                                    if i >= 3: break
                                    role = n.role_or_type.split('/')[-1] if n.role_or_type else f"Note {i+1}"
                                    text = n.text() if callable(n.text) else str(n.text)
                                    text = text[:3000] + ("..." if len(text) > 3000 else "")
                                    notes_text.append(f"**{role}**\n{text}\n")
                                
                                if notes_text:
                                    xbrl_highlights["XBRL Disclosures"] = "\n".join(notes_text)
                except Exception as e:
                    xbrl_highlights["error"] = f"Failed to extract XBRL: {str(e)}"
                    
                # Extract Supply Chain information from the latest 10-K specifically (since 10-Qs do not contain Item 1 Business)
                try:
                    latest_10k = next((f for f in filings if f.form == "10-K"), None)
                    if latest_10k:
                        doc = latest_10k.obj()
                        if doc:
                            item1_text = doc["Item 1"] if hasattr(doc, 'items') and "Item 1" in doc.items else ""
                            item1a_text = doc["Item 1A"] if hasattr(doc, 'items') and "Item 1A" in doc.items else ""
                            
                            combined_text = item1_text + "\n" + item1a_text
                            paragraphs = combined_text.split('\n')
                            
                            # Using \b to match whole words and avoid matching "open-sourcing" for "sourcing"
                            supply_chain_pattern = re.compile(r'\b(supply chain|supplier|suppliers|raw material|raw materials|vendor|vendors|manufacturing|logistics|sourcing)\b', re.IGNORECASE)
                            
                            extracted_paragraphs = []
                            for p in paragraphs:
                                if supply_chain_pattern.search(p):
                                    # check length to avoid very short generic sentences
                                    if len(p.split()) > 15:
                                        # clean up whitespace and ensure it ends with period
                                        cleaned = p.strip()
                                        if cleaned:
                                            extracted_paragraphs.append(cleaned)
                            
                            if extracted_paragraphs:
                                # limit to 10 paragraphs to avoid blowing up context
                                sc_text = "\n\n".join(extracted_paragraphs[:10])
                                xbrl_highlights["Supply Chain & Manufacturing (10-K)"] = sc_text
                except Exception as e:
                    xbrl_highlights["supply_chain_error"] = f"Failed to extract supply chain from 10-K: {str(e)}"
            
            # ──────────────────────────────────────────────
            #  P2-1: Form SD — Conflict Minerals Disclosure
            # ──────────────────────────────────────────────
            try:
                latest_sd = next((f for f in filings if f.form == "SD"), None)
                if latest_sd:
                    sd_data = self._extract_form_sd(latest_sd)
                    if sd_data:
                        xbrl_highlights["Conflict Minerals (Form SD)"] = sd_data
            except Exception as e:
                xbrl_highlights["form_sd_error"] = f"Failed to extract Form SD: {str(e)}"
                    
            return {
                "recent_filings": recent_filings,
                "xbrl_highlights": xbrl_highlights
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_form_sd(self, sd_filing) -> str:
        """Extract conflict minerals disclosure from Form SD filing.
        
        Returns structured text with smelter/refiner names, countries of origin,
        and minerals sourced, or empty string if extraction fails.
        """
        import re
        
        try:
            doc = sd_filing.obj()
            if not doc:
                full_text = sd_filing.text()
            else:
                # Try to get HTML or text content from the filing document
                full_text = ""
                if hasattr(doc, 'html') and callable(doc.html):
                    full_text = str(doc.html())
                elif hasattr(doc, 'text') and callable(doc.text):
                    full_text = str(doc.text())
                elif hasattr(doc, 'items'):
                    # Try concatenating all sections
                    parts = []
                    for key in doc.items:
                        if isinstance(doc[key], str):
                            parts.append(doc[key])
                    full_text = "\n".join(parts)
                else:
                    full_text = str(doc)
            
            if not full_text or len(full_text) < 100:
                return ""
            
            # Clean HTML tags for text extraction
            clean = re.sub(r'<[^>]+>', ' ', full_text)
            clean = re.sub(r'\s+', ' ', clean)
            
            # Keywords for conflict minerals sections
            conflict_patterns = [
                r'(?i)(conflict\s*mineral|Section\s*1502|Dodd[\s-]*Frank\s*Act)',
                r'(?i)(smelter|refiner|smelting|refining)',
                r'(?i)(DRC|Democratic\s*Republic\s*of\s*Congo|adjoining\s*country)',
                r'(?i)(tin|tantalum|tungsten|gold|3TG|columbite[\s-]*tantalite|coltan|cassiterite|wolframite)',
                r'(?i)(RCOI|reasonable\s*country\s*of\s*origin|country\s*of\s*origin\s*inquiry)',
                r'(?i)(Conflict[\s-]*Free\s*Smelter|CFS|RMI|Responsible\s*Minerals\s*Initiative)',
            ]
            
            # Find paragraphs containing conflict minerals keywords
            paragraphs = clean.split('. ')
            extracted = []
            for p in paragraphs:
                p = p.strip()
                if len(p.split()) < 8:
                    continue
                if any(re.search(pat, p) for pat in conflict_patterns):
                    # Clean up partial sentences
                    if not p.endswith(('.', '!', '?', ')', '"', "'")):
                        p += '.'
                    extracted.append(p)
            
            if not extracted:
                return ""
            
            # Extract smelter/refiner names and countries
            smelters = []
            countries = set()
            
            # Pattern for smelter/refiner names (often listed as proper names)
            smelter_pattern = re.compile(
                r'(?i)(?:smelter|refiner|facility)[:\s]*([A-Z][A-Za-z\s&\-\.]+(?:Corporation|Inc|Ltd|Limited|Co\.|Company|Group|Metal|Gold|Tin|Tungsten|Tantalum|Minerals?|Resources?|Materials?|International|Trading|Refining|Smelting|Chemical|Industries?|Technology|Corp\.))',
                re.IGNORECASE
            )
            smelter_matches = smelter_pattern.findall(clean)
            smelters.extend([s.strip() for s in smelter_matches[:20]])
            
            # Extract country names
            country_pattern = re.compile(
                r'\b(China|Taiwan|Hong\s*Kong|Japan|Korea|South\s*Korea|India|Indonesia|Malaysia|'
                r'Thailand|Vietnam|Philippines|Brazil|Chile|Peru|Mexico|Canada|United\s*States|'
                r'Germany|Belgium|Italy|France|Switzerland|Sweden|Poland|Russia|Turkey|'
                r'South\s*Africa|Rwanda|Uganda|Zambia|Namibia|Australia|Kazakhstan|'
                r'UAE|United\s*Arab\s*Emirates|Saudi\s*Arabia|Bolivia|Argentina|Colombia)\b'
            )
            country_matches = country_pattern.findall(clean)
            countries.update(c.strip() for c in country_matches)
            
            # Build structured output
            lines = []
            lines.append(f"**Form SD Filed**: {sd_filing.filing_date}")
            lines.append("")
            
            if smelters:
                lines.append("**Smelters / Refiners Identified**:")
                for s in smelters[:15]:
                    lines.append(f"  - {s}")
                lines.append("")
            
            if countries:
                lines.append(f"**Countries of Origin**: {', '.join(sorted(countries)[:20])}")
                lines.append("")
            
            # Add key disclosure excerpts
            lines.append("**Disclosure Excerpts**:")
            for p in extracted[:5]:
                if len(p) > 500:
                    p = p[:500] + "..."
                lines.append(f"  - {p}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Form SD extraction error: {str(e)}"
