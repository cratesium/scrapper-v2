"""Builds a clean HTML digest from job_scraper results.

Layout:
  • One section per position (e.g. "Software Engineer — 28 jobs")
    – job table inside each section
    – per-position easy-apply search links at the bottom of each section
  • Footer with run timestamp
"""

import datetime
import html as _html


# ---------------------------------------------------------------------------
# Position colours (cycles if more than 4 positions)
# ---------------------------------------------------------------------------
_COLORS = ["#2563eb", "#16a34a", "#9333ea", "#ea580c"]


_LOCATION_ICONS = {
    "remote": "🌐",
    "india":  "🇮🇳",
}

def _location_icon(location: str) -> str:
    loc = location.lower()
    if any(kw in loc for kw in ["remote", "worldwide", "global", "anywhere", "wfh"]):
        return "🌐 "
    if any(kw in loc for kw in ["india", "noida", "bangalore", "bengaluru", "hyderabad",
                                  "pune", "mumbai", "delhi", "gurgaon", "gurugram",
                                  "chennai", "kolkata"]):
        return "🇮🇳 "
    return ""


def _job_row(job) -> str:
    source_badge  = _html.escape(job.source)
    loc_icon      = _location_icon(job.location)
    _SRC_CSS = {
        "LinkedIn":             "src-linkedin",
        "YC Work at a Startup": "src-yc",
        "Wellfound":            "src-wellfound",
    }
    src_class = f"src-badge {_SRC_CSS.get(job.source, '')}"
    return f"""
      <tr>
        <td class="title"><a href="{_html.escape(job.url)}" target="_blank">{_html.escape(job.title)}</a></td>
        <td>{_html.escape(job.company)}</td>
        <td>{loc_icon}{_html.escape(job.location)}</td>
        <td><span class="{src_class}">{source_badge}</span></td>
      </tr>"""


_EASY_APPLY = {"LinkedIn Easy Apply", "YC Work at a Startup", "Wellfound", "Instahyre", "Naukri"}


def _link_pill(name: str, url: str) -> str:
    badge = ' <span class="ea-badge">⚡ Easy Apply</span>' if name in _EASY_APPLY else ""
    return (
        f'<a class="link-pill" href="{_html.escape(url)}" target="_blank">'
        f'{_html.escape(name)}{badge}</a>'
    )


def _position_section(position: str, jobs: list, links: dict, color: str) -> str:
    if not jobs:
        job_table = "<p class='no-jobs'>No open listings found for this position today.</p>"
    else:
        rows      = "".join(_job_row(j) for j in jobs)
        job_table = f"""
      <table>
        <tr><th>Title</th><th>Company</th><th>Location</th><th>Source</th></tr>
        {rows}
      </table>"""

    link_pills = "".join(_link_pill(n, u) for n, u in links.items())

    return f"""
  <section class="position-block" style="--accent:{color}">
    <h2>
      <span class="pos-title">{_html.escape(position)}</span>
      <span class="count">{len(jobs)} jobs</span>
    </h2>
    {job_table}
    <div class="link-row">
      <span class="link-label">🔗 Search live:</span>
      {link_pills}
    </div>
  </section>"""


def build_html(result: dict) -> str:
    today_str       = datetime.date.today().strftime("%A, %d %B %Y")
    jobs_by_pos     = result["jobs"]            # { position: [Job, ...] }
    links_by_pos    = result["search_links"]    # { position: { platform: url } }
    generated_at    = result.get("generated_at", "")

    total_jobs = sum(len(v) for v in jobs_by_pos.values())

    sections = []
    for idx, (position, jobs) in enumerate(jobs_by_pos.items()):
        color = _COLORS[idx % len(_COLORS)]
        pos_links = links_by_pos.get(position, {})
        sections.append(_position_section(position, jobs, pos_links, color))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Job Digest — {today_str}</title>
