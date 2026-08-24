from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable


FEEDBACK_CONTRACT_VERSION = "feedback-v1"
ALLOWED_HUMAN_DECISIONS = {"selected", "rejected", "hold"}
ALLOWED_EXECUTION_STATUSES = {"planned", "in_progress", "completed", "cancelled"}
ALLOWED_TRI_STATE = {"yes", "no", "unknown"}


@dataclass(frozen=True)
class FeedbackReadiness:
    review_rows: int
    decided_rows: int
    selected_rows: int
    selected_results_complete: int
    pending_decisions: int
    pending_selected_results: int
    success_definition_present: bool
    evaluation_ready: bool


def _text(value: object | None) -> str:
    return str(value or "").strip()


def _float(value: object | None) -> float | None:
    text = _text(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _int(value: object | None) -> int | None:
    number = _float(value)
    return int(number) if number is not None else None


def build_human_review_queue(
    shortlist_rows: Iterable[dict[str, object]],
    *,
    primary_review_limit: int = 10,
) -> list[dict[str, object]]:
    if primary_review_limit <= 0:
        raise ValueError("primary_review_limit must be greater than zero")

    rows = [dict(row) for row in shortlist_rows]
    seen_ids: set[str] = set()
    result: list[dict[str, object]] = []
    for row in rows:
        influencer_id = _text(row.get("influencer_id"))
        rank = _int(row.get("rank"))
        if not influencer_id:
            raise ValueError("shortlist row is missing influencer_id")
        if influencer_id in seen_ids:
            raise ValueError(f"duplicate shortlist influencer_id: {influencer_id}")
        if rank is None or rank <= 0:
            raise ValueError(f"invalid shortlist rank for {influencer_id}")
        seen_ids.add(influencer_id)

        result.append(
            {
                "feedback_contract_version": FEEDBACK_CONTRACT_VERSION,
                "scenario_id": _text(row.get("scenario_id")),
                "config_version": _text(row.get("config_version")),
                "influencer_id": influencer_id,
                "canonical_handle": _text(row.get("canonical_handle")),
                "rank": rank,
                "total_score": _float(row.get("total_score")),
                "review_priority": "primary_review" if rank <= primary_review_limit else "backup_review",
                "machine_recommendation": "shortlisted_for_human_review",
                "positive_reasons": _text(row.get("positive_reasons")),
                "cautions": _text(row.get("cautions")),
                "human_decision": "",
                "human_decision_reason": "",
                "reviewer": "",
                "reviewed_at": "",
                "decision_status": "pending",
            }
        )

    return sorted(result, key=lambda row: (int(row["rank"]), str(row["influencer_id"])))


def validate_human_review_rows(
    rows: Iterable[dict[str, object]],
    *,
    require_complete: bool = False,
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_ranks: set[int] = set()

    for index, row in enumerate(rows, start=2):
        influencer_id = _text(row.get("influencer_id"))
        rank = _int(row.get("rank"))
        decision = _text(row.get("human_decision")).casefold()
        reason = _text(row.get("human_decision_reason"))
        reviewer = _text(row.get("reviewer"))
        reviewed_at = _text(row.get("reviewed_at"))

        if not influencer_id:
            errors.append(f"row {index}: influencer_id is required")
        elif influencer_id in seen_ids:
            errors.append(f"row {index}: duplicate influencer_id {influencer_id}")
        seen_ids.add(influencer_id)

        if rank is None or rank <= 0:
            errors.append(f"row {index}: positive rank is required")
        elif rank in seen_ranks:
            errors.append(f"row {index}: duplicate rank {rank}")
        else:
            seen_ranks.add(rank)

        if decision:
            if decision not in ALLOWED_HUMAN_DECISIONS:
                errors.append(f"row {index}: invalid human_decision {decision}")
            if not reason:
                errors.append(f"row {index}: human_decision_reason is required when a decision is entered")
            if not reviewer:
                errors.append(f"row {index}: reviewer is required when a decision is entered")
            if not reviewed_at:
                errors.append(f"row {index}: reviewed_at is required when a decision is entered")
        elif require_complete:
            errors.append(f"row {index}: human_decision is required")

    return errors


def build_campaign_result_template(review_rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for row in review_rows:
        decision = _text(row.get("human_decision")).casefold()
        if decision == "selected":
            status = "waiting_for_campaign_result"
        elif decision in {"rejected", "hold"}:
            status = "not_applicable_until_selected"
        else:
            status = "waiting_for_human_decision"

        result.append(
            {
                "feedback_contract_version": FEEDBACK_CONTRACT_VERSION,
                "scenario_id": _text(row.get("scenario_id")),
                "influencer_id": _text(row.get("influencer_id")),
                "canonical_handle": _text(row.get("canonical_handle")),
                "rank": _int(row.get("rank")),
                "human_decision": decision,
                "execution_status": "",
                "result_observed_at": "",
                "business_success": "",
                "actual_fee": "",
                "content_posted": "",
                "views": "",
                "likes": "",
                "comments": "",
                "saves": "",
                "shares": "",
                "gmv": "",
                "sales_amount": "",
                "orders": "",
                "result_notes": "",
                "feedback_status": status,
            }
        )
    return result


def validate_campaign_result_rows(
    rows: Iterable[dict[str, object]],
    *,
    selected_influencer_ids: set[str] | None = None,
    require_selected_results_complete: bool = False,
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    selected_ids = selected_influencer_ids or set()

    for index, row in enumerate(rows, start=2):
        influencer_id = _text(row.get("influencer_id"))
        decision = _text(row.get("human_decision")).casefold()
        execution_status = _text(row.get("execution_status")).casefold()
        success = _text(row.get("business_success")).casefold()
        content_posted = _text(row.get("content_posted")).casefold()
        observed_at = _text(row.get("result_observed_at"))

        if not influencer_id:
            errors.append(f"row {index}: influencer_id is required")
        elif influencer_id in seen_ids:
            errors.append(f"row {index}: duplicate influencer_id {influencer_id}")
        seen_ids.add(influencer_id)

        if execution_status and execution_status not in ALLOWED_EXECUTION_STATUSES:
            errors.append(f"row {index}: invalid execution_status {execution_status}")
        if success and success not in ALLOWED_TRI_STATE:
            errors.append(f"row {index}: invalid business_success {success}")
        if content_posted and content_posted not in ALLOWED_TRI_STATE:
            errors.append(f"row {index}: invalid content_posted {content_posted}")

        has_result_evidence = bool(execution_status or success or content_posted or observed_at)
        if selected_ids and influencer_id not in selected_ids and has_result_evidence:
            errors.append(f"row {index}: campaign-result evidence is not allowed for a non-selected influencer")

        if decision and selected_ids:
            expected = "selected" if influencer_id in selected_ids else decision
            if decision != expected:
                errors.append(f"row {index}: human_decision does not agree with selected review state")

        if require_selected_results_complete and influencer_id in selected_ids:
            if execution_status != "completed":
                errors.append(f"row {index}: selected influencer result must be completed")
            if not observed_at:
                errors.append(f"row {index}: selected influencer result_observed_at is required")
            if success not in {"yes", "no"}:
                errors.append(f"row {index}: selected influencer business_success must be yes/no")

    return errors


def feedback_readiness(
    review_rows: Iterable[dict[str, object]],
    result_rows: Iterable[dict[str, object]],
    *,
    success_definition_present: bool,
) -> FeedbackReadiness:
    reviews = [dict(row) for row in review_rows]
    results = {str(row.get("influencer_id", "")): dict(row) for row in result_rows}

    decisions = [_text(row.get("human_decision")).casefold() for row in reviews]
    decided_rows = sum(1 for decision in decisions if decision in ALLOWED_HUMAN_DECISIONS)
    selected_ids = {
        _text(row.get("influencer_id"))
        for row in reviews
        if _text(row.get("human_decision")).casefold() == "selected"
    }

    complete = 0
    for influencer_id in selected_ids:
        row = results.get(influencer_id, {})
        if (
            _text(row.get("execution_status")).casefold() == "completed"
            and _text(row.get("business_success")).casefold() in {"yes", "no"}
            and bool(_text(row.get("result_observed_at")))
        ):
            complete += 1

    review_count = len(reviews)
    pending_decisions = review_count - decided_rows
    pending_selected_results = len(selected_ids) - complete
    ready = (
        review_count > 0
        and pending_decisions == 0
        and len(selected_ids) > 0
        and pending_selected_results == 0
        and success_definition_present
    )
    return FeedbackReadiness(
        review_rows=review_count,
        decided_rows=decided_rows,
        selected_rows=len(selected_ids),
        selected_results_complete=complete,
        pending_decisions=pending_decisions,
        pending_selected_results=pending_selected_results,
        success_definition_present=success_definition_present,
        evaluation_ready=ready,
    )


def evaluate_observational_feedback(
    review_rows: Iterable[dict[str, object]],
    result_rows: Iterable[dict[str, object]],
    *,
    success_definition: str,
    top_k: int = 10,
) -> dict[str, object]:
    reviews = [dict(row) for row in review_rows]
    results = {str(row.get("influencer_id", "")): dict(row) for row in result_rows}
    readiness = feedback_readiness(
        reviews,
        results.values(),
        success_definition_present=bool(success_definition.strip()),
    )
    if not readiness.evaluation_ready:
        raise ValueError("matching feedback is not ready for evaluation")

    selected = [row for row in reviews if _text(row.get("human_decision")).casefold() == "selected"]
    ranks = [int(_int(row.get("rank")) or 0) for row in selected]
    scores = [_float(row.get("total_score")) for row in selected]
    scores = [score for score in scores if score is not None]
    successes = [
        1 if _text(results[_text(row.get("influencer_id"))].get("business_success")).casefold() == "yes" else 0
        for row in selected
    ]
    selected_top_k = sum(1 for rank in ranks if rank <= top_k)

    return {
        "feedback_contract_version": FEEDBACK_CONTRACT_VERSION,
        "success_definition": success_definition.strip(),
        "review_rows": readiness.review_rows,
        "selected_rows": readiness.selected_rows,
        "decision_acceptance_rate": readiness.selected_rows / readiness.review_rows,
        "mean_selected_rank": mean(ranks),
        "mean_selected_score": mean(scores) if scores else None,
        "selected_within_top_k": selected_top_k,
        "selected_within_top_k_rate": selected_top_k / readiness.selected_rows,
        "selected_business_success_count": sum(successes),
        "selected_business_success_rate": sum(successes) / readiness.selected_rows,
        "evaluation_type": "observational_selected_outcomes_only",
        "counterfactual_claim_allowed": False,
        "automatic_weight_calibration_applied": False,
    }
