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
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                now,
                now,
            ),
        )
        return cur.lastrowid


def get_all_leads(stage_filter=None, search_query=None):
    with get_conn() as conn:
        query = "SELECT * FROM leads WHERE 1=1"
        params = []

        if stage_filter and stage_filter != "all":
            query += " AND pipeline_stage = ?"
            params.append(stage_filter)

        if search_query:
            query += " AND (LOWER(company_name) LIKE ? OR LOWER(contact_name) LIKE ? OR LOWER(contact_email) LIKE ? OR LOWER(industry_tag) LIKE ?)"
            wildcard = f"%{search_query.lower()}%"
            params.extend([wildcard, wildcard, wildcard, wildcard])

        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


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
