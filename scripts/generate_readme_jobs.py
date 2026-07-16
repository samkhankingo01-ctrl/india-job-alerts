"""README generator for India Job Alerts.

Produces a comprehensive README.md with badges, documentation, stats, and
a live job table. Uses marker comments for incremental stat updates.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import CATEGORY_MAP
from models import Job

logger = logging.getLogger(__name__)

# Marker strings used to locate the stats insertion region in README.md
JOBS_STATS_START = "<!-- JOBS_STATS_START -->"
JOBS_STATS_END = "<!-- JOBS_STATS_END -->"

# ---------------------------------------------------------------------------
# Full README template
# ---------------------------------------------------------------------------

README_TEMPLATE = """\
<p align="center">
  <img src="https://img.shields.io/badge/Jobs_Updated-{date}-brightgreen?style=for-the-badge" alt="Jobs Updated" />
  <img src="https://img.shields.io/badge/GitHub_Actions-Automated-blue?style=for-the-badge&logo=githubactions" alt="GitHub Actions" />
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python" alt="Python" />
</p>

# 🇮🇳 India Job Alerts

> 🔔 **Fully automated** job aggregator for India — scraped every 6 hours, deduplicated, categorized, and formatted into Instagram-ready captions.

---

## 📖 How It Works

```
┌─────────────┐     ┌───────────┐     ┌──────────────┐
│  Scrapers   │────▶│  Dedup    │────▶│  Categorizer │
│  5 sources  │     │ SHA-256   │     │ 14 categories│
└─────────────┘     └───────────┘     └──────────────┘
                                            │
                    ┌───────────────────────┘
                    ▼
┌──────────────────────────────────────────────────────┐
│                    Outputs                           │
│  • captions-YYYY-MM-DD.md (Instagram-ready)          │
│  • posted-jobs.json (dedup ledger)                   │
│  • README.md (live stats)                            │
└──────────────────────────────────────────────────────┘
```

1. **Scrape** — Pulls the latest job postings from Naukri, Indeed, LinkedIn, FreeJobAlert, and SarkariResult.
2. **Deduplicate** — SHA-256 fingerprints on `(title + company + location)` ensure no repeats.
3. **Categorize** — Keyword matching assigns every job to one of 14 categories.
4. **Format** — Generates Instagram-ready markdown captions with emojis and hashtags.
5. **Commit** — GitHub Actions auto-commits new jobs every 6 hours.

---

## 📂 Directory Structure

```
india-job-alerts/
├── .github/workflows/
│   └── update-jobs.yml          # GitHub Actions — runs every 6 hours
├── data/
│   └── posted-jobs.json         # Deduplication ledger
├── output/
│   └── captions-YYYY-MM-DD.md   # Daily caption output
├── scripts/
│   ├── scraper.py               # Multi-source job scraper
│   ├── dedup.py                 # Fingerprint-based dedup
│   ├── categorizer.py           # Keyword category classifier
│   ├── format_captions.py       # Instagram caption generator
│   └── generate_readme_jobs.py  # README stats updater
├── tests/
│   ├── test_scraper.py
│   ├── test_dedup.py
│   ├── test_categorizer.py
│   └── test_format_captions.py
├── config.py                    # Central configuration
├── models.py                    # Data models
├── main.py                      # Orchestrator CLI
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 📊 Job Categories

{sources_table}

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- pip

### Installation

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
| `--run-all` | Scrape → Dedup → Categorize → Format → Update README |
| `--scrape-only` | Run only the scrapers |
| `--format-only` | Generate captions from existing data |
| `--readme-only` | Update README stats only |

---

## 🤖 Automation

This repository uses **GitHub Actions** to run the full pipeline every **6 hours**.

```yaml
schedule:
  - cron: '0 */6 * * *'
```

You can also trigger it manually from the Actions tab using `workflow_dispatch`.

### Environment Variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_JOBS_PER_SOURCE` | `50` | Max jobs to scrape per source |
| `DEDUP_DAYS` | `7` | Days to retain fingerprints |
| `GITHUB_TOKEN` | – | For GitHub API calls (auto-set in Actions) |

Copy `.env.example` to `.env` to override defaults locally.

---

## 📸 Caption Format

