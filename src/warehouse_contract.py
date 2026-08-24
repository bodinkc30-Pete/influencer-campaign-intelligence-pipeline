from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Sequence
import csv
import hashlib
import json


@dataclass(frozen=True)
class TableContract:
    name: str
    primary_key: tuple[str, ...]
    foreign_keys: tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...]
    required_columns: tuple[str, ...]


TABLE_CONTRACTS: dict[str, TableContract] = {
    "dim_influencer": TableContract(
        name="dim_influencer",
        primary_key=("influencer_id",),
        foreign_keys=(),
        required_columns=(
            "influencer_id", "platform", "canonical_handle", "master_status",
            "identity_resolution_method", "identity_confidence", "observation_count",
            "reviewed_observation_count", "workbook_count", "sheet_count",
            "golden_master_version", "pii_boundary_status",
        ),
    ),
    "influencer_identity_alias": TableContract(
        name="influencer_identity_alias",
        primary_key=("source_row_hash", "alias_type", "alias_value"),
        foreign_keys=((("influencer_id",), "dim_influencer", ("influencer_id",)),),
        required_columns=(
            "influencer_id", "platform", "canonical_handle", "alias_type", "alias_value",
            "match_method", "source_filename", "source_sheet_name", "source_row_number", "source_row_hash",
        ),
    ),
    "dim_brand": TableContract(
        name="dim_brand",
        primary_key=("brand_id",),
        foreign_keys=(),
        required_columns=(
            "brand_id", "canonical_brand_name", "brand_mapping_method",
            "brand_mapping_confidence", "business_verification_status",
        ),
    ),
    "dim_campaign": TableContract(
        name="dim_campaign",
        primary_key=("campaign_id",),
        foreign_keys=((("brand_id",), "dim_brand", ("brand_id",)),),
        required_columns=(
            "campaign_id", "brand_id", "campaign_display_name", "source_filename",
            "candidate_sheet_name", "campaign_period_label", "period_resolution_method",
            "period_confidence", "platform", "campaign_name_status", "campaign_registry_version",
        ),
    ),
    "campaign_requirement": TableContract(
        name="campaign_requirement",
        primary_key=("campaign_id",),
        foreign_keys=((("campaign_id",), "dim_campaign", ("campaign_id",)),),
        required_columns=(
            "campaign_id", "primary_candidate_budget_amount", "primary_budget_scope",
            "budget_currency", "tier_sections_raw", "persona_raw", "target_content_raw",
            "content_style_raw", "target_gender_raw", "target_age_raw", "pain_point_raw",
            "platform_raw", "requirement_status", "requirement_inheritance_applied", "requirement_version",
        ),
    ),
    "fact_campaign_influencer": TableContract(
        name="fact_campaign_influencer",
        primary_key=("campaign_influencer_id",),
        foreign_keys=(
            (("campaign_id",), "dim_campaign", ("campaign_id",)),
            (("influencer_id",), "dim_influencer", ("influencer_id",)),
        ),
        required_columns=(
            "campaign_influencer_id", "campaign_id", "influencer_id", "canonical_handle",
            "observation_count", "selected_status", "confirmed_status", "fee_status",
            "campaign_history_dq_status", "history_version",
        ),
    ),
    "fact_campaign_deliverable": TableContract(
        name="fact_campaign_deliverable",
        primary_key=("deliverable_id",),
        foreign_keys=(
            (("campaign_id",), "dim_campaign", ("campaign_id",)),
            (("influencer_id",), "dim_influencer", ("influencer_id",)),
        ),
        required_columns=(
            "deliverable_id", "campaign_id", "influencer_id", "canonical_handle", "deliverable_type",
            "platform", "source_filename", "source_sheet_name", "source_row_number",
            "deliverable_version", "deliverable_dq_status",
        ),
    ),
    "fact_influencer_performance": TableContract(
        name="fact_influencer_performance",
        primary_key=("performance_id",),
        foreign_keys=(
            (("campaign_id",), "dim_campaign", ("campaign_id",)),
            (("influencer_id",), "dim_influencer", ("influencer_id",)),
            (("deliverable_id",), "fact_campaign_deliverable", ("deliverable_id",)),
        ),
        required_columns=(
            "performance_id", "campaign_id", "influencer_id", "measurement_scope",
            "metric_definition_version", "source_filename", "source_sheet_name", "source_row_number",
        ),
    ),
    "fact_campaign_performance": TableContract(
        name="fact_campaign_performance",
        primary_key=("campaign_performance_id",),
        foreign_keys=((("campaign_id",), "dim_campaign", ("campaign_id",)),),
        required_columns=(
            "campaign_performance_id", "campaign_id", "performance_scope",
            "metric_definition_version", "source_filename", "source_sheet_name", "source_row_number",
        ),
    ),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Mapping[str, object]], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        seen: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.append(key)
        fieldnames = seen
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def is_iso_date_text(value: str | None) -> bool:
    text = (value or "").strip()
    if len(text) != 10:
        return False
    try:
        date.fromisoformat(text)
        return True
    except ValueError:
        return False


