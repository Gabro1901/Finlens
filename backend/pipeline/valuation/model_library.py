"""
Valuation Model Library
=======================
Pure Python implementations of all supported valuation methodologies.
Every number is code-computed. No AI math.

Supported models:
  - dcf           Discounted Cash Flow (multi-scenario)
  - sotp          Sum of the Parts (segment-based)
  - comps         Comparable Company Analysis
  - ddm           Dividend Discount Model
  - ev_revenue    Enterprise Value / Revenue multiple
  - ev_ebitda     EV / EBITDA target multiple
  - pe_target     Price / Earnings target multiple

Each function receives the full bundled_data plus model-specific params
from the LLM's JSON config.
"""

from typing import Dict, List, Any, Optional


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _get_fy(d: dict, key: str, year: str) -> float:
    """Get a fiscal year value from a statement dict."""
    if key not in d:
        return 0.0
    for k, v in d[key].items():
        if k.startswith(year) and v is not None:
            return float(v)
    return 0.0


def _get_latest(d: dict, key: str) -> float:
    """Get the most recent value from a statement dict."""
    if key not in d:
        return 0.0
    vals = {k: float(v) for k, v in d[key].items() if v is not None}
    return vals[max(vals)] if vals else 0.0


def _extract_financials(data: dict) -> dict:
    """Extract key financials from bundled_data into a clean dict."""
    market = data.get('market', {}) or {}
    is_annual = market.get('income_stmt', {}) or {}
    bs_annual = market.get('balance_sheet', {}) or {}
    cf_annual = market.get('cashflow', {}) or {}
    info = market.get('info', {}) or {}
    norm = data.get('normalized', {}) or {}

    fy_years = ['2022', '2023', '2024', '2025']

    rev = {fy: _get_fy(is_annual, 'Total Revenue', fy) for fy in fy_years}
    ni  = {fy: _get_fy(is_annual, 'Net Income', fy) for fy in fy_years}
    ebit = {fy: _get_fy(is_annual, 'EBIT', fy) for fy in fy_years}
    gp = {fy: _get_fy(is_annual, 'Gross Profit', fy) for fy in fy_years}
    da = {fy: _get_fy(is_annual, 'Reconciled Depreciation', fy) for fy in fy_years}
    tax = {fy: _get_fy(is_annual, 'Tax Provision', fy) for fy in fy_years}
    pretax = {fy: _get_fy(is_annual, 'Pretax Income', fy) for fy in fy_years}
    shares = {fy: _get_fy(is_annual, 'Diluted Average Shares', fy) for fy in fy_years}
    fcf = {fy: _get_fy(cf_annual, 'Free Cash Flow', fy) for fy in fy_years}
    ocf = {fy: _get_fy(cf_annual, 'Operating Cash Flow', fy) for fy in fy_years}
    capex = {fy: abs(_get_fy(cf_annual, 'Capital Expenditure', fy)) for fy in fy_years}
    sbc = {fy: _get_fy(cf_annual, 'Stock Based Compensation', fy) for fy in fy_years}
    buyback = {fy: abs(_get_fy(cf_annual, 'Repurchase Of Capital Stock', fy)) for fy in fy_years}
    dividends = {fy: abs(_get_fy(cf_annual, 'Cash Dividends Paid', fy)) for fy in fy_years}

    total_debt = {fy: _get_fy(bs_annual, 'Total Debt', fy) for fy in fy_years}
    cash_st = {fy: _get_fy(bs_annual, 'Cash Cash Equivalents And Short Term Investments', fy) for fy in fy_years}
    wc = {fy: _get_fy(bs_annual, 'Working Capital', fy) for fy in fy_years}
    equity = {fy: _get_fy(bs_annual, 'Common Stock Equity', fy) for fy in fy_years}

    fy2025 = '2025'

    # Tax rate (2yr average)
    tax_rates = []
    for fy in ['2024', '2025']:
        if pretax.get(fy, 0) > 0:
            tax_rates.append(tax.get(fy, 0) / pretax[fy])
    avg_tax_rate = sum(tax_rates) / len(tax_rates) if tax_rates else 0.16

    # Net debt
    net_debt = total_debt.get(fy2025, 0) - cash_st.get(fy2025, 0)

    # Current market
    shares_out = float(info.get('sharesOutstanding') or 0)
    current_price = float(info.get('currentPrice') or 0)
    market_cap = float(info.get('marketCap') or 0)
    beta = float(info.get('beta') or 1.0)

    # EBITDA
    ebitda_val = norm.get('ebitda') or (ebit.get(fy2025, 0) + da.get(fy2025, 0))

    # ROIC
    roic = norm.get('roic_proxy') or 0

    # Peer data
    peers_raw = norm.get('peers', [])

    # Revenue growth CAGR
    rev_2022 = rev.get('2022', 0)
    rev_2025 = rev.get(fy2025, 0)
    rev_cagr = ((rev_2025 / rev_2022) ** (1/3) - 1) if rev_2022 > 0 else 0

    return {
        'revenue': rev,
        'net_income': ni,
        'ebit': ebit,
        'gross_profit': gp,
        'depreciation': da,
        'tax': tax,
        'pretax': pretax,
        'shares': shares,
        'fcf': fcf,
        'ocf': ocf,
        'capex': capex,
        'sbc': sbc,
        'buybacks': buyback,
        'dividends': dividends,
        'total_debt': total_debt,
        'cash_st': cash_st,
        'working_capital': wc,
        'equity': equity,
        'fy2025': fy2025,
        'avg_tax_rate': avg_tax_rate,
        'net_debt': net_debt,
        'shares_out': shares_out,
        'current_price': current_price,
        'market_cap': market_cap,
        'beta': beta,
        'ebitda': ebitda_val,
        'roic': roic,
        'peers_raw': peers_raw,
        'rev_cagr_3y': rev_cagr,
        'fy_years': fy_years,
        'info': info,
    }


