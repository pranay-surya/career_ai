"""
api/linkedin.py
LinkedIn profile analysis endpoints.
Supports: manual form input, PDF upload, pasted text.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import models
from database import get_db
from auth.utils import get_current_user
from services.linkedin_analyzer import analyze_linkedin_profile
from services.resume_parser import extract_text  # reuse PDF parser

router = APIRouter()


# ── Schemas ──
class LinkedInManualRequest(BaseModel):
    name:            Optional[str] = ""
    headline:        Optional[str] = ""
    location:        Optional[str] = ""
    connections:     Optional[int] = 0
    about:           Optional[str] = ""
    skills:          Optional[str] = ""
    recommendations: Optional[int] = 0
    experience:      Optional[str] = ""
    education:       Optional[str] = ""
    certifications:  Optional[str] = ""


class LinkedInTextRequest(BaseModel):
    text: str


# ── Endpoints ──

@router.post("/analyze")
def analyze_manual(
    payload: LinkedInManualRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Analyze LinkedIn profile from manual form input."""
    if not any([payload.name, payload.headline, payload.about, payload.experience]):
        raise HTTPException(400, "Please provide at least name, headline, or about section.")

    result = analyze_linkedin_profile(
        name            = payload.name or "",
        headline        = payload.headline or "",
        location        = payload.location or "",
        connections     = payload.connections or 0,
        about           = payload.about or "",
        skills          = payload.skills or "",
        recommendations = payload.recommendations or 0,
        experience      = payload.experience or "",
        education       = payload.education or "",
        certifications  = payload.certifications or "",
        career_goal     = current_user.career_goal or "",
    )

    # Save score to user profile
    current_user.linkedin_score = result["overall_score"]
    db.commit()

    return result


@router.post("/analyze-text")
def analyze_text(
    payload: LinkedInTextRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Analyze LinkedIn profile from pasted plain text."""
    text = payload.text.strip()
    if len(text) < 30:
        raise HTTPException(400, "Pasted text is too short. Please paste your full LinkedIn profile.")

    # Extract structured fields from raw pasted text
    parsed = _parse_raw_text(text)

    result = analyze_linkedin_profile(
        **parsed,
        career_goal = current_user.career_goal or "",
    )

    current_user.linkedin_score = result["overall_score"]
    db.commit()

    return result


@router.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Analyze LinkedIn profile from exported PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 5MB.")

    try:
        text = extract_text(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(422, f"Could not read PDF: {str(e)}")

    if len(text.strip()) < 30:
        raise HTTPException(422, "PDF appears empty or could not be parsed.")

    parsed = _parse_raw_text(text)

    result = analyze_linkedin_profile(
        **parsed,
        career_goal = current_user.career_goal or "",
    )

    current_user.linkedin_score = result["overall_score"]
    db.commit()

    return result


@router.get("/score")
def get_saved_score(current_user: models.User = Depends(get_current_user)):
    """Return saved LinkedIn score for current user."""
    return {"linkedin_score": current_user.linkedin_score}


# ── Raw text parser ──
def _parse_raw_text(text: str) -> dict:
    """
    Best-effort extraction of LinkedIn fields from raw pasted/PDF text.
    Returns a dict matching analyze_linkedin_profile parameters.
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    name = lines[0] if lines else ""

    # Headline: usually 2nd line and under 200 chars
    headline = ""
    if len(lines) > 1 and len(lines[1]) < 200:
        headline = lines[1]

    # Location: look for city/country pattern
    location = ""
    for line in lines[:10]:
        if re.search(r'(india|delhi|mumbai|bangalore|hyderabad|pune|chennai|kolkata|usa|uk|remote)', line, re.I):
            location = line
            break

    # Connections
    connections = 0
    conn_match = re.search(r'(\d+)\s*connections?', text, re.I)
    if conn_match:
        connections = int(conn_match.group(1))
    elif "500+" in text:
        connections = 500

    # About: text between "About" and next section keyword
    about = ""
    about_match = re.search(r'About\s*\n(.*?)(?=\n(?:Experience|Education|Skills|Licenses|Certifications|Languages))', text, re.S | re.I)
    if about_match:
        about = about_match.group(1).strip()

    # Experience
    exp = ""
    exp_match = re.search(r'Experience\s*\n(.*?)(?=\n(?:Education|Skills|Licenses|Certifications|Languages|Interests))', text, re.S | re.I)
    if exp_match:
        exp = exp_match.group(1).strip()

    # Education
    edu = ""
    edu_match = re.search(r'Education\s*\n(.*?)(?=\n(?:Skills|Licenses|Certifications|Languages|Interests|Experience))', text, re.S | re.I)
    if edu_match:
        edu = edu_match.group(1).strip()

    # Skills
    skills_text = ""
    skills_match = re.search(r'Skills\s*\n(.*?)(?=\n(?:Certifications|Languages|Interests|Recommendations|Education))', text, re.S | re.I)
    if skills_match:
        skills_text = skills_match.group(1).strip()

    # Certifications
    certs = ""
    cert_match = re.search(r'(?:Certifications?|Licenses?)\s*\n(.*?)(?=\n(?:Skills|Languages|Interests|Education|Experience))', text, re.S | re.I)
    if cert_match:
        certs = cert_match.group(1).strip()

    # Recommendations count
    recs = 0
    rec_match = re.search(r'(\d+)\s*recommendations?', text, re.I)
    if rec_match:
        recs = int(rec_match.group(1))

    return {
        "name":            name[:100],
        "headline":        headline[:220],
        "location":        location[:100],
        "connections":     connections,
        "about":           about[:2000],
        "skills":          skills_text[:1000],
        "recommendations": recs,
        "experience":      exp[:3000],
        "education":       edu[:500],
        "certifications":  certs[:500],
    }