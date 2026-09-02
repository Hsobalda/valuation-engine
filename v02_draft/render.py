"""render.py -- live variables inside thesis text (owner request, 2 Sep 2026).

Theses are handwritten but full of figures that go stale ("at 462p the
market implies..."). Allow {tokens} inside thesis text; at output time they
are replaced with the CURRENT run's values, so a thesis written once keeps
its numbers fresh on every workflow run.

Design guards:
  * Unknown tokens are left untouched (never an error, never silent loss).
  * Literal braces are written {{like this}}.
  * Rendering is display-only: the signed text in engine_v01.py is never
    modified. Substantive claims, falsifiers and triggers stay prose --
    variables refresh figures, they do not rewrite judgement.

Available tokens (formatted for humans):
  {symbol} {name} {verdict} {weight}
  {price} {fair} {mos} {r}
  {ig}  implied FCF growth   {ir}  implied return at g=0   {be} break-even decline
  {epv} {bear_dcf} {graham} {mult} {bull_dcf}
  {coverage} {nd_ebitda} {fscore} {altman} {risk}
"""

from __future__ import annotations

import re

from . import metrics as M

_TOKEN = re.compile(r'\{([a-z_]+)\}')


def _px(v, ccy):
    if v is None:
        return 'n/a'
    if ccy == 'GBp':
        return f'{v:,.0f}p'
    sym = {'USD': '$', 'EUR': '€', 'GBP': '£'}.get(ccy, '')
    return f'{sym}{v:,.2f}' if sym else f'{v:,.2f} {ccy}'


def _pc(x, signed=True, digits=1):
    return 'n/a' if x is None else (f'{x*100:+.{digits}f}%' if signed
                                    else f'{x*100:.{digits}f}%')


def variables(res):
    """The substitution dict for one assessment result."""
    d, m = res['d'], res.get('methods') or {}
    fs, az = M.fscore(d), M.altman_z(d)
    return {
        'symbol': d.get('symbol', ''),
        'name': d.get('name', ''),
        'verdict': res.get('verdict', 'n/a'),
        'weight': f"{res.get('weight', 0)*100:.0f}%",
        'price': _px(d.get('price'), d.get('price_ccy') or ''),
        'fair': _px(res.get('fair'), d.get('price_ccy') or ''),
        'mos': _pc(res.get('mos'), digits=0),
        'r': f"{res.get('rate', 0)*100:.0f}%",
        'ig': _pc(res.get('implied_growth')),
        'ir': _pc(res.get('implied_return')),
        'be': _pc(res.get('breakeven_decline')),
        'epv': _px(m.get('EPV'), d.get('price_ccy') or ''),
        'bear_dcf': _px(m.get('DCF(bear)'), d.get('price_ccy') or ''),
        'graham': _px(m.get('Graham'), d.get('price_ccy') or ''),
        'mult': _px(m.get('Multiples'), d.get('price_ccy') or ''),
        'bull_dcf': _px(res.get('bull'), d.get('price_ccy') or ''),
        'coverage': (f'{M.interest_coverage(d):.1f}x'
                     if M.interest_coverage(d) is not None else 'n/a'),
        'nd_ebitda': (f'{M.net_debt_to_ebitda(d):.1f}x'
                      if M.net_debt_to_ebitda(d) is not None else 'n/a'),
        'fscore': f"{fs['score']}/9" if fs['available'] else 'n/a',
        'altman': (f"{az['z']:.2f} ({az['zone']})" if az['available'] else 'n/a'),
        'risk': (f"{res['risk_composite']}/100"
                 if res.get('risk_composite') is not None else 'n/a'),
    }


def render(text, res):
    """Replace {tokens} with live values; unknown tokens stay literal."""
    vals = variables(res)

    def sub(match):
        key = match.group(1)
        return str(vals[key]) if key in vals else match.group(0)

    # honour {{escaped}} braces first, then restore them after substitution
    text = text.replace('{{', '\x00').replace('}}', '\x01')
    text = _TOKEN.sub(sub, text)
    return text.replace('\x00', '{').replace('\x01', '}')


def unrendered_tokens(text, res):
    """Tokens present in the text that this run could not fill -- for the
    data-quality panel, so a typo'd {tokn} is visible rather than silent."""
    vals = variables(res)
    return [t for t in _TOKEN.findall(text) if t not in vals]
