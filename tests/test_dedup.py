"""Tests for the dedup module."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import Job
from scripts.dedup import compute_fingerprint, deduplicate, update_posted_history


class TestComputeFingerprint:
    """Tests for the compute_fingerprint function."""

    def test_deterministic(self) -> None:
        """Same input should produce the same fingerprint."""
        j1 = Job(title="SWE", company="Google", city="Bangalore")
        j2 = Job(title="SWE", company="Google", city="Bangalore")
        assert compute_fingerprint(j1) == compute_fingerprint(j2)

    def test_different_jobs_different_fingerprints(self) -> None:
        """Different jobs should produce different fingerprints."""
        j1 = Job(title="SWE", company="Google", city="Bangalore")
        j2 = Job(title="PM", company="Google", city="Bangalore")
        assert compute_fingerprint(j1) != compute_fingerprint(j2)

    def test_case_insensitive(self) -> None:
        """Fingerprint should be case-insensitive."""
        j1 = Job(title="SWE", company="GOOGLE", city="BANGALORE")
        j2 = Job(title="swe", company="google", city="bangalore")
        assert compute_fingerprint(j1) == compute_fingerprint(j2)

    def test_whitespace_trimmed(self) -> None:
        """Extra whitespace should be trimmed."""
        j1 = Job(title="  SWE  ", company="Google", city="Bangalore")
        j2 = Job(title="SWE", company="Google", city="Bangalore")
        assert compute_fingerprint(j1) == compute_fingerprint(j2)

    def test_is_sha256_hex(self) -> None:
        """Fingerprint should be a 64-char hex string."""
        j = Job(title="Test", company="Test Co", city="Delhi")
        fp = compute_fingerprint(j)
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_hash_content(self) -> None:
        """Verify the fingerprint is the expected SHA-256."""
        j = Job(title="A", company="B", city="C")
        fp = compute_fingerprint(j)
        expected = hashlib.sha256("a|b|c".encode("utf-8")).hexdigest()
        assert fp == expected


class TestDeduplicate:
    """Tests for the deduplicate function."""

    def test_returns_all_as_new_when_no_history(self, tmp_path: Path) -> None:
        """When no posted-jobs.json exists, all jobs are new."""
        jobs = [
            Job(title="SWE", company="A", city="X"),
            Job(title="PM", company="B", city="Y"),
        ]
        posted_path = tmp_path / "posted.json"
        new = deduplicate(jobs, posted_path)
        assert len(new) == 2
        assert posted_path.exists()

    def test_filters_previously_seen(self, tmp_path: Path) -> None:
        """Jobs with fingerprints already in history should be filtered."""
        posted_path = tmp_path / "posted.json"
        history = {
            "fingerprints": [
                compute_fingerprint(Job(title="SWE", company="A", city="X")),
            ],
            "lastRun": None,
            "totalCount": 1,
        }
        posted_path.parent.mkdir(parents=True, exist_ok=True)
        posted_path.write_text(json.dumps(history))

        jobs = [
            Job(title="SWE", company="A", city="X"),  # already seen
            Job(title="PM", company="B", city="Y"),    # new
        ]
        new = deduplicate(jobs, posted_path)
        assert len(new) == 1
        assert new[0].title == "PM"

    def test_updates_history_with_new(self, tmp_path: Path) -> None:
        """After dedup, history should include new fingerprints."""
        posted_path = tmp_path / "posted.json"
        jobs = [Job(title="Unique", company="NewCo", city="Mumbai")]
        deduplicate(jobs, posted_path)

        with open(posted_path) as f:
            history = json.load(f)
        assert history["totalCount"] == 1
        assert len(history["fingerprints"]) == 1
        assert history["lastRun"] is not None

    def test_empty_input(self, tmp_path: Path) -> None:
        """Empty job list should return empty."""
        posted_path = tmp_path / "posted.json"
        new = deduplicate([], posted_path)
        assert new == []

    def test_corrupt_history_starts_fresh(self, tmp_path: Path) -> None:
        """Corrupt posted-jobs.json should be handled gracefully."""
        posted_path = tmp_path / "posted.json"
        posted_path.write_text("not valid json")

        jobs = [Job(title="A", company="B", city="C")]
        new = deduplicate(jobs, posted_path)
        assert len(new) == 1  # all treated as new


class TestUpdatePostedHistory:
    """Tests for update_posted_history."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """Should create the file with the provided history."""
        path = tmp_path / "data" / "posted.json"
        history = {"fingerprints": ["a", "b"], "lastRun": "now", "totalCount": 2}
        update_posted_history(path, history)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert data["fingerprints"] == ["a", "b"]
        assert data["totalCount"] == 2

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """Should overwrite an existing file."""
        path = tmp_path / "posted.json"
        path.write_text('{"old": true}')
        history = {"fingerprints": ["x"], "lastRun": None, "totalCount": 1}
        update_posted_history(path, history)
        with open(path) as f:
            data = json.load(f)
        assert "old" not in data
        assert data["fingerprints"] == ["x"]
