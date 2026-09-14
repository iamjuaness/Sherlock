import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from src.ui.api.main import app, PROFITABLE_LEAGUES_PATH

client = TestClient(app)

def test_save_analysis_respects_profitable_leagues(tmp_path, monkeypatch):
    """
    Verifica que al guardar un análisis sin count_in_profitability explícito:
    - Si la liga está en profitable_leagues.json, count_in_profitability es True.
    - Si la liga NO está en profitable_leagues.json, count_in_profitability es False.
    """
    fake_leagues_file = tmp_path / "profitable_leagues.json"
    fake_leagues_file.write_text(json.dumps(["Premier League", "LaLiga"]), encoding="utf-8")
    
    import src.ui.api.main as main_module
    monkeypatch.setattr(main_module, "PROFITABLE_LEAGUES_PATH", str(fake_leagues_file))
    
    # 1. Liga rentable: Premier League
    payload_profitable = {
        "sport": "football",
        "match_title": "Arsenal vs Chelsea",
        "match_date": "2026-10-01T15:00:00Z",
        "payload": {"competition": "Premier League"},
        "has_real_stats": True
    }
    res_prof = client.post("/api/v1/analysis", json=payload_profitable)
    assert res_prof.status_code == 200
    data_prof = res_prof.json()
    assert data_prof["count_in_profitability"] is True

    # 2. Liga NO rentable: Liga 2
    payload_non_profitable = {
        "sport": "football",
        "match_title": "Equipo A vs Equipo B",
        "match_date": "2026-10-02T15:00:00Z",
        "payload": {"competition": "Liga 2 No Rentable"},
        "has_real_stats": True
    }
    res_non_prof = client.post("/api/v1/analysis", json=payload_non_profitable)
    assert res_non_prof.status_code == 200
    data_non_prof = res_non_prof.json()
    assert data_non_prof["count_in_profitability"] is False
