"""
scraper.py — Playwright site-intelligence scraper for Elipse Studio outreach.

Given a prospect's website, reports whether they already show interactive 3D /
visualization tech (configurator, CGI, WebGL viewer, virtual tour), grabs a
product title + description, and saves a screenshot.

Designed to NEVER raise: every failure path returns the same dict shape with
`error` populated so the Streamlit app stays usable even when scraping is blocked.

Playwright + its Chromium binary are expected to be installed already
(`pip install playwright && playwright install chromium`). This module does not
install anything at runtime.

CLI:  python -m scraper https://example.com
"""

import os
import sys
import json
import subprocess

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - import guard for environments without playwright
    sync_playwright = None


# STRONG signals = real interactive-3D / visualization tech already on the site.
# Any one of these flips has_3d=True (lead already has what Elipse sells -> lower priority).
STRONG_SIGNALS = [
    "3d configurator",
    "configurator",
    "3d viewer",
    "3d visualization",
    "3d visualisation",
    "webgl",
    "three.js",
    "babylon.js",
    "360 view",
    "360-degree",
    "virtual tour",
    "virtual showroom",
    "augmented reality",
    " ar viewer",
    "cgi animation",
]

# WEAK mentions = marketing words that do NOT prove a 3D experience exists.
# Reported for context only; they never set has_3d.
WEAK_SIGNALS = [
    "customize",
    "customise",
    "build your own",
    "design your own",
    "3d model",
    "cgi",
]

# Back-compat alias (some callers may still import this name).
SIGNAL_KEYWORDS = STRONG_SIGNALS

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


# Text that means "the site refused us", not "the site is unrelated".
BLOCK_PHRASES = [
    "403 - forbidden", "403 forbidden", "access denied", "access to this page is forbidden",
    "401 unauthorized", "not authorized", "429 too many requests", "too many requests",
    "rate limit", "just a moment", "checking your browser", "attention required",
    "cloudflare", "ddos protection", "captcha", "are you a robot", "verify you are human",
    "enable javascript", "service unavailable", "502 bad gateway", "503 service",
    "404 not found", "page not found", "site can't be reached",
]


def looks_blocked(text: str) -> bool:
    t = " ".join((text or "").lower().split())
    if not t:
        return False
    return any(p in t for p in BLOCK_PHRASES)


def _blank_result(screenshot_path: str = "", error: str = "") -> dict:
    return {
        "has_3d": False,
        "matched_signals": [],
        "weak_signals": [],
        "product_title": "",
        "product_description": "",
        "screenshot_path": screenshot_path if not error else "",
        "http_status": 0,
        "blocked": False,
        "error": error,
    }


def _first_text(page, selectors) -> str:
    for sel, attr in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0:
                continue
            if attr:
                val = loc.get_attribute(attr, timeout=1500)
            else:
                val = loc.inner_text(timeout=1500)
            val = " ".join((val or "").split())
            # skip empty / trivially short / purely numeric fragments
            if len(val) >= 12 and not val.isdigit():
                return val[:600]
        except Exception:
            continue
    return ""


def check_configurator(url: str, screenshot_path: str = "product.png", timeout_ms: int = 20000, settle_ms: int = 3000) -> dict:
    """
    Visit `url`, detect interactive-3D signals, extract a product title/description,
    and screenshot the page. Returns a dict; never raises.
    """
    if not url or not isinstance(url, str):
        return _blank_result(error="no url provided")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url.strip()

    if sync_playwright is None:
        return _blank_result(error="playwright not installed")

    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(user_agent=DEFAULT_UA, viewport={"width": 1366, "height": 900})
            page = context.new_page()
            page.set_default_timeout(timeout_ms)

            http_status = 0
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if resp is not None:
                    http_status = resp.status or 0
            except Exception as e:
                return _blank_result(error=f"navigation failed: {e}")

            # Let the page actually finish rendering before reading it or shooting it.
            # Each step is best-effort: some sites never reach "networkidle" (analytics
            # polling, chat widgets), so a timeout here must not fail the whole scan.
            for state in ("load", "networkidle"):
                try:
                    page.wait_for_load_state(state, timeout=6000)
                except Exception:
                    pass

            # Nudge lazy-loaded hero images / sliders into rendering, then return to top.
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(600)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(400)
            except Exception:
                pass

            # Final settle for fonts / CSS transitions / hero animations.
            try:
                page.wait_for_timeout(max(0, int(settle_ms)))
            except Exception:
                pass

            try:
                html = (page.content() or "").lower()
            except Exception:
                html = ""

            matched = sorted({k for k in STRONG_SIGNALS if k in html})
            weak = sorted({k for k in WEAK_SIGNALS if k in html})

            product_title = _first_text(
                page,
                [
                    ('meta[property="og:title"]', "content"),
                    ("h1", None),
                    ("title", None),
                ],
            )
            product_description = _first_text(
                page,
                [
                    ('meta[name="description"]', "content"),
                    ('meta[property="og:description"]', "content"),
                    ("main p", None),
                    ("p", None),
                ],
            )

            saved_path = ""
            try:
                # Viewport only (not full_page) — an above-the-fold hero shot is enough to
                # eyeball the site and keeps files ~50KB instead of multi-MB 5000px strips.
                page.screenshot(path=screenshot_path)
                saved_path = screenshot_path
            except Exception:
                saved_path = ""

            blocked = http_status >= 400 or looks_blocked(f"{product_title} {product_description}")

            return {
                "has_3d": bool(matched) and not blocked,
                "matched_signals": [] if blocked else matched,
                "weak_signals": [] if blocked else weak,
                "product_title": product_title,
                "product_description": product_description,
                "screenshot_path": saved_path,
                "http_status": http_status,
                "blocked": blocked,
                "error": "",
            }
    except Exception as e:
        return _blank_result(error=str(e))
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass


def scan_site(url: str, screenshot_path: str = "product.png", timeout_ms: int = 20000, settle_ms: int = 3000) -> dict:
    """
    Process-isolated wrapper around check_configurator.

    Playwright's sync API cannot launch its browser subprocess from a non-main
    thread (Streamlit's script runner) — on Windows that raises NotImplementedError.
    Running the scan in a fresh child process sidesteps the event-loop/thread problem
    entirely. This is what the Streamlit app calls.
    """
    if not url:
        return _blank_result(error="no url provided")

    try:
        if screenshot_path and os.path.dirname(screenshot_path):
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
    except Exception:
        pass

    try:
        proc = subprocess.run(
            [sys.executable, os.path.abspath(__file__), url, screenshot_path or "product.png",
             str(int(timeout_ms)), str(int(settle_ms))],
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000) + (settle_ms / 1000) + 75,
        )
    except subprocess.TimeoutExpired:
        return _blank_result(error="scan timed out")
    except Exception as e:
        return _blank_result(error=f"scan subprocess failed: {e}")

    out = (proc.stdout or "").strip()
    start, end = out.find("{"), out.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(out[start:end + 1])
        except Exception:
            pass
    return _blank_result(error=(proc.stderr or "scanner produced no output").strip()[:300])


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "product.png"
    tmo = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 20000
    settle = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 3000
    result = check_configurator(target, screenshot_path=out_path, timeout_ms=tmo, settle_ms=settle)
    print(json.dumps(result, indent=2))
