# engine_v01.py -- Valuation & Verdict Engine v0.1
# Spec: ENGINE_DESIGN.md (owner-signed 23 Aug 2026)
# v0.1 scope: 4-method valuation stack, tiered verdict ladder w/ asymmetry test,
#             basic fatal flags, live data. Deliberately conservative: prices
#             steady cash flows only, refuses to pay for growth.
# v0.2 (see docs/VERSION_PLAN.md / GitHub issues): GROWTH LENS -- reverse-DCF
#             implied-growth column beside every margin figure (engine stops being
#             blind to growth-priced names); IFRS 16 lease-adjusted FCF; capex fix
#             (owner earnings); structural-decliner mode; risk panel w/ drillable
#             subscores + weighting engine; own-history/sector multiples;
#             wrong-model flags; journal stubs.
# v0.3+: growth mode -- expectations investing (implied growth vs driver-ceiling
#             lever maths); the value engine's burden-of-proof logic pointed at
#             growth-priced names instead of ignoring them.

import yfinance as yf
from statistics import median

# ----------------------------------------------------------------------
# THE HUMAN INPUTS (the "semi" in semi-automatic) -- owner must maintain.
# All 7 theses owner-written and signed 25 Aug 2026. Each carries a falsifier
# ("wrong if") and price triggers; the engine caps any name lacking these.
# ----------------------------------------------------------------------
WATCHLIST = {
    'TSCO.L': {'moat': 'narrow', 'cyclical': False,
               'thesis': ('PASS. Market prices ~1.3%/yr FCF growth, feasible, not a mispricing. Problem is '
                          'the payoff: 462p is 32% above my 350p fair value and even bull DCF only hits '
                          '480p, 4% above today. Leases make it worse: GBP7.9bn capitalised, ~GBP650m/yr '
                          'principal that headline FCF ignores (Tesco itself defines retail FCF after lease '
                          'payments). Adjusted EPV and bear DCF land 245-254p. Comps agree, held loosely '
                          'since real competitors (Aldi, Lidl, Asda) are private and cross-border comps '
                          'carry noise: Kroger 7.0x, Ahold 7.7x, Sainsburys 8.3x EV/EBITDA vs Tesco 9.0x, '
                          'so the quality premium is already in the price. Peer multiples imply 253-345p. '
                          'Good business, fully priced. Wrong if: Clubcard retail media lifts margins enough '
                          'to make 3-4% growth right. Look again below 298p, conviction nearer 245p where '
                          'lease-adjusted methods clear my 30% margin. [Signed 25 Aug 2026]')},
    'PEP':    {'moat': 'wide', 'cyclical': False,
               'thesis': ('PASS. Wide moat is real: brands, distribution, shelf power, and Frito-Lay snacks '
                          'carry the growth while soda declines. But the price wants growth the business '
                          'does not have. At $144.67 the market implies ~10%/yr FCF growth for a decade; at '
                          'a believable 4% the shares are worth ~$92, and my engine fair value is $79. Bull '
                          'DCF is $144, todays price IS the bull case, even less margin than Tesco offered. '
                          'Elliotts ~$4bn stake (Sept 2025, bottling and supply-chain review) is the '
                          'catalyst the market leans on, but a cost programme cannot bridge a 10% growth '
                          'assumption, and I dont pay 83% over fair value for someone elses activism '
                          'working out. No fatal flags, purely price. Honest caveat: my zero-growth engine '
                          'structurally undervalues wide-moat compounders and PEP is where that bias bites '
                          'hardest, so true fair value sits above $79, just nowhere near $145. Wrong if: '
                          'GLP-1 snack fears prove overdone AND Elliott unlocks 200bp+ of margin, together '
                          'making 6-7% growth real. Interested below ~$110 where implied growth drops to '
                          '~6%, conviction near $92. [Signed 25 Aug 2026]')},
    'EZJ.L':  {'moat': 'none', 'cyclical': True,
               'thesis': ('SELL / EXIT. Apollo agreed 715p cash on 6 Aug, completion expected by end-March '
                          '2027. At 676p im getting 5.8% if it closes (about 9-10% annualised), but if it '
                          'breaks the shares likely fall back near pre-bid ~500p, so -26%. Price implies '
                          'roughly 80% odds of completion and i have no edge guessing regulators. My old '
                          'value thesis is dead, nobody gets my 773p fair value, you get 715p or a broken '
                          'deal. Take the money and put it in names my framework can actually judge. Wrong '
                          'if: deal breaks and shares drop to ~500p, then its a normal valuation case again '
                          'and i re-run the engine. [Signed 25 Aug 2026]')},
    'SPOT':   {'moat': 'narrow', 'cyclical': False,
               'thesis': ('PASS. To justify today\'s price at a 10% required return, free cash flow has to '
                          'grow about 24% a year for a decade, roughly 8.6x. Building that generously from '
                          'the actual levers (subscribers 280m to 500m, prices up 4% a year, margins 30% to '
                          '40%) gets me to about 3.6x. The price needs more growth than the business can '
                          'plausibly deliver. The moat is thinner than it looks: the recommendation data '
                          'flywheel is real, but switching costs are low and the catalogue is no advantage, '
                          'since Universal, Sony and Warner deliberately license the same music to every '
                          'platform to keep them interchangeable and protect their two-thirds revenue cut, '
                          'which also caps the margin lever. Only two years of consistent profits make '
                          'normalised FCF unreliable anyway. Wrong if: gross margin sustainably breaks 35%, '
                          'or subscriber growth re-accelerates with price rises sticking. Interested below '
                          'about $270, where implied growth falls to 12% and the levers could deliver it. '
                          '[Signed 25 Aug 2026]')},
    # --- adopted from scans 23 Aug 2026; flags PROVISIONAL, theses owed by owner ---
    'IMB.L':  {'moat': 'narrow', 'cyclical': False,   # structural decliner, NOT cyclical
               'thesis': ('CAUTIOUS BUY (owner override, 4% weight cap). Engine caps at WATCH on the 2.9x '
                          'method spread and I keep that flag live, but the spread is a Graham artifact: '
                          'P/B 4.9 from years of buybacks shrinking book equity makes Graham lowball at '
                          '1550p while the three cash and earnings methods cluster tight at 4034-4439p. '
                          'Ex-Graham the engine agrees with itself. Core case: market prices a -8.4%/yr FCF '
                          'melt for a decade, but actual FCF has been flat for four years (3.17bn latest), '
                          'and break-even is -5.3%/yr even assuming the melt never stops. Pricing power on '
                          'a declining volume base keeps beating expectations. Dividend costs 49% of FCF, '
                          'double covered, with the 1.45bn/yr buyback the optional half of an 88% total '
                          'payout. Real risks: NGP laggard vs BAT and PMI, UK generational ban now LAW (Royal Assent April 2026, sales ban from Jan 2027; closed cohort locks in the melt rather than accelerating it near term), Canada '
                          'litigation ~312m through 2029, and a permanent ESG discount I may never get paid '
                          'out of except through the payout itself. REVISIT WATCHLIST, check at FY results '
                          '(Nov 17) and each half-year: 1) tobacco volume decline worse than mid single '
                          'digits, 2) FCF dropping below ~2.8bn (approaching my -5.3% break-even path), '
                          '3) dividend cover heading toward 1x or buyback cut, 4) NGP net revenue growth '
                          'stalling below double digits, 5) generational bans spreading to markets that matter: watch Massachusetts and Hawaii statewide bills (US is the profit pool that counts) and any EU shift from endgame goals to birthdate law, plus menthol and nicotine caps. Context: NZ repealed 2024, Malaysia dropped the clause, these laws are politically fragile so contagion is slow but must be tracked. Any two of these and the melt thesis is failing, exit. Wrong if: volume decline accelerates past pricing power so FCF '
                          'starts falling mid single digits yearly. Add toward 8% only if price nears '
                          '2100p (50% MoS) with FCF still flat. [Signed 25 Aug 2026]')},
    'KGF.L':  {'moat': 'none', 'cyclical': True,      # DIY retail: housing/consumer cycle
               'thesis': ('WATCH. Reverse DCF says the market prices a 7.8% yearly FCF decline for a decade, '
                          'but headline FCF (about GBP1bn) is flattered by IFRS 16: rent on leased stores '
                          'sits in financing, not operating cash flow. Lease adjusted FCF is nearer '
                          'GBP650-750m, and on that basis the market only assumes a 2-4% yearly decline. '
                          'Much less pessimism to bet against. Capex at 0.61 of D&A looks like '
                          'under-investment but my peer screen shows it is lease geometry: US chains that '
                          'own stores sit near 1.0, UK chains that rent sit at 0.3-0.6. The real cautions: '
                          '3-4% margins against Home Depot\'s 12%, no moat, and a third of revenue in weak '
                          'French chains. Screwfix France is the interesting growth story but at 35 stores '
                          'of a possible 600, opening 5 a year, it is an option, not a lever. Dividend is '
                          'covered about twice even on adjusted cash. I revisit at about 280p and rerun the '
                          'numbers lease adjusted; at about 260p the margin of safety clears my cyclical bar '
                          'and I can buy cautiously. Wrong if: Screwfix France accelerates to 30 or more '
                          'stores a year with like-for-like sales holding, or a French restructuring or exit '
                          'is announced. Either would justify paying nearer 285-300p. [Signed 25 Aug 2026]')},
    'T':      {'moat': 'narrow', 'cyclical': False,   # infrastructure oligopoly
               'thesis': ('CAUTIOUS BUY, 4% weight cap. Price $25.69 sits below my zero-growth EPV floor of '
                          '$27.69, so im paying less than the business is worth if it never grows again. '
                          'Methods cluster tight (spread 1.3x, consensus $30.41, street consensus lands the '
                          'same $30.40), MoS +16% clears my 15% cautious bar and the asymmetry test passes '
                          'easily with bull DCF at $63. Business is now a focused connectivity utility: '
                          'wireless triopoly plus fibre build to 40m+ locations, 43% of home internet on '
                          'converged bundles, FCF guided $18bn 2026 rising to $21bn by 2028, dividend 42% of '
                          'FCF, coverage 5x. Note my EPV likely understates: trailing FCF is depressed by '
                          'growth capex mid fibre build, the reverse of the lease problem. Real risks: net '
                          'debt/EBITDA ~3.2x after Lumen and EchoStar deals makes it rate sensitive, fibre '
                          'ARPU fell 1.3% from bundle discounting, and a T-Mobile/Verizon price war would '
                          'hurt. Wrong if: fibre net adds fall below 1m/yr (breaking an 8 year streak), '
                          'leverage stuck above 3x into 2027, or price war erupts. Add toward 8% only if '
                          'MoS reaches 30% (price ~$21) with flags still clean. [Signed 25 Aug 2026]')},
    'BT-A.L': {'moat': 'narrow', 'cyclical': False,   # UK telecom incumbent, Openreach network
               'thesis': 'TODO: owner thesis required.'},
    'CMCSA': {'moat': 'narrow', 'cyclical': False,    # US cable/broadband infrastructure + NBCU
               'thesis': ('TODO: owner thesis required. Scan 29 Aug 2026: +39% MoS, 4 methods, '
                          'spread 1.8x, no flags. The shape: market hates the broadband subscriber '
                          'bleed to fixed wireless; meanwhile ~$15bn FCF, relentless buybacks, owned '
                          'infrastructure, US GAAP (no lease distortion). AT&T-adjacent pattern. '
                          'Thesis must answer: 1) is the sub bleed a melt or a cycle, 2) does '
                          'broadband ARPU pricing power offset volume losses, 3) NBCU/Epic: asset '
                          'or distraction, 4) why is this cheaper than T on the same story.')},
}

