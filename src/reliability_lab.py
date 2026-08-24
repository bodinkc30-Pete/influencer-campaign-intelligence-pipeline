from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from src.discover_sources import discover_xlsx, duplicate_hash_groups, sha256_file
from src.sheet_classifier import classify_sheet, load_rules, normalize_text
from src.xlsx_probe import MAIN_NS, DOC_REL_NS, PKG_REL_NS, probe_workbook


@dataclass(frozen=True)
class ReliabilityIssue:
    severity: str
    code: str
    source_filename: str
    sheet_name: str
    evidence: str
    expected: str
    actual: str


@dataclass(frozen=True)
class BatchRegistration:
    batch_fingerprint: str
    action: str
    prior_seen_count: int
    current_seen_count: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_header_cells(row: list[object | None]) -> list[str]:
    result: list[str] = []
    for value in row:
        text = normalize_text(value)
        if text:
            result.append(text)
    return result


def build_baseline_manifest(input_dir: Path, rules_path: Path) -> dict:
    rules = load_rules(rules_path)
    discovered = discover_xlsx(input_dir)
    workbooks: list[dict] = []

    for record in discovered:
        workbook_path = input_dir / record.source_filename
        sheets: list[dict] = []
        for sheet in probe_workbook(
            workbook_path,
            max_rows=int(rules["candidate_header"]["scan_rows"]),
            max_cols=25,
        ):
            classification = classify_sheet(
                sheet.sheet_name,
                sheet.preview_rows,
                rules,
                source_filename=record.source_filename,
            )
            header_cells: list[str] = []
            if classification.primary_header_row:
                idx = classification.primary_header_row - 1
                if 0 <= idx < len(sheet.preview_rows):
                    header_cells = _normalized_header_cells(sheet.preview_rows[idx])
            non_empty_preview_rows = sum(
                1 for row in sheet.preview_rows if any(value not in (None, "") for value in row)
            )
            sheets.append(
                {
                    "sheet_name": sheet.sheet_name,
                    "sheet_xml_path": sheet.sheet_xml_path,
                    "dimension": sheet.dimension or "",
                    "sheet_type": classification.sheet_type,
                    "classification_confidence": classification.confidence,
                    "primary_header_row": classification.primary_header_row,
                    "header_signature": list(classification.header_signature),
                    "header_cells_normalized": header_cells,
                    "non_empty_preview_rows": non_empty_preview_rows,
                }
            )
        workbooks.append(
            {
                "source_filename": record.source_filename,
                "file_hash_sha256": record.file_hash_sha256,
                "file_size_bytes": record.file_size_bytes,
                "sheet_count": len(sheets),
                "candidate_sheet_count": sum(1 for item in sheets if item["sheet_type"] == "influencer_candidate"),
                "sheets": sheets,
            }
        )

    return {
        "manifest_version": 1,
        "generated_at_utc": utc_now(),
        "source_type": "excel_workbook",
        "validation_mode": "exact_batch_replay",
        "expected_workbook_count": len(workbooks),
        "expected_sheet_count": sum(item["sheet_count"] for item in workbooks),
        "expected_candidate_sheet_count": sum(item["candidate_sheet_count"] for item in workbooks),
        "workbooks": workbooks,
    }


