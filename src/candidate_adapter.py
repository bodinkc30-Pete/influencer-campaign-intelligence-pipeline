from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from src.pii_guard import looks_like_pii
from src.sheet_classifier import find_candidate_header_rows, normalize_text


@dataclass(frozen=True)
class CandidateSection:
    header_row: int
    end_row: int
    header: list[object | None]
    section_context_raw: str


def load_contract(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def _nonempty(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip() != "-"
    return True


def _header_matches(header_value: object | None, terms: list[str]) -> bool:
    text = normalize_text(header_value)
    compact = re.sub(r"\s+", "", text)
    return any(re.sub(r"\s+", "", normalize_text(term)) in compact for term in terms)


def _matching_columns(header: list[object | None], terms: list[str]) -> list[int]:
    return [index for index, value in enumerate(header) if _header_matches(value, terms)]


def _first_value(row: list[object | None], indices: list[int]) -> object | None:
    for index in indices:
        if index < len(row) and _nonempty(row[index]):
            return row[index]
    return None


def _safe_text(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def parse_number(value: object | None, *, percent: bool = False) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number

    text = str(value).strip()
    if not text or text == "-":
        return None
    text = text.replace(":", "").strip()
    text = text.strip("`'\" ")
    had_percent = "%" in text
    text = text.replace("%", "").strip()
    if percent and "," in text and "." not in text and text.count(",") == 1:
        left, right = text.split(",", 1)
        if left.replace("-", "").isdigit() and right.isdigit() and 1 <= len(right) <= 2:
            text = f"{left}.{right}"
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", "")

    multiplier = 1.0
    if text and text[-1:].casefold() == "k":
        multiplier = 1_000.0
        text = text[:-1]
    elif text and text[-1:].casefold() == "m":
        multiplier = 1_000_000.0
        text = text[:-1]

    try:
        number = float(text) * multiplier
    except ValueError:
        return None
    if percent and had_percent:
        number /= 100.0
    return number


def parse_fee(value: object | None) -> tuple[str, float | None, str]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return "missing", None, ""
    if isinstance(value, bool):
        return "unknown", None, ""
    if isinstance(value, (int, float)):
        return "fixed", float(value), "campaign"

    text = str(value).strip()
    if not text or text == "-":
        return "missing", None, ""
    lower = text.casefold()
    if "ยังไม่ตอบกลับ" in text or "pending" in lower:
        return "pending", None, ""
    if "barter" in lower:
        return "barter", 0.0, "campaign"
    if "free" in lower:
        return "free", 0.0, "campaign"

    hourly = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*/\s*(?:hr|hour)", lower)
    if hourly:
        return "hourly", float(hourly.group(1).replace(",", "")), "hour"

    number = parse_number(value)
    if number is not None:
        return "fixed", number, "campaign"
    return "unknown", None, ""


def _extract_handle(value: object | None) -> str | None:
    if value is None or isinstance(value, (bool, int, float)):
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None

    url_match = re.search(r"tiktok\.com/@([A-Za-z0-9._]+)", text, flags=re.IGNORECASE)
    if url_match:
        return url_match.group(1).casefold()

    parenthesized_handle = re.search(r"\(@([A-Za-z0-9._]+)\)", text)
    if parenthesized_handle:
        return parenthesized_handle.group(1).casefold()

    at_match = re.search(r"@([A-Za-z0-9._]+)", text)
    if at_match:
        return at_match.group(1).casefold()

    leading_token = re.match(r"^([A-Za-z0-9._]+)\s*\(", text)
    if leading_token:
        return leading_token.group(1).casefold()

    plain = text.lstrip("@").strip()
    if re.fullmatch(r"[A-Za-z0-9._]+", plain):
        return plain.casefold()
    return None


def identity_observation(
    header: list[object | None], row: list[object | None], contract: dict
) -> tuple[str, str, list[str], list[str]]:
    identity_indices = _matching_columns(header, contract["identity_header_terms"])
    raw_values: list[str] = []
    normalized: list[str] = []
    for index in identity_indices:
        if index >= len(row):
            continue
        value = row[index]
        if not _nonempty(value) or isinstance(value, (bool, int, float)):
            continue
        raw = str(value).strip()
        if raw not in raw_values:
            raw_values.append(raw)
        handle = _extract_handle(value)
        if handle and handle not in normalized:
            normalized.append(handle)

    primary_raw = raw_values[0] if raw_values else ""
    secondary_raw = raw_values[1] if len(raw_values) > 1 else ""
    return primary_raw, secondary_raw, raw_values, normalized


def _section_context(rows: list[list[object | None]], header_row: int) -> str:
    tokens = ("tier", "nano", "micro", "koc", "kol", "affiliate", "followers", "กลุ่มที่")
    context: list[str] = []
    start = max(1, header_row - 12)
    for row_number in range(header_row - 1, start - 1, -1):
        row = rows[row_number - 1]
        text = " | ".join(_safe_text(value) for value in row if _nonempty(value))
        if text and any(token in text.casefold() for token in tokens):
            context.append(text)
            if len(context) == 2:
                break
    return " || ".join(reversed(context))


def _is_influencer_table_header(row: list[object | None]) -> bool:
    text = " | ".join(normalize_text(value) for value in row if value is not None)
    compact = re.sub(r"\s+", "", text)
    has_influencer = "influencer" in compact or "อินฟลูเอนเซอร์" in compact
    has_follower = "follower" in compact
    has_structure_signal = any(
        token in compact
        for token in (
            "link",
            "tiktok",
            "lemon8",
            "script",
            "budget",
            "buget",
            "engagement",
            "engangement",
            "ลงโพส",
            "videoview",
        )
    )
    return has_influencer and has_follower and has_structure_signal


def _structural_header_rows(rows: list[list[object | None]]) -> list[int]:
    return [
        row_number
        for row_number, row in enumerate(rows, start=1)
        if _is_influencer_table_header(row)
    ]


def _ordinal_evidence(row: list[object | None]) -> bool:
    if not row:
        return False
    value = row[0]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return float(value).is_integer() and 1 <= float(value) <= 10000


def _suppress_pii(value: object | None) -> tuple[str, bool]:
    text = _safe_text(value)
    if text and looks_like_pii(text):
        return "", True
    return text, False


def detect_sections(rows: list[list[object | None]], classifier_rules: dict) -> list[CandidateSection]:
    matches = find_candidate_header_rows(rows, classifier_rules)
    candidate_header_rows = [item[0] for item in matches]
    structural_headers = sorted(set(_structural_header_rows(rows) + candidate_header_rows))
    sections: list[CandidateSection] = []
    for header_row in candidate_header_rows:
        later_boundaries = [row_number for row_number in structural_headers if row_number > header_row]
        end_row = (min(later_boundaries) - 1) if later_boundaries else len(rows)
        sections.append(
            CandidateSection(
                header_row=header_row,
                end_row=end_row,
                header=rows[header_row - 1],
                section_context_raw=_section_context(rows, header_row),
            )
        )
    return sections


def _field_indices(header: list[object | None], contract: dict) -> dict[str, list[int]]:
    return {
        field: _matching_columns(header, terms)
        for field, terms in contract["fields"].items()
    }


def _pii_indices(header: list[object | None], contract: dict) -> list[int]:
    return _matching_columns(header, contract["pii_header_terms"])


def _pii_headers(header: list[object | None], indices: list[int]) -> str:
    return ";".join(_safe_text(header[index]) for index in indices if index < len(header))


def _row_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def adapt_candidate_sheet(
    source_filename: str,
    sheet_name: str,
    rows: list[list[object | None]],
    classifier_rules: dict,
    contract: dict,
) -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []
    for section in detect_sections(rows, classifier_rules):
        field_indices = _field_indices(section.header, contract)
        pii_indices = _pii_indices(section.header, contract)

        for row_number in range(section.header_row + 1, section.end_row + 1):
            row = rows[row_number - 1]
            primary_raw, secondary_raw, raw_identity_values, normalized_handles = identity_observation(
                section.header, row, contract
            )
            if not raw_identity_values:
                continue

            follower_raw = _first_value(row, field_indices["follower_raw"])
            engagement_raw = _first_value(row, field_indices["engagement_raw"])
            budget_raw = _first_value(row, field_indices["budget_raw"])
            sales_raw = _first_value(row, field_indices["historical_sales_raw"])

            follower_preview = parse_number(follower_raw)
            engagement_preview = parse_number(engagement_raw, percent=True)
            fee_model, fee_amount_preview, fee_unit = parse_fee(budget_raw)
            budget_preview = fee_amount_preview
            sales_preview = parse_number(sales_raw)
            metric_evidence = (
                follower_preview is not None
                and follower_preview >= 1
                and (
                    bool(normalized_handles)
                    or engagement_preview is not None
                    or budget_preview is not None
                    or sales_preview is not None
                )
            )
            if not metric_evidence:
                continue
            gender_raw = _first_value(row, field_indices["audience_gender_raw"])
            age_raw = _first_value(row, field_indices["audience_age_raw"])
            selected_raw = _first_value(row, field_indices["selected_raw"])
            confirmed_raw = _first_value(row, field_indices["confirmed_raw"])
            pet_raw = _first_value(row, field_indices["pet_type_raw"])

            follower = follower_preview
            engagement = engagement_preview
            budget = budget_preview
            historical_sales = sales_preview

            dq_codes: list[str] = []
            if not normalized_handles:
                dq_codes.append("DQ_IDENTITY_UNPARSABLE")
            elif len(normalized_handles) > 1:
                dq_codes.append("DQ_IDENTITY_CONFLICT")
            if _nonempty(follower_raw) and follower is None:
                dq_codes.append("DQ_FOLLOWER_INVALID")
            elif follower is None:
                dq_codes.append("DQ_FOLLOWER_MISSING")
            if _nonempty(engagement_raw) and engagement is None:
                dq_codes.append("DQ_ENGAGEMENT_INVALID")
            elif engagement is None:
                dq_codes.append("DQ_ENGAGEMENT_MISSING")
            if fee_model == "unknown":
                dq_codes.append("DQ_FEE_INVALID")
            elif fee_model == "pending":
                dq_codes.append("DQ_FEE_PENDING")
            elif fee_model == "missing":
                dq_codes.append("DQ_FEE_MISSING")

            safe_primary_raw, guard_primary = _suppress_pii(primary_raw)
            safe_secondary_raw, guard_secondary = _suppress_pii(secondary_raw)
            safe_gender_raw, guard_gender = _suppress_pii(gender_raw)
            safe_age_raw, guard_age = _suppress_pii(age_raw)
            safe_pet_raw, guard_pet = _suppress_pii(pet_raw)
            pii_guard_triggered = any(
                (guard_primary, guard_secondary, guard_gender, guard_age, guard_pet)
            )
            if pii_guard_triggered:
                dq_codes.append("DQ_PII_GUARD_SUPPRESSED")

            error_codes = {
                "DQ_IDENTITY_UNPARSABLE",
                "DQ_IDENTITY_CONFLICT",
                "DQ_PII_GUARD_SUPPRESSED",
            }
            dq_status = "ERROR" if any(code in error_codes for code in dq_codes) else ("WARN" if dq_codes else "PASS")

            pii_present = any(index < len(row) and _nonempty(row[index]) for index in pii_indices)
            canonical_handle_candidate = normalized_handles[0] if len(normalized_handles) == 1 else ""

            record: dict[str, object] = {
                "source_filename": source_filename,
                "source_sheet_name": sheet_name,
                "source_row_number": row_number,
                "source_section_header_row": section.header_row,
                "section_context_raw": section.section_context_raw,
                "identity_primary_raw": safe_primary_raw,
                "identity_secondary_raw": safe_secondary_raw,
                "normalized_handle_candidates": ";".join(normalized_handles),
                "canonical_handle_candidate": canonical_handle_candidate,
                "follower_raw": _safe_text(follower_raw),
                "follower_normalized": "" if follower is None else int(follower) if follower.is_integer() else follower,
                "engagement_raw": _safe_text(engagement_raw),
                "engagement_normalized": "" if engagement is None else engagement,
                "budget_raw": _safe_text(budget_raw),
                "budget_normalized": "" if budget is None else budget,
                "fee_model": fee_model,
                "fee_amount_normalized": "" if budget is None else budget,
                "fee_unit": fee_unit,
                "historical_sales_raw": _safe_text(sales_raw),
                "historical_sales_normalized": "" if historical_sales is None else historical_sales,
                "audience_gender_raw": safe_gender_raw,
                "audience_age_raw": safe_age_raw,
                "selected_raw": _safe_text(selected_raw),
                "confirmed_raw": _safe_text(confirmed_raw),
                "pet_type_raw": safe_pet_raw,
                "pii_present": pii_present,
                "pii_guard_triggered": pii_guard_triggered,
                "pii_headers_present": _pii_headers(section.header, pii_indices) if pii_present else "",
                "dq_status": dq_status,
                "dq_codes": ";".join(dq_codes),
            }
            record["source_row_hash"] = _row_hash(record)
            observations.append(record)
    return observations
