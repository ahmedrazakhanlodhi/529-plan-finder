# utils/scoring.py — The 529 Network 529 Plan Finder
from utils.knowledge_base import PLAN_DATA, STATE_TAX_DATA, STATE_TAX_RATES

PRIORITY_MAP = {
    "State tax benefits (maximize my deduction or credit)": "tax",
    "Beneficios fiscales estatales (maximizar mi deduccion o credito)": "tax",
    "Lowest possible fees (keep more money invested)": "fee",
    "Las comisiones mas bajas posibles (mantener mas dinero invertido)": "fee",
    "Best investment options (more control, better funds)": "investment",
    "Las mejores opciones de inversion (mas control, mejores fondos)": "investment",
    "Plan ratings and reputation (third-party-vetted quality)": "rating",
    "Calificaciones y reputacion del plan (calidad verificada por terceros)": "rating",
}
MORNINGSTAR_SCORES = {"Gold": 20, "Silver": 15, "Bronze": 10, "Neutral": 5, "NR": 5}

SAVINGS_MIDPOINTS = {
    "Less than $1,000": 500, "Menos de $1,000": 500,
    "$1,000 to $5,000": 3000, "$1,000 a $5,000": 3000,
    "$1,000 – $5,000": 3000, "$1,000 - $5,000": 3000,
    "$5,000 to $15,000": 10000, "$5,000 a $15,000": 10000,
    "$5,000 – $15,000": 10000, "$5,000 - $15,000": 10000,
    "More than $15,000": 20000, "Mas de $15,000": 20000,
    "Not sure yet": 3000, "No estoy seguro/a": 3000,
    "I'm not sure yet": 3000,
}
FILING_STATUS = {
    "Under $50,000": "single", "Menos de $50,000": "single",
    "$50,000 to $100,000": "single", "$50,000 a $100,000": "single",
    "$50,000 – $100,000": "single", "$50,000 - $100,000": "single",
    "$100,000 to $200,000": "joint", "$100,000 a $200,000": "joint",
    "$100,000 – $200,000": "joint", "$100,000 - $200,000": "joint",
    "Over $200,000": "joint", "Mas de $200,000": "joint",
    "Prefer not to say": "single", "Prefiero no decirlo": "single",
}
AGE_TO_HORIZON = {
    "Not yet born": 18, "Aun no ha nacido": 18,
    "0-2 years old": 17, "0-2 anos": 17,
    "3-5 years old": 14, "3-5 anos": 14,
    "6-10 years old": 10, "6-10 anos": 10,
    "11-14 years old": 6, "11-14 anos": 6,
    "15-17 years old": 2, "15-17 anos": 2,
    "18 or older (in college or starting soon)": 0,
    "18 anos o mas (en la universidad o a punto de comenzar)": 0,
}
NO_TAX_STATES = {"AK","FL","NV","NH","SD","TN","TX","WA","WY"}
NO_DEDUCTION_STATES = {"CA","HI","KY","NC"}
PARITY_STATES = {"AZ","AR","KS","ME","MN","MO","MT","OH","PA"}
K12_NONCONFORMING = {"CA","HI","IL","MI","MN","MT","NE","NJ","NY","OR","VT","WI"}

def _annual_tax_savings(state, savings_str, income_str, instate):
    sd = STATE_TAX_DATA.get(state, {})
    if not sd.get("offers_529_deduction"):
        return 0.0
    is_parity = sd.get("parity", False)
    if not is_parity and not instate:
        return 0.0
    rate = STATE_TAX_RATES.get(state, 0.0)
    filing = FILING_STATUS.get(income_str, "single")
    savings = SAVINGS_MIDPOINTS.get(savings_str, 3000)
    if sd.get("unlimited_deduction"):
        deductible = savings
    else:
        limit_key = "deduction_limit_joint" if filing == "joint" else "deduction_limit_single"
        limit = sd.get(limit_key) or 0
        deductible = min(savings, limit)
    if sd.get("deduction_type") == "credit":
        credit_map = {
            "IN": min(savings * 0.20, 1500),
            "UT": min(savings * 0.0465, 130 if filing == "single" else 260),
            "OR": 170 if filing == "single" else 340,
            "MN": min(savings * 0.50, 500),
            "VT": deductible * rate,
        }
        return credit_map.get(state, deductible * rate)
    return deductible * rate

