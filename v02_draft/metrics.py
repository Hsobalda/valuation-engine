"""metrics.py -- quality, health and earnings-reality metrics (COMPARISON 1.2-1.4).

Closes the specced-but-uncoded fatal flags (Piotroski F-Score, Altman Z) and
the VALUE_TRAP_CHECKS Layer 4 checks (accruals, dilution, FCF-vs-NI backing).
All functions take a bundle (see data.py) and return drillable results, never
a bare float without provenance.
"""

from __future__ import annotations

from statistics import mean, pstdev

from .params import COVERAGE_KILL, FSCORE_KILL, ALTMAN_Z_KILL


# ---------------------------------------------------------------------------
# Coverage / leverage primitives
# ---------------------------------------------------------------------------
def interest_coverage(bundle):
    ebit, interest = bundle.get('ebit'), bundle.get('interest')
    if ebit is None or interest in (None, 0):
        return None
    return ebit / abs(interest)


def net_debt_to_ebitda(bundle):
    debt, cash = bundle.get('total_debt'), bundle.get('cash')
    ebitda = bundle.get('ebitda')
    if ebitda is None or ebitda <= 0:
        return None
    nd = (debt or 0.0) - (cash or 0.0)
    return nd / ebitda


def debt_to_equity(bundle):
    debt, eq = bundle.get('total_debt'), bundle.get('total_equity')
    if not eq:
        return None
    return (debt or 0.0) / eq


# ---------------------------------------------------------------------------
# Piotroski F-Score (issue: spec'd as fatal flag, uncoded in v0.1)
# ---------------------------------------------------------------------------
def fscore(bundle):
    """Standard 9-point F-Score on the two latest annual periods.
    Returns {'score': int, 'points': [(criterion, 0|1, reason)], 'available': bool}.
    Histories are newest-first."""
    out = {'score': None, 'points': [], 'available': False}

    def h(key):
        v = bundle.get(key) or []
        return v if len(v) >= 2 else None

    ta, ltd = h('total_assets_hist'), h('long_term_debt_hist')
    ca, cl = h('current_assets_hist'), h('current_liab_hist')
    rev, cogs = h('revenue_hist'), h('cogs_hist')
    ni, ocf, sh = h('ni_hist'), h('ocf_hist'), h('shares_hist')
    needed = [ta, ni, ocf, rev]
    if any(x is None for x in needed):
        out['points'] = [('insufficient history', 0,
                          'F-Score needs 2 yrs of assets, NI, OCF, revenue')]
        return out
    out['available'] = True

    ta0, ta1 = ta[0], ta[1]
    roa0 = ni[0] / ta0 if ta0 else 0.0
    roa1 = ni[1] / ta1 if ta1 else 0.0

    def pt(name, cond, why):
        out['points'].append((name, 1 if cond else 0, why))

    # Profitability
    pt('ROA > 0', roa0 > 0, f'ROA {roa0*100:.1f}%')
    pt('OCF > 0', ocf[0] > 0, f'OCF {ocf[0]:,.0f}')
    pt('ROA rising', roa0 > roa1, f'{roa1*100:.1f}% -> {roa0*100:.1f}%')
    pt('accruals: OCF/TA > ROA', (ocf[0] / ta0 if ta0 else 0) > roa0,
       f'OCF/TA {(ocf[0]/ta0)*100 if ta0 else 0:.1f}% vs ROA {roa0*100:.1f}%')
    # Leverage / liquidity / source of funds
    if ltd and ta:
        pt('leverage falling', (ltd[0] / ta0 if ta0 else 0) < (ltd[1] / ta1 if ta1 else 0),
           f'LTD/TA {(ltd[1]/ta1 if ta1 else 0)*100:.1f}% -> {(ltd[0]/ta0 if ta0 else 0)*100:.1f}%')
    else:
        pt('leverage falling', False, 'no LTD history')
    if ca and cl:
        cr0 = ca[0] / cl[0] if cl[0] else 99
        cr1 = ca[1] / cl[1] if cl[1] else 99
        pt('current ratio rising', cr0 > cr1, f'{cr1:.2f} -> {cr0:.2f}')
    else:
        pt('current ratio rising', False, 'no working-capital history')
    if sh:
        pt('no dilution', sh[0] <= sh[1] * 1.01, f'shares {sh[1]:,.0f} -> {sh[0]:,.0f}')
    else:
        pt('no dilution', False, 'no share-count history')
    # Operating efficiency
    if rev and cogs is not None:
        gm0 = (rev[0] - cogs[0]) / rev[0] if rev[0] else 0
        gm1 = (rev[1] - cogs[1]) / rev[1] if rev[1] else 0
        pt('gross margin rising', gm0 > gm1, f'{gm1*100:.1f}% -> {gm0*100:.1f}%')
    else:
        pt('gross margin rising', False, 'no COGS history')
    if rev and ta:
        pt('asset turnover rising', rev[0] / ta0 > rev[1] / ta1,
           f'{rev[1]/ta1:.2f} -> {rev[0]/ta0:.2f}')
    else:
        pt('asset turnover rising', False, 'no history')

    out['score'] = sum(p for _, p, _ in out['points'])
    return out


