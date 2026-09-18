"""Builds a clean HTML digest from job_scraper results."""

import datetime
import html


def _job_row(job) -> str:
    return f"""
    <tr>
      <td class="title"><a href="{html.escape(job.url)}" target="_blank">{html.escape(job.title)}</a></td>
      <td>{html.escape(job.company)}</td>
      <td>{html.escape(job.location)}</td>
      <td class="src">{html.escape(job.source)}</td>
    </tr>"""


def build_html(result: dict) -> str:
    today_str = datetime.date.today().strftime("%A, %d %B %Y")
    jobs_by_source = result["jobs"]
    links = result["search_links"]

    sections = []
    for source, jobs in jobs_by_source.items():
        if not jobs:
            continue
        rows = "".join(_job_row(j) for j in jobs)
        sections.append(f"""
        <h2>{html.escape(source)} <span class="count">({len(jobs)})</span></h2>
        <table>
          <tr><th>Title</th><th>Company</th><th>Location</th><th>Source</th></tr>
          {rows}
        </table>""")

    if not sections:
        sections.append("<p>No new matching jobs from open APIs today. Check the search links below.</p>")

    link_items = "".join(
        f'<li><a href="{html.escape(url)}" target="_blank">{html.escape(name)} — today\'s search</a></li>'
        for name, url in links.items()
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Daily Job Digest — {today_str}</title>
<style>
  :root {{
    --bg: #ffffff; --fg: #1a1a1a; --muted: #666; --accent: #2563eb; --border: #e5e7eb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg: #0f0f0f; --fg: #f0f0f0; --muted: #999; --accent: #60a5fa; --border: #2a2a2a; }}
  }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 24px; background: var(--bg); color: var(--fg); }}
  h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .subtitle {{ color: var(--muted); margin-bottom: 24px; }}
  h2 {{ font-size: 1.1rem; margin-top: 28px; border-bottom: 2px solid var(--border); padding-bottom: 6px; }}
  .count {{ color: var(--muted); font-weight: normal; font-size: 0.9rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid var(--border); font-size: 0.92rem; }}
  th {{ color: var(--muted); font-weight: 600; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .src {{ color: var(--muted); font-size: 0.85rem; }}
  .links-section {{ margin-top: 32px; padding: 16px; border: 1px solid var(--border); border-radius: 8px; }}
  .links-section ul {{ margin: 8px 0 0 0; padding-left: 20px; }}
  .links-section li {{ margin-bottom: 6px; }}
  footer {{ margin-top: 32px; color: var(--muted); font-size: 0.8rem; }}
</style>
</head>
<body>
  <h1>📋 Daily Job Digest</h1>
  <div class="subtitle">{today_str} · Generated {html.escape(result.get('generated_at',''))}</div>

  {''.join(sections)}

  <div class="links-section">
    <strong>🔗 Fresh search links (click for today's live results)</strong>
    <ul>{link_items}</ul>
  </div>

  <footer>Auto-generated daily by your GitHub Actions job scraper.</footer>
</body>
</html>"""
    return html_doc


def build_email_text(result: dict) -> str:
    """Plain-ish text/HTML body suitable for an email."""
    return build_html(result)
