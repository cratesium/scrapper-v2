"""
Job Scraper — pulls fresh listings from open/legitimate job APIs,
and generates pre-filled easy-apply search links for sites that block
automated scraping (LinkedIn, Naukri, Wellfound, YC Work at a Startup, Dice).

Fetched sources (public APIs, no auth required):
  - RemoteOK API
  - Remotive API
  - Arbeitnow API
  - Jobicy API
  - We Work Remotely (RSS)
  - Hacker News "Who's Hiring" (Algolia HN Search API)

Click-through link sources (filtered for easy/one-click apply):
  - LinkedIn Jobs  (Easy Apply filter)
  - Naukri.com
  - Wellfound (AngelList Talent)
  - YC Work at a Startup
  - Indeed
  - Dice.com  (tech-focused, many one-click applications)
  - Instahyre  (India-focused, many easy-apply roles)
"""

import requests
import feedparser
import urllib.parse
import datetime
from dataclasses import dataclass, field
from typing import List

import config


@dataclass
class Job:
    title:    str
    company:  str
    location: str
    url:      str
    source:   str
    posted:   str       = ""
    tags:     List[str] = field(default_factory=list)
    score:    int       = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_keywords(text: str) -> bool:
    text_low = text.lower()
    return (
        any(t.lower() in text_low for t in config.JOB_TITLES) or
        any(s.lower() in text_low for s in config.SKILLS)
    )


def _score(text: str) -> int:
    text_low = text.lower()
    score = 0
    for skill in config.SKILLS:
        if skill.lower() in text_low:
            score += 2
    for title in config.JOB_TITLES:
        if title.lower() in text_low:
            score += 3
    return score


def _top(jobs: List[Job]) -> List[Job]:
    jobs.sort(key=lambda j: j.score, reverse=True)
    return jobs[:config.MAX_PER_SOURCE]


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

def fetch_remoteok() -> List[Job]:
    jobs = []
    try:
        r = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        r.raise_for_status()
        for item in r.json():
            if not isinstance(item, dict) or "position" not in item:
                continue
            text_blob = (
                f"{item.get('position', '')} "
                f"{' '.join(item.get('tags', []))} "
                f"{item.get('description', '')}"
            )
            if not _matches_keywords(text_blob):
                continue
            jobs.append(Job(
                title=item.get("position", "Unknown"),
                company=item.get("company", "Unknown"),
                location=item.get("location", "Remote") or "Remote",
                url=item.get("url", "https://remoteok.com"),
                source="RemoteOK",
                posted=item.get("date", ""),
                tags=item.get("tags", []),
                score=_score(text_blob),
            ))
    except Exception as e:
        print(f"[RemoteOK] fetch failed: {e}")
    return _top(jobs)


def fetch_remotive() -> List[Job]:
    """Remotive — free public API, great for remote Java/backend roles."""
    jobs = []
    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"category": "software-dev", "search": "java backend", "limit": 50},
            timeout=15,
        )
        r.raise_for_status()
        for item in r.json().get("jobs", []):
            text_blob = (
                f"{item.get('title', '')} "
                f"{' '.join(item.get('tags', []))} "
                f"{item.get('description', '')}"
            )
            if not _matches_keywords(text_blob):
                continue
            jobs.append(Job(
                title=item.get("title", "Unknown"),
                company=item.get("company_name", "Unknown"),
                location=item.get("candidate_required_location", "Remote") or "Remote",
                url=item.get("url", "https://remotive.com"),
                source="Remotive",
                posted=item.get("publication_date", ""),
                tags=item.get("tags", []),
                score=_score(text_blob),
            ))
    except Exception as e:
        print(f"[Remotive] fetch failed: {e}")
    return _top(jobs)


def fetch_jobicy() -> List[Job]:
    """Jobicy — free public API, strong tech/engineering remote listings."""
    jobs = []
    try:
        r = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"tag": "java", "count": 50, "industry": "engineering"},
            timeout=15,
        )
        r.raise_for_status()
        for item in r.json().get("jobs", []):
            text_blob = (
                f"{item.get('jobTitle', '')} "
                f"{item.get('jobIndustry', '')} "
                f"{item.get('jobExcerpt', '')} "
                f"{item.get('jobDescription', '')}"
            )
            if not _matches_keywords(text_blob):
                continue
            jobs.append(Job(
                title=item.get("jobTitle", "Unknown"),
                company=item.get("companyName", "Unknown"),
                location=item.get("jobGeo", "Remote") or "Remote",
                url=item.get("url", "https://jobicy.com"),
                source="Jobicy",
                posted=item.get("pubDate", ""),
                score=_score(text_blob),
            ))
    except Exception as e:
        print(f"[Jobicy] fetch failed: {e}")
    return _top(jobs)


