"""
app.py — Elipse Studio CRM & Outreach Agent.
Luxury editorial design matching reference specifications with Dark/Light theme toggle.
"""

import os
import io
import csv
import urllib.parse
from datetime import datetime, date
from dotenv import load_dotenv
import streamlit as st

import db
import agent_core

load_dotenv()

# Bridge Streamlit Cloud secrets to environment variables if present
try:
    if hasattr(st, "secrets"):
        for key, val in st.secrets.items():
            if isinstance(val, str) and not os.environ.get(key):
                os.environ[key] = val
except Exception:
    pass

st.set_page_config(
    page_title="elipse / studio — CRM",
    page_icon="⬭",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

# ---------------------------------------------------------------------------
# Theme Management (Light / Dark)
# ---------------------------------------------------------------------------
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Today"

is_dark = st.session_state["theme"] == "dark"

# Theme Palette Variables
if is_dark:
    BG_COLOR = "#121316"
    CARD_BG = "#1A1C22"
    CARD_BORDER = "#2A2D37"
    TEXT_COLOR = "#F4F3EE"
    TEXT_MUTED = "#8E929E"
    ACCENT_COLOR = "#D9653B"
    ACCENT_HOVER = "#E07A54"
    TAG_BG = "#242731"
    INPUT_BG = "#181A20"
    SIDEBAR_BG = "#0D0E11"
    METRIC_BORDER = "#2D303B"
    BADGE_COLOR = "#E65A40"
else:
    BG_COLOR = "#F9F8F5"
    CARD_BG = "#FFFFFF"
    CARD_BORDER = "#E8E4DC"
    TEXT_COLOR = "#1C1D21"
    TEXT_MUTED = "#767982"
    ACCENT_COLOR = "#A84B2C"
    ACCENT_HOVER = "#B85736"
    TAG_BG = "#F1EEE7"
    INPUT_BG = "#FFFFFF"
    SIDEBAR_BG = "#F4F2EC"
    METRIC_BORDER = "#E6E2D8"
    BADGE_COLOR = "#C94528"

# ---------------------------------------------------------------------------
# Custom Luxury Editorial CSS Injection
# ---------------------------------------------------------------------------
custom_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* Global styles */
html, body, [data-testid="stAppViewContainer"] {{
    background-color: {BG_COLOR} !important;
    color: {TEXT_COLOR} !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}}

[data-testid="stSidebar"] {{
    background-color: {SIDEBAR_BG} !important;
    border-right: 1px solid {CARD_BORDER} !important;
}}

/* Typography */
h1, h2, h3, .serif-title {{
    font-family: 'Playfair Display', 'Cormorant Garamond', Georgia, serif !important;
    color: {TEXT_COLOR} !important;
    letter-spacing: -0.02em;
}}

.hero-heading {{
    font-family: 'Playfair Display', serif !important;
    font-size: 2.75rem !important;
    font-weight: 600 !important;
    line-height: 1.15 !important;
    color: {TEXT_COLOR} !important;
    margin-bottom: 0.25rem !important;
}}

.date-eyebrow {{
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: {TEXT_MUTED} !important;
    margin-bottom: 0.5rem !important;
}}

.subtitle {{
    font-size: 1.05rem !important;
    color: {TEXT_MUTED} !important;
    margin-bottom: 1.5rem !important;
}}

/* Logo */
.logo-container {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0.5rem 0 1.5rem 0;
}}

.logo-oval {{
    width: 22px;
    height: 14px;
    border: 2px solid {ACCENT_COLOR};
    border-radius: 50%;
    transform: rotate(-15deg);
    display: inline-block;
}}

.logo-text {{
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: {TEXT_COLOR};
}}

.logo-sub {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.95rem;
    color: {TEXT_MUTED};
    font-weight: 400;
}}

/* Metric Matrix Card */
.metric-grid-container {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 12px;
    padding: 1.5rem 1rem;
    margin-bottom: 1.75rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.02);
}}

.metric-column {{
    padding: 0.5rem 1.25rem;
    border-right: 1px solid {METRIC_BORDER};
}}

.metric-column:last-child {{
    border-right: none;
}}

