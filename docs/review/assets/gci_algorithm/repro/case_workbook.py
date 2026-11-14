"""Corrected copy of the owner's 40-case workbook (GCI v2.5 diffusion vs tech team), 13 Nov 2026.

Every score comes from the method lab (``gci_scoring.lab_row_score`` / ``lab_run`` /
``lab_behaviour``), the same code behind ``POST /api/v1/index/lab/run``. Research only:
nothing here is stored, ranked or published.

Run from the repo root:
    PYTHONPATH=backend python3 docs/review/assets/gci_algorithm/repro/case_workbook.py
"""
import os
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "backend"))

from app.data import metric_catalog  # noqa: E402
from app.jobs.validation_gates import _scored_companies, core_inputs  # noqa: E402
from app.services import gci_scoring as g  # noqa: E402

ASSETS = Path(__file__).resolve().parents[1]
SOURCE = ASSETS / "GCI_v2.5_vs_Tech_Team_40_Case_Evaluation.xlsx"
OUT = ASSETS / "GCI_40_Case_Evaluation_corrected_13_Nov_2026.xlsx"

# The catalog has no lower-is-better rate, cost amount or leverage metric. These exist in this script only.
RESEARCH_METRICS = {
    "opex_growth_pct": {"id": "opex_growth_pct", "display_name": "Opex growth (%)", "unit": "pct",
                        "family": "growth", "direction": "lower"},
    "opex_usd_mn": {"id": "opex_usd_mn", "display_name": "Opex (US$ m)", "unit": "usd_mn",
                    "family": "cost", "direction": "lower"},
    "net_debt_to_ebitda_x": {"id": "net_debt_to_ebitda_x", "display_name": "Net debt / EBITDA (x)", "unit": "x",
                             "family": "leverage", "direction": "lower"},
    "roce_wacc_spread_pct": {"id": "roce_wacc_spread_pct", "display_name": "ROCE over WACC (pp)", "unit": "pct",
                             "family": "returns", "direction": "higher"},
}
metric_catalog._BY_ID.update(RESEARCH_METRICS)

COMPARISONS = [
    g.lab_resolve({"id": "v4", "method": "classic"}),
    g.lab_resolve({"id": "range", "method": "range"}),
    g.lab_resolve({"id": "range_a1", "method": "range", "params": {"met_bound_full": False}}),
    g.lab_resolve({"id": "range_p", "method": "range_p"}),
    g.lab_resolve({"id": "diffusion", "method": "diffusion"}),
    g.lab_resolve({"id": "bias", "method": "diffusion", "preset": "guidance_bias"}),
]
LABELS = {
    "v4": "v4 (published scorer)",
    "range": "GCI Range: R2 with A1–A5 (tech proposal)",
    "range_a1": "R2 with A1 only (what the sheet shows)",
    "range_p": "Range-P (12 Nov scan)",
    "diffusion": "Diffusion (owner note)",
    "bias": "Guidance Bias (diffusion with direction and 5 pp growth floor)",
}
PREFERENCE_CHOICES = ["v4", "GCI Range A1-A5", "Range-P", "Diffusion", "Guidance Bias"]

