"""Scraper module – fetches jobs from JSearch, Arbeitnow, and Remotive."""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

import requests

from config import Config
from models import Job, ScraperResult

logger = logging.getLogger(__name__)


def _make_jsearch_job(item: dict[str, Any], cfg: Config) -> Job:
    """Convert a JSearch API response item into a Job model.

    Args:
        item: Raw job item from JSearch response.
        cfg: Pipeline configuration.

    Returns:
        A populated Job instance.
    """
    title = str(item.get("job_title", "") or "").strip()
    company = str(item.get("employer_name", "") or "").strip()
    city = str(item.get("job_city", "") or "").strip()
    state = str(item.get("job_state", "") or "").strip()
    # Build a stable fingerprint-like key for in-source dedup
    raw_key = f"{title}|{company}|{city}".lower()

    return Job(
        title=title,
        company=company,
        company_logo=str(item.get("employer_logo", "") or ""),
        city=city,
        state=state,
        area=str(item.get("job_country", "") or ""),
        salary=str(item.get("job_salary", "") or "").replace("None", ""),
        url=str(item.get("job_apply_link", "") or ""),
        source="jsearch",
        posted_date=str(item.get("job_posted_at", "") or ""),
        posted_date_raw=str(item.get("job_posted_at", "") or ""),
        description=str(item.get("job_description", "") or ""),
        employment_type=str(item.get("job_employment_type", "") or ""),
        is_government=False,
        is_remote=False,
        job_id=str(item.get("job_id", "") or ""),
        fingerprint=raw_key,  # temporary; real fingerprint set in dedup
    )


