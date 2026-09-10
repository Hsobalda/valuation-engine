# BUILD SPEC — Valuation Engine (v1)

> **START HERE.** This is the single source of truth for the build. It locks every
> decision, pins every contract, and defines the build order with checkpoints.
> The four reasoning docs (`PLANNING.md`, `VALUATION-THINKING.md`,
> `RESEARCH-FIRST-WORKFLOW.md`) are the *appendix* — read them for "why", not for "how".

---

## 0. Decisions (locked — do not relitigate)

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | matches the pure-engine design |
| UI framework | **Streamlit** | fastest to a working interactive tool; sliders + Plotly native; upgrade path to Dash/React documented but out of scope |
| Data source | **yfinance** for v1, behind a `DataProvider` interface | zero setup, no key, gets the pipeline end-to-end; swap to FMP/Alpha Vantage later without touching engine or UI |
| Charts | Plotly (via Streamlit) | interactive, share the same data as the tables |
| Scope | **Single-company deep dive + comps** | see §1 |
| Storage | in-memory + `@st.cache_data` (no DB in v1) | single-user; caching solves the rate-limit problem |
| Testing | `pytest` for the engine | the engine is pure and must be provably correct |

---

## 1. V1 scope

**IN (build this):**
1. Data access layer + normalized schema + caching
2. Valuation engine (pure library): WACC → projection → 3-stage DCF → sensitivity
3. Research brief (panels B, C, E, F — see §6; A and D are lightweight v1 versions)
4. Assumption panel (editable inputs, no silent defaults) wired to the engine
5. Comps module + football field
6. Margin of safety / buy-zone display
7. Disclaimers + attribution (required by data ToS)

**OUT (backlog — do NOT build in v1):** screener, watchlist, Monte Carlo, reverse DCF,
segment/SOTP, portfolio tracking, auth, database, alerts, analyst-estimate integration.

---

## 2. Project structure

```
valuation-engine/
├── app.py                    # Streamlit entry point (UI only, thin)
├── engine/                   # PURE library — zero I/O, zero Streamlit imports
│   ├── __init__.py
│   ├── wacc.py               # cost_of_equity(), wacc()
│   ├── projection.py         # project_fcff()
│   ├── dcf.py                # dcf_3stage() -> ValuationResult
│   ├── sensitivity.py        # sensitivity_grid()
│   ├── comps.py              # comps_analysis()
│   └── quality.py            # roic, margins, fcf_conversion, moat indicators
├── data/                     # data access layer — the ONLY thing that talks to yfinance
│   ├── __init__.py
│   ├── provider.py           # DataProvider protocol + YFinanceProvider
│   ├── schema.py             # normalized schema constants + normalizers
│   └── cache.py              # @st.cache_data wrappers
├── brief/                    # builds the research brief panels from normalized data
│   ├── __init__.py
│   └── panels.py             # one function per panel -> dict of evidence
├── ui/                       # Streamlit render helpers (layout, not logic)
│   ├── __init__.py
│   ├── assumptions.py        # input widgets + "default not justified" labels
│   └── charts.py             # football field, sensitivity heatmap, etc.
├── tests/
│   ├── test_wacc.py
│   ├── test_projection.py
│   ├── test_dcf.py           # includes the spreadsheet cross-check + sanity tests
│   ├── test_comps.py
│   └── test_quality.py
├── requirements.txt
└── README.md
```

**Hard rules:**
- `engine/` imports NOTHING from `data/`, `brief/`, `ui/`, `streamlit`, or `yfinance`.
- `data/` is the only layer that imports `yfinance`.
- `app.py` only wires layers together; no valuation math lives there.

---

## 3. Data contract (normalized schema)

`data/schema.py` defines canonical column names. All providers normalize into these.
**Fiscal years are calendarized** (use the company's fiscal-year dates, but align series
by fiscal year end). Use **TTM where noted**.

### Income statement — `INCOME_FIELDS`
`revenue, cost_of_revenue, gross_profit, operating_income, interest_expense,
pretax_income, income_tax, net_income, eps_diluted`

### Balance sheet — `BALANCE_FIELDS`
`cash_and_equiv, short_term_investments, total_debt, total_assets, total_liabilities,
stockholder_equity, minority_interest, goodwill`

### Cash flow — `CASHFLOW_FIELDS`
`operating_cash_flow, capital_expenditure, dividends_paid, stock_buybacks`

### Market data — `market_data(ticker) -> dict`
`price, market_cap, beta, shares_outstanding, shares_diluted, fifty_two_week_high_low`

### Company info — `company_info(ticker) -> dict`
`sector, industry, long_business_summary, full_name, country`

