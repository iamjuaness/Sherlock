"""
Verifica que las optimizaciones de indices en sherlock.db realmente se estan usando.
Corre EXPLAIN QUERY PLAN sobre las consultas clave de la UI (ligas, partidos por liga,
unidades ganadas, teams/count) y reporta si SQLite esta usando SEARCH (indice) o
SCAN (recorrido completo de tabla).

Uso (PowerShell, desde la raiz del proyecto):
    python verify_db_indexes.py
    python verify_db_indexes.py --db data/sherlock.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Consultas representativas de la UI a verificar.
# Ajusta los valores de ejemplo (ej. 'Premier League') si tu BD tiene otras ligas.
# ---------------------------------------------------------------------------
QUERIES: list[tuple[str, str, tuple]] = [
    (
        "Picks pendientes (pending-picks) filtrando por competition",
        "SELECT competition FROM analysis_history "
        "WHERE final_score_home IS NULL AND competition IS NOT NULL",
        (),
    ),
    (
        "Teams/count filtrando por liga",
        "SELECT match_title, competition FROM analysis_history "
        "WHERE competition = ?",
        ("Premier League",),
    ),
    (
        "Stats por liga (get_leagues_stats) agrupando por competition",
        "SELECT competition, COUNT(*), SUM(stake_units) FROM analysis_history "
        "WHERE competition IS NOT NULL GROUP BY competition",
        (),
    ),
    (
        "Stats global (get_global_stats) filtrando por rango de fechas",
        "SELECT * FROM analysis_history WHERE date >= ? AND date <= ?",
        ("2026-01-01", "2026-12-31"),
    ),
    (
        "Unidades ganadas por bookmaker",
        "SELECT bookmaker, SUM(stake_units) FROM analysis_history "
        "WHERE bookmaker IS NOT NULL GROUP BY bookmaker",
        (),
    ),
    (
        "Matches por competicion (join con competitions)",
        "SELECT m.id FROM matches m WHERE m.competition_id = ?",
        ("dummy-competition-id",),
    ),
    (
        "Matches con home_team_id (usado en joinedload)",
        "SELECT m.id FROM matches m WHERE m.home_team_id = ?",
        ("dummy-team-id",),
    ),
    (
        "Stat lines por equipo",
        "SELECT * FROM stat_lines_team WHERE team_id = ?",
        ("dummy-team-id",),
    ),
]


def check_query(conn: sqlite3.Connection, label: str, sql: str, params: tuple) -> dict:
    cur = conn.cursor()
    plan_rows = cur.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
    plan_text = "\n".join(str(r) for r in plan_rows)

    uses_scan = any("SCAN" in str(r) and "USING INDEX" not in str(r) for r in plan_rows)
    uses_search_or_covering_index = any(
        ("SEARCH" in str(r)) or ("USING INDEX" in str(r)) for r in plan_rows
    )

    return {
        "label": label,
        "sql": sql,
        "plan": plan_text,
        "full_scan": uses_scan and not uses_search_or_covering_index,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/sherlock.db", help="Ruta al archivo sherlock.db")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"No se encontro la base de datos en: {db_path.resolve()}")
        return 1

    conn = sqlite3.connect(str(db_path))
    try:
        results = [check_query(conn, label, sql, params) for label, sql, params in QUERIES]
    finally:
        conn.close()

    print("=" * 90)
    print(f"Verificacion de indices - {db_path}")
    print("=" * 90)

    any_full_scan = False
    for r in results:
        status = "SCAN COMPLETO (revisar indice)" if r["full_scan"] else "OK (usa indice)"
        any_full_scan = any_full_scan or r["full_scan"]
        print(f"\n[{status}] {r['label']}")
        print(f"SQL: {r['sql']}")
        print("Plan:")
        print(r["plan"])

    print("\n" + "=" * 90)
    if any_full_scan:
        print("Hay consultas haciendo SCAN completo de tabla. Revisa los indices "
              "correspondientes en create_indexes() de src/core/database.py.")
    else:
        print("Todas las consultas verificadas estan usando indices (SEARCH / USING INDEX).")
    print("=" * 90)

    return 0


if __name__ == "__main__":
    sys.exit(main())
