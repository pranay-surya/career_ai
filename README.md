# 🚀 CareerAI — AI-Powered Career Platform

CareerAI is a full-stack career development platform that helps students and fresh graduates become internship-ready using AI. It provides resume analysis, GitHub/LinkedIn profile scoring, AI-generated career roadmaps, smart internship matching, and a career chatbot — all powered by **Groq LLM**.

---

## ✨ Features

| Module | Description |
|--------|-------------|
| **Resume Analyzer** | Upload PDF resume → get ATS score, skill gaps & improvement suggestions |
| **GitHub Analyzer** | Analyze any GitHub profile — repos, languages, tech stack & recruiter attractiveness score |
| **LinkedIn Analyzer** | Paste profile data or upload PDF → headline optimization, skill gaps & networking tips |
| **Internship Finder** | AI-matched internships filtered by skills, level & location |
| **AI Career Roadmap** | Groq-powered personalized roadmap with phases, resources, projects & chatbot |
| **Career Chatbot** | Ask career questions, get interview tips, project ideas & career advice |

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** — Python web framework
- **SQLAlchemy** — ORM (PostgreSQL via Neon / SQLite for local dev)
- **Groq API** — LLM integration (llama-3.3-70b-versatile)
- **spaCy** — NLP for skill extraction
- **PyGithub** — GitHub API integration
- **pdfplumber** — Resume PDF parsing
- **passlib + python-jose** — Auth (bcrypt hashing + JWT tokens)

### Frontend
- **HTML5 + Tailwind CSS + Vanilla JS**
- Responsive design with mobile support
- Served via FastAPI `StaticFiles`

### Database
- **PostgreSQL** (Neon) for production
- **SQLite** fallback for local development

---

## 📁 Project Structure

```
career-platform/
├── .gitignore
├── README.md
├── DEPLOYMENT.md
├── backend/
│   ├── main.py              # FastAPI app + routes + static serving
│   ├── database.py           # DB engine (PostgreSQL / SQLite)
│   ├── models.py             # SQLAlchemy User model
│   ├── schemas.py            # Pydantic validation schemas
│   ├── requirements.txt      # Python dependencies
│   ├── Procfile              # Deploy command for Render/Heroku
│   ├── auth/
│   │   ├── router.py         # Register, Login, Logout, /me
│   │   └── utils.py          # Password hashing, JWT, auth dependency
│   ├── api/
│   │   ├── resume.py         # Resume upload & analysis endpoints
│   │   ├── github.py         # GitHub analysis endpoints
│   │   ├── linkedin.py       # LinkedIn analysis endpoints
│   │   ├── internships.py    # Internship finder endpoints
│   │   └── roadmap.py        # AI roadmap + chatbot endpoints
│   └── services/
│       ├── groq_service.py       # Groq LLM integration
│       ├── resume_parser.py      # PDF text extraction
│       ├── skill_extractor.py    # NLP skill extraction
│       ├── ats_scorer.py         # ATS scoring logic
│       ├── github_analyzer.py    # GitHub profile analysis
│       ├── linkedin_analyzer.py  # LinkedIn profile analysis
│       ├── internship_matcher.py # Internship matching
│       └── internship_scraper.py # Internship data collection
└── frontend/
    ├── index.html            # Landing page
    ├── login.html            # Sign in
    ├── register.html         # Create account
    ├── dashboard.html        # User dashboard
    ├── resume.html           # Resume analyzer UI
    ├── github.html           # GitHub analyzer UI
    ├── linkedin.html         # LinkedIn analyzer UI
    ├── internships.html      # Internship finder UI
    └── roadmap.html          # AI roadmap + chatbot UI
```

---

## ⚡ Quick Start (Local Development)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/career-platform.git
cd career-platform
```

### 2. Set up the backend
```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure environment variables
Create a `.env` file in the `backend/` folder:
```env
GROQ_API_KEY=your_groq_api_key
RAPIDAPI_KEY=your_rapidapi_key
JWT_SECRET_KEY=your_random_64_char_secret
DATABASE_URL=sqlite:///./careerai.db
ALLOWED_ORIGINS=*
```

> 💡 Generate a secure JWT secret: `python -c "import secrets; print(secrets.token_hex(32))"`

### 4. Start the server
```bash
uvicorn main:app --reload --port 8000
```

### 5. Open the app
- 🌐 **App:** http://localhost:8000/site/index.html
- 📖 **API Docs:** http://localhost:8000/docs

---

## 🚀 Deployment (Render)

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions.

**Quick steps:**
1. Push to GitHub
2. Create a **Web Service** on Render → connect your repo
3. **Root Directory:** `backend`
4. **Build Command:** `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
5. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Set environment variables in Render dashboard

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq API key for LLM features |
| `RAPIDAPI_KEY` | ✅ | RapidAPI key for job data |
| `JWT_SECRET_KEY` | ✅ | Secret for JWT token signing |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `ALLOWED_ORIGINS` | Optional | CORS origins (comma-separated or `*`) |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login & get JWT token |
| GET | `/auth/me` | Get current user profile |
| POST | `/resume/analyze` | Upload & analyze resume |
| POST | `/github/analyze` | Analyze GitHub profile |
| POST | `/linkedin/analyze` | Analyze LinkedIn profile |
| GET | `/internships/search` | Search internships |
| POST | `/roadmap/generate` | Generate AI career roadmap |
| POST | `/roadmap/chat` | Career chatbot |
| GET | `/health` | Health check |

---

## 📄 License

This project is for educational purposes. Built with ❤️ for students.
