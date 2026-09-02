"""note.py -- analyst-style research notes from v0.2 draft assessments.

Turns the engine's output into a one-page pitch document per company:
rating masthead, football field, what-the-market-is-pricing box, valuation
table with provenance, risk heat panel, sensitivity grid, signed thesis,
verdict trace with price triggers. Self-contained HTML (inline CSS, no
external assets): opens in any browser, prints to A4/PDF.

Usage (offline-first, same snapshot logic as run.py):
    python -m v02_draft.note T IMB.L          -> notes/<SYM>_note.html + index
    python -m v02_draft.note --live T         -> refresh snapshot, then build
"""

from __future__ import annotations

import argparse
import os
from datetime import date

from . import metrics as M
from . import params as P
from . import risk as RISK
from . import render as RENDER
from . import run
from . import valuation as V

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'docs')

# ---------------------------------------------------------------------------
# palette / tone
# ---------------------------------------------------------------------------
RATING_COLOR = {
    'STRONG BUY':  '#14532d',
    'BUY':         '#1b7a4a',
    'CAUTIOUS BUY':'#b07a1f',
    'WATCH':       '#5b6570',
    'PASS':        '#9b3b30',
    'WRONG TOOL':  '#6b4c9a',
    'NO DATA':     '#5b6570',
}


def fmt_px(v, ccy):
    """Per-share price in the bundle's price currency."""
    if v is None:
        return 'n/a'
    if ccy == 'GBp':
        return f'{v:,.0f}p'
    symbol = {'USD': '$', 'EUR': '€', 'GBP': '£'}.get(ccy, '')
    return f'{symbol}{v:,.2f}' if symbol else f'{v:,.2f} {ccy}'


def fmt_big(v):
    if v is None:
        return 'n/a'
    for div, suf in ((1e12, 'tn'), (1e9, 'bn'), (1e6, 'm')):
        if abs(v) >= div:
            return f'{v/div:,.1f}{suf}'
    return f'{v:,.0f}'


def pct(x, signed=True, digits=1):
    if x is None:
        return 'n/a'
    return f'{x*100:+.{digits}f}%' if signed else f'{x*100:.{digits}f}%'


def heat(score):
    """Colour class for a 0-100 RISK score (higher = riskier = redder)."""
    if score is None:
        return 'grey'
    if score >= 70:
        return 'bad'
    if score >= 50:
        return 'warn'
    if score >= 35:
        return 'ok'
    return 'good'


