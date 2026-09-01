"""End-to-end on the demo snapshots (offline). Verifies the whole stack runs
and reproduces the shape of the owner's committed v0.1 report cards."""

import os

import pytest

from v02_draft import run

SNAPS = os.path.join(os.path.dirname(__file__), '..', 'snapshots')


def _assess(symbol, fixture):
    path = os.path.join(SNAPS, fixture)
    if not os.path.exists(path):
        pytest.skip('demo snapshot not present')
    from v02_draft.data import load_snapshot
    return run.assess(symbol, load_snapshot(path))


def test_T_end_to_end():
    res = _assess('T', 'T.json')
    # methods reproduce the committed report card within demo-data tolerance
    m = res['methods']
    assert m['EPV'] == pytest.approx(28.6, abs=2.0)
    assert m['Graham'] == pytest.approx(33.0, abs=1.5)
    assert m['Multiples'] == pytest.approx(27.7, abs=2.0)
    assert res['fair'] == pytest.approx(30.4, abs=2.5)
    assert res['implied_growth'] == pytest.approx(-0.025, abs=0.02)
    # completing the specced kill-gates has a visible consequence: T's
    # buyback-shrunken retained earnings push Altman Z into the flag zone,
    # so the DRAFT verdict hardens from CAUTIOUS BUY to PASS. Owner must
    # sign off on this (or exempt equity-return programs) -- the draft's
    # job is to surface it, not hide it.
    assert any('Altman' in f for f in res['flags'])
    assert res['verdict'] == 'PASS'


def test_IMB_end_to_end():
    res = _assess('IMB.L', 'IMB_L.json')
    m = res['methods']
    # EPV now uses owner earnings (OCF - min(capex, D&A) ~2.955bn median), so
    # it lands ~3904p vs the v0.1 headline-FCV EPV 4034p: the input upgrade
    # moves the number, and the provenance string says why.
    assert m['EPV'] == pytest.approx(3904, abs=80)
    assert 'owner earnings' in res['fcf_provenance']
    assert m['Graham'] == pytest.approx(1554, rel=0.02)
    # spread > 2.5 -> capped at WATCH, exactly like the committed report
    assert res['verdict'] == 'WATCH'
    assert any('disagree' in n for n in res['notes'])
    # reverse DCF: report card said -8.4%/yr implied growth
    assert res['implied_growth'] == pytest.approx(-0.084, abs=0.02)
    # decliner mode: break-even perpetual decline in the -4..-7% band
    # (owner's hand maths said -5.3% on slightly different inputs)
    assert res['breakeven_decline'] is not None
    assert -0.075 < res['breakeven_decline'] < -0.035


def test_cli_offline(capsys):
    run.main(['T', 'IMB.L', '--panels', '--grid', '--size'])
    out = capsys.readouterr().out
    assert 'Valuation Engine v0.2 DRAFT' in out
    assert 'T ' in out and 'IMB.L' in out
    assert 'sensitivity' in out
    assert 'cash remainder' in out
    assert 'composite' in out
