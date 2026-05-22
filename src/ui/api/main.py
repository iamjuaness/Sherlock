"""FastAPI application – Sherlock REST API."""

from __future__ import annotations

from datetime import datetime
import json
import asyncio

from fastapi.responses import StreamingResponse
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from src.core.database import get_db, init_db
from src.core.domain import Competition, Match, Sport, AnalysisHistory
from src.ui.api.schemas import (
    CompetitionOut,
    MatchOut,
    SportOut,
    SyncResult,
    AnalysisSave,
    AnalysisHistoryOut,
    AnalysisResultsUpdate,
    GlobalStatsOut,
    PickStat,
)
from src.ui.api.compare import (
    compare_football,
    compare_nba,
    compare_tennis,
    FootballCompareRequest,
    NBACompareRequest,
    TennisCompareRequest,
    CompareResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Sherlock – Multi-Sport Analytics",
    description="API for football, NBA and tennis analytics with betting market analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O especifica "http://127.0.0.1:8000"
    allow_credentials=True,
    allow_methods=["*"],  # Esto habilita DELETE, POST, etc.
    allow_headers=["*"],
)

@app.middleware("http")
async def disable_cache_in_dev(request: Request, call_next):
    response = await call_next(request)

    if request.url.path.startswith("/static") or request.url.path == "/compare":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response

# ---------------------------------------------------------------------------
# Static & Templates
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(WEB_DIR, "templates"))

def file_version(path: str) -> str:
    return str(int(os.path.getmtime(path)))

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/compare", tags=["Web UI"])
def serve_dashboard(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    js_path = os.path.join(WEB_DIR, "static", "js", "comparator.js")

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
            "js_version": file_version(js_path),
        },
    )

@app.get("/api/v1/sports", response_model=list[SportOut], tags=["Sports"])
def list_sports() -> list[SportOut]:
    """List available sports."""
    return [SportOut(value=s.value, label=s.value.capitalize()) for s in Sport]


