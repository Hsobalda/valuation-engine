"""valuation.py -- the v0.2 draft method stack (COMPARISON items 1.1, 1.5-1.9).

Method selection and the verdict rules stay v0.1's; what changes:
  * FCF input can be owner earnings (OCF - min(capex, D&A)) [issue #1]
  * lease principal repayments deducted where exposed [issue #8]
  * Method 4 multiple = owner-configured peer median, fallback 15x [issue #6]
  * reverse DCF promoted into the core: implied growth, implied required
    return, break-even perpetual decline [issue #2 + #3]
  * deterministic sensitivity grid + exit-multiple terminal cross-check
"""

from __future__ import annotations

from statistics import median

from . import params as P


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def hist_growth(series):
    """Annualised growth oldest->newest of a newest-first history (v0.1 maths)."""
    if len(series) < 2 or series[-1] <= 0 or series[0] <= 0:
        return 0.0
    years = len(series) - 1
    return (series[0] / series[-1]) ** (1 / years) - 1


def discount_rate(inputs):
    r = P.BASE_RATE
    if inputs.get('cyclical'):
        r += P.CYCLICAL_BUMP
    if inputs.get('moat') == 'wide':
        r -= P.WIDE_MOAT_DISC
    return max(r, P.RATE_FLOOR)


# ---------------------------------------------------------------------------
# FCF inputs: owner earnings + IFRS 16 (issues #1, #8)
# ---------------------------------------------------------------------------
def owner_fcf_hist(bundle):
    """OCF - min(capex, D&A) per year where all three rows exist.
    Falls back to headline FCF history. Returns (series, provenance).
    Yahoo reports capex NEGATIVE (cash outflow): deduct its MAGNITUDE.
    (Regression, 2 Sep 2026: live runs doubled FCF inputs -- e.g. T fair
    value ~$58 vs ~$30 -- because min(-20, 20) added capex back.)"""
    ocf = bundle.get('ocf_hist') or []
    capex = [abs(c) for c in (bundle.get('capex_hist') or [])]
    da = [abs(d) for d in (bundle.get('da_hist') or [])]
    n = min(len(ocf), len(capex), len(da))
    if n >= 2:
        series = [o - min(c, d) for o, c, d in zip(ocf[:n], capex[:n], da[:n])]
        if len(series) >= 2:
            return series[:4], 'owner earnings = OCF - min(capex, D&A)'
    return (bundle.get('fcf_hist') or [])[:4], 'headline FCF (OCF/capex rows unavailable)'


def lease_adjust(series, bundle):
    """Deduct IFRS 16 lease principal repayments (newest-first) from an
    FCF series. Returns (adjusted_series, deduction_last_yr, applied)."""
    lease = bundle.get('lease_principal_hist') or []
    if not lease or not P.LEASE_ADJUST:
        return series, 0.0, False
    # repayments are usually reported negative in financing activities
    n = min(len(series), len(lease))
    adj = []
    for i in range(n):
        ded = abs(lease[i])
        adj.append(series[i] - ded)
    deduction = abs(lease[0])
    return adj, deduction, True


# ---------------------------------------------------------------------------
# The four methods (v0.1 selection, upgraded inputs)
# ---------------------------------------------------------------------------
def epv(bundle, r, fcf_series=None):
    if fcf_series is None:
        fcf_series, _ = owner_fcf_hist(bundle)
    if not fcf_series:
        return None
    fcf_norm = median(fcf_series)
    if fcf_norm <= 0 or not bundle.get('shares'):
        return None
    return (fcf_norm / r) / bundle['shares'] * (bundle.get('fx') or 1.0)


def dcf(bundle, growth, r, fcf_series=None, terminal_g=None):
    """10-yr DCF + Gordon terminal (v0.1 maths)."""
    if fcf_series is None:
        fcf_series, _ = owner_fcf_hist(bundle)
    if not fcf_series:
        return None
    fcf = median(fcf_series)
    if fcf <= 0 or not bundle.get('shares'):
        return None
    tg = P.TERMINAL_G if terminal_g is None else terminal_g
    total = sum(fcf * (1 + growth) ** y / (1 + r) ** y for y in range(1, 11))
    terminal = fcf * (1 + growth) ** 10 * (1 + tg) / (r - tg)
    return (total + terminal / (1 + r) ** 10) / bundle['shares'] * (bundle.get('fx') or 1.0)


def terminal_share(bundle, growth, r, fcf_series=None):
    """PV(terminal) / PV(total) for the Gordon DCF: how much of the value
    rests on the assumption after year 10."""
    if fcf_series is None:
        fcf_series, _ = owner_fcf_hist(bundle)
    if not fcf_series:
        return None
    fcf = median(fcf_series)
    if fcf <= 0 or r <= P.TERMINAL_G:
        return None
    explicit = sum(fcf * (1 + growth) ** y / (1 + r) ** y for y in range(1, 11))
    term = fcf * (1 + growth) ** 10 * (1 + P.TERMINAL_G) / (r - P.TERMINAL_G)
    pv_term = term / (1 + r) ** 10
    tot = explicit + pv_term
    return pv_term / tot if tot > 0 else None


