from datetime import datetime, timezone
from src.core.math_engine import LeagueMathEngine

def test_promedio_corners_ultima_jornada():
    # Simulación de partidos de Champions League (mismo escenario planteado por el usuario)
    partidos = [
        # Jornada del 26 de agosto (3 partidos, promedian 10 corners total)
        {
            "match_title": "Team A vs Team B",
            "match_date": "2026-08-26T20:00:00Z",
            "final_corners_home": 6,
            "final_corners_away": 4,
        },
        {
            "match_title": "Team C vs Team D",
            "match_date": "2026-08-26T20:00:00Z",
            "final_corners_home": 5,
            "final_corners_away": 5,
        },
        # Jornada del 9 de septiembre (última jornada jugada antes del 12 sept: 3 partidos)
        # Partido 1: 5 home, 3 away = 8
        {
            "match_title": "PSG vs Bayern",
            "match_date": "2026-09-09T20:00:00Z",
            "final_corners_home": 5,
            "final_corners_away": 3,
        },
        # Partido 2: 7 home, 4 away = 11
        {
            "match_title": "Real Madrid vs Man City",
            "match_date": "2026-09-09T20:00:00Z",
            "final_corners_home": 7,
            "final_corners_away": 4,
        },
        # Partido 3: 4 home, 2 away = 6
        {
            "match_title": "Inter vs Barca",
            "match_date": "2026-09-09T20:00:00Z",
            "final_corners_home": 4,
            "final_corners_away": 2,
        },
        # Partido del futuro (12 sept - el que estamos analizando hoy)
        {
            "match_title": "Arsenal vs Napoli",
            "match_date": "2026-09-12T20:00:00Z",
            "final_corners_home": 8,
            "final_corners_away": 8,
        },
    ]

    fecha_referencia = "2026-09-12T20:00:00Z"
    res = LeagueMathEngine.compute_last_round_corner_averages(partidos, reference_date=fecha_referencia)

    assert res["source"] == "last_round"
    assert res["last_round_date"] == "2026-09-09"
    # Promedio home del 9 de sep: (5 + 7 + 4) / 3 = 16 / 3 = 5.3333...
    # Promedio away del 9 de sep: (3 + 4 + 2) / 3 = 9 / 3 = 3.0
    # Promedio total: 5.3333 + 3.0 = 8.3333...
    assert round(res["home_corners"], 2) == 5.33
    assert round(res["away_corners"], 2) == 3.0
    assert round(res["avg_corners_per_game"], 2) == 8.33