# Locked parameters (see spec)
BASE_RATE = 0.10          # discount rate: 10% base...
CYCLICAL_BUMP = 0.02      # ...+2pts if cyclical
WIDE_MOAT_DISC = 0.01     # ...-1pt if wide moat
RATE_FLOOR = 0.09
TERMINAL_G = 0.02
BARS = {'strong': 0.50, 'buy': 0.30, 'cautious': 0.15}   # MoS bars
CYCLICAL_MOS_BUMP = 0.10  # cyclical names must clear +10pts on every bar
ASYMMETRY = 3.0           # cautious buy needs bull upside >= 3x bear downside
DISAGREE_CAP = 2.5        # max/min method ratio beyond which verdict caps at WATCH
FULL_POS, HALF_POS = 0.08, 0.04   # position caps (owner signed off)


def clamp(x, lo, hi):
    """Pin x inside [lo, hi]."""
    return max(lo, min(hi, x))


def fx_to_price_ccy(fin_ccy, price_ccy):
    """Financial statements can be in a different currency than the share price.
    Returns the multiplier that converts statement-currency into price-currency.
    London special case: prices are in PENCE, so convert to GBP first, then x100."""
    if fin_ccy == price_ccy:
        return 1.0
    target = 'GBP' if price_ccy == 'GBp' else price_ccy
    mult = 100.0 if price_ccy == 'GBp' else 1.0
    if fin_ccy == target:
        return mult
    pair = yf.Ticker(f'{fin_ccy}{target}=X').info.get('regularMarketPrice')
    if pair:
        return pair * mult
    raise ValueError(f'No FX rate for {fin_ccy}->{price_ccy}')


