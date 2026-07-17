"""Configuration for India Job Alerts.

Central configuration using Python dataclasses. All constants, URLs, output paths,
dedup settings, and caption format settings live here. Environment variables
override defaults where applicable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class SourceConfig:
    """Configuration for a single job source."""

    name: str
    base_url: str
    search_url: str
    enabled: bool = True
    rate_limit_seconds: float = 2.0
    max_retries: int = 3


@dataclass
class DedupConfig:
    """Deduplication settings."""

    fingerprint_algorithm: str = "sha256"
    fingerprint_fields: List[str] = field(
        default_factory=lambda: ["title", "company", "location"]
    )
    retention_days: int = 7


@dataclass
class CaptionConfig:
    """Instagram caption format settings."""

    corporate_header: str = "\U0001f6a8 Hiring Now!"
    government_header: str = "\U0001f3db\ufe0f GOVERNMENT JOB ALERT!"
    org_label_corporate: str = "Company"
    org_label_government: str = "Organization"
    separator: str = "\n---\n"
    hashtags_global: List[str] = field(
        default_factory=lambda: ["#jobs", "#indiajobs", "#hiring"]
    )


@dataclass
class AppConfig:
    """Application-wide configuration."""

    # --- Sources ---
    sources: List[SourceConfig] = field(default_factory=lambda: [
        SourceConfig(
            name="naukri",
            base_url="https://www.naukri.com",
            search_url="https://www.naukri.com/jobapi/v3/search?noOfResults=50&urlType=search_by_keyword&searchType=adv&keyword=all+jobs+india",
        ),
        SourceConfig(
            name="indeed",
            base_url="https://in.indeed.com",
            search_url="https://in.indeed.com/jobs?q=&l=India&sort=date&limit=50",
        ),
        SourceConfig(
            name="linkedin",
            base_url="https://www.linkedin.com",
            search_url="https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=&location=India&start=0",
        ),
        SourceConfig(
            name="freejobalert",
            base_url="https://www.freejobalert.com",
            search_url="https://www.freejobalert.com/latest-notifications/",
        ),
        SourceConfig(
            name="govtportals",
            base_url="https://www.sarkariresult.com",
            search_url="https://www.sarkariresult.com/latestjob/",
        ),
    ])

    # --- Output paths ---
    data_dir: str = "data"
    output_dir: str = "output"
    posted_jobs_file: str = "data/posted-jobs.json"
    captions_filename_template: str = "captions-{date}.md"
    readme_path: str = "README.md"

    # --- Dedup ---
    dedup: DedupConfig = field(default_factory=DedupConfig)

    # --- Captions ---
    caption: CaptionConfig = field(default_factory=CaptionConfig)

    # --- Limits ---
    max_jobs_per_source: int = 50

    # --- GitHub ---
    github_token: Optional[str] = field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Build config with environment variable overrides.

        Reads MAX_JOBS_PER_SOURCE and DEDUP_DAYS from environment.
        """
        max_jobs = int(os.getenv("MAX_JOBS_PER_SOURCE", "50"))
        dedup_days = int(os.getenv("DEDUP_DAYS", "7"))
        config = cls()
        config.max_jobs_per_source = max_jobs
        config.dedup.retention_days = dedup_days
        return config


# ---------------------------------------------------------------------------
# Category keyword map — used by categorizer.py
# ---------------------------------------------------------------------------

