import pytest

from v02_draft import data
from .conftest import make_bundle


def test_div_yield_normalises_both_semantics():
    assert data.normalize_div_yield(4.3) == pytest.approx(0.043)
    assert data.normalize_div_yield(0.043) == pytest.approx(0.043)
    assert data.normalize_div_yield(None) is None
    assert data.normalize_div_yield(0) is None


def test_div_yield_zero_is_valid():
    # a 0.5% yield arrives as 0.5 (percent) -> fraction; 0.005 -> itself
    assert data.normalize_div_yield(0.5) == pytest.approx(0.005)
    assert data.normalize_div_yield(0.005) == pytest.approx(0.005)


def test_snapshot_roundtrip(tmp_path):
    b = make_bundle()
    p = tmp_path / 'TEST.json'
    data.save_snapshot(b, p)
    b2 = data.load_snapshot(p)
    assert b2['symbol'] == 'TEST'
    assert b2['price'] == b['price']
    assert b2['source'] == 'snapshot'
    assert b2['fcf_hist'] == b['fcf_hist']


def test_audit_flags_missing_history():
    b = make_bundle(fcf_hist=[10.0], ni_hist=[])
    checks = {name: status for name, status, _ in data.audit(b)}
    assert checks['fcf history'] == 'FAIL'
    assert checks['net income history'] == 'FAIL'


def test_audit_ok_on_clean_bundle():
    checks = {name: status for name, status, _ in data.audit(make_bundle())}
    fails = [k for k, v in checks.items() if v == 'FAIL']
    assert fails == []
    assert checks['fcf history'] == 'OK'


def test_audit_warns_on_approximate_fixture():
    checks = {name: status for name, status, _ in data.audit(make_bundle(approximate=True))}
    assert checks['demo fixture'] == 'WARN'


def test_fx_london_quirk():
    # statement GBP -> price GBp: multiply by 100
    assert data.fx_to_price_ccy('GBP', 'GBp') == 100.0
    assert data.fx_to_price_ccy('USD', 'USD') == 1.0
    assert data.fx_to_price_ccy('GBp', 'GBp') == 1.0