def _capm_wacc(fin: dict, risk_free: float, erp: float, cost_of_debt: float) -> float:
    """Compute WACC via CAPM."""
    cost_equity = risk_free + fin['beta'] * erp
    mve = fin['market_cap']
    mvd = fin['total_debt'].get(fin['fy2025'], 0)
    if mve + mvd == 0:
        return cost_equity
    eq_w = mve / (mve + mvd)
    debt_w = mvd / (mve + mvd)
    return eq_w * cost_equity + debt_w * cost_of_debt * (1 - fin['avg_tax_rate'])


# ---------------------------------------------------------------------------
# 1. DISCOUNTED CASH FLOW (DCF)
# ---------------------------------------------------------------------------

def dcf_valuation(data: dict, params: dict) -> dict:
    """
    Multi-scenario Discounted Cash Flow valuation.

    Params expected from LLM:
      scenarios: [
        {name, probability, revenue_growth: [y1..y5], ebit_margin, terminal_growth},
        ...
      ]
      projection_years: int (default 5)
      risk_free_rate: float (default 0.038)
      equity_risk_premium: float (default 0.042)
      cost_of_debt: float (default 0.038)
      capex_pct: float
      da_pct: float
    """
    fin = _extract_financials(data)
    fy2025 = fin['fy2025']
    base_rev = fin['revenue'].get(fy2025, 0)
    shares_out = fin['shares_out']
    wc_ratio = fin['working_capital'].get(fy2025, 0) / base_rev if base_rev > 0 else 0

    rf = params.get('risk_free_rate', 0.038)
    erp = params.get('equity_risk_premium', 0.042)
    cod = params.get('cost_of_debt', 0.038)
    wacc = _capm_wacc(fin, rf, erp, cod)

    proj_years = params.get('projection_years', 5)
    capex_pct = params.get('capex_pct', 0.032)
    da_pct = params.get('da_pct', 0.028)
    tax_rate = fin['avg_tax_rate']

    scenarios = params.get('scenarios', [])
    if not scenarios:
        return {'model': 'dcf', 'error': 'No scenarios specified', 'results': {}}

    scenario_results = []
    for s in scenarios:
        name = s.get('name', 'Unnamed')
        prob = s.get('probability', 0)
        rev_growth = s.get('revenue_growth', [0.05]*proj_years)
        ebit_margin = s.get('ebit_margin', 0.30)
        terminal_g = s.get('terminal_growth', 0.025)

        revs, fcfs, pv_fcfs = [], [], []
        prev_rev = base_rev

        for i in range(proj_years):
            rev = prev_rev * (1 + rev_growth[i])
            ebit = rev * ebit_margin
            noplat = ebit * (1 - tax_rate)
            da_val = rev * da_pct
            capex_val = rev * capex_pct
            delta_wc = (rev - prev_rev) * wc_ratio
            fcf = noplat + da_val - capex_val - delta_wc

            pv = fcf / ((1 + wacc) ** (i + 1))
            revs.append(rev)
            fcfs.append(fcf)
            pv_fcfs.append(pv)
            prev_rev = rev

        terminal_fcf = fcfs[-1] * (1 + terminal_g)
        terminal_val = terminal_fcf / (wacc - terminal_g) if wacc > terminal_g else terminal_fcf * 10
        pv_terminal = terminal_val / ((1 + wacc) ** proj_years)

        ev = sum(pv_fcfs) + pv_terminal
        equity_val = ev - fin['net_debt']
        price = equity_val / shares_out if shares_out > 0 else 0
        upside = (price / fin['current_price'] - 1) * 100 if fin['current_price'] > 0 else 0

        scenario_results.append({
            'name': name,
            'probability': prob,
            'fy2026_revenue': revs[0] if revs else 0,
            'terminal_year_revenue': revs[-1] if revs else 0,
            'terminal_year_fcf': fcfs[-1] if fcfs else 0,
            'pv_projected_fcfs': sum(pv_fcfs),
            'terminal_value': terminal_val,
            'pv_terminal': pv_terminal,
            'enterprise_value': ev,
            'equity_value': equity_val,
            'implied_price': price,
            'upside_pct': upside,
            'tv_pct_of_ev': (pv_terminal / ev * 100) if ev > 0 else 0,
        })

    # Probability-weighted
    blended_price = sum(
        s['implied_price'] * s['probability'] for s in scenario_results
    ) if sum(s['probability'] for s in scenario_results) > 0 else 0

    return {
        'model': 'dcf',
        'error': None,
        'results': {
            'wacc': wacc,
            'tax_rate': tax_rate,
            'projection_years': proj_years,
            'scenarios': scenario_results,
            'blended_price': blended_price,
            'current_price': fin['current_price'],
            'blended_upside_pct': (blended_price / fin['current_price'] - 1) * 100 if fin['current_price'] > 0 else 0,
        }
    }


