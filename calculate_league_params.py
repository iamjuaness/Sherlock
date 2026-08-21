"""
Script CLI para calcular parámetros matemáticos (Dixon-Coles, promedios por liga,
fuerza ofensiva/defensiva y dispersión) para una liga en específico a partir de la BD de Watson.

Uso:
    python calculate_league_params.py --league "LaLiga"
    python calculate_league_params.py --league_id "123"
    python calculate_league_params.py --all
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

# Asegurar import de src
sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import SessionLocal
from src.core.math_engine import LeagueMathEngine, estimate_nb_dispersion

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("calculate_league_params")


def fetch_historical_matches_by_league(league_identifier: str) -> List[Dict[str, Any]]:
    """
    Obtiene todos los partidos finalizados de una liga buscando de forma exhaustiva en 
    `analysis_history` (payload JSON o title) y en las tablas `matches` / `competitions`.
    """
    session = SessionLocal()
    records = []

    try:
        # 1. Consultar en `analysis_history`
        query_ah = text("""
            SELECT 
                match_title,
                payload,
                final_score_home, final_score_away,
                final_corners_home, final_corners_away,
                final_yellow_cards_home, final_yellow_cards_away,
                final_shots_home, final_shots_away,
                final_shots_on_target_home, final_shots_on_target_away,
                final_fouls_home, final_fouls_away
            FROM analysis_history
            WHERE final_score_home IS NOT NULL 
              AND final_score_away IS NOT NULL
            ORDER BY match_date DESC
        """)
        
        rows = session.execute(query_ah).mappings().all()
        target_league = league_identifier.strip().lower()

        import json
        for r in rows:
            row_dict = dict(r)
            match_payload = {}
            if row_dict.get("payload"):
                try:
                    match_payload = json.loads(row_dict["payload"]) if isinstance(row_dict["payload"], str) else row_dict["payload"]
                except Exception:
                    pass

            # Extraer liga/competición explícitamente desde el payload o match_title
            comp_candidates = [
                match_payload.get("competition"),
                match_payload.get("competition_name"),
                match_payload.get("league"),
                match_payload.get("league_name"),
                match_payload.get("tournament"),
                row_dict.get("match_title")
            ]
            
            comp_str = " ".join([str(c) for c in comp_candidates if c]).lower()

            if not target_league or target_league in comp_str:
                records.append(row_dict)


        if records:
            logger.info("Encontrados %d partidos en `analysis_history` coincidentes con la liga '%s'.", len(records), league_identifier)
            return records

        # 2. Alternativa: Consultar en `matches` y `competitions`
        try:
            query_matches = text("""
                SELECT 
                    m.home_score AS final_score_home,
                    m.away_score AS final_score_away
                FROM matches m
                JOIN competitions c ON m.competition_id = c.id
                WHERE (c.id = :league_id OR c.external_id = :league_id OR LOWER(c.name) LIKE LOWER(:league_name))
                  AND m.home_score IS NOT NULL 
                  AND m.away_score IS NOT NULL
                ORDER BY m.date DESC
            """)

            res_matches = session.execute(query_matches, {
                "league_id": league_identifier,
                "league_name": f"%{league_identifier}%"
            }).mappings().all()

            records = [dict(r) for r in res_matches]
            if records:
                logger.info("Encontrados %d partidos en `matches`/`competitions` para la liga '%s'.", len(records), league_identifier)
        except Exception as err_m:
            logger.warning("No se pudo consultar `matches`: %s", err_m)

    except Exception as exc:
        logger.error("Error consultando la base de datos: %s", exc)
    finally:
        session.close()

    return records





def calculate_parameters(league: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula todos los parámetros matemáticos a partir de los datos históricos."""
    if not records:
        logger.warning("No se encontraron partidos para la liga '%s'. Retornando parámetros por defecto.", league)
        engine = LeagueMathEngine()
        return {
            "league": league,
            "sample_size": 0,
            "averages": engine.defaults,
            "dispersions": {"corners": 0.05, "cards": 0.05, "shots": 0.05}
        }

    # Promedios esperados
    avgs = LeagueMathEngine.compute_league_averages(records)

    # Dispersión por mercado (Binomial Negativa)
    corners_totals = [(r["final_corners_home"] + r["final_corners_away"]) for r in records if r.get("final_corners_home") is not None and r.get("final_corners_away") is not None]
    cards_totals = [(r["final_yellow_cards_home"] + r["final_yellow_cards_away"]) for r in records if r.get("final_yellow_cards_home") is not None and r.get("final_yellow_cards_away") is not None]
    shots_totals = [(r["final_shots_home"] + r["final_shots_away"]) for r in records if r.get("final_shots_home") is not None and r.get("final_shots_away") is not None]

    disp_corners = estimate_nb_dispersion(corners_totals)
    disp_cards = estimate_nb_dispersion(cards_totals)
    disp_shots = estimate_nb_dispersion(shots_totals)

    return {
        "league": league,
        "sample_size": len(records),
        "averages": avgs,
        "dispersions": {
            "corners": round(disp_corners, 4),
            "cards": round(disp_cards, 4),
            "shots": round(disp_shots, 4),
        }
    }


