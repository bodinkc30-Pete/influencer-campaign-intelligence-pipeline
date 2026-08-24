from src.pii_guard import looks_like_pii


def test_phone_and_address_are_pii():
    assert looks_like_pii("ที่อยู่ 99 ถนนสุขุมวิท เขตบางนา กรุงเทพ 0812345678") is True


def test_public_display_text_with_word_village_is_not_pii_by_itself():
    assert looks_like_pii("ตัวแทนหมู่บ้าน : SUNEE (@onjeeya) | TikTok") is False


def test_tracking_code_is_pii_like_operational_data():
    assert looks_like_pii("WB222936496TH") is True
