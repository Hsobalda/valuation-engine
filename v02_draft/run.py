"""run.py -- v0.2 draft CLI. Orchestrates the modules WITHOUT touching
engine_v01.py. Human inputs (moat/cyclical/thesis) are imported from the
shipped engine so there is one source of truth; new per-name config
(peer comps, sector) lives in watchlist_ext.py.

Usage (from repo root):
    python -m v02_draft.run                 # whole watchlist, offline-first
    python -m v02_draft.run T IMB.L         # subset
    python -m v02_draft.run --live          # fetch from Yahoo, cache snapshots
    python -m v02_draft.run --panels --grid # risk panels + sensitivity grids
    python -m v02_draft.run --journal journal/journal.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from statistics import median

from . import data, journal, metrics, params as P, risk, sizing, valuation as V
from .verdict import ladder, wrong_model
from .watchlist_ext import EXTENSIONS

# One source of truth for theses/moat/cyclicality: the shipped v0.1 watchlist.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine_v01 import WATCHLIST  # noqa: E402

SNAP_DIR = os.path.join(os.path.dirname(__file__), 'snapshots')


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------
def get_bundle(symbol, live=False):
    """Offline-first: snapshot if cached, else live if allowed."""
    snap = os.path.join(SNAP_DIR, f'{symbol.replace(".", "_")}.json')
    if not live and os.path.exists(snap):
        return data.load_snapshot(snap)
    if live:
        bundle = data.fetch_bundle(symbol)
        os.makedirs(SNAP_DIR, exist_ok=True)
        data.save_snapshot(bundle, snap)
        return bundle
    raise FileNotFoundError(
        f'no cached snapshot for {symbol}; run with --live once (or add a '
        f'fixture at {snap})')


def assess(symbol, bundle):
    inputs = dict(WATCHLIST.get(symbol, {}))
    inputs.update(EXTENSIONS.get(symbol, {}))
    r = V.discount_rate(inputs)
    price = bundle.get('price')
    res = {'d': bundle, 'inputs': inputs, 'rate': r, 'symbol': symbol}

    # --- FCF input provenance (issues #1, #8): always printed, never silent
    series, prov = V.owner_fcf_hist(bundle)
    adj, lease_paid, lease_applied = V.lease_adjust(series, bundle)
    fcf_note = prov + ('' if not lease_applied else
                       f'; lease-adjusted (deducted {lease_paid:,.0f} latest yr)')
    res['fcf_provenance'] = fcf_note
    res['lease_deduction'] = lease_paid if lease_applied else 0.0

    refuse = wrong_model(bundle)
    if refuse:
        res.update({'methods': {}, 'bull': None, 'fair': None, 'mos': None,
                    'verdict': 'WRONG TOOL', 'weight': 0.0, 'notes': [refuse],
                    'flags': [], 'risk_composite': None, 'implied_growth': None,
                    'breakeven_decline': None})
        return res

    g = V.hist_growth(adj)
    bear = V.dcf(bundle, V.clamp(g, -0.02, 0.02), r, fcf_series=adj)
    bull = V.dcf(bundle, V.clamp(g, 0.02, 0.10), r, fcf_series=adj)
    methods = {'EPV': V.epv(bundle, r, fcf_series=adj),
               'DCF(bear)': bear,
               'Graham': V.graham(bundle),
               'Multiples': V.multiples(bundle, inputs)}
    valid = {k: v for k, v in methods.items() if v is not None}
    res['methods'] = methods

    fair = median(valid.values()) if len(valid) >= 2 else None
    mos = (fair - price) / fair if (fair and price) else None
    flags = metrics.fatal_flags(bundle)
    panel = risk.risk_panel(bundle, valid, flags)

    res.update({'bull': bull, 'fair': fair, 'mos': mos, 'flags': flags,
                'risk': panel, 'risk_composite': panel['composite'],
                'implied_growth': V.implied_growth(bundle, r, price, fcf_series=adj),
                'implied_return': V.implied_required_return(bundle, price, fcf_series=adj),
                'breakeven_decline': V.breakeven_decline(bundle, r, price, fcf_series=adj),
                'terminal_share': V.terminal_share(bundle, V.clamp(g, -0.02, 0.02), r,
                                                  fcf_series=adj),
                'exit_mult_value': V.dcf_exit_multiple(
                    bundle, V.clamp(g, -0.02, 0.02), r, fcf_series=adj),
                'fcf_hist_used': adj, 'hist_growth': g})

    v, w, notes = ladder(bundle, inputs, valid, fair, mos, bull, bear, flags,
                         risk_composite=panel['composite'])
    res.update({'verdict': v, 'weight': w, 'notes': notes})
    return res


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def print_table(results):
    line = '-' * 118
    print(line)
    print(f"{'ticker':8} {'price':>10} {'fair val':>10} {'MoS':>7} {'impl.g':>7} "
          f"{'b/e dec':>8} {'risk':>5}  {'verdict':<13} {'wt':>4}  flags/notes")
    print(line)
    for sym, res in results:
        d = res['d']
        fair = f"{res['fair']:,.0f}" if res.get('fair') else '--'
        mos = f"{res['mos']*100:+.0f}%" if res.get('mos') is not None else '--'
        ig = res.get('implied_growth')
        igs = f'{ig*100:+.1f}%' if ig is not None else '--'
        bd = res.get('breakeven_decline')
        bds = f'{bd*100:+.1f}%' if bd is not None else '--'
        rc = res.get('risk_composite')
        rcs = f'{rc}' if rc is not None else '--'
        issues = '; '.join(res.get('flags', []) + res.get('notes', [])) or '-'
        print(f"{sym:8} {d.get('price') or 0:>10,.2f} {fair:>10} {mos:>7} "
              f"{igs:>7} {bds:>8} {rcs:>5}  {res['verdict']:<13} "
              f"{res.get('weight', 0)*100:>3.0f}%  {issues[:60]}")
    print(line)


def print_detail(res):
    d, res = res['d'], res
    print(f"\n{res['symbol']} -- {d.get('name')}  [{d.get('source')}"
          f"{', APPROXIMATE DEMO DATA' if d.get('approximate') else ''}]")
    for name, status, detail in data.audit(d):
        print(f"  [{status:>4}] {name}: {detail}")
    print(f"  FCF input: {res.get('fcf_provenance', 'n/a')}")
    if res.get('methods'):
        parts = ', '.join(f"{k}={v:,.0f}" if v else f"{k}=n/a"
                          for k, v in res['methods'].items())
        print(f"  methods (r={res['rate']*100:.0f}%): {parts}")
        mult, src = V.multiple_used(res['inputs'])
        print(f"  Method 4 multiple used: {mult}x ({src})")
        print(f"  bull DCF={res['bull'] and round(res['bull'], 2)}, "
              f"terminal share of bear DCF="
              f"{res['terminal_share'] and round(res['terminal_share'], 2)}, "
              f"exit-{P.EXIT_EBITDA_MULT}x cross-check="
              f"{res['exit_mult_value'] and round(res['exit_mult_value'], 2)}")
        ig, ir = res.get('implied_growth'), res.get('implied_return')
        bd = res.get('breakeven_decline')
        print(f"  reverse DCF: implied growth "
              f"{f'{ig*100:+.1f}%/yr' if ig is not None else 'n/a'}, implied "
              f"return at g=0 {f'{ir*100:.1f}%' if ir is not None else 'n/a'}, "
              f"break-even perpetual decline "
              f"{f'{bd*100:+.1f}%/yr' if bd is not None else 'n/a (no decline priced)'}")
    for n in res.get('notes', []):
        print(f"  note: {n}")
    if res.get('verdict') != 'WRONG TOOL':
        risk.print_panel(res['risk'])


def print_grid(res):
    g = V.clamp(res.get('hist_growth', 0.0), -0.02, 0.02)
    grid = V.sensitivity_grid(res['d'], g, fcf_series=res.get('fcf_hist_used'))
    price = res['d'].get('price')
    print(f"\n  sensitivity: bear-DCF fair value ({res['symbol']}, growth "
          f"{g*100:+.1f}%) -- cell shows fair / MoS vs price {price:,.2f}")
    terms = sorted(next(iter(grid.values())).keys())
    header = f"{'r / terminal g':>16}"
    print(header + ''.join(f'{t*100:>12.0f}%' for t in terms))
    for r, row in grid.items():
        cells = []
        for t in terms:
            v = row[t]
            if v is None or not price:
                cells.append(f"{'n/a':>12}")
            else:
                cells.append(f"{v:>7,.0f} {(v-price)/v*100:>4.0f}%")
        print(f"  {r*100:>15.0f}%" + ''.join(cells))


def main(argv=None):
    ap = argparse.ArgumentParser(prog='v02_draft')
    ap.add_argument('symbols', nargs='*')
    ap.add_argument('--live', action='store_true', help='fetch from Yahoo and cache snapshots')
    ap.add_argument('--panels', action='store_true', help='print per-name detail + risk panels')
    ap.add_argument('--grid', action='store_true', help='print sensitivity grids')
    ap.add_argument('--journal', default=None, help='JSONL journal path (append + diff)')
    ap.add_argument('--size', action='store_true', help='position sizing table')
    args = ap.parse_args(argv)

    symbols = args.symbols or list(WATCHLIST)
    results = []
    for sym in symbols:
        try:
            bundle = get_bundle(sym, live=args.live)
        except Exception as e:
            print(f'{sym}: SKIPPED ({e})')
            continue
        results.append((sym, assess(sym, bundle)))

    if not results:
        print('nothing to report.')
        return
    print('Valuation Engine v0.2 DRAFT -- '
          + ('live data' if args.live else 'cached snapshots (offline run)'))
    print_table(results)
    if args.panels:
        for _, res in results:
            print_detail(res)
    if args.grid:
        for _, res in results:
            if res.get('fcf_hist_used'):
                print_grid(res)
    if args.size:
        rows = [{'symbol': s, 'verdict': r['verdict'], 'mos': r.get('mos'),
                 'risk_composite': r.get('risk_composite'),
                 'sector': r['inputs'].get('sector')}
                for s, r in results]
        targets, actions, cash = sizing.size_positions(rows)
        print('\nPosition sizing (DRAFT: MoS / risk, caps 8/4%, sector 25%, min 2%)')
        for s, a in actions.items():
            print(f'  {s:8} {a}')
        print(f'  cash remainder: {cash*100:.0f}% (cash is a position)')
    if args.journal:
        diffs = journal.append_run(args.journal, results, P)
        print(f"\njournal: {args.journal}")
        for sym, change, detail in diffs:
            if change != 'SAME':
                print(f'  {sym:8} {change}: {detail}')
    print('\nDRAFT -- every new parameter needs owner sign-off (see params.py). '
          'engine_v01.py is untouched. Not financial advice.')


if __name__ == '__main__':
    main()
