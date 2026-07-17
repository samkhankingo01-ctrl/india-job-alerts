"""README generator for India Job Alerts.

Produces a comprehensive README.md with badges, documentation, stats,
and a live job table showing actual scraped jobs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import CATEGORY_MAP
from models import Job

logger = logging.getLogger(__name__)

# Marker strings for incremental stat updates
JOBS_STATS_START = "<!-- JOBS_STATS_START -->"
JOBS_STATS_END = "<!-- JOBS_STATS_END -->"

# ---------------------------------------------------------------------------
# Full README template (ASCII-safe for GitHub rendering)
# ---------------------------------------------------------------------------

README_TEMPLATE = """\
<p align="center">
  <img src="https://img.shields.io/badge/Jobs_Updated-{date}-brightgreen?style=for-the-badge" alt="Jobs Updated" />
  <img src="https://img.shields.io/badge/GitHub_Actions-Automated-blue?style=for-the-badge&logo=githubactions" alt="GitHub Actions" />
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python" alt="Python" />
</p>

<h1 align="center">India Job Alerts</h1>

<p align="center">
  <strong>Fully automated</strong> job aggregator for India &mdash; scraped every 6 hours, deduplicated, categorized, and formatted into Instagram-ready captions.
</p>

---

## How It Works

```
[1] Scrape (5 sources)  -->  [2] Dedup (SHA-256)  -->  [3] Categorize (14+ categories)
                                                      |
                                                      v
                              [4] Format captions  -->  [5] Update README + Commit
```

1. **Scrape** - Pulls the latest job postings from Naukri, Indeed, LinkedIn, FreeJobAlert, and SarkariResult
2. **Deduplicate** - SHA-256 fingerprints on `(title + company + location)` ensure no repeats
3. **Categorize** - Keyword matching assigns every job to one of 14+ categories
4. **Format** - Generates Instagram-ready markdown captions with emojis and hashtags
5. **Commit** - GitHub Actions auto-commits new jobs every 6 hours

---

## Directory Structure

```
india-job-alerts/
|-- .github/workflows/
|   |-- update-jobs.yml          # GitHub Actions - runs every 6 hours
|-- data/
|   |-- jobs-YYYY-MM-DD.json     # Daily scraped job database (ALL individual jobs)
|   |-- posted-jobs.json         # Deduplication ledger
|-- output/
|   |-- captions-YYYY-MM-DD.md   # Instagram-ready daily captions
|-- scripts/
|   |-- scraper.py               # Multi-source job scraper
|   |-- dedup.py                 # Fingerprint-based dedup engine
|   |-- categorizer.py           # Keyword category classifier
|   |-- format_captions.py       # Instagram caption generator
|   |-- generate_readme_jobs.py  # README stats updater
|-- tests/                       # Unit tests (pytest)
|-- config.py                    # Central configuration
|-- models.py                    # Data models (Job, ScraperResult, CaptionBlock)
|-- main.py                      # Orchestrator CLI
|-- requirements.txt
|-- pyproject.toml
|-- README.md
```

---

## Job Sources

