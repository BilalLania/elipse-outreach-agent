"""
app.py — Elipse Studio CRM & Outreach Agent.
Luxury editorial design matching reference specifications with Dark/Light theme toggle.
"""

import os
import io
import csv
import textwrap
import urllib.parse
from datetime import datetime, date
from dotenv import load_dotenv
import streamlit as st

import importlib
import db
try:
    importlib.reload(db)
except Exception:
    pass

import agent_core
try:
    importlib.reload(agent_core)
except Exception:
    pass

import team_analytics
try:
    importlib.reload(team_analytics)
except Exception:
    pass

import lead_engine
try:
    importlib.reload(lead_engine)
except Exception:
    pass

STANDARD_CATEGORIES = getattr(db, "STANDARD_CATEGORIES", [
    "⛳ Custom Golf Carts",
    "🏎️ Custom Automotive & Mobility",
    "🛋️ Luxury Furniture & Interiors",
    "🏗️ Real Estate & Megaprojects",
    "⛵ Superyachts & Marine",
    "⚡ Tech & Commercial Products",
])

def clean_html(html_str: str) -> str:
    # Completely strip leading whitespace from every line to prevent Markdown from ever creating code blocks
    return "\n".join(line.lstrip() for line in html_str.splitlines()).strip()

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
    BG_COLOR = "#0D0F12"
    CARD_BG = "#161920"
    CARD_BORDER = "#262B36"
    TEXT_COLOR = "#F8FAFC"
    TEXT_MUTED = "#94A3B8"
    ACCENT_COLOR = "#E06842"
    ACCENT_HOVER = "#EA7A56"
    TAG_BG = "#222733"
    INPUT_BG = "#1C202A"
    SIDEBAR_BG = "#0B0C0E"
    METRIC_BORDER = "#262B36"
    BADGE_COLOR = "#EF4444"
else:
    BG_COLOR = "#F8FAFC"
    CARD_BG = "#FFFFFF"
    CARD_BORDER = "#E2E8F0"
    TEXT_COLOR = "#0F172A"
    TEXT_MUTED = "#64748B"
    ACCENT_COLOR = "#A84B2C"
    ACCENT_HOVER = "#B85736"
    TAG_BG = "#F1F5F9"
    INPUT_BG = "#FFFFFF"
    SIDEBAR_BG = "#F1F5F9"
    METRIC_BORDER = "#E2E8F0"
    BADGE_COLOR = "#C94528"

# ---------------------------------------------------------------------------
# Custom Luxury Editorial CSS Injection
# ---------------------------------------------------------------------------
custom_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

/* Global styles */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background-color: {BG_COLOR} !important;
    color: {TEXT_COLOR} !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}}

[data-testid="stSidebar"] {{
    background-color: {SIDEBAR_BG} !important;
    border-right: 1px solid {CARD_BORDER} !important;
}}

[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {{
    color: {TEXT_COLOR} !important;
}}

/* Typography */
h1, h2, h3, h4, h5, h6, .serif-title {{
    font-family: 'Playfair Display', 'Cormorant Garamond', Georgia, serif !important;
    color: {TEXT_COLOR} !important;
    letter-spacing: -0.02em;
}}

p, span, label, div {{
    color: {TEXT_COLOR};
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
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}}

/* Metric Cards */
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

/* Buttons */
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

div.stButton > button[kind="secondary"] {{
    background-color: {CARD_BG} !important;
    color: {TEXT_COLOR} !important;
    border: 1px solid {CARD_BORDER} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.2s ease !important;
}}

div.stButton > button[kind="secondary"]:hover {{
    border-color: {ACCENT_COLOR} !important;
    color: {ACCENT_COLOR} !important;
}}

/* Form elements & Inputs */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"] {{
    background-color: {INPUT_BG} !important;
    border: 1px solid {CARD_BORDER} !important;
    border-radius: 8px !important;
}}

input, textarea, select {{
    color: {TEXT_COLOR} !important;
    -webkit-text-fill-color: {TEXT_COLOR} !important;
    background-color: transparent !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}}

input::placeholder, textarea::placeholder {{
    color: {TEXT_MUTED} !important;
    -webkit-text-fill-color: {TEXT_MUTED} !important;
    opacity: 0.75 !important;
}}

div[data-testid="stWidgetLabel"] label,
div[data-testid="stWidgetLabel"] p {{
    color: {TEXT_COLOR} !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}}

/* Selectbox & Popovers */
div[data-baseweb="select"] > div {{
    background-color: {INPUT_BG} !important;
    border: 1px solid {CARD_BORDER} !important;
    color: {TEXT_COLOR} !important;
    border-radius: 8px !important;
}}

div[data-baseweb="select"] span {{
    color: {TEXT_COLOR} !important;
}}

div[data-baseweb="popover"],
div[data-baseweb="menu"],
ul[data-baseweb="menu"] {{
    background-color: {CARD_BG} !important;
    border: 1px solid {CARD_BORDER} !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15) !important;
}}

li[data-baseweb="menu-item"] {{
    color: {TEXT_COLOR} !important;
    background-color: {CARD_BG} !important;
}}

li[data-baseweb="menu-item"]:hover {{
    background-color: {TAG_BG} !important;
    color: {ACCENT_COLOR} !important;
}}

/* Expanders */
div[data-testid="stExpander"] {{
    background-color: {CARD_BG} !important;
    border: 1px solid {CARD_BORDER} !important;
    border-radius: 10px !important;
    margin-bottom: 0.75rem !important;
}}

div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span {{
    color: {TEXT_COLOR} !important;
    font-weight: 600 !important;
}}

/* Pills & Segmented Controls */
div[data-testid="stPills"] button,
div[data-testid="stSegmentedControl"] button {{
    background-color: {CARD_BG} !important;
    color: {TEXT_COLOR} !important;
    border: 1px solid {CARD_BORDER} !important;
    font-weight: 600 !important;
}}

div[data-testid="stPills"] button[aria-checked="true"],
div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
    background-color: {ACCENT_COLOR} !important;
    color: white !important;
    border-color: {ACCENT_COLOR} !important;
}}

/* Terminal Tickers & Badges */
.terminal-ticker {{
    font-family: 'JetBrains Mono', 'SF Mono', Consolas, Menlo, monospace !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.2 !important;
}}

.terminal-pill-green {{
    background-color: rgba(16, 185, 129, 0.14);
    color: #10B981;
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    display: inline-block;
}}

.terminal-pill-amber {{
    background-color: rgba(245, 158, 11, 0.14);
    color: #F59E0B;
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    display: inline-block;
}}

.terminal-pill-blue {{
    background-color: rgba(59, 130, 246, 0.14);
    color: #3B82F6;
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    display: inline-block;
}}

