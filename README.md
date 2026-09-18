# Daily Job Digest

Runs automatically **twice daily** on GitHub Actions (free). It:

- **Scrapes live listings** from **LinkedIn, YC Work at a Startup, Wellfound, RemoteOK, Remotive, Arbeitnow, Jobicy, We Work Remotely,** and **HN "Who's Hiring"**.
- Targets **Java Developer, Software Engineer, Backend Developer, Software Engineer Intern,** and **Developer Intern** roles for **0–2 years experience**.
- Enforces a **65 % India on-site : 30 % Remote** ratio per position so the digest stays India-relevant.
- Generates pre-filled search links for **Naukri, Instahyre, Indeed India** (click-through; these sites block automated scraping).
- Saves a dated HTML report to `reports/YYYY-MM-DD.html` and `reports/latest.html`.
- **Auto-deletes reports older than 4 days** from the repo on every run.
- Emails the digest to one or more recipients.

---

## Sources at a glance

| Source | How | Location filter |
|---|---|---|
| **LinkedIn** | Public guest API, paginated (~100/query, `f_E=1,2,3` entry-level) | India only (on-site) |
| **YC Work at a Startup** | Inertia.js `data-page` JSON, paginated 4 pages | Remote / global |
| **Wellfound** | `__NEXT_DATA__` Apollo cache `JobListing:*` | Remote / global |
| **RemoteOK** | Public JSON API | Remote |
| **Remotive** | Public JSON API | Remote |
| **Arbeitnow** | Public JSON API | Remote |
| **Jobicy** | Public JSON API | Remote |
| **We Work Remotely** | RSS feed | Remote |
| **HN Who's Hiring** | Algolia comment search | Varies |
| **Naukri** *(search link)* | Click-through URL with 0–2 yr exp filter | India |
| **Instahyre** *(search link)* | Click-through URL | India |
| **Indeed India** *(search link)* | Click-through URL, entry level | India |

> **Why are Naukri / Instahyre / Indeed only search links?**  
> They use heavy bot-detection or client-side rendering that blocks plain HTTP requests — scraping them would require a headless browser. Instead, the digest generates the exact pre-filled search URL so you're one click from live results, risk-free.

---

## Positions searched

| Role | Jobs targeted | Experience |
|---|---|---|
| Java Developer | 100 | 0–2 yrs |
| Software Engineer | 100 | 0–2 yrs |
| Backend Developer | 60 | 0–2 yrs |
| Software Engineer Intern | 40 | 0–2 yrs |
| Developer Intern | 30 | 0–2 yrs |

---

## Setup (10 minutes, one time)

### 1. Create a GitHub repo
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
Regular Gmail passwords won't work — you need an **App Password**:
1. Go to [Google Account → Security](https://myaccount.google.com/security).
2. Turn on **2-Step Verification** (required for App Passwords).
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Create a new app password (name it `job-scraper`), copy the 16-character code.

### 3. Add secrets to your GitHub repo
**Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GMAIL_USER` | your Gmail address, e.g. `you@gmail.com` |
| `GMAIL_APP_PASSWORD` | the 16-character app password from step 2 |
| `TO_EMAIL` | recipient(s) — comma-separate for multiple: `a@x.com,b@x.com` |

### 4. Turn it on
The workflow runs at **9:00 AM IST** and **9:00 PM IST** daily (already configured).  
To change the schedule, edit the `cron` lines in `.github/workflows/daily-jobs.yml` — [crontab.guru](https://crontab.guru) helps.

**To test immediately:**
1. Go to your repo's **Actions** tab.
2. Click **Daily Job Scraper** on the left.
3. Click **Run workflow**.
4. Check the run logs, your email, and `reports/latest.html`.

---

## Customising your search

All config lives in **`config.py`** — no other file needs editing:

| Setting | What it controls |
|---|---|
| `SEARCH_POSITIONS` | Roles and per-role job cap |
| `SKILLS` | Keywords used to score/rank listings |
| `INDIA_RATIO` / `REMOTE_RATIO` | India : Remote split (default 0.65 : 0.30) |
| `FRESHNESS_HOURS` | How old a listing can be (default 48 h) |
| `EXPERIENCE_MIN` / `EXPERIENCE_MAX` | Experience range baked into search links |
| `SOURCE_LIMIT` | Max jobs each source returns per query call |
| `REPORT_RETENTION_DAYS` | How many days of dated reports to keep (default 4) |

Commit and push — the next run picks it up automatically.

---

## File reference

| File | Purpose |
|---|---|
| `main.py` | Entry point — orchestrates scrape → report → purge → email |
| `job_scraper.py` | All scrapers, location filter, ratio enforcement, search-link generator |
| `config.py` | Your search keywords, skills, locations, ratios |
| `report_generator.py` | Builds the HTML digest with source badges and 🇮🇳 / 🌐 icons |
| `email_sender.py` | Sends the digest via Gmail SMTP |
| `requirements.txt` | Python dependencies (`requests`, `feedparser`, `beautifulsoup4`) |
| `.github/workflows/daily-jobs.yml` | GitHub Actions schedule (9 AM + 9 PM IST) |
| `reports/latest.html` | Always the most recent digest |
| `reports/YYYY-MM-DD.html` | Dated archives (auto-deleted after 4 days) |

---

## Skills profile (from resume)

The scraper boosts score for listings matching your stack:

> **Languages:** Java, Python, SQL  
> **Backend & APIs:** Spring Boot, Spring Reactive (WebFlux), RESTful APIs, WebSocket, Microservices  
> **AI & Agentic:** Agentic AI Workflows, Cursor MCP, LLM Tool Integration  
> **Distributed Systems & DBs:** Apache Kafka, MySQL, Redis, Elasticsearch  
> **Cloud / Infra / DevOps:** AWS, Kubernetes (EKS), Docker, Jenkins, Flyway  
> **Observability & Testing:** ELK Stack, Grafana, Prometheus, JUnit, Mockito, System Design  
> **Core:** DSA, Agile, Git
