import pytest

from v02_draft import params as P
from v02_draft.verdict import ladder, wrong_model, scaled_bar
from .conftest import make_bundle, make_inputs


def run_ladder(mos_target, method_mos=0.35, fair=100.0, **kw):
    """Bundle/inputs crafted so MoS = (fair-price)/fair hits mos_target with
    every method at method_mos."""
    price = fair * (1 - mos_target)
    b = make_bundle(price=price)
    inputs = make_inputs(**kw)
    methods = {m: fair / (1 - method_mos) * (1 - method_mos) for m in
               ('EPV', 'DCF(bear)', 'Graham', 'Multiples')}
    methods = {m: fair for m in methods}       # all methods equal -> spread 1.0
    bull = fair * 2.5
    return ladder(b, inputs, methods, fair, mos_target, bull, fair, [], None)


def test_bars_exactly():
    # MoS exactly at each bar with all methods equal: >= applies
    v, w, _ = run_ladder(0.50)
    assert v == 'STRONG BUY' and w == P.FULL_POS
    v, w, _ = run_ladder(0.30)
    assert v == 'BUY' and w == P.FULL_POS
    # cautious needs the asymmetry test; bull 2.5x fair vs price 0.85*fair:
    # upside 250-85=165 >= 3*(85-100->0)=0 -> passes
    v, w, notes = run_ladder(0.15)
    assert v == 'CAUTIOUS BUY' and w == P.HALF_POS
    assert any('asymmetry' in n for n in notes)


def test_below_bar_is_watch():
    v, w, _ = run_ladder(0.149)
    assert v == 'WATCH' and w == 0.0
    v, w, _ = run_ladder(0.299)
    assert v in ('BUY', 'CAUTIOUS BUY')   # 29.9% still clears cautious bar


def test_negative_mos_is_pass():
    v, _, _ = run_ladder(-0.01)
    assert v == 'PASS'


def test_flags_force_pass():
    fair, price = 100.0, 50.0
    v, _, _ = ladder(make_bundle(price=price), make_inputs(),
                     {m: fair for m in ('EPV', 'DCF')}, fair, 0.50,
                     200.0, 100.0, ['interest coverage 1.2x < 2.0x'], None)
    assert v == 'PASS'


def test_disagreement_caps_watch():
    fair, price = 100.0, 50.0
    methods = {'EPV': 100.0, 'DCF(bear)': 300.0, 'Graham': 101.0, 'Multiples': 102.0}
    v, _w, notes = ladder(make_bundle(price=price), make_inputs(), methods,
                          fair, 0.50, 200.0, 100.0, [], None)
    assert v == 'WATCH'
    assert any('disagree' in n for n in notes)


def test_no_thesis_caps_watch():
    fair, price = 100.0, 50.0
    v, _w, notes = ladder(make_bundle(price=price),
                          make_inputs(thesis='TODO: write me'),
                          {m: fair for m in ('EPV', 'DCF')}, fair, 0.50, 200.0,
                          100.0, [], None)
    assert v == 'WATCH'
    assert any('no thesis' in n for n in notes)


def test_cyclical_bump():
    # 35% MoS would be BUY for a stable name, cyclical needs 40% -> WATCH
    v_stable, _, _ = run_ladder(0.35, cyclical=False)
    v_cyc, _, _ = run_ladder(0.35, cyclical=True)
    assert v_stable == 'BUY'
    assert v_cyc == 'CAUTIOUS BUY'      # 35-10=25 -> cautious band w/ asymmetry


def test_asymmetry_gate_blocks_cautious():
    fair, price = 100.0, 85.0
    # bull barely above price (upside 2) vs 3x real bear downside (3x25=75)
    # -> asymmetry fails -> WATCH, not CAUTIOUS BUY
    v, _, _ = ladder(make_bundle(price=price), make_inputs(),
                     {m: fair for m in ('EPV', 'DCF')}, fair, 0.15,
                     87.0, 60.0, [], None)
    assert v == 'WATCH'


def test_method_count_requirements():
    # BUY needs >=2 methods at >=20% MoS each; single-method edge
    fair, price = 100.0, 60.0
    methods = {'EPV': 100.0, 'DCF(bear)': 100.0, 'Graham': 60.01, 'Multiples': 60.01}
    v, _, _ = ladder(make_bundle(price=price), make_inputs(), methods, fair, 0.40,
                     200.0, 100.0, [], None)
    assert v == 'BUY'   # two methods at 40% >= 20%


# ---------------------------------------------------------------------------
# Wrong-model refusal (issue #4)
# ---------------------------------------------------------------------------
def test_wrong_model_bank():
    reason = wrong_model(make_bundle(industry='Banks - Regional',
                                     sector='Financial Services'))
    assert reason is not None and 'wrong model' in reason
    reason2 = wrong_model(make_bundle(industry='Credit Services',
                                      sector='Financial Services'))
    assert reason2 is not None and 'wrong model' in reason2


def test_wrong_model_insurer():
    assert wrong_model(make_bundle(industry='Insurance - Life')) is not None


def test_wrong_model_preprofit():
    r = wrong_model(make_bundle(ni_hist=[-1.0, -2.0, -3.0, -4.0],
                                fcf_hist=[-1.0, -1.0, 0.0, -2.0]))
    assert r is not None and 'pre-profit' in r


def test_wrong_model_clean():
    assert wrong_model(make_bundle()) is None


# ---------------------------------------------------------------------------
# Risk-scaled bars: OFF by default (v0.1 parity), explicit when on
# ---------------------------------------------------------------------------
def test_scaled_bar_off_by_default():
    assert P.RISK_SCALED_BARS is False
    assert scaled_bar(0.30, 50) == 0.30           # disabled -> unchanged


def test_scaled_bar_on():
    # inverted risk scale: 100 = riskiest -> bar scaled UP by 1.33;
    # 0 = safest -> bar earned down to x0.83
    assert scaled_bar(0.30, 100, enabled=True) == pytest.approx(0.30 * 1.33)
    assert scaled_bar(0.30, 0, enabled=True) == pytest.approx(0.30 * 0.83)
    assert scaled_bar(0.30, 50, enabled=True) == pytest.approx(0.30 * 1.08)
