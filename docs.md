# Implementation Log

Running record of features shipped, bugs fixed, and how each was verified.
Newest entry first. See `CLAUDE.md` for the logging rule.

Status key: ✅ Working · ⚠️ Partial · ❌ Not done

---

## 2026-09-09

### Features added

**Playwright site scanner — `scraper.py` (new)** ✅
Opens a prospect's website in headless Chromium and reports whether they already have interactive
3D tech, plus product intel and a screenshot. Runs in a **separate process** because Playwright's
sync API cannot launch a browser from Streamlit's worker thread.
- STRONG signals set `has_3d`: `3d configurator`, `webgl`, `three.js`, `3d viewer`, `360 view`,
  `virtual tour`, `augmented reality`, `cgi animation`
- WEAK mentions reported but never set `has_3d`: `customize`, `build your own`, `3d model`, `cgi`
- Returns `http_status` + `blocked` (403 / Cloudflare / captcha detection)
- Never raises — all failures return the same dict shape with `error` set
- CLI: `python -m scraper <url> [png] [nav_ms] [settle_ms]`

*Verified:* live scans of gowithgarretts.com, apexgolfcarts.com, tidewatercarts.com,
mowlemandco.com. Screenshots written to `screenshots/`, product titles extracted correctly.

**Lead verification — `agent_core.site_matches_lead()`** ✅
Cross-checks that a scraped page actually belongs to the lead. Returns `match` / `mismatch` /
`blocked` / `unknown`. Catches AI-hallucinated leads.
- *Verified:* 5/5 cases — Papilio Bespoke Kitchens (a Law-of-Attraction book site) → **mismatch**;
  Garrett's → **match**; Mowlem & Co (HTTP 403) → **blocked**; Cloudflare page → **blocked**;
  Ultimate Golf Carts (no text) → **unknown**.
- Works on already-saved leads without re-scanning.

**SignalHire enrichment — `agent_core.enrich_lead()`** ⚠️ Partial
Only the conservative case is wired: a lead with a real person's name + distinct company match
gets their verified job title via the synchronous `searchByQuery` endpoint.
- ❌ **Email/phone reveal not available.** SignalHire's Person API is callback-only — it POSTs
  results to a public HTTPS URL we do not host. `POST /candidate/search` returns
  `406 "Callback url is required"` without one.
- ⚠️ `searchByQuery` is rate-limited on the current plan (returned 36 profiles, then 0 minutes
  later). `enrich_lead` degrades to "no change" — never crashes.
- *Verified:* key valid (`GET /credits` → 5 credits). Hal Garrett → "President @ Go With Garrett's
  Golf Cars". Placeholder names ("Custom Sales Team") deliberately skipped — company-only search
  returned garbage.

**Adjustable lead count** ✅
`run_agent(..., max_leads=N)` (clamped 1–25) replaces the hardcoded "3 to 5" prompt. UI slider
(5–25, default 8) added to the AI Lead Finder and Cold Call Desk → Free AI Web Discovery, with a
caption warning about the ~20/day Gemini free quota.
- *Verified:* signature, clamp, prompt interpolation, and `candidates[:max_leads]` slice all
  present in the user's real environment.

**New DB columns** ✅
`has_3d`, `matched_signals`, `product_title`, `product_description`, `screenshot_path`,
`enrichment_source`, `enriched_at` — added via the existing `init_db()` migration dict and wired
into `add_lead()` / `batch_add_leads()`.
- *Verified:* migration + insert round-trip on a copy of `leads.db`.

**UI** ✅
`render_site_scan_ui()` added to lead cards on Today / Cold Call Desk / Pipeline / Contacts:
**🔍 Scan site** and **✨ Deep enrich (Hunter + SignalHire)** buttons, verdict banner, screenshot
behind a checkbox. Sidebar now shows SignalHire and Playwright status. CSV/Apollo import gained
default-off `scrape` / `enrich` checkboxes.

### Bugs fixed