.metric-label {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {TEXT_MUTED};
    margin-bottom: 0.4rem;
}}

.metric-val {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: {TEXT_COLOR};
    line-height: 1.1;
    margin-bottom: 0.35rem;
}}

.metric-sub {{
    font-size: 0.8rem;
    color: {TEXT_MUTED};
}}

/* Custom Cards */
.crm-card {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_BORDER};
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.2s ease;
}}

.crm-card:hover {{
    border-color: {ACCENT_COLOR};
    box-shadow: 0 4px 16px rgba(0,0,0,0.04);
}}

/* Badges and Tags */
.stage-tag {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background-color: {TAG_BG};
    color: {TEXT_COLOR};
    border: 1px solid {CARD_BORDER};
}}

.badge-count {{
    background-color: {BADGE_COLOR};
    color: white;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 10px;
    margin-left: 6px;
}}

/* Primary Buttons */
div.stButton > button[kind="primary"] {{
    background-color: {ACCENT_COLOR} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.25rem !important;
    font-size: 0.9rem !important;
    transition: background-color 0.2s ease !important;
}}

div.stButton > button[kind="primary"]:hover {{
    background-color: {ACCENT_HOVER} !important;
}}

/* Form elements */
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] {{
    background-color: {INPUT_BG} !important;
    border-color: {CARD_BORDER} !important;
    color: {TEXT_COLOR} !important;
    border-radius: 8px !important;
}}

/* Streamlit Expander clean styling */
div[data-testid="stExpander"] {{
    background-color: {CARD_BG} !important;
    border: 1px solid {CARD_BORDER} !important;
    border-radius: 10px !important;
    margin-bottom: 0.75rem !important;
}}

