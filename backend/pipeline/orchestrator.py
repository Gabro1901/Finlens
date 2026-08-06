import json
import asyncio
import datetime
import traceback
from .collectors.edgar import EdgarCollector
from .collectors.market import MarketCollector
from .collectors.macro import MacroCollector
from .collectors.news import NewsCollector
from .collectors.regulatory import RegulatoryCollector
from .collectors.peers import PeersCollector
from .normalizer import normalize_accounting
from .context_builder import build_context
from backend.ai.report_generator import generate_report_full, generate_arbiter_report
from backend.ai.prompt_loader import load_prompt
from backend.ai.valuation_writer import generate_valuation_report
from .valuation.engine import ValuationEngine
from .valuation.selector import select_valuation_model
from .supply_chain.import_yeti import ImportYetiCollector
from .supply_chain.supplier_extractor import SupplierExtractor
from .supply_chain.confidence_scorer import score_relationships


class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles date, datetime, Timestamp, numpy, 
    pandas, and other non-standard Python types gracefully."""
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.bool_):
                return bool(obj)
        except ImportError:
            pass
        try:
            import pandas as pd
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            if isinstance(obj, pd.Series):
                return obj.to_dict()
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict(orient='records')
        except ImportError:
            pass
        try:
            return str(obj)
        except Exception:
            return repr(obj)


def safe_json_dumps(obj):
    return json.dumps(obj, cls=SafeJSONEncoder, ensure_ascii=False)


async def run_pipeline(ticker: str, llm_provider: str, llm_api_key: str, fred_api_key: str = "", congress_api_key: str = "", sec_email: str = "", language: str = "en"):
    """
    Orchestrates the entire financial analysis pipeline for a given ticker.
    Uses a two-phase collection process.
    Yields dicts suitable for SSE.
    """
    from backend.config import settings
    if fred_api_key:
        settings.fred_api_key = fred_api_key
    if congress_api_key:
        settings.congress_api_key = congress_api_key
    if sec_email:
        settings.edgar_identity = f"FinLens User {sec_email}"
        
    # Both report generation and our internal deepseek extraction tasks can use this key
    llm_api_key = llm_api_key or settings.openai_api_key
    
    yield {"event": "status", "data": safe_json_dumps({"stage": "init", "message": f"Starting analysis for {ticker}..."})}
    
    from .cache import collector_cache
    cached_data = collector_cache.get(ticker)
    if cached_data:
        yield {"event": "status", "data": safe_json_dumps({"stage": "collection", "message": f"Using recently cached data for {ticker}..."})}
        bundled_data = cached_data
        context_markdown = bundled_data["context_prompt"]
        yield {"event": "raw_data", "data": safe_json_dumps(bundled_data)}
        
        # Run parallel multi-agent generation
        yield {"event": "status", "data": safe_json_dumps({"stage": "generation", "message": "Generating Optimistic and Pessimistic analyses in parallel..."})}
        try:
            optimistic_prompt = load_prompt("optimistic_prompt.md")
            pessimistic_prompt = load_prompt("pessimistic_prompt.md")
            
            optimistic_task = asyncio.create_task(generate_report_full(ticker, context_markdown, llm_provider, llm_api_key, optimistic_prompt, language=language))
            pessimistic_task = asyncio.create_task(generate_report_full(ticker, context_markdown, llm_provider, llm_api_key, pessimistic_prompt, language=language))
            
            optimistic_report, pessimistic_report = await asyncio.gather(optimistic_task, pessimistic_task)
            
            yield {"event": "status", "data": safe_json_dumps({"stage": "synthesis", "message": "Adjudicating and synthesizing final report..."})}
            
            arbiter_report = ""
            async for chunk in generate_arbiter_report(ticker, context_markdown, optimistic_report, pessimistic_report, llm_provider, llm_api_key, language=language):
                arbiter_report += chunk
                yield {"event": "report_chunk", "data": safe_json_dumps({"text": chunk})}
        except Exception as e:
            yield {"event": "report_chunk", "data": safe_json_dumps({"text": f"\n\n⚠️ **Generation Error**: {e}"})}
            arbiter_report = ""
        
        # --- VALUATION PIPELINE ---
        if arbiter_report:
            async for event in _run_valuation_step(ticker, arbiter_report, bundled_data, llm_api_key):
                yield event
        
        yield {"event": "complete", "data": safe_json_dumps({"message": "Analysis complete."})}

        return
    
    # 1. Initialize collectors
    try:
        edgar = EdgarCollector()
        market = MarketCollector()
        macro = MacroCollector()
        news = NewsCollector()
        reg = RegulatoryCollector()
        peers = PeersCollector(llm_provider, llm_api_key)
        import_yeti = ImportYetiCollector()
    except Exception as e:
        yield {"event": "status", "data": safe_json_dumps({"stage": "error", "message": f"Failed to initialize collectors: {e}"})}
        yield {"event": "error", "data": safe_json_dumps({"message": f"Initialization error: {e}"})}
        return
    
    # 2. Phase 1: Fetch Market Data to extract company metadata
    yield {"event": "status", "data": safe_json_dumps({"stage": "collection", "message": "Phase 1: Fetching Market Data..."})}
    
    try:
        market_data = await market.collect(ticker)
        info = market_data.get("info", {})
        company_name = info.get("shortName") or info.get("longName")
        sector = info.get("sector")
        industry = info.get("industry")
        market_cap = info.get("marketCap")
        business_summary = info.get("longBusinessSummary")
    except Exception as e:
        market_data = {"error": str(e)}
        company_name = None
        sector = None
        industry = None
        market_cap = None
        business_summary = None
        
    bundled_data = {"ticker": ticker, "market": market_data}
    
    # 3. Phase 2: Run remaining collectors concurrently using metadata
    yield {"event": "status", "data": safe_json_dumps({"stage": "collection", "message": "Phase 2: Fetching 6 additional sources (including supply chain)..."})}
    
    collector_names = ["edgar", "macro", "news", "regulatory", "peers", "import_yeti"]
    tasks = [
        asyncio.create_task(edgar.collect(ticker, company_name)),
        asyncio.create_task(macro.collect(ticker)),
        asyncio.create_task(news.collect(ticker, company_name)),
        asyncio.create_task(reg.collect(ticker, company_name, sector)),
        asyncio.create_task(peers.collect(ticker, company_name, sector, industry, market_cap, business_summary)),
        asyncio.create_task(import_yeti.collect(ticker, company_name))
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, name in enumerate(collector_names):
        if isinstance(results[i], Exception):
            bundled_data[name] = {"error": f"{type(results[i]).__name__}: {results[i]}"}
        else:
            bundled_data[name] = results[i]
            
    # 4. Normalize data
    yield {"event": "status", "data": safe_json_dumps({"stage": "normalization", "message": "Normalizing accounting and market metrics..."})}
    try:
        bundled_data["normalized"] = normalize_accounting(bundled_data)
    except Exception as e:
        bundled_data["normalized"] = {"error": f"Normalization failed: {e}", "traceback": traceback.format_exc()}
    
    # 4.5 Supply Chain Intelligence Pipeline (P2)
    yield {"event": "status", "data": safe_json_dumps({"stage": "supply_chain", "message": "Extracting supply chain relationships..."})}
    try:
        supply_chain_data = await _run_supply_chain_pipeline(bundled_data, llm_api_key)
        bundled_data["supply_chain"] = supply_chain_data
    except Exception as e:
        bundled_data["supply_chain"] = {"error": f"Supply chain extraction failed: {e}", "traceback": traceback.format_exc()}
    
    # 5. Build context
    yield {"event": "status", "data": safe_json_dumps({"stage": "context", "message": "Assembling financial context for AI..."})}
    try:
        context_markdown = build_context(bundled_data)
    except Exception as e:
        context_markdown = f"# Context Build Error\n\nFailed to build context: {e}\n\nRaw data was collected but context assembly failed. The AI will work with limited information."
        bundled_data["context_build_error"] = str(e)
        bundled_data["context_traceback"] = traceback.format_exc()
    
    bundled_data["context_prompt"] = context_markdown
    collector_cache.set(ticker, bundled_data)
    yield {"event": "raw_data", "data": safe_json_dumps(bundled_data)}
    
    # 6. Run parallel multi-agent generation
    yield {"event": "status", "data": safe_json_dumps({"stage": "generation", "message": "Generating Optimistic and Pessimistic analyses in parallel..."})}
    
    try:
        optimistic_prompt = load_prompt("optimistic_prompt.md")
        pessimistic_prompt = load_prompt("pessimistic_prompt.md")
        
        optimistic_task = asyncio.create_task(generate_report_full(ticker, context_markdown, llm_provider, llm_api_key, optimistic_prompt, language=language))
        pessimistic_task = asyncio.create_task(generate_report_full(ticker, context_markdown, llm_provider, llm_api_key, pessimistic_prompt, language=language))
        
        optimistic_report, pessimistic_report = await asyncio.gather(optimistic_task, pessimistic_task)
        
        yield {"event": "status", "data": safe_json_dumps({"stage": "synthesis", "message": "Adjudicating and synthesizing final report..."})}
        
        arbiter_report = ""
        async for chunk in generate_arbiter_report(ticker, context_markdown, optimistic_report, pessimistic_report, llm_provider, llm_api_key, language=language):
            arbiter_report += chunk
            yield {"event": "report_chunk", "data": safe_json_dumps({"text": chunk})}
    except Exception as e:
        yield {"event": "report_chunk", "data": safe_json_dumps({"text": f"\n\n⚠️ **Generation Error**: {e}"})}
        arbiter_report = ""
    
    # --- VALUATION PIPELINE ---
    if arbiter_report:
        async for event in _run_valuation_step(ticker, arbiter_report, bundled_data, llm_api_key):
            yield event
        
    yield {"event": "complete", "data": safe_json_dumps({"message": "Analysis complete."})}


async def _run_valuation_step(ticker: str, arbiter_report: str, bundled_data: dict, llm_api_key: str):
    """
    Valuation Pipeline (runs after Arbiter completes):
    1. Model Selector LLM -> chooses valuation methodology + parameters
    2. Python Valuation Engine -> computes all numbers (code, not AI)
    3. Analyst LLM -> writes professional research report (streaming)
    """
    try:
        yield {"event": "valuation_progress", "data": safe_json_dumps({
            "stage": "model_selection",
            "message": "Selecting optimal valuation methodology..."
        })}
    except Exception:
        pass

    # Step 1: Model Selector LLM
    try:
        valuation_config = await select_valuation_model(
            ticker=ticker,
            arbiter_report=arbiter_report,
            bundled_data=bundled_data,
            api_key=llm_api_key,
        )
    except Exception as e:
        yield {"event": "valuation_error", "data": safe_json_dumps({
            "message": f"Model selection failed: {e}"
        })}
        return

    if 'error' in valuation_config:
        yield {"event": "valuation_error", "data": safe_json_dumps({
            "message": f"Model selection error: {valuation_config['error']}"
        })}
        return

    bp = valuation_config.get('business_profile', {})
    plan = valuation_config.get('valuation_plan', {})
    primary = plan.get('primary', {})

    try:
        yield {"event": "valuation_progress", "data": safe_json_dumps({
            "stage": "model_selected",
            "model": primary.get('model', 'unknown'),
            "business_type": bp.get('type', 'unknown'),
            "lifecycle": bp.get('lifecycle_stage', 'unknown'),
            "message": f"Selected primary model: {primary.get('model', 'unknown').upper()} for {bp.get('type', 'unknown').replace('_', ' ').title()}"
        })}
    except Exception:
        pass

    # Step 2: Python Valuation Engine
    try:
        engine = ValuationEngine(bundled_data, valuation_config)
        for event in engine.run_streaming():
            yield event
    except Exception as e:
        yield {"event": "valuation_error", "data": safe_json_dumps({
            "message": f"Valuation engine failed: {e}"
        })}
        return

    # Get results for the writer
    engine_results = engine.run()

    # Step 3: Analyst LLM (streaming report)
    try:
        yield {"event": "valuation_progress", "data": safe_json_dumps({
            "stage": "writing_report",
            "message": "Writing professional research report..."
        })}
    except Exception:
        pass

    try:
        async for chunk in generate_valuation_report(
            ticker=ticker,
            arbiter_report=arbiter_report,
            valuation_results=engine_results,
            bundled_data=bundled_data,
            api_key=llm_api_key,
        ):
            yield {"event": "valuation_chunk", "data": safe_json_dumps({"text": chunk})}
    except Exception as e:
        yield {"event": "valuation_error", "data": safe_json_dumps({
            "message": f"Report generation failed: {e}"
        })}


async def _run_supply_chain_pipeline(bundled_data: dict, llm_api_key: str) -> dict:
    """
    P2: Run the supply chain intelligence extraction pipeline.
    
    Gathers text from multiple sources (EDGAR supply chain, Form SD,
    ImportYeti BoL, news) and extracts structured supplier relationships
    with confidence scoring.
    
    Returns:
        dict with keys: relationships (scored list), sources_used, error (if any).
    """
    
    # Gather source texts
    edgar = bundled_data.get("edgar", {})
    xbrl_highlights = edgar.get("xbrl_highlights", {}) if isinstance(edgar, dict) else {}
    
    edgar_supply_chain = xbrl_highlights.get("Supply Chain & Manufacturing (10-K)", "")
    form_sd_text = xbrl_highlights.get("Conflict Minerals (Form SD)", "")
    
    import_yeti_data = bundled_data.get("import_yeti", {})
    yeti_suppliers = import_yeti_data.get("suppliers", []) if isinstance(import_yeti_data, dict) else []
    
    news_data = bundled_data.get("news", {})
    news_articles = news_data.get("recent_news", []) if isinstance(news_data, dict) else []
    
    # Determine filing date for time decay (from EDGAR's latest 10-K)
    filing_date = None
    recent_filings = edgar.get("recent_filings", []) if isinstance(edgar, dict) else []
    for f in recent_filings:
        if f.get("form") == "10-K":
            filing_date = f.get("filing_date")
            break
    
    # Skip if no supply chain data available
    has_data = bool(
        edgar_supply_chain or form_sd_text or yeti_suppliers
    )
    if not has_data:
        return {"relationships": [], "sources_used": [], "error": "No supply chain source data available"}
    
    sources_used = []
    if edgar_supply_chain:
        sources_used.append("SEC 10-K (Supply Chain Disclosure)")
    if form_sd_text:
        sources_used.append("SEC Form SD (Conflict Minerals)")
    if yeti_suppliers:
        sources_used.append("ImportYeti (Bill of Lading)")
    if news_articles:
        sources_used.append("News Articles")
    
    # Run LLM extraction
    try:
        extractor = SupplierExtractor(llm_api_key)
        relationships = await extractor.extract_from_sources(
            edgar_supply_chain=edgar_supply_chain,
            form_sd_text=form_sd_text,
            import_yeti_suppliers=yeti_suppliers,
            news_articles=news_articles,
        )
    except Exception as e:
        return {"relationships": [], "sources_used": sources_used, "error": f"LLM extraction error: {e}"}
    
    # Score relationships
    scored = score_relationships(relationships, filing_date=filing_date)
    
    # Clean up internal merge metadata from output
    for r in scored:
        r.pop("_merged_from", None)
        r.pop("_all_sources", None)
    
    return {
        "relationships": scored,
        "sources_used": sources_used,
    }