# ---------------------------------------------------------------------------
# 2. SUM OF THE PARTS (SOTP)
# ---------------------------------------------------------------------------

def sotp_valuation(data: dict, params: dict) -> dict:
    """
    Sum of the Parts valuation with segment-level multiples.

    Params expected from LLM:
      segments: [
        {
          name, revenue_pct, revenue_growth,
          ebitda_margin, multiple_low, multiple_high
        },
        ...
      ]
      base_year: str (default '2025')
    """
    fin = _extract_financials(data)
    fy2025 = fin['fy2025']
    base_rev = fin['revenue'].get(fy2025, 0)
    shares_out = fin['shares_out']

    segments = params.get('segments', [])
    if not segments:
        return {'model': 'sotp', 'error': 'No segments specified', 'results': {}}

    seg_results = []
    total_ev_low, total_ev_mid, total_ev_high = 0, 0, 0

    for seg in segments:
        name = seg.get('name', 'Segment')
        rev_pct = seg.get('revenue_pct', 0)
        growth = seg.get('revenue_growth', 0.05)
        ebitda_margin = seg.get('ebitda_margin', 0.30)
        mult_low = seg.get('multiple_low', 10)
        mult_high = seg.get('multiple_high', 15)

        seg_rev_fy25 = base_rev * rev_pct
        seg_rev_fy26 = seg_rev_fy25 * (1 + growth)
        seg_ebitda = seg_rev_fy26 * ebitda_margin

        ev_low = seg_ebitda * mult_low
        ev_high = seg_ebitda * mult_high
        ev_mid = (ev_low + ev_high) / 2

        total_ev_low += ev_low
        total_ev_mid += ev_mid
        total_ev_high += ev_high

        seg_results.append({
            'name': name,
            'fy2026_ebitda': seg_ebitda,
            'multiple_range': [mult_low, mult_high],
            'ev_range': [ev_low, ev_high],
            'ev_mid': ev_mid,
        })

    net_debt = fin['net_debt']
    price_low = (total_ev_low - net_debt) / shares_out if shares_out > 0 else 0
    price_mid = (total_ev_mid - net_debt) / shares_out if shares_out > 0 else 0
    price_high = (total_ev_high - net_debt) / shares_out if shares_out > 0 else 0

    return {
        'model': 'sotp',
        'error': None,
        'results': {
            'segments': seg_results,
            'total_ev_low': total_ev_low,
            'total_ev_mid': total_ev_mid,
            'total_ev_high': total_ev_high,
            'net_debt': net_debt,
            'price_low': price_low,
            'price_mid': price_mid,
            'price_high': price_high,
            'current_price': fin['current_price'],
        }
    }


