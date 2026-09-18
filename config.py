"""
Job Search Configuration
=========================
Edit this file to change what jobs you're searching for.
Everything here was seeded from your resume - tweak freely.
"""

# --- Job titles to search for (used for API queries + search link generation) ---
JOB_TITLES = [
    "Backend Engineer",
    "Software Engineer",
    "Java Developer",
    "SDE",
    "Spring Boot Developer",
]

# --- Core skills (used to score/rank incoming listings by relevance) ---
SKILLS = [
    "Java", "Spring Boot", "Spring", "Microservices", "Kafka", "Apache Kafka",
    "Kubernetes", "k8s", "AWS", "Docker", "Redis", "Elasticsearch", "MySQL",
    "REST", "RESTful", "System Design", "Distributed Systems", "Backend",
]

# --- Experience level ---
EXPERIENCE_LEVEL = "entry"  # "intern" | "entry" | "mid" | "senior"
YEARS_EXPERIENCE = 1

# --- Locations (used in search links + API filters where supported) ---
LOCATIONS = [
    "Noida",
    "Delhi NCR",
    "Bangalore",
    "Remote",
]

# Primary location for site search links (LinkedIn/Naukri geo-id lookups etc.)
PRIMARY_LOCATION = "India"

# --- Remote-only toggle for the open-API sources (RemoteOK, WWR, etc. are remote-first anyway) ---
INCLUDE_REMOTE = True

# --- How many days back to consider a listing "fresh" ---
FRESHNESS_DAYS = 2

# --- Max jobs to include per source in the report (keeps digest readable) ---
MAX_PER_SOURCE = 8

# --- Email settings (values come from GitHub Actions secrets at runtime; these are fallbacks for local testing) ---
import os
EMAIL_FROM = os.environ.get("GMAIL_USER", "")
EMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
EMAIL_TO = os.environ.get("TO_EMAIL", "")