def write_manifest(manifest: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _baseline_workbook_map(manifest: dict) -> dict[str, dict]:
    return {item["source_filename"]: item for item in manifest.get("workbooks", [])}


def _current_sheet_map(path: Path, rules: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for sheet in probe_workbook(
        path,
        max_rows=int(rules["candidate_header"]["scan_rows"]),
        max_cols=25,
    ):
        classification = classify_sheet(
            sheet.sheet_name,
            sheet.preview_rows,
            rules,
            source_filename=path.name,
        )
        header_cells: list[str] = []
        if classification.primary_header_row:
            idx = classification.primary_header_row - 1
            if 0 <= idx < len(sheet.preview_rows):
                header_cells = _normalized_header_cells(sheet.preview_rows[idx])
        non_empty_preview_rows = sum(
            1 for row in sheet.preview_rows if any(value not in (None, "") for value in row)
        )
        result[sheet.sheet_name] = {
            "sheet_name": sheet.sheet_name,
            "dimension": sheet.dimension or "",
            "sheet_type": classification.sheet_type,
            "classification_confidence": classification.confidence,
            "primary_header_row": classification.primary_header_row,
            "header_signature": list(classification.header_signature),
            "header_cells_normalized": header_cells,
            "non_empty_preview_rows": non_empty_preview_rows,
        }
    return result


def validate_snapshot(
    input_dir: Path,
    manifest: dict,
    rules_path: Path,
    *,
    enforce_hashes: bool = True,
) -> dict:
    issues: list[ReliabilityIssue] = []
    rules = load_rules(rules_path)
    baseline_map = _baseline_workbook_map(manifest)
    discovered = discover_xlsx(input_dir)
    current_map = {item.source_filename: item for item in discovered}

    baseline_names = set(baseline_map)
    current_names = set(current_map)

    for filename in sorted(baseline_names - current_names):
        issues.append(
            ReliabilityIssue(
                "ERROR", "MISSING_WORKBOOK", filename, "",
                "Expected workbook is absent from source snapshot.",
                "present", "missing",
            )
        )

    for filename in sorted(current_names - baseline_names):
        issues.append(
            ReliabilityIssue(
                "ERROR", "UNEXPECTED_WORKBOOK", filename, "",
                "Workbook was not part of the approved baseline batch.",
                "absent", "present",
            )
        )

    for digest, filenames in sorted(duplicate_hash_groups(discovered).items()):
        issues.append(
            ReliabilityIssue(
                "ERROR", "DUPLICATE_WORKBOOK_HASH", ";".join(filenames), "",
                f"Multiple workbook paths share the same SHA-256 prefix {digest[:12]}.",
                "unique content hash per workbook", f"duplicate_count={len(filenames)}",
            )
        )

    for filename in sorted(baseline_names & current_names):
        baseline_wb = baseline_map[filename]
        current_record = current_map[filename]
        if enforce_hashes and current_record.file_hash_sha256 != baseline_wb["file_hash_sha256"]:
            issues.append(
                ReliabilityIssue(
                    "ERROR", "WORKBOOK_HASH_CHANGED", filename, "",
                    "Exact-batch replay hash changed from the approved baseline.",
                    baseline_wb["file_hash_sha256"][:16], current_record.file_hash_sha256[:16],
                )
            )

        path = input_dir / filename
        try:
            current_sheets = _current_sheet_map(path, rules)
        except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
            issues.append(
                ReliabilityIssue(
                    "ERROR", "WORKBOOK_UNREADABLE", filename, "",
                    f"OOXML parser could not read workbook: {type(exc).__name__}.",
                    "readable xlsx", "unreadable",
                )
            )
            continue

        baseline_sheets = {item["sheet_name"]: item for item in baseline_wb["sheets"]}
        for sheet_name in sorted(set(baseline_sheets) - set(current_sheets)):
            issues.append(
                ReliabilityIssue(
                    "ERROR", "MISSING_SHEET", filename, sheet_name,
                    "Expected sheet is absent from workbook.",
                    "present", "missing",
                )
            )

        for sheet_name in sorted(set(baseline_sheets) & set(current_sheets)):
            before = baseline_sheets[sheet_name]
            after = current_sheets[sheet_name]
            if before["non_empty_preview_rows"] > 0 and after["non_empty_preview_rows"] == 0:
                issues.append(
                    ReliabilityIssue(
                        "ERROR", "EMPTY_SHEET", filename, sheet_name,
                        "Sheet had preview data in baseline but is empty now.",
                        f"non_empty_preview_rows>0 ({before['non_empty_preview_rows']})", "0",
                    )
                )

            if before["sheet_type"] == "influencer_candidate":
                if after["sheet_type"] != "influencer_candidate":
                    before_headers = set(before.get("header_cells_normalized") or [])
                    after_headers = set(after.get("header_cells_normalized") or [])
                    removed = sorted(before_headers - after_headers)
                    added = sorted(after_headers - before_headers)
                    issues.append(
                        ReliabilityIssue(
                            "ERROR", "CANDIDATE_SCHEMA_DRIFT", filename, sheet_name,
                            "Candidate header signature is no longer recognized."
                            + (f" removed={removed[:6]}" if removed else "")
                            + (f" added={added[:6]}" if added else ""),
                            "influencer_candidate", after["sheet_type"],
                        )
                    )
                elif before.get("header_signature") != after.get("header_signature"):
                    issues.append(
                        ReliabilityIssue(
                            "WARN", "CANDIDATE_HEADER_SIGNATURE_CHANGED", filename, sheet_name,
                            "Candidate sheet remains classifiable, but header signals changed.",
                            ",".join(before.get("header_signature") or []),
                            ",".join(after.get("header_signature") or []),
                        )
                    )

    error_count = sum(issue.severity == "ERROR" for issue in issues)
    return {
        "status": "PASS" if error_count == 0 else "FAIL",
        "validated_at_utc": utc_now(),
        "input_dir": str(input_dir),
        "workbooks_discovered": len(discovered),
        "expected_workbooks": manifest.get("expected_workbook_count"),
        "error_count": error_count,
        "warn_count": sum(issue.severity == "WARN" for issue in issues),
        "issues": [asdict(issue) for issue in issues],
    }


def batch_fingerprint(records: Iterable) -> str:
    payload = "\n".join(
        f"{item.source_filename}\t{item.file_hash_sha256}"
        for item in sorted(records, key=lambda item: item.source_filename.casefold())
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def register_batch(ledger_path: Path, fingerprint: str) -> BatchRegistration:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    else:
        ledger = {"ledger_version": 1, "batches": {}}

    batches = ledger.setdefault("batches", {})
    prior = int(batches.get(fingerprint, {}).get("seen_count", 0))
    action = "PROCESS_NEW_BATCH" if prior == 0 else "SKIP_ALREADY_PROCESSED"
    now = utc_now()
    batches[fingerprint] = {
        "first_seen_at_utc": batches.get(fingerprint, {}).get("first_seen_at_utc", now),
        "last_seen_at_utc": now,
        "seen_count": prior + 1,
    }

    temp_path = ledger_path.with_suffix(ledger_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, ledger_path)
    return BatchRegistration(fingerprint, action, prior, prior + 1)


def copy_xlsx_snapshot(source_dir: Path, target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(source_dir.glob("*.xlsx"), key=lambda p: p.name.casefold()):
        shutil.copy2(path, target_dir / path.name)


def _workbook_sheet_paths(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map: dict[str, str] = {}
    for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship"):
        target = rel.attrib["Target"].replace("\\", "/")
        if target.startswith("/"):
            normalized = target.lstrip("/")
        elif target.startswith("xl/"):
            normalized = target
        else:
            normalized = f"xl/{target}"
        rel_map[rel.attrib["Id"]] = normalized
    result: dict[str, str] = {}
    sheets = workbook.find(f"{{{MAIN_NS}}}sheets")
    if sheets is None:
        return result
    for sheet in sheets.findall(f"{{{MAIN_NS}}}sheet"):
        rel_id = sheet.attrib[f"{{{DOC_REL_NS}}}id"]
        result[sheet.attrib["name"]] = rel_map[rel_id]
    return result


def _rewrite_zip_member(path: Path, member_name: str, transform) -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir=path.parent) as tmp:
        temp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
            for info in source.infolist():
                payload = source.read(info.filename)
                if info.filename == member_name:
                    payload = transform(payload)
                target.writestr(info, payload)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def replace_shared_string_exact(path: Path, old_text: str, new_text: str) -> int:
    member = "xl/sharedStrings.xml"
    replaced = {"count": 0}

    def transform(payload: bytes) -> bytes:
        root = ET.fromstring(payload)
        for node in root.iter(f"{{{MAIN_NS}}}t"):
            if (node.text or "").strip() == old_text:
                node.text = new_text
                replaced["count"] += 1
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(path, "r") as archive:
        if member not in archive.namelist():
            return 0
    _rewrite_zip_member(path, member, transform)
    return replaced["count"]


def empty_sheet(path: Path, sheet_name: str) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        member = _workbook_sheet_paths(archive)[sheet_name]

    def transform(payload: bytes) -> bytes:
        root = ET.fromstring(payload)
        sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
        if sheet_data is not None:
            sheet_data.clear()
        dimension = root.find(f"{{{MAIN_NS}}}dimension")
        if dimension is not None:
            dimension.attrib["ref"] = "A1"
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    _rewrite_zip_member(path, member, transform)


def manifest_candidate_targets(manifest: dict) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for workbook in manifest.get("workbooks", []):
        for sheet in workbook.get("sheets", []):
            if sheet.get("sheet_type") == "influencer_candidate":
                result.append((workbook["source_filename"], sheet["sheet_name"]))
    return result
