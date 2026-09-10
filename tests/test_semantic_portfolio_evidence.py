import csv
import json
import re
from pathlib import Path

import pytest

from src.historical_features import FEATURE_CONTRACT
from src.matching_v2 import REQUIRED_WEIGHT_KEYS, load_v2_config


ROOT = Path(__file__).resolve().parents[1]
SEMANTIC = ROOT / "evidence" / "semantic"


def test_historical_feature_contract_has_unique_implemented_metrics():
    names = [row[0] for row in FEATURE_CONTRACT]
    assert len(names) == len(set(names))
    assert {
        "campaign_count",
        "brand_count",
        "selected_rate",
        "fee_observed_median",
        "views_median",
        "posted_rate",
        "campaign_history_dq_warn_count",
        "identity_confidence",
    }.issubset(names)


def test_matching_weight_contract_is_governed_and_complete():
    data = json.loads((ROOT / "config" / "matching_v2_config.example.json").read_text(encoding="utf-8"))
    config = load_v2_config(data)
    assert set(config.weights) == REQUIRED_WEIGHT_KEYS
    assert sum(config.weights.values()) == pytest.approx(1.0)


def test_entity_glossary_contains_required_business_entities():
    text = (SEMANTIC / "entity_glossary.md").read_text(encoding="utf-8")
    for term in (
        "Influencer",
        "Canonical Influencer",
        "Identity Alias",
        "Source Identity",
        "Campaign Participation",
        "Performance Observation",
        "Matching Candidate",
        "Human Decision",
    ):
        assert term in text


def test_synthetic_identity_example_keeps_ambiguous_identity_unpromoted():
    with (SEMANTIC / "synthetic_identity_resolution_example.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 4
    assert len({row["source_observation_id"] for row in rows}) == 4
    pending = next(row for row in rows if row["resolution_method"] == "manual_review_pending")
    assert pending["review_required"] == "true"
    assert pending["canonical_influencer_id"] == ""
    assert all(row["public_safety"] == "SYNTHETIC" for row in rows)


def test_matching_explanation_is_synthetic_traceable_and_leakage_guarded():
    data = json.loads((SEMANTIC / "matching_explanation_example.json").read_text(encoding="utf-8"))
    assert data["example_type"] == "SYNTHETIC_PUBLIC_SAFE_MATCHING_EXPLANATION"
    assert data["candidate"]["eligibility_status"] == "eligible"
    assert data["candidate"]["leakage_guard_status"] == "PASS"
    assert data["candidate"]["rank"] == 1
    assert data["candidate"]["total_score"] == pytest.approx(77.83333333333333)
    assert data["guardrails"]["target_campaign_evidence_used_in_score"] is False
    assert data["guardrails"]["machine_learning"] is False
    assert data["guardrails"]["fuzzy_identity_resolution"] is False
    assert data["guardrails"]["human_decision_required"] is True
    assert len(data["semantic_trace"]) == len(REQUIRED_WEIGHT_KEYS)


def test_semantic_artifacts_are_public_safe_and_document_boundaries():
    files = [p for p in SEMANTIC.rglob("*") if p.is_file()]
    assert files
    combined = "\n".join(p.read_text(encoding="utf-8") for p in files)
    assert not re.search(r"[A-Za-z]:[\\/](?:Users|home)[\\/][^\\/\s]+", combined, re.IGNORECASE)
    assert not re.search(r"\b0[689]\d{8}\b", combined)
    assert "Recency scoring is not implemented" in combined
    assert "human decision remains pending" in combined
