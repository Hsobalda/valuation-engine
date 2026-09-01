"""sizing.py -- position sizing engine (spec Part B, COMPARISON item 2.2).

weight_i  ~  margin_of_safety_i / risk_i   (risk = composite/100 on the
             inverted scale where 100 = riskiest, floored at 0.10 so a
             perfect score cannot divide by zero)
then normalise across BUY-rated names, apply caps, keep the rest as cash.
Caps (8% / 4% / 25% sector / 2% min) are from the signed spec; the
normalisation and MAX_DEPLOYED fraction are DRAFT.
"""

from __future__ import annotations

from . import params as P

BUY_TIERS = {'STRONG BUY', 'BUY', 'CAUTIOUS BUY'}


def size_positions(assessments, current_weights=None):
    """assessments: list of dicts with keys symbol, verdict, mos, weight,
    risk_composite, sector. Returns (targets: {symbol: w}, actions, cash)."""
    current_weights = current_weights or {}
    candidates = [a for a in assessments if a['verdict'] in BUY_TIERS
                  and a.get('mos') is not None
                  and a.get('risk_composite') is not None]
    targets, actions = {}, {}
    if candidates:
        raw = {}
        for a in candidates:
            risk = max(a['risk_composite'] / 100.0, 0.10)   # 100 = riskiest
            cap = P.HALF_POS if a['verdict'] == 'CAUTIOUS BUY' else P.FULL_POS
            raw[a['symbol']] = max(a['mos'], 0.0) / risk, cap
        total = sum(r for r, _ in raw.values())
        if total > 0:
            deployed = 0.0
            # greedy cap application, largest raw weight first
            for sym, (r, cap) in sorted(raw.items(), key=lambda kv: -kv[1][0]):
                w = min(P.MAX_DEPLOYED * r / total, cap)
                targets[sym] = round(w, 4)
                deployed += w
            # sector cap (25%) -- trim violators, spillover stays in cash
            by_sector = {}
            for a in assessments:
                if a['symbol'] in targets:
                    by_sector.setdefault(a.get('sector') or 'n/a', []).append(a['symbol'])
            for sector, syms in by_sector.items():
                ssum = sum(targets[s] for s in syms)
                if ssum > 0.25:
                    scale = 0.25 / ssum
                    for s in syms:
                        targets[s] = round(targets[s] * scale, 4)
            # min position 2%: below that, not worth holding
            for s in list(targets):
                if targets[s] < P.MIN_POSITION:
                    actions[s] = f'{targets[s]*100:.1f}% < 2% floor -> 0 (not worth holding)'
                    del targets[s]

    for a in assessments:
        sym, v = a['symbol'], a['verdict']
        cur = current_weights.get(sym, 0.0)
        tgt = targets.get(sym, 0.0)
        if v not in BUY_TIERS:
            actions[sym] = 'EXIT' if cur > 0 else 'STAY OUT'
        elif tgt > cur + 0.01:
            actions[sym] = f'BUY MORE -> {tgt*100:.1f}%'
        elif tgt < cur - 0.01:
            actions[sym] = f'TRIM -> {tgt*100:.1f}%'
        else:
            actions[sym] = f'HOLD {tgt*100:.1f}%'
    cash = round(max(0.0, 1.0 - sum(targets.values())), 4)
    return targets, actions, cash