CSS = """
:root { --ink:#1a2332; --paper:#faf9f7; --line:#d8d5d0; --grey:#6b7280; }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'Segoe UI',system-ui,-apple-system,Arial,sans-serif;
       color:var(--ink); background:#eceae6; font-size:14px; line-height:1.45; }
.page { max-width:980px; margin:18px auto; background:var(--paper);
        border:1px solid var(--line); box-shadow:0 2px 14px rgba(0,0,0,.08); }
.masthead { display:flex; justify-content:space-between; align-items:center;
            padding:8px 22px; background:var(--ink); color:#e8e6e1; font-size:11px;
            letter-spacing:.14em; text-transform:uppercase; }
.masthead b { color:#fff; }
.banner { background:#f4e9d2; color:#7a5a12; padding:7px 22px; font-size:12px; }
.head { display:flex; justify-content:space-between; align-items:flex-start;
        gap:18px; padding:20px 22px 14px; border-bottom:3px solid var(--ink); }
.head h1 { font-family:Georgia,'Times New Roman',serif; font-size:27px; font-weight:700; }
.head .sub { color:var(--grey); font-size:12.5px; margin-top:3px; }
.ratingbox { text-align:right; min-width:240px; }
.rating { display:inline-block; color:#fff; font-weight:700; font-size:15px;
          letter-spacing:.06em; padding:6px 16px; border-radius:3px; }
.pxrow { margin-top:8px; font-size:13px; color:#374151; }
.pxrow b { font-size:15px; color:var(--ink); }
.grid { display:grid; grid-template-columns:1fr 292px; gap:0; }
.left { padding:16px 20px; border-right:1px solid var(--line); }
.right { padding:16px 18px; background:#f4f3f0; }
h2 { font-family:Georgia,serif; font-size:15px; margin:18px 0 8px; 
     padding-bottom:3px; border-bottom:1px solid var(--line); }
h2:first-child { margin-top:0; }
table { width:100%; border-collapse:collapse; font-size:12.5px; }
th { text-align:left; color:var(--grey); font-weight:600; font-size:11px;
     text-transform:uppercase; letter-spacing:.05em; padding:4px 6px;
     border-bottom:1px solid var(--line); }
td { padding:4.5px 6px; border-bottom:1px solid #eceae6; vertical-align:top; }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
.pos { color:#1b7a4a; font-weight:600; } .neg { color:#9b3b30; font-weight:600; }
.note { color:var(--grey); font-size:11.5px; }
/* football field */
.ff { position:relative; }
.ff .row { display:grid; grid-template-columns:92px 1fr; gap:8px; align-items:center;
           margin:7px 0; }
.ff .lbl { font-size:11.5px; color:#374151; text-align:right; }
.ff .track { position:relative; height:16px; }
.ff .axis { position:relative; height:16px; grid-column:2; }
.ff .bar { position:absolute; top:4px; height:8px; border-radius:4px;
           background:#1b7a4a33; border-left:2px solid #1b7a4a88;
           border-right:2px solid #1b7a4a88; }
.ff .dot { position:absolute; top:2.5px; width:11px; height:11px; border-radius:50%;
           background:#1b7a4a; border:1.5px solid #fff; box-shadow:0 0 0 1px #1b7a4a;
           transform:translateX(-50%); }
.ff .diamond { position:absolute; top:0.5px; width:12px; height:12px;
               background:var(--ink); border:1.5px solid #fff; transform:translateX(-50%) rotate(45deg); }
.ff .priceline { position:absolute; top:14px; bottom:0; width:0;
                 border-left:2px dashed var(--ink); transform:translateX(-1px); }
.ff .plabel { position:absolute; top:0; font-size:9.5px; font-weight:600;
              color:var(--ink); background:var(--paper); padding:0 4px;
              border:1px solid var(--line); border-radius:2px;
              transform:translateX(-50%); white-space:nowrap; }
.ff .overlay { position:absolute; left:100px; right:0; top:-16px; bottom:0;
               pointer-events:none; z-index:3; }
.ff .tick { position:absolute; top:0; font-size:9.5px; color:var(--grey);
            transform:translateX(-50%); }
/* heat chips + boxes */
.chip { display:inline-flex; align-items:center; gap:7px; padding:4px 9px;
        border-radius:3px; margin:2.5px 2px; font-size:12px; background:#fff;
        border:1px solid var(--line); }
.chip .score { font-weight:700; font-size:12.5px; width:34px; text-align:center;
               color:#fff; border-radius:2px; padding:1.5px 0; }
.good{background:#1b7a4a;} .ok{background:#7a9a1b;} .warn{background:#c07f1b;}
.bad{background:#9b3b30;} .grey{background:#8a8a8a;}
.kv { display:flex; justify-content:space-between; padding:3.5px 0;
      border-bottom:1px solid #eceae6; font-size:12.5px; }
.kv span:first-child { color:var(--grey); }
.kv b { font-variant-numeric:tabular-nums; }
.callout { background:#fff; border:1px solid var(--line); border-left:3px solid var(--ink);
           padding:9px 12px; margin:8px 0; font-size:12.5px; }
.callout .big { font-family:Georgia,serif; font-size:19px; font-weight:700; }
.reading { color:#374151; margin-top:3px; }
.flag { color:#9b3b30; font-weight:600; }
.gate { background:#fdeeec; border:1px solid #e5b5ae; padding:7px 10px; margin:6px 0;
        font-size:12.5px; }
.thesis { background:#f4f3f0; border:1px solid var(--line); padding:12px 14px;
          font-size:12.5px; color:#374151; }
.thesis .sig { margin-top:8px; color:var(--grey); font-size:11.5px; }
.trig { display:flex; gap:10px; flex-wrap:wrap; margin-top:8px; }
.trig div { background:#fff; border:1px solid var(--line); padding:6px 10px;
            font-size:12px; } .trig b { display:block; font-size:13px; }
.footer { padding:12px 22px; font-size:10.5px; color:var(--grey);
          border-top:1px solid var(--line); }
.sens td, .sens th { text-align:center; padding:4px; }
.sens .moS { font-size:10.5px; color:var(--grey); }
@media print { body { background:#fff; } .page { border:none; box-shadow:none; margin:0; } }
"""


