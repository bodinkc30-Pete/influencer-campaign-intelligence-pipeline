from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

_NS = {"x": MAIN_NS, "r": DOC_REL_NS}


@dataclass(frozen=True)
class SheetProbe:
    sheet_name: str
    sheet_xml_path: str
    dimension: str | None
    preview_rows: list[list[object | None]]


def _normalize_target(target: str) -> str:
    target = target.replace("\\", "/")
    if target.startswith("/"):
        return target.lstrip("/")
    if target.startswith("xl/"):
        return target
    return f"xl/{target}"


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(path))
    values: list[str] = []
    for si in root.findall(f"{{{MAIN_NS}}}si"):
        text_parts = [node.text or "" for node in si.iter(f"{{{MAIN_NS}}}t")]
        values.append("".join(text_parts))
    return values


def _workbook_sheet_paths(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationship_map = {
        rel.attrib["Id"]: _normalize_target(rel.attrib["Target"])
        for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship")
    }

    result: list[tuple[str, str]] = []
    sheets = workbook.find(f"{{{MAIN_NS}}}sheets")
    if sheets is None:
        return result
    for sheet in sheets.findall(f"{{{MAIN_NS}}}sheet"):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[f"{{{DOC_REL_NS}}}id"]
        result.append((name, relationship_map[rel_id]))
    return result


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref.upper())
    if not match:
        return 0
    letters = match.group(1)
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index - 1


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> object | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(f"{{{MAIN_NS}}}is")
        if inline is None:
            return None
        return "".join(node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t"))

    value_node = cell.find(f"{{{MAIN_NS}}}v")
    if value_node is None or value_node.text is None:
        return None
    raw = value_node.text

    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    if cell_type == "b":
        return raw == "1"
    if cell_type in {"str", "e"}:
        return raw

    try:
        number = float(raw)
        return int(number) if number.is_integer() else number
    except ValueError:
        return raw


def _column_letters(index: int) -> str:
    index += 1
    letters = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


def _preview_sheet(
    archive: zipfile.ZipFile,
    xml_path: str,
    shared_strings: list[str],
    max_rows: int,
    max_cols: int,
) -> tuple[str | None, list[list[object | None]]]:
    root = ET.fromstring(archive.read(xml_path))
    dimension_node = root.find(f"{{{MAIN_NS}}}dimension")
    declared_dimension = dimension_node.attrib.get("ref") if dimension_node is not None else None
    sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
    if sheet_data is None:
        return declared_dimension, []

    rows: list[list[object | None]] = []
    max_used_row = 0
    max_used_col = 0

    for row in sheet_data.findall(f"{{{MAIN_NS}}}row"):
        row_number = int(row.attrib.get("r", "0"))
        preview_values: list[object | None] | None = [None] * max_cols if 0 < row_number <= max_rows else None

        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            ref = cell.attrib.get("r", "A1")
            col_idx = _column_index(ref)
            max_used_row = max(max_used_row, row_number)
            max_used_col = max(max_used_col, col_idx + 1)
            if preview_values is not None and col_idx < max_cols:
                preview_values[col_idx] = _cell_value(cell, shared_strings)

        if preview_values is not None:
            while preview_values and preview_values[-1] is None:
                preview_values.pop()
            rows.append(preview_values)

    inferred_dimension = None
    if max_used_row and max_used_col:
        inferred_dimension = f"A1:{_column_letters(max_used_col - 1)}{max_used_row}"
    return declared_dimension or inferred_dimension, rows


def probe_workbook(path: Path, max_rows: int = 20, max_cols: int = 25) -> list[SheetProbe]:
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        result: list[SheetProbe] = []
        for sheet_name, xml_path in _workbook_sheet_paths(archive):
            dimension, rows = _preview_sheet(archive, xml_path, shared, max_rows=max_rows, max_cols=max_cols)
            result.append(
                SheetProbe(
                    sheet_name=sheet_name,
                    sheet_xml_path=xml_path,
                    dimension=dimension,
                    preview_rows=rows,
                )
            )
        return result


def iter_xlsx(input_dir: Path) -> Iterable[Path]:
    yield from sorted(input_dir.glob("*.xlsx"), key=lambda p: p.name.casefold())


def read_sheet_rows(path: Path, sheet_name: str, max_cols: int = 40) -> list[list[object | None]]:
    """Return a dense 1-based row sequence as a zero-based Python list.

    This is intentionally a lightweight OOXML reader for the controlled MVP
    candidate fields. It is not a replacement for a full Excel ingestion engine.
    """
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        sheet_map = dict(_workbook_sheet_paths(archive))
        if sheet_name not in sheet_map:
            raise KeyError(f"sheet not found: {sheet_name!r}")
        root = ET.fromstring(archive.read(sheet_map[sheet_name]))
        sheet_data = root.find(f"{{{MAIN_NS}}}sheetData")
        if sheet_data is None:
            return []

        row_map: dict[int, list[object | None]] = {}
        max_row = 0
        for row in sheet_data.findall(f"{{{MAIN_NS}}}row"):
            row_number = int(row.attrib.get("r", "0"))
            if row_number <= 0:
                continue
            values: list[object | None] = [None] * max_cols
            for cell in row.findall(f"{{{MAIN_NS}}}c"):
                col_idx = _column_index(cell.attrib.get("r", "A1"))
                if col_idx < max_cols:
                    values[col_idx] = _cell_value(cell, shared)
            while values and values[-1] is None:
                values.pop()
            row_map[row_number] = values
            max_row = max(max_row, row_number)

        return [row_map.get(row_number, []) for row_number in range(1, max_row + 1)]
