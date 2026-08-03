"""
P2-5: Supply Chain Module Unit Tests

Tests the confidence scoring engine, deduplication, time decay,
and fuzzy matching logic without requiring network access.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta

# Ensure we can import from backend.pipeline.supply_chain
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.supply_chain.confidence_scorer import (
    compute_source_weight,
    compute_frequency_boost,
    compute_time_decay,
    fuzzy_match,
    deduplicate_relationships,
    score_relationships,
    SOURCE_WEIGHTS,
)


# ──────────────────────────────────────────────
#  Source Weight Tests
# ──────────────────────────────────────────────

def test_source_weight_sec_filing():
    assert compute_source_weight("sec_filing") == 1.0


def test_source_weight_customs():
    assert compute_source_weight("customs") == 1.0


def test_source_weight_press_release():
    assert compute_source_weight("press_release") == 0.7


def test_source_weight_news():
    assert compute_source_weight("news") == 0.4


def test_source_weight_rumor():
    assert compute_source_weight("rumor") == 0.2


def test_source_weight_unknown_defaults_to_0_3():
    assert compute_source_weight("unknown") == 0.3
    assert compute_source_weight("nonexistent_type") == 0.3


# ──────────────────────────────────────────────
#  Frequency Boost Tests
# ──────────────────────────────────────────────

def test_frequency_boost_single_source():
    assert compute_frequency_boost(1) == 1.0


def test_frequency_boost_two_sources():
    assert compute_frequency_boost(2) == pytest.approx(1.3)


def test_frequency_boost_three_sources():
    assert compute_frequency_boost(3) == pytest.approx(1.6)


def test_frequency_boost_four_sources():
    assert compute_frequency_boost(4) == pytest.approx(1.9)


def test_frequency_boost_zero_sources():
    assert compute_frequency_boost(0) == 1.0


# ──────────────────────────────────────────────
#  Time Decay Tests
# ──────────────────────────────────────────────

def test_time_decay_current_date_is_1():
    """Data from today should have no decay."""
    today = datetime.now().strftime("%Y-%m-%d")
    assert compute_time_decay(today) == pytest.approx(1.0, abs=0.01)


def test_time_decay_one_year_ago():
    """~1 year ago should be ~0.85."""
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    decay = compute_time_decay(one_year_ago)
    assert 0.8 <= decay <= 0.9


def test_time_decay_five_years_ago_hits_floor():
    """5+ years ago should hit the 0.3 floor."""
    five_years_ago = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    assert compute_time_decay(five_years_ago) == pytest.approx(0.3, abs=0.05)


def test_time_decay_floor_never_below_0_3():
    """Very old data should never go below 0.3."""
    very_old = "2000-01-01"
    decay = compute_time_decay(very_old)
    assert decay >= 0.3


def test_time_decay_none_date_returns_1():
    assert compute_time_decay(None) == 1.0


def test_time_decay_year_only_string():
    """Year-only strings should be parsed correctly (Jan 1 of that year)."""
    current_year = datetime.now().year
    # "2025" means Jan 1, 2025 — ~1.6 years ago from Aug 2026
    # decay = max(0.3, 1 - 0.15 * years) ≈ max(0.3, 0.76)
    decay = compute_time_decay(str(current_year - 1))
    assert 0.7 <= decay <= 0.85


# ──────────────────────────────────────────────
#  Fuzzy Match Tests
# ──────────────────────────────────────────────

def test_fuzzy_match_identical():
    assert fuzzy_match("Apple Inc", "Apple Inc") is True


def test_fuzzy_match_suffix_variation():
    assert fuzzy_match("Apple Inc", "Apple Incorporated") is True
    assert fuzzy_match("Microsoft Corp", "Microsoft Corporation") is True


def test_fuzzy_match_case_insensitive():
    assert fuzzy_match("APPLE INC", "apple inc") is True


def test_fuzzy_match_typo_not_matched():
    """Significantly different company names should not fuzzy-match."""
    assert fuzzy_match("Apple Inc", "Exxon Mobil Corporation") is False


def test_fuzzy_match_subname_contained():
    """If one name contains the other, it should match."""
    assert fuzzy_match("Taiwan Semiconductor Manufacturing Company Ltd", "Taiwan Semiconductor") is True


def test_fuzzy_match_different_companies():
    assert fuzzy_match("Apple Inc", "Microsoft Corp") is False


# ──────────────────────────────────────────────
#  Deduplication Tests
# ──────────────────────────────────────────────

def test_deduplicate_empty_list():
    assert deduplicate_relationships([]) == []


def test_deduplicate_single_relationship():
    rels = [{"supplier": "TSMC", "component": "chips", "source_type": "sec_filing", "confidence_hint": "high"}]
    result = deduplicate_relationships(rels)
    assert len(result) == 1
    assert result[0]["supplier"] == "TSMC"


def test_deduplicate_merges_same_supplier():
    rels = [
        {"supplier": "TSMC", "component": "chips", "source_type": "sec_filing", "confidence_hint": "high", "evidence": "source1"},
        {"supplier": "TSMC", "component": "wafers", "source_type": "customs", "confidence_hint": "medium", "evidence": "source2"},
    ]
    result = deduplicate_relationships(rels)
    assert len(result) == 1
    assert "chips" in result[0]["component"]
    assert "wafers" in result[0]["component"]
    assert result[0]["_merged_from"] == 2
    assert "sec_filing" in result[0]["_all_sources"]
    assert "customs" in result[0]["_all_sources"]


def test_deduplicate_keeps_distinct_suppliers():
    rels = [
        {"supplier": "TSMC", "component": "chips", "source_type": "sec_filing", "confidence_hint": "high"},
        {"supplier": "Samsung Electronics", "component": "displays", "source_type": "news", "confidence_hint": "medium"},
        {"supplier": "Foxconn", "component": "assembly", "source_type": "customs", "confidence_hint": "high"},
    ]
    result = deduplicate_relationships(rels)
    assert len(result) == 3


# ──────────────────────────────────────────────
#  Full Scoring Tests
# ──────────────────────────────────────────────

def test_score_relationships_empty():
    assert score_relationships([]) == []


def test_score_relationships_includes_score_fields():
    rels = [
        {"supplier": "TSMC", "component": "chips", "source_type": "sec_filing", "confidence_hint": "high", "evidence": "test"},
    ]
    scored = score_relationships(rels, filing_date=datetime.now().strftime("%Y-%m-%d"))
    assert len(scored) == 1
    assert "confidence_score" in scored[0]
    assert "score_breakdown" in scored[0]
    breakdown = scored[0]["score_breakdown"]
    assert "source_weight" in breakdown
    assert "frequency_boost" in breakdown
    assert "time_decay" in breakdown


def test_score_relationships_sorted_descending():
    rels = [
        {"supplier": "Low confidence supplier", "component": "x", "source_type": "rumor", "confidence_hint": "low"},
        {"supplier": "High confidence supplier", "component": "y", "source_type": "sec_filing", "confidence_hint": "high"},
    ]
    scored = score_relationships(rels)
    assert scored[0]["confidence_score"] >= scored[-1]["confidence_score"]
    assert scored[0]["supplier"] == "High confidence supplier"


def test_score_multisource_gets_boost():
    """A relationship confirmed by both SEC and customs should score higher than SEC alone."""
    today = datetime.now().strftime("%Y-%m-%d")
    single_source = [
        {"supplier": "TSMC", "component": "chips", "source_type": "sec_filing", "confidence_hint": "high"},
    ]
    multi_source = [
        {"supplier": "TSMC", "component": "chips", "source_type": "sec_filing", "confidence_hint": "high"},
        {"supplier": "TSMC", "component": "wafers", "source_type": "customs", "confidence_hint": "medium"},
    ]
    single_scored = score_relationships(single_source, filing_date=today)
    multi_scored = score_relationships(multi_source, filing_date=today)
    assert multi_scored[0]["confidence_score"] > single_scored[0]["confidence_score"]


# ──────────────────────────────────────────────
#  Edge Cases
# ──────────────────────────────────────────────

def test_score_relationships_handles_missing_source_type():
    rels = [{"supplier": "Test Corp", "component": "stuff"}]
    scored = score_relationships(rels)
    assert len(scored) == 1
    assert "confidence_score" in scored[0]
    assert scored[0]["confidence_score"] > 0


def test_deduplicate_handles_empty_supplier_name():
    rels = [
        {"supplier": "", "component": "x", "source_type": "news"},
        {"supplier": "Valid Corp", "component": "y", "source_type": "sec_filing"},
    ]
    result = deduplicate_relationships(rels)
    # Empty supplier should be skipped or kept separately
    assert any(r["supplier"] == "Valid Corp" for r in result)
