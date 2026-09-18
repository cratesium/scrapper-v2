# Daily Job Digest

Runs automatically every 24 hours on GitHub Actions (free). It:
- Pulls fresh listings from **RemoteOK, Arbeitnow, We Work Remotely, and HN "Who's Hiring"** (legitimate open APIs — no login, no ToS issues), filtered to your profile (Java/Spring Boot/Backend/Kafka/Kubernetes/AWS).
- Generates today's pre-filled search links for **LinkedIn, Naukri, Wellfound, YC Work at a Startup, and Indeed** — one click, always fresh results.
- Saves an HTML report to `reports/latest.html` in this repo (viewable anytime).
- Emails you the same digest.

> **Why not scrape LinkedIn/Naukri/Wellfound directly?** They actively block automated scraping and it violates their Terms of Service — doing so risks your account/IP getting banned. Instead, this tool generates the exact search URL you'd type in yourself, pre-filled and dated, so you're one click from live results without any risk.

---

## Setup (10 minutes, one time)

### 1. Create a GitHub repo
1. Go to [github.com/new](https://github.com/new), name it e.g. `job-scraper`, keep it **Private** if you like, create it.
2. Upload all files from this folder into that repo (or use `git push` — see below).

```bash
cd job-scraper
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/job-scraper.git
git push -u origin main
```

### 2. Create a Gmail App Password
Regular Gmail passwords won't work for SMTP — you need an **App Password**:
1. Go to your [Google Account → Security](https://myaccount.google.com/security).
2. Turn on **2-Step Verification** if not already on (required for App Passwords).
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Create a new app password (name it "job-scraper"), copy the 16-character code shown.

### 3. Add secrets to your GitHub repo
In your repo: **Settings → Secrets and variables → Actions → New repository secret**. Add three:

| Secret name | Value |
|---|---|
| `GMAIL_USER` | your Gmail address, e.g. `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | the 16-character app password from step 2 |
| `TO_EMAIL` | where you want the digest sent (can be the same Gmail address) |

### 4. Turn it on
The workflow (`.github/workflows/daily-jobs.yml`) is already scheduled for **03:00 UTC daily** (~8:30 AM IST). To change the time, edit the `cron` line in that file — [crontab.guru](https://crontab.guru) helps write cron expressions.

To test it immediately instead of waiting a day:
1. Go to your repo's **Actions** tab.
2. Click **Daily Job Digest** on the left.
3. Click **Run workflow** (this is the `workflow_dispatch` trigger already built in).
4. Check the run logs, then check your email and `reports/latest.html`.

---

## Customizing your search

Edit **`config.py`** any time — no coding needed:
- `JOB_TITLES` — the roles you're targeting.
- `SKILLS` — used to rank/filter incoming listings.
- `LOCATIONS` / `PRIMARY_LOCATION` — where you're looking.
- `MAX_PER_SOURCE` — how many jobs per source show up in the digest.

Commit and push the change — the next scheduled run (or a manual "Run workflow") will pick it up.

## Files

| File | Purpose |
|---|---|
| `main.py` | Entry point run by GitHub Actions |
| `job_scraper.py` | Pulls jobs from open APIs + generates gated-site search links |
| `config.py` | Your search keywords, skills, locations |
| `report_generator.py` | Builds the HTML digest |
| `email_sender.py` | Sends the digest via Gmail SMTP |
| `.github/workflows/daily-jobs.yml` | The daily schedule |
| `reports/latest.html` | Always the most recent digest |

## Notes
- This was built from your resume (Backend/Java, Spring Boot, Kafka, Kubernetes, AWS, Paytm SWE background) — `config.py` reflects that starting point.
- If you ever want to add more open-API sources (e.g. Adzuna, Jooble — both have free API keys), it's a small addition to `job_scraper.py`; happy to add them if you want.
