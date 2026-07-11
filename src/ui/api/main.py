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
    FootballCompareRequest,
    CompareResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os
from fastapi.middleware.cors import CORSMiddleware


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Sherlock – Multi-Sport Analytics",
    description="API for football analytics with betting market analysis.",
    version="0.1.0",
    lifespan=lifespan,
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
# Routes
# ---------------------------------------------------------------------------

@app.get("/", tags=["Web UI"])
def serve_main_dashboard(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    js_path = os.path.join(WEB_DIR, "static", "js", "dashboard_main.js")
    
    js_ver = "1"
    if os.path.exists(js_path):
        js_ver = file_version(js_path)

    return templates.TemplateResponse(
        request=request,
        name="main_dashboard.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
            "js_version": js_ver,
        },
    )

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


# ---------------------------------------------------------------------------
# Prefill endpoint — used by browser extensions to push form data
# ---------------------------------------------------------------------------
# In-memory slot: stores the last payload pushed by the extension.
# Only one active slot is kept; it is cleared once the UI consumes it.
_prefill_store: dict | None = None


@app.post("/api/v1/prefill", tags=["Prefill"])
async def push_prefill(payload: dict) -> dict:
    """
    Browser extension pushes a (partial) form payload here.
    The Sherlock dashboard polls this endpoint and auto-fills the form.

    Expected body: any subset of the standard football payload.
    Example minimal body for football:
    {
      "sport": "football",
      "home": { "name": "Real Madrid", "goals_per_game": 2.1, ... },
      "away": { "name": "Barcelona", ... },
      "odds": { "home": 1.85, "draw": 3.50, "away": 4.20 }
    }
    """
    global _prefill_store
    _prefill_store = payload
    return {"status": "ok", "message": "Datos recibidos. Sherlock los cargará en el formulario."}


@app.get("/api/v1/prefill", tags=["Prefill"])
async def consume_prefill() -> dict:
    """
    Dashboard polls this to detect pending prefill data.
    Returns the payload once and clears the slot (single-use).
    """
    global _prefill_store
    if _prefill_store is None:
        return {"pending": False}
    data = _prefill_store
    _prefill_store = None
    return {"pending": True, "payload": data}


# ---------------------------------------------------------------------------
# Results endpoint — used by browser extensions to push match results
# ---------------------------------------------------------------------------
_result_store: dict | None = None


