"""Scraper module for India Job Alerts.

Provides modular scraping functions for each job source. Every scraper returns
a list[Job] and is wrapped with retry logic, rate limiting, and logging.

Scraping strategy: Use Google search as a meta-source to discover latest India
jobs across all categories, then parse the results. This works reliably on
GitHub Actions (Ubuntu) without needing to handle individual site anti-bot
measures.
"""

from __future__ import annotations

import hashlib
import logging
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
    """Return a randomly selected User-Agent string."""
    return random.choice(USER_AGENTS)


def _make_fingerprint(title: str, company: str, location: str) -> str:
    """Generate a SHA-256 fingerprint from job identity fields."""
    raw = f"{title.strip().lower()}|{company.strip().lower()}|{location.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_request(
    url: str,
    config: AppConfig,
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
                allow_redirects=True,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            logger.warning("[%s] Attempt %d/%d failed for %s: %s",
                           source_name, attempt, max_retries, url[:80], exc)
            if attempt < max_retries:
                backoff = rate_limit * (2 ** attempt)
                time.sleep(backoff)
    return None


def _parse_salary_text(salary_str: Optional[str]) -> str:
    """Normalise a raw salary string into a display-friendly format."""
    if not salary_str or not salary_str.strip():
        return "Not disclosed"
    cleaned = salary_str.strip().replace("\n", " ").replace("\r", "")
    cleaned = " ".join(cleaned.split())
    return cleaned or "Not disclosed"


def _is_valid_job_url(url: str) -> bool:
    """Check if a URL looks like a real job listing."""
    if not url or len(url) < 20:
        return False
    job_domains = [
        "naukri.com", "indeed.com", "linkedin.com", "glassdoor.com",
        "freshersworld.com", "freejobalert.com", "sarkariresult.com",
        "careerjet.com", "monster.com", "shine.com", "jobrapido.com",
        "wellfound.com", "angel.co", "hirist.com", "cutshort.io",
        "foundit.com", "timesjobs.com", "govtjobsalerts.com",
        "upsc.gov.in", "ssc.nic.in", "ibps.in", "rbi.org.in",
        "onlinedocument", "notification", "recruitment",
    ]
    return any(d in url.lower() for d in job_domains)


# ---------------------------------------------------------------------------
# Google-based meta scraper (primary strategy for GitHub Actions)
# ---------------------------------------------------------------------------


