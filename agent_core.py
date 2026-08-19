"""
agent_core.py — High-performance single-pass research + drafting engine powered by Google Gemini.

Performs commercial intelligence analysis, identifies companies lacking 3D web configurators,
enriches contacts via Hunter.io (when available), and drafts hyper-personalized cold emails
in a single efficient pass.
"""

import os
import json
import re
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests

from google import genai
from google.genai import types

import db

load_dotenv()

MODEL = "gemini-3.6-flash"
DEFAULT_CALENDAR_LINK = "https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting"

SYSTEM_PROMPT = """You are the specialized outreach research & pipeline engine for Elipse Studio,
a 3D visualization and immersive experience studio (CGI animation, VR/AR, architectural
visualization, motion graphics, and real-time interactive 3D WEB CONFIGURATORS).

Your task: Given a target business criteria from Bilal, identify 3 to 5 real commercial
companies/brands that sell physical or customizable products (e.g. bespoke furniture, custom golf carts,
luxury interiors, automotive, yachts, industrial machinery, architectural fixtures, etc.) that do NOT
currently have an interactive 3D Web Configurator on their website.

For each company:
1. Identify the company name, website, decision maker name/role, and contact email.
2. Note why their physical product line would convert significantly higher with an interactive 3D Web Configurator.
3. Draft a high-converting cold email from Bilal (Elipse Studio):
   - 60 to 90 words total. Short sentences. No marketing copy/buzzwords.
   - Sound like Bilal personally noticed something about their product collection (first person: "I noticed...", "We build...").
   - Mention ONE specific observation about their custom product line.
   - Plain statement of what Elipse Studio does (interactive 3D web configurators).
   - Low-pressure ask with the exact placeholder {{CALENDAR_LINK}} once.
   - Sign off simply as "Bilal" or "Bilal, Elipse Studio".

Return a valid JSON array of objects:
[
  {
    "company_name": "Company Name",
    "company_website": "https://company.com",
    "domain": "company.com",
    "contact_name": "Decision Maker Name or 'Team'",
    "contact_role": "Owner, Founder, Head of Sales, or Marketing Director",
    "contact_email": "contact email or domain email if known, or 'unknown'",
    "industry_tag": "Industry Niche Tag",
    "deal_value": 18000,
    "reason_no_configurator": "Specific observation on why a 3D configurator will increase their product conversions",
    "subject": "Punchy personalized subject line",
    "body": "Complete email body containing {{CALENDAR_LINK}} once"
  }
]
"""


def get_calendar_link():
    link = os.environ.get("CALENDAR_LINK")
    if not link:
        try:
            import streamlit as st
            link = st.secrets.get("CALENDAR_LINK")
        except Exception:
            pass
    return link or DEFAULT_CALENDAR_LINK


def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            pass
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file or Streamlit Cloud Secrets.")
    return genai.Client(api_key=api_key)


