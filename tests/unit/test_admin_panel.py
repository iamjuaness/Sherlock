"""Unit and Integration tests for Sherlock Admin Panel."""

import json
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.core.database import Base
from src.core.domain import AnalysisHistory, Competition, AdminAuditLog
from src.ui.api.main import app
from src.services.admin_stats_service import calculate_dashboard_summary, get_grouped_stats
from src.services.admin_picks_service import query_picks, get_pick_detail, update_operational_fields
from src.services.admin_database_service import list_whitelisted_tables, get_table_schema, update_table_row


@pytest.fixture
def db_session(tmp_path):
    """Create a temporary SQLite DB session for testing admin functionality."""
    db_path = tmp_path / "test_admin.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def test_admin_formulas_kpis(db_session: Session):
    """Verify exact financial and statistical formulas (ROI, Hit Rate, Break-even, Net Profit)."""
    # Seed analysis records
    sample_picks_1 = [
        {"selection": "home_win", "market": "1X2", "odds": 2.0, "model_prob": 0.60, "stake_units": 1.0, "status": "won", "is_publishable": True},
        {"selection": "over_2.5", "market": "Goals", "odds": 1.80, "model_prob": 0.65, "stake_units": 1.0, "status": "lost", "is_publishable": True},
    ]

    ah1 = AnalysisHistory(
        sport="football",
        date=datetime.utcnow(),
        match_date=datetime.utcnow(),
        match_title="Team A vs Team B",
        payload=json.dumps({"test": "data"}),
        picks_calculados=json.dumps(sample_picks_1),
        competition="Premier League",
        bookmaker="Bet365",
        stake_units=2.0,
        count_in_profitability=True,
        final_score_home=2,
        final_score_away=1,
    )
    db_session.add(ah1)
    db_session.commit()

    summary = calculate_dashboard_summary(db_session)
    kpis = summary.kpis

    # Won: 1 (odds 2.0, profit = +1.0u), Lost: 1 (odds 1.8, profit = -1.0u), Net profit = 0.0u
    assert kpis.picks_resolved == 2
    assert kpis.picks_won == 1
    assert kpis.picks_lost == 1
    assert kpis.hit_rate == 50.0  # (1 / 2) * 100
    assert kpis.net_profit == 0.0
    assert kpis.roi == 0.0  # (0.0 / 2.0) * 100
    assert kpis.avg_odds == 1.9  # (2.0 + 1.8) / 2
    assert kpis.break_even_rate == round((1.0 / 1.9) * 100, 2)  # ~52.63%


def test_picks_query_pagination_and_sorting(db_session: Session):
    """Test picks querying, server-side pagination, and column validation."""
    for i in range(15):
        ah = AnalysisHistory(
            sport="football",
            date=datetime.utcnow(),
            match_date=datetime.utcnow(),
            match_title=f"Match {i}",
            payload="{}",
            competition=f"League {i % 2}",
            bookmaker="Pinnacle",
            count_in_profitability=True,
        )
        db_session.add(ah)
    db_session.commit()

    picks, meta = query_picks(db_session, page=1, page_size=50, sort_by="match_date", sort_dir="desc")
    assert meta.total_records == 15
    assert len(picks) == 15
    assert meta.page == 1
    assert meta.has_next is False


def test_operational_fields_update_and_audit(db_session: Session):
    """Test authorized operational field updates and creation of audit log."""
    ah = AnalysisHistory(
        sport="football",
        date=datetime.utcnow(),
        match_title="Real Madrid vs Barcelona",
        payload="{}",
        competition="La Liga",
        bookmaker="Bwin",
        count_in_profitability=True,
    )
    db_session.add(ah)
    db_session.commit()

    # Update operational fields
    from src.schemas.admin import OperationalFieldsUpdate
    payload = OperationalFieldsUpdate(competition="LaLiga EA Sports", bookmaker="Bet365", count_in_profitability=False)
    updated = update_operational_fields(db_session, ah.id, payload, admin_user="test_admin")

    assert updated.competition == "LaLiga EA Sports"
    assert updated.bookmaker == "Bet365"
    assert updated.count_in_profitability is False

    # Check Audit Log created
    logs = db_session.query(AdminAuditLog).filter(AdminAuditLog.target_table == "analysis_history").all()
    assert len(logs) == 1
    assert logs[0].action == "update_operational_fields"
    assert logs[0].admin_user == "test_admin"


def test_database_explorer_whitelist_security(db_session: Session):
    """Test database explorer whitelisting and prevention of forbidden modifications."""
    tables = list_whitelisted_tables(db_session)
    table_names = [t.name for t in tables]
    assert "analysis_history" in table_names
    assert "competitions" in table_names

    # Test reading schema
    schema = get_table_schema(db_session, "analysis_history")
    assert schema.table_name == "analysis_history"
    col_names = [c.name for c in schema.columns]
    assert "id" in col_names
    assert "competition" in col_names

    ah = AnalysisHistory(
        sport="football",
        date=datetime.utcnow(),
        match_title="Test Match",
        payload="{}",
    )
    db_session.add(ah)
    db_session.commit()

    # Test trying to edit non-editable primary key column fails
    from src.schemas.admin import DatabaseRowUpdate
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        update_table_row(
            db_session,
            table_name="analysis_history",
            record_id=ah.id,
            update_payload=DatabaseRowUpdate(updates={"id": "prohibited_id_change"}),
            admin_user="test_admin",
        )
    assert exc_info.value.status_code == 400
    assert "No está permitido editar la columna 'id'" in exc_info.value.detail



