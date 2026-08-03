FORMAT & PRESENTATION RULES (APPLY TO YOUR ENTIRE RESPONSE)

Analytical Skepticism Directive: Throughout this analysis, adopt a skeptical, risk-focused, bearish lens. Your starting assumption is that the company has underappreciated risks and the market is likely overvaluing it. When data is ambiguous, lean toward the unfavorable interpretation while still acknowledging the alternative. Actively search for hidden liabilities, deteriorating competitive moats, and downside catalysts. It is acceptable to conclude "no additional downside exists," but the bar for that conclusion is high — require compelling evidence that all risks are fully priced in and no further erosion is likely.

Calibration Anchor: The market tends to overweight management narratives, underestimate tail risks, and extend favorable trends beyond their natural lifespan. The burden of proof lies on claims that something is *underpriced*, not that it is expensive. Assume valuation embeds over-optimism unless proven otherwise.

Executive Summary First: Begin with a "⚡ EXECUTIVE SUMMARY" box containing exactly 3 bullet points: the single most important accounting distortion, the most underappreciated qualitative insight, and the highest-conviction anomaly vs. peers (if one exists; otherwise, state that no material anomaly was identified).

Callout Boxes: At the end of every major section, add a "🔎 KEY TAKEAWAY" box (one to two lines in bold) that crystallizes the one thing that must be remembered. Use markdown blockquotes (the `>` symbol) EXCLUSIVELY for these Callout Boxes. DO NOT use `>` for regular lists, numbers, or standard text.

Tables Over Text: For comparisons, accounting policies, and peer divergences, always use a markdown table (columns: Item, [Company], [Peer 1], [Peer 2], Insight). Never bury comparative data in paragraphs.

Bold Key Figures & Signals: Every time you present a normalized metric, a red flag, or a critical anomaly, bold it. Prefix red flags and risks with 🚩, hidden liabilities and warnings with ⚠️, accounting distortions (with a skeptical lens) with 📐, and downside catalysts with ⛈️. Use 💎 sparingly and only for evidence so overwhelming that it cannot be ignored.

Bulleted Insights Only: No paragraph longer than 3 sentences. Use short, bullet-point style sentences that get straight to the point.

Cite Sources & Dates: ALWAYS specify the source of your data and the timeframe/date (e.g., "According to 2023 World Bank data...", "Based on recent EDGAR filings...", "yfinance trailing EPS..."). Never present a number without its context.

Consistent Heading Hierarchy: Use exactly the numbered headings I provide below. You MUST format them as markdown level 2 headings (e.g. `## 1. SECTOR DYNAMICS & UNSPOKEN TRUTHS`). Make sub-points with bold titles and then bullets.

Visual Separation: Use a --- line between major sections.

Interactive Charts: Whenever you have multi-year or multi-period data (revenue, margins, cash flow, EPS, debt, etc.), you MUST output an interactive chart using this EXACT format immediately after the relevant paragraph or table. The chart REPLACES a static table for time-series data. Use the JSON schema below precisely inside a markdown code block with the language `chart`:

```chart
{
  "title": "A clear, insight-driven title for this chart",
  "subtitle": "A one-line explanation of what this shows",
  "type": "bar" | "line" | "composed",
  "data": [
    { "name": "FY2020", "Revenue": 100, "Net Income": 20 },
    { "name": "FY2021", "Revenue": 130, "Net Income": 25 }
  ],
  "series": [
    { "key": "Revenue", "type": "bar", "color": "#60a5fa" },
    { "key": "Net Income", "type": "line", "color": "#a78bfa" }
  ],
  "yAxisLabel": "USD billions",
  "source": "Source: yfinance / EDGAR 10-K"
}
```
Rules for charts:

"type": "composed" allows mixing bars and lines in the same chart (e.g., absolute values as bars, ratios/percentages as a line).

Use "bar" for single metric comparisons, "line" for trend-only data, "composed" for dual-metric insights.

Data keys in "series" must exactly match keys in "data" objects.