@app.get("/api/v1/competitions", response_model=list[CompetitionOut], tags=["Competitions"])
def list_competitions(
    sport: str | None = Query(None, description="Filter by sport (football, basketball, tennis)"),
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


@app.get("/api/v1/matches", response_model=list[MatchOut], tags=["Matches"])
def list_matches(
    sport: str | None = Query(None),
    competition_id: str | None = Query(None),
    date_from: str | None = Query(None, description="ISO format YYYY-MM-DD"),
    date_to: str | None = Query(None, description="ISO format YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    """List matches with filters."""
    query = (
        db.query(Match)
        .options(
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.competition),
            joinedload(Match.betting_lines),
        )
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

    query = query.order_by(Match.date.desc()).offset(offset).limit(limit)
    return [MatchOut.model_validate(m) for m in query.all()]


@app.post(
    "/api/v1/datasources/{source}/sync",
    response_model=SyncResult,
    tags=["Data Sources"],
)
async def sync_datasource(
    source: str,
    season: str | None = Query(None),
    competition_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> SyncResult:
    """Trigger data sync from a specified datasource.

    Supported sources: api_football, thesportsdb_football, balldontlie, thesportsdb_tennis
    """
    from src.datasources.football_api_football import FootballApiFootballAdapter
    from src.datasources.football_thesportsdb import FootballTheSportsDBAdapter
    from src.datasources.nba_balldontlie import NBABallDontLieAdapter
    from src.datasources.tennis_thesportsdb import TennisTheSportsDBAdapter

    adapters = {
        "api_football": FootballApiFootballAdapter,
        "thesportsdb_football": FootballTheSportsDBAdapter,
        "balldontlie": NBABallDontLieAdapter,
        "thesportsdb_tennis": TennisTheSportsDBAdapter,
    }

    if source not in adapters:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{source}'. Available: {list(adapters.keys())}",
        )

    adapter = adapters[source]()
    kwargs = {}
    if season:
        kwargs["season"] = season

    # Sync competitions
    competitions = await adapter.fetch_competitions(**kwargs)
    comp_count = 0
    for comp in competitions:
        existing = (
            db.query(Competition)
            .filter(
                Competition.sport == comp.sport,
                Competition.name == comp.name,
                Competition.season == comp.season,
            )
            .first()
        )
        if not existing:
            db.add(comp)
            comp_count += 1
    db.commit()

    # Sync matches
    matches = await adapter.fetch_matches(competition_id=competition_id, **kwargs)
    match_count = 0
    for match in matches:
        # Resolve teams – get or create
        home_team_obj = getattr(match, "_home_team_obj", None)
        away_team_obj = getattr(match, "_away_team_obj", None)

        if home_team_obj:
            match.home_team_id = _get_or_create_team(db, home_team_obj)
        if away_team_obj:
            match.away_team_id = _get_or_create_team(db, away_team_obj)

        # Resolve competition
        comp_name = getattr(match, "_competition_name", None)
        if comp_name:
            comp = (
                db.query(Competition)
                .filter(Competition.name == comp_name, Competition.sport == match.sport)
                .first()
            )
            if comp:
                match.competition_id = comp.id

        # Check if match already exists
        if match.external_id and match.source:
            existing = (
                db.query(Match)
                .filter(
                    Match.external_id == match.external_id,
                    Match.source == match.source,
                )
                .first()
            )
            if existing:
                continue

        db.add(match)
        match_count += 1

    db.commit()

    return SyncResult(
        source=source,
        competitions_synced=comp_count,
        matches_synced=match_count,
        message=f"Synced {comp_count} competitions and {match_count} matches from {source}",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_create_team(db: Session, team_obj: object) -> str:
    """Get existing team by name+sport or create a new one. Returns team ID."""
    from src.core.domain import Team

    existing = (
        db.query(Team)
        .filter(Team.name == team_obj.name, Team.sport == team_obj.sport)  # type: ignore[attr-defined]
        .first()
    )
    if existing:
        return existing.id

    db.add(team_obj)  # type: ignore[arg-type]
    db.flush()
    return team_obj.id  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Comparator API
# ---------------------------------------------------------------------------


async def _enrich_with_results(sport: Sport, home: str, away: str, response: CompareResponse, db: Session):
    """Busca si el partido ya tiene resultados en la BD y marca acierto/fallo en el vuelo."""
    # Buscar el análisis más reciente para este partido que tenga resultados
    history = (
        db.query(AnalysisHistory)
        .filter(
            AnalysisHistory.sport == sport,
            AnalysisHistory.match_title.like(f"%{home}%"),
            AnalysisHistory.match_title.like(f"%{away}%"),
            AnalysisHistory.final_score_home != None
        )
        .order_by(AnalysisHistory.date.desc())
        .first()
    )
    
    if not history:
        return response
        
    res_dict = {
        "final_score_home": history.final_score_home,
        "final_score_away": history.final_score_away,
        "final_corners_home": history.final_corners_home,
        "final_corners_away": history.final_corners_away,
        "final_yellow_cards_home": history.final_yellow_cards_home,
        "final_yellow_cards_away": history.final_yellow_cards_away,
        "final_red_cards_home": history.final_red_cards_home,
        "final_red_cards_away": history.final_red_cards_away,
        "final_shots_home": history.final_shots_home,
        "final_shots_away": history.final_shots_away,
        "final_shots_on_target_home": history.final_shots_on_target_home,
        "final_shots_on_target_away": history.final_shots_on_target_away,
    }
    
    # Inyectar éxito en los picks
    for v in response.values:
        v.success = _check_pick_success(v.dict() if hasattr(v, 'dict') else v.__dict__, res_dict)
        
    return response

@app.post("/api/v1/compare/football", response_model=CompareResponse, tags=["Comparator"])
async def compare_teams_football(request: FootballCompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    res = await compare_football(request)
    return await _enrich_with_results(Sport.FOOTBALL, request.home.name, request.away.name, res, db)


@app.post("/api/v1/compare/nba", response_model=CompareResponse, tags=["Comparator"])
async def compare_teams_nba(request: NBACompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    res = await compare_nba(request)
    return await _enrich_with_results(Sport.NBA, request.home.name, request.away.name, res, db)


@app.post("/api/v1/compare/tennis", response_model=CompareResponse, tags=["Comparator"])
async def compare_players_tennis(request: TennisCompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    res = await compare_tennis(request)
    return await _enrich_with_results(Sport.TENNIS, request.player1.name, request.player2.name, res, db)

# ---------------------------------------------------------------------------
# Comparator LLM Streaming (SSE)
# ---------------------------------------------------------------------------

async def _call_llm_for_result(sport: str, result: CompareResponse, request) -> str:
    """Llama al LLM usando las funciones internas de compare.py sin importarlas."""
    import src.ui.api.compare as _cmp

    vp = [v for v in result.values if v.is_value]
    user_context = getattr(request, "user_context", "") or ""

    if sport == "football":
        fn = getattr(_cmp, "safe_generate_football_analysis", None) \
          or getattr(_cmp, "_safe_generate_football_analysis", None)
        if fn:
            return await fn(request.home, request.away, vp, result.projected_lines, request.league_stats, request.competition_name, user_context)

    elif sport == "nba":
        fn = getattr(_cmp, "safe_generate_nba_analysis", None) \
          or getattr(_cmp, "_safe_generate_nba_analysis", None)
        if fn:
            return await fn(request.home, request.away, vp, request)

    elif sport == "tennis":
        fn = getattr(_cmp, "safe_generate_tennis_analysis", None) \
          or getattr(_cmp, "_safe_generate_tennis_analysis", None)
        if fn:
            return await fn(request.player1, request.player2, vp, request.surface, user_context)

    return "⚠️ No se pudo encontrar el generador de análisis LLM."


async def _sse_stream(sport: str, request, compare_fn):
    """Generador SSE genérico: calcula resultado + llama LLM + hace streaming."""
    async def event_generator():
        try:
            result = await compare_fn(request)
            text = await _call_llm_for_result(sport, result, request)
            chunk_size = 60
            for i in range(0, len(text), chunk_size):
                yield f"data: {json.dumps({'chunk': text[i:i+chunk_size]})}\n\n"
                await asyncio.sleep(0.01)
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/v1/compare/football/analysis", tags=["Comparator"])
async def stream_football_analysis(request: FootballCompareRequest):
    """Stream LLM analysis for a football match via SSE."""
    return await _sse_stream("football", request, compare_football)


@app.post("/api/v1/compare/nba/analysis", tags=["Comparator"])
async def stream_nba_analysis(request: NBACompareRequest):
    """Stream LLM analysis for an NBA match via SSE."""
    return await _sse_stream("nba", request, compare_nba)


@app.post("/api/v1/compare/tennis/analysis", tags=["Comparator"])
async def stream_tennis_analysis(request: TennisCompareRequest):
    """Stream LLM analysis for a tennis match via SSE."""
    return await _sse_stream("tennis", request, compare_tennis)

# ---------------------------------------------------------------------------
# Analysis History API
# ---------------------------------------------------------------------------


@app.post("/api/v1/analysis", response_model=AnalysisHistoryOut, tags=["Analysis History"])
def save_analysis(
    req: AnalysisSave,
    db: Session = Depends(get_db),
) -> AnalysisHistoryOut:
    """Save or update an analysis in history."""
    try:
        sport_enum = Sport(req.sport)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sport: {req.sport}")

    # Check for existing record (Upsert logic)
    existing = (
        db.query(AnalysisHistory)
        .filter(
            AnalysisHistory.sport == sport_enum,
            AnalysisHistory.match_title == req.match_title,
        )
        .first()
    )

    if existing:
        existing.payload = json.dumps(req.payload)
        existing.match_date = req.match_date
        if req.picks_calculados is not None:
            existing.picks_calculados = json.dumps(req.picks_calculados)
        if req.user_context is not None:
            existing.user_context = req.user_context
        if req.llm_response is not None:
            existing.llm_response = req.llm_response
            existing.llm_timestamp = req.llm_timestamp or datetime.utcnow()
        if req.needs_reanalysis is not None:
            existing.needs_reanalysis = req.needs_reanalysis
        if req.compare_response_snapshot is not None:
            existing.compare_response_snapshot = json.dumps(req.compare_response_snapshot)
        
        db.commit()
        db.refresh(existing)
        out = AnalysisHistoryOut.model_validate(existing)
        return _populate_history_extra_fields(existing, out)

    # Create new record
    history = AnalysisHistory(
        sport=sport_enum,
        match_title=req.match_title,
        payload=json.dumps(req.payload),
        match_date=req.match_date,
        picks_calculados=json.dumps(req.picks_calculados) if req.picks_calculados else None,
        user_context=req.user_context,
        llm_response=req.llm_response,
        llm_timestamp=req.llm_timestamp,
        compare_response_snapshot=json.dumps(req.compare_response_snapshot) if req.compare_response_snapshot else None,
        needs_reanalysis=req.needs_reanalysis or False,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)


@app.get("/api/v1/analysis", response_model=list[AnalysisHistoryOut], tags=["Analysis History"])
def list_analysis(
    sport: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    match_date_from: str | None = Query(None),
    match_date_to: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AnalysisHistoryOut]:
    """List saved analyses with optional filters."""
    query = db.query(AnalysisHistory)
    if sport:
        try:
            sport_enum = Sport(sport)
            query = query.filter(AnalysisHistory.sport == sport_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")

    # Created date filters
    if date_from:
        query = query.filter(AnalysisHistory.date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AnalysisHistory.date <= datetime.fromisoformat(date_to))
        
    # Match date filters
    if match_date_from:
        query = query.filter(AnalysisHistory.match_date >= datetime.fromisoformat(match_date_from))
    if match_date_to:
        query = query.filter(AnalysisHistory.match_date <= datetime.fromisoformat(match_date_to))

    query = query.order_by(AnalysisHistory.date.desc()).limit(limit)
    history_list = query.all()
    results = []
    for h in history_list:
        out = AnalysisHistoryOut.model_validate(h)
        results.append(_populate_history_extra_fields(h, out))
    return results


@app.post("/api/v1/analysis/{analysis_id}/results", response_model=AnalysisHistoryOut, tags=["Analysis History"])
def update_analysis_results(
    analysis_id: str,
    req: AnalysisResultsUpdate,
    db: Session = Depends(get_db),
) -> AnalysisHistoryOut:
    """Update final match results and calculate accuracy."""
    history = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Update result fields
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(history, field, value)

    # Calculate Accuracy
    if history.picks_calculados:
        try:
            picks = json.loads(history.picks_calculados)
            if isinstance(picks, list) and len(picks) > 0:
                results_dict = req.model_dump()
                hits = 0
                total = 0
                
                # Calculate Accuracy
                for pick in picks:
                    # Filter: Only "Value" picks are counted for model accuracy stats
                    # High confidence picks (without edge) are for visual analysis only
                    if not (pick.get("is_publishable", pick.get("is_value", False))):
                        continue
                        
                    success = _check_pick_success(pick, results_dict)
                    if success is not None:
                        total += 1
                        if success:
                            hits += 1
                
                if total > 0:
                    history.accuracy_percentage = (hits / total) * 100
        except Exception as e:
            print(f"Error calculating accuracy: {e}")

    db.commit()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)


@app.post("/api/v1/analysis/recalculate-all", tags=["Analysis History"])
async def recalculate_all_accuracy(db: Session = Depends(get_db)):
    """
    Re-analiza todos los registros del historial:
    1. Vuelve a calcular los picks usando el payload original (motor de predicción).
    2. Actualiza los snapshots y los picks calculados.
    3. Si hay resultados finales, recalcula el acierto (accuracy_percentage).
    """
    history_list = db.query(AnalysisHistory).all()
    count = 0
    updated_accuracy_count = 0
    
    for history in history_list:
        try:
            if not history.payload:
                continue
                
            # Cargar el payload original
            payload_dict = json.loads(history.payload)
            sport = history.sport
            
            # Re-ejecutar el motor de comparación según el deporte
            new_response = None
            try:
                if sport == Sport.FOOTBALL:
                    req = FootballCompareRequest(**payload_dict)
                    new_response = await compare_football(req)
                elif sport == Sport.NBA or sport == Sport.BASKETBALL:
                    req = NBACompareRequest(**payload_dict)
                    new_response = await compare_nba(req)
                elif sport == Sport.TENNIS:
                    req = TennisCompareRequest(**payload_dict)
                    new_response = await compare_tennis(req)
            except Exception as comp_err:
                print(f"Error en motor de comparación para {history.id} ({sport}): {comp_err}")
                continue
                
            if new_response:
                # 1. Actualizar picks_calculados y snapshot
                picks = [v.model_dump() if hasattr(v, 'model_dump') else v.__dict__ for v in new_response.values]
                history.picks_calculados = json.dumps(picks)
                history.compare_response_snapshot = json.dumps(new_response.model_dump() if hasattr(new_response, 'model_dump') else new_response.__dict__)
                
                # 2. Si tiene resultados, recalcular acierto
                if history.final_score_home is not None:
                    results_dict = {
                        "final_score_home": history.final_score_home,
                        "final_score_away": history.final_score_away,
                        "final_corners_home": history.final_corners_home,
                        "final_corners_away": history.final_corners_away,
                        "final_yellow_cards_home": history.final_yellow_cards_home,
                        "final_yellow_cards_away": history.final_yellow_cards_away,
                        "final_red_cards_home": history.final_red_cards_home,
                        "final_red_cards_away": history.final_red_cards_away,
                        "final_shots_home": history.final_shots_home,
                        "final_shots_away": history.final_shots_away,
                        "final_shots_on_target_home": history.final_shots_on_target_home,
                        "final_shots_on_target_away": history.final_shots_on_target_away,
                    }
                    
                    hits = 0
                    total = 0
                    
                    for pick in picks:
                        # Filtro: Solo picks de valor cuentan para la estadística oficial
                        if not (pick.get("is_publishable", pick.get("is_value", False))):
                            continue
                            
                        success = _check_pick_success(pick, results_dict)
                        if success is not None:
                            total += 1
                            if success:
                                hits += 1
                    
                    if total > 0:
                        history.accuracy_percentage = (hits / total) * 100
                    else:
                        history.accuracy_percentage = None
                    
                    updated_accuracy_count += 1
                
                count += 1
        except Exception as e:
            print(f"Error re-analizando registro {history.id}: {e}")

    db.commit()
    return {
        "message": f"Se han re-analizado {count} partidos. Se actualizó el acierto en {updated_accuracy_count} de ellos.",
        "total_reanalyzed": count,
        "accuracy_updated": updated_accuracy_count
    }


@app.get("/api/v1/stats/global", response_model=GlobalStatsOut, tags=["Stats"])
def get_global_stats(db: Session = Depends(get_db)):
    """Calculate global performance metrics across all sports with advanced analytics."""
    history = db.query(AnalysisHistory).all()
    
    total_matches = len(history)
    matches_with_results = 0
    total_picks = 0
    total_hits = 0
    
    total_odds = 0.0
    total_winning_odds = 0.0
    winning_picks_count = 0
    
    sport_stats = {}
    market_counters = {}
    league_counters = {}
    team_counters = {}

    # Buckets configuration
    odds_buckets_cfg = [(1.0, 1.5, "1.0-1.5"), (1.5, 2.0, "1.5-2.0"), (2.0, 3.0, "2.0-3.0"), (3.0, 1000.0, ">3.0")]
    edge_buckets_cfg = [(-100.0, 5.0, "<5%"), (5.0, 10.0, "5-10%"), (10.0, 15.0, "10-15%"), (15.0, 1000.0, ">15%")]
    conf_buckets_cfg = [(0.0, 60.0, "<60%"), (60.0, 70.0, "60-70%"), (70.0, 80.0, "70-80%"), (80.0, 100.1, ">80%")]

    odds_b_stats = {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in odds_buckets_cfg}
    edge_b_stats = {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in edge_buckets_cfg}
    conf_b_stats = {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in conf_buckets_cfg}
    
    for h in history:
        has_result = h.final_score_home is not None
        if has_result:
            matches_with_results += 1
            
        if h.picks_calculados:
            try:
                picks = json.loads(h.picks_calculados)
                if not isinstance(picks, list): continue
                
                results_dict = {
                    "final_score_home": h.final_score_home,
                    "final_score_away": h.final_score_away,
                    "final_corners_home": h.final_corners_home,
                    "final_corners_away": h.final_corners_away,
                    "final_yellow_cards_home": h.final_yellow_cards_home,
                    "final_yellow_cards_away": h.final_yellow_cards_away,
                    "final_red_cards_home": h.final_red_cards_home,
                    "final_red_cards_away": h.final_red_cards_away,
                    "final_shots_home": h.final_shots_home,
                    "final_shots_away": h.final_shots_away,
                    "final_shots_on_target_home": h.final_shots_on_target_home,
                    "final_shots_on_target_away": h.final_shots_on_target_away,
                }
                
                sport = h.sport.value if hasattr(h.sport, 'value') else str(h.sport)
                if sport not in sport_stats:
                    sport_stats[sport] = {"picks": 0, "hits": 0}
                
                # Extract league info
                league = "Desconocida"
                if h.payload:
                    try:
                        p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                        league = p_data.get("match", {}).get("competition", {}).get("name", "Desconocida")
                    except: pass
                
                # Extract team info
                teams = []
                if h.match_title:
                    if " vs " in h.match_title:
                        teams = [t.strip() for t in h.match_title.split(" vs ")]
                    elif " - " in h.match_title:
                        teams = [t.strip() for t in h.match_title.split(" - ")]

                for pick in picks:
                    # Filter: Only "Value" picks are counted for performance stats
                    if not (pick.get("is_publishable", pick.get("is_value", False))):
                        continue

                    total_picks += 1
                    sport_stats[sport]["picks"] += 1
                    
                    odds = float(pick.get("odds", 0.0))
                    total_odds += odds
                    
                    market = pick.get("market", "Otro")
                    if market not in market_counters:
                        market_counters[market] = {"picks": 0, "hits": 0}
                    market_counters[market]["picks"] += 1
                    
                    if league not in league_counters:
                        league_counters[league] = {"picks": 0, "hits": 0}
                    league_counters[league]["picks"] += 1
                    
                    for t in teams:
                        if t not in team_counters:
                            team_counters[t] = {"picks": 0, "hits": 0}
                        team_counters[t]["picks"] += 1

                    # Success and resolution
                    success = False
                    if has_result:
                        success = _check_pick_success(pick, results_dict)
                        if success:
                            total_hits += 1
                            sport_stats[sport]["hits"] += 1
                            market_counters[market]["hits"] += 1
                            league_counters[league]["hits"] += 1
                            for t in teams:
                                team_counters[t]["hits"] += 1
                            total_winning_odds += odds
                            winning_picks_count += 1

                    # Bucketing logic
                    # Usamos edge_ev para los buckets de valor, convertido a % para mantener compatibilidad con las etiquetas
                    edge_val = float(pick.get("edge_ev", 0.0)) * 100.0
                    conf = float(pick.get("calibrated_prob", pick.get("model_prob", 0.0)))

                    for low, high, label in odds_buckets_cfg:
                        if low <= odds < high:
                            odds_b_stats[label]["count"] += 1
                            odds_b_stats[label]["total_odds"] += odds
                            if has_result:
                                odds_b_stats[label]["resolved"] += 1
                                if success: odds_b_stats[label]["hits"] += 1
                            break

                    for low, high, label in edge_buckets_cfg:
                        if low <= edge_val < high:
                            edge_b_stats[label]["count"] += 1
                            edge_b_stats[label]["total_odds"] += odds
                            if has_result:
                                edge_b_stats[label]["resolved"] += 1
                                if success: edge_b_stats[label]["hits"] += 1
                            break

                    for low, high, label in conf_buckets_cfg:
                        if low <= conf < high:
                            conf_b_stats[label]["count"] += 1
                            conf_b_stats[label]["total_odds"] += odds
                            if has_result:
                                conf_b_stats[label]["resolved"] += 1
                                if success: conf_b_stats[label]["hits"] += 1
                            break

            except Exception as e:
                print(f"Error in global stats loop: {e}")
                continue
                
    accuracy = (total_hits / total_picks * 100) if total_picks > 0 else 0.0
    avg_odds = (total_odds / total_picks) if total_picks > 0 else 0.0
    avg_winning_odds = (total_winning_odds / winning_picks_count) if winning_picks_count > 0 else 0.0
    
    # Calculate per-sport accuracy
    for s in sport_stats:
        p = sport_stats[s]["picks"]
        hits = sport_stats[s]["hits"]
        sport_stats[s]["accuracy"] = (hits / p * 100) if p > 0 else 0.0
        
    # Process market, league, team stats
    def to_stat_list(counters, min_picks=1):
        result = []
        for name, data in counters.items():
            if data["picks"] >= min_picks:
                acc = (data["hits"] / data["picks"] * 100)
                result.append({
                    "name": name,
                    "picks": data["picks"],
                    "hits": data["hits"],
                    "accuracy": acc
                })
        return result

    # Helper for buckets to list
    def bucket_to_list(stats_map):
        res = []
        for label, data in stats_map.items():
            avg_o = (data["total_odds"] / data["count"]) if data["count"] > 0 else 0.0
            acc = (data["hits"] / data["resolved"] * 100) if data["resolved"] > 0 else 0.0
            res.append({
                "bucket": label,
                "count": data["count"],
                "avg_odds": round(avg_o, 2),
                "accuracy": round(acc, 1)
            })
        return res

    all_markets = to_stat_list(market_counters)
    all_leagues = to_stat_list(league_counters, min_picks=2)
    all_teams = to_stat_list(team_counters, min_picks=2)
    
    # Sort and slice
    best_markets = sorted(all_markets, key=lambda x: x["accuracy"], reverse=True)[:5]
    worst_markets = sorted(all_markets, key=lambda x: x["accuracy"])[:5]
    best_leagues = sorted(all_leagues, key=lambda x: x["accuracy"], reverse=True)[:5]
    best_teams = sorted(all_teams, key=lambda x: x["accuracy"], reverse=True)[:10]
    
    return {
        "total_matches": total_matches,
        "total_matches_with_results": matches_with_results,
        "total_picks": total_picks,
        "total_hits": total_hits,
        "global_accuracy": accuracy,
        "sport_stats": sport_stats,
        "avg_odds": avg_odds,
        "avg_winning_odds": avg_winning_odds,
        "best_markets": best_markets,
        "worst_markets": worst_markets,
        "best_leagues": best_leagues,
        "best_teams": best_teams,
        "odds_buckets": bucket_to_list(odds_b_stats),
        "edge_buckets": bucket_to_list(edge_b_stats),
        "confidence_buckets": bucket_to_list(conf_b_stats)
    }

@app.get("/api/v1/stats/picks", response_model=list[PickStat], tags=["Stats"])
def get_all_picks(
    limit: int = 100,
    sport: str | None = None,
    db: Session = Depends(get_db)
):
    """Get a detailed list of all calculated picks with their outcomes."""
    query = db.query(AnalysisHistory)
    if sport:
        try:
            sport_enum = Sport(sport)
            query = query.filter(AnalysisHistory.sport == sport_enum)
        except:
            pass
            
    history = query.order_by(AnalysisHistory.date.desc()).limit(limit).all()
    all_picks = []
    
    for h in history:
        if not h.picks_calculados: continue
        try:
            picks = json.loads(h.picks_calculados)
            results_dict = {
                "final_score_home": h.final_score_home,
                "final_score_away": h.final_score_away,
                "final_corners_home": h.final_corners_home,
                "final_corners_away": h.final_corners_away,
                "final_yellow_cards_home": h.final_yellow_cards_home,
                "final_yellow_cards_away": h.final_yellow_cards_away,
                "final_red_cards_home": h.final_red_cards_home,
                "final_red_cards_away": h.final_red_cards_away,
                "final_shots_home": h.final_shots_home,
                "final_shots_away": h.final_shots_away,
                "final_shots_on_target_home": h.final_shots_on_target_home,
                "final_shots_on_target_away": h.final_shots_on_target_away,
            }
            
            has_result = h.final_score_home is not None
            
            for pick in picks:
                # Filter: Only "Value" picks are shown in the performance/stats table
                if not (pick.get("is_publishable", pick.get("is_value", False))):
                    continue

                success = None
                if has_result:
                    success = _check_pick_success(pick, results_dict)
                
                all_picks.append({
                    "match_id": h.id,
                    "match_title": h.match_title,
                    "sport": h.sport.value if hasattr(h.sport, 'value') else str(h.sport),
                    "date": h.date,
                    "selection": pick.get("selection", "N/A"),
                    "market": pick.get("market", "N/A"),
                    "line": pick.get("line"),
                    "odds": pick.get("odds", 0.0),
                    "success": success,
                    "is_value": pick.get("is_value", False),
                    "is_high_confidence": pick.get("is_high_confidence", False),
                    "calibrated_prob": pick.get("calibrated_prob"),
                    "edge_ev": pick.get("edge_ev"),
                    "display_score": pick.get("display_score"),
                    "fair_odds": pick.get("fair_odds"),
                    "kelly_fraction": pick.get("kelly_fraction"),
                    "stat_support": pick.get("stat_support"),
                    "proj_support": pick.get("proj_support")
                })

        except:
            continue
            
    return all_picks


def _check_pick_success(pick: dict, res: dict) -> bool | None:
    """Helper to verify if a pick was successful based on results."""
    sel = pick.get("selection", "").lower()
    
    h_score = res.get("final_score_home")
    a_score = res.get("final_score_away")
    
    # 1X2 / Winner (Common for all sports)
    if sel == "local":
        if h_score is not None and a_score is not None: return h_score > a_score
    if sel == "empate":
        if h_score is not None and a_score is not None: return h_score == a_score
    if sel == "visitante":
        if h_score is not None and a_score is not None: return a_score > h_score
        
    # Points / Total Score (NBA / Tennis Games / etc)
    if "puntos" in sel or "points" in sel or "juegos" in sel or "games" in sel:
        total_p = (h_score + a_score) if (h_score is not None and a_score is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            if line is not None and total_p is not None: return total_p > line
        if "under" in sel:
            line = _extract_line(sel, "under")
            if line is not None and total_p is not None: return total_p < line

    # BTTS
    if "btts sí" in sel or "btts yes" in sel:
        if h_score is not None and a_score is not None: return h_score > 0 and a_score > 0
    if "btts no" in sel:
        if h_score is not None and a_score is not None: return h_score == 0 or a_score == 0
        
    # Goals
    if "goles" in sel or "goals" in sel:
        total_g = (h_score + a_score) if (h_score is not None and a_score is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            if line is not None and total_g is not None: return total_g > line
        if "under" in sel:
            line = _extract_line(sel, "under")
            if line is not None and total_g is not None: return total_g < line

    # Corners
    h_corn = res.get("final_corners_home")
    a_corn = res.get("final_corners_away")
    if "corners" in sel:
        total_c = (h_corn + a_corn) if (h_corn is not None and a_corn is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            if line is not None and total_c is not None: return total_c > line
        if "under" in sel:
            line = _extract_line(sel, "under")
            if line is not None and total_c is not None: return total_c < line

    # Cards
    h_y = res.get("final_yellow_cards_home") or 0
    a_y = res.get("final_yellow_cards_away") or 0
    h_r = res.get("final_red_cards_home") or 0
    a_r = res.get("final_red_cards_away") or 0
    total_cards = (h_y + a_y) + ((h_r + a_r) * 2)
    if "tarjetas" in sel or "cards" in sel:
        if "over" in sel:
            line = _extract_line(sel, "over")
            if line is not None: return total_cards > line
        if "under" in sel:
            line = _extract_line(sel, "under")
            if line is not None: return total_cards < line

    # Shots
    h_s = res.get("final_shots_home")
    a_s = res.get("final_shots_away")
    if "tiros" in sel or "shots" in sel:
        total_s = (h_s + a_s) if (h_s is not None and a_s is not None) else None
        if "pta" in sel or "target" in sel:
            h_st = res.get("final_shots_on_target_home")
            a_st = res.get("final_shots_on_target_away")
            total_st = (h_st + a_st) if (h_st is not None and a_st is not None) else None
            if "over" in sel:
                line = _extract_line(sel, "over")
                if line is not None and total_st is not None: return total_st > line
            if "under" in sel:
                line = _extract_line(sel, "under")
                if line is not None and total_st is not None: return total_st < line
        else:
            if "over" in sel:
                line = _extract_line(sel, "over")
                if line is not None and total_s is not None: return total_s > line
            if "under" in sel:
                line = _extract_line(sel, "under")
                if line is not None and total_s is not None: return total_s < line

    return None

def _extract_line(text: str, prefix: str) -> float | None:
    try:
        parts = text.split(prefix)
        if len(parts) > 1:
            # Get the first number found after prefix
            import re
            match = re.search(r"(\d+(\.\d+)?)", parts[1])
            if match:
                return float(match.group(1))
    except: pass
    return None

def _populate_history_extra_fields(h: AnalysisHistory, out: AnalysisHistoryOut) -> AnalysisHistoryOut:
    """Computa campos virtuales de picks y acierto para el historial."""
    if not h.picks_calculados:
        out.has_picks = False
        return out
        
    try:
        picks = json.loads(h.picks_calculados)
        if not isinstance(picks, list):
            out.has_picks = False
            return out
            
        # Solo se consideran para el resumen de acierto los picks de Valor
        relevant_picks = [p for p in picks if p.get("is_value") or p.get("is_publishable")]
        out.has_picks = len(relevant_picks) > 0
        
        # Calculate summary if results exist
        res_dict = {
            "final_score_home": h.final_score_home,
            "final_score_away": h.final_score_away,
            "final_corners_home": h.final_corners_home,
            "final_corners_away": h.final_corners_away,
            "final_yellow_cards_home": h.final_yellow_cards_home,
            "final_yellow_cards_away": h.final_yellow_cards_away,
            "final_red_cards_home": h.final_red_cards_home,
            "final_red_cards_away": h.final_red_cards_away,
            "final_shots_home": h.final_shots_home,
            "final_shots_away": h.final_shots_away,
            "final_shots_on_target_home": h.final_shots_on_target_home,
            "final_shots_on_target_away": h.final_shots_on_target_away,
        }
        
        if res_dict.get("final_score_home") is not None:
            hits = 0
            total = 0
            for p in relevant_picks:
                success = _check_pick_success(p, res_dict)
                if success is not None:
                    total += 1
                    if success:
                        hits += 1
            if total > 0:
                out.picks_hits_summary = f"{hits}/{total}"

            # Inject success into compare_response_snapshot for individual pick visualization
            if out.compare_response_snapshot:
                # Ensure it's a dict
                if isinstance(out.compare_response_snapshot, str):
                    try:
                        out.compare_response_snapshot = json.loads(out.compare_response_snapshot)
                    except:
                        pass
                
                if isinstance(out.compare_response_snapshot, dict):
                    # 1. Main picks list (used by renderMultiLineCards)
                    if "values" in out.compare_response_snapshot:
                        for v_pick in out.compare_response_snapshot["values"]:
                            v_pick["success"] = _check_pick_success(v_pick, res_dict)
                    
                    # 2. Market picks (used by other components if any)
                    if "market_picks" in out.compare_response_snapshot:
                        for market in out.compare_response_snapshot["market_picks"].values():
                            if "picks" in market:
                                for p in market["picks"]:
                                    p["success"] = _check_pick_success(p, res_dict)
                            
    except Exception as e:
        print(f"Error populating history extra fields: {e}")
        out.has_picks = False
        
    return out


@app.get("/api/v1/analysis/{analysis_id}", response_model=AnalysisHistoryOut, tags=["Analysis History"])
def get_analysis_by_id(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> AnalysisHistoryOut:
    """Retrieve a specific analysis by ID."""
    history = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Analysis not found")
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)

@app.delete("/api/v1/analysis/{analysis_id}", status_code=204, tags=["Analysis History"])
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Delete a specific analysis by ID."""
    history = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(history)
    db.commit()
    return None