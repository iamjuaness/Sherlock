"""Database engine, session factory and Base for SQLAlchemy models."""

from __future__ import annotations

from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in settings.database_url else {},
)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


# ── SQLite performance PRAGMAs ─────────────────────────────────────────────
if "sqlite" in settings.database_url:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        """Apply performance PRAGMAs on every new SQLite connection."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")      # WAL: concurrent reads + writes
        cursor.execute("PRAGMA synchronous=NORMAL")    # safe + faster than FULL
        cursor.execute("PRAGMA cache_size=-32000")     # ~32 MB page cache
        cursor.execute("PRAGMA temp_store=MEMORY")     # temp tables in RAM
        cursor.execute("PRAGMA mmap_size=268435456")   # lecturas vía mmap (256 MB)
        cursor.execute("PRAGMA journal_size_limit=67108864")  # el WAL no queda gigante tras checkpoint
        cursor.close()


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
            # FLOAT columns
            ("expected_goals_home", "FLOAT"),
            ("expected_goals_away", "FLOAT"),
            ("ball_possession_home", "FLOAT"),
            ("ball_possession_away", "FLOAT"),
            ("aerial_duels_percentage_home", "FLOAT"),
            ("aerial_duels_percentage_away", "FLOAT"),
            ("ground_duels_percentage_home", "FLOAT"),
            ("ground_duels_percentage_away", "FLOAT"),
            ("dribbles_percentage_home", "FLOAT"),
            ("dribbles_percentage_away", "FLOAT"),
            ("duel_won_percent_home", "FLOAT"),
            ("duel_won_percent_away", "FLOAT"),
            ("won_tackle_percent_home", "FLOAT"),
            ("won_tackle_percent_away", "FLOAT"),
            ("goals_prevented_home", "FLOAT"),
            ("goals_prevented_away", "FLOAT"),
            # INT columns
            ("accurate_cross_home", "INTEGER"),
            ("accurate_cross_away", "INTEGER"),
            ("accurate_long_balls_home", "INTEGER"),
            ("accurate_long_balls_away", "INTEGER"),
            ("accurate_passes_home", "INTEGER"),
            ("accurate_passes_away", "INTEGER"),
            ("accurate_through_ball_home", "INTEGER"),
            ("accurate_through_ball_away", "INTEGER"),
            ("ball_recovery_home", "INTEGER"),
            ("ball_recovery_away", "INTEGER"),
            ("big_chance_created_home", "INTEGER"),
            ("big_chance_created_away", "INTEGER"),
            ("big_chance_missed_home", "INTEGER"),
            ("big_chance_missed_away", "INTEGER"),
            ("big_chance_scored_home", "INTEGER"),
            ("big_chance_scored_away", "INTEGER"),
            ("blocked_scoring_attempt_home", "INTEGER"),
            ("blocked_scoring_attempt_away", "INTEGER"),
            ("corner_kicks_home", "INTEGER"),
            ("corner_kicks_away", "INTEGER"),
            ("dispossessed_home", "INTEGER"),
            ("dispossessed_away", "INTEGER"),
            ("dive_saves_home", "INTEGER"),
            ("dive_saves_away", "INTEGER"),
            ("final_third_entries_home", "INTEGER"),
            ("final_third_entries_away", "INTEGER"),
            ("final_third_phase_statistic_home", "INTEGER"),
            ("final_third_phase_statistic_away", "INTEGER"),
            ("fouled_final_third_home", "INTEGER"),
            ("fouled_final_third_away", "INTEGER"),
            ("fouls_home", "INTEGER"),
            ("fouls_away", "INTEGER"),
            ("free_kicks_home", "INTEGER"),
            ("free_kicks_away", "INTEGER"),
            ("goal_kicks_home", "INTEGER"),
            ("goal_kicks_away", "INTEGER"),
            ("goalkeeper_saves_home", "INTEGER"),
            ("goalkeeper_saves_away", "INTEGER"),
            ("high_claims_home", "INTEGER"),
            ("high_claims_away", "INTEGER"),
            ("hit_woodwork_home", "INTEGER"),
            ("hit_woodwork_away", "INTEGER"),
            ("interception_won_home", "INTEGER"),
            ("interception_won_away", "INTEGER"),
            ("offsides_home", "INTEGER"),
            ("offsides_away", "INTEGER"),
            ("passes_home", "INTEGER"),
            ("passes_away", "INTEGER"),
            ("punches_home", "INTEGER"),
            ("punches_away", "INTEGER"),
            ("shots_off_goal_home", "INTEGER"),
            ("shots_off_goal_away", "INTEGER"),
            ("shots_on_goal_home", "INTEGER"),
            ("shots_on_goal_away", "INTEGER"),
            ("throw_ins_home", "INTEGER"),
            ("throw_ins_away", "INTEGER"),
            ("total_clearance_home", "INTEGER"),
            ("total_clearance_away", "INTEGER"),
            ("total_shots_inside_box_home", "INTEGER"),
            ("total_shots_inside_box_away", "INTEGER"),
            ("total_shots_on_goal_home", "INTEGER"),
            ("total_shots_on_goal_away", "INTEGER"),
            ("total_shots_outside_box_home", "INTEGER"),
            ("total_shots_outside_box_away", "INTEGER"),
            ("total_tackle_home", "INTEGER"),
            ("total_tackle_away", "INTEGER"),
            ("touches_in_opp_box_home", "INTEGER"),
            ("touches_in_opp_box_away", "INTEGER"),
            ("yellow_cards_home", "INTEGER"),
            ("yellow_cards_away", "INTEGER"),
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

        # ── analysis_history JSON/Text/Flag fields (if not present from ORM) ──
        json_fields = [
            ("compare_response_snapshot", "TEXT"),
            ("llm_response", "TEXT"),
            ("llm_timestamp", "TEXT"),
            ("pre_match_stats", "TEXT"),
            ("recent_form_stats", "TEXT"),
            ("historical_pick_rates", "TEXT"),
            ("has_odds", "BOOLEAN NOT NULL DEFAULT 0"),
            ("needs_recalc", "BOOLEAN NOT NULL DEFAULT 1"),
            ("last_recalculated_at", "DATETIME"),
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

        # ── Denormalized columns for stats queries (avoid json_extract per request) ──
        denorm_fields = [
            ("competition", "TEXT"),
            ("bookmaker",   "TEXT"),
            ("stake_units", "REAL"),
        ]
        for col, dtype in denorm_fields:
            if not _column_exists(conn, "analysis_history", col):
                try:
                    conn.execute(text(
                        f"ALTER TABLE analysis_history ADD COLUMN {col} {dtype}"
                    ))
                    print(f"DB migrated: {col} added to analysis_history.")
                except Exception as e:
                    print(f"DB migration warning for {col}: {e}")

        # ── FKs normalizadas: competición y equipos ──
        for col, ref in (("competition_id", "competitions"),
                         ("home_team_id", "teams"),
                         ("away_team_id", "teams")):
            if not _column_exists(conn, "analysis_history", col):
                try:
                    conn.execute(text(
                        f"ALTER TABLE analysis_history ADD COLUMN {col} VARCHAR(36) REFERENCES {ref}(id)"
                    ))
                except Exception as e:
                    print(f"DB migration warning for {col}: {e}")
        for col, dtype in (("full_name", "VARCHAR(200)"), ("slug", "VARCHAR(200)"),
                           ("name_code", "VARCHAR(10)"), ("gender", "VARCHAR(5)"),
                           ("team_colors", "TEXT"), ("aliases", "TEXT")):
            if not _column_exists(conn, "teams", col):
                try:
                    conn.execute(text(f"ALTER TABLE teams ADD COLUMN {col} {dtype}"))
                except Exception as e:
                    print(f"DB migration warning for teams.{col}: {e}")
        for col, dtype in (("slug", "VARCHAR(200)"), ("category", "VARCHAR(100)"),
                           ("country_code", "VARCHAR(3)"), ("tier", "INTEGER"),
                           ("user_count", "INTEGER"), ("primary_color", "VARCHAR(9)"),
                           ("secondary_color", "VARCHAR(9)"), ("logo_id", "INTEGER"),
                           ("season_id", "VARCHAR(30)"), ("season_name", "VARCHAR(200)"),
                           ("season_year", "VARCHAR(20)"),
                           ("active", "BOOLEAN NOT NULL DEFAULT 1"), ("synced_at", "DATETIME"),
                           ("aliases", "TEXT")):
            if not _column_exists(conn, "competitions", col):
                try:
                    conn.execute(text(f"ALTER TABLE competitions ADD COLUMN {col} {dtype}"))
                except Exception as e:
                    print(f"DB migration warning for competitions.{col}: {e}")
        # ── Temporada desnormalizada: backfill único al crear las columnas ──
        _season_new = False
        for col in ("season_id", "season_year", "season_label"):
            if not _column_exists(conn, "analysis_history", col):
                conn.execute(text(f"ALTER TABLE analysis_history ADD COLUMN {col} VARCHAR(30)"))
                _season_new = True
        if _season_new:
            conn.execute(text(
                "UPDATE analysis_history SET "
                "season_id = json_extract(payload, '$.season_id'), "
                "season_year = json_extract(payload, '$.season_year'), "
                "season_label = json_extract(payload, '$.season')"
            ))
            print("DB backfill: season_id/season_year/season_label desde payload.")
        if not _column_exists(conn, "analysis_history", "stage"):
            conn.execute(text("ALTER TABLE analysis_history ADD COLUMN stage VARCHAR(50)"))
            conn.execute(text(
                "UPDATE analysis_history SET stage = CASE "
                "WHEN competition LIKE '%, Apertura' THEN 'Apertura' "
                "WHEN competition LIKE '%, Clausura' THEN 'Clausura' END "
                "WHERE competition LIKE '%, Apertura' OR competition LIKE '%, Clausura'"
            ))
        try:
            from src.core.entity_resolver import backfill_entity_ids, consolidate_competitions
            n = consolidate_competitions(conn)
            if n:
                print(f"DB consolidate: {n} competencias unidas (torneos/alias).")
            n = backfill_entity_ids(conn)
            if n:
                print(f"DB backfill: {n} filas con competition_id/home_team_id/away_team_id.")
        except Exception as e:
            print(f"DB backfill warning for entity ids: {e}")

        # Idempotent backfill of has_odds for historical records
        try:
            conn.execute(text(
                "UPDATE analysis_history SET has_odds = 1 WHERE (has_odds IS NULL OR has_odds = 0) AND (payload LIKE '%\"odds\"%' OR payload LIKE '%\"sources\"%');"
            ))
        except Exception as e:
            print(f"DB backfill warning for has_odds: {e}")

        # ── Backfill: competition via json_extract (single SQL UPDATE, no Python loop) ──
        try:
            conn.execute(text("""
                UPDATE analysis_history
                SET competition = COALESCE(
                    NULLIF(TRIM(json_extract(payload, '$.competition')), ''),
                    json_extract(payload, '$.tournament.name')
                )
                WHERE competition IS NULL AND payload IS NOT NULL
            """))
            print("DB backfill: competition populated via json_extract.")
        except Exception as e:
            print(f"DB backfill warning for competition: {e}")

        # ── Backfill: bookmaker via json_extract ──
        try:
            conn.execute(text("""
                UPDATE analysis_history
                SET bookmaker = COALESCE(
                    json_extract(payload, '$.bookmaker'),
                    json_extract(payload, '$.sources[0].bookmaker')
                )
                WHERE bookmaker IS NULL AND payload IS NOT NULL
            """))
            print("DB backfill: bookmaker populated via json_extract.")
        except Exception as e:
            print(f"DB backfill warning for bookmaker: {e}")

        conn.commit()
        print("Database initialization complete.")
    create_indexes()


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_indexes():
    """Create indexes for analysis_history and related tables."""
    with engine.connect() as conn:
        # ── analysis_history existing indexes ──
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_analysis_history_sport_title ON analysis_history(sport, match_title);"
        ))
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_ah_competition_id ON analysis_history(competition_id)",
            "CREATE INDEX IF NOT EXISTS idx_ah_comp_season ON analysis_history(competition_id, season_year)",
            "CREATE INDEX IF NOT EXISTS idx_ah_season_id ON analysis_history(season_id)",
            "CREATE INDEX IF NOT EXISTS idx_ah_home_team_id ON analysis_history(home_team_id)",
            "CREATE INDEX IF NOT EXISTS idx_ah_away_team_id ON analysis_history(away_team_id)",
            "CREATE INDEX IF NOT EXISTS idx_teams_sport_lname ON teams(sport, lower(trim(name)))",
            "CREATE INDEX IF NOT EXISTS idx_competitions_sport_lname ON competitions(sport, lower(trim(name)))",
        ):
            conn.execute(text(stmt))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_analysis_history_sport_date ON analysis_history(sport, match_date DESC);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_analysis_history_has_odds ON analysis_history(has_odds);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_analysis_history_needs_recalc ON analysis_history(needs_recalc);"
        ))
        # ── New denormalized column indexes ──
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ah_competition ON analysis_history(competition);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ah_stake_units ON analysis_history(stake_units);"
        ))
        # Índices sin valor: bookmaker es 100% NULL; sport tiene un único valor y
        # idx_analysis_history_sport_date ya cubre el prefijo (sport).
        conn.execute(text("DROP INDEX IF EXISTS idx_ah_bookmaker"))
        conn.execute(text("DROP INDEX IF EXISTS ix_analysis_history_sport"))
        # Parciales: solo ~7% de las filas tiene picks/resultado -> índices diminutos.
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ah_picks_by_comp ON analysis_history(competition_id, match_date) "
            "WHERE picks_calculados IS NOT NULL;"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ah_results_by_comp ON analysis_history(competition_id, date DESC) "
            "WHERE final_score_home IS NOT NULL;"
        ))
        # Índice compuesto y "covering" para pending-picks:
        # cubre WHERE final_score_home IS NULL AND competition IS NOT NULL
        # sin tener que ir a la tabla a leer las columnas.
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ah_pending_picks "
            "ON analysis_history(final_score_home, competition);"
        ))
        # ── FK indexes missing on matches table ──
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_matches_competition_id ON matches(competition_id);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_matches_home_team_id ON matches(home_team_id);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_matches_away_team_id ON matches(away_team_id);"
        ))
        # ── Admin audit & search performance indexes ──
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_ah_match_date ON analysis_history(match_date);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON admin_audit_log(timestamp);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON admin_audit_log(action);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_target ON admin_audit_log(target_table, record_id);"
        ))
        conn.commit()
