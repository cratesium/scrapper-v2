"""
Job Scraper — fetches jobs position-by-position from open APIs.

Each position in config.SEARCH_POSITIONS is searched across ALL sources
independently, deduplicated by URL, then capped at its own limit:
  • Software Engineer        → 30 results
  • Java Developer           → 30 results
  • Software Engineer Intern → 30 results
  • Product Manager Intern   → 10 results
  Total cap: 100

Fetched sources (public APIs, no auth required):
  - RemoteOK
  - Remotive
  - Arbeitnow
  - Jobicy
  - We Work Remotely (RSS)
  - Hacker News "Who's Hiring" (Algolia)

Click-through / easy-apply links (not scraped):
  - LinkedIn Easy Apply, YC Work at a Startup, Wellfound,
    Dice, Instahyre, Naukri, Indeed
"""

import re
import requests
import feedparser
import urllib.parse
import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from email.utils import parsedate_to_datetime

import config


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

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
# Freshness filter  (keep only jobs posted within FRESHNESS_HOURS)
# ---------------------------------------------------------------------------

_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_posted(posted: str) -> Optional[datetime.datetime]:
    """
    Parse a posted/date string into a timezone-aware datetime.
    Returns None when the format is unrecognised (caller treats as fresh).

    Order matters:
      1. Unix timestamp
      2. Date-only  YYYY-MM-DD  → noon UTC (avoids midnight-UTC trap)
      3. ISO 8601 with time component
      4. RFC 2822 (RSS)
    """
    if not posted:
        return None
    s = str(posted).strip()

    # 1. Unix timestamp (plain integer string)
    if s.lstrip("-").isdigit():
        try:
            return datetime.datetime.fromtimestamp(int(s), tz=datetime.timezone.utc)
        except Exception:
            pass

    # 2. Date-only  "2024-01-15"
    #    Map to noon UTC so both the 9 AM and 9 PM IST cron runs treat
    #    today's date-only listings as fresh.
    if _DATE_ONLY_RE.match(s):
        try:
            d = datetime.date.fromisoformat(s)
            return datetime.datetime(d.year, d.month, d.day, 12, 0, 0,
                                     tzinfo=datetime.timezone.utc)
        except ValueError:
            pass

    # 3. ISO 8601 with time component  (handles trailing "Z" and "+00:00")
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass

    # 4. RFC 2822 — used by RSS feeds  "Mon, 15 Jan 2024 10:30:00 +0000"
    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass

    return None


def _is_fresh(posted: str) -> bool:
    """
    Return True if the job was posted within config.FRESHNESS_HOURS.
    A 10-minute grace period handles micro-timing differences at the boundary.
    Unknown / unparseable dates are conservatively treated as fresh so real
    listings are never silently dropped.
    """
    dt = _parse_posted(posted)
    if dt is None:
        return True                           # unknown date → include
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(hours=config.FRESHNESS_HOURS)
        + datetime.timedelta(minutes=10)      # grace for boundary edge-cases
    )
    return dt >= cutoff


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _matches_query(text: str, query: str) -> bool:
    """Return True if text is relevant to the searched position."""
    text_low  = text.lower()
    # At least one meaningful word from the position title must appear
    words = [w for w in query.lower().split() if len(w) > 2]
    return any(w in text_low for w in words)


def _score_for(text: str, query: str) -> int:
    """Score a job text against a specific position query."""
    text_low  = text.lower()
    query_low = query.lower()
    score = 0

    # Exact phrase match is strongest signal
    if query_low in text_low:
        score += 15

    # Individual query-word matches
    for word in query_low.split():
        if len(word) > 2 and word in text_low:
            score += 3

    # Skill-keyword bonus
    for skill in config.SKILLS:
        if skill.lower() in text_low:
            score += 1

    return score


# ---------------------------------------------------------------------------
# Source fetchers — each accepts (query, limit) and returns a list of Jobs
# ---------------------------------------------------------------------------

def _fetch_remoteok(query: str, limit: int) -> List[Job]:
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
            text = (
                f"{item.get('position', '')} "
                f"{' '.join(item.get('tags', []))} "
                f"{item.get('description', '')}"
            )
            if not _matches_query(text, query):
                continue
            jobs.append(Job(
                title    = item.get("position", "Unknown"),
                company  = item.get("company", "Unknown"),
                location = item.get("location", "Remote") or "Remote",
                url      = item.get("url", "https://remoteok.com"),
                source   = "RemoteOK",
                posted   = item.get("date", ""),
                tags     = item.get("tags", []),
                score    = _score_for(text, query),
            ))
    except Exception as e:
        print(f"  [RemoteOK] {query}: {e}")
    return jobs


