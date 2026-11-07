"""Rutas comparator de la API (extraídas de main.py)."""

from __future__ import annotations
import logging

from datetime import datetime
from fastapi import Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.domain import Sport, AnalysisHistory
from src.ui.api.compare_service import compare_football
from src.ui.api.compare_models import FootballCompareRequest, CompareResponse

from src.ui.api.shared import (
    _annotate_best_bookmaker,
    _apply_line_shopping,
    _enrich_with_results,
    _sse_stream,
)
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/v1/compare/football", response_model=CompareResponse, tags=["Comparator"])
async def compare_teams_football(
    request: FootballCompareRequest, db: Session = Depends(get_db)
) -> CompareResponse:
    """
    Analiza el partido y calcula TODOS los picks, aplicando line shopping
    automático si el payload trae cuotas de varias casas (odds.sources).
    """
    request, bookmaker_map = _apply_line_shopping(request)

    res = await compare_football(request, db=db)

    if bookmaker_map:
        _annotate_best_bookmaker(res, bookmaker_map, request.home.name, request.away.name)

    return await _enrich_with_results(
        Sport.FOOTBALL, request.home.name, request.away.name, res, db, match_date=request.match_date
    )


@router.post("/api/v1/compare/batch", tags=["Comparator"])
async def compare_batch_football(
    requests: list[FootballCompareRequest], db: Session = Depends(get_db)
) -> dict:
    """Procesamiento batch masivo de partidos: compara, guarda en historial y extrae picks con valor."""
    processed = 0
    errors = 0
    value_picks_total = []

    for req in requests:
        try:
            req_shopping, bmap = _apply_line_shopping(req)
            res = await compare_football(req_shopping, db=db)
            if bmap:
                _annotate_best_bookmaker(res, bmap, req.home.name, req.away.name)
            enriched = await _enrich_with_results(
                Sport.FOOTBALL, req.home.name, req.away.name, res, db, match_date=req.match_date
            )

            # Extraer picks con valor (EV positivo)
            val_picks = [
                v.model_dump() if hasattr(v, "model_dump") else v.dict()
                for v in enriched.values
                if getattr(v, "is_value", False)
            ]
            for vp in val_picks:
                vp["match"] = f"{req.home.name} vs {req.away.name}"
                vp["competition"] = req.competition
                value_picks_total.append(vp)

            # Auto-guardado en analysis_history
            m_date = req.match_date
            if not m_date and getattr(req, "start_timestamp", None):
                try:
                    m_date = datetime.utcfromtimestamp(req.start_timestamp)
                except Exception:
                    pass

            entry = AnalysisHistory(
                sport=Sport.FOOTBALL,
                match_title=f"{req.home.name} vs {req.away.name}",
                match_date=m_date,
                payload=req.model_dump() if hasattr(req, "model_dump") else req.dict(),
                picks_calculados=val_picks,
                compare_response_snapshot=enriched.model_dump()
                if hasattr(enriched, "model_dump")
                else enriched.dict(),
                competition=req.competition,
                season_id=getattr(req, "season_id", None) or getattr(req, "season", None),
                tournament_id=getattr(req, "tournament_id", None),
                has_real_stats=getattr(req, "has_real_stats", True),
            )
            db.add(entry)
            db.commit()
            processed += 1
        except Exception as e:
            db.rollback()
            errors += 1
            logging.getLogger("sherlock").warning(
                "[compare_batch_football] Error en partido %s vs %s: %s",
                req.home.name,
                req.away.name,
                e,
            )

    return {
        "status": "ok",
        "total_processed": processed,
        "total_errors": errors,
        "total_value_picks": len(value_picks_total),
        "value_picks": value_picks_total,
    }


@router.post("/api/v1/compare/football/analysis", tags=["Comparator"])
async def stream_football_analysis(request: FootballCompareRequest):
    """Stream LLM analysis for a football match via SSE."""
    return await _sse_stream("football", request, compare_football)
