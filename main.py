"""Entry point run daily by GitHub Actions."""

import datetime
import os

import job_scraper
import report_generator
import email_sender


def main():
    print("=" * 50)
    print(f"Job scraper run: {datetime.datetime.utcnow().isoformat()}Z")
    print("=" * 50)

    result = job_scraper.run_all()
    html_report = report_generator.build_html(result)

    # Save dated report + update "latest.html"
    os.makedirs("reports", exist_ok=True)
    date_str = datetime.date.today().isoformat()
    dated_path = f"reports/{date_str}.html"
    latest_path = "reports/latest.html"

    with open(dated_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html_report)

    print(f"Report saved: {dated_path} and {latest_path}")

    email_sender.send_email(html_report)

    print("Done.")


if __name__ == "__main__":
    main()