# case: (metric, low, high, bound, note); low == high is a point target.
PCT_CASES = {
    1: ("revenue_growth_cc_pct", 6, 10, None, ""),
    2: ("operating_margin_pct", 0, 10, None, ""),
    3: ("revenue_growth_cc_pct", -10, 10, None, "Zero midpoint: diffusion is not defined."),
    4: ("operating_margin_pct", -10, 0, None, ""),
    5: ("revenue_growth_cc_pct", 10, 10, "floor", ""),
    6: ("revenue_growth_cc_pct", 10, 10, "floor", "Same as case 5: strict and inclusive floors differ only on the bound."),
    7: ("opex_growth_pct", 10, 10, "ceiling", "A ceiling: above it is a miss. Research metric opex growth."),
    8: ("opex_growth_pct", 10, 10, "ceiling", "Same as case 7."),
    9: ("revenue_growth_cc_pct", 0, 0, None, "Zero midpoint: diffusion is not defined."),
    10: ("revenue_growth_cc_pct", 15, 15, None, ""),
    11: ("revenue_growth_cc_pct", 2, 8, None, ""),
    12: ("revenue_growth_cc_pct", 2, 8, None, "Same as case 11: open and closed endpoints differ only on the bound."),
    13: ("revenue_growth_cc_pct", 2, 8, None, "Same as case 11."),
    14: ("revenue_growth_cc_pct", -8, -2, None, ""),
    15: ("revenue_growth_cc_pct", -2, 8, None, ""),
    16: ("revenue_growth_cc_pct", 0, 0, "floor", "Zero floor: diffusion is not defined."),
    17: ("revenue_growth_cc_pct", 10, 10, None, "\"Target ≠ 10%\" is not a form of guidance. Scored as a point target of 10%."),
    18: ("revenue_growth_cc_pct", 5, 10, None, ""),
    19: ("revenue_growth_cc_pct", 20, 20, None, "No log transform is applied by any column."),
    20: ("roce_wacc_spread_pct", 3.5, 3.5, None, "Research metric ROCE over WACC."),
}
AMT_CASES = {
    **{k: ("revenue_usd_mn", lo, hi, b, n) for k, (_, lo, hi, b, n) in PCT_CASES.items()},
    7: ("opex_usd_mn", 10, 10, "ceiling", "A ceiling: above it is a miss. Research metric opex (US$ m)."),
    8: ("opex_usd_mn", 10, 10, "ceiling", "Same as case 7."),
    10: ("revenue_usd_mn", 10, 10, None, ""),
    18: ("revenue_usd_mn", 10, 20, None, ""),
    19: ("revenue_usd_mn", 100, 100, None, "No log transform is applied by any column."),
    20: ("net_debt_to_ebitda_x", 2.5, 2.5, "ceiling",
         "A leverage cap, in times, not $M. Research metric net debt / EBITDA. −2.5x means net cash."),
}