def _pos(v, price, xmax):
    return min(100.0, (v / price) / xmax * 100)


def football(res):
    d = res['d']
    price, ccy = d['price'], d['price_ccy']
    valid = {k: v for k, v in res['methods'].items() if v}
    if not valid or not price:
        return '<div class="note">no valid methods</div>'
    hi_ratio = max(v / price for v in valid.values())
    xmax = max(2.0, hi_ratio * 1.12)
    lo = min(valid.values())
    rows = []
    for name, v in valid.items():
        left = _pos(lo, price, xmax)
        width = max(0.6, _pos(v, price, xmax) - left)
        bar = (f'<div class="bar" style="left:{left:.1f}%;width:{width:.1f}%"></div>'
               f'<div class="dot" style="left:{_pos(v, price, xmax):.1f}%" '
               f'title="{name}: {fmt_px(v, ccy)} ({pct((v-price)/v)})"></div>')
        rows.append(f'<div class="row"><div class="lbl">{name}</div>'
                    f'<div class="track">{bar}</div></div>')
    px = _pos(price, price, xmax)
    fair = res.get('fair')
    fair_dot = (f'<div class="diamond" style="left:{_pos(fair, price, xmax):.1f}%" '
                f'title="consensus {fmt_px(fair, ccy)}"></div>'
                if fair else '')
    ticks = ''.join(f'<div class="tick" style="left:{t/xmax*100:.1f}%">{t}%</div>'
                    for t in (50, 100, 150) if t <= xmax * 100)
    axis = (f'<div class="row"><div class="lbl"></div><div class="axis">{ticks}'
            f'{fair_dot}</div></div>')
    # full-height price line: one overlay spans every row's track (labels
    # column is 92px + 8px gap), so the dashed line runs through ALL methods
    overlay = ('<div class="overlay">'
               f'<div class="priceline" style="left:{px:.1f}%" '
               f'title="today {fmt_px(price, ccy)}"></div>'
               f'<div class="plabel" style="left:{px:.1f}%">'
               f'today {fmt_px(price, ccy)}</div></div>')
    return (f'<div class="ff">{"".join(rows)}{axis}{overlay}</div>'
            '<div class="note">Bars and dots: each method\'s fair value as % of '
            'today\'s price (the dashed line through all rows). Diamond: '
            'consensus (median). Right of the line = undervalued.</div>')


def valuation_table(res):
    d, ccy, price = res['d'], res['d']['price_ccy'], res['d']['price']
    notes = {
        'EPV': 'zero-growth worth of the FCF input below',
        'DCF(bear)': f"10yr DCF, growth {pct(res.get('bear_growth', 0))} capped at +2%",
        'Graham': 'asset-anchored; self-disabled when P/B > 5',
        'Multiples': lambda: f"normalised EPS x {V.multiple_used(res['inputs'])[0]:.0f} "
                              f"({V.multiple_used(res['inputs'])[1]})",
    }
    rows = []
    for k, v in res['methods'].items():
        note = notes[k]() if callable(notes[k]) else notes[k]
        if v:
            cls = 'pos' if v > price else 'neg'
            rows.append(f'<tr><td>{k}</td><td class="num"><b>{fmt_px(v, ccy)}</b></td>'
                        f'<td class="num {cls}">{pct((v-price)/v)}</td>'
                        f'<td class="note">{note}</td></tr>')
        else:
            rows.append(f'<tr><td>{k}</td><td class="num">n/a</td><td class="num">--</td>'
                        f'<td class="note">{note}</td></tr>')
    fair, mos = res.get('fair'), res.get('mos')
    cons = (f'<tr><td><b>Consensus (median)</b></td><td class="num"><b>{fmt_px(fair, ccy)}</b></td>'
            f'<td class="num {"pos" if mos and mos > 0 else "neg"}"><b>{pct(mos)}</b></td>'
            f'<td class="note">margin of safety = (fair - price) / fair</td></tr>') if fair else ''
    return f'<table><tr><th>method</th><th class="num">fair value</th>' \
           f'<th class="num">vs price</th><th>basis</th></tr>{"".join(rows)}{cons}</table>'


