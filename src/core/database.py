"""Database engine, session factory and Base for SQLAlchemy models."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    """Create all tables that don't exist yet and run simple schema migrations."""
    Base.metadata.create_all(bind=engine)
    
    # Simple migration: ensure count_in_profitability column exists
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT count_in_profitability FROM analysis_history LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE analysis_history ADD COLUMN count_in_profitability BOOLEAN NOT NULL DEFAULT 1"))
                conn.commit()
                print("Database migrated: count_in_profitability column added to analysis_history.")
            except Exception as e:
                print(f"Error migrating database: {e}")


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
