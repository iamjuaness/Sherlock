"""Database engine, session factory and Base for SQLAlchemy models."""

from __future__ import annotations

from sqlalchemy import create_engine, text, inspect
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


def _column_exists(conn, table: str, column: str) -> bool:
    """Check if a column exists in a table (SQLite-compatible)."""
    try:
        conn.execute(text(f"SELECT {column} FROM {table} LIMIT 1"))
        return True
    except Exception:
        return False


def init_db() -> None:
    """Create all tables and run idempotent schema migrations."""
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        # ── analysis_history result fields ──
        result_fields = [
            ("final_score_home", "INTEGER"),
            ("final_score_away", "INTEGER"),
            ("final_corners_home", "INTEGER"),
            ("final_corners_away", "INTEGER"),
            ("final_yellow_cards_home", "INTEGER"),
            ("final_yellow_cards_away", "INTEGER"),
            ("final_red_cards_home", "INTEGER"),
            ("final_red_cards_away", "INTEGER"),
            ("final_shots_home", "INTEGER"),
            ("final_shots_away", "INTEGER"),
            ("final_shots_on_target_home", "INTEGER"),
            ("final_shots_on_target_away", "INTEGER"),
            ("final_fouls_home", "INTEGER"),
            ("final_fouls_away", "INTEGER"),
            ("final_offsides_home", "INTEGER"),
            ("final_offsides_away", "INTEGER"),
            ("accuracy_percentage", "FLOAT"),
            ("picks_hits_summary", "TEXT"),
            ("needs_reanalysis", "BOOLEAN NOT NULL DEFAULT 0"),
            ("count_in_profitability", "BOOLEAN NOT NULL DEFAULT 1"),
        ]

        for col, dtype in result_fields:
            if not _column_exists(conn, "analysis_history", col):
                try:
                    conn.execute(text(
                        f"ALTER TABLE analysis_history ADD COLUMN {col} {dtype}"
                    ))
                    print(f"DB migrated: {col} added to analysis_history.")
                except Exception as e:
                    print(f"DB migration warning for {col}: {e}")

        # ── analysis_history JSON/Text fields (if not present from ORM) ──
        json_fields = [
            ("compare_response_snapshot", "TEXT"),
            ("llm_response", "TEXT"),
            ("llm_timestamp", "TEXT"),
        ]
        for col, dtype in json_fields:
            if not _column_exists(conn, "analysis_history", col):
                try:
                    conn.execute(text(
                        f"ALTER TABLE analysis_history ADD COLUMN {col} {dtype}"
                    ))
                    print(f"DB migrated: {col} added to analysis_history.")
                except Exception as e:
                    print(f"DB migration warning for {col}: {e}")

        conn.commit()
        print("Database initialization complete.")


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()