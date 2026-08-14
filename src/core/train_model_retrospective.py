import requests
import json
import logging
from datetime import datetime
from src.core.database import get_db
from src.core.domain import AnalysisHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_season_stats_for_team(db, team_name: str, sport: str, target_date: datetime):
    """
    Busca todos los partidos históricos de un equipo que se hayan jugado ESTRICTAMENTE 
    ANTES de target_date (para evitar data leakage).
    
    A partir de esos partidos (revisando si fue local/visitante), acumula las estadísticas
    y devuelve un diccionario con los promedios calculados compatibles con `home_stats` / `away_stats`.
    Si el equipo no tiene partidos jugados antes de `target_date`, retorna None.
    """
    if not target_date:
        return None

    # Buscar partidos anteriores donde el equipo sea local (match_date < target_date)
    home_matches = db.query(AnalysisHistory).filter(
        AnalysisHistory.sport == sport,
        AnalysisHistory.match_title.startswith(f"{team_name} vs "),
        AnalysisHistory.match_date < target_date,
        AnalysisHistory.final_score_home.isnot(None)
    ).all()
    
    # Buscar partidos anteriores donde el equipo sea visitante (match_date < target_date)
    away_matches = db.query(AnalysisHistory).filter(
        AnalysisHistory.sport == sport,
        AnalysisHistory.match_title.endswith(f" vs {team_name}"),
        AnalysisHistory.match_date < target_date,
        AnalysisHistory.final_score_home.isnot(None)
    ).all()
    
    total_played = len(home_matches) + len(away_matches)
    
    # Instrucción Data Leakage: Si no hay partidos anteriores en DB antes de target_date, retorna None.
    if total_played == 0:
        return None
        
    stats = {
        "name": team_name,
        "matches_home": len(home_matches),
        "matches_away": len(away_matches),
        "matches_played": total_played,
        "goals_scored": 0,
        "goals_conceded": 0,
        "corners": 0,
        "corners_conceded": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "shots": 0,
        "shots_on_target": 0,
        "fouls": 0,
        "offsides": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0
    }
    
    # Acumular stats de local
    for m in home_matches:
        stats["goals_scored"] += (m.final_score_home or 0)
        stats["goals_conceded"] += (m.final_score_away or 0)
        stats["corners"] += (m.final_corners_home or 0)
        stats["corners_conceded"] += (m.final_corners_away or 0)
        stats["yellow_cards"] += (m.final_yellow_cards_home or 0)
        stats["red_cards"] += (m.final_red_cards_home or 0)
        stats["shots"] += (m.final_shots_home or 0)
        stats["shots_on_target"] += (m.final_shots_on_target_home or 0)
        stats["fouls"] += (m.final_fouls_home or 0)
        stats["offsides"] += (m.final_offsides_home or 0)
        
        if m.final_score_home is not None and m.final_score_away is not None:
            if m.final_score_home > m.final_score_away:
                stats["wins"] += 1
            elif m.final_score_home == m.final_score_away:
                stats["draws"] += 1
            else:
                stats["losses"] += 1
            
    # Acumular stats de visitante
    for m in away_matches:
        stats["goals_scored"] += (m.final_score_away or 0)
        stats["goals_conceded"] += (m.final_score_home or 0)
        stats["corners"] += (m.final_corners_away or 0)
        stats["corners_conceded"] += (m.final_corners_home or 0)
        stats["yellow_cards"] += (m.final_yellow_cards_away or 0)
        stats["red_cards"] += (m.final_red_cards_away or 0)
        stats["shots"] += (m.final_shots_away or 0)
        stats["shots_on_target"] += (m.final_shots_on_target_away or 0)
        stats["fouls"] += (m.final_fouls_away or 0)
        stats["offsides"] += (m.final_offsides_away or 0)
        
        if m.final_score_home is not None and m.final_score_away is not None:
            if m.final_score_away > m.final_score_home:
                stats["wins"] += 1
            elif m.final_score_home == m.final_score_away:
                stats["draws"] += 1
            else:
                stats["losses"] += 1

    # Calcular promedios históricos
    stats["goals_per_game"] = stats["goals_scored"] / total_played
    stats["goals_conceded_per_game"] = stats["goals_conceded"] / total_played
    stats["corners_per_game"] = stats["corners"] / total_played
    stats["corners_conceded_per_game"] = stats["corners_conceded"] / total_played
    stats["yellow_cards_per_game"] = stats["yellow_cards"] / total_played
    stats["shots_per_game"] = stats["shots"] / total_played
    stats["shots_on_target_per_game"] = stats["shots_on_target"] / total_played
    stats["fouls_per_game"] = stats["fouls"] / total_played
    stats["offside_per_game"] = stats["offsides"] / total_played
    
    # Defaults para fallbacks
    stats["possession_pct"] = 50.0 
    stats["xg_per_game"] = stats["goals_per_game"]
    stats["balls_recovered_per_game"] = 12.0
    
    return stats