# ---------------------------------------------------------------------------
# 3. COMPARABLE COMPANY ANALYSIS
# ---------------------------------------------------------------------------

def comps_valuation(data: dict, params: dict) -> dict:
    """
    Comparable company analysis using peer multiples.

    Params expected from LLM:
      peer_tickers: [str]  (which peers to include)
      metrics: [str]       ('ev_ebitda', 'pe', 'ev_revenue', 'pb')
      quality_adjustment: bool
      quality_premium_pct: float  (e.g. 0.30 for 30% premium vs. median)
    """
    fin = _extract_financials(data)
    peers_raw = fin['peers_raw']
    shares_out = fin['shares_out']
    current_price = fin['current_price']
    ebitda_val = fin['ebitda']
    ni_fy25 = fin['net_income'].get(fin['fy2025'], 0)
    rev_fy25 = fin['revenue'].get(fin['fy2025'], 0)
    equity_fy25 = fin['equity'].get(fin['fy2025'], 0)

    peer_tickers = params.get('peer_tickers', ['AMZN', 'GOOG'])
    metrics = params.get('metrics', ['ev_ebitda', 'pe'])
    quality_adj = params.get('quality_adjustment', False)
    quality_premium = params.get('quality_premium_pct', 0.30)

    # Extract peer multiples
    peer_data = {}
    for p in peers_raw:
        t = p.get('ticker', '')
        if t not in peer_tickers:
            continue
        peer_data[t] = {
            'ev_ebitda': float(p.get('evToEbitda', p.get('ev_to_ebitda', p.get('ebitda', 0)))),
            'trailing_pe': float(p.get('trailingPE', 0)),
            'ev_revenue': float(p.get('enterpriseToRevenue', 0)) if 'enterpriseToRevenue' in p else 0,
            'pb': float(p.get('priceToBook', 0)) if 'priceToBook' in p else 0,
            'roic': float(p.get('roic_proxy', 0)),
            'fcf_conv': float(p.get('fcf_conversion', 0)),
            'rev_growth': float(p.get('revenueGrowth', 0)),
        }

    if not peer_data:
        return {'model': 'comps', 'error': 'No peer data available for specified tickers', 'results': {}}

    comp_results = {}

    # EV/EBITDA
    if 'ev_ebitda' in metrics:
        ev_ebitda_values = [v['ev_ebitda'] for v in peer_data.values() if v['ev_ebitda'] > 0]
        if ev_ebitda_values:
            median_mult = sum(ev_ebitda_values) / len(ev_ebitda_values)
            unadj_ev = median_mult * ebitda_val
            unadj_price = (unadj_ev - fin['net_debt']) / shares_out if shares_out > 0 else 0

            if quality_adj:
                q_mult = median_mult * (1 + quality_premium)
                q_ev = q_mult * ebitda_val
                q_price = (q_ev - fin['net_debt']) / shares_out if shares_out > 0 else 0
            else:
                q_mult, q_price = None, None

            comp_results['ev_ebitda'] = {
                'peer_median_multiple': median_mult,
                'quality_adjusted_multiple': q_mult,
                'implied_price_unadjusted': unadj_price,
                'implied_price_quality_adjusted': q_price,
            }

    # P/E
    if 'pe' in metrics:
        pe_values = [v['trailing_pe'] for v in peer_data.values() if v['trailing_pe'] > 0]
        if pe_values and ni_fy25 > 0:
            median_pe = sum(pe_values) / len(pe_values)
            pe_price = median_pe * (ni_fy25 / shares_out) if shares_out > 0 else 0
            comp_results['pe'] = {
                'peer_median_pe': median_pe,
                'implied_price': pe_price,
            }

    # EV/Revenue
    if 'ev_revenue' in metrics:
        ev_rev_values = [v['ev_revenue'] for v in peer_data.values() if v['ev_revenue'] > 0]
        if ev_rev_values and rev_fy25 > 0:
            median_rev = sum(ev_rev_values) / len(ev_rev_values)
            rev_ev = median_rev * rev_fy25
            rev_price = (rev_ev - fin['net_debt']) / shares_out if shares_out > 0 else 0
            comp_results['ev_revenue'] = {
                'peer_median_multiple': median_rev,
                'implied_price': rev_price,
            }

    # P/B
    if 'pb' in metrics:
        pb_values = [v['pb'] for v in peer_data.values() if v['pb'] > 0]
        if pb_values and equity_fy25 > 0 and shares_out > 0:
            median_pb = sum(pb_values) / len(pb_values)
            pb_price = median_pb * (equity_fy25 / shares_out)
            comp_results['pb'] = {
                'peer_median_pb': median_pb,
                'implied_price': pb_price,
            }

    # Blend
    prices = []
    for metric_name, cr in comp_results.items():
        if metric_name == 'ev_ebitda':
            prices.append(cr.get('implied_price_quality_adjusted') or cr['implied_price_unadjusted'])
        else:
            if 'implied_price' in cr and cr['implied_price'] > 0:
                prices.append(cr['implied_price'])
    blended = sum(prices) / len(prices) if prices else 0

    return {
        'model': 'comps',
        'error': None,
        'results': {
            'peer_tickers_used': list(peer_data.keys()),
            'peer_details': {t: {
                'ev_ebitda': v['ev_ebitda'],
                'pe': v['trailing_pe'],
                'roic': v['roic'],
            } for t, v in peer_data.items()},
            'metrics_computed': comp_results,
            'blended_price': blended,
            'current_price': current_price,
        }
    }


