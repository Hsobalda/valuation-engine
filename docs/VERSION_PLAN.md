# 📦 Version Plan — Valuation Engine

## v0.1 — SHIP NOW (gate: theses signed, audit done, then GitHub + CV line)
**What it is:** watchlist-first, four-method value engine for steady-cash-flow businesses.
- Methods: EPV (zero-growth floor) · bear-case 10yr DCF (growth capped 2%) · Graham Number (self-disables P/B > 5) · normalised EPS × 15
- Verdict ladder: STRONG BUY / BUY / CAUTIOUS BUY / WATCH / PASS with MoS bars 50/30/15%, cyclical +10pt bump, asymmetry test 3:1, method-disagreement cap 2.5×, fatal flags (interest coverage < 2×, repeated negative FCF)
- Outputs: verdict table, ASCII ranges, football-field chart, per-company report cards
- **Companies (7):** TSCO.L, PEP, EZJ.L, SPOT, IMB.L, KGF.L, T

**v0.1 watchlist status (24 Aug 2026):**
| Ticker | Verdict | Thesis status |
|---|---|---|
| TSCO.L | PASS −30% | DRAFT — needs 2–3 signed sentences (why not buying at this price) |
| PEP | PASS −81% | DRAFT — same |
| EZJ.L | WATCH +13% | STALE — rewrite as merger-arb/exit note (Apollo 715p cash, ~end-Mar 2027) |
| SPOT | PASS −535% | Tightened thesis drafted — AWAITING OWNER SIGN-OFF |
| IMB.L | WATCH +40% (spread cap) | TODO — raw material complete (decline grid, payout, Graham artifact) |
| KGF.L | WATCH +23% | TODO — owner can't currently describe the company: write it or CUT from v0.1 |
| T | WATCH +17% | TODO — tight method cluster, potential cautious-buy candidate |

**Ship gate:** no name ships with a TODO. Write or cut. Depth > breadth.

## v0.2 — Nov 2026+ (after applications in; becomes final-round interview material)
GitHub Issues #1–#7:
1. EPV capex fix — owner earnings = OCF − min(capex, D&A), 4-yr medians
2. **GROWTH LENS: reverse DCF / implied-growth column in main engine + report cards** (headline v0.2 feature; owner request 25 Aug 2026 -- v0.1 is deliberately harsh but ignorant of what growth prices assume; this makes it articulate) ← bridge to v3
3. Structural-decliner mode — decline grids / break-even decline (IMB prototype: −5.3%/yr perpetual, −8.4% if melt stops)
4. Wrong-model flags (banks/insurers, pre-profit companies)
5. Risk-score weighting engine (position sizing beyond flat 8%/4% caps)
   Expanded scope (owner request 25 Aug 2026): risk-SCALED margin of safety. Uniform 30% bar treats
   predictable and unpredictable businesses the same. Instead scale the required MoS to measured
   uncertainty: method spread, FCF stability, leverage, cyclicality. Tight/stable/unlevered may
   need 25%; scattered/cyclical/levered demands 40%+. Same total conservatism, allocated to where
   the risk lives. NOT a loosening: any bar reduction must be earned by measured predictability.
   Extension (owner design, 25 Aug 2026): continuous subscores instead of cliff-edge thresholds.
   Each parameter scored 0-100 by distance from danger (coverage 2.3x scores ~40, not "pass");
   weighted blend -> one drillable risk rating per company, every subscore inspectable on demand
   (no opaque numbers). Near-limit values become visible instead of silently passing. Design
   guards: (a) absolute kill-gates survive UNDERNEATH the score (fatal flags cannot be averaged
   away by good subscores), (b) weights are signed owner decisions like the MoS bars, not derived.
   Refinement (25 Aug 2026): primary display is a RISK PANEL, not one blended number -- a list of
   per-metric subscores each with a plain-language reason (margin, method agreement, coverage, FCF
   stability, leverage, measurement quality). No weights to defend at display level. A composite is
   computed only where a decision needs an ordering (position sizing, watchlist ranking), always
   shown WITH its panel so the blend cannot hide its inputs. Panel for judgement, composite for action.
8. IFRS 16 lease adjustment: subtract lease principal repayments from FCF for leased-estate
   retailers (KGF, TSCO). Discovered via KGF capex/D&A peer screen 25 Aug 2026: US owners ~1.0,
   UK leaseholders 0.3-0.6. Headline FCF overstates owner cash flow; engine currently biased
   toward UK leased retail looking artificially cheap.
6. Multiples upgrade — own-history + sector medians instead of flat 15×
7. Journal stubs — dated thesis/review entries per position

## v3 — 2027 (parked) — Growth mode: expectations investing
Current engine is anti-growth by construction (will PASS every growth name — correct behaviour, wrong tool). v3 extends the burden-of-proof philosophy to growth prices:
- Reverse DCF as PRIMARY method: compute implied FCF growth from price (SPOT prototype: ~24%/yr implied)
- Driver-ceiling "lever maths": 2–4 named drivers × generous ceilings, multiplied (SPOT: 1.8 × 1.5 × 1.33 ≈ 3.6× vs 8.6× required) → if ceilings can't reach implied growth, PASS with evidence
- Verdict = growth gap, not price gap: BUY only when price implies LESS growth than conservative levers deliver
- Growth fatal flags: no positive FCF base, stock-comp dilution, customer concentration, single-product dependence
- Design guard: ceilings set BEFORE seeing the verdict — the tool defends against owner optimism
- Reading: Mauboussin, *Expectations Investing*

## Sequencing rule
v0.1 theses → GitHub upload → CV line live → applications (Sept) → v0.2 (Nov+) → v3 (2027).
No new machinery before the theses are signed.