def market_box(res):
    """What the price itself is telling you (reverse DCF trio)."""
    ccy, price = res['d']['price_ccy'], res['d']['price']
    ig, ir, bd = res.get('implied_growth'), res.get('implied_return'), res.get('breakeven_decline')
    if ig is None:
        return '<div class="note">reverse DCF unavailable</div>'
    if ig < -0.005:
        read = (f'The market pays for <b>decline</b>: {pct(ig)}/yr for a decade. '
                f'You win if the real melt runs slower than the price assumes.')
    elif ig < 0.06:
        read = (f'The market prices modest {pct(ig)}/yr growth. '
                f'Little optimism to refute; the case is about the gap, not the dream.')
    elif ig < 0.12:
        read = (f'The market prices {pct(ig)}/yr for a decade. Demanding; '
                f'the thesis must defend it with levers, not hope.')
    else:
        read = (f'The market prices {pct(ig)}/yr compounding ({(1+ig)**10:.1f}x FCF in a decade). '
                f'Heroic. Be very sceptical.')
    parts = [f'<div class="callout"><div class="big">{pct(ig)}/yr</div>'
             f'<div><b>implied FCF growth</b> in today\'s price ({fmt_px(price, ccy)})</div>'
             f'<div class="reading">{read}</div></div>']
    if ir is not None:
        extra = ('Above your 10% hurdle: the market is paying you to hold pessimism.'
                 if ir > 0.10 else 'Below your 10% hurdle: you are not being paid enough to wait.')
        parts.append(f'<div class="callout"><div class="big">{ir*100:.1f}%</div>'
                     f'<div><b>implied return at zero growth</b></div>'
                     f'<div class="reading">{extra}</div></div>')
    if bd is not None:
        parts.append(f'<div class="callout"><div class="big">{pct(bd)}/yr</div>'
                     f'<div><b>break-even decline</b> (perpetual-melt fair value = price)</div>'
                     f'<div class="reading">Falsifier in one line: the thesis dies if the '
                     f'melt runs faster than {abs(bd)*100:.1f}%/yr.</div></div>')
    return ''.join(parts)


def risk_section(res):
    rk = res.get('risk')
    if not rk:
        return '<div class="note">risk panel unavailable</div>'
    chips = []
    for name, sub in rk['panel'].items():
        score = sub['score']
        reason = sub['reason'].split(' -> ')[0].split(': ', 1)[-1]
        chips.append(f'<span class="chip"><span class="score {heat(score)}">'
                     f'{score if score is not None else "n/a"}</span>{reason}</span>')
    gates = ''.join(f'<div class="gate"><b>KILL-GATE</b> {g}</div>' for g in rk['kill_gates'])
    comp = rk['composite']
    comp_html = (f'<div class="kv"><span>risk composite</span>'
                 f'<b>{comp}/100</b></div>' if comp is not None else '')
    return (f'{gates}{"".join(chips)}'
            f'<div class="note" style="margin-top:6px">0 = far from danger, '
            f'100 = at it (colour runs green to red with risk). Subscores are '
            f'judgement inputs; the composite only orders (sizing, ranking). '
            f'Weights are DRAFT.</div>{comp_html}')