# ---------------------------------------------------------------------------
# 4. DIVIDEND DISCOUNT MODEL (DDM)
# ---------------------------------------------------------------------------

def ddm_valuation(data: dict, params: dict) -> dict:
    """
    Gordon Growth / Multi-stage Dividend Discount Model.

    Params expected from LLM:
      dividend_growth_stage1: float
      stage1_years: int
      terminal_dividend_growth: float
      cost_of_equity: float (optional; computed via CAPM if not provided)
    """
    fin = _extract_financials(data)
    shares_out = fin['shares_out']
    current_price = fin['current_price']

    fy2025 = fin['fy2025']
    dividends_paid = fin['dividends'].get(fy2025, 0)
    shares_avg = fin['shares'].get(fy2025, shares_out)
    dps_current = dividends_paid / shares_avg if shares_avg > 0 else 0

    rf = params.get('risk_free_rate', 0.038)
    erp = params.get('equity_risk_premium', 0.042)
    coe = params.get('cost_of_equity') or (rf + fin['beta'] * erp)

    stage1_growth = params.get('dividend_growth_stage1', 0.08)
    stage1_years = params.get('stage1_years', 5)
    terminal_g = params.get('terminal_dividend_growth', 0.03)

    if dps_current <= 0:
        return {'model': 'ddm', 'error': 'Company does not pay dividends; DDM not applicable', 'results': {}}

    pv_dividends = 0
    dps = dps_current
    for i in range(1, stage1_years + 1):
        dps *= (1 + stage1_growth)
        pv_dividends += dps / ((1 + coe) ** i)

    terminal_dps = dps * (1 + terminal_g)
    terminal_value = terminal_dps / (coe - terminal_g) if coe > terminal_g else dps * 20
    pv_terminal = terminal_value / ((1 + coe) ** stage1_years)

    fair_value = pv_dividends + pv_terminal
    upside = (fair_value / current_price - 1) * 100 if current_price > 0 else 0

    return {
        'model': 'ddm',
        'error': None,
        'results': {
            'dividend_per_share_current': dps_current,
            'cost_of_equity': coe,
            'stage1_growth': stage1_growth,
            'terminal_growth': terminal_g,
            'pv_dividends': pv_dividends,
            'terminal_value': terminal_value,
            'fair_value': fair_value,
            'current_price': current_price,
            'upside_pct': upside,
        }
    }


