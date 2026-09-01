# football_field.py -- valuation range chart ("football field") from engine results
# Everything is expressed as % of current price: the price line sits at 100%,
# and the horizontal gap between a bar and that line IS the margin of safety.
#
# Data source: live engine run if the network allows it, otherwise the last
# saved report cards in reports/ (same numbers, just frozen at generation time).

import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')                     # no display needed; save to file
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

GREEN = '#2d6a4f'   # undervalued
RED   = '#9d4141'   # overvalued
INK   = '#333333'
GREY  = '#8a8a8a'

NAMES = {
    'IMB.L': 'Imperial Brands', 'KGF.L': 'Kingfisher', 'TSCO.L': 'Tesco',
    'EZJ.L': 'easyJet', 'T': 'AT&T', 'PEP': 'PepsiCo', 'SPOT': 'Spotify',
}


def results_live():
    """Run the engine against live data (raises if the feed is unreachable)."""
    from engine_v01 import assess, WATCHLIST
    return [r for r in (assess(s) for s in WATCHLIST) if r['fair']]


def results_from_reports(folder='reports'):
    """Rebuild the same result dicts from the saved report cards."""
    results = []
    for path in sorted(Path(folder).glob('*.md')):
        text = path.read_text()
        price = re.search(r'\| Price \| ([\d,.]+)', text)
        cons = re.search(r'Consensus \(median\): ([\d,.]+)', text)
        mos = re.search(r'margin of safety ([+-]?\d+)%', text)
        verdict = re.search(r'\*\*Verdict: ([A-Z ]+)\*\*', text)
        if not (price and cons and mos and verdict):
            continue
        methods = {}
        for m in re.finditer(r'\| (EPV|DCF\(bear\)|Graham|Multiples) \| ([\d,.]+|n/a) \|', text):
            if m.group(2) != 'n/a':
                methods[m.group(1)] = float(m.group(2).replace(',', ''))
        results.append({
            'd': {'symbol': path.stem.replace('_', '.'),
                  'price': float(price.group(1).replace(',', ''))},
            'methods': methods,
            'fair': float(cons.group(1).replace(',', '')),
            'mos': int(mos.group(1)) / 100,
            'verdict': verdict.group(1).strip(),
        })
    return results


def draw(results, outfile='valuation_chart.png'):
    # most undervalued at the top, worst at the bottom
    results = sorted(results, key=lambda r: r['mos'])
    n = len(results)

    fig, ax = plt.subplots(figsize=(11, 0.85 * n + 1.9))

    xmax = 100
    for y, res in enumerate(results):
        price = res['d']['price']
        vals = [v / price * 100 for v in res['methods'].values() if v]
        fair = res['fair'] / price * 100
        colour = GREEN if fair >= 100 else RED
        lo, hi = min(vals), max(vals)

        # bar spanning the method range, one dot per method, diamond = consensus
        ax.barh(y, hi - lo, left=lo, height=0.42, color=colour, alpha=0.15, zorder=2)
        ax.plot([lo, hi], [y, y], color=colour, lw=1.2, alpha=0.55, zorder=3)
        ax.scatter(vals, [y] * len(vals), color=colour, s=34,
                   edgecolor='white', linewidth=0.8, zorder=4)
        ax.scatter([fair], [y], marker='D', color=colour, s=95,
                   edgecolor='white', linewidth=1.1, zorder=5)

        # margin of safety + verdict at the bar's edge
        ax.annotate(f"{res['mos']*100:+.0f}%  {res['verdict']}",
                    xy=(hi + 5, y), va='center', fontsize=8.5,
                    color=colour, fontweight='bold')
        xmax = max(xmax, hi)

    # today's price = 100%
    ax.axvline(100, color=INK, lw=1.2, ls=(0, (5, 3)), zorder=1)

    ax.set_yticks(range(n))
    ax.set_yticklabels([f"{NAMES.get(r['d']['symbol'], '')}  ({r['d']['symbol']})"
                        for r in results], fontsize=9.5, color=INK)
    ax.set_xlim(0, xmax + 42)
    ax.set_ylim(-0.7, n - 0.3)
    ax.xaxis.set_major_formatter(lambda x, _: f'{x:.0f}%')
    ax.tick_params(axis='x', labelsize=9, colors=GREY)
    ax.tick_params(length=0)
    ax.grid(axis='x', color=GREY, alpha=0.25, lw=0.7, ls=':')
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(GREY)

    ax.set_title('What is it worth vs. what it costs',
                 loc='left', fontsize=14, fontweight='bold', color=INK, pad=34)
    ax.annotate('Four valuation methods per company, as % of today\u2019s price '
                '\u2014 right of the dashed line = undervalued',
                xy=(0, 1), xycoords='axes fraction', xytext=(0, 14),
                textcoords='offset points', fontsize=9.5, color=GREY)

    ax.legend(handles=[
        Line2D([], [], marker='o', ls='none', color=GREY, markersize=6,
               markeredgecolor='white', label='single method'),
        Line2D([], [], marker='D', ls='none', color=GREY, markersize=8,
               markeredgecolor='white', label='consensus (median)'),
        Line2D([], [], color=INK, lw=1.2, ls=(0, (5, 3)), label='today\u2019s price'),
    ], loc='lower right', frameon=False, fontsize=8.5, handletextpad=0.5)

    fig.text(0.01, 0.012, 'engine v0.1 \u00b7 gap between diamond and dashed line = margin of safety '
             '\u00b7 full method breakdowns in reports/', fontsize=7.5, color=GREY)

    plt.tight_layout(rect=(0, 0.03, 1, 1))
    plt.savefig(outfile, dpi=150)
    print(f'saved {outfile}')


if __name__ == '__main__':
    try:
        results = results_live()
        print('data: live')
    except Exception as e:
        results = results_from_reports()
        print(f'data: saved report cards (live feed unavailable: {type(e).__name__})')
    draw(results)
