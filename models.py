"""Data models for India Job Alerts.

Defines the core data structures used throughout the project:
Job, ScraperResult, and CaptionBlock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Job:
    """Represents a single job posting from any source.

    Attributes:
        title: Job title / role name.
        company: Hiring organization name.
        location: City, state, or remote indicator.
        salary: Display string for compensation, e.g. "₹5 LPA" or "Not disclosed".
        url: Direct link to the job posting / application page.
        source: Name of the scraper source (naukri, indeed, etc.).
        category: Assigned category after classification.
        posted_date: ISO-format date string when the job was posted.
        last_date: For government jobs, the application deadline.
        description: Short snippet or first few lines of the description.
        is_government: Derived flag set by categorizer.
        fingerprint: SHA-256 hex digest for deduplication.
    """

    title: str
    company: str
    location: str = "India"
    salary: str = "Not disclosed"
    url: str = ""
    source: str = ""
    category: str = "Other"
    posted_date: str = ""
    last_date: str = ""
    description: str = ""
    is_government: bool = False
    fingerprint: str = ""


@dataclass
class ScraperResult:
    """Aggregate result of a scraping run across all sources.

    Attributes:
        total_jobs: Total number of Job objects returned.
        new_jobs: Count of jobs that passed deduplication.
        jobs: The list of (new) Job objects.
        source_stats: Per-source dict with keys 'success', 'failure', 'scraped'.
        errors: List of error messages encountered.
        elapsed_seconds: Wall-clock time for the scraping phase.
    """

    total_jobs: int = 0
    new_jobs: int = 0
    jobs: List[Job] = field(default_factory=list)
    source_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


@dataclass
class CaptionBlock:
    """A single Instagram-ready caption for one job.

    Attributes:
        text: Full caption text including header, fields, and hashtags.
        job_title: The underlying Job title for metadata.
        job_company: The underlying Job company.
        is_government: Whether the special government header was applied.
        hashtags: List of hashtags included.
    """

    text: str
    job_title: str
    job_company: str
    is_government: bool = False
    hashtags: List[str] = field(default_factory=list)
