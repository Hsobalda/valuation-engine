# Building an Interactive Equity Analysis & Valuation Tool — Workflow Plan

> Research-driven roadmap synthesized from multiple sources on valuation methodology
> (Damodaran, DCF/comps cheat sheets), financial data APIs, and dashboard architecture.
> This is a planning document only — no code. Work through it top to bottom; each step
> ends with a concrete "done when" checkpoint.

---

## Step 0 — Define scope & the one-sentence pitch

Before touching code, pin down what the tool is. This decision shapes every later step.

**Questions to answer (write answers down):**

1. **Who is it for?** Just you (personal research) vs. a small group vs. a public product.
   This determines whether you can use Streamlit/Dash or need React, and how much you
   invest in auth, caching, and multi-user state.
2. **What's the primary job?** Pick ONE north-star question, e.g.:
   - "What is this company's intrinsic value, and how much upside/downside vs. today's price?"
   - "Is this company cheap relative to its peers?"
   - "Which of my watchlist names are in a buy zone this week?"
3. **Which market(s)?** US-only (huge, free data available via SEC) vs. global (much harder data).
4. **What kind of "interactive" do you mean?** Editable assumptions (sliders on growth rate,
   WACC, margins), scenario toggles (bear/base/bull), sensitivity heatmaps, screener filters,
   or all of the above?

**Done when:** you have a written 3–5 line product brief and a list of 5 "must-have" features
vs. "nice-to-have" features.

---

## Step 1 — Decide the valuation framework (the "what" you're computing)