/* Sidebar navigation buttons */
.nav-btn {{
    width: 100%;
    text-align: left;
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# Fetch latest CRM Metrics
metrics = db.get_crm_metrics()

# ---------------------------------------------------------------------------
# Left Sidebar Navigation & Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    # Studio Logo
    st.markdown(
        f"""
        <div class="logo-container">
            <span class="logo-oval"></span>
            <span class="logo-text">elipse</span>
            <span class="logo-sub">/ studio</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="date-eyebrow">WORKSPACE</div>', unsafe_allow_html=True)

    # Navigation menu
    nav_options = [
        ("Today", "⊞", 0),
        ("Pipeline", "💼", metrics.get("active_opportunities", 0)),
        ("Contacts", "👥", metrics.get("total_leads", 0)),
        ("Follow-ups", "📅", metrics.get("followups_due", 0)),
        ("AI Lead Finder", "🔍", 0),
    ]

    for name, icon, count in nav_options:
        badge_html = f'<span class="badge-count">{count}</span>' if count > 0 and name == "Follow-ups" else ""
        is_selected = st.session_state["active_tab"] == name
        btn_label = f"{icon}  {name}"
        if count > 0 and name == "Follow-ups":
            btn_label = f"{icon}  {name} ({count})"

        if st.button(
            btn_label,
            key=f"nav_{name}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state["active_tab"] = name
            st.rerun()

    st.divider()

    # Theme Switcher
    st.markdown('<div class="date-eyebrow">PREFERENCES</div>', unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("☀️ Light", type="primary" if not is_dark else "secondary", use_container_width=True):
            st.session_state["theme"] = "light"
            st.rerun()
    with col_t2:
        if st.button("🌙 Dark", type="primary" if is_dark else "secondary", use_container_width=True):
            st.session_state["theme"] = "dark"
            st.rerun()

    st.divider()

    # System Status
    st.markdown('<div class="date-eyebrow">SYSTEM STATUS</div>', unsafe_allow_html=True)
    g_key = os.environ.get("GEMINI_API_KEY")
    h_key = os.environ.get("HUNTER_API_KEY")
    
    if g_key:
        st.caption("🟢 **Gemini 3.6 Flash:** Connected")
    else:
        st.caption("🔴 **Gemini API:** Missing")

    if h_key:
        st.caption("🟢 **Hunter.io:** Connected")
    else:
        st.caption("⚪ **Hunter.io:** Not configured")

    cal_link = agent_core.get_calendar_link()
    st.caption(f"📅 **Calendar:** `{cal_link[:26]}...`")


# ---------------------------------------------------------------------------
# Top Action Bar & Date Banner
# ---------------------------------------------------------------------------
top_col1, top_col2, top_col3 = st.columns([2.5, 3.5, 1.5])

with top_col1:
    st.caption(f"WORKSPACE / **{st.session_state['active_tab'].upper()}**")

with top_col2:
    search_query = st.text_input(
        "Search",
        placeholder="🔍 Search company, contact, or email...",
        label_visibility="collapsed",
    )

with top_col3:
    with st.popover("➕ Add a Lead", use_container_width=True):
        st.markdown("### ➕ Add New Opportunity")
        with st.form("manual_lead_form"):
            new_comp = st.text_input("Company Name *")
            new_web = st.text_input("Website URL", placeholder="https://...")
            new_cname = st.text_input("Contact Person Name", placeholder="e.g. David Ross")
            new_crole = st.text_input("Role / Title", placeholder="e.g. Head of Marketing")
            new_cemail = st.text_input("Contact Email", placeholder="name@company.com")
            new_val = st.number_input("Estimated Deal Value ($)", value=18000.0, step=1000.0)
            new_tag = st.selectbox("Industry / Product Tag", [
                "Bespoke Furniture",
                "Luxury Interiors",
                "Architectural & Real Estate",
                "Automotive & Transport",
                "Yacht & Marine",
                "Industrial Equipment",
                "Consumer Products",
            ])
            new_stage = st.selectbox("Pipeline Stage", [s[0] for s in db.PIPELINE_STAGES], format_func=lambda s: db.STAGE_LABELS.get(s, s))
            new_reason = st.text_area("3D Configurator Angle / Reason", placeholder="Why this company needs an interactive 3D configurator...")
            new_submitted = st.form_submit_button("Save Lead to CRM", type="primary")

            if new_submitted and new_comp.strip():
                db.add_lead(
                    company_name=new_comp.strip(),
                    company_website=new_web.strip(),
                    contact_name=new_cname.strip(),
                    contact_role=new_crole.strip(),
                    contact_email=new_cemail.strip() or "unknown",
                    industry_tag=new_tag,
                    deal_value=new_val,
                    pipeline_stage=new_stage,
                    reason=new_reason.strip(),
                    subject=f"3D Configurator for {new_comp.strip()}",
                    body="Hi team,\n\nI was looking at your product collection and noticed an opportunity to introduce interactive 3D configuration.\n\nBest,\nBilal",
                )
                st.success(f"Added {new_comp}!")
                st.rerun()

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 1: TODAY (Dashboard Executive Overview matching screenshot)
# ---------------------------------------------------------------------------
if st.session_state["active_tab"] == "Today":
    today_formatted = datetime.now().strftime("%A, %B %d, %Y").upper()

    # Hero Greetings
    st.markdown(f'<div class="date-eyebrow">{today_formatted}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 1.25rem;">
            <div>
                <div class="hero-heading">Good morning, Bilal.</div>
                <div class="subtitle">Here's the shape of the studio today.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # PROMINENT AI LEAD DISCOVERY & RESEARCH BAR
    # -----------------------------------------------------------------------
    with st.container():
        st.markdown(
            f"""
            <div class="crm-card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; border-left: 4px solid {ACCENT_COLOR};">
                <div class="date-eyebrow" style="margin-bottom: 0.25rem;">AI LEAD DISCOVERY & RESEARCH ENGINE</div>
                <div style="font-family:'Playfair Display', serif; font-size:1.35rem; font-weight:600; color:{TEXT_COLOR}; margin-bottom: 0.2rem;">
                    Find & Qualify Prospective Clients
                </div>
                <div style="font-size: 0.85rem; color:{TEXT_MUTED}; margin-bottom: 0.75rem;">
                    Enter what you are looking for. Gemini 3.6 Flash will search live web catalogs, verify lack of 3D configurators, lookup decision-maker emails with Hunter.io, and draft personalized outreach emails directly into your CRM.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("today_ai_finder_form"):
            prompt_c1, prompt_c2 = st.columns([4.2, 1.3])
            with prompt_c1:
                today_prompt = st.text_input(
                    "Search Criteria",
                    placeholder="e.g. Find 5 luxury bespoke furniture or kitchen cabinet manufacturers in UAE without a web configurator",
                    label_visibility="collapsed",
                )
            with prompt_c2:
                today_submitted = st.form_submit_button("🚀 Research & Draft", type="primary", use_container_width=True)

        if today_submitted and today_prompt.strip():
            with st.spinner("AI is researching and drafting personalized opportunities for Elipse Studio..."):
                result = agent_core.run_agent(today_prompt.strip(), log=lambda m: None)

            if result.get("error"):
                st.session_state["last_search_error"] = result["error"]
            elif result["saved"] > 0:
                st.session_state["last_search_msg"] = f"🎉 Successfully generated and added {result['saved']} new qualified lead(s) to your CRM!"
                if result.get("skipped_duplicates"):
                    st.session_state["last_search_skip"] = f"Skipped {len(result['skipped_duplicates'])} already in your database."
            else:
                if result.get("skipped_duplicates"):
                    st.session_state["last_search_skip"] = f"Found {len(result['skipped_duplicates'])} matching companies, but all were already in your CRM database."
                else:
                    st.session_state["last_search_error"] = "No new companies found for this prompt. Please try a different query."
            st.rerun()

        if "last_search_error" in st.session_state:
            st.error(f"⚠️ Notice: {st.session_state['last_search_error']}")
            del st.session_state["last_search_error"]

        if "last_search_msg" in st.session_state:
            st.success(st.session_state["last_search_msg"])
            del st.session_state["last_search_msg"]

        if "last_search_skip" in st.session_state:
            st.info(st.session_state["last_search_skip"])
            del st.session_state["last_search_skip"]

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 4-Column Stat Matrix Card
    pipeline_val_fmt = f"${metrics.get('pipeline_value', 0):,.0f}"
    won_val_fmt = f"${metrics.get('won_this_month', 0):,.0f}"
    active_opps = metrics.get("active_opportunities", 0)
    due_count = metrics.get("followups_due", 0)

    stat_cols = st.columns(4)

    with stat_cols[0]:
        st.markdown(
            f"""
            <div class="crm-card" style="padding: 1.25rem;">
                <div class="metric-label">PIPELINE VALUE</div>
                <div class="metric-val">{pipeline_val_fmt}</div>
                <div class="metric-sub">Across {active_opps} opportunities</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with stat_cols[1]:
        st.markdown(
            f"""
            <div class="crm-card" style="padding: 1.25rem;">
                <div class="metric-label">ACTIVE OPPORTUNITIES</div>
                <div class="metric-val">{active_opps}</div>
                <div class="metric-sub">{due_count} need attention</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with stat_cols[2]:
        st.markdown(
            f"""
            <div class="crm-card" style="padding: 1.25rem;">
                <div class="metric-label">WON THIS MONTH</div>
                <div class="metric-val">{won_val_fmt}</div>
                <div class="metric-sub">Closed 3D/CGI projects</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with stat_cols[3]:
        st.markdown(
            f"""
            <div class="crm-card" style="padding: 1.25rem;">
                <div class="metric-label">FOLLOW-UPS DUE</div>
                <div class="metric-val">{due_count}</div>
                <div class="metric-sub">{"Ready for next touch" if due_count > 0 else "All caught up"}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Pipeline at a Glance Card
    st.markdown(
        f"""
        <div class="crm-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.5rem;">
                <div class="date-eyebrow" style="margin-bottom:0;">PIPELINE AT A GLANCE</div>
            </div>
            <div style="font-family:'Playfair Display', serif; font-size:1.8rem; font-weight:600; color:{TEXT_COLOR}; margin-bottom:1rem;">
                Keep momentum moving
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Recent Leads requiring action
    recent_leads = db.get_all_leads()[:5]
    if recent_leads:
        st.markdown("### 🎯 Priority Outreach Items")
        for lead in recent_leads:
            stage_name = db.STAGE_LABELS.get(lead.get("pipeline_stage"), "Draft Ready")
            val = f"${lead.get('deal_value', 15000):,.0f}"

            with st.expander(f"**{lead['company_name']}** — {val} · {lead.get('industry_tag', '3D Configurator')} ({stage_name})"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**Decision Maker:** `{lead.get('contact_name') or 'N/A'}` ({lead.get('contact_role') or 'Role unknown'})")
                    st.markdown(f"**Email:** `{lead.get('contact_email') or 'unknown'}` · **Website:** [{lead.get('company_website')}]({lead.get('company_website')})")
                    st.markdown(f"**Fit Observation:** {lead.get('reason')}")
                    st.markdown(f"**Subject:** {lead.get('subject')}")
                    st.text_area("Draft Body", lead.get("body", ""), height=130, key=f"today_body_{lead['id']}")

                with c2:
                    st.markdown(f"**Current Stage:** `{stage_name}`")
                    new_stg = st.selectbox("Advance Stage", [s[0] for s in db.PIPELINE_STAGES], index=[s[0] for s in db.PIPELINE_STAGES].index(lead.get("pipeline_stage", "draft_ready")), key=f"stg_sel_{lead['id']}", format_func=lambda s: db.STAGE_LABELS.get(s, s))
                    if new_stg != lead.get("pipeline_stage"):
                        db.update_lead(lead["id"], pipeline_stage=new_stg)
                        st.rerun()

                    # Direct Mailto
                    email_target = lead["contact_email"]
                    if email_target and email_target != "unknown" and "@" in email_target:
                        encoded_subj = urllib.parse.quote(lead.get("subject", ""))
                        encoded_body = urllib.parse.quote(lead.get("body", ""))
                        mailto_url = f"mailto:{email_target}?subject={encoded_subj}&body={encoded_body}"
                        st.markdown(f'<a href="{mailto_url}" target="_blank" style="display:block; text-align:center; padding:7px 12px; background-color:{ACCENT_COLOR}; color:white; text-decoration:none; border-radius:6px; font-weight:600; margin-top:8px;">📧 Open in Email Client</a>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 2: PIPELINE (Deal Stage Columns)
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "Pipeline":
    st.markdown('<div class="hero-heading">Studio Pipeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Track and progress accounts through your sales stages.</div>', unsafe_allow_html=True)

    filter_stage = st.selectbox(
        "Stage Filter",
        ["all"] + [s[0] for s in db.PIPELINE_STAGES],
        format_func=lambda s: "All Pipeline Stages" if s == "all" else db.STAGE_LABELS.get(s, s),
    )

    leads = db.get_all_leads(stage_filter=filter_stage, search_query=search_query)

    if not leads:
        st.info("No leads found for this stage filter. Use 'AI Lead Finder' or 'Add a Lead' to populate.")
    else:
        for lead in leads:
            val = f"${lead.get('deal_value', 15000):,.0f}"
            stage_name = db.STAGE_LABELS.get(lead.get("pipeline_stage"), "Draft Ready")
            
            with st.expander(f"💼 **{lead['company_name']}** — {val} · {stage_name}"):
                c1, c2, c3 = st.columns([2, 2, 1.5])

                with c1:
                    st.markdown("#### 🏢 Company & Contact")
                    st.markdown(f"**Website:** [{lead.get('company_website')}]({lead.get('company_website')})")
                    st.markdown(f"**Contact:** {lead.get('contact_name') or 'N/A'} ({lead.get('contact_role') or 'Unknown'})")
                    st.markdown(f"**Email:** `{lead.get('contact_email') or 'unknown'}`")
                    st.markdown(f"**Tag:** `{lead.get('industry_tag', '3D Configurator')}`")
                    st.markdown(f"**Angle:** {lead.get('reason')}")

                with c2:
                    st.markdown("#### ✉️ Outreach Draft")
                    new_subj = st.text_input("Subject", lead.get("subject", ""), key=f"p_subj_{lead['id']}")
                    new_b = st.text_area("Body", lead.get("body", ""), height=150, key=f"p_b_{lead['id']}")

                with c3:
                    st.markdown("#### ⚙️ Manage Deal")
                    new_val = st.number_input("Deal Value ($)", value=float(lead.get("deal_value") or 15000.0), step=1000.0, key=f"val_{lead['id']}")
                    cur_idx = [s[0] for s in db.PIPELINE_STAGES].index(lead.get("pipeline_stage", "draft_ready"))
                    new_stage = st.selectbox("Stage", [s[0] for s in db.PIPELINE_STAGES], index=cur_idx, format_func=lambda s: db.STAGE_LABELS.get(s, s), key=f"p_stg_{lead['id']}")

                    if st.button("💾 Save Updates", key=f"save_p_{lead['id']}", type="primary"):
                        db.update_lead(lead["id"], subject=new_subj, body=new_b, deal_value=new_val, pipeline_stage=new_stage)
                        st.success("Updated!")
                        st.rerun()

                    if st.button("🗑️ Remove", key=f"del_p_{lead['id']}"):
                        db.delete_lead(lead["id"])
                        st.rerun()

                    email_target = lead["contact_email"]
                    if email_target and email_target != "unknown" and "@" in email_target:
                        encoded_subj = urllib.parse.quote(new_subj)
                        encoded_body = urllib.parse.quote(new_b)
                        mailto_url = f"mailto:{email_target}?subject={encoded_subj}&body={encoded_body}"
                        st.markdown(f'<a href="{mailto_url}" target="_blank" style="display:block; text-align:center; padding:6px 12px; background-color:{ACCENT_COLOR}; color:white; text-decoration:none; border-radius:6px; font-weight:600; margin-top:8px;">📧 Open in Mail App</a>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# VIEW 3: CONTACTS & ACCOUNTS
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "Contacts":
    st.markdown('<div class="hero-heading">Contacts & Accounts</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Complete client directory and interaction history.</div>', unsafe_allow_html=True)

    leads = db.get_all_leads(search_query=search_query)

    # CSV Export
    if leads:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Company", "Website", "Contact Name", "Role", "Email", "Phone", "Industry Tag", "Deal Value", "Stage", "Notes", "Created At"])
        for l in leads:
            writer.writerow([
                l["id"], l["company_name"], l["company_website"], l.get("contact_name", ""),
                l.get("contact_role", ""), l["contact_email"], l.get("contact_phone", ""),
                l.get("industry_tag", ""), l.get("deal_value", ""), l.get("pipeline_stage", ""),
                l.get("notes", ""), l["created_at"]
            ])

        st.download_button(
            label="📥 Export Directory to CSV",
            data=output.getvalue(),
            file_name="elipse_crm_contacts.csv",
            mime="text/csv",
        )

    for lead in leads:
        stage_name = db.STAGE_LABELS.get(lead.get("pipeline_stage"), "Draft Ready")
        with st.expander(f"👤 **{lead.get('contact_name') or lead['company_name']}** · {lead['company_name']} ({stage_name})"):
            c1, c2 = st.columns([1.5, 2])
            with c1:
                st.markdown(f"**Company:** [{lead['company_name']}]({lead.get('company_website')})")
                st.markdown(f"**Contact:** {lead.get('contact_name') or 'N/A'}")
                st.markdown(f"**Role:** {lead.get('contact_role') or 'Unknown'}")
                st.markdown(f"**Email:** `{lead['contact_email']}`")
                st.markdown(f"**Phone:** `{lead.get('contact_phone') or 'None'}`")
                st.markdown(f"**Industry:** `{lead.get('industry_tag')}`")
                st.markdown(f"**Deal Value:** `${lead.get('deal_value', 15000):,.0f}`")

            with c2:
                notes = st.text_area("Meeting & Relationship Notes", lead.get("notes") or "", height=120, key=f"notes_{lead['id']}", placeholder="Log call notes, design requirements, follow-up thoughts...")
                if st.button("💾 Save Notes", key=f"savenotes_{lead['id']}"):
                    db.update_lead(lead["id"], notes=notes)
                    st.success("Notes saved!")
                    st.rerun()


# ---------------------------------------------------------------------------
# VIEW 4: FOLLOW-UPS QUEUE
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "Follow-ups":
    st.markdown('<div class="hero-heading">Follow-up Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Stay on top of active conversations and scheduled check-ins.</div>', unsafe_allow_html=True)

    leads = db.get_all_leads()
    followup_leads = [l for l in leads if l.get("pipeline_stage") in ["contacted", "followup_due", "proposal_sent"]]

    if not followup_leads:
        st.info("No active follow-ups due right now. When you mark leads as 'Outreach Sent', they will appear here.")
    else:
        for lead in followup_leads:
            stage_name = db.STAGE_LABELS.get(lead.get("pipeline_stage"), "Outreach Sent")
            with st.expander(f"⏰ **{lead['company_name']}** — Next Step for {lead.get('contact_name') or 'Team'} ({stage_name})"):
                st.markdown(f"**Contact Email:** `{lead['contact_email']}`")
                st.markdown(f"**Initial Outreach Subject:** {lead.get('subject')}")

                # Quick 2nd touch generator
                suggested_followup = (
                    f"Hi {lead.get('contact_name', 'there')},\n\n"
                    f"Wanted to quickly bump this in case you missed my earlier note regarding interactive 3D web configurators for {lead['company_name']}.\n\n"
                    f"We recently put together an interactive visual demo showing how product customization increases customer engagement. Would you be open to a 10-minute preview?\n\n"
                    f"Here's my calendar: {agent_core.get_calendar_link()}\n\n"
                    f"Best,\nBilal"
                )

                st.markdown("#### ⚡ Quick Follow-up Draft")
                fu_body = st.text_area("Follow-up Message", suggested_followup, height=140, key=f"fu_{lead['id']}")

                b1, b2 = st.columns([1, 1])
                with b1:
                    email_target = lead["contact_email"]
                    if email_target and email_target != "unknown" and "@" in email_target:
                        encoded_subj = urllib.parse.quote(f"Re: {lead.get('subject', 'Question')}")
                        encoded_body = urllib.parse.quote(fu_body)
                        mailto_url = f"mailto:{email_target}?subject={encoded_subj}&body={encoded_body}"
                        st.markdown(f'<a href="{mailto_url}" target="_blank" style="display:inline-block; padding:6px 14px; background-color:{ACCENT_COLOR}; color:white; text-decoration:none; border-radius:6px; font-weight:600;">📧 Send Follow-up (1-Click)</a>', unsafe_allow_html=True)
                with b2:
                    if st.button("✅ Mark as Meeting Booked", key=f"mtg_{lead['id']}", type="primary"):
                        db.update_lead(lead["id"], pipeline_stage="meeting_booked")
                        st.success("Moved to Meeting Booked!")
                        st.rerun()


# ---------------------------------------------------------------------------
# VIEW 5: AI LEAD FINDER (Research & Drafting Hub)
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "AI Lead Finder":
    st.markdown('<div class="hero-heading">AI Lead Discovery & Research</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Gemini 3.6 Flash live web search + Hunter.io decision-maker enrichment.</div>', unsafe_allow_html=True)

    with st.form("ai_finder_form"):
        prompt = st.text_input(
            "What kind of businesses are you targeting?",
            placeholder="e.g. Find 5 luxury bespoke kitchen cabinet manufacturers in UAE or UK without a 3D configurator",
        )
        submitted = st.form_submit_button("🚀 Discover & Draft Leads", type="primary")

    if submitted and prompt.strip():
        with st.spinner("AI is researching and drafting personalized opportunities for Elipse Studio..."):
            result = agent_core.run_agent(prompt.strip(), log=lambda m: None)

        st.session_state["finder_search_msg"] = f"🎉 Successfully generated and added {result['saved']} new qualified lead(s) into your CRM!"
        if result.get("skipped_duplicates"):
            st.session_state["finder_search_skip"] = f"Skipped {len(result['skipped_duplicates'])} already in your database."
        st.rerun()

    if "finder_search_msg" in st.session_state:
        st.success(st.session_state["finder_search_msg"])
        if "finder_search_skip" in st.session_state:
            st.info(st.session_state["finder_search_skip"])
        del st.session_state["finder_search_msg"]
        if "finder_search_skip" in st.session_state:
            del st.session_state["finder_search_skip"]
