"""Scraper module for India Job Alerts.

Uses free APIs that work reliably on GitHub Actions:
1. Google Custom Search JSON API (100 queries/day FREE)
2. Remotive API (remote jobs, no auth needed)
3. Arbeitnow API (startup jobs, no auth needed)

All return structured job data with title, company, location, salary, and apply URL.
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from config import AppConfig, USER_AGENTS
from models import Job, ScraperResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def _make_fingerprint(title: str, company: str, location: str) -> str:
    raw = f"{title.strip().lower()}|{company.strip().lower()}|{location.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_salary(salary_raw: Optional[str]) -> str:
    if not salary_raw or not salary_raw.strip():
        return "Not disclosed"
    cleaned = " ".join(salary_raw.strip().split())
    return cleaned or "Not disclosed"


# ---------------------------------------------------------------------------
# Source 1: Google Custom Search JSON API (100/day FREE)
# ---------------------------------------------------------------------------

def scrape_google_cse(config: AppConfig) -> List[Job]:
    """Search for India jobs using Google Custom Search JSON API.

    Free tier: 100 queries/day. Needs GOOGLE_API_KEY and GOOGLE_CX
    environment variables (or GitHub Secrets).

    Args:
        config: Application configuration.

    Returns:
        List of Job objects from Google search results.
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    cx = os.getenv("GOOGLE_CX", "")

    if not api_key or not cx:
        logger.warning("[google_cse] GOOGLE_API_KEY or GOOGLE_CX not set. Skipping Google CSE.")
        logger.warning("[google_cse] Set these as GitHub Secrets to enable Google search.")
        return []

    logger.info("[google_cse] Starting Google Custom Search...")

    queries = [
        "jobs hiring India 2026 fresher",
        "latest job openings India software engineer",
        "government jobs India 2026 sarkari naukri recruitment",
        "IT jobs India 2026 developer hiring",
        "banking finance jobs India 2026",
        "remote work from home jobs India 2026",
        "healthcare medical jobs India 2026",
        "engineering jobs India mechanical electrical civil",
        "sales marketing jobs India 2026",
        "part time jobs India students 2026",
    ]

    all_jobs: List[Job] = []
    seen_urls: set = set()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for query in queries:
        try:
            url = (
                f"https://www.googleapis.com/customsearch/v1?"
                f"key={api_key}&cx={cx}&q={quote_plus(query)}&num=10"
            )
            resp = requests.get(
                url,
                headers={"User-Agent": _random_user_agent()},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            for item in items:
                link = item.get("link", "")
                if link in seen_urls or not link:
                    continue
                seen_urls.add(link)

                title = item.get("title", "")
                snippet = item.get("snippet", "")

                # Extract company name from snippet or title
                company = "See listing"
                company_match = re.search(
                    r"(?:at|@|\\b(?:Hiring|Recruitment)\b[:\\s]+)([A-Z][A-Za-z0-9&\\s]{2,30})",
                    title + " " + snippet,
                )
                if company_match:
                    company = company_match.group(1).strip()

                # Extract location
                location = "India"
                loc_match = re.search(
                    r"(Mumbai|Delhi|Bangalore|Bengaluru|Hyderabad|Chennai|Pune|"
                    r"Kolkata|Noida|Gurgaon|Gurugram|Jaipur|Ahmedabad|Lucknow|"
                    r"Chandigarh|Kochi|Coimbatore|Indore|Bhopal|Nagpur|"
                    r"Remote|Work from Home|WFH|All India|Pan India)",
                    snippet + " " + title,
                    re.IGNORECASE,
                )
                if loc_match:
                    location = loc_match.group(1).strip()

                # Extract salary
                salary = "Not disclosed"
                salary_match = re.search(
                    r"(?:Rs\.?|₹|INR)\s*[\d,.]+[\s-]*(?:Rs\.?|₹|INR)?\s*[\d,.]*\s*(?:LPA|Lacs|PA|per annum|month|year|/hr)?",
                    snippet,
                    re.IGNORECASE,
                )
                if salary_match:
                    salary = salary_match.group(0).strip()

                # Determine if government job
                is_govt = any(
                    kw in (title + " " + snippet).lower()
                    for kw in ["government", "govt", "sarkari", "upsc", "ssc", "ibps",
                               "railway", "defence", "army", "navy", "air force",
                               "public sector", "psu", "recruitment"]
                )

                job = Job(
                    title=title[:200],
                    company=company,
                    company_logo="",
                    location=location,
                    salary=salary,
                    url=link,
                    source="google_cse",
                    posted_date=today,
                    description=snippet[:300] if snippet else "",
                    is_government=is_govt,
                )
                job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
                all_jobs.append(job)

            time.sleep(1)  # Rate limit: 1 req/sec

        except Exception as exc:
            logger.error("[google_cse] Query failed: %s", exc)

    logger.info("[google_cse] Found %d job listings.", len(all_jobs))
    return all_jobs[:config.max_jobs_per_source]


# ---------------------------------------------------------------------------
# Source 2: Remotive API (FREE, no auth needed)
# ---------------------------------------------------------------------------

def scrape_remotive(config: AppConfig) -> List[Job]:
    """Fetch remote jobs from Remotive API (free, no auth).

    Filters for jobs mentioning India or worldwide remote roles.

    Args:
        config: Application configuration.

    Returns:
        List of Job objects.
    """
    logger.info("[remotive] Fetching remote jobs...")
    jobs: List[Job] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        url = "https://remotive.com/api/remote-jobs?limit=50&sort=newest"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("jobs", [])[:30]:
            title = item.get("title", "")
            company = item.get("company_name", "")
            location = item.get("candidate_required_location", "Remote")
            url = item.get("url", "")
            salary = item.get("salary", "")
            description = item.get("description", "")[:200]

            if not url:
                continue

            # Prioritize India-remote jobs but keep all remotes
            if "india" in (location + description + title).lower():
                location = location or "Remote (India)"
            else:
                location = location or "Remote (Worldwide)"

            job = Job(
                title=title,
                company=company,
                company_logo=item.get("company_logo_url", ""),
                location=location,
                salary=_parse_salary(salary),
                url=url,
                source="remotive",
                posted_date=today,
                description=description,
            )
            job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
            jobs.append(job)

    except Exception as exc:
        logger.error("[remotive] Fetch failed: %s", exc)

    logger.info("[remotive] Found %d remote jobs.", len(jobs))
    return jobs[:config.max_jobs_per_source]


# ---------------------------------------------------------------------------
# Source 3: Arbeitnow API (FREE, no auth needed)
# ---------------------------------------------------------------------------

def scrape_arbeitnow(config: AppConfig) -> List[Job]:
    """Fetch startup jobs from Arbeitnow API (free, no auth).

    Args:
        config: Application configuration.

    Returns:
        List of Job objects.
    """
    logger.info("[arbeitnow] Fetching startup jobs...")
    jobs: List[Job] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        url = "https://www.arbeitnow.com/api/job-board-api?page=1&per_page=50"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("data", [])[:30]:
            title = item.get("title", "")
            company = item.get("company_name", "")
            location = item.get("location", "")
            url = item.get("url", "")
            salary = item.get("salary", "")
            tags = item.get("tags", [])
            remote = item.get("remote", False)

            if not url:
                continue

            description_parts = tags[:3] if tags else []
            description = ", ".join(description_parts)

            if remote or "remote" in str(location).lower():
                location = "Remote" if not location else location

            job = Job(
                title=title,
                company=company,
                company_logo=item.get("company_logo_url", ""),
                location=location or "India",
                salary=_parse_salary(salary),
                url=url,
                source="arbeitnow",
                posted_date=today,
                description=description,
            )
            job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
            jobs.append(job)

    except Exception as exc:
        logger.error("[arbeitnow] Fetch failed: %s", exc)

    logger.info("[arbeitnow] Found %d startup jobs.", len(jobs))
    return jobs[:config.max_jobs_per_source]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_all_scrapers(config: AppConfig) -> ScraperResult:
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
        "google_cse": scrape_google_cse,
        "remotive": scrape_remotive,
        "arbeitnow": scrape_arbeitnow,
    }

    for name, scraper_fn in scrapers.items():
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
