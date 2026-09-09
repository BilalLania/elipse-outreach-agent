"""
lead_engine.py — Sourcing, Phone Scrubbing & High-Throughput Enrichment Engine for Elipse Studio.

Features:
1. Apollo.io API integration for querying verified decision makers with direct mobile/desk phones.
2. Bulk ICP CSV Importer: Auto-maps columns from Apollo, ZoomInfo, Clay, or Sales Navigator exports.
3. Phone Scrub & Normalization: Formats phone numbers, flags switchboards (1-800/888), and eliminates bad dials.
4. Battlecard Synthesis: Pairs each enriched lead with Gemini Flash cold-call scripts and objection rebuttals.
"""

import os
import re
import csv
import io
import requests
from datetime import datetime

import db
import agent_core


def get_apollo_key():
    key = os.environ.get("APOLLO_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("APOLLO_API_KEY")
        except Exception:
            pass
    return key


def scrub_and_format_phone(raw_phone: str) -> dict:
    if not raw_phone or not isinstance(raw_phone, str):
        return {"phone": "", "status": "missing", "type": "none"}

    raw = raw_phone.strip()
    digits = re.sub(r"\D", "", raw)

    if not digits or len(digits) < 7:
        return {"phone": "", "status": "invalid_format", "type": "none"}

    is_toll_free = bool(re.match(r"^(1)?(800|888|877|866|855|844|833)", digits))
    phone_type = "switchboard" if is_toll_free else "direct_line"

    if len(digits) == 10:
        formatted = f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith("1"):
        formatted = f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    elif len(digits) >= 11:
        formatted = f"+{digits}"
    else:
        formatted = raw

    return {
        "phone": formatted,
        "status": "switchboard" if is_toll_free else "verified_direct",
        "type": phone_type,
    }


def query_apollo_leads(icp_prompt: str, limit: int = 50, api_key: str = None) -> dict:
    key = api_key or get_apollo_key()
    if not key:
        return {
            "success": False,
            "error": "APOLLO_API_KEY not configured. Enter your key in the settings drawer or upload an Apollo CSV export.",
            "leads": [],
        }

    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": key,
    }

    seniorities = ["owner", "founder", "c_suite", "vp", "director"]
    payload = {
        "q_keywords": icp_prompt,
        "person_titles": ["Owner", "Founder", "President", "Chief Executive Officer", "VP Sales", "Director of Marketing"],
        "seniorities": seniorities,
        "page": 1,
        "per_page": min(limit, 100),
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 403:
            return {
                "success": False,
                "error": "Apollo Free Plan Notice: Apollo.io reserves their direct REST Search API for paid plans ($49/mo). Free options: 1) Use the 'Free AI Discovery' tab to generate leads via Gemini + Hunter.io, OR 2) Do your search on the free Apollo website, click 'Export CSV', and drop it into the 'Bulk CSV' tab!",
                "leads": [],
            }
        if r.status_code != 200:
            return {
                "success": False,
                "error": f"Apollo API Error ({r.status_code}): {r.text[:200]}",
                "leads": [],
            }

        data = r.json()
        people = data.get("people", [])
        parsed_leads = []

        for p in people:
            org = p.get("organization") or {}
            comp_name = org.get("name") or p.get("headline", "").split(" at ")[-1].strip()
            if not comp_name:
                continue

            phone_numbers = p.get("phone_numbers") or []
            raw_phone = phone_numbers[0].get("sanitized_number") if phone_numbers else ""
            if not raw_phone:
                raw_phone = org.get("primary_phone", {}).get("number") or ""

            scrubbed_phone = scrub_and_format_phone(raw_phone)

            name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or "Executive"
            role = p.get("title") or "Decision Maker"
            email = p.get("email") or f"contact@{org.get('primary_domain', 'company.com')}"
            website = org.get("website_url") or f"https://{org.get('primary_domain', '')}"
            linkedin = p.get("linkedin_url") or org.get("linkedin_url") or ""
            industry = org.get("industry") or "⚡ Tech & Commercial Products"

            clean_cat = agent_core.map_to_standard_category(industry, comp_name)

            parsed_leads.append({
                "company_name": comp_name,
                "company_website": website,
                "contact_name": name,
                "contact_role": role,
                "contact_email": email,
                "contact_phone": scrubbed_phone["phone"],
                "contact_linkedin": linkedin,
                "industry_tag": clean_cat,
                "deal_value": 25000.0,
                "phone_status": scrubbed_phone["status"],
                "source_prompt": f"Apollo ICP: {icp_prompt}",
            })

        return {
            "success": True,
            "leads": parsed_leads,
            "total_found": data.get("pagination", {}).get("total_entries", len(parsed_leads)),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "leads": [],
        }


def parse_and_enrich_csv(csv_content: str, max_records: int = 300) -> dict:
    try:
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        headers = [h.strip() for h in reader.fieldnames] if reader.fieldnames else []
    except Exception as e:
        return {"success": False, "error": f"Invalid CSV file: {str(e)}", "leads": []}

    def match_col(possible_names):
        for h in headers:
            normalized = h.lower().replace(" ", "_").replace("-", "_")
            if normalized in possible_names:
                return h
        return None

    c_company = match_col(["company", "company_name", "organization", "account_name", "business_name"])
    c_website = match_col(["website", "company_website", "domain", "website_url", "url"])
    c_name = match_col(["name", "contact_name", "full_name", "person_name"])
    c_first = match_col(["first_name", "firstname"])
    c_last = match_col(["last_name", "lastname"])
    c_role = match_col(["title", "role", "job_title", "position"])
    c_email = match_col(["email", "contact_email", "work_email", "corporate_email", "primary_email"])
    c_phone = match_col(["phone", "direct_phone", "mobile_phone", "corporate_phone", "phone_number", "mobile", "cell"])
    c_linkedin = match_col(["linkedin", "linkedin_url", "person_linkedin_url", "profile_url"])
    c_industry = match_col(["industry", "category", "keywords", "tags"])
    c_deal = match_col(["revenue", "annual_revenue", "deal_value", "estimated_value"])

    if not c_company:
        return {
            "success": False,
            "error": "Could not identify Company column in CSV. Ensure header contains 'Company', 'Company Name', or 'Organization'.",
            "leads": [],
        }

    parsed_leads = []
    skipped_duplicates = 0

    for row in reader:
        if len(parsed_leads) >= max_records:
            break

        comp = row.get(c_company, "").strip()
        if not comp:
            continue

        if db.is_duplicate(comp):
            skipped_duplicates += 1
            continue

        if c_name and row.get(c_name):
            contact_name = row.get(c_name, "").strip()
        elif c_first and row.get(c_first):
            contact_name = f"{row.get(c_first, '').strip()} {row.get(c_last, '').strip()}".strip()
        else:
            contact_name = "Decision Maker"

        website = row.get(c_website, "").strip() if c_website else ""
        if website and not website.startswith("http"):
            website = f"https://{website}"

        role = row.get(c_role, "").strip() if c_role else "Executive"
        email = row.get(c_email, "").strip() if c_email else "unknown"

        raw_phone = row.get(c_phone, "").strip() if c_phone else ""
        scrubbed = scrub_and_format_phone(raw_phone)

        linkedin = row.get(c_linkedin, "").strip() if c_linkedin else ""
        industry_val = row.get(c_industry, "").strip() if c_industry else "⚡ Tech & Commercial Products"
        clean_category = agent_core.map_to_standard_category(industry_val, comp)

        deal_val = 20000.0
        if c_deal and row.get(c_deal):
            try:
                deal_val = float(re.sub(r"[^\d.]", "", str(row.get(c_deal))))
                if deal_val < 5000:
                    deal_val = 15000.0
            except Exception:
                deal_val = 20000.0

        parsed_leads.append({
            "company_name": comp,
            "company_website": website,
            "contact_name": contact_name,
            "contact_role": role,
            "contact_email": email,
            "contact_phone": scrubbed["phone"],
            "contact_linkedin": linkedin,
            "industry_tag": clean_category,
            "deal_value": deal_val,
            "phone_status": scrubbed["status"],
            "source_prompt": "CSV Batch Import",
        })

    return {
        "success": True,
        "leads": parsed_leads,
        "total_parsed": len(parsed_leads),
        "skipped_duplicates": skipped_duplicates,
    }


def synthesize_lead_battlecards(leads_list: list, progress_callback=None) -> list:
    total = len(leads_list)
    enriched = []

    for idx, lead in enumerate(leads_list):
        if progress_callback:
            progress_callback(idx + 1, total, lead["company_name"])

        battlecard = agent_core.generate_cold_call_battlecard(
            company_name=lead["company_name"],
            website=lead.get("company_website", ""),
            contact_name=lead.get("contact_name", "Decision Maker"),
            contact_role=lead.get("contact_role", "Executive"),
            industry_tag=lead.get("industry_tag", "⚡ Tech & Commercial Products"),
        )

        lead["reason"] = battlecard.get("how_we_help", "High customization product catalog that converts higher with interactive real-time 3D web builder.")
        lead["phone_script"] = battlecard.get("phone_script", "")
        lead["objection_notes"] = battlecard.get("objection_matrix", "")
        lead["subject"] = f"3D configurator concept for {lead['company_name']}"
        lead["body"] = battlecard.get("email_body", "")

        enriched.append(lead)

    return enriched
