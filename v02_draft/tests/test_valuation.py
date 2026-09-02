import pytest

from v02_draft import valuation as V
from .conftest import make_bundle


# ---------------------------------------------------------------------------
# Golden numbers: bundle has FCF 10/yr, shares 100, price 100, fx 1
# ---------------------------------------------------------------------------
def test_epv_golden():
    # owner FCF = OCF - min(capex, D&A) = 12 - 4 = 8/yr -> EPV = 8/0.10 = 80
    # per share: 80/100 = 0.80... values are in millions-scale units, so
    # EPV/share = (8/0.10)/100 = 0.8
    b = make_bundle()
    v = V.epv(b, 0.10)
    assert v == pytest.approx(0.8)

    # headline FCF variant: median 10 -> 1.0
    v2 = V.epv(b, 0.10, fcf_series=[10.0] * 4)
    assert v2 == pytest.approx(1.0)


def test_dcf_golden_gordon():
    b = make_bundle()
    # flat FCF 10, g=0, r=10%, terminal 2%:
    # PV = 10 * annuity(10y,10%) + 10*1.02/0.08 / 1.1^10
    import math
    ann = sum(1 / 1.1 ** y for y in range(1, 11))          # 6.144567...
    term = 10 * 1.02 / 0.08 / 1.1 ** 10
    expected = (10 * ann + term) / 100
    assert V.dcf(b, 0.0, 0.10, fcf_series=[10.0] * 4) == pytest.approx(expected)


def test_dcf_monotone_in_growth_and_rate():
    b = make_bundle()
    f = [10.0] * 4
    assert V.dcf(b, 0.02, 0.10, f) > V.dcf(b, 0.00, 0.10, f)
    assert V.dcf(b, 0.00, 0.09, f) > V.dcf(b, 0.00, 0.12, f)


def test_graham_golden():
    b = make_bundle()
    assert V.graham(b) == pytest.approx((22.5 * 6.0 * 50.0) ** 0.5)


def test_graham_disabled_high_pb():
    assert V.graham(make_bundle(pb=6.0)) is None
    assert V.graham(make_bundle(eps_ps=-1.0)) is None


def test_multiples_flat_and_peer():
    b = make_bundle()
    # median NI 8 / shares 100 = 0.08 eps -> x15 = 1.2
    assert V.multiples(b, {}) == pytest.approx(1.2)
    # owner-configured comps override: median of [10, 20, 30] = 20
    assert V.multiples(b, {'comps': {'pe': [10, 20, 30]}}) == pytest.approx(1.6)
    mult, src = V.multiple_used({'comps': {'pe': [10, 20, 30]}})
    assert mult == 20 and 'peer median' in src
    mult, src = V.multiple_used({})
    assert mult == 15 and 'flat' in src


# ---------------------------------------------------------------------------
# Reverse DCF (issue #2) -- roundtrips are the property tests that matter
# ---------------------------------------------------------------------------
def test_implied_growth_roundtrip():
    b = make_bundle()
    f = [10.0] * 4
    ig = V.implied_growth(b, 0.10, 1.0, fcf_series=f)
    assert ig is not None
    # plugging the implied growth back in must re-price the stock at 1.0
    assert V.dcf(b, ig, 0.10, fcf_series=f) == pytest.approx(1.0, rel=1e-6)


def test_implied_return_roundtrip():
    b = make_bundle()
    f = [10.0] * 4
    ir = V.implied_required_return(b, 1.0, fcf_series=f)
    assert ir is not None and 0.03 < ir < 0.30
    assert V.dcf(b, 0.0, ir, fcf_series=f) == pytest.approx(1.0, rel=1e-6)


def test_breakeven_decline_roundtrip():
    b = make_bundle()
    f = [10.0] * 4          # flat FCF 10 -> equity value at r=10%: 100 -> 1.0/share
    bd = V.breakeven_decline(b, 0.10, 0.6, fcf_series=f)
    assert bd is not None and bd < 0
    val = V.perpetual_value(10.0, 0.10, bd) / b['shares']
    assert val == pytest.approx(0.6, rel=1e-6)


