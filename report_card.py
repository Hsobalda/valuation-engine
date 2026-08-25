# report_card.py -- one readable page per company: every metric, its value,
# its interpretation, and the thesis question it raises.
# Usage:  python3 report_card.py           -> all watchlist companies -> reports/*.md
#         python3 report_card.py IMB.L     -> one company, printed to screen too

import os, sys
from statistics import median
from engine_v01 import (WATCHLIST, fetch, epv, dcf, graham, multiples, fatal_flags,
                        clamp, hist_growth, discount_rate, assess, BARS,
                        CYCLICAL_MOS_BUMP, DISAGREE_CAP)


def implied_growth(d, r, price):
    """Reverse DCF: growth rate that makes the DCF equal today's price."""
    lo, hi = -0.30, 0.60
    for _ in range(80):
        mid = (lo + hi) / 2
        v = dcf(d, mid, r)
        if v is None:
            return None
        if v < price:
            lo = mid
        else:
            hi = mid
    return mid


def rate_coverage(cov):
    if cov is None: return 'no data'
    if cov >= 8:  return f'{cov:.1f}x -- fortress'
    if cov >= 4:  return f'{cov:.1f}x -- comfortable'
    if cov >= 2:  return f'{cov:.1f}x -- adequate, watch in downturns'
    return f'{cov:.1f}x -- FRAGILE (fatal flag: one bad year from distress)'


def rate_capex(ratio):
    if ratio is None: return 'no data'
    if ratio < 0.8:  return f'{ratio:.2f} -- spending below wear-and-tear: check for under-investment'
    if ratio < 1.15: return f'{ratio:.2f} -- maintenance mode: FCF is clean'
    if ratio < 1.5:  return f'{ratio:.2f} -- some growth capex: FCF slightly understates earning power'
    return f'{ratio:.2f} -- HEAVY growth capex: zero-growth methods understate this company'