Each job is rendered as:

```
🚨 Hiring Now!

🏢 Company: TechCorp India
💼 Role: Senior Software Engineer
📍 Location: Bangalore, Karnataka
💰 Salary: ₹18 LPA
🔗 Apply: https://example.com/job/12345

#jobs #indiajobs #hiring #ittech #techjobs #softwarejobs
---
```

**Government jobs** get a special header:

```
🏛️ GOVERNMENT JOB ALERT!

🏢 Company: Government of India
💼 Role: SSC CGL 2025
📍 Location: India
💰 Salary: Not disclosed
🔗 Apply: https://ssc.nic.in
📅 Last Date: 31 Aug 2025

#jobs #indiajobs #hiring #governmentjobs #sarkarinaukri
---
```

---

{stats_section}

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

- **Add a new scraper** — implement `scrape_<source>()` in `scripts/scraper.py`
- **Add categories** — extend `CATEGORY_MAP` in `config.py`
- **Improve captions** — tweak `build_caption()` in `scripts/format_captions.py`
- **Fix bugs** — open an issue or PR

Please ensure all tests pass before submitting:

```bash
pytest tests/ -v
```

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built with ❤️ for Indian job seekers | Auto-updated every 6 hours</sub>
</p>
"""

STATS_TEMPLATE = """\
## 📈 Live Stats

> Last updated: **{last_updated}**

| Metric | Value |
|--------|-------|
| 📦 Total Unique Jobs | **{total_count}** |
| 📂 Categories Covered | **{category_count}** |
| 🔍 Sources Monitored | **{source_count}** |
| 🆕 Latest Captions | `output/{captions_file}` |

### 🔥 Top 10 Latest Jobs

{job_table}

### 📊 By Category

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


def _build_job_table(jobs: List[Job], limit: int = 10) -> str:
    """Build a Markdown table of the top N jobs.

    Args:
        jobs: List of Job objects.
        limit: Maximum rows to include.

    Returns:
        Markdown table string.
    """
    if not jobs:
        return "| – | – | – |\n| *No jobs yet* | | |\n"

    lines = ["| 💼 Role | 🏢 Company | 📂 Category |", "|----------|------------|-------------|"]
    for job in jobs[:limit]:
        lines.append(f"| {job.title} | {job.company} | {job.category} |")
    return "\n".join(lines)


def _build_category_table(jobs: List[Job]) -> str:
    """Build a Markdown table of job counts by category.

    Args:
        jobs: List of Job objects.

    Returns:
        Markdown table string.
    """
    counts: Dict[str, int] = {}
    for job in jobs:
        counts[job.category] = counts.get(job.category, 0) + 1

    if not counts:
        return "| *No jobs categorized yet* | |\n"

    sorted_cats = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    lines = ["| 📂 Category | 📦 Count |", "|-------------|-----------|"]
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

    If an existing README.md has JOBS_STATS_START/END markers, only the
    stats section is replaced. Otherwise, a full new README is written.

    Args:
        jobs: List of categorized Job objects for stats.
        posted_jobs_path: Path to the posted-jobs ledger.
        output_path: Where to write README.md.
        owner: GitHub username for the clone URL placeholder.
    """
    ledger = _load_posted_jobs(posted_jobs_path)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    captions_file = f"captions-{today}.md"

    # Build sources table
    source_lines = ["| Source | Type | URL |", "|--------|------|-----|"]
    sources_info = [
        ("Naukri", "Private Sector", "https://www.naukri.com"),
        ("Indeed India", "Private Sector", "https://in.indeed.com"),
        ("LinkedIn", "Private Sector", "https://www.linkedin.com"),
        ("FreeJobAlert", "Government + Private", "https://www.freejobalert.com"),
        ("SarkariResult", "Government", "https://www.sarkariresult.com"),
    ]
    for name, stype, surl in sources_info:
        source_lines.append(f"| {name} | {stype} | [{surl}]({surl}) |")
    sources_table = "\n".join(source_lines)

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
        sources_table=sources_table,
        owner=owner,
        stats_section=stats_section,
    )

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(full_readme)
        logger.info("README.md generated at %s", output_path)
    except OSError as exc:
        logger.error("Failed to write README.md: %s", exc)