@app.post("/api/v1/result", tags=["Results"])
async def push_result(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Browser extension pushes match results here (e.g. from flashscore).
    Tries to find matching AnalysisHistory record and auto-update it,
    and also buffers it in memory for the UI to consume.
    """
    global _result_store
    _result_store = payload

    sport = payload.get("sport", "football")
    home_name = payload.get("home_team") or payload.get("home", {}).get("name")
    away_name = payload.get("away_team") or payload.get("away", {}).get("name")

    auto_updated = False
    match_title_found = ""

    if home_name and away_name:
        try:
            sport_enum = Sport(sport)
            # Find in recent AnalysisHistory entries
            recent_history = (
                db.query(AnalysisHistory)
                .filter(AnalysisHistory.sport == sport_enum)
                .order_by(AnalysisHistory.date.desc())
                .limit(40)
                .all()
            )

            for h in recent_history:
                title_lower = h.match_title.lower()
                h_name_lower = home_name.lower()
                a_name_lower = away_name.lower()

                # Simple flexible substring/containment check
                # Check if both are present in the title
                if (h_name_lower[:5] in title_lower and a_name_lower[:5] in title_lower) or \
                   (h_name_lower in title_lower and a_name_lower in title_lower):
                    
                    # Update fields
                    h.final_score_home = payload.get("final_score_home")
                    h.final_score_away = payload.get("final_score_away")
                    
                    # Optional extra stats
                    if "final_corners_home" in payload: h.final_corners_home = payload.get("final_corners_home")
                    if "final_corners_away" in payload: h.final_corners_away = payload.get("final_corners_away")
                    if "final_yellow_cards_home" in payload: h.final_yellow_cards_home = payload.get("final_yellow_cards_home")
                    if "final_yellow_cards_away" in payload: h.final_yellow_cards_away = payload.get("final_yellow_cards_away")
                    if "final_red_cards_home" in payload: h.final_red_cards_home = payload.get("final_red_cards_home")
                    if "final_red_cards_away" in payload: h.final_red_cards_away = payload.get("final_red_cards_away")
                    if "final_shots_home" in payload: h.final_shots_home = payload.get("final_shots_home")
                    if "final_shots_away" in payload: h.final_shots_away = payload.get("final_shots_away")
                    if "final_shots_on_target_home" in payload: h.final_shots_on_target_home = payload.get("final_shots_on_target_home")
                    if "final_shots_on_target_away" in payload: h.final_shots_on_target_away = payload.get("final_shots_on_target_away")
                    if "final_fouls_home" in payload: h.final_fouls_home = payload.get("final_fouls_home")
                    if "final_fouls_away" in payload: h.final_fouls_away = payload.get("final_fouls_away")
                    if "final_offsides_home" in payload: h.final_offsides_home = payload.get("final_offsides_home")
                    if "final_offsides_away" in payload: h.final_offsides_away = payload.get("final_offsides_away")

                    # Calculate Accuracy
                    if h.picks_calculados:
                        try:
                            picks = json.loads(str(h.picks_calculados))
                            if isinstance(picks, list) and len(picks) > 0:
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
                                    "final_fouls_home": h.final_fouls_home,
                                    "final_fouls_away": h.final_fouls_away,
                                    "final_offsides_home": h.final_offsides_home,
                                    "final_offsides_away": h.final_offsides_away,
                                }
                                hits = 0
                                total = 0
                                for pick in picks:
                                    if not (pick.get("is_publishable", pick.get("is_value", False))):
                                        continue
                                    success = _check_pick_success(pick, results_dict)
                                    if success is not None:
                                        total += 1
                                        if success is True:
                                            hits += 1
                                if total > 0:
                                    h.accuracy_percentage = (hits / total) * 100
                        except Exception as e:
                            print(f"Error calculating accuracy in push_result: {e}")

                    db.commit()
                    db.refresh(h)
                    auto_updated = True
                    match_title_found = h.match_title
                    break
        except Exception as ex:
            print(f"Error auto-matching result payload: {ex}")

    if auto_updated:
        return {
            "status": "ok",
            "message": f"Resultado recibido y auto-asociado al partido en BD: '{match_title_found}'",
            "auto_updated": True
        }
    else:
        return {
            "status": "ok",
            "message": f"Resultado recibido en memoria para {home_name} vs {away_name}. No se encontró partido pendiente coincidente en base de datos.",
            "auto_updated": False
        }


@app.get("/api/v1/result", tags=["Results"])
async def consume_result() -> dict:
    """
    Dashboard/comparator polls this to detect pending match results.
    Returns the payload once and clears the slot (single-use).
    """
    global _result_store
    if _result_store is None:
        return {"pending": False}
    data = _result_store
    _result_store = None
    return {"pending": True, "payload": data}




@app.get("/api/v1/competitions", response_model=list[CompetitionOut], tags=["Competitions"])
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
        return str(existing.id)  # type: ignore[return]

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
        v.success = _check_pick_success(v.model_dump() if hasattr(v, 'model_dump') else v.__dict__, res_dict)
        
    return response

@app.post("/api/v1/compare/football", response_model=CompareResponse, tags=["Comparator"])
async def compare_teams_football(request: FootballCompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    res = await compare_football(request)
    return await _enrich_with_results(Sport.FOOTBALL, request.home.name, request.away.name, res, db)


# ---------------------------------------------------------------------------
# Comparator LLM Streaming (SSE)
# ---------------------------------------------------------------------------

async def _call_llm_for_result(sport: str, result: CompareResponse, request) -> str:
    """Llama al LLM usando las funciones internas de compare.py sin importarlas."""
    import src.ui.api.compare as _cmp

    vp = [v for v in result.values if v.is_value]
    user_context = getattr(request, "user_context", "") or ""

    if sport == "football":
        fn = getattr(_cmp, "safe_generate_football_analysis", None)
        if fn:
            return await fn(request.home, request.away, vp, result.projected_lines, request.league_stats, request.competition_name, user_context)

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
    existing = None
    if req.id:
        existing = db.query(AnalysisHistory).filter(AnalysisHistory.id == req.id).first()

    if not existing:
        existing = (
            db.query(AnalysisHistory)
            .filter(
                AnalysisHistory.sport == sport_enum,
                AnalysisHistory.match_title == req.match_title,
            )
            .first()
        )

    if existing:
        # pyrefly: ignore [bad-assignment]
        existing.sport = sport_enum
        # pyrefly: ignore [bad-assignment]
        existing.match_title = req.match_title
        # pyrefly: ignore [bad-assignment]
        existing.payload = json.dumps(req.payload)
        if req.match_date is not None:
            # pyrefly: ignore [bad-assignment]
            existing.match_date = req.match_date
            # pyrefly: ignore [bad-assignment]
            existing.date = req.match_date
        if req.picks_calculados is not None:
            # pyrefly: ignore [bad-assignment]
            existing.picks_calculados = json.dumps(req.picks_calculados)
        if req.user_context is not None:
            # pyrefly: ignore [bad-assignment]
            existing.user_context = req.user_context
        if req.llm_response is not None:
            # pyrefly: ignore [bad-assignment]
            existing.llm_response = req.llm_response
            # pyrefly: ignore [bad-assignment, deprecated]
            existing.llm_timestamp = req.llm_timestamp or datetime.utcnow()
        if req.needs_reanalysis is not None:
            # pyrefly: ignore [bad-assignment]
            existing.needs_reanalysis = req.needs_reanalysis
        if req.compare_response_snapshot is not None:
            # pyrefly: ignore [bad-assignment]
            existing.compare_response_snapshot = json.dumps(req.compare_response_snapshot)
        
        db.commit()
        db.refresh(existing)
        out = AnalysisHistoryOut.model_validate(existing)
        return _populate_history_extra_fields(existing, out)

    # Create new record
    # Use match_date if provided, otherwise use current time (same as `date`)
    record_date = req.match_date or datetime.utcnow()
    history = AnalysisHistory(
        sport=sport_enum,
        match_title=req.match_title,
        payload=json.dumps(req.payload),
        date=record_date,
        match_date=record_date,
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
            # pyrefly: ignore [bad-argument-type]
            picks = json.loads(history.picks_calculados)
            if isinstance(picks, list) and len(picks) > 0:
                results_dict = req.model_dump()
                hits = 0
                total = 0
                
                # Calculate Accuracy
                for pick in picks:
                    # Filter: Only "Value" picks are counted for model accuracy stats
                    if not (pick.get("is_publishable", pick.get("is_value", False))):
                        continue
                        
                    success = _check_pick_success(pick, results_dict)
                    if success is not None:
                        total += 1
                        # "void" = push/nulo: no suma ni hit ni miss, pero SÍ está resuelto
                        if success is True:
                            hits += 1
                        # success == "void" → resuelto pero neutro (no afecta accuracy)
                
                if total > 0:
                    # pyrefly: ignore [bad-assignment]
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
            payload_dict = json.loads(str(history.payload))
            sport = history.sport
            
            # Re-ejecutar el motor de comparación según el deporte
            new_response = None
            try:
                if sport == Sport.FOOTBALL:
                    req = FootballCompareRequest(**payload_dict)
                    new_response = await compare_football(req)
            except Exception as comp_err:
                print(f"Error en motor de comparación para {history.id} ({sport}): {comp_err}")
                continue
                
            if new_response:
                # 1. Actualizar picks_calculados y snapshot
                picks = [v.model_dump() if hasattr(v, 'model_dump') else v.__dict__ for v in new_response.values]
                history.picks_calculados = json.dumps(picks)  # type: ignore[bad-assignment]
                history.compare_response_snapshot = json.dumps(new_response.model_dump() if hasattr(new_response, 'model_dump') else new_response.__dict__)  # type: ignore[bad-assignment]
                
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
                        history.accuracy_percentage = (hits / total) * 100  # type: ignore[bad-assignment]
                    else:
                        history.accuracy_percentage = None  # type: ignore[bad-assignment]
                
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


def get_market_name(selection: str) -> str:
    s = selection.strip().lower()
    if any(k in s for k in ["btts", "ambos marcan", "both teams to score"]):
        return "BTTS"
    if any(k in s for k in ["corner", "corners", "córner", "córners"]):
        return "Tiros de esquina: Over/Under"
    if any(k in s for k in ["tarjeta", "tarjetas", "cards", "yellow cards", "amarillas"]):
        return "Tarjetas: Over/Under"
    if any(k in s for k in ["foul", "fouls", "faltas"]):
        return "Faltas: Over/Under"
    if any(k in s for k in ["shot", "shots", "tiros", "remates"]):
        return "Tiros: Over/Under"
    if any(k in s for k in ["over", "under", "más de", "menos de"]) and any(k in s for k in ["gol", "goles", "goal", "goals"]):
        return "Goles: Over/Under"
    if any(k in s for k in ["handicap", "hándicap", "asian", "ah "]):
        return "Hándicap"

    if any(k in s for k in ["double chance", "doble oportunidad", "1x", "x2", "12"]):
        return "Doble Oportunidad"
    if s in ["local", "visitante", "empate", "home", "away", "draw"] or any(k in s for k in ["moneyline", "ml", "1x2", "ganador"]):
        return "1x2"
    if any(k in s for k in ["gol", "goles", "goal", "goals"]):
        return "Goles: Over/Under"
    return "Otros"


@app.get("/api/v1/stats/global", response_model=GlobalStatsOut, tags=["Stats"])
def get_global_stats(db: Session = Depends(get_db)):
    """Calculate global performance metrics across all sports with advanced analytics."""
    history = db.query(AnalysisHistory).all()
    
    total_matches = len(history)
    matches_with_results = 0
    total_picks = 0
    total_hits = 0
    total_pending = 0
    total_exact_scores_predicted = 0
    total_exact_scores_hits = 0
    
    total_odds = 0.0
    total_winning_odds = 0.0
    winning_picks_count = 0
    total_profit = 0.0
    # daily_profit_dict: date_str -> net profit that day
    daily_profit_dict: dict[str, float] = {}
    
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
    
    categories = ["professional", "underdog", "high_confidence"]
    cat_accumulators = {}
    for cat in categories:
        cat_accumulators[cat] = {
            "total_picks": 0,
            "total_hits": 0,
            "total_pending": 0,
            "total_odds": 0.0,
            "total_winning_odds": 0.0,
            "winning_picks_count": 0,
            "market_counters": {},
            "league_counters": {},
            "team_counters": {},
            "odds_b_stats": {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in odds_buckets_cfg},
            "edge_b_stats": {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in edge_buckets_cfg},
            "conf_b_stats": {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in conf_buckets_cfg}
        }
        
    for h in history:
        has_result = h.final_score_home is not None
        if has_result:
            matches_with_results += 1
            
        if h.picks_calculados:
            try:
                picks = json.loads(str(h.picks_calculados))
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
                    "final_fouls_home": h.final_fouls_home,
                    "final_fouls_away": h.final_fouls_away,
                    "final_offsides_home": h.final_offsides_home,
                    "final_offsides_away": h.final_offsides_away,
                }

                # Track exact score prediction
                if h.final_score_home is not None and h.final_score_away is not None and h.compare_response_snapshot:
                    try:
                        snap = json.loads(h.compare_response_snapshot) if isinstance(h.compare_response_snapshot, str) else h.compare_response_snapshot
                        if isinstance(snap, dict) and snap.get("most_probable_score"):
                            total_exact_scores_predicted += 1
                            predicted_parts = snap["most_probable_score"].split("-")
                            if len(predicted_parts) == 2:
                                pred_h = int(predicted_parts[0].strip())
                                pred_a = int(predicted_parts[1].strip())
                                if pred_h == h.final_score_home and pred_a == h.final_score_away:
                                    total_exact_scores_hits += 1
                    except: pass
                
                sport = h.sport.value if hasattr(h.sport, 'value') else str(h.sport)
                if sport not in sport_stats:
                    sport_stats[sport] = {"picks": 0, "hits": 0}
                
                # Extract league info
                league = "Desconocida"
                if h.payload:
                    try:
                        p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                        league = p_data.get("competition") or "Desconocida"
                    except: pass
                
                # Extract team info
                teams = []
                if h.match_title:
                    if " vs " in h.match_title:
                        teams = [t.strip() for t in h.match_title.split(" vs ")]
                    elif " - " in h.match_title:
                        teams = [t.strip() for t in h.match_title.split(" - ")]

                for pick in picks:
                    is_pub = pick.get("is_publishable", False)
                    is_und = pick.get("is_underdog", False)
                    is_hc = pick.get("is_high_confidence", False)
                    
                    # Fallback for old picks that might only have is_value
                    if not is_pub and not is_und and not is_hc:
                        if pick.get("is_value", False):
                            is_pub = True
                            
                    if not (is_pub or is_und or is_hc):
                        continue
                        
                    if is_pub:
                        cat = "professional"
                    elif is_und:
                        cat = "underdog"
                    else:
                        cat = "high_confidence"

                    odds = float(pick.get("odds", 0.0))
                    
                    # Map clean market name
                    market = pick.get("market")
                    if not market or market == "N/A" or market == "Otro":
                        market = get_market_name(pick.get("selection", ""))

                    # Success and resolution
                    success = None
                    if has_result:
                        success = _check_pick_success(pick, results_dict)

                    has_pick_result = success is not None

                    # --- If unresolved (Pending), only increment pending counters and skip totals ---
                    if not has_pick_result:
                        total_pending += 1
                        cat_accumulators[cat]["total_pending"] += 1
                        continue

                    # --- Only resolved picks beyond this point ---
                    total_picks += 1
                    sport_stats[sport]["picks"] += 1
                    total_odds += odds

                    # Calculate pick profit: Win = odds-1, Loss = -1, Void = 0
                    pick_profit = 0.0
                    if success is True:
                        pick_profit = odds - 1.0
                    elif success is False:
                        pick_profit = -1.0
                    
                    total_profit += pick_profit
                    
                    # Accumulate daily profit (use match_date or analysis date)
                    match_day = (h.match_date or h.date).strftime("%Y-%m-%d") if (h.match_date or h.date) else None
                    if match_day:
                        daily_profit_dict[match_day] = daily_profit_dict.get(match_day, 0.0) + pick_profit

                    if market not in market_counters:
                        market_counters[market] = {"picks": 0, "hits": 0, "profit": 0.0}
                    market_counters[market]["picks"] += 1
                    market_counters[market]["profit"] += pick_profit
                    
                    if league not in league_counters:
                        league_counters[league] = {"picks": 0, "hits": 0, "profit": 0.0}
                    league_counters[league]["picks"] += 1
                    league_counters[league]["profit"] += pick_profit
                    
                    for t in teams:
                        if t not in team_counters:
                            team_counters[t] = {"picks": 0, "hits": 0, "profit": 0.0}
                        team_counters[t]["picks"] += 1
                        team_counters[t]["profit"] += pick_profit

                    if success is True:
                        total_hits += 1
                        sport_stats[sport]["hits"] += 1
                        market_counters[market]["hits"] += 1
                        league_counters[league]["hits"] += 1
                        for t in teams:
                            team_counters[t]["hits"] += 1
                        total_winning_odds += odds
                        winning_picks_count += 1

                    # Bucketing logic
                    edge_val = float(pick.get("edge_ev", 0.0)) * 100.0
                    conf = float(pick.get("calibrated_prob", pick.get("model_prob", 0.0)))

                    for low, high, label in odds_buckets_cfg:
                        if low <= odds < high:
                            odds_b_stats[label]["count"] += 1
                            odds_b_stats[label]["total_odds"] += odds
                            odds_b_stats[label]["resolved"] += 1
                            if success is True: odds_b_stats[label]["hits"] += 1
                            break

                    for low, high, label in edge_buckets_cfg:
                        if low <= edge_val < high:
                            edge_b_stats[label]["count"] += 1
                            edge_b_stats[label]["total_odds"] += odds
                            edge_b_stats[label]["resolved"] += 1
                            if success is True: edge_b_stats[label]["hits"] += 1
                            break

                    for low, high, label in conf_buckets_cfg:
                        if low <= conf < high:
                            conf_b_stats[label]["count"] += 1
                            conf_b_stats[label]["total_odds"] += odds
                            conf_b_stats[label]["resolved"] += 1
                            if success is True: conf_b_stats[label]["hits"] += 1
                            break

                    # --- Category-Specific Stats Accumulation ---
                    cat_acc = cat_accumulators[cat]
                    cat_acc["total_picks"] += 1
                    cat_acc["total_odds"] += odds
                    
                    cat_market_counters = cat_acc["market_counters"]
                    if market not in cat_market_counters:
                        cat_market_counters[market] = {"picks": 0, "hits": 0, "profit": 0.0}
                    cat_market_counters[market]["picks"] += 1
                    cat_market_counters[market]["profit"] += pick_profit
                    
                    cat_league_counters = cat_acc["league_counters"]
                    if league not in cat_league_counters:
                        cat_league_counters[league] = {"picks": 0, "hits": 0, "profit": 0.0}
                    cat_league_counters[league]["picks"] += 1
                    cat_league_counters[league]["profit"] += pick_profit
                    
                    cat_team_counters = cat_acc["team_counters"]
                    for t in teams:
                        if t not in cat_team_counters:
                            cat_team_counters[t] = {"picks": 0, "hits": 0, "profit": 0.0}
                        cat_team_counters[t]["picks"] += 1
                        cat_team_counters[t]["profit"] += pick_profit

                    if success is True:
                        cat_acc["total_hits"] += 1
                        cat_market_counters[market]["hits"] += 1
                        cat_league_counters[league]["hits"] += 1
                        for t in teams:
                            cat_team_counters[t]["hits"] += 1
                        cat_acc["total_winning_odds"] += odds
                        cat_acc["winning_picks_count"] += 1

                    # Bucketing logic for category
                    cat_odds_b_stats = cat_acc["odds_b_stats"]
                    for low, high, label in odds_buckets_cfg:
                        if low <= odds < high:
                            cat_odds_b_stats[label]["count"] += 1
                            cat_odds_b_stats[label]["total_odds"] += odds
                            cat_odds_b_stats[label]["resolved"] += 1
                            if success: cat_odds_b_stats[label]["hits"] += 1
                            break

                    cat_edge_b_stats = cat_acc["edge_b_stats"]
                    for low, high, label in edge_buckets_cfg:
                        if low <= edge_val < high:
                            cat_edge_b_stats[label]["count"] += 1
                            cat_edge_b_stats[label]["total_odds"] += odds
                            cat_edge_b_stats[label]["resolved"] += 1
                            if success: cat_edge_b_stats[label]["hits"] += 1
                            break

                    cat_conf_b_stats = cat_acc["conf_b_stats"]
                    for low, high, label in conf_buckets_cfg:
                        if low <= conf < high:
                            cat_conf_b_stats[label]["count"] += 1  # type: ignore[bad-index]
                            cat_conf_b_stats[label]["total_odds"] += odds  # type: ignore[bad-index]
                            cat_conf_b_stats[label]["resolved"] += 1  # type: ignore[bad-index]
                            if success: cat_conf_b_stats[label]["hits"] += 1  # type: ignore[bad-index]
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
        sport_stats[s]["accuracy"] = (hits / p * 100) if p > 0 else 0.0  # type: ignore[unsupported-operation]
        
    # Process market, league, team stats
    def to_stat_list(counters, min_picks=1):
        result = []
        for name, data in counters.items():
            if data["picks"] >= min_picks:
                acc = (data["hits"] / data["picks"] * 100) if data["picks"] > 0 else 0.0
                result.append({
                    "name": name,
                    "picks": data["picks"],
                    "hits": data["hits"],
                    "accuracy": acc,
                    "profit": round(data.get("profit", 0.0), 2)
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
    
    # Sort and slice by profit
    best_markets = sorted(all_markets, key=lambda x: x["profit"], reverse=True)
    worst_markets = []
    best_leagues = sorted(all_leagues, key=lambda x: x["profit"], reverse=True)
    best_teams = sorted(all_teams, key=lambda x: x["profit"], reverse=True)
    
    # Compile category-level stats
    category_stats_out = {}
    for cat in categories:
        cat_acc = cat_accumulators[cat]
        cat_picks = cat_acc["total_picks"]
        cat_hits = cat_acc["total_hits"]
        cat_pending = cat_acc["total_pending"]
        cat_accuracy = (cat_hits / cat_picks * 100) if cat_picks > 0 else 0.0
        cat_avg_odds = (cat_acc["total_odds"] / cat_picks) if cat_picks > 0 else 0.0
        cat_winning_picks = cat_acc["winning_picks_count"]
        cat_avg_winning_odds = (cat_acc["total_winning_odds"] / cat_winning_picks) if cat_winning_picks > 0 else 0.0
        
        cat_all_markets = to_stat_list(cat_acc["market_counters"])
        cat_all_leagues = to_stat_list(cat_acc["league_counters"], min_picks=2)
        cat_all_teams = to_stat_list(cat_acc["team_counters"], min_picks=2)
        
        cat_best_markets = sorted(cat_all_markets, key=lambda x: x["profit"], reverse=True)
        cat_worst_markets = []
        cat_best_leagues = sorted(cat_all_leagues, key=lambda x: x["profit"], reverse=True)
        cat_best_teams = sorted(cat_all_teams, key=lambda x: x["profit"], reverse=True)
        
        category_stats_out[cat] = {
            "total_picks": cat_picks,
            "total_hits": cat_hits,
            "total_pending": cat_pending,
            "accuracy": round(cat_accuracy, 1),
            "avg_odds": round(cat_avg_odds, 2),
            "avg_winning_odds": round(cat_avg_winning_odds, 2),
            "best_markets": cat_best_markets,
            "worst_markets": cat_worst_markets,
            "best_leagues": cat_best_leagues,
            "best_teams": cat_best_teams,
            "odds_buckets": bucket_to_list(cat_acc["odds_b_stats"]),
            "edge_buckets": bucket_to_list(cat_acc["edge_b_stats"]),
            "confidence_buckets": bucket_to_list(cat_acc["conf_b_stats"])
        }
        
    # Build daily profit series sorted by date, with cumulative
    daily_profit_series = []
    cumulative = 0.0
    for day in sorted(daily_profit_dict.keys()):
        cumulative += daily_profit_dict[day]
        daily_profit_series.append({
            "date": day,
            "daily": round(daily_profit_dict[day], 2),
            "cumulative": round(cumulative, 2)
        })

    return {
        "total_matches": total_matches,
        "total_matches_with_results": matches_with_results,
        "total_picks": total_picks,
        "total_hits": total_hits,
        "total_pending": total_pending,
        "global_accuracy": accuracy,
        "sport_stats": sport_stats,
        "total_exact_scores_predicted": total_exact_scores_predicted,
        "total_exact_scores_hits": total_exact_scores_hits,
        "avg_odds": avg_odds,
        "avg_winning_odds": avg_winning_odds,
        "total_profit": round(total_profit, 2),
        "daily_profit_series": daily_profit_series,
        "best_markets": best_markets,
        "worst_markets": worst_markets,
        "best_leagues": best_leagues,
        "best_teams": best_teams,
        "odds_buckets": bucket_to_list(odds_b_stats),
        "edge_buckets": bucket_to_list(edge_b_stats),
        "confidence_buckets": bucket_to_list(conf_b_stats),
        "category_stats": category_stats_out
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
            picks = json.loads(str(h.picks_calculados))
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
                "final_fouls_home": h.final_fouls_home,
                "final_fouls_away": h.final_fouls_away,
                "final_offsides_home": h.final_offsides_home,
                "final_offsides_away": h.final_offsides_away,
            }
            
            has_result = h.final_score_home is not None
            
            for pick in picks:
                is_pub = pick.get("is_publishable", False)
                is_und = pick.get("is_underdog", False)
                is_hc = pick.get("is_high_confidence", False)
                
                # Fallback for old picks that might only have is_value
                if not is_pub and not is_und and not is_hc:
                    if pick.get("is_value", False):
                        is_pub = True
                        
                if not (is_pub or is_und or is_hc):
                    continue

                success = None
                if has_result:
                    success = _check_pick_success(pick, results_dict)
                
                market = pick.get("market")
                if not market or market == "N/A" or market == "Otro":
                    market = get_market_name(pick.get("selection", ""))

                all_picks.append({
                    "match_id": h.id,
                    "match_title": h.match_title,
                    "sport": h.sport.value if hasattr(h.sport, 'value') else str(h.sport),
                    "date": h.date,
                    "selection": pick.get("selection", "N/A"),
                    "market": market,
                    "line": pick.get("line"),
                    "odds": pick.get("odds", 0.0),
                    "success": success,
                    "is_value": pick.get("is_value", False),
                    "is_high_confidence": is_hc,
                    "is_underdog": is_und,
                    "calibrated_prob": pick.get("calibrated_prob"),
                    "edge_ev": pick.get("edge_ev"),
                    "display_score": pick.get("display_score"),
                    "fair_odds": pick.get("fair_odds"),
                    "kelly_fraction": pick.get("kelly_fraction"),
                    "stat_support": pick.get("stat_support"),
                    "proj_support": pick.get("proj_support")
                })

        except Exception as err:
            print(f"Error packing picks: {err}")
            continue
            
    return all_picks


def _check_projected_line_success(p_line: dict, res: dict, home_name: str, away_name: str) -> bool | None:
    """Helper to verify if a projected line was successful based on results."""
    import math
    val = p_line.get("value")
    if val is None:
        return None

    # Determine type of projected line
    t = p_line.get("type", "").lower()
    label = p_line.get("label", "").lower()

    h_score = res.get("final_score_home")
    a_score = res.get("final_score_away")

    # Rounding rule: strictly greater than .5 rounds up
    def get_rounded(v):
        return math.floor(v) if (v - math.floor(v)) <= 0.5 else math.ceil(v)



    # DC (Doble Oportunidad)
    if t == "double_chance" or "doble oportunidad" in label or "dc" in label:
        if h_score is not None and a_score is not None:
            p_line["actual_val"] = f"{h_score}-{a_score}"
            if "1x" in label:
                return h_score >= a_score
            elif "x2" in label:
                return a_score >= h_score
            elif "12" in label:
                return h_score != a_score
        return None

    # BTTS Sí
    elif t == "btts" or "btts" in label:
        if h_score is not None and a_score is not None:
            p_line["actual_val"] = f"{h_score}-{a_score}"
            if "sí" in label or "yes" in label:
                return h_score > 0 and a_score > 0
            elif "no" in label:
                return h_score == 0 or a_score == 0
        return None

    # Over Goals (e.g. Over 2.5 Goles)
    elif t == "goals" and "over" in label:
        if h_score is not None and a_score is not None:
            import re
            match = re.search(r"over\s+(\d+(\.\d+)?)\s+goles", label)
            if match:
                line_val = float(match.group(1))
                total_g = h_score + a_score
                p_line["actual_val"] = total_g
                p_line["diff_sign"] = "+" if total_g > line_val else "-"
                return total_g > line_val
        return None

    # Handicap checking
    elif t == "handicap_prob":
        if h_score is not None and a_score is not None:
            p_line["actual_val"] = f"{h_score}-{a_score}"
            if home_name.lower() in label:
                diff = h_score + val - a_score
                return diff > 0
            elif away_name.lower() in label:
                diff = a_score + val - h_score
                return diff > 0
        return None

    elif t == "handicap" and "spread" in label:
        if h_score is not None and a_score is not None:
            p_line["actual_val"] = f"{h_score}-{a_score}"
            diff = h_score + val - a_score
            return diff > 0
        return None

    # Stats check - all stats are maximums (at_most)
    actual = None

    if t in ("goals", "goals_team") or "goals" in label or "goles" in label:
        if "totales" in label or "goles totales" in label:
            if h_score is not None and a_score is not None:
                actual = h_score + a_score
        elif home_name.lower() in label:
            if h_score is not None:
                actual = h_score
        elif away_name.lower() in label:
            if a_score is not None:
                actual = a_score

    elif t in ("corners", "corners_team") or "corners" in label:
        h_corn = res.get("final_corners_home")
        a_corn = res.get("final_corners_away")
        if "totales" in label or "corners totales" in label:
            if h_corn is not None and a_corn is not None:
                actual = h_corn + a_corn
        elif home_name.lower() in label:
            if h_corn is not None:
                actual = h_corn
        elif away_name.lower() in label:
            if a_corn is not None:
                actual = a_corn

    elif t in ("cards", "cards_team") or "cards" in label or "tarjetas" in label:
        h_y = res.get("final_yellow_cards_home") or 0
        a_y = res.get("final_yellow_cards_away") or 0
        h_r = res.get("final_red_cards_home") or 0
        a_r = res.get("final_red_cards_away") or 0
        total_cards = (h_y + a_y) + ((h_r + a_r) * 2)
        if "totales" in label or "tarjetas totales" in label:
            if res.get("final_yellow_cards_home") is not None:
                actual = total_cards
        elif home_name.lower() in label:
            if res.get("final_yellow_cards_home") is not None:
                actual = h_y + (h_r * 2)
        elif away_name.lower() in label:
            if res.get("final_yellow_cards_away") is not None:
                actual = a_y + (a_r * 2)

    elif t in ("shots", "shots_team") or "shots" in label or "tiros" in label:
        # Avoid shots target
        if "pta" not in label and "target" not in label and "puerta" not in label:
            h_s = res.get("final_shots_home")
            a_s = res.get("final_shots_away")
            if "totales" in label or "tiros totales" in label:
                if h_s is not None and a_s is not None:
                    actual = h_s + a_s
            elif home_name.lower() in label:
                if h_s is not None:
                    actual = h_s
            elif away_name.lower() in label:
                if a_s is not None:
                    actual = a_s

    elif t in ("shots_target", "shots_target_team") or "pta" in label or "target" in label or "puerta" in label:
        h_st = res.get("final_shots_on_target_home")
        a_st = res.get("final_shots_on_target_away")
        if "totales" in label or "puerta" in label:
            if h_st is not None and a_st is not None:
                actual = h_st + a_st
        elif home_name.lower() in label:
            if h_st is not None:
                actual = h_st
        elif away_name.lower() in label:
            if a_st is not None:
                actual = a_st

    elif t == "total" or "total puntos" in label:
        if h_score is not None and a_score is not None:
            actual = h_score + a_score

    elif t == "team_total" or "total" in label:
        if home_name.lower() in label:
            if h_score is not None:
                actual = h_score
        elif away_name.lower() in label:
            if a_score is not None:
                actual = a_score

    elif t in ("fouls", "fouls_team") or "fouls" in label or "faltas" in label:
        h_f = res.get("final_fouls_home")
        a_f = res.get("final_fouls_away")
        if "totales" in label or "faltas totales" in label:
            if h_f is not None and a_f is not None:
                actual = h_f + a_f
        elif home_name.lower() in label:
            if h_f is not None:
                actual = h_f
        elif away_name.lower() in label:
            if a_f is not None:
                actual = a_f

    elif t in ("offsides", "offsides_team") or "offsides" in label or "fuera de juego" in label or "fueras" in label:
        h_o = res.get("final_offsides_home")
        a_o = res.get("final_offsides_away")
        if "totales" in label or "offsides totales" in label or "fuera de juego totales" in label or "fueras de juego totales" in label:
            if h_o is not None and a_o is not None:
                actual = h_o + a_o
        elif home_name.lower() in label:
            if h_o is not None:
                actual = h_o
        elif away_name.lower() in label:
            if a_o is not None:
                actual = a_o

    if actual is not None:
        p_line["actual_val"] = actual
        if val > actual + 0.4:
            p_line["diff_sign"] = "+"
        elif val < actual - 0.5:
            p_line["diff_sign"] = "-"
        else:
            p_line["diff_sign"] = "="
        return (actual - 0.5) <= val <= (actual + 0.4)

    return None


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



    # Doble Oportunidad
    if "doble oportunidad 1x" in sel or "dc 1x" in sel or "1x" in sel:
        if h_score is not None and a_score is not None:
            return h_score >= a_score
    if "doble oportunidad x2" in sel or "dc x2" in sel or "x2" in sel:
        if h_score is not None and a_score is not None:
            return a_score >= h_score
    if "doble oportunidad 12" in sel or "dc 12" in sel or "12" in sel:
        if h_score is not None and a_score is not None:
            return h_score != a_score
        
    # Points / Total Score
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

    # Fouls
    if "faltas" in sel or "fouls" in sel:
        h_f = res.get("final_fouls_home")
        a_f = res.get("final_fouls_away")
        total_f = (h_f + a_f) if (h_f is not None and a_f is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            if line is not None and total_f is not None: return total_f > line
        if "under" in sel:
            line = _extract_line(sel, "under")
            if line is not None and total_f is not None: return total_f < line

    # Offsides
    if "offsides" in sel or "fuera de juego" in sel or "fueras" in sel:
        h_o = res.get("final_offsides_home")
        a_o = res.get("final_offsides_away")
        total_o = (h_o + a_o) if (h_o is not None and a_o is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            if line is not None and total_o is not None: return total_o > line
        if "under" in sel:
            line = _extract_line(sel, "under")
            if line is not None and total_o is not None: return total_o < line

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
        picks = json.loads(str(h.picks_calculados))
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
            "final_fouls_home": h.final_fouls_home,
            "final_fouls_away": h.final_fouls_away,
            "final_offsides_home": h.final_offsides_home,
            "final_offsides_away": h.final_offsides_away,
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

                    # 3. Projected lines success
                    if "projected_lines" in out.compare_response_snapshot:
                        home_name = out.compare_response_snapshot.get("home_name") or ""
                        away_name = out.compare_response_snapshot.get("away_name") or ""
                        if not home_name or not away_name:
                            parts = h.match_title.split(" vs ")
                            if len(parts) == 2:
                                home_name, away_name = parts[0].strip(), parts[1].strip()
                            else:
                                parts = h.match_title.split(" - ")
                                if len(parts) == 2:
                                    home_name, away_name = parts[0].strip(), parts[1].strip()
                        for p_line in out.compare_response_snapshot["projected_lines"]:
                            p_line["success"] = _check_projected_line_success(p_line, res_dict, home_name, away_name)
                            
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