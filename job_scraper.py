"""
Job Scraper - pulls fresh listings from open/legitimate job APIs,
and generates fresh pre-filled search links for sites that block
automated scraping (LinkedIn, Naukri, Wellfound, YC Work at a Startup).

Data sources used (all public, no login/ToS violation):
  - RemoteOK API
  - Arbeitnow API
  - We Work Remotely (RSS)
  - Hacker News "Who's Hiring" (via Algolia HN Search API)
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
    title: str
    company: str
    location: str
    url: str
    source: str
    posted: str = ""
    tags: List[str] = field(default_factory=list)
    score: int = 0


def _matches_keywords(text: str) -> bool:
    text_low = text.lower()
    return any(t.lower() in text_low for t in config.JOB_TITLES) or \
           any(s.lower() in text_low for s in config.SKILLS)


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


def fetch_remoteok() -> List[Job]:
    jobs = []
    try:
        r = requests.get("https://remoteok.com/api", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        data = r.json()
        for item in data:
            if not isinstance(item, dict) or "position" not in item:
                continue
            text_blob = f"{item.get('position','')} {' '.join(item.get('tags', []))} {item.get('description','')}"
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
    jobs.sort(key=lambda j: j.score, reverse=True)
    return jobs[:config.MAX_PER_SOURCE]


def fetch_arbeitnow() -> List[Job]:
    jobs = []
    try:
        r = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
        for item in data:
            text_blob = f"{item.get('title','')} {' '.join(item.get('tags', []))} {item.get('description','')}"
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
    jobs.sort(key=lambda j: j.score, reverse=True)
    return jobs[:config.MAX_PER_SOURCE]


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
                text_blob = f"{entry.get('title','')} {entry.get('summary','')}"
                if not _matches_keywords(text_blob):
                    continue
                title = entry.get("title", "Unknown")
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
    jobs.sort(key=lambda j: j.score, reverse=True)
    return jobs[:config.MAX_PER_SOURCE]


def fetch_hn_whoishiring() -> List[Job]:
    """Finds the most recent monthly 'Who is Hiring' thread and searches its comments via Algolia HN API."""
    jobs = []
    try:
        search_url = "https://hn.algolia.com/api/v1/search_by_date"
        params = {"query": "Who is hiring", "tags": "story", "hitsPerPage": 5}
        r = requests.get(search_url, params=params, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        thread_id = None
        for h in hits:
            if h.get("title", "").lower().startswith("ask hn: who is hiring"):
                thread_id = h.get("objectID")
                break
        if not thread_id:
            return jobs

        comments_url = f"https://hn.algolia.com/api/v1/search"
        params = {"tags": f"comment,story_{thread_id}", "hitsPerPage": 200}
        r2 = requests.get(comments_url, params=params, timeout=15)
        r2.raise_for_status()
        comments = r2.json().get("hits", [])
        for c in comments:
            text = (c.get("comment_text") or "")
            if not text or not _matches_keywords(text):
                continue
            snippet = text.replace("<p>", " ").replace("</p>", " ")
            title_line = snippet.strip()[:120].replace("\n", " ")
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
    jobs.sort(key=lambda j: j.score, reverse=True)
    return jobs[:config.MAX_PER_SOURCE]


def generate_search_links() -> dict:
    """
    Generates fresh, pre-filled search URLs for sites that can't be
    safely auto-scraped (login-gated / anti-bot). Click-through, always current.
    """
    primary_title = config.JOB_TITLES[0]
    all_titles_query = " OR ".join(config.JOB_TITLES[:3])
    today = datetime.date.today().isoformat()

    links = {}

    # LinkedIn Jobs search (public search page, no login required to view results list)
    li_params = {
        "keywords": all_titles_query,
        "location": config.PRIMARY_LOCATION,
        "f_TPR": "r86400",  # past 24 hours
    }
    links["LinkedIn"] = "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(li_params)

    # Naukri.com search
    naukri_keywords = "-".join(primary_title.lower().split())
    links["Naukri"] = f"https://www.naukri.com/{naukri_keywords}-jobs?experience=1"

    # Wellfound (AngelList Talent) - role-based search
    wf_role = primary_title.lower().replace(" ", "-")
    links["Wellfound"] = f"https://wellfound.com/role/{wf_role}"

    # Y Combinator Work at a Startup
    yc_params = {"role": primary_title}
    links["YC Work at a Startup"] = "https://www.workatastartup.com/jobs?" + urllib.parse.urlencode(yc_params)

    # Indeed (bonus - public search, generally scrape-tolerant for viewing not automation)
    indeed_params = {"q": primary_title, "l": config.PRIMARY_LOCATION, "fromage": "1"}
    links["Indeed"] = "https://www.indeed.com/jobs?" + urllib.parse.urlencode(indeed_params)

    return links


def run_all() -> dict:
    print("Fetching RemoteOK...")
    remoteok = fetch_remoteok()
    print(f"  -> {len(remoteok)} matches")

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
            "RemoteOK": remoteok,
            "Arbeitnow": arbeitnow,
            "We Work Remotely": wwr,
            "HN Who's Hiring": hn,
        },
        "search_links": links,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    result = run_all()
    total = sum(len(v) for v in result["jobs"].values())
    print(f"\nTotal matched jobs from open APIs: {total}")
    print(f"Search links generated: {list(result['search_links'].keys())}")
