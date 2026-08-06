import re

# ──────────────────────────────────────────────
#  P1: Industry-Adjusted Thresholds
# ──────────────────────────────────────────────

# Threshold groups keyed by sector characteristics.
# Capital-intensive sectors tolerate higher leverage & accruals.
# Technology sectors demand tighter earnings quality.
# Financials skip debt/EBITDA (not meaningful).
INDUSTRY_THRESHOLDS = {
    "capital_intensive": {
        "accruals_ratio": 0.12,
        "debt_to_ebitda": 5.0,
        "fcf_conversion_min": 0.30,
        "capex_intensity_spike": 2.0,
    },
    "financial": {
        "accruals_ratio": 0.15,
        "debt_to_ebitda": None,       # N/A for financials
        "fcf_conversion_min": None,   # N/A for financials
        "capex_intensity_spike": 1.5,
    },
    "technology": {
        "accruals_ratio": 0.08,
        "debt_to_ebitda": 3.0,
        "fcf_conversion_min": 0.60,
        "capex_intensity_spike": 1.5,
    },
    "default": {
        "accruals_ratio": 0.10,
        "debt_to_ebitda": 4.0,
        "fcf_conversion_min": 0.50,
        "capex_intensity_spike": 1.5,
    },
}

# Map yfinance sector names → threshold groups
SECTOR_THRESHOLD_GROUP = {
    "Utilities": "capital_intensive",
    "Energy": "capital_intensive",
    "Oil & Gas": "capital_intensive",
    "Basic Materials": "capital_intensive",
    "Materials": "capital_intensive",
    "Industrials": "capital_intensive",
    "Real Estate": "capital_intensive",
    "Financial Services": "financial",
    "Financial": "financial",
    "Banks": "financial",
    "Insurance": "financial",
    "Technology": "technology",
    "Communication Services": "technology",
    "Telecommunications": "technology",
    "Media": "technology",
}

def _get_thresholds(sector: str = None) -> dict:
    """Return industry-adjusted thresholds for the given sector."""
    group = SECTOR_THRESHOLD_GROUP.get(sector, "default") if sector else "default"
    return INDUSTRY_THRESHOLDS.get(group, INDUSTRY_THRESHOLDS["default"])


# ──────────────────────────────────────────────

def _get_latest_and_prev(stmt, metric_names):
    """Helper to get latest and previous year values for a given metric."""
    for metric in metric_names:
        if metric in stmt and isinstance(stmt[metric], dict):
            dates = sorted(stmt[metric].keys(), reverse=True)
            if len(dates) >= 2:
                return stmt[metric][dates[0]], stmt[metric][dates[1]]
            elif len(dates) == 1:
                return stmt[metric][dates[0]], None
    return None, None


