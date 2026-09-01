# v0.2 DRAFT -- benchmark-driven upgrade, awaiting owner review

**Status: DRAFT. Nothing here touches `engine_v01.py`.** This package implements the improvement list from [`docs/COMPARISON.md`](../docs/COMPARISON.md) (itself the survey of comparable repos). Every parameter added beyond the v0.1 locked set lives in `params.py` Section B, marked `DRAFT -- OWNER SIGN-OFF REQUIRED`.

```bash
python -m v02_draft.run                      # offline run on cached snapshots
python -m v02_draft.run T IMB.L --panels --grid --size
python -m v02_draft.run --live               # fetch Yahoo, cache to snapshots/
python -m v02_draft.run --journal journal/journal.jsonl
python -m pytest v02_draft/tests -q          # 66 tests, no network
```

## Module map (what implements which comparison item)

| Module | Implements | VERSION_PLAN issue |
|---|---|---|
| `data.py` | hardened single fetch layer, yfinance field normalisation (dividendYield percent-vs-fraction, renamed rows), **snapshot cache + offline replay**, **data-quality audit panel** | COMPARISON 0.2, 0.3 |
| `metrics.py` | **Piotroski F-Score** (9 criteria, drillable), **Altman Z** (+ Z'' reported alongside), **Sloan accruals**, FCF/NI backing, dilution trend, FCF stability, completed fatal-flag set | spec'd-uncoded flags; Layer 4 |
| `valuation.py` | **owner earnings** (OCF − min(capex, D&A)), **IFRS 16 lease adjustment**, peer-median Method 4 with printed provenance, **reverse DCF: implied growth / implied required return / break-even perpetual decline** (decliner mode), **sensitivity grid**, **exit-multiple cross-check**, terminal-share-of-value | #1, #2, #3, #6, #8 + 1.9 |
| `risk.py` | **risk panel**: six continuous subscores (0–100, distance-from-danger curves), plain-language reasons, composite for ordering only, kill-gates preserved underneath | #5 |
| `verdict.py` | **wrong-model refusal** (banks/insurers, pre-profit), v0.1 ladder bit-for-bit, optional risk-scaled bars (OFF by default) | #4, #5 |
| `sizing.py` | **position sizing engine**: MoS ÷ risk composite, caps 8%/4%, sector ≤25%, min 2%, cash remainder | spec Part B |
| `journal.py` | **JSONL decision journal** with verdict-change diffs and parameters hash | #7 |
| `tests/` | 66 offline tests: golden numbers, ladder edge cases at the exact 15/30/50 bars, F-Score hand-computed, Altman hand-computed, reverse-DCF roundtrips, sizing caps, journal diffs | COMPARISON 0.1 |

## What the draft already surfaces (review notes for the owner)

Run on the demo snapshots (approximate data reconstructed from `reports/`), the draft flags three things v0.1 cannot see. These are *findings to confirm or overrule*, not silent changes:

1. **Completing the specced kill-gates changes verdicts.** AT&T's retained earnings are negative (dividends + buybacks > lifetime earnings), which pushes Altman Z to ~1.4 < 1.8 → the completed flag set hardens T from CAUTIOUS BUY to PASS. Your own IMB thesis documented exactly this failure mode for Graham ("buybacks shrink the anchor"); Altman's RE/TA term has the same bias. **Decision needed:** keep the gate (harsh but specced), exempt high-payout equity-returners, or use Z''.
2. **Owner earnings move IMB's numbers, with the reason printed.** EPV lands ~3,904p vs v0.1's 4,034p because capex (~£280m) < D&A (~£470m): FCF was deducting more than wear-and-tear. The provenance string shows which input produced every number.
3. **The terminal-value share of the bear DCF is 42–47%** on the demo names, and the 7× EBITDA exit cross-check values T far below the Gordon terminal. That is the honest fragility of a 10-yr + terminal model, now visible instead of buried.

## Deliberately NOT implemented (evaluated and rejected -- see COMPARISON.md §3)

Monte Carlo / probability-of-undervaluation, auto-WACC (CAPM/beta), Beneish M-Score (yfinance lacks the inputs; revisit only with an EDGAR/FMP data source), GUI dashboards, ML scoring, sentiment.

## Sign-off checklist

- [ ] Risk-panel anchor curves and weights (`risk.py::_CURVES`, `params.RISK_WEIGHTS`)
- [ ] `RISK_SCALED_BARS` stays OFF? (bars tighten/loosen by measured predictability)
- [ ] Altman Z kill-gate policy for buyback-heavy names (see note 1 above)
- [ ] Peer comps entries in `watchlist_ext.py` (TSCO pre-filled from the signed thesis)
- [ ] `EXIT_EBITDA_MULT = 7.0`, sensitivity grid ranges, `MAX_DEPLOYED = 0.80`
- [ ] Hygiene fixes: `.gitignore` added, `.pyc` untracked, `requirements.txt` pinned, LICENSE (MIT) -- see COMPARISON §4