def get_training_data():
    db = next(get_db())
    
    # 1. Obtener partidos históricos ordenados por fecha
    history_list = db.query(AnalysisHistory).filter(
        AnalysisHistory.final_score_home.isnot(None)
    ).order_by(AnalysisHistory.match_date.asc()).all()
    
    records = []
    
    for h in history_list:
        try:
            payload = json.loads(str(h.payload)) if isinstance(h.payload, str) else h.payload
            
            # Obtener nombres de los equipos
            home_team_name = payload.get("home", {}).get("name") if isinstance(payload, dict) else None
            away_team_name = payload.get("away", {}).get("name") if isinstance(payload, dict) else None
            sport = payload.get("sport", "football") if isinstance(payload, dict) else "football"
            
            if not home_team_name or not away_team_name:
                if h.match_title and " vs " in h.match_title:
                    parts = h.match_title.split(" vs ", 1)
                    home_team_name = home_team_name or parts[0].strip()
                    away_team_name = away_team_name or parts[1].strip()

            if not home_team_name or not away_team_name:
                continue

            # Determinar fecha del partido
            match_date = h.match_date or h.date
            
            # Reconstruir las stats retrospectivamente (match_date < target_date)
            home_stats = fetch_season_stats_for_team(db, home_team_name, sport, match_date)
            away_stats = fetch_season_stats_for_team(db, away_team_name, sport, match_date)
            
            # Si cualquiera de los dos retorna None, descartar este partido del entrenamiento
            if not home_stats or not away_stats:
                logger.info(f"Omitiendo partido {home_team_name} vs {away_team_name} ({match_date}) - No hay stats previas.")
                continue

            # Calcular suma de tarjetas (amarillas + 2*rojas)
            home_yellow = getattr(h, "final_yellow_cards_home", 0) or 0
            home_red = getattr(h, "final_red_cards_home", 0) or 0
            away_yellow = getattr(h, "final_yellow_cards_away", 0) or 0
            away_red = getattr(h, "final_red_cards_away", 0) or 0

            home_cards_val = home_yellow + (home_red * 2)
            away_cards_val = away_yellow + (away_red * 2)

            y_cards_home = getattr(h, "final_yellow_cards_home", 0) or 0
            r_cards_home = getattr(h, "final_red_cards_home", 0) or 0
            y_cards_away = getattr(h, "final_yellow_cards_away", 0) or 0
            r_cards_away = getattr(h, "final_red_cards_away", 0) or 0

            # Construir el record de entrenamiento con nomenclatura ORM y Flat keys
            record = {
                "home_stats": home_stats,
                "away_stats": away_stats,
                
                "final_score_home": h.final_score_home or 0,
                "final_score_away": h.final_score_away or 0,
                
                "final_corners_home": getattr(h, "final_corners_home", 0) or 0,
                "final_corners_away": getattr(h, "final_corners_away", 0) or 0,
                
                "final_yellow_cards_home": y_cards_home,
                "final_yellow_cards_away": y_cards_away,
                "final_red_cards_home": r_cards_home,
                "final_red_cards_away": r_cards_away,
                
                "final_shots_home": getattr(h, "final_shots_home", 0) or 0,
                "final_shots_away": getattr(h, "final_shots_away", 0) or 0,
                
                "final_shots_on_target_home": getattr(h, "final_shots_on_target_home", 0) or 0,
                "final_shots_on_target_away": getattr(h, "final_shots_on_target_away", 0) or 0,
                
                # Por si las flat keys también se requieren
                "home_corners": getattr(h, "final_corners_home", 0) or 0,
                "away_corners": getattr(h, "final_corners_away", 0) or 0,
                "home_cards": y_cards_home + (r_cards_home * 2),
                "away_cards": y_cards_away + (r_cards_away * 2),
                "home_shots": getattr(h, "final_shots_home", 0) or 0,
                "away_shots": getattr(h, "final_shots_away", 0) or 0,
                "home_shots_target": getattr(h, "final_shots_on_target_home", 0) or 0,
                "away_shots_target": getattr(h, "final_shots_on_target_away", 0) or 0,
            }
            records.append(record)
            logger.info(f"Agregado a training set: {home_team_name} vs {away_team_name} ({match_date})")
            
        except Exception as e:
            logger.error(f"Error procesando partido {getattr(h, 'id', 'unknown')}: {e}")
            
    db.close()
    return records


def train():
    logger.info("Extrayendo data histórica para construir features retrospectivas...")
    records = get_training_data()
    logger.info(f"Se lograron construir {len(records)} registros de entrenamiento válidos.")
    
    if len(records) < 80:
        logger.warning("⚠️ Advertencia: Tienes menos de 80 partidos válidos para entrenamiento. El modelo podría rechazar entrenar y usar el fallback heurístico.")
        
    if len(records) > 0:
        logger.info("Enviando datos al endpoint de entrenamiento...")
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/ml/train", 
                json={"records": records}
            )
            
            if response.status_code == 200:
                logger.info("✅ Entrenamiento exitoso!")
                print(json.dumps(response.json(), indent=2))
            else:
                logger.error(f"❌ Error en el entrenamiento: {response.status_code}")
                logger.error(response.text)
        except requests.exceptions.ConnectionError:
            logger.error("❌ No se pudo conectar a la API. Asegúrate de que el servidor FastAPI esté corriendo en http://localhost:8000")
    else:
        logger.error("❌ No hay datos suficientes para entrenar. El script no generó ningún registro válido.")

if __name__ == "__main__":
    train()