def fetch_arbeitnow() -> List[Job]:
    jobs = []
    try:
        r = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        r.raise_for_status()
        for item in r.json().get("data", []):
            text_blob = (
                f"{item.get('title', '')} "
                f"{' '.join(item.get('tags', []))} "
                f"{item.get('description', '')}"
            )
            if not _matches_keywords(text_blob):
                continue
            jobs.append(Job(
                title=item.get("title", "Unknown"),
                company=item.get("company_name", "Unknown"),
                location=item.get("location", "Remote") or "Remote",
                url=item.get("url", "https://arbeitnow.com"),
                source="Arbeitnow",
                posted=str(item.get("created_at", "")),
                tags=item.get("tags", []),
                score=_score(text_blob),
            ))
    except Exception as e:
        print(f"[Arbeitnow] fetch failed: {e}")
    return _top(jobs)


def fetch_weworkremotely() -> List[Job]:
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    ]
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                text_blob = f"{entry.get('title', '')} {entry.get('summary', '')}"
                if not _matches_keywords(text_blob):
                    continue
                title   = entry.get("title", "Unknown")
                company = title.split(":")[0].strip() if ":" in title else "Unknown"
                jobs.append(Job(
                    title=title,
                    company=company,
                    location="Remote",
                    url=entry.get("link", "https://weworkremotely.com"),
                    source="We Work Remotely",
                    posted=entry.get("published", ""),
                    score=_score(text_blob),
                ))
        except Exception as e:
            print(f"[WWR] fetch failed for {feed_url}: {e}")
    return _top(jobs)


def fetch_hn_whoishiring() -> List[Job]:
    """Most recent 'Ask HN: Who is Hiring' thread via Algolia HN Search API."""
    jobs = []
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={"query": "Who is hiring", "tags": "story", "hitsPerPage": 5},
            timeout=15,
        )
        r.raise_for_status()
        thread_id = None
        for h in r.json().get("hits", []):
            if h.get("title", "").lower().startswith("ask hn: who is hiring"):
                thread_id = h.get("objectID")
                break
        if not thread_id:
            return jobs

        r2 = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": f"comment,story_{thread_id}", "hitsPerPage": 200},
            timeout=15,
        )
        r2.raise_for_status()
        for c in r2.json().get("hits", []):
            text = c.get("comment_text") or ""
            if not text or not _matches_keywords(text):
                continue
            snippet     = text.replace("<p>", " ").replace("</p>", " ")
            title_line  = snippet.strip()[:120].replace("\n", " ")
            jobs.append(Job(
                title=title_line + "...",
                company="(see posting)",
                location="Varies",
                url=f"https://news.ycombinator.com/item?id={c.get('objectID')}",
                source="HN Who's Hiring",
                posted=c.get("created_at", ""),
                score=_score(text),
            ))
    except Exception as e:
        print(f"[HN] fetch failed: {e}")
    return _top(jobs)


# ---------------------------------------------------------------------------
# Search-link generator  (click-through, always current, free/easy apply)
# ---------------------------------------------------------------------------

