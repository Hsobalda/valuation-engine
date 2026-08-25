# football_field.py -- valuation range chart ("football field") from engine results
# Everything is expressed as % of current price: the price line sits at 100%,
# and the horizontal gap between a bar and that line IS the margin of safety.

import matplotlib
matplotlib.use('Agg')                     # no display needed; save to file
import matplotlib.pyplot as plt
from engine_v01 import assess, WATCHLIST

results = [r for r in (assess(s) for s in WATCHLIST) if r['fair']]

fig, ax = plt.subplots(figsize=(10, 5))
ys = range(len(results))

for y, res in zip(ys, results):
    price = res['d']['price']
    vals = [v / price * 100 for v in res['methods'].values() if v]
    fair = res['fair'] / price * 100
    undervalued = fair >= 100
    colour = '#2e7d32' if undervalued else '#c62828'

    # bar spanning the method range
    ax.barh(y, max(vals) - min(vals), left=min(vals), height=0.45,
            color=colour, alpha=0.30, edgecolor=colour)
    # dot per method, diamond for consensus
    ax.scatter(vals, [y] * len(vals), color=colour, s=45, zorder=3, label=None)
    ax.scatter([fair], [y], marker='D', color=colour, s=90, zorder=4)
    # margin-of-safety annotation at the bar's edge
    ax.annotate(f"MoS {res['mos']*100:+.0f}%  [{res['verdict']}]",
                xy=(max(vals) + 4, y), va='center', fontsize=9, color=colour)

ax.axvline(100, color='black', lw=1.5)
ax.text(100, len(results) - 0.25, ' current price = 100%', fontsize=9, va='bottom')

ax.set_yticks(list(ys))
ax.set_yticklabels([r['d']['symbol'] for r in results])
ax.set_xlabel('valuation as % of current price  (right of the line = undervalued)')
ax.set_title('Valuation ranges vs price -- engine v0.1 (dots = methods, diamond = consensus)')
ax.set_xlim(0, max(220, max(max(v / r['d']['price'] * 100 for v in r['methods'].values() if v) for r in results) + 40))
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig('valuation_chart.png', dpi=150)
print('saved valuation_chart.png')