CATEGORY_MAP: Dict[str, List[str]] = {
    "IT": [
        "software", "developer", "engineer", "programmer", "python", "java",
        "javascript", "react", "angular", "node", "full stack", "backend",
        "frontend", "devops", "cloud", "aws", "azure", "gcp", "docker",
        "kubernetes", "data science", "machine learning", "ai", "artificial intelligence",
        "cyber security", "security", "network", "system admin", "it support",
        "database", "sql", "qa", "testing", "mobile", "android", "ios",
        "flutter", "blockchain", "web developer", "app developer", "php",
        ".net", "c#", "c++", "ruby", "swift", "golang", "rust", "scala",
        "tech lead", "cto", "sre", "platform", "infrastructure", "scrum",
    ],
    "Government": [
        "government", "govt", "sarkari", "public sector", "psu", "central govt",
        "state govt", "railway", "defence", "bank of", "rbi", "ssc", "upsc",
        "bpsc", "mppsc", "uppsc", "civil service", "ias", "ips", "irs",
        "ifos", "navy", "army", "air force", "police", "forest", "pwd",
        "municipal", "corporation", "nisg", "nabard", "sebi", "irda",
        "parliament", "lok sabha", "rajya sabha", "legislative", "district court",
        "high court", "supreme court", "income tax", "customs", "gst",
        "excise", "post office", "india post", "bsnl", "mtnl", "psu jobs",
        "rrb", "ibps", "sbi", "fci", "coal india", "ongc", "gail",
    ],
    "Freshers": [
        "fresher", "freshers", "fresh graduate", "trainee", "intern",
        "entry level", "graduate trainee", "campus", "apprenticeship",
        "apprentice", "junior", "management trainee", "0 year",
        "zero experience", "walk-in", "walkin", "no experience",
    ],
    "Remote": [
        "remote", "work from home", "wfh", "work from anywhere", "telecommute",
        "virtual", "distributed", "hybrid", "home based", "online",
        "freelance", "freelancer", "contract",
    ],
    "Banking": [
        "banking", "bank", "finance", "financial", "investment", "equity",
        "mutual fund", "insurance", "loans", "credit", "nbfc", "fintech",
        "accounting", "accountant", "audit", "tax", "treasury", "chartered",
        "cfa", "ca", "actuarial", "underwriter", "wealth management",
    ],
    "Engineering": [
        "civil engineer", "mechanical", "electrical", "electronics",
        "chemical", "structural", "aeronautical", "automobile", "marine",
        "production", "manufacturing", "industrial", "design engineer",
        "site engineer", "project engineer", "maintenance", "quality engineer",
        "safety engineer", "environmental engineer", "bim", "cad", "autocad",
        "solidworks", "catia", "revit", "primavera", "piping",
    ],
    "Healthcare": [
        "doctor", "medical", "nurse", "hospital", "healthcare", "pharma",
        "pharmacy", "clinical", "surgeon", "physician", "dentist", "ayush",
        "biomedical", "biotech", "biotechnology", "lab technician",
        "radiologist", "pathology", "therapist", "psychologist", "counselor",
        "veterinary", "public health", "dietitian", "nutrition",
    ],
    "Sales": [
        "sales", "business development", "bde", "bdm", "account executive",
        "account manager", "client relation", "customer success",
        "presales", "inside sales", "field sales", "territory",
        "telesales", "retail", "showroom", "franchise", "channel sales",
    ],
    "Marketing": [
        "marketing", "digital marketing", "seo", "sem", "ppc", "social media",
        "content writer", "content marketing", "copywriter", "brand",
        "growth", "analytics", "market research", "advertising", "pr",
        "public relations", "communications", "media", "event management",
        "influencer", "affiliate", "email marketing", "graphic designer",
        "ui", "ux", "product design", "video editor", "animation",
    ],
    "Startup": [
        "startup", "founding", "co-founder", "head of", "vp of",
        "director of", "early stage", "seed", "venture", "growth hacker",
    ],
    "PSU": [
        "psu", "public sector undertaking", "bhel", "ntpc", "nhpc",
        "power grid", "sail", "ntpc", "nhpc", "hal", "bel", "beml",
        "mazagon", "garden reach", "hmt", "itdc", "hudco",
    ],
    "Part Time": [
        "part time", "part-time", "weekend", "evening", "temporary",
        "temp", "seasonal", "hourly", "gig", "side hustle",
    ],
    "Education": [
        "teacher", "professor", "lecturer", "faculty", "education",
        "school", "college", "university", "academic", "research",
        "training", "instructor", "tutor", "principal", "dean",
        "librarian", "administration", "admissions", "edtech",
    ],
    "HR": [
        "hr", "human resource", "recruiter", "recruitment", "talent",
        "payroll", "compensation", "benefits", "people operations",
        "l&d", "learning and development", "hrbp", "hr business partner",
        "onboarding", "employee", "workforce", "staffing",
    ],
}

# User-agent rotation list for scrapers
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# Logging defaults
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
