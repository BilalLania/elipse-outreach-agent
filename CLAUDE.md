# CLAUDE.md

Guidance for Claude Code when working in this repository.

---

## 📋 MANDATORY: Log every change to `docs.md`

**After finishing any implementation AND its tests pass, append an entry to `docs.md` before
reporting back to the user.** This is not optional and does not need to be asked for.

An entry must record:

| Field | What to write |
|---|---|
| **Date** | `YYYY-MM-DD` heading (group all of a day's work under one date) |
| **What changed** | Feature added / bug fixed — one line each, plain language |
| **Files touched** | File names only, no line numbers |
| **How it was verified** | The actual command run and its result. "Compiles" is not verification. |
| **Status** | ✅ Working · ⚠️ Partial (say what's missing) · ❌ Not done (say why) |

Rules:
- **Never log something as done or tested unless it actually ran and passed.** If a test was
  skipped or a feature is untested, say so explicitly.
- Newest date at the **top** of the log.
- Keep entries short — scannable bullets, not prose.
- If a change is later reverted or found broken, add a correcting entry rather than editing
  history.

---

## Project

Streamlit sales CRM for **Elipse Studio** (3D configurators, CGI, 3D visualisation, VR/AR).
Discovers prospects with Gemini, enriches contacts, scans their websites with Playwright to see
whether they already have 3D tech, and produces cold-call battlecards. Local SQLite storage.

| File | Role |
|---|---|
| `app.py` | Streamlit UI — 8 tabs, dispatched off `st.session_state["active_tab"]` |
| `agent_core.py` | Gemini agent + model cascade, Hunter.io / SignalHire, `site_matches_lead()` |
| `scraper.py` | Playwright site scanner (runs in a subprocess) |
| `lead_engine.py` | Apollo API, CSV importer, phone scrubbing |
| `db.py` | SQLite CRM + runtime column migrations |
| `team_analytics.py` | Google Sheet call stats with cached fallback |

## Commands

```bash
streamlit run app.py                  # dashboard on :8501
python -m scraper <url> [png] [nav_ms] [settle_ms]
python -m py_compile *.py             # syntax check
```

## Conventions & gotchas

- **`st.set_page_config()` must be the first Streamlit call** in `app.py`. Do not access
  `st.secrets` before it.
- **No nested `st.expander`.** Lead cards on Today/Pipeline/Contacts are already expanders — use
  `st.checkbox` or plain containers inside them.
- **Playwright must run in a subprocess** (`scraper.scan_site`). Its sync API cannot launch a
  browser from Streamlit's worker thread — Windows raises `NotImplementedError`.
- **`scraper.check_configurator()` must never raise.** Every failure path returns the same dict
  shape with `error` populated.
- **Enrichment merges are additive only** — never overwrite an existing verified email/phone.
- **Key lookups go through `agent_core._secret()`**, which treats empty env vars as unset and only
  touches `st.secrets` when a `secrets.toml` exists.
- **Never put a real API key in `.env.example`** (it is committed). Real keys live in `.env`.
- Working tree uses **CRLF**; committed blobs are LF. Use `git -c core.autocrlf=input diff` to see
  a meaningful diff.
- `db.init_db()` runs on every rerun and re-seeds sample leads — keep it cheap.

## Testing

The sandbox lacks the project's deps. Run real tests through the user's Windows interpreter:

```bash
"/mnt/c/Users/786 TRADERS/AppData/Local/Programs/Python/Python313/python.exe" -c "..."
```

Use a **copy** of `leads.db` for DB tests, never the live file.
