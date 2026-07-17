"""HTML job board generator – creates a self-contained interactive page.

Every job card displays the full required set of fields:
  Company Logo, Company Name, Job Title, State, City, Area, Salary,
  Posted Date, Source, and an Apply button that always opens the ORIGINAL job
  page (``job.url``).

The board supports filtering by: State, City, Category, Company (plus a free
text search and a Source filter).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from models import Job

logger = logging.getLogger(__name__)


def _escape_js(text: str) -> str:
    """Escape a string for safe embedding in a JavaScript string literal."""
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _svg_icon(icon: str) -> str:
    """Return an inline SVG icon HTML snippet."""
    icons: dict[str, str] = {
        "map-pin": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
            '<circle cx="12" cy="10" r="3"/></svg>'
        ),
        "briefcase": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>'
            '<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>'
        ),
        "money": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<line x1="12" y1="1" x2="12" y2="23"/>'
            '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'
        ),
        "link": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
            '<polyline points="15 3 21 3 21 9"/>'
            '<line x1="10" y1="14" x2="21" y2="3"/></svg>'
        ),
        "search": (
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<circle cx="11" cy="11" r="8"/>'
            '<line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
        ),
        "sun": (
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/>'
            '<line x1="12" y1="1" x2="12" y2="3"/>'
            '<line x1="12" y1="21" x2="12" y2="23"/>'
            '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>'
            '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
            '<line x1="1" y1="12" x2="3" y2="12"/>'
            '<line x1="21" y1="12" x2="23" y2="12"/>'
            '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>'
            '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
        ),
        "moon": (
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
        ),
        "calendar": (
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>'
            '<line x1="16" y1="2" x2="16" y2="6"/>'
            '<line x1="8" y1="2" x2="8" y2="6"/>'
            '<line x1="3" y1="10" x2="21" y2="10"/></svg>'
        ),
        "refresh": (
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2">'
            '<polyline points="23 4 23 10 17 10"/>'
            '<polyline points="1 20 1 14 7 14"/>'
            '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36'
            'A9 9 0 0 0 20.49 15"/></svg>'
        ),
    }
    return icons.get(icon, "")


def _category_color(category: str) -> str:
    colors: dict[str, str] = {
        "IT": "#3b82f6",
        "Government": "#f97316",
        "Freshers": "#22c55e",
        "Remote": "#8b5cf6",
        "Banking": "#eab308",
        "Engineering": "#06b6d4",
        "Healthcare": "#ef4444",
        "Sales": "#ec4899",
        "Marketing": "#f43f5e",
        "Startup": "#14b8a6",
        "PSU": "#64748b",
        "Part Time": "#a855f7",
        "Education": "#0ea5e9",
        "HR": "#d946ef",
        "Other": "#6b7280",
    }
    return colors.get(category, "#6b7280")


def _source_color(source: str) -> str:
    colors: dict[str, str] = {
        "jsearch": "#3b82f6",
        "arbeitnow": "#22c55e",
        "remotive": "#8b5cf6",
    }
    return colors.get(source, "#6b7280")


def _fmt_posted(value: str) -> str:
    """Human-friendly posted-date string (already ISO YYYY-MM-DD from scraper)."""
    return (value or "").strip() or "Recently"


def generate_html_board(jobs: list[Job], output_path: Path) -> None:
    """Generate a self-contained interactive HTML job board page.

    Required filter axes: State, City, Category, Company. Each card shows the
    full required field set and an Apply button linking to the original page.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total = len(jobs)

    # Distinct values for each filter dropdown
    states = sorted({j.state for j in jobs if j.state})
    cities = sorted({j.city for j in jobs if j.city})
    categories = sorted({(j.category or "Other") for j in jobs})
    companies = sorted({j.company for j in jobs if j.company})
    sources = sorted({j.source for j in jobs if j.source})

    def _count(getter) -> dict[str, int]:
        counts: dict[str, int] = {}
        for j in jobs:
            v = getter(j)
            if v:
                counts[v] = counts.get(v, 0) + 1
        return counts

    state_counts = _count(lambda j: j.state)
    city_counts = _count(lambda j: j.city)
    cat_counts = _count(lambda j: j.category or "Other")
    comp_counts = _count(lambda j: j.company)
    src_counts = _count(lambda j: j.source)

    # Serialize the FULL job data (incl. area, posted_date, location_raw) to
    # JSON and embed it. JSON is safe inside a <script type="application/json">
    # block, and we parse it client-side — no manual JS escaping needed.
    jobs_data = [
        {
            "logo": j.company_logo,
            "title": j.title,
            "company": j.company,
            "state": j.state,
            "city": j.city,
            "area": j.area,
            "locationRaw": j.location_raw,
            "salary": j.salary,
            "postedDate": _fmt_posted(j.posted_date),
            "url": j.url,  # ORIGINAL job page — Apply always opens this
            "source": j.source,
            "category": j.category or "Other",
            "empType": j.employment_type or "Full-time",
            "remote": bool(j.is_remote),
            "govt": bool(j.is_government),
            "description": (j.description or "")[:200],
        }
        for j in jobs
    ]
    jobs_json = json.dumps(jobs_data, ensure_ascii=False)

    def _options(values, counts, all_label):
        opts = [f'<option value="">{all_label}</option>']
        for v in values:
            opts.append(
                f'<option value="{_escape_attr(v)}">'
                f"{_escape_html(v)} ({counts.get(v, 0)})</option>"
            )
        return "\n".join(opts)

    state_options = _options(states, state_counts, "All States")
    city_options = _options(cities, city_counts, "All Cities")
    cat_options = _options(categories, cat_counts, "All Categories")
    company_options = _options(companies, comp_counts, "All Companies")
    src_options = _options(sources, src_counts, "All Sources")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🇮🇳 India Jobs Board</title>