def _tax_score(plan, state, savings_str, income_str):
    sd = STATE_TAX_DATA.get(state, {})
    if state in NO_TAX_STATES or state in NO_DEDUCTION_STATES:
        return 20.0
    if sd.get("parity"):
        return 20.0
    instate = plan["state"] == state
    sav = _annual_tax_savings(state, savings_str, income_str, instate)
    if sav <= 0:
        return 0.0
    return min(40.0, (sav / 500) * 40)

def _fee_score(plan):
    er = plan.get("avg_expense_ratio", 0.005)
    if er <= 0.0010: return 30.0
    elif er <= 0.0015: return 28.0
    elif er <= 0.0025: return 24.0
    elif er <= 0.0040: return 16.0
    elif er <= 0.0060: return 9.0
    return 4.0

def _inv_score(plan):
    return float(MORNINGSTAR_SCORES.get(plan.get("morningstar_rating", "NR"), 5))

def _weighted(raw, p1, p2):
    d1 = PRIORITY_MAP.get(p1, "")
    d2 = PRIORITY_MAP.get(p2, "")
    # Normalize rating -> investment dimension
    if d1 == "rating": d1 = "investment"
    if d2 == "rating": d2 = "investment"
    def mult(key):
        if key == d1: return 1.4
        if key == d2: return 1.2
        return 1.0
    tax_m = mult("tax"); fee_m = mult("fee"); inv_m = mult("investment")
    score = raw["tax"] * tax_m + raw["fee"] * fee_m + raw["investment"] * inv_m
    max_possible = 40 * tax_m + 30 * fee_m + 20 * inv_m
    return round(min(100.0, (score / max_possible) * 100), 1) if max_possible else 0.0

def _flags(plan, user, state):
    sd = STATE_TAX_DATA.get(state, {})
    flags = []
    if plan["state"] == state: flags.append("your_state")
    if plan.get("is_prepaid"): flags.append("prepaid")
    if sd.get("parity") and not plan.get("is_prepaid") and not plan.get("residency_required"):
        flags.append("parity")
    rel = user.get("relationship", "").lower()
    if ("grandchild" in rel or "nieto" in rel) and plan.get("good_for_grandparents"):
        flags.append("grandparents")
    if plan.get("low_minimum") or plan.get("min_contribution", 999) == 0:
        flags.append("low_min")
    return flags

def score_plans(user):
    state = user.get("state", "")
    savings_str = user.get("annual_savings", "")
    income_str = user.get("income", "")
    p1 = user.get("priority_1", "")
    p2 = user.get("priority_2", "")
    prepaid_str = user.get("prepaid_interest", "").lower()
    wants_prepaid = any(x in prepaid_str for x in ["lock", "yes", "fijar", "si", "prepaid"])
    results = []
    for plan in PLAN_DATA:
        if plan.get("residency_required") and plan["state"] != state:
            continue
        if plan.get("is_prepaid") and not wants_prepaid:
            continue
        if plan.get("is_prepaid") and plan["state"] != state:
            continue
        tax = _tax_score(plan, state, savings_str, income_str)
        fee = _fee_score(plan)
        inv = _inv_score(plan)
        raw = {"tax": tax, "fee": fee, "investment": inv}
        final = _weighted(raw, p1, p2)
        ts = _annual_tax_savings(state, savings_str, income_str, plan["state"] == state)
        results.append({**plan, "score": final, "sub_scores": raw,
                        "flags": _flags(plan, user, state),
                        "estimated_annual_tax_savings": ts})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

def get_context_tips(user):
    state = user.get("state", "")
    k12 = user.get("k12", "").lower()
    tips = []
    if state in NO_TAX_STATES:
        tips.append({"type": "info", "key": "no_income_tax_tip"})
    elif state in NO_DEDUCTION_STATES:
        tips.append({"type": "info", "title_key": "no_deduction_tip_title", "body_key": "no_deduction_tip_body"})
    elif state in PARITY_STATES:
        tips.append({"type": "success", "title_key": "parity_tip_title", "body_key": "parity_tip_body"})
    if state in K12_NONCONFORMING and any(x in k12 for x in ["yes", "si", "possibly", "posiblemente"]):
        tips.append({"type": "warning", "title_key": "k12_warning_title", "body_key": "k12_warning_body"})
    return tips