def _compute_core_metrics(info, income, balance, cashflow, red_flags, thresholds=None):
    """Compute the 7 core normalized metrics from financial statements.
    Shared between primary ticker and peer normalization.

    Args:
        thresholds: Optional dict of industry-adjusted thresholds from _get_thresholds().
    """
    if thresholds is None:
        thresholds = INDUSTRY_THRESHOLDS["default"]

    metrics = {}

    ebitda = info.get("ebitda", 0) or 0
    total_debt = info.get("totalDebt", 0) or 0
    total_cash = info.get("totalCash", 0) or 0
    enterprise_value = info.get("enterpriseValue", 0) or 0
    net_income = info.get("netIncomeToCommon", 0) or 0
    free_cashflow = info.get("freeCashflow", 0) or 0

    metrics["ebitda"] = ebitda
    metrics["net_debt"] = total_debt - total_cash

    if enterprise_value > 0 and ebitda > 0:
        metrics["ev_to_ebitda"] = round(enterprise_value / ebitda, 2)
    else:
        metrics["ev_to_ebitda"] = None

    # ── P1: Multi-year FCF Conversion Trend ──
    fcf_trend = {}
    fcf_stmt = cashflow.get("Free Cash Flow", {})
    ni_stmt = income.get("Net Income", {})
    if fcf_stmt and ni_stmt:
        common_years = sorted(
            set(fcf_stmt.keys()) & set(ni_stmt.keys()), reverse=True
        )
        for yr in common_years[:5]:
            fcf_val = fcf_stmt[yr]
            ni_val = ni_stmt[yr]
            if ni_val and ni_val > 0:
                fcf_trend[str(yr)] = round(fcf_val / ni_val, 2)
    metrics["fcf_conversion_trend"] = fcf_trend

    # Single-point FCF conversion (backward compatible; uses statement data if available)
    if fcf_trend:
        metrics["fcf_conversion"] = list(fcf_trend.values())[0]
    elif net_income > 0:
        metrics["fcf_conversion"] = round(free_cashflow / net_income, 2)
    else:
        metrics["fcf_conversion"] = None

    # ── CapEx Intensity (industry-adjusted spike threshold) ──
    capex_curr, capex_prev = _get_latest_and_prev(cashflow, ["Capital Expenditure", "CapitalExpenditure"])
    rev_curr, rev_prev = _get_latest_and_prev(income, ["Total Revenue"])

    if capex_curr is not None and rev_curr and rev_curr > 0:
        metrics["capex_intensity"] = round(abs(capex_curr) / rev_curr, 3)
        if capex_prev is not None and rev_prev and rev_prev > 0:
            intensity_prev = abs(capex_prev) / rev_prev
            spike_threshold = thresholds.get("capex_intensity_spike", 1.5)
            if metrics["capex_intensity"] > intensity_prev * spike_threshold:
                red_flags.append(f"CapEx Intensity spiked from {round(intensity_prev*100,1)}% to {round(metrics['capex_intensity']*100,1)}%.")

    # ── Accruals Gap (industry-adjusted threshold) ──
    ocf_curr, ocf_prev = _get_latest_and_prev(cashflow, ["Operating Cash Flow"])
    ni_curr, ni_prev = _get_latest_and_prev(income, ["Net Income"])
    assets_curr, assets_prev = _get_latest_and_prev(balance, ["Total Assets"])

    if ocf_curr is not None and ni_curr is not None and assets_curr and assets_curr > 0:
        accruals_ratio = (ni_curr - ocf_curr) / assets_curr
        metrics["accruals_ratio"] = round(accruals_ratio, 3)
        accruals_limit = thresholds.get("accruals_ratio", 0.10)
        if accruals_ratio > accruals_limit:
            red_flags.append(f"High Accruals Ratio ({round(accruals_ratio*100,1)}% > industry threshold {round(accruals_limit*100,1)}%). Earnings may be artificially inflated relative to cash flows.")

    # ── ROIC proxy ──
    ebit_curr, ebit_prev = _get_latest_and_prev(income, ["EBIT"])
    if ebit_curr is not None and assets_curr is not None:
        cl_curr, cl_prev = _get_latest_and_prev(balance, ["Current Liabilities", "Total Current Liabilities"])
        cl_curr = cl_curr or 0
        ic_curr = assets_curr - cl_curr
        if ic_curr > 0:
            roic = ebit_curr / ic_curr
            metrics["roic_proxy"] = round(roic, 3)

            if ebit_prev is not None and assets_prev is not None:
                cl_prev = cl_prev or 0
                ic_prev = assets_prev - cl_prev
                if ic_prev > 0:
                    roic_prev = ebit_prev / ic_prev
                    if roic < roic_prev - 0.05:
                        red_flags.append(f"ROIC declining significantly: {round(roic_prev*100,1)}% -> {round(roic*100,1)}%.")

    return metrics


