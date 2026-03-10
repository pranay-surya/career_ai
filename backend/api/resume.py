"""
api/resume.py
Resume upload, parsing, ATS scoring, and skill gap analysis endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import models
from database import get_db
from auth.utils import get_current_user
from services.resume_parser      import extract_text
from services.skill_extractor    import (
    extract_skills, detect_missing_skills,
    recommend_roles, detect_experience_level,
)
from services.ats_scorer         import calculate_ats_score
from services.experience_extractor import extract_experience

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {"pdf", "doc", "docx", "txt"}


class ResumeAnalysisResponse(BaseModel):
    ats_score:        int
    skills_found:     list[str]
    missing_skills:   list[str]
    suggested_skills: list[str]
    suggestions:      list[str]
    ats_keywords:     list[str]
    experience:       list[dict]
    recommended_roles:list[str]
    years_experience: int
    experience_level: str
    score_breakdown:  dict


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload a resume file and get:
    - ATS Score (0-100)
    - Skills detected
    - Missing/suggested skills
    - Experience entries
    - Role recommendations
    - Improvement suggestions
    """
    # ── Validate file ──
    ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_TYPES)}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large. Maximum size is 5MB.")
    if len(file_bytes) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

    # ── Extract text ──
    try:
        resume_text = extract_text(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(422, f"Could not read resume file: {str(e)}")

    if len(resume_text.strip()) < 50:
        raise HTTPException(422, "Resume appears to be empty or could not be parsed. Please try a different file.")

    # ── Analyze ──
    skills_found    = extract_skills(resume_text)
    missing_skills  = detect_missing_skills(skills_found, current_user.career_goal)
    recommended_roles = recommend_roles(skills_found)
    years_exp, exp_level = detect_experience_level(skills_found)
    experience      = extract_experience(resume_text)
    ats_result      = calculate_ats_score(resume_text, skills_found)

    # ── Save to user profile ──
    current_user.resume_ats_score = ats_result["total_score"]
    current_user.resume_text      = resume_text[:5000]  # store first 5000 chars
    current_user.resume_filename  = file.filename
    db.commit()

    return ResumeAnalysisResponse(
        ats_score        = ats_result["total_score"],
        skills_found     = skills_found,
        missing_skills   = missing_skills,
        suggested_skills = missing_skills[:5],
        suggestions      = ats_result["suggestions"],
        ats_keywords     = ats_result["ats_keywords"],
        experience       = experience,
        recommended_roles= recommended_roles,
        years_experience = years_exp,
        experience_level = exp_level,
        score_breakdown  = ats_result["breakdown"],
    )


@router.get("/history")
def get_resume_history(
    current_user: models.User = Depends(get_current_user),
):
    """Get the last analyzed resume info for the current user."""
    return {
        "ats_score":       current_user.resume_ats_score,
        "resume_filename": current_user.resume_filename,
        "has_resume":      bool(current_user.resume_text),
    }