def fetch(symbol):
    """Pull one company's bundle of raw data. Everything downstream reads this dict."""
    t = yf.Ticker(symbol)
    info = t.info
    cf, inc = t.cashflow, t.income_stmt

    fcf_hist = list(cf.loc['Free Cash Flow'].dropna()) if 'Free Cash Flow' in cf.index else []
    ni_hist = list(inc.loc['Net Income'].dropna()) if 'Net Income' in inc.index else []
    ebit = inc.loc['EBIT'].dropna().iloc[0] if 'EBIT' in inc.index else None
    interest = inc.loc['Interest Expense'].dropna().iloc[0] if 'Interest Expense' in inc.index else None

    # Balance sheet + sorted income statement for Altman Z / F-Score.
    # yfinance column order varies, so sort explicitly: oldest fiscal year -> newest.
    bs = t.balance_sheet
    if bs is not None and not bs.empty:
        bs = bs.sort_index(axis=1)
    inc_s = inc.sort_index(axis=1) if inc is not None and not inc.empty else None
    cfo = None
    if cf is not None and 'Operating Activities' in cf.index:
        cfo_s = cf.loc['Operating Activities'].dropna()
        cfo = cfo_s.iloc[0] if len(cfo_s) else None   # cf rows are newest-first

    price_ccy = info.get('currency')
    fin_ccy = info.get('financialCurrency')
    # Yahoo quirk: for London tickers the PRICE is in pence (GBp) but per-share
    # fields (eps, bookValue) are in POUNDS. Convert them to pence to match.
    pershare_fix = 100.0 if price_ccy == 'GBp' else 1.0
    return {
        'symbol': symbol,
        'name': info.get('shortName', symbol),
        'price': info.get('currentPrice'),
        'price_ccy': price_ccy,
        'eps': info.get('trailingEps') and info['trailingEps'] * pershare_fix,
        'bvps': info.get('bookValue') and info['bookValue'] * pershare_fix,
        'pb': info.get('priceToBook'),
        'div_yield': info.get('dividendYield'),      # percent form, e.g. 6.7
        'mkt_cap': info.get('marketCap'),
        'shares': info.get('sharesOutstanding'),
        'fcf_hist': fcf_hist,                     # statement currency!
        'ni_hist': ni_hist,                       # statement currency!
        'ebit': ebit, 'interest': interest,
        'bs': bs, 'inc_s': inc_s, 'cfo': cfo,     # statement currency, oldest -> newest cols
        'fx': fx_to_price_ccy(fin_ccy, price_ccy),
    }


