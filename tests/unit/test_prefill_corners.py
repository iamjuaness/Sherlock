"""
Tests para verificar el cálculo de corners por partido de la liga/temporada
en el momento en que Watson manda los datos a Sherlock (/api/v1/prefill).
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.ui.api.main import app, _compute_league_season_corners, push_prefill, prefill_store


@pytest.fixture
def client():
    return TestClient(app)


def test_compute_league_season_corners_primera_a_real_db():
    """
    Verifica que para 'Primera A' y temporada '2026', se calcule el promedio real
    de los partidos presentes en la base de datos (9.05).
    """
    avg = _compute_league_season_corners("Primera A", "2026")
    assert avg is not None
    assert round(avg, 2) == 9.05


def test_compute_league_season_corners_custom_session():
    """
    Verifica la función de cálculo con una sesión simulada en memoria
    para probar un promedio exacto esperado (ej. 8.99).
    La query ahora retorna 4 columnas: (corners_home, corners_away, match_date, date).
    """
    from datetime import datetime as _dt
    mock_session = MagicMock()
    # 99 partidos con 9 corners y 1 partido con 8 corners → avg = 8.99
    # Cada fila: (corners_home, corners_away, match_date, date)
    rows = []
    sample_date = _dt(2026, 3, 15)  # dentro de temporada 2026
    for _ in range(99):
        rows.append((5.0, 4.0, sample_date, None))   # 9 corners
    rows.append((4.0, 4.0, sample_date, None))         # 8 corners

    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    # La función llama a .filter().filter().order_by().all() para el path de temporada
    # y .filter().order_by().limit().all() para el fallback.
    # Con MagicMock, cada llamada devuelve un MagicMock que encadena.
    mock_chain = MagicMock()
    mock_query.filter.return_value = mock_chain
    mock_chain.filter.return_value = mock_chain
    mock_chain.order_by.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.all.return_value = rows

    computed = _compute_league_season_corners("Primera A", "2026", db_session=mock_session)
    assert computed == 8.99


def test_push_prefill_calculates_and_sets_corners():
    """
    Verifica que al mandar datos desde Watson a /api/v1/prefill:
    1. Obtiene el nombre de la liga ('Primera A') y temporada ('2026').
    2. Calcula los corners por partido.
    3. Llena league_stats.avg_corners_per_game en el payload que recibe el dashboard.
    """
    import asyncio

    watson_payload = {
        "competition": "Primera A",
        "season": "2026",
        "sport": "football",
        "home": {"name": "Millonarios"},
        "away": {"name": "Santa Fe"},
        "league_stats": {
            "avg_goals_per_game": 2.3,
            "avg_corners_per_game": 9.5,  # default de Sofascore / Watson
        }
    }

    res = asyncio.run(push_prefill(watson_payload))
    assert res["status"] == "ok"

    from src.ui.api.main import prefill_store
    assert prefill_store is not None
    assert "league_stats" in prefill_store
    assert prefill_store["league_stats"]["avg_corners_per_game"] == 9.05


def test_prefill_api_endpoint(client):
    """
    Prueba el endpoint HTTP POST /api/v1/prefill y GET /api/v1/prefill.
    """
    watson_payload = {
        "competition": "Primera A",
        "season": "2026",
        "home": {"name": "Nacional"},
        "away": {"name": "Junior"},
        "league_stats": {
            "avg_goals_per_game": 2.1,
            "avg_corners_per_game": 9.5
        }
    }

    post_resp = client.post("/api/v1/prefill", json=watson_payload)
    assert post_resp.status_code == 200

    get_resp = client.get("/api/v1/prefill")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["pending"] is True
    # avg_corners_per_game debe haber sido enriquecido para que el frontend lo cargue en fb-league-corners
    assert data["payload"]["league_stats"]["avg_corners_per_game"] == 9.05