def generate_search_links() -> dict:
    """
    Generates fresh, pre-filled search URLs for sites that can't be safely
    auto-scraped.  Links are filtered for easy / one-click application where
    the platform supports it.
    """
    primary_title   = config.JOB_TITLES[0]               # "Java Developer"
    java_query      = "Java Backend Developer"
    or_query        = " OR ".join(config.JOB_TITLES[:4])
    yrs             = config.YEARS_EXPERIENCE             # 2

    links = {}

    # ------------------------------------------------------------------
    # LinkedIn Jobs — Easy Apply filter (f_AL=true) + 24 h + 1-3 yrs exp
    # Experience levels: 2=Entry, 3=Associate  (covers 0-3 yrs)
    # ------------------------------------------------------------------
    li_params = {
        "keywords": java_query,
        "location": config.PRIMARY_LOCATION,
        "f_TPR":    "r86400",       # past 24 hours
        "f_AL":     "true",         # ✅ Easy Apply only
        "f_E":      "2,3",          # Entry + Associate level
        "sortBy":   "DD",           # date descending
    }
    links["LinkedIn Easy Apply"] = (
        "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(li_params)
    )

    # ------------------------------------------------------------------
    # Y Combinator — Work at a Startup
    # Direct job board; many startups allow 1-click apply via the platform
    # ------------------------------------------------------------------
    yc_params = {
        "role":           "engineer",
        "skills":         "java",
        "remote":         "only_remote",
        "yoe_min":        str(yrs - 1),
        "yoe_max":        str(yrs + 2),
    }
    links["YC Work at a Startup"] = (
        "https://www.workatastartup.com/jobs?" + urllib.parse.urlencode(yc_params)
    )

    # ------------------------------------------------------------------
    # Wellfound (AngelList Talent) — startup jobs, direct apply
    # ------------------------------------------------------------------
    wf_params = {
        "role":       "backend-engineer",
        "skills":     "java,spring-boot,microservices",
        "remote":     "true",
        "locationSlugs": "india",
    }
    links["Wellfound"] = (
        "https://wellfound.com/jobs?" + urllib.parse.urlencode(wf_params)
    )

    # ------------------------------------------------------------------
    # Dice.com — tech-focused US/global board; many easy-apply postings
    # ------------------------------------------------------------------
    dice_params = {
        "q":              "Java Backend Developer",
        "location":       "Remote",
        "radius":         "30",
        "radiusUnit":     "mi",
        "page":           "1",
        "pageSize":       "20",
        "filters.postedDate": "ONE_DAY",
        "language":       "en",
    }
    links["Dice"] = (
        "https://www.dice.com/jobs?" + urllib.parse.urlencode(dice_params)
    )

    # ------------------------------------------------------------------
    # Instahyre — India-focused, AI-matched, most listings have easy apply
    # ------------------------------------------------------------------
    ih_params = {
        "designation": "Java Developer",
        "experience":  f"{yrs - 1},{yrs + 2}",
    }
    links["Instahyre"] = (
        "https://www.instahyre.com/search-jobs/?" + urllib.parse.urlencode(ih_params)
    )

    # ------------------------------------------------------------------
    # Naukri.com — largest Indian board
    # ------------------------------------------------------------------
    naukri_kw = "-".join(primary_title.lower().split())
    links["Naukri"] = (
        f"https://www.naukri.com/{naukri_kw}-jobs?experience={yrs}"
    )

    # ------------------------------------------------------------------
    # Indeed — bonus, broad coverage
    # ------------------------------------------------------------------
    indeed_params = {
        "q":       "Java Backend Developer",
        "l":       config.PRIMARY_LOCATION,
        "fromage": "1",
        "explvl":  "entry_level",
    }
    links["Indeed"] = (
        "https://www.indeed.com/jobs?" + urllib.parse.urlencode(indeed_params)
    )

    return links


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_all() -> dict:
    print("Fetching RemoteOK...")
    remoteok = fetch_remoteok()
    print(f"  -> {len(remoteok)} matches")

    print("Fetching Remotive...")
    remotive = fetch_remotive()
    print(f"  -> {len(remotive)} matches")

    print("Fetching Jobicy...")
    jobicy = fetch_jobicy()
    print(f"  -> {len(jobicy)} matches")

    print("Fetching Arbeitnow...")
    arbeitnow = fetch_arbeitnow()
    print(f"  -> {len(arbeitnow)} matches")

    print("Fetching We Work Remotely...")
    wwr = fetch_weworkremotely()
    print(f"  -> {len(wwr)} matches")

    print("Fetching HN Who's Hiring...")
    hn = fetch_hn_whoishiring()
    print(f"  -> {len(hn)} matches")

    print("Generating search links for gated sites...")
    links = generate_search_links()

    return {
        "jobs": {
            "RemoteOK":          remoteok,
            "Remotive":          remotive,
            "Jobicy":            jobicy,
            "Arbeitnow":         arbeitnow,
            "We Work Remotely":  wwr,
            "HN Who's Hiring":   hn,
        },
        "search_links": links,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    result = run_all()
    total  = sum(len(v) for v in result["jobs"].values())
    print(f"\nTotal matched jobs from open APIs: {total}")
    print(f"Search links generated: {list(result['search_links'].keys())}")
