"""Rutas catalog de la API (extraídas de main.py)."""

from __future__ import annotations

from datetime import datetime
import json
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from src.core.database import get_db
from src.core.domain import AnalysisHistory, Competition, CompetitionSource, Match, Sport
from src.ui.api.schemas import (
    CompetitionOut,
    MatchOut,
    SportOut,
)

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/sports", response_model=list[SportOut], tags=["Sports"])
def list_sports() -> list[SportOut]:
    """List available sports."""
    return [SportOut(value=s.value, label=s.value.capitalize()) for s in Sport]


## Obtener la cantidad de partidos de una liga en especifico
@router.get("/api/v1/competitions/{competition_id}/matches", tags=["Competitions"])
def list_matches_count_for_competition(competition_id: str, db: Session = Depends(get_db)):
    """Return the number of matches for a specific competition."""
    from sqlalchemy.orm import load_only

    query = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.competition == competition_id)
        .options(load_only(AnalysisHistory.id))
        .count()
    )
    return query


@router.get("/api/v1/competitions", response_model=list[CompetitionOut], tags=["Competitions"])
def list_competitions(
    sport: str | None = Query(None, description="Filter by sport (football)"),
    db: Session = Depends(get_db),
) -> list[CompetitionOut]:
    """List competitions with optional sport filter."""
    query = db.query(Competition)
    if sport:
        try:
            sport_enum = Sport(sport)
            query = query.filter(Competition.sport == sport_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")
    return [CompetitionOut.model_validate(c) for c in query.all()]


@router.get("/api/v1/competitions/catalog", tags=["Competitions"])
def competitions_catalog(include_inactive: bool = Query(False), db: Session = Depends(get_db)):
    """Catálogo para Watson: una entrada por fuente (unique-tournament) con su temporada vigente.

    id = SofaScore unique-tournament, season = season_id vigente, name = liga (Liga MX tiene 2 fuentes:
    Apertura y Clausura). `discovered`: fuente sin enriquecer (aún sin temporada).
    """
    q = (
        db.query(CompetitionSource, Competition)
        .join(Competition, CompetitionSource.competition_id == Competition.id)
    )
    if not include_inactive:
        q = q.filter(CompetitionSource.active.is_(True), Competition.active.is_(True))
    out = []
    for s, c in q.order_by(Competition.name, CompetitionSource.stage).all():
        if not str(s.external_id).isdigit():
            continue
        out.append({
            "name": c.name, "id": int(s.external_id),
            "season": int(s.season_id) if str(s.season_id or "").isdigit() else None,
            "active": bool(s.active and c.active), "stage": s.stage, "source_name": s.name,
            "season_year": s.season_year, "tier": s.tier, "grade": s.grade, "category": c.category,
            "country_code": c.country_code, "teams_count": s.teams_count, "rounds_count": s.rounds_count,
            "tables_count": s.tables_count, "discovered": s.synced_at is None,
            "synced_at": s.synced_at.isoformat() if s.synced_at else None,
        })
    return out


@router.post("/api/v1/competitions/sync", tags=["Competitions"])
def sync_competitions(payload: dict, db: Session = Depends(get_db)):
    """Watson envía unique-tournaments de SofaScore (enriquecidos o solo descubiertos); upsert en `competitions`."""
    from src.core.entity_resolver import sync_sofascore_competition

    comps = [c for c in (payload.get("competitions") or [])
             if isinstance(c, dict) and c.get("name") and c.get("id") is not None]
    res = [sync_sofascore_competition(db, c) for c in comps]
    db.commit()
    return {"status": "ok", "received": len(comps), "created": res.count("created"),
            "updated": res.count("updated"), "skipped": res.count("skipped")}


@router.put("/api/v1/competitions/{competition_id}/active", tags=["Competitions"])
def set_competition_active(competition_id: str, active: bool = Query(...), db: Session = Depends(get_db)):
    """Activa/desactiva una competencia (y todas sus fuentes) para que Watson la incluya en las extracciones."""
    comp = db.get(Competition, competition_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Competencia no encontrada")
    comp.active = active
    for s in comp.sources:
        s.active = active
    db.commit()
    return {"status": "ok", "id": comp.id, "name": comp.name, "active": active}


@router.get("/api/v1/matches", response_model=list[MatchOut], tags=["Matches"])
def list_matches(
    sport: str | None = Query(None),
    competition_id: str | None = Query(None),
    date_from: str | None = Query(None, description="ISO format YYYY-MM-DD"),
    date_to: str | None = Query(None, description="ISO format YYYY-MM-DD"),
    before_date: str | None = Query(
        None, description="Cursor: traer partidos antes de esta fecha ISO"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    """List matches with filters."""
    query = db.query(Match).options(
        joinedload(Match.home_team),
        joinedload(Match.away_team),
        joinedload(Match.competition),
        joinedload(Match.betting_lines),
    )
    if sport:
        try:
            sport_enum = Sport(sport)
            query = query.filter(Match.sport == sport_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")
    if competition_id:
        query = query.filter(Match.competition_id == competition_id)
    if date_from:
        query = query.filter(Match.date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Match.date <= datetime.fromisoformat(date_to))
    if before_date:
        query = query.filter(Match.date < datetime.fromisoformat(before_date))

    if before_date:
        query = query.order_by(Match.date.desc()).limit(limit)
    else:
        query = query.order_by(Match.date.desc()).offset(offset).limit(limit)
    return [MatchOut.model_validate(m) for m in query.all()]


@router.get("/api/v1/competitions/pending-picks", tags=["Competitions"])
def get_pending_picks_competitions(db: Session = Depends(get_db)):
    """
    Retorna las ligas y los event_ids que tienen partidos con resultados pendientes (final_score_home is None).
    """
    from sqlalchemy.orm import load_only

    # Nombre de liga desde la tabla competitions (competition_id), no solo la columna texto legacy.
    rows = (
        db.query(AnalysisHistory, Competition.name)
        .options(
            load_only(
                AnalysisHistory.competition,
                AnalysisHistory.payload,
                AnalysisHistory.final_score_home,
            )
        )
        .outerjoin(Competition, AnalysisHistory.competition_id == Competition.id)
        .filter(AnalysisHistory.final_score_home.is_(None))
        .all()
    )

    pending_set = set()
    pending_event_ids = set()
    for rec, cat_name in rows:
        comp_name = cat_name or rec.competition
        if comp_name:
            pending_set.add(comp_name)
        elif rec.payload:
            try:
                p_dict = json.loads(str(rec.payload))
                comp_name = p_dict.get("competition", {}).get("name") or p_dict.get("league_name")
                if comp_name:
                    pending_set.add(comp_name)
            except Exception:
                pass

        if rec.payload:
            try:
                p_dict = json.loads(str(rec.payload))
                ext_id = (
                    p_dict.get("match", {}).get("external_id")
                    or p_dict.get("event_id")
                    or p_dict.get("eventId")
                )
                if ext_id:
                    pending_event_ids.add(str(ext_id))
            except Exception:
                pass

    return {
        "pending_competitions": list(pending_set),
        "pending_event_ids": list(pending_event_ids),
    }