def discount_rate(inputs):
    r = BASE_RATE
    if inputs['cyclical']:
        r += CYCLICAL_BUMP
    if inputs['moat'] == 'wide':
        r -= WIDE_MOAT_DISC
    return max(r, RATE_FLOOR)


def hist_growth(series):
    """Annualised growth from oldest to newest of a (newest-first) history."""
    if len(series) < 2 or series[-1] <= 0 or series[0] <= 0:
        return 0.0
    years = len(series) - 1
    return (series[0] / series[-1]) ** (1 / years) - 1


def fcf_trend(series):
    """OLS slope of FCF vs time, in FCF units per year. series is newest-first.
    Positive slope = cash flow improving. 0.0 when fewer than 3 points (no trend to fit)."""
    ys = list(reversed(series))          # oldest -> newest
    n = len(ys)
    if n < 3:
        return 0.0
    xs = list(range(n))
    mx = (n - 1) / 2.0
    my = sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / var if var else 0.0


def _cell(frame, name):
    """Latest non-NaN value of a row in an oldest->newest frame, else None."""
    try:
        v = frame.loc[name].dropna()
        return None if v.empty else v.iloc[-1]
    except Exception:
        return None


def altman_z(d):
    """Altman Z from the latest fiscal year. Returns (z, missing) — z is None
    when any component is missing. MVE is converted to statement currency."""
    bs = d.get('bs')
    if bs is None or bs.shape[1] < 1:
        return None, 'balance sheet'
    ta = _cell(bs, 'Total Assets')
    ca = _cell(bs, 'Current Assets')
    cl = _cell(bs, 'Current Liabilities')
    re_ = _cell(bs, 'Retained Earnings')
    rev_frame = d.get('inc_s')
    if rev_frame is None or rev_frame.empty:
        rev_frame = bs
    sa = _cell(rev_frame, 'Total Revenue')
    ebit, mve, fx = d.get('ebit'), d.get('mkt_cap'), d.get('fx', 1.0)
    if mve is not None:
        mve = mve / fx                     # price ccy -> statement ccy
    missing = [n for n, v in (('total assets', ta), ('current assets', ca),
                              ('current liabilities', cl), ('retained earnings', re_),
                              ('sales', sa), ('EBIT', ebit), ('market cap', mve)) if v is None]
    if ta is None or ta == 0 or missing:
        return None, ', '.join(missing)
    z = (1.2 * (ca - cl) + 1.4 * re_ + 1.0 * ebit + 0.6 * mve + 0.999 * sa) / ta
    return z, None


