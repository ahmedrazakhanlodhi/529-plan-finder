# utils/pdf_generator.py — The 529 Network
import io
from datetime import date

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
    GREEN = colors.HexColor("#3A8916")
    DARK_GREEN = colors.HexColor("#2B650B")
    ACCENT = colors.HexColor("#C6DDBB")
    GRAY = colors.HexColor("#708686")
    LIGHT = colors.HexColor("#F5F7F5")
    DARK = colors.HexColor("#1A1A1A")
except ImportError:
    REPORTLAB_AVAILABLE = False
    GREEN = DARK_GREEN = ACCENT = GRAY = LIGHT = DARK = None

from utils.translations import t

def generate_pdf(user_answers, top_plans, lang="en"):
    if not REPORTLAB_AVAILABLE:
        return _fallback(user_answers, top_plans, lang)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    S = lambda name, **kw: ParagraphStyle(name, parent=styles["Normal"], **kw)
    title_s = S("T", fontSize=20, textColor=DARK_GREEN, spaceAfter=4, fontName="Helvetica-Bold")
    sub_s = S("S", fontSize=10, textColor=GRAY, spaceAfter=2, fontName="Helvetica")
    h2_s = S("H2", fontSize=13, textColor=GREEN, spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold")
    plan_s = S("P", fontSize=12, textColor=DARK_GREEN, spaceBefore=8, spaceAfter=2, fontName="Helvetica-Bold")
    body_s = S("B", fontSize=10, textColor=DARK, spaceAfter=4, fontName="Helvetica", leading=14)
    small_s = S("Sm", fontSize=8, textColor=GRAY, spaceAfter=2, fontName="Helvetica")
    foot_s = S("F", fontSize=8, textColor=GRAY, spaceAfter=0, fontName="Helvetica", alignment=TA_CENTER)
    story = []
    story.append(Paragraph("The 529 Network", sub_s))
    story.append(Paragraph(t(lang,"pdf_title"), title_s))
    story.append(Paragraph(t(lang,"pdf_subtitle"), sub_s))
    story.append(Paragraph(f"{t(lang,'pdf_date_label')}: {date.today().strftime('%B %d, %Y')}", small_s))
    story.append(HRFlowable(width="100%", thickness=2, color=GREEN, spaceAfter=12))
    story.append(Paragraph(t(lang,"pdf_answers_heading"), h2_s))
    label_map = [("ans_state","state"),("ans_relationship","relationship"),("ans_age","age"),
                 ("ans_income","income"),("ans_annual_savings","annual_savings"),
                 ("ans_priority_1","priority_1"),("ans_priority_2","priority_2"),
                 ("ans_k12","k12"),("ans_prepaid","prepaid_interest"),("ans_existing","existing")]
    rows = [[Paragraph(t(lang,lk), body_s), Paragraph(str(user_answers.get(ak,"—")), body_s)]
            for lk,ak in label_map if user_answers.get(ak)]
    if rows:
        tbl = Table(rows, colWidths=[2.2*inch, 4.5*inch])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,-1),LIGHT),("TEXTCOLOR",(0,0),(0,-1),GRAY),
            ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),10),
            ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#E0E8E0")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(tbl)
    story.append(Spacer(1,10))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    story.append(Paragraph(t(lang,"pdf_recommendations_heading"), h2_s))
    for i, plan in enumerate(top_plans[:3]):
        blk = []
        rating = plan.get("morningstar_rating","")
        badge = {"Gold":"Gold","Silver":"Silver","Bronze":"Bronze"}.get(rating,"")
        blk.append(Paragraph(f"#{i+1} — {plan['name']}  ({badge})", plan_s))
        score = plan.get("score",0)
        blk.append(Paragraph(f"{t(lang,'match_label')}: {score:.0f}/100", small_s))
        er = plan.get("avg_expense_ratio",0)
        er_str = f"{er*100:.2f}%" if er > 0 else "0%"
        min_c = plan.get("min_contribution",0)
        min_str = t(lang,"no_minimum") if min_c == 0 else f"${min_c:,}"
        ts = plan.get("estimated_annual_tax_savings",0)
        ts_str = f"${ts:,.0f}/year" if ts > 0 else t(lang,"not_available")
        stat_rows = [
            [Paragraph(t(lang,"expense_ratio_label"), small_s), Paragraph(er_str, body_s)],
            [Paragraph(t(lang,"min_contrib_label"), small_s), Paragraph(min_str, body_s)],
            [Paragraph(t(lang,"state_deduction_label"), small_s), Paragraph(ts_str, body_s)],
            [Paragraph("URL", small_s), Paragraph(plan.get("enroll_url",""), body_s)],
        ]
        st = Table(stat_rows, colWidths=[1.8*inch, 4.9*inch])
        st.setStyle(TableStyle([
            ("TEXTCOLOR",(0,0),(0,-1),GRAY),("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),("LEFTPADDING",(0,0),(-1,-1),0),
        ]))
        blk.append(st)
        expl = plan.get("explanation", plan.get("highlight",""))
        if expl:
            blk.append(Spacer(1,4))
            blk.append(Paragraph(expl, body_s))
        blk.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT, spaceAfter=6))
        story.append(KeepTogether(blk))
        story.append(Spacer(1,4))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    story.append(Paragraph(t(lang,"pdf_next_steps_heading"), h2_s))
    for i, step in enumerate(t(lang,"pdf_next_steps"), 1):
        story.append(Paragraph(f"{i}. {step}", body_s))
    story.append(Spacer(1,16))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))
    story.append(Paragraph(t(lang,"pdf_footer"), foot_s))
    doc.build(story)
    buf.seek(0)
    return buf.read()

def _fallback(user_answers, top_plans, lang):
    lines = ["The 529 Network — 529 Plan Finder Results", f"Generated: {date.today().isoformat()}", ""]
    for i, p in enumerate(top_plans[:3], 1):
        lines += [f"#{i} {p['name']}", f"  Score: {p.get('score',0):.0f}/100",
                  f"  Fees: {p.get('avg_expense_ratio',0)*100:.2f}%",
                  f"  Rating: {p.get('morningstar_rating','N/A')}",
                  f"  Enroll: {p.get('enroll_url','')}",""]
    lines.append(t(lang,"pdf_footer"))
    return "\n".join(lines).encode("utf-8")