| Bug | Fix | Verified |
|---|---|---|
| Playwright `NotImplementedError` inside Streamlit (Windows) | Run scan via subprocess (`scan_site`) | ✅ live scan works in-app |
| Screenshot taken before page finished loading | `load` → `networkidle` → scroll down/up → 3s settle | ✅ Apex Golf Carts **+76% content**; "Featured Products" images now render (visual diff) |
| Blocked sites (403) reported as fake leads | `blocked` verdict added, checked before `mismatch` | ✅ mowlemandco.com → `403, blocked:True` |
| `has_3d` false positive on the word "customize" | Split STRONG vs WEAK signal lists | ✅ Garrett's → `has_3d:false`, `weak:["customize"]` |
| `batch_add_leads` didn't dedupe **within** one batch (uncommitted-transaction visibility) | Added in-batch `seen` set | ✅ 3 duplicate variants → 1 insert |
| `.streamlit/config.toml` had a UTF-8 BOM → TOML parse crash on startup | Rewrote file without BOM | ✅ parses, app starts |
| `st.set_page_config()` not first (st.secrets read before it) | Reordered; secrets read guarded by file existence | ✅ app starts |
| "No secrets found" console spam | All key lookups go through `_secret()`; empty env vars treated as unset | ✅ |
| "Both GOOGLE_API_KEY and GEMINI_API_KEY are set" spam | Drop `GOOGLE_API_KEY` at startup when `GEMINI_API_KEY` present | ✅ |
| google-genai "AFC not recommended" spam | Logger suppression | ✅ |
| Nested `st.expander` crash (screenshot inside a lead card) | Replaced with `st.checkbox` | ✅ |
| Screenshots huge (1366×5222) | Viewport-only capture + 420px display | ✅ now 1366×900 |
| Junk `"0"` shown as product description | Skip text <12 chars / numeric-only | ✅ |
| "Hi Custom," / "Hi Sales," in call scripts for team-name contacts | Non-personal-name detection → "Hi there," | ✅ |
| Stale "Spoke with receptionist…" on every card | It was placeholder text; genericized | ✅ |
| **Regression caught in pre-commit review:** with `scrape=True`, the scrape note overwrote `reason`, so `lead.get("reason") or battlecard...` silently **dropped the AI-written `how_we_help`**. Also `site_note` was only assigned inside `elif` branches, so it could **leak from the previous lead** in the loop. | `site_note = ""` reset per iteration; reason now built as `note + battlecard_reason` | ✅ 4-lead test: note+AI reason both kept, blocked lead gets no note, no leak to the next lead, and `scrape=False` output is byte-identical to main-branch behaviour |

### Behaviour changes vs `main` (no bug, but know about these)

| Change | Impact |
|---|---|
| **`run_agent` now calls `enrich_lead()` for every discovered lead** (`agent_core.py:810`) — this did not exist on main. | Adds a SignalHire `searchByQuery` call per lead. Cannot crash (wrapped in try/except), and normally returns in <2s because the endpoint is rate-limited. **But `signalhire_search` has a 15s timeout**, so a worst case of 25 leads × 15s ≈ **6 extra minutes** on a large run. Lower the timeout if this bites. |
| **`agent_core` mutates `os.environ` at import** (`agent_core.py:48-52`) — pops `GOOGLE_API_KEY`. | Only pops when `GEMINI_API_KEY` is also set; otherwise it migrates `GOOGLE_API_KEY` → `GEMINI_API_KEY` first, so no key is ever lost. Done to stop the SDK's "Both … are set" spam and make which key is used deterministic. |
| **Screenshots are viewport-only** (`full_page=True` removed). | 1366×900 instead of 1366×5222. Below-the-fold content is no longer captured — deliberate, for display size. |
| **Scans take ~5-7s longer.** | `load` + `networkidle` + scroll + 3s settle replaced a flat 1.5s wait. Necessary: pages were being shot before images loaded. |
| **`has_3d` and signals are cleared when a site is `blocked`.** | A 403 page obviously has no 3D — recording "none found" there would be a false negative. |
| **Key lookups treat empty env vars as unset** (`_secret()`). | `HUNTER_API_KEY=` (blank) now returns `None` instead of falling through to `st.secrets`. On Streamlit Cloud `secrets.toml` exists so `st.secrets` is still read — no regression there. |

### Files touched

`scraper.py` (new) · `packages.txt` (new) · `.env` (new) · `CLAUDE.md` (new) · `docs.md` (new) ·
`agent_core.py` · `app.py` · `db.py` · `lead_engine.py` · `requirements.txt` · `.gitignore` ·
`.env.example` · `.streamlit/config.toml` · `README.md`

### Test run (user's Windows Python 3.13 + real `.env`)

✅ Streamlit health `ok` · all 5 modules import · Gemini client constructs · phone scrubbing
(5/5 cases) · CSV column auto-mapping · category mapping · JSON extraction · DB migration +
inserts + metrics · team analytics **live** from Google Sheet (2,954 dials, 5 meetings, 18%
contact rate) · scraper live scans · `scan_site` subprocess round-trip.

### Pre-commit regression review

Ran before handing the branch over. Checked: functions removed or renamed (**none**), signature
changes (**all additive with defaults** — `max_leads=5`, `enrich=False`, `scrape=False`,
`blocked=False`, `settle_ms=3000`, so existing callers keep working), circular imports
(**none** — `scraper.py` imports nothing from the project), DB INSERT placeholder counts
(minimal args / all-new args / batch / dedup / `update_lead(**fields)` / metrics — all pass),
all 11 call sites pass valid arguments, and all 5 modules import cleanly.

One real regression was found and fixed (see the last row of the bug table above).

### Known gaps carried forward

- ❌ **`HUNTER_API_KEY` is empty in `.env`** — this is the app's only working source of verified
  emails/phones. Biggest available improvement.
- ❌ SignalHire contact reveal — needs a public callback receiver + tunnel/deployment.
- ❌ Playwright on Streamlit Cloud — no runtime browser install by decision; scans are local-only
  and fail gracefully on Cloud.
- ⚠️ Gemini still hallucinates companies. The scanner flags them, but every AI lead should be
  scanned before outreach.
- ❌ No "edit website" field on lead cards (AI sometimes returns a wrong domain).
- ⚠️ `CALENDAR_LINK` in `.env` is still the placeholder and appears in draft emails.
