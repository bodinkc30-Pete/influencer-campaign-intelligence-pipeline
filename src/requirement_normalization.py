from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

AGE_RE = re.compile(r"(?P<min>\d{1,2})\s*(?:-|–|—|to)\s*(?P<max>\d{1,2})", re.I)

DEFAULT_TAXONOMY = {
    "campaign_theme": {
        "skin_care": ["ผิว", "สกินแคร์", "skincare", "โลชั่น", "สิว", "ชุ่มชื้น"],
        "clinic_aesthetic": ["คลินิก", "เจ็บ", "บวม", "หมอ", "เครื่องมือ"],
        "sleep_wellness": ["นอน", "หลับ", "ก่อนนอน", "วิตกกังวล", "กัมมี่"],
        "joint_mobility": ["ข้อ", "เข่า", "ข้อต่อ", "วิ่ง", "เวท"],
        "hair_care": ["ผม", "ทำสี", "ผมร่วง", "ผมแห้ง"],
        "pet_care": ["สัตว์เลี้ยง", "น้องกิน", "อึ", "ถ่ายเหลว", "ขนร่วง"],
        "eyewear_fashion": ["แว่น", "แฟชั่น", "accessory", "หน้าจอ"],
    },
    "persona": {
        "self_care": ["self-care", "ดูแลตัวเอง", "ดูแลรูปร่าง"],
        "skin_concern_user": ["ปัญหาผิว", "ผิวหมอง", "เป็นสิว", "ผิวขาดน้ำ", "ผิวแห้ง"],
        "clinic_review_creator": ["สกินแคร์เชิงวิชาการ", "รีวิวคลินิก", "ความรู้พื้นฐาน"],
        "student": ["นักศึกษา", "เรียน"],
        "early_career": ["วัยเริ่มทำงาน"],
        "freelancer": ["ฟรีแลนซ์"],
        "health_fitness": ["เฮลตี้", "ฟิตเนส", "วิ่ง", "เวท"],
        "office_worker": ["พนักงานออฟฟิศ", "วัยทำงาน", "working people"],
        "working_parent": ["working moms", "คุณแม่"],
        "pet_owner": ["เจ้าของสัตว์เลี้ยง"],
        "general_consumer": ["ลูกค้าจริง", "คนทั่วไป"],
        "fashion_minimal": ["แฟชั่นมินิมอล"],
        "everyday_glasses_user": ["ใส่แว่นจริง", "ใส่เรียน", "ใส่ทำงาน"],
    },
    "content_style": {
        "real_review": ["real review", "รีวิวจริง", "ใช้จริง", "ความรู้สึกหลังใช้"],
        "ugc": ["ugc"],
        "diary": ["diary"],
        "before_after": ["before", "after", "ก่อนใช้", "หลังใช้"],
        "vlog": ["vlog"],
        "informal_storytelling": ["เพื่อนเล่าให้เพื่อนฟัง", "informal", "ไม่ใช้สคริปต์ขาย"],
        "close_up_product": ["close-up", "texture", "เนื้อสัมผัส"],
        "routine": ["routine"],
        "unboxing": ["แกะกล่อง", "เปิดถุง"],
    },
}


def _norm_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def normalize_platform(raw: str) -> tuple[str, str]:
    text = _norm_text(raw)
    if not text:
        return "", "source_missing"
    if "tiktok" in text or "tik tok" in text:
        return "tiktok", "exact_keyword"
    return "", "unmapped"


def normalize_target_gender(raw: str) -> dict[str, object]:
    text = _norm_text(raw)
    if not text:
        return {"mode": "unknown", "female_target_share": None, "male_target_share": None, "method": "source_missing"}
    female = any(x in text for x in ["หญิง", "ผู้หญิง", "female"])
    male = any(x in text for x in ["ชาย", "ผู้ชาย", "male"])
    pct = [int(x) for x in re.findall(r"(\d{1,3})\s*%", text)]
    if female and male and len(pct) >= 2:
        return {"mode": "mixed_weighted", "female_target_share": pct[0] / 100, "male_target_share": pct[1] / 100, "method": "explicit_percentages"}
    if female and male:
        return {"mode": "all", "female_target_share": 0.5, "male_target_share": 0.5, "method": "explicit_both"}
    if female:
        return {"mode": "female_only", "female_target_share": 1.0, "male_target_share": 0.0, "method": "explicit_gender"}
    if male:
        return {"mode": "male_only", "female_target_share": 0.0, "male_target_share": 1.0, "method": "explicit_gender"}
    return {"mode": "unmapped", "female_target_share": None, "male_target_share": None, "method": "unmapped"}