def add_parsed_date(row: Mapping[str, str], raw_column: str, parsed_column: str) -> dict[str, str]:
    result = dict(row)
    raw_value = (row.get(raw_column) or "").strip()
    result[f"{parsed_column}_raw"] = raw_value
    result[parsed_column] = raw_value if is_iso_date_text(raw_value) else ""
    return result


def table_fingerprint(rows: Sequence[Mapping[str, str]], key_columns: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda r: tuple((r.get(c) or "") for c in key_columns)):
        payload = "|".join((row.get(c) or "") for c in key_columns)
        digest.update(payload.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def validate_required_columns(table_name: str, rows: Sequence[Mapping[str, str]]) -> list[str]:
    contract = TABLE_CONTRACTS[table_name]
    if not rows:
        return [f"{table_name}:EMPTY_INPUT"]
    columns = set(rows[0].keys())
    return [f"{table_name}:MISSING_COLUMN:{col}" for col in contract.required_columns if col not in columns]


def duplicate_primary_keys(table_name: str, rows: Sequence[Mapping[str, str]]) -> list[tuple[str, ...]]:
    contract = TABLE_CONTRACTS[table_name]
    seen: set[tuple[str, ...]] = set()
    duplicates: list[tuple[str, ...]] = []
    for row in rows:
        key = tuple((row.get(col) or "").strip() for col in contract.primary_key)
        if key in seen:
            duplicates.append(key)
        else:
            seen.add(key)
    return duplicates


def blank_primary_keys(table_name: str, rows: Sequence[Mapping[str, str]]) -> list[tuple[str, ...]]:
    contract = TABLE_CONTRACTS[table_name]
    output: list[tuple[str, ...]] = []
    for row in rows:
        key = tuple((row.get(col) or "").strip() for col in contract.primary_key)
        if any(not value for value in key):
            output.append(key)
    return output


def foreign_key_violations(tables: Mapping[str, Sequence[Mapping[str, str]]]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    indexes: dict[tuple[str, tuple[str, ...]], set[tuple[str, ...]]] = {}
    for child_name, child_rows in tables.items():
        contract = TABLE_CONTRACTS[child_name]
        for child_cols, parent_name, parent_cols in contract.foreign_keys:
            idx_key = (parent_name, parent_cols)
            if idx_key not in indexes:
                indexes[idx_key] = {
                    tuple((row.get(col) or "").strip() for col in parent_cols)
                    for row in tables[parent_name]
                }
            parent_keys = indexes[idx_key]
            for row in child_rows:
                child_key = tuple((row.get(col) or "").strip() for col in child_cols)
                # Nullable FK is allowed only when every component is blank.
                if all(not part for part in child_key):
                    continue
                if child_key not in parent_keys:
                    violations.append({
                        "child_table": child_name,
                        "child_columns": ",".join(child_cols),
                        "child_key": "|".join(child_key),
                        "parent_table": parent_name,
                        "parent_columns": ",".join(parent_cols),
                    })
    return violations


def simulate_idempotent_upsert(rows: Sequence[Mapping[str, str]], key_columns: Sequence[str]) -> tuple[int, int, int]:
    """Return row_count_after_first, row_count_after_second, changed_rows_on_second."""
    store: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple((row.get(c) or "") for c in key_columns)
        store[key] = dict(row)
    first_count = len(store)
    changed = 0
    for row in rows:
        key = tuple((row.get(c) or "") for c in key_columns)
        before = store.get(key)
        after = dict(row)
        if before != after:
            changed += 1
        store[key] = after
    return first_count, len(store), changed


def contract_as_json() -> dict[str, object]:
    return {
        name: {
            "primary_key": list(contract.primary_key),
            "foreign_keys": [
                {
                    "child_columns": list(child_cols),
                    "parent_table": parent_table,
                    "parent_columns": list(parent_cols),
                }
                for child_cols, parent_table, parent_cols in contract.foreign_keys
            ],
            "required_columns": list(contract.required_columns),
        }
        for name, contract in TABLE_CONTRACTS.items()
    }
