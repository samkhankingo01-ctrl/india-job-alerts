"""Categorizer module for India Job Alerts.

Assigns each Job to a category based on keyword matching against
the CATEGORY_MAP defined in config.py. Falls back to "Other" when
no keywords match.
"""

from __future__ import annotations

import logging
from typing import List

from config import CATEGORY_MAP
from models import Job

logger = logging.getLogger(__name__)


def _match_category(title: str, description: str) -> str:
    """Determine the best-matching category for a job's text.

    Checks both the title and description against every keyword in
    CATEGORY_MAP. The category with the most keyword matches wins.

    Args:
        title: Job title string.
        description: Job description / snippet string.

    Returns:
        Category name string (e.g. "IT", "Government").
    """
    combined = f"{title} {description}".lower()
    best_category = "Other"
    best_score = 0

    for category, keywords in CATEGORY_MAP.items():
        score = sum(1 for kw in keywords if kw.lower() in combined)
        if score > best_score:
            best_score = score
            best_category = category

    return best_category


def categorize_jobs(jobs: List[Job]) -> List[Job]:
    """Assign a category to every job in the list.

    Mutates the Job objects in-place (sets job.category) and returns
    the same list for chaining convenience.

    Args:
        jobs: List of Job objects to classify.

    Returns:
        The same list with category fields populated.
    """
    stats: dict = {}
    for job in jobs:
        job.category = _match_category(job.title, job.description)
        stats[job.category] = stats.get(job.category, 0) + 1

    logger.info("Categorization: %s", stats)
    return jobs
