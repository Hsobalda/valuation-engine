# ⚙️ The System — Valuation-First
**Design decision:** this tool is *valuation-first*, not screener-first. You choose the companies (watchlist); the tool's job is to answer **"what is it worth, and how big is the gap to the price?"** Cheapness ratios are shown as context, never used as gatekeepers.

---

## Stage 0 — Watchlist 🌍
You maintain a list of companies you're interested in (any size — 5 or 50). Optional later add-on: a screener mode to *suggest* names for the watchlist.

## Stage 1 — Snapshot 💰 (context, not a filter)
For each watchlist company, display the basic ratios (P/E, P/B, EV/EBIT, FCF yield) vs sector median and vs the company's own 5-yr history — purely so you see how the market currently prices it.

## Stage 2 — Trap checks 🪤 (warnings, not eliminations)
Run the health tests (F-Score, interest coverage, Altman Z, FCF vs earnings, dilution) and attach **red flags** to each company. Nothing is auto-deleted — you see the warnings next to the valuation.

## Stage 3 — Valuation ⚖️ (THE CORE OF THE TOOL)
For each watchlist company, estimate fair value THREE ways and take the range:
1. **Graham Number / asset value** — floor value, conservative
2. **DCF** — project free cash flows 5–10 yrs, discount them back:
   - Fair value = Σ FCFₜ ÷ (1+r)ᵗ + terminal value
   - r (discount rate) ≈ 8–12%; growth assumptions LOW (this is where DCFs lie)
   - ⚠️ DCF is hypersensitive to inputs: always run 3 scenarios (bear/base/bull) and use the BEAR case for your margin of safety
3. **Peer multiples** — what would it be worth at the sector's median EV/EBIT?

**Margin of safety = (conservative fair value − price) ÷ fair value. Demand ≥ 30%.**
**Output per company: fair value range, margin of safety %, red-flag list.**

## Stage 4 — Human judgement 🧠 (not codeable)
Read the annual report. Answer in writing: Why is it cheap? Is that temporary or terminal? What's the moat? Would I be happy owning this if the market closed for 5 years?
**→ your actual buy list.**

## Stage 5 — Position sizing & portfolio construction 📊
- Max ~5–10% per position; start smaller
- Diversify across sectors (5+ sectors, 10–20 holdings)
- Bigger margin of safety + higher quality = bigger position
- Keep cash when nothing qualifies — the system saying "buy nothing" is a feature

## Stage 6 — Monitoring & review 📈 (this is where Sharpe lives)
Track continuously:
| Metric | What it answers |
|---|---|
| P/L per position & total | Am I making money? |
| **Sharpe ratio** = (return − risk-free rate) ÷ volatility | Was the return worth the ride? (>1 good, >2 excellent) |
| Max drawdown | Worst peak-to-trough — can I stomach it? |
| vs benchmark (FTSE All-Share / S&P 500 tracker) | Am I beating "just buy the index"? Be honest. |
| Thesis check per holding | Has the reason I bought changed? Sell on thesis break, not price wiggles |

**Re-run Stages 1–3 monthly. Review holdings quarterly. Judge the system over years, not weeks.**

---

## Build order for the tool
| Module | Stage | Needs (course days) |
|---|---|---|
| Ratio calculators | 1 | Days 1–3 ✅ started |
| Screener loop over watchlist | 1–2 | Days 5, 8, 10 |
| Trap-filter functions | 2 | Days 11, 15, 17 |
| Live data via yfinance | all | Days 19–20, 25 |
| DCF (3 scenarios) | 3 | Day 11 + a loop |
| Portfolio tracker + Sharpe | 5–6 | Day 25 (pandas) |

## ⚠️ Reality checks
- Backtest/paper-trade the screen before real money.
- Sharpe needs ~1yr+ of data to mean much.
- No system removes the need for Stage 4. The tool narrows 2,000 to 15; you pick from 15.

---

## House thesis style (locked 25 Aug 2026, owner sign-off)
Every thesis in the WATCHLIST follows this register. Reference examples: KGF.L and SPOT [Signed 25 Aug 2026].

**Tone rules:**
1. Real finance terms where they earn their place (reverse DCF, IFRS 16, FCF, D&A, margin of safety, like-for-like). No dumbing down.
2. No jargon for its own sake: nothing like "commoditised by design", "re-underwrite", "framework-clean".
3. Short declarative sentences. First person for judgement calls ("I revisit at about 280p").
4. No em or en dashes. Commas, colons and full stops only.
5. Numbers in every claim. A sentence without a number is probably decoration.

**Mandatory structure:**
- Verdict word first (PASS / WATCH / BUY etc.)
- The core argument: what the market prices vs what I think is real
- The honest cautions, including anything that weakens my own case
- "Wrong if:" observable falsifier(s)
- Price trigger(s), each labelled with what happens there
- [Signed DD Mon YYYY] date stamp