A good tool is built around a *defensible* model, not a magic number. The standard practice
(mirroring Aswath Damodaran's three approaches) is to combine:

### 1a. Intrinsic valuation — Discounted Cash Flow (DCF)

The workhorse. Core structure (standard 5–6 step build):

1. **Project revenue** for 5–10 years (growth driven by history, guidance, industry).
2. **Build to Free Cash Flow to the Firm (FCFF):**
   `FCFF = EBIT × (1 − tax) + D&A − CapEx − ΔWorking Capital`
3. **Calculate WACC** (the discount rate):
   - Cost of equity via CAPM: `risk-free + β × equity risk premium`
   - After-tax cost of debt
   - Weighted by **market-value** debt/equity mix
4. **Discount each year's FCF** at WACC (use mid-year convention: discount by `t − 0.5`).
5. **Terminal value** — run BOTH methods and cross-check:
   - Gordon Growth: `TV = FCF₍ₙ₊₁₎ / (WACC − g)`, g ≈ 2–3% (long-run GDP/inflation)
   - Exit Multiple: `TV = terminal EBITDA × exit EV/EBITDA`
6. **Bridge to equity value per share:**
   `Equity = EV − Net Debt − Minority Interest − Preferred + Cash`
   `Per-share = Equity / diluted shares (treasury stock method)`

**Critical caveats to bake into the tool:**
- Terminal value is typically **60–80% of total EV** — it dominates. Surface this to the user.
- Always present a **range, not a point estimate**. Sensitivity tables on WACC (±1%) ×
  perpetual growth (±0.5%) × revenue growth are non-negotiable.
- Warn when TV > ~80% of value (the model is essentially a one-number bet on growth).

### 1b. Relative valuation — comparable companies (comps)

Value by benchmarking against peers:

1. **Select a peer group** (5–15 companies, similar business model/size/growth). This is the
   single most subjective and important step — bad peers = bad valuation.
2. **Calculate multiples** — EV/EBITDA (most common, capital-structure neutral), P/E, EV/Revenue,
   P/B. Match the multiple to the sector (e.g. banks → P/tangible book, REITs → P/FFO,
   SaaS → EV/NTM revenue).
3. **Benchmark** — use median (and 25th/75th percentile), exclude outliers.
4. **Apply** the median multiple to the target's metric → implied value range.
5. **Triangulate** — if EV/EBITDA, EV/Revenue, and P/E disagree, dig into why.

### 1c. "Football field" summary (the money view)

Overlay all methods on one horizontal bar chart: DCF range, comps implied range, current
price, analyst targets. This is the single most valuable output of any valuation tool.

**Done when:** you can write out, by hand, every formula in the model and state where each
input comes from. If you can't explain an assumption, don't code it yet.

---

## Step 2 — Choose your data sources

The model is only as good as its inputs. Decide early because it shapes the data layer.

**What you need:**
- Financial statements (income, balance sheet, cash flow) — annual + quarterly, ideally 5–10 yrs
- Market data: price, market cap, beta, shares outstanding, 52-week range
- Company profile: sector/industry, description
- Derived ratios if you don't compute them yourself (ROE, ROIC, margins, FCF yield)
- Ideally: analyst estimates (for growth anchors + targets), risk-free rate (FRED)

**Free-tier reality check (limits are the main constraint):**

| Provider | Free tier | Strengths |
|---|---|---|
| **Alpha Vantage** | ~25 req/day, full normalized statements + overview ratios | Best free starting point for prototyping |
| **Financial Modeling Prep (FMP)** | ~250 req/day | Statements, transcripts, even pre-built DCF endpoints; low-cost paid |
| **Finnhub** | 60 req/min, SEC as-reported + key metrics | Good free mix; clean statements are premium |
| **yfinance** | unofficial, no key, rate-limited | Easiest zero-setup prototype data (price + basics) |
| **SEC EDGAR / XBRL** | free, unlimited-ish | Ground truth for US filings; parsing is the hard part |
| **StockFit / Business Quant** | free, SEC-traceable | Audit-grade, point-in-time if you need traceability |

**Practical recommendation for a first build:** prototype with **yfinance** (zero friction)
to get the pipeline working end-to-end, then swap in **FMP or Alpha Vantage** for stable,
rate-limit-aware fundamentals. Cache everything aggressively — you do *not* re-hit APIs on
every slider drag.

**Done when:** you can fetch and store, for one ticker: 5+ years of the 3 statements,
price history, market cap, shares outstanding, and beta.

---

## Step 3 — Architecture & tech stack

Decide the shape based on your Step 0 answers. Three common tiers, in order of ambition:

| Tier | Stack | Best for |
|---|---|---|
| **Prototype / personal** | Streamlit + Plotly + pandas | Fastest to ship, but weak multi-user state & fine-grained control |
| **Analytical app** | Dash (Flask+React+Plotly.js) or FastAPI + React | Interactive analytics, callbacks, custom layouts |
| **Product** | FastAPI backend + React/Next.js frontend, Postgres/Parquet cache | Real multi-user product, auth, scale |

**Recommended clean layering regardless of tier** (this is what makes the tool *maintainable*):

```
┌─────────────────────────────────────────────┐
│  UI layer (sliders, charts, tables)          │  ← present values, never recompute here
├─────────────────────────────────────────────┤
│  Valuation engine (pure functions)           │  ← DCF, WACC, comps math — NO I/O
├─────────────────────────────────────────────┤
│  Data access layer (fetch + cache + normalize)│ ← the only thing that talks to APIs/DB
├─────────────────────────────────────────────┤
│  Storage (SQLite/Postgres, Parquet, cache)   │
└─────────────────────────────────────────────┘
```

**Two non-negotiable rules (repeated across every good source):**
1. **The valuation engine is a pure, deterministic library** with zero network/database calls.
   Inputs in → outputs out. This is what makes it unit-testable and auditable.
2. **Cache + pre-aggregate.** Never hand a 100k-row DataFrame to a chart, and never re-fetch
   fundamentals on every interaction.

**Done when:** you've drawn a one-page diagram of the components and can say which technology
fills each box.

---

## Step 4 — Build the valuation engine (first, before any UI)

Build the core math as pure functions with tests. This is the part that must be *right*.

**Build order:**
1. **WACC module** — CAPM cost of equity, after-tax cost of debt, market-value weights.
2. **FCFF projection module** — revenue growth → margins → D&A → CapEx → ΔWC → FCFF per year.
3. **Terminal value module** — Gordon Growth + exit multiple (both).
4. **Discounting module** — PV of explicit FCFs + PV of TV, mid-year convention toggle.
5. **Equity bridge** — EV → equity → per-share.
6. **Comps module** — multiples, median/percentiles, implied value.
7. **Sensitivity module** — 2-D grids (WACC × growth, WACC × exit multiple).
8. **Scenario module** — bear/base/bull presets that vary the top drivers.

**Golden-source validation (do this before trusting any output):** hand-build the same model in
a spreadsheet for one well-known company (e.g. AAPL or MSFT), and confirm your engine matches
to the dollar. Every bug in valuation lives in the bridge/units (EBIT vs EBITDA vs net income,
per-share vs total, calendarization of fiscal years).

**Done when:** `test_dcf.py` and `test_comps.py` pass, and the engine output matches a
hand-built spreadsheet for one company.

---

## Step 5 — Build the data access layer

1. **Normalize** raw statements into a common schema (the #1 hidden cost — every API formats
   differently, and fiscal-year offsets differ across companies).
2. **Cache** aggressively (disk/SQLite/Redis) with sensible TTLs — daily for price, quarterly
   for fundamentals.
3. **Handle rate limits** gracefully (queue/backoff, degrade features rather than crash).
4. **Make assumptions visible** — the best tools show exactly which data points feed each
   assumption, and flag missing/stale data instead of silently filling gaps.

**Done when:** the engine can run on any ticker via the data layer without the engine itself
knowing where data came from.

---

## Step 6 — Build the interactive dashboard (the "interactive" part)

Start with a **single-company page**, then expand. The interactions that make a valuation tool
useful (rather than a static report) are:

1. **Assumption sliders / inputs** — revenue growth, operating margin, WACC, terminal growth,
   exit multiple, tax rate. Every drag recalculates instantly (engine is fast + cached).
2. **Scenario toggles** — bear/base/bull one-click presets.
3. **Sensitivity heatmaps** — WACC × terminal growth, WACC × exit multiple (color-coded table).
4. **Football field chart** — DCF vs comps vs analyst targets vs current price.
5. **Fair value vs. price chart** — price history with the intrinsic value line and a
   margin-of-safety band.
6. **Upside/downside headline** — intrinsic value per share, % upside, a clear (but
   disclaimered) signal, never presented as financial advice.

**Then, phase-2 features (in rough priority):**
- **Comps table** — editable peer set, median multiples, side-by-side comparison.
- **Financial statements viewer** — clean tables, 5-yr trends, growth/margin sparklines.
- **Watchlist** — with "current price vs. fair value" and % to buy-zone.
- **Screener** — filter the universe on valuation + quality + growth metrics.
- **Quality/moat overlay** — ROIC, margins, debt, Piotroski F-score (cheap *and* good).

**Done when:** you (or a friend) can value a company from scratch in under 2 minutes without
reading the code.

---

## Step 7 — Test & validate

- **Unit tests** on every engine function (boundary cases: negative FCF, WACC ≤ g, zero debt).
- **Spreadsheet cross-check** (from Step 4) — keep it as a permanent regression test.
- **Known-value sanity tests** — e.g. a perpetuity with g=0 and WACC=10% → value = FCF/0.10.
- **UI smoke tests** — does every slider round-trip without crashing or NaN-ing the chart.

**Done when:** `pytest` is green and one golden company matches your hand model.

---

## Step 8 — Deploy

1. Pin dependencies (minimum-version floors, e.g. `streamlit>=1.55, plotly>=6`).
2. Containerize (Docker) for reproducibility.
3. Host where it fits the audience: Streamlit Cloud / Render / Fly.io for personal; a managed
   Postgres + worker for a real product.
4. Add a prominent **"informational only, not investment advice"** disclaimer and data-source
   attribution (many free APIs *require* attribution in their ToS).

**Done when:** you can open it from a browser on another device and value a ticker.

---

## Step 9 — Iterate (backlog, in order of value)

1. Forward-looking anchors (analyst estimates) for growth instead of trailing history.
2. Monte Carlo on key drivers → probability distribution of value (instead of 3 scenarios).
3. Reverse-DCF ("what growth does today's price imply?") — very insightful, cheap to add.
4. Watchlist alerts (price crosses buy-zone, rating change, earnings date).
5. Sum-of-the-parts / segment-level views for conglomerates.
6. Sector-specific multiple conventions (banks, REITs, SaaS, E&P, etc.).

---

## Key references worth reading while you plan

- **Damodaran's intro to valuation** (the canonical 3-approach framing):
  `pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/ValIntroSpr24.pdf`
- **Damodaran on relative valuation** (multiple fundamentals, Propositions 1–4):
  `pages.stern.nyu.edu/~adamodar/pdfiles/country/relval.pdf`
- **DCF step-by-step + common mistakes** (TV dominance, sensitivity):
  `valuationmasterclass.com/how-to-build-a-dcf-model/`
- **Comps cheat sheet** (peer selection, EV bridge, sector multiples):
  `equityref.com/cheat-sheets/comparable-company-analysis/`
- **Fundamentals API comparison** (free tiers, SEC traceability):
  `developer.stockfit.io/blog/best-fundamentals-api`
- **Dashboard framework guide** (Streamlit vs Dash vs React, caching rules):
  `usedatabrain.com/how-to/create-python-dashboard`

---

## The 30-second summary

1. **Scope it** — one north-star question, 5 must-have features.
2. **Model it** — DCF + comps + football field; always a range, never a point.
3. **Feed it** — free API (yfinance → FMP/Alpha Vantage), cache everything.
4. **Layer it** — pure testable engine → data layer → thin UI.
5. **Build the engine first**, prove it against a spreadsheet.
6. **Make it interactive** — sliders, scenarios, sensitivity, football field.
7. **Deploy, disclaim, iterate** toward estimates, Monte Carlo, and reverse-DCF.