def test_admin_api_endpoints():
    """Integration test for Admin API routes using FastAPI TestClient."""
    client = TestClient(app)

    # Test /admin redirect
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "/admin/dashboard"

    # Test HTML page renders
    resp_dash = client.get("/admin/dashboard")
    assert resp_dash.status_code == 200
    assert "Sherlock Admin Panel" in resp_dash.text

    # Test API dashboard summary
    resp_api = client.get("/api/v1/admin/dashboard/summary")
    assert resp_api.status_code == 200
    data = resp_api.json()
    assert "kpis" in data
    assert "quality" in data
    assert "charts" in data

    # Test API database tables
    resp_tables = client.get("/api/v1/admin/database/tables")
    assert resp_tables.status_code == 200
    assert isinstance(resp_tables.json(), list)


def test_is_publishable_filter_and_picks_export(db_session: Session):
    """Test filtering picks by is_publishable and exporting to Excel and CSV formats."""
    sample_picks = [
        {"selection": "home_win", "market": "1X2", "odds": 2.10, "model_prob": 0.60, "stake_units": 1.0, "status": "won", "is_publishable": True},
        {"selection": "away_win", "market": "1X2", "odds": 3.50, "model_prob": 0.35, "stake_units": 1.0, "status": "lost", "is_publishable": False},
    ]

    ah = AnalysisHistory(
        sport="football",
        date=datetime.utcnow(),
        match_date=datetime.utcnow(),
        match_title="Publishable Test Match",
        payload="{}",
        picks_calculados=json.dumps(sample_picks),
        competition="Test League",
        bookmaker="Pinnacle",
        count_in_profitability=True,
    )
    db_session.add(ah)
    db_session.commit()

    # Query publishable picks only
    pub_picks, meta_pub = query_picks(db_session, is_publishable=True)
    assert len(pub_picks) == 1
    assert pub_picks[0].is_publishable is True
    assert pub_picks[0].selection == "home_win"

    # Query non-publishable picks only
    non_pub_picks, meta_non = query_picks(db_session, is_publishable=False)
    assert len(non_pub_picks) == 1
    assert non_pub_picks[0].is_publishable is False
    assert non_pub_picks[0].selection == "away_win"

    # Query all picks without filtering is_publishable
    all_picks, meta_all = query_picks(db_session, is_publishable=None)
    assert len(all_picks) == 2

    # Test export function directly
    from src.services.admin_picks_service import export_picks_file
    excel_content, mime_excel, fname_excel = export_picks_file(db_session, export_format="excel", is_publishable=True)
    assert mime_excel == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert fname_excel.endswith(".xlsx")
    assert len(excel_content) > 0

    csv_content, mime_csv, fname_csv = export_picks_file(db_session, export_format="csv", is_publishable=True)
    assert mime_csv == "text/csv; charset=utf-8"
    assert fname_csv.endswith(".csv")
    csv_str = csv_content.decode("utf-8-sig")
    assert "ID Partido" in csv_str
    assert "Detalle de Picks" not in csv_str  # Sheet name only in Excel
    assert "home_win" in csv_str
    assert "away_win" not in csv_str

    # Test API endpoint for picks export via TestClient
    client = TestClient(app)
    resp_export = client.get("/api/v1/admin/picks/export?export_format=excel&is_publishable=true")
    assert resp_export.status_code == 200
    assert resp_export.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Test is_underdog filter
    und_picks, _ = query_picks(db_session, is_underdog=True)
    assert len(und_picks) == 1
    assert und_picks[0].is_underdog is True
    assert und_picks[0].selection == "away_win"

    # Test category filter (profesional and underdog)
    prof_picks, _ = query_picks(db_session, category="profesional")
    assert len(prof_picks) == 1
    assert prof_picks[0].category.lower() == "profesional"

    und_cat_picks, _ = query_picks(db_session, category="underdog")
    assert len(und_cat_picks) == 1
    assert und_cat_picks[0].category.lower() == "underdog"


def test_filter_correlated_picks(db_session: Session):
    """Test deduplication of correlated picks in the same match."""
    # doublechance_draw_away (X2 / Empate o Visita) and result_home (Local / 1) have rho = -1.0 in market_correlation.json
    sample_picks = [
        {"selection": "Local", "market": "Resultado final 1X2", "odds": 2.0, "edge": 0.15, "is_publishable": True, "is_value": True, "is_blacklisted": False, "is_rule_blocked": False},
        {"selection": "X2", "market": "Doble oportunidad", "odds": 1.9, "edge": 0.10, "is_publishable": True, "is_value": True, "is_blacklisted": False, "is_rule_blocked": False},
    ]
    ah = AnalysisHistory(
        sport="football",
        date=datetime.utcnow(),
        match_date=datetime.utcnow(),
        match_title="Correlation Test Match",
        payload="{}",
        picks_calculados=json.dumps(sample_picks),
        competition="Test League",
        bookmaker="Pinnacle",
        count_in_profitability=True,
    )
    db_session.add(ah)
    db_session.commit()

    # With filter_correlated=True (default), weaker correlated pick is removed (only 1 pick remains)
    picks_filtered, _ = query_picks(db_session, filter_correlated=True)
    assert len(picks_filtered) == 1
    assert picks_filtered[0].selection == "Local"  # Higher edge pick kept

    # With filter_correlated=False, both picks are returned
    picks_all, _ = query_picks(db_session, filter_correlated=False)
    assert len(picks_all) == 2



