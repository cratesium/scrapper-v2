"""
Job Search Configuration
=========================
Targeted for a Java Backend Developer with 0–2 years of experience.

Position targets  (each fetched across ALL sources):
  Java Developer           → 100
  Software Engineer        → 100
  Backend Developer        →  60
  Software Engineer Intern →  40   (≥20 from each source where possible)
  Intern                   →  30   (≥20 from each source where possible)

  Total cap: 330

Location rules:
  • On-site / hybrid → India only
  • Remote           → anywhere worldwide
"""

# ---------------------------------------------------------------------------
# Position-wise search config
# ---------------------------------------------------------------------------
SEARCH_POSITIONS = [
    {"title": "Java Developer",            "limit": 100},
    {"title": "Software Engineer",         "limit": 100},
    {"title": "Backend Developer",         "limit":  60},
    {"title": "Software Engineer Intern",  "limit":  40},
    {"title": "Developer Intern",          "limit":  30},
]

MAX_TOTAL = 330   # hard ceiling across all positions

# Per-source target — each scraper tries to return this many per query call.
# Aggregated over 5 positions → ~100-150 per source in the final digest.
SOURCE_LIMIT = 30

# ---------------------------------------------------------------------------
# India : Remote ratio  (remaining slots go to "other" / hybrid / vague)
# e.g. 0.65 India + 0.30 Remote + 0.05 Other per position bucket
# ---------------------------------------------------------------------------
INDIA_RATIO  = 0.65
REMOTE_RATIO = 0.30

# Only include jobs posted/updated within this window (matches cron cadence)
FRESHNESS_HOURS = 48   # 48h gives good intern coverage (intern posts are rarer)

# ---------------------------------------------------------------------------
# Experience target
# ---------------------------------------------------------------------------
EXPERIENCE_MIN = 0
EXPERIENCE_MAX = 2

# ---------------------------------------------------------------------------
# Core skills — used to boost relevance score (from resume)
# ---------------------------------------------------------------------------
SKILLS = [
    # Languages
    "Java", "Python", "SQL",
    # Backend & APIs
    "Spring Boot", "Spring", "Spring Reactive", "WebFlux", "RESTful",
    "REST", "WebSocket", "Microservices", "API", "Backend",
    # AI & Agentic
    "Agentic AI", "LLM", "MCP", "Model Context Protocol",
    # Distributed systems & DBs
    "Apache Kafka", "Kafka", "MySQL", "Redis", "Elasticsearch",
    "Distributed Systems",
    # Cloud / Infra / DevOps
    "AWS", "Kubernetes", "k8s", "Amazon EKS", "Docker", "Jenkins",
    "Flyway", "CI/CD", "Cloud",
    # Observability & Testing
    "ELK", "Grafana", "Prometheus", "Kibana", "JUnit", "Mockito",
    "System Design",
    # Core
    "Data Structures", "Algorithms", "DSA", "Agile", "Scrum", "Git",
    # General match helpers
    "Software Engineer", "Software Development", "Backend Engineer",
    "Java Developer", "Fresher", "Entry Level", "Junior",
    # Intern signals
    "Intern", "Internship", "Trainee", "Graduate",
]

# ---------------------------------------------------------------------------
# Location / remote prefs
# ---------------------------------------------------------------------------
INDIA_CITIES = [
    "india", "noida", "bangalore", "bengaluru", "hyderabad", "pune",
    "mumbai", "delhi", "delhi ncr", "ncr", "gurgaon", "gurugram",
    "chennai", "kolkata", "ahmedabad", "jaipur", "kochi", "blr", "hyd",
    "trivandrum", "thiruvananthapuram", "coimbatore", "indore", "bhopal",
    "nagpur", "visakhapatnam", "vizag",
]

REMOTE_KEYWORDS = [
    "remote", "worldwide", "global", "anywhere", "distributed",
    "work from home", "wfh", "fully remote",
]

PRIMARY_LOCATION = "India"
INCLUDE_REMOTE   = True
YEARS_EXPERIENCE = EXPERIENCE_MAX   # kept for backward compat

# ---------------------------------------------------------------------------
# Email settings (set as GitHub Actions secrets — never hardcode here)
# TO_EMAIL supports comma-separated list: "a@x.com,b@x.com"
# ---------------------------------------------------------------------------
import os

EMAIL_FROM         = os.environ.get("GMAIL_USER", "")
EMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

_raw_to            = os.environ.get("TO_EMAIL", "")
EMAIL_TO_LIST: list[str] = [e.strip() for e in _raw_to.split(",") if e.strip()]
EMAIL_TO           = ", ".join(EMAIL_TO_LIST)
