"""Rutas catalog de la API (extraídas de main.py)."""

from __future__ import annotations

from datetime import datetime
import json
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from src.core.database import get_db
from src.core.domain import Competition, Match, Sport, AnalysisHistory
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

    records = (
        db.query(AnalysisHistory)
        .options(
            load_only(
                AnalysisHistory.competition,
                AnalysisHistory.payload,
                AnalysisHistory.final_score_home,
            )
        )
        .filter(AnalysisHistory.final_score_home.is_(None))
        .all()
    )

    pending_set = set()
    pending_event_ids = set()
    for rec in records:
        # Use pre-extracted competition column; fall back to payload only for event_id
        comp_name = rec.competition
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