def generate_explanation(plan, user, rank, lang="en"):
    state = user.get("state", "")
    sd = STATE_TAX_DATA.get(state, {})
    age = user.get("age", "")
    horizon = AGE_TO_HORIZON.get(age, 10)
    er_pct = f"{plan['avg_expense_ratio']*100:.2f}%"
    rating = plan.get("morningstar_rating", "")
    state_name = sd.get("name", state)
    tax_sav = plan.get("estimated_annual_tax_savings", 0)
    managers = ", ".join(plan.get("fund_managers", [])[:2]) or "institutional managers"

    if state in NO_TAX_STATES:
        s1 = (f"As a {state_name} resident, there's no state income tax, so we focused on fees and investment quality."
              if lang == "en" else
              f"Como residente de {state_name}, no hay impuesto estatal, por lo que nos enfocamos en comisiones y calidad.")
    elif state in NO_DEDUCTION_STATES:
        s1 = ("Your state doesn't offer a 529 deduction, so this plan was chosen for competitive fees and investment quality."
              if lang == "en" else
              "Tu estado no ofrece deduccion fiscal, por lo que elegimos este plan por sus comisiones y calidad.")
    elif sd.get("parity"):
        s1 = (f"Your state has tax parity — your deduction applies to any plan you choose, so {plan['name']} costs you no state benefit."
              if lang == "en" else
              f"Tu estado tiene paridad fiscal — tu deduccion aplica a cualquier plan, por lo que {plan['name']} no te cuesta ningun beneficio.")
    elif plan["state"] == state and tax_sav > 0:
        s1 = (f"As a {state_name} resident, you can claim roughly ${tax_sav:,.0f}/year in state tax savings with this plan."
              if lang == "en" else
              f"Como residente de {state_name}, puedes reclamar aproximadamente ${tax_sav:,.0f}/ano en ahorros fiscales estatales.")
    else:
        s1 = ("This plan is open to all U.S. residents and delivers full federal tax-free growth and withdrawals."
              if lang == "en" else
              "Este plan esta disponible para todos los residentes de EE.UU. y ofrece crecimiento y retiros libres de impuestos federales.")

    if rank == 1:
        s2 = (f"With a {er_pct} expense ratio and Morningstar {rating} recognition, it pairs low cost with proven quality."
              if lang == "en" else
              f"Con una tasa de gastos de {er_pct} y calificacion Morningstar {rating}, combina bajo costo con calidad probada.")
    elif rank == 2:
        s2 = (f"Managed by {managers} and rated Morningstar {rating}, this is a well-established, reliable choice."
              if lang == "en" else
              f"Gestionado por {managers} con calificacion Morningstar {rating}, es una opcion solida y confiable.")
    else:
        s2 = (f"A consistent Morningstar {rating} rating and {er_pct} annual fees mean more of your money stays invested."
              if lang == "en" else
              f"Una calificacion Morningstar {rating} constante y comisiones de {er_pct} anuales significan que mas dinero permanece invertido.")

    if horizon >= 15:
        s3 = (f"With {horizon}+ years ahead, you have ample time to benefit from long-term growth."
              if lang == "en" else
              f"Con mas de {horizon} anos por delante, tienes tiempo suficiente para aprovechar el crecimiento a largo plazo.")
    elif horizon >= 6:
        s3 = (f"With about {horizon} years to invest, an age-based portfolio will automatically shift toward conservative options as college approaches."
              if lang == "en" else
              f"Con unos {horizon} anos para invertir, una cartera basada en edad se ajustara automaticamente hacia opciones mas conservadoras.")
    elif horizon >= 1:
        s3 = ("With college close, the conservative options in this plan are well-suited to protect what you've saved."
              if lang == "en" else
              "Con la universidad cerca, las opciones conservadoras de este plan son ideales para proteger tus ahorros.")
    else:
        s3 = ("Even with college underway, tax-free growth continues on any remaining balance."
              if lang == "en" else
              "Incluso con la universidad en curso, el crecimiento libre de impuestos continua sobre el saldo restante.")

    return f"{s1} {s2} {s3}"