HEAD = Font(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F3A5F")
SHEET_FILL = PatternFill("solid", fgColor="EDEDED")
WRONG_FILL = PatternFill("solid", fgColor="F8CBAD")
FLAG_FILL = PatternFill("solid", fgColor="FFF2CC")
WRAP = Alignment(wrap_text=True, vertical="top")


def score(cid, metric, lo, hi, actual, bound):
    c = next(c for c in COMPARISONS if c["id"] == cid)
    r = g.lab_row_score(c["method"], c["params"], metric, lo, hi, actual, bound=bound)
    return r["score"] if r["score"] is not None else "not defined"


def position(lo, hi, actual, bound):
    if bound == "floor":
        return "met floor" if actual >= lo else "below floor"
    if bound == "ceiling":
        return "met ceiling" if actual <= hi else "above ceiling"
    if lo == hi:
        return "on target" if actual == lo else "above target" if actual > lo else "below target"
    if actual == lo:
        return "inside, on lower bound"
    if actual == hi:
        return "inside, on upper bound"
    if lo < actual < hi:
        return "inside"
    return "above range" if actual > hi else "below range"


def promise(lo, hi, bound):
    if bound == "floor":
        return f"at least {lo:g}"
    if bound == "ceiling":
        return f"at most {hi:g}"
    return f"{lo:g}" if lo == hi else f"{lo:g} to {hi:g}"


def differs(a, b):
    if isinstance(a, str) or isinstance(b, str) or a is None or b is None:
        return True
    return abs(float(a) - float(b)) > 0.05


def header(ws, cols, widths):
    for i, (name, w) in enumerate(zip(cols, widths), start=1):
        cell = ws.cell(row=1, column=i, value=name)
        cell.font, cell.fill, cell.alignment = HEAD, HEAD_FILL, WRAP
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 60
    ws.freeze_panes = "D2"


def case_sheet(wb, src, title, cases, unit):
    ws = wb.create_sheet(title)
    cols = ["Case", "Guidance type (owner)", "Guidance (owner)", "Metric scored", "Direction", "Promise", "Actual",
            "Position", "Tag (beat / in line / miss)",
            LABELS["v4"], LABELS["range"], LABELS["range_a1"], LABELS["range_p"], LABELS["diffusion"], LABELS["bias"],
            "Sheet: diffusion", "Sheet: R2+A1", "Sheet: Range-P", "Sheet: v4",
            "Sheet columns that differ", "Note", "Your preference"]
    header(ws, cols, [6, 24, 18, 22, 10, 14, 8, 20, 12, 11, 13, 13, 11, 11, 13, 10, 10, 10, 10, 26, 48, 16])
    out_rows = 0
    for r in src.iter_rows(min_row=3, values_only=True):
        if r[0] is None:
            continue
        case, actual = int(r[0]), float(str(r[4]).replace("%", "").replace("$M", ""))
        metric, lo, hi, bound, note = cases[case]
        s = {c["id"]: score(c["id"], metric, lo, hi, actual, bound) for c in COMPARISONS}
        sheet = {"diffusion": r[6], "range_a1": r[7], "range_p": r[8], "v4": r[9]}
        wrong = [k for k in ("diffusion", "range_a1", "range_p", "v4") if differs(sheet[k], s[k])]
        pos = position(lo, hi, actual, bound)
        tag = g.lab_tag(metric, lo, hi, actual, bound).replace("_", " ")
        flags = list(note and [note] or [])
        if tag == "in line" and sheet["diffusion"] in (0, 100):
            flags.append("Delivered inside the promise; diffusion scores it as the largest possible "
                         + ("beat." if sheet["diffusion"] == 100 else "miss."))
        if r[10] and "BEAT" in str(r[10]) and tag == "miss":
            flags.append("Sheet tags this BEAT; it is a miss for this metric.")
        if r[10] and "MISS" in str(r[10]) and tag != "miss":
            flags.append(f"Sheet tags this MISS; it is {tag}.")
        u = "x" if metric.endswith("_x") else unit
        row = [case, r[1], r[2], metric, metric_catalog.metric_direction(metric), f"{promise(lo, hi, bound)} {u}",
               actual, pos, tag, s["v4"], s["range"], s["range_a1"], s["range_p"], s["diffusion"], s["bias"],
               sheet["diffusion"], sheet["range_a1"], sheet["range_p"], sheet["v4"],
               ", ".join(wrong) if wrong else "none", " ".join(flags), None]
        ws.append(row)
        n = ws.max_row
        for col in range(16, 20):
            ws.cell(row=n, column=col).fill = SHEET_FILL
        for k, col in (("diffusion", 16), ("range_a1", 17), ("range_p", 18), ("v4", 19)):
            if k in wrong:
                ws.cell(row=n, column=col).fill = WRONG_FILL
        if len(flags) > (1 if note else 0):
            ws.cell(row=n, column=21).fill = FLAG_FILL
        for col in range(1, len(cols) + 1):
            ws.cell(row=n, column=col).alignment = WRAP
        out_rows += 1
    dv = DataValidation(type="list", formula1='"' + ",".join(PREFERENCE_CHOICES) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"V2:V{ws.max_row}")
    return out_rows


EXTRA = [
    ("Result on the top of the range", "revenue_growth_cc_pct", 6, 10, None, 10.0),
    ("Result on the bottom of the range", "revenue_growth_cc_pct", 6, 10, None, 6.0),
    ("Infosys FY26 revenue growth (cc): opening guidance and reported", "revenue_growth_cc_pct", 0, 3, None, 3.1),
    ("Same miss, narrow range", "revenue_growth_cc_pct", 4, 6, None, 11.0),
    ("Same miss, wide range", "revenue_growth_cc_pct", 0, 10, None, 11.0),
    ("1 pp miss on a 2% point guide", "revenue_growth_cc_pct", 2, 2, None, 1.0),
    ("1 pp miss on a 20% point guide", "revenue_growth_cc_pct", 20, 20, None, 19.0),
    ("Working-capital days above guidance (cost)", "wc_days", 40, 50, None, 55.0),
    ("Working-capital days below guidance (cost)", "wc_days", 40, 50, None, 35.0),
    ("Cipla FY25 R&D spend (two-sided): opening guidance and reported", "rd_spend_pct_of_revenue", 5, 6, None, 5.0),
    ("R&D spend above its range (two-sided)", "rd_spend_pct_of_revenue", 5, 6, None, 6.5),
]


def extra_sheet(wb):
    ws = wb.create_sheet("Cases to add")
    cols = ["Case", "Metric", "Direction", "Promise", "Actual", "Position", "Tag",
            *(LABELS[c["id"]] for c in COMPARISONS), "What it tests"]
    header(ws, cols, [44, 24, 10, 12, 8, 20, 12, 11, 13, 13, 11, 11, 13, 50])
    tests = [
        "Exact bound: inside the promise. Diffusion reads it as a beat.",
        "Exact bound: inside the promise. Diffusion reads it as a miss.",
        "Low-growth overshoot of 0.1 pp. Real row from the packaged dataset.",
        "Width: the same 11% result against a 2-point range.",
        "Width: the same 11% result against a 10-point range. A proper score should not reward the wider range.",
        "Scale: a 1 pp miss at low growth.",
        "Scale: a 1 pp miss at high growth. Should a 1 pp miss cost the same at 2% and 20%?",
        "Direction: above a cost guide is a miss.",
        "Direction: below a cost guide is a beat.",
        "Two-sided: inside the range. Real row from the packaged dataset.",
        "Two-sided: outside the range is neither a beat nor a miss.",
    ]
    for (label, metric, lo, hi, bound, actual), test in zip(EXTRA, tests):
        ws.append([label, metric, metric_catalog.metric_direction(metric), promise(lo, hi, bound), actual,
                   position(lo, hi, actual, bound), g.lab_tag(metric, lo, hi, actual, bound).replace("_", " "),
                   *(score(c["id"], metric, lo, hi, actual, bound) for c in COMPARISONS), test])
        for col in range(1, len(cols) + 1):
            ws.cell(row=ws.max_row, column=col).alignment = WRAP
    ws.append([])
    ws.append(["Hypothetical figures except the two rows marked as real. Typed-in rows, as the method lab's "
               "hypothetical rows; not data for any company."])


PROPERTIES = [
    ("gain_from_guiding_low", "Points gained by setting the range below the company's own expectation (0 is right)"),
    ("best_half_width_pp", "Range half-width that maximises the expected score, pp (honest 80% range: 1.92)"),
    ("width_ignored", "Score does not depend on range width"),
    ("one_pp_miss_at_2", "Row score for a 1 pp miss on 2% growth"),
    ("one_pp_miss_at_20", "Row score for a 1 pp miss on 20% growth"),
    ("steady_record", "Level for a record that lands on guidance every year"),
    ("alternating_record", "Level for a record that misses and beats by the same amount in alternate years"),
    ("low_growth_beat", "Row score for a small overshoot of low-growth guidance"),
]


def properties_sheet(wb):
    ws = wb.create_sheet("Method properties")
    cols = ["Property", *(LABELS[c["id"]] for c in COMPARISONS)]
    header(ws, cols, [60, 13, 15, 15, 13, 13, 15])
    beh = {c["id"]: g.lab_behaviour(c) for c in COMPARISONS}
    for key, label in PROPERTIES:
        ws.append([label, *(beh[c["id"]].get(key) for c in COMPARISONS)])
        for col in range(1, len(cols) + 1):
            ws.cell(row=ws.max_row, column=col).alignment = WRAP
    ws.append([])
    ws.append(["Checks from the 12 Nov algorithm scan, recomputed by gci_scoring.lab_behaviour: a growth figure "
               "whose true expectation is 5% with a 1.5 pp spread. These are the properties a single-row case "
               "table cannot show."])


def rollup_sheet(wb):
    ws = wb.create_sheet("Roll-up Infosys, Cipla")
    cols = ["Company", "Period", "Metric", "Opening guidance", "Reported", "Tag",
            *(LABELS[c["id"]] for c in COMPARISONS)]
    header(ws, cols, [10, 8, 26, 14, 9, 12, 11, 13, 13, 11, 11, 13])
    companies = _scored_companies()
    for cid in ("infy", "cipla"):
        kw = core_inputs(cid, companies[cid])
        run = g.lab_run(kw["outcomes"], COMPARISONS, row_scope="all_closed", audit_flags=kw["audit_flags"])
        for r in run["rows"]:
            ws.append([cid, r["period"], r["metric"], promise(r["low"], r["high"], r["bound"]), r["actual"],
                       r["tag"].replace("_", " "), *(r["scores"][c["id"]] for c in COMPARISONS)])
        lv = run["levels"]
        ws.append([cid, "Level", "lab roll-up, each method's own defaults", None, None, None,
                   *(lv[c["id"]]["level"] for c in COMPARISONS)])
        for col in range(1, len(cols) + 1):
            ws.cell(row=ws.max_row, column=col).font = Font(bold=True)
        ws.append([])
    ws.append(["All closed rows (shadow scope, as the Core engine reads them); not a published set. "
               "The diffusion level is a simple mean: a beat offsets a miss, so the more erratic record can "
               "sit above the steadier one."])


def readme(wb, counts):
    ws = wb.active
    ws.title = "Read me"
    ws.column_dimensions["A"].width = 120
    lines = [
        "GCI 40-case evaluation, corrected copy · 13 Nov 2026 · research only, nothing published",
        "",
        "Source: GCI_v2.5_vs_Tech_Team_40_Case_Evaluation.xlsx (owner, 12 Nov). The original values are kept "
        "in the grey 'Sheet:' columns; red cells are values the named rule does not produce.",
        f"Rows checked: {counts} (20 cases × upside and downside × 2 sheets).",
        "",
        "What was corrected",
        "• 'Tech R2+A1' was R2 with A1 but without A2. The tech proposal is R2 with A1–A5; A2 scores a met "
        "floor or ceiling 100. Both are shown.",
        "• 'Range-P' scored floors and ceilings as point targets, and scored $M in raw dollars. The spec "
        "measures amounts as a per cent of the guided midpoint.",
        "• 'Legacy v4' did not reproduce the published scorer: v4 scores a result inside the range 100 and "
        "floors beats at 60.",
        "• 'Diffusion' matched the owner formula except at a zero midpoint, where it is undefined and the "
        "sheet's values differed between sheets for identical numbers.",
        "• Added: the promise, the position of the result, a beat / in line / miss tag set by the metric's "
        "direction, and Guidance Bias (diffusion with direction and a 5 pp growth floor).",
        "• Added sheets: 'Cases to add' (exact bounds, width, scale, cost and two-sided metrics), 'Method "
        "properties' (guiding low, width, alternating records) and 'Roll-up Infosys, Cipla' (real rows).",
        "• 'Your preference' is cleared: the three earlier choices were made against incorrect v4 and Range-P "
        "values.",
        "",
        "Methods (backend/app/services/gci_scoring.py, method lab defaults)",
        *(f"• {LABELS[c['id']]}: {g.lab_method(c['method'])['formula']}" for c in COMPARISONS
          if c["id"] not in ("range_a1", "bias")),
        "• R2 with A1 only: as GCI Range with met_bound_full off (a beaten floor or ceiling is charged).",
        "• Guidance Bias: diffusion preset 'guidance_bias' (5 pp growth floor, metric direction).",
        "",
        "Metrics",
        "• % sheet: revenue growth (cc) unless the case names a margin; amounts: revenue (US$ m).",
        "• Research metrics added in the script only, not in the catalog: opex_growth_pct and opex_usd_mn "
        "(ceiling cases 7 and 8), net_debt_to_ebitda_x (amounts case 20), roce_wacc_spread_pct (% case 20). "
        "Opex and leverage are lower-is-better.",
        "• Range-P on amounts uses the scan's illustrative constants (12.5 points per 1% of midpoint, width "
        "charge 0.1). They are calibrated for revenue growth, not amounts, so a wide $M range that contains "
        "the result can still score 0. Calibration is CAL-R2-01 / decision D-D.",
        "",
        "Regenerate: PYTHONPATH=backend python3 docs/review/assets/gci_algorithm/repro/case_workbook.py",
        "Review note: docs/review/GCI_40_Case_Workbook_Review_13_Nov_2026.md",
    ]
    for line in lines:
        ws.append([line])
        ws.cell(row=ws.max_row, column=1).alignment = Alignment(wrap_text=True, vertical="top")
    ws["A1"].font = Font(bold=True, size=13)
    for r in range(1, ws.max_row + 1):
        if ws.cell(row=r, column=1).value in ("What was corrected", "Methods (backend/app/services/gci_scoring.py, "
                                              "method lab defaults)", "Metrics"):
            ws.cell(row=r, column=1).font = Font(bold=True)


def main():
    src = openpyxl.load_workbook(os.environ.get("CASE_WORKBOOK", SOURCE))
    wb = openpyxl.Workbook()
    n = case_sheet(wb, src["Percentage Point Cases (%)"], "Percentage points", PCT_CASES, "%")
    n += case_sheet(wb, src["Absolute Amount Cases ($M)"], "Amounts", AMT_CASES, "US$ m")
    extra_sheet(wb)
    properties_sheet(wb)
    rollup_sheet(wb)
    readme(wb, n)
    wb.save(OUT)
    print(OUT, n, "rows")


if __name__ == "__main__":
    main()
