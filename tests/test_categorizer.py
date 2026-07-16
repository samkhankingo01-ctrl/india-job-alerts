"""Tests for job categorizer."""

from __future__ import annotations

from models import Job
from scripts.categorizer import categorize_jobs


def test_categorize_it_job():
    job = Job(title="Software Engineer", company="Microsoft", location="Bangalore")
    categorize_jobs([job])
    assert job.category == "IT"


def test_categorize_fresher_job():
    job = Job(title="Fresher Software Developer", company="TCS", location="Chennai")
    categorize_jobs([job])
    assert job.category in ("IT", "Freshers")


def test_categorize_banking_job():
    job = Job(title="Relationship Manager", company="HDFC Bank", location="Mumbai", description="banking")
    categorize_jobs([job])
    assert job.category in ("Banking", "Sales")


def test_categorize_engineering_job():
    job = Job(title="Mechanical Engineer", company="L&T", location="Pune", description="mechanical engineering manufacturing cad")
    categorize_jobs([job])
    assert job.category == "Engineering"


def test_categorize_healthcare_job():
    job = Job(title="Staff Nurse", company="Apollo Hospitals", location="Chennai", description="healthcare medical hospital")
    categorize_jobs([job])
    assert job.category == "Healthcare"


def test_categorize_falls_back_to_other():
    """Jobs with no matching keywords fall back to 'Other'."""
    job = Job(title="Mystery Role X99ZZ", company="UnknownCorp", location="Nowhere", description="")
    categorize_jobs([job])
    assert job.category == "Other"


def test_categorize_empty_title():
    """Edge case: empty title still returns a category."""
    job = Job(title="", company="Acme Corp", location="Delhi")
    categorize_jobs([job])
    assert isinstance(job.category, str)
    assert len(job.category) > 0


def test_categorize_bulk_jobs():
    """All jobs in a list get categorized."""
    jobs = [
        Job(title="Software Engineer", company="MS", location="BLR"),
        Job(title="Doctor", company="AIIMS", location="Delhi", description="healthcare"),
        Job(title="Bank PO", company="SBI", location="Mumbai", description="banking"),
    ]
    categorize_jobs(jobs)
    categories = {job.category for job in jobs}
    assert "Other" not in categories or len(categories) >= 2