def normalize_peer(peer: dict) -> dict:
    """Compute the same 7 normalized metrics for a single peer."""
    red_flags = []

    # Build info dict from peer's now-rich top-level keys
    # NOTE: Previously we had `peer.get("evToEbitda")` as a fallback for ebitda,
    # which was a critical bug (using a ratio as a dollar value). Fixed.
    info = {
        "ebitda": peer.get("ebitda", 0) or 0,
        "totalDebt": peer.get("totalDebt", 0) or 0,
        "totalCash": peer.get("totalCash", 0) or 0,
        "enterpriseValue": peer.get("enterpriseValue", 0) or 0,
        "netIncomeToCommon": peer.get("netIncomeToCommon", 0) or 0,
        "freeCashflow": peer.get("freeCashflow", 0) or 0,
        "sector": peer.get("sector"),
        "beta": peer.get("beta"),
    }

    income = peer.get("income_stmt", {})
    balance = peer.get("balance_sheet", {})
    cashflow = peer.get("cashflow", {})

    # Extract from statements if top-level keys are missing/zero
    if not info["ebitda"]:
        ebitda_curr, _ = _get_latest_and_prev(income, ["EBITDA"])
        if ebitda_curr:
            info["ebitda"] = ebitda_curr
    if not info["netIncomeToCommon"]:
        ni_curr, _ = _get_latest_and_prev(income, ["Net Income"])
        if ni_curr:
            info["netIncomeToCommon"] = ni_curr
    if not info["freeCashflow"]:
        fcf_curr, _ = _get_latest_and_prev(cashflow, ["Free Cash Flow"])
        if fcf_curr:
            info["freeCashflow"] = fcf_curr

    # Total debt from balance sheet (prefer top-level, fallback to statement)
    if not info["totalDebt"]:
        debt_curr, _ = _get_latest_and_prev(balance, ["Total Debt", "Long Term Debt"])
        if debt_curr:
            info["totalDebt"] = debt_curr
    if not info["totalCash"]:
        cash_curr, _ = _get_latest_and_prev(balance, ["Cash And Cash Equivalents", "Cash"])
        if cash_curr:
            info["totalCash"] = cash_curr

    # Enterprise value: top-level preferred, else approximate from market cap + debt - cash
    if not info["enterpriseValue"]:
        info["enterpriseValue"] = (peer.get("marketCap") or 0) + (info["totalDebt"] or 0) - (info["totalCash"] or 0)

    # Use peer's sector for industry-adjusted thresholds, fallback to default
    thresholds = _get_thresholds(info.get("sector")) if info.get("sector") else INDUSTRY_THRESHOLDS["default"]

    metrics = _compute_core_metrics(info, income, balance, cashflow, red_flags, thresholds)

    # Add identity and classification
    metrics["ticker"] = peer.get("ticker", "")
    metrics["sector"] = peer.get("sector")
    metrics["industry"] = peer.get("industry")
    if red_flags:
        metrics["red_flags"] = red_flags

    # Also carry forward the original peer surface metrics for backward compatibility
    metrics["marketCap"] = peer.get("marketCap")
    metrics["enterpriseValue"] = peer.get("enterpriseValue")
    metrics["trailingPE"] = peer.get("trailingPE")
    metrics["forwardPE"] = peer.get("forwardPE")
    metrics["priceToBook"] = peer.get("priceToBook")
    metrics["priceToSales"] = peer.get("priceToSales")
    metrics["evToEbitda"] = peer.get("evToEbitda") or metrics.get("ev_to_ebitda")
    metrics["enterpriseToRevenue"] = peer.get("enterpriseToRevenue")
    metrics["returnOnEquity"] = peer.get("returnOnEquity")
    metrics["returnOnAssets"] = peer.get("returnOnAssets")
    metrics["profitMargins"] = peer.get("profitMargins")
    metrics["grossMargins"] = peer.get("grossMargins")
    metrics["operatingMargins"] = peer.get("operatingMargins")
    metrics["revenueGrowth"] = peer.get("revenueGrowth")
    metrics["earningsGrowth"] = peer.get("earningsGrowth")
    metrics["debtToEquity"] = peer.get("debtToEquity")
    metrics["currentRatio"] = peer.get("currentRatio")
    metrics["beta"] = peer.get("beta")
    metrics["dividendYield"] = peer.get("dividendYield")

    return metrics


