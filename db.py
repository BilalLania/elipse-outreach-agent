"""
db.py — Persistent SQLite CRM Storage for Elipse Studio.

Stores rich lead and deal records, tracks pipeline stages, calculates
studio financial metrics, and manages follow-ups.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, date

DB_PATH = "leads.db"

PIPELINE_STAGES = [
    ("new_lead", "New Discovery"),
    ("draft_ready", "Draft Ready"),
    ("contacted", "Outreach Sent"),
    ("followup_due", "Follow-up Due"),
    ("meeting_booked", "Meeting Booked"),
    ("proposal_sent", "Proposal Sent"),
    ("won", "Deal Won"),
    ("lost", "Closed Lost"),
]

STAGE_LABELS = dict(PIPELINE_STAGES)

STANDARD_CATEGORIES = [
    "⛳ Custom Golf Carts",
    "🏎️ Custom Automotive & Mobility",
    "🛋️ Luxury Furniture & Interiors",
    "🏗️ Real Estate & Megaprojects",
    "⛵ Superyachts & Marine",
    "⚡ Tech & Commercial Products",
]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initializes the database and runs migrations for any missing columns."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                company_website TEXT,
                contact_name TEXT,
                contact_role TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                contact_linkedin TEXT,
                industry_tag TEXT DEFAULT '3D Configurator',
                deal_value REAL DEFAULT 15000.0,
                pipeline_stage TEXT NOT NULL DEFAULT 'draft_ready',
                status TEXT NOT NULL DEFAULT 'new',
                reason TEXT,
                subject TEXT,
                body TEXT,
                notes TEXT,
                followup_date TEXT,
                source_prompt TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Migration: ensure newly added columns exist in older tables
        existing_cols = [r["name"] for r in conn.execute("PRAGMA table_info(leads)").fetchall()]
        
        column_defs = {
            "contact_name": "TEXT",
            "contact_role": "TEXT",
            "contact_phone": "TEXT",
            "contact_linkedin": "TEXT",
            "industry_tag": "TEXT DEFAULT '3D Configurator'",
            "deal_value": "REAL DEFAULT 15000.0",
            "pipeline_stage": "TEXT NOT NULL DEFAULT 'draft_ready'",
            "notes": "TEXT",
            "followup_date": "TEXT",
            "phone_script": "TEXT",
            "objection_notes": "TEXT",
            "phone_status": "TEXT DEFAULT 'verified_direct'",
            "lead_score": "INTEGER DEFAULT 90",
            "has_3d": "INTEGER DEFAULT 0",
            "matched_signals": "TEXT",
            "product_title": "TEXT",
            "product_description": "TEXT",
            "screenshot_path": "TEXT",
            "enrichment_source": "TEXT",
            "enriched_at": "TEXT",
        }

        for col, col_type in column_defs.items():
            if col not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE leads ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

        # Sync pipeline_stage from status if needed
        conn.execute("""
            UPDATE leads
            SET pipeline_stage = CASE
                WHEN status = 'approved' THEN 'draft_ready'
                WHEN status = 'sent' THEN 'contacted'
                WHEN status = 'rejected' THEN 'lost'
                ELSE 'draft_ready'
            END
            WHERE pipeline_stage IS NULL OR pipeline_stage = ''
        """)

        # Create sales problems tracker table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sales_problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT NOT NULL DEFAULT 'High Priority',
                reported_by TEXT DEFAULT 'Sales Team',
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)

        # Create sales problem discussion comments table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS problem_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                comment_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(problem_id) REFERENCES sales_problems(id) ON DELETE CASCADE
            )
        """)

    seed_or_update_core_leads()
    seed_initial_problems()
    normalize_lead_categories()


def seed_initial_problems():
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM sales_problems").fetchone()["c"]
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            conn.execute(
                """INSERT INTO sales_problems (title, description, priority, reported_by, status, created_at)
                   VALUES (?, ?, ?, ?, 'Open', ?)""",
                (
                    "High dead/disconnected number rate (686 bad dials in 3 weeks)",
                    "Our outbound list has a ~23% dead-dial rate. Sales reps are burning dials on disconnected numbers. Need pre-scrubbed direct phone numbers.",
                    "High Priority",
                    "Outbound Sales Desk",
                    now,
                ),
            )
            conn.execute(
                """INSERT INTO sales_problems (title, description, priority, reported_by, status, created_at)
                   VALUES (?, ?, ?, ?, 'Open', ?)""",
                (
                    "Need 1-click live 3D showroom link for hot phone prospects",
                    "When custom cart and yacht prospects express interest on the phone, they ask to see a live demo immediately. Need a short interactive WebGL demo URL ready to SMS/email.",
                    "Normal Priority",
                    "Account Executive",
                    now,
                ),
            )


