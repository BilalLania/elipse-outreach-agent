"""
agent_core.py — Multi-Model Cascade & Context-Aware Intelligence Engine for Elipse Studio.

Features:
1. Multi-Model Cascade with Automatic Fallback (gemini-3.6-flash, gemini-3.7-flash, gemini-flash-latest, gemini-3.5-flash, gemini-2.5-pro)
   to ensure zero 503 / 429 downtime.
2. Context-Aware Outreach Drafting:
   - Event / Conference Networking (LEAP Riyadh, GITEX, Index, etc.) -> In-person booth meetups & coffee.
   - Commercial Web 3D Configurators (Bespoke furniture, custom automotive, yachts, luxury kitchens) -> Online 3D visualizers.
   - Architecture & Megaprojects (Saudi Vision 2030, UAE PropTech, Masterplans) -> Interactive Digital Twins & Virtual Sales Apps.
3. Automated Website Verification & Hunter.io Decision-Maker Enrichment.
"""

import os
import json
import re
import time
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

from google import genai
from google.genai import types

import db

load_dotenv()

# Multi-Model Fallback Cascade to prevent 503 / 429 outages
MODEL_CASCADE = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-2.5-pro",
]

DEFAULT_CALENDAR_LINK = "https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting"

SYSTEM_PROMPT = """You are the elite business development intelligence engine for Elipse Studio,
a premier 3D visualization and spatial technology studio (CGI animation, VR/AR, real-time interactive 3D Web Configurators,
and photorealistic architectural digital twins).

Founder: Bilal (Elipse Studio).

Analyze the user's outreach goal carefully. Recognize the outreach angle:
1. EVENT / CONFERENCE NETWORKING (e.g. LEAP Riyadh, GITEX Dubai, Index Saudi, Salone del Mobile, Monaco Yacht Show):
   - Identify real major exhibitors/companies actively participating or relevant to the event.
   - Tailor the outreach draft specifically for IN-PERSON MEETINGS at the event (e.g. "I'll be in Riyadh for LEAP later this month...", "Let's grab a 10-minute coffee at your booth or the VIP lounge").
   - Pitch how Elipse Studio's real-time 3D, CGI, or digital twins elevate their exhibition presence and buyer engagement.

2. COMMERCIAL WEB 3D CONFIGURATOR (e.g. Custom golf carts, luxury bespoke furniture, automotive, kitchens, yachts):
   - Identify real companies with high-customization products that only have static 2D photos.
   - Pitch how an interactive Web 3D configurator lets customers customize options in real time and increases conversions.

3. ARCHITECTURE & MEGAPROJECTS (e.g. Saudi Vision 2030, UAE PropTech, Luxury Real Estate Developers):
   - Identify real developers, masterplan builders, and spatial tech innovators.
   - Pitch interactive 3D web masterplans, photorealistic CGI walkthroughs, and virtual sales center apps.

Email Rules:
- 60 to 85 words total. Short, confident sentences. Zero corporate fluff/clichés.
- Written in first person by Bilal ("I'll be attending...", "At Elipse Studio, we build...").
- Specific observation about their project, product line, or booth.
- If event-related: Low-pressure ask for a quick 10-minute in-person coffee/booth visit at the event.
- If remote-related: Low-pressure ask including {{CALENDAR_LINK}} once.
- Sign off as:
  Best,
  Bilal
  Founder, Elipse Studio

Return a valid JSON array of objects:
[
  {
    "company_name": "Exact Company Name",
    "company_website": "https://official-domain.com",
    "domain": "official-domain.com",
    "contact_name": "Full Name of Executive (or Department Team)",
    "contact_role": "Executive Title (e.g. CMO, Head of Innovation, VP Marketing, Owner)",
    "contact_email": "direct email or company contact email",
    "industry_tag": "Must be one of: '⛳ Custom Golf Carts', '🏎️ Custom Automotive & Mobility', '🛋️ Luxury Furniture & Interiors', '🏗️ Real Estate & Megaprojects', '⛵ Superyachts & Marine', '⚡ Tech & Commercial Products'",
    "deal_value": 35000,
    "reason_no_configurator": "Precise reason why Elipse Studio adds massive value",
    "subject": "Personalized punchy subject line",
    "body": "Complete email body"
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


def verify_and_resolve_official_website(company_name: str, suggested_url: str) -> str:
    """Verifies that a URL is active. If invalid or hallucinated, searches for the exact official website."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # 1. Quick check on suggested URL
    if suggested_url and ("http://" in suggested_url or "https://" in suggested_url):
        try:
            r = requests.head(suggested_url, timeout=3, headers=headers, allow_redirects=True)
            if r.status_code < 400:
                return r.url
        except Exception:
            pass

    # 2. Fast resolution for the real official website via web search
    if DDGS and company_name:
        try:
            clean_name = re.sub(r'[\"\']+', ' ', company_name).strip()
            results = list(DDGS().text(f"{clean_name} official website", max_results=4))
            for res in results:
                href = res.get("href")
                if href and not any(x in href.lower() for x in ["linkedin.com", "facebook.com", "instagram.com", "yelp.com", "yellowpages.com", "mapquest.com", "wikipedia.org", "bloomberg.com"]):
                    return href
        except Exception:
            pass

    return suggested_url or f"https://www.{extract_domain(company_name)}.com"


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


