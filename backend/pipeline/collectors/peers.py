import asyncio
import re
import httpx
import yfinance as yf
import datetime
from openai import AsyncOpenAI
from ..rate_limiter import async_retry, sync_retry


def _sanitize_value(val):
    """Convert non-JSON-serializable types to native Python equivalents."""
    if val is None:
        return None
    try:
        import numpy as np
        if isinstance(val, (np.integer,)):
            return int(val)
        if isinstance(val, (np.floating,)):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val)
        if isinstance(val, np.bool_):
            return bool(val)
        if isinstance(val, np.ndarray):
            return val.tolist()
    except ImportError:
        pass
    try:
        import pandas as pd
        if isinstance(val, pd.Timestamp):
            return val.isoformat()
        if isinstance(val, float) and pd.isna(val):
            return None
    except ImportError:
        pass
    if isinstance(val, datetime.datetime):
        return val.isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): _sanitize_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_sanitize_value(v) for v in val]
    if type(val).__name__ == 'float' and val != val:
        return None
    return val


def _df_to_dict(df):
    """Convert yfinance DataFrame to {metric: {date: value}} dict."""
    if df is None or df.empty:
        return {}
    res = {}
    for metric, row in df.iterrows():
        res[str(metric)] = {str(col.date() if hasattr(col, 'date') else col): _sanitize_value(val) for col, val in row.items()}
    return res


# Valid ticker pattern: 1-5 uppercase letters, optionally followed by .A, .B, etc. (e.g., BRK.B)
_VALID_TICKER_RE = re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$')

# Multi-class stock pairs — when both appear, keep only the primary (first listed)
_MULTI_CLASS_DEDUP = {
    'GOOGL': 'GOOG',   # Alphabet Class A → Class C
    'BRK.B': 'BRK.A',  # Berkshire B → A
    'LEN.B': 'LEN',    # Lennar B → A
    'HEI.A': 'HEI',    # Heico A → common
}


def _validate_ticker(t: str) -> bool:
    """Check if a string looks like a valid US stock ticker."""
    return bool(_VALID_TICKER_RE.match(t))


def _deduplicate_multi_class(tickers: list, primary_ticker: str) -> list:
    """
    Remove multi-class duplicates, keeping the most liquid/primary class.
    Also removes the primary ticker itself if it snuck in.
    """
    seen = set()
    result = []
    # Track which dedup groups we've seen
    dedup_groups_seen = set()
    for t in tickers:
        if t.upper() == primary_ticker.upper():
            continue
        # Check if this ticker should be deduped to another
        canonical = _MULTI_CLASS_DEDUP.get(t, t)
        if canonical in dedup_groups_seen:
            continue
        if t in _MULTI_CLASS_DEDUP:
            # This is the secondary class; check if primary class is already in result
            primary_class = _MULTI_CLASS_DEDUP[t]
            if primary_class in seen:
                continue
            # Replace with the more liquid class if not already present
            dedup_groups_seen.add(canonical)
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


