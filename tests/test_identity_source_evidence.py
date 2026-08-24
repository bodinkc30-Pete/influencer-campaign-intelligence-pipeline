from src.scan_identity_source_evidence import classify_strong_identity_cell


def test_tiktok_url_is_strong_identity_evidence():
    assert classify_strong_identity_cell('https://www.tiktok.com/@creator_one?_r=1') == ('tiktok_profile_url', 'creator_one')


def test_parenthesized_handle_is_strong_identity_evidence():
    assert classify_strong_identity_cell('Display (@creator.two) | TikTok') == ('parenthesized_profile_handle', 'creator.two')


def test_plain_handle_is_not_source_wide_strong_evidence():
    assert classify_strong_identity_cell('creator_one') is None