def f_score(d):
    """Piotroski F-Score 0-9 from the two latest fiscal years. Returns (score, missing) —
    score is None when a component is missing (no partial scores, no silent passes)."""
    bs, inc = d.get('bs'), d.get('inc_s')
    if bs is None or inc is None or bs.shape[1] < 2 or inc.shape[1] < 2:
        return None, 'need 2 years of statements'
    def v1(frame, name): return _cell(frame, name)
    def v0(frame, name):
        try:
            s = frame.loc[name].dropna()
            return None if len(s) < 2 else s.iloc[-2]
        except Exception:
            return None
    ni1, ta1, ltd1, ca1, cl1, sh1 = v1(inc, 'Net Income'), v1(bs, 'Total Assets'), \
        v1(bs, 'Long Term Debt'), v1(bs, 'Current Assets'), v1(bs, 'Current Liabilities'), \
        v1(bs, 'Ordinary Shares Number') or v1(bs, 'Share Issued')
    ni0, ta0, ltd0, ca0, cl0, sh0 = v0(inc, 'Net Income'), v0(bs, 'Total Assets'), \
        v0(bs, 'Long Term Debt'), v0(bs, 'Current Assets'), v0(bs, 'Current Liabilities'), \
        v0(bs, 'Ordinary Shares Number') or v0(bs, 'Share Issued')
    rev1, rev0 = v1(inc, 'Total Revenue'), v0(inc, 'Total Revenue')
    cogs1, cogs0 = v1(inc, 'Cost Of Revenue'), v0(inc, 'Cost Of Revenue')
    cfo = d.get('cfo')
    missing = [n for n, v in (('NI', ni1), ('TA', ta1), ('LTD', ltd1), ('CA', ca1),
                              ('CL', cl1), ('shares', sh1), ('NI0', ni0), ('TA0', ta0),
                              ('LTD0', ltd0), ('CA0', ca0), ('CL0', cl0), ('shares0', sh0),
                              ('revenue', rev1), ('revenue0', rev0),
                              ('COGS', cogs1), ('COGS0', cogs0), ('CFO', cfo)) if v is None]
    if missing:
        return None, ', '.join(missing)
    s = 0
    s += ni1 > 0                                            # 1 ROA positive
    s += cfo > 0                                            # 2 cash flow positive
    s += (ni1 / ta1) > (ni0 / ta0)                          # 3 ROA improved
    s += cfo > ni1                                          # 4 accruals: cash > income
    s += (ltd1 / ta1) < (ltd0 / ta0)                        # 5 leverage down
    s += (ca1 / cl1) > (ca0 / cl0)                          # 6 liquidity up
    s += sh1 <= sh0                                         # 7 no dilution
    s += (1 - cogs1 / rev1) > (1 - cogs0 / rev0)            # 8 gross margin up
    s += (rev1 / ta1) > (rev0 / ta0)                        # 9 asset turnover up
    return s, None


def epv(d, r):
    """Method 1 -- Earnings Power Value: zero-growth worth of normalised FCF."""
    if not d['fcf_hist']:
        return None
    fcf_norm = median(d['fcf_hist'])
    if fcf_norm <= 0:
        return None
    return (fcf_norm / r) / d['shares'] * d['fx']


