"""
Job Search Configuration
=========================
Edit this file to change what jobs you're searching for.
Optimised for a Java Backend Developer with ~2 years of experience.
"""

# --- Job titles to search for ---
JOB_TITLES = [
    "Java Developer",
    "Backend Java Engineer",
    "Software Engineer",
    "Backend Engineer",
    "Java Backend Developer",
    "SDE",
    "Spring Boot Developer",
    "Java Software Engineer",
]

# --- Core skills (used to score/rank incoming listings by relevance) ---
SKILLS = [
    # Primary stack
    "Java", "Spring Boot", "Spring", "Spring MVC", "Spring Security",
    # Architecture
    "Microservices", "REST", "RESTful", "API", "Backend",
    # Messaging / streaming
    "Kafka", "Apache Kafka", "RabbitMQ", "ActiveMQ",
    # DevOps / infra
    "Kubernetes", "k8s", "Docker", "AWS", "GCP", "Azure", "CI/CD",
    # Data
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "Hibernate", "JPA",
    # Concepts
    "System Design", "Distributed Systems", "Multithreading", "Concurrency",
]

# --- Experience level ---
EXPERIENCE_LEVEL = "entry"          # 2 yrs still qualifies for entry/associate roles
YEARS_EXPERIENCE = 2                # used in search-link params

# --- Locations ---
LOCATIONS = [
    "Noida",
    "Gurugram",
    "Delhi NCR",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Remote",
]
PRIMARY_LOCATION = "India"

# --- Remote toggle ---
INCLUDE_REMOTE = True

# --- How many days back a listing is considered "fresh" ---
FRESHNESS_DAYS = 2

# --- Max jobs per source in the digest ---
MAX_PER_SOURCE = 8

# ---------------------------------------------------------------------------
# Email settings
# ---------------------------------------------------------------------------
# TO_EMAIL can be a single address OR a comma-separated list, e.g.:
#   TO_EMAIL=alice@gmail.com,bob@gmail.com
#
# Set these as GitHub Actions encrypted secrets (never hardcode here).
# ---------------------------------------------------------------------------
import os

EMAIL_FROM        = os.environ.get("GMAIL_USER", "")
EMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

_raw_to           = os.environ.get("TO_EMAIL", "")
EMAIL_TO_LIST: list[str] = [e.strip() for e in _raw_to.split(",") if e.strip()]
EMAIL_TO          = ", ".join(EMAIL_TO_LIST)   # kept for display / header
