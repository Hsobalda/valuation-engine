import pytest

from v02_draft import metrics as M
from .conftest import make_bundle


# ---------------------------------------------------------------------------
# F-Score: the conftest bundle is a deteriorating-ish company; verify every
# criterion against hand-computed values.
# ---------------------------------------------------------------------------
def test_fscore_hand_computed():
    b = make_bundle()
    fs = M.fscore(b)
    assert fs['available']
    pts = {name: p for name, p, _ in fs['points']}
    # ROA latest = 8/300 > 0 -> 1
    assert pts['ROA > 0'] == 1
    # OCF 12 > 0 -> 1
    assert pts['OCF > 0'] == 1
    # ROA: prior 8/295=2.71% -> latest 8/300=2.67% (falling) -> 0
    assert pts['ROA rising'] == 0
    # accruals: OCF/TA = 12/300 = 4% > ROA 2.67% -> 1
    assert pts['accruals: OCF/TA > ROA'] == 1
    # LTD/TA: 65/295=22.0% -> 55/300=18.3% (falling) -> 1
    assert pts['leverage falling'] == 1
    # current ratio: 78/52=1.50 -> 80/50=1.60 (rising) -> 1
    assert pts['current ratio rising'] == 1
    # shares 101.5 -> 100 (buyback, no dilution) -> 1
    assert pts['no dilution'] == 1
    # gross margin: (88-50)/88=43.2% -> (90-50)/90=44.4% (rising) -> 1
    assert pts['gross margin rising'] == 1
    # asset turnover: 88/295=0.298 -> 90/300=0.300 (rising) -> 1
    assert pts['asset turnover rising'] == 1
    assert fs['score'] == 8


def test_fscore_needs_two_years():
    b = make_bundle(ni_hist=[8.0])
    fs = M.fscore(b)
    assert not fs['available'] and fs['score'] is None


# ---------------------------------------------------------------------------
# Altman Z: hand-computed on the conftest bundle
# ---------------------------------------------------------------------------
def test_altman_z_hand_computed():
    b = make_bundle()
    az = M.altman_z(b)
    assert az['available']
    # WC = 80-50 = 30; TA=300; RE=60; EBIT=12; mktcap=10000; TL=60; S=90
    expected = (1.2 * 30 / 300 + 1.4 * 60 / 300 + 3.3 * 12 / 300
                + 0.6 * 10000 / 60 + 1.0 * 90 / 300)
    assert az['z'] == pytest.approx(expected)
    assert az['zone'] == 'safe'          # huge MVE/TL term dominates


def test_altman_z_distress_zone_flags():
    b = make_bundle(mkt_cap=120.0, retained_earnings=-30.0, ebit=1.0,
                    total_assets=300.0, revenue=90.0)
    az = M.altman_z(b)
    assert az['z'] < 1.8 and az['zone'] == 'distress'


def test_altman_z_missing_inputs():
    b = make_bundle(total_assets=None)
    az = M.altman_z(b)
    assert not az['available'] and 'total_assets' in az['missing']


# ---------------------------------------------------------------------------
# Earnings reality (Layer 4)
# ---------------------------------------------------------------------------
def test_accruals_ratio():
    # (NI 8 - OCF 12)/TA 300 = -1.3%: cash runs ahead of earnings (good)
    assert M.accruals_ratio(make_bundle()) == pytest.approx(-4 / 300)
    assert M.accruals_ratio(make_bundle(ocf_hist=[4.0] * 4)) == pytest.approx(4 / 300)


def test_fcf_ni_backing():
    assert M.fcf_ni_backing(make_bundle()) == pytest.approx(10.0 / 8.0)


def test_dilution_annual_negative_for_buybacks():
    d = M.dilution_annual(make_bundle())   # shares 101.5 -> 100 over 3 yrs
    assert d < 0


def test_fcf_stability_flat_is_zero():
    assert M.fcf_stability(make_bundle()) == pytest.approx(0.0)
    assert M.fcf_stability(make_bundle(fcf_hist=[10.0, 5.0, 15.0])) > 0.4


def test_coverage_and_leverage():
    assert M.interest_coverage(make_bundle()) == pytest.approx(8.0)
    assert M.net_debt_to_ebitda(make_bundle()) == pytest.approx(50 / 16)


def test_fatal_flags_complete_spec():
    # v0.1: coverage < 2x; repeated negative FCF. v0.2 draft adds F-Score and
    # Altman Z kill-gates (both were specced in ENGINE_DESIGN but uncoded).
    assert any('coverage' in f for f in M.fatal_flags(make_bundle(ebit=2.0)))
    assert any('FCF negative' in f
               for f in M.fatal_flags(make_bundle(fcf_hist=[-1, -1, 5, 5])))
    # deteriorating: profits falling, cash behind earnings, dilution,
    # leverage rising, CR falling, margins and turnover falling -> score 2/9
    dying = make_bundle(ni_hist=[2.0, 6.0, 8.0, 8.0],
                        ocf_hist=[1.0, 5.0, 6.0, 6.0],
                        shares_hist=[110.0, 105.0, 100.0, 100.0],
                        long_term_debt_hist=[70.0, 65.0, 60.0, 55.0],
                        current_assets_hist=[74.0, 76.0, 78.0, 80.0],
                        current_liab_hist=[56.0, 54.0, 52.0, 50.0],
                        revenue_hist=[80.0, 84.0, 86.0, 90.0],
                        cogs_hist=[62.0, 61.0, 62.0, 63.0],
                        ebit=2.0)
    assert M.fscore(dying)['score'] == 2
    assert any('F-Score' in f for f in M.fatal_flags(dying))
    assert any('Altman' in f for f in M.fatal_flags(
        make_bundle(mkt_cap=100.0, retained_earnings=-30.0, ebit=1.0)))


def test_fatal_flags_clean_bundle():
    assert M.fatal_flags(make_bundle()) == []
