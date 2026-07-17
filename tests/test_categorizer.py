"""Tests for the categorizer module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from models import Job
from scripts.categorizer import categorize, categorize_all


class TestCategorize:
    """Tests for the categorize function."""

    def test_categorize_it_by_python_keyword(self) -> None:
        """A job with 'python' in the title should be IT."""
        job = Job(title="Python Developer", description="Backend role")
        result = categorize(job, Config.CATEGORY_MAP)
        assert result == "IT"

    def test_categorize_it_by_software_keyword(self) -> None:
        """'Software' should match IT."""
        job = Job(title="Software Engineer", description="")
        assert categorize(job, Config.CATEGORY_MAP) == "IT"

    def test_categorize_government(self) -> None:
        """'government' keyword should match Government."""
        job = Job(title="Government Clerk", description="Sarkari job")
        assert categorize(job, Config.CATEGORY_MAP) == "Government"

    def test_categorize_freshers(self) -> None:
        """'fresher' should match Freshers."""
        job = Job(title="Fresher Hiring", description="Entry level")
        assert categorize(job, Config.CATEGORY_MAP) == "Freshers"

    def test_categorize_internship(self) -> None:
        """'internship' should match Freshers."""
        job = Job(title="Graduate Internship", description="")
        assert categorize(job, Config.CATEGORY_MAP) == "Freshers"

    def test_categorize_remote_explicit(self) -> None:
        """'work from home' should match Remote."""
        job = Job(title="Consultant", description="Work from home opportunity")
        assert categorize(job, Config.CATEGORY_MAP) == "Remote"

    def test_categorize_banking(self) -> None:
        """'banking' in description should match Banking."""
        job = Job(title="Officer", description="Banking sector job")
        assert categorize(job, Config.CATEGORY_MAP) == "Banking"

    def test_categorize_engineering(self) -> None:
        """'mechanical' should match Engineering."""
        job = Job(title="Mechanical Designer", description="")
        assert categorize(job, Config.CATEGORY_MAP) == "Engineering"

    def test_categorize_healthcare(self) -> None:
        """'doctor' should match Healthcare."""
        job = Job(title="Doctor", description="Medical professional")
        assert categorize(job, Config.CATEGORY_MAP) == "Healthcare"

    def test_categorize_sales(self) -> None:
        """'sales' should match Sales."""
        job = Job(title="Sales Executive", description="")
        assert categorize(job, Config.CATEGORY_MAP) == "Sales"

    def test_categorize_marketing(self) -> None:
        """'digital marketing' should match Marketing."""
        job = Job(title="Digital Marketing Manager", description="SEO and SEM")
        assert categorize(job, Config.CATEGORY_MAP) == "Marketing"

    def test_categorize_startup(self) -> None:
        """'startup' should match Startup."""
        job = Job(title="Operations Lead", description="Exciting startup opportunity")
        assert categorize(job, Config.CATEGORY_MAP) == "Startup"

    def test_categorize_psu(self) -> None:
        """'BHEL' should match PSU."""
        job = Job(title="Officer Post", description="BHEL recruitment notice")
        assert categorize(job, Config.CATEGORY_MAP) == "PSU"

    def test_categorize_part_time(self) -> None:
        """'part time' should match Part Time."""
        job = Job(title="Tutor", description="Part time tutoring job")
        assert categorize(job, Config.CATEGORY_MAP) == "Part Time"

    def test_categorize_education(self) -> None:
        """'teacher' should match Education."""
        job = Job(title="Math Teacher", description="School teaching position")
        assert categorize(job, Config.CATEGORY_MAP) == "Education"

    def test_categorize_hr(self) -> None:
        """'recruiter' should match HR."""
        job = Job(title="Technical Recruiter", description="Hiring for IT")
        assert categorize(job, Config.CATEGORY_MAP) == "HR"

    def test_categorize_other_fallback(self) -> None:
        """A job with no matching keywords should be Other."""
        job = Job(title="Mystery Role", description="We do stuff")
        assert categorize(job, Config.CATEGORY_MAP) == "Other"

    def test_categorize_description_match(self) -> None:
        """Keywords in description only should still match."""
        job = Job(title="Associate", description="Looking for a developer")
        assert categorize(job, Config.CATEGORY_MAP) == "IT"

    def test_first_match_wins(self) -> None:
        """When multiple categories match, the first one in the map should win."""
        # 'developer' matches IT, 'remote' matches Remote; IT comes first
        job = Job(title="Remote Developer", description="Work from home")
        result = categorize(job, Config.CATEGORY_MAP)
        assert result == "IT"


class TestCategorizeAll:
    """Tests for categorize_all."""

    def test_mutates_in_place(self) -> None:
        """All jobs should have their category field populated."""
        jobs = [
            Job(title="Python Dev"),
            Job(title="Government Officer"),
            Job(title="Mystery Role"),
        ]
        result = categorize_all(jobs)
        assert result is jobs  # same list
        assert jobs[0].category == "IT"
        assert jobs[1].category == "Government"
        assert jobs[2].category == "Other"

    def test_does_not_overwrite_existing(self) -> None:
        """Jobs with an existing category should keep it."""
        jobs = [
            Job(title="Python Dev", category="AlreadySet"),
        ]
        categorize_all(jobs)
        assert jobs[0].category == "AlreadySet"

    def test_empty_list(self) -> None:
        """Empty job list should be handled."""
        result = categorize_all([])
        assert result == []

    def test_sets_category_on_all(self) -> None:
        """All empty-category jobs should get a category."""
        jobs = [Job(title=f"Job {i}") for i in range(5)]
        categorize_all(jobs)
        for job in jobs:
            assert job.category != ""
