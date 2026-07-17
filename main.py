"""Main pipeline CLI for the India Jobs Board scraper.

Usage:
    python main.py --run-all       # Full pipeline
    python main.py --scrape-only   # Scrape + save, no formatting
    python main.py --format-only   # Format captions from existing data
    python main.py --readme-only   # Regenerate README + HTML from existing data
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# ── sys.path setup – MUST come before local imports ──────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from config import Config
from models import Job, ScraperResult
from scripts.dedup import deduplicate
from scripts.categorizer import categorize_all
from scripts.format_captions import format_all_captions
from scripts.generate_readme import generate_readme
from scripts.generate_html_board import generate_html_board
from scripts.scraper import run_all_scrapers

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format=Config.LOG_FORMAT,
    datefmt=Config.LOG_DATE_FORMAT,
)
logger = logging.getLogger("main")


def _save_json(data: list[dict] | dict, path: Path) -> None:
    """Save data as JSON with UTF-8 encoding and indentation.

    Args:
        data: A list or dict to serialize.
        path: Output file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    logger.info("Saved %s", path)


def cmd_run_all(cfg: Config) -> int:
    """Execute the full pipeline: scrape → dedup → categorize → format → generate.

    Args:
        cfg: Pipeline configuration.

    Returns:
        Exit code (0 for success).
    """
    start: float = time.time()
    logger.info("=== India Jobs Board Pipeline START ===")

    # 1. Scrape
    logger.info("Step 1/7: Scraping all sources...")
    result: ScraperResult = run_all_scrapers(cfg)
    logger.info(
        "Scraped %d total jobs from %s in %.1fs",
        result.total_jobs,
        ", ".join(f"{k}={v}" for k, v in result.source_stats.items()),
        result.elapsed_seconds,
    )
    if result.errors:
        for err in result.errors:
            logger.warning("Scraper error: %s", err)

    # 2. Dedup
    logger.info("Step 2/7: Deduplicating...")
    new_jobs: list[Job] = deduplicate(
        result.jobs,
        cfg.posted_jobs_file,
        cfg.DEDUP_RETENTION_DAYS,
    )
    result.new_jobs = len(new_jobs)
    logger.info("New jobs after dedup: %d", len(new_jobs))

    if not new_jobs:
        logger.info("No new jobs found. Pipeline complete.")
        elapsed = time.time() - start
        logger.info("=== Pipeline done in %.1fs ===", elapsed)
        return 0

    # 3. Categorize
    logger.info("Step 3/7: Categorizing...")
    categorize_all(new_jobs)

    # 4. Save jobs-today.json
    logger.info("Step 4/7: Saving jobs-today.json...")
    _save_json([j.to_dict() for j in new_jobs], cfg.jobs_today_file)

    # 5. Save posted-jobs.json (already done in dedup, but ensure it exists)
    logger.info("Step 5/7: Posted history already updated during dedup.")

    # 6. Format captions
    logger.info("Step 6/7: Formatting captions...")
    format_all_captions(new_jobs, cfg.captions_file)

    # 7. Generate README + HTML
    logger.info("Step 7/7: Generating README and HTML board...")
    generate_readme(new_jobs, cfg.posted_jobs_file, cfg.readme_path)
    generate_html_board(new_jobs, cfg.html_board_path)

    elapsed: float = time.time() - start
    logger.info("=== Pipeline complete in %.1fs ===", elapsed)
    logger.info("Summary: %d new jobs | %d total tracked", len(new_jobs), 0)
    return 0


def cmd_scrape_only(cfg: Config) -> int:
    """Scrape and dedup only; save raw and posted data.

    Args:
        cfg: Pipeline configuration.

    Returns:
        Exit code.
    """
    logger.info("=== Scrape-only mode ===")
    result: ScraperResult = run_all_scrapers(cfg)
    new_jobs: list[Job] = deduplicate(
        result.jobs, cfg.posted_jobs_file, cfg.DEDUP_RETENTION_DAYS,
    )
    categorize_all(new_jobs)
    _save_json([j.to_dict() for j in new_jobs], cfg.jobs_today_file)
    logger.info("Scrape-only done: %d new jobs", len(new_jobs))
    return 0


def cmd_format_only(cfg: Config) -> int:
    """Regenerate captions, README, and HTML from existing jobs-today.json.

    Args:
        cfg: Pipeline configuration.

    Returns:
        Exit code.
    """
    logger.info("=== Format-only mode ===")
    if not cfg.jobs_today_file.exists():
        logger.error("No jobs-today.json found at %s", cfg.jobs_today_file)
        return 1

    with open(cfg.jobs_today_file, "r", encoding="utf-8") as fh:
        data: list[dict] = json.load(fh)

    jobs: list[Job] = [Job.from_dict(d) for d in data]
    logger.info("Loaded %d jobs from %s", len(jobs), cfg.jobs_today_file)

    format_all_captions(jobs, cfg.captions_file)
    generate_readme(jobs, cfg.posted_jobs_file, cfg.readme_path)
    generate_html_board(jobs, cfg.html_board_path)
    logger.info("Format-only done.")
    return 0


def cmd_readme_only(cfg: Config) -> int:
    """Regenerate only README and HTML from existing jobs-today.json.

    Args:
        cfg: Pipeline configuration.

    Returns:
        Exit code.
    """
    logger.info("=== README-only mode ===")
    if not cfg.jobs_today_file.exists():
        logger.error("No jobs-today.json found at %s", cfg.jobs_today_file)
        return 1

    with open(cfg.jobs_today_file, "r", encoding="utf-8") as fh:
        data: list[dict] = json.load(fh)

    jobs: list[Job] = [Job.from_dict(d) for d in data]
    generate_readme(jobs, cfg.posted_jobs_file, cfg.readme_path)
    generate_html_board(jobs, cfg.html_board_path)
    logger.info("README-only done.")
    return 0


def main() -> int:
    """Parse arguments and dispatch to the appropriate pipeline command.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = argparse.ArgumentParser(
        description="India Jobs Board – Automated Job Aggregator",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--run-all",
        action="store_true",
        help="Run the full pipeline (scrape -> dedup -> format -> generate)",
    )
    group.add_argument(
        "--scrape-only",
        action="store_true",
        help="Scrape, dedup, and categorize only (no README/captions)",
    )
    group.add_argument(
        "--format-only",
        action="store_true",
        help="Regenerate captions, README, and HTML from existing jobs-today.json",
    )
    group.add_argument(
        "--readme-only",
        action="store_true",
        help="Regenerate only README + HTML from existing jobs-today.json",
    )

    args = parser.parse_args()

    # Default to --run-all if no flag given
    if not any([args.run_all, args.scrape_only, args.format_only, args.readme_only]):
        args.run_all = True

    cfg: Config = Config.get_config()

    try:
        if args.scrape_only:
            return cmd_scrape_only(cfg)
        elif args.format_only:
            return cmd_format_only(cfg)
        elif args.readme_only:
            return cmd_readme_only(cfg)
        else:
            return cmd_run_all(cfg)
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user.")
        return 130
    except Exception:
        logger.exception("Pipeline failed with an unhandled error.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
