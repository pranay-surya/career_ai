import os
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Configurable — defaults to SQLite for local dev, set DATABASE_URL for production (e.g. PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./careerai.db")

# Strip 'channel_binding' param — psycopg2 doesn't support it (Neon DB adds it)
if "channel_binding" in DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    params = parse_qs(parsed.query)
    params.pop("channel_binding", None)
    clean_query = urlencode(params, doseq=True)
    DATABASE_URL = urlunparse(parsed._replace(query=clean_query))

# check_same_thread is only needed for SQLite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()