# 🪤 Beyond "Cheap": Tests to Separate Bargains from Value Traps
A stock passing the cheapness screen earns a **look**, not a buy. These layers filter out companies that are cheap *for a reason*. Each one is codeable with free `yfinance` data.

---

## Layer 1 — Cheapness (what we already have)
| Test | Signal |
|---|---|
| P/E vs market & sector | Lower = cheaper |
| P/B (price/book) | < 1 means priced below net assets |
| Earnings yield (E/P) | Higher = cheaper |
| Graham Number margin of safety | Price ≥ 25–30% below fair value |

**Trap risk if used alone:** dying businesses look "cheap" all the way to zero.

---

## Layer 2 — Quality & profitability (is the business any good?)
| Test | What it catches | Rough pass mark |
|---|---|---|
| **ROE** (return on equity) | Weak businesses | > 10–12%, stable over 5 yrs |
| **ROIC / ROA** | Capital-destroying firms | ROIC above ~8–10% |
| **Operating margin trend** | Eroding competitiveness | Flat or rising, not shrinking |
| **Piotroski F-Score** (9-point checklist) | Overall deterioration | Score ≥ 7 strong, ≤ 3 avoid |

💡 *Greenblatt's "Magic Formula" = rank by cheapness AND quality together. This is exactly the 2-axis screen your tool should use.*

## Layer 3 — Financial health (can it survive long enough to re-rate?)
| Test | What it catches | Rough pass mark |
|---|---|---|
| **Debt/Equity** | Leverage time-bombs | < 1.0 (sector-dependent) |
| **Interest coverage** (EBIT ÷ interest) | Firms one bad year from distress | > 3–4× |
| **Current ratio** | Short-term cash crunches | > 1.2 |
| **Altman Z-Score** | Bankruptcy risk | > 3 safe, < 1.8 danger |

Value traps are often *cheap + indebted*. Debt is what turns "temporarily unloved" into "insolvent".

## Layer 4 — Earnings reality check (are the profits real?)
| Test | What it catches |
|---|---|
| **FCF vs net income** | Paper profits: cash flow should roughly back up earnings over 3–5 yrs |
| **One-off items** | A single asset sale can fake a low P/E for a year |
| **Revenue trend (5 yr)** | Melting-ice-cube businesses: cheap P/E on shrinking sales |
| **Share count trend** | Dilution silently eating your ownership |

## Layer 5 — Context checks
- **vs its own history:** is today's P/E low *for this company*? (5–10 yr percentile)
- **vs sector peers:** a P/E of 9 is cheap for software, normal for banks
- **Sector-wide cheapness:** if the whole industry is cheap, the market may be pricing structural decline (e.g. print media) — not 30 bargains
- **Dividend sustainability:** payout ratio < ~70%; a 12% yield usually means the market expects a cut

## Layer 6 — What code CAN'T check (your judgement)
- Moat: why will this company still win in 10 years?
- Management quality and capital allocation record
- The actual *reason* it's cheap — there always is one; your job is deciding whether it's temporary or terminal

---

## 🏗️ How this shapes the tool
Final screener output per company = **two scores + flags**:
1. **Value score** (Layer 1) — how cheap?
2. **Quality/safety score** (Layers 2–4) — how likely is the cheapness real?
3. **Red flags list** (Layer 4–5) — auto-generated warnings ("EPS boosted by one-off", "interest coverage 1.9×")

Buy candidates = high value score **AND** high quality score **AND** no fatal flags → then Layer 6 by hand.
