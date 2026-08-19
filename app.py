"""
app.py — Elipse Studio Outreach Agent Dashboard.
Run with: streamlit run app.py
"""

import os
import io
import csv
import urllib.parse
from dotenv import load_dotenv
import streamlit as st

import db
import agent_core

load_dotenv()

# Automatically bridge Streamlit Cloud secrets to environment variables if present
try:
    if hasattr(st, "secrets"):
        for key, val in st.secrets.items():
            if isinstance(val, str) and not os.environ.get(key):
                os.environ[key] = val
except Exception:
    pass

st.set_page_config(
    page_title="Elipse Outreach Agent",
    page_icon="🎯",
    layout="wide",
)

db.init_db()

# ---------------------------------------------------------------------------
# Sidebar: Settings & Key status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Configuration")
    
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        st.success("✅ Google Gemini API: Connected")
    else:
        st.error("❌ Google Gemini API: Missing in .env")

    hunter_key = os.environ.get("HUNTER_API_KEY")
    if hunter_key:
        st.success("✅ Hunter.io: Connected")
    else:
        st.info("ℹ️ Hunter.io: Optional (Add `HUNTER_API_KEY` in `.env` for verified decision-maker emails)")

    cal_link = os.environ.get("CALENDAR_LINK", "https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting")
    st.caption(f"📅 **Calendar Link:**\n`{cal_link}`")
    
    st.divider()
    st.markdown("### 🚀 Deployment Tips")
    st.markdown(
        "To deploy this app to the cloud:\n"
        "1. Push this repository to **GitHub**.\n"
        "2. Connect your repo to **Streamlit Community Cloud** (Free) or **Render**.\n"
        "3. Add your `GEMINI_API_KEY` in the cloud environment settings."
    )

# ---------------------------------------------------------------------------
# Main Header & Metrics
# ---------------------------------------------------------------------------
st.title("🎯 Elipse Studio — Outreach Agent")
st.caption("AI-powered research & cold outreach pipeline tailored for 3D Web Configurators & CGI visualization.")

stats = db.get_stats()
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Leads", stats.get("total", 0))
m2.metric("🆕 New", stats.get("new", 0))
m3.metric("✅ Approved", stats.get("approved", 0))
m4.metric("📤 Sent", stats.get("sent", 0))
m5.metric("❌ Rejected", stats.get("rejected", 0))

st.divider()

# ---------------------------------------------------------------------------
# Lead Generation Form
# ---------------------------------------------------------------------------
with st.form("generate_form"):
    st.subheader("🔍 Find & Draft New Leads")
    prompt = st.text_input(
        "Describe your target companies & niche:",
        placeholder="e.g. Find 5 luxury bespoke furniture or kitchen cabinet manufacturers in UAE without a 3D configurator",
    )
    submitted = st.form_submit_button("🚀 Research & Draft Leads", type="primary")

if submitted and prompt.strip():
    log_area = st.empty()
    log_lines = []

    def log(msg):
        log_lines.append(msg)
        log_area.markdown("\n\n".join([f"`{line}`" for line in log_lines]))

    with st.spinner("AI Agent is searching live web, identifying targets, and drafting emails..."):
        result = agent_core.run_agent(prompt.strip(), log=log)

    st.success(f"🎉 Done! Generated and saved {result['saved']} new lead(s).")
    if result["skipped_duplicates"]:
        st.info(f"Skipped existing leads: {', '.join(result['skipped_duplicates'])}")
    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Lead Dashboard & Filtering
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.subheader("📋 Lead Pipeline")
with col2:
    status_filter = st.selectbox(
        "Filter by status",
        ["all", "new", "approved", "sent", "rejected"],
        label_visibility="collapsed",
    )

leads = db.get_all_leads(status_filter)

with col3:
    if leads:
        # Prepare CSV export
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Company", "Website", "Email", "Status", "Subject", "Body", "Reason", "Created At"])
        for l in leads:
            writer.writerow([l["id"], l["company_name"], l["company_website"], l["contact_email"], l["status"], l["subject"], l["body"], l["reason"], l["created_at"]])
        
        st.download_button(
            label="📥 Export CSV",
            data=output.getvalue(),
            file_name=f"leads_{status_filter}.csv",
            mime="text/csv",
        )

if not leads:
    st.info("No leads found for this filter. Use the prompt box above to generate some!")
else:
    status_emoji = {"new": "🆕", "approved": "✅", "rejected": "❌", "sent": "📤"}

    for lead in leads:
        emoji = status_emoji.get(lead["status"], "•")
        header = f"{emoji} **{lead['company_name']}** — {lead['subject']}"

        with st.expander(header, expanded=(lead["status"] == "new")):
            meta_col1, meta_col2 = st.columns([2, 1])
            with meta_col1:
                st.markdown(f"**🌐 Website:** [{lead['company_website']}]({lead['company_website']})")
                st.markdown(f"**✉️ Contact Email:** `{lead['contact_email'] or 'unknown'}`")
                st.markdown(f"**💡 Angle / Fit Reason:** {lead['reason']}")
            with meta_col2:
                st.markdown(f"**Status:** `{lead['status'].upper()}`")
                st.markdown(f"**Created:** {lead['created_at']}")
                st.markdown(f"**Prompt Source:** *{lead.get('source_prompt', 'N/A')}*")

            st.markdown("#### ✏️ Email Draft Review")
            new_subject = st.text_input("Subject", value=lead["subject"], key=f"subj_{lead['id']}")
            new_body = st.text_area("Body", value=lead["body"], height=180, key=f"body_{lead['id']}")

            btn_c1, btn_c2, btn_c3, btn_c4, btn_c5 = st.columns(5)

            if btn_c1.button("💾 Save Edits", key=f"save_{lead['id']}"):
                db.update_lead(lead["id"], subject=new_subject, body=new_body)
                st.success("Saved!")
                st.rerun()

            if btn_c2.button("✅ Approve", key=f"approve_{lead['id']}"):
                db.update_lead(lead["id"], status="approved", subject=new_subject, body=new_body)
                st.rerun()

            if btn_c3.button("❌ Reject", key=f"reject_{lead['id']}"):
                db.update_lead(lead["id"], status="rejected")
                st.rerun()

            if lead["status"] in ["approved", "new"]:
                if btn_c4.button("📤 Mark as Sent", key=f"sent_{lead['id']}"):
                    db.update_lead(lead["id"], status="sent", subject=new_subject, body=new_body)
                    st.rerun()

            if btn_c5.button("🗑️ Delete", key=f"del_{lead['id']}"):
                db.delete_lead(lead["id"])
                st.rerun()

            # Direct Mailto Link if contact email is valid
            email_target = lead["contact_email"]
            if email_target and email_target != "unknown" and "@" in email_target:
                encoded_subj = urllib.parse.quote(new_subject)
                encoded_body = urllib.parse.quote(new_body)
                mailto_url = f"mailto:{email_target}?subject={encoded_subj}&body={encoded_body}"
                st.markdown(f'<a href="{mailto_url}" target="_blank" style="display:inline-block;padding:6px 12px;background-color:#0088cc;color:white;text-decoration:none;border-radius:4px;font-weight:bold;margin-top:8px;">📧 Open in Email App (1-Click)</a>', unsafe_allow_html=True)