<style>
:root {{
  --bg:#f8fafc; --surface:#ffffff; --surface-hover:#f1f5f9;
  --text:#0f172a; --text-secondary:#475569; --text-muted:#94a3b8;
  --border:#e2e8f0; --border-light:#f1f5f9;
  --accent:#3b82f6; --accent-hover:#2563eb; --accent-light:#dbeafe;
  --shadow-sm:0 1px 2px rgba(0,0,0,.05);
  --shadow-md:0 4px 6px -1px rgba(0,0,0,.1),0 2px 4px -2px rgba(0,0,0,.1);
  --radius:12px; --radius-sm:8px; --transition:.2s ease;
}}
[data-theme="dark"] {{
  --bg:#0f172a; --surface:#1e293b; --surface-hover:#334155;
  --text:#f1f5f9; --text-secondary:#cbd5e1; --text-muted:#64748b;
  --border:#334155; --border-light:#1e293b;
  --accent:#60a5fa; --accent-hover:#93bbfd; --accent-light:#1e3a5f;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  background:var(--bg); color:var(--text); line-height:1.6;
  min-height:100vh; transition:background var(--transition),color var(--transition);
}}
.header{{
  background:var(--surface); border-bottom:1px solid var(--border);
  padding:1.25rem 2rem; position:sticky; top:0; z-index:100;
  box-shadow:var(--shadow-sm); backdrop-filter:blur(12px);
  transition:background var(--transition),border var(--transition);
}}
.header-inner{{max-width:1400px;margin:0 auto;display:flex;align-items:center;
  justify-content:space-between;gap:1rem;flex-wrap:wrap;}}
.header-left{{display:flex;align-items:center;gap:.75rem;}}
.header-logo{{font-size:1.75rem;line-height:1;}}
.header-title{{font-size:1.35rem;font-weight:700;letter-spacing:-.02em;}}
.header-subtitle{{font-size:.8rem;color:var(--text-muted);}}
.header-actions{{display:flex;align-items:center;gap:.75rem;}}
.theme-toggle{{
  background:var(--surface-hover);border:1px solid var(--border);
  border-radius:50%;width:40px;height:40px;display:flex;
  align-items:center;justify-content:center;cursor:pointer;
  color:var(--text-secondary);transition:all var(--transition);
}}
.theme-toggle:hover{{background:var(--accent-light);color:var(--accent);border-color:var(--accent);}}
.job-count{{
  background:var(--accent);color:#fff;padding:.35rem .9rem;
  border-radius:100px;font-size:.85rem;font-weight:600;white-space:nowrap;
}}
.updated-badge{{font-size:.75rem;color:var(--text-muted);white-space:nowrap;}}
.filter-bar{{
  max-width:1400px;margin:1.5rem auto 1rem;padding:0 2rem;
  display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;
}}
.search-wrapper{{position:relative;flex:1;min-width:220px;}}
.search-wrapper svg{{position:absolute;left:12px;top:50%;
  transform:translateY(-50%);color:var(--text-muted);pointer-events:none;}}