def parse_age_range(raw: str) -> dict[str, object]:
    text = _norm_text(raw).replace("ปี", "")
    if not text:
        return {"age_min": None, "age_max": None, "method": "source_missing"}
    match = AGE_RE.search(text)
    if not match:
        return {"age_min": None, "age_max": None, "method": "unmapped"}
    lo, hi = int(match.group("min")), int(match.group("max"))
    if lo > hi or lo < 13 or hi > 80:
        return {"age_min": None, "age_max": None, "method": "invalid_range"}
    return {"age_min": lo, "age_max": hi, "method": "explicit_range"}


def derive_tags(text: str, rules: Mapping[str, Sequence[str]]) -> tuple[list[str], list[str]]:
    normalized = _norm_text(text)
    tags: list[str] = []
    rule_ids: list[str] = []
    for tag, keywords in rules.items():
        matched = [kw for kw in keywords if _norm_text(kw) in normalized]
        if matched:
            tags.append(tag)
            rule_ids.append(f"{tag}:{'|'.join(sorted(set(matched)))}")
    return sorted(tags), sorted(rule_ids)


def normalize_audience_gender(raw: str) -> tuple[str, str]:
    text = _norm_text(raw)
    if not text:
        return "unknown", "source_missing"
    if AGE_RE.search(text) or re.fullmatch(r"\d{1,2}-\d{1,2}", text):
        return "invalid_age_in_gender", "schema_shift_detected"
    female = any(x in text for x in ["ผู้หญิง", "เพศหญิง", "หญิง", "female"])
    male = any(x in text for x in ["ผู้ชาย", "เพศชาย", "ชาย", "male"])
    if female and male:
        return "mixed", "explicit_both"
    if female:
        return "female", "explicit_gender"
    if male:
        return "male", "explicit_gender"
    return "unmapped", "unmapped"


def normalize_audience_age(raw: str) -> tuple[int | None, int | None, str]:
    text = _norm_text(raw)
    if not text:
        return None, None, "source_missing"
    if any(x in text for x in ["ผู้หญิง", "ผู้ชาย", "เพศหญิง", "เพศชาย"]):
        return None, None, "schema_shift_detected"
    result = parse_age_range(text)
    return result["age_min"], result["age_max"], result["method"]


