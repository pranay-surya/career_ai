"""
api/github.py
GitHub profile analyzer endpoint.
Uses the free GitHub REST API — no paid token required for public profiles.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
from database import get_db
from auth.utils import get_current_user
from services.github_analyzer import fetch_github_profile
import os

router = APIRouter()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional — raises rate limit to 5000/hr


@router.get("/analyze")
async def analyze_github(
    username: str = Query(..., min_length=1, max_length=39, description="GitHub username"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Analyze a GitHub profile.
    - Fetches profile info, repos, languages, stars
    - Calculates overall score & recruiter attractiveness score
    - Returns tech stack, top repos, improvement suggestions
    """
    username = username.strip().lstrip("@")  # handle "@username" input

    if not username:
        raise HTTPException(400, "Username cannot be empty.")

    try:
        result = await fetch_github_profile(username, token=GITHUB_TOKEN)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch GitHub data: {str(e)}")

    # Save github username and score to user profile
    current_user.github_username = username
    current_user.github_score    = result.get("overall_score", 0)
    db.commit()

    return result


@router.get("/profile")
def get_saved_github(
    current_user: models.User = Depends(get_current_user),
):
    """Return saved GitHub username and score for current user."""
    return {
        "github_username": current_user.github_username,
        "github_score":    current_user.github_score,
    }