def card(symbol):
    res = assess(symbol)
    d, inputs, r = res['d'], res['inputs'], res['rate']
    price, fair, mos = d['price'], res['fair'], res['mos']
    L = []
    add = L.append
    ccy = d['price_ccy']

    add(f"# {d['name']} ({symbol}) -- Report Card")
    add(f"*Generated from live data. Discount rate applied: {r*100:.0f}% "
        f"(base 10%{', +2 cyclical' if inputs['cyclical'] else ''}"
        f"{', -1 wide moat' if inputs['moat']=='wide' else ''}).*\n")

    # ---- 1. snapshot
    add('## 1 | Snapshot')
    cap = f"{d['mkt_cap']/1e9:.1f}bn" if d['mkt_cap'] else 'n/a'
    add(f"| Metric | Value | Interpretation |")
    add(f"|---|---|---|")
    add(f"| Price | {price:,.2f} {ccy} | market cap ~{cap} |")
    if d['eps'] and d['eps'] > 0:
        pe = price / d['eps']
        ey = d['eps'] / price * 100
        anchor = ('paying for GROWTH -- what growth, exactly? see section 3'
                  if pe > 12 else ('roughly zero-growth pricing at a 10% hurdle'
                  if pe > 8 else 'priced for DECLINE -- market expects shrinkage'))
        add(f"| P/E | {pe:.1f} | earnings yield {ey:.1f}% vs your 10% hurdle -> {anchor} |")
    else:
        add(f"| P/E | n/a (no positive earnings) | earnings-based methods unreliable here |")
    if d['pb']:
        pbnote = ('asset-light or buyback-shrunken equity: Graham unreliable' if d['pb'] > 5
                  else 'balance sheet meaningfully backs the price' if d['pb'] < 2
                  else 'moderate asset backing')
        add(f"| P/B | {d['pb']:.1f} | {pbnote} |")
    if d['div_yield']:
        add(f"| Dividend yield | {d['div_yield']:.1f}% | cash returned while you wait; check payout sustainability |")
    if d['fcf_hist'] and d['mkt_cap']:
        fcf_yield = median(d['fcf_hist']) * d['fx'] / (d['mkt_cap'] if ccy != 'GBp' else d['mkt_cap']*100) * 100
        fy = median(d['fcf_hist']) / (d['mkt_cap'] / (100 if ccy == 'GBp' else 1) / d['fx'] * 1) 
        # simpler: FCF / (shares*price in fin ccy)
        fcf_yield = median(d['fcf_hist']) / (d['shares'] * price / d['fx']) * 100
        note = ('exceptional -- market deeply sceptical, find out why' if fcf_yield > 12
                else 'high -- genuine value zone' if fcf_yield > 8
                else 'fair' if fcf_yield > 5 else 'low -- growth expectations baked in')
        add(f"| FCF yield | {fcf_yield:.1f}% | {note} |")

    # ---- 2. valuation stack
    add('\n## 2 | Valuation stack (four independent methods)')
    add('| Method | Fair value | vs price | Reliability note |')
    add('|---|---|---|---|')
    notes = {
        'EPV': 'zero-growth floor: worth if it never grows again',
        'DCF(bear)': f'10yr DCF, growth capped at 2% (used {clamp(hist_growth(d["fcf_hist"]), -0.02, 0.02)*100:+.1f}%)',
        'Graham': 'asset-anchored; self-disabled when P/B > 5' ,
        'Multiples': 'normalised EPS x long-run 15x multiple (v0.1 simplification)',
    }
    for k, v in res['methods'].items():
        if v:
            add(f"| {k} | {v:,.0f} | {(v-price)/v*100:+.0f}% | {notes[k]} |")
        else:
            add(f"| {k} | n/a | -- | {notes[k]} -- disabled for this company |")
    valid = [v for v in res['methods'].values() if v]
    if len(valid) >= 2:
        spread = max(valid)/min(valid)
        sp_note = ('methods AGREE -- conclusion trustworthy' if spread < 1.5
                   else 'moderate scatter -- estimate is blurry' if spread < DISAGREE_CAP
                   else 'methods DISAGREE (> cap) -- you do not understand this company yet; verdict capped')
        add(f"\n**Consensus (median): {fair:,.0f} {ccy} -> margin of safety {mos*100:+.0f}%.** Method spread {spread:.1f}x: {sp_note}.")

    # ---- 3. growth lens
    add('\n## 3 | Growth lens')
    g_hist = hist_growth(d['fcf_hist'])
    hist_str = ' -> '.join(f'{f/1e9:.2f}' for f in reversed(d['fcf_hist']))
    add(f"- FCF history (bn, oldest->newest): {hist_str}  (trend {g_hist*100:+.1f}%/yr)")
    if res['bull']:
        add(f"- Bull-case DCF (growth {clamp(g_hist,0.02,0.10)*100:.0f}%): {res['bull']:,.0f} -- upside ceiling if optimism is right")
    ig = implied_growth(d, r, price)
    if ig is not None:
        if ig < -0.005:
            read = (f"market prices PERPETUAL DECLINE of {abs(ig)*100:.1f}%/yr. Your question: is the real decline "
                    f"slower than that? If yes, the price overshoots pessimism -> that gap IS the thesis")
        elif ig < 0.06:
            read = f"market prices modest {ig*100:.1f}%/yr growth -- believable for most healthy firms; little optimism to refute"
        elif ig < 0.12:
            read = f"market prices {ig*100:.1f}%/yr for a DECADE -- demanding; thesis must defend it"
        else:
            read = f"market prices {ig*100:.1f}%/yr compound for a DECADE ({(1+ig)**10:.1f}x) -- heroic; be very sceptical"
        add(f"- **Reverse DCF: today's price implies {ig*100:+.1f}%/yr FCF growth for 10 yrs.** {read}.")

    # ---- 4. survival
    add('\n## 4 | Survival (can it live long enough to re-rate?)')
    cov = (d['ebit'] / abs(d['interest'])) if (d['ebit'] is not None and d['interest'] not in (None, 0)) else None
    add(f"- Interest coverage: {rate_coverage(cov)}")
    neg = sum(1 for f in d['fcf_hist'] if f < 0)
    add(f"- FCF negative years: {neg} of {len(d['fcf_hist'])}" + (' -- earnings may be paper, cash says otherwise' if neg else ' -- cash generation consistent'))
    try:
        import yfinance as yf
        cf = yf.Ticker(symbol).cashflow
        capex = abs(cf.loc['Capital Expenditure'].dropna().iloc[0])
        da = cf.loc['Depreciation And Amortization'].dropna().iloc[0]
        add(f"- Capex / D&A: {rate_capex(capex/da)}")
    except Exception:
        add('- Capex / D&A: data unavailable')
    add(f"- Fatal flags: {', '.join(res['flags']) if res['flags'] else 'none'}")

    # ---- 5. verdict trace
    add('\n## 5 | Verdict trace')
    bump = CYCLICAL_MOS_BUMP if inputs['cyclical'] else 0.0
    add(f"- **Verdict: {res['verdict']}**" + (f" (weight {res['weight']*100:.0f}%)" if res['weight'] else ''))
    for n in res['notes']:
        add(f"- capped/noted: {n}")
    if fair:
        add(f"- Price triggers (at current fair value): CAUTIOUS BUY below {fair*(1-BARS['cautious']-bump):,.0f} | "
            f"BUY below {fair*(1-BARS['buy']-bump):,.0f} | STRONG BUY below {fair*(1-BARS['strong']-bump):,.0f}")
    add(f"- Human inputs on file: moat = {inputs['moat']}, cyclical = {inputs['cyclical']}, "
        f"thesis = {'MISSING (verdict capped)' if inputs['thesis'].startswith('TODO') else 'present'}")

    # ---- 6. thesis prompts
    add('\n## 6 | Questions your thesis must answer')
    qs = []
    if mos and mos > 0.15 and not res['flags']:
        qs.append('The market is offering a discount with no obvious fatal flaw. WHY? There is always a reason -- name it, then argue it is temporary or overblown.')
    if ig is not None and ig < -0.005:
        qs.append(f'Do you believe FCF declines slower than {abs(ig)*100:.1f}%/yr? What evidence (pricing power, history, industry data)?')
    if ig is not None and ig > 0.12:
        qs.append(f'Can this company really compound FCF at {ig*100:.0f}%/yr for a decade? Show subs x price x margin (or equivalent) maths.')
    if valid and len(valid) >= 2 and max(valid)/min(valid) > DISAGREE_CAP:
        qs.append('Your methods disagree wildly. Which method is WRONG for this business, and why? (Answer before trusting any number.)')
    if inputs['cyclical']:
        qs.append('Cyclical: where are we in the cycle NOW? Trailing numbers flatter peaks and slander troughs.')
    if d['pb'] and d['pb'] > 5:
        qs.append('Asset-light: value depends on intangibles staying valuable. What breaks the brand/network/data advantage?')
    if d['div_yield'] and d['div_yield'] > 6:
        qs.append(f"Dividend {d['div_yield']:.1f}% -- market doubts it survives. Check payout vs FCF.")
    qs.append('What observable fact would prove you WRONG? (falsifier -- mandatory)')
    for i, q in enumerate(qs, 1):
        add(f'{i}. {q}')
    add('\n---\n*Semi-automatic: the engine computes, you judge. Not financial advice.*')
    return '\n'.join(L)


if __name__ == '__main__':
    targets = sys.argv[1:] or list(WATCHLIST)
    os.makedirs('reports', exist_ok=True)
    for sym in targets:
        text = card(sym)
        path = f'reports/{sym.replace(".", "_")}.md'
        with open(path, 'w') as f:
            f.write(text)
        print(f'written {path}')
        if len(targets) == 1:
            print('\n' + text)