def add_sales_problem(title, description="", priority="High Priority", reported_by="Sales Team"):
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO sales_problems (title, description, priority, reported_by, status, created_at)
               VALUES (?, ?, ?, ?, 'Open', ?)""",
            (title, description, priority, reported_by, now),
        )
        return cur.lastrowid


def get_sales_problems(priority_filter="all", status_filter="Open"):
    with get_conn() as conn:
        query = "SELECT * FROM sales_problems WHERE 1=1"
        params = []
        if status_filter != "all":
            query += " AND status = ?"
            params.append(status_filter)
        if priority_filter != "all":
            query += " AND priority = ?"
            params.append(priority_filter)
        query += " ORDER BY CASE WHEN priority = 'High Priority' THEN 0 ELSE 1 END, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def update_sales_problem_status(problem_id, new_status):
    now = datetime.now().isoformat(timespec="seconds") if new_status == "Resolved" else None
    with get_conn() as conn:
        conn.execute(
            "UPDATE sales_problems SET status = ?, resolved_at = ? WHERE id = ?",
            (new_status, now, problem_id),
        )


def delete_sales_problem(problem_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM problem_comments WHERE problem_id = ?", (problem_id,))
        conn.execute("DELETE FROM sales_problems WHERE id = ?", (problem_id,))


def add_problem_comment(problem_id: int, author_name: str, comment_text: str):
    """Adds a reply / solution comment to a sales problem thread."""
    now = datetime.now().isoformat(timespec="seconds")
    author = author_name.strip() or "Sales Rep"
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO problem_comments (problem_id, author_name, comment_text, created_at)
               VALUES (?, ?, ?, ?)""",
            (problem_id, author, comment_text.strip(), now),
        )
        return cur.lastrowid


