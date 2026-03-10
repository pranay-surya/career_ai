import os
import logging
from dotenv import load_dotenv

# ── Load .env FIRST so every module sees the env vars ──
load_dotenv()

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from database import engine, Base
from auth.router      import router as auth_router
from api.resume       import router as resume_router
from api.github       import router as github_router
from api.internships  import router as internships_router
from api.roadmap      import router as roadmap_router
from api.linkedin     import router as linkedin_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("careerai")

# ── Create tables ──
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified successfully.")
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    logger.error("Check your DATABASE_URL environment variable.")

app = FastAPI(title="CareerAI API", version="1.0.0")

# CORS — load allowed origins from env, fallback to localhost for dev
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:5500,http://127.0.0.1:5500")
if allowed_origins_raw.strip() == "*":
    origins_list = ["*"]
else:
    origins_list = [o.strip() for o in allowed_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_credentials=False if "*" in origins_list else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,        prefix="/auth",        tags=["Authentication"])
app.include_router(resume_router,      prefix="/resume",      tags=["Resume Analyzer"])
app.include_router(github_router,      prefix="/github",      tags=["GitHub Analyzer"])
app.include_router(internships_router, prefix="/internships", tags=["Internship Finder"])
app.include_router(roadmap_router,     prefix="/roadmap",     tags=["AI Roadmap"])
app.include_router(linkedin_router,    prefix="/linkedin",    tags=["LinkedIn Analyzer"])

@app.get("/")
def root():
    return RedirectResponse(url="/site/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

# Serve frontend static files (mount AFTER API routes so API takes priority)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/site", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    logger.info(f"Frontend served from: {frontend_dir}")
else:
    logger.warning(f"Frontend directory not found at: {frontend_dir}")