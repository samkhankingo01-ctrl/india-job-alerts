"""Categorizer – assigns a category to each job based on keyword matching."""

from __future__ import annotations

import logging
from typing import ClassVar

from config import Config
from models import Job

logger = logging.getLogger(__name__)


def categorize(job: Job, category_map: dict[str, list[str]]) -> str:
    """Assign a single category to a job based on title keyword matching.

    The first matching category in order is used. If nothing matches,
    returns "Other".

    Args:
        job: The Job to categorize.
        category_map: Mapping of category name -> list of keyword patterns.

    Returns:
        The assigned category name.
    """
    text: str = (job.title + " " + job.description).lower()

    for category, keywords in category_map.items():
        for kw in keywords:
            if kw.lower() in text:
                logger.debug(
                    "Job '%s' matched category '%s' via keyword '%s'",
                    job.title,
                    category,
                    kw,
                )
                return category

    # Detect government source tags
    if "government" in (job.title + " " + job.description).lower():
        return "Government"

    logger.debug("Job '%s' fell through to 'Other'", job.title)
    return "Other"


def categorize_all(jobs: list[Job]) -> list[Job]:
    """Assign categories to all jobs in-place.

    Args:
        jobs: List of Job instances to categorize.

    Returns:
        The same list (mutated in place) for chaining convenience.
    """
    category_map: dict[str, list[str]] = Config.CATEGORY_MAP
    count: int = 0
    for job in jobs:
        if not job.category:
            job.category = categorize(job, category_map)
            count += 1
    logger.info("Categorized %d jobs.", count)
    return jobs
