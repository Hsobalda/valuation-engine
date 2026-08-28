#!/usr/bin/env python3
"""
reports_to_json.py -- bridge between the Python valuation engine and the
interactive website.

Reads:
    reports/*.md      (report_card.py output -- prices, methods, verdicts)
    engine_v01.py     (WATCHLIST dict -- moat, cyclicality, signed theses)

Emits ONE json file matching the site schema:
    src/engine/engine-data.json  (or ./engine-data.json)
"""

import argparse
import ast
import json
import re
import sys
from datetime import date
from pathlib import Path

DISPLAY = {
    "IMB.L":  {"name": "Imperial Brands", "sector": "Tobacco",            "exchange": "LSE"},
    "KGF.L":  {"name": "Kingfisher",      "sector": "DIY Retail",         "exchange": "LSE"},
    "TSCO.L": {"name": "Tesco",           "sector": "Grocery Retail",     "exchange": "LSE"},
    "EZJ.L":  {"name": "easyJet",         "sector": "Airlines",           "exchange": "LSE"},
    "T":      {"name": "AT&T",            "sector": "Telecoms",           "exchange": "NYSE"},
    "PEP":    {"name": "PepsiCo",         "sector": "Beverages & Snacks", "exchange": "NASDAQ"},
    "SPOT":   {"name": "Spotify",         "sector": "Streaming",          "exchange": "NYSE"},
}

NUM = r"(-?[\d,]+(?:\.\d+)?)"

def fnum(s):
    return float(s.replace(",", ""))

