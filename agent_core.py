"""
agent_core.py — Research + drafting agent loop powered by Google Gemini.

1. Generates targeted search queries based on user criteria.
2. Performs live web searches to find matching companies.
3. Uses Hunter.io (if configured) or web search to find decision-maker contacts.
4. Uses Google Gemini to analyze companies, verify lack of 3D configurators,
   and draft personalized high-converting outreach emails.
5. Saves qualified leads to SQLite (db.py), skipping duplicates.
"""

import os
import json
import re
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

MODEL = "gemini-3.6-flash"
DEFAULT_CALENDAR_LINK = "https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting"


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


def search_web(query: str, max_results: int = 8, log=print):
    """Executes live web search using DDGS."""
    _safe_log(f"🌐 Searching the web: '{query}'...", log)
    try:
        results = list(DDGS().text(query, max_results=max_results))
        return results
    except Exception as e:
        _safe_log(f"⚠️ Search warning: {e}", log)
        return []


def extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc
        domain = re.sub(r"^www\.", "", netloc).strip()
        return domain
    except Exception:
        return ""


def execute_find_employee_contact(domain: str, log=print) -> dict:
    """Calls Hunter.io's Domain Search API to find real employee contacts."""
    hunter_key = get_hunter_key()
    if not hunter_key:
        return {"name": "", "position": "", "email": "unknown", "source": "none"}

    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": hunter_key, "limit": 10},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
    except Exception as e:
        _safe_log(f"⚠️ Hunter.io lookup error for {domain}: {e}", log)
        return {"name": "", "position": "", "email": "unknown", "source": "error"}

    emails = [e for e in data.get("emails", []) if e.get("type") == "personal"]
    if not emails:
        # Fallback to generic if present
        generic = [e for e in data.get("emails", []) if e.get("value")]
        if generic:
            return {"name": "", "position": "General Inbox", "email": generic[0].get("value"), "source": "hunter_generic"}
        return {"name": "", "position": "", "email": "unknown", "source": "hunter_none"}

    priority_keywords = ["sales", "marketing", "founder", "owner", "ceo", "director", "business development", "head"]

    def score(e):
        position = (e.get("position") or "").lower()
        role_bonus = 15 if any(k in position for k in priority_keywords) else 0
        return role_bonus + (e.get("confidence") or 0)

    emails.sort(key=score, reverse=True)
    best = emails[0]
    first = best.get("first_name") or ""
    last = best.get("last_name") or ""
    name = f"{first} {last}".strip()
    position = best.get("position") or ""
    email = best.get("value") or "unknown"

    if name:
        _safe_log(f"🎯 Hunter.io found: {name} ({position}) <{email}>", log)
    return {"name": name, "position": position, "email": email, "source": "hunter"}


