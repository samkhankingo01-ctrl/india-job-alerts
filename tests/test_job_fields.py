"""Integration test: verify generated jobs-today.json contains all required fields
and that Apply links point to the ORIGINAL job page.

This is the contract test for the core requirement:
  - Every job has State / City / Area (area may be empty, that's allowed)
  - Every job has location_raw (original posting location, never just "India")
  - Every job has url (Apply always opens the original page)
  - No job has a non-Indian location
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scripts.location_parser import is_india_location  # noqa: E402

# Required keys every job object must carry
REQUIRED_KEYS = {
    "title",
    "company",
    "company_logo",
    "city",
    "state",
    "area",
    "location_raw",
    "salary",
    "url",
    "source",
    "category",
    "posted_date",
}


def _load_jobs():
    repo = Path(__file__).resolve().parents[1]
    jobs_file = repo / "data" / "jobs-today.json"
    if not jobs_file.exists():
        return None, jobs_file
    with open(jobs_file, encoding="utf-8") as fh:
        return json.load(fh), jobs_file


def test_jobs_file_has_required_keys():
    """If a jobs-today.json exists, every job must carry all required fields."""
    jobs, jobs_file = _load_jobs()
    if jobs is None:
        import pytest

        pytest.skip(f"{jobs_file} not present – run pipeline first")
    assert isinstance(jobs, list) and len(jobs) > 0, "jobs-today.json is empty"
    for i, job in enumerate(jobs):
        missing = REQUIRED_KEYS - set(job.keys())
        assert not missing, f"job #{i} missing keys: {missing}"


def test_no_location_replaced_with_just_india():
    """location_raw must never be the bare string 'India'."""
    jobs, _ = _load_jobs()
    if jobs is None:
        import pytest

        pytest.skip("jobs-today.json not present")
    for i, job in enumerate(jobs):
        raw = (job.get("location_raw") or "").strip().lower()
        assert raw != "india", f"job #{i} location_raw is bare 'India'"


def test_all_jobs_are_indian():
    """Hard guarantee: every job's parsed location must be Indian."""
    jobs, _ = _load_jobs()
    if jobs is None:
        import pytest

        pytest.skip("jobs-today.json not present")
    for i, job in enumerate(jobs):
        combined = ", ".join(
            p for p in (job.get("area"), job.get("city"), job.get("state")) if p
        )
        assert is_india_location(combined), (
            f"job #{i} is not an Indian location: {combined!r}"
        )


def test_apply_url_present_and_original():
    """Apply button must always open the ORIGINAL job page (a real http url)."""
    jobs, _ = _load_jobs()
    if jobs is None:
        import pytest

        pytest.skip("jobs-today.json not present")
    for i, job in enumerate(jobs):
        url = (job.get("url") or "").strip()
        assert url, f"job #{i} has no url"
        assert url.startswith("http"), f"job #{i} url is not absolute: {url!r}"