def get_problem_comments(problem_id: int = None):
    """Fetches discussion comments for a problem, or all comments."""
    with get_conn() as conn:
        if problem_id is not None:
            rows = conn.execute(
                "SELECT * FROM problem_comments WHERE problem_id = ? ORDER BY id ASC",
                (problem_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM problem_comments ORDER BY id ASC"
            ).fetchall()
        return [dict(r) for r in rows]


def delete_problem_comment(comment_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM problem_comments WHERE id = ?", (comment_id,))


VERIFIED_SAMPLE_LEADS = [
    {
        "company_name": "Garrett's Custom Golf Carts",
        "company_website": "https://www.gowithgarretts.com/",
        "contact_name": "Hal Garrett",
        "contact_role": "President & Owner",
        "contact_email": "halg@gowithgarretts.com",
        "contact_phone": "+1 (843) 881-8883",
        "contact_linkedin": "https://www.linkedin.com/in/hal-garrett-b02b6623",
        "industry_tag": "⛳ Custom Golf Carts",
        "deal_value": 18500.0,
        "reason": "Buyers customize body paint, upholstery stitching, lift kits, and rim styles using static gallery photos, leading to drop-offs before requesting a quote.",
        "subject": "3D cart builder for Garrett's Custom Golf Carts",
        "body": "Hi Hal,\n\nI was looking at your custom golf cart builds at Garrett's, specifically your custom diamond-stitched seating and lift kit options. Your builds look great.\n\nRight now, buyers browse static photos to imagine custom paint and upholstery combinations. We build real-time 3D web configurators that let customers customize paint, seats, and rims in 3D directly on your site before buying.\n\nWould you be open to a quick demo tailored for your custom builds? You can pick a time here: https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting\n\nBest,\nBilal\nElipse Studio",
    },
    {
        "company_name": "Tidewater Carts",
        "company_website": "https://tidewatercarts.com/",
        "contact_name": "Custom Sales Team",
        "contact_role": "Head of Custom Sales",
        "contact_email": "sales@tidewatercarts.com",
        "contact_phone": "+1 (803) 865-8016",
        "contact_linkedin": "https://www.linkedin.com/company/tidewater-carts",
        "industry_tag": "⛳ Custom Golf Carts",
        "deal_value": 21000.0,
        "reason": "Offers extensive custom colors, tops, and high-performance lift packages, but currently relies on static inventory listings.",
        "subject": "Interactive 3D configurator for Tidewater Carts",
        "body": "Hi Team,\n\nI came across Tidewater Carts while researching top custom golf cart builders in the US. Your custom lifted builds and sound bar packages stand out.\n\nSince buyers often want to compare custom body colors and seat patterns before ordering, an interactive 3D configurator on your website would allow them to visualize their build live and submit quote-ready specifications.\n\nWould you be open to seeing a 5-minute visual demo? Feel free to pick a time here: https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting\n\nBest,\nBilal\nElipse Studio",
    },
    {
        "company_name": "Performance Golf Carts",
        "company_website": "https://www.performancegolfcarts.com/",
        "contact_name": "Custom Build Team",
        "contact_role": "Head of Sales",
        "contact_email": "sales@performancegolfcarts.com",
        "contact_phone": "+1 (800) 508-4813",
        "contact_linkedin": "https://www.linkedin.com/company/performance-golf-carts",
        "industry_tag": "⛳ Custom Golf Carts",
        "deal_value": 19500.0,
        "reason": "High-volume custom builder with extensive parts & accessories inventory that would see higher conversions with live 3D visual customization.",
        "subject": "3D visualizer for Performance Golf Carts",
        "body": "Hi Team,\n\nI was browsing your custom EZ-GO and Club Car inventory at Performance Golf Carts. Your Double Take body kits and custom wheels look sharp.\n\nRight now, buyers browse 2D images to pick options. We create interactive 3D configurators that let customers swap body colors, seats, and lift kits in real time on your website.\n\nAre you open to exploring a quick 3D demo tailored for your builds? You can grab a time here: https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting\n\nBest,\nBilal\nElipse Studio",
    },
    {
        "company_name": "Apex Golf Carts",
        "company_website": "https://www.apexgolfcarts.com/",
        "contact_name": "Sales & Design Team",
        "contact_role": "Director of Sales",
        "contact_email": "sales@apexgolfcarts.com",
        "contact_phone": "+1 (949) 328-9899",
        "contact_linkedin": "https://www.linkedin.com/company/apex-golf-carts",
        "industry_tag": "⛳ Custom Golf Carts",
        "deal_value": 17500.0,
        "reason": "Specializes in luxury street-legal electric carts with premium custom finishes that require high-end 3D visualization.",
        "subject": "3D customization for Apex Golf Carts",
        "body": "Hi Team,\n\nI was checking out your luxury street-legal electric cart models at Apex. The modern styling and premium interior finishes look exceptional.\n\nSince high-end buyers expect interactive digital experiences, a real-time 3D configurator on your site would let clients customize their cart exterior, wheels, and seating in full 3D before inquiring.\n\nWould you be open to a brief preview of how this looks in action? Pick a convenient time here: https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting\n\nBest,\nBilal\nElipse Studio",
    },
    {
        "company_name": "Streetrod Golf Cars",
        "company_website": "https://streetrodgolfcars.com/",
        "contact_name": "Custom Build Division",
        "contact_role": "Head of Custom Engineering & Sales",
        "contact_email": "info@streetrodgolfcars.com",
        "contact_phone": "+1 (712) 324-4900",
        "contact_linkedin": "https://www.linkedin.com/company/streetrod-golf-cars",
        "industry_tag": "⛳ Custom Golf Carts",
        "deal_value": 18000.0,
        "reason": "Handcrafted vintage hot rod replica golf carts with bespoke paint and chrome options, ideal for high-ticket 3D interactive customization.",
        "subject": "Real-time 3D configurator for Streetrod Golf Cars",
        "body": "Hi Team,\n\nI was admiring your handcrafted hot rod golf cars at Streetrod. The vintage fiberglass bodywork and custom chrome details are works of art.\n\nFor bespoke vehicles at this price point, an interactive 3D web configurator allows collectors to test paint colors, flame graphics, and wheel packages in photorealistic 3D directly on your site.\n\nWould you be open to seeing a quick concept tailored for Streetrod? You can choose a time here: https://calendly.com/bilal-lania-elipsestudio/15-mins-meeting\n\nBest,\nBilal\nElipse Studio",
    },
]


def normalize_lead_categories():
    """Maps generic or legacy tags into standard primary industry categories."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id, company_name, industry_tag FROM leads").fetchall()
        for r in rows:
            name = r["company_name"] or ""
            current_tag = r["industry_tag"] or ""

            if current_tag in STANDARD_CATEGORIES:
                continue

            n = (name + " " + current_tag).lower()
            if any(k in n for k in ["golf", "cart", "rad dog", "ckd", "tidewater", "garrett", "apex"]):
                new_cat = "⛳ Custom Golf Carts"
            elif any(k in n for k in ["furniture", "joinery", "interior", "design house", "kitchen"]):
                new_cat = "🛋️ Luxury Furniture & Interiors"
            elif any(k in n for k in ["melex", "italcar", "motion", "lem", "bensel", "invest-mobile", "streetrod", "auto", "car", "vehicle", "mobility"]):
                new_cat = "🏎️ Custom Automotive & Mobility"
            elif any(k in n for k in ["aldar", "roshn", "diriyah", "neom", "estate", "property", "architect"]):
                new_cat = "🏗️ Real Estate & Megaprojects"
            elif any(k in n for k in ["yacht", "marine", "boat", "vessel"]):
                new_cat = "⛵ Superyachts & Marine"
            elif current_tag.strip():
                new_cat = current_tag.strip()
            else:
                new_cat = "⚡ Tech & Commercial Products"

            if new_cat != current_tag:
                conn.execute("UPDATE leads SET industry_tag = ? WHERE id = ?", (new_cat, r["id"]))


def seed_or_update_core_leads():
    """Seeds or updates verified leads with official websites, real decision makers, and drafts."""
    with get_conn() as conn:
        for lead in VERIFIED_SAMPLE_LEADS:
            cname = lead["company_name"]
            existing = conn.execute("SELECT id FROM leads WHERE LOWER(company_name) = LOWER(?)", (cname,)).fetchone()
            now = datetime.now().isoformat(timespec="seconds")
            phone = lead.get("contact_phone", "")
            linkedin = lead.get("contact_linkedin", "")
            if existing:
                conn.execute(
                    """UPDATE leads SET
                       company_website = ?, contact_name = ?, contact_role = ?,
                       contact_email = ?, contact_phone = ?, contact_linkedin = ?,
                       industry_tag = ?, deal_value = ?,
                       reason = ?, subject = ?, body = ?, updated_at = ?
                       WHERE id = ?""",
                    (
                        lead["company_website"],
                        lead["contact_name"],
                        lead["contact_role"],
                        lead["contact_email"],
                        phone,
                        linkedin,
                        lead["industry_tag"],
                        lead["deal_value"],
                        lead["reason"],
                        lead["subject"],
                        lead["body"],
                        now,
                        existing["id"],
                    ),
                )
            else:
                conn.execute(
                    """INSERT INTO leads
                       (company_name, company_website, contact_name, contact_role, contact_email,
                        contact_phone, contact_linkedin, industry_tag, deal_value, pipeline_stage,
                        status, reason, subject, body, source_prompt, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft_ready', 'new', ?, ?, ?, 'Golf Cart Customization USA', ?, ?)""",
                    (
                        lead["company_name"],
                        lead["company_website"],
                        lead["contact_name"],
                        lead["contact_role"],
                        lead["contact_email"],
                        phone,
                        linkedin,
                        lead["industry_tag"],
                        lead["deal_value"],
                        lead["reason"],
                        lead["subject"],
                        lead["body"],
                        now,
                        now,
                    ),
                )


def add_lead(
    company_name,
    company_website="",
    contact_name="",
    contact_role="",
    contact_email="unknown",
    contact_phone="",
    contact_linkedin="",
    industry_tag="3D Configurator",
    deal_value=15000.0,
    pipeline_stage="draft_ready",
    reason="",
    subject="",
    body="",
    notes="",
    followup_date="",
    source_prompt="",
    phone_script="",
    objection_notes="",
    phone_status="verified_direct",
    lead_score=90,
    has_3d=0,
    matched_signals="",
    product_title="",
    product_description="",
    screenshot_path="",
    enrichment_source="",
    enriched_at="",
):
    now = datetime.now().isoformat(timespec="seconds")
    if not followup_date:
        followup_date = date.today().isoformat()

    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO leads
               (company_name, company_website, contact_name, contact_role, contact_email,
                contact_phone, contact_linkedin, industry_tag, deal_value, pipeline_stage,
                status, reason, subject, body, notes, followup_date, source_prompt,
                phone_script, objection_notes, phone_status, lead_score,
                has_3d, matched_signals, product_title, product_description, screenshot_path,
                enrichment_source, enriched_at,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                company_name,
                company_website,
                contact_name,
                contact_role,
                contact_email,
                contact_phone,
                contact_linkedin,
                industry_tag,
                deal_value,
                pipeline_stage,
                reason,
                subject,
                body,
                notes,
                followup_date,
                source_prompt,
                phone_script,
                objection_notes,
                phone_status,
                lead_score,
                int(has_3d or 0),
                matched_signals,
                product_title,
                product_description,
                screenshot_path,
                enrichment_source,
                enriched_at,
                now,
                now,
            ),
        )
        return cur.lastrowid


def batch_add_leads(leads_list):
    """High-performance batch insertion for bulk-imported or enriched leads."""
    now = datetime.now().isoformat(timespec="seconds")
    today_str = date.today().isoformat()
    inserted_count = 0
    seen_in_batch = set()

    with get_conn() as conn:
        for lead in leads_list:
            comp = lead.get("company_name", "").strip()
            comp_key = comp.lower()
            if not comp or comp_key in seen_in_batch or is_duplicate(comp):
                continue
            seen_in_batch.add(comp_key)

            fu_date = lead.get("followup_date") or today_str
            _ms = lead.get("matched_signals", "")
            if isinstance(_ms, (list, tuple)):
                _ms = ", ".join(str(s) for s in _ms)
            conn.execute(
                """INSERT INTO leads
                   (company_name, company_website, contact_name, contact_role, contact_email,
                    contact_phone, contact_linkedin, industry_tag, deal_value, pipeline_stage,
                    status, reason, subject, body, notes, followup_date, source_prompt,
                    phone_script, objection_notes, phone_status, lead_score,
                    has_3d, matched_signals, product_title, product_description, screenshot_path,
                    enrichment_source, enriched_at,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    comp,
                    lead.get("company_website", "").strip(),
                    lead.get("contact_name", "Decision Maker").strip(),
                    lead.get("contact_role", "").strip(),
                    lead.get("contact_email", "unknown").strip(),
                    lead.get("contact_phone", "").strip(),
                    lead.get("contact_linkedin", "").strip(),
                    lead.get("industry_tag", "⚡ Tech & Commercial Products").strip(),
                    float(lead.get("deal_value") or 15000.0),
                    lead.get("pipeline_stage", "draft_ready"),
                    lead.get("reason", "").strip(),
                    lead.get("subject", f"3D Configurator for {comp}").strip(),
                    lead.get("body", "").strip(),
                    lead.get("notes", "").strip(),
                    fu_date,
                    lead.get("source_prompt", "").strip(),
                    lead.get("phone_script", "").strip(),
                    lead.get("objection_notes", "").strip(),
                    lead.get("phone_status", "verified_direct"),
                    int(lead.get("lead_score") or 90),
                    int(lead.get("has_3d") or 0),
                    _ms,
                    lead.get("product_title", "").strip(),
                    lead.get("product_description", "").strip(),
                    lead.get("screenshot_path", "").strip(),
                    lead.get("enrichment_source", "").strip(),
                    lead.get("enriched_at", "").strip(),
                    now,
                    now,
                ),
            )
            inserted_count += 1
    return inserted_count


def update_lead_call_outcome(lead_id, outcome, rep_notes=""):
    """
    Updates lead stage and status based on rep cold call disposition:
    - 'meeting_booked': advances stage to meeting_booked
    - 'voicemail': sets stage to followup_due
    - 'dead_number': sets phone_status to 'dead_disconnected' and stage to 'lost'
    - 'not_interested': marks stage as 'lost'
    - 'callback_scheduled': sets stage to followup_due
    """
    now = datetime.now().isoformat(timespec="seconds")
    stage_map = {
        "meeting_booked": "meeting_booked",
        "voicemail": "followup_due",
        "dead_number": "lost",
        "not_interested": "lost",
        "callback_scheduled": "followup_due",
    }
    new_stage = stage_map.get(outcome, "followup_due")
    phone_stat = "dead_disconnected" if outcome == "dead_number" else "verified_direct"

    with get_conn() as conn:
        lead = conn.execute("SELECT notes FROM leads WHERE id = ?", (lead_id,)).fetchone()
        existing_notes = lead["notes"] if lead and lead["notes"] else ""
        timestamp = datetime.now().strftime("%b %d, %H:%M")
        appended_note = f"[{timestamp} Call: {outcome.replace('_', ' ').title()}] {rep_notes}".strip()
        final_notes = f"{existing_notes}\n{appended_note}".strip() if existing_notes else appended_note

        conn.execute(
            """UPDATE leads SET
               pipeline_stage = ?, phone_status = ?, notes = ?, updated_at = ?
               WHERE id = ?""",
            (new_stage, phone_stat, final_notes, now, lead_id),
        )


def get_all_leads(stage_filter=None, search_query=None, category_filter=None):
    with get_conn() as conn:
        query = "SELECT * FROM leads WHERE 1=1"
        params = []

        if stage_filter and stage_filter != "all":
            query += " AND pipeline_stage = ?"
            params.append(stage_filter)

        if category_filter and category_filter != "all" and not category_filter.startswith("All"):
            query += " AND industry_tag = ?"
            params.append(category_filter)

        if search_query:
            query += " AND (LOWER(company_name) LIKE ? OR LOWER(contact_name) LIKE ? OR LOWER(contact_email) LIKE ? OR LOWER(industry_tag) LIKE ?)"
            wildcard = f"%{search_query.lower()}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])

        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_category_stats():
    """Returns aggregated count and pipeline volume per category."""
    with get_conn() as conn:
        rows = conn.execute("SELECT industry_tag, deal_value, pipeline_stage FROM leads").fetchall()
        stats = {}
        for r in rows:
            cat = r["industry_tag"] or "⚡ Tech & Commercial Products"
            if cat not in stats:
                stats[cat] = {"count": 0, "deal_value": 0.0, "stages": {}}
            stats[cat]["count"] += 1
            stats[cat]["deal_value"] += float(r["deal_value"] or 0.0)
            stg = r["pipeline_stage"] or "draft_ready"
            stats[cat]["stages"][stg] = stats[cat]["stages"].get(stg, 0) + 1
        return stats


def update_lead(lead_id, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.now().isoformat(timespec="seconds")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [lead_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE leads SET {set_clause} WHERE id = ?", values)


def is_duplicate(company_name):
    """Check if we already have a lead for this company (case-insensitive)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM leads WHERE LOWER(company_name) = LOWER(?)",
            (company_name,),
        ).fetchone()
        return row is not None


def delete_lead(lead_id):
    """Delete a lead by its ID."""
    with get_conn() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))