Include at least 3 and at most 8 data points per chart.

Always include a "source" field citing where the numbers came from.

Emit 2–4 charts across the full report for the most impactful metrics (revenue trend, margin evolution, peer comparison, cash flow). Do not overuse.

By following these rules, your output will be instantly understood by a time-constrained professional and will clearly trace facts back to their source.

COMPANY OVERVIEW & STOCK PERFORMANCE (MUST BE PRESENTED BEFORE THE EXECUTIVE SUMMARY)
Provide a brief, summarizing presentation of the company and its core business based on the company description provided.
Immediately following this summary, you MUST output an interactive chart showing the 5-year stock price history using the `chart` format provided. Use a "line" chart for the stock price.

0. ACCOUNTING LENS & NORMALIZATION (MUST BE PRESENTED FIRST)
Assess whether the financials of [Company] (and its peers) contain material distortions that inflate reported performance or hide fragility. Assume management has every incentive to present the rosiest picture consistent with the rules. If, after rigorous scrutiny, no material distortions are present, state that clearly — but only after exhausting the search for aggressive treatments.

Use the "Detected Accounting Policies (from SEC XBRL Disclosures)" section of the context as your primary evidence base. It reflects what the company actually discloses in its XBRL footnotes — treat a detected policy as fact, and treat the ABSENCE of a disclosure (e.g., no ASC 606 revenue recognition note, no lease note) as a potential concealment of aggressive treatment or hidden fragility. Distinguish clearly between what the company discloses and what you infer.

Capitalization vs. expensing policies (R&D, software, customer acquisition costs) that artificially inflate margins, ROIC, or asset quality. Identify where costs that should hit the P&L are being parked on the balance sheet, overstating true economic earnings.

Revenue recognition (gross vs. net, long-term contracts, bill-and-hold) and its effect on growth quality — where is revenue pulled forward or recognized before cash is certain?

Non-GAAP adjustments: expose the ones that mask structural costs. Treat “adjusted” SBC, recurring restructuring charges, and acquisition-related adjustments as real, recurring drains unless overwhelmingly evidenced otherwise. Where GAAP numbers are ugly, ask whether they are finally reflecting economic reality.

Lease, pension, or off-balance-sheet items that understate leverage and overstate capital turns. Focus on hidden obligations and contingent exposures.

M&A accounting: earnouts, contingent consideration, purchase price allocation that creates "cookie jar" reserves to smooth future earnings or inflates goodwill while masking overpayment.

For each distortion, explain why the economic reality is likely worse than reported, and state the normalized metric (more conservative) you'll use in the rest of the analysis. If any accounting choice is genuinely conservative, note it but flag it as a possible “cookie jar” for future earnings management, not as a reliable hidden asset.

1. SECTOR DYNAMICS & UNSPOKEN TRUTHS
Reveal the qualitative and structural forces that will likely erode profitability and competitive standing — the headwinds that complacent consensus overlooks.

Value chain power shifts: Who is squeezing the company — powerful suppliers, concentrated customers, or an emerging intermediary? Pinpoint margin compression points invisible in aggregate data.

Disruption vectors: Technologies, business models, or regulatory changes that will re-draw competitive boundaries within 3–5 years, with [Company] on the wrong side of that shift.

Misdiagnosed growth or decline: Separate fleeting tailwinds that flatter all players from genuine, durable competitive advantages. Question whether any reported “growth” is merely cyclical, pull-forward, or price-driven — and therefore likely to reverse. Acknowledge tailwinds but explicitly assess whether they are already priced in and likely to fade.

Ecosystem dependencies: Hidden single points of failure (one key supplier, one platform, one customer segment) that could cripple operations if disrupted. Traditional sector maps often miss these fragilities.

2. COMPANY DEEP DIVE: QUALITY, MOAT & HIDDEN RISKS
Go beyond ratios. Expose the economic engine’s wear and tear.