def keydata(res):
    from statistics import median as _med
    d = res['d']
    price, ccy = d['price'], d['price_ccy']
    fcf_yield = None
    if res.get('fcf_hist_used') and d.get('shares') and price:
        fcf_med = _med(res['fcf_hist_used'])
        fcf_yield = fcf_med * (d.get('fx') or 1.0) / (d['shares'] * price)
    pe = price / d['eps_ps'] if d.get('eps_ps') else None
    fs = M.fscore(d)
    az = M.altman_z(d)
    rows = [
        ('market cap', fmt_big(d.get('mkt_cap')) + ('' if ccy != 'GBp' else '')),
        ('P/E', f'{pe:.1f}' if pe else 'n/a'),
        ('P/B', f"{d['pb']:.1f}" if d.get('pb') else 'n/a'),
        ('dividend yield', pct(d.get('div_yield'), signed=False) if d.get('div_yield') else 'none'),
        ('FCF yield (input)', pct(fcf_yield, signed=False) if fcf_med else 'n/a'),
        ('interest coverage', f"{M.interest_coverage(d):.1f}x" if M.interest_coverage(d) else 'n/a'),
        ('net debt/EBITDA', f"{M.net_debt_to_ebitda(d):.1f}x" if M.net_debt_to_ebitda(d) else 'n/a'),
        ('Piotroski F-Score', f"{fs['score']}/9" if fs['available'] else 'n/a'),
        ('Altman Z', f"{az['z']:.2f} ({az['zone']})" if az['available'] else 'n/a'),
    ]
    return ''.join(f'<div class="kv"><span>{k}</span><b>{v}</b></div>' for k, v in rows)


def sens_table(res):
    g = res.get('bear_growth')
    grid = V.sensitivity_grid(res['d'], g, fcf_series=res.get('fcf_hist_used'))
    price, ccy = res['d']['price'], res['d']['price_ccy']
    terms = sorted(next(iter(grid.values())).keys())
    head = ''.join(f'<th>terminal {t*100:.0f}%</th>' for t in terms)
    rows = []
    for r, row in grid.items():
        cells = ''.join(
            f'<td>{"n/a" if v is None else fmt_px(v, ccy)}'
            f'<div class="moS">{pct((v-price)/v) if v and price else ""}</div></td>'
            for v in (row[t] for t in terms))
        rows.append(f'<tr><td class="num"><b>r = {r*100:.0f}%</b></td>{cells}</tr>')
    return (f'<table class="sens"><tr><th></th>{head}</tr>{"".join(rows)}</table>'
            f'<div class="note">Bear DCF fair value per share at each discount rate x '
            f'terminal growth; small grey figure = margin of safety vs today. '
            f'Read: is the verdict robust or one assumption away from flipping?</div>')


def triggers(res):
    fair, inputs = res.get('fair'), res['inputs']
    if not fair:
        return ''
    bump = P.CYCLICAL_MOS_BUMP if inputs.get('cyclical') else 0.0
    ccy = res['d']['price_ccy']
    return (f'<div class="trig">'
            f'<div>CAUTIOUS BUY below<b>{fmt_px(fair*(1-P.BARS["cautious"]-bump), ccy)}</b></div>'
            f'<div>BUY below<b>{fmt_px(fair*(1-P.BARS["buy"]-bump), ccy)}</b></div>'
            f'<div>STRONG BUY below<b>{fmt_px(fair*(1-P.BARS["strong"]-bump), ccy)}</b></div>'
            f'</div>')


