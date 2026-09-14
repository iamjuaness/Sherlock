from datetime import datetime, timezone
from fastapi.testclient import TestClient
from src.ui.api.main import app
from src.core.math_engine import LeagueMathEngine

client = TestClient(app)

def test_ticket1_missing_match_date_returns_400():
    """Ticket 1: Guardar partido sin fecha debe responder 400 Bad Request y detener el flujo."""
    payload = {
        "sport": "football",
        "match_title": "Real Madrid vs Barcelona",
        "match_date": None,  # Fecha nula
        "payload": {"competition": "LaLiga"}
    }
    response = client.post("/api/v1/analysis", json=payload)
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "Fecha del partido no detectada" in detail or "inválida" in detail

def test_ticket3_corner_averages_last_round_and_current_season():
    """Ticket 3: Promedio de corners toma la última jornada o temporada actual sin 9.5 hardcoded."""
    matches = [
        # Jornada previa 1
        {
            "match_title": "Team X vs Team Y",
            "match_date": "2026-08-15T18:00:00Z",
            "final_corners_home": 3,
            "final_corners_away": 3,
        },
        # Jornada previa 2 (Última jornada completada)
        {
            "match_title": "Team A vs Team B",
            "match_date": "2026-09-05T18:00:00Z",
            "final_corners_home": 6,
            "final_corners_away": 4,
        },
        {
            "match_title": "Team C vs Team D",
            "match_date": "2026-09-05T20:00:00Z",
            "final_corners_home": 8,
            "final_corners_away": 2,
        },
    ]

    ref_date = "2026-09-10T15:00:00Z"
    corners_res = LeagueMathEngine.compute_last_round_corner_averages(matches, reference_date=ref_date)

    assert corners_res["source"] == "last_round"
    assert corners_res["last_round_date"] == "2026-09-05"
    # (6+8)/2 = 7 home, (4+2)/2 = 3 away => Total = 10.0
    assert corners_res["home_corners"] == 7.0
    assert corners_res["away_corners"] == 3.0
    assert corners_res["avg_corners_per_game"] == 10.0
