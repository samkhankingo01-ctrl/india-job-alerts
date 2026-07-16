# 🇮🇳 India Job Alerts – Instagram Ready

> Automated job alerts from across India — scraped, deduplicated, and formatted for Instagram posting every 6 hours.

[![Jobs Updated](https://img.shields.io/badge/Jobs%20Updated-Daily-brightgreen)](https://github.com/khanzindagi/india-job-alerts/actions)
[![GitHub Actions](https://github.com/khanzindagi/india-job-alerts/actions/workflows/update-jobs.yml/badge.svg)](https://github.com/khanzindagi/india-job-alerts/actions)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🔄 How It Works

```
🌐 Search Sources  →  🧹 Deduplicate  →  🏷️ Categorize  →  📝 Captions  →  📊 Update README
     4 portals            SHA-256            25+ cats        Instagram        Live stats
```

| Step | Description |
|------|-------------|
| **1. Search** | Scrapes Naukri, Indeed, LinkedIn, FreeJobAlert + Govt portals every 6 hours |
| **2. Dedup** | SHA-256 fingerprint on (title + company + location) – no repeats |
| **3. Categorize** | Keyword-based classification into 25+ categories |
| **4. Format** | Clean emoji-rich Instagram captions with hashtags |
| **5. Commit** | Auto-commits & pushes new data back to GitHub |

---

## 📂 Directory Structure

```
india-job-alerts/
├── .github/
│   └── workflows/
│       └── update-jobs.yml           # GitHub Actions: every 6 hours
├── scripts/
│   ├── scraper.py                    # Multi-source web scraper
│   ├── dedup.py                      # SHA-256 deduplication engine
│   ├── categorizer.py                # Keyword-based job classifier
│   ├── format_captions.py            # Instagram caption generator
│   └── generate_readme_jobs.py       # Auto-updates README with stats
├── tests/
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_dedup.py
│   ├── test_categorizer.py
│   └── test_format_captions.py
├── data/
│   ├── jobs-today.json               # Today's scraped jobs (JSON)
│   └── posted-jobs.json              # Dedup fingerprint ledger
├── output/
│   └── captions-YYYY-MM-DD.md        # Instagram-ready post draft
├── config.py                         # Central configuration (dataclass)
├── models.py                         # Job, ScraperResult, CaptionBlock
├── main.py                           # CLI orchestrator
├── pyproject.toml                    # Project metadata + pytest config
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variable template
├── .gitignore
├── LICENSE                           # MIT
└── README.md
```

---

## 🏷️ Categories Covered

| Category | Examples |
|----------|----------|
| 💻 **IT / Tech** | Software Engineer, Full Stack, DevOps, Cloud, AI/ML |
| 🏛️ **Government** | UPSC, SSC, Railways, Defence, State & Central Govt |
| 🚀 **Startup** | Product, Growth, UI/UX, Backend at funded startups |
| 🎓 **Freshers** | Entry-level, Internships, Trainee, 0-3 years |
| 🏠 **Remote / WFH** | Remote software, remote marketing, remote HR |
| 🏦 **Banking / Finance** | Banking, Credit, Insurance, Finance Analyst |
| ⚙️ **Engineering** | Mechanical, Civil, Electrical, Manufacturing |
| 🏥 **Healthcare** | Nurse, Doctor, Medical Officer, Pharmacist |
| 📈 **Sales / Marketing** | BDM, Sales Executive, Digital Marketing |
| 📚 **Education / Research** | Professor, JRF, Research Fellow, Teaching |
| 👥 **HR / Recruitment** | HR, Talent Acquisition, Recruitment Coordinator |
| 🏭 **PSU** | HPCL, BHEL, NTPC, SAIL, Port Authority |
| ⏰ **Part Time / Student** | Content Writing, Tutoring, Data Entry, Internships |
| 🛡️ **Defence** | Army, Navy, Air Force, Paramilitary |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Git

### Installation
```bash
git clone https://github.com/khanzindagi/india-job-alerts.git
cd india-job-alerts
pip install -r requirements.txt
```

### Run Locally
```bash
# Full pipeline (scrape → dedup → format → readme)
python main.py --run-all

# Scrape only
python main.py --scrape-only

# Generate captions from existing data
python main.py --format-only

# Update README stats only
python main.py --readme-only

# Run tests
pytest tests/ -v
```

---

## ⚙️ Automation

The GitHub Actions workflow (`update-jobs.yml`) runs **every 6 hours** (`0 */6 * * *`) and can also be triggered manually via the `workflow_dispatch` button in the Actions tab.

### What the workflow does:
1. Checks out the repo
2. Sets up Python 3.12
3. Installs dependencies
4. Runs `python main.py --run-all`
5. Commits and pushes new data

---

## 📝 Caption Format

Every Instagram post follows this clean, emoji-rich format:

```
🚨 Hiring Now!

🏢 Company: Microsoft
💼 Role: Software Engineer
📍 Location: Bengaluru, Karnataka
💰 Salary: ₹15-30 LPA
🔗 Apply: https://apply-link.com

#jobs #indiajobs #hiring #itjobs #techjobs #softwareengineer
```

### Government Jobs get special treatment:
```
🏛️ GOVERNMENT JOB ALERT!

🏢 Organization: UPSC
💼 Role: Drug Inspector (450 Posts)
📍 Location: All India
💰 Pay Scale: Level-7 (₹44,900 – ₹1,42,400)
📅 Last Date: 2026-08-15
🔗 Apply: https://upsc.gov.in

#govtjobs #sarkarijobs #government #upsc #indiajobs
```

---

## 📊 Live Stats

<!-- JOBS_STATS_START -->

> **Last Updated:** 2026-07-17
> **Total Jobs Today:** 131

### By Category

| Category | Jobs |
|----------|------|
| IT | 21 |
| Government | 20+ |
| Healthcare | 12 |
| Education/Research | 11 |
| Finance | 9 |
| Startup | 9 |
| Engineering | 8 |
| Sales/Marketing | 7 |

<!-- JOBS_STATS_END -->

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-source`)
3. Add your scraper function in `scripts/scraper.py`
4. Register it in the `scraper_modules` list
5. Submit a PR

### Adding a New Job Source

```python
# In scripts/scraper.py
def scrape_newsource(config: AppConfig) -> list[Job]:
    """Scrape jobs from New Job Source."""
    # Your scraping logic here
    return jobs

# Register in main.py:
from scripts.scraper import scrape_newsource
```

---

## 📋 Requirements

- `requests` – HTTP requests with retry/backoff
- `beautifulsoup4` – HTML parsing
- `lxml` – Fast XML/HTML parser
- `pandas` – Data manipulation (optional, for analytics)

---

## 📄 License

MIT — Free to use, modify, and share. See [LICENSE](LICENSE).

---

<p align="center">
  <b>🇮🇳 Made for India's Job Seekers</b><br>
  <sub>Helping millions find their dream job, one post at a time.</sub>
</p>
