# CareerAI — Deployment Guide

## Environment Variables

Set these on your hosting platform (Render, Railway, etc.):

| Variable | Required | Example |
|---|---|---|
| `GROQ_API_KEY` | ✅ | `gsk_...` |
| `RAPIDAPI_KEY` | ✅ | Your RapidAPI key |
| `JWT_SECRET_KEY` | ✅ | Random 64-char string |
| `DATABASE_URL` | ✅ | `postgresql://user:pass@host/db` |
| `ALLOWED_ORIGINS` | Optional | `https://your-frontend.com` |

> **Tip:** Generate a secure JWT secret: `python -c "import secrets; print(secrets.token_hex(32))"`

## Deploy on Render (Free Tier)

### Backend
1. Push code to GitHub
2. Create a **Web Service** on Render → connect your repo
3. **Root Directory:** `backend`
4. **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
5. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add all environment variables above
7. For database, create a free **PostgreSQL** instance on Render and use its Internal URL as `DATABASE_URL`

### Frontend
The frontend is served by FastAPI at `/app/` (e.g., `https://your-backend.onrender.com/app/index.html`).

No separate hosting needed!

## Local Development

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --reload
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Frontend: http://localhost:8000/app/
