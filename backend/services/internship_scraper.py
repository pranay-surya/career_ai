"""
internship_scraper.py  —  Hybrid Real-Data Internship Aggregator
================================================================
Six sources, two tiers:

  TIER 1 — Free APIs (always reliable, no HTML parsing)
  ┌──────────────┬──────────────────────────────────────────────────┬────────────────────────┐
  │ Remotive     │ https://remotive.com/api/remote-jobs             │ No key — always on     │
  │ Adzuna       │ https://api.adzuna.com/v1/api/jobs/in/search/1   │ Free key @ adzuna.com  │
  │ Unstop JSON  │ https://unstop.com/api/public/opportunity/search │ No key — internal API  │
  └──────────────┴──────────────────────────────────────────────────┴────────────────────────┘

  TIER 2 — Web Scrapers (fallback if APIs blocked/quota exceeded)
  ┌──────────────┬──────────────────────────────────────────────────┬────────────────────────┐
  │ Internshala  │ https://internshala.com/internships/             │ BeautifulSoup, HTML    │
  │ Indeed India │ https://in.indeed.com/jobs                       │ BeautifulSoup, HTML    │
  │ Naukri       │ https://www.naukri.com/internship-jobs           │ BeautifulSoup, HTML    │
  └──────────────┴──────────────────────────────────────────────────┴────────────────────────┘

  TIER 3 — Curated fallback (always available, used when all else fails)

Caching strategy:
  - File-based JSON cache (survives server restarts)
  - Per-source TTL: APIs=2hr, Scrapers=1hr
  - Stored in: backend/cache/
  - Cache key: md5(source + normalised query + location)

Setup (.env):
  ADZUNA_APP_ID=your_app_id        # free at https://developer.adzuna.com/
  ADZUNA_API_KEY=your_api_key      # same signup
  # No other keys needed
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Cache directory ──────────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Per-source TTL (seconds)
TTL = {
    "remotive":     7200,   # 2 hr
    "adzuna":       7200,   # 2 hr
    "unstop":       1800,   # 30 min (updates frequently)
    "internshala":  3600,   # 1 hr
    "indeed":       7200,   # 2 hr
    "naukri":       3600,   # 1 hr
    "merged":       1800,   # 30 min for final combined result
}


def _cache_path(source: str, query: str, location: str = "") -> Path:
    key = hashlib.md5(f"{source}:{query.lower().strip()}:{location.lower().strip()}".encode()).hexdigest()
    return CACHE_DIR / f"{source}_{key}.json"


def _cache_read(source: str, query: str, location: str = "") -> Optional[list]:
    p = _cache_path(source, query, location)
    if not p.exists():
        return None
    try:
        with p.open() as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) < TTL.get(source, 3600):
            logger.debug(f"[{source}] Cache HIT — {len(data['items'])} items")
            return data["items"]
        p.unlink(missing_ok=True)
    except Exception:
        pass
    return None


def _cache_write(source: str, query: str, location: str, items: list) -> None:
    p = _cache_path(source, query, location)
    try:
        with p.open("w") as f:
            json.dump({"ts": time.time(), "source": source, "items": items}, f)
    except Exception as e:
        logger.debug(f"[{source}] Cache write failed: {e}")


# ── HTTP helpers ─────────────────────────────────────────────────────────────
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]
_ua_idx = 0

def _next_ua() -> str:
    global _ua_idx
    ua = UA_LIST[_ua_idx % len(UA_LIST)]
    _ua_idx += 1
    return ua

def _headers(extra: dict = None) -> dict:
    h = {
        "User-Agent": _next_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }
    if extra:
        h.update(extra)
    return h

TIMEOUT = httpx.Timeout(14.0, connect=7.0)


# ════════════════════════════════════════════════════════════════════════════
#  TIER 1-A  —  REMOTIVE (free JSON API, no key, always on)
# ════════════════════════════════════════════════════════════════════════════
async def fetch_remotive(query: str = "") -> list[dict]:
    """
    Remotive free public API. Zero setup. Covers remote-only tech roles.
    https://remotive.com/api/remote-jobs
    """
    SRC = "remotive"
    cached = _cache_read(SRC, query)
    if cached is not None:
        return cached

    category = _to_remotive_category(query)
    search   = query.replace(" ", "%20")
    url      = f"https://remotive.com/api/remote-jobs?category={category}&search={search}&limit=20"

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=_headers({"Accept": "application/json"})) as c:
        try:
            r = await c.get(url)
            r.raise_for_status()
            jobs = r.json().get("jobs", [])
            logger.info(f"[Remotive] HTTP {r.status_code} | {len(jobs)} jobs returned")
            for job in jobs:
                title   = job.get("title", "")
                company = job.get("company_name", "")
                if not title:
                    continue
                tags    = [t.strip() for t in (job.get("tags") or []) if t.strip()][:8]
                desc    = _strip_html(job.get("description", ""))[:300]
                pub     = job.get("publication_date", "")
                days_ago= _days_since(pub[:10]) if pub else 0
                results.append(_normalize({
                    "title":   title,
                    "company": company,
                    "location":    "Remote (Worldwide)",
                    "mode":        "remote",
                    "stipend":     job.get("salary") or "Competitive",
                    "stipend_value": 0,
                    "duration":    "Internship / Part-time",
                    "duration_months": 3,
                    "skills":      tags or _extract_skills(title + " " + desc),
                    "description": desc,
                    "apply_url":   job.get("url", "https://remotive.com"),
                    "company_logo": job.get("company_logo", ""),
                    "posted_days_ago": days_ago,
                    "source":      "Remotive",
                    "source_color": "#1ecc7a",
                }))
        except Exception as e:
            logger.warning(f"[Remotive] {e}")

    _cache_write(SRC, query, "", results)
    logger.info(f"[Remotive] {len(results)} listings for '{query}'")
    return results


def _to_remotive_category(q: str) -> str:
    q = q.lower()
    if any(w in q for w in ["data", "analytics", "science", "ml", "ai", "machine"]):
        return "data"
    if any(w in q for w in ["design", "ui", "ux", "figma"]):
        return "design"
    if any(w in q for w in ["devops", "cloud", "aws", "gcp", "sre", "infra"]):
        return "devops-sysadmin"
    if any(w in q for w in ["product", "manager", "pm"]):
        return "product"
    if any(w in q for w in ["mobile", "android", "ios", "flutter"]):
        return "mobile"
    return "software-dev"


# ════════════════════════════════════════════════════════════════════════════
#  TIER 1-B  —  ADZUNA API (free signup, 250 free calls/month)
#  Sign up → https://developer.adzuna.com/
#  Set ADZUNA_APP_ID + ADZUNA_API_KEY in .env
# ════════════════════════════════════════════════════════════════════════════
async def fetch_adzuna(query: str = "", location: str = "India") -> list[dict]:
    """
    Adzuna job search API — India endpoint.
    Best for finding real Indian internship listings with stipend data.
    """
    SRC = "adzuna"
    app_id  = os.getenv("ADZUNA_APP_ID", "")
    api_key = os.getenv("ADZUNA_API_KEY", "")
    if not app_id or not api_key:
        logger.info("[Adzuna] Skipped — set ADZUNA_APP_ID + ADZUNA_API_KEY in .env (free)")
        return []

    cached = _cache_read(SRC, query, location)
    if cached is not None:
        return cached

    # Country code
    cc = "in"
    if any(w in location.lower() for w in ["us", "usa", "america"]):
        cc = "us"
    elif any(w in location.lower() for w in ["uk", "london", "britain"]):
        cc = "gb"

    url = (
        f"https://api.adzuna.com/v1/api/jobs/{cc}/search/1"
        f"?app_id={app_id}&app_key={api_key}"
        f"&results_per_page=20"
        f"&what=intern+{query.replace(' ', '+')}"
        f"&content-type=application/json"
        f"&sort_by=date"
    )

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        try:
            r = await c.get(url)
            r.raise_for_status()
            jobs = r.json().get("results", [])
            logger.info(f"[Adzuna] HTTP {r.status_code} | {len(jobs)} results")
            for job in jobs:
                title   = job.get("title", "")
                company = (job.get("company") or {}).get("display_name", "")
                if not title:
                    continue
                loc_obj = job.get("location") or {}
                loc     = ", ".join((loc_obj.get("area") or ["India"])[-2:])
                desc    = _strip_html(job.get("description", ""))[:300]
                smin    = job.get("salary_min")
                smax    = job.get("salary_max")
                stipend, sval = _adzuna_stipend(smin, smax, job.get("salary_currency", "INR"))
                created = job.get("created", "")
                days_ago= _days_since(created[:10]) if created else 30
                results.append(_normalize({
                    "title":   title,
                    "company": company,
                    "location": loc,
                    "mode":     _detect_mode(loc),
                    "stipend":  stipend,
                    "stipend_value": sval,
                    "duration": "3-6 Months",
                    "duration_months": 4,
                    "skills":   _extract_skills(title + " " + desc),
                    "description": desc,
                    "apply_url": job.get("redirect_url", "https://adzuna.com"),
                    "company_logo": "",
                    "posted_days_ago": days_ago,
                    "source":   "Adzuna",
                    "source_color": "#f58220",
                }))
        except Exception as e:
            logger.warning(f"[Adzuna] {e}")

    _cache_write(SRC, query, location, results)
    logger.info(f"[Adzuna] {len(results)} listings for '{query}' / '{location}'")
    return results


def _adzuna_stipend(smin, smax, currency: str) -> tuple[str, int]:
    if not smin and not smax:
        return "As per company", 0
    lo, hi = int(smin or 0), int(smax or 0)
    sym = "₹" if currency == "INR" else "$"
    # Convert annual to monthly estimate
    if lo > 100000:
        lo, hi = lo // 12, hi // 12
    if lo and hi:
        return f"{sym}{lo:,}–{sym}{hi:,}/mo", lo
    return f"From {sym}{lo:,}/mo", lo


# ════════════════════════════════════════════════════════════════════════════
#  TIER 1-C  —  UNSTOP internal JSON API (no key needed)
#  Unstop uses Angular SSR but exposes an internal REST endpoint
#  that their own frontend calls — works without authentication
# ════════════════════════════════════════════════════════════════════════════
async def fetch_unstop(query: str = "") -> list[dict]:
    """
    Unstop internal search API — returns hackathons + internships.
    Filters to internship type only.
    https://unstop.com/api/public/opportunity/search-result
    """
    SRC = "unstop"
    cached = _cache_read(SRC, query)
    if cached is not None:
        return cached

    url = "https://unstop.com/api/public/opportunity/search-result"
    params = {
        "opportunity": "internship",
        "search":      query,
        "per_page":    "20",
        "page":        "1",
        "sort":        "latest",
    }
    hdrs = _headers({
        "Accept":   "application/json, text/plain, */*",
        "Origin":   "https://unstop.com",
        "Referer":  "https://unstop.com/internships",
    })

    results: list[dict] = []
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
        try:
            r = await c.get(url, params=params, headers=hdrs)
            r.raise_for_status()
            data = r.json()

            # Unstop API response shapes (verified against live API):
            # Shape 1: { data: { data: [...] } }          <- most common
            # Shape 2: { data: [...] }                     <- sometimes
            # Shape 3: { data: { data: { data: [...] } } } <- paginated
            raw = data.get("data", {})
            if isinstance(raw, list):
                items = raw
            elif isinstance(raw, dict):
                inner = raw.get("data", [])
                if isinstance(inner, list):
                    items = inner
                elif isinstance(inner, dict):
                    items = inner.get("data", [])
                else:
                    items = []
            else:
                items = []

            logger.info(f"[Unstop] Raw response keys: {list(data.keys())} | items found: {len(items)}")

            for item in items:
                title   = item.get("title", "") or item.get("name", "")
                org     = (item.get("organisation") or {}).get("name", "") or item.get("org_name", "")
                if not title:
                    continue

                # Stipend
                stip_min = item.get("stipend_min") or item.get("min_stipend", 0)
                stip_max = item.get("stipend_max") or item.get("max_stipend", 0)
                if stip_min or stip_max:
                    stipend = f"₹{int(stip_min):,}–₹{int(stip_max):,}/mo" if stip_min and stip_max else f"₹{int(stip_min or stip_max):,}/mo"
                    sval    = int(stip_min or 0)
                else:
                    stipend = "As per discussion"
                    sval    = 0

                # Skills
                skills_raw = item.get("skills") or item.get("filters") or []
                if isinstance(skills_raw, list):
                    skills = [
                        (s.get("label") or s.get("name") or s) if isinstance(s, dict) else s
                        for s in skills_raw
                    ][:8]
                else:
                    skills = _extract_skills(title)

                # Location
                loc_raw = item.get("location") or item.get("city") or "India"
                if isinstance(loc_raw, list):
                    loc = ", ".join(loc_raw[:2])
                else:
                    loc = str(loc_raw)
                if item.get("work_from_home") or "remote" in loc.lower():
                    loc = "Remote"

                # Duration
                dur_val = item.get("duration") or item.get("internship_duration", "")
                dur_unit= item.get("duration_type", "months")
                duration_str  = f"{dur_val} {dur_unit}".strip() if dur_val else "2-3 Months"
                duration_months = int(dur_val) if str(dur_val).isdigit() else 2

                # Apply URL
                slug     = item.get("seo_url") or item.get("url_title") or ""
                apply_url = f"https://unstop.com/{slug}" if slug else "https://unstop.com/internships"

                # Posted
                created  = item.get("start_date") or item.get("created_at") or ""
                days_ago = _days_since(created[:10]) if created and len(created) >= 10 else 0

                # Logo
                logo = item.get("logo") or (item.get("organisation") or {}).get("logo") or ""

                results.append(_normalize({
                    "title":           title,
                    "company":         org or "Company on Unstop",
                    "location":        loc,
                    "mode":            "remote" if loc == "Remote" else _detect_mode(loc),
                    "stipend":         stipend,
                    "stipend_value":   sval,
                    "duration":        duration_str,
                    "duration_months": duration_months,
                    "skills":          [str(s) for s in skills if s],
                    "description":     _strip_html(item.get("description", ""))[:300],
                    "apply_url":       apply_url,
                    "company_logo":    logo,
                    "posted_days_ago": days_ago,
                    "source":          "Unstop",
                    "source_color":    "#7b2ff7",
                }))
        except Exception as e:
            logger.warning(f"[Unstop] {e}")

    _cache_write(SRC, query, "", results)
    logger.info(f"[Unstop] {len(results)} listings for '{query}'")
    return results


# ════════════════════════════════════════════════════════════════════════════
#  TIER 2-A  —  INTERNSHALA (BeautifulSoup HTML scraper)
#  Internshala serves real static HTML — most reliable Indian scrape target
# ════════════════════════════════════════════════════════════════════════════
async def scrape_internshala(query: str = "") -> list[dict]:
    """
    Scrapes Internshala listing page.
    Tries keyword-specific URL first, falls back to general WFH listing.
    Anti-bot: Rotates UA, adds realistic headers, respects 1-hr cache.
    """
    SRC = "internshala"
    cached = _cache_read(SRC, query)
    if cached is not None:
        return cached

    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") if query else "computer-science"
    urls_to_try = [
        f"https://internshala.com/internships/{slug}-internship",
        "https://internshala.com/internships/work-from-home-internships",
        "https://internshala.com/internships/",
    ]

    results: list[dict] = []
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers=_headers({
            "Referer":       "https://www.google.com/",
            "Cache-Control": "no-cache",
            "Pragma":        "no-cache",
        })
    ) as c:
        for url in urls_to_try:
            try:
                await asyncio.sleep(0.5)    # polite delay
                r = await c.get(url)
                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "lxml")

                # Internshala card selectors — ordered most→least reliable
                cards = (
                    soup.select('[id^="internshipid_"]') or          # id-based (most stable)
                    soup.select(".individual_internship") or          # class-based
                    soup.select(".internship_meta") or               # older layout
                    soup.select(".internship-listing-card") or       # newer layout
                    soup.select("[class*='internship'][class*='card']")
                )

                logger.info(f"[Internshala] URL: {url} | HTTP {r.status_code} | cards found: {len(cards)}")

                for card in cards[:15]:
                    try:
                        t  = card.select_one(".job-internship-name, .profile a, h3 a, h3")
                        co = card.select_one(".company-name a, .link_display_like_text")
                        lo = card.select_one(".locations span, .location_link, .item_body.locations")
                        st = card.select_one(".stipend, .item_body.stipend")
                        du = card.select_one(".item_body.duration, .duration")
                        lk = card.select_one("a[href*='/internship/detail'], a[href*='internshala.com']")
                        # Fallback link from card id
                        card_id = card.get("id", "")
                        iid_match = re.search(r"internshipid_(\d+)", card_id)

                        title   = t.get_text(strip=True)  if t  else ""
                        company = co.get_text(strip=True) if co else ""
                        loc     = lo.get_text(strip=True) if lo else "India"
                        stipend = st.get_text(strip=True) if st else ""
                        dur_str = du.get_text(strip=True) if du else "2 Months"

                        href = ""
                        if lk and lk.get("href"):
                            href = lk["href"]
                        elif iid_match:
                            href = f"/internship/detail/id/{iid_match.group(1)}"
                        apply_url = (
                            f"https://internshala.com{href}" if href.startswith("/")
                            else href if href.startswith("http")
                            else "https://internshala.com/internships"
                        )

                        if not title or len(title) < 4:
                            continue

                        results.append(_normalize({
                            "title":           title,
                            "company":         company or "Company",
                            "location":        loc,
                            "mode":            _detect_mode(loc),
                            "stipend":         _clean_stipend(stipend),
                            "stipend_value":   _parse_rupee(stipend),
                            "duration":        dur_str,
                            "duration_months": _parse_duration_months(dur_str),
                            "skills":          _extract_skills(title),
                            "description":     f"{title} internship at {company}. Apply on Internshala.",
                            "apply_url":       apply_url,
                            "company_logo":    "",
                            "posted_days_ago": 0,
                            "source":          "Internshala",
                            "source_color":    "#ff4d4d",
                        }))
                    except Exception as e:
                        logger.debug(f"[Internshala] card parse: {e}")

                if results:
                    break  # success on this URL
            except Exception as e:
                logger.warning(f"[Internshala] {url}: {e}")

    _cache_write(SRC, query, "", results)
    logger.info(f"[Internshala] {len(results)} listings for '{query}'")
    return results


# ════════════════════════════════════════════════════════════════════════════
#  TIER 2-B  —  INDEED INDIA (BeautifulSoup HTML scraper)
#  in.indeed.com serves static HTML for basic job listings
# ════════════════════════════════════════════════════════════════════════════
async def scrape_indeed(query: str = "", location: str = "India") -> list[dict]:
    """
    Scrapes Indeed India public listing page.
    Uses static HTML endpoint — works without JavaScript execution.
    Anti-bot: Rotates UA, adds Referer, respects 2-hr cache.
    """
    SRC = "indeed"
    cached = _cache_read(SRC, query, location)
    if cached is not None:
        return cached

    q   = (query + " intern").replace(" ", "+")
    loc = location.replace(" ", "+")
    url = f"https://in.indeed.com/jobs?q={q}&l={loc}&sort=date&limit=15&fromage=30"

    results: list[dict] = []
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers=_headers({
            "Referer":       "https://www.google.com/",
            "Accept":        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })
    ) as c:
        try:
            await asyncio.sleep(1.0)    # polite delay
            r = await c.get(url)
            if r.status_code != 200:
                logger.warning(f"[Indeed] HTTP {r.status_code}")
                return []

            soup = BeautifulSoup(r.text, "lxml")

            cards = (
                soup.select(".job_seen_beacon") or
                soup.select(".resultContent") or
                soup.select('[data-testid="slider_item"]') or
                soup.select(".jobsearch-SerpJobCard")
            )
            logger.info(f"[Indeed] HTTP {r.status_code} | cards found: {len(cards)}")

            for card in cards[:15]:
                try:
                    t  = card.select_one("h2.jobTitle a, h2 a span, .jobTitle span")
                    co = card.select_one(".companyName, [data-testid='company-name']")
                    lo = card.select_one(".companyLocation, [data-testid='text-location']")
                    sa = card.select_one(".salary-snippet, .estimated-salary span, .salaryOnly")
                    lk = card.select_one("h2.jobTitle a, a.jcs-JobTitle")

                    title   = t.get_text(strip=True)  if t  else ""
                    company = co.get_text(strip=True) if co else ""
                    loc_str = lo.get_text(strip=True) if lo else location
                    salary  = sa.get_text(strip=True) if sa else ""
                    href    = lk.get("href", "") if lk else ""
                    apply_url = (
                        f"https://in.indeed.com{href}" if href.startswith("/")
                        else href if href.startswith("http")
                        else "https://in.indeed.com"
                    )

                    if not title or len(title) < 4:
                        continue

                    results.append(_normalize({
                        "title":           title,
                        "company":         company or "Company",
                        "location":        loc_str,
                        "mode":            _detect_mode(loc_str),
                        "stipend":         _clean_stipend(salary),
                        "stipend_value":   _parse_rupee(salary),
                        "duration":        "3-6 Months",
                        "duration_months": 4,
                        "skills":          _extract_skills(title),
                        "description":     f"{title} at {company}. Apply on Indeed India.",
                        "apply_url":       apply_url,
                        "company_logo":    "",
                        "posted_days_ago": 0,
                        "source":          "Indeed",
                        "source_color":    "#003a9b",
                    }))
                except Exception as e:
                    logger.debug(f"[Indeed] card: {e}")

        except Exception as e:
            logger.warning(f"[Indeed] {e}")

    _cache_write(SRC, query, location, results)
    logger.info(f"[Indeed] {len(results)} listings for '{query}'")
    return results


# ════════════════════════════════════════════════════════════════════════════
#  TIER 2-C  —  NAUKRI (BeautifulSoup HTML scraper)
#  India's #1 job board — serves static HTML listing pages
# ════════════════════════════════════════════════════════════════════════════
async def scrape_naukri(query: str = "") -> list[dict]:
    """
    Scrapes Naukri.com internship listing page.
    Naukri serves JSON-in-HTML embedded data — we parse both.
    """
    SRC = "naukri"
    cached = _cache_read(SRC, query)
    if cached is not None:
        return cached

    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") if query else "software"
    urls_to_try = [
        f"https://www.naukri.com/{slug}-internship-jobs",
        "https://www.naukri.com/internship-jobs",
    ]

    results: list[dict] = []
    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers=_headers({
            "Referer":  "https://www.google.com/",
            "appid":    "109",
            "systemid": "Naukri",
        })
    ) as c:
        for url in urls_to_try:
            try:
                await asyncio.sleep(0.5)
                r = await c.get(url)
                if r.status_code != 200:
                    continue

                soup = BeautifulSoup(r.text, "lxml")

                # Try JSON-LD structured data first (most reliable)
                ld_scripts = soup.find_all("script", type="application/ld+json")
                for script in ld_scripts:
                    try:
                        raw = json.loads(script.string or "")
                        items = raw if isinstance(raw, list) else [raw]
                        for item in items:
                            if item.get("@type") not in ("JobPosting",):
                                continue
                            title   = item.get("title", "")
                            company = (item.get("hiringOrganization") or {}).get("name", "")
                            loc_obj = (item.get("jobLocation") or {})
                            if isinstance(loc_obj, list):
                                loc_obj = loc_obj[0] if loc_obj else {}
                            loc = (loc_obj.get("address") or {}).get("addressLocality", "India")
                            salary_obj = item.get("baseSalary") or {}
                            val_obj    = salary_obj.get("value") or {}
                            smin = val_obj.get("minValue", 0)
                            smax = val_obj.get("maxValue", 0)
                            stipend, sval = _adzuna_stipend(smin, smax, "INR") if (smin or smax) else ("As per company", 0)
                            apply_url = item.get("url", url)
                            desc = _strip_html(item.get("description", ""))[:300]
                            if title and len(title) >= 4:
                                results.append(_normalize({
                                    "title":   title,
                                    "company": company or "Company",
                                    "location": loc,
                                    "mode":    _detect_mode(loc),
                                    "stipend": stipend,
                                    "stipend_value": sval,
                                    "duration": "3-6 Months",
                                    "duration_months": 4,
                                    "skills":  _extract_skills(title + " " + desc),
                                    "description": desc,
                                    "apply_url": apply_url,
                                    "company_logo": "",
                                    "posted_days_ago": 0,
                                    "source":  "Naukri",
                                    "source_color": "#ff7555",
                                }))
                    except Exception:
                        pass

                # Fallback: HTML card selectors
                if not results:
                    cards = (
                        soup.select(".cust-job-tuple") or
                        soup.select("article.jobTuple") or
                        soup.select(".srp-jobtuple-wrapper") or
                        soup.select("[class*='job-tuple']")
                    )
                    for card in cards[:15]:
                        try:
                            t  = card.select_one(".title, .jobTitle, h2 a")
                            co = card.select_one(".comp-name, .companyInfo a")
                            lo = card.select_one(".locWdth, .location-container span, .ni-job-tuple-icon-srp-loc")
                            sa = card.select_one(".salary, .package-container")
                            lk = card.select_one("a.title, a[href*='naukri.com/job-listings']")

                            title   = t.get_text(strip=True)  if t  else ""
                            company = co.get_text(strip=True) if co else ""
                            loc_str = lo.get_text(strip=True) if lo else "India"
                            salary  = sa.get_text(strip=True) if sa else ""
                            href    = lk.get("href", "") if lk else ""
                            apply_url = href if href.startswith("http") else f"https://www.naukri.com{href}"

                            if not title or len(title) < 4:
                                continue
                            results.append(_normalize({
                                "title":   title,
                                "company": company or "Company",
                                "location": loc_str,
                                "mode":    _detect_mode(loc_str),
                                "stipend": _clean_stipend(salary),
                                "stipend_value": _parse_rupee(salary),
                                "duration": "3-6 Months",
                                "duration_months": 4,
                                "skills":  _extract_skills(title),
                                "description": f"{title} at {company}. Apply on Naukri.",
                                "apply_url": apply_url,
                                "company_logo": "",
                                "posted_days_ago": 0,
                                "source":  "Naukri",
                                "source_color": "#ff7555",
                            }))
                        except Exception as e:
                            logger.debug(f"[Naukri] card: {e}")

                if results:
                    break
            except Exception as e:
                logger.warning(f"[Naukri] {url}: {e}")

    _cache_write(SRC, query, "", results)
    logger.info(f"[Naukri] {len(results)} listings for '{query}'")
    return results


# ════════════════════════════════════════════════════════════════════════════
#  MAIN AGGREGATOR
# ════════════════════════════════════════════════════════════════════════════
async def fetch_all_internships(
    query:    str = "software developer",
    location: str = "India",
) -> list[dict]:
    """
    Runs all 5 sources concurrently.
    Source priority order for deduplication:
      APIs first (Remotive > Adzuna > Unstop) then Scrapers (Internshala > Indeed > Naukri)
    Falls back to curated INTERNSHIP_DB if every source returns 0.
    """
    # Check merged cache first
    merged_cached = _cache_read("merged", query, location)
    if merged_cached:   # len > 0 check — empty [] must NOT bypass fallback
        logger.info(f"[Aggregator] Merged cache hit — {len(merged_cached)} items")
        return merged_cached
    elif merged_cached is not None:
        logger.info("[Aggregator] Merged cache was empty — re-fetching live sources")

    logger.info(f"[Aggregator] Fetching all sources for '{query}' / '{location}'")

    # Run everything concurrently
    api_tasks = [
        fetch_remotive(query),
        fetch_adzuna(query, location),
        fetch_unstop(query),
    ]
    scrape_tasks = [
        scrape_internshala(query),
        scrape_indeed(query, location),
        scrape_naukri(query),
    ]

    api_results     = await asyncio.gather(*api_tasks,     return_exceptions=True)
    scrape_results  = await asyncio.gather(*scrape_tasks,  return_exceptions=True)

    # Merge in priority order
    ordered: list[dict] = []
    for res in list(api_results) + list(scrape_results):
        if isinstance(res, list):
            ordered.extend(res)
        elif isinstance(res, Exception):
            logger.debug(f"[Aggregator] Source exception: {res}")

    # Deduplicate by normalised title+company
    seen:   set[str]   = set()
    unique: list[dict] = []
    for item in ordered:
        key = re.sub(r"\s+", " ", (item["title"] + "|" + item["company"]).lower().strip())
        if key not in seen and len(item.get("title", "")) > 3:
            seen.add(key)
            unique.append(item)

    if not unique:
        logger.warning("[Aggregator] All live sources returned 0 — using curated fallback")
        from services.internship_matcher import INTERNSHIP_DB
        unique = [dict(job) for job in INTERNSHIP_DB]
        for job in unique:
            job.setdefault("is_real", False)
            job.setdefault("source_color", "#aaa")
            job.setdefault("company_logo", "")
            job.setdefault("highlights", {})
    else:
        logger.info(f"[Aggregator] Total unique: {len(unique)} from live sources")

    # Sort by recency (0 posted_days_ago first)
    unique.sort(key=lambda x: x.get("posted_days_ago", 999))

    # Only cache non-empty results — never poison cache with []
    if unique:
        _cache_write("merged", query, location, unique)
    return unique


# ════════════════════════════════════════════════════════════════════════════
#  SHARED NORMALISER  —  every source returns this exact schema
# ════════════════════════════════════════════════════════════════════════════
def _normalize(raw: dict) -> dict:
    """Enforce consistent schema across all sources."""
    title   = raw.get("title", "").strip()
    company = raw.get("company", "").strip()
    return {
        # Identity
        "id":           f"{raw.get('source','?').lower()[:3]}_{hash(title+company) & 0xFFFFFF:06x}",
        "title":        title,
        "company":      company,
        "company_logo": raw.get("company_logo", ""),
        # Location
        "location":     raw.get("location", "India"),
        "mode":         raw.get("mode", "onsite"),
        # Compensation
        "stipend":      raw.get("stipend", "As per company"),
        "stipend_value":raw.get("stipend_value", 0),
        # Duration
        "duration":     raw.get("duration", "2-3 Months"),
        "duration_months": raw.get("duration_months", 2),
        # Classification
        "skills":       raw.get("skills", []),
        "level":        _infer_level(title, raw.get("description", "")),
        "domain":       _infer_domain(title + " " + raw.get("description", "")),
        # Content
        "description":  raw.get("description", ""),
        "highlights":   raw.get("highlights", {"qualifications": [], "responsibilities": [], "benefits": []}),
        # Source metadata
        "apply_url":    raw.get("apply_url", "#"),
        "source":       raw.get("source", "Unknown"),
        "source_color": raw.get("source_color", "#888"),
        "posted_days_ago": raw.get("posted_days_ago", 0),
        "is_real":      True,
    }


# ════════════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════
_SKILLS = [
    "Python","JavaScript","TypeScript","Java","C++","C#","Go","Rust","Kotlin","Swift","PHP","Ruby","R","Scala",
    "React","Vue","Angular","Next.js","HTML","CSS","Tailwind","Bootstrap","Redux","jQuery","SASS","Webpack",
    "Node.js","Django","FastAPI","Flask","Express","Spring","Laravel","GraphQL","REST API","Microservices",
    "SQL","PostgreSQL","MySQL","MongoDB","Redis","Firebase","SQLite","Elasticsearch","Cassandra",
    "AWS","Azure","GCP","Docker","Kubernetes","Terraform","CI/CD","Linux","Git","Jenkins","Ansible",
    "Machine Learning","Deep Learning","TensorFlow","PyTorch","Scikit-learn","Pandas","NumPy","NLP",
    "Computer Vision","LLM","Hugging Face","OpenCV",
    "Android","iOS","Flutter","React Native","Swift",
    "Figma","Jira","Agile","Scrum","Power BI","Tableau","Excel","Selenium","Playwright",
]

def _extract_skills(text: str) -> list[str]:
    tl = text.lower()
    return [s for s in _SKILLS if s.lower() in tl][:8]

def _strip_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", " ", re.sub(r"&[a-z]+;", " ", raw or "")).strip()

def _detect_mode(location: str) -> str:
    l = location.lower()
    if any(w in l for w in ["remote", "work from home", "wfh", "anywhere", "worldwide"]):
        return "remote"
    if "hybrid" in l:
        return "hybrid"
    return "onsite"

def _parse_duration_months(s: str) -> int:
    nums = re.findall(r"\d+", s or "")
    if not nums:
        return 2
    n = int(nums[0])
    return max(1, n // 4) if "week" in (s or "").lower() else n

def _clean_stipend(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw or raw.lower() in ("unpaid", "0", "-", "not disclosed"):
        return "Unpaid / PPO"
    if re.match(r"^\d", raw):
        return f"₹{raw}"
    return raw

def _parse_rupee(raw: str) -> int:
    """Extract first integer from stipend string for sorting."""
    nums = re.findall(r"\d[\d,]*", (raw or "").replace(",", ""))
    if not nums:
        return 0
    val = int(re.sub(r"\D", "", nums[0]))
    return val // 12 if val > 500000 else val  # convert annual to monthly

def _days_since(date_str: str) -> int:
    try:
        pub = datetime.strptime(date_str, "%Y-%m-%d")
        return max(0, (datetime.now() - pub).days)
    except Exception:
        return 0

def _infer_level(title: str, description: str) -> str:
    text = (title + " " + description).lower()
    if any(w in text for w in ["senior", "sr.", "lead", "3+ year", "5+ year", "experienced"]):
        return "advanced"
    if any(w in text for w in ["1-2 year", "2 year", "junior", "associate", "mid-level"]):
        return "intermediate"
    return "beginner"

def _infer_domain(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["frontend", "front-end", "react", "vue", "angular", "html", "css", "ui developer"]):
        return "frontend"
    if any(w in t for w in ["backend", "back-end", "api", "server", "django", "flask", "node", "spring"]):
        return "backend"
    if any(w in t for w in ["fullstack", "full stack", "full-stack", "mern", "mean"]):
        return "fullstack"
    if any(w in t for w in ["machine learning", "deep learning", "ml", "ai", "nlp", "data science", "llm"]):
        return "ai-ml"
    if any(w in t for w in ["data analyst", "analytics", "bi", "tableau", "power bi"]):
        return "data"
    if any(w in t for w in ["devops", "cloud", "aws", "azure", "gcp", "kubernetes", "docker", "sre"]):
        return "cloud-devops"
    if any(w in t for w in ["android", "ios", "mobile", "flutter", "react native"]):
        return "mobile"
    if any(w in t for w in ["cyber", "security", "ethical hack", "penetration", "infosec"]):
        return "security"
    if any(w in t for w in ["design", "ui/ux", "figma", "graphic", "product design"]):
        return "design"
    return "software"