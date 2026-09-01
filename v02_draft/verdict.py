"""verdict.py -- wrong-model gate (issue #4) + the v0.1 verdict ladder.

The ladder is bit-for-bit v0.1's (same constants, same ordering) with two
additions in front of it:
  1. WRONG TOOL refusal for banks/insurers and pre-profit names, replacing
     quietly unreliable output with an explicit reason.
  2. Optional risk-scaled MoS bars (VERSION_PLAN issue #5 extension),
     OFF by default so v0.1 behaviour is reproducible exactly.
"""

from __future__ import annotations

from . import params as P


def wrong_model(bundle):
    """Returns a reason string if this engine is the wrong tool, else None."""
    industry = (bundle.get('industry') or '').strip().lower()
    sector = (bundle.get('sector') or '').strip().lower()
    caught = (industry in P.WRONG_MODEL_SECTORS
              or industry.startswith(('banks', 'insurance'))
              or (sector == 'financial services'
                  and industry in P.WRONG_MODEL_SECTORS))
    if caught:
        return (f'wrong model: {bundle.get("industry") or bundle.get("sector")} '
                '(balance-sheet/capital-structure businesses; EPV/DCF on FCF '
                'and Graham on equity book are not meaningful -- use P/B vs '
                'tangible book and dividend-capacity analysis instead)')
    ni = [x for x in (bundle.get('ni_hist') or []) if x is not None]
    fcf = [x for x in (bundle.get('fcf_hist') or []) if x is not None]
    if ni and max(ni) <= 0 and fcf and max(fcf) <= 0:
        return ('wrong model: pre-profit name (no positive year of NI or FCF '
                'on record; zero-growth methods undefined -- v3 lever maths '
                'is the tool for this)')
    return None


def scaled_bar(bar, risk_composite, enabled=None):
    """Risk-scaled MoS bar. Disabled (or no composite) -> v0.1 bar unchanged.
    Composite is on the inverted scale (100 = riskiest), so the bar RISES
    with measured risk and is earned down by predictability."""
    if enabled is None:
        enabled = P.RISK_SCALED_BARS
    if not enabled or risk_composite is None:
        return bar
    t = (100 - risk_composite) / 100.0        # safety fraction
    factor = P.BAR_SCALE_WORST + t * (P.BAR_SCALE_BEST - P.BAR_SCALE_WORST)
    return bar * factor


def ladder(bundle, inputs, methods_valid, fair, mos, bull, bear, flags,
           risk_composite=None):
    """The v0.1 verdict ladder. Returns (verdict, weight, notes)."""
    notes = []
    price = bundle.get('price')
    bump = P.CYCLICAL_MOS_BUMP if inputs.get('cyclical') else 0.0
    method_mos = {k: (v - price) / v for k, v in methods_valid.items()}
    thesis_ok = inputs.get('thesis') and not inputs['thesis'].startswith('TODO')
    disagree = (max(methods_valid.values()) / min(methods_valid.values())
                if min(methods_valid.values()) > 0 else 99)
    scale = scaled_bar if risk_composite is not None else (lambda b, c: b)

    if flags or mos is None or mos < 0:
        return 'PASS', 0.0, notes
    if disagree > P.DISAGREE_CAP:
        notes.append(f'methods disagree {disagree:.1f}x > {P.DISAGREE_CAP} -- capped')
        return 'WATCH', 0.0, notes
    if not thesis_ok:
        notes.append('no thesis written -- verdict capped')
        return 'WATCH', 0.0, notes

    bar = scale(P.BARS['strong'], risk_composite)
    if mos >= bar + bump and sum(1 for m in method_mos.values() if m >= 0.30) >= 3:
        return 'STRONG BUY', P.FULL_POS, notes
    bar = scale(P.BARS['buy'], risk_composite)
    if mos >= bar + bump and sum(1 for m in method_mos.values() if m >= 0.20) >= 2:
        return 'BUY', P.FULL_POS, notes
    bar = scale(P.BARS['cautious'], risk_composite)
    if mos >= bar + bump and bull is not None and \
            (bull - price) >= P.ASYMMETRY * max(price - (bear or 0), 0.01 * price):
        notes.append('asymmetry test passed (bull upside >= 3x bear downside)')
        return 'CAUTIOUS BUY', P.HALF_POS, notes
    if mos >= 0:
        return 'WATCH', 0.0, notes
    return 'PASS', 0.0, notes