def _fetch_remotive(query: str, limit: int) -> List[Job]:
    jobs = []
    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": limit * 3},
            timeout=15,
        )
        r.raise_for_status()
        for item in r.json().get("jobs", []):
            text = (
                f"{item.get('title', '')} "
                f"{' '.join(item.get('tags', []))} "
                f"{item.get('description', '')}"
            )
            if not _matches_query(text, query):
                continue
            jobs.append(Job(
                title    = item.get("title", "Unknown"),
                company  = item.get("company_name", "Unknown"),
                location = item.get("candidate_required_location", "Remote") or "Remote",
                url      = item.get("url", "https://remotive.com"),
                source   = "Remotive",
                posted   = item.get("publication_date", ""),
                tags     = item.get("tags", []),
                score    = _score_for(text, query),
            ))
    except Exception as e:
        print(f"  [Remotive] {query}: {e}")
    return jobs


def _fetch_jobicy(query: str, limit: int) -> List[Job]:
    jobs = []
    # Jobicy uses technology tags; map position titles to best tag
    tag_map = {
        "java developer":           "java",
        "software engineer":        "software-engineer",
        "software engineer intern": "intern",
        "product manager intern":   "product-manager",
    }
    tag = tag_map.get(query.lower(), query.lower().replace(" ", "-"))
    try:
        r = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"tag": tag, "count": limit * 3},
            timeout=15,
        )
        r.raise_for_status()
        for item in r.json().get("jobs", []):
            text = (
                f"{item.get('jobTitle', '')} "
                f"{item.get('jobExcerpt', '')} "
                f"{item.get('jobDescription', '')}"
            )
            if not _matches_query(text, query):
                continue
            jobs.append(Job(
                title    = item.get("jobTitle", "Unknown"),
                company  = item.get("companyName", "Unknown"),
                location = item.get("jobGeo", "Remote") or "Remote",
                url      = item.get("url", "https://jobicy.com"),
                source   = "Jobicy",
                posted   = item.get("pubDate", ""),
                score    = _score_for(text, query),
            ))
    except Exception as e:
        print(f"  [Jobicy] {query}: {e}")
    return jobs


def _fetch_arbeitnow(query: str, limit: int) -> List[Job]:
    jobs = []
    try:
        r = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        r.raise_for_status()
        for item in r.json().get("data", []):
            text = (
                f"{item.get('title', '')} "
                f"{' '.join(item.get('tags', []))} "
                f"{item.get('description', '')}"
            )
            if not _matches_query(text, query):
                continue
            jobs.append(Job(
                title    = item.get("title", "Unknown"),
                company  = item.get("company_name", "Unknown"),
                location = item.get("location", "Remote") or "Remote",
                url      = item.get("url", "https://arbeitnow.com"),
                source   = "Arbeitnow",
                posted   = str(item.get("created_at", "")),
                tags     = item.get("tags", []),
                score    = _score_for(text, query),
            ))
    except Exception as e:
        print(f"  [Arbeitnow] {query}: {e}")
    return jobs


def _fetch_weworkremotely(query: str, limit: int) -> List[Job]:
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-management-executive-jobs.rss",
    ]
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                text = f"{entry.get('title', '')} {entry.get('summary', '')}"
                if not _matches_query(text, query):
                    continue
                title   = entry.get("title", "Unknown")
                company = title.split(":")[0].strip() if ":" in title else "Unknown"
                jobs.append(Job(
                    title    = title,
                    company  = company,
                    location = "Remote",
                    url      = entry.get("link", "https://weworkremotely.com"),
                    source   = "We Work Remotely",
                    posted   = entry.get("published", ""),
                    score    = _score_for(text, query),
                ))
        except Exception as e:
            print(f"  [WWR] {query}: {e}")
    return jobs


