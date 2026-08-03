import json

def _dict_to_md_table(title, data_dict):
    """
    Converts a nested dictionary {metric: {date1: val1, date2: val2}} to a markdown table.
    """
    if not data_dict:
        return ""
    
    # Extract all unique dates and sort them descending (newest first)
    dates = set()
    for metric, values in data_dict.items():
        if isinstance(values, dict):
            dates.update(values.keys())
    dates = sorted(list(dates), reverse=True)
    
    if not dates:
        return ""
        
    lines = [f"### {title}"]
    header = "| Metric | " + " | ".join(dates) + " |"
    separator = "|---|" + "|".join(["---"] * len(dates)) + "|"
    lines.append(header)
    lines.append(separator)
    
    for metric, values in data_dict.items():
        if not isinstance(values, dict):
            continue
        row = [metric]
        for d in dates:
            val = values.get(d)
            if val is None:
                row.append("-")
            elif isinstance(val, (int, float)):
                # Format large numbers compactly
                if abs(val) >= 1_000_000_000:
                    row.append(f"{val/1_000_000_000:.2f}B")
                elif abs(val) >= 1_000_000:
                    row.append(f"{val/1_000_000:.2f}M")
                elif abs(val) >= 1_000:
                    row.append(f"{val/1_000:.2f}K")
                else:
                    row.append(f"{val:.2f}")
            else:
                row.append(str(val)[:30]) # truncate long strings
        lines.append("| " + " | ".join(row) + " |")
        
    return "\n".join(lines) + "\n\n"


