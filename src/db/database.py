import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL on Railway — fix scheme if needed
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    DATA_DIR = Path(__file__).parent.parent.parent / "data"
    DB_PATH = DATA_DIR / "lastautai.db"
    DATA_DIR.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables if they don't exist."""
    from src.db.models import User, Workflow  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
