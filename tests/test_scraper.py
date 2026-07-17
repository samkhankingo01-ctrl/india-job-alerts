"""Tests for models and scraper helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import CaptionBlock, Job, ScraperResult


class TestJobModel:
    """Tests for the Job dataclass."""

    def test_default_construction(self) -> None:
        """Job should have sensible defaults for all fields."""
        j = Job()
        assert j.title == ""
        assert j.company == ""
        assert j.source == ""
        assert j.category == ""
        assert j.is_government is False
        assert j.is_remote is False
        assert j.fingerprint == ""

    def test_full_construction(self) -> None:
        """Job should accept all field values."""
        j = Job(
            title="Software Engineer",
            company="Google",
            company_logo="https://logo.com/g.png",
            city="Bangalore",
            state="Karnataka",
            area="India",
            salary="15 LPA",
            url="https://apply.com/1",
            source="jsearch",
            category="IT",
            posted_date="2025-07-01",
            posted_date_raw="2025-07-01T10:00:00Z",
            last_date="2025-08-01",
            description="Great job",
            employment_type="FULLTIME",
            is_government=False,
            is_remote=True,
            fingerprint="abc123",
            job_id="j_001",
        )
        assert j.title == "Software Engineer"
        assert j.company == "Google"
        assert j.salary == "15 LPA"
        assert j.category == "IT"
        assert j.is_remote is True
        assert j.fingerprint == "abc123"

    def test_from_dict(self) -> None:
        """from_dict should parse a complete dict correctly."""
        data = {
            "title": "Data Scientist",
            "company": "Meta",
            "city": "Mumbai",
            "state": "Maharashtra",
            "salary": "20 LPA",
            "url": "https://apply.com/2",
            "source": "arbeitnow",
            "category": "IT",
            "is_remote": True,
            "is_government": False,
            "fingerprint": "fp_xyz",
            "job_id": "j_002",
            "company_logo": "",
            "area": "",
            "posted_date": "",
            "posted_date_raw": "",
            "last_date": "",
            "description": "",
            "employment_type": "",
        }
        j = Job.from_dict(data)
        assert j.title == "Data Scientist"
        assert j.company == "Meta"
        assert j.city == "Mumbai"
        assert j.category == "IT"
        assert j.is_remote is True

    def test_from_dict_missing_fields(self) -> None:
        """from_dict should handle missing keys gracefully."""
        j = Job.from_dict({"title": "X", "company": "Y"})
        assert j.title == "X"
        assert j.company == "Y"
        assert j.city == ""
        assert j.url == ""

    def test_from_dict_none_values(self) -> None:
        """from_dict should convert None values to empty strings."""
        j = Job.from_dict({"title": None, "company": None, "salary": None})
        assert j.title == ""
        assert j.company == ""
        assert j.salary == ""

    def test_to_dict_roundtrip(self) -> None:
        """to_dict → from_dict should be lossless for known fields."""
        j1 = Job(
            title="SWE",
            company="Comp",
            city="Delhi",
            salary="10 LPA",
            url="https://x.com",
            source="remotive",
            category="IT",
            is_remote=True,
            fingerprint="hash1",
            job_id="j_003",
        )
        j2 = Job.from_dict(j1.to_dict())
        for field in [
            "title", "company", "city", "salary", "url", "source",
            "category", "is_remote", "fingerprint", "job_id",
        ]:
            assert getattr(j2, field) == getattr(j1, field), f"Field {field} mismatch"

    def test_to_dict_keys(self) -> None:
        """to_dict should include all expected keys."""
        j = Job()
        d = j.to_dict()
        expected_keys = {
            "title", "company", "company_logo", "city", "state", "area",
            "salary", "url", "source", "category", "posted_date",
            "posted_date_raw", "last_date", "description", "employment_type",
            "is_government", "is_remote", "fingerprint", "job_id",
        }
        assert set(d.keys()) == expected_keys


class TestScraperResult:
    """Tests for the ScraperResult dataclass."""

    def test_defaults(self) -> None:
        sr = ScraperResult()
        assert sr.total_jobs == 0
        assert sr.new_jobs == 0
        assert sr.jobs == []
        assert sr.errors == []
        assert sr.elapsed_seconds == 0.0

    def test_from_dict(self) -> None:
        data = {
            "total_jobs": 10,
            "new_jobs": 5,
            "jobs": [{"title": "A", "company": "B"}],
            "source_stats": {"jsearch": 10},
            "errors": ["err1"],
            "elapsed_seconds": 2.5,
        }
        sr = ScraperResult.from_dict(data)
        assert sr.total_jobs == 10
        assert sr.new_jobs == 5
        assert len(sr.jobs) == 1
        assert sr.jobs[0].title == "A"
        assert sr.source_stats == {"jsearch": 10}
        assert sr.errors == ["err1"]
        assert sr.elapsed_seconds == 2.5

    def test_to_dict(self) -> None:
        sr = ScraperResult(
            total_jobs=3,
            new_jobs=2,
            jobs=[Job(title="T", company="C")],
            errors=["e"],
        )
        d = sr.to_dict()
        assert d["total_jobs"] == 3
        assert d["new_jobs"] == 2
        assert len(d["jobs"]) == 1


class TestCaptionBlock:
    """Tests for the CaptionBlock dataclass."""

    def test_defaults(self) -> None:
        cb = CaptionBlock()
        assert cb.text == ""
        assert cb.hashtags == []
        assert cb.is_government is False

    def test_from_dict(self) -> None:
        data = {
            "text": "Hello",
            "job_title": "SWE",
            "job_company": "Corp",
            "is_government": True,
            "hashtags": ["jobs", "india"],
        }
        cb = CaptionBlock.from_dict(data)
        assert cb.text == "Hello"
        assert cb.job_title == "SWE"
        assert cb.is_government is True
        assert cb.hashtags == ["jobs", "india"]

    def test_to_dict_roundtrip(self) -> None:
        cb1 = CaptionBlock(
            text="Test caption",
            job_title="Manager",
            job_company="ACME",
            is_government=False,
            hashtags=["hiring", "mba"],
        )
        cb2 = CaptionBlock.from_dict(cb1.to_dict())
        assert cb2.text == cb1.text
        assert cb2.job_title == cb1.job_title
        assert cb2.hashtags == cb1.hashtags
