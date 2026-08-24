from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Classification:
    sheet_type: str
    confidence: str
    basis: str
    primary_header_row: int | None
    detected_header_rows: tuple[int, ...]
    header_signature: tuple[str, ...]


def load_rules(path: Path, overrides_path: Path | None = None) -> dict:
    with path.open("r", encoding="utf-8") as file_obj:
        rules = json.load(file_obj)
    rules.setdefault("sheet_overrides", [])
    if overrides_path is not None:
        with overrides_path.open("r", encoding="utf-8") as file_obj:
            private_config = json.load(file_obj)
        rules["sheet_overrides"].extend(private_config.get("sheet_overrides", []))
    return rules


def normalize_text(value: object | None) -> str:
    if value is None:
        return ""
    text = str(value).casefold().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _row_text(row: list[object | None]) -> str:
    return " | ".join(normalize_text(value) for value in row if value is not None)


def _candidate_score(row: list[object | None], signals: dict[str, int]) -> tuple[int, list[str]]:
    text = _row_text(row)
    compact = re.sub(r"\s+", "", text)
    hits: list[str] = []
    score = 0

    checks = {
        "tiktok": ("tiktok" in compact),
        "follower": ("follower" in compact),
        "engagement": ("engagement" in compact or "engangement" in compact),
        "budget": ("budget" in compact or "buget" in compact or "buget" in compact),
        "selection": ("เลือก" in text or "คอนเฟิร์ม" in text or "confirm" in compact),
        "influencer": ("influencer" in compact or "อินฟลูเอนเซอร์" in compact),
    }

    for signal, matched in checks.items():
        if matched:
            hits.append(signal)
            score += int(signals.get(signal, 0))
    return score, hits


def find_candidate_header_rows(preview_rows: list[list[object | None]], rules: dict) -> list[tuple[int, int, list[str]]]:
    config = rules["candidate_header"]
    min_score = int(config["min_score"])
    signals = config["signals"]
    matches: list[tuple[int, int, list[str]]] = []
    for index, row in enumerate(preview_rows, start=1):
        score, hits = _candidate_score(row, signals)
        if score >= min_score and "tiktok" in hits and "follower" in hits:
            matches.append((index, score, hits))
    return matches


def classify_sheet(
    sheet_name: str,
    preview_rows: list[list[object | None]],
    rules: dict,
    source_filename: str | None = None,
) -> Classification:
    name = normalize_text(sheet_name)

    if source_filename is not None:
        for override in rules.get("sheet_overrides", []):
            if (
                override["source_filename"] == source_filename
                and override["sheet_name"] == sheet_name
            ):
                return Classification(
                    sheet_type=override["sheet_type"],
                    confidence="high",
                    basis=f"manual override: {override['reason']}",
                    primary_header_row=None,
                    detected_header_rows=(),
                    header_signature=(),
                )

    candidate_headers = find_candidate_header_rows(preview_rows, rules)
    if candidate_headers:
        header_rows = tuple(item[0] for item in candidate_headers)
        primary = candidate_headers[0]
        return Classification(
            sheet_type="influencer_candidate",
            confidence="high",
            basis=f"candidate header signature score={primary[1]}",
            primary_header_row=primary[0],
            detected_header_rows=header_rows,
            header_signature=tuple(primary[2]),
        )

    for rule in rules["name_rules"]:
        for pattern in rule["patterns"]:
            if normalize_text(pattern) in name:
                return Classification(
                    sheet_type=rule["sheet_type"],
                    confidence="medium",
                    basis=f"sheet-name rule: {pattern}",
                    primary_header_row=None,
                    detected_header_rows=(),
                    header_signature=(),
                )

    return Classification(
        sheet_type=rules["fallback_type"],
        confidence="low",
        basis="no candidate signature or known name rule",
        primary_header_row=None,
        detected_header_rows=(),
        header_signature=(),
    )
