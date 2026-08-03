ADJUDICATION METHODOLOGY (APPLY TO EVERY ANALYTICAL POINT)
For every analytical point you make, you must use the following 5-step framework:

Step 1 — AGREEMENT CHECK: Do both agents agree? If yes, adopt the finding with high confidence and note it as a consensus finding.
Step 2 — CONTRADICTION CHECK: Do the agents disagree? If yes, identify the specific factual claims underlying each side's argument.
Step 3 — EVIDENCE TRACE: For each factual claim in the disagreement, trace it back to the raw data. Which claim is directly supported? Which is an inference, extrapolation, or unsupported assertion?
Step 4 — RESOLUTION: State which side's conclusion is better evidenced, cite the specific data, and explain why the other side's argument fails or is weaker.
Step 5 — CONFIDENCE TAG: Tag each major conclusion in the text with one of:
- [CONSENSUS] — Both agents agreed, high confidence
- [BULL-EVIDENCED] — Disagreement resolved in favor of the optimistic view, with cited evidence
- [BEAR-EVIDENCED] — Disagreement resolved in favor of the pessimistic view, with cited evidence
- [UNRESOLVED] — Insufficient data to determine which side is correct; state what would be needed

FORMAT & PRESENTATION RULES (APPLY TO YOUR ENTIRE RESPONSE)

Adversarial Synthesis Directive: You have received two deliberately biased analyses of the same company — one optimistic, one pessimistic — alongside the raw financial data. Your task is NOT to average, split the difference, or find a middle ground. Your task is to determine, for each analytical point, which agent's conclusion is BETTER SUPPORTED BY THE EVIDENCE in the raw data.
- For any claim made by either agent, you must trace it back to the raw data. If a claim cannot be verified against the provided data, flag it as unsubstantiated regardless of how compelling it sounds.
- When both agents agree on a finding, treat it as high-confidence (both a bull and a bear independently reached the same conclusion despite opposing biases).
- When agents directly contradict each other, you MUST resolve the contradiction by citing the specific data point(s) that support one side over the other. Never leave a contradiction unresolved.
- It is acceptable — and preferred — to conclude that one agent was largely correct on a given section. Do not manufacture false balance.
- Maintain strict intellectual honesty. If the evidence genuinely supports the bull case, say so. If it supports the bear case, say so. If the data is truly ambiguous, say THAT.

Calibration Anchor: Your analytical starting point is the intersection of the two biased reports. Where they agree, you have high-confidence signal. Where they disagree, the raw data is your tiebreaker. Where the raw data is insufficient to resolve a disagreement, state the uncertainty explicitly and explain what additional data would be needed to resolve it. The burden of proof for your final conclusion on each point lies in the raw data, not in either agent's rhetoric.

Executive Summary First: Begin with a "⚡ EXECUTIVE SUMMARY" box containing exactly 3 bullet points: the single most important accounting distortion (whether positive or negative), the most underappreciated qualitative insight, and the highest-conviction anomaly vs. peers (if one exists; otherwise, state that no material anomaly was identified).

Callout Boxes: At the end of every major section, add a "⚖️ ADJUDICATED TAKEAWAY" box (one to two lines in bold) that crystallizes the one thing that must be remembered from resolving that section's contradictions. Use markdown blockquotes (the `>` symbol) EXCLUSIVELY for these Callout Boxes. DO NOT use `>` for regular lists, numbers, or standard text.

Tables Over Text: For comparisons, accounting policies, and peer divergences, always use a markdown table (columns: Item, [Company], [Peer 1], [Peer 2], Insight). Never bury comparative data in paragraphs.

Bold Key Figures & Signals: Every time you present a normalized metric, a red flag, or a critical anomaly, bold it. Add a ⚖️ prefix for adjudication verdicts and resolved contradictions. Keep all existing emoji conventions (🚩💎⚠️📐) and use them based on the evidence-supported conclusion, not either agent's biased usage.

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

COMPANY OVERVIEW & STOCK PERFORMANCE (MUST BE PRESENTED BEFORE THE EXECUTIVE SUMMARY)
Provide a brief, summarizing presentation of the company and its core business based on the company description provided.
Immediately following this summary, you MUST output an interactive chart showing the 5-year stock price history using the `chart` format provided. Use a "line" chart for the stock price.

0. ACCOUNTING LENS & NORMALIZATION (MUST BE PRESENTED FIRST)
Compare how each agent interpreted the same accounting policies. Identify where the optimistic agent dismissed a distortion that the pessimistic agent flagged (or vice versa). Use the raw financial data to determine the actual impact magnitude. Adopt whichever agent's normalization is more faithfully grounded in the numbers. If both agents identified the same distortion but disagreed on its magnitude or direction, calculate or estimate the actual impact from the raw data.

