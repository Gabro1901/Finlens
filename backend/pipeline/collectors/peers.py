import asyncio
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


class PeersCollector:
    def __init__(self, llm_provider: str = None, llm_api_key: str = None):
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key

    async def collect(self, ticker: str, company_name: str = None) -> dict:
        """
        Collects peer tickers and their full financial data using a two-tier approach:
        1. LLM selection for accurate business peers.
        2. Fallback to Yahoo Finance recommendations.
        Fetches full financial statements in parallel for all peers.
        """
        try:
            peers = await self._get_llm_peers(ticker, company_name)

            # Fallback if LLM failed or returned no peers
            if not peers:
                print(f"[Peers] LLM failed to find peers for {ticker}, falling back to Yahoo Finance...")
                peers = await self._get_peer_tickers(ticker)

            if not peers:
                return {"error": "No peers found via LLM or Yahoo fallback."}

            peer_data = await self._fetch_all_peers(peers)
            return {"peers": peer_data}

        except Exception as e:
            return {"error": str(e)}

    @async_retry(max_retries=3, base_delay=1.0)
    async def _get_llm_peers(self, ticker: str, company_name: str) -> list:
        # We know we are using DeepSeek as instructed
        client = AsyncOpenAI(api_key=self.llm_api_key, base_url="https://api.deepseek.com")

        target = company_name if company_name else ticker
        prompt = (
            f"You are a financial analyst. Provide exactly the top 3 direct business competitors "
            f"for {target} ({ticker}) that are publicly traded on US exchanges. "
            f"Return ONLY a comma-separated list of their exact stock ticker symbols (e.g., AAPL, MSFT, GOOG). "
            f"Do not include the word 'Ticker' or any other text, just the 3 symbols separated by commas."
        )

        try:
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You output only comma-separated ticker symbols."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=20,
                temperature=0.0
            )

            content = response.choices[0].message.content.strip()
            tickers = [t.strip().upper() for t in content.split(',')]
            valid_tickers = [t for t in tickers if t.isalpha() and t != ticker.upper()]

            return valid_tickers[:3]
        except Exception as e:
            print(f"[Peers] LLM Error: {e}")
            return []

    @async_retry(max_retries=2, base_delay=1.0)
    async def _get_peer_tickers(self, ticker: str) -> list:
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
                        return [r['symbol'] for r in recs[:3]]
            except Exception:
                pass
        return []

    async def _fetch_all_peers(self, peers: list) -> list:
        """Fetch full financial data for all peers in parallel."""
        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(None, self._fetch_single_peer, p) for p in peers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict) and "error" not in r]

    @sync_retry(max_retries=2, base_delay=1.0)
    def _fetch_single_peer(self, ticker: str) -> dict:
        """Fetch comprehensive data for a single peer ticker."""
        try:
            t = yf.Ticker(ticker)
            info = t.info
            if not info or info.get('trailingPegRatio') is None and info.get('marketCap') is None:
                # Likely invalid/delisted ticker
                return {"error": f"No data for ticker {ticker}"}

            ev = info.get('enterpriseValue', 0)
            ebitda = info.get('ebitda', 0)
            ev_ebitda = round(ev / ebitda, 2) if ev and ebitda else None

            peer = {
                "ticker": ticker,
                "marketCap": info.get('marketCap'),
                "trailingPE": info.get('trailingPE'),
                "forwardPE": info.get('forwardPE'),
                "evToEbitda": ev_ebitda,
                "returnOnEquity": info.get('returnOnEquity'),
                "profitMargins": info.get('profitMargins'),
                "revenueGrowth": info.get('revenueGrowth'),
            }

            # Fetch full financial statements
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
