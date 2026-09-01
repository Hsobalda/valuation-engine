"""risk.py -- the RISK PANEL (VERSION_PLAN issue #5, COMPARISON item 1.2).

Design (owner, 25 Aug 2026): continuous subscores instead of cliff edges.
Each metric scores 0-100 by DISTANCE FROM DANGER, carries a plain-language
reason, and is individually inspectable. No weights at display level.

A composite is computed ONLY where a decision needs an ordering (position
sizing, ranking) and must always be shown WITH the panel. Absolute kill-gates
(fatal flags) survive underneath: they cannot be averaged away.
"""

from __future__ import annotations

from . import metrics as M
from . import params as P


def _piecewise(pts, x):
    """Piecewise-linear score through (value, score) anchor points."""
    if x is None:
        return None, 'no data'
    pts = sorted(pts)
    if x <= pts[0][0]:
        return pts[0][1], None
    if x >= pts[-1][0]:
        return pts[-1][1], None
    for (x0, s0), (x1, s1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            return round(s0 + t * (s1 - s0)), None
    return None, 'unreachable'


def _fmt(x, pct=False, mult=False):
    if x is None:
        return 'n/a'
    if pct:
        return f'{x*100:.1f}%'
    if mult:
        return f'{x:.2f}x'
    return f'{x:,.0f}'


# Anchor curves: value -> score (100 = far from danger, 0 = at/past danger).
# DRAFT -- owner sign-off required for every curve.
_CURVES = {
    'coverage':     [(-9, 0), (1, 5), (2, 35), (3, 55), (5, 75), (8, 90), (12, 100)],
    'leverage':     [(0, 100), (1, 85), (2, 70), (3, 50), (4, 25), (5, 0), (9, 0)],
    'fcf_stability': [(0.0, 100), (0.15, 80), (0.30, 60), (0.50, 35), (0.75, 15), (1.0, 0)],
    'method_agreement': [(1.0, 100), (1.5, 75), (2.0, 45), (2.5, 20), (3.5, 0)],
    'accruals':     [(-0.05, 100), (0.0, 85), (0.03, 65), (0.06, 45), (0.10, 20), (0.15, 0)],
    'measurement':  [(5, 100), (4, 80), (3, 55), (2, 25), (1, 0)],
}


def subscore(name, value, reason_fmt):
    score, err = _piecewise(_CURVES[name], value)
    if err:
        return {'score': None, 'value': None,
                'reason': f'{name}: no data -- subscore excluded'}
    return {'score': score, 'value': value,
            'reason': f'{name}: {reason_fmt(value)} -> {score}/100'}


def risk_panel(bundle, methods_valid, flags):
    """methods_valid: {method: fair_value} of the valid methods (for the
    agreement subscore). flags: fatal flags list (kill-gates)."""
    panel = {}

    cov = M.interest_coverage(bundle)
    panel['coverage'] = subscore('coverage', cov, lambda v: f'interest coverage {_fmt(v, mult=True)}')
    if cov is not None and cov < P.COVERAGE_KILL:
        panel['coverage']['reason'] += ' [KILL-GATE: < 2x]'

    lev = M.net_debt_to_ebitda(bundle)
    if lev is None:
        # D/E anchors differ from net-debt/EBITDA anchors; refuse to fake a
        # comparable score. The panel prefers an honest gap to a wrong number.
        panel['leverage'] = {'score': None, 'value': None,
                             'reason': 'leverage: net debt/EBITDA unavailable '
                                       '(EBITDA missing) -- subscore excluded'}
    else:
        panel['leverage'] = subscore('leverage', lev,
                                     lambda v: f'net debt/EBITDA {_fmt(v, mult=True)}')

    stab = M.fcf_stability(bundle)
    panel['fcf_stability'] = subscore('fcf_stability', stab,
                                      lambda v: f'FCF coefficient of variation {_fmt(v)}')

    vals = [v for v in (methods_valid or {}).values() if v]
    spread = (max(vals) / min(vals)) if len(vals) >= 2 and min(vals) > 0 else None
    panel['method_agreement'] = subscore('method_agreement', spread,
                                         lambda v: f'method spread {_fmt(v, mult=True)}')
    if spread is not None and spread > P.DISAGREE_CAP:
        panel['method_agreement']['reason'] += ' [verdict already capped at WATCH]'

    acc = M.accruals_ratio(bundle)
    panel['accruals'] = subscore('accruals', acc,
                                 lambda v: f'accruals (NI-OCF)/TA {_fmt(v, pct=True)}')

    yrs = len(bundle.get('fcf_hist') or [])
    panel['measurement'] = subscore('measurement', yrs,
                                    lambda v: f'{int(v)} yrs of FCF history')

    available = {k: v['score'] for k, v in panel.items() if v['score'] is not None}
    composite = None
    if available:
        wsum = sum(P.RISK_WEIGHTS.get(k, 0) for k in available)
        if wsum > 0:
            composite = round(sum(P.RISK_WEIGHTS[k] * s for k, s in available.items())
                              / wsum)
    return {'panel': panel, 'composite': composite,
            'kill_gates': list(flags or []),
            'note': 'panel for judgement; composite only ranks; gates cannot '
                    'be averaged away'}


def print_panel(risk, indent='  '):
    for name, sub in risk['panel'].items():
        score = 'n/a' if sub['score'] is None else f"{sub['score']:>3}"
        print(f"{indent}{score}/100  {sub['reason']}")
    print(f"{indent}composite {risk['composite']}/100 (weights DRAFT, ordering only)")
    if risk['kill_gates']:
        for g in risk['kill_gates']:
            print(f"{indent}KILL-GATE: {g}")