def dcf(d, growth, r):
    """Method 2 -- 10yr DCF + terminal value. Same maths as my_work/mini_dcf.py."""
    if not d['fcf_hist']:
        return None
    fcf = median(d['fcf_hist'])
    if fcf <= 0:
        return None
    total = 0.0
    for year in range(1, 11):
        total += fcf * (1 + growth) ** year / (1 + r) ** year
    terminal = fcf * (1 + growth) ** 10 * (1 + TERMINAL_G) / (r - TERMINAL_G)
    total += terminal / (1 + r) ** 10
    return total / d['shares'] * d['fx']


def graham(d):
    """Method 3 -- Graham Number. Self-flags as unreliable for asset-light firms."""
    if d['eps'] is None or d['bvps'] is None or d['eps'] <= 0 or d['bvps'] <= 0:
        return None
    if d['pb'] is not None and d['pb'] > 5:
        return None                        # asset-light: method not meaningful
    return (22.5 * d['eps'] * d['bvps']) ** 0.5


def multiples(d):
    """Method 4 (v0.1 simplification) -- normalised EPS x long-run market multiple 15.
    v0.2 upgrades this to own-history and sector medians."""
    if not d['ni_hist'] or median(d['ni_hist']) <= 0:
        return None
    eps_norm = median(d['ni_hist']) / d['shares'] * d['fx']
    return eps_norm * 15


def fatal_flags(d):
    """Signed fatal flags. Returns (flags, notes): flags PASS the verdict,
    notes are visible data gaps (missing data never silently passes).
    Signed 31 Aug 2026: FCF negative 3 of N = fatal; 2 of N = fatal only
    when the FCF trend (OLS slope) is not positive. Z < 1.8 and F-Score <= 3
    restore the two signed kill-gates that were in the spec but not the code."""
    flags, notes = [], []
    if d['ebit'] is not None and d['interest'] not in (None, 0):
        if d['ebit'] / abs(d['interest']) < 2:
            flags.append('interest coverage < 2x')
    elif d['ebit'] is None or d['interest'] is None:
        notes.append('interest coverage: missing data')

    neg = sum(1 for f in d['fcf_hist'] if f < 0)
    n = len(d['fcf_hist'])
    if n >= 3:
        if neg >= 3:
            flags.append(f'FCF negative {neg} of {n} yrs')
        elif neg == 2 and fcf_trend(d['fcf_hist']) <= 0:
            flags.append(f'FCF negative 2 of {n} yrs, no growth trend')
    elif n > 0:
        notes.append(f'FCF flag: only {n} yrs available, rule needs 3')

    z, z_missing = altman_z(d)
    if z is None:
        notes.append(f'Altman Z: missing {z_missing}')
    elif z < 1.8:
        flags.append(f'Altman Z {z:.2f} < 1.8')

    fs, fs_missing = f_score(d)
    if fs is None:
        notes.append(f'F-Score: missing {fs_missing}')
    elif fs <= 3:
        flags.append(f'F-Score {fs}/9 <= 3')
    return flags, notes