def normalize_all_peers(peers_data: dict) -> list:
    """Normalize metrics for all peers. Returns list of normalized peer dicts."""
    peers = peers_data.get("peers", [])
    normalized_peers = []
    for peer in peers:
        try:
            norm = normalize_peer(peer)
            normalized_peers.append(norm)
        except Exception:
            # If normalization fails for a peer, include raw data
            normalized_peers.append(peer)
    return normalized_peers


# ──────────────────────────────────────────────
#  Accounting Policy Detection (P0 Tasks 3 & 4)
# ──────────────────────────────────────────────

# Keyword patterns for detecting accounting policies from XBRL notes
POLICY_PATTERNS = {
    "Revenue Recognition": {
        "keywords": [
            r"revenue\s+recognition", r"ASC\s*606", r"IFRS\s*15",
            r"bill[\s-]and[\s-]hold", r"gross\s+vs\.?\s+net",
            r"principal\s+vs\.?\s+agent", r"performance\s+obligation",
            r"contract\s+asset", r"contract\s+liability",
            r"long[\s-]term\s+contract", r"percentage[\s-]of[\s-]completion",
            r"point\s+in\s+time", r"over\s+time.*revenue",
            r"multiple\s+element\s+arrangement", r"bundled\s+arrangement",
        ],
        "flag_if_missing": True,  # Important to flag if no disclosure found
    },
    "R&D / Software Capitalization": {
        "keywords": [
            r"capitalized\s+software", r"capitali[sz]ation\s+of\s+software",
            r"internal[\s-]use\s+software", r"software\s+development\s+cost",
            r"ASC\s*985", r"ASC\s*350[\s-]*40", r"research\s+and\s+development\s+cost",
            r"R&D\s+cost", r"development\s+cost.*capitali",
            r"technology\s+development", r"product\s+development\s+cost",
        ],
        "flag_if_missing": False,
    },
    "Lease Accounting": {
        "keywords": [
            r"right[\s-]of[\s-]use\s+asset", r"ROU\s+asset",
            r"operating\s+lease\s+liability", r"finance\s+lease",
            r"ASC\s*842", r"IFRS\s*16", r"lease\s+liability",
            r"lease\s+term", r"incremental\s+borrowing\s+rate",
        ],
        "flag_if_missing": False,
    },
    "M&A / Goodwill / Intangibles": {
        "keywords": [
            r"business\s+combination", r"goodwill\s+impairment",
            r"purchase\s+price\s+allocation", r"intangible\s+asset",
            r"ASC\s*805", r"ASC\s*350", r"fair\s+value\s+of\s+acquired",
            r"contingent\s+consideration", r"bargain\s+purchase",
        ],
        "flag_if_missing": False,
    },
    "Fair Value / Level 3 Assets": {
        "keywords": [
            r"fair\s+value\s+hierarchy", r"Level\s+[123]\s+(asset|input|measure)",
            r"ASC\s*820", r"fair\s+value\s+measurement",
            r"mark[\s-]to[\s-]market", r"significant\s+unobservable\s+input",
        ],
        "flag_if_missing": False,
    },
    "Stock-Based Compensation": {
        "keywords": [
            r"stock[\s-]based\s+compensation", r"share[\s-]based\s+payment",
            r"ASC\s*718", r"restricted\s+stock\s+unit",
            r"employee\s+stock\s+purchase\s+plan", r"option\s+pricing\s+model",
            r"Black[\s-]Scholes", r"grant[\s-]date\s+fair\s+value",
        ],
        "flag_if_missing": False,
    },
}


