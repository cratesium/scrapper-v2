"""
Job Search Configuration
=========================
Targeted for a Java Backend Developer with 0–2 years of experience.
Positions: Java Developer + Software Engineer.
Location rules:
  • On-site / hybrid → India only
  • Remote           → anywhere worldwide
Total digest cap: 100 links.
"""

# ---------------------------------------------------------------------------
# Position-wise search config
# Each entry: title searched across ALL sources, capped at its own limit.
# ---------------------------------------------------------------------------
SEARCH_POSITIONS = [
    {"title": "Java Developer",    "limit": 40},
    {"title": "Software Engineer", "limit": 40},
    {"title": "Backend Developer", "limit": 20},
]

MAX_TOTAL = 100   # hard ceiling across all positions

# Only include jobs posted/updated within this window (matches cron cadence)
FRESHNESS_HOURS = 24   # widened to 24h so LinkedIn & slower boards appear

# ---------------------------------------------------------------------------
# Experience target  (used in search-link generation and score boosting)
# ---------------------------------------------------------------------------
EXPERIENCE_MIN = 0    # years
EXPERIENCE_MAX = 2    # years

# ---------------------------------------------------------------------------
# Core skills — used to boost relevance score  (from resume)
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
]

# ---------------------------------------------------------------------------
# Location / remote prefs
# ---------------------------------------------------------------------------
INDIA_CITIES = [
    "india", "noida", "bangalore", "bengaluru", "hyderabad", "pune",
    "mumbai", "delhi", "delhi ncr", "ncr", "gurgaon", "gurugram",
    "chennai", "kolkata", "ahmedabad", "jaipur", "kochi", "blr", "hyd",
]

REMOTE_KEYWORDS = [
    "remote", "worldwide", "global", "anywhere", "distributed",
    "work from home", "wfh", "fully remote",
]

PRIMARY_LOCATION = "India"
INCLUDE_REMOTE   = True
YEARS_EXPERIENCE = EXPERIENCE_MAX   # kept for backward compat

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
