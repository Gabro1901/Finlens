"""
P2-5: Pipeline Integration Tests

Tests the full analysis pipeline end-to-end for known tickers.
Verifies that all collectors return data, normalization produces metrics,
and the pipeline completes without crashing.

These tests require network access and valid API keys in .env.
Marked with @pytest.mark.integration to allow selective execution.
"""

import os
import sys
import json
import pytest
import asyncio

# Ensure we can import from backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.integration


# ──────────────────────────────────────────────
#  Helper: run pipeline and collect all events
# ──────────────────────────────────────────────

async def _collect_pipeline_events(ticker: str, llm_provider: str = "openai",
                                    llm_api_key: str = "", language: str = "en") -> list:
    """Run the pipeline for a ticker and return all events as a list."""
    from pipeline.orchestrator import run_pipeline

    events = []
    async for event in run_pipeline(
        ticker=ticker,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        language=language,
    ):
        events.append(event)
    return events


# ──────────────────────────────────────────────
#  Phase 1-2: Data Collection Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_market_collector_returns_data():
    """Market collector should return info dict with expected fields."""
    from pipeline.collectors.market import MarketCollector

    collector = MarketCollector()
    data = await collector.collect("AAPL")

    assert "error" not in data, f"Market collector error: {data.get('error')}"
    info = data.get("info", {})
    assert "shortName" in info or "longName" in info
    assert "marketCap" in info or "sector" in info


@pytest.mark.asyncio
async def test_edgar_collector_returns_data():
    """EDGAR collector should return filings and XBRL highlights."""
    from pipeline.collectors.edgar import EdgarCollector

    collector = EdgarCollector()
    data = await collector.collect("AAPL")

    assert "error" not in data, f"EDGAR collector error: {data.get('error')}"
    assert "recent_filings" in data
    assert "xbrl_highlights" in data
    filings = data.get("recent_filings", [])
    assert len(filings) > 0, "No SEC filings found"


@pytest.mark.asyncio
async def test_edgar_collector_includes_supply_chain_data():
    """EDGAR collector should now include supply chain and Form SD sections."""
    from pipeline.collectors.edgar import EdgarCollector

    collector = EdgarCollector()
    data = await collector.collect("AAPL")

    xbrl = data.get("xbrl_highlights", {})
    assert "Supply Chain & Manufacturing (10-K)" in xbrl or "supply_chain_error" in xbrl, \
        "10-K supply chain extraction should be present or have a documented error"


@pytest.mark.asyncio
async def test_news_collector_returns_data():
    """News collector should return recent articles."""
    from pipeline.collectors.news import NewsCollector

    collector = NewsCollector()
    data = await collector.collect("AAPL", "Apple Inc")

    assert "error" not in data, f"News collector error: {data.get('error')}"
    assert "recent_news" in data


@pytest.mark.asyncio
async def test_macro_collector_returns_data():
    """Macro collector should return FRED data."""
    from pipeline.collectors.macro import MacroCollector

    collector = MacroCollector()
    data = await collector.collect("AAPL")

    assert "error" not in data, f"Macro collector error: {data.get('error')}"
    fred = data.get("fred", {})
    assert fred, "FRED data should not be empty"


@pytest.mark.asyncio
async def test_regulatory_collector_returns_data():
    """Regulatory collector should return federal register or congress data."""
    from pipeline.collectors.regulatory import RegulatoryCollector

    collector = RegulatoryCollector()
    data = await collector.collect("AAPL", "Apple Inc", "Technology")

    assert "error" not in data, f"Regulatory collector error: {data.get('error')}"


@pytest.mark.asyncio
async def test_peers_collector_returns_data():
    """Peers collector should return peers with full financials."""
    from pipeline.collectors.peers import PeersCollector

    collector = PeersCollector(llm_provider="openai", llm_api_key="")
    data = await collector.collect("AAPL", "Apple Inc")

    assert "error" not in data, f"Peers collector error: {data.get('error')}"
    peers = data.get("peers", [])
    assert len(peers) > 0, "No peers found"
    has_statements = any(
        p.get("income_stmt") or p.get("balance_sheet") or p.get("cashflow")
        for p in peers
    )
    assert has_statements, "Peers should include financial statements"


