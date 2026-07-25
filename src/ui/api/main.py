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
    split_asian_line,
    _market_family,
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

MAX_STAKE = 5
MIN_STAKE = 1

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

@app.get("/leagues", tags=["Web UI"])
def serve_leagues(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    js_path = os.path.join(WEB_DIR, "static", "js", "leagues.js")
    
    js_ver = "1"
    if os.path.exists(js_path):
        js_ver = file_version(js_path)

    return templates.TemplateResponse(
        request=request,
        name="leagues.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
            "js_version": js_ver,
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
# Separate slot for Betano odds (merged into stats prefill on GET)
_prefill_odds_store: dict | None = None



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
    If there are pending Betano odds, they are merged into the payload.
    """
    global _prefill_store, _prefill_odds_store
    if _prefill_store is None and _prefill_odds_store is None:
        return {"pending": False}
        
    if _prefill_store is not None:
        data = dict(_prefill_store)
        _prefill_store = None
        # Merge pending Betano odds if present
        if _prefill_odds_store is not None:
            data["odds"] = _prefill_odds_store
            _prefill_odds_store = None
        return {"pending": True, "payload": data}
        
    # Only odds are pending
    data = {
        "odds": _prefill_odds_store,
        "sport": "football"
    }
    
    # Extract team names so the UI banner and form inputs can display them
    home_name = _prefill_odds_store.get("home_team")
    away_name = _prefill_odds_store.get("away_team")
    if home_name:
        data["home"] = {"name": home_name}
    if away_name:
        data["away"] = {"name": away_name}
        
    _prefill_odds_store = None
    return {"pending": True, "payload": data}


# ---------------------------------------------------------------------------
# Prefill/Odds endpoint — used by Watson extension to push Betano odds


def _normalize_betano_odds(raw: dict) -> dict:
    """
    Convert the snake_case payload from betano_content.js into the
    camelCase format that comparator.js populateAppForm() expects.

    Mapping applied:
      goals_over  → goalsOverOdds      goals_under  → goalsUnderOdds
      corners_over → cornersOverOdds   corners_under → cornersUnderOdds
      cards_over  → cardsOverOdds      cards_under  → cardsUnderOdds
      shots_over  → shotsOverOdds      shots_under  → shotsUnderOdds
      shots_target_over → shotsTargetOverOdds  shots_target_under → shotsTargetUnderOdds
      handicap_home → handicapHomeOdds handicap_away → handicapAwayOdds
      goals_lines  → goals_lines  (kept as-is for FootballOdds model)
    """
    def _to_float_dict(d) -> dict:
        if not isinstance(d, dict):
            return {}
        return {k: float(v) for k, v in d.items() if v is not None}

    def _to_float_list(lst) -> list:
        if not isinstance(lst, list):
            return []
        return [float(x) for x in lst if x is not None]

    normalized = {
        "bookmaker": raw.get("bookmaker", "betano"),
        "home_team": raw.get("home_team"),
        "away_team": raw.get("away_team"),
        "home":      raw.get("home"),
        "draw":      raw.get("draw"),
        "away":      raw.get("away"),
        "btts_yes":  raw.get("btts_yes"),
        "btts_no":   raw.get("btts_no"),
        "dc_1x":     raw.get("dc_1x"),
        "dc_x2":     raw.get("dc_x2"),
        "dc_12":     raw.get("dc_12"),
        "dnb_home":  raw.get("dnb_home"),
        "dnb_away":  raw.get("dnb_away"),
        # Lines (kept as snake_case — comparator reads goals_lines etc.)
        "goals_lines":       _to_float_list(raw.get("goals_lines", [])),
        "corners_lines":     _to_float_list(raw.get("corners_lines", [])),
        "cards_lines":       _to_float_list(raw.get("cards_lines", [])),
        "shots_lines":       _to_float_list(raw.get("shots_lines", [])),
        "shots_target_lines": _to_float_list(raw.get("shots_target_lines", [])),
        "handicap_lines":    _to_float_list(raw.get("handicap_lines", [])),
        # Odds dicts — converted to camelCase for comparator.js
        "goalsOverOdds":          _to_float_dict(raw.get("goals_over", {})),
        "goalsUnderOdds":         _to_float_dict(raw.get("goals_under", {})),
        "cornersOverOdds":        _to_float_dict(raw.get("corners_over", {})),
        "cornersUnderOdds":       _to_float_dict(raw.get("corners_under", {})),
        "cardsOverOdds":          _to_float_dict(raw.get("cards_over", {})),
        "cardsUnderOdds":         _to_float_dict(raw.get("cards_under", {})),
        "shotsOverOdds":          _to_float_dict(raw.get("shots_over", {})),
        "shotsUnderOdds":         _to_float_dict(raw.get("shots_under", {})),
        "shotsTargetOverOdds":    _to_float_dict(raw.get("shots_target_over", {})),
        "shotsTargetUnderOdds":   _to_float_dict(raw.get("shots_target_under", {})),
        "handicapHomeOdds":       _to_float_dict(raw.get("handicap_home", {})),
        "handicapAwayOdds":       _to_float_dict(raw.get("handicap_away", {})),
    }

    # Derive over_25 / under_25 / over_15 / under_15 for legacy fields
    go = normalized["goalsOverOdds"]
    gu = normalized["goalsUnderOdds"]
    normalized["over_25"]  = go.get("2.5")
    normalized["under_25"] = gu.get("2.5")
    normalized["over_15"]  = go.get("1.5")
    normalized["under_15"] = gu.get("1.5")

    return normalized


@app.post("/api/v1/prefill/odds", tags=["Prefill"])
async def push_prefill_odds(payload: dict) -> dict:
    """
    Watson extension (betano_content.js) pushes Betano odds here separately
    from the SofaScore stats payload.

    Expected body (wrapped by betano_content.js):
    {
      "odds": {
        "bookmaker": "betano",
        "home_team": "Mushuc Runa",
        "away_team": "Orense",
        "home": 2.02, "draw": 3.4, "away": 3.6,
        "btts_yes": 1.82, "btts_no": 1.9,
        "dc_1x": 1.31, "dc_x2": 1.82, "dc_12": 1.3,
        "dnb_home": 1.47, "dnb_away": 2.57,
        "goals_lines": ["1.5","2.5"], "goals_over": {"1.5":...,"2.5":...}, ...
      }
    }
    """
    global _prefill_odds_store
    raw_odds = payload.get("odds", payload)  # unwrap if wrapped in {"odds": ...}
    _prefill_odds_store = _normalize_betano_odds(raw_odds)
    return {
        "status": "ok",
        "message": "Cuotas Betano recibidas. Se inyectarán en el comparador.",
        "home_team": raw_odds.get("home_team"),
        "away_team": raw_odds.get("away_team"),
    }


@app.get("/api/v1/prefill/odds", tags=["Prefill"])
async def consume_prefill_odds() -> dict:
    """
    Returns the last Betano odds payload (standalone, without stats).
    Single-use: clears the slot after returning.
    """
    global _prefill_odds_store
    if _prefill_odds_store is None:
        return {"pending": False}
    data = _prefill_odds_store
    _prefill_odds_store = None
    return {"pending": True, "odds": data}


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

                    # Detailed stats from SofaScore
                    det_fields = [
                        "expected_goals_home", "expected_goals_away",
                        "ball_possession_home", "ball_possession_away",
                        "aerial_duels_percentage_home", "aerial_duels_percentage_away",
                        "ground_duels_percentage_home", "ground_duels_percentage_away",
                        "dribbles_percentage_home", "dribbles_percentage_away",
                        "duel_won_percent_home", "duel_won_percent_away",
                        "won_tackle_percent_home", "won_tackle_percent_away",
                        "goals_prevented_home", "goals_prevented_away",
                        "accurate_cross_home", "accurate_cross_away",
                        "accurate_long_balls_home", "accurate_long_balls_away",
                        "accurate_passes_home", "accurate_passes_away",
                        "accurate_through_ball_home", "accurate_through_ball_away",
                        "ball_recovery_home", "ball_recovery_away",
                        "big_chance_created_home", "big_chance_created_away",
                        "big_chance_missed_home", "big_chance_missed_away",
                        "big_chance_scored_home", "big_chance_scored_away",
                        "blocked_scoring_attempt_home", "blocked_scoring_attempt_away",
                        "corner_kicks_home", "corner_kicks_away",
                        "dispossessed_home", "dispossessed_away",
                        "dive_saves_home", "dive_saves_away",
                        "final_third_entries_home", "final_third_entries_away",
                        "final_third_phase_statistic_home", "final_third_phase_statistic_away",
                        "fouled_final_third_home", "fouled_final_third_away",
                        "fouls_home", "fouls_away",
                        "free_kicks_home", "free_kicks_away",
                        "goal_kicks_home", "goal_kicks_away",
                        "goalkeeper_saves_home", "goalkeeper_saves_away",
                        "high_claims_home", "high_claims_away",
                        "hit_woodwork_home", "hit_woodwork_away",
                        "interception_won_home", "interception_won_away",
                        "offsides_home", "offsides_away",
                        "passes_home", "passes_away",
                        "punches_home", "punches_away",
                        "shots_off_goal_home", "shots_off_goal_away",
                        "shots_on_goal_home", "shots_on_goal_away",
                        "throw_ins_home", "throw_ins_away",
                        "total_clearance_home", "total_clearance_away",
                        "total_shots_inside_box_home", "total_shots_inside_box_away",
                        "total_shots_on_goal_home", "total_shots_on_goal_away",
                        "total_shots_outside_box_home", "total_shots_outside_box_away",
                        "total_tackle_home", "total_tackle_away",
                        "touches_in_opp_box_home", "touches_in_opp_box_away",
                        "yellow_cards_home", "yellow_cards_away"
                    ]
                    for field in det_fields:
                        if field in payload:
                            setattr(h, field, payload.get(field))

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
                                    if pick.get("is_blacklisted"):
                                        continue
                                    if not (pick.get("is_publishable", pick.get("is_value", False))):
                                        continue
                                    success = _check_pick_success(pick, results_dict)
                                    if success is not None and success != "void":
                                        total += 1
                                        if _is_pick_hit(success):
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
        # Create a new AnalysisHistory record for this match result (e.g. historical data)
        try:
            sport_enum = Sport(sport)
            competition_name = payload.get("tournament.name") or payload.get("competition") or "Desconocida"
            match_title = f"{home_name} vs {away_name}"

            # Reconstruct cleanup payload for storage
            cleaned_payload = {
                "sport": sport,
                "home": {"name": home_name},
                "away": {"name": away_name},
                "competition": competition_name,
                "season_year": payload.get("season_year"),
                "season_id": payload.get("season_id"),
                "tournament_id": payload.get("tournament_id"),
                "round": payload.get("round"),
                "start_timestamp": payload.get("start_timestamp"),
                "event_id": payload.get("event_id")
            }

            print(f"Reconstruido payload: {cleaned_payload}")

            match_date_val = None
            if payload.get("start_timestamp"):
                match_date_val = datetime.utcfromtimestamp(payload["start_timestamp"])
            else:
                match_date_val = datetime.utcnow()

            # ── Deduplication: skip if exact same event already saved ──
            event_id_str = str(payload.get("event_id")) if payload.get("event_id") else None
            if event_id_str:
                existing_by_event = db.query(AnalysisHistory).filter(
                    AnalysisHistory.sport == sport_enum,
                    AnalysisHistory.match_title == match_title,
                    AnalysisHistory.match_date == match_date_val,
                ).first()
                if existing_by_event:
                    return {
                        "status": "ok",
                        "message": f"Evento {event_id_str} ya existe — omitido",
                        "auto_updated": False,
                        "skipped_duplicate": True
                    }

            history = AnalysisHistory(
                sport=sport_enum,
                match_title=match_title,
                payload=json.dumps(cleaned_payload),
                date=match_date_val,
                match_date=match_date_val,
                picks_calculados=None,
                has_real_stats=True,
                count_in_profitability=False, # Don't skew stats since it has no picks
                final_score_home=payload.get("final_score_home"),
                final_score_away=payload.get("final_score_away"),
                final_corners_home=payload.get("final_corners_home"),
                final_corners_away=payload.get("final_corners_away"),
                final_yellow_cards_home=payload.get("final_yellow_cards_home"),
                final_yellow_cards_away=payload.get("final_yellow_cards_away"),
                final_red_cards_home=payload.get("final_red_cards_home"),
                final_red_cards_away=payload.get("final_red_cards_away"),
                final_shots_home=payload.get("final_shots_home"),
                final_shots_away=payload.get("final_shots_away"),
                final_shots_on_target_home=payload.get("final_shots_on_target_home"),
                final_shots_on_target_away=payload.get("final_shots_on_target_away"),
                final_fouls_home=payload.get("final_fouls_home"),
                final_fouls_away=payload.get("final_fouls_away"),
                final_offsides_home=payload.get("final_offsides_home"),
                final_offsides_away=payload.get("final_offsides_away")
            )
            
            # Detailed stats from SofaScore
            det_fields = [
                "expected_goals_home", "expected_goals_away",
                "ball_possession_home", "ball_possession_away",
                "aerial_duels_percentage_home", "aerial_duels_percentage_away",
                "ground_duels_percentage_home", "ground_duels_percentage_away",
                "dribbles_percentage_home", "dribbles_percentage_away",
                "duel_won_percent_home", "duel_won_percent_away",
                "won_tackle_percent_home", "won_tackle_percent_away",
                "goals_prevented_home", "goals_prevented_away",
                "accurate_cross_home", "accurate_cross_away",
                "accurate_long_balls_home", "accurate_long_balls_away",
                "accurate_passes_home", "accurate_passes_away",
                "accurate_through_ball_home", "accurate_through_ball_away",
                "ball_recovery_home", "ball_recovery_away",
                "big_chance_created_home", "big_chance_created_away",
                "big_chance_missed_home", "big_chance_missed_away",
                "big_chance_scored_home", "big_chance_scored_away",
                "blocked_scoring_attempt_home", "blocked_scoring_attempt_away",
                "corner_kicks_home", "corner_kicks_away",
                "dispossessed_home", "dispossessed_away",
                "dive_saves_home", "dive_saves_away",
                "final_third_entries_home", "final_third_entries_away",
                "final_third_phase_statistic_home", "final_third_phase_statistic_away",
                "fouled_final_third_home", "fouled_final_third_away",
                "fouls_home", "fouls_away",
                "free_kicks_home", "free_kicks_away",
                "goal_kicks_home", "goal_kicks_away",
                "goalkeeper_saves_home", "goalkeeper_saves_away",
                "high_claims_home", "high_claims_away",
                "hit_woodwork_home", "hit_woodwork_away",
                "interception_won_home", "interception_won_away",
                "offsides_home", "offsides_away",
                "passes_home", "passes_away",
                "punches_home", "punches_away",
                "shots_off_goal_home", "shots_off_goal_away",
                "shots_on_goal_home", "shots_on_goal_away",
                "throw_ins_home", "throw_ins_away",
                "total_clearance_home", "total_clearance_away",
                "total_shots_inside_box_home", "total_shots_inside_box_away",
                "total_shots_on_goal_home", "total_shots_on_goal_away",
                "total_shots_outside_box_home", "total_shots_outside_box_away",
                "total_tackle_home", "total_tackle_away",
                "touches_in_opp_box_home", "touches_in_opp_box_away",
                "yellow_cards_home", "yellow_cards_away"
            ]
            for field in det_fields:
                if field in payload:
                    setattr(history, field, payload.get(field))
            
            db.add(history)
            db.commit()
            
            return {
                "status": "ok",
                "message": f"Resultado guardado como nuevo registro histórico para {home_name} vs {away_name}.",
                "auto_updated": False,
                "created_new": True
            }
        except Exception as create_ex:
            print(f"Error creating historical record: {create_ex}")
            return {
                "status": "error",
                "message": f"Error al crear registro histórico: {str(create_ex)}",
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
            return await fn(request.home, request.away, vp, result.projected_lines, request.league_stats, request.competition, user_context)

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
        has_real_stats_val = req.has_real_stats if req.has_real_stats is not None else True
        if req.count_in_profitability is not None:
            count_in_prof_val = req.count_in_profitability
        else:
            count_in_prof_val = False if not has_real_stats_val else True

        if req.count_in_profitability is not None:
            # pyrefly: ignore [bad-assignment]
            existing.count_in_profitability = req.count_in_profitability
        elif not has_real_stats_val:
            existing.count_in_profitability = False

        if req.has_real_stats is not None:
            # pyrefly: ignore [bad-assignment]
            existing.has_real_stats = req.has_real_stats
        
        db.commit()
        db.refresh(existing)
        out = AnalysisHistoryOut.model_validate(existing)
        return _populate_history_extra_fields(existing, out)

    # Create new record
    # Use match_date if provided, otherwise use current time (same as `date`)
    record_date = req.match_date or datetime.utcnow()
    has_real_stats_val = req.has_real_stats if req.has_real_stats is not None else True
    if req.count_in_profitability is not None:
        count_in_prof_val = req.count_in_profitability
    else:
        count_in_prof_val = False if not has_real_stats_val else True

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
        count_in_profitability=count_in_prof_val,
        has_real_stats=has_real_stats_val,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)


@app.post("/api/v1/analysis/quick-save", response_model=AnalysisHistoryOut, tags=["Analysis History"])
def quick_save_match(
    payload: dict,
    db: Session = Depends(get_db)
) -> AnalysisHistoryOut:
    """
    Saves a match details without statistics (early league / placeholder match).
    Automatically maps tournament/competition details.
    """
    sport = payload.get("sport", "football")
    try:
        sport_enum = Sport(sport)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sport: {sport}")

    home_name = payload.get("home", {}).get("name") or "Local"
    away_name = payload.get("away", {}).get("name") or "Visitante"
    match_title = f"{home_name} vs {away_name}"
    
    # competition gets correctly set here
    competition = payload.get("competition") or "Desconocida"
    
    # Prepare clean payload for quick save
    cleaned_payload = {
        "sport": sport,
        "home": payload.get("home", {}),
        "away": payload.get("away", {}),
        "competition": competition,
        "league_stats": payload.get("league_stats", {}),
        "odds": payload.get("odds", {})
    }

    # Find existing or create
    existing = db.query(AnalysisHistory).filter(
        AnalysisHistory.sport == sport_enum,
        AnalysisHistory.match_title == match_title
    ).first()

    record_date = datetime.utcnow()

    if existing:
        existing.payload = json.dumps(cleaned_payload)
        existing.has_real_stats = False
        existing.count_in_profitability = False
        db.commit()
        db.refresh(existing)
        out = AnalysisHistoryOut.model_validate(existing)
        return _populate_history_extra_fields(existing, out)

    history = AnalysisHistory(
        sport=sport_enum,
        match_title=match_title,
        payload=json.dumps(cleaned_payload),
        date=record_date,
        match_date=record_date,
        picks_calculados=None,
        has_real_stats=False,
        count_in_profitability=False
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
    competition: str | None = Query(None),
    limit: int = Query(5000, ge=1, le=10000),
    use_stake: bool = Query(False),
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

    query = query.order_by(AnalysisHistory.date.desc())
    history_list = query.all()
    
    # Filter by competition in JSON payload if specified
    if competition:
        filtered_list = []
        for h in history_list:
            if h.payload:
                try:
                    p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                    c_name = p_data.get("competition") or p_data.get("competition") or "Desconocida"
                    if c_name.lower() == competition.lower():
                        filtered_list.append(h)
                except:
                    pass
        history_list = filtered_list
        
    # Slice list by limit
    history_list = history_list[:limit]
    
    results = []
    for h in history_list:
        out = AnalysisHistoryOut.model_validate(h)
        results.append(_populate_history_extra_fields(h, out, use_stake=use_stake))
    return results


@app.get("/api/v1/stats/leagues", tags=["Stats"])
def get_leagues_stats(
    use_stake: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Groups AnalysisHistory by competition inside the JSON payload and calculates stats.
    Also computes per-market hit rates and historical performance data for LRS computation.
    """
    history = db.query(AnalysisHistory).all()
    leagues_data = {}
    
    for h in history:
        # Resolve competition name
        comp_name = "Desconocida"
        if h.payload:
            try:
                p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                comp_name = p_data.get("competition") or "Desconocida"
            except:
                pass
                
        if comp_name not in leagues_data:
            leagues_data[comp_name] = {
                "name": comp_name,
                "total_matches": 0,
                "total_picks": 0,
                "total_hits": 0,
                "accuracy": 0.0,
                "total_profit": 0.0,
                "has_pending_matches": False,
                # Per-market tracking: {family: {"hits": 0, "total": 0}}
                "_market_stats": {},
            }
            
        leagues_data[comp_name]["total_matches"] += 1
        
        if h.picks_calculados:
            try:
                picks = json.loads(h.picks_calculados) if isinstance(h.picks_calculados, str) else h.picks_calculados
                if isinstance(picks, list):
                    res_dict = {
                        "final_score_home": h.final_score_home,
                        "final_score_away": h.final_score_away,
                        "final_corners_home": h.final_corners_home,
                        "final_corners_away": h.final_corners_away,
                        "final_yellow_cards_home": h.final_yellow_cards_home,
                        "final_yellow_cards_away": h.final_yellow_cards_away,
                        "final_red_cards_home": h.final_red_cards_home,
                        "final_red_cards_away": h.final_red_cards_away,
                    }
                    
                    has_result = h.final_score_home is not None
                    
                    for pick in picks:
                        if pick.get("is_blacklisted"):
                            continue
                        is_pub = pick.get("is_publishable", False)
                        is_und = pick.get("is_underdog", False)
                        is_hc = pick.get("is_high_confidence", False)
                        
                        if not is_pub and not is_und and not is_hc:
                            if pick.get("is_value", False):
                                is_pub = True
                                
                        if not (is_pub or is_und or is_hc):
                            continue
                        
                        # If resolving success
                        if has_result:
                            success = _check_pick_success(pick, res_dict)
                            if success is not None:
                                if use_stake:
                                    kelly = float(pick.get("kelly_fraction") or 0.0)
                                    stake = min(MAX_STAKE, max(MIN_STAKE, round(kelly * 100.0))) if kelly > 0 else MIN_STAKE
                                else:
                                    stake = MIN_STAKE
                                pick_profit = _calculate_pick_profit(success, pick.get("odds", 0.0)) * stake
                                leagues_data[comp_name]["total_profit"] += pick_profit
                                if success != "void":
                                    leagues_data[comp_name]["total_picks"] += 1
                                    is_hit = _is_pick_hit(success)
                                    if is_hit:
                                        leagues_data[comp_name]["total_hits"] += 1
                                    
                                    # Track per-market hit rate
                                    sel_text = pick.get("selection", "")
                                    try:
                                        family = _market_family(sel_text)
                                    except Exception:
                                        family = "generic"
                                    mkt = leagues_data[comp_name]["_market_stats"]
                                    if family not in mkt:
                                        mkt[family] = {"hits": 0, "total": 0}
                                    mkt[family]["total"] += 1
                                    if is_hit:
                                        mkt[family]["hits"] += 1
                        else:
                            leagues_data[comp_name]["has_pending_matches"] = True
            except:
                pass

    # Calculate final accuracies, round profits, compute market_hit_rates and LRS
    results = []
    for league in leagues_data.values():
        picks_cnt = league["total_picks"]
        league["accuracy"] = round((league["total_hits"] / picks_cnt * 100), 1) if picks_cnt > 0 else 0.0
        league["total_profit"] = round(league["total_profit"], 2)
        
        # Build market_hit_rates dict: {family: rate}
        raw_mkt = league.pop("_market_stats", {})
        market_hit_rates = {}
        for family, stats in raw_mkt.items():
            if stats["total"] >= 3:  # mínimo 3 picks para considerar la tasa
                market_hit_rates[family] = round(stats["hits"] / stats["total"], 3)
        league["market_hit_rates"] = market_hit_rates
        
        # Historical data for LRS
        league["historical_matches"] = league["total_matches"]
        league["historical_picks"] = picks_cnt
        league["historical_hits"] = league["total_hits"]
        league["historical_profit"] = league["total_profit"]
        
        results.append(league)
        
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
                    if pick.get("is_blacklisted"):
                        continue
                    # Filter: Only "Value" picks are counted for model accuracy stats
                    if not (pick.get("is_publishable", pick.get("is_value", False))):
                        continue
                        
                    success = _check_pick_success(pick, results_dict)
                    if success is not None:
                        if success != "void":
                            total += 1
                            if _is_pick_hit(success):
                                hits += 1
                
                if total > 0:
                    # pyrefly: ignore [bad-assignment]
                    history.accuracy_percentage = (hits / total) * 100
        except Exception as e:
            print(f"Error calculating accuracy: {e}")

    db.commit()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)


@app.post("/api/v1/analysis/{analysis_id}/profitability", tags=["Analysis History"])
def update_analysis_profitability(
    analysis_id: str,
    count_in_profitability: bool = Query(...),
    db: Session = Depends(get_db),
):
    """Update count_in_profitability status for a given match."""
    history = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Analysis not found")
    history.count_in_profitability = count_in_profitability
    db.commit()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)


