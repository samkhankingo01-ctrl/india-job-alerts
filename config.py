"""Configuration dataclass and factory for the India Jobs Board pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class Config:
    """Central configuration for the India Jobs Board scraper pipeline."""

    # ── API sources ──────────────────────────────────────────────────────────
    sources: list[dict[str, str]] = field(default_factory=lambda: [
        {"name": "jsearch", "base_url": "https://jsearch.p.rapidapi.com"},
        {"name": "arbeitnow", "base_url": "https://www.arbeitnow.com/api"},
        {"name": "remotive", "base_url": "https://remotive.com/api"},
    ])

    # ── JSearch queries (India-specific) ─────────────────────────────────────
    SEARCH_QUERIES: ClassVar[list[str]] = [
        "software engineer jobs in India",
        "government jobs India 2025",
        "IT jobs India freshers",
        "banking jobs India",
        "remote jobs India",
        "data scientist jobs India",
        "mechanical engineer jobs India",
        "MBA jobs India",
        "teaching jobs India",
        "healthcare jobs India",
        "PSU jobs India 2025",
        "startup jobs Bangalore India",
        "sales jobs India",
        "part time jobs India",
        "HR jobs India",
    ]

    # ── Category mapping ─────────────────────────────────────────────────────
    CATEGORY_MAP: ClassVar[dict[str, list[str]]] = {
        "IT": [
            "software engineer", "software developer", "software",
            "developer", "programmer", "data scientist", "data engineer",
            "machine learning", "artificial intelligence", "ai engineer",
            "full stack", "frontend", "backend", "devops", "cloud engineer",
            "aws", "azure", "cyber security", "security analyst",
            "network engineer", "system admin", "system administrator",
            "database", "sql", "dba", "qa engineer", "qa tester",
            "mobile developer", "android developer", "ios developer",
            "flutter", "web developer", "php", "python",
            "java developer", "javascript", "react", "node", "nodejs",
        ],
        "Government": [
            "government", "govt", "sarkari", "public sector",
            "civil service", "ias", "ips", "defence", "railway",
            "bank clerk", "ssc", "upsc", "state government",
            "central government", "ministry", "municipal",
        ],
        "Freshers": [
            "fresher", "fresh graduate", "entry level",
            "trainee", "intern", "internship", "graduate trainee",
            "campus", "0-1 year", "0 year", "freshers",
        ],
        "Remote": [
            "remote", "work from home", "wfh", "telecommute",
            "virtual", "distributed", "anywhere", "home based",
        ],
        "Banking": [
            "bank", "banking", "finance", "financial",
            "investment", "insurance", "nbfc", "loan", "credit",
            "treasury", "accounting", "accountant", "audit",
            "chartered accountant", "cfa", "rbi",
        ],
        "Engineering": [
            "mechanical", "civil engineer", "electrical", "electronics",
            "chemical engineer", "automobile", "aerospace", "manufacturing",
            "production", "industrial", "design engineer", "cad",
            "structural", "project engineer", "site engineer",
        ],
        "Healthcare": [
            "doctor", "nurse", "medical", "pharma", "pharmaceutical",
            "hospital", "clinical", "healthcare", "health", "surgeon",
            "physician", "dentist", "lab technician", "radiologist",
            "biotech", "biotechnology", "therapist",
        ],
        "Sales": [
            "sales", "business development", "bde", "account manager",
            "client", "customer success", "inside sales", "field sales",
            "telesales", "retail", "showroom", "bdm",
        ],
        "Marketing": [
            "marketing", "digital marketing", "seo", "sem", "social media",
            "content", "brand", "advertising", "pr", "public relations",
            "growth", "analytics", "copywriter", "creative",
        ],
        "Startup": [
            "startup", "founder", "co-founder", "early stage",
            "venture", "seed", "entrepreneur",
        ],
        "PSU": [
            "psu", "public sector undertaking", "bhel", "ongc",
            "sail", "ntpc", "iocl", "bpcl", "hpcl", "gail",
            "coal india", "power grid", "nhpc",
        ],
        "Part Time": [
            "part time", "part-time", "freelance", "contract",
            "gig", "temporary", "weekend", "hourly",
        ],
        "Education": [
            "teacher", "professor", "faculty", "lecturer", "education",
            "school", "college", "university", "academic", "research",
            "tutor", "principal", "dean", "training",
        ],
        "HR": [
            "hr", "human resource", "recruiter", "recruitment",
            "talent acquisition", "payroll", "people operations",
            "hrbp", "hr business partner", "employee relations",
            "l&d", "learning and development",
        ],
    }

    # ── Scraping / dedup settings ────────────────────────────────────────────
    USER_AGENTS: ClassVar[list[str]] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    ]

    MAX_JOBS_PER_SOURCE: int = 50
    DEDUP_RETENTION_DAYS: int = 7

    # ── Paths ────────────────────────────────────────────────────────────────
    data_dir: Path = field(default_factory=lambda: Path("data"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    docs_dir: Path = field(default_factory=lambda: Path("docs"))

    @property
    def posted_jobs_file(self) -> Path:
        """Path to the posted-jobs.json fingerprint store."""
        return self.data_dir / "posted-jobs.json"

    @property
    def jobs_today_file(self) -> Path:
        """Path to today's scraped jobs JSON."""
        return self.data_dir / "jobs-today.json"

    @property
    def captions_file(self) -> Path:
        """Path to the formatted Instagram captions."""
        return self.output_dir / "captions.txt"

    @property
    def readme_path(self) -> Path:
        """Path to the generated README."""
        return Path("README.md")

    @property
    def html_board_path(self) -> Path:
        """Path to the generated HTML job board."""
        return self.docs_dir / "index.html"

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_FORMAT: ClassVar[str] = (
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    LOG_DATE_FORMAT: ClassVar[str] = "%Y-%m-%d %H:%M:%S"

    # ── Factory ──────────────────────────────────────────────────────────────
    @classmethod
    def get_config(cls, **overrides: Any) -> Config:
        """Create a Config instance, resolving RAPIDAPI_KEY from environment.

        Args:
            **overrides: Any field overrides for the dataclass.

        Returns:
            A fully initialized Config instance.
        """
        cfg = cls(**overrides)
        # Ensure directories exist
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        cfg.output_dir.mkdir(parents=True, exist_ok=True)
        cfg.docs_dir.mkdir(parents=True, exist_ok=True)
        return cfg