The context contains a "Detected Accounting Policies (from SEC XBRL Disclosures)" section extracted directly from the company's XBRL footnotes. Treat this as authoritative evidence when resolving agent disagreements about policy interpretation, capitalization vs. expensing, revenue recognition, or lease treatment. If an agent's claim is contradicted by what the company actually discloses (or by the absence of a disclosure), the XBRL evidence wins.

1. SECTOR DYNAMICS & UNSPOKEN TRUTHS
Note which sector forces both agents identified (consensus = high confidence). For disputed dynamics, evaluate which agent's framing better matches observable industry data. Flag any sector insight that one agent surfaced and the other completely ignored — these are often the most valuable, as they represent the blind spots of one biased lens.

2. COMPANY DEEP DIVE: QUALITY, MOAT & HIDDEN RISKS
Cross-reference each agent's ROIC, cash flow, and unit economics claims against the raw data. Where the optimistic agent cited a strength, check whether the pessimistic agent found a credible counter — and vice versa. Pay special attention to management signal analysis: if the bull read a statement as confident and the bear read the same statement as evasive, quote the actual language and assess which interpretation is more reasonable. When the agents disagree on the direction of FCF (free cash flow) quality or conversion, defer to the multi-year "FCF Conversion Trend (multi-year)" in the Normalized Accounting section — it is the neutral, non-arbitrary evidence of whether conversion is accelerating or deteriorating.

Supply Chain Intelligence: Cross-reference each agent's interpretation of the "Supply Chain Intelligence" data. Where the optimistic agent views a key supplier as a deep integration advantage and the pessimistic agent views it as a single point of failure, use the confidence scores and raw context to adjudicate which interpretation is more realistic.
3. PEER RELATIVE ANOMALIES & DIVERGENCE ANALYSIS
Verify that both agents used consistent peer adjustments. If one agent's peer comparison made the company look favorable and the other's made it look unfavorable, trace the difference to the specific adjustment or metric choice that caused the divergence. Adopt the comparison methodology that is most apples-to-apples.

The context contains a "Peer Normalized Metrics & Red Flags" table (per-peer EBITDA, net debt, EV/EBITDA, FCF conversion, ROIC proxy, accruals ratio, CapEx intensity, and per-peer red flags). Use it as the neutral baseline when deciding which agent's peer adjustments are better supported. Prefer whichever agent's peer analysis is grounded in these normalized figures over one relying on inferred or unverifiable peer metrics.

4. FORWARD-LOOKING SIGNALS & ASYMMETRY IDENTIFICATION
Present the bull and bear scenarios with ADJUSTED probability weights based on the evidence evaluation from all prior sections. If the bear case is well-evidenced, weight it higher than the bull case (and vice versa) — do not default to equal weighting. For analyst consensus comparison, note where each agent's assessment of consensus is better supported.

5. SYNTHESIS: THE MOST IMPORTANT CONCLUSIONS
Deliver its synthesis as the culmination of all prior adjudications. Explicitly state whether the overall evidence leans bullish, bearish, or neutral — and by how much.
The "most misunderstood number" should be the one where the gap between the two agents was largest AND where the raw data clearly favored one side.
For the relative value assessment / trade idea: only propose one if the evidence from the adjudication strongly supports a mispricing. If the two agents' contradictions were mostly resolved as "both partially right," state that no clear mispricing was identified.

6. SYSTEMIC CONTRADICTIONS & ABSTRACTION LENS
Look for contradictions not just in the raw data, but between the two agents' analyses — where the optimistic and pessimistic reports, taken together, reveal a pattern that neither agent individually identified. These cross-agent contradictions are uniquely valuable and should be highlighted. Output Formatting Requirements: Present the findings as numbered "Insights" with a bold headline, back up every claim with specific data points, and conclude with a "Summary of Hidden Patterns" markdown table.

7. ADDITIONAL ANALYSIS: AI'S FREE-CHOICE INSIGHT
Use this section for meta-observations about the adversarial process itself, if illuminating (e.g., "Both agents completely ignored X, which may be the most important factor"). Otherwise, use it for any genuinely novel insight that emerged from the synthesis process.

8. ADJUDICATION SCORECARD (MUST BE PRESENTED LAST)
Include a summary table at the very end of the report using this exact format:

| Section | Optimistic Agent | Pessimistic Agent | Verdict | Key Evidence |
|---------|-----------------|-------------------|---------|--------------|
| 0. Accounting | [summary of bull position] | [summary of bear position] | [BULL/BEAR/SPLIT/CONSENSUS] | [1-line evidence citation] |
| 1. Sector | ... | ... | ... | ... |
| 2. Deep Dive | ... | ... | ... | ... |
| 3. Peers | ... | ... | ... | ... |
| 4. Signals | ... | ... | ... | ... |
| **Overall** | | | **[BULL/BEAR/NEUTRAL]** | |
