# The Research-First Workflow: Evidence Before Judgment

> The engine does the math. You do the judgment. But there's a step *before* judgment
> that matters just as much: **evidence.** This doc designs the layer that turns raw data
> into an understandable research brief, so that every number you later type into the
> valuation is a *decision you can defend* — not a default you inherited.

---

## The principle

Damodaran's framing is the anchor: *"A good valuation is a marriage between stories and
numbers. Every number in your valuation has to have a story attached, and every story has
to have a number attached."* His working sequence is:

```
story → reality-check against data → convert to numbers → feedback loop
```

Your instinct restates this as a product rule: **the tool must never ask you for an
assumption it hasn't first shown you the evidence for.** Raw data → understandable
format → *your* decision → the engine's math. The engine is downstream of your judgment,
and your judgment is downstream of the evidence.

The one iron rule that follows:

> **The research brief SHOWS evidence; it never draws the conclusion.** It shows the ROIC
> spread, the margin history, the leverage — it does not say "wide moat" or "undervalued."
> The conclusion is *yours*, because the conclusion is the entire job.

---

## The research brief: what the tool assembles before you touch anything

Six panels, ordered so context precedes numbers. Each panel transforms raw data into
evidence and ends in a specific decision it feeds.

### Panel A — What is this business? *(understanding → go/no-go)*

| Raw data | Transformed into evidence |
|---|---|
| 10-K Item 1, MD&A, segment note | One-paragraph business model: how it makes money, what it sells, who pays |
| Segment revenue | Revenue mix by segment/geography (stacked bar) |
| Revenue recognition note | Recurring vs. lumpy revenue, subscription vs. project |

**Purpose:** the "circle of competence" test. If you can't explain how the business makes
money in one sentence, you shouldn't be valuing it yet.

**Decision it feeds:** *Do I proceed?* (and it frames every later assumption — the TAM and
revenue story are a *choice*, as Damodaran's Uber example shows: "urban car service" vs.
"global transportation platform" is a story decision that moves the whole valuation.)

### Panel B — What has it done? *(history → the forecast baseline)*

| Raw data | Transformed into evidence |
|---|---|
| Income statement, 10 yrs | Revenue, EBITDA, net income trend (indexed to year 1) |
| Margins | Gross / operating / net margin *trajectory* over 10 yrs, not a snapshot |
| Cash flow statement | FCF trend + FCF vs. net income (cash conversion) |
| Balance sheet | Shares outstanding trend (dilution), book value, debt trend |

**Purpose:** establish the *empirical* anchor for growth and margin assumptions. Every
forecast is a deviation from this history, and the deviation is the thing you must justify.

**Decision it feeds:** your growth and margin inputs — but with the history sitting right
next to the input box so "I'll assume 12% growth" is visibly a claim *above* the 6% the
company has actually done.

### Panel C — How good is it? *(quality fingerprints → the moat / fade decision)*

This is the moat evidence, presented as *facts, not a rating*:

| Evidence | What it lets you judge |
|---|---|
| ROIC vs. WACC over 10 years (spread chart) | Is there a moat at all, and is it widening/narrowing? |
| Gross margin std. dev. (stability) | Pricing power vs. commodity/competitive pressure |
| FCF / net income (≥ 1 = quality) | Are earnings real cash? |
| Customer concentration | Fragility to a single buyer |
| ROIC spread *duration* (how many years > 0) | The fade period you'll choose |