def test_breakeven_decline_none_when_no_decline_priced():
    b = make_bundle()
    # price above the flat-FCF perpetual value (1.0) -> nothing to solve
    assert V.breakeven_decline(b, 0.10, 1.5, fcf_series=[10.0] * 4) is None


def test_decliner_matches_imb_thesis_shape():
    """The IMB maths: flat actual FCF, price far below flat value ->
    break-even decline must be negative and plausibly mid-single-digit."""
    # FCF in GBP millions (3.17bn -> 3170), shares 757m, price 2511p
    f = [3170.0, 2890.0, 2950.0, 3170.0]
    b = make_bundle(fcf_hist=f, shares=757.0, fx=100.0)
    bd = V.breakeven_decline(b, 0.10, 2511.0, fcf_series=f)
    # hand maths: 3060*(1+d)/(0.10-d) = 2511*757/100 -> d = -5.3%
    assert bd == pytest.approx(-0.053, abs=0.005)


# ---------------------------------------------------------------------------
# Owner earnings + IFRS 16 (issues #1, #8)
# ---------------------------------------------------------------------------
def test_owner_earnings_floor_at_capex_below_da():
    # capex 2 < D&A 5: owner FCF = 12 - min(2,5) = 10 (maintenance mode)
    b = make_bundle(capex_hist=[2.0] * 4, da_hist=[5.0] * 4)
    series, prov = V.owner_fcf_hist(b)
    assert series[0] == pytest.approx(10.0)
    assert 'owner earnings' in prov


def test_owner_earnings_deducts_growth_capex():
    # capex 9 > D&A 4: owner FCF = 12 - min(9,4) = 8 (growth spend capped at D&A)
    b = make_bundle(capex_hist=[9.0] * 4, da_hist=[4.0] * 4)
    series, _ = V.owner_fcf_hist(b)
    assert series[0] == pytest.approx(8.0)


def test_lease_adjustment_deducts_principal():
    b = make_bundle(lease_principal_hist=[-1.5, -1.4, -1.3, -1.2])
    adj, ded, applied = V.lease_adjust([10.0] * 4, b)
    assert applied and ded == pytest.approx(1.5)
    assert adj[0] == pytest.approx(8.5)


def test_sensitivity_grid_monotone():
    b = make_bundle()
    grid = V.sensitivity_grid(b, 0.0, rates=[0.09, 0.11], terminals=[0.01, 0.03],
                              fcf_series=[10.0] * 4)
    assert grid[0.09][0.03] > grid[0.11][0.01]   # both effects push value up
    assert grid[0.09][0.03] > grid[0.09][0.01]   # higher terminal -> higher value


def test_terminal_share_in_range():
    b = make_bundle()
    ts = V.terminal_share(b, 0.0, 0.10, fcf_series=[10.0] * 4)
    assert ts is not None and 0.0 < ts < 1.0


def test_exit_multiple_crosscheck_positive():
    b = make_bundle()   # EBITDA 16, net debt 50
    v = V.dcf_exit_multiple(b, 0.0, 0.10, exit_mult=7.0, fcf_series=[10.0] * 4)
    assert v is not None and v > 0
    # zero net debt must raise the equity value
    b2 = make_bundle(total_debt=10.0, cash=10.0)
    v3 = V.dcf_exit_multiple(b2, 0.0, 0.10, exit_mult=7.0, fcf_series=[10.0] * 4)
    assert v3 > v


def test_owner_earnings_handles_yahoo_negative_capex():
    """Regression, live run 2 Sep 2026: Yahoo returns capex NEGATIVE; the
    deduction must use its magnitude. min(-20, 20) added capex back and
    doubled fair values (T ~$58 vs ~$30)."""
    b = make_bundle(capex_hist=[-4.0] * 4, da_hist=[-4.0] * 4)
    series, prov = V.owner_fcf_hist(b)
    assert series[0] == pytest.approx(8.0)      # 12 - min(4,4), NOT 12+4
    assert 'owner earnings' in prov
