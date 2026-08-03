"""
Model Selector
==============
LLM integration that analyzes the business (from arbiter report + raw data)
and selects the most appropriate valuation methodology with parameters.

Outputs a JSON config consumed by ValuationEngine.
"""

import json
import re
from openai import AsyncOpenAI


DEFAULT_VALUATION_CONFIG = {
    "business_profile": {
        "type": "mature_technology",
        "lifecycle_stage": "mature",
        "revenue_drivers": ["general"]
    },
    "valuation_plan": {
        "primary": {
            "model": "dcf",
            "weight": 0.6,
            "params": {
                "wacc": 0.09,
                "terminal_growth_rate": 0.02,
                "projection_years": 5
            }
        },
        "cross_checks": [
            {
                "label": "pe_target",
                "model": "pe_target",
                "weight": 0.2,
                "params": {
                    "target_pe": 20
                }
            },
            {
                "label": "ev_ebitda",
                "model": "ev_ebitda",
                "weight": 0.2,
                "params": {
                    "target_multiple": 12
                }
            }
        ]
    }
}


SELECTOR_SYSTEM_PROMPT = """You are a senior valuation analyst at a top-tier investment bank. Your job is to analyze a company and select the most appropriate valuation methodology.

You will receive:
1. The full adjudicated arbiter report (already synthesized from optimistic and pessimistic analyses)
2. Key financial metrics extracted from the company's filings

Your task: Output a VALID JSON object with this exact structure:

{
  "business_profile": {
    "type": "mature_technology | high_growth | cyclical_industrial | financial_services | real_estate | resource_extraction | biotech_pharma | consumer_staples | other",
    "characteristics": ["list", "of", "key", "characteristics"],
    "lifecycle_stage": "mature_growth | hyper_growth | stable_mature | decline | turnaround",
    "rationale": "One sentence explaining your classification."
  },
  "valuation_plan": {
    "primary": {
      "model": "dcf | sotp | comps | ddm | ev_revenue | ev_ebitda | pe_target | nav",
      "weight": 0.50,
      "params": { ... model-specific parameters ... }
    },
    "cross_checks": [
      {
        "label": "comps_cross_check",
        "model": "comps | ev_ebitda | pe_target | ev_revenue | ddm",
        "weight": 0.25,
        "params": { ... }
      },
      ...
    ]
  }
}

MODEL SELECTION RULES:

1. **DCF** — Use for: mature companies with stable, predictable cash flows. Requires: at least 3 years of positive operating cash flow, visibility into future growth. NOT for: pre-revenue, highly cyclical (without scenario modeling), financials.

2. **SOTP (Sum of the Parts)** — Use for: conglomerates or companies with distinctly different business segments. Requires: segment revenue/profit breakdown available. Each segment gets its own multiple based on comparable companies for that segment type.

3. **Comps (Comparable Company Analysis)** — ALWAYS include as a cross-check. Use: peer trading multiples (EV/EBITDA, P/E, EV/Revenue, P/B). For quality companies, apply a quality premium if ROIC materially exceeds peers.

4. **DDM (Dividend Discount Model)** — Use for: mature companies with a consistent, growing dividend policy. NOT for: companies that don't pay dividends or have erratic dividend history.

5. **EV/Revenue** — Use for: high-growth companies that are pre-profit or have very low margins. The multiple should reflect growth rate and sector norms.

6. **EV/EBITDA** — Use for: profitable companies where EBITDA is the primary market valuation metric. Best for capital-intensive industries.

7. **P/E Target** — Use for: companies where earnings are the primary market focus. Anchor the multiple on peers, growth rate, and quality (ROIC).

8. **NAV (Net Asset Value)** — Use for: financials (banks, insurance), REITs, resource companies where asset value is the primary driver.

PARAMETER RULES:

For DCF:
- "scenarios": Array of {name, probability, revenue_growth: [5 annual rates], ebit_margin, terminal_growth}
- Probabilities must sum to 1.0
- Revenue growth should reflect the business's realistic trajectory based on historical CAGR, sector trends, and the arbiter's findings
- EBIT margin should be grounded in historical levels with appropriate adjustments for mix shift, scale, or pressure
- Terminal growth: 2.0-3.5% for mature companies, 3.0-5.0% for high-growth
- Also include: risk_free_rate (default 0.038), equity_risk_premium (default 0.042), cost_of_debt (default 0.038)

For SOTP:
- "segments": Array of {name, revenue_pct, revenue_growth, ebitda_margin, multiple_low, multiple_high}
- Revenue percentages must sum to 1.0

For Comps:
- "peer_tickers": Array of ticker symbols (from the available peers)
- "metrics": Array of metrics to use (ev_ebitda, pe, ev_revenue, pb)
- "quality_adjustment": true/false
- "quality_premium_pct": e.g. 0.30 for 30% premium

For DDM:
- "dividend_growth_stage1": initial growth rate
- "stage1_years": number of high-growth years
- "terminal_dividend_growth": terminal growth rate

For EV/Revenue, EV/EBITDA, P/E Target:
- Specify the target multiple, reference year, and any forward estimates

WEIGHTING:
- Primary model: 40-60% weight
- Each cross-check: 15-30% weight
- All weights must sum to 1.0

CRITICAL: Output ONLY the JSON object. No markdown, no explanation outside the JSON. The JSON must be valid and parseable.
"""