| Source | Type | URL |
|--------|------|-----|
| Naukri | Private Sector | [naukri.com](https://www.naukri.com) |
| Indeed India | Private Sector | [in.indeed.com](https://in.indeed.com) |
| LinkedIn | Private Sector | [linkedin.com/jobs](https://www.linkedin.com/jobs) |
| FreeJobAlert | Government + Private | [freejobalert.com](https://www.freejobalert.com) |
| SarkariResult | Government | [sarkariresult.com](https://www.sarkariresult.com) |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/{owner}/india-job-alerts.git
cd india-job-alerts

# Install dependencies
pip install -r requirements.txt

# Run a full update
python main.py --run-all
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--run-all` | Scrape + Dedup + Categorize + Format + Update README |
| `--scrape-only` | Run only the scrapers |
| `--format-only` | Generate captions from existing data |
| `--readme-only` | Update README stats only |

---

## Automation

This repository uses **GitHub Actions** to run the full pipeline every **6 hours**.

```yaml
schedule:
  - cron: '0 */6 * * *'
```

You can also trigger it manually from the Actions tab using `workflow_dispatch`.

---

## Caption Format

Each job is rendered as an Instagram-ready caption:

```
Hiring Now!

Company: TechCorp India
Role: Senior Software Engineer
Location: Bangalore, Karnataka
Salary: Rs.18 LPA
Apply: https://example.com/job/12345

#jobs #indiajobs #hiring #ittech #techjobs #softwarejobs
---
```

**Government jobs** get a special header:

```
GOVERNMENT JOB ALERT!

Organization: UPSC
Role: Drug Inspector (450 Posts)
Location: All India
Salary: Pay Level-7 (Rs.44,900 - Rs.1,42,400)
Last Date: 15 Aug 2026
Apply: https://upsc.gov.in

#jobs #indiajobs #hiring #governmentjobs #sarkarinaukri
---
```

---

{stats_section}

---

## Contributing

Contributions are welcome!

- **Add a new scraper** - implement `scrape_<source>()` in `scripts/scraper.py`
- **Add categories** - extend `CATEGORY_MAP` in `config.py`
- **Improve captions** - tweak `build_caption()` in `scripts/format_captions.py`

Please ensure all tests pass before submitting:

```bash
pytest tests/ -v
```

---

## License

MIT - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built for Indian job seekers | Auto-updated every 6 hours</sub>
</p>
"""

STATS_TEMPLATE = """\
## Live Stats

> Last updated: **{last_updated}**

| Metric | Value |
|--------|-------|
| Total Unique Jobs | **{total_count}** |
| Categories Covered | **{category_count}** |
| Sources Monitored | **{source_count}** |
| Latest Captions | `output/{captions_file}` |

### Latest Jobs

{job_table}

### By Category

{category_table}
"""


def _load_posted_jobs(posted_jobs_path: str = "data/posted-jobs.json") -> Dict[str, Any]:
    """Load the posted-jobs ledger, returning defaults if unavailable."""
    default: Dict[str, Any] = {"fingerprints": [], "lastRun": None, "totalCount": 0, "sources": {}}
    try:
        with open(posted_jobs_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _build_job_table(jobs: List[Job], limit: int = 20) -> str:
    """Build a Markdown table of the latest jobs.

    Args:
        jobs: List of Job objects.
        limit: Maximum rows to include.

    Returns:
        Markdown table string.
    """
    if not jobs:
        return "| - | - | - | - |\n| *No jobs yet* | | | |\n"

    lines = ["| # | Role | Company | Location | Category | Source |",
             "|---|------|---------|----------|----------|--------|"]
    for i, job in enumerate(jobs[:limit], 1):
        title = job.title[:60] + ("..." if len(job.title) > 60 else "")
        company = job.company[:30] + ("..." if len(job.company) > 30 else "")
        lines.append(
            f"| {i} | {title} | {company} | {job.location} | {job.category} | {job.source} |"
        )
    return "\n".join(lines)


def _build_category_table(jobs: List[Job]) -> str:
    """Build a Markdown table of job counts by category."""
    counts: Dict[str, int] = {}
    for job in jobs:
        counts[job.category] = counts.get(job.category, 0) + 1

    if not counts:
        return "| *No jobs categorized yet* | |\n"

    sorted_cats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    lines = ["| Category | Count |", "|----------|-------|"]
    for cat, cnt in sorted_cats:
        lines.append(f"| {cat} | {cnt} |")
    return "\n".join(lines)


def generate_readme(
    jobs: List[Job],
    posted_jobs_path: str = "data/posted-jobs.json",
    output_path: str = "README.md",
    owner: str = "your-username",
) -> None:
    """Generate a complete README.md for the repository.

    Args:
        jobs: List of categorized Job objects for stats display.
        posted_jobs_path: Path to the posted-jobs ledger.
        output_path: Where to write README.md.
        owner: GitHub username for the clone URL placeholder.
    """
    ledger = _load_posted_jobs(posted_jobs_path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    captions_file = f"captions-{today}.md"

    total_categories = len(CATEGORY_MAP)
    source_count = 5

    job_table = _build_job_table(jobs)
    category_table = _build_category_table(jobs)

    stats_section = STATS_TEMPLATE.format(
        last_updated=datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
        total_count=ledger.get("totalCount", len(jobs)),
        category_count=total_categories,
        source_count=source_count,
        captions_file=captions_file,
        job_table=job_table,
        category_table=category_table,
    )

    full_readme = README_TEMPLATE.format(
        date=today,
        sources_table="",
        owner=owner,
        stats_section=stats_section,
    )

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(full_readme)
        logger.info("README.md generated at %s with %d jobs.", output_path, len(jobs))
    except OSError as exc:
        logger.error("Failed to write README.md: %s", exc)
