from pathlib import Path

import pytest

from src.candidate_adapter import adapt_candidate_sheet, identity_observation, load_contract, parse_fee, parse_number
from src.sheet_classifier import load_rules

RULES = load_rules(Path("config/sheet_classification_rules.json"))
CONTRACT = load_contract(Path("config/candidate_column_contract.json"))


def test_parse_follower_abbreviation():
    assert parse_number("21K") == 21000.0
    assert parse_number(": 11,489") == 11489.0


def test_parse_percent_with_double_percent_sign():
    assert parse_number("5.4%%", percent=True) == pytest.approx(0.054)


def test_identity_conflict_keeps_canonical_blank():
    header = ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET"]
    rows = [
        header,
        [1, "creator_a", "Name (@creator_b) | TikTok", 1000, 0.1, 1500],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert records[0]["dq_status"] == "ERROR"
    assert "DQ_IDENTITY_CONFLICT" in records[0]["dq_codes"]
    assert records[0]["canonical_handle_candidate"] == ""


def test_pii_values_are_not_emitted():
    header = ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET", "ที่อยู่จัดส่ง"]
    rows = [
        header,
        [1, "creator_a", "https://www.tiktok.com/@creator_a", 1000, 0.1, 1500, "SECRET ADDRESS 0812345678"],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    record_text = str(records[0])
    assert records[0]["pii_present"] is True
    assert "ที่อยู่จัดส่ง" in records[0]["pii_headers_present"]
    assert "SECRET ADDRESS" not in record_text
    assert "0812345678" not in record_text


def test_campaign_brief_row_between_sections_is_not_candidate():
    rows = [
        ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET"],
        [1, "creator_a", "https://www.tiktok.com/@creator_a", 1000, 0.1, 1500],
        ["Persona Influencer", "Healthy lifestyle creator"],
        ["Platform", "Tiktok"],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert len(records) == 1
    assert records[0]["canonical_handle_candidate"] == "creator_a"


def test_non_tiktok_influencer_header_ends_tiktok_section():
    rows = [
        ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET", "เพศผู้ติดตาม"],
        [1, "creator_a", "https://www.tiktok.com/@creator_a", 1000, 0.1, 1500, "ผู้หญิง"],
        ["Influencer LEMON8"],
        ["Number", "Influencer", "Link Lemon8", "Follower", "BUDGET", "เลือก 5", "ชื่อ-ที่อยู่"],
        [1, "creator_b", "https://www.lemon8-app.com/@creator_b", 1200, 800, True, "SECRET ADDRESS 0812345678"],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert len(records) == 1
    assert records[0]["canonical_handle_candidate"] == "creator_a"
    assert "SECRET ADDRESS" not in str(records)


def test_summary_metric_row_is_not_candidate():
    rows = [
        ["Influencer", "TIKTOK", "Follower", "Engangement Rate%", "BUDGET", "เลือก"],
        [1, "creator_a", 1000, 0.1, 1500, True],
        [None, "Minimum ER%", 0.08, 0.78, "Pass"],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert len(records) == 1


def test_value_level_pii_guard_suppresses_misaligned_address():
    rows = [
        ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET", "เพศผู้ติดตาม"],
        [1, "creator_a", "https://www.tiktok.com/@creator_a", 1000, 0.1, 1500, "ที่อยู่ 99 ถนนสุขุมวิท เขตบางนา 0812345678"],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert records[0]["audience_gender_raw"] == ""
    assert records[0]["pii_guard_triggered"] is True
    assert "DQ_PII_GUARD_SUPPRESSED" in records[0]["dq_codes"]
    assert "0812345678" not in str(records[0])


def test_fee_models_cover_real_source_variants():
    assert parse_fee("*Free*") == ("free", 0.0, "campaign")
    assert parse_fee("Barter No Budget") == ("barter", 0.0, "campaign")
    assert parse_fee("1500/hr") == ("hourly", 1500.0, "hour")
    assert parse_fee("ยังไม่ตอบกลับ") == ("pending", None, "")
    assert parse_fee(2500) == ("fixed", 2500.0, "campaign")


def test_candidate_header_without_influencer_label_still_closes_previous_section():
    rows = [
        ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET"],
        [1, "creator_a", "https://www.tiktok.com/@creator_a", 1000, 0.1, 1500],
        ["Number", "เลือก", "Link Tiktok", "Follower", "Engangement & View Rate%", "ยอดขาย", "เพศผู้ติดตาม", "อายุผู้ติดตาม", "BUDGET"],
        [1, True, "Name (@creator_b) | TikTok", 2000, 0.2, 5000, "ผู้หญิง", "25-34", "*Free*"],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert len(records) == 2
    assert records[0]["canonical_handle_candidate"] == "creator_a"
    assert records[1]["canonical_handle_candidate"] == "creator_b"
    assert records[1]["fee_model"] == "free"


def test_content_header_ends_candidate_section():
    rows = [
        ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET"],
        [1, "creator_a", "https://www.tiktok.com/@creator_a", 1000, 0.1, 1500],
        ["Num#", "Influencer", "***", "Follower", "Script", "ส่งดราฟแล้ว", "ลิ้งค์ดราฟ", "สินค้าที่ส่ง", "ลงโพส", "VideoView"],
        [1, "@creator_b", "รอ insight", 30000, "script text", False, None, "product", "url", 5000],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert len(records) == 1
    assert records[0]["canonical_handle_candidate"] == "creator_a"


def test_parse_number_tolerates_trailing_backtick():
    assert parse_number("11047`") == 11047.0


def test_percent_decimal_comma_is_not_thousands_separator():
    assert parse_number("12,84%", percent=True) == pytest.approx(0.1284)


def test_parenthesized_handle_wins_over_display_at_mention():
    header = ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET"]
    raw = [1, "bb.nattawut", "@bbNawut (@bb.nattawut) | TikTok", 16000, 0.06, 1500]
    _, _, _, handles = identity_observation(header, raw, CONTRACT)
    assert handles == ["bb.nattawut"]


def test_leading_ascii_handle_before_display_parentheses():
    header = ["Number", "TIKTOK", "Follower", "Engagement %", "BUDGET"]
    raw = [1, "creamwor (ครีมวอ)", 16100, 0.05, 2500]
    _, _, _, handles = identity_observation(header, raw, CONTRACT)
    assert handles == ["creamwor"]


def test_ordinal_only_summary_row_is_not_candidate():
    rows = [
        ["Number", "Influencer", "Link Tiktok", "Follower", "Engagement %", "BUDGET"],
        [1, "creator_a", "https://www.tiktok.com/@creator_a", 1000, 0.1, 1500],
        [1, "เลือก 1 คน", None, None, None, None],
    ]
    records = adapt_candidate_sheet("workbook.xlsx", "Influencer", rows, RULES, CONTRACT)
    assert len(records) == 1
