# utils/pdf_generator.py — The 529 Network
# Polished, neutral, family-facing PDF summary.
import io, os
from datetime import date

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                    HRFlowable, KeepTogether, Image)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
    GREEN = colors.HexColor("#3A8916")
    DARK_GREEN = colors.HexColor("#2B650B")
    ACCENT = colors.HexColor("#C6DDBB")
    GRAY = colors.HexColor("#708686")
    LIGHT = colors.HexColor("#F5F7F5")
    CALLOUT_BG = colors.HexColor("#F2F9ED")
    DARK = colors.HexColor("#1A1A1A")
except ImportError:
    REPORTLAB_AVAILABLE = False
    GREEN = DARK_GREEN = ACCENT = GRAY = LIGHT = CALLOUT_BG = DARK = None

from utils.translations import t

# ── projection helpers (self-contained so PDF is consistent for email + download) ──
def _midpoint(savings_str):
    from utils.scoring import SAVINGS_MIDPOINTS
    return SAVINGS_MIDPOINTS.get(savings_str, 3000)

def _horizon(age_str):
    from utils.scoring import AGE_TO_HORIZON
    return AGE_TO_HORIZON.get(age_str, 10)

def _instate_annual(state):
    """Per-state annual cost of attendance from shared CSV, with fallback."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "college_costs.csv")
    fallback = {
        "AL":26800,"AK":27800,"AZ":27200,"AR":23600,"CA":36000,"CO":30600,"CT":36800,
        "DC":45000,"DE":30400,"FL":21800,"GA":26200,"HI":29600,"ID":23200,"IL":31400,
        "IN":27800,"IA":25400,"KS":24800,"KY":25200,"LA":23800,"ME":30200,"MD":32400,
        "MA":38600,"MI":29400,"MN":28600,"MS":21400,"MO":26200,"MT":25600,"NE":24600,
        "NV":22800,"NH":34600,"NJ":35200,"NM":21600,"NY":32400,"NC":24400,"ND":23800,
        "OH":28400,"OK":22800,"OR":30800,"PA":34200,"RI":36400,"SC":27000,"SD":24400,
        "TN":25600,"TX":26400,"UT":21800,"VT":40600,"VA":30200,"WA":27400,"WV":22400,
        "WI":27600,"WY":16400,
    }
    try:
        import csv
        with open(os.path.normpath(path), newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("State") or "").strip().upper() == state:
                    return float(row["cost_dollars"])
    except Exception:
        pass
    return fallback.get(state, 26000)

def _project(monthly, years, rate=0.06):
    mr = rate / 12; bal = 0.0
    for _ in range(years * 12):
        bal = bal * (1 + mr) + monthly
    return int(bal)

def _infl(base, years, r=0.04):
    return int(base * (1 + r) ** years)

def _projection_summary(user_answers):
    """Compute a default in-state-public projection + one-third-rule target."""
    state = user_answers.get("state", "")
    years = _horizon(user_answers.get("age", ""))
    annual = _midpoint(user_answers.get("annual_savings", ""))
    monthly = max(int(annual / 12), 25)
    base_4yr = int(_instate_annual(state) * 4)
    future_cost = _infl(base_4yr, years) if years > 0 else base_4yr
    projected = _project(monthly, years) if years > 0 else 0
    one_third_target = int(future_cost / 3)
    return {
        "years": years, "monthly": monthly, "future_cost": future_cost,
        "projected": projected, "one_third_target": one_third_target,
        "covered_pct": min(100, (projected / future_cost * 100)) if future_cost else 0,
        "third_pct": min(100, (projected / one_third_target * 100)) if one_third_target else 0,
    }


def generate_pdf(user_answers, top_plans, lang="en"):
    if not REPORTLAB_AVAILABLE:
        return _fallback(user_answers, top_plans, lang)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
        rightMargin=0.7*inch, leftMargin=0.7*inch,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        title="529 Plan Finder Results", author="The 529 Network")
    styles = getSampleStyleSheet()
    S = lambda name, **kw: ParagraphStyle(name, parent=styles["Normal"], **kw)
    title_s   = S("T", fontSize=21, textColor=DARK_GREEN, spaceAfter=2, fontName="Helvetica-Bold", leading=24)
    sub_s     = S("S", fontSize=10, textColor=GRAY, spaceAfter=2, fontName="Helvetica")
    h2_s      = S("H2", fontSize=13, textColor=GREEN, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold")
    plan_s    = S("P", fontSize=12, textColor=DARK_GREEN, spaceBefore=6, spaceAfter=2, fontName="Helvetica-Bold")
    body_s    = S("B", fontSize=10, textColor=DARK, spaceAfter=4, fontName="Helvetica", leading=14)
    callout_s = S("C", fontSize=9.5, textColor=DARK, spaceAfter=3, fontName="Helvetica", leading=13)
    callout_h = S("CH", fontSize=10, textColor=DARK_GREEN, spaceAfter=2, fontName="Helvetica-Bold")
    small_s   = S("Sm", fontSize=8, textColor=GRAY, spaceAfter=2, fontName="Helvetica", leading=11)
    foot_s    = S("F", fontSize=7.5, textColor=GRAY, spaceAfter=0, fontName="Helvetica", alignment=TA_CENTER, leading=10)
    big_num_s = S("BN", fontSize=17, textColor=DARK_GREEN, fontName="Helvetica-Bold", alignment=TA_CENTER, leading=20, spaceAfter=2)
    num_lbl_s = S("NL", fontSize=8, textColor=GRAY, fontName="Helvetica", alignment=TA_CENTER, leading=10)
    story = []

    # ── Branded header (logo if available) ───────────────────────────────────
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.jpg")
    header_cells = []
    if os.path.exists(os.path.normpath(logo_path)):
        try:
            img = Image(os.path.normpath(logo_path), width=2.3*inch, height=0.55*inch)
            img.hAlign = "LEFT"
            header_cells.append(img)
        except Exception:
            header_cells.append(Paragraph("The 529 Network", title_s))
    else:
        header_cells.append(Paragraph("The 529 Network", title_s))
    story.append(header_cells[0])
    story.append(Spacer(1, 8))
    story.append(Paragraph(t(lang, "pdf_title"), title_s))
    story.append(Paragraph(t(lang, "pdf_subtitle"), sub_s))
    story.append(Paragraph(f"{t(lang,'pdf_date_label')}: {date.today().strftime('%B %d, %Y')}", small_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN, spaceBefore=6, spaceAfter=10))

    # ── Savings snapshot (the one-third rule reframe) ────────────────────────
    proj = _projection_summary(user_answers)
    if proj["years"] > 0:
        story.append(Paragraph(t(lang, "pdf_snapshot_heading"), h2_s))
        # three big numbers: projected | smart target (1/3) | est. 4yr cost
        snap = Table([[
            Paragraph(f"${proj['projected']:,}", big_num_s),
            Paragraph(f"${proj['one_third_target']:,}", big_num_s),
            Paragraph(f"${proj['future_cost']:,}", big_num_s),
        ], [
            Paragraph(t(lang, "pdf_snap_projected"), num_lbl_s),
            Paragraph(t(lang, "pdf_snap_target"), num_lbl_s),
            Paragraph(t(lang, "pdf_snap_cost"), num_lbl_s),
        ]], colWidths=[2.25*inch, 2.25*inch, 2.25*inch])
        snap.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),CALLOUT_BG),
            ("BOX",(0,0),(-1,-1),1,ACCENT),
            ("INNERGRID",(0,0),(-1,0),0.5,colors.white),
            ("TOPPADDING",(0,0),(-1,0),12),("BOTTOMPADDING",(0,0),(-1,0),6),
            ("TOPPADDING",(0,1),(-1,1),0),("BOTTOMPADDING",(0,1),(-1,1),12),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        story.append(snap)
        story.append(Spacer(1, 4))
        # The reframe message
        if proj["projected"] >= proj["one_third_target"]:
            msg = t(lang, "pdf_third_ontrack", target=proj["one_third_target"])
        else:
            gap_third = proj["one_third_target"] - proj["projected"]
            msg = t(lang, "pdf_third_gap", target=proj["one_third_target"], gap=gap_third)
        story.append(Paragraph(msg, body_s))
        story.append(Paragraph(t(lang, "pdf_third_explain"), small_s))

    # ── Your answers (compact) ───────────────────────────────────────────────
    story.append(Paragraph(t(lang, "pdf_answers_heading"), h2_s))
    label_map = [("ans_state","state"),("ans_relationship","relationship"),("ans_age","age"),
                 ("ans_income","income"),("ans_annual_savings","annual_savings"),
                 ("ans_priority_1","priority_1"),("ans_priority_2","priority_2"),
                 ("ans_k12","k12"),("ans_prepaid","prepaid_interest"),("ans_existing","existing")]
    rows = [[Paragraph(t(lang,lk), small_s), Paragraph(str(user_answers.get(ak,"\u2014")), body_s)]
            for lk,ak in label_map if user_answers.get(ak)]
    if rows:
        tbl = Table(rows, colWidths=[2.2*inch, 4.5*inch])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,-1),LIGHT),("TEXTCOLOR",(0,0),(0,-1),GRAY),
            ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#E0E8E0")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),("LEFTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(tbl)

    # ── Plans (neutral) ──────────────────────────────────────────────────────
    story.append(Paragraph(t(lang,"pdf_plans_heading"), h2_s))
    story.append(Paragraph(t(lang,"pdf_neutral_note"), small_s))
    story.append(Spacer(1,6))
    for i, plan in enumerate(top_plans[:4]):
        blk = []
        rating = plan.get("morningstar_rating","")
        rating_str = rating if rating in ("Gold","Silver","Bronze") else ""
        label = ""
        if plan.get("_is_home"):
            label = "  (Your Home State Plan)" if lang=="en" else "  (Plan de tu Estado)"
        name_line = f"{plan['name']}{label}"
        if rating_str:
            name_line += f"  \u2014 {rating_str}"
        blk.append(Paragraph(name_line, plan_s))
        er = plan.get("avg_expense_ratio",0)
        er_str = f"{er*100:.2f}%" if er > 0 else "0%"
        min_c = plan.get("min_contribution",0)
        min_str = t(lang,"no_minimum") if min_c == 0 else f"${min_c:,}"
        ts = plan.get("estimated_annual_tax_savings",0)
        ts_str = f"${ts:,.0f}/year" if ts > 0 else t(lang,"not_available")
        stat_rows = [[
            Paragraph(f"{t(lang,'expense_ratio_label')}: <b>{er_str}</b>", small_s),
            Paragraph(f"{t(lang,'min_contrib_label')}: <b>{min_str}</b>", small_s),
            Paragraph(f"{t(lang,'state_deduction_label')}: <b>{ts_str}</b>", small_s),
        ]]
        st = Table(stat_rows, colWidths=[2.25*inch, 2.25*inch, 2.25*inch])
        st.setStyle(TableStyle([
            ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(-1,-1),0),
        ]))
        blk.append(st)
        blk.append(Paragraph(f'<font color="#3A8916">{plan.get("enroll_url","")}</font>', small_s))
        blk.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT, spaceBefore=4, spaceAfter=6))
        story.append(KeepTogether(blk))

    # ── Smart ways to save more (educational, neutral, plan-agnostic) ────────
    story.append(Paragraph(t(lang,"pdf_tips_heading"), h2_s))
    tips = [
        ("pdf_tip_third_h", "pdf_tip_third_b"),
        ("pdf_tip_roth_h", "pdf_tip_roth_b"),
        ("pdf_tip_super_h", "pdf_tip_super_b"),
        ("pdf_tip_loan_h", "pdf_tip_loan_b"),
    ]
    tip_cells = []
    for h, b in tips:
        cell = [Paragraph(t(lang, h), callout_h), Paragraph(t(lang, b), callout_s)]
        tip_cells.append(cell)
    # 2x2 grid of callouts
    grid = Table([
        [tip_cells[0], tip_cells[1]],
        [tip_cells[2], tip_cells[3]],
    ], colWidths=[3.35*inch, 3.35*inch])
    grid.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),CALLOUT_BG),
        ("BOX",(0,0),(-1,-1),0.5,ACCENT),
        ("INNERGRID",(0,0),(-1,-1),0.5,colors.white),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
    ]))
    story.append(grid)

    # ── Next steps ───────────────────────────────────────────────────────────
    story.append(Paragraph(t(lang,"pdf_next_steps_heading"), h2_s))
    for i, step in enumerate(t(lang,"pdf_next_steps"), 1):
        story.append(Paragraph(f"{i}. {step}", body_s))

    # ── Footer: neutrality + provenance ──────────────────────────────────────
    story.append(Spacer(1,14))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6))
    story.append(Paragraph(t(lang,"pdf_neutral_footer"), foot_s))
    story.append(Spacer(1,3))
    story.append(Paragraph(t(lang,"pdf_footer"), foot_s))
    doc.build(story)
    buf.seek(0)
    return buf.read()


def _fallback(user_answers, top_plans, lang):
    lines = ["The 529 Network — 529 Plan Finder Results",
             f"Generated: {date.today().isoformat()}", ""]
    proj = _projection_summary(user_answers)
    if proj["years"] > 0:
        lines += [f"Projected balance: ${proj['projected']:,}",
                  f"Smart target (1/3 of cost): ${proj['one_third_target']:,}",
                  f"Est. 4-year cost: ${proj['future_cost']:,}", ""]
    for p in top_plans[:4]:
        home = " (Your Home State Plan)" if p.get("_is_home") else ""
        lines += [f"{p['name']}{home}",
                  f"  Fees: {p.get('avg_expense_ratio',0)*100:.2f}%",
                  f"  Rating: {p.get('morningstar_rating','N/A')}",
                  f"  Visit: {p.get('enroll_url','')}",""]
    lines.append(t(lang,"pdf_footer"))
    return "\n".join(lines).encode("utf-8")
