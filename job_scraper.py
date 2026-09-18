"""
Job Scraper — fetches jobs position-by-position from multiple sources.

Scraped sources (actual job data pulled):
  - LinkedIn      (public guest API — India, entry-level, paginated ~100/query)
  - Naukri        (internal jobapi — India, 0-2yr exp)
  - YC Work at a Startup  (__NEXT_DATA__ JSON)
  - Wellfound     (__NEXT_DATA__ JSON)
  - RemoteOK
  - Remotive
  - Arbeitnow
  - Jobicy
  - We Work Remotely (RSS)
  - Hacker News "Who's Hiring" (Algolia)

Location policy:
  • Remote jobs   → included regardless of geography
  • On-site/hybrid jobs → India only

Experience target: 0–2 years (passed to APIs where supported).
"""

import json as _json
import re
import time
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
# Freshness filter
# ---------------------------------------------------------------------------

_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_posted(posted: str) -> Optional[datetime.datetime]:
    if not posted:
        return None
    s = str(posted).strip()

    if s.lstrip("-").isdigit():
        try:
            return datetime.datetime.fromtimestamp(int(s), tz=datetime.timezone.utc)
        except Exception:
            pass

    if _DATE_ONLY_RE.match(s):
        try:
            d = datetime.date.fromisoformat(s)
            return datetime.datetime(d.year, d.month, d.day, 12, 0, 0,
                                     tzinfo=datetime.timezone.utc)
        except ValueError:
            pass

    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass

    return None


def _is_fresh(posted: str) -> bool:
    dt = _parse_posted(posted)
    if dt is None:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(hours=config.FRESHNESS_HOURS)
        + datetime.timedelta(minutes=10)
    )
    return dt >= cutoff


# ---------------------------------------------------------------------------
# Location filter
# ---------------------------------------------------------------------------

def _passes_location_filter(location: str) -> bool:
    """Remote → always pass. On-site → India only. Vague → pass."""
    if not location:
        return True
    loc = location.lower()

    if any(kw in loc for kw in config.REMOTE_KEYWORDS):
        return True

    vague = ["varies", "multiple", "various", "flexible", "hybrid",
             "worldwide", "international", "global"]
    if any(kw in loc for kw in vague):
        return True

    if any(kw in loc for kw in config.INDIA_CITIES):
        return True

    return False


# "india" | "remote" | "other"
def _classify_location(location: str) -> str:
    if not location:
        return "other"
    loc = location.lower()
    if any(kw in loc for kw in config.REMOTE_KEYWORDS):
        return "remote"
    if any(kw in loc for kw in config.INDIA_CITIES):
        return "india"
    return "other"


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _matches_query(text: str, query: str) -> bool:
    text_low = text.lower()
    words = [w for w in query.lower().split() if len(w) > 2]
    return any(w in text_low for w in words)