def _scrape_google_jobs(
    query: str,
    config: AppConfig,
    source_label: str,
    is_government: bool = False,
) -> List[Job]:
    """Search Google for job listings and parse the result snippets.

    Args:
        query: Google search query string.
        config: Application configuration.
        source_label: Label for the source (e.g. 'naukri', 'indeed').
        is_government: Whether results are government jobs.

    Returns:
        List of Job objects.
    """
    logger.info("[%s] Searching: %s", source_label, query[:80])
    jobs: List[Job] = []

    search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=30&hl=en"
    headers = {
        "User-Agent": _random_user_agent(),
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = _safe_request(search_url, config, source_label, headers=headers, timeout=20)
    if resp is None:
        logger.error("[%s] No response from Google.", source_label)
        return jobs

    soup = BeautifulSoup(resp.text, "lxml")

    # Parse Google search result items
    for g in soup.select("div.g"):
        try:
            # Extract URL
            link_el = g.find("a", href=True)
            if not link_el:
                continue
            href = link_el.get("href", "")
            # Clean Google redirect URL
            url_match = re.search(r"(https?://[^&\s]+)", href)
            if url_match:
                url = url_match.group(1)
            else:
                continue

            # Extract title
            title_el = g.find("h3")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            # Extract snippet (may contain company, location, salary info)
            snippet_parts = []
            for span in g.find_all("span"):
                text = span.get_text(strip=True)
                if text and len(text) > 5:
                    snippet_parts.append(text)
            snippet = " ".join(snippet_parts[:3])

            # Try to extract company name from snippet
            company = "See listing"
            location = "India"
            salary = "Not disclosed"

            # Extract salary pattern
            salary_match = re.search(
                r"[\$₹]?\s*[\d,.]+[\s-]*[\$₹]?\s*[\d,.]*\s*(LPA|Lacs|per annum|PA|month|year|/hr)",
                snippet, re.IGNORECASE,
            )
            if salary_match:
                salary = salary_match.group(0).strip()

            # Extract location pattern
            loc_match = re.search(
                r"(Mumbai|Delhi|Bangalore|Bengaluru|Hyderabad|Chennai|Pune|Kolkata|"
                r"Noida|Gurgaon|Gurugram|Gurugram|Jaipur|Ahmedabad|Lucknow|"
                r"Chandigarh|Kochi|Coimbatore|Indore|Bhopal|Nagpur|Vizag|"
                r"Trivandrum|Thiruvananthapuram|Mysore|Mangalore|Surat|"
                r"Vadodara|Nashik|Aurangabad|Rajkot|Jamshedpur|Bhubaneswar|"
                r"Patna|Guwahati|Srinagar|Dehradun|Raipur|Ranchi|"
                r"Remote|Work from Home|WFH|All India|Pan India|"
                r"Andhra Pradesh|Karnataka|Kerala|Tamil Nadu|"
                r"Telangana|Maharashtra|Gujarat|Rajasthan|West Bengal|"
                r"Uttar Pradesh|Madhya Pradesh|Bihar|Haryana|Punjab|Odisha)",
                snippet, re.IGNORECASE,
            )
            if loc_match:
                location = loc_match.group(1).strip()

            job = Job(
                title=title,
                company=company,
                location=location,
                salary=salary,
                url=url,
                source=source_label,
                posted_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                description=snippet[:200] if snippet else "",
                is_government=is_government,
            )
            job.fingerprint = _make_fingerprint(job.title, job.company, job.location)
            jobs.append(job)

        except Exception as exc:
            logger.debug("[%s] Skipping result: %s", source_label, exc)

    logger.info("[%s] Found %d job listings.", source_label, len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Per-source scrapers (each uses Google meta-search for reliability)
# ---------------------------------------------------------------------------


def scrape_naukri(config: AppConfig) -> List[Job]:
    """Scrape latest Naukri.com job listings via Google search."""
    logger.info("[naukri] Starting scrape...")
    today = datetime.now(timezone.utc).strftime("%d %B %Y")

    queries = [
        f"site:naukri.com jobs India {today}",
        f"site:naukri.com hiring India 2026",
        f"site:naukri.com latest job openings",
    ]

    all_jobs: List[Job] = []
    seen_urls: set = set()

    for q in queries:
        jobs = _scrape_google_jobs(q, config, "naukri")
        for j in jobs:
            if j.url not in seen_urls:
                seen_urls.add(j.url)
                all_jobs.append(j)

    return all_jobs[: config.max_jobs_per_source]


def scrape_indeed(config: AppConfig) -> List[Job]:
    """Scrape latest Indeed India job listings via Google search."""
    logger.info("[indeed] Starting scrape...")

    queries = [
        "site:in.indeed.com jobs India 2026",
        "site:in.indeed.com hiring now India",
        "site:in.indeed.com part time jobs India",
    ]

    all_jobs: List[Job] = []
    seen_urls: set = set()

    for q in queries:
        jobs = _scrape_google_jobs(q, config, "indeed")
        for j in jobs:
            if j.url not in seen_urls:
                seen_urls.add(j.url)
                all_jobs.append(j)

    return all_jobs[: config.max_jobs_per_source]


def scrape_linkedin(config: AppConfig) -> List[Job]:
    """Scrape latest LinkedIn India job listings via Google search."""
    logger.info("[linkedin] Starting scrape...")

    queries = [
        "site:linkedin.com/jobs India 2026 hiring",
        "site:linkedin.com/jobs software engineer India",
        "site:linkedin.com/jobs remote India 2026",
    ]

    all_jobs: List[Job] = []
    seen_urls: set = set()

    for q in queries:
        jobs = _scrape_google_jobs(q, config, "linkedin")
        for j in jobs:
            if j.url not in seen_urls:
                seen_urls.add(j.url)
                all_jobs.append(j)

    return all_jobs[: config.max_jobs_per_source]


def scrape_freejobalert(config: AppConfig) -> List[Job]:
    """Scrape latest FreeJobAlert.com government + private job notifications."""
    logger.info("[freejobalert] Starting scrape...")

    queries = [
        "site:freejobalert.com latest government jobs 2026",
        "site:freejobalert.com recruitment notification 2026",
    ]

    all_jobs: List[Job] = []
    seen_urls: set = set()

    for q in queries:
        jobs = _scrape_google_jobs(q, config, "freejobalert", is_government=True)
        for j in jobs:
            if j.url not in seen_urls:
                seen_urls.add(j.url)
                all_jobs.append(j)

    return all_jobs[: config.max_jobs_per_source]


def scrape_govtportals(config: AppConfig) -> List[Job]:
    """Scrape government job postings from various portals."""
    logger.info("[govtportals] Starting scrape...")

    queries = [
        "site:sarkariresult.com latest job 2026",
        "site:govtjobsalerts.in government jobs India 2026",
        "sarkari naukri 2026 latest recruitment India",
        "government jobs India July 2026 hiring now",
    ]

    all_jobs: List[Job] = []
    seen_urls: set = set()

    for q in queries:
        jobs = _scrape_google_jobs(q, config, "govtportals", is_government=True)
        for j in jobs:
            if j.url not in seen_urls:
                seen_urls.add(j.url)
                all_jobs.append(j)

    return all_jobs[: config.max_jobs_per_source]


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
