from pathlib import Path

from src.sheet_classifier import classify_sheet, load_rules

RULES = load_rules(Path("config/sheet_classification_rules.json"))


def test_candidate_header_detects_common_variant():
    rows = [
        ["Campaign"],
        ["Number", "Influencer", "Link Tiktok", "Follower", "Engangement Rate%", "BUDGET", "เลือก 5 คน"],
    ]
    result = classify_sheet("Influencer เดือน1", rows, RULES)
    assert result.sheet_type == "influencer_candidate"
    assert result.primary_header_row == 2
    assert "tiktok" in result.header_signature
    assert "follower" in result.header_signature


def test_report_kols_is_not_candidate_without_follower_signature():
    rows = [["Num#", "Influencer", "Script", "คอนเฟิร์ม", "ลงโพส", "ลิงค์โพสต์"]]
    result = classify_sheet("Report KOLs", rows, RULES)
    assert result.sheet_type == "performance"


def test_ads_name_rule():
    result = classify_sheet("Report Ads", [["Campaign", "Spend"]], RULES)
    assert result.sheet_type == "ads"


def test_live_name_rule():
    result = classify_sheet("Report Livesteaming", [["Creator", "Revenue"]], RULES)
    assert result.sheet_type == "live"


def test_manual_override_for_ambiguous_sheet():
    rules = dict(RULES)
    rules["sheet_overrides"] = [
        {
            "source_filename": "workbook_01.xlsx",
            "sheet_name": "Sheet24",
            "sheet_type": "content_timeline",
            "reason": "reviewed ambiguous source sheet",
        }
    ]
    result = classify_sheet(
        "Sheet24",
        [["Influencer", "Follower", "Script", "Post"]],
        rules,
        source_filename="workbook_01.xlsx",
    )
    assert result.sheet_type == "content_timeline"
    assert result.confidence == "high"