def parse_watchlist(engine_path: Path) -> dict:
    if not engine_path.exists():
        print(f"  ! {engine_path} not found", file=sys.stderr)
        return {}
    tree = ast.parse(engine_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "WATCHLIST":
                    return ast.literal_eval(node.value)
    return {}

def parse_card(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    ticker = path.stem.replace("_", ".")
    out = {"ticker": ticker}
    grab = lambda pat, src=text, flags=0: re.search(pat, src, flags)

    m = grab(r"^# (.+?) \(([^)]+)\) -- Report Card", text, re.M)
    legal_name = m.group(1).title() if m else ticker

    m = grab(r"Discount rate applied: (\d+(?:\.\d+)?)% \(([^)]+)\)")
    out["rate"] = float(m.group(1)) / 100 if m else 0.10
    out["rateNote"] = m.group(2) if m else "base 10%"

    m = grab(rf"\| Price \| {NUM} (GBp|USD) \| market cap ~{NUM}bn")
    out["price"] = fnum(m.group(1))
    out["ccy"] = m.group(2)
    out["mktCapBn"] = fnum(m.group(3))

    def snap(row):
        m = grab(rf"\| {row} \| ([^|]+) \| ([^|]+) \|")
        return (m.group(1).strip(), m.group(2).strip()) if m else (None, None)

    def pct_or_none(v):
        if v is None or "n/a" in v: return None
        m = re.search(NUM, v)
        return fnum(m.group(1)) if m else None

    v, note = snap("P/E")
    out["pe"] = pct_or_none(v)
    out["peNote"] = (note.split("->")[-1].replace(" see section 3", "").strip().replace("--", "—") if note else "")
    v, note = snap("P/B")
    out["pb"] = pct_or_none(v)
    out["pbNote"] = (note or "").replace("--", "—")
    v, _ = snap("Dividend yield")
    out["divYield"] = pct_or_none(v)
    v, note = snap("FCF yield")
    out["fcfYield"] = pct_or_none(v)
    out["fcfYieldNote"] = (note or "").replace("--", "—")

    def method(row):
        m = grab(rf"\| {re.escape(row)} \| ([^|]+) \| [^|]+ \| ([^|]+) \|")
        if not m: return None, ""
        raw, note = m.group(1).strip(), m.group(2).strip()
        return (None if "n/a" in raw else fnum(raw)), note

    epv, _ = method("EPV")
    bear, bear_note = method("DCF(bear)")
    graham, _ = method("Graham")
    mult, _ = method("Multiples")
    out["methods"] = {"EPV": epv, "bear": bear, "graham": graham, "mult": mult}

    m = grab(r"\(used ([+-]?[\d.]+)%\)", bear_note)
    out["bearG"] = float(m.group(1)) / 100 if m else 0.0

    m = grab(rf"\*\*Consensus \(median\): {NUM} [A-Z]+ -> margin of safety ([+-]?[\d.]+)%\.\*\* Method spread ([\d.]+)x: (.*?)\.")
    out["consensus"] = fnum(m.group(1))
    out["mos"] = float(m.group(2)) / 100
    out["spread"] = float(m.group(3))
    tail = m.group(4)
    out["spreadState"] = ("agree" if "AGREE" in tail else "disagree" if "DISAGREE" in tail else "scatter")

    m = grab(r"FCF history \(bn, oldest->newest\): ([\d. ->]+)\s+\(trend ([+-]?[\d.]+)%/yr\)")
    out["fcfHist"] = [float(x) for x in m.group(1).split("->")]
    out["fcfTrend"] = float(m.group(2)) / 100
    m = grab(rf"Bull-case DCF \(growth ([\d.]+)%\): {NUM}")
    out["bullG"] = float(m.group(1)) / 100
    out["bull"] = fnum(m.group(2))
    m = grab(r"implies ([+-]?[\d.]+)%/yr FCF growth")
    out["impliedGrowth"] = float(m.group(1)) / 100

    m = grab(rf"Interest coverage: {NUM}x -- ([^(\n]+)")
    out["coverage"] = fnum(m.group(1)) if m else None
    out["coverageNote"] = m.group(2).strip() if m else ""
    m = grab(r"FCF negative years: (\d+) of (\d+)")
    out["negFcfYears"] = int(m.group(1))
    out["fcfYears"] = int(m.group(2))
    m = grab(rf"Capex / D&A: {NUM} -- ([^\n]+)")
    out["capexDa"] = fnum(m.group(1)) if m else None
    out["capexNote"] = m.group(2).strip() if m else ""
    m = grab(r"Fatal flags: ([^\n]+)")
    out["flags"] = [] if not m or m.group(1).strip() == "none" else [f.strip() for f in m.group(1).split(",")]

    m = grab(r"\*\*Verdict: ([A-Z ]+?)\*\*(?: \(weight (\d+)%\))?")
    out["verdict"] = m.group(1).strip()
    out["weight"] = int(m.group(2)) / 100 if m.group(2) else 0.0
    out["engineNotes"] = [n.strip().replace("--", "—") for n in re.findall(r"- capped/noted: ([^\n]+)", text)]
    m = grab(rf"CAUTIOUS BUY below {NUM} \| BUY below {NUM} \| STRONG BUY below {NUM}")
    out["triggers"] = {"cautious": fnum(m.group(1)), "buy": fnum(m.group(2)), "strong": fnum(m.group(3))}

    qsec = text.split("## 6 |", 1)[-1]
    out["questions"] = [re.sub(r"^\d+\.\s*", "", q).strip() for q in re.findall(r"^\d+\..+$", qsec, re.M)]

    out["normFcfPps"] = round(epv * out["rate"], 6) if epv is not None else 0.0
    out["normEps"] = round(mult / 15, 6) if mult is not None else None

    disp = DISPLAY.get(ticker, {"name": legal_name, "sector": "—", "exchange": "—"})
    out.update(disp)
    return out

def merge_human(rec: dict, wl: dict) -> None:
    human = wl.get(rec["ticker"]) or {}
    rec["moat"] = human.get("moat", "—")
    rec["cyclical"] = bool(human.get("cyclical", False))
    thesis = " ".join((human.get("thesis") or "").split())
    rec["thesis"] = thesis
    m = re.search(r"\[Signed ([^\]]+)\]", thesis)
    rec["signedDate"] = m.group(1) if m else ""

    first = (thesis.split(". ")[0] + ".") if thesis else ""
    rec["ownerVerdict"] = None
    if "owner override" in first.lower():
        cap = re.search(r"(\d+)% weight", first)
        label = first[:-1].replace("(owner override,", "· owner override ·").replace("weight cap", "").replace("  ", " ").strip()
        rec["ownerVerdict"] = label
        rec["weight"] = int(cap.group(1)) / 100 if cap else rec["weight"]
    elif re.match(r"^(SELL|EXIT)\b", first):
        rec["ownerVerdict"] = "SELL / EXIT · special situation"
        rec["weight"] = 0.0

    if rec["cyclical"] and 0.15 <= rec["mos"] < 0.25 and rec["verdict"] == "WATCH":
        note = f"cyclical: margin-of-safety bar raised +10pts (needs 25%, has {rec['mos']*100:.0f}%)"
        if note not in rec["engineNotes"]:
            rec["engineNotes"].append(note)
    if rec["spreadState"] == "disagree" and not any("disagree" in n for n in rec["engineNotes"]):
        rec["engineNotes"].insert(0, f"methods disagree {rec['spread']:.1f}x > 2.5 — you do not understand this company yet")
    if rec["methods"]["graham"] is None and rec.get("pb") and rec["pb"] > 5:
        note = f"graham disabled: P/B {rec['pb']:.1f} > 5 (low reliability self-flag)"
        if not any("graham" in n for n in rec["engineNotes"]):
            rec["engineNotes"].append(note)

KEY_ORDER = [
    "ticker", "name", "sector", "exchange", "ccy", "moat", "cyclical", "rate", "rateNote",
    "price", "mktCapBn", "pe", "pb", "divYield", "fcfYield", "peNote", "pbNote", "fcfYieldNote",
    "fcfHist", "fcfTrend", "normFcfPps", "normEps", "bearG", "bullG", "methods", "bull",
    "consensus", "mos", "spread", "spreadState", "verdict", "engineNotes", "ownerVerdict",
    "weight", "triggers", "impliedGrowth", "coverage", "coverageNote", "capexDa", "capexNote",
    "negFcfYears", "fcfYears", "flags", "thesis", "signedDate", "questions",
]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--reports-dir", default=None)
    ap.add_argument("--engine", default=None)
    ap.add_argument("--out", default="engine-data.json")
    args = ap.parse_args()

    repo = Path(args.repo)
    reports_dir = Path(args.reports_dir) if args.reports_dir else repo / "reports"
    engine_path = Path(args.engine) if args.engine else repo / "engine_v01.py"

    cards = sorted(reports_dir.glob("*.md"))
    if not cards:
        sys.exit(f"no report cards found in {reports_dir}")

    watchlist = parse_watchlist(engine_path)
    companies = []
    for card in cards:
        rec = parse_card(card)
        merge_human(rec, watchlist)
        companies.append({k: rec.get(k) for k in KEY_ORDER})
        print(f"  ok {rec['ticker']:7s} {rec['verdict']:<13s} MoS {rec['mos']*100:+.0f}%")

    payload = {
        "generatedFrom": "reports/*.md + engine_v01.py WATCHLIST via scripts/reports_to_json.py",
        "generatedAt": date.today().isoformat(),
        "companies": companies,
    }
    out_path = Path(args.out)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path} ({len(companies)} companies)")

if __name__ == "__main__":
    main()