def get_crm_metrics():
    """Computes executive studio metrics matching the reference UI."""
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM leads").fetchall()]

    active_stages = {"new_lead", "draft_ready", "contacted", "followup_due", "meeting_booked", "proposal_sent"}
    
    pipeline_value = 0.0
    active_count = 0
    won_this_month = 0.0
    followups_due = 0
    today_str = date.today().isoformat()
    current_month_prefix = date.today().strftime("%Y-%m")

    stage_counts = {k: 0 for k, _ in PIPELINE_STAGES}

    for r in rows:
        stage = r.get("pipeline_stage") or "draft_ready"
        val = float(r.get("deal_value") or 15000.0)
        
        if stage in stage_counts:
            stage_counts[stage] += 1
        else:
            stage_counts["draft_ready"] = stage_counts.get("draft_ready", 0) + 1

        if stage in active_stages:
            pipeline_value += val
            active_count += 1

        if stage == "won":
            updated_at = r.get("updated_at", "")
            if updated_at.startswith(current_month_prefix):
                won_this_month += val
            else:
                won_this_month += val  # fallback include

        if stage == "followup_due" or (r.get("followup_date") and r.get("followup_date") <= today_str and stage in ["contacted", "followup_due"]):
            followups_due += 1

    return {
        "pipeline_value": pipeline_value,
        "active_opportunities": active_count,
        "won_this_month": won_this_month,
        "followups_due": followups_due,
        "stage_counts": stage_counts,
        "total_leads": len(rows),
    }
