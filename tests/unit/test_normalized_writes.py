"""Endpoints que escriben analysis_history (Watson/Sherlock) mantienen ids de equipo/liga y temporada."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import src.ui.api.routes.results_routes as results_routes
from src.core.database import Base, get_db
from src.core.domain import AnalysisHistory
from src.ui.api.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    c = TestClient(app)
    c.session = Session
    yield c
    app.dependency_overrides.clear()


def _row(client, title):
    s = client.session()
    try:
        return s.query(AnalysisHistory).filter(AnalysisHistory.match_title == title).one()
    finally:
        s.close()


def _payload(home, away, comp="Liga X", season_year="2025/2026", season_id=777):
    return {"home": {"name": home}, "away": {"name": away}, "competition": comp,
            "season_year": season_year, "season_id": season_id}


def test_save_analysis_sets_ids_and_season(client):
    r = client.post("/api/v1/analysis", json={
        "sport": "football", "match_title": "Foo vs Bar", "match_date": "2026-01-10T20:00:00",
        "payload": _payload("Foo", "Bar")})
    assert r.status_code == 200, r.text
    row = _row(client, "Foo vs Bar")
    assert row.home_team_id and row.away_team_id and row.competition_id
    assert (row.season_id, row.season_year) == ("777", "2025/2026")


def test_quick_save_and_result_reuse_same_entities(client):
    r = client.post("/api/v1/analysis/quick-save", json=_payload("Foo", "Bar"))
    assert r.status_code == 200, r.text
    first = _row(client, "Foo vs Bar")
    results_routes._in_leagues_window = True
    r = client.post("/api/v1/result", json={
        "sport": "football", "home_team": "foo", "away_team": "Baz", "competition": "liga x",
        "season_year": "2025/2026", "season_id": 777, "start_timestamp": 1768075200,
        "event_id": 99, "final_score_home": 2, "final_score_away": 1})
    assert r.status_code == 200, r.text
    new = _row(client, "foo vs Baz")
    assert new.home_team_id == first.home_team_id          # misma entidad aunque cambie el case
    assert new.competition_id == first.competition_id
    assert new.season_id == "777"
    s = client.session()
    assert s.execute(text("select count(*) from teams")).scalar() == 3  # Foo, Bar, Baz
    assert s.execute(text("select count(*) from competitions")).scalar() == 1


def test_renames_keep_ids_consistent(client):
    for h, a in (("Foo", "Bar"), ("Baz", "Foo")):
        client.post("/api/v1/analysis/quick-save", json=_payload(h, a))
    assert client.put("/api/v1/analysis/team/Foo", params={"new_name": "Foo FC"}).json()["updated_count"] == 2
    assert client.put("/api/v1/analysis/competition/Liga X", params={"new_name": "Liga Y"}).json()["updated_count"] == 2
    s = client.session()
    assert sorted(r[0] for r in s.execute(text("select name from teams"))) == ["Bar", "Baz", "Foo FC"]
    assert [r[0] for r in s.execute(text("select name from competitions"))] == ["Liga Y"]
    row = _row(client, "Foo FC vs Bar")
    assert json.loads(row.payload)["competition"] == "Liga Y"
    # temporada sigue consultable por columna
    assert client.get("/api/v1/leagues/Liga Y/matches", params={"season": "2025/2026"}).json()


def test_payload_update_refreshes_season(client):
    r = client.post("/api/v1/analysis", json={
        "sport": "football", "match_title": "Foo vs Bar", "match_date": "2026-01-10T20:00:00",
        "payload": _payload("Foo", "Bar")})
    aid = r.json()["id"]
    r = client.post("/api/v1/analysis", json={
        "id": aid, "sport": "football", "match_title": "Foo vs Bar", "match_date": "2026-01-10T20:00:00",
        "payload": _payload("Foo", "Bar", season_year="2026/2027", season_id=888)})
    assert r.status_code == 200, r.text
    row = _row(client, "Foo vs Bar")
    assert (row.season_id, row.season_year) == ("888", "2026/2027")


def test_result_goes_to_twin_row_with_picks_when_team_names_differ(client):
    """'Amed' (análisis con picks) vs 'Amedspor' (Watson): el resultado debe llegar a la fila con picks."""
    s = client.session()
    from datetime import datetime
    from src.core.domain import Sport
    d = datetime(2026, 10, 24, 11, 0)
    s.add(AnalysisHistory(sport=Sport.FOOTBALL, match_title="Samsunspor vs Amed", payload="{}", date=d,
                          match_date=d, picks_calculados="[]", competition="Liga X"))
    s.add(AnalysisHistory(sport=Sport.FOOTBALL, match_title="Samsunspor vs Amedspor", payload="{}", date=d,
                          match_date=d, competition="Liga X", final_score_home=1, final_score_away=2))
    s.commit()
    s.close()
    r = client.post("/api/v1/result", json={
        "sport": "football", "home_team": "Samsunspor", "away_team": "Amedspor", "competition": "Liga X",
        "season_year": "2026/2027", "start_timestamp": int(d.replace(tzinfo=None).timestamp()),
        "final_score_home": 1, "final_score_away": 2})
    assert r.status_code == 200, r.text
    row = _row(client, "Samsunspor vs Amed")
    assert (row.final_score_home, row.final_score_away) == (1, 2)


def test_result_with_event_id_also_reaches_twin_row_with_picks(client):
    from datetime import datetime
    from src.core.domain import Sport
    d = datetime(2026, 10, 24, 11, 0)
    s = client.session()
    s.add(AnalysisHistory(sport=Sport.FOOTBALL, match_title="Samsunspor vs Amed", payload="{}", date=d,
                          match_date=d, picks_calculados="[]", competition="Liga X"))
    s.add(AnalysisHistory(sport=Sport.FOOTBALL, match_title="Samsunspor vs Amedspor", payload='{"event_id": 16483794}',
                          date=d, match_date=d, competition="Liga X", final_score_home=1, final_score_away=2))
    s.commit()
    s.close()
    r = client.post("/api/v1/result", json={
        "sport": "football", "home_team": "Samsunspor", "away_team": "Amedspor", "competition": "Liga X",
        "season_year": "2026/2027", "event_id": 16483794, "final_score_home": 1, "final_score_away": 2})
    assert r.status_code == 200, r.text
    row = _row(client, "Samsunspor vs Amed")
    assert (row.final_score_home, row.final_score_away) == (1, 2)
    assert json.loads(row.payload).get("event_id") == 16483794