def normalize_requirement_rows(
    requirements: Iterable[Mapping[str, str]],
    campaign_registry: Mapping[str, Mapping[str, str]],
    taxonomy: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    taxonomy = taxonomy or DEFAULT_TAXONOMY
    output: list[dict[str, object]] = []
    dq: list[dict[str, object]] = []
    for row in requirements:
        campaign_id = row["campaign_id"]
        registry = campaign_registry.get(campaign_id, {})
        combined = "\n".join([
            row.get("persona_raw", ""), row.get("target_content_raw", ""), row.get("content_style_raw", ""), row.get("pain_point_raw", ""), row.get("tier_sections_raw", "")
        ])
        theme_tags, theme_rules = derive_tags(combined, taxonomy["campaign_theme"])
        persona_tags, persona_rules = derive_tags(row.get("persona_raw", ""), taxonomy["persona"])
        style_tags, style_rules = derive_tags("\n".join([row.get("target_content_raw", ""), row.get("content_style_raw", "")]), taxonomy["content_style"])
        gender = normalize_target_gender(row.get("target_gender_raw", ""))
        age = parse_age_range(row.get("target_age_raw", ""))
        platform, platform_method = normalize_platform(row.get("platform_raw", ""))
        source_has_brief = row.get("requirement_status", "") in {"explicit_source_fields"}
        confidence = "high" if source_has_brief and theme_tags and gender["mode"] not in {"unknown", "unmapped"} and age["age_min"] is not None else ("medium" if source_has_brief else "low")
        normalized = {
            "campaign_id": campaign_id,
            "campaign_display_name": registry.get("campaign_display_name", ""),
            "brand_id": registry.get("brand_id", ""),
            "platform": platform,
            "platform_mapping_method": platform_method,
            "target_gender_mode": gender["mode"],
            "female_target_share": gender["female_target_share"],
            "male_target_share": gender["male_target_share"],
            "gender_mapping_method": gender["method"],
            "target_age_min": age["age_min"],
            "target_age_max": age["age_max"],
            "age_mapping_method": age["method"],
            "campaign_theme_tags": ";".join(theme_tags),
            "persona_tags": ";".join(persona_tags),
            "content_style_tags": ";".join(style_tags),
            "theme_rule_evidence": " || ".join(theme_rules),
            "persona_rule_evidence": " || ".join(persona_rules),
            "content_style_rule_evidence": " || ".join(style_rules),
            "requirement_source_status": row.get("requirement_status", ""),
            "fit_readiness": "ready_for_rule_based_fit" if source_has_brief and platform and (gender["mode"] not in {"unknown", "unmapped"} or age["age_min"] is not None or theme_tags) else "insufficient_source_requirement",
            "normalization_confidence": confidence,
            "requirement_normalization_version": "v1",
        }
        output.append(normalized)
        if not source_has_brief:
            dq.append({"entity_type": "campaign_requirement", "entity_id": campaign_id, "dq_code": "SOURCE_REQUIREMENT_MISSING", "severity": "WARN", "evidence": row.get("requirement_status", ""), "action": "Do not infer missing requirement fields from same-brand campaigns."})
        if row.get("target_gender_raw") and gender["mode"] == "unmapped":
            dq.append({"entity_type": "campaign_requirement", "entity_id": campaign_id, "dq_code": "TARGET_GENDER_UNMAPPED", "severity": "WARN", "evidence": row.get("target_gender_raw", ""), "action": "Manual taxonomy review required before gender fit."})
        if row.get("target_age_raw") and age["age_min"] is None:
            dq.append({"entity_type": "campaign_requirement", "entity_id": campaign_id, "dq_code": "TARGET_AGE_UNMAPPED", "severity": "WARN", "evidence": row.get("target_age_raw", ""), "action": "Manual age-range review required before age fit."})
        if source_has_brief and not theme_tags:
            dq.append({"entity_type": "campaign_requirement", "entity_id": campaign_id, "dq_code": "THEME_TAG_NOT_DERIVED", "severity": "WARN", "evidence": combined[:240], "action": "Keep theme fit disabled until a governed rule is added."})
    return output, dq


def build_audience_profiles(observations: Iterable[Mapping[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    dq: list[dict[str, object]] = []
    for row in observations:
        if row.get("influencer_id"):
            grouped[row["influencer_id"]].append(row)
    profiles: list[dict[str, object]] = []
    for influencer_id, rows in sorted(grouped.items()):
        gender_counts: Counter[str] = Counter()
        age_counts: Counter[str] = Counter()
        handles = Counter(r.get("canonical_handle", "") for r in rows if r.get("canonical_handle"))
        for r in rows:
            g, gm = normalize_audience_gender(r.get("audience_gender_raw", ""))
            if g in {"female", "male", "mixed"}:
                gender_counts[g] += 1
            elif g == "invalid_age_in_gender":
                dq.append({"entity_type": "influencer_audience", "entity_id": influencer_id, "dq_code": "AUDIENCE_GENDER_SCHEMA_SHIFT", "severity": "WARN", "evidence": r.get("audience_gender_raw", ""), "action": "Exclude shifted value from audience-gender profile."})
            lo, hi, am = normalize_audience_age(r.get("audience_age_raw", ""))
            if lo is not None and hi is not None:
                age_counts[f"{lo}-{hi}"] += 1
            elif am == "schema_shift_detected":
                dq.append({"entity_type": "influencer_audience", "entity_id": influencer_id, "dq_code": "AUDIENCE_AGE_SCHEMA_SHIFT", "severity": "WARN", "evidence": r.get("audience_age_raw", ""), "action": "Exclude shifted value from audience-age profile."})
        gender_total = sum(gender_counts.values())
        dominant_gender = gender_counts.most_common(1)[0][0] if gender_total else "unknown"
        gender_share = (gender_counts[dominant_gender] / gender_total) if gender_total else None
        age_total = sum(age_counts.values())
        dominant_age = age_counts.most_common(1)[0][0] if age_total else ""
        profiles.append({
            "influencer_id": influencer_id,
            "canonical_handle": handles.most_common(1)[0][0] if handles else "",
            "audience_gender_observation_count": gender_total,
            "audience_gender_female_count": gender_counts["female"],
            "audience_gender_male_count": gender_counts["male"],
            "audience_gender_mixed_count": gender_counts["mixed"],
            "audience_gender_dominant": dominant_gender,
            "audience_gender_dominant_share": gender_share,
            "audience_age_observation_count": age_total,
            "audience_age_dominant_band": dominant_age,
            "audience_age_band_counts": ";".join(f"{k}:{v}" for k, v in sorted(age_counts.items())),
            "audience_profile_confidence": "high" if gender_total >= 2 and age_total >= 2 else ("medium" if gender_total or age_total else "low"),
            "audience_profile_version": "v1",
        })
    return profiles, dq


def build_requirement_experience(
    observations: Iterable[Mapping[str, str]],
    normalized_requirements: Mapping[str, Mapping[str, object]],
) -> list[dict[str, object]]:
    theme: dict[str, Counter[str]] = defaultdict(Counter)
    persona: dict[str, Counter[str]] = defaultdict(Counter)
    style: dict[str, Counter[str]] = defaultdict(Counter)
    campaign_ids: dict[str, set[str]] = defaultdict(set)
    handles: dict[str, Counter[str]] = defaultdict(Counter)
    seen_pairs: set[tuple[str, str]] = set()
    for row in observations:
        iid, cid = row.get("influencer_id", ""), row.get("campaign_id", "")
        if not iid or not cid or (iid, cid) in seen_pairs:
            continue
        seen_pairs.add((iid, cid))
        req = normalized_requirements.get(cid)
        if not req:
            continue
        campaign_ids[iid].add(cid)
        if row.get("canonical_handle"):
            handles[iid][row["canonical_handle"]] += 1
        for tag in str(req.get("campaign_theme_tags", "")).split(";"):
            if tag: theme[iid][tag] += 1
        for tag in str(req.get("persona_tags", "")).split(";"):
            if tag: persona[iid][tag] += 1
        for tag in str(req.get("content_style_tags", "")).split(";"):
            if tag: style[iid][tag] += 1
    all_iids = sorted(set(campaign_ids) | set(handles))
    out: list[dict[str, object]] = []
    for iid in all_iids:
        out.append({
            "influencer_id": iid,
            "canonical_handle": handles[iid].most_common(1)[0][0] if handles[iid] else "",
            "campaign_experience_count": len(campaign_ids[iid]),
            "theme_experience_tags": ";".join(sorted(theme[iid])),
            "theme_experience_counts": ";".join(f"{k}:{theme[iid][k]}" for k in sorted(theme[iid])),
            "persona_requirement_experience_tags": ";".join(sorted(persona[iid])),
            "persona_requirement_experience_counts": ";".join(f"{k}:{persona[iid][k]}" for k in sorted(persona[iid])),
            "content_style_experience_tags": ";".join(sorted(style[iid])),
            "content_style_experience_counts": ";".join(f"{k}:{style[iid][k]}" for k in sorted(style[iid])),
            "experience_semantics": "historical_campaign_requirement_exposure_not_intrinsic_creator_trait",
            "requirement_experience_version": "v1",
        })
    return out


def age_overlap_score(target_min: int | None, target_max: int | None, observed_band: str) -> float | None:
    if target_min is None or target_max is None or not observed_band:
        return None
    m = AGE_RE.search(observed_band)
    if not m:
        return None
    obs_min, obs_max = int(m.group("min")), int(m.group("max"))
    overlap = max(0, min(target_max, obs_max) - max(target_min, obs_min) + 1)
    denom = max(1, obs_max - obs_min + 1)
    return round(100 * overlap / denom, 4)


def gender_fit_status(target_mode: str, dominant_gender: str) -> str:
    if target_mode in {"unknown", "unmapped"} or dominant_gender == "unknown":
        return "unknown"
    if target_mode == "all":
        return "broad_target"
    if target_mode == "mixed_weighted":
        return "match" if dominant_gender in {"female", "male", "mixed"} else "unknown"
    if target_mode == "female_only":
        return "match" if dominant_gender in {"female", "mixed"} else "mismatch"
    if target_mode == "male_only":
        return "match" if dominant_gender in {"male", "mixed"} else "mismatch"
    return "unknown"


def load_taxonomy(path: str | Path | None) -> dict[str, dict[str, list[str]]]:
    if not path:
        return DEFAULT_TAXONOMY
    return json.loads(Path(path).read_text(encoding="utf-8"))
