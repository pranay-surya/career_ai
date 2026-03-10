"""
api/internships.py
──────────────────
Internship search endpoint with hybrid real-data aggregation.

Data flow:
  1. fetch_all_internships()  — 5 live sources (Remotive, Adzuna, Unstop, Internshala, Indeed/Naukri)
  2. _apply_filters()         — hard-filter by level / mode / duration / role
  3. _score_and_rank()        — skill-overlap match score (0–100) per listing
  4. Return sorted, paginated results
"""
import asyncio
import re
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query
import models
from auth.utils import get_current_user
from services.internship_scraper import fetch_all_internships

router = APIRouter()


# ── Skill-overlap + role match scoring ──────────────────────────────────────
def _score_match(job: dict, user_skills: list[str], role: str) -> int:
    score = 0

    # 50 pts — skill overlap
    req = [s.lower() for s in (job.get("skills") or [])]
    usr = [s.lower() for s in user_skills]
    if req:
        matched = sum(1 for s in req if s in usr)
        score  += int((matched / len(req)) * 50)
    else:
        score  += 20  # neutral when no skills listed

    # 30 pts — title/domain keyword match (keep ALL words including AI, ML)
    if role:
        role_words  = set(re.sub(r"[^a-z0-9]", " ", role.lower()).split())
        target_text = " ".join([
            job.get("title",""), job.get("domain",""),
            job.get("description",""), " ".join(job.get("skills",[]))
        ]).lower()
        overlap = sum(1 for w in role_words if w in target_text)
        score  += min(30, overlap * 8)

    # 20 pts — level match bonus
    if job.get("level") == "beginner":
        score += 10   # most users are beginners — mild boost
    return min(100, score)


def _apply_filters(items: list, level: str, mode: str, duration: str, role: str) -> list:
    out = []
    # Pre-process role into words — keep ALL words including short ones like AI, ML
    role_words = list(set(
        re.sub(r"[^a-z0-9]", " ", role.lower()).split()
    )) if role else []

    for item in items:
        if level and level != "all" and item.get("level") != level:
            continue
        if mode and mode != "all" and item.get("mode") != mode:
            continue
        if duration and duration != "all":
            months = item.get("duration_months", 0)
            if duration == "1-2" and not (1 <= months <= 2):  continue
            if duration == "3-6" and not (3 <= months <= 6):  continue
            if duration == "6+"  and months < 6:              continue
        if role_words:
            text = " ".join([
                item.get("title", ""),
                item.get("domain", ""),
                item.get("description", ""),
                " ".join(item.get("skills", [])),
            ]).lower()
            # Pass if ANY role word appears in the combined text
            if not any(w in text for w in role_words):
                continue
        out.append(item)
    return out


