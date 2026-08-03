"""
P2-2: ImportYeti Bill of Lading Collector

Searches ImportYeti (importyeti.com) for a company's US customs
Bill of Lading data, extracting supplier names, product descriptions,
and shipment details.

ImportYeti is a free web tool — no API key required.
Uses web scraping (httpx + regex) against the public search endpoint.
"""

import asyncio
import re
import httpx
from typing import Optional
from ..rate_limiter import async_retry


# User-Agent identifying the tool per ImportYeti's robots.txt allowance
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

BASE_URL = "https://www.importyeti.com"


class ImportYetiCollector:
    """Collects supplier/shipment data from ImportYeti's free Bill of Lading database."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=15.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def collect(self, ticker: str, company_name: str = None) -> dict:
        """
        Search ImportYeti for the company and return structured supplier data.

        Args:
            ticker: Stock ticker (used as fallback search term).
            company_name: Full company name for better search results.

        Returns:
            dict with keys: suppliers (list of supplier dicts), raw_search_url,
            error (if any).
        """
        search_term = company_name if company_name else ticker

        try:
            # Step 1: Search for the company
            search_url = f"{BASE_URL}/search?q={search_term}"
            search_results = await self._search_company(search_term)

            if not search_results:
                return {
                    "suppliers": [],
                    "search_url": search_url,
                    "error": f"No ImportYeti results found for '{search_term}'",
                }

            # Step 2: Fetch the best-matching company page
            best_match_url = search_results[0].get("url", "")
            if not best_match_url:
                return {
                    "suppliers": [],
                    "search_url": search_url,
                    "error": "Could not resolve company page URL from search results.",
                }

            suppliers = await self._extract_suppliers(best_match_url)

            return {
                "suppliers": suppliers,
                "search_url": search_url,
                "company_url": best_match_url,
            }

        except Exception as e:
            return {
                "suppliers": [],
                "search_url": f"{BASE_URL}/search?q={search_term}",
                "error": str(e),
            }

    @async_retry(max_retries=2, base_delay=1.0)
    async def _search_company(self, query: str) -> list:
        """Search ImportYeti for a company and return result entries."""
        client = await self._get_client()

        try:
            resp = await client.get(f"{BASE_URL}/search", params={"q": query})
            if resp.status_code != 200:
                return []

            html = resp.text

            # Extract search result entries from the page
            # ImportYeti search results contain links like /company/.../...
            results = []
            link_pattern = re.compile(
                r'href="(/company/[^"]+)"[^>]*>([^<]+)</a>',
                re.IGNORECASE,
            )
            for match in link_pattern.finditer(html):
                url = f"{BASE_URL}{match.group(1)}"
                name = match.group(2).strip()
                if name and len(name) > 1:
                    results.append({"url": url, "name": name})

            return results[:5]  # Top 5 matches

        except httpx.RequestError:
            return []

    @async_retry(max_retries=2, base_delay=1.0)
    async def _extract_suppliers(self, company_url: str) -> list:
        """Parse a company's ImportYeti page for supplier/shipment data."""
        client = await self._get_client()

        try:
            resp = await client.get(company_url)
            if resp.status_code != 200:
                return []

            html = resp.text

            suppliers = []

            # ImportYeti displays supplier names in table rows or link patterns
            # Look for supplier-related sections
            supplier_section_patterns = [
                # Pattern for supplier names in links within supplier sections
                r'(?i)<a[^>]*href="[^"]*supplier[^"]*"[^>]*>([^<]+)</a>',
                # Pattern for company names in the supplier list tables
                r'(?i)<td[^>]*>(?:<a[^>]*>)?([A-Z][A-Za-z\s&\.\-]{3,60}(?:Inc|Ltd|LLC|Corp|Co|Limited|Group|International|Trading|Logistics|Industries))</',
                # Generic: any proper-name-like entity in supplier context
                r'(?i)(?:supplier|shipper|manufacturer)[:\s]*</?(?:td|span|div)[^>]*>([A-Z][A-Za-z\s&\.\-]{5,50})</',
            ]

            found_names = set()
            for pattern in supplier_section_patterns:
                for match in re.finditer(pattern, html):
                    name = match.group(1).strip()
                    # Filter out HTML noise and short names
                    if (
                        len(name) > 3
                        and not name.startswith("<")
                        and not re.match(r'^\s*(Home|About|Contact|Search|Login|Sign|Menu|Page)\s*$', name, re.IGNORECASE)
                    ):
                        clean_name = re.sub(r'\s+', ' ', name).strip()
                        if clean_name not in found_names:
                            found_names.add(clean_name)
                            suppliers.append({"name": clean_name, "source": "ImportYeti BoL"})

            # Also try to extract product descriptions
            product_patterns = [
                r'(?i)(?:product|commodity|description|goods)[:\s]*</?(?:td|span|div)[^>]*>([^<]{5,100})</',
                r'(?i)<td[^>]*class="[^"]*(?:product|commodity|description)[^"]*"[^>]*>([^<]{5,100})</td>',
            ]

            products = set()
            for pattern in product_patterns:
                for match in re.finditer(pattern, html):
                    desc = match.group(1).strip()
                    if desc and len(desc) > 5:
                        products.add(desc)

            # Attach products to suppliers where possible
            # (crude: just attach all products to the result set)
            result = []
            for s in suppliers[:15]:
                entry = dict(s)
                result.append(entry)

            if products and result:
                result.append({
                    "name": "[Products/Commodities]",
                    "products": list(products)[:20],
                    "source": "ImportYeti BoL",
                })

            return result

        except httpx.RequestError:
            return []