SELECTOR_USER_PROMPT_TEMPLATE = """Company: {ticker}

=== ARBITER'S ADJUDICATED REPORT ===
{arbiter_report}

=== KEY FINANCIAL METRICS ===
{metrics_summary}

=== AVAILABLE PEER TICKERS ===
{peer_tickers}

Based on the above, select the most appropriate valuation methodology and output the JSON config.
"""


async def select_valuation_model(
    ticker: str,
    arbiter_report: str,
    bundled_data: dict,
    api_key: str,
    model: str = "deepseek-v4-flash",
) -> dict:
    """
    Calls the LLM to analyze the business and select the right valuation model(s).

    Returns the parsed JSON config dict, or a dict with an 'error' key.
    """
    # Build a concise metrics summary from bundled_data
    info = bundled_data.get('market', {}).get('info', {}) or {}
    norm = bundled_data.get('normalized', {}) or {}
    is_annual = bundled_data.get('market', {}).get('income_stmt', {}) or {}

    def _fy(key, yr):
        d = is_annual.get(key, {})
        for k, v in d.items():
            if k.startswith(yr) and v is not None:
                return float(v)
        return 0

    rev_25 = _fy('Total Revenue', '2025')
    ni_25 = _fy('Net Income', '2025')
    gp_25 = _fy('Gross Profit', '2025')
    ebit_25 = _fy('EBIT', '2025')
    rev_24 = _fy('Total Revenue', '2024')
    ni_24 = _fy('Net Income', '2024')

    gm = (gp_25 / rev_25 * 100) if rev_25 > 0 else 0
    om = (ebit_25 / rev_25 * 100) if rev_25 > 0 else 0
    nim = (ni_25 / rev_25 * 100) if rev_25 > 0 else 0
    rev_growth = ((rev_25 / rev_24 - 1) * 100) if rev_24 > 0 else 0
    ni_growth = ((ni_25 / ni_24 - 1) * 100) if ni_24 > 0 else 0

    peers_raw = norm.get('peers', [])
    peer_tickers = [p.get('ticker', '') for p in peers_raw if p.get('ticker')]

    metrics_summary = f"""
Revenue (FY2025): ${rev_25/1e9:.1f}B
Net Income (FY2025): ${ni_25/1e9:.1f}B
Revenue Growth (YoY): {rev_growth:.1f}%
Net Income Growth (YoY): {ni_growth:.1f}%
Gross Margin: {gm:.1f}%
Operating Margin: {om:.1f}%
Net Margin: {nim:.1f}%
ROIC (proxy): {norm.get('roic_proxy', 0)*100:.1f}%
FCF Conversion: {norm.get('fcf_conversion', 0):.2f}x
EV/EBITDA: {norm.get('ev_to_ebitda', 0):.1f}x
Dividend Yield: {float(info.get('dividendYield', 0))*100:.2f}%
Beta: {float(info.get('beta', 1.0)):.2f}
Sector: {info.get('sector', 'Unknown')}
Industry: {info.get('industry', 'Unknown')}
"""

    user_prompt = SELECTOR_USER_PROMPT_TEMPLATE.format(
        ticker=ticker,
        arbiter_report=arbiter_report[-15000:],  # last 15K chars — should contain conclusions
        metrics_summary=metrics_summary,
        peer_tickers=', '.join(peer_tickers),
    )

    client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SELECTOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            temperature=0.3,  # Low temperature for structured output
        )

        content = response.choices[0].message.content or ""
        return _parse_selector_output(content)

    except Exception as e:
        print(f"Model selection API failed: {e}. Falling back to default DCF.")
        return DEFAULT_VALUATION_CONFIG


def _parse_selector_output(content: str) -> dict:
    """Extract JSON from the LLM's response, handling markdown wrappers and fuzzy fallbacks."""
    # Try to find JSON block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
    if json_match:
        content_to_parse = json_match.group(1)
    else:
        content_to_parse = content

    # Try direct parse
    try:
        return json.loads(content_to_parse)
    except json.JSONDecodeError:
        pass

    # Try to find first { to last }
    start = content_to_parse.find('{')
    end = content_to_parse.rfind('}')
    if start >= 0 and end > start:
        try:
            return json.loads(content_to_parse[start:end+1])
        except json.JSONDecodeError:
            pass

    # Fuzzy matching for models
    print(f"Failed to parse model selector output as JSON. Trying fuzzy match on content length {len(content)}")
    content_lower = content.lower()
    
    # Extract some WACC or target_pe if possible
    wacc = 0.09
    wacc_match = re.search(r'wacc.*?([0-9]*\.[0-9]+)', content_lower)
    if wacc_match:
        try: wacc = float(wacc_match.group(1))
        except: pass

    if "dcf" in content_lower or "discounted cash flow" in content_lower:
        fallback = DEFAULT_VALUATION_CONFIG.copy()
        fallback["valuation_plan"]["primary"]["params"]["wacc"] = wacc
        return fallback
    elif "sotp" in content_lower or "sum of the parts" in content_lower:
        fallback = DEFAULT_VALUATION_CONFIG.copy()
        fallback["valuation_plan"]["primary"]["model"] = "sotp"
        return fallback

    return DEFAULT_VALUATION_CONFIG
