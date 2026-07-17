"""Tests for scraper module."""

from __future__ import annotations

from models import Job
from scripts.scraper import _make_fingerprint, _parse_salary_text, _is_valid_job_url


class TestFingerprinting:
    """Tests for the SHA-256 fingerprint generator."""

    def test_deterministic(self):
        fp1 = _make_fingerprint("SWE", "MS", "BLR")
        fp2 = _make_fingerprint("SWE", "MS", "BLR")
        assert fp1 == fp2

    def test_case_insensitive(self):
        fp1 = _make_fingerprint("Software Engineer", "Microsoft", "Bangalore")
        fp2 = _make_fingerprint("software engineer", "MICROSOFT", "bangalore")
        assert fp1 == fp2

    def test_whitespace_insensitive(self):
        fp1 = _make_fingerprint("  SWE  ", "MS", "  BLR  ")
        fp2 = _make_fingerprint("SWE", "MS", "BLR")
        assert fp1 == fp2

    def test_different_fields_produce_different_fingerprints(self):
        fp1 = _make_fingerprint("SWE", "MS", "BLR")
        fp2 = _make_fingerprint("SWE", "MS", "DEL")
        assert fp1 != fp2

    def test_unicode_handling(self):
        fp = _make_fingerprint("D\u00e9veloppeur", "Caf\u00e9", "M\u00e9xico")
        assert len(fp) == 64  # SHA-256 hex digest length

    def test_fingerprint_on_job_model(self):
        job = Job(title="Dev", company="Co", location="City")
        job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
        assert len(job.fingerprint) == 64


class TestSalaryParsing:
    """Tests for salary text normalizer."""

    def test_none_returns_not_disclosed(self):
        assert _parse_salary_text(None) == "Not disclosed"

    def test_empty_returns_not_disclosed(self):
        assert _parse_salary_text("") == "Not disclosed"

    def test_whitespace_only_returns_not_disclosed(self):
        assert _parse_salary_text("   ") == "Not disclosed"

    def test_normal_salary(self):
        assert _parse_salary_text("10-15 LPA") == "10-15 LPA"

    def test_salary_with_newlines(self):
        result = _parse_salary_text("5-7\nLPA")
        assert "\n" not in result


class TestValidJobUrl:
    """Tests for URL validation."""

    def test_naukri_url(self):
        assert _is_valid_job_url("https://www.naukri.com/job-listings-123") is True

    def test_linkedin_url(self):
        assert _is_valid_job_url("https://www.linkedin.com/jobs/view/123") is True

    def test_indeed_url(self):
        assert _is_valid_job_url("https://in.indeed.com/viewjob?jk=abc") is True

    def test_short_url(self):
        assert _is_valid_job_url("https://a.co") is False

    def test_empty_url(self):
        assert _is_valid_job_url("") is False

    def test_google_url(self):
        assert _is_valid_job_url("https://www.google.com/search?q=jobs") is False


class TestJobModel:
    """Tests for the Job data model."""

    def test_default_values(self):
        job = Job(title="SWE", company="MS", location="BLR")
        assert job.salary == "Not disclosed"
        assert job.source == ""
        assert job.category == "Other"
        assert job.is_government is False
        assert job.fingerprint == ""

    def test_government_job(self):
        job = Job(title="Clerk", company="SSC", location="India",
                  is_government=True, last_date="2026-08-15")
        assert job.is_government is True
        assert job.last_date == "2026-08-15"