**Decision it feeds:** the **fade period** — the single most important input in the whole
model (it *is* the moat rating, as Morningstar's 3-stage DCF shows). The panel gives you
the raw material to choose 5 vs. 15 vs. 20 years, but *you* make the call.

### Panel D — How is it managed? *(capital allocation → reinvestment & dilution)*

| Evidence | What it lets you judge |
|---|---|
| 5-yr uses of cash (capex / M&A / buybacks / dividends) | Is capital being reinvested well or burned? |
| Shares outstanding trend | Dilution working for or against you |
| Insider ownership & recent Form 4 activity | Are insiders aligned with you? |
| Buybacks at high vs. low prices | Is management capital-allocation-disciplined? |

**Decision it feeds:** reinvestment rate and the share count in your equity bridge (and
skepticism about management guidance you're about to read).

### Panel E — What could go wrong? *(risks → discount rate & margin of safety)*

| Evidence | What it lets you judge |
|---|---|
| Net debt / EBITDA, leverage trend, debt maturities | Balance-sheet fragility |
| 10-K Item 1A risk factors (year-over-year *changes*) | What management itself now worries about |
| Accounting red flags (FCF < NI persistently, goodwill %, WC deterioration) | Earnings quality |
| Beta, price volatility, cyclicality of earnings | How uncertain the cash flows really are |

**Decision it feeds:** the **discount rate** (higher uncertainty → higher WACC) and the
**margin of safety** (lower confidence in the value → larger required discount). This is
the bridge we established earlier: the moat (Panel C) *lowers* the required margin; the
risks (Panel E) *raise* it.

### Panel F — What's already priced in? *(market view → the reality check)*

| Evidence | What it lets you judge |
|---|---|
| Current P/E, EV/EBITDA, EV/Revenue vs. 5-yr own history | Is the market already paying up? |
| Same multiples vs. a peer set | Is the premium/discount justified by Panels B–E? |
| Analyst targets + consensus growth | What's the *consensus* story you're agreeing/disagreeing with? |
| Reverse DCF: growth implied by today's price | The market's embedded forecast, made explicit |

**Decision it feeds:** your **variant view** — the specific place you believe the market is
wrong. This is what a real thesis requires ("what does the market believe, what do I
believe differently, why does it matter to value?"). Without this panel you're just
re-deriving the market's own number.

---

## The transformation rules (raw → evidence)

The manipulation you asked for — "raw data into some understandable format" — has five
consistent moves. The data layer should apply all of them mechanically, every time:

1. **Normalize** — calendarize fiscal years, use TTM where appropriate, keep per-share vs.
   total consistent, reconcile GAAP vs. non-GAAP with visible adjustments.
2. **Trend-ize** — always show a 5–10 year *series*, never a single-year snapshot. A moat
   is visible only in the series.
3. **Benchmark** — against the company's own history AND a peer set. Absolute numbers are
   meaningless; relative ones are evidence.
4. **Flag** — surface anomalies automatically (stale data, missing quarters, FCF < NI
   persistently, concentration > 20%, goodwill > 40% of assets). Flag, don't conclude.
5. **Contextualize** — each figure carries a one-line "what this means" gloss, in plain
   language, tied back to which decision it will inform.

The discipline: **the brief is a mirror, not a verdict.** It exists so that when you type
"fade = 15 years," that number is the *summary of evidence you just read*, not a guess.

---

## The full workflow, end to end

```
1. RAW DATA (filings, statements, prices, estimates)
        ↓  [data layer: normalize, trend-ize, benchmark, flag, contextualize]
2. RESEARCH BRIEF (Panels A–F, evidence only)
        ↓  [YOU read it]
3. STORY / THESIS (your variant view — where is the market wrong?)
        ↓  [reality-check the story against the brief]
4. ASSUMPTIONS (growth, margins, fade, discount rate, MoS — each anchored to a panel)
        ↓  [engine: pure math]
5. VALUATION (a range + distribution, not a point)
        ↓  [sensitivity shows which assumption is load-bearing]
6. DECISION (price vs. margin-of-safety-adjusted value)
        ↓
   feedback loop: new data → brief updates → story re-checked
```

The critical ordering: **panels are shown, then inputs are requested — never the reverse.**
Each input field in the UI should sit *adjacent to* the panel of evidence that justifies
it, so the relationship is visible rather than implied.

---

## What this means for the build

- **The research brief is its own first-class component**, not an afterthought bolted onto
  a valuation page. Build it *before* the assumption panel.
- **The data layer has two outputs:** (1) the evidence panels, and (2) the parameterized
  inputs the engine needs. The same fetched data feeds both — the brief is the "human"
  view, the engine input is the "machine" view of the *same* normalized data.
- **Every assumption input is annotated** with: which panel it came from, the range the
  evidence supports, and what changing it does (a one-line sensitivity note).
- **Defaults are forbidden as silent values.** If the engine needs a number you haven't
  chosen, it should be visibly labelled "DEFAULT — not yet justified," so an assumption
  can never sneak into the model without you seeing it.
- **The brief is reusable:** the screener/watchlist can reuse Panels B, C, and E as the
  triage layer (uniform treatment at the top of the funnel), while the full A–F brief is
  the deep-dive (individual treatment at the bottom).

---

## Key references

- **Damodaran, "Narrative and Numbers"** (the story→reality-check→numbers→feedback loop):
  `aswathdamodaran.substack.com/p/narrative-and-numbers-how-a-number-17-01-11`
  and `seanmaguinness.substack.com/p/narratives-and-numbers-a-beginners`
- **Equity research report structure** (thesis before model, variant view, falsifiable):
  `valuationmasterclass.com/equity-research-report/` and
  `boardinfinity.com/blog/building-an-investment-thesis-structure/`
- **10-K analysis sequence** (MD&A + financials first, footnotes as primary research,
  red-flag list): `minalyst.com/blog/research-guides/how-to-analyze-10k-filing`
- **Due-diligence checklist** (business → financials → management → risk stages):
  `minalyst.com/blog/research-guides/due-diligence-checklist`
