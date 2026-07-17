"""Data models for the India Jobs Board scraper pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    """Represents a single job listing from any source."""

    title: str = ""
    company: str = ""
    company_logo: str = ""
    city: str = ""
    state: str = ""
    area: str = ""
    salary: str = ""
    url: str = ""
    source: str = ""
    category: str = ""
    posted_date: str = ""
    posted_date_raw: str = ""
    last_date: str = ""
    description: str = ""
    employment_type: str = ""
    is_government: bool = False
    is_remote: bool = False
    fingerprint: str = ""
    job_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        """Construct a Job from a dictionary.

        Args:
            data: Dictionary with job fields.

        Returns:
            A new Job instance.
        """
        return cls(
            title=str(data.get("title", "") or ""),
            company=str(data.get("company", "") or ""),
            company_logo=str(data.get("company_logo", "") or ""),
            city=str(data.get("city", "") or ""),
            state=str(data.get("state", "") or ""),
            area=str(data.get("area", "") or ""),
            salary=str(data.get("salary", "") or ""),
            url=str(data.get("url", "") or ""),
            source=str(data.get("source", "") or ""),
            category=str(data.get("category", "") or ""),
            posted_date=str(data.get("posted_date", "") or ""),
            posted_date_raw=str(data.get("posted_date_raw", "") or ""),
            last_date=str(data.get("last_date", "") or ""),
            description=str(data.get("description", "") or ""),
            employment_type=str(data.get("employment_type", "") or ""),
            is_government=bool(data.get("is_government", False)),
            is_remote=bool(data.get("is_remote", False)),
            fingerprint=str(data.get("fingerprint", "") or ""),
            job_id=str(data.get("job_id", "") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this Job to a plain dictionary.

        Returns:
            Dictionary representation of the job.
        """
        return {
            "title": self.title,
            "company": self.company,
            "company_logo": self.company_logo,
            "city": self.city,
            "state": self.state,
            "area": self.area,
            "salary": self.salary,
            "url": self.url,
            "source": self.source,
            "category": self.category,
            "posted_date": self.posted_date,
            "posted_date_raw": self.posted_date_raw,
            "last_date": self.last_date,
            "description": self.description,
            "employment_type": self.employment_type,
            "is_government": self.is_government,
            "is_remote": self.is_remote,
            "fingerprint": self.fingerprint,
            "job_id": self.job_id,
        }


@dataclass
class ScraperResult:
    """Aggregate result from one or more scrapers."""

    total_jobs: int = 0
    new_jobs: int = 0
    jobs: list[Job] = field(default_factory=list)
    source_stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScraperResult:
        """Construct a ScraperResult from a dictionary.

        Args:
            data: Dictionary with scraper result fields.

        Returns:
            A new ScraperResult instance.
        """
        return cls(
            total_jobs=int(data.get("total_jobs", 0)),
            new_jobs=int(data.get("new_jobs", 0)),
            jobs=[Job.from_dict(j) for j in data.get("jobs", [])],
            source_stats={
                str(k): int(v) for k, v in data.get("source_stats", {}).items()
            },
            errors=[str(e) for e in data.get("errors", [])],
            elapsed_seconds=float(data.get("elapsed_seconds", 0.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this ScraperResult to a plain dictionary.

        Returns:
            Dictionary representation of the scraper result.
        """
        return {
            "total_jobs": self.total_jobs,
            "new_jobs": self.new_jobs,
            "jobs": [j.to_dict() for j in self.jobs],
            "source_stats": self.source_stats,
            "errors": self.errors,
            "elapsed_seconds": self.elapsed_seconds,
        }


@dataclass
class CaptionBlock:
    """Represents a formatted Instagram caption for a single job."""

    text: str = ""
    job_title: str = ""
    job_company: str = ""
    is_government: bool = False
    hashtags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CaptionBlock:
        """Construct a CaptionBlock from a dictionary.

        Args:
            data: Dictionary with caption fields.

        Returns:
            A new CaptionBlock instance.
        """
        return cls(
            text=str(data.get("text", "") or ""),
            job_title=str(data.get("job_title", "") or ""),
            job_company=str(data.get("job_company", "") or ""),
            is_government=bool(data.get("is_government", False)),
            hashtags=[str(h) for h in data.get("hashtags", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this CaptionBlock to a plain dictionary.

        Returns:
            Dictionary representation of the caption block.
        """
        return {
            "text": self.text,
            "job_title": self.job_title,
            "job_company": self.job_company,
            "is_government": self.is_government,
            "hashtags": self.hashtags,
        }
