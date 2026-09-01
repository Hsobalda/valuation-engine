"""watchlist_ext.py -- NEW per-name configuration for the v0.2 draft.

The moat/cyclicality/thesis inputs stay in engine_v01.WATCHLIST (one source
of truth, owner-signed). This file adds only v0.2 draft extensions:

  sector : display + sector-cap bucket for the sizing engine
  comps  : owner-researched peer multiples for Method 4 (issue #6).
           Keeping them HERE (hand-configured, not scraped) preserves the
           "semi" in semi-automatic: peer sets are a judgement call.
           Sources: TSCO comps from the signed TSCO thesis (25 Aug 2026).

DRAFT -- owner should confirm/correct each entry before sign-off.
"""

EXTENSIONS = {
    'TSCO.L': {'sector': 'Grocery Retail',
               'comps': {'ev_ebitda': [7.0, 7.7, 8.3]},      # KR, AHODR.AS, SBRY.L
               },
    'KGF.L':  {'sector': 'DIY Retail',
               # owner thesis: capex/D&A 0.61 is lease geometry, IFRS 16 applies
               },
    'IMB.L':  {'sector': 'Tobacco'},
    'EZJ.L':  {'sector': 'Airlines'},
    'PEP':    {'sector': 'Beverages & Snacks'},
    'SPOT':   {'sector': 'Streaming'},
    'T':      {'sector': 'Telecoms'},
}
