from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.core.domain import Base, Competition, Sport
from src.core.entity_resolver import sync_sofascore_competition

PRIMERA_A = {
    "id": 11539, "name": "Primera A", "slug": "primera-a-apertura", "tier": 1, "userCount": 25852,
    "category": "Colombia", "country": "Colombia", "countryCode": "CO",
    "primaryColor": "#002c6d", "secondaryColor": "#00afcf", "logoId": 323457,
    "season": {"id": 88503, "name": "Liga DIMAYOR 2026", "year": "2026"},
}


def _db():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_sync_creates_then_updates_without_duplicates():
    db = _db()
    assert sync_sofascore_competition(db, PRIMERA_A) == "created"
    assert sync_sofascore_competition(db, {**PRIMERA_A, "season": {"id": 99, "year": "2027"}}) == "updated"
    rows = db.query(Competition).all()
    assert len(rows) == 1
    c = rows[0]
    assert (c.external_id, c.season_id, c.season_year, c.tier, c.country_code, c.active) == (
        "11539", "99", "2027", 1, "CO", True,
    )
    assert c.season_name == "Liga DIMAYOR 2026"  # campo ausente no pisa el guardado


def test_sync_matches_existing_row_by_name_and_keeps_its_name():
    db = _db()
    db.add(Competition(sport=Sport.FOOTBALL, name="Ñandú Liga"))
    db.commit()
    sync_sofascore_competition(db, {"id": 5, "name": "ñandú liga", "season": {"id": 1, "year": "2026"}})
    rows = db.query(Competition).all()
    assert len(rows) == 1 and rows[0].name == "Ñandú Liga" and rows[0].external_id == "5"


def test_sync_alias_matches_local_name():
    db = _db()
    db.add(Competition(sport=Sport.FOOTBALL, name="Campeonato Brasileiro Série A"))
    db.commit()
    sync_sofascore_competition(db, {"id": 325, "name": "Brasileirão Betano", "alias": "Campeonato Brasileiro Série A"})
    assert db.execute(text("select count(*) from competitions")).scalar() == 1


def _liga_mx(db):
    base = {"category": "Mexico", "countryCode": "MX", "tier": 1}
    sync_sofascore_competition(db, {**base, "id": 11620, "name": "Liga MX, Clausura",
                                    "season": {"id": 87699, "year": "2025/2026"}})
    sync_sofascore_competition(db, {**base, "id": 11621, "name": "Liga MX, Apertura",
                                    "season": {"id": 96191, "year": "2026"}})


def test_liga_mx_is_one_competition_with_two_sources():
    db = _db()
    _liga_mx(db)
    comp = db.query(Competition).one()
    assert comp.name == "Liga MX"
    assert {s.stage: s.external_id for s in comp.sources} == {"Clausura": "11620", "Apertura": "11621"}
    assert (comp.external_id, comp.season_id) == ("11621", "96191")  # espejo = fuente con temporada más nueva


def test_discovered_is_inactive_and_never_overwrites():
    db = _db()
    sync_sofascore_competition(db, PRIMERA_A)
    assert sync_sofascore_competition(db, {"id": 11539, "name": "Primera A", "discovered": True}) == "skipped"
    sync_sofascore_competition(db, {"id": 777, "name": "Liga Nueva", "discovered": True})
    nueva = db.query(Competition).filter_by(name="Liga Nueva").one()
    assert nueva.active is False and nueva.sources[0].synced_at is None


def test_consolidate_merges_staged_and_legacy_rows_and_moves_picks():
    from datetime import datetime

    from src.core.domain import AnalysisHistory
    from src.core.entity_resolver import consolidate_competitions

    db = _db()
    db.add_all([
        Competition(sport=Sport.FOOTBALL, name="Primera A", external_id="11539", season_id="88503", active=True),
        Competition(sport=Sport.FOOTBALL, name="Liga DIMAYOR"),
        Competition(sport=Sport.FOOTBALL, name="Liga MX"),
        Competition(sport=Sport.FOOTBALL, name="Liga MX, Apertura", external_id="11621", season_id="96191", active=True),
        Competition(sport=Sport.FOOTBALL, name="Liga MX, Clausura", external_id="11620", season_id="87699", active=True),
    ])
    db.commit()
    now = datetime.utcnow()
    h = AnalysisHistory(sport=Sport.FOOTBALL, match_title="A vs B", payload="{}", date=now, match_date=now,
                        competition="Liga DIMAYOR")
    db.add(h)
    db.commit()

    assert consolidate_competitions(db.connection()) == 3
    db.commit()
    db.expire_all()
    names = sorted(c.name for c in db.query(Competition).all())
    assert names == ["Liga MX", "Primera A"]
    primera = db.query(Competition).filter_by(name="Primera A").one()
    assert db.get(AnalysisHistory, h.id).competition_id == primera.id
    liga_mx = db.query(Competition).filter_by(name="Liga MX").one()
    assert {s.stage for s in liga_mx.sources} == {"Apertura", "Clausura"}
    assert consolidate_competitions(db.connection()) == 0  # idempotente

    h2 = AnalysisHistory(sport=Sport.FOOTBALL, match_title="C vs D", payload="{}", date=now, match_date=now,
                         competition="Liga DIMAYOR")
    h3 = AnalysisHistory(sport=Sport.FOOTBALL, match_title="E vs F", payload="{}", date=now, match_date=now,
                         competition="Liga MX, Apertura")
    db.add_all([h2, h3])
    db.commit()
    assert h2.competition_id == primera.id  # alias resuelve a la liga canónica
    assert (h3.competition_id, h3.stage) == (liga_mx.id, "Apertura")