class PeersCollector:
    def __init__(self, llm_provider: str = None, llm_api_key: str = None):
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key

    async def collect(self, ticker: str, company_name: str = None,
                      sector: str = None, industry: str = None,
                      market_cap: float = None, business_summary: str = None) -> dict:
        """
        Collects peer tickers and their full financial data using a three-tier approach:
        1. LLM selection with full industry/sector context (most accurate).
        2. Fallback: Yahoo Finance industry-based peer discovery.
        3. Last resort: Yahoo Finance recommendations endpoint.

        Returns 5-8 peers with comprehensive financial data.
        """
        try:
            peers = await self._get_llm_peers(
                ticker, company_name, sector, industry, market_cap, business_summary
            )

            if not peers:
                print(f"[Peers] LLM failed for {ticker}, trying industry-based fallback...")
                peers = await self._get_industry_peers(ticker, sector, industry)

            if not peers:
                print(f"[Peers] Industry fallback failed for {ticker}, trying Yahoo recommendations...")
                peers = await self._get_yahoo_recs(ticker)

            if not peers:
                return {"error": f"No peers found for {ticker} via LLM, industry, or Yahoo fallback."}

            peer_data = await self._fetch_all_peers(peers)

            if not peer_data:
                return {"error": f"Peers identified ({', '.join(peers)}) but no financial data could be fetched."}

            return {"peers": peer_data}

        except Exception as e:
            return {"error": str(e)}

    @async_retry(max_retries=3, base_delay=1.0)
    async def _get_llm_peers(self, ticker: str, company_name: str = None,
                              sector: str = None, industry: str = None,
                              market_cap: float = None, business_summary: str = None) -> list:
        """
        Use LLM to identify truly comparable business peers.
        Provides full industry/sector/financial context for better selection.
        """
        client = AsyncOpenAI(api_key=self.llm_api_key, base_url="https://api.deepseek.com")

        target = company_name if company_name else ticker

        # Build rich context for the LLM
        context_parts = [f"Company: {target} (Ticker: {ticker})"]
        if sector:
            context_parts.append(f"Sector: {sector}")
        if industry:
            context_parts.append(f"Industry: {industry}")
        if market_cap and market_cap > 0:
            if market_cap >= 1e12:
                cap_str = f"${market_cap/1e12:.1f}T"
            elif market_cap >= 1e9:
                cap_str = f"${market_cap/1e9:.1f}B"
            else:
                cap_str = f"${market_cap/1e6:.0f}M"
            context_parts.append(f"Market Cap: {cap_str}")
        if business_summary:
            # Truncate summary to ~300 chars to keep prompt focused
            summary_short = business_summary[:300]
            if len(business_summary) > 300:
                summary_short += "..."
            context_parts.append(f"Business: {summary_short}")

        context = "\n".join(context_parts)

        system_prompt = (
            "You are a senior equity research analyst with deep knowledge of global public companies. "
            "Your job is to identify direct business competitors — companies in the same industry with "
            "similar business models, revenue drivers, and market positioning. "
            "Only select companies that are publicly traded on major US exchanges (NYSE, NASDAQ). "
            "Output ONLY ticker symbols separated by commas. No other text."
        )

        user_prompt = (
            f"{context}\n\n"
            f"Identify the top 5-8 most direct publicly-traded business competitors for {target}. "
            f"Focus on companies with similar:\n"
            f"- Business model and revenue drivers\n"
            f"- Market capitalization and scale\n"
            f"- Industry and end markets served\n\n"
            f"Return ONLY the ticker symbols, separated by commas (e.g., AAPL, MSFT, GOOG, AMZN, ORCL)."
        )

        try:
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=60,
                temperature=0.0
            )

            content = response.choices[0].message.content.strip()
            # Robust parsing: split on commas, strip whitespace, uppercase
            raw_tickers = [t.strip().upper().rstrip('.') for t in content.split(',')]
            # Filter out obvious non-tickers (common LLM artifacts)
            raw_tickers = [t for t in raw_tickers if t and len(t) <= 5 and not t.startswith('HTTP')]

            # Validate ticker format
            valid_tickers = [t for t in raw_tickers if _validate_ticker(t)]

            # Deduplicate multi-class and remove self
            result = _deduplicate_multi_class(valid_tickers, ticker)

            print(f"[Peers] LLM returned: {result} (raw: {content[:80]})")
            return result[:8]

        except Exception as e:
            print(f"[Peers] LLM Error: {e}")
            return []

    @async_retry(max_retries=2, base_delay=1.0)
    async def _get_industry_peers(self, ticker: str, sector: str = None, industry: str = None) -> list:
        """
        Fallback 1: Use Yahoo Finance's industry/sector classification to find peers.
        Searches by industry key if available.
        """
        if not sector and not industry:
            # Try to get sector/industry from the ticker itself first
            try:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: yf.Ticker(ticker).info)
                sector = info.get('sector') or info.get('industry')
                industry = info.get('industry')
            except Exception:
                pass

        if not industry and not sector:
            return []

        # Use Yahoo Finance's screener via the query endpoint
        search_term = industry if industry else sector
        url = "https://query2.finance.yahoo.com/v1/finance/screener"
        params = {
            "formatted": "true",
            "lang": "en-US",
            "region": "US",
            "scrIds": search_term,
            "count": 15,
        }
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, headers=headers, params=params, timeout=8.0)
                if res.status_code == 200:
                    data = res.json()
                    quotes = data.get('finance', {}).get('result', [{}])[0].get('quotes', [])
                    tickers = [q.get('symbol', '') for q in quotes if q.get('symbol')]
                    # Filter valid, deduplicate, and remove self
                    valid = [t for t in tickers if _validate_ticker(t)]
                    result = _deduplicate_multi_class(valid, ticker)
                    print(f"[Peers] Industry-based fallback returned: {result[:8]}")
                    return result[:8]
            except Exception as e:
                print(f"[Peers] Industry fallback error: {e}")

        return []

    @async_retry(max_retries=2, base_delay=1.0)
    async def _get_yahoo_recs(self, ticker: str) -> list:
        """
        Fallback 2: Yahoo Finance recommendations endpoint.
        """
        url = f"https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/{ticker}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(url, headers=headers, timeout=5.0)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get('finance', {}).get('result', [])
                    if results and len(results) > 0:
                        recs = results[0].get('recommendedSymbols', [])
                        tickers = [r['symbol'] for r in recs if r.get('symbol')]
                        valid = [t for t in tickers if _validate_ticker(t)]
                        result = _deduplicate_multi_class(valid, ticker)
                        print(f"[Peers] Yahoo recs fallback returned: {result[:8]}")
                        return result[:8]
            except Exception as e:
                print(f"[Peers] Yahoo recs error: {e}")
        return []

    async def _fetch_all_peers(self, peers: list) -> list:
        """Fetch full financial data for all peers in parallel."""
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, self._fetch_single_peer, p) for p in peers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for r in results:
            if isinstance(r, dict) and "error" not in r:
                valid_results.append(r)
            elif isinstance(r, Exception):
                print(f"[Peers] Peer fetch exception: {r}")
        return valid_results

    @sync_retry(max_retries=3, base_delay=1.5)
    def _fetch_single_peer(self, ticker: str) -> dict:
        """
        Fetch comprehensive data for a single peer ticker.
        Extracts surface metrics AND underlying financial statement data
        so that normalize_peer() has everything it needs.
        """
        try:
            t = yf.Ticker(ticker)
            info = t.info

            # Robust validation: must have market cap (exists) and at least one meaningful metric
            if not info:
                return {"error": f"Empty info for ticker {ticker}"}

            market_cap = info.get('marketCap')
            has_data = bool(
                market_cap or
                info.get('trailingPE') or
                info.get('forwardPE') or
                info.get('revenueGrowth') or
                info.get('totalRevenue')
            )
            if not has_data:
                return {"error": f"No meaningful financial data for ticker {ticker} (possibly delisted)"}

            # --- Compute derived metrics ---
            ev = info.get('enterpriseValue', 0) or 0
            ebitda_raw = info.get('ebitda', 0) or 0
            ev_ebitda = round(ev / ebitda_raw, 2) if ev and ebitda_raw and ebitda_raw > 0 else None

            total_revenue = info.get('totalRevenue', 0) or 0
            price_to_sales = round(market_cap / total_revenue, 2) if market_cap and total_revenue and total_revenue > 0 else None

            # --- Build comprehensive peer dict ---
            peer = {
                "ticker": ticker,
                # Valuation multiples
                "marketCap": market_cap,
                "enterpriseValue": ev,
                "trailingPE": info.get('trailingPE'),
                "forwardPE": info.get('forwardPE'),
                "priceToBook": info.get('priceToBook'),
                "priceToSales": price_to_sales,
                "evToEbitda": ev_ebitda,
                "enterpriseToRevenue": info.get('enterpriseToRevenue'),
                # Profitability
                "returnOnEquity": info.get('returnOnEquity'),
                "returnOnAssets": info.get('returnOnAssets'),
                "profitMargins": info.get('profitMargins'),
                "grossMargins": info.get('grossMargins'),
                "operatingMargins": info.get('operatingMargins'),
                # Growth
                "revenueGrowth": info.get('revenueGrowth'),
                "earningsGrowth": info.get('earningsGrowth'),
                "earningsQuarterlyGrowth": info.get('earningsQuarterlyGrowth'),
                # Financial health
                "totalDebt": info.get('totalDebt'),
                "totalCash": info.get('totalCash'),
                "debtToEquity": info.get('debtToEquity'),
                "currentRatio": info.get('currentRatio'),
                "quickRatio": info.get('quickRatio'),
                # Market data
                "beta": info.get('beta'),
                "dividendYield": info.get('dividendYield'),
                "payoutRatio": info.get('payoutRatio'),
                # Classification
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "fullTimeEmployees": info.get('fullTimeEmployees'),
                "country": info.get('country'),
                # Raw fundamentals (needed by normalize_peer)
                "ebitda": ebitda_raw,
                "totalRevenue": total_revenue,
                "netIncomeToCommon": info.get('netIncomeToCommon'),
                "freeCashflow": info.get('freeCashflow'),
            }

            # --- Fetch full financial statements (needed by normalize_peer for multi-year ratios) ---
            try:
                peer["income_stmt"] = _df_to_dict(t.income_stmt)
            except Exception:
                peer["income_stmt"] = {}
            try:
                peer["balance_sheet"] = _df_to_dict(t.balance_sheet)
            except Exception:
                peer["balance_sheet"] = {}
            try:
                peer["cashflow"] = _df_to_dict(t.cashflow)
            except Exception:
                peer["cashflow"] = {}

            return peer

        except Exception as e:
            return {"error": f"Failed to fetch peer {ticker}: {str(e)}"}
