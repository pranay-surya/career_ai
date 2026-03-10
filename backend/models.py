from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    first_name    = Column(String(100), nullable=False)
    last_name     = Column(String(100), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    career_goal   = Column(String(200), nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # Profile scores (updated when user analyzes their profiles)
    resume_ats_score   = Column(Integer, nullable=True)
    github_score       = Column(Integer, nullable=True)
    linkedin_score     = Column(Integer, nullable=True)

    # Resume storage (path or raw text)
    resume_text        = Column(Text, nullable=True)
    resume_filename    = Column(String(255), nullable=True)

    # GitHub username
    github_username    = Column(String(100), nullable=True)

    def full_name(self):
        return f"{self.first_name} {self.last_name}"