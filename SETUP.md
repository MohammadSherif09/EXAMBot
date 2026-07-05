# Setup Guide — MOrth Part B Booking Alert Bot

Follow these steps once. Total time ≈ 15 minutes. No coding needed — just copy/paste.
When you're done, the bot runs on GitHub's servers 24/7 and pings the doctors on
Telegram (+ email) the moment MOrth Part B booking opens. **Your own computer does
not need to stay on.**

---

## What you'll end up with
- A free **public** GitHub repo holding these files.
- A **Telegram bot** posting to a group the doctors join.
- An **email backup** alert.
- A schedule that checks the exam page every ~5 minutes for free.

---

## Step 1 — Create the Telegram bot (2 min)
1. In Telegram, search for **@BotFather** and press **Start**.
2. Send `/newbot`.
3. Give it a name (e.g. `MOrth Alert`) and a username ending in `bot`
   (e.g. `morth_alert_xxx_bot`).
4. BotFather replies with a line like `Use this token to access the HTTP API:` followed by
   a token such as `123456789:AAH...`. **Copy that whole token** — this is your `TELEGRAM_TOKEN`.

## Step 2 — Create the group and get its Chat ID (3 min)
1. Create a **Telegram group** and add all the doctors.
2. Add your new bot to the group (search its username → add to group).
3. In the group, send any message (e.g. `hello`).
4. In a browser, open (replace `<TOKEN>` with your token):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Find `"chat":{"id":-1001234567890,...}`. The number (it usually starts with `-100`
   for groups) is your `TELEGRAM_CHAT_ID`. Copy it **including the minus sign**.

> Tip: if `getUpdates` is empty, send another message in the group and refresh the page.

## Step 3 — Email backup (3 min, optional but recommended)
Using Gmail:
1. Turn on 2-Step Verification on the Google account.
2. Go to **Google Account → Security → App passwords**, create one for "Mail".
3. You'll get a 16-character password. That's your `EMAIL_PASSWORD`.
   - `EMAIL_SENDER` = the Gmail address.
   - `EMAIL_RECIPIENTS` = the doctors' emails, comma-separated.
   - `SMTP_HOST` = `smtp.gmail.com`, `SMTP_PORT` = `465`.

(Skip this step if you only want Telegram — the bot still works.)

## Step 4 — Create the GitHub repo (2 min)
1. Sign in at github.com → **New repository**.
2. Name it e.g. `morth-alert-bot`. Set it to **Public** (this is what makes Actions
   unlimited-free). Create it.
3. Upload every file from this folder, keeping the structure:
   ```
   monitor.py
   requirements.txt
   .gitignore
   .github/workflows/watch.yml
   .github/workflows/keepalive.yml
   ```
   (Use **Add file → Upload files**, or drag the folder in. Make sure the
   `.github/workflows/` path is preserved.)

## Step 5 — Add your secrets (3 min)
In the repo: **Settings → Secrets and variables → Actions → New repository secret**.
Add each of these (name on the left, your value on the right):

| Secret name        | Value |
|--------------------|-------|
| `TELEGRAM_TOKEN`   | the BotFather token from Step 1 |
| `TELEGRAM_CHAT_ID` | the group id from Step 2 (with the minus sign) |
| `EMAIL_SENDER`     | your Gmail address (optional) |
| `EMAIL_PASSWORD`   | the 16-char app password (optional) |
| `EMAIL_RECIPIENTS` | doctor1@x.com, doctor2@y.com (optional) |
| `SMTP_HOST`        | smtp.gmail.com (optional) |
| `SMTP_PORT`        | 465 (optional) |

> Secrets are encrypted and stay private even though the repo is public. They are
> never printed in logs.

## Step 6 — Test it end-to-end (1 min)
1. Repo → **Actions** tab → you may need to click **"I understand… enable workflows"**.
2. Open the **MOrth Part B Watcher** workflow → **Run workflow** (manual button).
3. To test the *alert path*, temporarily change the run command in
   `.github/workflows/watch.yml` from `python monitor.py` to `python monitor.py --test`,
   commit, run it once — you should get a test message on Telegram and email — then
   change it back to `python monitor.py`.

## Step 7 — You're live
That's it. The watcher now runs every ~5 minutes automatically. When booking opens,
the doctors get the alert with a one-tap link to the booking page.

---

## Good to know
- **Latency:** GitHub runs the schedule roughly every 5 minutes (sometimes 5–15 min under
  load). Great as an early warning. If seats prove to vanish in seconds and you need
  faster, tell me and we move it to a small always-on server (~$5/mo) checking every 30s —
  same code.
- **No duplicate spam:** after the first real alert the bot records a flag and goes quiet.
  To re-arm it for a future cycle, run the workflow once after changing the command to
  `python monitor.py --reset` (then set it back), or delete `state/alerted.flag` in the repo.
- **Staying awake:** the `keepalive.yml` workflow makes a tiny commit monthly so GitHub
  never pauses the schedule for inactivity.
- **Security reminder:** the Telegram bot token that was shared in the earlier chat is
  exposed — create a **fresh** bot (Step 1) or revoke the old one in @BotFather with
  `/revoke`. Never paste tokens into the code; only into Secrets.