### Derived (computed in `engine/quality.py`, never fetched)
`ebitda = operating_income + d&a`, `fcf = operating_cash_flow - capital_expenditure`,
`fcf_conversion = fcf / net_income`, `roic = nopat / invested_capital`,
`net_debt = total_debt - (cash_and_equiv + short_term_investments)`,
`ev = market_cap + net_debt + minority_interest - cash... (per equity bridge)`,
growth rates and 10-yr margin std. dev.

---

## 4. Engine API (exact signatures — implement these)

```python
# engine/wacc.py
def cost_of_equity(risk_free: float, beta: float, erp: float) -> float
def wacc(equity_value: float, debt_value: float, cost_equity: float,
         cost_debt: float, tax_rate: float) -> float
```

```python
# engine/projection.py
def project_fcff(
    base_revenue: float,
    revenue_growth: float,          # Stage 1 annual growth (decimal, e.g. 0.08)
    ebit_margin: float,
    tax_rate: float,
    da_pct_revenue: float,          # D&A as % of revenue
    capex_pct_revenue: float,       # capex as % of revenue
    nwc_pct_revenue: float,         # net working capital as % of revenue
    years: int = 5,
) -> list[float]
```

```python
# engine/dcf.py
@dataclass
class ValuationResult:
    pv_explicit: float      # PV of Stage-1 FCFF
    pv_fade: float          # PV of Stage-2 (fade) FCFF
    pv_terminal: float      # PV of terminal value
    enterprise_value: float
    equity_value: float
    equity_value_per_share: float
    terminal_share_of_ev: float   # must be surfaced; warn if > 0.8

def dcf_3stage(
    fcff_stage1: list[float],
    wacc: float,
    fade_years: int,          # THE moat input: 5 / 10 / 15 / 20
    terminal_growth: float,   # 0.02 – 0.03
    final_ebit_margin: float = 0.0,   # where margins fade to (optional)
    net_debt: float = 0.0,
    minority_interest: float = 0.0,
    cash: float = 0.0,
    shares_diluted: float = 1.0,
) -> ValuationResult
```

**Fade semantics (Stage 2):** from year 5 to year `5 + fade_years`, the Stage-1 exit
growth decays **linearly** toward `terminal_growth` (and, if `final_ebit_margin` is set,
the margin decays linearly to it). Stage 3 = Gordon Growth perpetuity on the last fade-year
cash flow. This operationalizes the moat as `fade_years`, exactly as designed in
`VALUATION-THINKING.md`.

```python
# engine/sensitivity.py
def sensitivity_grid(
    fcff_stage1: list[float],
    wacc_range: tuple[float, float, float],     # (min, max, step)
    growth_range: tuple[float, float, float],   # terminal growth (min, max, step)
    fade_years: int,
    **bridge_kwargs,
) -> pd.DataFrame   # index=wacc, columns=growth, values=equity_value_per_share
```

```python
# engine/comps.py
@dataclass
class CompsResult:
    peer_table: pd.DataFrame   # rows=peers, cols=EV/EBITDA, P/E, EV/Revenue, P/B
    medians: dict[str, float]
    implied_values: dict[str, float]   # median multiple × target metric

def comps_analysis(target_ticker: str, peers: list[str], metrics: list[str],
                   provider: DataProvider) -> CompsResult
```

```python
# engine/quality.py
def roic_series(nopat: pd.Series, invested_capital: pd.Series) -> pd.Series
def margin_stability(margins: pd.Series) -> float          # std. dev.
def fcf_conversion_series(fcf: pd.Series, net_income: pd.Series) -> pd.Series
```

---

## 5. Data access layer

```python
# data/provider.py
class DataProvider(Protocol):
    def income_statement(self, ticker: str, period: str = "annual") -> pd.DataFrame
    def balance_sheet(self, ticker: str, period: str = "annual") -> pd.DataFrame
    def cash_flow(self, ticker: str, period: str = "annual") -> pd.DataFrame
    def market_data(self, ticker: str) -> dict
    def company_info(self, ticker: str) -> dict
```

- `YFinanceProvider` implements it; every method returns the **normalized schema** from §3.
- Wrap all provider calls in `@st.cache_data(ttl=86400)` (daily) via `data/cache.py`.
- `comps_analysis()` and the brief may call `provider` for peers too — same cache applies.
- **Swap path:** implement `FmpProvider` or `AlphaVantageProvider` later; nothing else changes.

---

## 6. Research brief panels (evidence only — never a conclusion)

`brief/panels.py` exposes one pure function per panel returning a dict of *evidence*.
Each panel renders as: chart/table + "what this means" one-liner + the decision it feeds.