def _score_for(text: str, query: str) -> int:
    text_low  = text.lower()
    query_low = query.lower()
    score = 0

    if query_low in text_low:
        score += 15

    for word in query_low.split():
        if len(word) > 2 and word in text_low:
            score += 3

    for skill in config.SKILLS:
        if skill.lower() in text_low:
            score += 1

    entry_signals = ["0-2", "0 - 2", "fresher", "entry level", "entry-level",
                     "junior", "0-1 year", "1-2 year", "associate",
                     "intern", "internship", "trainee", "graduate", "fresh graduate"]
    for sig in entry_signals:
        if sig in text_low:
            score += 5

    return score


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_HTML_HEADERS = {
    "User-Agent":      _BROWSER_UA,
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
_JSON_HEADERS = {
    "User-Agent":      _BROWSER_UA,
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": _BROWSER_UA})  # only UA in session; per-call overrides accept


def _extract_next_data(html: str) -> dict:
    """Extract the __NEXT_DATA__ JSON blob embedded in Next.js pages."""
    m = re.search(
        r'<script\s+id="__NEXT_DATA__"[^>]*>\s*(\{.*?\})\s*</script>',
        html, re.DOTALL
    )
    if not m:
        return {}
    try:
        return _json.loads(m.group(1))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Source fetchers
# ---------------------------------------------------------------------------

# ── LinkedIn (paginated, India, entry-level) ──────────────────────────────

def _fetch_linkedin(query: str, limit: int) -> List[Job]:
    """
    LinkedIn public guest search — no auth required.
    Paginates through up to 4 pages (25 results each ≈ 100 per query).
    Searches India, entry/associate level (f_E=1,2,3).
    """
    jobs = []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("  [LinkedIn] beautifulsoup4 not installed — run: pip install beautifulsoup4")
        return jobs

    seen_urls: set = set()
    page_size  = 25
    max_pages  = max(1, min(4, (limit + page_size - 1) // page_size))

    for page in range(max_pages):
        try:
            params = {
                "keywords": query,
                "location": "India",
                "start":    str(page * page_size),
                "f_E":      "1,2,3",      # Internship, Entry Level, Associate
                "f_TPR":    "r172800",    # past 48 h (matches FRESHNESS_HOURS)
                "sortBy":   "DD",
            }
            r = _SESSION.get(
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                params=params,
                headers=_HTML_HEADERS,
                timeout=20,
            )
            r.raise_for_status()

            soup  = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("li")
            if not cards:
                break                          # no more results on this page

            new_this_page = 0
            for card in cards:
                try:
                    title_el    = card.find(class_="base-search-card__title")
                    company_el  = card.find(class_="base-search-card__subtitle")
                    location_el = card.find(class_="job-search-card__location")
                    link_el     = card.find("a", class_="base-card__full-link")
                    time_el     = card.find("time")

                    if not title_el or not link_el:
                        continue

                    url = (link_el.get("href") or "").split("?")[0]
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title    = title_el.get_text(strip=True)
                    company  = company_el.get_text(strip=True) if company_el else "Unknown"
                    location = location_el.get_text(strip=True) if location_el else "India"
                    posted   = time_el.get("datetime", "") if time_el else ""

                    text = f"{title} {company} {location}"
                    if not _matches_query(text, query):
                        continue

                    jobs.append(Job(
                        title    = title,
                        company  = company,
                        location = location,
                        url      = url or "https://www.linkedin.com/jobs",
                        source   = "LinkedIn",
                        posted   = posted,
                        score    = _score_for(text, query),
                    ))
                    new_this_page += 1
                except Exception:
                    continue

            if new_this_page == 0:
                break           # LinkedIn returned a page with no new results

            time.sleep(0.5)     # be polite between pages

        except Exception as e:
            print(f"  [LinkedIn] {query} page {page + 1}: {e}")
            break

    return jobs


# ── Naukri (internal jobapi, India, experience-filtered) ─────────────────

def _fetch_naukri(query: str, limit: int) -> List[Job]:
    """
    Naukri internal search API — India-specific, 0-2yr experience filter.
    Seeds cookies by visiting the homepage first, then hits the JSON API.
    """
    jobs = []
    try:
        naukri_session = requests.Session()
        # Seed cookies by visiting homepage
        naukri_session.get(
            "https://www.naukri.com/",
            headers=_HTML_HEADERS,
            timeout=15,
        )

        ts = int(time.time() * 1000)
        r = naukri_session.get(
            "https://www.naukri.com/jobapi/v3/search",
            params={
                "noOfResults":  min(limit * 2, 100),
                "urlType":      "search_by_key_loc",
                "searchType":   "adv",
                "keyword":      query,
                "location":     "india",
                "experience":   config.EXPERIENCE_MIN,
                "jobAge":       3,
                "t":            ts,
            },
            headers={
                **_JSON_HEADERS,
                "Referer":  "https://www.naukri.com/",
                "Origin":   "https://www.naukri.com",
                "appid":    "109",
                "systemid": "109",
                "gid":      "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()

        for item in data.get("jobDetails", []):
            title   = item.get("title", "").strip()
            company = item.get("companyName", "Unknown").strip()

            location = "India"
            for ph in item.get("placeholders", []):
                if ph.get("label") == "location":
                    location = ph.get("value", "India").strip()
                    break

            jd_url = item.get("jdURL", "") or item.get("jobLink", "")
            if not jd_url:
                continue
            url = jd_url if jd_url.startswith("http") else f"https://www.naukri.com{jd_url}"

            tags_raw = item.get("tagsAndSkills", "") or ""
            tags     = [t.strip() for t in tags_raw.split(",") if t.strip()]
            text     = f"{title} {company} {location} {tags_raw}"

            if not _matches_query(text, query):
                continue

            jobs.append(Job(
                title    = title,
                company  = company,
                location = location,
                url      = url,
                source   = "Naukri",
                posted   = "",          # Naukri uses relative dates ("2d ago") — treat fresh
                tags     = tags,
                score    = _score_for(text, query),
            ))

    except Exception as e:
        print(f"  [Naukri] {query}: {e}")
    return jobs


# ── YC Work at a Startup ─────────────────────────────────────────────────

def _fetch_yc(query: str, limit: int) -> List[Job]:
    """
    YC Work at a Startup — uses Inertia.js `data-page` attribute.
    Each page returns 30 jobs; paginate to reach `limit`.
    """
    jobs = []
    seen: set = set()
    pages = max(1, min(4, (limit + 29) // 30))

    for page in range(1, pages + 1):
        try:
            r = requests.get(
                "https://www.workatastartup.com/jobs",
                params={"role": "eng", "q": query, "remote": "yes", "page": page},
                headers={**_HTML_HEADERS, "Referer": "https://www.workatastartup.com/"},
                timeout=25,
            )
            r.raise_for_status()

            m = re.search(r'data-page="([^"]+)"', r.text)
            if not m:
                break
            from html import unescape as _unescape
            page_data = _json.loads(_unescape(m.group(1)))
            raw_jobs  = page_data.get("props", {}).get("jobs", [])
            if not raw_jobs:
                break

            new_this_page = 0
            for item in raw_jobs:
                try:
                    title   = (item.get("title") or "").strip()
                    company = (item.get("companyName") or "Unknown").strip()
                    loc_raw = item.get("location") or ""
                    # YC location field: "Remote" or "City, ST" or empty
                    location = loc_raw.strip() or "Remote"
                    url      = item.get("applyUrl") or (
                        f"https://www.workatastartup.com/jobs/{item.get('id','')}"
                    )
                    text = f"{title} {company} {location} {item.get('roleType','')} {item.get('jobType','')}"

                    if not title or not _matches_query(text, query):
                        continue
                    if url in seen:
                        continue
                    seen.add(url)

                    jobs.append(Job(
                        title    = title,
                        company  = company,
                        location = location,
                        url      = url,
                        source   = "YC Work at a Startup",
                        posted   = "",   # no date field; treat as fresh (site shows open roles)
                        score    = _score_for(text, query),
                    ))
                    new_this_page += 1
                except Exception:
                    continue

            if new_this_page == 0:
                break
            time.sleep(0.3)

        except Exception as e:
            print(f"  [YC] {query} page {page}: {e}")
            break

    return jobs


# ── Wellfound ─────────────────────────────────────────────────────────────

def _fetch_wellfound(query: str, limit: int) -> List[Job]:
    """
    Wellfound — parses __NEXT_DATA__ Apollo state embedded in their search page.
    Resolves JobListing:* and Startup:* refs from the Apollo cache.
    """
    jobs = []
    try:
        r = requests.get(
            "https://wellfound.com/jobs",
            params={"q": query, "remote": "true"},
            headers={**_HTML_HEADERS, "Referer": "https://wellfound.com/"},
            timeout=25,
        )
        r.raise_for_status()

        nd = _extract_next_data(r.text)
        apollo_data = (
            nd.get("props", {})
              .get("pageProps", {})
              .get("apolloState", {})
              .get("data", {})
        )
        if not apollo_data:
            return jobs

        # Build a ref-resolver for __ref lookups
        def _resolve(obj):
            if isinstance(obj, dict) and "__ref" in obj:
                return apollo_data.get(obj["__ref"], {})
            return obj or {}

        # Extract all concrete JobListing entries (not Config)
        for key, item in apollo_data.items():
            if not (key.startswith("JobListing:") and
                    not key.startswith("JobListingRemoteConfig")):
                continue
            try:
                title    = (item.get("title") or "").strip()
                slug     = item.get("slug") or item.get("id") or ""
                url      = f"https://wellfound.com/jobs/{slug}" if slug else "https://wellfound.com/jobs"

                # Company from Startup ref
                startup  = _resolve(item.get("startup", {}))
                company  = startup.get("name", "Unknown")

                # Location
                locs     = item.get("locationNames") or item.get("acceptedRemoteLocationNames") or []
                location = ", ".join(locs) if locs else "Remote"
                if item.get("remote"):
                    location = f"Remote / {location}" if location != "Remote" else "Remote"

                # liveStartAt is a Unix timestamp
                posted   = str(item.get("liveStartAt", ""))

                text = f"{title} {company} {location}"
                if not title or not _matches_query(text, query):
                    continue

                jobs.append(Job(
                    title    = title,
                    company  = company,
                    location = location,
                    url      = url,
                    source   = "Wellfound",
                    posted   = posted,
                    score    = _score_for(text, query),
                ))
            except Exception:
                continue

    except Exception as e:
        print(f"  [Wellfound] {query}: {e}")
    return jobs


# ── RemoteOK ──────────────────────────────────────────────────────────────

def _fetch_remoteok(query: str, limit: int) -> List[Job]:
    jobs = []
    try:
        r = _SESSION.get("https://remoteok.com/api", timeout=15)
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


# ── Remotive ──────────────────────────────────────────────────────────────

def _fetch_remotive(query: str, limit: int) -> List[Job]:
    jobs = []
    try:
        r = _SESSION.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": limit * 2},
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


# ── Jobicy ────────────────────────────────────────────────────────────────

def _fetch_jobicy(query: str, limit: int) -> List[Job]:
    jobs = []
    tag_map = {
        "java developer":            "java",
        "software engineer":         "software-engineer",
        "backend developer":         "backend",
        "software engineer intern":  "intern",
        "developer intern":          "intern",
    }
    tag = tag_map.get(query.lower(), query.lower().replace(" ", "-"))
    try:
        r = _SESSION.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"tag": tag, "count": limit * 2},
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


# ── Arbeitnow ─────────────────────────────────────────────────────────────

def _fetch_arbeitnow(query: str, limit: int) -> List[Job]:
    jobs = []
    try:
        r = _SESSION.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
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


# ── We Work Remotely ──────────────────────────────────────────────────────

def _fetch_weworkremotely(query: str, limit: int) -> List[Job]:
    jobs = []
    feeds = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
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


# ── Hacker News Who's Hiring ──────────────────────────────────────────────

def _fetch_hn(query: str, limit: int) -> List[Job]:
    jobs = []
    try:
        r = _SESSION.get(
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

        r2 = _SESSION.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query":       query,
                "tags":        f"comment,story_{thread_id}",
                "hitsPerPage": limit * 2,
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
    _fetch_linkedin,          # India-focused, entry-level, paginated ~100/query
    _fetch_yc,                # YC startups — Inertia.js, paginated ~120/query
    _fetch_wellfound,         # Wellfound — Apollo state, ~46/query
    _fetch_remoteok,
    _fetch_remotive,
    _fetch_jobicy,
    _fetch_arbeitnow,
    _fetch_weworkremotely,
    _fetch_hn,
    # _fetch_naukri — requires JS rendering; Naukri kept as search-link only
]

# Track per-source counts for the summary
_SOURCE_COUNTS: Dict[str, int] = {}


def _fetch_for_position(title: str, limit: int) -> List[Job]:
    """
    Call every source for `title`, merge results, apply:
      1. Freshness filter  (FRESHNESS_HOURS)
      2. Location filter   (India on-site / anywhere remote)
    Deduplicate by URL, sort by score, return top `limit` jobs.
    """
    all_jobs: List[Job] = []
    seen_urls: set      = set()
    stale_count         = 0
    location_dropped    = 0
    source_raw: Dict[str, int] = {}

    for fetcher in _FETCHERS:
        raw = fetcher(title, config.SOURCE_LIMIT)
        src = raw[0].source if raw else fetcher.__name__.replace("_fetch_", "").title()
        source_raw[src] = source_raw.get(src, 0) + len(raw)

        for job in raw:
            if not _is_fresh(job.posted):
                stale_count += 1
                continue
            if not _passes_location_filter(job.location):
                location_dropped += 1
                continue
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                all_jobs.append(job)

    if stale_count:
        print(f"  ↳ dropped {stale_count} stale (>{config.FRESHNESS_HOURS}h) | "
              f"{location_dropped} non-India on-site")

    # Log per-source raw counts for this position
    src_summary = "  ↳ raw/source: " + " | ".join(
        f"{s}={n}" for s, n in sorted(source_raw.items())
    )
    print(src_summary)

    all_jobs.sort(key=lambda j: j.score, reverse=True)

    # ── Enforce 65 : 30 India : Remote ratio ─────────────────────────────
    india_cap  = round(limit * config.INDIA_RATIO)   # e.g. 65 out of 100
    remote_cap = round(limit * config.REMOTE_RATIO)  # e.g. 30 out of 100
    other_cap  = limit - india_cap - remote_cap       # remaining (5)

    buckets: Dict[str, List[Job]] = {"india": [], "remote": [], "other": []}
    for job in all_jobs:
        cat = _classify_location(job.location)
        buckets[cat].append(job)

    selected: List[Job] = (
        buckets["india"][:india_cap]
        + buckets["remote"][:remote_cap]
        + buckets["other"][:other_cap]
    )
    # If any bucket is short, fill from others (preserve score order)
    if len(selected) < limit:
        used_urls = {j.url for j in selected}
        for job in all_jobs:
            if len(selected) >= limit:
                break
            if job.url not in used_urls:
                selected.append(job)
                used_urls.add(job.url)

    # Re-sort by score so the final list is score-ordered
    selected.sort(key=lambda j: j.score, reverse=True)

    india_n  = sum(1 for j in selected if _classify_location(j.location) == "india")
    remote_n = sum(1 for j in selected if _classify_location(j.location) == "remote")
    other_n  = len(selected) - india_n - remote_n
    print(f"  ↳ ratio — 🇮🇳 India={india_n}  🌐 Remote={remote_n}  Other={other_n}")

    return selected


# ---------------------------------------------------------------------------
# Search-link generator  (click-through easy-apply links per position)
# ---------------------------------------------------------------------------

def generate_search_links() -> Dict[str, Dict[str, str]]:
    result = {}

    for pos in config.SEARCH_POSITIONS:
        title = pos["title"]
        links = {}

        # LinkedIn Easy Apply — India, entry level, past 48 h
        links["LinkedIn Easy Apply"] = (
            "https://www.linkedin.com/jobs/search/?"
            + urllib.parse.urlencode({
                "keywords": title,
                "location": config.PRIMARY_LOCATION,
                "f_TPR":    "r172800",  # 48 h
                "f_AL":     "true",
                "f_E":      "1,2,3",
                "sortBy":   "DD",
            })
        )

        # YC Work at a Startup
        links["YC Work at a Startup"] = (
            "https://www.workatastartup.com/jobs?"
            + urllib.parse.urlencode({"role": "eng", "q": title, "remote": "yes"})
        )

        # Wellfound
        links["Wellfound"] = (
            "https://wellfound.com/jobs?"
            + urllib.parse.urlencode({"q": title, "remote": "true"})
        )

        # Naukri — India, 0–2 years
        naukri_kw = "-".join(title.lower().split())
        links["Naukri"] = (
            f"https://www.naukri.com/{naukri_kw}-jobs?"
            + urllib.parse.urlencode({
                "experience": f"{config.EXPERIENCE_MIN}-{config.EXPERIENCE_MAX}",
                "location":   "India",
            })
        )

        # Instahyre — India fresher/junior roles
        links["Instahyre"] = (
            "https://www.instahyre.com/search-jobs/?"
            + urllib.parse.urlencode({
                "q":          title,
                "location":   "India",
                "experience": f"{config.EXPERIENCE_MIN}-{config.EXPERIENCE_MAX}",
            })
        )

        # Indeed India
        links["Indeed India"] = (
            "https://in.indeed.com/jobs?"
            + urllib.parse.urlencode({
                "q":       title,
                "l":       "India",
                "fromage": "3",
                "explvl":  "entry_level",
            })
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
        print(f"\nFetching '{title}' (limit {limit})…")
        matched = _fetch_for_position(title, limit)
        jobs_by_position[title] = matched
        print(f"  → {len(matched)} jobs collected")

    total = sum(len(v) for v in jobs_by_position.values())
    print(f"\nTotal jobs across all positions: {total} / {config.MAX_TOTAL}")

    # Per-source summary across all positions
    source_totals: Dict[str, int] = {}
    for jobs in jobs_by_position.values():
        for j in jobs:
            source_totals[j.source] = source_totals.get(j.source, 0) + 1
    print("Source breakdown: " + " | ".join(
        f"{s}={n}" for s, n in sorted(source_totals.items(), key=lambda x: -x[1])
    ))

    print("\nGenerating search links…")
    links = generate_search_links()

    return {
        "jobs":         jobs_by_position,
        "search_links": links,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }


if __name__ == "__main__":
    result = run_all()
    for pos, jobs in result["jobs"].items():
        print(f"\n[{pos}] {len(jobs)} jobs")
        for j in jobs[:3]:
            print(f"  • {j.title} @ {j.company} | {j.location}  [{j.source}] (score={j.score})")