@app.post("/api/v1/analysis/recalculate-all", tags=["Analysis History"])
async def recalculate_all_accuracy(
    use_general_stats: bool = Query(False),
    threshold_date: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """
    Re-analiza todos los registros del historial:
    1. Vuelve a calcular los picks usando el payload original (motor de predicción).
    2. Actualiza los snapshots y los picks calculados.
    3. Si hay resultados finales, recalcula el acierto (accuracy_percentage).
    """
    threshold_dt = None
    if threshold_date:
        try:
            threshold_dt = datetime.strptime(threshold_date, "%Y-%m-%d")
        except Exception:
            try:
                threshold_dt = datetime.fromisoformat(threshold_date)
            except Exception:
                pass

    history_list = db.query(AnalysisHistory).all()
    count = 0
    updated_accuracy_count = 0
    
    for history in history_list:
        try:
            if not history.payload:
                continue
                
            # Skip matches with no calculated picks (picks_calculados is empty/null/[])
            if not history.picks_calculados or not str(history.picks_calculados).strip() or str(history.picks_calculados).strip() == "[]":
                continue
                
            # Cargar el payload original
            payload_dict = json.loads(str(history.payload))
            sport = history.sport
            
            # Determine correct use_general_stats based on parameter and threshold
            target_use_gen = False
            if use_general_stats:
                if threshold_dt:
                    m_date = history.match_date or history.date
                    if m_date:
                        target_use_gen = m_date.date() >= threshold_dt.date()
                    else:
                        target_use_gen = True
                else:
                    target_use_gen = True
            
            payload_dict["use_general_stats"] = target_use_gen
            history.payload = json.dumps(payload_dict)
            
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
                        if pick.get("is_blacklisted"):
                            continue
                        # Filtro: Solo picks de valor cuentan para la estadística oficial
                        if not (pick.get("is_publishable", pick.get("is_value", False))):
                            continue
                            
                        success = _check_pick_success(pick, results_dict)
                        if success is not None and success != "void":
                            total += 1
                            if _is_pick_hit(success):
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


@app.post("/api/v1/analysis/apply-blacklist", tags=["Analysis History"])
def apply_blacklist(db: Session = Depends(get_db)):
    """
    Actualiza el estado de blacklist/publicación de los picks ya guardados
    en base a los parámetros actuales de data/league_penalties.json,
    sin recalcular probabilidades de los partidos.
    """
    from src.ui.api.compare import (
        is_market_blacklisted_for_league,
        is_publishable_pick,
        is_high_confidence_pick,
        is_underdog_pick,
        score_pick_quality,
        _calculate_display_score,
        _frontend_style_strategic_score,
        ValueIndicator
    )
    import json

    history_list = db.query(AnalysisHistory).all()
    updated_count = 0

    for history in history_list:
        if not history.picks_calculados:
            continue
        try:
            picks = json.loads(str(history.picks_calculados))
            if not isinstance(picks, list) or len(picks) == 0:
                continue

            # Obtener el nombre de la liga/competencia desde el payload
            league_name = None
            if history.payload:
                try:
                    p_data = json.loads(str(history.payload))
                    league_name = p_data.get("competition")
                except Exception:
                    pass

            if not league_name:
                continue

            changed = False
            for pick in picks:
                sel = pick.get("selection")
                if not sel:
                    continue

                # Comprobar si está en la blacklist
                should_be_blacklisted = is_market_blacklisted_for_league(league_name, sel)
                current_blacklisted = pick.get("is_blacklisted", False)

                if should_be_blacklisted != current_blacklisted:
                    changed = True
                    pick["is_blacklisted"] = should_be_blacklisted

                    if should_be_blacklisted:
                        pick["is_publishable"] = False
                        pick["is_value"] = False
                        pick["quality_score"] = -1
                        pick["strategic_score"] = -1
                        pick["is_high_confidence"] = False
                        pick["is_underdog"] = False
                    else:
                        # Re-construimos ValueIndicator temporal para re-calcular los campos utilizando las fórmulas
                        v = ValueIndicator(
                            selection=sel,
                            odds=pick.get("odds"),
                            model_prob=pick.get("model_prob", 0.0),
                            calibrated_prob=pick.get("calibrated_prob"),
                            edge_ev=pick.get("edge_ev", 0.0),
                            data_quality_score=pick.get("data_quality_score"),
                            sample_size_weight=pick.get("sample_size_weight"),
                            is_blacklisted=False
                        )
                        # Re-calculamos usando las funciones de compare.py
                        pick["is_publishable"] = is_publishable_pick(v)
                        pick["is_value"] = (v.edge_ev or 0.0) > 0.03
                        pick["quality_score"] = score_pick_quality(v)
                        pick["display_score"] = _calculate_display_score(v)
                        pick["is_high_confidence"] = is_high_confidence_pick(v)
                        pick["is_underdog"] = is_underdog_pick(v)
                        pick["strategic_score"] = _frontend_style_strategic_score(v)

            if changed:
                history.picks_calculados = json.dumps(picks)
                
                # Recalcular el accuracy del partido en base a los picks actualizados
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
                    
                    for p_item in picks:
                        if p_item.get("is_blacklisted"):
                            continue
                        if not (p_item.get("is_publishable", p_item.get("is_value", False))):
                            continue
                            
                        success = _check_pick_success(p_item, results_dict)
                        if success is not None and success != "void":
                            total += 1
                            if _is_pick_hit(success):
                                hits += 1
                    
                    if total > 0:
                        history.accuracy_percentage = (hits / total) * 100
                    else:
                        history.accuracy_percentage = None

                updated_count += 1
        except Exception as e:
            print(f"Error actualizando blacklist para {history.id}: {e}")

    if updated_count > 0:
        db.commit()

    return {
        "status": "ok",
        "message": f"Se actualizó la blacklist en {updated_count} partidos del historial.",
        "updated_count": updated_count
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
def get_global_stats(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    use_stake: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Calculate global performance metrics across all sports with advanced analytics."""
    query = db.query(AnalysisHistory)
    if date_from:
        try:
            query = query.filter(AnalysisHistory.date >= datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            query = query.filter(AnalysisHistory.date <= datetime.fromisoformat(date_to))
        except Exception:
            pass
            
    history = query.all()
    # Filter only matches that count in profitability
    history = [h for h in history if getattr(h, "count_in_profitability", True)]
    
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
    total_staked_picks = 0
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
            "total_profit": 0.0,
            "total_staked_picks": 0,
            "total_odds": 0.0,
            "total_winning_odds": 0.0,
            "winning_picks_count": 0,
            "market_counters": {},
            "league_counters": {},
            "team_counters": {},
            "odds_b_stats": {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in odds_buckets_cfg},
            "edge_b_stats": {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in edge_buckets_cfg},
            "conf_b_stats": {label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0} for _, _, label in conf_buckets_cfg},
            "daily_profit_dict": {}
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
                    if pick.get("is_blacklisted"):
                        continue
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
                    if use_stake:
                        kelly = float(pick.get("kelly_fraction") or 0.0)
                        stake = min(MAX_STAKE, max(MIN_STAKE, round(kelly * 100.0))) if kelly > 0 else MIN_STAKE
                    else:
                        stake = MIN_STAKE
                    pick_profit = _calculate_pick_profit(success, odds) * stake
                    total_profit += pick_profit

                    counts_for_accuracy = success != "void"
                    if counts_for_accuracy:
                        total_picks += 1
                        total_staked_picks += stake
                        sport_stats[sport]["picks"] += 1
                        total_odds += odds
                    
                    # Accumulate daily profit (use match_date or analysis date)
                    match_day = (h.match_date or h.date).strftime("%Y-%m-%d") if (h.match_date or h.date) else None
                    if match_day:
                        daily_profit_dict[match_day] = daily_profit_dict.get(match_day, 0.0) + pick_profit
                        cat_accumulators[cat]["daily_profit_dict"][match_day] = cat_accumulators[cat]["daily_profit_dict"].get(match_day, 0.0) + pick_profit

                    if counts_for_accuracy:
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

                        if _is_pick_hit(success):
                            total_hits += 1
                            sport_stats[sport]["hits"] += 1
                            market_counters[market]["hits"] += 1
                            league_counters[league]["hits"] += 1
                            for t in teams:
                                team_counters[t]["hits"] += 1
                            total_winning_odds += odds
                            winning_picks_count += 1

                    # Bucketing logic (solo picks con stake efectivo)
                    edge_val = float(pick.get("edge", 0.0))
                    conf = float(pick.get("calibrated_prob", pick.get("model_prob", 0.0)))

                    if counts_for_accuracy:
                        for low, high, label in odds_buckets_cfg:
                            if low <= odds < high:
                                odds_b_stats[label]["count"] += 1
                                odds_b_stats[label]["total_odds"] += odds
                                odds_b_stats[label]["resolved"] += 1
                                if _is_pick_hit(success): odds_b_stats[label]["hits"] += 1
                                break

                        for low, high, label in edge_buckets_cfg:
                            if low <= edge_val < high:
                                edge_b_stats[label]["count"] += 1
                                edge_b_stats[label]["total_odds"] += odds
                                edge_b_stats[label]["resolved"] += 1
                                if _is_pick_hit(success): edge_b_stats[label]["hits"] += 1
                                break

                        for low, high, label in conf_buckets_cfg:
                            if low <= conf < high:
                                conf_b_stats[label]["count"] += 1
                                conf_b_stats[label]["total_odds"] += odds
                                conf_b_stats[label]["resolved"] += 1
                                if _is_pick_hit(success): conf_b_stats[label]["hits"] += 1
                                break

                    # --- Category-Specific Stats Accumulation ---
                    cat_acc = cat_accumulators[cat]
                    cat_acc["total_profit"] += pick_profit
                    if counts_for_accuracy:
                        cat_acc["total_picks"] += 1
                        cat_acc["total_staked_picks"] += stake
                        cat_acc["total_odds"] += odds
                    
                    cat_market_counters = cat_acc["market_counters"]
                    if counts_for_accuracy:
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

                        if _is_pick_hit(success):
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
                                if _is_pick_hit(success): cat_odds_b_stats[label]["hits"] += 1
                                break

                        cat_edge_b_stats = cat_acc["edge_b_stats"]
                        for low, high, label in edge_buckets_cfg:
                            if low <= edge_val < high:
                                cat_edge_b_stats[label]["count"] += 1
                                cat_edge_b_stats[label]["total_odds"] += odds
                                cat_edge_b_stats[label]["resolved"] += 1
                                if _is_pick_hit(success): cat_edge_b_stats[label]["hits"] += 1
                                break

                        cat_conf_b_stats = cat_acc["conf_b_stats"]
                        for low, high, label in conf_buckets_cfg:
                            if low <= conf < high:
                                cat_conf_b_stats[label]["count"] += 1  # type: ignore[bad-index]
                                cat_conf_b_stats[label]["total_odds"] += odds  # type: ignore[bad-index]
                                cat_conf_b_stats[label]["resolved"] += 1  # type: ignore[bad-index]
                                if _is_pick_hit(success): cat_conf_b_stats[label]["hits"] += 1  # type: ignore[bad-index]
                                break

            except Exception as e:
                print(f"Error in global stats loop: {e}")
                continue
                
    accuracy = (total_hits / total_picks * 100) if total_picks > 0 else 0.0
    roi = (total_profit / total_staked_picks * 100) if total_staked_picks > 0 else 0.0
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
        cat_roi = (cat_acc["total_profit"] / cat_acc["total_staked_picks"] * 100) if cat_acc["total_staked_picks"] > 0 else 0.0
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
        
        cat_daily_profit_dict = cat_acc["daily_profit_dict"]
        cat_daily_profit_series = []
        cat_cumulative = 0.0
        for day in sorted(cat_daily_profit_dict.keys()):
            cat_cumulative += cat_daily_profit_dict[day]
            cat_daily_profit_series.append({
                "date": day,
                "daily": round(cat_daily_profit_dict[day], 2),
                "cumulative": round(cat_cumulative, 2)
            })
            
        category_stats_out[cat] = {
            "total_picks": cat_picks,
            "total_hits": cat_hits,
            "total_pending": cat_pending,
            "total_profit": round(cat_acc["total_profit"], 2),
            "roi": round(cat_roi, 1),
            "accuracy": round(cat_accuracy, 1),
            "avg_odds": round(cat_avg_odds, 2),
            "avg_winning_odds": round(cat_avg_winning_odds, 2),
            "best_markets": cat_best_markets,
            "worst_markets": cat_worst_markets,
            "best_leagues": cat_best_leagues,
            "best_teams": cat_best_teams,
            "odds_buckets": bucket_to_list(cat_acc["odds_b_stats"]),
            "edge_buckets": bucket_to_list(cat_acc["edge_b_stats"]),
            "confidence_buckets": bucket_to_list(cat_acc["conf_b_stats"]),
            "daily_profit_series": cat_daily_profit_series
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
        "roi": round(roi, 1),
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


@app.get("/api/v1/report/excel", tags=["Stats"])
def export_excel_report(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    use_stake: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Genera y descarga un reporte detallado en Excel (.xlsx) con los datos del modelo, partidos, picks y rentabilidad."""
    import io
    import json
    import pandas as pd
    import openpyxl
    from openpyxl.utils import get_column_letter
    from datetime import datetime

    # 1. Consultar registros
    query = db.query(AnalysisHistory)
    if date_from:
        try:
            query = query.filter(AnalysisHistory.date >= datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            query = query.filter(AnalysisHistory.date <= datetime.fromisoformat(date_to))
        except Exception:
            pass
            
    history = query.all()
    
    matches_data = []
    picks_data = []
    
    # Métricas generales de resumen
    total_matches = len(history)
    matches_with_results = 0
    total_picks = 0
    total_hits = 0
    total_pending = 0
    total_profit = 0.0
    total_odds = 0.0
    total_staked_picks = 0
    total_winning_odds = 0.0
    winning_picks_count = 0
    total_exact_scores_predicted = 0
    total_exact_scores_hits = 0
    
    # Acumuladores de categorías
    categories = ["professional", "underdog", "high_confidence"]
    cat_accumulators = {
        cat: {
            "picks": 0,
            "hits": 0,
            "pending": 0,
            "profit": 0.0,
            "staked": 0,
            "odds": 0.0,
            "winning_odds": 0.0,
            "winning_count": 0
        }
        for cat in categories
    }
    
    # Acumuladores de ligas y mercados
    league_counters = {}
    market_counters = {}
    
    for h in history:
        has_result = h.final_score_home is not None
        if has_result:
            matches_with_results += 1
            
        # Obtener liga del payload
        league = "Desconocida"
        if h.payload:
            try:
                p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                league = p_data.get("competition") or "Desconocida"
            except:
                pass
                
        # Obtener equipos del título del partido
        teams = []
        if h.match_title:
            if " vs " in h.match_title:
                teams = [t.strip() for t in h.match_title.split(" vs ")]
            elif " - " in h.match_title:
                teams = [t.strip() for t in h.match_title.split(" - ")]
                
        # Verificar marcador exacto
        exact_score_pred = "N/A"
        exact_score_hit = "N/A"
        if h.final_score_home is not None and h.final_score_away is not None and h.compare_response_snapshot:
            try:
                snap = json.loads(h.compare_response_snapshot) if isinstance(h.compare_response_snapshot, str) else h.compare_response_snapshot
                if isinstance(snap, dict) and snap.get("most_probable_score"):
                    exact_score_pred = snap["most_probable_score"]
                    total_exact_scores_predicted += 1
                    predicted_parts = exact_score_pred.split("-")
                    if len(predicted_parts) == 2:
                        pred_h = int(predicted_parts[0].strip())
                        pred_a = int(predicted_parts[1].strip())
                        if pred_h == h.final_score_home and pred_a == h.final_score_away:
                            total_exact_scores_hits += 1
                            exact_score_hit = "Sí"
                        else:
                            exact_score_hit = "No"
            except:
                pass
                
        # Añadir datos de partidos
        matches_data.append({
            "ID Partido": h.id,
            "Fecha de Análisis": h.date.strftime("%Y-%m-%d %H:%M") if h.date else "",
            "Fecha de Partido": h.match_date.strftime("%Y-%m-%d %H:%M") if h.match_date else "",
            "Deporte": h.sport.value if hasattr(h.sport, 'value') else str(h.sport),
            "Partido": h.match_title,
            "Goles Local": h.final_score_home,
            "Goles Visitante": h.final_score_away,
            "Corners Local": h.final_corners_home,
            "Corners Visitante": h.final_corners_away,
            "Tarjetas Amarillas Local": h.final_yellow_cards_home,
            "Tarjetas Amarillas Visitante": h.final_yellow_cards_away,
            "Tarjetas Rojas Local": h.final_red_cards_home,
            "Tarjetas Rojas Visitante": h.final_red_cards_away,
            "Remates Local": h.final_shots_home,
            "Remates Visitante": h.final_shots_away,
            "Remates al Arco Local": h.final_shots_on_target_home,
            "Remates al Arco Visitante": h.final_shots_on_target_away,
            "Faltas Local": h.final_fouls_home,
            "Faltas Visitante": h.final_fouls_away,
            "Fueras de Juego Local": h.final_offsides_home,
            "Fueras de Juego Visitante": h.final_offsides_away,
            "Predicción Marcador": exact_score_pred,
            "Marcador Acertado": exact_score_hit,
            "Precisión (%)": h.accuracy_percentage,
            "Cuenta en Rentabilidad": "Sí" if getattr(h, "count_in_profitability", True) else "No",
            "Tiene Stats Reales": "Sí" if getattr(h, "has_real_stats", True) else "No",
        })
        
        # Procesar Picks
        if h.picks_calculados:
            try:
                picks = json.loads(str(h.picks_calculados))
                if isinstance(picks, list):
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
                    
                    for pick in picks:
                        if pick.get("is_blacklisted"):
                            continue
                        is_pub = pick.get("is_publishable", False)
                        is_und = pick.get("is_underdog", False)
                        is_hc = pick.get("is_high_confidence", False)
                        
                        if not is_pub and not is_und and not is_hc:
                            if pick.get("is_value", False):
                                is_pub = True
                                
                        if not (is_pub or is_und or is_hc):
                            continue
                            
                        cat = "professional" if is_pub else ("underdog" if is_und else "high_confidence")
                        
                        odds = float(pick.get("odds", 0.0))
                        market = pick.get("market")
                        if not market or market == "N/A" or market == "Otro":
                            market = get_market_name(pick.get("selection", ""))
                            
                        success = None
                        if has_result:
                            success = _check_pick_success(pick, results_dict)
                            
                        counts_in_prof = getattr(h, "count_in_profitability", True)
                        
                        success_str = "Pendiente"
                        pick_profit = 0.0
                        
                        if use_stake:
                            kelly = float(pick.get("kelly_fraction") or 0.0)
                            stake = min(MAX_STAKE, max(MIN_STAKE, round(kelly * 100.0))) if kelly > 0 else MIN_STAKE
                        else:
                            stake = MIN_STAKE
                            
                        if success is not None:
                            if success is True:
                                success_str = "Hit"
                            elif success is False:
                                success_str = "Miss"
                            elif success == "void":
                                success_str = "Void"
                            elif success == "half_win":
                                success_str = "Half Win"
                            elif success == "half_loss":
                                success_str = "Half Loss"
                                
                            pick_profit = _calculate_pick_profit(success, odds) * stake
                        
                        if success is None:
                            total_pending += 1
                            cat_accumulators[cat]["pending"] += 1
                        else:
                            counts_for_accuracy = success != "void"
                            total_profit += pick_profit
                            cat_accumulators[cat]["profit"] += pick_profit
                                
                            if counts_for_accuracy:
                                total_picks += 1
                                total_staked_picks += stake
                                total_odds += odds
                                cat_accumulators[cat]["picks"] += 1
                                cat_accumulators[cat]["staked"] += stake
                                cat_accumulators[cat]["odds"] += odds
                                
                                if league not in league_counters:
                                    league_counters[league] = {"picks": 0, "hits": 0, "profit": 0.0}
                                league_counters[league]["picks"] += 1
                                league_counters[league]["profit"] += pick_profit
                                
                                if market not in market_counters:
                                    market_counters[market] = {"picks": 0, "hits": 0, "profit": 0.0}
                                market_counters[market]["picks"] += 1
                                market_counters[market]["profit"] += pick_profit
                                
                                if _is_pick_hit(success):
                                    total_hits += 1
                                    total_winning_odds += odds
                                    winning_picks_count += 1
                                    cat_accumulators[cat]["hits"] += 1
                                    cat_accumulators[cat]["winning_odds"] += odds
                                    cat_accumulators[cat]["winning_count"] += 1
                                    
                                    league_counters[league]["hits"] += 1
                                    market_counters[market]["hits"] += 1
                                        
                        picks_data.append({
                            "ID Partido": h.id,
                            "Fecha": h.date.strftime("%Y-%m-%d %H:%M") if h.date else "",
                            "Partido": h.match_title,
                            "Deporte": h.sport.value if hasattr(h.sport, 'value') else str(h.sport),
                            "Selección": pick.get("selection", ""),
                            "Mercado": market,
                            "Línea": pick.get("line"),
                            "Cuota": odds,
                            "Prob Calibrada (%)": float(pick.get("calibrated_prob", 0.0)) if pick.get("calibrated_prob") is not None else None,
                            "Prob Modelo (%)": float(pick.get("model_prob", 0.0)) if pick.get("model_prob") is not None else None,
                            "EV Edge (%)": float(pick.get("edge", 0.0)) if pick.get("edge") is not None else None,
                            "Fracción Kelly (%)": float(pick.get("kelly_fraction", 0.0)) if pick.get("kelly_fraction") is not None else None,
                            "Stake Sugerido (u)": max(1, round(float(pick.get("kelly_fraction", 0.0)) * 100.0)) if float(pick.get("kelly_fraction", 0.0)) > 0 else 1,
                            "Resultado": success_str,
                            "Beneficio (u)": pick_profit if success is not None else None,
                            "Categoría": cat,
                            "Cuenta en Rentabilidad": "Sí" if counts_in_prof else "No"
                        })
            except Exception as ex:
                pass
                
    # 3. Crear DataFrames de Pandas
    global_accuracy = (total_hits / total_picks * 100) if total_picks > 0 else 0.0
    global_roi = (total_profit / total_staked_picks * 100) if total_staked_picks > 0 else 0.0
    global_avg_odds = (total_odds / total_picks) if total_picks > 0 else 0.0
    global_avg_winning_odds = (total_winning_odds / winning_picks_count) if winning_picks_count > 0 else 0.0
    exact_hit_rate = (total_exact_scores_hits / total_exact_scores_predicted * 100) if total_exact_scores_predicted > 0 else 0.0
    
    summary_general_rows = [
        {"Métrica": "Partidos Analizados Totales", "Valor": total_matches},
        {"Métrica": "Partidos con Resultado", "Valor": matches_with_results},
        {"Métrica": "Picks Evaluados Totales", "Valor": total_picks},
        {"Métrica": "Picks Acertados (Hits)", "Valor": total_hits},
        {"Métrica": "Picks Pendientes", "Valor": total_pending},
        {"Métrica": "Precisión de Picks (%)", "Valor": round(global_accuracy, 2)},
        {"Métrica": "Rentabilidad Total (unidades)", "Valor": round(total_profit, 2)},
        {"Métrica": "ROI (%)", "Valor": round(global_roi, 2)},
        {"Métrica": "Cuota Promedio Evaluada", "Valor": round(global_avg_odds, 2)},
        {"Métrica": "Cuota Promedio Ganadora", "Valor": round(global_avg_winning_odds, 2)},
        {"Métrica": "Predicciones Marcador Exacto", "Valor": total_exact_scores_predicted},
        {"Métrica": "Aciertos Marcador Exacto", "Valor": total_exact_scores_hits},
        {"Métrica": "Tasa Acierto Marcador Exacto (%)", "Valor": round(exact_hit_rate, 2)},
    ]
    df_summary_general = pd.DataFrame(summary_general_rows)
    
    category_summary_rows = []
    for cat in categories:
        cat_acc = cat_accumulators[cat]
        cat_picks = cat_acc["picks"]
        cat_hits = cat_acc["hits"]
        cat_accuracy = (cat_hits / cat_picks * 100) if cat_picks > 0 else 0.0
        cat_roi = (cat_acc["profit"] / cat_acc["staked"] * 100) if cat_acc["staked"] > 0 else 0.0
        cat_avg_odds = (cat_acc["odds"] / cat_picks) if cat_picks > 0 else 0.0
        cat_avg_winning_odds = (cat_acc["winning_odds"] / cat_acc["winning_count"]) if cat_acc["winning_count"] > 0 else 0.0
        
        category_summary_rows.append({
            "Categoría": cat.capitalize(),
            "Picks Evaluados": cat_picks,
            "Aciertos (Hits)": cat_hits,
            "Pendientes": cat_acc["pending"],
            "Rentabilidad (u)": round(cat_acc["profit"], 2),
            "ROI (%)": round(cat_roi, 2),
            "Precisión (%)": round(cat_accuracy, 2),
            "Cuota Promedio": round(cat_avg_odds, 2),
            "Cuota Ganadora Promedio": round(cat_avg_winning_odds, 2)
        })
    df_summary_categories = pd.DataFrame(category_summary_rows)
    
    df_matches = pd.DataFrame(matches_data)
    df_picks = pd.DataFrame(picks_data)
    
    # Desglose de Ligas
    league_rows = []
    for league, stats in league_counters.items():
        l_picks = stats["picks"]
        l_hits = stats["hits"]
        l_acc = (l_hits / l_picks * 100) if l_picks > 0 else 0.0
        league_rows.append({
            "Liga / Competición": league,
            "Picks Evaluados": l_picks,
            "Aciertos (Hits)": l_hits,
            "Precisión (%)": round(l_acc, 2),
            "Rentabilidad (u)": round(stats["profit"], 2)
        })
    df_leagues = pd.DataFrame(league_rows)
    if not df_leagues.empty:
        df_leagues = df_leagues.sort_values(by="Rentabilidad (u)", ascending=False)
        
    # Desglose de Mercados
    market_rows = []
    for market, stats in market_counters.items():
        m_picks = stats["picks"]
        m_hits = stats["hits"]
        m_acc = (m_hits / m_picks * 100) if m_picks > 0 else 0.0
        market_rows.append({
            "Mercado": market,
            "Picks Evaluados": m_picks,
            "Aciertos (Hits)": m_hits,
            "Precisión (%)": round(m_acc, 2),
            "Rentabilidad (u)": round(stats["profit"], 2)
        })
    df_markets = pd.DataFrame(market_rows)
    if not df_markets.empty:
        df_markets = df_markets.sort_values(by="Rentabilidad (u)", ascending=False)
        
    # 4. Escribir archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_summary_general.to_excel(writer, sheet_name="Resumen", index=False, startrow=1)
        df_summary_categories.to_excel(writer, sheet_name="Resumen", index=False, startrow=18)
        
        df_matches.to_excel(writer, sheet_name="Partidos Analizados", index=False)
        df_picks.to_excel(writer, sheet_name="Detalle de Picks", index=False)
        df_leagues.to_excel(writer, sheet_name="Rentabilidad por Liga", index=False)
        df_markets.to_excel(writer, sheet_name="Rentabilidad por Mercado", index=False)
        
        workbook = writer.book
        
        # Formatos en pestaña Resumen
        resumen_ws = workbook["Resumen"]
        resumen_ws["A1"] = "Estadísticas Generales Sherlock"
        resumen_ws["A1"].font = openpyxl.styles.Font(size=14, bold=True)
        resumen_ws["A17"] = "Desglose por Categoría"
        resumen_ws["A17"].font = openpyxl.styles.Font(size=14, bold=True)
        
        for sheet_name in workbook.sheetnames:
            ws = workbook[sheet_name]
            for col in ws.columns:
                max_len = 0
                for cell in col:
                    if cell.value:
                        if sheet_name == "Resumen" and cell.coordinate in ["A1", "A17"]:
                            continue
                        max_len = max(max_len, len(str(cell.value)))
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 11)
                
    output.seek(0)
    
    filename = f"Reporte_Sherlock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/v1/stats/picks", response_model=list[PickStat], tags=["Stats"])
def get_all_picks(
    limit: int = 100,
    sport: str | None = None,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
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
            
    if date_from:
        try:
            query = query.filter(AnalysisHistory.date >= datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            query = query.filter(AnalysisHistory.date <= datetime.fromisoformat(date_to))
        except Exception:
            pass
            
    # filter out matches that shouldn't count in profitability
    query = query.filter(AnalysisHistory.count_in_profitability != False)
            
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
                if pick.get("is_blacklisted"):
                    continue
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
                    "count_in_profitability": getattr(h, "count_in_profitability", True),
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


PickOutcome = bool | str | None


def _settle_total_line(total: float, line: float, side: str) -> str:
    """Liquida over/under para una línea simple. Devuelve win/loss/push."""
    if side == "over":
        if total > line:
            return "win"
        if total < line:
            return "loss"
        return "push"
    if total < line:
        return "win"
    if total > line:
        return "loss"
    return "push"


def _combine_split_outcomes(results: list[str]) -> PickOutcome:
    """Combina resultados de líneas asiáticas divididas (.25 / .75)."""
    if len(results) == 1:
        r = results[0]
        if r == "win":
            return True
        if r == "loss":
            return False
        return "void"

    if all(r == "win" for r in results):
        return True
    if all(r == "loss" for r in results):
        return False
    if all(r == "push" for r in results):
        return "void"
    if "win" in results and "push" in results:
        return "half_win"
    if "loss" in results and "push" in results:
        return "half_loss"
    return None


def _resolve_ou_outcome(total: float | None, line: float | None, side: str) -> PickOutcome:
    """Resuelve over/under incluyendo push y medias asiáticas."""
    if total is None or line is None:
        return None
    lines = split_asian_line(line)
    results = [_settle_total_line(total, l, side) for l in lines]
    return _combine_split_outcomes(results)


def _resolve_ah_outcome(h_score: int, a_score: int, line: float, for_home: bool) -> PickOutcome:
    """Resuelve Asian Handicap para local o visitante."""
    margin_base = (h_score - a_score) if for_home else (a_score - h_score)
    lines = split_asian_line(line)
    results = []
    for l in lines:
        margin = margin_base + l
        if margin > 0:
            results.append("win")
        elif margin < 0:
            results.append("loss")
        else:
            results.append("push")
    return _combine_split_outcomes(results)


def _parse_ah_line(selection: str) -> float | None:
    """Extrae la línea de un pick AH, p.ej. 'AH -0.50 Real Madrid'."""
    import re
    match = re.search(r"ah\s*([+-]?\d+(?:\.\d+)?)", selection, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _calculate_pick_profit(outcome: PickOutcome, odds: float) -> float:
    """Calcula beneficio en unidades con stake plano de 1u."""
    if outcome is None:
        return 0.0
    if outcome is True:
        return odds - 1.0
    if outcome is False:
        return -1.0
    if outcome == "void":
        return 0.0
    if outcome == "half_win":
        return (odds - 1.0) / 2.0
    if outcome == "half_loss":
        return -0.5
    return 0.0


def _is_pick_hit(outcome: PickOutcome) -> bool:
    """True si el pick cuenta como acierto (incluye half-win)."""
    return outcome is True or outcome == "half_win"


def _check_pick_success(pick: dict, res: dict) -> PickOutcome:
    """Helper to verify if a pick was successful based on results."""
    sel = pick.get("selection", "").lower()
    
    h_score = res.get("final_score_home")
    a_score = res.get("final_score_away")

    # DNB (Draw No Bet)
    if "dnb" in sel:
        if h_score is not None and a_score is not None:
            if h_score == a_score:
                return "void"
            if "local" in sel or "home" in sel:
                return h_score > a_score
            if "visitante" in sel or "away" in sel:
                return a_score > h_score

    # Asian Handicap
    if sel.startswith("ah ") or " ah " in sel:
        if h_score is not None and a_score is not None:
            line = _parse_ah_line(sel)
            if line is not None:
                home_name = (pick.get("home_team") or "").lower()
                for_home = "local" in sel or "home" in sel or (home_name and home_name in sel)
                if not for_home and not ("visitante" in sel or "away" in sel):
                    # Inferir lado por el signo si no hay pista explícita
                    for_home = line <= 0
                return _resolve_ah_outcome(h_score, a_score, line, for_home=for_home)
    
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
            return _resolve_ou_outcome(total_p, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_p, line, "under")

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
            return _resolve_ou_outcome(total_g, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_g, line, "under")

    # Corners
    h_corn = res.get("final_corners_home")
    a_corn = res.get("final_corners_away")
    if "corners" in sel:
        total_c = (h_corn + a_corn) if (h_corn is not None and a_corn is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            return _resolve_ou_outcome(total_c, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_c, line, "under")

    # Cards
    h_y = res.get("final_yellow_cards_home") or 0
    a_y = res.get("final_yellow_cards_away") or 0
    h_r = res.get("final_red_cards_home") or 0
    a_r = res.get("final_red_cards_away") or 0
    total_cards = (h_y + a_y) + ((h_r + a_r) * 2)
    if "tarjetas" in sel or "cards" in sel:
        if "over" in sel:
            line = _extract_line(sel, "over")
            return _resolve_ou_outcome(total_cards, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_cards, line, "under")

    # Shots
    h_s = res.get("final_shots_home")
    a_s = res.get("final_shots_away")
    if "tiros" in sel or "shots" in sel:
        if "pta" in sel or "target" in sel:
            h_st = res.get("final_shots_on_target_home")
            a_st = res.get("final_shots_on_target_away")
            total_st = (h_st + a_st) if (h_st is not None and a_st is not None) else None
            if "over" in sel:
                line = _extract_line(sel, "over")
                return _resolve_ou_outcome(total_st, line, "over")
            if "under" in sel:
                line = _extract_line(sel, "under")
                return _resolve_ou_outcome(total_st, line, "under")
        else:
            total_s = (h_s + a_s) if (h_s is not None and a_s is not None) else None
            if "over" in sel:
                line = _extract_line(sel, "over")
                return _resolve_ou_outcome(total_s, line, "over")
            if "under" in sel:
                line = _extract_line(sel, "under")
                return _resolve_ou_outcome(total_s, line, "under")

    # Fouls
    if "faltas" in sel or "fouls" in sel:
        h_f = res.get("final_fouls_home")
        a_f = res.get("final_fouls_away")
        total_f = (h_f + a_f) if (h_f is not None and a_f is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            return _resolve_ou_outcome(total_f, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_f, line, "under")

    # Offsides
    if "offsides" in sel or "fuera de juego" in sel or "fueras" in sel:
        h_o = res.get("final_offsides_home")
        a_o = res.get("final_offsides_away")
        total_o = (h_o + a_o) if (h_o is not None and a_o is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            return _resolve_ou_outcome(total_o, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_o, line, "under")

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

def _populate_history_extra_fields(h: AnalysisHistory, out: AnalysisHistoryOut, use_stake: bool = False) -> AnalysisHistoryOut:
    """Computa campos virtuales de picks y acierto para el historial."""
    if not h.picks_calculados:
        out.has_picks = False
        out.profit = 0.0
        return out
        
    try:
        picks = json.loads(str(h.picks_calculados))
        if not isinstance(picks, list):
            out.has_picks = False
            out.profit = 0.0
            return out
            
        # Solo se consideran para el resumen de acierto los picks de Valor
        relevant_picks = [p for p in picks if (p.get("is_value") or p.get("is_publishable") or p.get("is_underdog") or p.get("is_high_confidence")) and not p.get("is_blacklisted")]
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
            match_profit = 0.0
            has_resolved = False
            for p in relevant_picks:
                success = _check_pick_success(p, res_dict)
                if success is not None:
                    if success != "void":
                        total += 1
                        has_resolved = True
                        if _is_pick_hit(success):
                            hits += 1
                    
                    if use_stake:
                        kelly = float(p.get("kelly_fraction") or 0.0)
                        stake = min(MAX_STAKE, max(MIN_STAKE, round(kelly * 100.0))) if kelly > 0 else MIN_STAKE
                    else:
                        stake = MIN_STAKE
                    pick_profit = _calculate_pick_profit(success, float(p.get("odds") or 0.0)) * stake
                    match_profit += pick_profit
            if total > 0:
                out.picks_hits_summary = f"{hits}/{total}"
            if has_resolved:
                out.profit = round(match_profit, 2)
            else:
                out.profit = None

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