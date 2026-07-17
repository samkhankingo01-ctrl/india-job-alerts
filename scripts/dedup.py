"""Deduplication module – fingerprinting and posted-job history management."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from models import Job

logger = logging.getLogger(__name__)


def compute_fingerprint(job: Job) -> str:
    """Compute a SHA-256 hex fingerprint for a job.

    The fingerprint is derived from the canonical title + company + city
    triple, lowercased and stripped of whitespace.

    Args:
        job: The Job instance to fingerprint.

    Returns:
        A 64-character SHA-256 hex digest string.
    """
    raw: str = (
        f"{job.title.strip()}|{job.company.strip()}|{job.city.strip()}"
        f"|{job.area.strip()}".strip().lower()
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_posted(path: Path) -> dict[str, Any]:
    """Load the posted-jobs history file, returning defaults if missing.

    Args:
        path: Path to posted-jobs.json.

    Returns:
        A dict with 'fingerprints', 'lastRun', and 'totalCount' keys.
    """
    if not path.exists():
        return {"fingerprints": [], "lastRun": None, "totalCount": 0}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not parse %s – starting fresh.", path)
        return {"fingerprints": [], "lastRun": None, "totalCount": 0}


def deduplicate(
    jobs: list[Job],
    posted_path: Path,
    retention_days: int = 7,
) -> list[Job]:
    """Filter out jobs already seen and prune old fingerprints.

    Args:
        jobs: Incoming Job instances to check against history.
        posted_path: Path to posted-jobs.json.
        retention_days: Number of days to retain fingerprints.

    Returns:
        List of *new* Job instances not previously seen.
    """
    history: dict[str, Any] = _load_posted(posted_path)
    existing: set[str] = set(history.get("fingerprints", []))

    # Assign fingerprints to incoming jobs
    for job in jobs:
        job.fingerprint = compute_fingerprint(job)

    new_jobs: list[Job] = [j for j in jobs if j.fingerprint not in existing]

    # Add new fingerprints
    for job in new_jobs:
        existing.add(job.fingerprint)

    # Prune old entries (simple count-based; if too large)
    max_fingerprints: int = retention_days * 500  # rough heuristic
    if len(existing) > max_fingerprints:
        logger.info("Pruning fingerprint set to %d entries.", max_fingerprints // 2)
        existing = set(list(existing)[-max_fingerprints // 2 :])

    # Update history
    history["fingerprints"] = sorted(existing)
    history["lastRun"] = datetime.now(timezone.utc).isoformat()
    history["totalCount"] = len(existing)

    update_posted_history(posted_path, history)

    logger.info(
        "Dedup: %d incoming, %d new, %d total known fingerprints",
        len(jobs),
        len(new_jobs),
        len(existing),
    )
    return new_jobs


def update_posted_history(
    posted_path: Path,
    history: dict[str, Any],
) -> None:
    """Write the posted-jobs history to disk.

    Args:
        posted_path: Path to posted-jobs.json.
        history: The history dictionary to persist.
    """
    posted_path.parent.mkdir(parents=True, exist_ok=True)
    with open(posted_path, "w", encoding="utf-8") as fh:
        json.dump(history, fh, ensure_ascii=False, indent=2)
    logger.debug("Posted history saved to %s", posted_path)
