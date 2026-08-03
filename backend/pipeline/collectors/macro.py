import asyncio
from fredapi import Fred
import wbgapi as wb
from backend.config import settings
from ..rate_limiter import sync_retry

class MacroCollector:
    def __init__(self):
        self.fred_key = settings.fred_api_key

    async def collect(self, ticker: str) -> dict:
        """
        Collects macro economic data (FRED and World Bank).
        Runs synchronously in an executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_macro_data)

    @sync_retry(max_retries=3, base_delay=2.0)
    def _fetch_macro_data(self) -> dict:
        data = {}
        
        # 1. Fetch FRED data if key is available
        if self.fred_key:
            try:
                fred = Fred(api_key=self.fred_key)
                
                # Fetch recent CPI and 10-Year Treasury
                cpi = fred.get_series('CPIAUCSL')
                treasury = fred.get_series('DGS10')
                
                data["fred"] = {
                    "cpi_latest": float(cpi.iloc[-1]) if cpi is not None and not cpi.empty else None,
                    "treasury_10y_latest": float(treasury.iloc[-1]) if treasury is not None and not treasury.empty else None
                }
            except Exception as e:
                data["fred"] = {"error": str(e)}
        else:
            data["fred"] = {"error": "FRED_API_KEY not configured."}
            
        # 2. Fetch World Bank Data (No Key Required)
        try:
            # Example: Fetching latest GDP for USA
            # NY.GDP.MKTP.CD is GDP (current US$)
            wb_data = wb.data.DataFrame('NY.GDP.MKTP.CD', ['USA'], mrv=1) # Most recent value
            
            if wb_data is not None and not wb_data.empty:
                val = wb_data.iloc[0, 0]
                data["world_bank"] = {
                    "usa_gdp_latest": float(val) if val is not None else None
                }
            else:
                data["world_bank"] = {"usa_gdp_latest": None}
                
        except Exception as e:
            data["world_bank"] = {"error": str(e)}
            
        return data