def _extract_accounting_policies(xbrl_disclosures_text: str) -> dict:
    """Scan XBRL notes text for accounting policy disclosures.
    Returns a dict mapping policy area → list of detected signal descriptions.
    """
    if not xbrl_disclosures_text:
        return {}

    # Normalize whitespace for regex matching
    text = " ".join(xbrl_disclosures_text.split())

    findings = {}
    for policy_area, config in POLICY_PATTERNS.items():
        matches = []
        for pattern in config["keywords"]:
            found = re.findall(pattern, text, re.IGNORECASE)
            if found:
                # Extract surrounding context (~100 chars around first match)
                for match_text in set(found):
                    idx = text.lower().find(match_text.lower())
                    if idx >= 0:
                        start = max(0, idx - 80)
                        end = min(len(text), idx + len(match_text) + 80)
                        snippet = text[start:end].strip()
                        matches.append(snippet)

        if matches:
            findings[policy_area] = matches[:3]  # Keep up to 3 snippets per area
        elif config.get("flag_if_missing"):
            findings[policy_area] = ["⚠️ No explicit disclosure found in XBRL notes."]

    return findings


def _build_accounting_notes(policy_findings: dict) -> str:
    """Build dynamic accounting_notes string from policy detection results."""
    if not policy_findings:
        return "No XBRL accounting policy disclosures available for analysis."

    notes_parts = []

    for policy_area, snippets in policy_findings.items():
        notes_parts.append(f"**{policy_area}**:")
        for snippet in snippets:
            # Clean and truncate snippet for brevity
            cleaned = snippet.strip()
            if len(cleaned) > 200:
                cleaned = cleaned[:200] + "..."
            notes_parts.append(f"  - {cleaned}")
        notes_parts.append("")

    return "\n".join(notes_parts).strip()