def get_top_decision_makers(domain: str, limit: int = 3) -> list:
    """Queries Hunter.io Domain Search and returns up to 3 top decision-maker contacts."""
    hunter_key = get_hunter_key()
    if not hunter_key:
        return []

    clean_dom = extract_domain(domain) or domain.strip().replace("https://", "").replace("http://", "").split("/")[0]

    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": clean_dom, "api_key": hunter_key, "limit": 10},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            emails = data.get("emails", [])

            priority_keywords = ["founder", "owner", "ceo", "director", "sales", "marketing", "head", "president", "partner", "vp", "chief", "manager"]

            def score(e):
                pos = (e.get("position") or "").lower()
                role_bonus = 25 if any(k in pos for k in priority_keywords) else 0
                is_personal = 15 if e.get("type") == "personal" else 0
                return role_bonus + is_personal + (e.get("confidence") or 0)

            emails.sort(key=score, reverse=True)
            results = []
            for e in emails[:limit]:
                first = e.get("first_name") or ""
                last = e.get("last_name") or ""
                name = f"{first} {last}".strip() or "Executive Contact"
                results.append({
                    "name": name,
                    "position": e.get("position") or "Company Executive",
                    "email": e.get("value") or "",
                    "confidence": e.get("confidence") or 0,
                    "type": e.get("type", "personal"),
                })
            return results
    except Exception:
        pass

    return []


def map_to_standard_category(tag, company_name=""):
    t = (tag or "").strip()
    standard_cats = getattr(db, "STANDARD_CATEGORIES", [
        "⛳ Custom Golf Carts",
        "🏎️ Custom Automotive & Mobility",
        "🛋️ Luxury Furniture & Interiors",
        "🏗️ Real Estate & Megaprojects",
        "⛵ Superyachts & Marine",
        "⚡ Tech & Commercial Products",
    ])
    if t in standard_cats:
        return t
    comb = (t + " " + company_name).lower()
    if any(k in comb for k in ["golf", "cart", "rad dog", "ckd", "tidewater", "garrett", "apex"]):
        return "⛳ Custom Golf Carts"
    if any(k in comb for k in ["furniture", "joinery", "interior", "kitchen", "cabinet", "decor", "sofa", "lighting"]):
        return "🛋️ Luxury Furniture & Interiors"
    if any(k in comb for k in ["automotive", "car", "vehicle", "mobility", "motor", "melex", "italcar", "motion", "bensel"]):
        return "🏎️ Custom Automotive & Mobility"
    if any(k in comb for k in ["real estate", "property", "proptech", "giga", "megaproject", "leap", "architecture", "developer"]):
        return "🏗️ Real Estate & Megaprojects"
    if any(k in comb for k in ["yacht", "marine", "boat", "vessel"]):
        return "⛵ Superyachts & Marine"
    return "⚡ Tech & Commercial Products"


def run_agent(user_prompt: str, log=None) -> dict:
    """
    Executes multi-model fallback cascade intelligence to research companies,
    verify live official websites, lookup contacts, and draft custom outreach emails.
    """
    client = get_gemini_client()
    saved_count = 0
    skipped_duplicates = []
    new_leads_list = []
    cal_link = get_calendar_link()

    prompt_content = f"""Target Outreach Request from Bilal:
"{user_prompt}"

Identify 3 to 5 real commercial businesses/brands/exhibitors matching this request that would benefit significantly from Elipse Studio's 3D Configurators, CGI Animation, or Digital Twins. Provide complete company profiles and write a personalized email draft for each."""

    candidates = None
    last_error = None

    # Cascade through available Gemini models to guarantee 100% uptime and resilience against 503/429
    for model_name in MODEL_CASCADE:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            candidates = extract_json_safe(response.text)
            if candidates and isinstance(candidates, list):
                break
        except Exception as e:
            last_error = str(e)
            time.sleep(0.5)
            continue

    if not candidates or not isinstance(candidates, list):
        return {"saved": 0, "skipped_duplicates": [], "leads": [], "error": last_error or "No companies found"}

    for c in candidates:
        if not isinstance(c, dict):
            continue

        company_name = c.get("company_name", "").strip()
        raw_website = c.get("company_website", "").strip()
        website = verify_and_resolve_official_website(company_name, raw_website)
        domain = extract_domain(website) or c.get("domain") or extract_domain(raw_website)
        reason = c.get("reason_no_configurator", "")
        contact_name = c.get("contact_name", "Team")
        contact_role = c.get("contact_role", "")
        contact_email = c.get("contact_email", "unknown")
        raw_tag = c.get("industry_tag", "⚡ Tech & Commercial Products")
        industry_tag = map_to_standard_category(raw_tag, company_name)
        deal_val = float(c.get("deal_value") or 25000.0)
        subject = c.get("subject", f"Question regarding {company_name}")
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

        # Fallback email if still missing
        if not contact_email or contact_email == "unknown":
            if domain:
                contact_email = f"info@{domain}"

        body = raw_body.replace("{{CALENDAR_LINK}}", cal_link)

        # Generate custom 20-second cold-call script & objection battlecard
        battlecard = generate_cold_call_battlecard(
            company_name=company_name,
            website=website,
            contact_name=contact_name,
            contact_role=contact_role,
            industry_tag=industry_tag,
        )
        phone_script = battlecard.get("phone_script", "")
        objection_notes = battlecard.get("objection_matrix", "")
        if not reason:
            reason = battlecard.get("how_we_help", "")

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
            phone_script=phone_script,
            objection_notes=objection_notes,
            phone_status="verified_direct",
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


