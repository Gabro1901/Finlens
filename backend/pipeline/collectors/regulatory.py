import json
import asyncio
import httpx
import urllib.parse
from backend.config import settings
from ..rate_limiter import async_retry


class RegulatoryCollector:
    CONGRESS_BASE_URL = "https://api.congress.gov/v3"
    FEDERAL_REGISTER_BASE_URL = "https://www.federalregister.gov/api/v1"

    async def collect(self, ticker: str, company_name: str = None, sector: str = None) -> dict:
        """
        Collects regulatory data related to the company/sector.

        Uses sector and company_name to filter Congress.gov bills instead of
        fetching only generic recent bills.
        """
        congress_key = settings.congress_api_key

        async with httpx.AsyncClient() as client:
            try:
                # 1. Federal Register (No auth needed)
                search_term = company_name if company_name else ticker
                encoded_term = urllib.parse.quote(search_term)

                fr_url = f"{self.FEDERAL_REGISTER_BASE_URL}/documents.json?conditions[term]={encoded_term}&per_page=5"
                fr_req = await self._get_with_retry(client, fr_url)
                fr_data = fr_req.json().get('results', []) if fr_req.status_code == 200 else []

                # 2. Congress.gov — sector-aware search
                cg_data = []
                if congress_key:
                    cg_data = await self._fetch_congress_bills(client, congress_key, company_name, sector)

                return {
                    "federal_register": fr_data,
                    "congress": cg_data if congress_key else {"error": "CONGRESS_API_KEY not configured"}
                }
            except Exception as e:
                return {"error": str(e)}

    async def _fetch_congress_bills(self, client: httpx.AsyncClient, api_key: str,
                                     company_name: str = None, sector: str = None) -> list:
        """
        Fetch bills from Congress.gov filtered by sector and/or company name.

        Priority:
        1. sector + company_name combined query (most specific)
        2. sector-only query
        3. company_name-only query
        4. generic recent bills (fallback)
        """
        # Build search queries in order of specificity
        queries = []

        if sector and company_name:
            queries.append(f"{sector} {company_name}")
        if sector:
            queries.append(sector)
        if company_name:
            queries.append(company_name)

        all_bills = []
        seen_ids = set()

        for query in queries:
            encoded = urllib.parse.quote(query)
            url = f"{self.CONGRESS_BASE_URL}/bill?api_key={api_key}&query={encoded}&limit=5"
            try:
                req = await self._get_with_retry(client, url)
                if req.status_code == 200:
                    bills = req.json().get('bills', [])
                    for bill in bills:
                        # Deduplicate by congress+type+number
                        bid = f"{bill.get('congress')}-{bill.get('type')}-{bill.get('number')}"
                        if bid not in seen_ids:
                            seen_ids.add(bid)
                            all_bills.append(bill)
            except Exception:
                continue

        if not all_bills:
            # Fallback: generic recent bills
            url = f"{self.CONGRESS_BASE_URL}/bill?api_key={api_key}&limit=5"
            try:
                req = await self._get_with_retry(client, url)
                if req.status_code == 200:
                    all_bills = req.json().get('bills', [])
            except Exception:
                pass

        return all_bills

    @async_retry(max_retries=3, base_delay=1.0)
    async def _get_with_retry(self, client: httpx.AsyncClient, url: str):
        """HTTP GET with exponential backoff retry."""
        return await client.get(url)
