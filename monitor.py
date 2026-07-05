#!/usr/bin/env python3
"""
MOrth Part B booking watcher.

Checks the RCSEd Membership in Orthodontics (MOrth) Part B exam page (and the
exam calendar) and, the moment booking looks open, alerts the doctors on
Telegram (primary) and by email (backup) with a one-tap booking link.

Runs on GitHub Actions every ~5 minutes. All secrets come from environment
variables (set as GitHub Secrets) so nothing sensitive lives in the code.

Usage:
    python monitor.py          # normal check
    python monitor.py --test   # send a test alert to all channels and exit
    python monitor.py --reset  # clear the "already alerted" flag and exit
"""

import os
import sys
import time
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXAM_URL = "https://services.rcsed.ac.uk/exams/exam-details-membership-in-orthodontics-part-b"
CALENDAR_URL = "https://services.rcsed.ac.uk/exams/rcsed-exams?examGroup=dental"

# The sentence that means the exam is CLOSED. While this is on the page, no booking.
CLOSED_MARKER = "there are currently no live dates for this exam"

# Any of these appearing suggests booking is OPEN.
OPEN_KEYWORDS = [
    "book now",
    "apply now",
    "places available",
    "applications currently open",
    "add to basket",
    "book this exam",
]

PAGE_TIMEOUT_MS = 60_000          # max time to load a page
RECHECK_PAUSE_SEC = 12            # wait before the confirming second check

# Secrets (from environment / GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "").strip()
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "").strip()
EMAIL_RECIPIENTS = os.environ.get("EMAIL_RECIPIENTS", "").strip()  # comma-separated
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))

# Anti-spam flag: once we alert, we stop until this file is removed (--reset).
FLAG_FILE = Path("state") / "alerted.flag"


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------

def send_telegram(text: str) -> bool:
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("[telegram] skipped — TELEGRAM_TOKEN / TELEGRAM_CHAT_ID not set")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "false",
            },
            timeout=30,
        )
        if r.status_code == 200:
            print("[telegram] sent")
            return True
        print(f"[telegram] failed {r.status_code}: {r.text[:200]}")
    except Exception as e:  # noqa: BLE001
        print(f"[telegram] error: {e}")
    return False


def send_email(subject: str, body: str) -> bool:
    recipients = [a.strip() for a in EMAIL_RECIPIENTS.split(",") if a.strip()]
    if not (EMAIL_SENDER and EMAIL_PASSWORD and recipients):
        print("[email] skipped — EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECIPIENTS not set")
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = ", ".join(recipients)
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
        print(f"[email] sent to {len(recipients)} recipient(s)")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[email] error: {e}")
    return False


def notify(reason: str) -> None:
    tg_text = (
        "🚨 <b>MOrth Part B — booking may be OPEN!</b>\n\n"
        f"Signal: {reason}\n\n"
        f'👉 <a href="{EXAM_URL}">Open the booking page now</a>\n\n'
        "Verify and book quickly — places can fill fast."
    )
    email_body = (
        "MOrth Part B booking may be OPEN.\n\n"
        f"Signal detected: {reason}\n\n"
        f"Booking page: {EXAM_URL}\n\n"
        "This is an automated alert. Verify on the page and book quickly."
    )
    send_telegram(tg_text)
    send_email("🚨 MOrth Part B booking may be OPEN", email_body)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def looks_open(page_text: str) -> tuple[bool, str]:
    """Return (is_open, reason) for a single page's text."""
    low = page_text.lower()
    if CLOSED_MARKER in low:
        return False, "still shows 'no live dates'"
    for kw in OPEN_KEYWORDS:
        if kw in low:
            return True, f"found keyword '{kw}'"
    # Closed marker gone and page is substantial -> treat as possibly open.
    if len(low) > 500:
        return True, "'no live dates' message has disappeared"
    return False, "inconclusive (page too short)"


def read_page(page, url: str) -> str:
    page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
    return page.locator("body").inner_text()


def check_once(page) -> tuple[bool, str]:
    """Check the exam page (and calendar as backup). Return (is_open, reason)."""
    text = read_page(page, EXAM_URL)
    is_open, reason = looks_open(text)
    if is_open:
        return True, f"exam page: {reason}"

    # Secondary signal: sometimes a date shows on the calendar first.
    try:
        cal = read_page(page, CALENDAR_URL)
        if "orthodontics" in cal.lower() and "part b" in cal.lower():
            block = cal.lower()
            for kw in ("book", "places available", "apply"):
                if kw in block:
                    return True, f"calendar page: found '{kw}' near MOrth Part B"
    except Exception as e:  # noqa: BLE001
        print(f"[calendar] check skipped: {e}")

    return False, reason


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def already_alerted() -> bool:
    return FLAG_FILE.exists()


def write_flag(reason: str) -> None:
    FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    FLAG_FILE.write_text(f"alerted at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\nreason: {reason}\n")
    print(f"[state] wrote flag: {FLAG_FILE}")


def run_check() -> None:
    if already_alerted():
        print("[state] already alerted previously — staying quiet. Run --reset to re-arm.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            is_open, reason = check_once(page)
            print(f"[check-1] open={is_open} :: {reason}")

            if is_open:
                # Two-signal confirmation to avoid a half-loaded false positive.
                time.sleep(RECHECK_PAUSE_SEC)
                is_open2, reason2 = check_once(page)
                print(f"[check-2] open={is_open2} :: {reason2}")
                if is_open2:
                    notify(reason2)
                    write_flag(reason2)
                else:
                    print("[result] second check disagreed — not alerting (likely a load blip).")
            else:
                print("[result] closed — no action.")
        finally:
            browser.close()


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if arg == "--reset":
        if FLAG_FILE.exists():
            FLAG_FILE.unlink()
            print("[state] flag cleared — watcher re-armed.")
        else:
            print("[state] no flag to clear.")
        return 0

    if arg == "--test":
        print("[test] sending a test alert to all configured channels...")
        notify("TEST — this is a wiring test, not a real opening")
        return 0

    try:
        run_check()
    except Exception as e:  # noqa: BLE001
        # Never hard-fail the CI job on a transient network/page error;
        # just log it so the next run tries again.
        print(f"[error] transient failure this run: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
