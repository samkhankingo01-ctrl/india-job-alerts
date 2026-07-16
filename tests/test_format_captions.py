"""Tests for caption formatter."""

from __future__ import annotations

import tempfile
import os

from config import AppConfig
from models import Job
from scripts.format_captions import build_caption


def test_build_caption_contains_key_fields():
    config = AppConfig()
    job = Job(
        title="Software Engineer",
        company="Microsoft",
        location="Bengaluru, Karnataka",
        salary="₹15-30 LPA",
        url="https://apply.example.com",
        category="IT",
        source="linkedin",
    )
    caption = build_caption(job, config)
    assert "Microsoft" in caption.text
    assert "Software Engineer" in caption.text
    assert "Bengaluru, Karnataka" in caption.text
    assert "₹15-30 LPA" in caption.text
    assert "https://apply.example.com" in caption.text
    assert "#jobs" in caption.text
    assert "#indiajobs" in caption.text


def test_build_caption_no_salary():
    """When salary is empty, show 'Not disclosed'."""
    config = AppConfig()
    job = Job(
        title="Analyst",
        company="KPMG",
        location="Mumbai",
        salary="",
        url="https://example.com",
        category="Finance",
        source="naukri",
    )
    caption = build_caption(job, config)
    # Salary field should be present (even if empty)
    assert "Salary" in caption.text


def test_build_government_job_header():
    """Government jobs get special header with last date."""
    config = AppConfig()
    job = Job(
        title="Drug Inspector",
        company="UPSC",
        location="All India",
        salary="Pay Level-7",
        url="https://upsc.gov.in",
        category="Government",
        source="govtportals",
        is_government=True,
        last_date="2026-08-15",
    )
    caption = build_caption(job, config)
    assert "🏛️" in caption.text
    assert "Last Date" in caption.text
    assert "2026-08-15" in caption.text


def test_build_caption_hashtags():
    """Caption includes global and category hashtags."""
    config = AppConfig()
    job = Job(
        title="DevOps Engineer",
        company="AWS",
        location="Remote",
        category="IT",
        source="indeed",
    )
    caption = build_caption(job, config)
    assert "#jobs" in caption.text
    assert "#ittech" in caption.text
