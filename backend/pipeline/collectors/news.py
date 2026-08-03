import asyncio
import datetime
import yfinance as yf
from ..rate_limiter import sync_retry


class NewsCollector:
    async def collect(self, ticker: str, company_name: str = None) -> dict:
        """
        Collects recent news articles via Yahoo Finance (yfinance.news).
        Replaces the deprecated Google News RSS feed.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_news, ticker)

    @sync_retry(max_retries=3, base_delay=2.0)
    def _fetch_news(self, ticker: str) -> dict:
        try:
            t = yf.Ticker(ticker)
            raw_news = t.news  # list of dicts from Yahoo Finance

            entries = []
            for item in raw_news[:10]:
                # Handle new yfinance format where data is nested in 'content', fallback to flat
                article = item.get("content", item)
                
                title = article.get("title", "Untitled")
                link = article.get("canonicalUrl", {}).get("url") or article.get("link", "")
                publisher = article.get("provider", {}).get("displayName") or article.get("publisher", "Unknown")
                summary = article.get("summary", "")
                
                pub_time = article.get("pubDate") or article.get("providerPublishTime")
                if pub_time and isinstance(pub_time, (int, float)):
                    try:
                        pub_time = datetime.datetime.fromtimestamp(pub_time).isoformat()
                    except (TypeError, ValueError, OSError):
                        pub_time = str(pub_time)

                entries.append({
                    "title": title,
                    "link": link,
                    "publisher": publisher,
                    "published": pub_time or "N/A",
                    "summary": summary,
                    "type": article.get("contentType") or article.get("type", ""),
                })

            return {"recent_news": entries}
        except Exception as e:
            return {"error": str(e)}
