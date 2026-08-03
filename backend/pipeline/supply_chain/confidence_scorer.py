"""
P2-4: Confidence Scoring Engine

Implements the three-variable scoring formula for supplier relationships:

    Score = SourceWeight × FrequencyBoost × TimeDecay

Where:
- SourceWeight: Based on data provenance (SEC=1.0, Customs=1.0, PressRelease=0.7, News=0.4, Rumor=0.2)
- FrequencyBoost: max(1.0, 1.0 + 0.3 × (unique_sources - 1)) — bonus for multi-source corroboration
- TimeDecay: max(0.3, 1.0 - 0.15 × years_since_data) — recent data weighted higher; floor at 0.3

Also provides entity deduplication via fuzzy name matching.
"""

import datetime
import re
from difflib import SequenceMatcher
from typing import Optional


# ──────────────────────────────────────────────
#  Source Weight Configuration
# ──────────────────────────────────────────────

SOURCE_WEIGHTS = {
    "sec_filing": 1.0,
    "customs": 1.0,
    "press_release": 0.7,
    "news": 0.4,
    "rumor": 0.2,
    "unknown": 0.3,
}

# Map supplier_extractor source_type values to canonical source weights
SOURCE_TYPE_MAP = {
    "sec_filing": "sec_filing",
    "customs": "customs",
    "press_release": "press_release",
    "news": "news",
    "rumor": "rumor",
}


def _normalize_name(name: str) -> str:
    """Normalize a company/supplier name for fuzzy comparison."""
    name = name.lower().strip()
    # Remove common suffixes
    for suffix in [" inc", " ltd", " llc", " corp", " co.", " co", " limited",
                   " corporation", " group", " plc", " s.a.", " s.a", " ag",
                   " gmbh", " srl", " spa", " nv", " bv"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    # Remove punctuation and extra whitespace
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def fuzzy_match(name1: str, name2: str, threshold: float = 0.75) -> bool:
    """Check if two supplier names likely refer to the same entity."""
    norm1 = _normalize_name(name1)
    norm2 = _normalize_name(name2)
    if norm1 == norm2:
        return True
    # Check if one contains the other
    if norm1 in norm2 or norm2 in norm1:
        return True
    return SequenceMatcher(None, norm1, norm2).ratio() >= threshold


def compute_source_weight(source_type: str) -> float:
    """Get the source weight for a given source type string."""
    canonical = SOURCE_TYPE_MAP.get(source_type, source_type)
    return SOURCE_WEIGHTS.get(canonical, SOURCE_WEIGHTS["unknown"])


def compute_frequency_boost(unique_sources: int) -> float:
    """Multi-source corroboration bonus.

    Formula: max(1.0, 1.0 + 0.3 × (unique_sources - 1))
    A relationship confirmed by 2 sources gets 1.3x, 3 sources gets 1.6x, etc.
    """
    if unique_sources < 2:
        return 1.0
    return max(1.0, 1.0 + 0.3 * (unique_sources - 1))


def compute_time_decay(data_date: Optional[str] = None,
                       reference_date: Optional[str] = None) -> float:
    """Compute recency decay factor.

    Formula: max(0.3, 1.0 - 0.15 × years_since_data)
    2026 data = 1.0, 2022 data = ~0.4, older than ~4.7 years = floor at 0.3

    Args:
        data_date: ISO date string (YYYY-MM-DD) or year string (YYYY).
        reference_date: Reference date, defaults to today.
    """
    if not data_date:
        return 1.0  # No date = assume current

    # Parse the data date
    try:
        # Try full date
        if "-" in data_date:
            data_dt = datetime.datetime.strptime(data_date[:10], "%Y-%m-%d")
        else:
            # Just a year
            data_dt = datetime.datetime(int(data_date), 1, 1)
    except (ValueError, TypeError):
        return 1.0

    ref_dt = datetime.datetime.now()
    if reference_date:
        try:
            ref_dt = datetime.datetime.strptime(reference_date[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    years = max(0, (ref_dt - data_dt).days / 365.25)
    decay = 1.0 - 0.15 * years
    return max(0.3, decay)


def deduplicate_relationships(relationships: list) -> list:
    """Merge relationships that refer to the same supplier.

    When multiple entries share the same supplier name (fuzzy match),
    they are merged, with component info concatenated and source count increased.
    """
    if not relationships:
        return []

    merged = []
    used = set()

    for i, rel in enumerate(relationships):
        if i in used:
            continue

        supplier = rel.get("supplier", "")
        if not supplier:
            continue

        # Find all matches for this supplier
        matches = [rel]
        match_indices = {i}
        for j, other in enumerate(relationships):
            if j <= i or j in used:
                continue
            other_supplier = other.get("supplier", "")
            if fuzzy_match(supplier, other_supplier):
                matches.append(other)
                match_indices.add(j)

        used.update(match_indices)

        if len(matches) == 1:
            merged.append(rel)
        else:
            # Merge: use the name from the highest-confidence match
            best = max(matches, key=lambda r: r.get("confidence_hint", "low") == "high")
            components = list(set(
                r.get("component", "") for r in matches if r.get("component")
            ))
            sources = list(set(
                r.get("source_type", "unknown") for r in matches
            ))
            merged.append({
                "supplier": best.get("supplier", supplier),
                "component": "; ".join(components) if components else best.get("component", ""),
                "relationship_type": best.get("relationship_type", "direct_supplier"),
                "confidence_hint": best.get("confidence_hint", "medium"),
                "evidence": best.get("evidence", ""),
                "source_type": best.get("source_type", "unknown"),
                "_merged_from": len(matches),
                "_all_sources": sources,
            })

    return merged


def score_relationships(
    relationships: list,
    filing_date: Optional[str] = None,
) -> list:
    """Apply the full confidence scoring formula to a list of relationships.

    Args:
        relationships: List of relationship dicts with at least 'source_type'.
        filing_date: Date of the primary source (e.g., 10-K filing date) for time decay.

    Returns:
        The same list with 'confidence_score' and score breakdown fields added,
        sorted by score descending.
    """
    # First deduplicate
    deduped = deduplicate_relationships(relationships)

    scored = []
    for rel in deduped:
        source_type = rel.get("source_type", "unknown")
        merged_from = rel.get("_merged_from", 1)
        all_sources = rel.get("_all_sources", [source_type])

        # Source weight: use the best source weight among merged entries
        source_weights = [compute_source_weight(s) for s in all_sources]
        source_weight = max(source_weights) if source_weights else compute_source_weight(source_type)

        # Frequency boost based on unique sources that confirmed this relationship
        unique_sources = len(set(all_sources))
        frequency_boost = compute_frequency_boost(max(unique_sources, merged_from))

        # Time decay based on filing date
        time_decay = compute_time_decay(filing_date)

        # Final score
        score = source_weight * frequency_boost * time_decay

        rel["confidence_score"] = round(score, 3)
        rel["score_breakdown"] = {
            "source_weight": source_weight,
            "frequency_boost": round(frequency_boost, 3),
            "time_decay": round(time_decay, 3),
            "unique_sources": unique_sources,
        }

        scored.append(rel)

    # Sort by confidence score descending
    scored.sort(key=lambda r: r.get("confidence_score", 0), reverse=True)
    return scored