def get_hunter_key():
    key = os.environ.get("HUNTER_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("HUNTER_API_KEY")
        except Exception:
            pass
    return key


def extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        domain = re.sub(r"^www\.", "", netloc).strip()
        return domain
    except Exception:
        return ""


def extract_json_safe(text: str):
    if not text:
        return None
    cleaned = text.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass

    arr_m = re.search(r"\[\s*\{[\s\S]*\}\s*\]", cleaned)
    if arr_m:
        try:
            return json.loads(arr_m.group(0).strip())
        except Exception:
            pass

    return None


def execute_find_employee_contact(domain: str, contact_name: str = "") -> dict:
    """Finds verified employee email via Hunter.io Domain Search & Email Finder."""
    hunter_key = get_hunter_key()
    if not hunter_key:
        return {"name": contact_name, "position": "", "email": "unknown", "source": "none"}

    clean_dom = extract_domain(domain) or domain.strip().replace("https://", "").replace("http://", "").split("/")[0]

    # 1. Try Specific Name Finder if contact_name is known
    if contact_name and contact_name.lower() not in ["team", "unknown", "n/a", ""]:
        try:
            resp = requests.get(
                "https://api.hunter.io/v2/email-finder",
                params={"domain": clean_dom, "full_name": contact_name, "api_key": hunter_key},
                timeout=6,
            )
            if resp.status_code == 200:
                edata = resp.json().get("data", {})
                if edata.get("email"):
                    return {
                        "name": contact_name,
                        "position": edata.get("position") or "",
                        "email": edata["email"],
                        "source": "hunter_finder",
                    }
        except Exception:
            pass

    # 2. Try Domain Search for Top Personal Executive Contact
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": clean_dom, "api_key": hunter_key, "limit": 10},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            personal_emails = [e for e in data.get("emails", []) if e.get("type") == "personal"]
            if personal_emails:
                priority_keywords = ["sales", "marketing", "founder", "owner", "ceo", "director", "head", "president"]
                def score(e):
                    pos = (e.get("position") or "").lower()
                    return (15 if any(k in pos for k in priority_keywords) else 0) + (e.get("confidence") or 0)
                personal_emails.sort(key=score, reverse=True)
                top = personal_emails[0]
                first = top.get("first_name") or ""
                last = top.get("last_name") or ""
                fullname = f"{first} {last}".strip()
                return {
                    "name": fullname or contact_name,
                    "position": top.get("position") or "",
                    "email": top.get("value") or "unknown",
                    "source": "hunter_domain",
                }
            # Fallback to domain email
            generic = [e for e in data.get("emails", []) if e.get("value")]
            if generic:
                return {
                    "name": contact_name,
                    "position": "Company Contact",
                    "email": generic[0].get("value"),
                    "source": "hunter_generic",
                }
    except Exception:
        pass

    return {"name": contact_name, "position": "", "email": "unknown", "source": "none"}


def run_agent(user_prompt: str, log=None) -> dict:
    """
    Executes single-pass AI discovery and drafting with Gemini 3.6 Flash.
    """
    client = get_gemini_client()
    saved_count = 0
    skipped_duplicates = []
    new_leads_list = []
    cal_link = get_calendar_link()

    prompt_content = f"""Target Goal from Bilal:
"{user_prompt}"

Identify 3 to 5 real commercial businesses/brands matching this request that do not have interactive 3D web configurators on their site. Provide complete company profiles and write a personalized email draft for each."""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        candidates = extract_json_safe(response.text) or []
    except Exception as e:
        return {"saved": 0, "skipped_duplicates": [], "leads": [], "error": str(e)}

    if not candidates or not isinstance(candidates, list):
        return {"saved": 0, "skipped_duplicates": [], "leads": []}

    for c in candidates:
        if not isinstance(c, dict):
            continue

        company_name = c.get("company_name", "").strip()
        website = c.get("company_website", "").strip()
        domain = c.get("domain") or extract_domain(website)
        reason = c.get("reason_no_configurator", "")
        contact_name = c.get("contact_name", "Team")
        contact_role = c.get("contact_role", "")
        contact_email = c.get("contact_email", "unknown")
        industry_tag = c.get("industry_tag", "3D Configurator / CGI")
        deal_val = float(c.get("deal_value") or 18000.0)
        subject = c.get("subject", f"3D Configurator for {company_name}")
        raw_body = c.get("body", "")

        if not company_name:
            continue

        # Check duplicates
        if db.is_duplicate(company_name):
            skipped_duplicates.append(company_name)
            continue

        # Run Hunter.io enrichment to get verified executive email
        if domain:
            hunter_info = execute_find_employee_contact(domain, contact_name=contact_name)
            if hunter_info.get("email") and hunter_info.get("email") != "unknown":
                contact_email = hunter_info["email"]
            if hunter_info.get("name") and hunter_info.get("name") not in ["Team", "unknown", ""]:
                contact_name = hunter_info["name"]
            if hunter_info.get("position") and hunter_info.get("position") != "Company Contact":
                contact_role = hunter_info["position"]

        # If email is still unknown, provide fallback domain contact email
        if not contact_email or contact_email == "unknown":
            if domain:
                contact_email = f"info@{domain}"

        body = raw_body.replace("{{CALENDAR_LINK}}", cal_link)

        new_id = db.add_lead(
            company_name=company_name,
            company_website=website,
            contact_name=contact_name,
            contact_role=contact_role,
            contact_email=contact_email,
            industry_tag=industry_tag,
            deal_value=deal_val,
            pipeline_stage="draft_ready",
            reason=reason,
            subject=subject,
            body=body,
            source_prompt=user_prompt,
        )

        saved_count += 1
        new_leads_list.append({
            "id": new_id,
            "company_name": company_name,
            "company_website": website,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": contact_email,
            "industry_tag": industry_tag,
            "deal_value": deal_val,
            "pipeline_stage": "draft_ready",
            "reason": reason,
            "subject": subject,
            "body": body,
        })

    return {
        "saved": saved_count,
        "skipped_duplicates": skipped_duplicates,
        "leads": new_leads_list,
    }