def build_note(res):
    d, inputs = res['d'], res['inputs']
    ccy = d['price_ccy']
    verdict = res['verdict']
    colour = RATING_COLOR.get(verdict, '#5b6570')
    mos = res.get('mos')

    if verdict == 'WRONG TOOL':
        return f"""<!doctype html><html><head><meta charset="utf-8"><title>{d['symbol']} -- wrong tool</title>
<style>{CSS}</style></head><body><div class="page">
<div class="masthead"><span><b>VALUATION ENGINE</b> v0.2 draft</span><span>{date.today().isoformat()}</span></div>
<div class="head"><div><h1>{d.get('name')} ({d['symbol']})</h1>
<div class="sub">{d.get('industry') or ''} · {d.get('sector') or ''}</div></div>
<div class="ratingbox"><span class="rating" style="background:{colour}">WRONG TOOL</span></div></div>
<div style="padding:20px 22px"><div class="gate"><b>This engine refuses to value this company.</b><br>
{res['notes'][0] if res['notes'] else ''}</div></div>
{FOOTER}</div></body></html>"""
    # thesis: {tokens} inside the signed text are filled with THIS run's
    # values so figures stay fresh; unknown tokens are surfaced, not silent
    raw_thesis = inputs.get('thesis', 'MISSING: verdict capped at WATCH until written.')
    thesis_text = RENDER.render(raw_thesis, res)
    bad_tokens = RENDER.unrendered_tokens(raw_thesis, res)
    thesis_note = ''
    if '{' in raw_thesis:
        thesis_note = ('<div class="note">Figures in {braces} auto-refresh from '
                       'live data each run; the signed wording is unchanged.'
                       '</div>')
        if bad_tokens:
            thesis_note += (f'<div class="gate"><b>Unrecognised tokens</b> left '
                            f'as-is: {", ".join("{" + t + "}" for t in bad_tokens)}'
                            '</div>')
    audit_chips = ''.join(
        f'<span class="chip"><span class="score {"good" if s=="OK" else ("warn" if s=="WARN" else "bad")}">'
        f'{s}</span>{name}</span>'
        for name, s, _detail in run.data.audit(d))
    notes_html = ''.join(f'<li>{n}</li>' for n in res.get('notes', []))
    flags_html = ''.join(f'<li class="flag">{f}</li>' for f in res.get('flags', []))

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{d.get('name')} ({d['symbol']}) -- research note</title><style>{CSS}</style></head>
<body><div class="page">
<div class="masthead"><span><b>VALUATION ENGINE</b> · v0.2 DRAFT · semi-automatic</span>
<span>{date.today().isoformat()} · {d.get('source')} data</span></div>
{'<div class="banner">DEMO DATA: approximate figures reconstructed from the 25 Aug 2026 report cards. Refresh with --live before acting on anything.</div>' if d.get('approximate') else ''}
<div class="head">
  <div><h1>{d.get('name')} <span style="color:var(--grey)">({d['symbol']})</span></h1>
    <div class="sub">{d.get('industry') or ''} · {d.get('sector') or ''} · discount rate {res['rate']*100:.0f}%
    ({'cyclical +2, ' if inputs.get('cyclical') else ''}moat: {inputs.get('moat')})</div></div>
  <div class="ratingbox"><span class="rating" style="background:{colour}">{verdict}</span>
    <div class="pxrow">price <b>{fmt_px(d['price'], ccy)}</b> ·
      fair <b>{fmt_px(res.get('fair'), ccy)}</b> ·
      MoS <b class="{'pos' if mos and mos>0 else 'neg'}">{pct(mos, digits=0)}</b></div>
    <div class="pxrow">position weight: <b>{res.get('weight', 0)*100:.0f}%</b></div></div>
</div>
<div class="grid">
  <div class="left">
    <h2>Valuation: four independent methods</h2>
    {football(res)}
    {valuation_table(res)}
    <div class="note" style="margin-top:6px">FCF input: {res.get('fcf_provenance', 'n/a')}
    {' · lease principal deducted: ' + fmt_big(res.get('lease_deduction')) if res.get('lease_deduction') else ''}</div>

    <h2>Cross-checks (where the model is fragile)</h2>
    <div class="kv"><span>terminal value share of bear DCF</span>
      <b>{pct(res.get('terminal_share'), signed=False, digits=0) if res.get('terminal_share') else 'n/a'}</b></div>
    <div class="kv"><span>exit-multiple variant ({P.EXIT_EBITDA_MULT:.0f}x EV/EBITDA terminal)</span>
      <b>{fmt_px(res.get('exit_mult_value'), ccy)}</b></div>
    <div class="kv"><span>bull DCF (upside ceiling)</span><b>{fmt_px(res.get('bull'), ccy)}</b></div>
    <div class="note" style="margin-top:5px">The Gordon terminal carries {pct(res.get('terminal_share'), signed=False, digits=0) if res.get('terminal_share') else 'n/a'}
    of the value; the exit-multiple variant shows what happens when it does not.</div>

    <h2>Sensitivity: bear DCF</h2>
    {sens_table(res)}

    <h2>Thesis on file (owner-signed)</h2>
    <div class="thesis">{thesis_text}
    <div class="sig">Human inputs: moat {inputs.get('moat')} · cyclicality {inputs.get('cyclical')}</div></div>
    {thesis_note}

    <h2>Verdict trace</h2>
    <ul>{flags_html}{notes_html or '<li>no caps or notes: verdict issued on the ladder as-is</li>'}</ul>
    {triggers(res)}
  </div>
  <div class="right">
    <h2>What the price is saying</h2>
    {market_box(res)}
    <h2>Key data</h2>
    {keydata(res)}
    <h2>Risk panel</h2>
    {risk_section(res)}
    <h2>Data quality</h2>
    {audit_chips}
  </div>
