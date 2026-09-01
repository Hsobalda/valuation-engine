import json

import pytest

from v02_draft import params as P
from v02_draft import risk, sizing, journal
from .conftest import make_bundle, make_inputs


# ---------------------------------------------------------------------------
# Risk panel
# ---------------------------------------------------------------------------
def test_panel_scores_and_reasons():
    b = make_bundle()
    panel = risk.risk_panel(b, {'EPV': 100.0, 'DCF': 102.0}, [])
    assert set(panel['panel']) == {'coverage', 'leverage', 'fcf_stability',
                                   'method_agreement', 'accruals', 'measurement'}
    for name, sub in panel['panel'].items():
        assert sub['score'] is None or 0 <= sub['score'] <= 100
        assert name in sub['reason']
    assert panel['composite'] is not None and 0 <= panel['composite'] <= 100
    # INVERTED scale (owner, 1 Sep 2026): 0 = far from danger, 100 = at it.
    # coverage 8.0x -> risk 10/100; flat FCF -> risk 0/100
    assert panel['panel']['coverage']['score'] == 10
    assert panel['panel']['fcf_stability']['score'] == 0


def test_panel_kill_gates_survive():
    panel = risk.risk_panel(make_bundle(), {}, ['interest coverage 1.2x < 2.0x'])
    assert 'interest coverage 1.2x < 2.0x' in panel['kill_gates']


def test_panel_flags_spread_cap():
    panel = risk.risk_panel(make_bundle(),
                            {'EPV': 100.0, 'DCF': 300.0}, [])
    assert 'capped' in panel['panel']['method_agreement']['reason']


def test_piecewise_anchors():
    assert risk._piecewise(risk._CURVES['coverage'], 2.3)[0] == 59  # ~60 risk
    assert risk._piecewise(risk._CURVES['coverage'], None)[0] is None
    assert risk._piecewise(risk._CURVES['leverage'], 0)[0] == 0     # unlevered
    assert risk._piecewise(risk._CURVES['leverage'], 6)[0] == 100   # max risk


def test_composite_respects_draft_weights():
    b = make_bundle()
    panel = risk.risk_panel(b, {'EPV': 100.0, 'DCF': 102.0}, [])
    got = panel['composite']
    exp = sum(P.RISK_WEIGHTS[k] * v['score'] for k, v in panel['panel'].items()
              if v['score'] is not None) / sum(P.RISK_WEIGHTS[k] for k, v
              in panel['panel'].items() if v['score'] is not None)
    assert got == round(exp)


# ---------------------------------------------------------------------------
# Sizing
# ---------------------------------------------------------------------------
def _ass(sym, verdict, mos, comp, sector='x'):
    return {'symbol': sym, 'verdict': verdict, 'mos': mos,
            'risk_composite': comp, 'sector': sector}


def test_sizing_caps_and_cash():
    rows = [_ass('A', 'STRONG BUY', 0.5, 90), _ass('B', 'STRONG BUY', 0.45, 85)]
    targets, actions, cash = sizing.size_positions(rows)
    assert targets['A'] <= P.FULL_POS and targets['B'] <= P.FULL_POS
    assert sum(targets.values()) + cash == pytest.approx(1.0, abs=0.001)
    assert cash >= 1 - P.MAX_DEPLOYED - 0.001


def test_cautious_cap_half():
    rows = [_ass('A', 'CAUTIOUS BUY', 0.2, 60), _ass('B', 'CAUTIOUS BUY', 0.2, 60)]
    targets, _, _ = sizing.size_positions(rows)
    assert all(v <= P.HALF_POS + 1e-9 for v in targets.values())


def test_pass_names_get_zero():
    targets, actions, _ = sizing.size_positions([_ass('A', 'PASS', -0.2, 50)])
    assert 'A' not in targets and actions['A'] in ('EXIT', 'STAY OUT')


def test_min_position_floor():
    rows = [_ass('A', 'STRONG BUY', 0.5, 95), _ass('B', 'BUY', 0.16, 20)]
    targets, actions, _ = sizing.size_positions(rows)
    for s, w in targets.items():
        assert w >= P.MIN_POSITION


def test_sector_cap():
    rows = [_ass('A', 'STRONG BUY', 0.5, 90, sector='Tobacco'),
            _ass('B', 'STRONG BUY', 0.49, 90, sector='Tobacco')]
    targets, _, _ = sizing.size_positions(rows)
    assert sum(targets.values()) <= 0.25 + 1e-6


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------
def test_journal_append_and_diff(tmp_path):
    path = str(tmp_path / 'j.jsonl')
    r1 = {'d': {'price': 100.0}, 'verdict': 'WATCH', 'mos': 0.10, 'fair': 111.0,
          'methods': {'EPV': 111.0}, 'risk_composite': 60, 'implied_growth': 0.02}
    diffs = journal.append_run(path, [('T', r1)], P)
    assert diffs[0][1] == 'ADDED'
    diffs = journal.append_run(path, [('T', r1)], P)
    assert diffs[0][1] == 'SAME'
    r2 = dict(r1, verdict='CAUTIOUS BUY')
    diffs = journal.append_run(path, [('T', r2)], P)
    assert diffs[0][1] == 'CHANGED'
    assert 'WATCH -> CAUTIOUS BUY' in diffs[0][2]
    rows = [json.loads(l) for l in open(path)]
    assert len(rows) == 3 and rows[0]['params'] == rows[-1]['params']


def test_params_hash_stable_and_sensitive():
    class Fake:  BARS = {'a': 1}
    h1 = journal.params_hash(Fake)
    assert h1 == journal.params_hash(Fake)
    Fake.BARS = {'a': 2}
    assert journal.params_hash(Fake) != h1