def _fetch_hn(query: str, limit: int) -> List[Job]:
    """HN 'Who is Hiring' thread — search comments for the position query."""
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
            params={
                "query":       query,
                "tags":        f"comment,story_{thread_id}",
                "hitsPerPage": limit * 3,
            },
            timeout=15,
        )
        r2.raise_for_status()
        for c in r2.json().get("hits", []):
            text = (c.get("comment_text") or "")
            if not text or not _matches_query(text, query):
                continue
            snippet    = text.replace("<p>", " ").replace("</p>", " ")
            title_line = snippet.strip()[:120].replace("\n", " ")
            jobs.append(Job(
                title    = title_line + "…",
                company  = "(see posting)",
                location = "Varies",
                url      = f"https://news.ycombinator.com/item?id={c.get('objectID')}",
                source   = "HN Who's Hiring",
                posted   = c.get("created_at", ""),
                score    = _score_for(text, query),
            ))
    except Exception as e:
        print(f"  [HN] {query}: {e}")
    return jobs


# ---------------------------------------------------------------------------
# Per-position aggregator
# ---------------------------------------------------------------------------

_FETCHERS = [
    _fetch_remoteok,
    _fetch_remotive,
    _fetch_jobicy,
    _fetch_arbeitnow,
    _fetch_weworkremotely,
    _fetch_hn,
]


def _fetch_for_position(title: str, limit: int) -> List[Job]:
    """
    Call every source for `title`, merge results, apply 12-hour freshness
    filter, deduplicate by URL, sort by score, return top `limit` jobs.
    """
    all_jobs: List[Job] = []
    seen_urls: set      = set()
    stale_count         = 0

    for fetcher in _FETCHERS:
        for job in fetcher(title, limit):
            if not _is_fresh(job.posted):
                stale_count += 1
                continue
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                all_jobs.append(job)

    if stale_count:
        print(f"  ↳ dropped {stale_count} stale listings (>{ config.FRESHNESS_HOURS}h old)")

    all_jobs.sort(key=lambda j: j.score, reverse=True)
    return all_jobs[:limit]


# ---------------------------------------------------------------------------
# Search-link generator  (click-through easy-apply links per position)
# ---------------------------------------------------------------------------

def generate_search_links() -> Dict[str, Dict[str, str]]:
    """
    Returns a dict keyed by position title, each containing a dict of
    platform → URL.  Links are filtered for easy / one-click apply.
    """
    yrs    = config.YEARS_EXPERIENCE
    result = {}

    for pos in config.SEARCH_POSITIONS:
        title = pos["title"]
        links = {}

        # LinkedIn Easy Apply
        links["LinkedIn Easy Apply"] = (
            "https://www.linkedin.com/jobs/search/?"
            + urllib.parse.urlencode({
                "keywords": title,
                "location": config.PRIMARY_LOCATION,
                "f_TPR":    "r43200",   # past 12 hours — matches cron cadence
                "f_AL":     "true",
                "f_E":      "1,2,3",
                "sortBy":   "DD",
            })
        )

        # YC Work at a Startup
        links["YC Work at a Startup"] = (
            "https://www.workatastartup.com/jobs?"
            + urllib.parse.urlencode({"role": title})
        )

        # Wellfound
        links["Wellfound"] = (
            "https://wellfound.com/jobs?"
            + urllib.parse.urlencode({"q": title, "remote": "true"})
        )

        # Naukri
        naukri_kw = "-".join(title.lower().split())
        links["Naukri"] = f"https://www.naukri.com/{naukri_kw}-jobs?experience={yrs}"

        # Indeed
        links["Indeed"] = (
            "https://www.indeed.com/jobs?"
            + urllib.parse.urlencode({"q": title, "l": config.PRIMARY_LOCATION, "fromage": "1"})
            # Indeed minimum granularity = 1 day; 12h filter applied on fetched results
        )

        result[title] = links

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_all() -> dict:
    jobs_by_position: Dict[str, List[Job]] = {}

    for pos in config.SEARCH_POSITIONS:
        title = pos["title"]
        limit = pos["limit"]
        print(f"Fetching '{title}' (limit {limit}) across all sources…")
        matched = _fetch_for_position(title, limit)
        jobs_by_position[title] = matched
        print(f"  → {len(matched)} jobs collected")

    total = sum(len(v) for v in jobs_by_position.values())
    print(f"\nTotal jobs across all positions: {total} / {config.MAX_TOTAL}")

    print("Generating search links…")
    links = generate_search_links()

    return {
        "jobs":         jobs_by_position,
        "search_links": links,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    result = run_all()
    for pos, jobs in result["jobs"].items():
        print(f"\n[{pos}] {len(jobs)} jobs")
        for j in jobs[:3]:
            print(f"  • {j.title} @ {j.company}  (score={j.score})")
