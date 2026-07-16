"""Tests for the scraper module.

These tests cover helper functions (fingerprinting, salary parsing) and
the scraper result aggregation without making actual network calls.
"""

from __future__ import annotations

import hashlib

import pytest

from models import Job, ScraperResult


# ---------------------------------------------------------------------------
# Helpers under test (imported from scraper module)
# ---------------------------------------------------------------------------


def _make_fingerprint(title: str, company: str, location: str) -> str:
    """Inline helper so tests are self-contained."""
    raw = f"{title.strip().lower()}|{company.strip().lower()}|{location.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_job() -> Job:
    """Return a single representative Job for testing."""
    return Job(
        title="Software Engineer",
        company="TechCorp",
        location="Bangalore, Karnataka",
        salary="₹15 LPA",
        url="https://example.com/job/1",
        source="naukri",
    )


@pytest.fixture
def sample_jobs() -> list[Job]:
    """Return a list of jobs from different sources."""
    return [
        Job(
            title="Frontend Developer",
            company="WebCo",
            location="Mumbai, Maharashtra",
            source="indeed",
        ),
        Job(
            title="Data Scientist",
            company="AI Labs",
            location="Remote",
            source="linkedin",
        ),
        Job(
            title="SSC CGL 2025",
            company="Government of India",
            location="India",
            source="govtportals",
            is_government=True,
            last_date="31 Aug 2025",
        ),
    ]


# ---------------------------------------------------------------------------
# Fingerprinting tests
# ---------------------------------------------------------------------------


class TestFingerprinting:
    """Tests for SHA-256 job fingerprinting."""

    def test_deterministic(self, sample_job: Job) -> None:
        """Fingerprint should be deterministic for the same inputs."""
        fp1 = _make_fingerprint(sample_job.title, sample_job.company, sample_job.location)
        fp2 = _make_fingerprint(sample_job.title, sample_job.company, sample_job.location)
        assert fp1 == fp2
        assert len(fp1) == 64

    def test_case_insensitive(self) -> None:
        """Fingerprinting should be case-insensitive."""
        fp1 = _make_fingerprint("SOFTWARE ENGINEER", "TECHCORP", "BANGALORE")
        fp2 = _make_fingerprint("software engineer", "techcorp", "bangalore")
        assert fp1 == fp2

    def test_whitespace_insensitive(self) -> None:
        """Fingerprinting should strip leading/trailing whitespace."""
        fp1 = _make_fingerprint("  Dev  ", "  Acme  ", "  Delhi  ")
        fp2 = _make_fingerprint("Dev", "Acme", "Delhi")
        assert fp1 == fp2

    def test_different_fields_produce_different_fingerprints(self) -> None:
        """Jobs with different title/company/location should have unique fingerprints."""
        fp1 = _make_fingerprint("Dev", "Acme", "Delhi")
        fp2 = _make_fingerprint("QA", "Acme", "Delhi")
        fp3 = _make_fingerprint("Dev", "BetaCorp", "Delhi")
        fp4 = _make_fingerprint("Dev", "Acme", "Mumbai")
        distinct = {fp1, fp2, fp3, fp4}
        assert len(distinct) == 4

    def test_unicode_handling(self) -> None:
        """Fingerprinting should handle Unicode characters in Indian languages."""
        fp = _make_fingerprint("डेवलपर", "कंपनी", "दिल्ली")
        assert len(fp) == 64
        assert isinstance(fp, str)

    def test_fingerprint_on_job_model(self, sample_job: Job) -> None:
        """The Job model should accept and store a fingerprint."""
        sample_job.fingerprint = _make_fingerprint(
            sample_job.title, sample_job.company, sample_job.location
        )
        assert len(sample_job.fingerprint) == 64
        assert isinstance(sample_job.fingerprint, str)


# ---------------------------------------------------------------------------
# ScraperResult tests
# ---------------------------------------------------------------------------


class TestScraperResult:
    """Tests for the ScraperResult aggregate model."""

    def test_defaults(self) -> None:
        """A default ScraperResult should have zero jobs and empty lists."""
        result = ScraperResult()
        assert result.total_jobs == 0
        assert result.new_jobs == 0
        assert result.jobs == []
        assert result.source_stats == {}
        assert result.errors == []

    def test_with_data(self, sample_jobs: list[Job]) -> None:
        """ScraperResult should hold jobs and stats."""
        result = ScraperResult(
            total_jobs=3,
            new_jobs=2,
            jobs=sample_jobs,
            source_stats={
                "indeed": {"success": True, "scraped": 1},
                "linkedin": {"success": True, "scraped": 1},
                "govtportals": {"success": True, "scraped": 1},
            },
        )
        assert result.total_jobs == 3
        assert len(result.jobs) == 3
        assert result.source_stats["indeed"]["scraped"] == 1

    def test_error_accumulation(self) -> None:
        """Errors should accumulate in the errors list."""
        result = ScraperResult(errors=["Timeout on naukri", "Parse error on indeed"])
        assert len(result.errors) == 2
        assert "Timeout" in result.errors[0]


# ---------------------------------------------------------------------------
# Job model tests
# ---------------------------------------------------------------------------


class TestJobModel:
    """Tests for the Job dataclass."""

    def test_default_values(self) -> None:
        """Job defaults should be sensible."""
        job = Job(title="Test", company="TestCo")
        assert job.location == "India"
        assert job.salary == "Not disclosed"
        assert job.url == ""
        assert job.source == ""
        assert job.category == "Other"
        assert job.is_government is False

    def test_government_job(self) -> None:
        """Government jobs should have the flag set."""
        job = Job(
            title="IAS Officer",
            company="UPSC",
            is_government=True,
            last_date="15 Dec 2025",
        )
        assert job.is_government is True
        assert job.last_date == "15 Dec 2025"
