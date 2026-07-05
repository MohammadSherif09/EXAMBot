# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file watcher (`monitor.py`) that scrapes the RCSEd MOrth Part B exam page and alerts via Telegram + email the moment booking looks open. It runs entirely on GitHub Actions cron (every ~5 min) — there is no server, database, or web frontend. All logic lives in `monitor.py`; everything else is config, workflows, and docs.

## Commands

```bash
pip install -r requirements.txt
python -m playwright install chromium   # required — Playwright drives headless Chromium

python monitor.py          # one real check
python monitor.py --test   # send a test alert to every configured channel, then exit
python monitor.py --reset  # clear the "already alerted" flag, then exit
```

There are no tests, linters, or build steps. The `--test` and `--reset` flags are the primary way to exercise the code locally.

## Runtime configuration (env vars only)

All secrets come from environment variables, injected in CI as GitHub Actions Secrets — never hardcode them. Required for alerts to fire: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`. Optional email backup: `EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECIPIENTS` (comma-separated), `SMTP_HOST`, `SMTP_PORT`. Missing credentials cause that channel to be skipped with a log line, not an error — the watcher degrades gracefully.

## Key architectural points

- **Two-signal + confirming re-check.** `check_once()` looks for `OPEN_KEYWORDS` and treats the disappearance of `CLOSED_MARKER` ("no live dates") as a positive. A first positive triggers a `RECHECK_PAUSE_SEC` sleep and a second `check_once()`; both must agree before alerting. This exists specifically to suppress false positives from half-loaded pages — preserve it when changing detection.

- **Anti-spam flag file: `state/alerted.flag`.** Once an alert fires, this file is written and `run_check()` stays silent on every future run until it's removed. In CI the flag is committed back to the repo by the `watch.yml` "Persist alert state" step (needs `permissions: contents: write`), so the quiet state survives across runs on ephemeral runners. `--reset` re-arms it.

- **Failures are swallowed by design.** `main()` catches all exceptions from `run_check()` and exits 0, so a transient network/page error never fails the CI job — the next scheduled run just retries. Keep this behavior; a red Actions run here would be noise, not signal.

- **Detection targets brittle page copy.** `CLOSED_MARKER` and `OPEN_KEYWORDS` are matched against lowercased page text from a third-party site. When RCSEd changes their wording, these constants are the thing to update.

## Workflows

- `.github/workflows/watch.yml` — the `*/5 * * * *` schedule (plus a manual `workflow_dispatch` button). Installs Chromium with `--with-deps`, runs `python monitor.py`, then commits any `state/` change back. `concurrency` is set so two checks never overlap.
- `.github/workflows/keepalive.yml` — a monthly commit that stops GitHub from disabling the schedule after 60 days of repo inactivity.

## Not tracked in git

The repo is not initialized as a git repository in this working copy. `.env`, `__pycache__/`, and Playwright caches are gitignored. `MOrth-Part-B-Bot-Reference.docx` and `architecture.png` are reference material, not code.