def calculate_parameters_per_match(league: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calcula por cada partido las estadísticas acumuladas de la liga y de los dos equipos
    utilizando ÚNICAMENTE los partidos jugados ANTES de la fecha de ese partido.
    Además calcula las ventanas de forma reciente (últimos 5, 10 y 15 partidos).
    """
    processed = []
    import json

    # Ordenar cronológicamente (más antiguo a más reciente)
    sorted_records = sorted(records, key=lambda x: str(x.get("match_date") or x.get("date") or ""))

    for idx, current_match in enumerate(sorted_records):
        prior_records = sorted_records[:idx]  # Partidos estrictamente anteriores

        # 1. Promedios acumulados de la liga anteriores a este partido
        league_params = calculate_parameters(league, prior_records)

        # 2. Extraer equipos del título o payload
        title = current_match.get("match_title", "")
        home_team = title.split(" vs ")[0].strip() if " vs " in title else "Home"
        away_team = title.split(" vs ")[1].strip() if " vs " in title else "Away"

        # 3. Ventanas de forma reciente (5, 10, 15 partidos previos)
        home_form = LeagueMathEngine.compute_recent_form_windows(prior_records, home_team, windows=[5, 10, 15])
        away_form = LeagueMathEngine.compute_recent_form_windows(prior_records, away_team, windows=[5, 10, 15])

        # 4. Frecuencia empírica previa (% de acierto real en 2.5 goles como ejemplo)
        home_over25 = LeagueMathEngine.compute_pick_hit_rate(prior_records, home_team, "goals", 2.5, is_over=True, role_filter="home")
        away_over25 = LeagueMathEngine.compute_pick_hit_rate(prior_records, away_team, "goals", 2.5, is_over=True, role_filter="away")

        processed.append({
            "match_title": title,
            "match_date": current_match.get("match_date"),
            "prior_sample_size": len(prior_records),
            "league_averages": league_params["averages"],
            "league_dispersions": league_params["dispersions"],
            "recent_form": {
                "home": home_form,
                "away": away_form,
            },
            "sample_pick_rates": {
                "home_over25_home": home_over25,
                "away_over25_away": away_over25,
            }
        })

    return processed


def print_summary(params: Dict[str, Any]) -> None:
    """Imprime un informe formateado en consola."""
    print("\n" + "=" * 60)
    print(f"  PARÁMETROS MATEMÁTICOS DE LIGA: {params['league'].upper()}")
    print("=" * 60)
    print(f" Muestras Analizadas : {params['sample_size']} partidos")
    print("-" * 60)
    print(" PROMEDIOS POR LIGA (Por Partido):")
    avgs = params["averages"]
    print(f"  - Goles Local        : {avgs.get('home_goals', 0.0):.2f}")
    print(f"  - Goles Visitante    : {avgs.get('away_goals', 0.0):.2f}")
    print(f"  - Total Goles Liga   : {(avgs.get('home_goals', 0.0) + avgs.get('away_goals', 0.0)):.2f}")
    print(f"  - Corners Local      : {avgs.get('home_corners', 0.0):.2f}")
    print(f"  - Corners Visitante  : {avgs.get('away_corners', 0.0):.2f}")
    print(f"  - Tarjetas Local     : {avgs.get('home_cards', 0.0):.2f}")
    print(f"  - Tarjetas Visitante : {avgs.get('away_cards', 0.0):.2f}")
    print(f"  - Tiros Local        : {avgs.get('home_shots', 0.0):.2f}")
    print(f"  - Tiros Visitante    : {avgs.get('away_shots', 0.0):.2f}")
    print("-" * 60)
    print(" DISPERSIÓN (Binomial Negativa / Cola larga):")
    disps = params["dispersions"]
    print(f"  - Dispersión Corners : {disps.get('corners', 0.0)}")
    print(f"  - Dispersión Tarjetas: {disps.get('cards', 0.0)}")
    print(f"  - Dispersión Tiros   : {disps.get('shots', 0.0)}")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculador de Parámetros Matemáticos por Liga Sherlock")
    parser.add_argument("--league", "-l", type=str, help="Nombre o ID de la liga a calcular (ej. 'Premier League', 'LaLiga')")
    parser.add_argument("--per-match", action="store_true", help="Calcular parámetros e historia previa partido por partido")

    args = parser.parse_args()

    league_name = args.league
    if not league_name:
        league_name = input("Ingrese el nombre o ID de la liga (ej. 'LaLiga', 'Premier League'): ").strip()

    if not league_name:
        print("Debe especificar una liga.")
        sys.exit(1)

    records = fetch_historical_matches_by_league(league_name)
    params = calculate_parameters(league_name, records)
    print_summary(params)

    if args.per_match:
        per_match_data = calculate_parameters_per_match(league_name, records)
        print(f"Calculados parámetros previos para {len(per_match_data)} partidos de '{league_name}'.")
        if per_match_data:
            last = per_match_data[-1]
            print(f"\nÚltimo partido analizado: {last['match_title']}")
            print(f"Muestras previas: {last['prior_sample_size']}")
            print(f"Forma reciente Local (últimos 5): {last['recent_form']['home'].get('last_5')}")
            print(f"Forma reciente Visitante (últimos 5): {last['recent_form']['away'].get('last_5')}")


if __name__ == "__main__":
    main()
