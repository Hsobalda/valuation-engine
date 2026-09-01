# 📊 Benchmark: This Engine vs Comparable Open-Source Valuation Engines

*Survey date: 1 Sep 2026. Purpose: before building v0.2, look at what repos with similar aims actually ship, decide component-by-component what is worth adopting, and log the reasoning. Companion draft implementation: [`v02_draft/`](../v02_draft/) (code, tests, none of it merged into `engine_v01.py`).*

---

## 1. The peer set

Two reference platforms (too big to "compete" with, useful as feature catalogues) and ten direct peers (single-purpose valuation/screener tools like this one).

| Repo | What it is | Notable components |
|---|---|---|
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) | The standard open finance terminal | Multi-source fundamentals, fraud-detection menu, export to csv/json/xlsx, DCF |
| [JerBouma/FinanceToolkit](https://github.com/JerBouma/FinanceToolkit) (~4.9k★) | 200+ transparent ratios/models library | WACC, DuPont, Sharpe/VaR, portfolio module, custom ratio builder |
| [EmanueleSturzo/DCF-Valuation-Model](https://github.com/EmanueleSturzo/DCF-Valuation-Model) | Single-name DCF | WACC via CAPM, **Monte Carlo (P10–P90, prob. undervalued)**, **sensitivity table**, scenario analysis, **exit-multiple terminal value**, comps, implied growth, JSON export, importable class |
| [dafahentra/dcf-valuation-tool](https://github.com/dafahentra/dcf-valuation-tool) | Streamlit DCF | Monte Carlo PDF of value, real-time beta, **multi-market (US/UK/DE/JP/HK/IN/CN) with region risk-free rates**, clean engine/UI separation |
| [mehul532/reverse-dcf-valuation-model](https://github.com/mehul532/reverse-dcf-valuation-model) | Reverse-DCF app | Implied growth, **implied FCF margin, implied WACC**, sensitivity tables, **data-quality audit**, historical comparison, report export |
| [Keenan-ux/implied-expectations](https://github.com/Keenan-ux/implied-expectations) (also on [awesome-quant](https://github.com/wilsonfreitas/awesome-quant)) | Expectations-investing reverse DCF on SEC EDGAR | Solves for implied **growth, duration, and operating margin**; explicitly "no price targets, no ratings" |
| [TomSOhm/invest](https://github.com/TomSOhm/invest) | FastAPI+Next.js fundamental platform | **Piotroski / Altman / Beneish M-Score / Sloan accruals**, **sector-relative percentiles**, DCF sensitivity grid, universe screener with cache + parquet persistence, three-horizon scoring |
| [asafravid/sss](https://github.com/asafravid/sss) (~160★) | yfinance fundamental scanner | EV/EBITDA screens, **email alerts of scan results**, PDF reports, results archived over time |
| [astro30/valinvest](https://github.com/astro30/valinvest) (~196★) | pip-installable Graham/Piotroski scorer | F-Score package with **unit tests**, technicals gate |
| [hjones20/fundamental-analysis](https://github.com/hjones20/fundamental-analysis) | FMP screener + DCF | WACC calculation, **"stability graphs" of indicators over 8 years** (EPS, BVPS, ROE, D/E stability) |
| [akashaero/Intrinsic-Value-Calculator](https://github.com/akashaero/Intrinsic-Value-Calculator) | GUI DCF, batch mode | **Solves implied growth AND implied FCF margin AND implied RRR from price**, request caching |
| [wlamont/securities-screener](https://github.com/wlamont/securities-screener) | Graham *Intelligent Investor* screen | 5-yr avg EPS × multiple max-price rule |

## 2. Where this engine is already ahead of the peer set

Worth stating up front, because the comparison is not "peer good, ours bad". None of the ten direct peers have:

1. **Verdict gating on human inputs.** No peer refuses to issue a verdict without a written thesis. The nearest is implied-expectations' "no price targets, no ratings" stance, which dodges the problem rather than gating on it.
2. **Method-disagreement cap (2.5× → WATCH).** Every peer reports a point fair value regardless of internal contradiction. Ours treats disagreement as *information* ("you don't understand this company yet").
3. **Bear-case-binds consensus.** Peers run base/bull/bear and use the base or a Monte Carlo median. Using only the pessimistic DCF for verdicts is more conservative than anything in the peer set.
4. **Asymmetry test on thin cushions** (bull upside ≥ 3× bear downside before a CAUTIOUS BUY).
5. **Falsifiers and price triggers as first-class data** ("wrong if:", "look again below 298p") attached to every name, signed and dated.
6. **A documented, signed parameter set** with the anti-features written down (what the engine refuses to do).

These are the interview story. The gaps below are about making that story *verifiable* (tests, data quality) and *finished* (the v0.2 list, prioritised by what peers proved is worth building).

## 3. Component-by-component evaluation

For each component seen in peers: adopt / adapt / reject, with reasoning against this engine's design principles (semi-automatic, conservative, drillable, no opaque numbers).

| Component (who has it) | Verdict | Reasoning |
|---|---|---|
| **Unit tests + CI** (valinvest, TomSOhm) | **ADOPT (P0)** | Nothing else on this list matters if the maths silently breaks. Zero tests today; `fx_to_price_ccy`, `hist_growth`, the ladder bars — one regression corrupts every verdict invisibly. Cheapest, highest-ROI item here. |
| **Data-quality audit** (mehul532) | **ADOPT (P0)** | Panel of checks: years of FCF history, missing eps/bvps, stale price, FX applied. Degrading inputs should downgrade methods visibly, not produce quiet garbage. Also fixes the fragile coupling where `football_field.py` regex-parses our own markdown reports as a fallback. |
| **Snapshot cache + offline replay** (akashaero's caching; dafahentra's JSON export) | **ADOPT (P0)** | Every run currently hits the network; reports can't be regenerated reproducibly; CI re-runs are hostage to Yahoo. Save each fetch bundle to dated JSON; replay mode for tests, charts and report diffs. |
| **Pinned dependencies + field normalisation** (all maintained peers pin) | **ADOPT (P0)** | `requirements.txt` is unpinned. yfinance has changed `dividendYield` semantics between percent (4.3) and fraction (0.043) across versions; the report card prints the raw value with a `%` → version drift turns "4.3%" into "0.0%". Yahoo row-label drift breaks `fetch` silently. Normalise at the boundary, pin, and test with fixtures. |
| **Reverse DCF as first-class output** (mehul532, sughanthAM, akashaero, implied-expectations) | **ADOPT (P1, issue #2)** | Already proven manually in four theses; peers confirm the pattern and extend it: solve implied **required return** and **break-even decline** too, not just growth. Promote from `report_card.py` into the core verdict table. |
| **Implied-margin / implied-duration solves** (implied-expectations, mehul532) | **ADAPT (P1, park margin solve for v3)** | Solving implied FCF *margin* needs a revenue-driven model we deliberately don't run. The *duration* idea is cheap and useful: how many years of priced growth must be real? Park margin for v3 lever-maths. |
| **Risk panel w/ continuous subscores** (TomSOhm's percentile scoring; our own spec Part B) | **ADOPT (P1, issue #5)** | Spec exists, unimplemented. Peers prove it's codeable with free data. Keep our twist (drillable subscores + plain-language reasons, kill-gates preserved underneath, composite only for ordering) — that's better than a single opaque number. |
| **Piotroski F-Score, Altman Z** (TomSOhm, valinvest) | **ADOPT (P1)** | Our own ENGINE_DESIGN lists both as fatal flags; v0.1 implements only 2 of the 4 specced flags. F-Score ≤ 3 and Altman Z < 1.8 complete the spec'd kill-gates. |
| **Sloan accruals + dilution trend** (TomSOhm) | **ADOPT (P1)** | Closes VALUE_TRAP_CHECKS Layer 4, which is documented but coded nowhere: FCF-vs-NI backing, accruals ratio, share-count trend. |
| **Beneish M-Score** (TomSOhm) | **REJECT for now** | Needs 8 specific ratios over ≥2 years of quarterly data; yfinance doesn't reliably carry them. Documented as "needs better data source (EDGAR/FMP)". Revisit only if we change data vendor. |
| **Sensitivity table (deterministic)** (Sturzo, TomSOhm) | **ADOPT (P1)** | 2-way grid: discount rate × terminal growth on the bear DCF, each cell showing MoS. Directly serves "the blurrier your estimate, the riskier the position" without any probabilistic claims. |
| **Exit-multiple terminal cross-check** (Sturzo) | **ADOPT (P1)** | Cheap honesty check: recompute bear DCF with an EV/EBITDA exit multiple instead of Gordon growth, and print terminal value's share of total. Answers "is the terminal doing all the work?" |
| **Monte Carlo / probability undervalued** (Sturzo, dafahentra) | **REJECT as headline, keep out** | A P(undervalued)=62% is exactly the kind of number our design refuses to produce: distributional assumptions fake precision the inputs don't have, and it invites betting on the model. The 4-method spread + sensitivity grid already measures uncertainty honestly. If ever added: appendix only. |
| **CAPM/WACC auto-discount-rate** (Sturzo, dafahentra, hjones20, FinanceToolkit) | **REJECT** | Beta-based WACC is backward-looking volatility dressed as a hurdle rate. Our 10% + judgement bumps is a *policy*, not an estimate; it's signed-off and drillable. Adopting WACC would make the engine agree with the market's own pricing. |
| **Peer/sector-relative multiples** (TomSOhm percentiles, hjones20, wlamont) | **ADOPT (P1, issue #6)** | Replace flat 15×. But adapt, not copy: peer multiples enter as *owner-configured* comps (the TSCO thesis already researched them: KR 7.0×, AHODR 7.7×, SBRY 8.3× EV/EBITDA), keeping the "semi" in semi-automatic and working offline. |
| **Indicator stability graphs** (hjones20's 8-yr stability) | **ADAPT (P2)** | The idea (how stable is the thing you're normalising?) becomes a *number*: FCF stability = std/mean over history, feeding the risk panel and risk-scaled MoS bars. No separate plotting module needed. |
| **Own-history multiples** (wlamont 5-yr EPS; our issue #6) | **ADOPT (P1)** | Median historical EPS already computed; add own-history P/E when price history is available; falls back to comps then 15×, with the fallback *printed*, never silent. |
| **Position sizing engine** (our spec Part B; FinanceToolkit portfolio) | **ADOPT (P2)** | MoS ÷ risk-composite weights, caps preserved (8%/4%, 25% sector, 2% min, cash remainder). Peers do portfolio *reporting*; none do risk-scaled value sizing. |
| **Decision journal + verdict diffing** (nobody) | **ADOPT (P2, issue #7)** | No peer has it. JSONL journal, stamped with price/verdict/params; re-runs print CHANGED/SAME diffs. Natural extension of the signed-thesis discipline; cheap; differentiating. |
| **Verdict track-record / calibration** (nobody) | **ADOPT (P2)** | SYSTEM.md promises "judge the system over years" — needs data to judge with. Journal already stores price per verdict; a look-back table (verdict → subsequent return vs benchmark) is ~50 lines on top. |
| **Email alerts of scans** (asafravid/sss) | **PARK** | Useful when the watchlist grows past ~15 names and price triggers exist to alert on. Not yet; the price-trigger table in report cards covers the need at n=7. |
| **Streamlit/GUI dashboard** (dafahentra, akashaero, mehul532) | **REJECT** | UI effort buys zero analytical rigour; the static site via CI already exists; CLI + markdown *is* the audit trail. Revisit only if the tool ever goes multi-user. |
| **ML prediction / genetic selection** (francisco3511/stocksense) | **REJECT** | Unexplainable scores contradict "the tool argues, the human decides" and the drillability rule. |
| **Sentiment analysis bolt-on** (dbogatic/value_investing) | **REJECT** | Uncorrelated noise for a concentrated value book; adds data dependence without adding valuation content. |

## 4. Repo hygiene (found during the survey; all P0)

1. **`__pycache__/engine_v01.cpython-311.pyc` is committed to git.** Untrack it, add `.gitignore`.
2. **No LICENSE file.** Every peer has one. For a CV-line repo this is friction: nobody can legally reuse it and it looks unfinished.
3. **`deploy.yml` is broken as committed:** it runs `python scripts/reports_to_json.py --out src/engine/engine-data.json`, then `npm install && npm run build` — but the repo has `reports_to_json.py` at root, and no `scripts/`, `src/`, `package.json` at all. Every scheduled Mon/Thu run fails at the JSON step. Either the website tree needs committing or the workflow needs trimming to engine + report cards only.
4. **Unpinned `requirements.txt`** (see §3, dependencies).
5. **`report_card.py` FCF-yield block contains dead/confused code** (two competing calculations, first overwritten) and an inline second `yf.Ticker` fetch for capex/D&A that bypasses `fetch()` — a bug magnet of exactly the kind tests + a single data layer remove.
6. **`deploy.yml` lives at root** rather than `.github/workflows/` — confirm GitHub is actually picking it up (repo file listing suggests it is not in the workflow path).

## 5. The deep-dive list (what to do better, prioritised)

Priorities: **P0** = trust infrastructure (nothing analytical matters until these are fixed), **P1** = analytical gaps the peers prove are worth closing (maps to VERSION_PLAN issues #1–#8), **P2** = process differentiators nobody else has. Each item lists acceptance criteria so "done" is checkable.

### P0 — trust infrastructure
| # | Item | Acceptance criteria |
|---|---|---|
| 0.1 | **Test suite** | `pytest` green offline; golden-number tests for EPV/DCF/Graham/multiples/reverse-DCF; ladder edge cases at exactly 15/30/50% bars; kill-gate precedence; FX/pence conversion; F-Score and Altman against hand-built statements |
| 0.2 | **Data layer hardening** | Single `fetch_bundle()`; yfinance field normalisation (dividendYield both semantics, missing rows → explicit `None`); data-quality panel (history length, missing fields, staleness) printed with every run |
| 0.3 | **Snapshot cache + offline replay** | `--snapshot date.json` reads cached bundle; `--save-snapshot` writes it; charts/reports/tests run with network off; fixtures in-repo |
| 0.4 | **Hygiene** | `.pyc` untracked; `.gitignore`; LICENSE (MIT); `requirements.txt` pinned with comments; `deploy.yml` either fixed to match repo contents or trimmed; dead FCF-yield code removed |

### P1 — analytical upgrades (VERSION_PLAN mapping)
| # | Item | Maps to | Acceptance criteria |
|---|---|---|---|
| 1.1 | **Reverse DCF in core** | issue #2 | Implied-growth column in the verdict table; implied required return; break-even decline (perpetual-decay variant, the IMB −5.3% maths automated); monotonicity tested |
| 1.2 | **Risk panel** | issue #5 | Per-metric subscores 0–100 each with a plain-language reason (coverage, FCF stability, leverage, method agreement, accruals, measurement quality); composite computed but always shown *with* the panel; fatal flags preserved as kill-gates underneath |
| 1.3 | **F-Score + Altman Z kill-gates** | spec'd, unimplemented | F-Score ≤ 3 and Altman Z < 1.8 join the fatal-flag set (spec parity); hand-checked against real numbers for one name |
| 1.4 | **Earnings quality** | VALUE_TRAP Layer 4 | Accruals ratio (Sloan), FCF/NI backing over history, share-count dilution trend → flags + risk subscore |
| 1.5 | **IFRS 16 lease adjustment** | issue #8 | Lease principal repayments deducted from FCF when detectable; adjustment size printed; applies to EPV + DCF inputs |
| 1.6 | **Owner earnings** | issue #1 | Owner FCF = OCF − min(capex, D&A), 4-yr median, feeding EPV/DCF; both raw and adjusted printed |
| 1.7 | **Multiples upgrade** | issue #6 | Method 4 = normalised EPS × (owner-configured peer median multiple, else 15×); the multiple actually used is always printed |
| 1.8 | **Wrong-model refusal** | issue #4 | Banks/insurers (sector-based) and pre-profit names get an explicit WRONG TOOL verdict + reason instead of quietly unreliable numbers |
| 1.9 | **Sensitivity + exit-multiple cross-check** | new (peer-proven) | Bear DCF grid over r ∈ {9..12%} × terminal g ∈ {1..3%} with MoS per cell; exit-multiple terminal variant + terminal-share-of-value printed |

### P2 — process differentiators
| # | Item | Maps to | Acceptance criteria |
|---|---|---|---|
| 2.1 | **Journal** | issue #7 | JSONL append per run (date, symbol, price, verdict, MoS, methods, params hash); re-runs print CHANGED/SAME per symbol |
| 2.2 | **Position sizing engine** | spec Part B | weight ∝ MoS ÷ risk composite across buy-rated names; caps 8%/4%, sector ≤ 25%, min 2%, remainder = cash; output table BUY MORE/HOLD/TRIM/EXIT |
| 2.3 | **Track record** | SYSTEM.md Stage 6 | Look-back table from journal history: verdict → price change since, vs benchmark; honest "n too small" refusal |
| 2.4 | **Structural-decliner mode** | issue #3 | Decliner names get break-even decline + perpetual-decay DCF variant instead of the +2%-floored bear DCF (delivered by 1.1's perpetual solver) |
| 2.5 | **Packaging** | — | `v02_draft` importable as a module; config (watchlist/params) separable from engine code so thesis edits never touch maths files |

## 6. Draft status

Everything P0 + P1 + journal/sizing (2.1–2.2) is drafted in [`v02_draft/`](../v02_draft/) with tests — **nothing touches `engine_v01.py`**; v0.1 remains the shipped engine until each piece is reviewed and signed off. The draft README maps each module to the items above and flags every *new* parameter as `DRAFT — owner sign-off required`.

Rejected-on-the-record (so future me doesn't relitigate without new evidence): Monte Carlo headline, auto-WACC, Beneish (data), GUI dashboards, ML selection, sentiment.