# ---------------------------------------------------------------------------
# 5. EV / REVENUE MULTIPLE
# ---------------------------------------------------------------------------

def ev_revenue_valuation(data: dict, params: dict) -> dict:
    """
    Enterprise Value / Revenue multiple valuation.
    Appropriate for high-growth, pre-profit or early-profitability companies.

    Params expected from LLM:
      target_ev_revenue: float  (the multiple to apply)
      revenue_year: str         (which fiscal year revenue to use, e.g. '2025' or '2026')
      fwd_revenue_growth: float (if using forward revenue estimate)
    """
    fin = _extract_financials(data)
    shares_out = fin['shares_out']

    target_mult = params.get('target_ev_revenue', 0)
    rev_year = params.get('revenue_year', '2025')
    fwd_growth = params.get('fwd_revenue_growth', 0)

    if rev_year == '2025':
        rev = fin['revenue'].get('2025', 0)
    elif rev_year == '2026':
        rev = fin['revenue'].get('2025', 0) * (1 + fwd_growth)
    else:
        rev = fin['revenue'].get(rev_year, 0)

    if rev <= 0 or target_mult <= 0:
        return {'model': 'ev_revenue', 'error': 'Invalid revenue or multiple', 'results': {}}

    ev = rev * target_mult
    equity_val = ev - fin['net_debt']
    price = equity_val / shares_out if shares_out > 0 else 0
    upside = (price / fin['current_price'] - 1) * 100 if fin['current_price'] > 0 else 0

    return {
        'model': 'ev_revenue',
        'error': None,
        'results': {
            'revenue_used': rev,
            'target_multiple': target_mult,
            'enterprise_value': ev,
            'equity_value': equity_val,
            'implied_price': price,
            'current_price': fin['current_price'],
            'upside_pct': upside,
        }
    }


# ---------------------------------------------------------------------------
# 6. EV / EBITDA TARGET MULTIPLE
# ---------------------------------------------------------------------------

def ev_ebitda_valuation(data: dict, params: dict) -> dict:
    """
    Target EV/EBITDA multiple valuation.

    Params expected from LLM:
      target_ev_ebitda: float
      ebitda_growth: float  (for forward EBITDA estimate; 0 = use current)
    """
    fin = _extract_financials(data)
    shares_out = fin['shares_out']

    target_mult = params.get('target_ev_ebitda', 0)
    ebitda_growth = params.get('ebitda_growth', 0)

    ebitda_used = fin['ebitda'] * (1 + ebitda_growth)

    if ebitda_used <= 0 or target_mult <= 0:
        return {'model': 'ev_ebitda', 'error': 'Invalid EBITDA or multiple', 'results': {}}

    ev = ebitda_used * target_mult
    equity_val = ev - fin['net_debt']
    price = equity_val / shares_out if shares_out > 0 else 0
    upside = (price / fin['current_price'] - 1) * 100 if fin['current_price'] > 0 else 0

    return {
        'model': 'ev_ebitda',
        'error': None,
        'results': {
            'ebitda_used': ebitda_used,
            'target_multiple': target_mult,
            'enterprise_value': ev,
            'equity_value': equity_val,
            'implied_price': price,
            'current_price': fin['current_price'],
            'upside_pct': upside,
        }
    }


