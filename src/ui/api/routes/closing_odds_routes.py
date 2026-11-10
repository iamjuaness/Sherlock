"""Rutas closing_odds de la API (extraídas de main.py)."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from src.core.database import get_db
from src.core.domain import AnalysisHistory

from src.ui.api.shared import _normalize_betano_odds, match_closing_odds_to_pick
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/closing-odds/pending-matches", tags=["Closing Odds"])
@router.get("/api/v1/prefill/pending-closing-matches", tags=["Closing Odds"])
def get_pending_closing_odds_matches(db: Session = Depends(get_db)) -> dict:
    """
    Retorna los partidos sin resultado (final_score_home IS NULL) y próximos a empezar
    que tienen picks calculados pero requieren cuotas de cierre.
    """
    now = datetime.utcnow()
    min_date = now - timedelta(hours=2)
    max_date = now + timedelta(hours=48)

    query = db.query(AnalysisHistory).filter(
        AnalysisHistory.final_score_home.is_(None),
        AnalysisHistory.picks_calculados.isnot(None),
        or_(
            and_(AnalysisHistory.match_date >= min_date, AnalysisHistory.match_date <= max_date),
            and_(AnalysisHistory.match_date.is_(None), AnalysisHistory.date >= min_date),
        ),
    )
    matches = query.all()

    results = []
    for ah in matches:
        try:
            raw_picks = (
                json.loads(ah.picks_calculados)
                if isinstance(ah.picks_calculados, str)
                else ah.picks_calculados
            )
        except Exception:
            raw_picks = []

        if not isinstance(raw_picks, list) or len(raw_picks) == 0:
            continue

        has_all_closing = all(
            p.get("closing_odds") is not None for p in raw_picks if isinstance(p, dict)
        )

        m_dt = ah.match_date or ah.date
        match_date_str = m_dt.isoformat() if m_dt else None

        home_team = ""
        away_team = ""
        if " vs " in ah.match_title:
            parts = ah.match_title.split(" vs ")
            home_team = parts[0].strip()
            away_team = parts[1].strip()
        elif " - " in ah.match_title:
            parts = ah.match_title.split(" - ")
            home_team = parts[0].strip()
            away_team = parts[1].strip()
        else:
            home_team = ah.match_title
            away_team = ""

        results.append(
            {
                "id": ah.id,
                "match_title": ah.match_title,
                "home_team": home_team,
                "away_team": away_team,
                "competition": ah.competition or "",
                "match_date": match_date_str,
                "has_all_closing_odds": has_all_closing,
                "picks": [
                    {
                        "selection": p.get("selection") or p.get("pick") or "",
                        "market": p.get("market") or "",
                        "line": p.get("line"),
                        "odds": p.get("odds"),
                        "closing_odds": p.get("closing_odds"),
                    }
                    for p in raw_picks
                    if isinstance(p, dict)
                ],
            }
        )

    return {"status": "ok", "pending_matches": results}


@router.post("/api/v1/closing-odds/submit", tags=["Closing Odds"])
@router.post("/api/v1/prefill/closing-odds", tags=["Closing Odds"])
async def submit_closing_odds(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Guarda las cuotas de cierre para los picks de un partido en AnalysisHistory.picks_calculados.
    Asegura mantener la cuota original (opening odds) intacta en pick["odds"].
    """
    analysis_id = payload.get("analysis_id") or payload.get("id")
    match_title = payload.get("match_title")

    ah = None
    if analysis_id:
        ah = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    elif match_title:
        from src.core.entity_resolver import find_team_id, split_title

        _h, _a = split_title(match_title)
        _hid, _aid = find_team_id(db, _h), find_team_id(db, _a)
        if _hid and _aid:
            _title_filter = and_(AnalysisHistory.home_team_id == _hid, AnalysisHistory.away_team_id == _aid)
        else:
            _title_filter = AnalysisHistory.match_title.ilike(f"%{match_title}%")
        ah = (
            db.query(AnalysisHistory)
            .filter(_title_filter, AnalysisHistory.final_score_home.is_(None))
            .first()
        )

    if not ah:
        raise HTTPException(status_code=404, detail="Partido o análisis no encontrado en Sherlock.")

    if not ah.picks_calculados:
        raise HTTPException(status_code=400, detail="El partido no tiene picks calculados.")

    try:
        raw_picks = (
            json.loads(ah.picks_calculados)
            if isinstance(ah.picks_calculados, str)
            else ah.picks_calculados
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parseando picks_calculados: {e}")

    if not isinstance(raw_picks, list):
        raise HTTPException(status_code=400, detail="Estructura de picks_calculados inválida.")

    raw_odds = payload.get("odds") or payload.get("odds_data") or payload
    if isinstance(raw_odds, dict) and (
        "goals_over" in raw_odds or "home" in raw_odds or "goalsOverOdds" in raw_odds
    ):
        if "goalsOverOdds" in raw_odds:
            normalized = raw_odds
        else:
            normalized = _normalize_betano_odds(raw_odds)
    else:
        normalized = {}

    explicit_closing_map = payload.get("closing_odds_map") or {}

    updated_count = 0
    for idx, pick in enumerate(raw_picks):
        if not isinstance(pick, dict):
            continue

        exp_odd = explicit_closing_map.get(str(idx)) or explicit_closing_map.get(
            pick.get("selection")
        )
        if exp_odd is not None:
            pick["closing_odds"] = float(exp_odd)
            updated_count += 1
            continue

        if normalized:
            matched_odd = match_closing_odds_to_pick(pick, normalized)
            if matched_odd is not None and matched_odd > 1.0:
                pick["closing_odds"] = float(matched_odd)
                updated_count += 1

    ah.picks_calculados = json.dumps(raw_picks)
    ah.last_recalculated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "ok",
        "message": f"Cuotas de cierre guardadas exitosamente para {updated_count} pick(s).",
        "analysis_id": ah.id,
        "updated_picks_count": updated_count,
    }
