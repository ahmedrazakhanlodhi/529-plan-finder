# app.py — 529 Plan Finder — The 529 Network
# Data compiled by The 529 Network. Not financial advice.

import re
import streamlit as st
from utils.knowledge_base import STATE_TAX_DATA, STATE_PLAN_IDS, PREPAID_PLAN_IDS, PLAN_BY_ID
from utils.translations import t, STRINGS
from utils.scoring import score_plans, get_context_tips, generate_explanation

st.set_page_config(
    page_title="529 Plan Finder | The 529 Network",
    page_icon="\U0001F393",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding-top:1.5rem;padding-bottom:2rem;max-width:760px;}
.stProgress>div>div>div>div{background-color:#3A8916;}
.stButton>button{background:#3A8916;color:white;border:none;border-radius:6px;font-weight:600;padding:.55rem 1.4rem;transition:background .15s;}
.stButton>button:hover{background:#2B650B;}
.back-btn button{background:transparent!important;color:#708686!important;border:1px solid #C6DDBB!important;}
.plan-card{border-left:5px solid #3A8916;background:#f8fbf6;border-radius:0 10px 10px 0;padding:1.2rem 1.4rem;margin-bottom:1.2rem;}
.plan-card.rank-1{border-left-color:#2B650B;background:#f2f9ed;}
.plan-card.rank-3{border-left-color:#708686;background:#f5f7f7;}
.home-plan-card{border:2px solid #3A8916;background:#f2f9ed;border-radius:12px;padding:1.4rem 1.6rem;margin-bottom:1rem;}
.home-plan-banner{display:inline-block;background:#2B650B;color:white;font-size:.72rem;font-weight:700;letter-spacing:.04em;padding:3px 12px;border-radius:20px;margin-bottom:10px;text-transform:uppercase;}
.neutral-plan-card{border:1px solid #d8e3d2;background:#ffffff;border-radius:10px;padding:1.1rem 1.3rem;margin-bottom:.9rem;}
.neutral-plan-card:hover{border-color:#C6DDBB;box-shadow:0 2px 8px rgba(58,137,22,0.06);}
.tax-callout{background:#d4edda;border-radius:6px;padding:.5rem .8rem;font-size:.88rem;color:#2B650B;font-weight:600;margin:8px 0;}
.neutrality-note{background:#f5f7f5;border:1px solid #e0e8e0;border-radius:8px;padding:.8rem 1rem;font-size:.8rem;color:#708686;margin-bottom:1rem;line-height:1.5;}
.fact-grid{display:flex;gap:24px;flex-wrap:wrap;font-size:.85rem;margin:10px 0;}
.fact-grid .lbl{color:#708686;display:block;font-size:.76rem;}
.fact-grid .val{color:#1A1A1A;font-weight:600;}
.match-bar-outer{background:#e0e8e0;border-radius:4px;height:8px;width:100%;margin:4px 0 10px;}
.match-bar-inner{background:linear-gradient(90deg,#3A8916,#2B650B);border-radius:4px;height:8px;}
.badge{display:inline-block;background:#C6DDBB;color:#2B650B;font-size:.72rem;font-weight:600;padding:2px 9px;border-radius:12px;margin-right:5px;margin-bottom:5px;}
.badge-gold{background:#FFF3CD;color:#856404;}
.badge-silver{background:#E9ECEF;color:#495057;}
.badge-bronze{background:#F5E6D3;color:#7B4F2E;}
.tip-success{background:#d4edda;border-left:4px solid #3A8916;border-radius:0 6px 6px 0;padding:.8rem 1rem;margin-bottom:1rem;}
.tip-warning{background:#fff3cd;border-left:4px solid #ffc107;border-radius:0 6px 6px 0;padding:.8rem 1rem;margin-bottom:1rem;}
.tip-info{background:#d1ecf1;border-left:4px solid #17a2b8;border-radius:0 6px 6px 0;padding:.8rem 1rem;margin-bottom:1rem;}
.hint-text{color:#708686;font-size:.87rem;font-style:italic;margin-top:-6px;margin-bottom:10px;}
.enroll-link a{display:inline-block;background:#3A8916;color:white!important;padding:.5rem 1.3rem;border-radius:6px;font-weight:600;font-size:.9rem;text-decoration:none!important;}
.enroll-link a:hover{background:#2B650B;}
.app-footer{font-size:.76rem;color:#708686;text-align:center;margin-top:2rem;padding-top:1rem;border-top:1px solid #e0e8e0;}
</style>
""", unsafe_allow_html=True)

TOTAL_STEPS = 10

def esc(options):
    """Escape $ in radio/selectbox labels so Streamlit doesn't render them as LaTeX."""
    if isinstance(options, list):
        return [o.replace("$", "\\$") for o in options]
    return options.replace("$", "\\$")

def init_state():
    for k,v in [("screen","welcome"),("step",1),("lang","en"),
                ("answers",{}),("results",None),("all_results",[]),
                ("email_sent",False),("email_failed",False),("show_q8_explainer",False)]:
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
lang = st.session_state.lang
answers = st.session_state.answers

def rerun(): st.rerun()
def reset():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    init_state()
    st.rerun()

def state_options():
    return [""] + [f"{v['name']} ({k})" for k,v in sorted(STATE_TAX_DATA.items(), key=lambda x: x[1]["name"])]

def parse_state(sel):
    m = re.search(r'\(([A-Z]{2})\)$', sel)
    return m.group(1) if m else ""

def valid_email(e):
    return bool(re.match(r'^[\w.%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$', e.strip()))

def logo_bar():
    import os, base64
    c1,c2 = st.columns([5,1])
    with c1:
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.jpg")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<img src="data:image/jpeg;base64,{logo_b64}" style="height:48px;object-fit:contain;">', unsafe_allow_html=True)
        else:
            st.markdown('<div><b style="color:#2B650B;font-size:1.05rem;">The 529 Network</b><br><span style="color:#708686;font-size:.75rem;">529network.org</span></div>', unsafe_allow_html=True)
    with c2:
        if st.button(t(lang,"language_toggle"), key="lang_btn"):
            st.session_state.lang = "es" if lang == "en" else "en"
            st.rerun()
    st.markdown('<div style="border-top:1px solid #C6DDBB;margin:10px 0 14px;"></div>', unsafe_allow_html=True)

def hint(text):
    st.markdown(f'<div class="hint-text">{text}</div>', unsafe_allow_html=True)

def footer():
    st.markdown(f'<div class="app-footer">{t(lang,"footer")}</div>', unsafe_allow_html=True)

def progress(step):
    st.progress(step / TOTAL_STEPS)
    st.caption(t(lang,"step_label", current=step, total=TOTAL_STEPS))

def badge_html(plan, flags):
    r = plan.get("morningstar_rating","")
    css = {"Gold":"badge badge-gold","Silver":"badge badge-silver","Bronze":"badge badge-bronze"}
    html = ""
    if r in css: html += f'<span class="{css[r]}">{t(lang,"badge_"+r.lower())}</span> '
    flag_map = {"your_state":"badge_your_state","prepaid":"badge_prepaid","parity":"badge_parity","grandparents":"badge_grandparents","low_min":"badge_low_min"}
    for f in flags:
        if f in flag_map: html += f'<span class="badge">{t(lang,flag_map[f])}</span> '
    return html

# ── WELCOME ──────────────────────────────────────────────────────────────────
def screen_welcome():
    logo_bar()
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#f2f9ed,#e8f4e0);border-radius:12px;padding:2rem;margin-bottom:1.5rem;border:1px solid #C6DDBB;">
      <h1 style="color:#2B650B;font-size:1.8rem;margin-bottom:.5rem;">{t(lang,"welcome_heading")}</h1>
      <p style="color:#444;line-height:1.65;">{t(lang,"welcome_intro")}</p>
      <p style="color:#708686;font-size:.85rem;margin-top:.75rem;">⏱ {t(lang,"welcome_time")}</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button(t(lang,"welcome_cta"), key="start"):
        st.session_state.screen = "questionnaire"
        st.session_state.step = 1
        st.rerun()
    footer()

# ── QUESTIONNAIRE ─────────────────────────────────────────────────────────────
def screen_questionnaire():
    logo_bar()
    step = st.session_state.step
    progress(step)
    st.markdown("---")
    if step > 1:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button(t(lang,"back_button"), key="back"):
            st.session_state.step = max(1, step - 1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if step == 1:
        st.subheader(t(lang,"q1_label"))
        hint(t(lang,"q1_hint"))
        opts = state_options()
        cur = answers.get("state_display","")
        idx = opts.index(cur) if cur in opts else 0
        sel = st.selectbox(t(lang,"q1_label"), opts, index=idx, label_visibility="collapsed", key="q1")
        if st.button(t(lang,"next_button"), key="q1n"):
            if not sel:
                st.error("Please select your state." if lang=="en" else "Por favor selecciona tu estado.")
                return
            answers["state_display"] = sel
            answers["state"] = parse_state(sel)
            st.session_state.step += 1; st.rerun()

    elif step == 2:
        st.subheader(t(lang,"q2_label")); hint(t(lang,"q2_hint"))
        opts = t(lang,"q2_options")
        cur = answers.get("relationship", opts[0])
        sel = st.radio(t(lang,"q2_label"), opts, index=opts.index(cur) if cur in opts else 0, label_visibility="collapsed", key="q2")
        if st.button(t(lang,"next_button"), key="q2n"):
            answers["relationship"] = sel; st.session_state.step += 1; st.rerun()

    elif step == 3:
        st.subheader(t(lang,"q3_label")); hint(t(lang,"q3_hint"))
        opts = t(lang,"q3_options")
        cur = answers.get("age", opts[1])
        sel = st.radio(t(lang,"q3_label"), opts, index=opts.index(cur) if cur in opts else 1, label_visibility="collapsed", key="q3")
        if st.button(t(lang,"next_button"), key="q3n"):
            answers["age"] = sel; st.session_state.step += 1; st.rerun()

    elif step == 4:
        st.subheader(t(lang,"q4_label")); hint(t(lang,"q4_hint"))
        opts = t(lang,"q4_options")
        display_opts = esc(opts)
        cur = answers.get("income", opts[1])
        cur_d = cur.replace("$", "\\$")
        sel_d = st.radio(t(lang,"q4_label"), display_opts, index=display_opts.index(cur_d) if cur_d in display_opts else 1, label_visibility="collapsed", key="q4")
        if st.button(t(lang,"next_button"), key="q4n"):
            answers["income"] = sel_d.replace("\\$", "$"); st.session_state.step += 1; st.rerun()

    elif step == 5:
        st.subheader(t(lang,"q5_label")); hint(t(lang,"q5_hint"))
        opts = t(lang,"q5_options")
        display_opts = esc(opts)
        cur = answers.get("annual_savings", opts[1])
        cur_d = cur.replace("$", "\\$")
        sel_d = st.radio(t(lang,"q5_label"), display_opts, index=display_opts.index(cur_d) if cur_d in display_opts else 1, label_visibility="collapsed", key="q5")
        if st.button(t(lang,"next_button"), key="q5n"):
            answers["annual_savings"] = sel_d.replace("\\$", "$"); st.session_state.step += 1; st.rerun()

    elif step == 6:
        st.subheader(t(lang,"q6_label")); hint(t(lang,"q6_hint"))
        opts = t(lang,"q6_options")
        st.markdown(f"**{t(lang,'q6_priority_1')}**")
        cur_p1 = answers.get("priority_1", opts[0])
        p1 = st.radio(t(lang,"q6_priority_1"), opts, index=opts.index(cur_p1) if cur_p1 in opts else 0, label_visibility="collapsed", key="q6p1")
        remaining = [o for o in opts if o != p1]
        st.markdown(f"**{t(lang,'q6_priority_2')}**")
        cur_p2 = answers.get("priority_2", remaining[0])
        p2 = st.radio(t(lang,"q6_priority_2"), remaining, index=remaining.index(cur_p2) if cur_p2 in remaining else 0, label_visibility="collapsed", key="q6p2")
        if st.button(t(lang,"next_button"), key="q6n"):
            answers["priority_1"] = p1; answers["priority_2"] = p2
            st.session_state.step += 1; st.rerun()

    elif step == 7:
        st.subheader(t(lang,"q7_label")); hint(t(lang,"q7_hint"))
        opts = t(lang,"q7_options")
        cur = answers.get("k12", opts[1])
        sel = st.radio(t(lang,"q7_label"), opts, index=opts.index(cur) if cur in opts else 1, label_visibility="collapsed", key="q7")
        if st.button(t(lang,"next_button"), key="q7n"):
            answers["k12"] = sel; st.session_state.step += 1; st.rerun()

    elif step == 8:
        state = answers.get("state","")
        if not STATE_TAX_DATA.get(state,{}).get("has_prepaid_plan"):
            answers["prepaid_interest"] = "No"
            st.session_state.step += 1; st.rerun(); return
        st.subheader(t(lang,"q8_label")); hint(t(lang,"q8_hint"))
        if st.session_state.show_q8_explainer:
            st.info(t(lang,"q8_explainer"))
            st.markdown(f"**{t(lang,'q8_repeat')}**")
        opts = t(lang,"q8_options")
        display_opts = [o for o in opts if "more" not in o.lower() and "mas" not in o.lower()] if st.session_state.show_q8_explainer else opts
        cur = answers.get("prepaid_interest", display_opts[0])
        sel = st.radio(t(lang,"q8_label"), display_opts, index=display_opts.index(cur) if cur in display_opts else 0, label_visibility="collapsed", key="q8")
        if st.button(t(lang,"next_button"), key="q8n"):
            if "more" in sel.lower() or "mas" in sel.lower():
                st.session_state.show_q8_explainer = True; st.rerun()
            else:
                answers["prepaid_interest"] = sel; st.session_state.show_q8_explainer = False
                st.session_state.step += 1; st.rerun()

    elif step == 9:
        st.subheader(t(lang,"q9_label")); hint(t(lang,"q9_hint"))
        opts = t(lang,"q9_options")
        cur = answers.get("existing", opts[0])
        sel = st.radio(t(lang,"q9_label"), opts, index=opts.index(cur) if cur in opts else 0, label_visibility="collapsed", key="q9")
        if st.button(t(lang,"next_button"), key="q9n"):
            answers["existing"] = sel; st.session_state.step += 1; st.rerun()

    elif step == 10:
        st.subheader(t(lang,"q10_label")); hint(t(lang,"q10_hint"))
        email_val = answers.get("email","")
        email_in = st.text_input(t(lang,"q10_label"), value=email_val,
            placeholder=t(lang,"q10_placeholder"), label_visibility="collapsed", key="q10")
        c1,c2 = st.columns([2,2])
        with c1:
            if st.button(t(lang,"next_button"), key="q10n"):
                if email_in and not valid_email(email_in):
                    st.error(t(lang,"q10_invalid")); return
                answers["email"] = email_in.strip(); answers["lang"] = lang
                _compute_results()
        with c2:
            if st.button(t(lang,"q10_skip"), key="q10s"):
                answers["email"] = ""; answers["lang"] = lang
                _compute_results()

    footer()

def _sort_other_plans(plans, priority_1):
    """Sort the non-home plans by the OBJECTIVE factor the user prioritized.
    No composite 'match score' is used \u2014 the user sets the axis, we sort by fact."""
    from utils.scoring import PRIORITY_MAP
    dim = PRIORITY_MAP.get(priority_1, "")
    if dim == "fee":
        return sorted(plans, key=lambda p: p.get("avg_expense_ratio", 1.0)), "sorted_by_fees"
    if dim in ("investment", "rating"):
        rating_order = {"Gold": 0, "Silver": 1, "Bronze": 2, "Neutral": 3, "NR": 4}
        return (sorted(plans, key=lambda p: (rating_order.get(p.get("morningstar_rating", "NR"), 4),
                                             p.get("avg_expense_ratio", 1.0))),
                "sorted_by_rating")
    if dim == "tax":
        return sorted(plans, key=lambda p: p["name"]), "sorted_by_tax"
    return sorted(plans, key=lambda p: p["name"]), "sorted_by_default"

def _compute_results():
    from utils.knowledge_base import STATE_PLAN_IDS, PLAN_BY_ID
    answers = st.session_state.answers
    state = answers.get("state", "")
    ranked = score_plans(answers)

    # Separate the home-state plan (surfaced as disclosure, never ranked)
    home_id = STATE_PLAN_IDS.get(state)
    home_plan = next((p for p in ranked if p["id"] == home_id), None) if home_id else None

    # Curated list of other plans: exclude the home plan to avoid duplication,
    # exclude residency-locked plans, then sort by the user's chosen objective factor.
    others_pool = [p for p in ranked
                   if p["id"] != home_id
                   and not p.get("residency_required")
                   and not p.get("is_prepaid")]
    sorted_others, sort_key = _sort_other_plans(others_pool, answers.get("priority_1", ""))
    other_plans = sorted_others[:4]   # curated, not exhaustive

    st.session_state.home_plan = home_plan
    st.session_state.other_plans = other_plans
    st.session_state.other_sort_key = sort_key
    st.session_state.all_results = ranked
    # Keep a combined list for the PDF (home first, then others)
    if home_plan:
        home_plan["_is_home"] = True
    pdf_plans = ([home_plan] if home_plan else []) + other_plans

    email = answers.get("email", "")
    if email:
        try:
            from utils.pdf_generator import generate_pdf
            from utils.email_sender import send_results_email
            pdf = generate_pdf(answers, pdf_plans[:4], lang)
            ok = send_results_email(email, pdf, lang)
            st.session_state.email_sent = ok
            st.session_state.email_failed = not ok
        except:
            st.session_state.email_failed = True
    st.session_state.screen = "results"; st.rerun()

# ── RESULTS ────────────────────────────────────────────────────────────────────
# Fallback in-state annual cost of attendance (used only if data/college_costs.csv is absent)
_FALLBACK_INSTATE_ANNUAL = {
    "AL":26800,"AK":27800,"AZ":27200,"AR":23600,"CA":36000,"CO":30600,
    "CT":36800,"DC":45000,"DE":30400,"FL":21800,"GA":26200,"HI":29600,
    "ID":23200,"IL":31400,"IN":27800,"IA":25400,"KS":24800,"KY":25200,
    "LA":23800,"ME":30200,"MD":32400,"MA":38600,"MI":29400,"MN":28600,
    "MS":21400,"MO":26200,"MT":25600,"NE":24600,"NV":22800,"NH":34600,
    "NJ":35200,"NM":21600,"NY":32400,"NC":24400,"ND":23800,"OH":28400,
    "OK":22800,"OR":30800,"PA":34200,"RI":36400,"SC":27000,"SD":24400,
    "TN":25600,"TX":26400,"UT":21800,"VT":40600,"VA":30200,"WA":27400,
    "WV":22400,"WI":27600,"WY":16400,
}

@st.cache_data
def _load_instate_costs():
    """
    Load per-state average annual cost of attendance from the shared
    data/college_costs.csv (College Scorecard, the same source the 529
    Intelligence Dashboard uses). Returns (cost_map, source_label).
    Falls back to a built-in table if the file is missing or unreadable.
    """
    import os, csv
    path = os.path.join(os.path.dirname(__file__), "data", "college_costs.csv")
    try:
        costs = {}
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                st_abbr = (row.get("State") or "").strip().upper()
                val = row.get("cost_dollars")
                if st_abbr and val:
                    costs[st_abbr] = float(val)
        if len(costs) >= 45:
            return costs, "college_scorecard"
    except Exception:
        pass
    return dict(_FALLBACK_INSTATE_ANNUAL), "fallback"

def _get_college_costs(state):
    """
    4-year total cost of attendance by school type, derived from the
    shared per-state College Scorecard annual figure (one source of truth
    with the 529 Intelligence Dashboard).

    The CSV gives one blended annual cost per state, which we treat as the
    in-state public baseline. Other school types are derived from it with
    documented multipliers. Community college is a 2-year total; the rest
    are 4-year totals.
    """
    instate_annual, _src = _load_instate_costs()
    base = instate_annual.get(state, 26000)   # annual in-state COA for this state

    # Derived annual figures from the in-state baseline
    oos_annual = min(base * 1.55, 55000)       # out-of-state premium
    private_annual = base * 2.05               # private avg roughly 2x public COA
    cc_annual = max(base * 0.62, 14000)        # community college incl. living costs

    return {
        "In-state public university": int(base * 4),
        "Out-of-state public university": int(oos_annual * 4),
        "Private university": int(private_annual * 4),
        "Community college (2-year)": int(cc_annual * 2),
    }

def _cost_source_label(lang="en"):
    _costs, src = _load_instate_costs()
    if src == "college_scorecard":
        return ("Cost data: U.S. Dept. of Education College Scorecard, compiled by The 529 Network."
                if lang == "en" else
                "Datos de costos: College Scorecard del Departamento de Educación de EE.UU., compilados por The 529 Network.")
    return ("Cost data: representative College Board figures (illustrative)."
            if lang == "en" else
            "Datos de costos: cifras representativas de College Board (ilustrativo).")

def _project_balance(monthly_contribution, years, annual_return):
    """Compound monthly contribution with given annual return."""
    monthly_rate = annual_return / 12
    balance = 0
    balances = [0]
    for _ in range(years * 12):
        balance = balance * (1 + monthly_rate) + monthly_contribution
        if _ % 12 == 11:
            balances.append(round(balance, 0))
    return int(balance), list(range(years + 1)), balances

def _inflation_adjusted_cost(base_cost, years, inflation_rate=0.04):
    """Project college cost forward with tuition inflation (historically ~4%/yr)."""
    return int(base_cost * (1 + inflation_rate) ** years)

def screen_results():
    logo_bar()
    home_plan = st.session_state.get("home_plan")
    other_plans = st.session_state.get("other_plans", [])
    email = answers.get("email", "")
    state = answers.get("state", "")
    age_str = answers.get("age", "")
    savings_str = answers.get("annual_savings", "")

    if st.session_state.get("email_sent") and email:
        st.success(t(lang, "email_sent_banner", email=email))
    elif st.session_state.get("email_failed") and email:
        st.warning(t(lang, "email_error"))

    st.markdown(f"## {t(lang, 'results_heading')}")
    st.markdown(f"*{t(lang, 'neutral_subheading')}*")
    st.markdown(f'<div class="neutrality-note">{t(lang, "neutrality_disclaimer")}</div>', unsafe_allow_html=True)

    for tip in get_context_tips(answers):
        typ = tip.get("type", "info")
        if "key" in tip:
            st.markdown(f'<div class="tip-{typ}">{t(lang, tip["key"])}</div>', unsafe_allow_html=True)
        else:
            title = t(lang, tip.get("title_key", ""))
            body = t(lang, tip.get("body_key", ""))
            st.markdown(f'<div class="tip-{typ}"><strong>{title}</strong><br>{body}</div>', unsafe_allow_html=True)

    # ── SECTION 1: US MAP ────────────────────────────────────────────────────
    st.markdown("---")
    map_title = "Your State at a Glance" if lang == "en" else "Tu Estado de un Vistazo"
    st.markdown(f"### {map_title}")
    map_sub = (f"Your state (**{state}**) is highlighted. Green = tax deduction available. Light green = tax parity (any plan qualifies). Gray = no deduction."
               if lang == "en" else
               f"Tu estado (**{state}**) está resaltado. Verde = deducción disponible. Verde claro = paridad fiscal. Gris = sin deducción.")
    st.caption(map_sub)

    from utils.knowledge_base import STATE_TAX_DATA
    from utils.scoring import NO_TAX_STATES, NO_DEDUCTION_STATES, PARITY_STATES

    # Build color map for all states
    state_colors = {}
    for abbr, data in STATE_TAX_DATA.items():
        if abbr == state:
            state_colors[abbr] = "#2B650B"   # user's state — dark green
        elif abbr in PARITY_STATES:
            state_colors[abbr] = "#C6DDBB"   # parity — accent green
        elif data.get("offers_529_deduction") and data.get("has_income_tax"):
            state_colors[abbr] = "#3A8916"   # has deduction — primary green
        elif abbr in NO_TAX_STATES:
            state_colors[abbr] = "#A8C5A0"   # no income tax — medium green
        else:
            state_colors[abbr] = "#D0D8D8"   # no deduction — gray

    # SVG US map (simplified but accurate state positions)
    state_positions = {
        "AL": (760,380), "AK": (220,440), "AZ": (220,330), "AR": (680,350),
        "CA": (120,280), "CO": (340,290), "CT": (950,210), "DC": (910,270),
        "DE": (930,255), "FL": (780,430), "GA": (780,370), "HI": (320,460),
        "ID": (210,200), "IL": (720,270), "IN": (750,270), "IA": (650,240),
        "KS": (560,300), "KY": (770,310), "LA": (680,400), "ME": (980,160),
        "MD": (910,260), "MA": (960,195), "MI": (760,220), "MN": (630,180),
        "MS": (710,390), "MO": (660,300), "MT": (290,170), "NE": (540,255),
        "NV": (170,265), "NH": (960,185), "NJ": (940,245), "NM": (310,350),
        "NY": (910,205), "NC": (840,330), "ND": (530,170), "OH": (800,265),
        "OK": (560,350), "OR": (150,210), "PA": (880,240), "RI": (965,210),
        "SC": (830,360), "SD": (530,215), "TN": (750,340), "TX": (530,400),
        "UT": (250,280), "VT": (950,180), "VA": (870,295), "WA": (170,165),
        "WV": (840,280), "WI": (700,210), "WY": (330,230),
    }

    # Build map using Plotly choropleth - proper US map with state fills
    import plotly.graph_objects as go

    state_abbrs = list(state_colors.keys())
    color_vals = []
    color_scale_map = {"#2B650B": 4, "#3A8916": 3, "#C6DDBB": 2, "#A8C5A0": 1, "#D0D8D8": 0}
    for abbr in state_abbrs:
        color_vals.append(color_scale_map.get(state_colors.get(abbr, "#D0D8D8"), 0))

    # Custom discrete colorscale matching brand colors
    colorscale = [
        [0.0, "#D0D8D8"],   # no deduction - gray
        [0.25, "#D0D8D8"],
        [0.25, "#A8C5A0"],  # no income tax - light green
        [0.5, "#A8C5A0"],
        [0.5, "#C6DDBB"],   # tax parity - accent green
        [0.75, "#C6DDBB"],
        [0.75, "#3A8916"],  # tax deduction - primary green
        [0.95, "#3A8916"],
        [0.95, "#2B650B"],  # user state - dark green
        [1.0, "#2B650B"],
    ]

    # Hover text per state
    hover_texts = []
    from utils.knowledge_base import STATE_TAX_DATA as STD
    def _deduction_label(sd):
        if sd.get("parity"):
            return "Tax parity — deduct contributions to any 529 plan"
        if sd.get("unlimited_deduction"):
            return "Unlimited deduction — 100% of contributions"
        if sd.get("offers_529_deduction"):
            limit = sd.get("deduction_limit_single")
            if limit:
                return f"Deduction up to ${limit:,}/yr (single filer)"
            return "State deduction available"
        if not sd.get("has_income_tax"):
            return "No state income tax"
        return "No 529 state deduction"

    for abbr in state_abbrs:
        sd = STD.get(abbr, {})
        name = sd.get("name", abbr)
        label = _deduction_label(sd)
        if abbr == state:
            hover_texts.append(f"<b>{name} — YOUR STATE</b><br>{label}")
        else:
            hover_texts.append(f"<b>{name}</b><br>{label}")

    fig_map = go.Figure(go.Choropleth(
        locations=state_abbrs,
        z=color_vals,
        locationmode="USA-states",
        colorscale=colorscale,
        zmin=0, zmax=4,
        showscale=False,
        hovertext=hover_texts,
        hoverinfo="text",
        marker_line_color="white",
        marker_line_width=1.5,
    ))

    # Add annotation for user state
    state_name_full = STATE_TAX_DATA.get(state, {}).get("name", state)
    fig_map.add_annotation(
        text=f"▶ {state_name_full}",
        xref="paper", yref="paper",
        x=0.01, y=0.98,
        showarrow=False,
        font=dict(size=13, color="#2B650B", family="Inter, Arial"),
        bgcolor="rgba(242,249,237,0.9)",
        bordercolor="#3A8916",
        borderwidth=1,
        borderpad=4,
    )

    fig_map.update_layout(
        geo=dict(
            scope="usa",
            projection_type="albers usa",
            showlakes=False,
            showland=True,
            landcolor="#f0f6ed",
            showocean=False,
            bgcolor="#f0f6ed",
            framewidth=0,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=340,
        paper_bgcolor="#f0f6ed",
        plot_bgcolor="#f0f6ed",
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Inter, Arial",
            bordercolor="#C6DDBB",
        ),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Legend below map
    legend_html = """
    <div style="display:flex;gap:18px;flex-wrap:wrap;font-size:0.8rem;color:#444;margin-top:-10px;margin-bottom:8px;padding-left:4px;">
      <span><span style="display:inline-block;width:12px;height:12px;background:#2B650B;border-radius:2px;margin-right:4px;"></span>Your state</span>
      <span><span style="display:inline-block;width:12px;height:12px;background:#3A8916;border-radius:2px;margin-right:4px;"></span>Tax deduction</span>
      <span><span style="display:inline-block;width:12px;height:12px;background:#C6DDBB;border-radius:2px;margin-right:4px;"></span>Tax parity (any plan qualifies)</span>
      <span><span style="display:inline-block;width:12px;height:12px;background:#A8C5A0;border-radius:2px;margin-right:4px;"></span>No income tax</span>
      <span><span style="display:inline-block;width:12px;height:12px;background:#D0D8D8;border-radius:2px;margin-right:4px;"></span>No deduction</span>
    </div>"""
    st.markdown(legend_html, unsafe_allow_html=True)

        # ── SECTION 2: SAVINGS PROJECTION ────────────────────────────────────────
    st.markdown("---")
    proj_title = "Your College Savings Projection" if lang == "en" else "Tu Proyección de Ahorro Universitario"
    st.markdown(f"### {proj_title}")

    from utils.scoring import SAVINGS_MIDPOINTS, AGE_TO_HORIZON
    default_annual = SAVINGS_MIDPOINTS.get(savings_str, 3000)
    default_monthly = max(int(default_annual / 12), 25)
    years_to_enroll = AGE_TO_HORIZON.get(age_str, 10)
    costs_by_type = _get_college_costs(state)

    if years_to_enroll > 0:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 2])
        with col_ctrl1:
            monthly_input = st.number_input(
                "Monthly contribution" if lang == "en" else "Contribución mensual",
                min_value=25, max_value=5000, value=default_monthly, step=25,
                format="%d", help="How much you plan to save each month"
            )
        with col_ctrl2:
            return_options = {"Conservative (4%)": 0.04, "Moderate (6%)": 0.06, "Growth (8%)": 0.08}
            return_options_es = {"Conservador (4%)": 0.04, "Moderado (6%)": 0.06, "Crecimiento (8%)": 0.08}
            ro = return_options if lang == "en" else return_options_es
            return_label = st.selectbox(
                "Expected annual return" if lang == "en" else "Rendimiento anual esperado",
                list(ro.keys()), index=1
            )
            return_rate = ro[return_label]
        with col_ctrl3:
            school_type_options = list(costs_by_type.keys())
            school_type_options_es = [
                "Universidad pública (en estado)",
                "Universidad pública (fuera de estado)",
                "Universidad privada",
                "Colegio comunitario (2 años)"
            ]
            school_opts = school_type_options if lang == "en" else school_type_options_es
            school_label = st.selectbox(
                "School type" if lang == "en" else "Tipo de institución",
                school_opts, index=0
            )
            # Map ES labels back to EN keys
            if lang == "es":
                es_to_en = dict(zip(school_type_options_es, school_type_options))
                school_type_key = es_to_en.get(school_label, school_type_options[0])
            else:
                school_type_key = school_label

        base_cost = costs_by_type[school_type_key]
        future_cost = _inflation_adjusted_cost(base_cost, years_to_enroll)
        projected, years_list, balances = _project_balance(monthly_input, years_to_enroll, return_rate)

        # Cost projection line (inflation-adjusted year by year)
        cost_line = [_inflation_adjusted_cost(base_cost, y) for y in years_list]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years_list, y=balances,
            mode="lines+markers",
            name="Your 529 Balance" if lang == "en" else "Tu Saldo 529",
            line=dict(color="#3A8916", width=3),
            marker=dict(size=5, color="#2B650B"),
            fill="tozeroy", fillcolor="rgba(58,137,22,0.08)",
            hovertemplate="Year %{x}: $%{y:,.0f}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=years_list, y=cost_line,
            mode="lines",
            name="Est. Cost (w/ 4% tuition inflation)" if lang == "en" else "Costo Estimado (inflación 4%)",
            line=dict(color="#708686", width=2, dash="dash"),
            hovertemplate="Year %{x}: $%{y:,.0f}<extra></extra>"
        ))
        fig.update_layout(
            height=340,
            margin=dict(l=20, r=20, t=20, b=50),
            plot_bgcolor="#f8fbf6",
            paper_bgcolor="#ffffff",
            xaxis=dict(
                title="Years from now" if lang == "en" else "Años desde ahora",
                gridcolor="#e0e8e0", tickmode="linear", dtick=max(1, years_to_enroll//10)
            ),
            yaxis=dict(gridcolor="#e0e8e0", tickformat="$,.0f"),
            legend=dict(orientation="h", y=-0.28, x=0),
            font=dict(family="Inter, Arial", size=12, color="#1A1A1A"),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Metrics row
        gap = future_cost - projected
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                "Projected Balance" if lang == "en" else "Saldo Proyectado",
                f"${projected:,.0f}",
                help="At the return rate you selected" if lang == "en" else "Al rendimiento seleccionado"
            )
        with c2:
            st.metric(
                f"Est. {school_type_key.split()[0]} Cost" if lang == "en" else "Costo Estimado",
                f"${future_cost:,.0f}",
                help="Adjusted for 4% annual tuition inflation" if lang == "en" else "Ajustado por inflación universitaria del 4% anual"
            )
        with c3:
            if gap > 0:
                st.metric(
                    "Funding Gap" if lang == "en" else "Brecha",
                    f"${gap:,.0f}",
                    delta=f"-${gap:,.0f}",
                    delta_color="inverse"
                )
                monthly_needed = int((gap / (((1 + return_rate/12)**(years_to_enroll*12) - 1) / (return_rate/12))) + 0.5) if return_rate > 0 else int(gap / (years_to_enroll * 12))
                st.caption(f"To fully fund: ~${monthly_needed + monthly_input:,}/mo total" if lang == "en"
                          else f"Para financiar completo: ~${monthly_needed + monthly_input:,}/mes total")
            else:
                surplus = abs(gap)
                st.metric(
                    "Surplus" if lang == "en" else "Excedente",
                    f"${surplus:,.0f}",
                    delta="Fully funded ✓" if lang == "en" else "¡Completamente financiado ✓"
                )

        # ── Years of college covered (savings adequacy framing) ──────────────
        # Same concept the 529 Intelligence Dashboard uses: balance / annual cost.
        future_annual_cost = future_cost / (2 if "Community" in school_type_key else 4)
        if future_annual_cost > 0:
            years_covered = projected / future_annual_cost
            total_years = 2 if "Community" in school_type_key else 4
            years_covered_capped = min(years_covered, total_years)
            pct = min(100, (projected / future_cost) * 100) if future_cost > 0 else 0
            if lang == "en":
                yc_msg = (f"That projected balance covers about **{years_covered:.1f} of {total_years} years** "
                          f"of {school_type_key.lower()} ({pct:.0f}% of the total cost).")
            else:
                yc_msg = (f"Ese saldo proyectado cubre aproximadamente **{years_covered:.1f} de {total_years} años** "
                          f"({pct:.0f}% del costo total).")
            bar_html = f"""
            <div style="margin:6px 0 12px;">
              <div style="background:#e0e8e0;border-radius:6px;height:22px;width:100%;position:relative;overflow:hidden;">
                <div style="background:linear-gradient(90deg,#3A8916,#2B650B);height:22px;width:{pct:.0f}%;border-radius:6px;"></div>
                <div style="position:absolute;top:0;left:0;width:100%;height:22px;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:600;color:#1A1A1A;">{years_covered_capped:.1f} / {total_years} years</div>
              </div>
            </div>"""
            st.markdown(bar_html, unsafe_allow_html=True)
            st.markdown(yc_msg)

        note = (f"Balance projected using ${monthly_input:,}/month at {return_rate*100:.0f}% annual return, compounded monthly. "
                f"Cost projection for {school_type_key} in {STATE_TAX_DATA.get(state,{}).get('name',state)} assumes 4% annual tuition inflation. "
                f"For illustrative purposes only \u2014 not financial advice."
                if lang == "en" else
                f"Saldo proyectado con ${monthly_input:,}/mes al {return_rate*100:.0f}% de rendimiento anual. "
                f"El costo asume una inflación universitaria del 4% anual. Solo con fines ilustrativos.")
        st.caption(note)
        st.caption(_cost_source_label(lang))
    else:
        st.info("College is starting soon — focus on stable, low-risk investment options in your plan." if lang == "en"
                else "La universidad está por comenzar — enfócate en opciones de inversión estables y de bajo riesgo.")

    # ── SECTION 3: HOME STATE PLAN (neutral disclosure, never ranked) ────────
    from utils.knowledge_base import STATE_TAX_DATA as _STD
    from utils.scoring import NO_TAX_STATES as _NTS, NO_DEDUCTION_STATES as _NDS
    home_plan = st.session_state.get("home_plan")
    other_plans = st.session_state.get("other_plans", [])
    state_name = _STD.get(state, {}).get("name", state)

    st.markdown("---")
    st.markdown(f"### {t(lang, 'home_plan_heading')}")

    if home_plan:
        # Choose the right intro based on the state's tax situation
        if state in _NTS:
            intro = t(lang, "home_plan_intro_notax", state=state_name)
        elif state in _NDS:
            intro = t(lang, "home_plan_intro_nodeduction", state=state_name)
        else:
            intro = t(lang, "home_plan_intro_tax", state=state_name)
        st.markdown(intro)

        er = home_plan.get("avg_expense_ratio", 0)
        er_str = f"{er*100:.2f}%" if er > 0 else "0%"
        min_c = home_plan.get("min_contribution", 0)
        min_str = t(lang, "no_minimum") if min_c == 0 else f"${min_c:,}"
        rating = home_plan.get("morningstar_rating", "NR")
        rating_str = rating if rating != "NR" else ("Not rated" if lang == "en" else "Sin calificación")
        managers = ", ".join(home_plan.get("fund_managers", [])) or "\u2014"
        ts = home_plan.get("estimated_annual_tax_savings", 0)
        url = home_plan.get("enroll_url", "#")

        tax_callout = ""
        if ts > 0:
            tax_callout = f'<div class="tax-callout">\u2713 {t(lang, "home_plan_tax_callout", amount=ts)}</div>'

        card = f"""
        <div class="home-plan-card">
          <span class="home-plan-banner">{t(lang, 'home_plan_heading')}</span>
          <div style="font-size:1.3rem;font-weight:700;color:#2B650B;margin-bottom:4px;">{home_plan['name']}</div>
          {tax_callout}
          <div class="fact-grid">
            <div><span class="lbl">{t(lang,'plan_facts_fees')}</span><span class="val">{er_str}</span></div>
            <div><span class="lbl">{t(lang,'plan_facts_min')}</span><span class="val">{min_str}</span></div>
            <div><span class="lbl">{t(lang,'plan_facts_rating')}</span><span class="val">{rating_str}</span></div>
            <div><span class="lbl">{t(lang,'plan_facts_managers')}</span><span class="val">{managers}</span></div>
          </div>
          <div class="enroll-link" style="margin-top:8px;"><a href="{url}" target="_blank" rel="noopener noreferrer">{t(lang,'view_plan_button')} \u2192</a></div>
        </div>"""
        st.markdown(card, unsafe_allow_html=True)
    else:
        # State sponsors no plan (e.g., Wyoming)
        st.info(t(lang, "no_home_plan", state=state_name))

    # ── SECTION 3b: OTHER PLANS TO EXPLORE (curated, neutral sort) ───────────
    if other_plans:
        st.markdown("---")
        st.markdown(f"### {t(lang, 'other_plans_heading')}")
        st.markdown(t(lang, "other_plans_intro"))
        sort_key = st.session_state.get("other_sort_key", "sorted_by_default")
        st.caption(t(lang, sort_key))

        for plan in other_plans:
            er = plan.get("avg_expense_ratio", 0)
            er_str = f"{er*100:.2f}%" if er > 0 else "0%"
            min_c = plan.get("min_contribution", 0)
            min_str = t(lang, "no_minimum") if min_c == 0 else f"${min_c:,}"
            rating = plan.get("morningstar_rating", "NR")
            rating_str = rating if rating != "NR" else ("Not rated" if lang == "en" else "Sin calificación")
            managers = ", ".join(plan.get("fund_managers", [])[:3]) or "\u2014"
            url = plan.get("enroll_url", "#")

            card = f"""
            <div class="neutral-plan-card">
              <div style="font-size:1.1rem;font-weight:700;color:#2B650B;margin-bottom:6px;">{plan['name']}</div>
              <div class="fact-grid">
                <div><span class="lbl">{t(lang,'plan_facts_fees')}</span><span class="val">{er_str}</span></div>
                <div><span class="lbl">{t(lang,'plan_facts_min')}</span><span class="val">{min_str}</span></div>
                <div><span class="lbl">{t(lang,'plan_facts_rating')}</span><span class="val">{rating_str}</span></div>
                <div><span class="lbl">{t(lang,'plan_facts_managers')}</span><span class="val">{managers}</span></div>
              </div>
              <div class="enroll-link" style="margin-top:6px;"><a href="{url}" target="_blank" rel="noopener noreferrer">{t(lang,'view_plan_button')} \u2192</a></div>
            </div>"""
            st.markdown(card, unsafe_allow_html=True)

    # ── SECTION 4: TAX BENEFIT CHART ─────────────────────────────────────────
    from utils.scoring import SAVINGS_MIDPOINTS, AGE_TO_HORIZON
    from utils.knowledge_base import STATE_TAX_DATA, STATE_TAX_RATES
    from utils.scoring import NO_TAX_STATES, NO_DEDUCTION_STATES

    if state not in NO_TAX_STATES and state not in NO_DEDUCTION_STATES and home_plan:
        st.markdown("---")
        tax_title = "Your Home State Tax Benefit Over Time" if lang == "en" else "Tu Beneficio Fiscal Estatal en el Tiempo"
        st.markdown(f"### {tax_title}")
        tax_sub = (f"If you contribute to your home state plan, here is the estimated state tax benefit accumulated over {years_to_enroll} years."
                   if lang == "en" else
                   f"Si contribuyes al plan de tu estado, este es el beneficio fiscal estatal estimado acumulado durante {years_to_enroll} años.")
        st.caption(tax_sub)

        annual_tax_sav = home_plan.get("estimated_annual_tax_savings", 0)

        if annual_tax_sav > 0 and years_to_enroll > 0:
            import plotly.graph_objects as go
            years_tax = list(range(1, years_to_enroll + 1))
            cumulative = [round(annual_tax_sav * y, 0) for y in years_tax]

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=years_tax, y=cumulative,
                marker_color="#3A8916",
                marker_line_color="#2B650B",
                marker_line_width=1,
                name="Cumulative Tax Savings" if lang == "en" else "Ahorro Fiscal Acumulado",
                hovertemplate="Year %{x}: $%{y:,.0f} saved<extra></extra>",
            ))
            fig2.update_layout(
                height=260,
                margin=dict(l=20, r=20, t=20, b=40),
                plot_bgcolor="#f8fbf6",
                paper_bgcolor="#ffffff",
                xaxis=dict(title="Year" if lang == "en" else "Año",
                          gridcolor="#e0e8e0", tickmode="linear", dtick=2),
                yaxis=dict(title="Cumulative savings (USD)", gridcolor="#e0e8e0",
                          tickformat="$,.0f"),
                font=dict(family="Inter, Arial", size=12, color="#1A1A1A"),
            )
            st.plotly_chart(fig2, use_container_width=True)

            total_tax_sav = annual_tax_sav * years_to_enroll
            msg = (f"Contributing to **{home_plan['name']}** could provide an estimated **${total_tax_sav:,.0f}** in state income tax benefits over {years_to_enroll} years \u2014 a benefit available specifically because it is your home state plan."
                   if lang == "en" else
                   f"Contribuir a **{home_plan['name']}** podría brindar aproximadamente **${total_tax_sav:,.0f}** en beneficios fiscales estatales durante {years_to_enroll} años \u2014 disponible por ser el plan de tu estado.")
            st.success(msg)
        else:
            st.info("No direct state tax benefit for this plan combination, but federal tax-free growth applies." if lang == "en"
                    else "No hay beneficio fiscal estatal directo para esta combinación, pero el crecimiento libre de impuestos federales aplica.")

    # ── PDF DOWNLOAD ──────────────────────────────────────────────────────────
    st.markdown("---")
    try:
        from utils.pdf_generator import generate_pdf
        _pdf_plans = ([home_plan] if home_plan else []) + other_plans
        pdf = generate_pdf(answers, _pdf_plans[:4], lang)
        label = "\U0001F4C4 Download Your PDF Summary" if lang == "en" else "\U0001F4C4 Descargar Resumen PDF"
        st.download_button(label=label, data=pdf, file_name="529_plan_results.pdf",
                          mime="application/pdf", key="dl_pdf")
    except:
        pass

    st.markdown("---")
    all_url = "https://www.529network.org/529-plans-by-state/"
    st.markdown(f'<a href="{all_url}" target="_blank" style="color:#3A8916;font-weight:600;">{t(lang,"see_all_plans")} \u2192</a>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(t(lang, "start_over"), key="restart"):
        reset()
    footer()

# ── ROUTER ────────────────────────────────────────────────────────────────────
screen = st.session_state.screen
if screen == "welcome": screen_welcome()
elif screen == "questionnaire": screen_questionnaire()
elif screen == "results": screen_results()
else: screen_welcome()