def generate_cold_call_battlecard(
    company_name: str,
    website: str = "",
    contact_name: str = "Decision Maker",
    contact_role: str = "Owner",
    industry_tag: str = "⚡ Tech & Commercial Products",
) -> dict:
    """
    Generates tailored 3D configurator sales angle, 20-second cold-call phone opener,
    and 3 custom objection rebuttals for an outbound sales rep.
    """
    first_name = contact_name.split()[0] if contact_name and contact_name != "Decision Maker" else "there"
    fallback_script = (
        f"Hi {first_name}, Bilal with Elipse Studio. I was checking out {company_name}'s collection online, "
        f"and noticed your buyers currently browse static photos before asking for a quote. "
        f"We build interactive real-time 3D web configurators that let clients customize options live on your website before buying. "
        f"Would you be open to a 3-minute visual concept tailored for {company_name} this Thursday?"
    )
    fallback_objections = (
        "**• 'We already have photos on our site':**\n"
        "Photos show what you already built; an interactive 3D builder lets high-ticket buyers customize what they want to buy today.\n\n"
        "**• 'Just send me an email with information':**\n"
        "I'll send that over to your direct inbox right now. Are you at your screen Thursday at 2 PM to see a 3-minute live preview?\n\n"
        "**• 'We are too busy / call back in 6 months':**\n"
        "Completely understand. Our 3D models integrate directly into your site in under 2 weeks without eating up your team's time."
    )
    fallback_help = (
        f"{company_name} sells customizable high-ticket products using static 2D gallery photos. "
        f"Adding a real-time Web 3D configurator increases customer time-on-site and generates quote-ready configurations."
    )
    fallback_email = (
        f"Hi {first_name},\n\n"
        f"I came across {company_name} while researching leaders in {industry_tag}. Your builds look impressive.\n\n"
        f"Right now, buyers imagine custom configurations using static photos. We build real-time 3D web configurators that let customers customize finishes, materials, and options live on your website before ordering.\n\n"
        f"Would you be open to a quick 5-minute visual demo? You can grab a time here: {get_calendar_link()}\n\n"
        f"Best,\nBilal\nFounder, Elipse Studio"
    )

    prompt = f"""
Company: {company_name}
Website: {website}
Contact: {contact_name} ({contact_role})
Sector: {industry_tag}

You are an elite B2B sales development strategist for Elipse Studio (custom 3D web configurators, CGI animations, and digital twins).
Generate a high-conversion cold-call battlecard for a sales rep calling {contact_name} at {company_name}.

Return JSON:
{{
  "how_we_help": "1-2 punchy sentences explaining exactly why {company_name} needs real-time 3D web configuration over static photos.",
  "phone_script": "A natural, conversational 20-second cold-call opener (under 55 words) spoken by the sales rep. Starts with polite disruption, mentions an observation about their products, pitches interactive 3D customization, and ends with a low-friction meeting ask.",
  "objection_matrix": "Markdown text containing specific 1-sentence rebuttals for: 1. 'We already have photos', 2. 'Just send me an email', 3. 'Not interested / too small'",
  "email_body": "Short 65-word follow-up email."
}}
"""
    try:
        client = get_gemini_client()
        for model_name in MODEL_CASCADE[:3]:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        response_mime_type="application/json",
                    ),
                )
                data = extract_json_safe(response.text)
                if isinstance(data, dict) and data.get("phone_script"):
                    return {
                        "how_we_help": data.get("how_we_help", fallback_help),
                        "phone_script": data.get("phone_script", fallback_script),
                        "objection_matrix": data.get("objection_matrix", fallback_objections),
                        "email_body": data.get("email_body", fallback_email),
                    }
            except Exception:
                continue
    except Exception:
        pass

    return {
        "how_we_help": fallback_help,
        "phone_script": fallback_script,
        "objection_matrix": fallback_objections,
        "email_body": fallback_email,
    }
