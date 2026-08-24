from src.deliverable_performance import IdentityResolver, excel_date_to_iso, is_influencer_header, is_performance_header, map_headers, parse_number


def test_excel_date_guard():
    assert excel_date_to_iso(46125).startswith('2026-')
    assert excel_date_to_iso(244365) == '244365'


def test_parse_number_k_and_errors():
    assert parse_number('4.5K') == 4500
    assert parse_number('#DIV/0!') is None


def test_influencer_content_header():
    row=['No','Influencer','Follower','วันที่ลงโพสต์','ลิงค์โพสต์','VideoView','Like']
    assert is_influencer_header(row)
    h=map_headers(row)
    assert h['identity']==1 and h['views']==5


def test_campaign_performance_header():
    row=['Date','Revenue','Order','Traffic','ROAS']
    assert is_performance_header(row)


def test_identity_resolver_exact_only():
    masters=[{'influencer_id':'inf_1','canonical_handle':'creator.one'}]
    aliases=[{'influencer_id':'inf_1','alias_value':'Creator One (@creator.one) | TikTok'}]
    resolver=IdentityResolver(masters,aliases)
    assert resolver.resolve('@creator.one')[0]=='inf_1'
    assert resolver.resolve('Creator One (@creator.one) | TikTok')[0]=='inf_1'
    assert resolver.resolve('creator.on')[0]==''

def test_source_excel_error_date_is_sanitized():
    assert excel_date_to_iso('#DIV/0!') == ''
