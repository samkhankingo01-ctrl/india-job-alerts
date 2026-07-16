"""Main orchestrator for India Job Alerts.

Entry-point CLI that wires together scraping, deduplication, categorization,
caption formatting, and README generation. Provides --run-all, --scrape-only,
--format-only, and --readme-only flags.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import List

from config import AppConfig, LOG_FORMAT, LOG_DATE_FORMAT
from models import Job, ScraperResult

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with a consistent format.

    Args:
        level: Logging level (default INFO).
    """
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quiet down noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Stage runners
# ---------------------------------------------------------------------------


def run_scrape(config: "AppConfig") -> ScraperResult:
    """Execute the scraping stage.

    Args:
        config: Application configuration.

    Returns:
        ScraperResult with all jobs and source stats.
    """
    from scripts.scraper import run_all_scrapers

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 1: Scraping all sources")
    logger.info("=" * 60)

    result = run_all_scrapers(config)
    for name, stats in result.source_stats.items():
        status = "✅" if stats.get("success") else "❌"
        scraped = stats.get("scraped", 0)
        logger.info("  %s %s: %d jobs", status, name, scraped)

    if result.errors:
        for err in result.errors:
            logger.error("  Scraper error: %s", err)

    return result


def run_dedup(jobs: List[Job], config: "AppConfig") -> List[Job]:
    """Execute the deduplication stage.

    Args:
        jobs: Raw job list from scraping.
        config: Application configuration.

    Returns:
        List of new (non-duplicate) jobs.
    """
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
    """Execute the categorization stage.

    Args:
        jobs: New job list after dedup.

    Returns:
        Categorized job list.
    """
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
    """Execute the caption formatting stage.

    Args:
        jobs: Categorized job list.
        config: Application configuration.
    """
    from scripts.format_captions import format_captions

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 4: Caption formatting")
    logger.info("=" * 60)

    captions = format_captions(jobs, config)
    logger.info("  %d captions generated.", len(captions))


def run_readme(jobs: List[Job], config: "AppConfig") -> None:
    """Execute the README generation stage.

    Args:
        jobs: Categorized job list.
        config: Application configuration.
    """
    from scripts.generate_readme_jobs import generate_readme

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("STAGE 5: README generation")
    logger.info("=" * 60)

    generate_readme(jobs, posted_jobs_path=config.posted_jobs_file, output_path=config.readme_path)
    logger.info("  README.md updated.")


def run_all(config: "AppConfig") -> None:
    """Run the complete pipeline: scrape → dedup → categorize → format → readme.

    Args:
        config: Application configuration.
    """
    logger = logging.getLogger(__name__)
    overall_start = time.monotonic()

    # Stage 1: Scrape
    scrape_result = run_scrape(config)
    all_jobs = scrape_result.jobs

    if not all_jobs:
        logger.warning("No jobs scraped. Pipeline stopping.")
        return

    # Stage 2: Dedup
    new_jobs = run_dedup(all_jobs, config)

    if not new_jobs:
        logger.info("No new jobs after dedup. Skipping format/readme stages.")
        return

    # Stage 3: Categorize
    categorized = run_categorize(new_jobs)

    # Stage 4: Format captions
    run_format(categorized, config)

    # Stage 5: README
    run_readme(categorized, config)

    elapsed = time.monotonic() - overall_start
    logger.info("=" * 60)
    logger.info("Pipeline complete in %.1f seconds.", elapsed)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Raw sys.argv.

    Returns:
        Parsed namespace object.
    """
    parser = argparse.ArgumentParser(
        description="India Job Alerts — automated job aggregator",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--run-all",
        action="store_true",
        help="Run the full pipeline (scrape → dedup → categorize → format → readme)",
    )
    group.add_argument(
        "--scrape-only",
        action="store_true",
        help="Run only the scraping stage",
    )
    group.add_argument(
        "--format-only",
        action="store_true",
        help="Generate captions from existing data",
    )
    group.add_argument(
        "--readme-only",
        action="store_true",
        help="Update README stats only",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    return parser.parse_args(argv[1:])


def main(argv: List[str] | None = None) -> None:
    """Main entry-point.

    Args:
        argv: Command-line arguments; defaults to sys.argv.
    """
    if argv is None:
        argv = sys.argv

    args = _parse_args(argv)
    _setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(__name__)

    config = AppConfig.from_env()

    # Default to --run-all if no flag given
    if not any([args.run_all, args.scrape_only, args.format_only, args.readme_only]):
        args.run_all = True

    try:
        if args.scrape_only:
            run_scrape(config)
        elif args.format_only:
            # Load jobs from a hypothetical source; in practice the formatter
            # is invoked with already-scraped data.
            logger.info("Format-only mode: no jobs in memory. Use --run-all for full pipeline.")
        elif args.readme_only:
            from scripts.dedup import load_posted_jobs

            ledger = load_posted_jobs(config.posted_jobs_file)
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
