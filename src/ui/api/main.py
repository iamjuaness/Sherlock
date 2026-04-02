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


@app.post("/api/v1/compare/football", response_model=CompareResponse, tags=["Comparator"])
async def compare_teams_football(request: FootballCompareRequest) -> CompareResponse:
    return await compare_football(request)


@app.post("/api/v1/compare/nba", response_model=CompareResponse, tags=["Comparator"])
async def compare_teams_nba(request: NBACompareRequest) -> CompareResponse:
    return await compare_nba(request)


@app.post("/api/v1/compare/tennis", response_model=CompareResponse, tags=["Comparator"])
async def compare_players_tennis(request: TennisCompareRequest) -> CompareResponse:
    return await compare_tennis(request)

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
            return await fn(request.home, request.away, vp, result.projected_lines, request.competition_name, user_context)

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
    """Save an analysis to history."""
    try:
        sport_enum = Sport(req.sport)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sport: {req.sport}")

    history = AnalysisHistory(
        sport=sport_enum,
        match_title=req.match_title,
        payload=json.dumps(req.payload),
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return AnalysisHistoryOut.model_validate(history)


@app.get("/api/v1/analysis", response_model=list[AnalysisHistoryOut], tags=["Analysis History"])
def list_analysis(
    sport: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
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

    if date_from:
        query = query.filter(AnalysisHistory.date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AnalysisHistory.date <= datetime.fromisoformat(date_to))

    query = query.order_by(AnalysisHistory.date.desc()).limit(limit)
    return [AnalysisHistoryOut.model_validate(h) for h in query.all()]


@app.get("/api/v1/analysis/{analysis_id}", response_model=AnalysisHistoryOut, tags=["Analysis History"])
def get_analysis_by_id(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> AnalysisHistoryOut:
    """Retrieve a specific analysis by ID."""
    history = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisHistoryOut.model_validate(history)

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