/* Streamlit Container Border styling for cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: {CARD_BG} !important;
    border-color: {CARD_BORDER} !important;
    border-radius: 12px !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background-color: {CARD_BG} !important;
    border-color: {CARD_BORDER} !important;
    border-radius: 12px !important;
}}

/* Discussion Comment Cards */
.comment-card {{
    background-color: {TAG_BG};
    border-left: 3px solid {ACCENT_COLOR};
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
}}
.comment-author {{
    font-weight: 700;
    font-size: 0.85rem;
    color: {TEXT_COLOR};
}}
.comment-time {{
    font-size: 0.72rem;
    color: {TEXT_MUTED};
    margin-left: 6px;
}}
.comment-body {{
    font-size: 0.88rem;
    color: {TEXT_COLOR};
    margin-top: 4px;
    line-height: 1.45;
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

    # Navigation menu
    open_problems_count = len(db.get_sales_problems(status_filter="Open"))
    call_ready_count = len([l for l in db.get_all_leads() if l.get("pipeline_stage") in ["draft_ready", "followup_due"] and l.get("phone_status") != "dead_disconnected"])
    nav_options = [
        ("Today", "⊞", 0),
        ("Sales Terminal", "📊", 0),
        ("Cold Call Desk", "⚡", call_ready_count),
        ("Problem Desk", "🎯", open_problems_count),
        ("Pipeline", "💼", metrics.get("active_opportunities", 0)),
        ("Contacts", "👥", metrics.get("total_leads", 0)),
        ("Follow-ups", "📅", metrics.get("followups_due", 0)),
        ("AI Lead Finder", "🔍", 0),
    ]

    for name, icon, count in nav_options:
        badge_html = f'<span class="badge-count">{count}</span>' if count > 0 and name in ["Follow-ups", "Problem Desk", "Cold Call Desk"] else ""
        is_selected = st.session_state["active_tab"] == name
        btn_label = f"{icon}  {name}"
        if count > 0 and name in ["Follow-ups", "Problem Desk", "Cold Call Desk"]:
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
            new_tag = st.selectbox("Industry Category", STANDARD_CATEGORIES)
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


def get_linkedin_profile_url(contact_name: str, company_name: str, existing_url: str = "") -> str:
    """
    Returns direct LinkedIn URL if present; otherwise creates an optimized Google X-Ray search link
    (site:linkedin.com/in ...) that directly surfaces the prospect's profile without LinkedIn's 'No results found' error.
    """
    if existing_url and "linkedin.com" in existing_url:
        return existing_url
    clean_target = f"{contact_name or ''} {company_name or ''}".strip() or (company_name or "company")
    return f"https://www.google.com/search?q={urllib.parse.quote('site:linkedin.com/in ' + clean_target)}"


def get_linkedin_direct_search_url(contact_name: str, company_name: str) -> str:
    query = f"{contact_name or ''} {company_name or ''}".strip() or (company_name or "company")
    return f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(query)}"


def render_linkedin_research_and_reveal_ui(lead, key_prefix="cc"):
    """
    Renders the 1-click LinkedIn profile/Apollo Reveal button,
    plus an interactive '🤖 AI Find LinkedIn (Gemini Flash)' research button.
    """
    lead_id = lead["id"]
    comp_name = lead.get("company_name", "")
    c_name = lead.get("contact_name") or ""
    c_li = lead.get("contact_linkedin") or ""

    # 1. AI Research button with Gemini Flash
    if st.button("🤖 AI Research LinkedIn (Gemini Flash)", key=f"btn_ai_li_{key_prefix}_{lead_id}", use_container_width=True):
        with st.spinner(f"Gemini Flash is researching decision makers and LinkedIn for {comp_name}..."):
            res = agent_core.research_prospect_linkedin(comp_name, c_name)
        if res.get("linkedin_url"):
            up_dict = {
                "contact_name": res["contact_name"],
                "contact_role": res["contact_role"],
                "contact_linkedin": res["linkedin_url"],
            }
            db.update_lead(lead_id, **up_dict)
            st.success(f"🎉 Identified {res['contact_name']} ({res['contact_role']})!\nLinked: {res['linkedin_url']}")
            st.rerun()
        else:
            st.warning("Could not resolve direct URL automatically. Use Google X-Ray link below.")

    # 2. LinkedIn Open / Reveal Buttons
    if c_li and "linkedin.com" in c_li:
        st.markdown(
            f'<a href="{c_li}" target="_blank" style="display:block; text-align:center; padding:9px 12px; background:#0A66C2; color:white !important; font-family:\'Plus Jakarta Sans\', sans-serif; font-weight:700; font-size:0.86rem; border-radius:7px; text-decoration:none; margin-top:4px; margin-bottom:4px; box-shadow: 0 2px 8px rgba(10,102,194,0.3);">🔗 Open LinkedIn (Apollo Reveal)</a>',
            unsafe_allow_html=True,
        )
    else:
        xray_url = get_linkedin_profile_url(c_name, comp_name, "")
        li_search_url = get_linkedin_direct_search_url(c_name, comp_name)
        st.markdown(
            f'<a href="{xray_url}" target="_blank" style="display:block; text-align:center; padding:8px 11px; background:#1E293B; border:1px solid #0A66C2; color:#38BDF8 !important; font-family:\'Plus Jakarta Sans\', sans-serif; font-weight:700; font-size:0.82rem; border-radius:7px; text-decoration:none; margin-top:4px; margin-bottom:3px;">🌐 Google X-Ray Search (Apollo Reveal)</a>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="text-align:center; font-size:0.75rem; margin-bottom:4px;"><a href="{li_search_url}" target="_blank" style="color:{TEXT_MUTED}; text-decoration:underline;">Or open in LinkedIn search bar</a></div>',
            unsafe_allow_html=True,
        )


def render_hunter_decision_makers_ui(lead, key_prefix="today"):
    """Renders interactive Hunter.io 3-decision-maker finder and selector with auto website resolution."""
    lead_id = lead["id"]
    comp_name = lead.get("company_name", "")
    raw_website = lead.get("company_website") or comp_name

    if st.button("🎯 Find Decision Makers (Hunter.io)", key=f"btn_hdm_{key_prefix}_{lead_id}"):
        with st.spinner(f"Verifying website & querying Hunter.io for {comp_name}..."):
            resolved_url = agent_core.verify_and_resolve_official_website(comp_name, raw_website)
            if resolved_url != raw_website:
                db.update_lead(lead_id, company_website=resolved_url)
            contacts = agent_core.get_top_decision_makers(resolved_url, limit=3)
            if contacts:
                st.session_state[f"dms_{lead_id}"] = {"contacts": contacts, "url": resolved_url}
            else:
                st.warning(f"No verified decision-maker emails found on Hunter.io for {resolved_url}.")

    if f"dms_{lead_id}" in st.session_state:
        dm_state = st.session_state[f"dms_{lead_id}"]
        contacts = dm_state["contacts"]
        resolved_url = dm_state.get("url", raw_website)

        st.markdown(f"<div style='background-color:{CARD_BG}; padding:12px 14px; border-radius:8px; border:1px solid {CARD_BORDER}; margin-top:8px; margin-bottom:8px;'>", unsafe_allow_html=True)
        st.markdown(f"**👥 Decision Makers Found for [{resolved_url}]({resolved_url}):**")

        for idx, dm in enumerate(contacts):
            dm_c1, dm_c2 = st.columns([3, 1.3])
            with dm_c1:
                conf_badge = f"<span style='background:#10b98120; color:#10b981; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:600;'>{dm['confidence']}% verified</span>" if dm.get('confidence', 0) > 50 else ""
                li_snippet = f" · <a href='{dm['linkedin_url']}' target='_blank' style='color:#0A66C2; font-weight:700;'>🔗 LinkedIn</a>" if dm.get("linkedin_url") else ""
                st.markdown(
                    f"**👤 {dm['name']}** — *{dm['position']}* {conf_badge}{li_snippet}<br>"
                    f"<code>{dm['email']}</code>",
                    unsafe_allow_html=True
                )
            with dm_c2:
                if st.button("👉 Select Contact", key=f"apply_dm_{key_prefix}_{lead_id}_{idx}"):
                    up_kwargs = {
                        "company_website": resolved_url,
                        "contact_name": dm["name"],
                        "contact_role": dm["position"],
                        "contact_email": dm["email"],
                    }
                    if dm.get("linkedin_url"):
                        up_kwargs["contact_linkedin"] = dm["linkedin_url"]
                    db.update_lead(lead_id, **up_kwargs)
                    st.success(f"Assigned {dm['name']} ({dm['email']}) as primary contact!")
                    del st.session_state[f"dms_{lead_id}"]
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_sales_problems_ui(key_prefix: str = "today", default_expanded: bool = False):
    """Renders the Sales Team Priority & Problem Desk with High Priority & Normal Priority tracking."""
    problems_open = db.get_sales_problems(status_filter="Open")
    high_count = sum(1 for p in problems_open if p.get("priority") == "High Priority")
    normal_count = sum(1 for p in problems_open if p.get("priority") == "Normal Priority")

    st.markdown(
        clean_html(f"""
        <div class="crm-card" style="padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; border-left: 4px solid #EF4444;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
                <div>
                    <div class="date-eyebrow" style="margin-bottom: 0.25rem;">SALES TEAM BOTTLENECKS & CHALLENGES</div>
                    <div style="font-family:'Playfair Display', serif; font-size:1.35rem; font-weight:600; color:{TEXT_COLOR}; margin-bottom: 0.2rem;">
                        Sales Problem Desk // Priority Tracker
                    </div>
                    <div style="font-size: 0.85rem; color:{TEXT_MUTED};">
                        Sales team logs top-priority roadblocks, objections, and process hurdles that need immediate solving.
                    </div>
                </div>
                <div style="display:flex; gap:8px;">
                    <span style="background:rgba(239, 68, 68, 0.15); color:#EF4444; font-weight:700; font-family:'JetBrains Mono', monospace; padding:4px 10px; border-radius:6px; font-size:0.8rem;">
                        🔴 {high_count} High Priority
                    </span>
                    <span style="background:rgba(245, 158, 11, 0.15); color:#F59E0B; font-weight:700; font-family:'JetBrains Mono', monospace; padding:4px 10px; border-radius:6px; font-size:0.8rem;">
                        🟡 {normal_count} Normal Priority
                    </span>
                </div>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # Log New Problem Form
    with st.expander("➕ **Log a Top-Priority Sales Problem**", expanded=default_expanded):
        with st.form(f"{key_prefix}_prob_form"):
            np_col1, np_col2 = st.columns([3, 1.5])
            with np_col1:
                p_title = st.text_input("Problem / Bottleneck Title", placeholder="e.g. Prospects asking for live 3D pricing before agreeing to meeting")
            with np_col2:
                p_prio = st.radio(
                    "Priority",
                    ["🔴 High Priority", "🟡 Normal Priority"],
                    horizontal=True,
                    help="High Priority = urgent blocker stopping deals/calls. Normal Priority = process or collateral improvement."
                )

            np_c3, np_c4 = st.columns([3, 1.5])
            with np_c3:
                p_desc = st.text_area("Details / Context / What needs to be solved", placeholder="Explain the exact objection, missing collateral, or list quality issue...", height=80)
            with np_c4:
                p_rep = st.text_input("Reported By", value="Sales Rep")

            p_submit = st.form_submit_button("🚨 Submit Problem to Desk", type="primary", use_container_width=True)

        if p_submit and p_title.strip():
            clean_p = "High Priority" if "High" in p_prio else "Normal Priority"
            db.add_sales_problem(
                title=p_title.strip(),
                description=p_desc.strip(),
                priority=clean_p,
                reported_by=p_rep.strip() or "Sales Team",
            )
            st.success("Logged problem successfully!")
            st.rerun()

    # Filter selector
    filter_opts = ["All Open", "🔴 High Priority Only", "🟡 Normal Priority Only", "✅ Resolved Archive"]
    f_prio = st.segmented_control(
        "Priority Filter",
        filter_opts,
        default="All Open",
        key=f"{key_prefix}_filter_prio",
        label_visibility="collapsed",
    ) if hasattr(st, "segmented_control") else st.radio(
        "Priority Filter",
        filter_opts,
        horizontal=True,
        key=f"{key_prefix}_filter_prio",
        label_visibility="collapsed",
    )

    if f_prio == "✅ Resolved Archive":
        items = db.get_sales_problems(status_filter="Resolved")
    elif "High Priority" in f_prio:
        items = db.get_sales_problems(priority_filter="High Priority", status_filter="Open")
    elif "Normal Priority" in f_prio:
        items = db.get_sales_problems(priority_filter="Normal Priority", status_filter="Open")
    else:
        items = db.get_sales_problems(status_filter="Open")

    if not items:
        st.info("No problems recorded in this category. All clear!")
    else:
        for p in items:
            is_high = p.get("priority") == "High Priority"
            border_c = "#EF4444" if is_high else "#F59E0B"
            badge_markup = (
                "<span style='background:rgba(239, 68, 68, 0.15); color:#EF4444; font-weight:700; padding:2px 8px; border-radius:4px; font-size:0.75rem;'>🔴 HIGH PRIORITY</span>"
                if is_high
                else "<span style='background:rgba(245, 158, 11, 0.15); color:#F59E0B; font-weight:700; padding:2px 8px; border-radius:4px; font-size:0.75rem;'>🟡 NORMAL PRIORITY</span>"
            )
            status_markup = (
                f"<span style='background:#10B98120; color:#10B981; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:600;'>{p['status']}</span>"
                if p["status"] == "Resolved"
                else "<span style='background:rgba(59, 130, 246, 0.12); color:#3B82F6; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:600;'>Open</span>"
            )

            st.markdown(
                clean_html(f"""
                <div class="crm-card" style="padding: 1rem 1.25rem; border-left: 4px solid {border_c}; margin-bottom: 0.5rem;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        {badge_markup}
                        {status_markup}
                        <span style="font-size:0.75rem; color:{TEXT_MUTED};">Reported by <b>{p.get('reported_by', 'Sales Team')}</b> · {p.get('created_at', '')[:10]}</span>
                    </div>
                    <div style="font-weight:700; font-size:1.05rem; color:{TEXT_COLOR}; margin-bottom:4px;">
                        {p['title']}
                    </div>
                    <div style="font-size:0.85rem; color:{TEXT_MUTED};">
                        {p.get('description') or 'No additional context provided.'}
                    </div>
                </div>
                """),
                unsafe_allow_html=True,
            )

            act_c1, act_c2, act_c3 = st.columns([1.5, 1.5, 4])
            with act_c1:
                if p["status"] == "Open":
                    if st.button("✅ Mark Resolved", key=f"{key_prefix}_res_{p['id']}", use_container_width=True):
                        db.update_sales_problem_status(p["id"], "Resolved")
                        st.success("Problem marked as Resolved!")
                        st.rerun()
                else:
                    if st.button("🔄 Reopen", key=f"{key_prefix}_reopen_{p['id']}", use_container_width=True):
                        db.update_sales_problem_status(p["id"], "Open")
                        st.rerun()
            with act_c2:
                if st.button("🗑️ Delete", key=f"{key_prefix}_del_{p['id']}", use_container_width=True):
                    db.delete_sales_problem(p["id"])
                    st.rerun()

            # Collaborative Discussion & Solution Thread
            comments = db.get_problem_comments(p["id"])
            comm_count = len(comments)
            exp_label = f"💬 Team Discussion & Solutions ({comm_count})" if comm_count > 0 else "💬 Add Discussion / Proposed Solution"
            with st.expander(exp_label, expanded=(comm_count > 0)):
                if comments:
                    for c in comments:
                        c_auth = c.get("author_name") or "Team Member"
                        c_date = c.get("created_at", "")[:16].replace("T", " ")
                        c_body = c.get("comment_text", "")
                        st.markdown(
                            clean_html(f"""
                            <div class="comment-card">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div>
                                        <span class="comment-author">👤 {c_auth}</span>
                                        <span class="comment-time">· {c_date}</span>
                                    </div>
                                </div>
                                <div class="comment-body">{c_body}</div>
                            </div>
                            """),
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No discussions yet. Share your thoughts, objection rebuttals, or solutions below!")

                # Post a reply form
                with st.form(key=f"rep_form_{key_prefix}_{p['id']}"):
                    f_col1, f_col2 = st.columns([1.3, 3])
                    with f_col1:
                        def_author = st.session_state.get("user_author_name", "Bilal")
                        reply_author = st.text_input("Your Name", value=def_author, key=f"inp_auth_{key_prefix}_{p['id']}", placeholder="e.g. Bilal, Sarah, Rep")
                    with f_col2:
                        reply_body = st.text_area("Your Input / Solution / Playbook", placeholder="Write response or solution here...", key=f"inp_msg_{key_prefix}_{p['id']}", height=68)

                    btn_post = st.form_submit_button("💬 Post Response", type="primary")
                    if btn_post:
                        if reply_body.strip():
                            chosen_name = reply_author.strip() or "Sales Team"
                            st.session_state["user_author_name"] = chosen_name
                            db.add_problem_comment(p["id"], chosen_name, reply_body.strip())
                            st.success(f"Response logged by {chosen_name}!")
                            st.rerun()
                        else:
                            st.warning("Please enter your thoughts or solution before posting.")



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

    # 1. LIVE SALES FLOOR TICKER BANNER AT THE VERY TOP
    team_data_quick = team_analytics.fetch_team_metrics(st.session_state.get("sheet_url", team_analytics.DEFAULT_GOOGLE_SHEET_URL))
    tq = team_data_quick["total"]
    tq_c1, tq_c2 = st.columns([4, 1.2])
    with tq_c1:
        st.markdown(
            clean_html(f"""
            <div class="crm-card" style="padding: 1rem 1.25rem; border-left: 4px solid #10B981; margin-bottom: 1.25rem;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="terminal-pill-green">⚡ SALES FLOOR DESK</span>
                    <span style="font-size:0.75rem; color:{TEXT_MUTED};">Live Sprint Velocity</span>
                </div>
                <div style="font-family:'JetBrains Mono', monospace; font-size:1.1rem; font-weight:700; color:{TEXT_COLOR}; margin-top:4px;">
                    {tq['attempts']:,} Dials &nbsp;·&nbsp; {tq['live_interactions']} Live Calls &nbsp;·&nbsp; <span style="color:#10B981;">{tq['meetings_scheduled']} Meetings Booked</span> &nbsp;·&nbsp; <span style="color:{ACCENT_COLOR};">${tq['pipeline_value']:,.0f} Pipeline</span>
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
    with tq_c2:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if st.button("📊 Open Sales Terminal", key="goto_terminal_btn", use_container_width=True, type="primary"):
            st.session_state["active_tab"] = "Sales Terminal"
            st.rerun()

    # 2. SALES TEAM PROBLEM DESK // PRIORITY TRACKER
    render_sales_problems_ui(key_prefix="today", default_expanded=False)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 3. 4-COLUMN STAT MATRIX CARD
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
                    contact_channels = [f"**Email:** `{lead.get('contact_email') or 'unknown'}`"]
                    if lead.get("contact_phone"):
                        contact_channels.append(f"**Phone:** `{lead.get('contact_phone')}`")
                    if lead.get("company_website"):
                        contact_channels.append(f"**Website:** [{lead.get('company_website')}]({lead.get('company_website')})")
                    st.markdown(" · ".join(contact_channels))

                    render_linkedin_research_and_reveal_ui(lead, key_prefix=f"today_{lead['id']}")

                    render_hunter_decision_makers_ui(lead, key_prefix="today")
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
# VIEW: SALES TERMINAL (Wall Street Outbound Velocity & Google Sheet Sync)
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "Sales Terminal":
    if "sheet_url" not in st.session_state:
        st.session_state["sheet_url"] = team_analytics.DEFAULT_GOOGLE_SHEET_URL

    team_data = team_analytics.fetch_team_metrics(st.session_state["sheet_url"])

    head_c1, head_c2 = st.columns([3, 1.8])
    with head_c1:
        st.markdown('<div class="date-eyebrow">WALL STREET OUTREACH TERMINAL // ELIPSE DESK</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-heading" style="font-size: 2.2rem; margin-bottom: 0.2rem;">Sales Floor Velocity</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">High-frequency outbound dials, live connections, and meeting pipeline generation.</div>', unsafe_allow_html=True)
    with head_c2:
        sync_badge = "🟢 LIVE GOOGLE SHEET SYNC" if team_data.get("is_live") else "🟡 CACHED BASELINE"
        st.markdown(
            clean_html(f"""
            <div style='text-align:right; margin-bottom: 6px;'>
                <span class='terminal-pill-green'>{sync_badge}</span><br>
                <span style='font-size:0.75rem; color:{TEXT_MUTED};'>Updated: {team_data.get('synced_at')}</span>
            </div>
            """),
            unsafe_allow_html=True,
        )
        sync_btn_col1, sync_btn_col2 = st.columns([1, 1])
        with sync_btn_col1:
            if st.button("🔄 Sync Live Sheet", key="refresh_sheet_btn", use_container_width=True):
                st.rerun()
        with sync_btn_col2:
            st.markdown(f'<a href="{st.session_state["sheet_url"]}" target="_blank" style="display:block; text-align:center; padding:7px 10px; background-color:{CARD_BG}; border:1px solid {CARD_BORDER}; color:{TEXT_COLOR}; text-decoration:none; border-radius:8px; font-size:0.85rem; font-weight:600;">↗ Open Sheet</a>', unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Timeframe Horizon Selector
    st.markdown("<div style='font-size:0.78rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:" + TEXT_MUTED + "; margin-bottom:6px;'>⏱️ SELECT SPRINT HORIZON</div>", unsafe_allow_html=True)
    tf_cols = st.columns(4)
    if "terminal_tf" not in st.session_state:
        st.session_state["terminal_tf"] = "total"

    with tf_cols[0]:
        if st.button("📊 3-Week Aggregate", key="tf_total", type="primary" if st.session_state["terminal_tf"] == "total" else "secondary", use_container_width=True):
            st.session_state["terminal_tf"] = "total"
            st.rerun()
    with tf_cols[1]:
        if st.button("📅 Week 3 (Aug 24-28)", key="tf_w3", type="primary" if st.session_state["terminal_tf"] == "week_3" else "secondary", use_container_width=True):
            st.session_state["terminal_tf"] = "week_3"
            st.rerun()
    with tf_cols[2]:
        if st.button("📅 Week 2 (Aug 17-21)", key="tf_w2", type="primary" if st.session_state["terminal_tf"] == "week_2" else "secondary", use_container_width=True):
            st.session_state["terminal_tf"] = "week_2"
            st.rerun()
    with tf_cols[3]:
        if st.button("📅 Week 1 (Aug 12-14)", key="tf_w1", type="primary" if st.session_state["terminal_tf"] == "week_1" else "secondary", use_container_width=True):
            st.session_state["terminal_tf"] = "week_1"
            st.rerun()

    # Active dataset
    if st.session_state["terminal_tf"] == "total":
        active_set = team_data["total"]
    else:
        active_set = next((w for w in team_data["weeks"] if w["week_id"] == st.session_state["terminal_tf"]), team_data["total"])

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    # 5-Column High-Density Wall Street Ticker Matrix
    m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
    with m_c1:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.15rem; margin-bottom: 1rem;">
            <div class="metric-label">OUTREACH ATTEMPTS</div>
            <div class="terminal-ticker" style="color:{TEXT_COLOR};">{active_set['attempts']:,}</div>
            <div class="metric-sub" style="margin-top:4px;"><span class="terminal-pill-amber">{active_set['avg_dials_day']} / day</span> avg pace</div>
            <div style="font-size:0.75rem; color:{TEXT_MUTED}; margin-top:6px;">{active_set.get('companies_worked', 0)} companies worked</div>
        </div>
        """), unsafe_allow_html=True)

    with m_c2:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.15rem; margin-bottom: 1rem;">
            <div class="metric-label">CONTACTS REACHED</div>
            <div class="terminal-ticker" style="color:{TEXT_COLOR};">{active_set['contacts_reached']:,}</div>
            <div class="metric-sub" style="margin-top:4px;"><span class="terminal-pill-blue">{active_set['contact_rate_pct']}%</span> pickup rate</div>
            <div style="font-size:0.75rem; color:{TEXT_MUTED}; margin-top:6px;">{active_set.get('dead_dials', 0)} bad / dead dials</div>
        </div>
        """), unsafe_allow_html=True)

    with m_c3:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.15rem; margin-bottom: 1rem;">
            <div class="metric-label">LIVE CONVERSATIONS</div>
            <div class="terminal-ticker" style="color:{TEXT_COLOR};">{active_set['live_interactions']:,}</div>
            <div class="metric-sub" style="margin-top:4px;"><span class="terminal-pill-green">{active_set['connect_to_conv_pct']}%</span> connect rate</div>
            <div style="font-size:0.75rem; color:{TEXT_MUTED}; margin-top:6px;">Direct decision discussions</div>
        </div>
        """), unsafe_allow_html=True)

    with m_c4:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.15rem; margin-bottom: 1rem;">
            <div class="metric-label">EXPLICIT INTEREST</div>
            <div class="terminal-ticker" style="color:{TEXT_COLOR};">{active_set['explicit_interest']:,}</div>
            <div class="metric-sub" style="margin-top:4px;"><span class="terminal-pill-green">{active_set['interest_rate_pct']}%</span> interest rate</div>
            <div style="font-size:0.75rem; color:{TEXT_MUTED}; margin-top:6px;">{active_set.get('followups', 0)} scheduled follow-ups</div>
        </div>
        """), unsafe_allow_html=True)

    with m_c5:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.15rem; margin-bottom: 1rem; border: 1.5px solid {ACCENT_COLOR};">
            <div class="metric-label">MEETINGS BOOKED</div>
            <div class="terminal-ticker" style="color:{ACCENT_COLOR};">{active_set['meetings_scheduled']}</div>
            <div class="metric-sub" style="margin-top:4px;"><span class="terminal-pill-amber">{active_set['dials_per_meeting']:,.0f} dials</span> / meeting</div>
            <div style="font-size:0.75rem; font-weight:700; color:{TEXT_COLOR}; margin-top:6px;">${active_set['pipeline_value']:,.0f} Pipeline Value</div>
        </div>
        """), unsafe_allow_html=True)

    # 2 Columns: Conversion Funnel & Weekly Velocity Comparison
    f_c1, f_c2 = st.columns([1.4, 1.6])

    with f_c1:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.25rem;">
            <div style="font-family:'Playfair Display', serif; font-size:1.15rem; font-weight:600; color:{TEXT_COLOR}; margin-bottom:0.25rem;">
                Conversion Funnel & Efficiency
            </div>
            <div style="font-size:0.8rem; color:{TEXT_MUTED}; margin-bottom:1rem;">
                Step-by-step conversion drop-off from dial to booked meeting ({active_set['title']}).
            </div>

            <div style="background:{INPUT_BG}; border-left:4px solid {TEXT_MUTED}; padding:10px 14px; border-radius:0 8px 8px 0; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-weight:600; font-size:0.85rem;">1. Outreach Dials Initiated</span>
                    <span style="font-family:'JetBrains Mono', monospace; font-weight:700;">{active_set['attempts']:,}</span>
                </div>
                <div style="font-size:0.75rem; color:{TEXT_MUTED};">Base outbound volume</div>
            </div>

            <div style="background:{INPUT_BG}; border-left:4px solid #3B82F6; padding:10px 14px; border-radius:0 8px 8px 0; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-weight:600; font-size:0.85rem;">2. Contacts Reached</span>
                    <span style="font-family:'JetBrains Mono', monospace; font-weight:700;">{active_set['contacts_reached']:,} ({active_set['contact_rate_pct']}%)</span>
                </div>
                <div style="font-size:0.75rem; color:{TEXT_MUTED};">Pickups vs dead / disconnected numbers</div>
            </div>

            <div style="background:{INPUT_BG}; border-left:4px solid #10B981; padding:10px 14px; border-radius:0 8px 8px 0; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-weight:600; font-size:0.85rem;">3. Live Conversations</span>
                    <span style="font-family:'JetBrains Mono', monospace; font-weight:700;">{active_set['live_interactions']:,} ({active_set['connect_to_conv_pct']}%)</span>
                </div>
                <div style="font-size:0.75rem; color:{TEXT_MUTED};">Actual human sales conversations</div>
            </div>

            <div style="background:{INPUT_BG}; border-left:4px solid #F59E0B; padding:10px 14px; border-radius:0 8px 8px 0; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-weight:600; font-size:0.85rem;">4. Explicit Interest Expressed</span>
                    <span style="font-family:'JetBrains Mono', monospace; font-weight:700;">{active_set['explicit_interest']:,} ({active_set['interest_rate_pct']}%)</span>
                </div>
                <div style="font-size:0.75rem; color:{TEXT_MUTED};">Positive buyer feedback / request for follow-up</div>
            </div>

            <div style="background:{INPUT_BG}; border-left:4px solid {ACCENT_COLOR}; padding:10px 14px; border-radius:0 8px 8px 0;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-weight:700; font-size:0.9rem; color:{ACCENT_COLOR};">5. Qualified Meetings Booked</span>
                    <span style="font-family:'JetBrains Mono', monospace; font-weight:800; font-size:1rem; color:{ACCENT_COLOR};">{active_set['meetings_scheduled']}</span>
                </div>
                <div style="font-size:0.75rem; color:{TEXT_MUTED};">Conversion: 1 booked meeting every {active_set['dials_per_meeting']:,.0f} dials</div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    with f_c2:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.25rem;">
            <div style="font-family:'Playfair Display', serif; font-size:1.15rem; font-weight:600; color:{TEXT_COLOR}; margin-bottom:0.25rem;">
                Weekly Velocity & Sprint Momentum
            </div>
            <div style="font-size:0.8rem; color:{TEXT_MUTED}; margin-bottom:1rem;">
                Sprint-over-sprint tracking across all 3 weeks of team execution.
            </div>
        </div>
        """), unsafe_allow_html=True)

        for w in team_data["weeks"]:
            with st.expander(f"📅 **{w['title']} ({w['dates']})** — {w['attempts']:,} Dials · {w['live_interactions']} Live Calls · **{w['meetings_scheduled']} Meetings**", expanded=(w["week_id"] == "week_3")):
                wc1, wc2, wc3, wc4 = st.columns(4)
                with wc1:
                    st.metric("Dials / Day", f"{w['avg_dials_day']}", f"{w['working_days']} days worked")
                with wc2:
                    st.metric("Live Connects", f"{w['live_interactions']}", f"{w['connect_to_conv_pct']}% of reached")
                with wc3:
                    st.metric("Explicit Interest", f"{w['explicit_interest']}", f"{w['followups']} follow-ups")
                with wc4:
                    st.metric("Meetings Booked", f"{w['meetings_scheduled']}", f"${w['pipeline_value']:,.0f} val")

        # Telephony & Call Outcome Breakdown Card
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding: 1.25rem; margin-top: 1rem;">
            <div style="font-family:'Playfair Display', serif; font-size:1.05rem; font-weight:600; color:{TEXT_COLOR}; margin-bottom:0.25rem;">
                Telephony & Call Friction Analysis
            </div>
            <div style="font-size:0.8rem; color:{TEXT_MUTED}; margin-bottom:0.75rem;">
                Breakdown of where dials landed during this sprint.
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div style="padding:8px 12px; background:{INPUT_BG}; border-radius:6px;">
                    <div style="font-size:0.75rem; color:{TEXT_MUTED};">VOICEMAILS LEFT</div>
                    <div style="font-family:'JetBrains Mono', monospace; font-weight:700; font-size:1.1rem;">{active_set.get('voicemails', 0):,}</div>
                </div>
                <div style="padding:8px 12px; background:{INPUT_BG}; border-radius:6px;">
                    <div style="font-size:0.75rem; color:{TEXT_MUTED};">GATEKEEPERS & RECEPTION</div>
                    <div style="font-family:'JetBrains Mono', monospace; font-weight:700; font-size:1.1rem;">{active_set.get('gatekeeper', 0):,}</div>
                </div>
                <div style="padding:8px 12px; background:{INPUT_BG}; border-radius:6px;">
                    <div style="font-size:0.75rem; color:{TEXT_MUTED};">DEAD DIALS (DISCONNECTED/BAD)</div>
                    <div style="font-family:'JetBrains Mono', monospace; font-weight:700; font-size:1.1rem;">{active_set.get('dead_dials', 0):,}</div>
                </div>
                <div style="padding:8px 12px; background:{INPUT_BG}; border-radius:6px;">
                    <div style="font-size:0.75rem; color:{TEXT_MUTED};">NOT INTERESTED / DNC</div>
                    <div style="font-family:'JetBrains Mono', monospace; font-weight:700; font-size:1.1rem;">{active_set.get('not_interested', 0):,} <span style="font-size:0.7rem; color:#10B981;">(Low 1.5% drop)</span></div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # Google Sheets Connection Settings
    with st.expander("⚙️ **Google Sheets Live Ingestion Settings**"):
        st.markdown(f"**Connected Source Spreadsheet:** [{st.session_state['sheet_url']}]({st.session_state['sheet_url']})")
        new_url = st.text_input("Change Google Sheets URL", value=st.session_state["sheet_url"], key="custom_sheet_url_input")
        if st.button("💾 Save Sheet URL & Re-sync", key="save_sheet_url_btn", type="primary"):
            st.session_state["sheet_url"] = new_url.strip()
            st.success("Updated Google Sheet URL! Synchronizing now...")
            st.rerun()


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# VIEW: COLD CALL DESK (Zero-Research Calling Deck & Battlecard Queue)
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "Cold Call Desk":
    st.markdown('<div class="date-eyebrow">OUTBOUND VELOCITY // ZERO-RESEARCH CALLING DESK</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-heading">Cold Call Battlecard Deck</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">300 daily pre-scrubbed leads with verified direct lines, live on-screen 20-second scripts, and objection rebuttals.</div>', unsafe_allow_html=True)

    # Ingestion Expander: Free AI Discovery, CSV Importer & Apollo API
    with st.expander("📥 **Ingest Daily 300-Lead Batch (Free AI Discovery, CSV Import, or Apollo API)**", expanded=False):
        tab_ai_free, tab_csv, tab_apollo = st.tabs(["🤖 Free AI Web Discovery (No API Key)", "📁 Bulk CSV Drag-and-Drop (Free)", "🚀 Apollo.io Direct API (Paid Plans)"])

        with tab_ai_free:
            st.markdown("Use Gemini Flash live web search + Hunter.io enrichment to discover real commercial businesses, look up decision makers, and generate custom 20-second phone scripts — **100% Free, no Apollo API key required**.")
            free_prompt = st.text_input(
                "Target ICP & Industry Query",
                value="US companies that are B Tier companies doing around 1M to 10M in profits and would be interested in Interactive 3D Configurators",
                key="free_icp_search_query",
            )
            if st.button("🚀 Discover & Generate Calling Battlecards (Free)", key="btn_free_ai_discover", type="primary"):
                with st.spinner("AI is searching Google, verifying official websites, and generating custom cold-call battlecards..."):
                    res = agent_core.run_agent(free_prompt.strip(), log=lambda m: None)
                if res.get("saved", 0) > 0:
                    st.success(f"🎉 Generated and added {res['saved']} qualified call-ready leads with scripts to your Cold Call Desk!")
                    st.rerun()
                elif res.get("error"):
                    st.error(f"⚠️ {res['error']}")
                else:
                    st.info("Found no new companies (or all discovered were already in your database). Try specifying a different niche or state!")

        with tab_apollo:
            st.markdown("Query Apollo.io's B2B database directly for verified decision-maker emails, mobile phone numbers, and LinkedIn URLs.")
            st.info("ℹ️ **Apollo Plan Notice:** Apollo.io blocks direct REST API access on their Free plan (requires Basic $49/mo). If you are on Apollo's free plan, simply do your search on the Apollo.io website, click **'Export to CSV'**, and drop it into the **'Bulk CSV Drag-and-Drop'** tab for free!")
            ap_c1, ap_c2 = st.columns([3, 1.2])
            with ap_c1:
                icp_query = st.text_input(
                    "Target ICP Query",
                    value="Custom golf cart builders and luxury vehicle manufacturers in US with $1M-$20M revenue",
                    key="apollo_icp_query",
                )
            with ap_c2:
                batch_limit = st.slider("Leads to Fetch", min_value=10, max_value=100, value=30, step=10, key="apollo_batch_limit")

            ap_key_input = st.text_input(
                "Apollo.io API Key",
                value=lead_engine.get_apollo_key() or "",
                type="password",
                placeholder="Paste Apollo API key...",
                key="apollo_api_key_input",
                help="Get your key from Apollo.io -> Settings -> API Keys (Requires paid Apollo plan)",
            )

            if st.button("🚀 Fetch & Enrich Batch from Apollo", key="btn_fetch_apollo", type="primary"):
                with st.spinner(f"Querying Apollo for verified executives matching '{icp_query}'..."):
                    result = lead_engine.query_apollo_leads(icp_query, limit=batch_limit, api_key=ap_key_input.strip() or None)

                if not result.get("success"):
                    st.error(f"⚠️ {result.get('error')}")
                else:
                    fetched_leads = result.get("leads", [])
                    st.info(f"Retrieved {len(fetched_leads)} leads from Apollo. Generating AI sales scripts & battlecards...")

                    prog_bar = st.progress(0)
                    def update_prog(cur, tot, name):
                        prog_bar.progress(cur / tot, text=f"Analyzing {name} ({cur}/{tot})...")

                    enriched_leads = lead_engine.synthesize_lead_battlecards(fetched_leads, progress_callback=update_prog)
                    inserted = db.batch_add_leads(enriched_leads)
                    st.success(f"🎉 Successfully added {inserted} verified, call-ready leads to your Cold Call Desk!")
                    st.rerun()

        with tab_csv:
            st.markdown("Drag and drop any CSV export from **Apollo, ZoomInfo, Clay, or LinkedIn Sales Navigator**. The engine auto-detects columns, standardizes phone numbers, and generates custom scripts.")
            uploaded_csv = st.file_uploader("Upload CSV File", type=["csv"], key="csv_lead_uploader")

            if uploaded_csv:
                csv_text = uploaded_csv.getvalue().decode("utf-8", errors="ignore")
                parsed_res = lead_engine.parse_and_enrich_csv(csv_text, max_records=300)

                if not parsed_res.get("success"):
                    st.error(f"⚠️ {parsed_res.get('error')}")
                else:
                    leads_to_add = parsed_res.get("leads", [])
                    st.info(f"Detected {len(leads_to_add)} unique leads in CSV (skipped {parsed_res.get('skipped_duplicates', 0)} duplicates already in CRM).")

                    if st.button(f"⚡ Scrub Phones & Generate Battlecards ({len(leads_to_add)} Leads)", key="btn_process_csv", type="primary"):
                        prog_bar = st.progress(0)
                        def update_csv_prog(cur, tot, name):
                            prog_bar.progress(cur / tot, text=f"Writing 20-second script for {name} ({cur}/{tot})...")

                        enriched = lead_engine.synthesize_lead_battlecards(leads_to_add, progress_callback=update_csv_prog)
                        inserted = db.batch_add_leads(enriched)
                        st.success(f"🎉 Successfully scrubbed and imported {inserted} call-ready leads!")
                        st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Calling Queue Leads
    all_raw_leads = db.get_all_leads()
    call_queue = [
        l for l in all_raw_leads
        if l.get("pipeline_stage") in ["draft_ready", "followup_due"]
        and l.get("phone_status") != "dead_disconnected"
    ]

    # Queue Metrics Bar
    direct_lines = sum(1 for l in call_queue if l.get("phone_status") == "verified_direct" and l.get("contact_phone"))
    queue_val = sum(float(l.get("deal_value") or 15000.0) for l in call_queue)

    qm_c1, qm_c2, qm_c3, qm_c4 = st.columns(4)
    with qm_c1:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding:1rem;">
            <div class="metric-label">CALL-READY QUEUE</div>
            <div class="terminal-ticker" style="color:{TEXT_COLOR}; font-size:1.8rem;">{len(call_queue)}</div>
            <div class="metric-sub">Active leads to dial today</div>
        </div>
        """), unsafe_allow_html=True)

    with qm_c2:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding:1rem;">
            <div class="metric-label">VERIFIED DIRECT LINES</div>
            <div class="terminal-ticker" style="color:#10B981; font-size:1.8rem;">{direct_lines}</div>
            <div class="metric-sub">Direct cell / desk phones</div>
        </div>
        """), unsafe_allow_html=True)

    with qm_c3:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding:1rem;">
            <div class="metric-label">QUEUE PIPELINE VALUE</div>
            <div class="terminal-ticker" style="color:{ACCENT_COLOR}; font-size:1.8rem;">${queue_val:,.0f}</div>
            <div class="metric-sub">Total potential contract value</div>
        </div>
        """), unsafe_allow_html=True)

    with qm_c4:
        st.markdown(clean_html(f"""
        <div class="crm-card" style="padding:1rem;">
            <div class="metric-label">DIALING EFFICIENCY</div>
            <div class="terminal-ticker" style="color:#3B82F6; font-size:1.8rem;">0s</div>
            <div class="metric-sub">Prep time / rep research</div>
        </div>
        """), unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Queue Filtering Pills
    q_cat_counts = {}
    for l in call_queue:
        c = l.get("industry_tag") or "⚡ Tech & Commercial Products"
        q_cat_counts[c] = q_cat_counts.get(c, 0) + 1

    pill_cats = ["All Categories"] + [c for c in STANDARD_CATEGORIES if c in q_cat_counts]
    for c in q_cat_counts:
        if c not in pill_cats:
            pill_cats.append(c)

    selected_q_cat = st.pills(
        "Queue Category",
        pill_cats,
        default="All Categories",
        format_func=lambda c: f"🌐 All Sectors ({len(call_queue)})" if c == "All Categories" else f"{c} ({q_cat_counts.get(c, 0)})",
        key="cold_call_cat_pill",
        label_visibility="collapsed",
    )
    if not selected_q_cat:
        selected_q_cat = "All Categories"

    filtered_queue = [l for l in call_queue if l.get("industry_tag") == selected_q_cat] if selected_q_cat != "All Categories" else call_queue

    if search_query:
        sq = search_query.lower()
        filtered_queue = [
            l for l in filtered_queue
            if sq in l.get("company_name", "").lower()
            or sq in l.get("contact_name", "").lower()
            or sq in l.get("contact_phone", "").lower()
        ]

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if not filtered_queue:
        st.info("🎯 **No leads in this queue!** Use the batch ingestion drawer above to pull verified leads from Apollo or drop a CSV file.")
    else:
        for idx, lead in enumerate(filtered_queue):
            lead_id = lead["id"]
            comp_name = lead["company_name"]
            c_name = lead.get("contact_name") or "Decision Maker"
            c_role = lead.get("contact_role") or "Owner"
            c_phone = lead.get("contact_phone") or ""
            phone_stat = lead.get("phone_status") or "verified_direct"
            c_email = lead.get("contact_email") or ""
            c_li = lead.get("contact_linkedin") or ""
            deal_val = float(lead.get("deal_value") or 15000.0)
            tag = lead.get("industry_tag") or "⚡ Tech & Commercial Products"

            # Check if phone_script exists; if missing, synthesize fallback
            script = lead.get("phone_script")
            if not script or len(script) < 15:
                script = (
                    f"Hi {c_name.split()[0]}, Bilal with Elipse Studio. I was looking at {comp_name}'s custom collection online, "
                    f"and noticed your buyers browse static photos rather than customizing finishes live in 3D. "
                    f"We build interactive real-time 3D web configurators that let clients customize options live on your site before buying. "
                    f"Would you be open to a 3-minute visual concept tailored for {comp_name} this Thursday?"
                )

            objection_text = lead.get("objection_notes")
            if not objection_text or len(objection_text) < 15:
                objection_text = (
                    "**- 'We already have photos on our site':**\\n"
                    "Photos show what you already built; an interactive 3D builder lets high-ticket buyers customize what they want to buy today.\\n\\n"
                    "**- 'Just send me an email with information':**\\n"
                    "I'll send that over to your direct inbox right now. Are you at your screen Thursday at 2 PM to see a 3-minute live preview?\\n\\n"
                    "**- 'We are too busy / call back in 6 months':**\\n"
                    "Completely understand. Our 3D models integrate directly into your site in under 2 weeks without eating up your team's time."
                )

            # Phone Status Badge
            if phone_stat == "verified_direct" and c_phone:
                phone_badge = '<span class="terminal-pill-green">🟢 Verified Direct Line</span>'
                card_border_color = "#10B981"
            elif phone_stat == "switchboard":
                phone_badge = '<span class="terminal-pill-amber">🟡 Switchboard</span>'
                card_border_color = "#F59E0B"
            else:
                phone_badge = '<span style="background:rgba(239,68,68,0.12); color:#EF4444; font-size:0.72rem; font-weight:700; padding:3px 8px; border-radius:4px;">⚪ Needs Direct Line</span>'
                card_border_color = CARD_BORDER

            with st.container(border=True):
                # Header row
                st.markdown(clean_html(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid {CARD_BORDER};">
                    <div>
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <span style="font-family:'Playfair Display', serif; font-size:1.35rem; font-weight:700; color:{TEXT_COLOR};">{comp_name}</span>
                            <span style="font-family:'JetBrains Mono', monospace; font-size:0.85rem; font-weight:700; color:{ACCENT_COLOR}; background:{TAG_BG}; padding:2px 8px; border-radius:4px;">${deal_val:,.0f}</span>
                            {phone_badge}
                            <span style="font-size:0.75rem; color:{TEXT_MUTED}; background:{INPUT_BG}; border:1px solid {CARD_BORDER}; padding:2px 8px; border-radius:4px;">{tag}</span>
                        </div>
                        <div style="font-size:0.9rem; color:{TEXT_COLOR}; margin-top:4px;">
                            👤 <b>{c_name}</b> · <span style="color:{TEXT_MUTED};">{c_role}</span>
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)

                # Two Columns: Channel/Dialer & On-Screen Script
                col_dialer, col_battlecard = st.columns([1.2, 2.0], gap="medium")

                with col_dialer:
                    st.markdown("##### 📞 Direct Outbound Line")
                    if c_phone:
                        st.markdown(
                            f'<a href="tel:{c_phone}" style="display:block; text-align:center; padding:11px 14px; background:#10B981; color:white; font-family:monospace; font-weight:700; font-size:1.15rem; border-radius:8px; text-decoration:none; margin-bottom:8px; box-shadow: 0 2px 8px rgba(16,185,129,0.25);">📞 Call {c_phone}</a>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.warning("No phone on file.")

                    # LinkedIn Research & Apollo Phone Reveal
                    render_linkedin_research_and_reveal_ui(lead, key_prefix=f"cc_{lead_id}")

                    # Quick Phone & LinkedIn Profile Editor (collapsed by default)
                    with st.expander("✏️ Edit Phone / LinkedIn", expanded=False):
                        edit_ph = st.text_input("Direct Phone", value=c_phone, key=f"quick_p_{lead_id}", placeholder="+1 (555) 000-0000")
                        edit_li = st.text_input("LinkedIn Profile URL", value=c_li, key=f"quick_li_{lead_id}", placeholder="https://www.linkedin.com/in/...")
                        if st.button("💾 Save Contact Info", key=f"save_ci_{lead_id}"):
                            scrub = lead_engine.scrub_and_format_phone(edit_ph) if edit_ph else {"phone": "", "status": "needs_enrichment"}
                            db.update_lead(
                                lead_id,
                                contact_phone=scrub["phone"],
                                phone_status=scrub["status"] if edit_ph else "needs_enrichment",
                                contact_linkedin=edit_li.strip(),
                            )
                            st.success("Updated contact info!")
                            st.rerun()

                    # Quick Links
                    st.markdown("##### 🌐 Research & Channels")
                    ch_links = []
                    if lead.get("company_website"):
                        ch_links.append(f"[↗ Website]({lead['company_website']})")
                    if c_email and c_email != "unknown":
                        ch_links.append(f"[✉️ {c_email}](mailto:{c_email})")
                    if c_li:
                        ch_links.append(f"[🔗 LinkedIn]({c_li})")
                    else:
                        xray_url = get_linkedin_profile_url(c_name, comp_name, "")
                        ch_links.append(f"[🔗 Search LinkedIn]({xray_url})")

                    if ch_links:
                        st.markdown(" · ".join(ch_links))

                    render_hunter_decision_makers_ui(lead, key_prefix="cc_desk")

                    # How We Can Help Box
                    st.markdown(clean_html(f"""
                    <div style="background:{INPUT_BG}; border-left:3px solid {ACCENT_COLOR}; padding:8px 12px; border-radius:0 6px 6px 0; font-size:0.8rem; color:{TEXT_MUTED}; margin-top:8px;">
                        <strong style="color:{TEXT_COLOR};">Why Elipse Studio Helps:</strong><br>
                        {lead.get('reason') or 'High-ticket custom catalog converts higher with real-time 3D web builder.'}
                    </div>
                    """), unsafe_allow_html=True)

                with col_battlecard:
                    st.markdown("##### 🎯 Live 20-Second Phone Script (Read Verbatim)")
                    st.markdown(clean_html(f"""
                    <div style="background:{TAG_BG}; border:1.5px solid {ACCENT_COLOR}; padding:14px 16px; border-radius:8px; font-size:0.95rem; line-height:1.55; color:{TEXT_COLOR}; margin-bottom:12px; font-family:'Plus Jakarta Sans', sans-serif;">
                        "{script}"
                    </div>
                    """), unsafe_allow_html=True)

                    with st.expander("🛡️ **Live Objection Matrix & Rebuttals**", expanded=False):
                        st.markdown(objection_text)

                    # Quick Rep Notes
                    rep_call_note = st.text_input("Call Notes / Follow-up Details", placeholder="Spoke with receptionist, Hal returns at 3 PM...", key=f"cnote_{lead_id}")

                    # 1-Click Speed Dispositions Bar
                    st.markdown("<div style='font-size:0.75rem; font-weight:700; color:" + TEXT_MUTED + "; text-transform:uppercase; margin-bottom:6px; margin-top:8px;'>⚡ 1-Click Call Outcome Dispositions</div>", unsafe_allow_html=True)
                    disp_cols = st.columns(5)

                    with disp_cols[0]:
                        if st.button("🔴 Dead Line", key=f"btn_dead_{lead_id}", help="Number is disconnected or bad. Removes from queue.", use_container_width=True):
                            db.update_lead_call_outcome(lead_id, "dead_number", rep_call_note)
                            st.warning(f"Marked {comp_name} as Dead Line.")
                            st.rerun()

                    with disp_cols[1]:
                        if st.button("🟡 Voicemail", key=f"btn_vm_{lead_id}", help="Left pitch voicemail. Keeps in Follow-up queue.", use_container_width=True):
                            db.update_lead_call_outcome(lead_id, "voicemail", rep_call_note)
                            st.info("Logged Voicemail.")
                            st.rerun()

                    with disp_cols[2]:
                        if st.button("💬 No Interest", key=f"btn_dnc_{lead_id}", help="Spoke with decision maker, not interested.", use_container_width=True):
                            db.update_lead_call_outcome(lead_id, "not_interested", rep_call_note)
                            st.info("Moved to Closed Lost.")
                            st.rerun()

                    with disp_cols[3]:
                        if st.button("⏳ Callback", key=f"btn_cb_{lead_id}", help="Asked to call back later.", use_container_width=True):
                            db.update_lead_call_outcome(lead_id, "callback_scheduled", rep_call_note)
                            st.info("Logged Callback.")
                            st.rerun()

                    with disp_cols[4]:
                        if st.button("🎯 Booked!", key=f"btn_book_{lead_id}", type="primary", help=f"Qualified Meeting Booked! Advances to Pipeline stage.", use_container_width=True):
                            db.update_lead_call_outcome(lead_id, "meeting_booked", rep_call_note)
                            st.balloons()
                            st.success(f"🎉 BOOM! Meeting booked for {comp_name} (${deal_val:,.0f})!")
                            st.rerun()




# VIEW: PROBLEM DESK (Full-page Priority Manager)
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "Problem Desk":
    st.markdown('<div class="date-eyebrow">SALES OPERATIONS & STRATEGY</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-heading">Sales Problem Desk</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Prioritize and resolve the top blockers faced by your outreach team.</div>', unsafe_allow_html=True)
    render_sales_problems_ui(key_prefix="full_desk", default_expanded=True)


# ---------------------------------------------------------------------------
# VIEW 2: PIPELINE (Deal Stage Columns)
# ---------------------------------------------------------------------------
elif st.session_state["active_tab"] == "Pipeline":
    st.markdown('<div class="hero-heading">Studio Pipeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Track and progress accounts through your sales stages and industry sectors.</div>', unsafe_allow_html=True)

    col_stg, col_cat = st.columns([1, 1])
    with col_stg:
        filter_stage = st.selectbox(
            "Stage Filter",
            ["all"] + [s[0] for s in db.PIPELINE_STAGES],
            format_func=lambda s: "All Pipeline Stages" if s == "all" else db.STAGE_LABELS.get(s, s),
        )
    with col_cat:
        filter_cat = st.selectbox(
            "Category Filter",
            ["All Categories"] + STANDARD_CATEGORIES,
        )

    leads = db.get_all_leads(stage_filter=filter_stage, search_query=search_query, category_filter=filter_cat)

    if not leads:
        st.info("No leads found for this filter combination. Try selecting 'All Categories' or use 'AI Lead Finder'.")
    else:
        for lead in leads:
            val = f"${lead.get('deal_value', 15000):,.0f}"
            stage_name = db.STAGE_LABELS.get(lead.get("pipeline_stage"), "Draft Ready")
            cat_label = lead.get('industry_tag') or "⚡ Tech & Commercial Products"
            
            with st.expander(f"💼 **{lead['company_name']}** — {val} · {cat_label} ({stage_name})"):
                c1, c2, c3 = st.columns([2, 2, 1.5])

                with c1:
                    st.markdown("#### 🏢 Company & Contact")
                    st.markdown(f"**Website:** [{lead.get('company_website')}]({lead.get('company_website')})")
                    st.markdown(f"**Contact:** {lead.get('contact_name') or 'N/A'} ({lead.get('contact_role') or 'Unknown'})")
                    st.markdown(f"**Email:** `{lead.get('contact_email') or 'unknown'}`")
                    p_phone = lead.get("contact_phone") or ""
                    if p_phone:
                        st.markdown(f"**Direct Phone:** `{p_phone}`")

                    render_linkedin_research_and_reveal_ui(lead, key_prefix=f"pipe_{lead['id']}")

                    render_hunter_decision_makers_ui(lead, key_prefix="pipe")
                    st.markdown(f"**Category:** `{cat_label}`")
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
                    new_p_phone = st.text_input("Direct Phone", value=lead.get("contact_phone") or "", key=f"p_ph_{lead['id']}")
                    new_p_li = st.text_input("LinkedIn URL", value=lead.get("contact_linkedin") or "", placeholder="https://www.linkedin.com/in/...", key=f"p_li_{lead['id']}")

                    if st.button("💾 Save Updates", key=f"save_p_{lead['id']}", type="primary"):
                        db.update_lead(
                            lead["id"],
                            subject=new_subj,
                            body=new_b,
                            deal_value=new_val,
                            pipeline_stage=new_stage,
                            contact_phone=new_p_phone.strip(),
                            contact_linkedin=new_p_li.strip(),
                        )
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
    st.markdown('<div class="date-eyebrow">DIRECTORY & SEGMENTATION</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-heading">Contacts & Accounts</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Segmented client directory by target industry sector with real-time deal management.</div>', unsafe_allow_html=True)

    all_leads = db.get_all_leads(search_query=search_query)

    # Calculate dynamic category counts
    cat_counts = {}
    for l in all_leads:
        cat = l.get("industry_tag") or "⚡ Tech & Commercial Products"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # Standard categories first, then any extra categories present in DB
    available_cats = [c for c in STANDARD_CATEGORIES if c in cat_counts]
    for c in cat_counts:
        if c not in available_cats:
            available_cats.append(c)

    pill_choices = ["All Categories"] + available_cats

    if "contact_selected_cat" not in st.session_state:
        st.session_state["contact_selected_cat"] = "All Categories"
    if st.session_state["contact_selected_cat"] not in pill_choices:
        st.session_state["contact_selected_cat"] = "All Categories"

    st.markdown("<div style='margin-bottom:6px; font-size:0.75rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; color:" + TEXT_MUTED + ";'>🏷️ BROWSE LEADS BY CATEGORY</div>", unsafe_allow_html=True)

    active_cat = st.pills(
        "Filter by Industry Category",
        pill_choices,
        default=st.session_state["contact_selected_cat"],
        format_func=lambda c: f"🌐 All Leads ({len(all_leads)})" if c == "All Categories" else f"{c} ({cat_counts.get(c, 0)})",
        key="contact_cat_pill_selector",
        label_visibility="collapsed",
    )
    if not active_cat:
        active_cat = "All Categories"
    st.session_state["contact_selected_cat"] = active_cat

    # Filter leads by selected category
    if active_cat != "All Categories":
        leads = [l for l in all_leads if l.get("industry_tag") == active_cat]
    else:
        leads = all_leads

    # Executive Category Overview Card
    cat_total_val = sum(float(l.get("deal_value") or 0) for l in leads)
    cat_lead_count = len(leads)
    draft_count = sum(1 for l in leads if l.get("pipeline_stage") == "draft_ready")
    contacted_count = sum(1 for l in leads if l.get("pipeline_stage") in ["contacted", "followup_due"])
    meeting_count = sum(1 for l in leads if l.get("pipeline_stage") in ["meeting_booked", "proposal_sent", "won"])

    st.markdown(
        clean_html(f"""
        <div class="crm-card" style="padding: 1.15rem 1.4rem; margin-top: 0.5rem; margin-bottom: 1.25rem; border-left: 4px solid {ACCENT_COLOR};">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div class="date-eyebrow" style="margin-bottom:0.15rem;">ACTIVE SECTOR OVERVIEW</div>
                    <div style="font-family:'Playfair Display', serif; font-size:1.3rem; font-weight:600; color:{TEXT_COLOR};">
                        {active_cat if active_cat != 'All Categories' else '🌐 All Industry Sectors'}
                    </div>
                    <div style="font-size:0.85rem; color:{TEXT_MUTED}; margin-top:2px;">
                        Showing <b>{cat_lead_count}</b> account{'s' if cat_lead_count != 1 else ''} · <b>${cat_total_val:,.0f}</b> combined pipeline value
                    </div>
                </div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    <span class="terminal-pill-blue" style="font-size:0.78rem;">📝 {draft_count} Draft Ready</span>
                    <span class="terminal-pill-amber" style="font-size:0.78rem;">📤 {contacted_count} Outreach / Due</span>
                    <span class="terminal-pill-green" style="font-size:0.78rem;">🎯 {meeting_count} Booked / Pipeline</span>
                </div>
            </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # CSV Export
    if leads:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Company", "Website", "Contact Name", "Role", "Email", "Phone", "LinkedIn", "Industry Tag", "Deal Value", "Stage", "Notes", "Created At"])
        for l in leads:
            writer.writerow([
                l["id"], l["company_name"], l["company_website"], l.get("contact_name", ""),
                l.get("contact_role", ""), l["contact_email"], l.get("contact_phone", ""),
                l.get("contact_linkedin", ""),
                l.get("industry_tag", ""), l.get("deal_value", ""), l.get("pipeline_stage", ""),
                l.get("notes", ""), l["created_at"]
            ])

        st.download_button(
            label=f"📥 Export {len(leads)} Filtered Contact{'s' if len(leads) != 1 else ''} to CSV",
            data=output.getvalue(),
            file_name=f"elipse_{active_cat.replace(' ', '_').lower()}_contacts.csv",
            mime="text/csv",
        )

    if not leads:
        st.info(f"No leads found under '{active_cat}'. Use 'AI Lead Finder' or 'Add a Lead' to discover companies for this category.")
    else:
        for lead in leads:
            stage_name = db.STAGE_LABELS.get(lead.get("pipeline_stage"), "Draft Ready")
            cat_tag = lead.get("industry_tag") or "⚡ Tech & Commercial Products"
            val = f"${lead.get('deal_value', 15000):,.0f}"

            with st.expander(f"👤 **{lead.get('contact_name') or lead['company_name']}** · **{lead['company_name']}** — {val} · {cat_tag} ({stage_name})"):
                c1, c2, c3 = st.columns([1.8, 1.8, 1.4])
                with c1:
                    st.markdown("#### 🏢 Company & Contact")
                    st.markdown(f"**Company:** [{lead['company_name']}]({lead.get('company_website')})")
                    st.markdown(f"**Contact:** `{lead.get('contact_name') or 'N/A'}`")
                    st.markdown(f"**Role:** *{lead.get('contact_role') or 'Unknown'}*")
                    st.markdown(f"**Email:** `{lead['contact_email']}`")
                    c_phone = lead.get("contact_phone") or ""
                    if c_phone:
                        st.markdown(f"**Direct Phone:** `{c_phone}`")

                    render_linkedin_research_and_reveal_ui(lead, key_prefix=f"cnt_{lead['id']}")

                    render_hunter_decision_makers_ui(lead, key_prefix="contacts")
                    if lead.get("reason"):
                        st.markdown(f"**Sales Angle:** {lead.get('reason')}")

                with c2:
                    st.markdown("#### 🏷️ Classification & Deal")
                    cur_cat = lead.get("industry_tag") or "⚡ Tech & Commercial Products"
                    cat_idx = STANDARD_CATEGORIES.index(cur_cat) if cur_cat in STANDARD_CATEGORIES else 0
                    new_cat = st.selectbox(
                        "Category Sector",
                        STANDARD_CATEGORIES,
                        index=cat_idx,
                        key=f"c_cat_{lead['id']}"
                    )
                    
                    cur_stg_idx = [s[0] for s in db.PIPELINE_STAGES].index(lead.get("pipeline_stage", "draft_ready"))
                    new_stg = st.selectbox(
                        "Pipeline Stage",
                        [s[0] for s in db.PIPELINE_STAGES],
                        index=cur_stg_idx,
                        key=f"c_stg_{lead['id']}",
                        format_func=lambda s: db.STAGE_LABELS.get(s, s)
                    )
                    new_phone = st.text_input("Direct Phone", lead.get("contact_phone") or "", key=f"c_ph_{lead['id']}")
                    new_linkedin = st.text_input("LinkedIn Profile URL", lead.get("contact_linkedin") or "", placeholder="https://www.linkedin.com/in/...", key=f"c_li_{lead['id']}")
                    new_val = st.number_input("Deal Value ($)", value=float(lead.get("deal_value") or 15000.0), step=1000.0, key=f"c_val_{lead['id']}")

                    if st.button("💾 Save Lead Details", key=f"save_lead_c_{lead['id']}", type="primary"):
                        db.update_lead(
                            lead["id"],
                            industry_tag=new_cat,
                            pipeline_stage=new_stg,
                            contact_phone=new_phone.strip(),
                            contact_linkedin=new_linkedin.strip(),
                            deal_value=new_val
                        )
                        st.success("Lead details updated!")
                        st.rerun()

                with c3:
                    st.markdown("#### 📝 Notes & Actions")
                    notes = st.text_area("Relationship Notes", lead.get("notes") or "", height=95, key=f"notes_{lead['id']}", placeholder="Log call notes, objections...")
                    if st.button("💾 Save Notes", key=f"savenotes_{lead['id']}"):
                        db.update_lead(lead["id"], notes=notes)
                        st.success("Notes saved!")
                        st.rerun()

                    # Direct Mailto
                    email_target = lead["contact_email"]
                    if email_target and email_target != "unknown" and "@" in email_target:
                        encoded_subj = urllib.parse.quote(lead.get("subject", f"Question regarding {lead['company_name']}"))
                        encoded_body = urllib.parse.quote(lead.get("body", ""))
                        mailto_url = f"mailto:{email_target}?subject={encoded_subj}&body={encoded_body}"
                        st.markdown(f'<a href="{mailto_url}" target="_blank" style="display:block; text-align:center; padding:6px 12px; background-color:{ACCENT_COLOR}; color:white; text-decoration:none; border-radius:6px; font-weight:600; margin-top:8px;">📧 Open in Email App</a>', unsafe_allow_html=True)


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
        del st.session_state["finder_search_msg"]

    if "finder_search_skip" in st.session_state:
        st.info(st.session_state["finder_search_skip"])
        del st.session_state["finder_search_skip"]

    if "finder_search_error" in st.session_state:
        err = str(st.session_state["finder_search_error"])
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            st.warning(
                "⚠️ **Google Gemini API Daily Quota Limit (Free Sandbox Tier):**\n\n"
                "Your API key reached Google AI Studio's free cap of 20 requests/day for this project.\n\n"
                "**How to unlock unlimited searches:**\n"
                "1. Go to [aistudio.google.com](https://aistudio.google.com/) and click **'Set up billing'** on your project, OR\n"
                "2. Click **'Create API key in new project'** in Google AI Studio and paste the new key into your Streamlit Secrets."
            )
        else:
            st.error(f"⚠️ {err}")
        del st.session_state["finder_search_error"]