# ---------------------------------------------------------------------------
# Altman Z (issue: spec'd as fatal flag, uncoded in v0.1)
# ---------------------------------------------------------------------------
def altman_z(bundle):
    """Altman Z (manufacturing) and Z'' (non-manufacturer, no sales term).
    Returns {'z': float, 'variant': str, 'terms': {...}, 'zone': str,
             'available': bool, 'missing': [..]}."""
    ta = bundle.get('total_assets')
    mkt_cap_fin = None
    if bundle.get('mkt_cap'):
        # Yahoo's marketCap is in MAJOR price-currency units (GBP, not GBp),
        # while `fx` converts statement-currency -> price-currency units
        # (x100 for London). Statement-currency market cap is therefore:
        # mkt_cap / fx, then x100 back for GBp-priced names.
        gbp_factor = 100.0 if bundle.get('price_ccy') == 'GBp' else 1.0
        mkt_cap_fin = bundle['mkt_cap'] / (bundle.get('fx') or 1.0) * gbp_factor
    need = {'total_assets': ta, 'current_assets': bundle.get('current_assets'),
            'current_liab': bundle.get('current_liab'),
            'retained_earnings': bundle.get('retained_earnings'),
            'ebit': bundle.get('ebit'), 'mkt_cap': mkt_cap_fin,
            'total_debt': bundle.get('total_debt'),
            'revenue': bundle.get('revenue')}
    missing = [k for k, v in need.items() if v is None]
    if missing or not ta:
        return {'z': None, 'variant': None, 'terms': {}, 'zone': 'unavailable',
                'available': False, 'missing': missing}
    wc = need['current_assets'] - need['current_liab']
    tl = need['total_debt']
    terms = {
        'WC/TA': 1.2 * wc / ta,
        'RE/TA': 1.4 * need['retained_earnings'] / ta,
        'EBIT/TA': 3.3 * need['ebit'] / ta,
        'MVE/TL': 0.6 * need['mkt_cap'] / tl if tl else 99.0,
    }
    z = sum(terms.values())
    z += 1.0 * need['revenue'] / ta           # sales term: manufacturing Z
    # Z'' (non-manufacturer variant) reported alongside for the risk panel;
    # the kill-gate uses the classic manufacturing Z for spec parity.
    z2 = 6.56 * wc / ta + 3.26 * need['retained_earnings'] / ta \
        + 6.72 * need['ebit'] / ta \
        + (1.05 * need['mkt_cap'] / tl if tl else 99.0)
    zone = 'safe' if z >= 3.0 else ('grey' if z >= ALTMAN_Z_KILL else 'distress')
    return {'z': z, 'z_double_prime': z2, 'variant': 'manufacturing',
            'terms': terms, 'zone': zone, 'available': True, 'missing': []}


# ---------------------------------------------------------------------------
# Earnings-reality checks (VALUE_TRAP_CHECKS Layer 4)
# ---------------------------------------------------------------------------
def accruals_ratio(bundle):
    """Sloan-style accruals: (NI - OCF) / total assets, latest year.
    Positive = earnings running ahead of cash (warning)."""
    ni = (bundle.get('ni_hist') or [None])[0]
    ocf = (bundle.get('ocf_hist') or [None])[0]
    ta = bundle.get('total_assets')
    if ni is None or ocf is None or not ta:
        return None
    return (ni - ocf) / ta


def fcf_ni_backing(bundle):
    """Median FCF / median NI over overlapping history. ~>=1 = cash backs
    earnings; persistently <0.8 = paper profits."""
    fcf, ni = bundle.get('fcf_hist') or [], bundle.get('ni_hist') or []
    n = min(len(fcf), len(ni))
    if n < 2:
        return None
    med = mean(sorted(x / y for x, y in zip(fcf[:n], ni[:n]) if y))
    return med


def dilution_annual(bundle):
    """Annualised share-count change across the share history (negative =
    buybacks). Newest-first."""
    sh = bundle.get('shares_hist') or []
    if len(sh) < 2 or not sh[-1]:
        return None
    years = len(sh) - 1
    return (sh[0] / sh[-1]) ** (1 / years) - 1


def fcf_stability(bundle):
    """Coefficient of variation of FCF history (lower = steadier).
    None if <3 yrs."""
    fcf = [f for f in (bundle.get('fcf_hist') or []) if f is not None]
    if len(fcf) < 3 or mean(fcf) <= 0:
        return None
    return pstdev(fcf) / mean(fcf)


# ---------------------------------------------------------------------------
# Fatal flags (v0.1 spec parity: coverage, neg-FCF, F-Score, Altman Z)
# ---------------------------------------------------------------------------
def fatal_flags(bundle):
    flags = []
    cov = interest_coverage(bundle)
    if cov is not None and cov < COVERAGE_KILL:
        flags.append(f'interest coverage {cov:.1f}x < {COVERAGE_KILL}x')
    fcf_hist = bundle.get('fcf_hist') or []
    neg = sum(1 for f in fcf_hist if f < 0)
    if len(fcf_hist) >= 3 and neg >= 2:
        flags.append(f'FCF negative in {neg} of {len(fcf_hist)} yrs')
    fs = fscore(bundle)
    if fs['available'] and fs['score'] <= FSCORE_KILL:
        flags.append(f'F-Score {fs["score"]}/9 <= {FSCORE_KILL}')
    az = altman_z(bundle)
    if az['available'] and az['z'] < ALTMAN_Z_KILL:
        flags.append(f'Altman Z {az["z"]:.2f} < {ALTMAN_Z_KILL} ({az["zone"]})')
    return flags