| Panel | Computes & renders | Feeds decision |
|---|---|---|
| **A — Business** (v1 light) | name, sector, industry, one-paragraph summary, revenue mix if segments available | go/no-go + the revenue story |
| **B — History** | 10-yr revenue/EBITDA/net income indexed chart; gross/op/net margin trajectory; FCF trend + conversion | growth & margin inputs (history sits beside the input) |
| **C — Quality (moat)** | ROIC vs WACC spread over 10 yrs; gross-margin std. dev.; FCF/income; customer concentration (if available) | **fade_years** input |
| **E — Risk** | net debt/EBITDA trend; leverage; FCF<NI flag; beta & price vol; earnings-quality flags | **WACC** & **margin of safety** |
| **F — Priced in** | current P/E, EV/EBITDA, EV/Revenue vs 5-yr own history + peers; analyst target (basic); simple "growth implied by price" note | **variant view** (where is the market wrong?) |

**Flag list (auto-surface, do NOT conclude):** FCF < net income for 3+ consecutive years;
customer > 20% concentration; goodwill > 40% of assets; working-capital deterioration
while revenue grows; stale/missing data.

---

## 7. UI layout (`app.py`, single page, top-to-bottom)

```
1. Ticker input + "Analyze"
2. RESEARCH BRIEF (Panels A–F)          ← shown FIRST, read-only
3. ASSUMPTION PANEL (editable widgets)  ← each input sits beside its evidence panel
   - growth, ebit margin, tax rate, capex %, NWC %
   - fade_years (slider 5/10/15/20, labelled "moat: no/narrow/wide")
   - WACC inputs (risk-free, beta, ERP, cost of debt, weights) OR direct WACC
   - terminal growth
   - every widget shows "DEFAULT — not yet justified" until the user changes it
4. VALUATION OUTPUT
   - equity value per share + % upside/downside vs price
   - terminal value as % of EV (warn if > 80%)
   - sensitivity heatmap (WACC × terminal growth)
   - football field (DCF range vs comps range vs analyst target vs current price)
   - margin-of-safety band (value × (1 − MoS)) + buy-zone line
5. COMPARABLES (editable peer set + multiples table)
6. Disclaimer: "Informational only — not investment advice." + data attribution.
```

---

## 8. Acceptance criteria (v1 is "done" only when ALL pass)

1. `pytest` green across `tests/`.
2. **Spreadsheet cross-check:** hand-build AAPL in Excel/Sheets (5-yr FCFF + WACC +
   Gordon Growth) and confirm `dcf_3stage()` matches to within ±1%. Keep the spreadsheet
   inputs in `tests/test_dcf.py` as a permanent regression test.
3. **Sanity test:** perpetuity with `g=0`, `wacc=0.10`, `fcf=100` → value = 1000.
4. Running the app: enter `AAPL` → brief renders → change `fade_years` and WACC → value
   updates instantly with no crash/NaN.
5. Sensitivity heatmap and football field render for AAPL + a peer set.
6. Every unfilled assumption is visibly labelled "default — not justified."

---

## 9. Build order (stop and verify at each checkpoint)

1. **Data layer** → `data/` + schema + cache.
   ✅ *Checkpoint:* fetch AAPL, print normalized 3 statements + market data.
2. **Engine core** → `wacc.py`, `projection.py`, `dcf.py`.
   ✅ *Checkpoint:* `test_dcf.py` passes incl. spreadsheet match + sanity test.
3. **Quality + sensitivity** → `quality.py`, `sensitivity.py`.
   ✅ *Checkpoint:* ROIC series and sensitivity grid return correct shapes/values.
4. **Research brief** → `brief/panels.py` + render in app.
   ✅ *Checkpoint:* AAPL brief renders all panels with real data.
5. **Assumption panel** → `ui/assumptions.py` wired to engine.
   ✅ *Checkpoint:* dragging `fade_years` recomputes value live.
6. **Comps + football field** → `comps.py` + `ui/charts.py`.
   ✅ *Checkpoint:* AAPL vs 4 peers renders table + football field.
7. **Margin of safety + disclaimers** → final polish, empty/error states.
   ✅ *Checkpoint:* full acceptance criteria §8 pass.

---

## 10. Non-negotiable rules (repeated for emphasis)

- The engine is pure and deterministic. No I/O, no Streamlit, no yfinance.
- Every assumption is a visible input; **no silent defaults**.
- The brief **shows evidence, never concludes** — no "wide moat" or "undervalued" verdicts.
- Always show a **range** (sensitivity + scenarios), never a single point as "the" value.
- Terminal value as % of EV is always surfaced; warn above 80%.
- Cache every network call; never re-fetch on a slider drag.
