"""Scraper module for India Job Alerts.

Provides modular scraping functions for each job source. Every scraper returns
a list[Job] and is wrapped with retry logic, rate limiting, and logging.
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from datetime import datetime, timezone
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from config import AppConfig, USER_AGENTS
from models import Job, ScraperResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _random_user_agent() -> str:
    """Return a randomly selected User-Agent string."""
    return random.choice(USER_AGENTS)


def _make_fingerprint(title: str, company: str, location: str) -> str:
    """Generate a SHA-256 fingerprint from job identity fields."""
    raw = f"{title.strip().lower()}|{company.strip().lower()}|{location.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_request(
    url: str,
    config: "AppConfig",
    source_name: str,
    headers: Optional[dict] = None,
    timeout: int = 30,
) -> Optional[requests.Response]:
    """Make a GET request with retry and backoff.

    Args:
        url: Target URL.
        config: AppConfig with rate-limit details.
        source_name: For logging context.
        headers: Optional custom headers dict.
        timeout: Request timeout in seconds.

    Returns:
        Response object or None if all retries exhausted.
    """
    source_cfg = next((s for s in config.sources if s.name == source_name), None)
    max_retries = source_cfg.max_retries if source_cfg else 3
    rate_limit = source_cfg.rate_limit_seconds if source_cfg else 2.0

    for attempt in range(1, max_retries + 1):
        try:
            time.sleep(rate_limit)
            resp = requests.get(
                url,
                headers=headers or {"User-Agent": _random_user_agent()},
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "[%s] Attempt %d/%d failed for %s: %s",
                source_name,
                attempt,
                max_retries,
                url,
                exc,
            )
            if attempt < max_retries:
                backoff = rate_limit * (2 ** attempt)
                time.sleep(backoff)
    return None


def _parse_salary_text(salary_str: Optional[str]) -> str:
    """Normalise a raw salary string into a display-friendly format."""
    if not salary_str or not salary_str.strip():
        return "Not disclosed"
    cleaned = salary_str.strip().replace("\n", " ").replace("\r", " ")
    # Collapse whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned or "Not disclosed"


# ---------------------------------------------------------------------------
# Per-source scrapers
# ---------------------------------------------------------------------------


def scrape_naukri(config: "AppConfig") -> List[Job]:
    """Scrape jobs from Naukri.com API.

    Naukri exposes a JSON API; we parse it directly rather than HTML.

    Args:
        config: Application configuration.

    Returns:
        List of Job objects scraped from Naukri.
    """
    logger.info("[naukri] Starting scrape...")
    jobs: List[Job] = []
    source_cfg = next(s for s in config.sources if s.name == "naukri")

    try:
        headers = {
            "User-Agent": _random_user_agent(),
            "Accept": "application/json",
            "appid": "109",
            "systemid": "109",
        }
        resp = _safe_request(source_cfg.search_url, config, "naukri", headers=headers)
        if resp is None:
            logger.error("[naukri] No response received.")
            return jobs

        data = resp.json()
        raw_jobs = data.get("jobDetails", [])[: config.max_jobs_per_source]

        for item in raw_jobs:
            try:
                title = item.get("title", "Unknown")
                company = item.get("companyName", "Unknown")
                city = item.get(
                    "placeholders",
                    [{"label": "location", "value": "India"}],
                )
                location = (
                    city[0].get("value", "India")
                    if isinstance(city, list) and city
                    else "India"
                )
                salary = item.get("salaryDetail", "Not disclosed")
                if isinstance(salary, dict):
                    salary = salary.get("label", "Not disclosed")

                job_id = item.get("jobId", "")
                url = f"https://www.naukri.com/job-listings-{job_id}" if job_id else ""

                job = Job(
                    title=title,
                    company=company,
                    location=location,
                    salary=_parse_salary_text(salary),
                    url=url,
                    source="naukri",
                    posted_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                )
                job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
                jobs.append(job)
            except Exception as exc:
                logger.debug("[naukri] Skipping malformed job entry: %s", exc)

        logger.info("[naukri] Scraped %d jobs.", len(jobs))
    except Exception as exc:
        logger.error("[naukri] Fatal error: %s", exc)

    return jobs


def scrape_indeed(config: "AppConfig") -> List[Job]:
    """Scrape jobs from Indeed India search results.

    Parses the HTML listing page for job cards.

    Args:
        config: Application configuration.

    Returns:
        List of Job objects scraped from Indeed.
    """
    logger.info("[indeed] Starting scrape...")
    jobs: List[Job] = []

    try:
        resp = _safe_request(config.sources[1].search_url, config, "indeed")
        if resp is None:
            logger.error("[indeed] No response received.")
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.find_all("div", class_="job_seen_beacon")[: config.max_jobs_per_source]

        for card in cards:
            try:
                title_el = card.find("h2", class_="jobTitle")
                title = title_el.get_text(strip=True) if title_el else "Unknown"

                company_el = card.find("span", class_="companyName")
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                location_el = card.find("div", class_="companyLocation")
                location = location_el.get_text(strip=True) if location_el else "India"

                salary_el = card.find("div", class_="salary-snippet-container")
                salary_text = salary_el.get_text(strip=True) if salary_el else "Not disclosed"

                link_el = title_el.find("a") if title_el else None
                jk = link_el.get("data-jk", "") if link_el else ""
                url = f"https://in.indeed.com/viewjob?jk={jk}" if jk else ""

                job = Job(
                    title=title,
                    company=company,
                    location=location,
                    salary=_parse_salary_text(salary_text),
                    url=url,
                    source="indeed",
                    posted_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                )
                job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
                jobs.append(job)
            except Exception as exc:
                logger.debug("[indeed] Skipping malformed card: %s", exc)

        logger.info("[indeed] Scraped %d jobs.", len(jobs))
    except Exception as exc:
        logger.error("[indeed] Fatal error: %s", exc)

    return jobs


def scrape_linkedin(config: "AppConfig") -> List[Job]:
    """Scrape jobs from LinkedIn guest job API.

    LinkedIn provides a guest-facing API; no authentication required for
    basic job post metadata.

    Args:
        config: Application configuration.

    Returns:
        List of Job objects scraped from LinkedIn.
    """
    logger.info("[linkedin] Starting scrape...")
    jobs: List[Job] = []
    source_cfg = next(s for s in config.sources if s.name == "linkedin")

    try:
        headers = {
            "User-Agent": _random_user_agent(),
            "Accept": "application/json",
        }
        collected = 0
        start = 0
        max_pages = (config.max_jobs_per_source // 25) + 1

        for _ in range(max_pages):
            if collected >= config.max_jobs_per_source:
                break
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=&location=India&start={start}"
            resp = _safe_request(url, config, "linkedin", headers=headers)
            if resp is None:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.find_all("div", class_="base-card")

            for card in cards:
                if collected >= config.max_jobs_per_source:
                    break
                try:
                    title_el = card.find("h3", class_="base-search-card__title")
                    title = title_el.get_text(strip=True) if title_el else "Unknown"

                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                    location_el = card.find("span", class_="job-search-card__location")
                    location = location_el.get_text(strip=True) if location_el else "India"

                    link_el = card.find("a", class_="base-card__full-link")
                    url_str = link_el.get("href", "").split("?")[0] if link_el else ""

                    job = Job(
                        title=title,
                        company=company,
                        location=location,
                        url=url_str,
                        source="linkedin",
                        posted_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    )
                    job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
                    jobs.append(job)
                    collected += 1
                except Exception as exc:
                    logger.debug("[linkedin] Skipping card: %s", exc)

            start += 25

        logger.info("[linkedin] Scraped %d jobs.", len(jobs))
    except Exception as exc:
        logger.error("[linkedin] Fatal error: %s", exc)

    return jobs


def scrape_freejobalert(config: "AppConfig") -> List[Job]:
    """Scrape jobs from FreeJobAlert.com latest notifications.

    Args:
        config: Application configuration.

    Returns:
        List of Job objects scraped from FreeJobAlert.
    """
    logger.info("[freejobalert] Starting scrape...")
    jobs: List[Job] = []

    try:
        resp = _safe_request(config.sources[3].search_url, config, "freejobalert")
        if resp is None:
            logger.error("[freejobalert] No response received.")
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")
        # FreeJobAlert lists notifications in list items
        items = soup.select("ul.latest-news li, .entry-content ul li")[: config.max_jobs_per_source]

        for item in items:
            try:
                link_el = item.find("a")
                if not link_el:
                    continue
                title = link_el.get_text(strip=True)
                url = link_el.get("href", "")

                # Extract date if present
                date_el = item.find("span", class_="date")
                posted_date = date_el.get_text(strip=True) if date_el else datetime.now(timezone.utc).strftime("%Y-%m-%d")

                job = Job(
                    title=title,
                    company="Various (see link)",
                    location="India",
                    url=url,
                    source="freejobalert",
                    posted_date=posted_date,
                    is_government=True,
                )
                job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
                jobs.append(job)
            except Exception as exc:
                logger.debug("[freejobalert] Skipping item: %s", exc)

        logger.info("[freejobalert] Scraped %d jobs.", len(jobs))
    except Exception as exc:
        logger.error("[freejobalert] Fatal error: %s", exc)

    return jobs


def scrape_govtportals(config: "AppConfig") -> List[Job]:
    """Scrape government job postings from SarkariResult.com.

    Args:
        config: Application configuration.

    Returns:
        List of Job objects scraped from government portals.
    """
    logger.info("[govtportals] Starting scrape...")
    jobs: List[Job] = []

    try:
        resp = _safe_request(config.sources[4].search_url, config, "govtportals")
        if resp is None:
            logger.error("[govtportals] No response received.")
            return jobs

        soup = BeautifulSoup(resp.text, "lxml")
        # SarkariResult lists jobs in tables and post lists
        rows = soup.select("table tbody tr, .post-list li, #post-list li")[: config.max_jobs_per_source]

        for row in rows:
            try:
                link_el = row.find("a")
                if not link_el:
                    continue
                title = link_el.get_text(strip=True)
                url = link_el.get("href", "")
                if not url.startswith("http"):
                    url = f"https://www.sarkariresult.com{url}"

                # Try to find last date
                cells = row.find_all("td")
                last_date = ""
                if len(cells) >= 2:
                    last_date = cells[-1].get_text(strip=True)

                job = Job(
                    title=title,
                    company="Government of India",
                    location="India",
                    url=url,
                    source="govtportals",
                    posted_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    last_date=last_date,
                    is_government=True,
                )
                job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
                jobs.append(job)
            except Exception as exc:
                logger.debug("[govtportals] Skipping row: %s", exc)

        logger.info("[govtportals] Scraped %d jobs.", len(jobs))
    except Exception as exc:
        logger.error("[govtportals] Fatal error: %s", exc)

    return jobs


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_all_scrapers(config: "AppConfig") -> ScraperResult:
    """Run every enabled scraper and aggregate results.

    Args:
        config: Application configuration.

    Returns:
        ScraperResult with all jobs, per-source stats, and errors.
    """
    start_time = time.monotonic()
    all_jobs: List[Job] = []
    source_stats: dict = {}
    errors: list = []

    scrapers = {
        "naukri": scrape_naukri,
        "indeed": scrape_indeed,
        "linkedin": scrape_linkedin,
        "freejobalert": scrape_freejobalert,
        "govtportals": scrape_govtportals,
    }

    for name, scraper_fn in scrapers.items():
        source_cfg = next((s for s in config.sources if s.name == name), None)
        if source_cfg and not source_cfg.enabled:
            logger.info("[%s] Skipped (disabled).", name)
            source_stats[name] = {"success": False, "scraped": 0, "error": "Disabled"}
            continue

        try:
            jobs = scraper_fn(config)
            all_jobs.extend(jobs)
            source_stats[name] = {"success": True, "scraped": len(jobs)}
        except Exception as exc:
            msg = f"[{name}] Scraper failed: {exc}"
            logger.error(msg)
            errors.append(msg)
            source_stats[name] = {"success": False, "scraped": 0, "error": str(exc)}

    elapsed = time.monotonic() - start_time
    logger.info(
        "Scraping complete: %d jobs from %d sources in %.1fs.",
        len(all_jobs),
        len(source_stats),
        elapsed,
    )

    return ScraperResult(
        total_jobs=len(all_jobs),
        jobs=all_jobs,
        source_stats=source_stats,
        errors=errors,
        elapsed_seconds=elapsed,
    )
