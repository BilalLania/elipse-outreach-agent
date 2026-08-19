"""
db.py — Simple persistent storage for leads/drafts using SQLite.

SQLite stores everything in a single file (leads.db) — no server to
install or run. This is what makes the system "remember" leads between
runs, instead of the old version that only wrote to a text file.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "leads.db"


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
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                company_website TEXT,
                contact_email TEXT,
                reason TEXT,
                subject TEXT,
                body TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                source_prompt TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def add_lead(company_name, company_website, contact_email, reason, subject, body, source_prompt):
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO leads
               (company_name, company_website, contact_email, reason, subject, body,
                status, source_prompt, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?, ?)""",
            (company_name, company_website, contact_email, reason, subject, body,
             source_prompt, now, now),
        )
        return cur.lastrowid


def get_all_leads(status_filter=None):
    with get_conn() as conn:
        if status_filter and status_filter != "all":
            rows = conn.execute(
                "SELECT * FROM leads WHERE status = ? ORDER BY created_at DESC",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leads ORDER BY created_at DESC"
            ).fetchall()
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


def get_stats():
    """Returns count of leads grouped by status."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as count FROM leads GROUP BY status"
        ).fetchall()
        stats = {r["status"]: r["count"] for r in rows}
        stats["total"] = sum(stats.values())
        return stats

