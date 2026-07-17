"""Caption formatter – produces Instagram-ready captions for job listings."""

from __future__ import annotations

import logging
from pathlib import Path

from models import CaptionBlock, Job

logger = logging.getLogger(__name__)

# Base hashtags applied to every caption
_BASE_HASHTAGS: list[str] = [
    "jobs",
    "indiajobs",
    "hiring",
    "jobsearch",
    "careergoals",
    "jobseekers",
    "india",
]


def format_caption(job: Job) -> CaptionBlock:
    """Produce a single Instagram-ready caption block from a Job.

    Args:
        job: The Job instance to format.

    Returns:
        A CaptionBlock with formatted text and metadata.
    """
    salary: str = job.salary if job.salary else "Not Disclosed"
    location: str = job.city or "Anywhere"
    if job.state:
        location += f", {job.state}"

    category_tag: list[str] = []
    if job.category and job.category != "Other":
        cat_lower: str = job.category.lower().replace(" ", "")
        category_tag.append(cat_lower)

    hashtags: list[str] = _BASE_HASHTAGS + category_tag

    text: str = (
        f"🚨 Hiring Now!\n\n"
        f"🏢 Company: {job.company}\n"
        f"💼 Role: {job.title}\n"
        f"📍 Location: {location}\n"
        f"💰 Salary: {salary}\n"
        f"🔗 Apply: {job.url}\n\n"
        + " ".join(f"#{h}" for h in hashtags)
        + "\n---"
    )

    return CaptionBlock(
        text=text,
        job_title=job.title,
        job_company=job.company,
        is_government=job.is_government,
        hashtags=hashtags,
    )


def format_all_captions(jobs: list[Job], output_path: Path) -> None:
    """Format captions for all jobs and write to a single file.

    Args:
        jobs: List of Job instances to format.
        output_path: Path where the captions file will be written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []

    for job in jobs:
        cb: CaptionBlock = format_caption(job)
        blocks.append(cb.text)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n\n\n".join(blocks))

    logger.info("Wrote %d captions to %s", len(blocks), output_path)
