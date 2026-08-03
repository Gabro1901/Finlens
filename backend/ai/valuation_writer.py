"""
Valuation Report Writer
=======================
Feeds computed valuation results + arbiter report to the Analyst LLM
and streams the resulting professional research report.

This is the final step in the pipeline: Collect -> Normalize -> Context ->
Optimistic/Pessimistic -> Arbiter -> Model Selector -> Python Engine -> Analyst Writer
"""

import json
from openai import AsyncOpenAI
from backend.ai.prompt_loader import load_prompt


async def generate_valuation_report(
    ticker: str,
    arbiter_report: str,
    valuation_results: dict,
    bundled_data: dict,
    api_key: str,
    model: str = "deepseek-v4-pro",
    language: str = "en",
):
    """
    Streams a professional investment research report built on the
    code-computed valuation results.

    Yields string chunks suitable for SSE streaming.
    """
    system_prompt = load_prompt("valuation_analyst.md")

    # Build the user prompt with all context injected
    user_prompt = _build_user_prompt(ticker, arbiter_report, valuation_results, bundled_data, language)

    client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"\n\nError generating valuation report: {str(e)}"


def _build_user_prompt(
    ticker: str,
    arbiter_report: str,
    valuation_results: dict,
    bundled_data: dict,
    language: str,
) -> str:
    """Construct the comprehensive user prompt with all data injected."""

    # Extract key financials for reference
    info = bundled_data.get('market', {}).get('info', {}) or {}
    norm = bundled_data.get('normalized', {}) or {}
    is_annual = bundled_data.get('market', {}).get('income_stmt', {}) or {}
    cf_annual = bundled_data.get('market', {}).get('cashflow', {}) or {}
    bs_annual = bundled_data.get('market', {}).get('balance_sheet', {}) or {}

    def _fy(d, key, yr):
        for k, v in d.get(key, {}).items():
            if k.startswith(yr) and v is not None:
                return float(v)
        return 0

    fy_years = ['2022', '2023', '2024', '2025']

    # Build financial summary
    fin_lines = []
    fin_lines.append("### Historical Financials")
    fin_lines.append("| Metric | FY2022 | FY2023 | FY2024 | FY2025 |")
    fin_lines.append("|---|---:|---:|---:|---:|")

    rev = {fy: _fy(is_annual, 'Total Revenue', fy) for fy in fy_years}
    ni = {fy: _fy(is_annual, 'Net Income', fy) for fy in fy_years}
    gp = {fy: _fy(is_annual, 'Gross Profit', fy) for fy in fy_years}
    fcf = {fy: _fy(cf_annual, 'Free Cash Flow', fy) for fy in fy_years}
    shares = {fy: _fy(is_annual, 'Diluted Average Shares', fy) for fy in fy_years}

    fin_lines.append(
        f"| Revenue ($B) | {rev['2022']/1e9:.1f} | {rev['2023']/1e9:.1f} | "
        f"{rev['2024']/1e9:.1f} | {rev['2025']/1e9:.1f} |"
    )
    fin_lines.append(
        f"| Gross Margin | {gp['2022']/rev['2022']*100:.1f}% | {gp['2023']/rev['2023']*100:.1f}% | "
        f"{gp['2024']/rev['2024']*100:.1f}% | {gp['2025']/rev['2025']*100:.1f}% |"
    ) if all(rev[f] > 0 for f in fy_years) else None

    eps_data = {fy: ni[fy]/shares[fy] if shares[fy] > 0 else 0 for fy in fy_years}
    fin_lines.append(
        f"| Diluted EPS | ${eps_data['2022']:.2f} | ${eps_data['2023']:.2f} | "
        f"${eps_data['2024']:.2f} | ${eps_data['2025']:.2f} |"
    )
    fin_lines.append(
        f"| FCF ($B) | {fcf['2022']/1e9:.1f} | {fcf['2023']/1e9:.1f} | "
        f"{fcf['2024']/1e9:.1f} | {fcf['2025']/1e9:.1f} |"
    )
    fin_lines.append(
        f"| FCF Conversion | {fcf['2022']/ni['2022']:.2f}x | {fcf['2023']/ni['2023']:.2f}x | "
        f"{fcf['2024']/ni['2024']:.2f}x | {fcf['2025']/ni['2025']:.2f}x |"
    ) if all(ni[f] > 0 for f in fy_years) else None

    # Peer metrics
    peer_lines = []
    peer_lines.append("### Peer Comparison")
    peer_lines.append("| Ticker | EV/EBITDA | Trailing P/E | ROIC | FCF Conv | Revenue Growth |")
    peer_lines.append("|---|---:|---:|---:|---:|---:|")
    def _v(val): return val if val is not None else 0
    for p in norm.get('peers', []):
        t = p.get('ticker', '')
        peer_lines.append(
            f"| {t} | "
            f"{_v(p.get('evToEbitda', p.get('ev_to_ebitda', p.get('ebitda', 0)))):.1f}x | "
            f"{_v(p.get('trailingPE', 0)):.1f}x | "
            f"{_v(p.get('roic_proxy', 0))*100:.0f}% | "
            f"{_v(p.get('fcf_conversion', 0)):.2f}x | "
            f"{_v(p.get('revenueGrowth', 0))*100:.0f}% |"
        )

    # Valuation results summary
    val_lines = []
    val_lines.append("### Valuation Results (COMPUTED BY PYTHON - VERIFIED)")
    val_lines.append(f"```json")
    val_lines.append(json.dumps(valuation_results, indent=2, default=str))
    val_lines.append(f"```")

    # Build final prompt from markdown template
    import os
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "valuation_prompt.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        # Fallback if file is missing
        template = "DATA INPUTS:\n\n{{FINANCIALS}}\n\n{{VALUATION_MATH}}\n\n{{ARBITER_REPORT}}"

    financials_text = '\n'.join(fin_lines) + '\n\n' + '\n'.join(peer_lines)
    valuation_text = '\n'.join(val_lines)
    
    # We also inject current price and target into the valuation text
    valuation_text = f"Current Price: ${(valuation_results.get('current_price') or 0):.2f}\nComputed Blended Target: ${(valuation_results.get('blended_target') or 0):.2f}\n\n" + valuation_text

    user_prompt = template.replace("{{FINANCIALS}}", financials_text)
    user_prompt = user_prompt.replace("{{VALUATION_MATH}}", valuation_text)
    user_prompt = user_prompt.replace("{{ARBITER_REPORT}}", arbiter_report[-20000:])
    user_prompt = user_prompt.replace("[Company Name]", ticker)
    user_prompt = user_prompt.replace("[Ticker]", ticker)
    
    if language == "it":
        user_prompt += "\n\nIMPORTANTE: Scrivi l'intero report di valutazione ESCLUSIVAMENTE in lingua ITALIANA."

    return user_prompt