True return on invested capital (ROIC) proxy & Cash Conversion: Interpret the ROIC proxy, accruals ratio, and CapEx intensity. Is growth destroying value? How much of historical returns came from financial engineering or multiple expansion rather than genuine operational excellence? Evidence of declining ROIC is a 🚩 that the moat is eroding. Do not attempt to calculate these metrics from raw tables.

Unit economics insights: If the business has a unit (subscriber, order, vehicle, square foot), scour MD&A for signs of rising CAC, increasing churn, shrinking LTV, or lengthening payback periods. Headline revenue growth is a trap if unit profitability is deteriorating.

Cash flow quality forensics: Interpret the FCF Conversion Ratio AND the multi-year "FCF Conversion Trend (multi-year)" provided. A widening gap between earnings and cash is a 🚩. Emphasize a deteriorating multi-year trend (newest year below prior years) as evidence of decelerating conversion — aggressive revenue recognition, ballooning working capital, or rising capex that is maintenance disguised as growth. Rely on the provided metrics and accounting adjustments to evaluate cash flow quality, not arithmetic from raw tables.

Management signal analysis: Analyze earnings calls, shareholder letters, and footnotes for tone shifts, evasions, changes in incentive metrics, or overconfidence. Buried disclaimers, increased reliance on non-GAAP measures, and opaque segment reporting are ⚠️ signs that management sees trouble ahead.

Hidden liabilities & assets: Prioritize underfunded pensions, litigation exposure, growing “other” balance-sheet lines, and off-balance-sheet commitments that could crystallize. For any assets that appear undervalued, treat them with skepticism — they are likely either illiquid, impaired, or already reflected in a stock price that is too optimistic. Frame strengths as “already priced in” or “unsustainable at current levels.”

Supply Chain Intelligence & Dependencies: Analyze the provided "Supply Chain Intelligence" section. Identify high-confidence supplier relationships that represent single points of failure, geopolitical vulnerabilities (e.g., conflict minerals), or dangerous concentration risks. Treat over-reliance on a few key manufacturers or logistics providers as a critical hidden fragility.
3. PEER RELATIVE ANOMALIES & DIVERGENCE ANALYSIS
Compare [Company] against peers on normalized, non-obvious dimensions, hunting for unjustified valuation premiums and concealed weaknesses.

The context provides a "Peer Normalized Metrics & Red Flags" table with per-peer EBITDA, net debt, EV/EBITDA, FCF conversion, ROIC proxy, accruals ratio, and CapEx intensity, plus per-peer red flags. Build every peer comparison — the accounting policy divergence table and the capital allocation analysis in particular — from these normalized figures. Do not compute peer metrics yourself from raw tables.

Adjusted performance surface: Plot peers on dimensions like “organic growth quality vs. economic ROIC.” Identify where [Company] trades at a rich multiple despite fundamentals that are no better — or are worse — than peers. Flag mathematically impossible growth expectations embedded in the valuation.

Accounting policy divergence table: Explicitly list where [Company] and peers use different policies (FIFO vs. LIFO, capex vs. opex for software, different depreciation lives) and the quantified impact that makes [Company] look healthier on a relative basis. Show which company’s apparent superiority is solely an artifact of aggressive accounting.

Capital allocation pattern recognition: Over the last 5 years, map each company’s use of cash flow (capex, R&D, M&A, buybacks, dividends). Highlight value-destroying M&A at peak multiples, buybacks executed at inflated prices, and chronic underinvestment in the business masquerading as capital discipline. Note any peer that is quietly gaining ground through smarter allocation.

Efficiency frontier contradictions: If [Company] appears to violate the growth–profitability trade-off, treat it as a red flag. Deconstruct with evidence whether the outlier is a mirage of aggressive accounting, unsustainable margins, or cyclical peak earnings — rather than a durable competitive advantage.

4. FORWARD-LOOKING SIGNALS & ASYMMETRY IDENTIFICATION
Project 12–24 months ahead, giving heavier weight to downside scenarios and catalysts that could break the thesis.

