"""Tests for deduplication engine."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from models import Job
from scripts.dedup import _generate_fingerprint, deduplicate_jobs, load_posted_jobs, save_posted_jobs


def test_generate_fingerprint_identical():
    """Same job fields produce identical fingerprints."""
    job1 = Job(title="Software Engineer", company="Microsoft", location="Bangalore")
    job2 = Job(title="Software Engineer", company="Microsoft", location="Bangalore")
    assert _generate_fingerprint(job1) == _generate_fingerprint(job2)


def test_generate_fingerprint_different():
    """Different fields produce different fingerprints."""
    job1 = Job(title="Software Engineer", company="Microsoft", location="Bangalore")
    job2 = Job(title="Software Engineer", company="Microsoft", location="Hyderabad")
    assert _generate_fingerprint(job1) != _generate_fingerprint(job2)


def test_generate_fingerprint_case_insensitive():
    """Fingerprint is case-insensitive."""
    job1 = Job(title="SOFTWARE ENGINEER", company="MICROSOFT", location="BANGALORE")
    job2 = Job(title="software engineer", company="microsoft", location="bangalore")
    assert _generate_fingerprint(job1) == _generate_fingerprint(job2)


def test_generate_fingerprint_whitespace_insensitive():
    """Fingerprint ignores leading/trailing whitespace."""
    job1 = Job(title="  Software Engineer  ", company="Microsoft", location="Bangalore  ")
    job2 = Job(title="Software Engineer", company="Microsoft", location="Bangalore")
    assert _generate_fingerprint(job1) == _generate_fingerprint(job2)


def test_load_posted_jobs_empty():
    """Returns default structure when file doesn't exist."""
    result = load_posted_jobs("/nonexistent/path.json")
    assert result["fingerprints"] == []
    assert result["totalCount"] == 0


def test_save_and_load_roundtrip():
    """Saved data can be loaded back."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    try:
        data = {"fingerprints": ["abc123"], "lastRun": "2026-07-17", "totalCount": 1, "sources": {}}
        save_posted_jobs(path, data)
        loaded = load_posted_jobs(path)
        assert loaded["fingerprints"] == ["abc123"]
        assert loaded["totalCount"] == 1
    finally:
        os.unlink(path)


def test_deduplicate_removes_duplicate():
    """Jobs with same fingerprint are filtered out."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    try:
        # Pre-populate with one fingerprint
        job = Job(title="SWE", company="MS", location="BLR")
        fp = _generate_fingerprint(job)
        save_posted_jobs(path, {"fingerprints": [fp], "lastRun": None, "totalCount": 1, "sources": {}})

        # Submit same job again
        jobs = [job]
        new_jobs = deduplicate_jobs(jobs, path)
        assert len(new_jobs) == 0
    finally:
        os.unlink(path)


def test_deduplicate_passes_new():
    """New, unseen jobs pass through."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    try:
        save_posted_jobs(path, {"fingerprints": ["old_fp"], "lastRun": None, "totalCount": 1, "sources": {}})
        job = Job(title="New Role", company="NewCorp", location="NewCity")
        new_jobs = deduplicate_jobs([job], path)
        assert len(new_jobs) == 1
    finally:
        os.unlink(path)
