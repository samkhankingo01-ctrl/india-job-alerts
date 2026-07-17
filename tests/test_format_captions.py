"""Tests for the caption formatter module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import CaptionBlock, Job
from scripts.format_captions import format_all_captions, format_caption


class TestFormatCaption:
    """Tests for the format_caption function."""

    def test_returns_caption_block(self) -> None:
        """Should return a CaptionBlock instance."""
        job = Job(title="SWE", company="Google", city="Bangalore")
        cb = format_caption(job)
        assert isinstance(cb, CaptionBlock)

    def test_includes_basic_info(self) -> None:
        """Caption should contain title, company, and location."""
        job = Job(
            title="Software Engineer",
            company="Acme Corp",
            city="Mumbai",
            state="Maharashtra",
            url="https://apply.example.com/1",
        )
        cb = format_caption(job)
        assert "Software Engineer" in cb.text
        assert "Acme Corp" in cb.text
        assert "Mumbai" in cb.text
        assert "Maharashtra" in cb.text
        assert "https://apply.example.com/1" in cb.text

    def test_salary_not_disclosed_default(self) -> None:
        """When salary is empty, 'Not Disclosed' should be shown."""
        job = Job(title="Role", company="Co", salary="")
        cb = format_caption(job)
        assert "Not Disclosed" in cb.text

    def test_salary_shown_when_present(self) -> None:
        """When salary is set, it should appear in the caption."""
        job = Job(title="Role", company="Co", salary="12 LPA")
        cb = format_caption(job)
        assert "12 LPA" in cb.text

    def test_location_no_state(self) -> None:
        """Location should show city only when state is empty."""
        job = Job(title="R", company="C", city="Delhi", state="")
        cb = format_caption(job)
        assert "Delhi" in cb.text

    def test_location_no_city(self) -> None:
        """Location should show 'Anywhere' when city is empty."""
        job = Job(title="R", company="C", city="", state="")
        cb = format_caption(job)
        assert "Anywhere" in cb.text

    def test_hashtags_include_base(self) -> None:
        """Base hashtags should always be included."""
        job = Job(title="R", company="C")
        cb = format_caption(job)
        assert "#jobs" in cb.text
        assert "#indiajobs" in cb.text
        assert "#hiring" in cb.text
        assert "#jobsearch" in cb.text
        assert "#careergoals" in cb.text
        assert "#jobseekers" in cb.text
        assert "#india" in cb.text

    def test_category_hashtag_added(self) -> None:
        """Category should be added as a hashtag when not 'Other'."""
        job = Job(title="Python Developer", company="C", category="IT")
        cb = format_caption(job)
        assert "#it" in cb.text

    def test_other_category_no_hashtag(self) -> None:
        """'Other' category should not add a hashtag."""
        job = Job(title="R", company="C", category="Other")
        cb = format_caption(job)
        # Only base hashtags, no 'other' tag
        hashtag_count = cb.text.count("---")
        assert hashtag_count == 1

    def test_is_government_flag(self) -> None:
        """is_government should be passed through."""
        job = Job(title="R", company="C", is_government=True)
        cb = format_caption(job)
        assert cb.is_government is True

    def test_job_title_and_company_on_block(self) -> None:
        """CaptionBlock metadata should match the job."""
        job = Job(title="Data Scientist", company="Meta")
        cb = format_caption(job)
        assert cb.job_title == "Data Scientist"
        assert cb.job_company == "Meta"

    def test_startswith_hiring_banner(self) -> None:
        """Caption should start with the hiring banner."""
        job = Job(title="R", company="C")
        cb = format_caption(job)
        assert cb.text.startswith("🚨 Hiring Now!")

    def test_ends_with_separator(self) -> None:
        """Caption should end with '---' separator."""
        job = Job(title="R", company="C")
        cb = format_caption(job)
        assert cb.text.rstrip().endswith("---")


class TestFormatAllCaptions:
    """Tests for the format_all_captions function."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """Should create the captions file with content."""
        jobs = [
            Job(title="SWE", company="A", city="Delhi"),
            Job(title="PM", company="B", city="Mumbai"),
        ]
        output = tmp_path / "captions.txt"
        format_all_captions(jobs, output)
        assert output.exists()

        content = output.read_text(encoding="utf-8")
        assert "SWE" in content
        assert "PM" in content
        assert "---" in content

    def test_empty_jobs_creates_empty_file(self, tmp_path: Path) -> None:
        """Empty job list should create an empty file."""
        output = tmp_path / "captions.txt"
        format_all_captions([], output)
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert content == ""

    def test_single_job_no_triple_separator(self, tmp_path: Path) -> None:
        """Single job should not have triple newline separator."""
        jobs = [Job(title="SWE", company="A")]
        output = tmp_path / "captions.txt"
        format_all_captions(jobs, output)
        content = output.read_text(encoding="utf-8")
        # Should contain only one caption block
        assert content.count("🚨 Hiring Now!") == 1