def assess(symbol):
    """Run the full stack for one company. Returns the result bundle."""
    inputs = WATCHLIST[symbol]
    d = fetch(symbol)
    r = discount_rate(inputs)
    g = hist_growth(d['fcf_hist'])

    bear = dcf(d, clamp(g, -0.02, 0.02), r)
    base = dcf(d, clamp(g, 0.0, 0.06), r)     # spec's third scenario; display only in v0.1.1
    bull = dcf(d, clamp(g, 0.02, 0.10), r)
    methods = {'EPV': epv(d, r), 'DCF(bear)': bear,
               'Graham': graham(d), 'Multiples': multiples(d)}
    valid = {k: v for k, v in methods.items() if v is not None}

    flags, hnotes = fatal_flags(d)
    result = {'d': d, 'inputs': inputs, 'rate': r, 'methods': methods,
              'bull': bull, 'base': base, 'flags': flags, 'fair': None,
              'mos': None, 'verdict': 'NO DATA', 'weight': 0.0, 'notes': list(hnotes)}
    if len(valid) < 2:
        result['notes'].append('fewer than 2 valid methods')
        return result

    fair = median(valid.values())
    mos = (fair - d['price']) / fair
    result['fair'], result['mos'] = fair, mos

    # verdict ladder (owner-designed tiers)
    bump = CYCLICAL_MOS_BUMP if inputs['cyclical'] else 0.0
    disagree = max(valid.values()) / min(valid.values()) if min(valid.values()) > 0 else 99
    method_mos = {k: (v - d['price']) / v for k, v in valid.items()}
    thesis_ok = inputs['thesis'] and not inputs['thesis'].startswith('TODO')

    if result['flags'] or mos is None or mos < 0:
        v = 'PASS'
    elif disagree > DISAGREE_CAP:
        v = 'WATCH'
        result['notes'].append(f'methods disagree {disagree:.1f}x > {DISAGREE_CAP} -- capped')
    elif not thesis_ok:
        v = 'WATCH'
        result['notes'].append('no thesis written -- verdict capped')
    elif mos >= BARS['strong'] + bump and sum(1 for m in method_mos.values() if m >= 0.30) >= 3:
        v, result['weight'] = 'STRONG BUY', FULL_POS
    elif mos >= BARS['buy'] + bump and sum(1 for m in method_mos.values() if m >= 0.20) >= 2:
        v, result['weight'] = 'BUY', FULL_POS
    elif mos >= BARS['cautious'] + bump and bull is not None and \
            (bull - d['price']) >= ASYMMETRY * max(d['price'] - (bear or 0), 0.01 * d['price']):
        v, result['weight'] = 'CAUTIOUS BUY', HALF_POS
        result['notes'].append('asymmetry test passed (bull upside >= 3x bear downside)')
    elif mos >= 0:
        v = 'WATCH'
    else:
        v = 'PASS'
    result['verdict'] = v
    return result


def visual(results, width=56):
    """ASCII margin-of-safety view. Everything is scaled as % of current price,
    so the price is always the '|' at 100% and the bar is the method range."""
    print('\nValuation range vs price (each bar = min..max of methods, F = consensus fair value):')
    print(f"{'':10}0%{'':24}100% (price){'':16}200%")
    for res in results:
        if not res['fair']:
            continue
        d, methods = res['d'], {k: v for k, v in res['methods'].items() if v}
        # convert everything to % of price, then to a character column (0..200% -> 0..width)
        col = lambda pct: min(int(pct / 200 * width), width - 1)
        lo = col(min(methods.values()) / d['price'] * 100)
        hi = col(max(methods.values()) / d['price'] * 100)
        row = [' '] * width
        for c in range(lo, hi + 1):
            row[c] = '='                      # the method range bar
        row[col(res['fair'] / d['price'] * 100)] = 'F'   # consensus fair value
        row[col(100)] = '|'                   # current price marker
        mos = f"{res['mos']*100:+.0f}%"
        print(f"{d['symbol']:8} [{''.join(row)}] MoS {mos}")


def report(results):
    line = '-' * 100
    print(line)
    print(f"{'ticker':8} {'price':>10} {'fair val':>10} {'MoS':>7}  {'verdict':<13} {'weight':>6}  flags/notes")
    print(line)
    for res in results:
        d = res['d']
        fair = f"{res['fair']:.2f}" if res['fair'] else '--'
        mos = f"{res['mos']*100:.0f}%" if res['mos'] is not None else '--'
        issues = '; '.join(res['flags'] + res['notes']) or '-'
        print(f"{d['symbol']:8} {d['price']:>10.2f} {fair:>10} {mos:>7}  {res['verdict']:<13} {res['weight']*100:>5.0f}%  {issues}")
    print(line)
    print('\nPer-method fair values (price currency):')
    for res in results:
        d = res['d']
        parts = ', '.join(f'{k}={v:.2f}' if v else f'{k}=n/a' for k, v in res['methods'].items())
        slope = fcf_trend(d['fcf_hist']) * d['fx']
        base = f"{res['base']:.2f}" if res['base'] else 'n/a'
        bull = f"{res['bull']:.2f}" if res['bull'] else 'n/a'
        print(f"  {d['symbol']:8} r={res['rate']*100:.0f}%  {parts}, Base DCF={base}, Bull DCF={bull}, FCF slope={slope:+,.0f}/yr")


if __name__ == '__main__':
    print('Valuation Engine v0.1 -- live run\n')
    results = [assess(s) for s in WATCHLIST]
    report(results)
    visual(results)
    print('\nNOTE: all theses owner-signed 25 Aug 2026; positions sized per signed-off caps (8%/4%);')
    print('risk-score weighting engine arrives in v0.2. Not financial advice.')