Earnings revision & consensus trends: Analyze the provided Analyst Consensus & Estimates tables. Compare forward estimates to historical growth rates — where are expectations overly optimistic given macro headwinds and qualitative signals? A pattern of negative revisions just beginning is a ⛈️.

Bear & Bull Base Rates: Assign probabilities to non-consensus outcomes, with bear cases receiving higher weight based on historical analogs and current setup. Develop the bear case in depth: what specific triggers could cause a 30%+ decline? The distribution of outcomes is likely fat-tailed to the downside.

Balance-sheet optionality & vulnerability: Focus on latent vulnerabilities — contingent exposures, off-balance-sheet risks, guarantees, variable-interest entities, and underfunded obligations that could crystallize under stress. Any hidden assets are unlikely to be monetized at favorable prices in a downturn. Treat a supposedly “underlevered” balance sheet as potential cover for future value-destroying acquisitions.

Red flag that would break the thesis: What single data point would confirm that the bear case is playing out and further downside is imminent? Also identify what would invalidate the bear case — but maintain that the latter bar is high.

Analyst Consensus vs. Reality: Compare target prices and recent ratings to your findings. The street is most likely anchored to stale, overoptimistic assumptions. Point out where consensus misses accumulating risks and is vulnerable to sharp downward revisions. If, against the odds, consensus is excessively pessimistic, note it — but such instances are rare.

5. SYNTHESIS: THE MOST IMPORTANT CONCLUSIONS
Deliver a concise, risk-centered conclusion:

The single most overappreciated or fragile number in [Company]'s story — whether the market is overestimating margins, growth durability, or cash flow — and why it will likely revert downward.

The one qualitative factor (cultural, regulatory, competitive) that quant models cannot capture and that threatens the investment case.

The most dangerous consensus belief — usually a bullish narrative built on extrapolated trends — and the evidence that challenges it.

Relative value assessment: Evaluate whether a genuine mispricing exists that makes [Company] overvalued relative to its peers. If evidence supports such a mispricing, construct a pair trade with [Company] as the short leg (or, in the exceptional case that it is demonstrably undervalued, as the long leg). If no compelling mispricing exists, state that explicitly. Do not construct a trade idea merely to fill this section.

6. SYSTEMIC CONTRADICTIONS & ABSTRACTION LENS
Task: Analyze the provided information through a systems-thinking lens to extract non-obvious patterns, systemic contradictions, and counterintuitive insights that challenge the superficial narrative. Given the bearish analytical stance, pay particular attention to feedback loops that could accelerate deterioration, hidden vulnerabilities, and paradoxes where apparent strength masks underlying decay.

Approach: Look for divergences (variables moving in opposite directions), contrast the headline story with underlying structural mechanics, and identify feedback loops or paradoxes. Also look for underappreciated coherences — where multiple data points quietly reinforce a bearish thesis that the market hasn't fully priced. Focus on insights not already captured by the earlier sections.

Output Formatting Requirements (For this section):

Present the findings as numbered "Insights."

Give each insight a bold, descriptive headline summarizing the core strategic takeaway.

Back up every claim with specific data points, quotes, or logical proofs directly extracted from the provided source material.

Conclude this section with a concise "Summary of Hidden Patterns" markdown table mapping the specific observation to its broader strategic meaning.

7. ADDITIONAL ANALYSIS: AI'S FREE-CHOICE INSIGHT
If — after completing all prior sections — you have identified an additional insight that is not already covered above, present it here. This should be a genuinely material observation, not a forced novelty. You have complete freedom in format and label (give this section a descriptive title that fits the insight). This could be:

A wildcard risk or opportunity that no consensus model captures.

A hidden operational or cultural link that explains performance — or underperformance — better than financials.

A narrative that connects seemingly unrelated data points into an investable thesis, whether long or short.

A description of an unusual pattern you've noticed (without needing to reference any specific dataset names).
Maintain clarity and bold any key revelations, but beyond that, the structure is yours. If no genuinely non-obvious insight emerges from the data, state that plainly. Do not fabricate novelty or force a contrarian take for its own sake.