# ──────────────────────────────────────────────
#  Normalizer Tests
# ──────────────────────────────────────────────

def test_normalizer_produces_metrics():
    """Normalizer should compute all 7 core metrics + accounting policies."""
    from pipeline.normalizer import normalize_accounting
    from pipeline.collectors.market import MarketCollector

    async def _get_data():
        market = MarketCollector()
        return await market.collect("AAPL")

    market_data = asyncio.run(_get_data())

    bundled = {
        "ticker": "AAPL",
        "market": market_data,
        "edgar": {"xbrl_highlights": {}, "recent_filings": []},
        "peers": {"peers": []},
        "news": {"recent_news": []},
    }

    normalized = normalize_accounting(bundled)

    assert "error" not in normalized, f"Normalizer error: {normalized.get('error')}"
    assert "ebitda" in normalized
    assert "net_debt" in normalized
    assert "ev_to_ebitda" in normalized
    assert "fcf_conversion" in normalized
    assert "roic_proxy" in normalized
    assert "accruals_ratio" in normalized
    assert "capex_intensity" in normalized
    assert "red_flags" in normalized
    assert "accounting_notes" in normalized


def test_normalizer_peer_normalization():
    """Normalizer should normalize peer metrics."""
    from pipeline.normalizer import normalize_peer

    peer = {
        "ticker": "MSFT",
        "marketCap": 3000000000000,
        "ebitda": 120000000000,
        "enterpriseValue": 3100000000000,
        "totalDebt": 80000000000,
        "totalCash": 100000000000,
        "netIncomeToCommon": 85000000000,
        "freeCashflow": 75000000000,
        "income_stmt": {},
        "balance_sheet": {},
        "cashflow": {},
    }

    norm = normalize_peer(peer)
    assert norm["ticker"] == "MSFT"
    assert norm["ebitda"] == 120000000000
    assert norm["net_debt"] == -20000000000  # 80B - 100B


# ──────────────────────────────────────────────
#  Context Builder Tests
# ──────────────────────────────────────────────

def test_context_builder_includes_supply_chain_section():
    """Context builder should render supply chain data when present."""
    from pipeline.context_builder import build_context

    bundled = {
        "ticker": "TEST",
        "market": {"info": {}, "income_stmt": {}, "balance_sheet": {}, "cashflow": {}},
        "edgar": {"recent_filings": [], "xbrl_highlights": {}},
        "macro": {"fred": {}, "world_bank": {}},
        "news": {"recent_news": []},
        "regulatory": {"federal_register": [], "congress": []},
        "peers": {"peers": []},
        "normalized": {"red_flags": [], "peers": [], "accounting_policies": {}},
        "supply_chain": {
            "relationships": [
                {
                    "supplier": "Test Supplier Corp",
                    "component": "widgets",
                    "relationship_type": "direct_supplier",
                    "confidence_hint": "high",
                    "confidence_score": 0.9,
                    "evidence": "We source widgets from Test Supplier Corp.",
                    "source_type": "sec_filing",
                }
            ],
            "sources_used": ["SEC 10-K"],
        },
        "import_yeti": {"suppliers": []},
    }

    context = build_context(bundled)
    assert "Supply Chain Intelligence" in context
    assert "Test Supplier Corp" in context
    assert "widgets" in context


def test_context_builder_handles_missing_supply_chain():
    """Context builder should not crash when supply_chain key is missing."""
    from pipeline.context_builder import build_context

    bundled = {
        "ticker": "TEST",
        "market": {"info": {}, "income_stmt": {}, "balance_sheet": {}, "cashflow": {}},
        "edgar": {"recent_filings": [], "xbrl_highlights": {}},
        "macro": {"fred": {}, "world_bank": {}},
        "news": {"recent_news": []},
        "regulatory": {"federal_register": [], "congress": []},
        "peers": {"peers": []},
        "normalized": {"red_flags": [], "peers": [], "accounting_policies": {}},
    }

    context = build_context(bundled)
    assert isinstance(context, str)
    assert len(context) > 0


