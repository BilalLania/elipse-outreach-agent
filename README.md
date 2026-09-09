# 🎯 Elipse Studio — AI Outreach Agent & Lead CRM

A Streamlit sales CRM for **Elipse Studio** (3D configurators, CGI, 3D visualisation, VR/AR).
It discovers prospect companies with AI, enriches their contacts, scans their websites with a
real browser to check whether they already have 3D tech, and produces cold-call battlecards and
email drafts — all tracked in a local SQLite pipeline.

---

## ⚡ What It Does

| Module | Role |
|---|---|
| `app.py` | Streamlit UI — 8 tabs (Today, Sales Terminal, Cold Call Desk, Problem Desk, Pipeline, Contacts, Follow-ups, AI Lead Finder) |
| `agent_core.py` | Gemini agent (multi-model cascade), Hunter.io + SignalHire enrichment, battlecard generation, site/lead match verification |
| `scraper.py` | **Playwright site scanner** — detects existing 3D tech, grabs product intel, screenshots the page |
| `lead_engine.py` | Apollo.io API, CSV importer with column auto-mapping, phone scrubbing |
| `db.py` | SQLite CRM — leads, pipeline stages, sales problems, migrations |
| `team_analytics.py` | Pulls outbound call stats from a Google Sheet (with cached fallback) |

### Lead discovery (`AI Lead Finder` / `Cold Call Desk → Free AI Web Discovery`)
1. You describe your ICP → Gemini returns N companies (**slider: 5–25 per run**)
2. Website verified/resolved via DuckDuckGo
3. Duplicates skipped, Hunter.io + SignalHire enrichment applied
4. Gemini writes a 20-second cold-call script + objection rebuttals + email draft
5. Saved to SQLite

### Bulk import
Drag-and-drop CSV from **Apollo / ZoomInfo / Clay / Sales Navigator** — columns auto-mapped, phone
numbers normalised, switchboards flagged. Optional checkboxes for site-scanning and deep enrichment.

---

## 🕷️ The Site Scanner (`scraper.py`)

Runs in a **separate process** (Playwright's sync API cannot launch a browser from Streamlit's
worker thread — on Windows that raises `NotImplementedError`).

**Pipeline:** headless Chromium (1366×900, real UA) → `domcontentloaded` → `load` → `networkidle`
→ scroll down/up (triggers lazy-loading) → 3s settle → read + screenshot.

**Returns:**

| Field | Meaning |
|---|---|
| `has_3d` | Site already shows interactive 3D tech |
| `matched_signals` | **STRONG** hits: `3d configurator`, `webgl`, `three.js`, `3d viewer`, `360 view`, `virtual tour`, `augmented reality`, `cgi animation` |
| `weak_signals` | **WEAK** mentions that prove nothing: `customize`, `build your own`, `3d model`, `cgi` |
| `product_title` / `product_description` | From `og:title`/`h1`/`title` and `meta description`/`og:description`/`<p>` |
| `screenshot_path` | Viewport PNG in `screenshots/` |
| `http_status`, `blocked` | Detects 403 / Cloudflare / captcha refusals |
| `error` | Never raises — failures return the same shape with `error` set |

**Lead verification.** `agent_core.site_matches_lead()` compares the scraped text against the
company name and its industry keywords and returns one of:

- **match** — page mentions the company or its industry ✅
- **mismatch** — page is about something else → 🚫 *AI most likely hallucinated this lead*
- **blocked** — the site refused the scanner → 🛡️ *proves nothing; check manually*
- **unknown** — too little text to judge

**Where it runs:** the 🔍 *Scan site* button on any lead card · optional checkbox during CSV/Apollo
import · CLI. It does **not** run automatically during AI discovery.

```bash
python -m scraper https://example.com                    # default
python -m scraper https://example.com shot.png 20000 5000  # url, path, nav timeout, settle ms
```

---

## 🚀 Local Setup

```bash
git clone <your-repo-url>
cd elipse-outreach-agent
pip install -r requirements.txt
playwright install chromium          # required for the site scanner
streamlit run app.py                 # http://localhost:8501
```

### `.env` (copy from `.env.example`)

```env
GEMINI_API_KEY=your_gemini_api_key_here        # required
HUNTER_API_KEY=your_hunter_api_key_here        # emails/phones — strongly recommended
SIGNALHIRE_API_KEY=your_signalhire_api_key     # optional, limited (see below)
APOLLO_API_KEY=your_apollo_api_key             # optional, paid plans only
CALENDAR_LINK=https://calendly.com/you/15-mins
```

> Set **only one** of `GEMINI_API_KEY` / `GOOGLE_API_KEY` — the app normalises to `GEMINI_API_KEY`
> at startup, but a stale second key in your OS environment causes confusion.

---

## ⚠️ Known Limitations

| Item | Status |
|---|---|
| **SignalHire email/phone reveal** | ❌ Not wired. SignalHire's Person API is **callback-only** — it POSTs results to a public HTTPS URL you must host. Only its synchronous `searchByQuery` (job-title verification, no contacts) is used, and it is rate-limited on small plans. |
| **AI hallucination** | ⚠️ Gemini sometimes invents companies and attaches unrelated live domains. The site scanner catches this (**mismatch** verdict) — **always scan an AI lead before calling or emailing.** |
| **Playwright on Streamlit Cloud** | ❌ No runtime browser install. Scans work locally; on Cloud they fail gracefully with an `error`. A Docker host (`playwright install --with-deps chromium`) is the fix. |
| **Bot-protected sites** | Some sites 403 everything non-browser. Reported as **blocked** — not a bad lead. |
| **SQLite persistence** | `leads.db` is local and gitignored. On Streamlit Cloud it is **ephemeral** — use Postgres/Supabase for real multi-user use. |
| **Apollo free plan** | Blocks REST API (403). Use the CSV tab instead. |
| **Gemini free tier** | ~20 requests/day. Each lead costs ~1 extra call, so runs above ~12 leads can exhaust the daily quota. |

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push to GitHub, then create the app at [share.streamlit.io](https://share.streamlit.io/) pointing at `app.py`.
2. Add your keys under **Advanced Settings → Secrets** (TOML):
   ```toml
   GEMINI_API_KEY = "..."
   HUNTER_API_KEY = "..."
   SIGNALHIRE_API_KEY = "..."
   CALENDAR_LINK = "https://calendly.com/you/15-mins"
   ```
3. `packages.txt` ships the apt libraries headless Chromium needs. The **browser binary itself is
   not installed at runtime**, so site scanning is disabled on Cloud (everything else works).

---

## 🔒 Security

`.env`, `leads.db`, `screenshots/` and `product.png` are gitignored. Keep real API keys in `.env`
(or Streamlit Secrets) — **never** in `.env.example`, which is committed.
