<p align="center">
  <img src="https://img.shields.io/badge/Jobs_Updated-2026-07-17-brightgreen?style=for-the-badge" alt="Jobs Updated" />
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

| Source | Type | URL |
|--------|------|-----|
| Naukri | Private Sector | [https://www.naukri.com](https://www.naukri.com) |
| Indeed India | Private Sector | [https://in.indeed.com](https://in.indeed.com) |
| LinkedIn | Private Sector | [https://www.linkedin.com](https://www.linkedin.com) |
| FreeJobAlert | Government + Private | [https://www.freejobalert.com](https://www.freejobalert.com) |
| SarkariResult | Government | [https://www.sarkariresult.com](https://www.sarkariresult.com) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/india-job-alerts.git
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

## 📈 Live Stats

> Last updated: **17 Jul 2026, 07:36 UTC**

| Metric | Value |
|--------|-------|
| 📦 Total Unique Jobs | **30** |
| 📂 Categories Covered | **14** |
| 🔍 Sources Monitored | **5** |
| 🆕 Latest Captions | `output/captions-2026-07-17.md` |

### 🔥 Top 10 Latest Jobs

| 💼 Role | 🏢 Company | 📂 Category |
|----------|------------|-------------|
| CHANGE THE WORLD | VDS INNOVATION | Other |
| Anything | Nash | Other |
| Register Now | CREW Resources Worldwide | Other |
| QA | VDS INNOVATION | IT |
| Tuple | Tuple | Other |
| Assistant - ARFF | Adani Airport Holdings Ltd | Other |
| Talent Sourcer | Red Sky | HR |
| Members Don't Join for Dollar Value | Steward | Other |
| Quality Control | Esteem | Other |
| 1838 | 4BUILD Group | Other |

### 📊 By Category

| 📂 Category | 📦 Count |
|-------------|-----------|
| Other | 19 |
| IT | 6 |
| Marketing | 2 |
| HR | 1 |
| Banking | 1 |
| Freshers | 1 |


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
