from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime

# ── AUTH SCHEMAS ──

class RegisterRequest(BaseModel):
    first_name:  str = Field(..., min_length=1, max_length=100)
    last_name:   str = Field(..., min_length=1, max_length=100)
    email:       EmailStr
    password:    str = Field(..., min_length=8)
    career_goal: Optional[str] = None

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           int
    first_name:   str
    last_name:    str
    email:        str
    career_goal:  Optional[str] = None
    resume_ats_score:  Optional[int] = None
    github_score:      Optional[int] = None
    linkedin_score:    Optional[int] = None
    github_username:   Optional[str] = None
    created_at:   datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserOut

class MessageResponse(BaseModel):
    message: str