def normalize_accounting(bundled_data: dict) -> dict:
    """
    Takes the raw bundled data and computes normalized metrics
    and standardizes accounting policies. Includes multi-year ratios
    and EDGAR-based accounting policy detection.
    """
    normalized = {}
    red_flags = []

    market = bundled_data.get("market", {})
    if isinstance(market, Exception) or "error" in market:
        return {"error": "Market data unavailable for normalization", "red_flags": red_flags}

    info = market.get("info", {}) if isinstance(market, dict) else {}
    income = market.get("income_stmt", {})
    balance = market.get("balance_sheet", {})
    cashflow = market.get("cashflow", {})

    # ── P1: Detect sector & compute industry-adjusted thresholds ──
    sector = info.get("sector") or info.get("industry") or None
    thresholds = _get_thresholds(sector)
    normalized["sector"] = sector
    normalized["threshold_group"] = SECTOR_THRESHOLD_GROUP.get(sector, "default") if sector else "default"

    # Compute core 7 metrics with industry-adjusted thresholds
    metrics = _compute_core_metrics(info, income, balance, cashflow, red_flags, thresholds)
    normalized.update(metrics)

    # --- Red Flag Watchlist (industry-adjusted) ---
    ebitda = normalized.get("ebitda", 0)
    total_debt = info.get("totalDebt", 0) or 0

    # 1. Poor cash conversion (industry-adjusted)
    fcf_min = thresholds.get("fcf_conversion_min")
    if fcf_min is not None and normalized.get("fcf_conversion") is not None:
        if normalized["fcf_conversion"] < fcf_min:
            red_flags.append(f"Low cash conversion: FCF is only {normalized['fcf_conversion']}x of Net Income (below {sector or 'general'} threshold of {fcf_min}x).")
        # Also check multi-year trend for deterioration
        fcf_trend = normalized.get("fcf_conversion_trend", {})
        if len(fcf_trend) >= 2:
            values = list(fcf_trend.values())
            if values[0] < values[-1] * 0.7:  # >30% decline from oldest to newest
                red_flags.append(f"FCF Conversion deteriorating: {', '.join(f'{yr}={v}x' for yr, v in list(fcf_trend.items())[:3])}.")

    # 2. High Leverage (industry-adjusted; skipped for financials)
    debt_limit = thresholds.get("debt_to_ebitda")
    if debt_limit is not None and ebitda > 0 and (total_debt / ebitda) > debt_limit:
        red_flags.append(f"High Leverage: Debt/EBITDA is {round(total_debt/ebitda, 2)}x (Red Flag: >{debt_limit}x for {sector or 'general'} sector).")

    # 3. High short interest
    if (info.get("shortRatio") or 0) > 5:
        red_flags.append(f"High short interest ratio: {info.get('shortRatio')} days to cover.")

    # 4. Insider Activity
    insiders = market.get("insider_transactions", [])
    if isinstance(insiders, list) and len(insiders) > 0:
        sale_count = 0
        significant_sale_count = 0
        buy_count = 0
        
        for tx in insiders:
            if isinstance(tx, dict):
                text_val = str(tx).lower()
                shares = tx.get('Shares', 0)
                value = tx.get('Value', 0)
                
                is_sale = 'sale' in text_val or 'sell' in text_val or (isinstance(shares, (int, float)) and shares < 0)
                is_buy = 'buy' in text_val or 'purchase' in text_val or (isinstance(shares, (int, float)) and shares > 0)
                
                if is_sale:
                    sale_count += 1
                    # A sale is significant if value > $10M
                    if isinstance(value, (int, float)) and abs(value) > 10000000:
                        significant_sale_count += 1
                elif is_buy:
                    buy_count += 1

        # Only flag if there are multiple SIGNIFICANT sales
        if significant_sale_count >= 2:
            red_flags.append(f"Insider Activity: Detected {significant_sale_count} significant insider sales (>$10M). Note: selling can happen for personal reasons, but massive liquidation is a red flag.")
            
        # Optional: Add positive signal to normalized context if strong buying is detected
        if buy_count > sale_count and buy_count >= 2:
            normalized["insider_buying_signal"] = "Strong positive signal: Multiple insider purchases detected."

    # Low news volume
    news = bundled_data.get("news", {})
    if not isinstance(news, Exception) and "error" not in news:
        recent = news.get("recent_news", [])
        if len(recent) == 0:
            red_flags.append("Warning: Unusually low news volume for this ticker.")

    # ─────────────────────────────────────────
    #  P0: EDGAR-based accounting policy detection
    # ─────────────────────────────────────────
    edgar = bundled_data.get("edgar", {})
    if isinstance(edgar, dict) and "error" not in edgar:
        xbrl_highlights = edgar.get("xbrl_highlights", {})
        xbrl_disclosures = xbrl_highlights.get("XBRL Disclosures", "")

        policy_findings = _extract_accounting_policies(xbrl_disclosures)
        normalized["accounting_policies"] = policy_findings
        normalized["accounting_notes"] = _build_accounting_notes(policy_findings)

        # Enrich red flags with XBRL-disclosed risk signals
        if policy_findings.get("Revenue Recognition", []) and any(
            "⚠️ No explicit disclosure" in s for s in policy_findings["Revenue Recognition"]
        ):
            red_flags.append("Revenue Recognition Policy: No explicit ASC 606 / IFRS 15 disclosure found in XBRL notes — potential transparency concern.")

        if policy_findings.get("Fair Value / Level 3 Assets"):
            level3_signals = policy_findings["Fair Value / Level 3 Assets"]
            if any("Level 3" in s for s in level3_signals):
                red_flags.append("Fair Value Risk: Level 3 assets detected in XBRL disclosures — indicates significant unobservable inputs in valuation.")

        # R&D capitalization + high CapEx intensity = double-check
        if policy_findings.get("R&D / Software Capitalization"):
            if normalized.get("capex_intensity") and normalized["capex_intensity"] > 0.15:
                red_flags.append("CapEx-R&D Nexus: High CapEx intensity combined with software/R&D capitalization — verify expense vs. capitalize boundary.")

    else:
        normalized["accounting_policies"] = {}
        normalized["accounting_notes"] = "No XBRL accounting policy disclosures available for analysis."

    # ─────────────────────────────────────────
    #  Peer normalization
    # ─────────────────────────────────────────
    peers_data = bundled_data.get("peers", {})
    if isinstance(peers_data, dict) and "error" not in peers_data:
        normalized["peers"] = normalize_all_peers(peers_data)
    else:
        normalized["peers"] = []

    normalized["red_flags"] = red_flags
    return normalized