.search-input{{
  width:100%;padding:.65rem 1rem .65rem 2.5rem;border:1px solid var(--border);
  border-radius:var(--radius-sm);background:var(--surface);color:var(--text);
  font-size:.9rem;transition:all var(--transition);outline:none;
}}
.search-input:focus{{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-light);}}
.filter-select{{
  padding:.65rem 2rem .65rem .75rem;border:1px solid var(--border);
  border-radius:var(--radius-sm);background:var(--surface);color:var(--text);
  font-size:.85rem;cursor:pointer;appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
  transition:all var(--transition);min-width:140px;
}}
.filter-select:focus{{border-color:var(--accent);outline:none;}}
.reset-btn{{
  padding:.65rem 1rem;border:1px solid var(--border);border-radius:var(--radius-sm);
  background:var(--surface);color:var(--text-secondary);font-size:.85rem;
  cursor:pointer;display:flex;align-items:center;gap:.4rem;
  transition:all var(--transition);white-space:nowrap;
}}
.reset-btn:hover{{background:var(--surface-hover);border-color:var(--accent);color:var(--accent);}}
.results-count{{font-size:.85rem;color:var(--text-muted);margin-left:auto;white-space:nowrap;}}
.card-grid{{
  max-width:1400px;margin:0 auto;padding:0 2rem 3rem;
  display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:1.25rem;
}}
.job-card{{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.25rem;transition:all var(--transition);display:flex;flex-direction:column;
  gap:.6rem;box-shadow:var(--shadow-sm);position:relative;overflow:hidden;
}}
.job-card::before{{
  content:'';position:absolute;top:0;left:0;width:100%;height:3px;
  background:var(--card-accent,var(--accent));opacity:0;transition:opacity var(--transition);
}}
.job-card:hover{{transform:translateY(-2px);box-shadow:var(--shadow-md);border-color:var(--accent);}}
.job-card:hover::before{{opacity:1;}}
.card-header{{display:flex;align-items:flex-start;gap:.75rem;}}
.company-logo{{
  width:48px;height:48px;border-radius:var(--radius-sm);object-fit:contain;
  background:var(--surface-hover);border:1px solid var(--border-light);
  flex-shrink:0;display:flex;align-items:center;justify-content:center;
  font-size:1.25rem;font-weight:700;color:var(--accent);overflow:hidden;
}}
.company-logo-img{{width:100%;height:100%;object-fit:contain;}}
.card-title{{
  font-size:1rem;font-weight:600;color:var(--text);line-height:1.35;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
.card-company{{font-size:.85rem;color:var(--text-secondary);margin-top:.15rem;}}
.card-meta{{display:flex;flex-wrap:wrap;gap:.4rem .9rem;align-items:center;
  font-size:.8rem;color:var(--text-muted);}}
.meta-item{{display:inline-flex;align-items:center;gap:.3rem;}}
.meta-item strong{{color:var(--text-secondary);font-weight:600;}}
.card-tags{{display:flex;flex-wrap:wrap;gap:.4rem;}}
.tag{{
  font-size:.7rem;font-weight:600;padding:.2rem .55rem;border-radius:100px;
  text-transform:uppercase;letter-spacing:.03em;
}}
.tag-category{{background:var(--accent-light);color:var(--accent);}}
.tag-source{{background:var(--surface-hover);color:var(--text-secondary);border:1px solid var(--border);}}
.tag-remote{{background:#dcfce7;color:#16a34a;}}
[data-theme="dark"] .tag-remote{{background:#052e16;color:#4ade80;}}
.tag-govt{{background:#fff7ed;color:#ea580c;}}
[data-theme="dark"] .tag-govt{{background:#431407;color:#fb923c;}}
.card-description{{
  font-size:.8rem;color:var(--text-muted);display:-webkit-box;
  -webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.5;
}}
.card-footer{{margin-top:auto;display:flex;align-items:center;
  justify-content:space-between;gap:.5rem;}}
.apply-btn{{
  display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;
  background:var(--accent);color:#fff;border:none;border-radius:var(--radius-sm);
  font-size:.85rem;font-weight:600;text-decoration:none;cursor:pointer;
  transition:all var(--transition);white-space:nowrap;
}}
.apply-btn:hover{{background:var(--accent-hover);transform:scale(1.02);}}
.empty-state{{grid-column:1/-1;text-align:center;padding:4rem 2rem;color:var(--text-muted);}}
.empty-state-icon{{font-size:3rem;margin-bottom:1rem;}}
.footer{{text-align:center;padding:2rem;color:var(--text-muted);
  font-size:.8rem;border-top:1px solid var(--border);}}
.footer a{{color:var(--accent);text-decoration:none;}}
.footer a:hover{{text-decoration:underline;}}
@media (max-width:768px){{
  .header{{padding:1rem;}}
  .header-title{{font-size:1.1rem;}}
  .card-grid{{grid-template-columns:1fr;padding:0 1rem 2rem;}}
  .filter-bar{{padding:0 1rem;flex-direction:column;}}
  .search-wrapper{{width:100%;}}
  .filter-select{{width:100%;}}
  .reset-btn{{width:100%;justify-content:center;}}
  .results-count{{margin-left:0;text-align:center;width:100%;}}
  .updated-badge{{display:none;}}
}}
</style>
</head>
<body>

<header class="header">
  <div class="header-inner">
    <div class="header-left">
      <span class="header-logo">🇮🇳</span>
      <div>
        <h1 class="header-title">India Jobs Board</h1>
        <p class="header-subtitle">Curated India job listings &mdash; exact State / City / Area</p>
      </div>
    </div>
    <div class="header-actions">
      <span class="updated-badge">Updated: {now_iso}</span>
      <span class="job-count" id="jobCount">{total} jobs</span>
      <button class="theme-toggle" id="themeToggle" aria-label="Toggle theme" title="Toggle dark mode">
        {_svg_icon("sun")}
      </button>
    </div>
  </div>
</header>

<div class="filter-bar">
  <div class="search-wrapper">
    {_svg_icon("search")}
    <input type="text" class="search-input" id="searchInput"
           placeholder="Search by title, company, area, city...">
  </div>
  <select class="filter-select" id="stateFilter">{state_options}</select>
  <select class="filter-select" id="cityFilter">{city_options}</select>
  <select class="filter-select" id="categoryFilter">{cat_options}</select>
  <select class="filter-select" id="companyFilter">{company_options}</select>
  <select class="filter-select" id="sourceFilter">{src_options}</select>
  <button class="reset-btn" id="resetBtn" title="Reset all filters">
    {_svg_icon("refresh")} Reset
  </button>
  <span class="results-count" id="resultsCount">Showing {total} of {total}</span>
</div>

<main class="card-grid" id="cardGrid"></main>

<footer class="footer">
  <p>🇮🇳 India Jobs Board &mdash; Auto-updated every 6 hours &mdash;
    Powered by <a href="https://github.com/samkhankingo01-ctrl/jobs-repo" target="_blank" rel="noopener">GitHub Actions</a></p>
</footer>

<script type="application/json" id="jobsData">__JOBS_JSON__</script>
<script>
(function() {{
"use strict";

var ALL_JOBS = JSON.parse(document.getElementById('jobsData').textContent);

var grid = document.getElementById('cardGrid');
var searchInput = document.getElementById('searchInput');
var stateFilter = document.getElementById('stateFilter');
var cityFilter = document.getElementById('cityFilter');
var categoryFilter = document.getElementById('categoryFilter');
var companyFilter = document.getElementById('companyFilter');
var sourceFilter = document.getElementById('sourceFilter');
var resetBtn = document.getElementById('resetBtn');
var resultsCount = document.getElementById('resultsCount');
var jobCount = document.getElementById('jobCount');
var themeToggle = document.getElementById('themeToggle');

var jobs = ALL_JOBS;

// ===== Theme =====
var SUN = {_svg_icon("sun")};
var MOON = {_svg_icon("moon")};
function setTheme(theme) {{
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('jobs-board-theme', theme);
  themeToggle.innerHTML = theme === 'dark' ? MOON : SUN;
}}
setTheme(localStorage.getItem('jobs-board-theme') || 'light');
themeToggle.addEventListener('click', function() {{
  var cur = document.documentElement.getAttribute('data-theme');
  setTheme(cur === 'dark' ? 'light' : 'dark');
}});

// ===== Icons =====
var ICON = {{
  pin: {_svg_icon("map-pin")},
  money: {_svg_icon("money")},
  cal: {_svg_icon("calendar")},
  brief: {_svg_icon("briefcase")},
  link: {_svg_icon("link")}
}};

function esc(s) {{
  s = s || '';
  return String(s).replace(/[&<>"']/g, function(c) {{
    return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];
  }});
}}

function companyInitials(company) {{
  if (!company) return '?';
  var parts = company.trim().split(/\\s+/);
  return (parts[0] ? parts[0][0] : '') + (parts[1] ? parts[1][0] : '');
}}

function catColor(cat) {{
  var m = {{IT:'#3b82f6',Government:'#f97316',Freshers:'#22c55e',Remote:'#8b5cf6',
    Banking:'#eab308',Engineering:'#06b6d4',Healthcare:'#ef4444',Sales:'#ec4899',
    Marketing:'#f43f5e',Startup:'#14b8a6',PSU:'#64748b','Part Time':'#a855f7',
    Education:'#0ea5e9',HR:'#d946ef',Other:'#6b7280'}};
  return m[cat] || '#6b7280';
}}
function srcColor(src) {{
  var m = {{jsearch:'#3b82f6',arbeitnow:'#22c55e',remotive:'#8b5cf6'}};
  return m[src] || '#6b7280';
}}

function renderCards() {{
  if (jobs.length === 0) {{
    grid.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div>'
      + '<h3 style="font-size:1.2rem;color:var(--text-secondary);margin-bottom:.5rem;">'
      + 'No jobs match your filters</h3>'
      + '<p>Try adjusting your search or filters</p></div>';
    resultsCount.textContent = '0 results';
    jobCount.textContent = '0 jobs';
    return;
  }}

  grid.innerHTML = jobs.map(function(job) {{
    var initials = companyInitials(job.company);
    var showLogo = job.logo && job.logo.length > 5;
    var cardStyle = '--card-accent:' + catColor(job.category);

    // Tags
    var tags = '<span class="tag tag-category" style="background:'
      + catColor(job.category) + '1a;color:' + catColor(job.category) + '">'
      + esc(job.category) + '</span>';
    tags += '<span class="tag tag-source" style="border-color:'
      + srcColor(job.source) + ';color:' + srcColor(job.source) + '">'
      + esc(job.source) + '</span>';
    if (job.remote) tags += '<span class="tag tag-remote">Remote</span>';
    if (job.govt) tags += '<span class="tag tag-govt">Govt</span>';

    // Logo
    var logoHtml = showLogo
      ? '<img class="company-logo-img" src="' + esc(job.logo) + '" alt="'
        + esc(job.company) + '" loading="lazy" onerror="this.parentElement.textContent=\''
        + esc(initials) + '\'">'
      : esc(initials);

    // Location lines — preserve exact State / City / Area
    var locLines = '';
    var locParts = [];
    if (job.area) locParts.push('<strong>Area:</strong> ' + esc(job.area));
    if (job.city) locParts.push('<strong>City:</strong> ' + esc(job.city));
    if (job.state) locParts.push('<strong>State:</strong> ' + esc(job.state));
    if (locParts.length) {{
      locLines = '<span class="meta-item">' + ICON.pin + ' '
        + locParts.join(' &middot; ') + '</span>';
    }} else if (job.locationRaw) {{
      locLines = '<span class="meta-item">' + ICON.pin + ' '
        + esc(job.locationRaw) + '</span>';
    }} else {{
      locLines = '<span class="meta-item">' + ICON.pin + ' India</span>';
    }}

    var salary = '<span class="meta-item">' + ICON.money + ' '
      + (job.salary ? esc(job.salary) : 'Not Disclosed') + '</span>';

    var posted = '<span class="meta-item">' + ICON.cal + ' '
      + esc(job.postedDate) + '</span>';

    return '<div class="job-card" style="' + cardStyle + '">'
      + '<div class="card-header">'
        + '<div class="company-logo">' + logoHtml + '</div>'
        + '<div style="min-width:0;">'
          + '<div class="card-title">' + esc(job.title) + '</div>'
          + '<div class="card-company">' + esc(job.company) + '</div>'
        + '</div>'
      + '</div>'
      + '<div class="card-meta">' + locLines + salary + posted + '</div>'
      + '<div class="card-tags">' + tags + '</div>'
      + (job.description ? '<div class="card-description">' + esc(job.description) + '</div>' : '')
      + '<div class="card-footer">'
        + '<span class="meta-item" style="font-size:.75rem">' + ICON.brief + ' '
          + esc(job.empType) + '</span>'
        // Apply button ALWAYS opens the ORIGINAL job page (job.url)
        + '<a class="apply-btn" href="' + esc(job.url) + '" target="_blank" rel="noopener noreferrer">'
          + ICON.link + ' Apply Now</a>'
      + '</div>'
    + '</div>';
  }}).join('');

  resultsCount.textContent = 'Showing ' + jobs.length + ' of ' + ALL_JOBS.length;
  jobCount.textContent = jobs.length + ' jobs';
}}

function filterJobs() {{
  var search = searchInput.value.toLowerCase().trim();
  var st = stateFilter.value;
  var ci = cityFilter.value;
  var ca = categoryFilter.value;
  var co = companyFilter.value;
  var so = sourceFilter.value;

  jobs = ALL_JOBS.filter(function(job) {{
    if (st && job.state !== st) return false;
    if (ci && job.city !== ci) return false;
    if (ca && (job.category || 'Other') !== ca) return false;
    if (co && job.company !== co) return false;
    if (so && job.source !== so) return false;
    if (search) {{
      var hay = (job.title + ' ' + job.company + ' ' + job.city + ' '
        + job.state + ' ' + job.area + ' ' + (job.description||'')).toLowerCase();
      if (hay.indexOf(search) === -1) return false;
    }}
    return true;
  }});
  renderCards();
}}

searchInput.addEventListener('input', filterJobs);
stateFilter.addEventListener('change', filterJobs);
cityFilter.addEventListener('change', filterJobs);
categoryFilter.addEventListener('change', filterJobs);
companyFilter.addEventListener('change', filterJobs);
sourceFilter.addEventListener('change', filterJobs);

resetBtn.addEventListener('click', function() {{
  searchInput.value = '';
  stateFilter.value = '';
  cityFilter.value = '';
  categoryFilter.value = '';
  companyFilter.value = '';
  sourceFilter.value = '';
  filterJobs();
}});

document.addEventListener('keydown', function(e) {{
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{
    e.preventDefault();
    searchInput.focus();
  }}
}});

renderCards();
}})();
</script>
</body>
</html>"""

    # Embed jobs JSON safely into the script tag. Escape the closing-tag
    # sequence so a stray "</script>" in job data can't break out of the block.
    safe_json = jobs_json.replace("</", "<\\/")
    html = html.replace("__JOBS_JSON__", safe_json, 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    logger.info(
        "HTML board written to %s (%d jobs, %d chars)",
        output_path,
        total,
        len(html),
    )


def _escape_html(text: str) -> str:
    """Escape text for safe HTML insertion."""
    s = str(text or "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _escape_attr(text: str) -> str:
    """Escape text for use inside an HTML attribute value."""
    return _escape_html(text)