</div>
{FOOTER}</div></body></html>"""


FOOTER = ("""<div class="footer">Semi-automatic: the engine computes, you judge. Draft output from the
v0.2 draft engine; every new parameter (risk curves, exit multiple, sizing) is pending owner
sign-off, see v02_draft/README.md. Numbers from cached snapshots where marked. Not financial advice.</div>""")


def build_index(results):
    rows = []
    for sym, res in results:
        d = res['d']
        mos = res.get('mos')
        colour = RATING_COLOR.get(res['verdict'], '#5b6570')
        ig = res.get('implied_growth')
        rc = res.get('risk_composite')
        rows.append(f"""<tr><td><a href="{sym.replace('.', '_')}_note.html"><b>{sym}</b></a><br>
<span class="note">{d.get('name')}</span></td>
<td><span class="rating" style="background:{colour};font-size:11px;padding:3px 9px">{res['verdict']}</span></td>
<td class="num">{fmt_px(d['price'], d['price_ccy'])}</td>
<td class="num">{fmt_px(res.get('fair'), d['price_ccy'])}</td>
<td class="num {'pos' if mos and mos > 0 else 'neg'}">{pct(mos, digits=0)}</td>
<td class="num">{pct(ig) if ig is not None else '--'}</td>
<td class="num">{rc if rc is not None else '--'}</td></tr>""")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Watchlist notes</title>
<style>{CSS}</style></head><body><div class="page">
<div class="masthead"><span><b>VALUATION ENGINE</b> · v0.2 DRAFT</span><span>{date.today().isoformat()}</span></div>
<div style="padding:18px 22px"><h2 style="margin-top:0">Watchlist</h2>
<table><tr><th>company</th><th>verdict</th><th class="num">price</th><th class="num">fair value</th>
<th class="num">MoS</th><th class="num">implied growth</th><th class="num">risk</th></tr>
{''.join(rows)}</table>
<div class="note" style="margin-top:8px">Click a ticker for the full research note.</div></div>
{FOOTER}</div></body></html>"""


def write_notes(symbols, live=False, outdir=OUT_DIR):
    os.makedirs(outdir, exist_ok=True)
    results = []
    for sym in symbols:
        try:
            bundle = run.get_bundle(sym, live=live)
        except Exception as e:
            print(f'{sym}: skipped ({e})')
            continue
        res = run.assess(sym, bundle)
        res.setdefault('bear_growth', V.clamp(res.get('hist_growth', 0.0), -0.02, 0.02))
        results.append((sym, res))
        path = os.path.join(outdir, f"{sym.replace('.', '_')}_note.html")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(build_note(res))
        print(f'written {path}')
    if results:
        path = os.path.join(outdir, 'index.html')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(build_index(results))
        print(f'written {path}')
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(prog='v02_draft.note')
    ap.add_argument('symbols', nargs='*')
    ap.add_argument('--live', action='store_true')
    ap.add_argument('--out', default=OUT_DIR)
    args = ap.parse_args(argv)
    from engine_v01 import WATCHLIST
    symbols = args.symbols or list(WATCHLIST)
    write_notes(symbols, live=args.live, outdir=args.out)


if __name__ == '__main__':
    main()
