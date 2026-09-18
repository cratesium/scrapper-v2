"""
Job Search Configuration
=========================
Jobs are fetched position-by-position with individual caps.
Total digest cap: 100 links (30 + 30 + 30 + 10).
Optimised for a Java Backend Developer with ~2 years of experience.
"""

# ---------------------------------------------------------------------------
# Position-wise search config
# Each entry: title searched across ALL sources, capped at its own limit.
# Total = sum of all limits (must be ≤ 100).
# ---------------------------------------------------------------------------
SEARCH_POSITIONS = [
    {"title": "Software Engineer",        "limit": 30},
    {"title": "Java Developer",           "limit": 30},
    {"title": "Software Engineer Intern", "limit": 30},
    {"title": "Product Manager Intern",   "limit": 10},
]

MAX_TOTAL = 100   # hard ceiling across all positions

# Only include jobs posted/updated within this window (matches cron cadence)
FRESHNESS_HOURS = 12

# ---------------------------------------------------------------------------
# Core skills — used to boost relevance score for Java/backend roles
# ---------------------------------------------------------------------------
SKILLS = [
    # Primary stack
    "Java", "Spring Boot", "Spring", "Spring MVC", "Spring Security",
    # Architecture
    "Microservices", "REST", "RESTful", "API", "Backend",
    # Messaging / streaming
    "Kafka", "Apache Kafka", "RabbitMQ",
    # DevOps / infra
    "Kubernetes", "Docker", "AWS", "GCP", "CI/CD",
    # Data
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Hibernate", "JPA",
    # Concepts
    "System Design", "Distributed Systems", "Multithreading",
    # PM / intern keywords (scored when relevant)
    "Product Manager", "Product Management", "Intern", "Internship",
    "Roadmap", "Stakeholder", "Agile", "Scrum",
]

# ---------------------------------------------------------------------------
# Location / remote prefs
# ---------------------------------------------------------------------------
LOCATIONS       = ["Noida", "Gurugram", "Delhi NCR", "Bangalore", "Hyderabad", "Pune", "Remote"]
PRIMARY_LOCATION = "India"
INCLUDE_REMOTE  = True
YEARS_EXPERIENCE = 2

# ---------------------------------------------------------------------------
# Email settings  (set as GitHub Actions secrets — never hardcode here)
# TO_EMAIL supports comma-separated list: "a@x.com,b@x.com"
# ---------------------------------------------------------------------------
import os

EMAIL_FROM         = os.environ.get("GMAIL_USER", "")
EMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

_raw_to            = os.environ.get("TO_EMAIL", "")
EMAIL_TO_LIST: list[str] = [e.strip() for e in _raw_to.split(",") if e.strip()]
EMAIL_TO           = ", ".join(EMAIL_TO_LIST)
