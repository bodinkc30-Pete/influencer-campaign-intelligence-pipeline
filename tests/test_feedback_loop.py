import copy

import pytest

from src.feedback_loop import (
    build_campaign_result_template,
    build_human_review_queue,
    evaluate_observational_feedback,
    feedback_readiness,
    validate_campaign_result_rows,
    validate_human_review_rows,
)


def shortlist_row(i: int, rank: int | None = None):
    rank = rank or i
    return {
        "scenario_id": "demo",
        "config_version": "matching-v1",
        "influencer_id": f"inf_{i}",
        "canonical_handle": f"creator_{i}",
        "rank": rank,
        "total_score": 90 - i,
        "positive_reasons": "evidence",
        "cautions": "",
    }


def completed_review(rows):
    out = copy.deepcopy(rows)
    decisions = ["selected", "selected", "rejected"]
    for row, decision in zip(out, decisions):
        row["human_decision"] = decision
        row["human_decision_reason"] = "business review"
        row["reviewer"] = "reviewer"
        row["reviewed_at"] = "2026-08-21"
        row["decision_status"] = "completed"
    return out


def completed_results(review_rows):
    rows = build_campaign_result_template(review_rows)
    for row in rows:
        if row["human_decision"] == "selected":
            row["execution_status"] = "completed"
            row["result_observed_at"] = "2026-09-30"
            row["business_success"] = "yes" if row["rank"] == 1 else "no"
            row["content_posted"] = "yes"
    return rows


def test_review_queue_preserves_rank_and_starts_pending():
    rows = build_human_review_queue([shortlist_row(1), shortlist_row(2)])
    assert [row["rank"] for row in rows] == [1, 2]
    assert all(row["human_decision"] == "" for row in rows)
    assert rows[0]["review_priority"] == "primary_review"


def test_review_queue_rejects_duplicate_influencer():
    with pytest.raises(ValueError):
        build_human_review_queue([shortlist_row(1), shortlist_row(1, rank=2)])


def test_review_validation_requires_reason_reviewer_and_date_after_decision():
    rows = build_human_review_queue([shortlist_row(1)])
    rows[0]["human_decision"] = "selected"
    errors = validate_human_review_rows(rows)
    assert any("human_decision_reason" in error for error in errors)
    assert any("reviewer" in error for error in errors)
    assert any("reviewed_at" in error for error in errors)


def test_review_validation_can_require_all_decisions():
    rows = build_human_review_queue([shortlist_row(1)])
    errors = validate_human_review_rows(rows, require_complete=True)
    assert any("human_decision is required" in error for error in errors)


def test_result_template_waits_for_human_decision():
    review = build_human_review_queue([shortlist_row(1)])
    result = build_campaign_result_template(review)[0]
    assert result["feedback_status"] == "waiting_for_human_decision"


def test_result_template_waits_for_campaign_result_after_selection():
    review = completed_review(build_human_review_queue([shortlist_row(1), shortlist_row(2), shortlist_row(3)]))
    results = build_campaign_result_template(review)
    selected = next(row for row in results if row["influencer_id"] == "inf_1")
    rejected = next(row for row in results if row["influencer_id"] == "inf_3")
    assert selected["feedback_status"] == "waiting_for_campaign_result"
    assert rejected["feedback_status"] == "not_applicable_until_selected"


def test_result_validation_rejects_evidence_for_non_selected_candidate():
    rows = [{
        "influencer_id": "inf_2",
        "human_decision": "rejected",
        "execution_status": "completed",
        "result_observed_at": "2026-09-30",
        "business_success": "yes",
        "content_posted": "yes",
    }]
    errors = validate_campaign_result_rows(rows, selected_influencer_ids={"inf_1"})
    assert any("non-selected" in error for error in errors)


def test_readiness_is_false_when_human_decisions_are_pending():
    review = build_human_review_queue([shortlist_row(1)])
    results = build_campaign_result_template(review)
    status = feedback_readiness(review, results, success_definition_present=True)
    assert not status.evaluation_ready
    assert status.pending_decisions == 1


def test_readiness_is_false_without_success_definition():
    review = completed_review(build_human_review_queue([shortlist_row(1), shortlist_row(2), shortlist_row(3)]))
    results = completed_results(review)
    status = feedback_readiness(review, results, success_definition_present=False)
    assert not status.evaluation_ready


def test_completed_selected_results_validate():
    review = completed_review(build_human_review_queue([shortlist_row(1), shortlist_row(2), shortlist_row(3)]))
    results = completed_results(review)
    selected = {row["influencer_id"] for row in review if row["human_decision"] == "selected"}
    assert validate_campaign_result_rows(results, selected_influencer_ids=selected, require_selected_results_complete=True) == []


def test_observational_evaluation_never_claims_counterfactual_accuracy():
    review = completed_review(build_human_review_queue([shortlist_row(1), shortlist_row(2), shortlist_row(3)]))
    results = completed_results(review)
    metrics = evaluate_observational_feedback(
        review,
        results,
        success_definition="Business owner marked campaign outcome success using the approved campaign objective.",
        top_k=2,
    )
    assert metrics["selected_rows"] == 2
    assert metrics["selected_business_success_rate"] == 0.5
    assert metrics["selected_within_top_k_rate"] == 1.0
    assert metrics["counterfactual_claim_allowed"] is False
    assert metrics["automatic_weight_calibration_applied"] is False
