# MOrth Part B — Booking Alert Bot

Watches the RCSEd **Membership in Orthodontics (MOrth) Part B** exam page and alerts
the doctors on **Telegram** (primary) and **email** (backup) the moment booking opens,
with a one-tap link to the booking page.

- **Runs in the cloud** on GitHub Actions — free, 24/7, your PC can be off.
- **Checks every ~5 minutes** on the exam detail page (the authoritative source).
- **Two-signal detection** (the "no live dates" message disappearing, or a
  Book/Apply/Places-available control appearing) with a confirming re-check to avoid
  false alarms.
- **Alert-only** with a booking deep link — no logins or payments are automated.

## Files
| File | Purpose |
|------|---------|
| `monitor.py` | The watcher + Telegram/email notifiers |
| `requirements.txt` | Python dependencies |
| `.github/workflows/watch.yml` | The 5-minute schedule (+ manual run) |
| `.github/workflows/keepalive.yml` | Monthly commit so the schedule never sleeps |
| `SETUP.md` | **Start here** — step-by-step setup (~15 min) |

## Quick start
See **[SETUP.md](SETUP.md)**. In short: create a Telegram bot + group, make a **public**
GitHub repo, upload these files, add your tokens as **Actions Secrets**, and enable the
workflow.

## Commands (for local testing)
```bash
pip install -r requirements.txt
python -m playwright install chromium

python monitor.py          # one real check
python monitor.py --test   # send a test alert to all channels
python monitor.py --reset  # clear the "already alerted" flag
```