def build_context(bundled_data: dict) -> str:
    """
    Transforms the bundled raw data into a structured Markdown string
    to be injected into the LLM prompt.
    """
    ticker = bundled_data.get("ticker", "UNKNOWN")
    edgar = bundled_data.get("edgar", {})
    market = bundled_data.get("market", {})
    macro = bundled_data.get("macro", {})
    news = bundled_data.get("news", {})
    regulatory = bundled_data.get("regulatory", {})
    peers = bundled_data.get("peers", {})
    normalized = bundled_data.get("normalized", {})
    
    lines = []
    lines.append(f"# Raw Financial Context for {ticker}\n")
    
    # 1. Market Data & Valuation
    lines.append("## Market & Valuation Data")
    if "error" in market:
        lines.append(f"Error fetching market data: {market['error']}\n")
    else:
        info = market.get("info", {})
        desc = info.get('longBusinessSummary', info.get('description', 'N/A'))
        lines.append(f"- Company Description: {desc}")
        lines.append(f"- Sector: {info.get('sector', 'N/A')}")
        lines.append(f"- Industry: {info.get('industry', 'N/A')}")
        lines.append(f"- Market Cap: {info.get('marketCap', 'N/A')}")
        lines.append(f"- Enterprise Value: {info.get('enterpriseValue', 'N/A')}")
        lines.append(f"- Forward P/E: {info.get('forwardPE', 'N/A')}")
        lines.append(f"- Trailing P/E: {info.get('trailingPE', 'N/A')}")
        lines.append(f"- Price to Book: {info.get('priceToBook', 'N/A')}")
        lines.append(f"- Short Ratio: {info.get('shortRatio', 'N/A')}")
        lines.append(f"- Forward EPS: {info.get('forwardEps', 'N/A')}")
        lines.append(f"- Trailing EPS: {info.get('trailingEps', 'N/A')}")
        lines.append(f"- Target Mean Price: {info.get('targetMeanPrice', 'N/A')}")
        lines.append(f"- Target High Price: {info.get('targetHighPrice', 'N/A')}")
        lines.append(f"- Target Low Price: {info.get('targetLowPrice', 'N/A')}")
        lines.append(f"- Average Analyst Rating: {info.get('averageAnalystRating', 'N/A')}")
        lines.append(f"- Number of Analysts: {info.get('numberOfAnalystOpinions', 'N/A')}")
        lines.append(f"- Recommendation Key: {info.get('recommendationKey', 'N/A')}")
        lines.append(f"- Beta: {info.get('beta', 'N/A')}")
        lines.append(f"- 52-Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}")
        lines.append(f"- 52-Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}")
        lines.append(f"- 52-Week Change: {info.get('52WeekChange', 'N/A')}\n")
        
        hist = market.get("history", {})
        if hist:
            lines.append("### 5-Year Stock Price History (Close Prices)")
            lines.append(json.dumps(hist))
            lines.append("\n")

        
    # 2. Financial Statements (Income, Balance, Cashflow)
    lines.append("## Financial Statements (Multi-Year Context)")
    if "error" not in market:
        inc = _dict_to_md_table("Income Statement (Annual)", market.get("income_stmt", {}))
        bal = _dict_to_md_table("Balance Sheet (Annual)", market.get("balance_sheet", {}))
        cf = _dict_to_md_table("Cash Flow (Annual)", market.get("cashflow", {}))
        
        q_inc = _dict_to_md_table("Income Statement (Quarterly)", market.get("quarterly_income_stmt", {}))
        q_bal = _dict_to_md_table("Balance Sheet (Quarterly)", market.get("quarterly_balance_sheet", {}))
        q_cf = _dict_to_md_table("Cash Flow (Quarterly)", market.get("quarterly_cashflow", {}))
        
        if inc or bal or cf:
            lines.append(inc)
            lines.append(bal)
            lines.append(cf)
        else:
            lines.append("Annual financial statements not available via yfinance.\n")
            
        if q_inc or q_bal or q_cf:
            lines.append(q_inc)
            lines.append(q_bal)
            lines.append(q_cf)
        else:
            lines.append("Quarterly financial statements not available via yfinance.\n")

    # 3. Normalized Accounting
    lines.append("## Normalized Accounting, Metrics & Red Flags")
    lines.append(f"- Adjusted EBITDA: {normalized.get('ebitda', 'N/A')}")
    lines.append(f"- Net Debt: {normalized.get('net_debt', 'N/A')}")
    lines.append(f"- EV / Adjusted EBITDA: {normalized.get('ev_to_ebitda', 'N/A')}")
    lines.append(f"- FCF Conversion Ratio: {normalized.get('fcf_conversion', 'N/A')}")
    fcf_trend = normalized.get('fcf_conversion_trend', {})
    if fcf_trend:
        readable = ", ".join(f"{yr}: {v}x" for yr, v in fcf_trend.items())
        lines.append(f"- FCF Conversion Trend (multi-year): {readable}")
    lines.append(f"- Threshold Group (sector-adjusted): {normalized.get('threshold_group', 'default')}")
    lines.append(f"- ROIC Proxy: {normalized.get('roic_proxy', 'N/A')}")
    lines.append(f"- Accruals Ratio: {normalized.get('accruals_ratio', 'N/A')}")
    lines.append(f"- CapEx Intensity: {normalized.get('capex_intensity', 'N/A')}")
    lines.append(f"- Accounting Adjustments: {normalized.get('accounting_notes', 'None')}")
    
    red_flags = normalized.get('red_flags', [])
    if red_flags:
        lines.append("- AUTOMATED RED FLAGS:")
        for flag in red_flags:
            lines.append(f"  - 🚩 {flag}")
    lines.append("\n")

    # 4. SEC EDGAR Disclosures
    lines.append("## SEC EDGAR Disclosures (10-K/10-Q Extracts)")
    if "error" in edgar:
        lines.append(f"Error fetching EDGAR data: {edgar['error']}\n")
    else:
        recent = edgar.get('recent_filings', [])
        if recent:
            lines.append(f"Recent filings processed: {len(recent)}")
            for f in recent:
                lines.append(f"- {f.get('form')} filed on {f.get('filing_date')} (Accession: {f.get('accession_no')})")
        
        xbrl = edgar.get('xbrl_highlights', {})
        if "error" in xbrl:
            lines.append(f"\nXBRL Extraction Error: {xbrl['error']}\n")
        elif xbrl:
            lines.append("\n### Key SEC 10-K/10-Q Extracts:")
            for k, v in xbrl.items():
                if v:
                    lines.append(f"#### {k}")
                    # truncate heavily if it's super long, but user said context size is fine
                    # still, maybe limit to 5000 chars per table to avoid total explosion
                    lines.append(str(v)[:15000])
                    lines.append("\n")
    lines.append("\n")
    
    # 5. Management & Analyst Signals
    lines.append("## Management & Analyst Signals")
    if "error" not in market:
        insiders = market.get("insider_transactions", [])
        if insiders:
            lines.append("### Recent Insider Transactions")
            for tx in insiders:
                # keys depend on yfinance version, usually 'Text', 'Shares', 'Value', 'Start Date'
                lines.append(f"- {json.dumps(tx)}")
            lines.append("\n")
            
        recs = market.get("recommendations", [])
        if recs:
            lines.append("### Analyst Recommendations")
            lines.append(json.dumps(recs, indent=2))
            lines.append("\n")
            
        ud = market.get("upgrades_downgrades", [])
        if ud:
            lines.append("### Recent Analyst Ratings (Upgrades/Downgrades)")
            lines.append("| Date | Firm | Action | To Grade | From Grade |")
            lines.append("|---|---|---|---|---|")
            for item in ud:
                date_str = item.get("GradeDate", "")
                if isinstance(date_str, str) and "T" in date_str:
                    date_str = date_str.split("T")[0]
                lines.append(f"| {date_str} | {item.get('Firm', '')} | {item.get('Action', '')} | {item.get('ToGrade', '')} | {item.get('FromGrade', '')} |")
            lines.append("\n")

        # Consensus Estimates
        e_est = market.get("earnings_estimate")
        r_est = market.get("revenue_estimate")
        if e_est or r_est:
            lines.append("### Analyst Consensus & Estimates")
            if e_est:
                lines.append("#### Earnings Estimates")
                lines.append(json.dumps(e_est, indent=2))
                lines.append("\n")
            if r_est:
                lines.append("#### Revenue Estimates")
                lines.append(json.dumps(r_est, indent=2))
                lines.append("\n")

    # 6. Macro & Geo Data
    lines.append("## Macroeconomic Context (FRED & World Bank)")
    if "error" in macro:
        lines.append(f"Error fetching macro data: {macro['error']}\n")
    else:
        fred = macro.get("fred", {})
        wb = macro.get("world_bank", {})
        lines.append(f"- US CPI (Latest): {fred.get('cpi_latest', 'N/A')}")
        lines.append(f"- US 10-Year Treasury Yield: {fred.get('treasury_10y_latest', 'N/A')}")
        lines.append(f"- US GDP (Latest): {wb.get('usa_gdp_latest', 'N/A')}\n")

    # 7. News
    lines.append("## Recent News Headlines")
    if "error" in news:
        lines.append(f"Error fetching News data: {news['error']}\n")
    else:
        recent = news.get("recent_news", [])
        for r in recent:
            lines.append(f"- {r.get('title')} ({r.get('published')})")
    lines.append("\n")

    # 8. Regulatory Context
    lines.append("## Regulatory Context (Congress & Federal Register)")
    if "error" in regulatory:
        lines.append(f"Error fetching Regulatory data: {regulatory['error']}\n")
    else:
        fr = regulatory.get("federal_register", [])
        lines.append("### Federal Register Mentions:")
        for doc in fr:
            lines.append(f"- {doc.get('title')}")
            
        cg = regulatory.get("congress", [])
        if isinstance(cg, list) and len(cg) > 0:
            lines.append("\n### Congressional Bills (Sector context):")
            for bill in cg:
                lines.append(f"- {bill.get('title')}")
    lines.append("\n")
    

    # 10. Peer Comparison Data
    lines.append("## Peer Comparison Data")
    if "error" in peers:
        lines.append(f"Error fetching Peer data: {peers['error']}\n")
    else:
        peer_list = peers.get("peers", [])
        if peer_list:
            lines.append("### Peer Surface Metrics")
            lines.append("| Ticker | Market Cap | Trailing P/E | Forward P/E | EV/EBITDA | ROE | Margins | Growth |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for p in peer_list:
                lines.append(f"| {p.get('ticker')} | {p.get('marketCap')} | {p.get('trailingPE')} | {p.get('forwardPE')} | {p.get('evToEbitda')} | {p.get('returnOnEquity')} | {p.get('profitMargins')} | {p.get('revenueGrowth')} |")
        else:
            lines.append("No peer data found.")
    lines.append("\n")

    # 10b. Normalized Peer Metrics
    normalized_peers = normalized.get("peers", [])
    if normalized_peers:
        lines.append("### Peer Normalized Metrics & Red Flags")
        lines.append("| Ticker | EBITDA | Net Debt | EV/EBITDA | FCF Conv | ROIC | Accruals | CapEx Int |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for np in normalized_peers:
            lines.append(
                f"| {np.get('ticker', '')} "
                f"| {np.get('ebitda', 'N/A')} "
                f"| {np.get('net_debt', 'N/A')} "
                f"| {np.get('ev_to_ebitda', 'N/A')} "
                f"| {np.get('fcf_conversion', 'N/A')} "
                f"| {np.get('roic_proxy', 'N/A')} "
                f"| {np.get('accruals_ratio', 'N/A')} "
                f"| {np.get('capex_intensity', 'N/A')} |"
            )
            # Per-peer red flags
            peer_flags = np.get("red_flags", [])
            if peer_flags:
                for pf in peer_flags:
                    lines.append(f"  - 🚩 [{np.get('ticker', '')}] {pf}")
        lines.append("")

    # 10c. Accounting Policy Detection (from XBRL Notes)
    accounting_policies = normalized.get("accounting_policies", {})
    if accounting_policies:
        lines.append("### Detected Accounting Policies (from SEC XBRL Disclosures)")
        for policy_area, snippets in accounting_policies.items():
            lines.append(f"- **{policy_area}**:")
            for s in snippets[:2]:  # Max 2 snippets per area to control context size
                if len(s) > 250:
                    s = s[:250] + "..."
                lines.append(f"  - {s}")
        lines.append("")

    # 11. Supply Chain Intelligence (P2)
    supply_chain = bundled_data.get("supply_chain", {})
    if isinstance(supply_chain, dict) and "error" not in supply_chain:
        sc_relationships = supply_chain.get("relationships", [])
        sc_sources = supply_chain.get("sources_used", [])
        if sc_relationships or sc_sources:
            lines.append("## Supply Chain Intelligence")
            if sc_sources:
                lines.append(f"**Data Sources**: {', '.join(sc_sources)}")
                lines.append("")
            if sc_relationships:
                lines.append("### Extracted Supplier Relationships (Confidence Scored)")
                lines.append("| Supplier | Component/Service | Relationship Type | Confidence | Score | Evidence |")
                lines.append("|---|---|---|---|---|---|")
                for r in sc_relationships[:10]:  # Top 10 by score
                    supplier = r.get("supplier", "")[:30]
                    component = r.get("component", "")[:40]
                    rel_type = r.get("relationship_type", "")
                    confidence = r.get("confidence_hint", "")
                    score = r.get("confidence_score", "N/A")
                    evidence = (r.get("evidence", "") or "")[:80]
                    lines.append(
                        f"| {supplier} | {component} | {rel_type} | {confidence} | {score} | {evidence} |"
                    )
                lines.append("")
                # Geopolitical risk flags from conflict minerals data
                high_risk = [r for r in sc_relationships if r.get("confidence_score", 0) >= 0.7]
                if high_risk:
                    lines.append("**High-Confidence Supplier Dependencies:**")
                    for r in high_risk[:5]:
                        lines.append(f"  - {r.get('supplier')}: {r.get('component')} (Score: {r.get('confidence_score')})")
                    lines.append("")
        else:
            lines.append("## Supply Chain Intelligence")
            lines.append("No supplier relationships extracted. Consider the supply chain risk as unknown.")
            lines.append("")
    elif isinstance(supply_chain, dict) and "error" in supply_chain:
        lines.append("## Supply Chain Intelligence")
        lines.append(f"Supply chain analysis unavailable: {supply_chain.get('error', 'Unknown error')}")
        lines.append("")

    return "\n".join(lines)
