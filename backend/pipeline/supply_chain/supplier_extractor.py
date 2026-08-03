"""
P2-3: Relationship Extraction Engine

Takes text from multiple sources (EDGAR 10-K supply chain paragraphs,
Form SD conflict minerals, ImportYeti BoL data, news articles) and uses
an LLM to extract structured Supplier → Component/Service → Company
relationship triples.

Outputs JSON arrays of relationship objects for downstream scoring.
"""

import json
import re
from typing import Optional
from openai import AsyncOpenAI
from ..rate_limiter import async_retry

# ──────────────────────────────────────────────
#  Extraction Prompt Template
# ──────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a supply chain intelligence analyst. Your task is to extract structured supplier-relationship data from unstructured text.

For each supplier relationship you find, output a JSON object with these exact fields:
- "supplier": The supplier company name (string)
- "component": What they supply — component, raw material, service, or product (string)
- "relationship_type": One of: "direct_supplier", "strategic_partner", "raw_material_source", "contract_manufacturer", "logistics_provider", "technology_provider", "distributor", "joint_venture"
- "confidence_hint": Your confidence in this extraction: "high", "medium", or "low" (based on explicitness of the text)
- "evidence": A SHORT quote or paraphrase from the source text supporting this relationship

Rules:
1. Only extract relationships where a supplier/vendor/partner is explicitly linked to the target company.
2. If the text only mentions industry-level supply chain dynamics without naming specific companies, skip it.
3. Output ONLY a JSON array. No markdown, no explanation, no backticks.
4. If no relationships can be confidently extracted, output an empty array: []

Example output:
[{"supplier": "Taiwan Semiconductor", "component": "advanced-node semiconductor wafers", "relationship_type": "direct_supplier", "confidence_hint": "high", "evidence": "We source our A-series chips from TSMC under a multi-year supply agreement."}]"""


def _clean_llm_json(text: str) -> str:
    """Strip markdown fences and extract raw JSON array from LLM response."""
    text = text.strip()
    # Remove markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    # Find the JSON array boundaries
    start = text.find('[')
    end = text.rfind(']')
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


class SupplierExtractor:
    """LLM-powered supplier relationship extraction from unstructured text."""

    def __init__(self, llm_api_key: str, base_url: str = "https://api.deepseek.com",
                 model: str = "deepseek-chat"):
        self._client = AsyncOpenAI(api_key=llm_api_key, base_url=base_url)
        self._model = model

    async def extract_from_sources(
        self,
        edgar_supply_chain: str = "",
        form_sd_text: str = "",
        import_yeti_suppliers: list = None,
        news_articles: list = None,
    ) -> list:
        """
        Extract supplier relationships from all available text sources.

        Args:
            edgar_supply_chain: Text from 10-K Item 1/1A supply chain paragraphs.
            form_sd_text: Text from Form SD conflict minerals disclosure.
            import_yeti_suppliers: List of supplier dicts from ImportYeti collector.
            news_articles: List of news article dicts with 'title' and 'summary'.

        Returns:
            List of relationship dicts with supplier/component/type/evidence fields.
        """
        # Build a combined text block from all sources
        source_blocks = []
        source_annotations = {}

        if edgar_supply_chain:
            source_blocks.append(f"=== SOURCE: SEC 10-K Supply Chain Disclosure ===\n{edgar_supply_chain[:8000]}")
            source_annotations["SEC 10-K"] = "sec_filing"

        if form_sd_text:
            source_blocks.append(f"=== SOURCE: SEC Form SD (Conflict Minerals) ===\n{form_sd_text[:4000]}")
            source_annotations["SEC Form SD"] = "sec_filing"

        if import_yeti_suppliers:
            yeti_text = json.dumps(import_yeti_suppliers, indent=2)
            source_blocks.append(f"=== SOURCE: ImportYeti Bill of Lading Data ===\n{yeti_text[:4000]}")
            source_annotations["ImportYeti"] = "customs"

        if news_articles:
            news_lines = []
            for a in (news_articles or [])[:5]:
                title = a.get("title", "")
                summary = a.get("summary", "") or a.get("text", "") or ""
                if title:
                    news_lines.append(f"- TITLE: {title}")
                    if summary:
                        news_lines.append(f"  SUMMARY: {summary[:300]}")
            if news_lines:
                source_blocks.append(f"=== SOURCE: Recent News Articles ===\n" + "\n".join(news_lines))
                source_annotations["News"] = "news"

        if not source_blocks:
            return []

        combined_text = "\n\n".join(source_blocks)

        # Call LLM for extraction (with retry/backoff)
        try:
            relationships = await self._call_llm_extraction(combined_text)
        except Exception as e:
            print(f"[SupplierExtractor] LLM extraction error: {e}")
            return []

        # Annotate each relationship with source type based on evidence
        for rel in relationships:
            evidence = rel.get("evidence", "")
            source_type = "unknown"
            for src_name, src_type in source_annotations.items():
                if src_name.lower() in combined_text.lower():
                    src_idx = combined_text.lower().find(src_name.lower())
                    ev_idx = combined_text.lower().find(evidence[:50].lower()) if evidence else -1
                    if src_idx >= 0 and ev_idx >= 0:
                        source_type = src_type
                        break
            rel["source_type"] = source_type

        return relationships

    @async_retry(max_retries=3, base_delay=1.0)
    async def _call_llm_extraction(self, combined_text: str) -> list:
        """Call the LLM for supplier relationship extraction.
        
        Separated to allow @async_retry to catch and retry on API failures."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract all supplier relationships from the following sources:\n\n{combined_text}"},
            ],
            max_tokens=2000,
            temperature=0.1,
        )

        raw_output = response.choices[0].message.content or "[]"
        cleaned = _clean_llm_json(raw_output)

        relationships = json.loads(cleaned)
        if not isinstance(relationships, list):
            return []
        return relationships