def dcf_exit_multiple(bundle, growth, r, exit_mult=None, fcf_series=None):
    """Cross-check: same explicit 10 years but terminal value = exit EV/EBITDA
    multiple on year-10 EBITDA (equity value approx: + net cash adjustment)."""
    if bundle.get('ebitda') is None or bundle.get('ebitda') <= 0:
        return None
    if fcf_series is None:
        fcf_series, _ = owner_fcf_hist(bundle)
    if not fcf_series or not bundle.get('shares'):
        return None
    fcf = median(fcf_series)
    em = P.EXIT_EBITDA_MULT if exit_mult is None else exit_mult
    explicit = sum(fcf * (1 + growth) ** y / (1 + r) ** y for y in range(1, 11))
    ebitda10 = bundle['ebitda'] * (1 + growth) ** 10
    ev = explicit + em * ebitda10 / (1 + r) ** 10
    net_debt = (bundle.get('total_debt') or 0.0) - (bundle.get('cash') or 0.0)
    equity = ev - net_debt
    return equity / bundle['shares'] * (bundle.get('fx') or 1.0)


def graham(bundle):
    eps, bvps = bundle.get('eps_ps'), bundle.get('bvps_ps')
    pb = bundle.get('pb')
    if eps is None or bvps is None or eps <= 0 or bvps <= 0:
        return None
    if pb is not None and pb > 5:
        return None                      # asset-light: method not meaningful
    return (22.5 * eps * bvps) ** 0.5


def multiple_used(inputs):
    """Peer-median multiple if the owner configured comps, else the v0.1 flat
    15x. Always returns (multiple, source) so it can be printed, never silent."""
    comps = inputs.get('comps') or {}
    mults = comps.get('pe') or comps.get('ev_ebitda') or []
    mults = [m for m in mults if m and m > 0]
    if mults:
        kind = 'pe' if comps.get('pe') else 'ev_ebitda'
        return median(mults), f"owner-configured peer median {kind} of {len(mults)}"
    return P.FLAT_MULTIPLE, 'v0.1 flat long-run multiple'


def multiples(bundle, inputs):
    if not bundle.get('ni_hist') or not bundle.get('shares'):
        return None
    ni_med = median(bundle['ni_hist'])
    if ni_med <= 0:
        return None
    eps_norm = ni_med / bundle['shares'] * (bundle.get('fx') or 1.0)
    mult, _src = multiple_used(inputs)
    return eps_norm * mult


# ---------------------------------------------------------------------------
# Reverse DCF (issue #2 headline; decliner mode #3 via perpetual solver)
# ---------------------------------------------------------------------------
def implied_growth(bundle, r, price, fcf_series=None):
    """Growth rate g at which the Gordon DCF equals today's price."""
    if fcf_series is None:
        fcf_series, _ = owner_fcf_hist(bundle)
    if not fcf_series or not price:
        return None
    lo, hi = P.IMPLIED_G_BOUNDS
    best = None
    for _ in range(90):
        mid = (lo + hi) / 2
        v = dcf(bundle, mid, r, fcf_series)
        if v is None:
            return None
        best = mid
        if v < price:
            lo = mid
        else:
            hi = mid
    return best


def implied_required_return(bundle, price, fcf_series=None):
    """Discount rate r (at g = 0) at which the DCF equals today's price:
    the return the market is offering you if the company never grows."""
    if fcf_series is None:
        fcf_series, _ = owner_fcf_hist(bundle)
    if not fcf_series or not price:
        return None
    lo, hi = P.IMPLIED_R_BOUNDS
    if dcf(bundle, 0.0, lo, fcf_series) is None:
        return None
    best = None
    for _ in range(90):
        mid = (lo + hi) / 2
        v = dcf(bundle, 0.0, mid, fcf_series)
        if v is None:
            return None
        best = mid
        if v > price:          # higher r -> lower value; value above price -> r up
            lo = mid
        else:
            hi = mid
    return best


def perpetual_value(fcf0, r, decay):
    """EPV-with-decay: sum_{t>=1} FCF0*(1+decay)^t / (1+r)^t
       = FCF0*(1+decay)/(r-decay), valid for decay > -(1+r)... use r > decay."""
    if r <= decay:
        return None
    return fcf0 * (1 + decay) / (r - decay)


def breakeven_decline(bundle, r, price, fcf_series=None):
    """Structural-decliner mode (issue #3): the CONSTANT annual decline at
    which the PERPETUAL decay value equals today's price. The IMB '-5.3%/yr'
    break-even maths, automated. None if price exceeds the flat-FCF value
    (i.e. no decline is priced)."""
    if fcf_series is None:
        fcf_series, _ = owner_fcf_hist(bundle)
    if not fcf_series or not price or not bundle.get('shares'):
        return None
    fcf0 = median(fcf_series)
    if fcf0 <= 0:
        return None
    per_share = lambda d: (perpetual_value(fcf0, r, d) or 0) / bundle['shares'] \
        * (bundle.get('fx') or 1.0)
    flat = per_share(0.0)
    if price >= flat:
        return None                     # no decline priced: perpetual solver n/a
    lo, hi = -0.99, 0.0                 # bisection on decay
    for _ in range(90):
        mid = (lo + hi) / 2
        if per_share(mid) > price:
            hi = mid                    # worth more than price -> more decline needed
        else:
            lo = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------------------
# Sensitivity grid (item 1.9)
# ---------------------------------------------------------------------------
def sensitivity_grid(bundle, growth, rates=None, terminals=None, fcf_series=None):
    """{rate: {terminal_g: fair_value_per_share}} for the bear DCF."""
    rates = P.SENS_RATES if rates is None else rates
    terminals = P.SENS_TERMINAL if terminals is None else terminals
    grid = {}
    for r in rates:
        row = {}
        for tg in terminals:
            row[tg] = dcf(bundle, growth, r, fcf_series, terminal_g=tg)
        grid[r] = row
    return grid