def _safe_log(msg: str, log=print):
    try:
        log(msg)
    except UnicodeEncodeError:
        try:
            # Fallback to ascii/printable representation
            log(msg.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass


def run_agent(user_prompt: str, log=print) -> dict:
    """
    Runs the multi-stage research and drafting pipeline with Gemini 3.6 Flash.
    """
    client = get_gemini_client()
    saved_count = 0
    skipped_duplicates = []

    def app_log(msg):
        _safe_log(msg, log)

    app_log("🤖 Step 1/4: Analyzing your target criteria with Gemini...")

    # Stage 1: Ask Gemini to plan optimal search queries
    query_gen_prompt = f"""The user wants to find outreach targets for Elipse Studio (3D Web Configurator & Visualization).
User Request: "{user_prompt}"

Generate 2 distinct, highly effective search queries to find real company websites matching this request.
Return ONLY a valid JSON array of strings, e.g. ["query 1", "query 2"]. Do not add markdown or backticks."""

    queries = []
    try:
        q_resp = client.models.generate_content(
            model=MODEL,
            contents=query_gen_prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        cleaned_text = q_resp.text.strip().replace("```json", "").replace("```", "").strip()
        queries = json.loads(cleaned_text)
    except Exception:
        queries = [user_prompt, f"{user_prompt} manufacturers retailers official site"]

    # Stage 2: Execute searches
    search_snippets = []
    seen_urls = set()
    for q in queries[:2]:
        results = search_web(q, max_results=6, log=app_log)
        for r in results:
            url = r.get("href", "")
            if url and url not in seen_urls and not any(d in url for d in ["wikipedia.org", "yellowpages", "tripadvisor", "linkedin.com/pulse"]):
                seen_urls.add(url)
                search_snippets.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("body", "")
                })

    if not search_snippets:
        app_log("⚠️ No direct search results found. Searching broader terms...")
        broad_results = search_web(f"{user_prompt} company website", max_results=5, log=app_log)
        for r in broad_results:
            search_snippets.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })

    app_log(f"🔎 Step 2/4: Identified {len(search_snippets)} prospective candidates from web research.")

    # Stage 3: Extract structured candidate companies using Gemini
    app_log("🧠 Step 3/4: Qualifying companies & verifying 3D configurator opportunities...")

    qualification_prompt = f"""Search Results:
{json.dumps(search_snippets, indent=2)}

Target Goal: "{user_prompt}"

From the search results, select the best 3 to 5 real commercial companies that sell physical or configurable products and would benefit from an interactive 3D Web Configurator.

Return ONLY a JSON array of objects with the following keys:
- "company_name": Name of the company
- "company_website": Official website URL
- "domain": Root domain (e.g. example.com)
- "reason_no_configurator": Why this company is a great fit (what they sell, observation that they only have 2D images or static catalog, and how 3D configurator helps).
- "product_observation": One specific product line or feature observed from their description.

Return ONLY the raw JSON array (no markdown code fences)."""

    candidates = []
    try:
        qual_resp = client.models.generate_content(
            model=MODEL,
            contents=qualification_prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        raw_candidates = qual_resp.text.strip().replace("```json", "").replace("```", "").strip()
        candidates = json.loads(raw_candidates)
    except Exception as e:
        app_log(f"⚠️ Error parsing qualified candidates: {e}")
        # Fallback if json parsing failed
        candidates = []

    if not candidates:
        app_log("⚠️ Could not extract qualified companies. Please try a more specific search prompt.")
        return {"saved": 0, "skipped_duplicates": []}

    # Stage 4: Contact lookup + Personalized Draft generation
    app_log(f"✍️ Step 4/4: Drafting personalized emails for {len(candidates)} companies...")

    for c in candidates:
        company_name = c.get("company_name", "").strip()
        website = c.get("company_website", "").strip()
        domain = c.get("domain") or extract_domain(website)
        reason = c.get("reason_no_configurator", "")
        product_obs = c.get("product_obs") or c.get("product_observation", "")

        if not company_name:
            continue

        if db.is_duplicate(company_name):
            skipped_duplicates.append(company_name)
            app_log(f"⏭️ Skipped '{company_name}' (already in database)")
            continue

        # Look up contact
        contact_info = execute_find_employee_contact(domain, log=app_log)
        contact_name = contact_info.get("name", "")
        contact_email = contact_info.get("email", "unknown")
        contact_role = contact_info.get("position", "")

        # Generate personalized email with Gemini
        draft_prompt = f"""{SYSTEM_PROMPT}

Target Company:
- Name: {company_name}
- Website: {website}
- Product Observation: {product_obs}
- Fit Reason: {reason}
- Contact Person: {contact_name if contact_name else 'Unknown (use gentle generic or direct greeting)'} ({contact_role})

Write a high-converting, personalized cold email from Bilal (Elipse Studio).
Requirements:
1. 60 to 90 words.
2. Short sentences.
3. Natural mention of {{CALENDAR_LINK}} placeholder once.
4. Subject line must be punchy and personalized (e.g. "Quick question re: [specific product line] on [Company Name]" or "3D visualizer for [Company Name]").

Return ONLY a JSON object with:
{{
  "subject": "The email subject line",
  "body": "The complete email body containing {{CALENDAR_LINK}} once"
}}
Return raw JSON without markdown formatting."""

        try:
            draft_resp = client.models.generate_content(
                model=MODEL,
                contents=draft_prompt,
                config=types.GenerateContentConfig(temperature=0.4),
            )
            raw_draft = draft_resp.text.strip().replace("```json", "").replace("```", "").strip()
            draft_data = json.loads(raw_draft)
            subject = draft_data.get("subject", f"Question regarding {company_name}")
            raw_body = draft_data.get("body", "")
            cal_link = get_calendar_link()
            body = raw_body.replace("{{CALENDAR_LINK}}", cal_link)

            db.add_lead(
                company_name=company_name,
                company_website=website,
                contact_name=contact_name,
                contact_role=contact_role,
                contact_email=contact_email,
                industry_tag=c.get("industry", "3D Configurator / CGI"),
                deal_value=18000.0,
                pipeline_stage="draft_ready",
                reason=reason,
                subject=subject,
                body=body,
                source_prompt=user_prompt,
            )
            saved_count += 1
            app_log(f"✅ Saved lead: {company_name} ({contact_email})")

        except Exception as e:
            app_log(f"⚠️ Error drafting email for {company_name}: {e}")

    app_log(f"🎉 Complete! Saved {saved_count} new leads to your dashboard.")
    return {"saved": saved_count, "skipped_duplicates": skipped_duplicates}
