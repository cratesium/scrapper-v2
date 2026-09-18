"""Entry point run daily by GitHub Actions."""

import datetime
import os
import re

import job_scraper
import report_generator
import email_sender

REPORT_RETENTION_DAYS = 4   # delete dated reports older than this

_DATE_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.html$")


def _purge_old_reports(reports_dir: str, retention_days: int) -> None:
    """
    Delete dated report files (YYYY-MM-DD.html) that are older than
    `retention_days` days.  Always keeps latest.html untouched.
    """
    cutoff = datetime.date.today() - datetime.timedelta(days=retention_days)
    removed = []

    for fname in os.listdir(reports_dir):
        if not _DATE_FILE_RE.match(fname):
            continue                                   # skip latest.html etc.
        try:
            file_date = datetime.date.fromisoformat(fname.replace(".html", ""))
        except ValueError:
            continue
        if file_date < cutoff:
            path = os.path.join(reports_dir, fname)
            os.remove(path)
            removed.append(fname)

    if removed:
        print(f"Purged {len(removed)} old report(s): {', '.join(sorted(removed))}")
    else:
        print("No old reports to purge.")


def main():
    print("=" * 50)
    print(f"Job scraper run: {datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}")
    print("=" * 50)

    result = job_scraper.run_all()
    html_report = report_generator.build_html(result)

    # Save dated report + update "latest.html"
    os.makedirs("reports", exist_ok=True)
    date_str    = datetime.date.today().isoformat()
    dated_path  = f"reports/{date_str}.html"
    latest_path = "reports/latest.html"

    with open(dated_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html_report)

    print(f"Report saved: {dated_path} and {latest_path}")

    # Clean up reports older than REPORT_RETENTION_DAYS days
    _purge_old_reports("reports", REPORT_RETENTION_DAYS)

    email_sender.send_email(html_report)

    print("Done.")


if __name__ == "__main__":
    main()
