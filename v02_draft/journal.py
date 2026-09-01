"""journal.py -- dated decision journal (VERSION_PLAN issue #7, item 2.1).

JSONL append per run: date, symbol, price, verdict, MoS, methods, risk
composite, parameters hash. Re-runs diff against the last entry per symbol so
verdict changes are surfaced, not silently overwritten. Nobody in the peer
set ships this; for a process-first tool it is the differentiator.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date


def params_hash(params_module):
    """Stable hash of the engine's parameter set, so a journal row is only
    comparable to rows with identical maths."""
    blob = json.dumps({k: getattr(params_module, k) for k in dir(params_module)
                       if k.isupper()}, sort_keys=True, default=str)
    return hashlib.md5(blob.encode()).hexdigest()[:10]


def _row(symbol, res, phash):
    return {
        'date': date.today().isoformat(),
        'symbol': symbol,
        'price': res['d'].get('price'),
        'verdict': res['verdict'],
        'mos': None if res.get('mos') is None else round(res['mos'], 4),
        'fair': None if res.get('fair') is None else round(res['fair'], 2),
        'methods': {k: (round(v, 2) if v else None)
                    for k, v in (res.get('methods') or {}).items()},
        'risk_composite': res.get('risk_composite'),
        'implied_growth': None if res.get('implied_growth') is None
                          else round(res['implied_growth'], 4),
        'params': phash,
    }


def last_entries(path):
    """{symbol: most recent row} from an existing journal."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                out[row['symbol']] = row          # later lines win
            except json.JSONDecodeError:
                continue
    return out


def append_run(path, results, params_module):
    """Append one row per symbol; returns [(symbol, change, detail)] diffs
    versus the previous run."""
    phash = params_hash(params_module)
    prev = last_entries(path)
    diffs = []
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        for sym, res in results:
            row = _row(sym, res, phash)
            f.write(json.dumps(row, default=str) + '\n')
            old = prev.get(sym)
            if old is None:
                diffs.append((sym, 'ADDED', f"first entry, verdict {row['verdict']}"))
            elif old['verdict'] != row['verdict']:
                diffs.append((sym, 'CHANGED',
                              f"{old['verdict']} -> {row['verdict']} "
                              f"(was price {old['price']}, MoS "
                              f"{old['mos']*100 if old['mos'] is not None else 'n/a'}%)"))
            elif old.get('params') != phash:
                diffs.append((sym, 'PARAMS', 'same verdict, parameters changed'))
            else:
                diffs.append((sym, 'SAME', ''))
    return diffs
