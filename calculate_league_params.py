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
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

# Asegurar import de src
sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import SessionLocal
from src.core.math_engine import (
    LeagueMathEngine,
    estimate_nb_dispersion,
    get_league_profile,
    load_league_profiles_config,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("calculate_league_params")


def normalize_league_name(name: Optional[str]) -> str:
    """Normaliza el nombre de una liga para comparaciones exactas sin distinción de mayúsculas/espacios."""
    if not name:
        return ""
    clean = str(name).strip().lower()
    clean = " ".join(clean.split())
    aliases = {
        "la liga": "laliga",
        "laliga santander": "laliga",
        "la liga 2": "laliga 2",
        "laliga2": "laliga 2",
        "la liga smartbank": "laliga 2",
        "laliga hypermotion": "laliga 2",
    }
    return aliases.get(clean, clean)


def extract_match_competition(match_row: Dict[str, Any]) -> str:
    """Extrae la competición de un registro histórico probando campos de payload (strings o dicts)."""
    payload = match_row.get("payload")
    if not payload:
        return ""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return ""

    if isinstance(payload, dict):
        for key in ("competition", "competition_name", "league", "league_name", "tournament"):
            val = payload.get(key)
            if isinstance(val, dict):
                val = val.get("name") or val.get("competition_name") or val.get("league_name")
            if val and str(val).strip():
                return str(val).strip()

    return ""


def fetch_historical_matches_by_league(league_identifier: str) -> List[Dict[str, Any]]:
    """
    Obtiene todos los partidos finalizados de una liga buscando de forma exacta y exhaustiva en 
    `analysis_history` (payload JSON o title) y en las tablas `matches` / `competitions`.
    """
    session = SessionLocal()
    records = []

    try:
        query_ah = text("""
            SELECT 
                match_title,
                payload,
                match_date,
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
        target_norm = normalize_league_name(league_identifier)

        for r in rows:
            row_dict = dict(r)
            extracted_comp = extract_match_competition(row_dict)
            comp_norm = normalize_league_name(extracted_comp)

            if not target_norm or comp_norm == target_norm:
                records.append(row_dict)

        if records:
            logger.info("Encontrados %d partidos en `analysis_history` coincidentes con la liga '%s'.", len(records), league_identifier)
            return records

        # 2. Alternativa: Consultar en `matches` y `competitions` con coincidencia exacta
        try:
            query_matches = text("""
                SELECT 
                    m.home_score AS final_score_home,
                    m.away_score AS final_score_away,
                    m.date AS match_date
                FROM matches m
                JOIN competitions c ON m.competition_id = c.id
                WHERE (c.id = :league_id OR c.external_id = :league_id OR LOWER(c.name) = LOWER(:league_name))
                  AND m.home_score IS NOT NULL 
                  AND m.away_score IS NOT NULL
                ORDER BY m.date DESC
            """)

            res_matches = session.execute(query_matches, {
                "league_id": league_identifier,
                "league_name": league_identifier.strip().lower()
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





def scan_and_update_league_profiles() -> Dict[str, Any]:
    """
    Escanea la base de datos para identificar todas las ligas/competiciones,
    las clasifica por su perfil estructural y actualiza `data/league_profiles.json`.
    """
    session = SessionLocal()
    counts: Dict[str, int] = {}
    try:
        query_ah = text("""
            SELECT payload
            FROM analysis_history
            WHERE payload IS NOT NULL
        """)
        rows = session.execute(query_ah).mappings().all()

        for r in rows:
            comp = extract_match_competition(dict(r))
            if comp:
                counts[comp] = counts.get(comp, 0) + 1

    except Exception as exc:
        logger.error("Error escaneando ligas de la base de datos: %s", exc)
    finally:
        session.close()

    def classify_league(name: str) -> str:
        n = name.lower().replace("é", "e").replace("á", "a").replace("í", "i").replace("ó", "o").replace("ú", "u")
        if any(k in n for k in [" 2", "2.", "serie b", "3. liga", "segunda", "championship", "liga 2"]):
            return "high_turnover_or_structural_change"
        if any(k in n for k in ["copa", "cup", "pokal", "apertura", "clausura", "libertadores", "sudamericana", "champions", "europa", "nations league", "profesional", "te apuesto", "mx", "liga 1"]):
            return "small_or_short_format"
        return "stable_high_volume"

    profiles_config, existing_leagues = load_league_profiles_config()
    updated_leagues = dict(existing_leagues)

    for l_name, cnt in sorted(counts.items()):
        current_cfg = updated_leagues.get(l_name, {})
        prof = current_cfg.get("profile") if isinstance(current_cfg, dict) else None
        if not prof:
            prof = classify_league(l_name)

        updated_leagues[l_name] = {
            "profile": prof,
            "sample_count": cnt,
        }

    full_data = {
        "_description": "Configuración jerárquica de perfiles históricos por competición para Sherlock",
        "profiles": profiles_config,
        "leagues": updated_leagues,
    }

    out_path = Path("data/league_profiles.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

    logger.info("Guardado data/league_profiles.json con %d ligas escaneadas.", len(updated_leagues))
    return full_data


def calculate_parameters(league: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula todos los parámetros matemáticos a partir de los datos históricos respetando el perfil de la liga."""
    if not records:
        logger.warning("No se encontraron partidos para la liga '%s'. Retornando parámetros por defecto.", league)
        engine = LeagueMathEngine()
        return {
            "league": league,
            "sample_size": 0,
            "averages": engine.defaults,
            "dispersions": {"corners": 0.05, "cards": 0.05, "shots": 0.05},
            "profile_used": "default",
        }

    profile = get_league_profile(league)

    # Promedios esperados usando el half-life y min_effective_sample_size del perfil
    avgs = LeagueMathEngine.compute_league_averages(
        historical_matches=records,
        half_life_days=profile["league_prior_half_life_days"],
        min_effective_sample_size=profile["min_effective_sample_size"],
    )

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
        "profile_used": profile,
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
    if isinstance(params.get("profile_used"), dict):
        print(f" Half-Life de Liga   : {params['profile_used'].get('league_prior_half_life_days')} días")
        print(f" Half-Life de Equipo : {params['profile_used'].get('team_half_life_matches')} partidos")
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
    parser.add_argument("--scan", action="store_true", help="Escanear ligas de la BD y actualizar data/league_profiles.json")
    parser.add_argument("--all", action="store_true", help="Calcular parámetros para todas las ligas escaneadas")
    parser.add_argument("--per-match", action="store_true", help="Calcular parámetros e historia previa partido por partido")

    args = parser.parse_args()

    if args.scan or args.all:
        logger.info("Escaneando ligas de la BD y actualizando data/league_profiles.json...")
        profiles_config = scan_and_update_league_profiles()

        if args.all:
            leagues_dict = profiles_config.get("leagues", {})
            all_params = {}
            for l_name in leagues_dict:
                records = fetch_historical_matches_by_league(l_name)
                params = calculate_parameters(l_name, records)
                all_params[l_name] = params
                print_summary(params)

            out_params = Path("data/calculated_league_params.json")
            out_params.parent.mkdir(parents=True, exist_ok=True)
            with open(out_params, "w", encoding="utf-8") as f:
                json.dump(all_params, f, ensure_ascii=False, indent=2)
            logger.info("Guardados parámetros calculados para %d ligas en data/calculated_league_params.json.", len(all_params))
            return

        if not args.league:
            return

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