def scrape_jsearch(cfg: Config) -> list[Job]:
    """Scrape jobs from the JSearch RapidAPI endpoint.

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of deduplicated Job instances from JSearch.
    """
    api_key: str = os.getenv("RAPIDAPI_KEY", "")
    if not api_key:
        logger.warning(
            "RAPIDAPI_KEY not set – skipping JSearch scraper."
        )
        return []

    headers: dict[str, str] = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    seen: set[str] = set()
    jobs: list[Job] = []

    for query in cfg.SEARCH_QUERIES:
        url: str = (
            f"https://jsearch.p.rapidapi.com/v1/search?"
            f"query={requests.utils.quote(query)}&page=1&num_pages=2"
        )
        try:
            logger.info("JSearch querying: %s", query)
            resp: requests.Response = requests.get(
                url, headers=headers, timeout=30,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            items: list[dict[str, Any]] = data.get("data", [])
            for item in items:
                job: Job = _make_jsearch_job(item, cfg)
                key: str = job.fingerprint
                if key not in seen:
                    seen.add(key)
                    jobs.append(job)
            logger.debug("JSearch got %d jobs for query: %s", len(items), query)
            # Be polite to the API
            time.sleep(random.uniform(0.5, 1.5))
        except Exception:
            logger.exception("JSearch failed for query: %s", query)

    logger.info("JSearch total unique jobs: %d", len(jobs))
    return jobs


def _make_arbeitnow_job(item: dict[str, Any], cfg: Config) -> Job:
    """Convert an Arbeitnow API response item into a Job model.

    Args:
        item: Raw job item from Arbeitnow response.
        cfg: Pipeline configuration.

    Returns:
        A populated Job instance.
    """
    title: str = str(item.get("title", "") or "").strip()
    company: str = str(item.get("company_name", "") or "").strip()
    raw_key: str = f"{title}|{company}|".lower()
    salary: str = str(item.get("salary", "") or "")
    if salary in ("None", "NaN", ""):
        salary = ""

    return Job(
        title=title,
        company=company,
        company_logo=str(item.get("company_logo_url", "") or ""),
        city=str(item.get("location", "") or ""),
        state="",
        area="",
        salary=salary,
        url=str(item.get("url", "") or ""),
        source="arbeitnow",
        posted_date=str(item.get("created_at", "") or ""),
        posted_date_raw=str(item.get("created_at", "") or ""),
        description="",
        employment_type=str(item.get("employment_type", "") or ""),
        is_government=False,
        is_remote=bool(item.get("remote", False)),
        job_id=str(item.get("id", "") or ""),
        fingerprint=raw_key,
    )


def scrape_arbeitnow(cfg: Config) -> list[Job]:
    """Scrape jobs from the Arbeitnow job board API (no auth needed).

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of deduplicated Job instances from Arbeitnow.
    """
    seen: set[str] = set()
    jobs: list[Job] = []

    for page in range(1, 11):
        url: str = (
            f"https://www.arbeitnow.com/api/job-board-api?"
            f"page={page}&per_page=50"
        )
        try:
            logger.info("Arbeitnow fetching page %d", page)
            resp: requests.Response = requests.get(url, timeout=30)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            items: list[dict[str, Any]] = data.get("data", [])
            for item in items:
                job: Job = _make_arbeitnow_job(item, cfg)
                key: str = job.fingerprint
                if key not in seen:
                    seen.add(key)
                    jobs.append(job)
            logger.debug("Arbeitnow page %d: %d jobs", page, len(items))
            if len(items) < 50:
                logger.info("Arbeitnow: fewer than 50 on page %d, stopping.", page)
                break
            time.sleep(random.uniform(0.3, 0.8))
        except Exception:
            logger.exception("Arbeitnow failed on page %d", page)

    logger.info("Arbeitnow total unique jobs: %d", len(jobs))
    return jobs


def _make_remotive_job(item: dict[str, Any], cfg: Config) -> Job:
    """Convert a Remotive API response item into a Job model.

    Args:
        item: Raw job item from Remotive response.
        cfg: Pipeline configuration.

    Returns:
        A populated Job instance.
    """
    title: str = str(item.get("title", "") or "").strip()
    company: str = str(item.get("company_name", "") or "").strip()
    raw_key: str = f"{title}|{company}|".lower()

    return Job(
        title=title,
        company=company,
        company_logo=str(item.get("company_logo_url", "") or ""),
        city=str(item.get("candidate_required_location", "") or ""),
        state="",
        area="",
        salary=str(item.get("salary", "") or "").replace("None", ""),
        url=str(item.get("url", "") or ""),
        source="remotive",
        posted_date=str(item.get("publication_date", "") or ""),
        posted_date_raw=str(item.get("publication_date", "") or ""),
        description=str(item.get("description", "") or ""),
        employment_type="",
        is_government=False,
        is_remote=True,
        job_id=str(item.get("id", "") or ""),
        fingerprint=raw_key,
    )


def scrape_remotive(cfg: Config) -> list[Job]:
    """Scrape jobs from the Remotive remote-jobs API (no auth needed).

    Args:
        cfg: Pipeline configuration.

    Returns:
        List of deduplicated Job instances from Remotive.
    """
    seen: set[str] = set()
    jobs: list[Job] = []
    url: str = "https://remotive.com/api/remote-jobs?limit=50&sort=newest"

    try:
        logger.info("Remotive fetching jobs")
        resp: requests.Response = requests.get(url, timeout=30)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        items: list[dict[str, Any]] = data.get("jobs", [])
        for item in items:
            job: Job = _make_remotive_job(item, cfg)
            key: str = job.fingerprint
            if key not in seen:
                seen.add(key)
                jobs.append(job)
        logger.info("Remotive total jobs: %d", len(jobs))
    except Exception:
        logger.exception("Remotive scraper failed")

    return jobs


def run_all_scrapers(cfg: Config) -> ScraperResult:
    """Run all three scrapers and aggregate results.

    Args:
        cfg: Pipeline configuration.

    Returns:
        A ScraperResult with all jobs, source stats, and errors.
    """
    start: float = time.time()
    errors: list[str] = []
    all_jobs: list[Job] = []
    source_stats: dict[str, int] = {}

    scrapers: list[tuple[str, callable]] = [
        ("jsearch", scrape_jsearch),
        ("arbeitnow", scrape_arbeitnow),
        ("remotive", scrape_remotive),
    ]

    for name, scraper_fn in scrapers:
        try:
            jobs: list[Job] = scraper_fn(cfg)
            source_stats[name] = len(jobs)
            all_jobs.extend(jobs)
            logger.info("Source %s: %d jobs", name, len(jobs))
        except Exception:
            msg: str = f"Scraper {name} raised an unhandled exception"
            logger.exception(msg)
            errors.append(msg)
            source_stats[name] = 0

    elapsed: float = time.time() - start
    logger.info(
        "All scrapers done: %d total jobs in %.2fs",
        len(all_jobs),
        elapsed,
    )

    return ScraperResult(
        total_jobs=len(all_jobs),
        new_jobs=0,  # will be set after dedup
        jobs=all_jobs,
        source_stats=source_stats,
        errors=errors,
        elapsed_seconds=elapsed,
    )
