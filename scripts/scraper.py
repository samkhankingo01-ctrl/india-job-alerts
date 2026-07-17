"""Scraper module – fetches INDIA-ONLY jobs and preserves exact locations.

Sources:
  * JSearch (RapidAPI)  – primary. Supports ``country=in`` and returns
    ``job_city`` + ``job_state`` per posting (best location fidelity).
  * Arbeitnow           – secondary / fallback. Filtered to India only.
  * Remotive            – secondary / fallback. Filtered to India only.

Hard guarantee: any job whose location is NOT an Indian location is dropped.
Locations are split into ``state`` / ``city`` / ``area`` via the
``location_parser`` module, and the original raw string is kept in the Job so
nothing is ever replaced with just "India".
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

import requests

from config import Config
from models import Job, ScraperResult
from scripts.location_parser import (
    enrich_job_location,
    is_india_location,
    parse_location,
)

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _finalize_location(job: Job) -> Job:
    """Normalize a job's location in place into state/city/area fields.

    Also captures the original raw location string into ``location_raw`` so
    nothing is ever lost or replaced with just "India".
    """
    parsed = enrich_job_location(job)
    job.state = parsed.get("state", "")
    job.city = parsed.get("city", "")
    job.area = parsed.get("area", "")
    # Preserve the original posting location verbatim
    raw_parts = [p for p in (job.area, job.city, job.state) if p]
    if raw_parts and not job.location_raw:
        job.location_raw = ", ".join(raw_parts)
    return job


def _keep_india_only(jobs: list[Job]) -> list[Job]:
    """Drop any job whose location is not Indian.

    A job is kept if it has an explicit Indian state, an Indian city, OR the
    literal token "India"/"Bharat" in its raw location.
    """
    kept: list[Job] = []
    dropped: int = 0
    for job in jobs:
        combined = ", ".join(
            p for p in (job.area, job.city, job.state) if p
        )
        if is_india_location(combined):
            kept.append(job)
        else:
            dropped += 1
    if dropped:
        logger.info("India-filter: dropped %d non-Indian jobs.", dropped)
    return kept


def _normalize_posted_date(value: Any) -> str:
    """Best-effort normalization of a posted-date value to ISO ``YYYY-MM-DD``.

    Accepts epoch seconds/millis, ISO strings, and empty values.
    """
    if not value:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    # Epoch seconds / millis
    if s.isdigit():
        try:
            n = int(s)
            if n > 10_000_000_000:  # millis
                n //= 1000
            from datetime import datetime, timezone

            return datetime.fromtimestamp(n, tz=timezone.utc).strftime(
                "%Y-%m-%d"
            )
        except (ValueError, OSError):
            return s
    # ISO-ish string → take the date portion
    return s.split("T")[0][:10] if len(s) >= 10 else s


# ── JSearch ─────────────────────────────────────────────────────────────────
def _make_jsearch_job(item: dict[str, Any]) -> Job:
    """Convert a JSearch API response item into a Job model."""
    title = str(item.get("job_title", "") or "").strip()
    company = str(item.get("employer_name", "") or "").strip()
    city = str(item.get("job_city", "") or "").strip()
    state = str(item.get("job_state", "") or "").strip()
    salary = str(item.get("job_salary", "") or "")
    salary = "" if salary.lower() in ("none", "nan") else salary
    posted_raw = str(
        item.get("job_posted_at_datetime_utc", "") or ""
    ) or str(item.get("job_posted_at", "") or "")

    # Build the verbatim location from city + state (area not provided by API)
    loc_parts = [p for p in (city, state) if p]

    return Job(
        title=title,
        company=company,
        company_logo=str(item.get("employer_logo", "") or ""),
        city=city,
        state=state,
        area="",
        location_raw=", ".join(loc_parts),
        salary=salary,
        url=str(item.get("job_apply_link", "") or "")
        or str(item.get("job_google_link", "") or ""),
        source="jsearch",
        posted_date=_normalize_posted_date(posted_raw),
        posted_date_raw=str(posted_raw),
        description=str(item.get("job_description", "") or "")[:500],
        employment_type=str(item.get("job_employment_type", "") or ""),
        is_government=False,
        is_remote=str(item.get("work_from_home", "") or "").lower()
        in ("true", "1", "yes"),
        job_id=str(item.get("job_id", "") or ""),
    )


def scrape_jsearch(cfg: Config) -> list[Job]:
    """Scrape INDIA jobs from the JSearch RapidAPI endpoint.

    Uses ``country=in`` so only India postings are returned, then applies a
    secondary hard India-filter as a safety net. Tries multiple endpoint
    variants per query so a single 404/exception doesn't kill the whole run.
    """
    api_key: str = os.getenv("RAPIDAPI_KEY", "")
    if not api_key:
        logger.info("RAPIDAPI_KEY not set - skipping JSearch scraper.")
        return []

    headers: dict[str, str] = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    # Endpoint variants – JSearch rotates these on RapidAPI. We try each per
    # query instead of relying on a single up-front probe (which can flake).
    endpoints = [
        "https://jsearch.p.rapidapi.com/v1/search",
        "https://jsearch.p.rapidapi.com/search",
    ]

    seen: set[str] = set()
    jobs: list[Job] = []
    rate_limited = False

    for query in cfg.SEARCH_QUERIES:
        if rate_limited:
            break
        for endpoint in endpoints:
            url = (
                f"{endpoint}?query={requests.utils.quote(query)}"
                f"&country=in&page=1&num_pages=2"
            )
            try:
                logger.info("JSearch querying: %s (%s)", query, endpoint)
                resp = requests.get(url, headers=headers, timeout=30)
            except Exception:
                logger.debug("JSearch request error on %s", endpoint)
                continue  # try next endpoint variant

            if resp.status_code == 429:
                logger.warning("JSearch rate limited on %s.", endpoint)
                rate_limited = True
                break
            if resp.status_code == 404:
                logger.info("JSearch 404 on %s, trying next variant.", endpoint)
                continue  # try next endpoint variant
            if resp.status_code != 200:
                logger.warning(
                    "JSearch %s -> HTTP %d | body: %s",
                    endpoint,
                    resp.status_code,
                    resp.text[:300],
                )
                continue  # try next endpoint variant

            try:
                items = resp.json().get("data", []) or []
            except ValueError:
                logger.debug("JSearch non-JSON response on %s", endpoint)
                continue

            for item in items:
                job = _make_jsearch_job(item)
                _finalize_location(job)
                key = f"{job.title}|{job.company}|{job.city}".lower()
                if key not in seen and job.city:
                    seen.add(key)
                    jobs.append(job)
            break  # success on this query, move to next query
        time.sleep(random.uniform(0.8, 1.8))

    if not jobs:
        logger.warning(
            "JSearch: 0 jobs fetched (check RAPIDAPI_KEY validity / quota)."
        )
    jobs = _keep_india_only(jobs)
    logger.info("JSearch total unique India jobs: %d", len(jobs))
    return jobs


# ── Arbeitnow ───────────────────────────────────────────────────────────────
def _make_arbeitnow_job(item: dict[str, Any]) -> Job:
    """Convert an Arbeitnow API response item into a Job model."""
    title = str(item.get("title", "") or "").strip()
    company = str(item.get("company_name", "") or "").strip()
    location = str(item.get("location", "") or "")
    salary = str(item.get("salary", "") or "")
    if salary.lower() in ("none", "nan"):
        salary = ""
    posted_raw = str(item.get("created_at", "") or "")

    parsed = parse_location(location)
    return Job(
        title=title,
        company=company,
        company_logo=str(item.get("company_logo_url", "") or ""),
        city=parsed["city"],
        state=parsed["state"],
        area=parsed["area"],
        location_raw=parsed["location_raw"] or location,
        salary=salary,
        url=str(item.get("url", "") or ""),
        source="arbeitnow",
        posted_date=_normalize_posted_date(posted_raw),
        posted_date_raw=posted_raw,
        description=str(item.get("description", "") or "")[:500],
        employment_type=str(item.get("employment_type", "") or ""),
        is_government=False,
        is_remote=bool(item.get("remote", False)),
        job_id=str(item.get("slug", "") or ""),
    )


def scrape_arbeitnow(cfg: Config) -> list[Job]:
    """Scrape jobs from Arbeitnow, keeping ONLY India postings."""
    seen: set[str] = set()
    jobs: list[Job] = []

    for page in range(1, 16):
        url = (
            f"https://www.arbeitnow.com/api/job-board-api?"
            f"page={page}&per_page=50"
        )
        try:
            logger.info("Arbeitnow fetching page %d", page)
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            items = resp.json().get("data", [])
            for item in items:
                job = _make_arbeitnow_job(item)
                # Hard India filter BEFORE dedup
                loc = ", ".join(
                    p for p in (job.area, job.city, job.state) if p
                )
                if not is_india_location(loc):
                    continue
                _finalize_location(job)
                key = f"{job.title}|{job.company}|{job.city}".lower()
                if key not in seen and job.city:
                    seen.add(key)
                    jobs.append(job)
            if len(items) < 50:
                break
            time.sleep(random.uniform(1.0, 2.0))
        except Exception:
            logger.exception("Arbeitnow failed on page %d", page)

    logger.info("Arbeitnow total unique India jobs: %d", len(jobs))
    return jobs


# ── Remotive ────────────────────────────────────────────────────────────────
def _make_remotive_job(item: dict[str, Any]) -> Job:
    """Convert a Remotive API response item into a Job model."""
    title = str(item.get("title", "") or "").strip()
    company = str(item.get("company_name", "") or "").strip()
    location = str(item.get("candidate_required_location", "") or "")
    salary = str(item.get("salary", "") or "")
    if salary.lower() in ("none", "nan"):
        salary = ""
    posted_raw = str(item.get("publication_date", "") or "")

    parsed = parse_location(location)
    return Job(
        title=title,
        company=company,
        company_logo=str(item.get("company_logo_url", "") or ""),
        city=parsed["city"],
        state=parsed["state"],
        area=parsed["area"],
        location_raw=parsed["location_raw"] or location,
        salary=salary,
        url=str(item.get("url", "") or ""),
        source="remotive",
        posted_date=_normalize_posted_date(posted_raw),
        posted_date_raw=posted_raw,
        description=str(item.get("description", "") or "")[:500],
        employment_type="",
        is_government=False,
        is_remote=True,
        job_id=str(item.get("id", "") or ""),
    )


def scrape_remotive(cfg: Config) -> list[Job]:
    """Scrape jobs from Remotive, keeping ONLY India postings."""
    seen: set[str] = set()
    jobs: list[Job] = []
    url = "https://remotive.com/api/remote-jobs?limit=200&sort=newest"

    try:
        logger.info("Remotive fetching jobs")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        items = resp.json().get("jobs", [])
        for item in items:
            job = _make_remotive_job(item)
            loc = ", ".join(p for p in (job.area, job.city, job.state) if p)
            if not is_india_location(loc):
                continue
            _finalize_location(job)
            key = f"{job.title}|{job.company}|{job.city}".lower()
            if key not in seen and job.city:
                seen.add(key)
                jobs.append(job)
    except Exception:
        logger.exception("Remotive scraper failed")

    logger.info("Remotive total unique India jobs: %d", len(jobs))
    return jobs


# ── Orchestrator ────────────────────────────────────────────────────────────
def run_all_scrapers(cfg: Config) -> ScraperResult:
    """Run all India-only scrapers and aggregate results."""
    start = time.time()
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
            jobs = scraper_fn(cfg)
            source_stats[name] = len(jobs)
            all_jobs.extend(jobs)
            logger.info("Source %s: %d India jobs", name, len(jobs))
        except Exception:
            msg = f"Scraper {name} raised an unhandled exception"
            logger.exception(msg)
            errors.append(msg)
            source_stats[name] = 0

    elapsed = time.time() - start
    logger.info(
        "All scrapers done: %d India jobs in %.2fs", len(all_jobs), elapsed
    )

    return ScraperResult(
        total_jobs=len(all_jobs),
        new_jobs=0,
        jobs=all_jobs,
        source_stats=source_stats,
        errors=errors,
        elapsed_seconds=elapsed,
    )