@router.get("/search")
async def search(
    role:     Optional[str]       = Query(None,      description="Job title / domain keywords"),
    level:    Optional[str]       = Query("all",     description="beginner | intermediate | advanced | all"),
    mode:     Optional[str]       = Query("all",     description="remote | onsite | hybrid | all"),
    duration: Optional[str]       = Query("all",     description="1-2 | 3-6 | 6+ | all"),
    skills:   Optional[list[str]] = Query(None,      description="User skills for match scoring"),
    location: Optional[str]       = Query("India",   description="City or country"),
    sort_by:  Optional[str]       = Query("match",   description="match | recent | stipend"),
    page:     Optional[int]       = Query(1,         description="Page number (20 per page)"),
    current_user: models.User     = Depends(get_current_user),
):
    """
    Returns real internships from 5 sources, scored + ranked by user skills.
    """
    user_skills = skills or []
    search_role = role or (current_user.career_goal or "software developer")
    search_loc  = location or "India"

    # Fetch from all sources (cached 30 min)
    raw = await fetch_all_internships(query=search_role, location=search_loc)

    # Filter
    filtered = _apply_filters(raw, level or "all", mode or "all", duration or "all", search_role)

    # Score
    for item in filtered:
        item["match_score"] = _score_match(item, user_skills, search_role)

    # Sort
    if sort_by == "recent":
        filtered.sort(key=lambda x: x.get("posted_days_ago", 999))
    elif sort_by == "stipend":
        filtered.sort(key=lambda x: x.get("stipend_value", 0), reverse=True)
    else:
        filtered.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    # Paginate
    page_size = 20
    total     = len(filtered)
    start     = (page - 1) * page_size
    paged     = filtered[start:start + page_size]

    # Source breakdown
    all_sources  = list({item["source"] for item in filtered})
    live_sources = list({item["source"] for item in filtered if item.get("is_real")})

    return {
        "total":        total,
        "page":         page,
        "page_size":    page_size,
        "total_pages":  max(1, -(-total // page_size)),
        "internships":  paged,
        "sources":      all_sources,
        "live_sources": live_sources,
        "is_live_data": any(item.get("is_real") for item in paged),
        "filters_applied": {
            "role": search_role, "level": level, "mode": mode,
            "duration": duration, "skills": user_skills, "location": search_loc,
        },
    }


@router.get("/sources")
async def get_sources():
    """Show which data sources are active and their status."""
    adzuna_active = bool(os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_API_KEY"))
    return {
        "sources": [
            {
                "id":         "remotive",
                "name":       "Remotive",
                "type":       "Free API",
                "covers":     "Remote tech jobs worldwide",
                "active":     True,
                "requires":   "Nothing — always on",
                "free_tier":  "Unlimited",
                "signup_url": None,
            },
            {
                "id":         "adzuna",
                "name":       "Adzuna",
                "type":       "Free API",
                "covers":     "India + global job boards aggregated",
                "active":     adzuna_active,
                "requires":   "ADZUNA_APP_ID + ADZUNA_API_KEY in .env",
                "free_tier":  "250 calls/month free",
                "signup_url": "https://developer.adzuna.com/",
            },
            {
                "id":         "unstop",
                "name":       "Unstop",
                "type":       "Internal JSON API",
                "covers":     "Internships + hackathons, India-focused",
                "active":     True,
                "requires":   "Nothing — public endpoint",
                "free_tier":  "Unlimited",
                "signup_url": None,
            },
            {
                "id":         "internshala",
                "name":       "Internshala",
                "type":       "Web Scraper",
                "covers":     "India's largest internship platform",
                "active":     True,
                "requires":   "Nothing — HTML scraper",
                "free_tier":  "1-hour cache, polite delays",
                "signup_url": None,
            },
            {
                "id":         "indeed",
                "name":       "Indeed India",
                "type":       "Web Scraper",
                "covers":     "Indeed India listings (in.indeed.com)",
                "active":     True,
                "requires":   "Nothing — HTML scraper",
                "free_tier":  "2-hour cache, polite delays",
                "signup_url": None,
            },
            {
                "id":         "naukri",
                "name":       "Naukri",
                "type":       "Web Scraper",
                "covers":     "India's #1 job board",
                "active":     True,
                "requires":   "Nothing — JSON-LD + HTML scraper",
                "free_tier":  "1-hour cache, polite delays",
                "signup_url": None,
            },
        ]
    }


@router.delete("/cache")
async def clear_cache(current_user: models.User = Depends(get_current_user)):
    """Admin: clear all cached internship JSON files to force fresh fetch."""
    cache_dir = Path(__file__).parent.parent / "cache"
    cleared = 0
    for f in cache_dir.glob("*.json"):
        try:
            f.unlink()
            cleared += 1
        except Exception:
            pass
    return {"cleared": cleared, "message": f"Cleared {cleared} cache files. Next search will fetch live data."}


@router.get("/levels")
def get_levels():
    return {
        "levels": [
            {"id": "beginner",     "label": "Beginner",     "desc": "No prior experience required.",        "icon": "seedling"},
            {"id": "intermediate", "label": "Intermediate", "desc": "Requires projects or coursework.",     "icon": "bolt"},
            {"id": "advanced",     "label": "Advanced",     "desc": "Prior internship or work experience.", "icon": "fire"},
        ]
    }


@router.get("/debug")
async def debug_sources(
    query:    str = "python developer",
    location: str = "India",
    current_user: models.User = Depends(get_current_user),
):
    """
    Runs each source individually and reports count + first result title.
    Use this to diagnose which sources are working.
    GET /internships/debug?query=python+developer
    """
    import time
    from services.internship_scraper import (
        fetch_remotive, fetch_adzuna, fetch_unstop,
        scrape_internshala, scrape_indeed, scrape_naukri
    )

    async def _run(name, coro):
        t0 = time.time()
        try:
            results = await coro
            elapsed = round(time.time() - t0, 2)
            return {
                "source":  name,
                "count":   len(results),
                "elapsed": elapsed,
                "status":  "ok" if results else "empty",
                "sample":  results[0]["title"] if results else None,
                "error":   None,
            }
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            return {
                "source":  name,
                "count":   0,
                "elapsed": elapsed,
                "status":  "error",
                "sample":  None,
                "error":   str(e),
            }

    results = await asyncio.gather(
        _run("remotive",    fetch_remotive(query)),
        _run("adzuna",      fetch_adzuna(query, location)),
        _run("unstop",      fetch_unstop(query)),
        _run("internshala", scrape_internshala(query)),
        _run("indeed",      scrape_indeed(query, location)),
        _run("naukri",      scrape_naukri(query)),
    )

    total = sum(r["count"] for r in results)
    return {
        "query":    query,
        "location": location,
        "total_live": total,
        "sources":  results,
        "tip": "Sources with count=0 and status=empty are being blocked or returning no HTML. Check logs for warnings.",
    }