def test_context_builder_handles_supply_chain_error():
    """Context builder should display supply chain error gracefully."""
    from pipeline.context_builder import build_context

    bundled = {
        "ticker": "TEST",
        "market": {"info": {}, "income_stmt": {}, "balance_sheet": {}, "cashflow": {}},
        "edgar": {"recent_filings": [], "xbrl_highlights": {}},
        "macro": {"fred": {}, "world_bank": {}},
        "news": {"recent_news": []},
        "regulatory": {"federal_register": [], "congress": []},
        "peers": {"peers": []},
        "normalized": {"red_flags": [], "peers": [], "accounting_policies": {}},
        "supply_chain": {"error": "Test error message"},
    }

    context = build_context(bundled)
    assert "Supply Chain Intelligence" in context
    assert "Test error message" in context


# ──────────────────────────────────────────────
#  Full Pipeline Smoke Test (no LLM generation)
# ──────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.slow
async def test_pipeline_collection_phase_completes():
    """
    Smoke test: run the pipeline for AAPL without LLM generation
    (stops after raw_data event). Verifies all collectors complete.
    """
    from pipeline.orchestrator import run_pipeline

    events = []
    async for event in run_pipeline(
        ticker="AAPL",
        llm_provider="openai",
        llm_api_key="",
        language="en",
    ):
        events.append(event)
        if event.get("event") == "raw_data":
            break

    event_types = [e.get("event") for e in events]
    assert "status" in event_types
    assert "raw_data" in event_types

    error_events = [e for e in events if e.get("event") == "error"]
    assert len(error_events) == 0, f"Pipeline had errors: {error_events}"

    raw_event = next(e for e in events if e.get("event") == "raw_data")
    raw_data_json = raw_event.get("data", "{}")
    raw_data = json.loads(raw_data_json)

    for key in ["market", "edgar", "macro", "news", "regulatory", "peers", "import_yeti"]:
        assert key in raw_data, f"Missing collector data: {key}"
        collector_data = raw_data[key]
        assert isinstance(collector_data, dict), f"{key} data is not a dict"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pipeline_normalization_produces_data():
    """Verify the normalization step produces metrics."""
    from pipeline.orchestrator import run_pipeline

    events = []
    async for event in run_pipeline(
        ticker="AAPL",
        llm_provider="openai",
        llm_api_key="",
        language="en",
    ):
        events.append(event)
        if event.get("event") == "raw_data":
            break

    raw_event = next(e for e in events if e.get("event") == "raw_data")
    raw_data = json.loads(raw_event.get("data", "{}"))

    normalized = raw_data.get("normalized", {})
    assert "error" not in normalized, f"Normalization error: {normalized.get('error')}"
    assert "ebitda" in normalized
    assert normalized["ebitda"] is not None and normalized["ebitda"] > 0, \
        f"EBITDA should be positive for AAPL, got {normalized['ebitda']}"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_pipeline_for_multiple_tickers():
    """Test pipeline collection for 3 different sector tickers."""
    from pipeline.orchestrator import run_pipeline

    tickers = ["AAPL", "JPM", "PFE"]

    for ticker in tickers:
        events = []
        async for event in run_pipeline(
            ticker=ticker,
            llm_provider="openai",
            llm_api_key="",
            language="en",
        ):
            events.append(event)
            if event.get("event") == "raw_data":
                break

        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) == 0, f"Pipeline had errors for {ticker}: {error_events}"

        raw_event = next(e for e in events if e.get("event") == "raw_data")
        raw_data = json.loads(raw_event.get("data", "{}"))
        assert raw_data.get("ticker") == ticker
