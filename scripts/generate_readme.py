"""README generator – builds a professional project README.md."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models import Job

logger = logging.getLogger(__name__)


def _badges() -> str:
    """Return the README badge line."""
    return (
        "[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)]"
        "(https://www.python.org/) "
        "[![License](https://img.shields.io/badge/License-MIT-green.svg)]"
        "(./LICENSE) "
        "[![Auto Update](https://img.shields.io/badge/Auto-Update-brightgreen.svg)]"
        "(./.github/workflows/update-jobs.yml) "
        "[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]"
        "(./CONTRIBUTING.md)"
    )


def _category_breakdown(jobs: list[Job]) -> str:
    """Build a markdown table of category counts.

    Args:
        jobs: List of categorized Job instances.

    Returns:
        A markdown-formatted category breakdown table.
    """
    counts: dict[str, int] = {}
    total: int = len(jobs)
    for job in jobs:
        cat: str = job.category or "Other"
        counts[cat] = counts.get(cat, 0) + 1

    rows: list[str] = []
    rows.append("| Category | Count | % |")
    rows.append("|----------|-------|---|")
    for cat in sorted(counts, key=lambda c: counts[c], reverse=True):
        pct: str = f"{(counts[cat] / total * 100):.1f}%" if total else "0%"
        rows.append(f"| {cat} | {counts[cat]} | {pct} |")

    return "\n".join(rows)


def _top_jobs_table(jobs: list[Job], limit: int = 20) -> str:
    """Build a markdown table of the top N jobs.

    Args:
        jobs: List of Job instances.
        limit: Maximum number of rows.

    Returns:
        A markdown-formatted table.
    """
    rows: list[str] = []
    rows.append("| # | Title | Company | State | City | Area | Source |")
    rows.append("|---|-------|---------|-------|------|------|--------|")

    for i, job in enumerate(jobs[:limit], start=1):
        title: str = job.title[:45].replace("|", "\\|")
        company: str = job.company[:25].replace("|", "\\|")
        state: str = (job.state or "—").replace("|", "\\|")
        city: str = (job.city or "—").replace("|", "\\|")
        area: str = (job.area or "—").replace("|", "\\|")
        source: str = job.source.replace("|", "\\|")
        rows.append(
            f"| {i} | {title} | {company} | {state} | {city} | {area} | {source} |"
        )

    return "\n".join(rows)


def _current_time() -> str:
    """Return the current UTC time as an ISO string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def generate_readme(
    jobs: list[Job],
    posted_path: Path,
    output_path: Path,
    owner: str = "samkhankingo01-ctrl",
) -> None:
    """Generate a professional README.md for the jobs board.

    Args:
        jobs: List of current Job instances.
        posted_path: Path to posted-jobs.json for stats.
        output_path: Path to write README.md.
        owner: GitHub owner/repo prefix for links.
    """
    total: int = len(jobs)
    posted_total: int = 0
    if posted_path.exists():
        try:
            with open(posted_path, "r", encoding="utf-8") as fh:
                posted_data: dict[str, Any] = json.load(fh)
                posted_total = posted_data.get("totalCount", 0)
        except Exception:
            posted_total = total

    readme: str = f"""# 🇮🇳 India Jobs Board

{_badges()}

> Automatically aggregated job listings from multiple sources, updated every 6 hours.  
> Built for job seekers in India — curated, categorized, and ready to explore.

---

## 📊 Live Stats

- **Jobs in this update:** {total}
- **Total unique jobs tracked:** {posted_total}
- **Last updated:** {_current_time()}
- **Live board:** [jobsboard.samkhan.in](https://{owner}.github.io/jobs-repo/) (→ `docs/index.html`)

---

## 🔍 How It Works

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Scrapers   │ --> │  India-filter│ --> │  Captions +   │
│  (JSearch,  │     │  + Location  │     │  README +     │
│  Arbeitnow, │     │  split       │     │  HTML Board    │
│  Remotive)  │     │  + Dedup     │     │                │
└─────────────┘     └──────────────┘     └───────────────┘
```

1. **Scrape** – Pulls jobs from JSearch (RapidAPI `country=in`), Arbeitnow, Remotive.
2. **India filter** – Hard filter drops any job whose location is not Indian.
3. **Location split** – Each location is split into **State / City / Area**; the
   original string is preserved verbatim in `location_raw`. Locations are never
   replaced with just "India".
4. **Dedup** – SHA-256 fingerprinting (title + company + city + area).
5. **Categorize** – Keyword matching assigns jobs to 14 categories.
6. **Deliver** – Captions, README, and an interactive HTML board.

---

## 📍 Location Fields (per job)

Every job in `data/jobs-today.json` carries these location fields:

| Field | Description |
|-------|-------------|
| `state` | Indian State / UT (e.g. `Maharashtra`, `Delhi`, `Karnataka`) |
| `city` | City (e.g. `Mumbai`, `New Delhi`, `Bangalore`) |
| `area` | Locality / area, if available (e.g. `Dadar`, `Connaught Place`, `Whitefield`) |
| `location_raw` | Complete location EXACTLY as on the original posting |

Example JSON:
```json
{{
  "state": "Maharashtra",
  "city": "Mumbai",
  "area": "Dadar",
  "location_raw": "Dadar, Mumbai, Maharashtra"
}}
```

---

## 🎛️ Filtering

The live HTML board (`docs/index.html`) supports filtering by:

- **State** – all Indian states/UTs present in the data
- **City** – all cities present
- **Category** – 14 categories (IT, Government, Freshers, …)
- **Company** – all companies present
- **Source** – jsearch / arbeitnow / remotive
- **Free-text search** – title, company, area, city, description

---

## 🃏 What each job card shows

Every card on the board displays: **Company Logo**, **Company Name**,
**Job Title**, **State**, **City**, **Area** (if available), **Salary** (if
available), **Posted Date**, **Source**, and an **Apply** button that always
opens the **original job page** (`url` from the source).

---

## 📁 Directory Structure

```
├── config.py              # Central configuration dataclass
├── models.py              # Job, ScraperResult, CaptionBlock models
├── main.py                # Pipeline CLI entrypoint
├── scripts/
│   ├── scraper.py         # JSearch, Arbeitnow, Remotive scrapers
│   ├── dedup.py           # SHA-256 fingerprint deduplication
│   ├── categorizer.py     # Keyword-based job categorization
│   ├── format_captions.py # Instagram-ready caption generator
│   ├── generate_readme.py # README.md generator
│   └── generate_html_board.py  # Interactive HTML job board
├── data/
│   ├── posted-jobs.json   # Fingerprint history
│   └── jobs-today.json    # Latest scraped jobs
├── output/
│   └── captions.txt       # Formatted Instagram captions
├── docs/
│   └── index.html         # Live job board (GitHub Pages)
└── tests/                 # Pytest test suite
```

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/{owner}/jobs-repo.git
cd jobs-repo

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API key (required for JSearch)
export RAPIDAPI_KEY="your_key_here"

# 4. Run full pipeline
python main.py --run-all
```

---

## 🤖 Automation

The pipeline runs automatically via GitHub Actions every 6 hours (`0 */6 * * *`).

```yaml
# .github/workflows/update-jobs.yml
schedule: 0 */6 * * *
```

Results are committed back to the repository and deployed to GitHub Pages.

---

## 📝 Caption Format

Each job produces an Instagram-ready caption block:

```
🚨 Hiring Now!

🏢 Company: Example Corp
💼 Role: Software Engineer
📍 Location: Bangalore, Karnataka
💰 Salary: Not Disclosed
🔗 Apply: https://...

#jobs #indiajobs #hiring #jobsearch #careergoals #jobseekers #india #it
---
```

---

## 🏷️ Categories

| Category | Matches |
|----------|---------|
| IT | Software, Developer, Data Science, DevOps, Cloud, Security |
| Government | Sarkari, PSU, Civil Service, Railway, Defence |
| Freshers | Entry Level, Intern, Trainee, Campus |
| Remote | Work From Home, WFH, Virtual, Anywhere |
| Banking | Bank, Finance, Insurance, Accounting, CA |
| Engineering | Mechanical, Civil, Electrical, Manufacturing |
| Healthcare | Doctor, Nurse, Medical, Pharma, Hospital |
| Sales | Sales, BD, Account Manager, Retail |
| Marketing | Digital Marketing, SEO, Brand, Advertising |
| Startup | Startup, Founder, Early Stage, Entrepreneur |
| PSU | BHEL, ONGC, SAIL, NTPC, IOCL, GAIL |
| Part Time | Freelance, Contract, Temporary, Gig |
| Education | Teacher, Professor, Faculty, Research |
| HR | HR, Recruiter, Talent, Payroll |

---

## 📈 Category Breakdown

{_category_breakdown(jobs)}

---

## 🔥 Top 20 Listings

{_top_jobs_table(jobs)}

---

## 🛡️ License

MIT © {owner} – see [LICENSE](./LICENSE) for details.

---

*Made with ❤️ for the Indian job-seeking community. Star this repo if you find it useful!*
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(readme)

    logger.info("README written to %s (%d chars)", output_path, len(readme))
