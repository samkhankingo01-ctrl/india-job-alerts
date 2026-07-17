"""Caption formatter for India Job Alerts.

Generates Instagram-ready captions (Markdown) from Job objects and writes
them to dated output files. Uses ASCII-safe emoji characters that render
correctly on all platforms.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List

from config import AppConfig
from models import CaptionBlock, Job

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category-specific hashtags
# ---------------------------------------------------------------------------

CATEGORY_HASHTAG_MAP: Dict[str, str] = {
    "IT": "#ittech #techjobs #softwarejobs",
    "Government": "#governmentjobs #sarkarinaukri #govtjobs",
    "Freshers": "#fresherjobs #entrylevel #campusplacement",
    "Remote": "#remotejobs #wfh #workfromhome",
    "Banking": "#bankingjobs #financejobs #bankjobs",
    "Engineering": "#engineeringjobs #corejobs #engineer",
    "Healthcare": "#healthcarejobs #medicaljobs #doctorjobs",
    "Sales": "#salesjobs #bde #businessdevelopment",
    "Marketing": "#marketingjobs #digitalmarketing #contentjobs",
    "Startup": "#startupjobs #founders #startuplife",
    "PSU": "#psujobs #publicsector #govtjobs",
    "Part Time": "#parttimejobs #gigeconomy #sidehustle",
    "Education": "#educationjobs #teachingjobs #academicjobs",
    "HR": "#hrjobs #recruitment #talentacquisition",
    "Other": "#jobsearch #career",
}


def _get_category_hashtags(category: str) -> str:
    """Return category-specific hashtags."""
    return CATEGORY_HASHTAG_MAP.get(category, "#jobsearch #career")


# ---------------------------------------------------------------------------
# Caption building
# ---------------------------------------------------------------------------


def build_caption(job: Job, config: AppConfig) -> CaptionBlock:
    """Build a single Instagram-ready caption for one Job.

    Applies the government header variant when job.is_government is True.

    Args:
        job: The Job to render.
        config: Application configuration for caption settings.

    Returns:
        CaptionBlock with full caption text and metadata.
    """
    cfg = config.caption

    if job.is_government:
        header = cfg.government_header
        org_label = "Organization"
        last_date_line = f"\nLast Date: {job.last_date}" if job.last_date else ""
    else:
        header = cfg.corporate_header
        org_label = "Company"
        last_date_line = ""

    category_hashtags = _get_category_hashtags(job.category)
    global_hashtags = " ".join(cfg.hashtags_global)

    lines = [
        header,
        "",
        f"{org_label}: {job.company}",
        f"Role: {job.title}",
        f"Location: {job.location}",
        f"Salary: {job.salary}",
        f"Apply: {job.url}",
    ]

    if last_date_line:
        lines.append(last_date_line)

    lines.extend([
        "",
        f"{global_hashtags} {category_hashtags}",
        cfg.separator,
    ])

    all_hashtags = f"{global_hashtags} {category_hashtags}"
    hashtags = [h.strip() for h in all_hashtags.split() if h.strip()]

    return CaptionBlock(
        text="\n".join(lines),
        job_title=job.title,
        job_company=job.company,
        is_government=job.is_government,
        hashtags=hashtags,
    )


def format_captions(jobs: List[Job], config: AppConfig) -> List[CaptionBlock]:
    """Generate captions for a list of jobs and write them to a dated file.

    Args:
        jobs: List of categorized Job objects.
        config: Application configuration.

    Returns:
        List of CaptionBlock objects generated.
    """
    if not jobs:
        logger.warning("format_captions called with empty job list; nothing to write.")
        return []

    captions: List[CaptionBlock] = []
    for job in jobs:
        captions.append(build_caption(job, config))

    # Write to dated output file
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = config.captions_filename_template.format(date=today)
    output_path = os.path.join(config.output_dir, filename)
    os.makedirs(config.output_dir, exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(f"# India Job Alerts - {today}\n\n")
            fh.write(f"**Total Jobs Today:** {len(jobs)}\n\n---\n\n")
            for i, cb in enumerate(captions, 1):
                fh.write(f"## Post #{i}\n\n")
                fh.write(cb.text)
                fh.write("\n")
        logger.info("Wrote %d captions to %s", len(captions), output_path)
    except OSError as exc:
        logger.error("Failed to write captions file %s: %s", output_path, exc)

    return captions
