# 🇮🇳 India Jobs Board

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/) [![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE) [![Auto Update](https://img.shields.io/badge/Auto-Update-brightgreen.svg)](./.github/workflows/update-jobs.yml) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

> Automatically aggregated job listings from multiple sources, updated every 6 hours.  
> Built for job seekers in India — curated, categorized, and ready to explore.

---

## 📊 Live Stats

- **Jobs in this update:** 7
- **Total unique jobs tracked:** 7
- **Last updated:** 2026-07-17 11:40:06 UTC
- **Live board:** [jobsboard.samkhan.in](https://samkhankingo01-ctrl.github.io/jobs-repo/) (→ `docs/index.html`)

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
{
  "state": "Maharashtra",
  "city": "Mumbai",
  "area": "Dadar",
  "location_raw": "Dadar, Mumbai, Maharashtra"
}
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
git clone https://github.com/samkhankingo01-ctrl/jobs-repo.git
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

| Category | Count | % |
|----------|-------|---|
| IT | 3 | 42.9% |
| Marketing | 1 | 14.3% |
| Government | 1 | 14.3% |
| HR | 1 | 14.3% |
| Engineering | 1 | 14.3% |

---

## 🔥 Top 20 Listings

| # | Title | Company | State | City | Area | Source |
|---|-------|---------|-------|------|------|--------|
| 1 | Software Engineer II | Flipkart | Karnataka | Bangalore | Whitefield | jsearch |
| 2 | Marketing Manager | Tata Motors | Maharashtra | Mumbai | Dadar | arbeitnow |
| 3 | Govt Bank PO | State Bank of India | Delhi | New Delhi | Connaught Place | jsearch |
| 4 | Python Developer (Remote) | Zoho | Tamil Nadu | Chennai | — | remotive |
| 5 | HR Business Partner | Infosys | Maharashtra | Pune | Hinjewadi | jsearch |
| 6 | Data Scientist | Swiggy | Karnataka | Bangalore | Koramangala | jsearch |
| 7 | Civil Engineer | L&T Construction | Telangana | Hyderabad | Gachibowli | arbeitnow |

---

## 🛡️ License

MIT © samkhankingo01-ctrl – see [LICENSE](./LICENSE) for details.

---

*Made with ❤️ for the Indian job-seeking community. Star this repo if you find it useful!*
