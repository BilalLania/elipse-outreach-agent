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
import urllib.parse
from urllib.parse import urlparse
from datetime import datetime
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

# Silence noisy google-genai INFO/WARNING lines (the spurious "AFC not recommended"
# notice and the "Both GOOGLE_API_KEY and GEMINI_API_KEY are set" notice). Real errors
# still surface.
import logging as _logging
for _n in ("google_genai", "google.genai", "google_genai.models", "google_genai._api_client"):
    _logging.getLogger(_n).setLevel(_logging.ERROR)

import db

load_dotenv()

# The SDK complains on every client init when both env vars are set. Keep GEMINI_API_KEY
# (from .env) as the single source of truth so calls are deterministic.
if os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
    os.environ.pop("GOOGLE_API_KEY", None)
elif os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
    os.environ.pop("GOOGLE_API_KEY", None)


def _secrets_file_exists():
    import pathlib
    for p in (
        pathlib.Path.home() / ".streamlit" / "secrets.toml",
        pathlib.Path(".streamlit") / "secrets.toml",
    ):
        try:
            if p.exists():
                return True
        except Exception:
            pass
    return False


def _secret(name):
    """Env var first (ignoring empty strings); st.secrets only if a secrets.toml exists."""
    val = os.environ.get(name)
    if val:
        return val
    if _secrets_file_exists():
        try:
            import streamlit as st
            return st.secrets.get(name)
        except Exception:
            return None
    return None


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
    "contact_linkedin": "Direct personal LinkedIn profile URL (https://www.linkedin.com/in/...) or company LinkedIn page (https://www.linkedin.com/company/...)",
    "industry_tag": "Must be one of: '⛳ Custom Golf Carts', '🏎️ Custom Automotive & Mobility', '🛋️ Luxury Furniture & Interiors', '🏗️ Real Estate & Megaprojects', '⛵ Superyachts & Marine', '⚡ Tech & Commercial Products'",
    "deal_value": 35000,
    "reason_no_configurator": "Precise reason why Elipse Studio adds massive value",
    "subject": "Personalized punchy subject line",
    "body": "Complete email body"
  }
]
"""


def get_calendar_link():
    return _secret("CALENDAR_LINK") or DEFAULT_CALENDAR_LINK


def get_gemini_client():
    api_key = _secret("GEMINI_API_KEY") or _secret("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please add it to your .env file or Streamlit Cloud Secrets.")
    return genai.Client(api_key=api_key)


def get_hunter_key():
    return _secret("HUNTER_API_KEY")


def get_signalhire_key():
    return _secret("SIGNALHIRE_API_KEY")


SIGNALHIRE_BASE = "https://www.signalhire.com/api/v1/candidate"

_SR_KEYWORDS = ("owner", "founder", "ceo", "chief executive", "president", "partner",
                "principal", "managing director", "director", "vp ", "vice president",
                "head of", "gm", "general manager")
_NON_PERSONAL = ("team", "division", "department", "sales", "design", "build", "custom",
                 "group", "desk", "decision maker", "n/a", "unknown", "")


def signalhire_search(name: str = "", company: str = "", title: str = "") -> list:
    """
    Synchronous SignalHire profile search (POST /candidate/searchByQuery).
    No credits, no callback URL. Returns a list of profile dicts (name, current
    title/company, location, uid) but NO email/phone — contact reveal is a
    separate credit-metered async call that needs a public callback URL.
    """
    key = get_signalhire_key()
    if not key or not (name or company):
        return []

    body = {}
    if name and name.strip().lower() not in _NON_PERSONAL:
        body["fullName"] = name.strip()
    if company:
        body["currentCompany"] = company.strip()
    if title:
        body["currentTitle"] = title.strip()
    if not body:
        return []

    try:
        r = requests.post(
            f"{SIGNALHIRE_BASE}/searchByQuery",
            json=body,
            headers={"apikey": key, "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code != 200 or not r.content:
            return []
        return _signalhire_extract_candidates(r.json())
    except Exception:
        return []


_COMPANY_STOPWORDS = {
    "the", "and", "inc", "llc", "ltd", "co", "corp", "company", "group", "holdings",
    "golf", "carts", "cart", "cars", "car", "custom", "customs", "vehicles", "vehicle",
    "motors", "auto", "autos", "automotive", "furniture", "interiors", "design", "designs",
    "studio", "studios", "solutions", "services", "products", "usa", "international",
    "global", "enterprises", "industries", "specialty", "specialties", "of", "for",
}


def _distinctive_tokens(company: str):
    return [
        t for t in re.split(r"[^a-z0-9]+", (company or "").lower())
        if len(t) > 2 and t not in _COMPANY_STOPWORDS
    ]


def _company_match(profile: dict, company: str) -> bool:
    tokens = _distinctive_tokens(company)
    if not tokens:
        return False
    exp = profile.get("experience") or []
    hay = " ".join((e.get("company") or "") for e in exp if isinstance(e, dict)).lower()
    return any(t in hay for t in tokens)


# Words that should appear on a site genuinely belonging to each category.
INDUSTRY_KEYWORDS = {
    "⛳ Custom Golf Carts": ["golf cart", "golf car", "ez-go", "ezgo", "club car", "yamaha", "buggy", "lsv", "street legal"],
    "🏎️ Custom Automotive & Mobility": ["vehicle", "automotive", "truck", "motor", "restomod", "4x4", "chassis", "ev ", "car "],
    "🛋️ Luxury Furniture & Interiors": ["kitchen", "furniture", "interior", "cabinet", "joinery", "worktop", "wardrobe", "bespoke", "cabinetry", "showroom"],
    "🏗️ Real Estate & Megaprojects": ["real estate", "property", "development", "villa", "residence", "masterplan", "architect", "apartment"],
    "⛵ Superyachts & Marine": ["yacht", "marine", "boat", "vessel", "tender", "shipyard"],
}


def site_matches_lead(company_name: str, industry_tag: str, scraped_text: str, blocked: bool = False):
    """
    Cheap sanity check that a scraped page actually belongs to the lead.

    Catches hallucinated leads where the model invented a company and attached an
    unrelated live domain (e.g. "Papilio Bespoke Kitchens" -> papilio.uk, a book site).

    Crucially it must NOT accuse a real lead just because the site blocked the scanner
    (403 / Cloudflare / captcha) — that tells us nothing about the company.

    Returns (verdict, detail):
      "match"    page mentions the company's distinctive name or its industry
      "mismatch" page has real text but relates to neither -> almost certainly wrong site
      "blocked"  the site refused the scanner, so nothing could be verified
      "unknown"  too little text scraped to judge
    """
    text = " ".join((scraped_text or "").lower().split())

    # A refusal page proves nothing about the lead — check this BEFORE mismatch.
    try:
        import scraper as _scraper
        _blocked_text = _scraper.looks_blocked(text)
    except Exception:
        _blocked_text = False
    if blocked or _blocked_text:
        return "blocked", "the site refused the scanner (bot protection), so nothing could be read"

    if len(text) < 25:
        return "unknown", "not enough page text to verify"

    for t in _distinctive_tokens(company_name):
        if t in text:
            return "match", f"page mentions “{t}”"

    for kw in INDUSTRY_KEYWORDS.get(industry_tag or "", []):
        if kw in text:
            return "match", f"page mentions “{kw.strip()}”"

    return "mismatch", "page content relates to neither the company name nor its industry"


def enrich_lead(lead: dict) -> dict:
    """
    Conservative identity check via SignalHire's synchronous searchByQuery, layered on
    top of Hunter.io. It ONLY acts when the lead already has a real contact name AND a
    SignalHire profile for that name distinctly matches the company — in that case it
    fills in the person's real current title / captures their SignalHire uid.

    It deliberately does NOT run for placeholder contacts ("Custom Sales Team") — the
    company-only search is too noisy. Email / phone are never available here (SignalHire
    reveals those only via a credit-metered async callback flow the app can't host).
    Merge is strictly additive; nothing good is overwritten. Never raises.
    """
    if not isinstance(lead, dict):
        return lead
    if not get_signalhire_key():
        return lead

    company = (lead.get("company_name") or "").strip()
    name = (lead.get("contact_name") or "").strip()
    if not name or name.lower() in _NON_PERSONAL or not company:
        return lead
    if not _distinctive_tokens(company):
        return lead  # company name too generic to confirm a match

    try:
        profiles = signalhire_search(name=name)
        matches = [p for p in profiles if _company_match(p, company)]
        if not matches:
            return lead  # no confident person<->company match; leave lead untouched

        def seniority(p):
            exp = p.get("experience") or []
            t0 = (exp[0].get("title") or exp[0].get("position") or "").lower() if exp else ""
            return 1 if any(k in t0 for k in _SR_KEYWORDS) else 0

        best = sorted(matches, key=seniority, reverse=True)[0]
        found = _signalhire_pick_contacts(best)

        if found.get("position") and not (lead.get("contact_role") or "").strip():
            lead["contact_role"] = found["position"]
        if best.get("uid"):
            lead["signalhire_uid"] = best["uid"]  # for a later credit-metered reveal

        prev_src = (lead.get("enrichment_source") or "").strip()
        lead["enrichment_source"] = (
            "hunter+signalhire" if "hunter" in prev_src
            else (prev_src + "+signalhire" if prev_src else "signalhire")
        )
        lead["enriched_at"] = datetime.now().isoformat(timespec="seconds")
    except Exception:
        return lead

    return lead


def _signalhire_extract_candidates(data) -> list:
    """Normalizes the several shapes SignalHire may return into a list of candidate dicts."""
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("candidates", "results", "profiles", "data", "items"):
        val = data.get(key)
        if isinstance(val, list) and val:
            out = []
            for entry in val:
                if isinstance(entry, dict):
                    out.append(entry.get("candidate") if isinstance(entry.get("candidate"), dict) else entry)
            if out:
                return out
    if data.get("candidate") and isinstance(data["candidate"], dict):
        return [data["candidate"]]
    return []


def _signalhire_pick_contacts(candidate: dict) -> dict:
    """Pulls the first email / phone / LinkedIn + headline from a SignalHire candidate."""
    result = {"email": "", "phone": "", "linkedin": "", "name": "", "position": ""}
    if not isinstance(candidate, dict):
        return result

    full_name = candidate.get("fullName") or candidate.get("full_name") or ""
    if not full_name:
        fn = candidate.get("firstName") or candidate.get("first_name") or ""
        ln = candidate.get("lastName") or candidate.get("last_name") or ""
        full_name = f"{fn} {ln}".strip()
    result["name"] = full_name

    exp = candidate.get("experience") or candidate.get("positions") or []
    if isinstance(exp, list) and exp and isinstance(exp[0], dict):
        result["position"] = exp[0].get("position") or exp[0].get("title") or ""
    result["position"] = result["position"] or candidate.get("headline") or candidate.get("title") or ""

    contacts = candidate.get("contacts") or candidate.get("contactInfo") or []
    if isinstance(contacts, dict):
        contacts = [contacts]
    for c in contacts if isinstance(contacts, list) else []:
        if not isinstance(c, dict):
            continue
        ctype = str(c.get("type") or "").lower()
        value = c.get("value") or c.get("email") or c.get("phone") or ""
        if not value:
            continue
        if ("email" in ctype or "@" in str(value)) and not result["email"]:
            result["email"] = str(value)
        elif ("phone" in ctype or ctype in ("mobile", "work", "tel")) and not result["phone"]:
            result["phone"] = str(value)

    if not result["email"]:
        emails = candidate.get("emails") or []
        if isinstance(emails, list) and emails:
            first = emails[0]
            result["email"] = first.get("email") if isinstance(first, dict) else str(first)
    if not result["phone"]:
        phones = candidate.get("phones") or candidate.get("phoneNumbers") or []
        if isinstance(phones, list) and phones:
            first = phones[0]
            result["phone"] = first.get("phone") if isinstance(first, dict) else str(first)

    social = candidate.get("social") or candidate.get("socialLinks") or candidate.get("social_links") or []
    if isinstance(social, list):
        for s in social:
            link = s.get("link") or s.get("url") if isinstance(s, dict) else str(s)
            if link and "linkedin.com" in link:
                result["linkedin"] = link
                break

    return result


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
                        "linkedin_url": edata.get("linkedin_url") or "",
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
                    "linkedin_url": top.get("linkedin_url") or "",
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
                    "linkedin_url": e.get("linkedin_url") or "",
                })
            return results
    except Exception:
        pass

    return []


def research_prospect_linkedin(company_name: str, contact_name: str = "") -> dict:
    """
    Uses Gemini Flash cascade intelligence to research and find the exact personal
    LinkedIn profile URL (or company LinkedIn page) for the founder, CEO, or top executive.
    """
    clean_target = f"{contact_name or ''} {company_name}".strip()
    xray_fallback = f"https://www.google.com/search?q={urllib.parse.quote('site:linkedin.com/in ' + clean_target)}"

    try:
        client = get_gemini_client()
    except Exception as e:
        return {
            "success": False,
            "contact_name": contact_name or "Decision Maker",
            "contact_role": "Owner",
            "linkedin_url": "",
            "company_linkedin": "",
            "google_xray_url": xray_fallback,
            "reason": str(e),
        }

    target_query = f"{contact_name} at {company_name}" if contact_name and contact_name.lower() not in ["decision maker", "team", "unknown", ""] else company_name

    prompt = f"""You are an elite B2B executive researcher. Find the exact verified LinkedIn profile for the primary decision maker (Founder, CEO, President, Owner, or COO) of:
Target Prospect: {target_query}
Company Name: {company_name}

Instructions:
1. Identify the actual current Founder, CEO, Owner, or top executive of {company_name}. If '{contact_name}' is not the primary executive or doesn't have an indexed profile, identify the actual founder/owner (e.g. Jonathan Ward for ICON 4x4).
2. Provide their verified personal LinkedIn profile URL (format: https://www.linkedin.com/in/...).
3. If personal URL is uncertain, provide the official company LinkedIn page (format: https://www.linkedin.com/company/...).
4. Construct an optimized Google X-Ray search query.

Return ONLY a JSON object:
{{
  "contact_name": "Full Name of decision maker",
  "contact_role": "Current Title / Role",
  "linkedin_url": "https://www.linkedin.com/in/username or https://www.linkedin.com/company/companyname",
  "company_linkedin": "https://www.linkedin.com/company/companyname",
  "search_query": "Clean keyword query for LinkedIn or Google",
  "reason": "1 brief sentence explaining who this person is at the company"
}}"""

    for model_name in MODEL_CASCADE:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            data = extract_json_safe(response.text)
            if data and isinstance(data, dict):
                li_url = (data.get("linkedin_url") or "").strip()
                c_name = (data.get("contact_name") or contact_name or "Decision Maker").strip()
                c_role = (data.get("contact_role") or "Owner").strip()
                search_q = data.get("search_query") or f"{c_name} {company_name}"
                xray_url = f"https://www.google.com/search?q={urllib.parse.quote('site:linkedin.com/in ' + search_q)}"

                # Fallback to company_linkedin if personal linkedin_url is empty
                if not li_url and data.get("company_linkedin"):
                    li_url = data.get("company_linkedin").strip()

                return {
                    "success": True,
                    "contact_name": c_name,
                    "contact_role": c_role,
                    "linkedin_url": li_url,
                    "company_linkedin": data.get("company_linkedin", "").strip(),
                    "google_xray_url": xray_url,
                    "reason": data.get("reason", "").strip(),
                }
        except Exception:
            time.sleep(0.4)
            continue

    return {
        "success": False,
        "contact_name": contact_name or "Decision Maker",
        "contact_role": "Owner",
        "linkedin_url": "",
        "company_linkedin": "",
        "google_xray_url": xray_fallback,
        "reason": "Could not automatically resolve. Use Google X-Ray search.",
    }


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


def run_agent(user_prompt: str, log=None, max_leads: int = 5) -> dict:
    """
    Executes multi-model fallback cascade intelligence to research companies,
    verify live official websites, lookup contacts, and draft custom outreach emails.

    max_leads: how many businesses to ask the model for (clamped to 1..25).
    """
    max_leads = max(1, min(int(max_leads or 5), 25))
    client = get_gemini_client()
    saved_count = 0
    skipped_duplicates = []
    new_leads_list = []
    cal_link = get_calendar_link()

    prompt_content = f"""Target Outreach Request from Bilal:
"{user_prompt}"

Identify {max_leads} real commercial businesses/brands/exhibitors matching this request that would benefit significantly from Elipse Studio's 3D Configurators, CGI Animation, or Digital Twins. Provide complete company profiles and write a personalized email draft for each."""

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

    candidates = candidates[:max_leads]

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

        contact_linkedin = c.get("contact_linkedin") or c.get("linkedin_url") or ""

        # Run Hunter.io enrichment to get verified executive email
        if domain:
            hunter_info = execute_find_employee_contact(domain, contact_name=contact_name)
            if hunter_info.get("email") and hunter_info.get("email") != "unknown":
                contact_email = hunter_info["email"]
            if hunter_info.get("name") and hunter_info.get("name") not in ["Team", "unknown", ""]:
                contact_name = hunter_info["name"]
            if hunter_info.get("position") and hunter_info.get("position") != "Company Contact":
                contact_role = hunter_info["position"]
            if hunter_info.get("linkedin_url"):
                contact_linkedin = hunter_info["linkedin_url"]

        # Parallel/complementary enrichment via SignalHire (layered on top of Hunter.io)
        contact_phone = ""
        enrichment_source = "hunter" if domain else ""
        enriched_at = ""
        _lead_tmp = {
            "company_name": company_name,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "contact_linkedin": contact_linkedin,
            "enrichment_source": enrichment_source,
        }
        _lead_tmp = enrich_lead(_lead_tmp)
        contact_name = _lead_tmp.get("contact_name") or contact_name
        contact_role = _lead_tmp.get("contact_role") or contact_role
        contact_email = _lead_tmp.get("contact_email") or contact_email
        contact_phone = _lead_tmp.get("contact_phone") or ""
        contact_linkedin = _lead_tmp.get("contact_linkedin") or contact_linkedin
        enrichment_source = _lead_tmp.get("enrichment_source") or enrichment_source
        enriched_at = _lead_tmp.get("enriched_at") or ""

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
            contact_phone=contact_phone,
            contact_linkedin=contact_linkedin,
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
            enrichment_source=enrichment_source,
            enriched_at=enriched_at,
        )

        saved_count += 1
        new_leads_list.append({
            "id": new_id,
            "company_name": company_name,
            "company_website": website,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "contact_linkedin": contact_linkedin,
            "industry_tag": industry_tag,
            "deal_value": deal_val,
            "pipeline_stage": "draft_ready",
            "reason": reason,
            "subject": subject,
            "body": body,
            "enrichment_source": enrichment_source,
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
    _cn = (contact_name or "").strip()
    _non_personal = any(w in _cn.lower() for w in ["team", "division", "department", "sales", "design", "build", "custom", "group", "desk", "n/a", "unknown"])
    first_name = _cn.split()[0] if (_cn and _cn != "Decision Maker" and not _non_personal) else "there"
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
