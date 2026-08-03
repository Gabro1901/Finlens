import asyncio
import yfinance as yf
import datetime
from ..rate_limiter import sync_retry

def _sanitize_value(val):
    """Convert non-JSON-serializable types to native Python equivalents."""
    if val is None:
        return None
    # numpy types
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
    # pandas Timestamp
    try:
        import pandas as pd
        if isinstance(val, pd.Timestamp):
            return val.isoformat()
        if isinstance(val, float) and pd.isna(val):
            return None
    except ImportError:
        pass
    # datetime types
    if isinstance(val, datetime.datetime):
        return val.isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    # dicts and lists: recurse
    if isinstance(val, dict):
        return {str(k): _sanitize_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_sanitize_value(v) for v in val]
    
    if type(val).__name__ == 'float' and val != val: # isnan
        return None
        
    return val

def _df_to_dict(df):
    if df is None or df.empty:
        return {}
    # yfinance statements: columns are dates, index is metrics.
    # Result: { metric: { date: value, ... }, ... }
    res = {}
    for metric, row in df.iterrows():
        res[str(metric)] = {str(col.date() if hasattr(col, 'date') else col): _sanitize_value(val) for col, val in row.items()}
    return res

class MarketCollector:
    async def collect(self, ticker: str) -> dict:
        """
        Collects comprehensive market and financial data via yfinance.
        Runs in an executor to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_yfinance, ticker)

    @sync_retry(max_retries=3, base_delay=2.0)
    def _fetch_yfinance(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        data = {}
        try:
            info = t.info
            data["info"] = _sanitize_value(info) if isinstance(info, dict) else {}
            
            # Financial Statements (Annual and Quarterly)
            try:
                data["income_stmt"] = _df_to_dict(t.income_stmt)
                data["quarterly_income_stmt"] = _df_to_dict(t.quarterly_income_stmt)
            except Exception: pass
            
            try:
                data["balance_sheet"] = _df_to_dict(t.balance_sheet)
                data["quarterly_balance_sheet"] = _df_to_dict(t.quarterly_balance_sheet)
            except Exception: pass
            
            try:
                data["cashflow"] = _df_to_dict(t.cashflow)
                data["quarterly_cashflow"] = _df_to_dict(t.quarterly_cashflow)
            except Exception: pass
            
            # Historical Prices (5 years, monthly)
            try:
                hist = t.history(period="5y", interval="1mo")
                if not hist.empty:
                    data["history"] = {str(k.date() if hasattr(k, 'date') else k): _sanitize_value(v) for k, v in hist['Close'].to_dict().items()}
            except Exception: pass
            
            # Institutional and Insider Ownership
            try:
                mh = t.major_holders
                if mh is not None and not mh.empty:
                    # major_holders is a Series or DataFrame depending on yfinance version
                    if hasattr(mh, 'to_dict'):
                        data["major_holders"] = _sanitize_value(mh.to_dict())
            except Exception: pass
            
            try:
                insider = t.insider_transactions
                if insider is not None and not insider.empty:
                    recent = insider.head(10)
                    data["insider_transactions"] = _sanitize_value(recent.to_dict(orient='records'))
            except Exception: pass
            
            try:
                recs = t.recommendations
                if recs is not None and not recs.empty:
                    data["recommendations"] = _sanitize_value(recs.head(5).to_dict(orient='records'))
            except Exception: pass
            
            try:
                ud = t.upgrades_downgrades
                if ud is not None and not ud.empty:
                    ud_subset = ud[['Firm', 'ToGrade', 'FromGrade', 'Action']].head(15).reset_index()
                    data["upgrades_downgrades"] = _sanitize_value(ud_subset.to_dict(orient='records'))
            except Exception: pass
            
            try:
                eps_hist = t.earnings_history
                if eps_hist is not None and not eps_hist.empty:
                    data["earnings_history"] = _sanitize_value(eps_hist.to_dict(orient='records'))
            except Exception: pass
            
            try:
                e_est = t.earnings_estimate
                if e_est is not None and not e_est.empty:
                    data["earnings_estimate"] = _sanitize_value(e_est.to_dict())
            except Exception: pass

            try:
                r_est = t.revenue_estimate
                if r_est is not None and not r_est.empty:
                    data["revenue_estimate"] = _sanitize_value(r_est.to_dict())
            except Exception: pass
            
        except Exception as e:
            data["error"] = str(e)
            
        return data
