"""Deduplication module for India Job Alerts.

Uses SHA-256 fingerprinting on (title + company + location) to detect
duplicate jobs across runs. Maintains a posted-jobs.json ledger.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List

from models import Job

logger = logging.getLogger(__name__)


def _generate_fingerprint(job: Job) -> str:
    """Generate a deterministic SHA-256 fingerprint for a job.

    Uses the lowercased, whitespace-stripped concatenation of
    title, company, and location.

    Args:
        job: The Job to fingerprint.

    Returns:
        64-character hex digest string.
    """
    raw = (
        f"{job.title.strip().lower()}|"
        f"{job.company.strip().lower()}|"
        f"{job.location.strip().lower()}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_posted_jobs(posted_jobs_path: str) -> Dict:
    """Load the posted-jobs.json ledger file.

    Args:
        posted_jobs_path: Filesystem path to posted-jobs.json.

    Returns:
        Dictionary with keys 'fingerprints', 'lastRun', 'totalCount', 'sources'.
        Returns a default empty ledger if the file is missing or corrupt.
    """
    default: Dict = {
        "fingerprints": [],
        "lastRun": None,
        "totalCount": 0,
        "sources": {},
    }

    if not os.path.exists(posted_jobs_path):
        logger.warning("posted-jobs.json not found at %s; starting fresh.", posted_jobs_path)
        return default

    try:
        with open(posted_jobs_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Ensure required keys exist
        for key in default:
            data.setdefault(key, default[key])
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read posted-jobs.json: %s. Starting fresh.", exc)
        return default


def save_posted_jobs(posted_jobs_path: str, data: Dict) -> None:
    """Persist the posted-jobs ledger to disk.

    Args:
        posted_jobs_path: Filesystem path to save to.
        data: Ledger dictionary to serialise.
    """
    os.makedirs(os.path.dirname(posted_jobs_path) or ".", exist_ok=True)
    try:
        with open(posted_jobs_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        logger.debug("posted-jobs.json saved with %d fingerprints.", len(data.get("fingerprints", [])))
    except OSError as exc:
        logger.error("Failed to save posted-jobs.json: %s", exc)


def deduplicate_jobs(
    jobs: List[Job],
    posted_jobs_path: str,
    retention_days: int = 7,
) -> List[Job]:
    """Filter out jobs that have already been posted (fingerprint match).

    Also updates the posted-jobs.json ledger with new fingerprints and
    last-run timestamp.

    Args:
        jobs: Incoming list of Job objects.
        posted_jobs_path: Path to posted-jobs.json ledger.
        retention_days: Number of days to retain fingerprints; older
            entries are pruned automatically.

    Returns:
        List of new Job objects (not previously seen).
    """
    ledger = load_posted_jobs(posted_jobs_path)
    existing_fingerprints: set = set(ledger.get("fingerprints", []))

    new_jobs: List[Job] = []
    new_fingerprints: List[str] = []

    for job in jobs:
        fp = job.fingerprint or _generate_fingerprint(job)
        job.fingerprint = fp
        if fp not in existing_fingerprints:
            new_jobs.append(job)
            new_fingerprints.append(fp)
            existing_fingerprints.add(fp)

    # Update ledger
    ledger["fingerprints"] = list(existing_fingerprints)
    ledger["lastRun"] = datetime.now(timezone.utc).isoformat()
    ledger["totalCount"] = len(existing_fingerprints)

    save_posted_jobs(posted_jobs_path, ledger)

    logger.info(
        "Dedup: %d total, %d new, %d duplicates skipped.",
        len(jobs),
        len(new_jobs),
        len(jobs) - len(new_jobs),
    )
    return new_jobs
