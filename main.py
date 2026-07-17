"""Main orchestrator for India Job Alerts.

Entry-point CLI that wires together scraping, deduplication, categorization,
caption formatting, and README generation. Provides --run-all, --scrape-only,
--format-only, and --readme-only flags.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import List, Optional

from config import AppConfig, LOG_FORMAT, LOG_DATE_FORMAT
from models import Job, ScraperResult

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a consistent format."""
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Data persistence
# ---------------------------------------------------------------------------


def save_jobs_json(jobs: List[Job], path: str) -> None:
    """Save scraped jobs to a JSON file.

    Each job is serialized as a dict with all fields.

    Args:
        jobs: List of Job objects to persist.
        path: Output file path.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = [
        {
            "title": j.title,
            "company": j.company,
            "company_logo": "",
            "location": j.location,
            "salary": j.salary,
            "url": j.url,
            "source": j.source,
            "category": j.category,
            "posted_date": j.posted_date,
            "last_date": j.last_date,
            "is_government": j.is_government,
            "description": j.description,
            "fingerprint": j.fingerprint,
        }
        for j in jobs
    ]
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        logger = logging.getLogger(__name__)
        logger.info("Saved %d jobs to %s", len(data), path)
    except OSError as exc:
        logging.getLogger(__name__).error("Failed to save jobs JSON: %s", exc)


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------


def run_scrape(config: "AppConfig") -> ScraperResult:
    """Execute the scraping stage."""
    from scripts.scraper import run_all_scrapers

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 1: Scraping all sources")
    logger.info("=" * 60)

    result = run_all_scrapers(config)
    for name, stats in result.source_stats.items():
        status = "OK" if stats.get("success") else "FAIL"
        scraped = stats.get("scraped", 0)
        logger.info("  [%s] %s: %d jobs", status, name, scraped)

    if result.errors:
        for err in result.errors:
            logger.error("  Scraper error: %s", err)

    return result


def run_dedup(jobs: List[Job], config: "AppConfig") -> List[Job]:
    """Execute the deduplication stage."""
    from scripts.dedup import deduplicate_jobs

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 2: Deduplication")
    logger.info("=" * 60)

    new_jobs = deduplicate_jobs(
        jobs,
        posted_jobs_path=config.posted_jobs_file,
        retention_days=config.dedup.retention_days,
    )
    logger.info("  %d jobs after dedup.", len(new_jobs))
    return new_jobs


def run_categorize(jobs: List[Job]) -> List[Job]:
    """Execute the categorization stage."""
    from scripts.categorizer import categorize_jobs

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 3: Categorization")
    logger.info("=" * 60)

    categorized = categorize_jobs(jobs)
    categories = {job.category for job in categorized}
    logger.info("  Categories found: %s", sorted(categories))
    return categorized


def run_format(jobs: List[Job], config: "AppConfig") -> None:
    """Execute the caption formatting stage."""
    from scripts.format_captions import format_captions

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 4: Caption formatting")
    logger.info("=" * 60)

    captions = format_captions(jobs, config)
    logger.info("  %d captions generated.", len(captions))


def run_readme(jobs: List[Job], config: "AppConfig") -> None:
    """Execute the README generation stage."""
    from scripts.generate_readme_jobs import generate_readme

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 5: README generation")
    logger.info("=" * 60)

    generate_readme(jobs, posted_jobs_path=config.posted_jobs_file, output_path=config.readme_path)
    logger.info("  README.md updated.")


def run_all(config: "AppConfig") -> None:
    """Run the complete pipeline: scrape → dedup → categorize → format → readme.

    Also saves jobs-today.json with all individual job records.
    """
    from datetime import datetime, timezone

    logger = logging.getLogger(__name__)
    overall_start = time.monotonic()

    # Stage 1: Scrape
    scrape_result = run_scrape(config)
    all_jobs = scrape_result.jobs

    if not all_jobs:
        logger.warning("No jobs scraped. Creating empty data files.")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_jobs_json([], os.path.join(config.data_dir, f"jobs-{today}.json"))
        return

    # Save ALL scraped jobs to jobs-today.json (before dedup)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    jobs_today_path = os.path.join(config.data_dir, f"jobs-{today}.json")
    save_jobs_json(all_jobs, jobs_today_path)

    # Stage 2: Dedup
    new_jobs = run_dedup(all_jobs, config)

    # Stage 3: Categorize
    categorized = run_categorize(new_jobs if new_jobs else all_jobs)

    # Stage 4: Format captions
    run_format(categorized, config)

    # Stage 5: README
    run_readme(categorized, config)

    elapsed = time.monotonic() - overall_start
    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds — %d total, %d new jobs.",
                elapsed, len(all_jobs), len(new_jobs))
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="India Job Alerts - automated job aggregator",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--run-all", action="store_true",
                       help="Run the full pipeline")
    group.add_argument("--scrape-only", action="store_true",
                       help="Run only the scraping stage")
    group.add_argument("--format-only", action="store_true",
                       help="Generate captions from existing data")
    group.add_argument("--readme-only", action="store_true",
                       help="Update README stats only")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable DEBUG-level logging")
    return parser.parse_args(argv[1:])


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry-point."""
    if argv is None:
        argv = sys.argv

    args = _parse_args(argv)
    _setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(__name__)

    config = AppConfig.from_env()

    if not any([args.run_all, args.scrape_only, args.format_only, args.readme_only]):
        args.run_all = True

    try:
        if args.scrape_only:
            result = run_scrape(config)
            if result.jobs:
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                save_jobs_json(result.jobs, os.path.join(config.data_dir, f"jobs-{today}.json"))
        elif args.format_only:
            # Load existing jobs data
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            jobs_path = os.path.join(config.data_dir, f"jobs-{today}.json")
            if os.path.exists(jobs_path):
                with open(jobs_path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                jobs = [Job(**item) for item in raw]
                categorized = run_categorize(jobs)
                run_format(categorized, config)
            else:
                logger.warning("No jobs data found at %s. Run --run-all first.", jobs_path)
        elif args.readme_only:
            run_readme([], config)
        else:
            run_all(config)
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
