"""data.py -- single hardened data layer (COMPARISON items 0.2, 0.3, 1.5 feed).

Everything downstream consumes a plain dict "bundle" (JSON-serialisable), so:
  * tests run on fixtures with the network off,
  * snapshots can be cached, reloaded and diffed,
  * yfinance schema drift is normalised at exactly one boundary.

Bundle schema (statement-currency fields unless suffixed _ps):
    symbol, name, sector, industry, price, price_ccy, fin_ccy, fx,
    shares, eps_ps, bvps_ps, pb, div_yield (FRACTION, e.g. 0.043), mkt_cap,
    ebit, interest, revenue, ebitda, tax,
    total_assets, total_equity, total_debt, cash, current_assets,
    current_liab, retained_earnings, long_term_debt,
    *_hist lists are NEWEST-FIRST, e.g. fcf_hist, ni_hist, ocf_hist,
    capex_hist (absolute), da_hist, lease_principal_hist, shares_hist,
    total_assets_hist, long_term_debt_hist, current_assets_hist,
    current_liab_hist, revenue_hist, cogs_hist.
    source ('live'|'snapshot'), fetched_at, approximate (bool, demo fixtures).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

# ---------------------------------------------------------------------------
# yfinance row-label candidates. Yahoo renames rows across versions/markets;
# probe in order and take the first hit (COMPARISON 0.2).
# ---------------------------------------------------------------------------
_ROWS = {
    'fcf_hist': ['Free Cash Flow'],
    'ni_hist': ['Net Income', 'Net Income Common Stockholders'],
    'ocf_hist': ['Operating Cash Flow', 'Total Cash From Operating Activities'],
    'capex_hist': ['Capital Expenditure'],
    'da_hist': ['Depreciation And Amortization',
                'Depreciation, Amortization and Accretion, Net'],
    # IFRS 16 (issue #8): lease principal repayments sit in financing
    'lease_principal_hist': ['Principal Repayments on Finance Leases',
                             'Finance Lease Principal Payments',
                             'Principal Payments under Finance Leases'],
    'shares_hist': ['Diluted Average Shares'],
    'total_assets_hist': ['Total Assets'],
    'long_term_debt_hist': ['Long Term Debt'],
    'current_assets_hist': ['Current Assets', 'Total Current Assets'],
    'current_liab_hist': ['Current Liabilities', 'Total Current Liabilities'],
    'revenue_hist': ['Total Revenue'],
    'cogs_hist': ['Cost Of Revenue', 'Cost of Goods and Services Sold'],
}

_SINGLE = {   # statement field -> row-label candidates (probed across frames)
    'ebit': ['EBIT', 'Operating Income'],
    'interest': ['Interest Expense'],
    'revenue': ['Total Revenue'],
    'ebitda': ['EBITDA'],
    'tax': ['Tax Provision', 'Income Tax Expense'],
    'total_assets': ['Total Assets'],
    'total_equity': ['Stockholders Equity', 'Total Equity Gross Minority Interest'],
    'total_debt': ['Total Debt'],
    'cash': ['Cash And Cash Equivalents'],
    'current_assets': ['Current Assets', 'Total Current Assets'],
    'current_liab': ['Current Liabilities', 'Total Current Liabilities'],
    'retained_earnings': ['Retained Earnings'],
    'long_term_debt': ['Long Term Debt'],
}


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def normalize_div_yield(raw):
    """yfinance has shipped BOTH semantics for info['dividendYield']:
    percent (4.3) and fraction (0.043). Normalise to a fraction."""
    if raw is None or raw <= 0:
        return None
    # Heuristic: percent form (4.3) is almost always > 0.25; fraction form
    # (0.043) is almost always <= 0.25 (a 25%+ yield is not a yield, it is a
    # liquidation). Ambiguity in [0.25, 1.0] resolved as percent; the audit
    # flags implausible yields anyway.
    return raw / 100.0 if raw > 0.25 else float(raw)


def _series(df, candidates):
    """Newest-first list from a yfinance statement frame, or []."""
    if df is None or df.empty:
        return []
    for label in candidates:
        if label in df.index:
            return [float(v) for v in df.loc[label].dropna().tolist()]
    return []


def _single(df_map, candidates):
    """Latest value of a statement row, or None."""
    for label in candidates:
        for key in ('inc', 'bs', 'cf'):
            vals = _series(df_map.get(key), [label])
            if vals:
                return vals[0]
    return None


def fx_to_price_ccy(fin_ccy, price_ccy, fx_getter=None):
    """Multiplier statement-currency -> price-currency. London quirk: prices
    in pence (GBp) but per-share fields in pounds."""
    if fin_ccy is None or price_ccy is None or fin_ccy == price_ccy:
        return 1.0
    target = 'GBP' if price_ccy == 'GBp' else price_ccy
    mult = 100.0 if price_ccy == 'GBp' else 1.0
    if fin_ccy == target:
        return mult
    pair = f'{fin_ccy}{target}=X'
    if fx_getter is not None:
        rate = fx_getter(pair)
        if rate:
            return rate * mult
    raise ValueError(f'No FX rate for {fin_ccy}->{target} (pair {pair})')


def fetch_bundle(symbol, yf=None):
    """Build the bundle from live yfinance. `yf` is injected so tests can pass
    a stub; production calls bind the real module at import time (see run.py)."""
    if yf is None:                                    # pragma: no cover
        import yfinance as _yf
        yf = _yf
    t = yf.Ticker(symbol)
    info = t.info or {}
    df_map = {'cf': t.cashflow, 'inc': t.income_stmt, 'bs': t.balance_sheet}

    bundle = {
        'symbol': symbol,
        'name': info.get('shortName', symbol),
        'sector': info.get('sector'),
        'industry': info.get('industry'),
        'price': info.get('currentPrice') or info.get('regularMarketPrice'),
        'price_ccy': info.get('currency'),
        'fin_ccy': info.get('financialCurrency'),
        'shares': info.get('sharesOutstanding'),
        'eps_ps': info.get('trailingEps'),
        'bvps_ps': info.get('bookValue'),
        'pb': info.get('priceToBook'),
        'div_yield': normalize_div_yield(info.get('dividendYield')),
        'mkt_cap': info.get('marketCap'),
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'source': 'live',
        'approximate': False,
    }
    # London per-share quirk: price in pence, per-share fields in pounds.
    if bundle['price_ccy'] == 'GBp':
        for k in ('eps_ps', 'bvps_ps'):
            if bundle[k] is not None:
                bundle[k] *= 100.0
    for key, labels in _ROWS.items():
        bundle[key] = _series(df_map.get(df_for(key)), labels)
    for key, labels in _SINGLE.items():
        bundle[key] = _single(df_map, labels)
    bundle['fx'] = fx_to_price_ccy(
        bundle['fin_ccy'], bundle['price_ccy'],
        fx_getter=lambda p: (yf.Ticker(p).info or {}).get('regularMarketPrice'))
    return bundle


def df_for(hist_key):
    return {'fcf_hist': 'cf', 'ni_hist': 'inc', 'ocf_hist': 'cf',
            'capex_hist': 'cf', 'da_hist': 'cf', 'lease_principal_hist': 'cf',
            'shares_hist': 'inc', 'total_assets_hist': 'bs',
            'long_term_debt_hist': 'bs', 'current_assets_hist': 'bs',
            'current_liab_hist': 'bs', 'revenue_hist': 'inc',
            'cogs_hist': 'inc'}[hist_key]


# ---------------------------------------------------------------------------
# Snapshots (COMPARISON 0.3)
# ---------------------------------------------------------------------------
def save_snapshot(bundle, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, indent=1, default=str)


def load_snapshot(path):
    with open(path, encoding='utf-8') as f:
        b = json.load(f)
    b['source'] = 'snapshot'
    return b


# ---------------------------------------------------------------------------
# Data-quality audit (COMPARISON 0.2)
# ---------------------------------------------------------------------------
def _amt(x):
    """Human-scale a statement amount for the audit panel."""
    if x is None:
        return 'n/a'
    for div, suf in ((1e9, 'bn'), (1e6, 'm')):
        if abs(x) >= div:
            return f'{x/div:,.1f}{suf}'
    return f'{x:,.0f}'


def audit(bundle):
    """List of (check, status, detail). status in {'OK','WARN','FAIL'}.
    FAIL means at least one method is unreliable or the run is not usable."""
    checks = []

    def add(name, ok, warn, detail):
        checks.append((name, 'OK' if ok else ('WARN' if warn else 'FAIL'), detail))

    fcf_n = len(bundle.get('fcf_hist') or [])
    add('fcf history', fcf_n >= 4, fcf_n >= 2,
        f'{fcf_n} yrs (want >=4 for medians)')
    ni_n = len(bundle.get('ni_hist') or [])
    add('net income history', ni_n >= 4, ni_n >= 2, f'{ni_n} yrs')
    add('price', bundle.get('price') is not None, False,
        f"{bundle.get('price')} {bundle.get('price_ccy') or ''}".strip())
    add('per-share data', bundle.get('eps_ps') is not None,
        bundle.get('bvps_ps') is not None,
        f"eps={bundle.get('eps_ps')} bvps={bundle.get('bvps_ps')}")
    add('coverage inputs', bundle.get('ebit') is not None
        and bundle.get('interest') not in (None, 0), False,
        f"ebit={_amt(bundle.get('ebit'))} interest={_amt(bundle.get('interest'))}")
    add('capex/D&A rows', bool(bundle.get('capex_hist')) and
        bool(bundle.get('da_hist')), bool(bundle.get('capex_hist')),
        'owner-earnings fix needs both' if not
        (bundle.get('capex_hist') and bundle.get('da_hist')) else 'present')
    add('OCF rows', bool(bundle.get('ocf_hist')), False,
        'no OCF rows: accruals check degrades' if not bundle.get('ocf_hist')
        else 'present')
    add('balance-sheet rows', all(bundle.get(k) is not None for k in
        ('total_assets', 'current_assets', 'current_liab',
         'retained_earnings', 'total_debt')), any(bundle.get(k) is not None
        for k in ('total_assets', 'total_debt')),
        'Altman Z + leverage need the full set' if not all(
        bundle.get(k) is not None for k in
        ('total_assets', 'current_assets', 'current_liab',
         'retained_earnings', 'total_debt')) else 'present')
    dy = bundle.get('div_yield')
    add('dividend yield sane', dy is None or 0 < dy < 0.15, True,
        f'{dy*100:.1f}%' if dy else 'no dividend')
    fetched = bundle.get('fetched_at', '')
    add('snapshot freshness', bool(fetched), True,
        f'fetched {fetched[:10] if fetched else "unknown"}')
    if bundle.get('approximate'):
        add('demo fixture', False, True,
            'approximate numbers reconstructed from reports/*.md -- demo only')
    return checks


def audit_summary(checks):
    fails = [c for c in checks if c[1] == 'FAIL']
    warns = [c for c in checks if c[1] == 'WARN']
    return f"{len(checks)-len(fails)-len(warns)} ok, {len(warns)} warn, {len(fails)} fail"
