"""
api/roadmap.py
AI-powered career roadmap generation and chatbot endpoints.
Powered by Groq LLM (free tier).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import models
from auth.utils import get_current_user
from services.groq_service import generate_roadmap, chat_with_groq

router = APIRouter()


class RoadmapRequest(BaseModel):
    career_goal:    str
    level:          Optional[str] = "beginner"
    time_available: Optional[str] = "2-3 hours/day"
    focus_area:     Optional[str] = "job-ready"
    roadmap_type:   Optional[str] = "simple"


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = []
    context: Optional[str] = ""


@router.post("/generate")
async def generate(
    payload: RoadmapRequest,
    current_user: models.User = Depends(get_current_user),
):
    """
    Generate a personalized AI career roadmap.
    Uses Groq LLM if API key is set, otherwise returns static roadmap.
    """
    if not payload.career_goal.strip():
        raise HTTPException(400, "Career goal cannot be empty.")

    try:
        roadmap = await generate_roadmap(
            career_goal    = payload.career_goal,
            level          = payload.level or "beginner",
            time_available = payload.time_available or "2-3 hours/day",
            focus_area     = payload.focus_area or "job-ready",
            roadmap_type   = payload.roadmap_type or "simple",
        )
        return roadmap
    except Exception as e:
        raise HTTPException(500, f"Roadmap generation failed: {str(e)}")


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    current_user: models.User = Depends(get_current_user),
):
    """
    Career advice chatbot powered by Groq.
    """
    if not payload.message.strip():
        raise HTTPException(400, "Message cannot be empty.")

    try:
        reply = await chat_with_groq(
            message = payload.message,
            history = payload.history or [],
            context = payload.context or "",
        )
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")


@router.get("/careers")
def list_careers():
    """Return supported career paths."""
    return {"careers": [
        "Frontend Developer", "Backend Developer", "Full Stack Developer",
        "AI / ML Engineer", "Data Scientist", "Data Analyst",
        "DevOps Engineer", "Cloud Engineer", "Cybersecurity Specialist",
        "Android Developer", "iOS Developer",
    ]}