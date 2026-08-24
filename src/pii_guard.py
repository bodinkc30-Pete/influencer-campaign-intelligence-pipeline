from __future__ import annotations

import re

_ADDRESS_MARKERS = (
    "จังหวัด",
    "อำเภอ",
    "ตำบล",
    "แขวง",
    "เขต",
    "ซอย",
    "ถนน",
    "หมู่ที่",
)


def looks_like_pii(value: object | None) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False

    compact_phone = re.sub(r"[^0-9]", "", text)
    phone_match = re.search(r"(?<!\d)0(?:[\s-]?\d){8,9}(?!\d)", text)
    if phone_match and 9 <= len(re.sub(r"\D", "", phone_match.group(0))) <= 10:
        return True

    lower = text.casefold()
    if "ที่อยู่" in lower and any(ch.isdigit() for ch in text):
        return True
    if ("เบอร์โทร" in lower or "โทร:" in lower or "โทร :" in lower or "tel:" in lower) and len(compact_phone) >= 9:
        return True

    marker_hits = sum(marker in text for marker in _ADDRESS_MARKERS)
    if marker_hits >= 2 and any(ch.isdigit() for ch in text):
        return True

    if re.search(r"\b[A-Z]{2}\s*\d{9}\s*TH\b", text, flags=re.IGNORECASE):
        return True

    return False