<style>
  :root {{
    --bg: #ffffff; --fg: #1a1a1a; --muted: #666;
    --border: #e5e7eb; --row-hover: #f9fafb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #0f0f0f; --fg: #f0f0f0; --muted: #999;
             --border: #2a2a2a; --row-hover: #1a1a1a; }}
  }}

  body {{
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    max-width: 960px; margin: 0 auto; padding: 24px;
    background: var(--bg); color: var(--fg);
  }}

  /* Header */
  .header-title {{ font-size: 1.6rem; font-weight: 700; margin: 0; }}
  .header-meta  {{ color: var(--muted); margin: 4px 0 32px; font-size: 0.9rem; }}

  /* Position section */
  .position-block {{
    border-left: 4px solid var(--accent, #2563eb);
    padding: 0 0 0 16px;
    margin-bottom: 40px;
  }}
  .position-block h2 {{
    font-size: 1.15rem; margin: 0 0 12px;
    display: flex; align-items: center; gap: 10px;
  }}
  .pos-title {{ color: var(--accent, #2563eb); }}
  .count {{
    background: var(--border); color: var(--muted);
    border-radius: 99px; padding: 2px 10px;
    font-size: 0.8rem; font-weight: 600;
  }}

  /* Job table */
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
  th, td {{
    text-align: left; padding: 8px 10px;
    border-bottom: 1px solid var(--border); font-size: 0.88rem;
  }}
  th {{ color: var(--muted); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; }}
  tr:hover td {{ background: var(--row-hover); }}
  .title a {{ color: var(--accent, #2563eb); text-decoration: none; font-weight: 500; }}
  .title a:hover {{ text-decoration: underline; }}

  /* Source badge */
  .src-badge {{
    background: var(--border); border-radius: 4px;
    padding: 2px 7px; font-size: 0.78rem; color: var(--muted);
    white-space: nowrap;
  }}

  /* Per-position link row */
  .link-row {{
    display: flex; flex-wrap: wrap; align-items: center;
    gap: 8px; margin-top: 4px;
  }}
  .link-label {{ color: var(--muted); font-size: 0.82rem; }}
  .link-pill {{
    display: inline-flex; align-items: center; gap: 4px;
    background: var(--border); border-radius: 99px;
    padding: 4px 12px; font-size: 0.82rem;
    color: var(--fg); text-decoration: none;
    transition: background 0.15s;
  }}
  .link-pill:hover {{ background: var(--accent, #2563eb); color: #fff; }}
  .ea-badge {{
    background: #dcfce7; color: #15803d;
    border-radius: 4px; padding: 1px 5px; font-size: 0.72rem; font-weight: 700;
  }}
  @media (prefers-color-scheme: dark) {{
    .ea-badge {{ background: #14532d; color: #86efac; }}
  }}

  .no-jobs {{ color: var(--muted); font-size: 0.9rem; margin: 8px 0; }}

  /* Experience badge in header */
  .exp-badge {{
    background: #eff6ff; color: #1d4ed8;
    border-radius: 99px; padding: 2px 10px;
    font-size: 0.78rem; font-weight: 700;
    border: 1px solid #bfdbfe;
  }}
  @media (prefers-color-scheme: dark) {{
    .exp-badge {{ background: #1e3a5f; color: #93c5fd; border-color: #1d4ed8; }}
  }}

  /* Per-source badge colour overrides */
  .src-linkedin    {{ background: #dbeafe; color: #1d4ed8; }}
  .src-yc          {{ background: #fff7ed; color: #c2410c; }}
  .src-wellfound   {{ background: #f0fdf4; color: #15803d; }}
  @media (prefers-color-scheme: dark) {{
    .src-linkedin  {{ background: #1e3a5f; color: #93c5fd; }}
    .src-yc        {{ background: #431407; color: #fb923c; }}
    .src-wellfound {{ background: #14532d; color: #86efac; }}
  }}

  footer {{ margin-top: 40px; color: var(--muted); font-size: 0.78rem; border-top: 1px solid var(--border); padding-top: 12px; }}
</style>
</head>
<body>
  <h1 class="header-title">📋 Daily Job Digest</h1>
  <p class="header-meta">
    {today_str} &nbsp;·&nbsp; {total_jobs} jobs across {len(jobs_by_pos)} positions
    &nbsp;·&nbsp; <span class="exp-badge">0–2 yrs exp</span>
    &nbsp;·&nbsp; 🇮🇳 On-site India &nbsp;·&nbsp; 🌐 Remote worldwide
    &nbsp;·&nbsp; Generated {_html.escape(generated_at)}
  </p>

  {''.join(sections)}

  <footer>Auto-generated twice daily by your GitHub Actions job scraper.</footer>
</body>
</html>"""


def build_email_text(result: dict) -> str:
    return build_html(result)
