# 🏗️ Valuation & Risk Engine — Design Spec v0.1
**Design principle:** semi-automatic. The tool computes everything computable; the human supplies exactly THREE judgement inputs per company; verdicts are only issued when both halves exist. Rigor = triangulation of independent methods + bear-case as binding constraint.

---

## PART A — The Valuation Stack (four independent methods)

Each method attacks "what's it worth?" from a different direction. Agreement between them is the rigor signal; divergence is itself information.

### Method 1 — Earnings Power Value (EPV) · the "no-growth floor"
`EPV = normalised FCF ÷ discount rate` — what the company is worth if it NEVER grows again.
- Normalised FCF = median of last 5 years' free cash flow (median kills one-off spikes)
- Fully automatic. The most honest number in the stack: any price below EPV means the market is paying you to hold zero-growth pessimism.

### Method 2 — Three-scenario DCF · the workhorse
10-yr projected FCF + terminal value, discounted back.
- **Bear:** growth = min(historical 5-yr FCF growth, 2%) — never higher than 2%
- **Base:** growth = min(historical, 6%), capped
- **Bull:** growth = min(historical, 10%), capped
- Caps are hard-coded honesty: no company gets >10% assumed growth regardless of history
- Fully automatic once discount rate is set. **Bear case is the number used for verdicts.**

### Method 3 — Graham Number · the asset-anchored check
`√(22.5 × EPS × BVPS)` — value anchored to assets + current earnings, not projections.
- Fully automatic. Weak for asset-light companies (flags itself when P/B > 5 and reports "low reliability" instead of a number).

### Method 4 — Multiples reversion · the relative check
What would the price be at (a) the company's own 5-yr median P/E, and (b) sector median EV/EBIT?
- Fully automatic. Catches "cheap vs itself" and "cheap vs peers" separately.

### The three HUMAN inputs (the "semi" in semi-automatic)
| Input | Options | Effect |
|---|---|---|
| **Moat rating** | none / narrow / wide | none → bear-case DCF weight doubled in consensus |
| **Cyclicality flag** | stable / cyclical | cyclical → normalised FCF uses full-cycle (7yr) median; required MoS +10pts |
| **Thesis sentence** | free text, mandatory | no thesis = no verdict. Forces the "why is it cheap?" answer |

### Consensus & verdict — LOCKED PARAMETERS (owner sign-off 23 Aug 2026)
- **Discount rate: 10% base** (+2pts if flagged cyclical, −1pt if wide moat; floor 9%)
- **Only the BEAR-case DCF enters the consensus.** Bull/base cases never touch fair value — bull–bear spread feeds the risk score; bull case feeds the asymmetry test below. EPV (zero-growth) and Graham (asset floor) are inherently conservative, so consensus fair value is pessimism-tilted by construction.
- **Fair value = median of (EPV, bear DCF, Graham, multiples)** — median, not mean, so one crazy method can't drag the answer
- **Margin of safety = (fair value − price) ÷ fair value**
- **Cash policy: cash is fine.** No minimum-invested constraint; verdicts never stretch to deploy capital.
- Verdict ladder (tiered per owner design):
  - `STRONG BUY`: MoS ≥ 50% AND ≥3 methods independently show ≥30% AND zero fatal flags AND human inputs complete → full weighting
  - `BUY`: MoS ≥ 30% AND ≥2 methods ≥20% AND no fatal flags → full weighting
  - `CAUTIOUS BUY`: MoS 15–30% AND **asymmetry test**: (bull FV − price) ≥ 3 × (price − bear FV) AND no fatal flags → **weight capped at half a normal position**. Rationale: a thin cushion is only acceptable when the payoff is heavily skewed in your favour
  - `WATCH`: MoS ≥ 0%, or failed asymmetry test
  - `PASS`: negative MoS, or any fatal flag
- **Fatal flags** (auto): interest coverage < 2× · Altman Z < 1.8 · FCF negative in 3 of last 5 yrs · F-Score ≤ 3
- **Method disagreement warning:** if max method ÷ min method > 2.5, verdict is capped at WATCH — "your methods don't agree; you don't understand this company yet"

---

## PART B — Automated Risk Assessment & Position Weighting

### Per-ticker risk score (0–100, higher = riskier), from five components:
| Component | Weight | Measures | Source |
|---|---|---|---|
| **Valuation uncertainty** | 30% | (bull FV − bear FV) ÷ base FV — how blurry is your own estimate? | your own DCF spread |
| **Balance-sheet risk** | 25% | D/E, interest coverage, Altman Z blended | fundamentals |
| **Price volatility** | 20% | 1-yr weekly return std dev + beta | price history |
| **Earnings quality** | 15% | FCF/net income gap, F-Score | fundamentals |
| **Concentration context** | 10% | sector overlap with existing holdings | your portfolio |

The 30% on valuation uncertainty is the signature: **the blurrier your own fair-value estimate, the riskier the position — regardless of how good the company looks.** (Spotify-type names get big scores here automatically.)

### Weighting rule (conviction ÷ risk, capped)
```
raw_weight(i)   = margin_of_safety(i) ÷ risk_score(i)
target_weight   = raw_weight ÷ Σ raw_weights, then apply caps
```
**Caps:** max 8% per full-conviction position (**pending owner sign-off** — the one unlocked parameter) · CAUTIOUS BUY capped at 4% (half) · max 25% per sector · min position 2% (else "not worth holding") · verdicts below CAUTIOUS BUY get weight 0 · uninvested remainder = cash (cash is a position, not a failure)

### Output per run
A table: ticker · price · fair value (4 methods + consensus) · MoS% · verdict · risk score · current weight · target weight · action (BUY MORE / HOLD / TRIM / EXIT) · red flags. Plus a journal stub per verdict change, timestamped — your documented process, automated.

---

## Honest limits (stated on every output)
- Works for profitable, cash-generative companies; auto-refuses banks/insurers ("wrong model" flag) and pre-profit firms (EPV/DCF undefined)
- Risk score measures *estimability and fragility*, not true risk — a wide-moat firm during a scandal scores "risky" and may be the best buy on the list. The score sizes positions; it doesn't pick them
- All parameters visible and overridable — the tool argues, the human decides
