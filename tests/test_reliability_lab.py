from __future__ import annotations

import json
import zipfile
from pathlib import Path

from src.discover_sources import discover_xlsx, duplicate_hash_groups
from src.reliability_lab import (
    batch_fingerprint,
    build_baseline_manifest,
    copy_xlsx_snapshot,
    empty_sheet,
    register_batch,
    replace_shared_string_exact,
    validate_snapshot,
)


def _write_minimal_xlsx(path: Path, *, candidate_header: list[str] | None = None) -> None:
    candidate_header = candidate_header or [
        "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET", "เลือก"
    ]
    shared = candidate_header + ["demo_user", "https://www.tiktok.com/@demo_user", "Operations", "Status"]
    shared_index = {value: idx for idx, value in enumerate(shared)}

    def row_xml(row_number: int, values: list[str]) -> str:
        cells = []
        for col_idx, value in enumerate(values, start=1):
            n = col_idx
            letters = ""
            while n:
                n, rem = divmod(n - 1, 26)
                letters = chr(65 + rem) + letters
            cells.append(f'<c r="{letters}{row_number}" t="s"><v>{shared_index[value]}</v></c>')
        return f'<row r="{row_number}">{"".join(cells)}</row>'

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Influencer" sheetId="1" r:id="rId1"/><sheet name="Operations" sheetId="2" r:id="rId2"/></sheets>
</workbook>'''
    workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>'''
    shared_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="%d" uniqueCount="%d">%s</sst>' % (
        len(shared), len(shared), ''.join(f'<si><t>{value}</t></si>' for value in shared)
    )
    sheet1 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:F2"/><sheetData>%s%s</sheetData></worksheet>''' % (
        row_xml(1, candidate_header),
        row_xml(2, ["demo_user", "https://www.tiktok.com/@demo_user"]),
    )
    sheet2 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:B1"/><sheetData>%s</sheetData></worksheet>''' % row_xml(1, ["Operations", "Status"])

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/sharedStrings.xml", shared_xml)
        z.writestr("xl/worksheets/sheet1.xml", sheet1)
        z.writestr("xl/worksheets/sheet2.xml", sheet2)


def _rules_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "sheet_classification_rules.json"


def test_baseline_snapshot_passes(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_minimal_xlsx(raw / "campaign.xlsx")
    manifest = build_baseline_manifest(raw, _rules_path())
    result = validate_snapshot(raw, manifest, _rules_path())
    assert result["status"] == "PASS"
    assert manifest["expected_workbook_count"] == 1
    assert manifest["expected_candidate_sheet_count"] == 1


def test_missing_workbook_is_blocking(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_minimal_xlsx(raw / "campaign.xlsx")
    manifest = build_baseline_manifest(raw, _rules_path())
    (raw / "campaign.xlsx").unlink()
    result = validate_snapshot(raw, manifest, _rules_path())
    assert result["status"] == "FAIL"
    assert "MISSING_WORKBOOK" in {i["code"] for i in result["issues"]}


def test_duplicate_hash_is_blocking(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_minimal_xlsx(raw / "campaign.xlsx")
    manifest = build_baseline_manifest(raw, _rules_path())
    copy_xlsx_snapshot(raw, tmp_path / "snapshot")
    snapshot = tmp_path / "snapshot"
    (snapshot / "duplicate.xlsx").write_bytes((snapshot / "campaign.xlsx").read_bytes())
    result = validate_snapshot(snapshot, manifest, _rules_path())
    codes = {i["code"] for i in result["issues"]}
    assert result["status"] == "FAIL"
    assert "DUPLICATE_WORKBOOK_HASH" in codes
    records = discover_xlsx(snapshot)
    assert duplicate_hash_groups(records)


def test_candidate_schema_drift_is_blocking(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_minimal_xlsx(raw / "campaign.xlsx")
    manifest = build_baseline_manifest(raw, _rules_path())
    assert replace_shared_string_exact(raw / "campaign.xlsx", "Follower", "Audience Size") == 1
    result = validate_snapshot(raw, manifest, _rules_path())
    codes = {i["code"] for i in result["issues"]}
    assert result["status"] == "FAIL"
    assert "WORKBOOK_HASH_CHANGED" in codes
    assert "CANDIDATE_SCHEMA_DRIFT" in codes


def test_empty_expected_sheet_is_blocking(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_minimal_xlsx(raw / "campaign.xlsx")
    manifest = build_baseline_manifest(raw, _rules_path())
    empty_sheet(raw / "campaign.xlsx", "Influencer")
    result = validate_snapshot(raw, manifest, _rules_path())
    codes = {i["code"] for i in result["issues"]}
    assert result["status"] == "FAIL"
    assert "EMPTY_SHEET" in codes


def test_same_batch_rerun_is_idempotent(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_minimal_xlsx(raw / "campaign.xlsx")
    fingerprint = batch_fingerprint(discover_xlsx(raw))
    ledger = tmp_path / "ledger.json"
    first = register_batch(ledger, fingerprint)
    second = register_batch(ledger, fingerprint)
    assert first.action == "PROCESS_NEW_BATCH"
    assert second.action == "SKIP_ALREADY_PROCESSED"
    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["batches"][fingerprint]["seen_count"] == 2


def test_discover_sources_duplicate_gate_fails_by_default(tmp_path: Path) -> None:
    from src.discover_sources import discovery_gate_failures

    raw = tmp_path / "raw"
    raw.mkdir()
    _write_minimal_xlsx(raw / "campaign.xlsx")
    (raw / "duplicate.xlsx").write_bytes((raw / "campaign.xlsx").read_bytes())
    failures = discovery_gate_failures(discover_xlsx(raw))
    assert "duplicate workbook content hashes detected" in failures