# ---------------------------------------------------------------------------
# 7. P/E TARGET MULTIPLE
# ---------------------------------------------------------------------------

def pe_target_valuation(data: dict, params: dict) -> dict:
    """
    Price/Earnings target multiple valuation.

    Params expected from LLM:
      target_pe: float
      eps_year: str  ('current', 'fy2026', 'fy2027')
      eps_estimate: float  (override if using forward EPS)
    """
    fin = _extract_financials(data)
    shares_out = fin['shares_out']
    fy2025 = fin['fy2025']

    target_pe = params.get('target_pe', 0)
    eps_year = params.get('eps_year', 'current')
    eps_override = params.get('eps_estimate', 0)

    if eps_override > 0:
        eps = eps_override
    else:
        ni_fy25 = fin['net_income'].get(fy2025, 0)
        if eps_year == 'current':
            eps = ni_fy25 / shares_out if shares_out > 0 else 0
        elif eps_year == 'fy2026':
            # Use analyst estimates if available
            fwd_eps = fin['info'].get('forwardEps', 0)
            eps = float(fwd_eps) if fwd_eps else (ni_fy25 / shares_out * 1.08 if shares_out > 0 else 0)
        elif eps_year == 'fy2027':
            eps = (ni_fy25 / shares_out * 1.15) if shares_out > 0 else 0
        else:
            eps = ni_fy25 / shares_out if shares_out > 0 else 0

    if eps <= 0 or target_pe <= 0:
        return {'model': 'pe_target', 'error': 'Invalid EPS or P/E', 'results': {}}

    price = eps * target_pe
    upside = (price / fin['current_price'] - 1) * 100 if fin['current_price'] > 0 else 0

    return {
        'model': 'pe_target',
        'error': None,
        'results': {
            'eps_used': eps,
            'target_pe': target_pe,
            'implied_price': price,
            'current_price': fin['current_price'],
            'upside_pct': upside,
        }
    }


# ---------------------------------------------------------------------------
# 8. NET ASSET VALUE (NAV)
# ---------------------------------------------------------------------------

def nav_valuation(data: dict, params: dict) -> dict:
    """
    Net Asset Value / Book Value based valuation.
    Appropriate for financials, REITs, resource companies.

    Params expected from LLM:
      target_pb: float  (target Price/Book multiple)
      adjust_book: bool  (whether to adjust book value)
    """
    fin = _extract_financials(data)
    shares_out = fin['shares_out']
    fy2025 = fin['fy2025']

    equity_val = fin['equity'].get(fy2025, 0)
    bvps = equity_val / shares_out if shares_out > 0 else 0

    target_pb = params.get('target_pb', 1.5)
    adjust_book = params.get('adjust_book', False)

    if adjust_book:
        # Simple adjustment: add back goodwill/intangible write-downs (not implemented in MVP)
        pass

    if bvps <= 0 or target_pb <= 0:
        return {'model': 'nav', 'error': 'Invalid book value or P/B multiple', 'results': {}}

    price = bvps * target_pb
    upside = (price / fin['current_price'] - 1) * 100 if fin['current_price'] > 0 else 0

    return {
        'model': 'nav',
        'error': None,
        'results': {
            'book_value_per_share': bvps,
            'target_pb': target_pb,
            'implied_price': price,
            'current_price': fin['current_price'],
            'upside_pct': upside,
        }
    }


# ---------------------------------------------------------------------------
# MODEL REGISTRY
# ---------------------------------------------------------------------------

MODEL_REGISTRY = {
    'dcf': dcf_valuation,
    'sotp': sotp_valuation,
    'comps': comps_valuation,
    'ddm': ddm_valuation,
    'ev_revenue': ev_revenue_valuation,
    'ev_ebitda': ev_ebitda_valuation,
    'pe_target': pe_target_valuation,
    'nav': nav_valuation,
}
