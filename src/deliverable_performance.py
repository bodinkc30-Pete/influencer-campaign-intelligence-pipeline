from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable

from src.candidate_adapter import _extract_handle
from src.pii_guard import looks_like_pii


def norm(value: object | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(p or "") for p in parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:16]}"


def excel_date_to_iso(value: object | None) -> str:
    if isinstance(value, (int, float)) and 40000 <= float(value) <= 60000:
        date = datetime(1899, 12, 30) + timedelta(days=float(value))
        return date.date().isoformat()
    text = str(value or "").strip()
    if text in {"#DIV/0!", "#N/A", "#VALUE!", "#REF!", "#NAME?"}:
        return ""
    return text


def parse_number(value: object | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "#DIV/0!", "#N/A", "#VALUE!"}:
        return None
    mult = 1.0
    if text.casefold().endswith("k"):
        mult = 1000.0
        text = text[:-1]
    try:
        return float(text.replace("%", "")) * mult
    except ValueError:
        return None


def normalized_alias(value: object | None) -> str:
    return norm(value)


class IdentityResolver:
    def __init__(self, masters: list[dict[str, str]], aliases: list[dict[str, str]]):
        self.handle_to_id: dict[str, str] = {}
        self.alias_to_ids: dict[str, set[str]] = defaultdict(set)
        for row in masters:
            self.handle_to_id[norm(row.get("canonical_handle"))] = row["influencer_id"]
        for row in aliases:
            alias = normalized_alias(row.get("alias_value"))
            if alias:
                self.alias_to_ids[alias].add(row["influencer_id"])
            handle = _extract_handle(row.get("alias_value", ""))
            if handle:
                self.alias_to_ids[norm(handle)].add(row["influencer_id"])

    def resolve(self, raw: object | None) -> tuple[str, str, str]:
        text = str(raw or "").strip()
        if not text:
            return "", "", "missing_identity"
        handle = _extract_handle(text)
        if handle and norm(handle) in self.handle_to_id:
            return self.handle_to_id[norm(handle)], norm(handle), "exact_canonical_handle"
        key = normalized_alias(text)
        ids = self.alias_to_ids.get(key, set())
        if len(ids) == 1:
            inf_id = next(iter(ids))
            canonical = next((h for h, i in self.handle_to_id.items() if i == inf_id), "")
            return inf_id, canonical, "exact_known_alias"
        if handle:
            ids = self.alias_to_ids.get(norm(handle), set())
            if len(ids) == 1:
                inf_id = next(iter(ids))
                canonical = next((h for h, i in self.handle_to_id.items() if i == inf_id), "")
                return inf_id, canonical, "exact_alias_handle"
        return "", norm(handle) if handle else "", "unresolved_exact_only"


HEADER_SYNONYMS = {
    "identity": ("influencer", "kols name", "kol name", "บัญชี tiktok"),
    "post_url": ("ลิงค์โพส", "ลิงค์โพสต์", "link post", "post link"),
    "draft_url": ("ลิงค์ดราฟ", "ลิ้งค์ดราฟ", "link draft"),
    "posted_date": ("วันที่ลงโพสต์", "วันลงโพสต์"),
    "schedule_date": ("กำหนดการลงโพส", "กำหนดการ", "วันลง"),
    "confirmed": ("คอนเฟิร์ม", "confirm"),
    "posted": ("ลงโพส", "ลงโพสต์"),
    "gencode": ("รหัสเจนโค้ด", "gencode", "gen code"),
    "ad_status": ("status ads", "ads status"),
    "product": ("รีวิวสินค้า", "สินค้า", "product"),
    "views": ("videoview", "video view", "ยอดวิว"),
    "likes": ("like", "การถูกใจ"),
    "comments": ("comment", "ความคิดเห็น"),
    "saves": ("save",),
    "shares": ("shared", "share", "แชร์"),
    "gmv": ("gmv",),
    "sales": ("ยอดขาย",),
    "orders": ("ออเดอร์", "order", "คำสั่งซื้อ"),
    "traffic": ("traffic", "การเข้าชม"),
    "viewers": ("ผู้ชม", "ผู้ชมทั้งหมด"),
    "ctr": ("ctr",),
    "cost": ("ต้นทุน", "งบแอดใช้จริง", "ค่าแอด"),
    "revenue": ("รายได้ขั้นต้น", "revenue"),
    "roi": ("roi",),
    "roas": ("roas",),
    "impressions": ("impressions", "ยอดการแสดงผล"),
    "clicks": ("click", "ยอดการคลิก"),
}


def map_headers(row: list[object | None]) -> dict[str, int]:
    result: dict[str, int] = {}
    for idx, value in enumerate(row):
        header = norm(value)
        if not header:
            continue
        for canonical, signals in HEADER_SYNONYMS.items():
            if canonical in result:
                continue
            if any(signal in header for signal in signals):
                result[canonical] = idx
    return result


def is_influencer_header(row: list[object | None]) -> bool:
    h = map_headers(row)
    return "identity" in h and len(set(h) & {"post_url", "posted_date", "gencode", "views", "likes", "product", "confirmed"}) >= 2


def is_performance_header(row: list[object | None]) -> bool:
    h = map_headers(row)
    return len(set(h) & {"sales", "orders", "traffic", "viewers", "views", "revenue", "gmv", "roi", "roas", "cost", "impressions"}) >= 3


def nearest_section_label(rows: list[list[object | None]], row_index_1based: int) -> str:
    labels: list[str] = []
    period_label = ""
    period_tokens = ("ตุลาคม", "พฤศจิกายน", "ธันวาคม", "oct", "nov", "dec", "เดือน 1", "เดือน 2", "เดือน 3", "เดือน 4")
    for pos in range(row_index_1based - 2, max(-1, row_index_1based - 70), -1):
        if pos < 0:
            break
        vals = [str(v).strip() for v in rows[pos] if v is not None and str(v).strip()]
        if 0 < len(vals) <= 2:
            label = " | ".join(vals)
            if any(err in label for err in ("#DIV/0!", "#N/A", "#VALUE!", "#REF!", "#NAME?")):
                continue
            if not period_label and any(token in norm(label) for token in period_tokens):
                period_label = label
            if len(labels) < 3:
                labels.append(label)
    parts: list[str] = []
    if period_label:
        parts.append(period_label)
    for label in reversed(labels):
        if label not in parts:
            parts.append(label)
    return " || ".join(parts)

def get_value(row: list[object | None], headers: dict[str, int], key: str) -> object | None:
    idx = headers.get(key)
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def pii_safe_text(value: object | None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text in {"#DIV/0!", "#N/A", "#VALUE!", "#REF!", "#NAME?"}:
        return ""
    return "" if looks_like_pii(value) else text
