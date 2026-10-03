"""FastAPI application – Sherlock REST API."""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import asyncio
import copy
import traceback

from fastapi.responses import StreamingResponse
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import or_, and_

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
    _market_family
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os
from fastapi.middleware.cors import CORSMiddleware
import io
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

from contextlib import asynccontextmanager
from src.ui.api.admin_routes import admin_router

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

app.include_router(admin_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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

MAX_STAKE = 3
MIN_STAKE = 1

app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(WEB_DIR, "templates"))

def file_version(path: str) -> str:
    return str(int(os.path.getmtime(path)))

def _resolve_stake_from_pick(pick: dict) -> float:
    explicit = pick.get("stake_units")
    if explicit is not None and explicit > 0:
        return float(explicit)
    
    kelly = float(pick.get("kelly_fraction") or 0.0)
    if kelly > 0:
        return min(MAX_STAKE, max(MIN_STAKE, round(kelly * 100.0)))
    return MIN_STAKE


def _extract_competition(payload) -> str | None:
    """Extract competition name from payload dict, avoiding json.loads in callers."""
    if not payload:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return None
    comp = payload.get("competition")
    if comp and isinstance(comp, str) and comp.strip():
        return comp.strip()
    tournament = payload.get("tournament")
    if isinstance(tournament, dict):
        name = tournament.get("name")
        if name and isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _extract_bookmaker(payload) -> str | None:
    """Extract primary bookmaker from payload dict."""
    if not payload:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return None
    bm = payload.get("bookmaker")
    if bm and isinstance(bm, str):
        return bm.strip() or None
    sources = payload.get("sources")
    if isinstance(sources, list) and sources:
        bm = sources[0].get("bookmaker") if isinstance(sources[0], dict) else None
        if bm and isinstance(bm, str):
            return bm.strip() or None
    return None


def _sum_stake_from_picks(picks_calculados) -> float | None:
    """Return the sum of stake_units for publishable picks of a match."""
    if not picks_calculados:
        return None
    try:
        picks = json.loads(picks_calculados) if isinstance(picks_calculados, str) else picks_calculados
        if not isinstance(picks, list):
            return None
        total = 0.0
        counted = 0
        for p in picks:
            if p.get("is_blacklisted") or p.get("is_rule_blocked"):
                continue
            is_pub = p.get("is_publishable", False)
            is_und = p.get("is_underdog", False)
            if not is_pub and not is_und:
                if p.get("is_value", False):
                    is_pub = True
            if not (is_pub or is_und):
                continue
            total += float(p.get("stake_units") or 1.0)
            counted += 1
        return round(total, 4) if counted > 0 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# In-memory TTL cache for aggregated stats endpoints
# ---------------------------------------------------------------------------
import time
from threading import Lock

_stats_cache: dict = {}
_stats_cache_lock = Lock()
_STATS_TTL: float = 30.0  # seconds — fallback; explicit invalidation is the primary mechanism


def _get_cache(key: str):
    """Return cached value if still fresh, else None."""
    with _stats_cache_lock:
        entry = _stats_cache.get(key)
        if entry and (time.monotonic() - entry["ts"]) < _STATS_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data) -> None:
    """Store value in cache with current timestamp."""
    with _stats_cache_lock:
        _stats_cache[key] = {"data": data, "ts": time.monotonic()}


def _invalidate_stats_cache() -> None:
    """Clear all cached stats — called after any AnalysisHistory write."""
    with _stats_cache_lock:
        _stats_cache.clear()


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


@app.get("/rules", tags=["Web UI"])
def serve_rules(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    return templates.TemplateResponse(
        request=request,
        name="rules.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
        },
    )


@app.get("/api/v1/sports", response_model=list[SportOut], tags=["Sports"])
def list_sports() -> list[SportOut]:
    """List available sports."""
    return [SportOut(value=s.value, label=s.value.capitalize()) for s in Sport]


@app.get("/api/v1/competitions", tags=["Competitions"])
def list_competitions():
    """Return active competitions list from data/competitions.json."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))), "data", "competitions.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(os.getcwd(), "data", "competitions.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading competitions.json: {e}")
    return []

## Obtener la cantidad de partidos de una liga en especifico
@app.get("/api/v1/competitions/{competition_id}/matches", tags=["Competitions"])
def list_matches(competition_id: str, db: Session = Depends(get_db)):
    """Return the number of matches for a specific competition."""
    from sqlalchemy.orm import load_only
    query = db.query(AnalysisHistory).filter(AnalysisHistory.competition == competition_id).options(load_only(AnalysisHistory.id)).count()
    return query

@app.get("/api/v1/competitions/pending-picks", tags=["Competitions"])
def list_competitions_with_pending_picks(db: Session = Depends(get_db)):
    """Return list of competition names that have pending picks (final score not set)."""
    from sqlalchemy.orm import load_only
    rows = (
        db.query(AnalysisHistory)
        .options(load_only(AnalysisHistory.competition, AnalysisHistory.payload, AnalysisHistory.final_score_home))
        .filter(AnalysisHistory.final_score_home.is_(None))
        .all()
    )
    comps = set()
    for r in rows:
        c_name = r.competition
        if not c_name and r.payload:
            try:
                p = json.loads(r.payload) if isinstance(r.payload, str) else r.payload
                c_name = p.get("competition") or p.get("tournament", {}).get("name")
            except Exception:
                pass
        if c_name:
            comps.add(c_name.strip())
    return {"pending_competitions": list(comps)}



# ---------------------------------------------------------------------------
# Prefill endpoint — used by browser extensions to push form data
# ---------------------------------------------------------------------------
# In-memory slot: stores the last payload pushed by the extension.
# Solo un slot activo a la vez; se limpia una vez el frontend lo consume.
prefill_store: dict | None = None

# Acumulador por casa de apuestas: {"betano": {...normalizado...}, "betplay": {...}}
prefill_odds_store: dict[str, dict] = {}

# A qué partido pertenece lo acumulado actualmente (para resetear si cambia el partido)
prefill_odds_match: tuple | None = None



@app.post("/api/v1/prefill", tags=["Prefill"])
async def push_prefill(payload: dict) -> dict:
    """
    Browser extension pushes a (partial) form payload here.
    The Sherlock dashboard polls this endpoint and auto-fills the form.
    """
    global prefill_store
    prefill_store = payload
    return {"status": "ok", "message": "Datos recibidos. Sherlock los cargará en el formulario."}


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
        # Lines (kept as snake_case — comparator reads goals_lines etc.)
        "goals_lines":       _to_float_list(raw.get("goals_lines", [])),
        "corners_lines":     _to_float_list(raw.get("corners_lines", [])),
        "cards_lines":       _to_float_list(raw.get("cards_lines", [])),
        "shots_lines":       _to_float_list(raw.get("shots_lines", [])),
        "shots_target_lines": _to_float_list(raw.get("shots_target_lines", [])),
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
        "shotsTargetUnderOdds":   _to_float_dict(raw.get("shots_target_under", {}))
    }

    # Derive over_25 / under_25 / over_15 / under_15 for legacy fields
    go = normalized["goalsOverOdds"]
    gu = normalized["goalsUnderOdds"]
    normalized["over_25"]  = go.get("2.5")
    normalized["under_25"] = gu.get("2.5")
    normalized["over_15"]  = go.get("1.5")
    normalized["under_15"] = gu.get("1.5")

    return normalized

def _check_payload_has_odds(payload: dict | str | None) -> bool:
    """Helper to determine if a payload dict or JSON string contains valid odds (> 1.0)."""
    if not payload:
        return False
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
        if not isinstance(data, dict):
            return False

        odds_data = data.get("odds")
        sources_data = data.get("sources")
        if isinstance(odds_data, dict) and not sources_data:
            sources_data = odds_data.get("sources")

        def _has_valid(d: Any) -> bool:
            if isinstance(d, dict):
                return any(_has_valid(v) for v in d.values())
            elif isinstance(d, list):
                return any(_has_valid(v) for v in d)
            elif isinstance(d, (int, float)):
                return d > 1.0
            return False

        if odds_data and _has_valid(odds_data):
            return True
        if sources_data and _has_valid(sources_data):
            return True
        return False
    except Exception:
        return False


def _merge_best_odds(sources: dict) -> dict:
    """
    Recorre las cuotas crudas de todas las casas (formato de
    prefill_odds_store / _normalize_betano_odds) y calcula, para cada
    campo de FootballOdds, la MEJOR cuota disponible entre casas.

    Devuelve:
      - "odds_update": dict con nombres de campo de FootballOdds (snake_case)
         listo para pasar a `FootballOdds.model_copy(update=...)`.
      - "bookmaker_map": mismo shape, pero con el nombre de la casa que
         ofrece esa mejor cuota (para anotar los picks después).
    """
    if not sources:
        return {"odds_update": {}, "bookmaker_map": {}}

    simple_field_variants = {
        "home": ["home"],
        "draw": ["draw"],
        "away": ["away"],
        "btts_yes": ["btts_yes", "bttsYes"],
        "btts_no": ["btts_no", "bttsNo"],
        "dc_1x": ["dc_1x", "dc1x", "dc_1X", "dc1X"],
        "dc_x2": ["dc_x2", "dcX2", "dc_X2", "dcx2"],
        "dc_12": ["dc_12", "dc12", "dc_12"],
    }
    line_dict_field_map = [
        ("goalsOverOdds", "goals_over_odds"), ("goalsUnderOdds", "goals_under_odds"),
        ("cornersOverOdds", "corners_over_odds"), ("cornersUnderOdds", "corners_under_odds"),
        ("cardsOverOdds", "cards_over_odds"), ("cardsUnderOdds", "cards_under_odds"),
        ("shotsOverOdds", "shots_over_odds"), ("shotsUnderOdds", "shots_under_odds"),
        ("shotsTargetOverOdds", "shots_target_over_odds"), ("shotsTargetUnderOdds", "shots_target_under_odds")
    ]

    best: dict = {}
    bookmaker_map: dict = {}

    # Sort sources by key to ensure deterministic processing order
    for bookmaker_key, odds in sorted(sources.items(), key=lambda x: str(x[0])):
        if not isinstance(odds, dict):
            continue
        bk_label = odds.get("bookmaker") or bookmaker_key

        for dst_key, variants in simple_field_variants.items():
            val = None
            for v_key in variants:
                if v_key in odds and odds[v_key] is not None:
                    val = odds[v_key]
                    break
            if val is None:
                continue
            current = best.get(dst_key)
            if current is None or val > current:
                best[dst_key] = val
                bookmaker_map[dst_key] = bk_label

        for src_key, dst_key in line_dict_field_map:
            incoming = odds.get(src_key) or odds.get(dst_key) or {}
            if not incoming:
                continue
            best.setdefault(dst_key, {})
            bookmaker_map.setdefault(dst_key, {})
            for line_str, val in incoming.items():
                if val is None:
                    continue
                current = best[dst_key].get(line_str)
                if current is None or val > current:
                    best[dst_key][line_str] = val
                    bookmaker_map[dst_key][line_str] = bk_label

        # For lines lists, handle both snake_case and camelCase
        for snake_k, camel_k in [
            ("goals_lines", "goalsLines"),
            ("corners_lines", "cornersLines"),
            ("cards_lines", "cardsLines"),
            ("shots_lines", "shotsLines"),
            ("shots_target_lines", "shotsTargetLines")
        ]:
            incoming_lines = odds.get(snake_k) or odds.get(camel_k) or []
            if not incoming_lines:
                continue
            merged = set(best.get(snake_k, [])) | set(incoming_lines)
            best[snake_k] = sorted(merged)

    return {"odds_update": best, "bookmaker_map": bookmaker_map}

def _annotate_best_bookmaker(res: CompareResponse, bookmaker_map: dict, home_name: str, away_name: str) -> None:
    """
    Anota en cada ValueIndicator.bookmaker qué casa ofreció la mejor cuota
    para ese mercado, haciendo match por el texto exacto del `selection`
    que genera el motor de picks. Es puramente informativo: si no encuentra
    coincidencia para algún pick, simplemente deja `bookmaker=None` (nunca
    lanza error ni bloquea el análisis).
    """
    label_to_bookmaker: dict[str, str] = {}

    simple_labels = {
        "home": "Local",
        "draw": "Empate",
        "away": "Visitante",
        "btts_yes": "BTTS Sí",
        "btts_no": "BTTS No",
        "dc_1x": "Doble Oportunidad 1X",
        "dc_x2": "Doble Oportunidad X2",
        "dc_12": "Doble Oportunidad 12",
    }
    for field, label in simple_labels.items():
        bk = bookmaker_map.get(field)
        if isinstance(bk, str):
            label_to_bookmaker[label] = bk

    line_labels = [
        ("goals_over_odds", "Over {line} Goles"), ("goals_under_odds", "Under {line} Goles"),
        ("corners_over_odds", "Over {line} Corners"), ("corners_under_odds", "Under {line} Corners"),
        ("cards_over_odds", "Over {line} Tarjetas"), ("cards_under_odds", "Under {line} Tarjetas"),
        ("shots_over_odds", "Over {line} Tiros"), ("shots_under_odds", "Under {line} Tiros"),
        ("shots_target_over_odds", "Over {line} Tiros a Pta"), ("shots_target_under_odds", "Under {line} Tiros a Pta"),
    ]
    for field, template in line_labels:
        line_map = bookmaker_map.get(field) or {}
        if not isinstance(line_map, dict):
            continue
        for line_str, bk in line_map.items():
            try:
                line_fmt = f"{float(line_str):g}"
            except (TypeError, ValueError):
                line_fmt = line_str
            label_to_bookmaker[template.format(line=line_fmt)] = bk

    for v in res.values:
        bk = label_to_bookmaker.get(v.selection)
        if bk:
            v.bookmaker = bk

def _apply_line_shopping(request: FootballCompareRequest) -> tuple[FootballCompareRequest, dict]:
    """
    Si el payload trae odds.sources (cuotas crudas de varias casas), calcula
    la mejor cuota por mercado y devuelve una COPIA de `request` con esas
    cuotas ya fusionadas, junto con el mapa de qué casa dio cada mejor cuota
    (para anotar los picks después con _annotate_best_bookmaker).

    Si no hay sources (o ninguna covers ningún mercado), devuelve el request
    tal cual y un bookmaker_map vacío — no rompe el flujo normal.
    """
    if not request.odds.sources:
        return request, {}

    merged = _merge_best_odds(request.odds.sources)
    odds_update = merged["odds_update"]
    bookmaker_map = merged["bookmaker_map"]

    if not odds_update:
        return request, {}

    new_odds = request.odds.model_copy(update=odds_update)
    new_request = request.model_copy(update={"odds": new_odds})
    return new_request, bookmaker_map

@app.post("/api/v1/prefill/odds", tags=["Prefill"])
async def push_prefill_odds(payload: dict) -> dict:
    """
    Recibe cuotas de una o varias casas de apuestas para el mismo partido.
    Las cuotas se ACUMULAN por casa: un nuevo envío nunca borra las cuotas
    de una casa distinta ya guardadas, salvo que el partido haya cambiado.
    """
    global prefill_odds_store, prefill_odds_match

    if "odds_by_bookmaker" in payload and isinstance(payload["odds_by_bookmaker"], dict):
        raw_map = payload["odds_by_bookmaker"]
        incoming: dict[str, dict] = {}
        match_key = None

        for bookmaker_key, raw_odds in raw_map.items():
            normalized = _normalize_betano_odds(raw_odds)
            normalized["bookmaker"] = normalized.get("bookmaker") or bookmaker_key
            incoming[bookmaker_key] = normalized
            if match_key is None:
                match_key = (normalized.get("home_team"), normalized.get("away_team"))

        # Si el partido cambió, se reinicia el acumulador (no mezclar
        # cuotas de partidos distintos). Si es el mismo partido (o el
        # acumulador estaba vacío), se FUSIONA con lo que ya había.
        if prefill_odds_match is not None and prefill_odds_match != match_key:
            prefill_odds_store = {}

        prefill_odds_store.update(incoming)  # ← merge, ya no reemplaza todo
        prefill_odds_match = match_key

        return {
            "status": "ok",
            "message": (
                f"Cuotas recibidas de {len(incoming)} casa(s) "
                f"({', '.join(incoming.keys())}). "
                f"Total acumulado: {len(prefill_odds_store)} casa(s)."
            ),
            "bookmakers_received": list(incoming.keys()),
            "bookmakers_accumulated": list(prefill_odds_store.keys()),
        }

    # ── Legacy: una sola casa por llamada (ya fusionaba correctamente) ──
    raw_odds = payload.get("odds", payload)
    normalized = _normalize_betano_odds(raw_odds)
    bookmaker = normalized.get("bookmaker") or "unknown"

    match_key = (normalized.get("home_team"), normalized.get("away_team"))
    if prefill_odds_match is not None and prefill_odds_match != match_key:
        prefill_odds_store = {}

    prefill_odds_match = match_key
    prefill_odds_store[bookmaker] = normalized

    return {
        "status": "ok",
        "message": (
            f"Cuotas de {bookmaker} recibidas "
            f"({len(prefill_odds_store)} casa(s) acumulada(s))."
        ),
        "home_team": raw_odds.get("home_team"),
        "away_team": raw_odds.get("away_team"),
        "bookmakers_received": list(prefill_odds_store.keys()),
    }


@app.get("/api/v1/prefill", tags=["Prefill"])
async def consume_prefill() -> dict:
    global prefill_store, prefill_odds_store, prefill_odds_match

    try:
        if prefill_store is None and not prefill_odds_store:
            return {"pending": False}

        if prefill_store is not None:
            data = dict(prefill_store)
            prefill_store = None

            if prefill_odds_store:
                data["odds"] = {"sources": prefill_odds_store}
            prefill_odds_store = {}
            prefill_odds_match = None       

            return {"pending": True, "payload": data}

        sources = prefill_odds_store or {}
        data = {"odds": {"sources": sources}, "sport": "football"}

        any_entry = next(iter(sources.values()), {}) if sources else {}
        home_name = any_entry.get("home_team") if isinstance(any_entry, dict) else None
        away_name = any_entry.get("away_team") if isinstance(any_entry, dict) else None
        if home_name:
            data["home"] = {"name": home_name}
        if away_name:
            data["away"] = {"name": away_name}

        prefill_odds_store = {}
        prefill_odds_match = None
        return {"pending": True, "payload": data}

    except Exception as e:
        # NUNCA dejar que esto se propague como 500: eso mata el polling
        # del dashboard (ver bug de checkPrefill en el frontend).
        print(f"[Sherlock] Error en consume_prefill: {e}")
        # Limpiamos el estado para no quedar atascados repitiendo el error
        prefill_store = None
        prefill_odds_store = {}
        prefill_odds_match = None
        return {"pending": False}


@app.get("/api/v1/prefill/odds", tags=["Prefill"])
async def consume_prefill_odds() -> dict:
    """
    Devuelve el detalle crudo de cuotas por casa acumulado hasta ahora.
    Single-use: limpia el slot después de devolverlo.
    """
    global prefill_odds_store, prefill_odds_match
    if not prefill_odds_store:
        return {"pending": False}
    sources = prefill_odds_store
    prefill_odds_store = {}
    prefill_odds_match = None
    return {"pending": True, "odds": {"sources": sources}}


# ---------------------------------------------------------------------------
# Closing Odds endpoints — used by Watson extension & Sherlock to track CLV
# ---------------------------------------------------------------------------

def match_closing_odds_to_pick(pick: dict, normalized_odds: dict) -> float | None:
    """
    Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds)
    y un pick (con selection, market, line), encuentra la cuota de cierre correspondiente.
    """
    if not isinstance(pick, dict) or not isinstance(normalized_odds, dict):
        return None

    selection = str(pick.get("selection") or pick.get("pick") or "").strip().lower()
    market = str(pick.get("market") or "").strip().lower()
    line = pick.get("line")

    if line is None:
        import re
        m = re.search(r"(\d+(?:\.\d+)?)", selection)
        if m:
            try:
                line = float(m.group(1))
            except Exception:
                line = None

    line_str = str(line) if line is not None else ""
    if line_str.endswith(".0"):
        line_str = line_str[:-2]

    # 1. 1X2 / Match Winner
    if "1x2" in market or "resultado final" in market or "ganador" in market:
        if "local" in selection or "home" in selection or selection == "1":
            return float(normalized_odds.get("home")) if normalized_odds.get("home") else None
        elif "empate" in selection or "draw" in selection or selection == "x":
            return float(normalized_odds.get("draw")) if normalized_odds.get("draw") else None
        elif "visitante" in selection or "away" in selection or selection == "2":
            return float(normalized_odds.get("away")) if normalized_odds.get("away") else None

    # 2. Total Goles
    if "gol" in market:
        is_over = "más" in selection or "over" in selection or ">" in selection
        is_under = "menos" in selection or "under" in selection or "<" in selection
        if is_over:
            go = normalized_odds.get("goalsOverOdds", {})
            val = go.get(line_str) or go.get(str(line))
            return float(val) if val else None
        elif is_under:
            gu = normalized_odds.get("goalsUnderOdds", {})
            val = gu.get(line_str) or gu.get(str(line))
            return float(val) if val else None

    # 3. Córners
    if "córner" in market or "corner" in market:
        is_over = "más" in selection or "over" in selection or ">" in selection
        is_under = "menos" in selection or "under" in selection or "<" in selection
        if is_over:
            co = normalized_odds.get("cornersOverOdds", {})
            val = co.get(line_str) or co.get(str(line))
            return float(val) if val else None
        elif is_under:
            cu = normalized_odds.get("cornersUnderOdds", {})
            val = cu.get(line_str) or cu.get(str(line))
            return float(val) if val else None

    # 4. Tarjetas
    if "tarjeta" in market or "card" in market:
        is_over = "más" in selection or "over" in selection or ">" in selection
        is_under = "menos" in selection or "under" in selection or "<" in selection
        if is_over:
            cdo = normalized_odds.get("cardsOverOdds", {})
            val = cdo.get(line_str) or cdo.get(str(line))
            return float(val) if val else None
        elif is_under:
            cdu = normalized_odds.get("cardsUnderOdds", {})
            val = cdu.get(line_str) or cdu.get(str(line))
            return float(val) if val else None

    # 5. Remates
    if "remate" in market or "shot" in market:
        is_target = "puerta" in market or "target" in market
        is_over = "más" in selection or "over" in selection or ">" in selection
        is_under = "menos" in selection or "under" in selection or "<" in selection
        dict_over = normalized_odds.get("shotsTargetOverOdds", {}) if is_target else normalized_odds.get("shotsOverOdds", {})
        dict_under = normalized_odds.get("shotsTargetUnderOdds", {}) if is_target else normalized_odds.get("shotsUnderOdds", {})
        if is_over:
            val = dict_over.get(line_str) or dict_over.get(str(line))
            return float(val) if val else None
        elif is_under:
            val = dict_under.get(line_str) or dict_under.get(str(line))
            return float(val) if val else None

    # 6. BTTS / Ambos anotan
    if "ambos" in market or "btts" in market:
        if "sí" in selection or "yes" in selection or "si" in selection:
            return float(normalized_odds.get("btts_yes")) if normalized_odds.get("btts_yes") else None
        elif "no" in selection:
            return float(normalized_odds.get("btts_no")) if normalized_odds.get("btts_no") else None

    # 7. Doble Oportunidad
    if "doble" in market or "double" in market or "dc" in market:
        if "1x" in selection:
            return float(normalized_odds.get("dc_1x")) if normalized_odds.get("dc_1x") else None
        elif "x2" in selection:
            return float(normalized_odds.get("dc_x2")) if normalized_odds.get("dc_x2") else None
        elif "12" in selection:
            return float(normalized_odds.get("dc_12")) if normalized_odds.get("dc_12") else None

    return None


@app.get("/api/v1/closing-odds/pending-matches", tags=["Closing Odds"])
@app.get("/api/v1/prefill/pending-closing-matches", tags=["Closing Odds"])
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
            and_(AnalysisHistory.match_date.is_(None), AnalysisHistory.date >= min_date)
        )
    )
    matches = query.all()

    results = []
    for ah in matches:
        try:
            raw_picks = json.loads(ah.picks_calculados) if isinstance(ah.picks_calculados, str) else ah.picks_calculados
        except Exception:
            raw_picks = []

        if not isinstance(raw_picks, list) or len(raw_picks) == 0:
            continue

        has_all_closing = all(p.get("closing_odds") is not None for p in raw_picks if isinstance(p, dict))

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

        results.append({
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
                    "closing_odds": p.get("closing_odds")
                }
                for p in raw_picks if isinstance(p, dict)
            ]
        })

    return {"status": "ok", "pending_matches": results}


@app.post("/api/v1/closing-odds/submit", tags=["Closing Odds"])
@app.post("/api/v1/prefill/closing-odds", tags=["Closing Odds"])
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
        ah = db.query(AnalysisHistory).filter(
            AnalysisHistory.match_title.ilike(f"%{match_title}%"),
            AnalysisHistory.final_score_home.is_(None)
        ).first()

    if not ah:
        raise HTTPException(status_code=404, detail="Partido o análisis no encontrado en Sherlock.")

    if not ah.picks_calculados:
        raise HTTPException(status_code=400, detail="El partido no tiene picks calculados.")

    try:
        raw_picks = json.loads(ah.picks_calculados) if isinstance(ah.picks_calculados, str) else ah.picks_calculados
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parseando picks_calculados: {e}")

    if not isinstance(raw_picks, list):
        raise HTTPException(status_code=400, detail="Estructura de picks_calculados inválida.")

    raw_odds = payload.get("odds") or payload.get("odds_data") or payload
    if isinstance(raw_odds, dict) and ("goals_over" in raw_odds or "home" in raw_odds or "goalsOverOdds" in raw_odds):
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

        exp_odd = explicit_closing_map.get(str(idx)) or explicit_closing_map.get(pick.get("selection"))
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
        "updated_picks_count": updated_count
    }



# ---------------------------------------------------------------------------
# Results endpoint — used by browser extensions to push match results
# ---------------------------------------------------------------------------
_result_store: dict | None = None
_in_leagues_window: bool = False


@app.post("/api/v1/leagues/active-state", tags=["Leagues"])
def set_leagues_active_state(active: bool = Query(...)):
    global _in_leagues_window
    _in_leagues_window = active
    return {"status": "ok", "in_leagues_window": _in_leagues_window}


@app.post("/api/v1/result", tags=["Results"])
async def push_result(payload: dict, db: Session = Depends(get_db)) -> dict:
    """
    Browser extension pushes match results here (e.g. from flashscore).
    Tries to find matching AnalysisHistory record and auto-update it,
    and also buffers it in memory for the UI to consume.
    """
    global _result_store, _in_leagues_window
    is_historical = payload.get("season_year") is not None
    if not _in_leagues_window and not is_historical:
        return {"status": "ignored", "message": "Ignored because user is not in the leagues window."}
        
    _result_store = payload

    sport = payload.get("sport", "football")
    home_name = payload.get("home_team") or payload.get("home", {}).get("name")
    away_name = payload.get("away_team") or payload.get("away", {}).get("name")


    if home_name and away_name:
        try:
            sport_enum = Sport(sport)
            h_name_lower = home_name.lower()
            a_name_lower = away_name.lower()

            # ── ESTRATEGIA 1: Busqueda directa por event_id (la mas rapida) ──
            event_id = payload.get("event_id")
            matched = None
            if event_id:
                matched = (
                    db.query(AnalysisHistory)
                    .filter(
                        AnalysisHistory.sport == sport_enum,
                        AnalysisHistory.payload.contains(str(event_id))
                    )
                    .first()
                )


            if not matched:
               # ── ESTRATEGIA 2: Búsqueda por título exacto + fecha ──
                match_date_val = None
                if payload.get("start_timestamp"):
                    try:
                        match_date_val = datetime.utcfromtimestamp(payload["start_timestamp"])
                    except Exception:
                        pass
                if not match_date_val and payload.get("match_date"):
                    try:
                        match_date_val = datetime.fromisoformat(str(payload["match_date"]).replace("Z", "+00:00"))
                    except Exception:
                        pass
                if not match_date_val and payload.get("date"):
                    try:
                        match_date_val = datetime.fromisoformat(str(payload["date"]).replace("Z", "+00:00"))
                    except Exception:
                        pass

                # 2a. Intento exacto: título con orden correcto + fecha cercana (+/- 2 días)
                exact_title = f"{home_name} vs {away_name}"
                query = (
                    db.query(AnalysisHistory)
                    .filter(
                        AnalysisHistory.sport == sport_enum,
                        AnalysisHistory.match_title == exact_title,
                    )
                )
                if match_date_val:
                    from datetime import timedelta
                    query = query.filter(
                        or_(
                            and_(
                                AnalysisHistory.match_date.isnot(None),
                                AnalysisHistory.match_date >= match_date_val - timedelta(days=2),
                                AnalysisHistory.match_date <= match_date_val + timedelta(days=2),
                            ),
                            and_(
                                AnalysisHistory.match_date.is_(None),
                                AnalysisHistory.date >= match_date_val - timedelta(days=2),
                                AnalysisHistory.date <= match_date_val + timedelta(days=2),
                            )
                        )
                    )
                matched = query.order_by(AnalysisHistory.date.desc()).first()

                # 2b. Si no hay exacto, buscar candidatos con ambos nombres PERO
                #    filtrar estrictamente por fecha y respetar el orden (local primero, visitante segundo)
                if not matched:
                    candidates_query = (
                        db.query(AnalysisHistory)
                        .filter(
                            AnalysisHistory.sport == sport_enum,
                            AnalysisHistory.match_title.ilike(f"%{home_name}%"),
                            AnalysisHistory.match_title.ilike(f"%{away_name}%"),
                        )
                    )
                    if match_date_val:
                        from datetime import timedelta
                        candidates_query = candidates_query.filter(
                            or_(
                                and_(
                                    AnalysisHistory.match_date.isnot(None),
                                    AnalysisHistory.match_date >= match_date_val - timedelta(days=2),
                                    AnalysisHistory.match_date <= match_date_val + timedelta(days=2),
                                ),
                                and_(
                                    AnalysisHistory.match_date.is_(None),
                                    AnalysisHistory.date >= match_date_val - timedelta(days=2),
                                    AnalysisHistory.date <= match_date_val + timedelta(days=2),
                                )
                            )
                        )
                    candidates = candidates_query.order_by(AnalysisHistory.date.desc()).all()

                    for h in candidates:
                        title_lower = h.match_title.lower()
                        home_match = h_name_lower[:5] in title_lower or h_name_lower in title_lower
                        away_match = a_name_lower[:5] in title_lower or a_name_lower in title_lower
                        if not (home_match and away_match):
                            continue

                        # Diferenciación estricta por fecha: si el candidato es de otra fecha (+/- 2 días), omitir
                        rec_date = h.match_date or h.date
                        if match_date_val and rec_date:
                            if abs((rec_date - match_date_val).total_seconds()) > 2 * 86400:
                                continue

                        home_idx = title_lower.find(h_name_lower)
                        away_idx = title_lower.find(a_name_lower)
                        if home_idx != -1 and away_idx != -1 and home_idx < away_idx:
                            matched = h
                            break

                    if not matched and candidates:
                        cand = candidates[0]
                        rec_date = cand.match_date or cand.date
                        if not match_date_val or not rec_date or abs((rec_date - match_date_val).total_seconds()) <= 2 * 86400:
                            matched = cand

            # ── Si encontramos el partido, actualizamos ──
            if matched:
                h = matched
                
                # Update fields
                h.final_score_home = payload.get("final_score_home")
                h.final_score_away = payload.get("final_score_away")
                
                # Optional extra stats
                optional_fields = [
                    "final_corners_home", "final_corners_away",
                    "final_yellow_cards_home", "final_yellow_cards_away",
                    "final_red_cards_home", "final_red_cards_away",
                    "final_shots_home", "final_shots_away",
                    "final_shots_on_target_home", "final_shots_on_target_away",
                    "final_fouls_home", "final_fouls_away",
                    "final_offsides_home", "final_offsides_away"
                ]
                for field in optional_fields:
                    if field in payload:
                        setattr(h, field, payload.get(field))

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
                
                return {
                    "status": "ok",
                    "message": f"Resultado recibido y auto-asociado al partido en BD: '{h.match_title}'",
                    "auto_updated": True
                }

        except Exception as ex:
            print(f"Error auto-matching result payload: {ex}")

    # ── Si llegamos aca, NO se encontro en toda la BD: crear nuevo registro ──
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

        # ── Deduplicacion CORREGIDA: ahora SI usa event_id ──
        event_id_str = str(payload.get("event_id")) if payload.get("event_id") else None
        
        existing = None
        if event_id_str:
            # Buscar por event_id en el payload JSON o en el match_title exacto + fecha
            existing = db.query(AnalysisHistory).filter(
                AnalysisHistory.sport == sport_enum,
                AnalysisHistory.match_date == match_date_val,
                or_(
                    AnalysisHistory.payload.contains(event_id_str),
                    AnalysisHistory.match_title == match_title
                )
            ).first()
        else:
            # Sin event_id, buscar por titulo exacto + fecha
            existing = db.query(AnalysisHistory).filter(
                AnalysisHistory.sport == sport_enum,
                AnalysisHistory.match_title == match_title,
                AnalysisHistory.match_date == match_date_val,
            ).first()

        if existing:
            return {
                "status": "ok",
                "message": f"Evento ya existe — omitido",
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
            has_odds=_check_payload_has_odds(cleaned_payload),
            needs_recalc=True,
            has_real_stats=True,
            count_in_profitability=False,
            competition=_extract_competition(cleaned_payload),
            bookmaker=_extract_bookmaker(cleaned_payload),
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
        _invalidate_stats_cache()
        
        return {
            "status": "ok",
            "message": f"Resultado guardado como nuevo registro historico para {home_name} vs {away_name}.",
            "auto_updated": False,
            "created_new": True
        }
    except Exception as create_ex:
        print(f"Error creating historical record: {create_ex}")
        return {
            "status": "error",
            "message": f"Error al crear registro historico: {str(create_ex)}",
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
    before_date: str | None = Query(None, description="Cursor: traer partidos antes de esta fecha ISO"),
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
    if before_date:
        query = query.filter(Match.date < datetime.fromisoformat(before_date))

    if before_date:
        query = query.order_by(Match.date.desc()).limit(limit)
    else:
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

async def _enrich_with_results(
    sport: Sport,
    home: str,
    away: str,
    response: CompareResponse,
    db: Session,
    match_date: Optional[str] = None
):
    """Busca si el partido ya tiene resultados en la BD y marca acierto/fallo en el vuelo."""
    from datetime import datetime, timedelta

    # Resolver la fecha de comparación
    dt = None
    if match_date:
        try:
            if isinstance(match_date, str):
                if len(match_date) >= 10:
                    dt = datetime.strptime(match_date[:10], "%Y-%m-%d")
                else:
                    dt = datetime.fromisoformat(match_date)
            elif isinstance(match_date, datetime):
                dt = match_date
        except Exception:
            pass

    if not dt:
        # Fallback al día actual si no se proporciona o no se puede parsear
        dt = datetime.utcnow()

    date_start = dt - timedelta(days=1)
    date_end = dt + timedelta(days=1)

    # 1. Intento exacto: orden home vs away + fecha cercana (respetando match_date o date)
    history = (
        db.query(AnalysisHistory)
        .filter(
            AnalysisHistory.sport == sport,
            AnalysisHistory.match_title == f"{home} vs {away}",
            AnalysisHistory.final_score_home != None,
            (
                ((AnalysisHistory.match_date >= date_start) & (AnalysisHistory.match_date <= date_end)) |
                ((AnalysisHistory.match_date == None) & (AnalysisHistory.date >= date_start) & (AnalysisHistory.date <= date_end))
            )
        )
        .order_by(AnalysisHistory.date.desc())
        .first()
    )

    # 2. Si no hay exacto, buscar con ambos nombres pero respetando orden + fecha cercana
    if not history:
        candidates = (
            db.query(AnalysisHistory)
            .filter(
                AnalysisHistory.sport == sport,
                AnalysisHistory.match_title.ilike(f"%{home}%"),
                AnalysisHistory.match_title.ilike(f"%{away}%"),
                AnalysisHistory.final_score_home != None,
                (
                    ((AnalysisHistory.match_date >= date_start) & (AnalysisHistory.match_date <= date_end)) |
                    ((AnalysisHistory.match_date == None) & (AnalysisHistory.date >= date_start) & (AnalysisHistory.date <= date_end))
                )
            )
            .order_by(AnalysisHistory.date.desc())
            .all()
        )
        home_l = home.lower()
        away_l = away.lower()
        for h in candidates:
            title_lower = h.match_title.lower()
            h_idx = title_lower.find(home_l)
            a_idx = title_lower.find(away_l)
            if h_idx != -1 and a_idx != -1 and h_idx < a_idx:
                history = h
                break

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

    for v in response.values:
        v.success = _check_pick_success(
            v.model_dump() if hasattr(v, "model_dump") else v.__dict__, res_dict
        )

    return response

@app.post("/api/v1/compare/football", response_model=CompareResponse, tags=["Comparator"])
async def compare_teams_football(request: FootballCompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    """
    Analiza el partido y calcula TODOS los picks, aplicando line shopping
    automático si el payload trae cuotas de varias casas (odds.sources).
    """
    request, bookmaker_map = _apply_line_shopping(request)

    res = await compare_football(request, db=db)

    if bookmaker_map:
        _annotate_best_bookmaker(res, bookmaker_map, request.home.name, request.away.name)

    return await _enrich_with_results(Sport.FOOTBALL, request.home.name, request.away.name, res, db, match_date=request.match_date)


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

    if req.match_date is None:
        raise HTTPException(status_code=400, detail="Fecha del partido no detectada o inválida")

    # Check for existing record (Upsert logic)

    existing = None
    if req.id:
        existing = db.query(AnalysisHistory).filter(AnalysisHistory.id == req.id).first()

    if not existing:
        from datetime import timedelta, datetime
        
        query = db.query(AnalysisHistory).filter(
            AnalysisHistory.sport == sport_enum,
            AnalysisHistory.match_title == req.match_title,
        )
        
        if req.match_date:
            date_start = req.match_date - timedelta(days=1)
            date_end = req.match_date + timedelta(days=1)
            query = query.filter(
                or_(
                    and_(AnalysisHistory.match_date >= date_start, AnalysisHistory.match_date <= date_end),
                    and_(AnalysisHistory.match_date == None, AnalysisHistory.date >= date_start, AnalysisHistory.date <= date_end)
                )
            )
        else:
            # Si no viene fecha, asume que es un partido reciente (evita mezclar con temporadas anteriores)
            date_start = datetime.utcnow() - timedelta(days=3)
            query = query.filter(AnalysisHistory.date >= date_start)
            
        existing = query.order_by(AnalysisHistory.date.desc()).first()

    # ── Calcular parámetros previos, ventanas de forma reciente (5, 10, 15) y hit rates empíricos ──
    from datetime import datetime, timezone
    from src.core.math_engine import LeagueMathEngine
    from src.domain.temporal import TemporalCutoff

    # Antes: `req.match_date or datetime.now(timezone.utc)`. Sin fecha de
    # partido se usaba AHORA como cutoff, lo que admite en el historico todo lo
    # jugado hasta este instante -- incluidos partidos posteriores al saque
    # inicial real si el partido aun no se ha jugado. Ahora, sin fecha
    # utilizable no se calculan parametros retrospectivos: es mejor no tenerlos
    # que tenerlos contaminados.
    prior_cutoff = TemporalCutoff.create(req.match_date)
    record_date = prior_cutoff.kickoff if prior_cutoff else None
    pre_match_data = req.pre_match_stats
    recent_form_data = req.recent_form_stats
    pick_rates_data = req.historical_pick_rates

    try:
        if prior_cutoff is None:
            raise _SkipPriorParams(
                "sin fecha de partido utilizable: no se calculan parametros retrospectivos"
            )

        title = req.match_title or ""
        h_name = title.split(" vs ")[0].strip() if " vs " in title else ""
        a_name = title.split(" vs ")[1].strip() if " vs " in title else ""
        comp_name = req.payload.get("competition") if isinstance(req.payload, dict) else ""

        # Sin competicion objetivo no se puede acotar la muestra a una liga, y
        # mezclar ligas hace que un hit rate no signifique nada. Antes
        # `if not target_comp` dejaba pasar TODAS las competiciones.
        if not (comp_name or "").strip():
            raise _SkipPriorParams(
                "sin competicion objetivo: el historico mezclaria ligas distintas"
            )

        # Obtener partidos históricos jugados antes de este partido
        q_prior = db.query(AnalysisHistory).filter(
            AnalysisHistory.final_score_home.isnot(None),
            AnalysisHistory.final_score_away.isnot(None)
        )
        # `record_date` esta garantizado a estas alturas. Se exige match_date NO
        # nula: el fallback anterior a `AnalysisHistory.date` usaba la fecha de
        # CREACION del registro como si fuese la del partido, y un analisis
        # creado antes del kickoff puede corresponder a un partido posterior.
        q_prior = q_prior.filter(
            AnalysisHistory.id != req.id,  # Excluir el mismo registro explícitamente
            AnalysisHistory.match_date.isnot(None),
            AnalysisHistory.match_date < record_date,
        )
        prior_rows = q_prior.order_by(AnalysisHistory.date.desc()).all()
        prior_records = []
        target_comp = (comp_name or "").strip().lower()
        for r in prior_rows:
            r_payload = {}
            if r.payload:
                try:
                    r_payload = json.loads(r.payload) if isinstance(r.payload, str) else r.payload
                except Exception:
                    pass
            comp_cand = f"{r_payload.get('competition', '')} {r_payload.get('league', '')} {r.match_title}".lower()
            # Segundo cinturon: el cutoff del dominio se reaplica en memoria. La
            # comparacion en SQLite es lexicografica sobre texto y no entiende
            # zonas horarias, asi que no basta por si sola.
            if not prior_cutoff.allows(r.match_date or r.date):
                continue
            if target_comp and target_comp in comp_cand:
                prior_records.append({
                    "match_title": r.match_title,
                    "match_date": r.match_date or r.date,
                    "final_score_home": r.final_score_home,
                    "final_score_away": r.final_score_away,
                    "final_corners_home": r.final_corners_home,
                    "final_corners_away": r.final_corners_away,
                    "final_yellow_cards_home": r.final_yellow_cards_home,
                    "final_yellow_cards_away": r.final_yellow_cards_away,
                    "final_shots_home": r.final_shots_home,
                    "final_shots_away": r.final_shots_away,
                })

        if prior_records:
            if not pre_match_data:
                avg_engine = LeagueMathEngine.compute_league_averages(prior_records)
                pre_match_data = {"league_averages": avg_engine, "sample_size": len(prior_records)}

            if not recent_form_data:
                recent_form_data = {
                    "home": LeagueMathEngine.compute_recent_form_windows(prior_records, h_name, windows=[5, 10, 15]),
                    "away": LeagueMathEngine.compute_recent_form_windows(prior_records, a_name, windows=[5, 10, 15])
                }

            if not pick_rates_data:
                league_prior_over25 = LeagueMathEngine.compute_league_pick_hit_rate(
                    prior_records, "goals", 2.5, is_over=True, current_match_date=record_date
                )
                pick_rates_data = {
                    "home_over25_home": LeagueMathEngine.compute_pick_hit_rate_recency(
                        prior_records, h_name, "goals", 2.5, is_over=True,
                        role_filter="home", current_match_date=record_date,
                        prior_rate=league_prior_over25,
                    ),
                    "away_over25_away": LeagueMathEngine.compute_pick_hit_rate_recency(
                        prior_records, a_name, "goals", 2.5, is_over=True,
                        role_filter="away", current_match_date=record_date,
                        prior_rate=league_prior_over25,
                    ),
                }
    except _SkipPriorParams as skip:
        print(f"Parámetros previos omitidos por seguridad temporal: {skip}")
    except Exception as err_p:
        print(f"Error calculando parámetros previos al guardar análisis: {err_p}")

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
            existing.llm_response = req.llm_response
            existing.llm_timestamp = req.llm_timestamp or datetime.now(timezone.utc)
        if req.needs_reanalysis is not None:
            # pyrefly: ignore [bad-assignment]
            existing.needs_reanalysis = req.needs_reanalysis
        if req.compare_response_snapshot is not None:
            # pyrefly: ignore [bad-assignment]
            existing.compare_response_snapshot = json.dumps(req.compare_response_snapshot)
        comp_name = _extract_competition(req.payload)
        has_real_stats_val = req.has_real_stats if req.has_real_stats is not None else True
        if req.count_in_profitability is not None:
            existing.count_in_profitability = req.count_in_profitability
        elif comp_name:
            existing.count_in_profitability = is_league_profitable(comp_name)
        elif not has_real_stats_val:
            existing.count_in_profitability = False

        if req.has_real_stats is not None:
            # pyrefly: ignore [bad-assignment]
            existing.has_real_stats = req.has_real_stats

        if pre_match_data is not None:
            existing.pre_match_stats = json.dumps(pre_match_data) if not isinstance(pre_match_data, str) else pre_match_data
        if recent_form_data is not None:
            existing.recent_form_stats = json.dumps(recent_form_data) if not isinstance(recent_form_data, str) else recent_form_data
        if pick_rates_data is not None:
            existing.historical_pick_rates = json.dumps(pick_rates_data) if not isinstance(pick_rates_data, str) else pick_rates_data

        # ── Populate denormalized columns ──
        existing.competition = _extract_competition(req.payload)
        existing.bookmaker = _extract_bookmaker(req.payload)
        if req.picks_calculados is not None:
            existing.stake_units = _sum_stake_from_picks(req.picks_calculados)

        db.commit()
        _invalidate_stats_cache()
        db.refresh(existing)
        out = AnalysisHistoryOut.model_validate(existing)
        return _populate_history_extra_fields(existing, out)

    # Create new record
    comp_name = _extract_competition(req.payload)
    has_real_stats_val = req.has_real_stats if req.has_real_stats is not None else True
    if req.count_in_profitability is not None:
        count_in_prof_val = req.count_in_profitability
    elif comp_name:
        count_in_prof_val = is_league_profitable(comp_name)
    else:
        count_in_prof_val = False if not has_real_stats_val else True

    _picks_json = json.dumps(req.picks_calculados) if req.picks_calculados else None
    history = AnalysisHistory(
        sport=sport_enum,
        match_title=req.match_title,
        payload=json.dumps(req.payload),
        date=record_date,
        match_date=record_date,
        picks_calculados=_picks_json,
        user_context=req.user_context,
        llm_response=req.llm_response,
        llm_timestamp=req.llm_timestamp or (datetime.now(timezone.utc) if req.llm_response else None),
        needs_reanalysis=req.needs_reanalysis or False,
        compare_response_snapshot=json.dumps(req.compare_response_snapshot) if req.compare_response_snapshot else None,
        count_in_profitability=count_in_prof_val,
        has_real_stats=has_real_stats_val,
        pre_match_stats=json.dumps(pre_match_data) if pre_match_data and not isinstance(pre_match_data, str) else (pre_match_data if isinstance(pre_match_data, str) else None),
        recent_form_stats=json.dumps(recent_form_data) if recent_form_data and not isinstance(recent_form_data, str) else (recent_form_data if isinstance(recent_form_data, str) else None),
        historical_pick_rates=json.dumps(pick_rates_data) if pick_rates_data and not isinstance(pick_rates_data, str) else (pick_rates_data if isinstance(pick_rates_data, str) else None),
        # ── Denormalized columns ──
        competition=_extract_competition(req.payload),
        bookmaker=_extract_bookmaker(req.payload),
        stake_units=_sum_stake_from_picks(_picks_json),
    )
    db.add(history)
    db.commit()
    _invalidate_stats_cache()
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

    from datetime import timedelta, datetime

    # Intentar extraer match_date del payload para buscar coincidencias
    match_date_str = payload.get("match_date")
    
    query = db.query(AnalysisHistory).filter(
        AnalysisHistory.sport == sport_enum,
        AnalysisHistory.match_title == match_title
    )

    if match_date_str:
        try:
            # Parsear la fecha del payload
            if 'T' in match_date_str:
                dt = datetime.fromisoformat(match_date_str)
            else:
                dt = datetime.strptime(match_date_str[:10], "%Y-%m-%d")
                
            date_start = dt - timedelta(days=1)
            date_end = dt + timedelta(days=1)
            query = query.filter(
                or_(
                    and_(AnalysisHistory.match_date >= date_start, AnalysisHistory.match_date <= date_end),
                    and_(AnalysisHistory.match_date == None, AnalysisHistory.date >= date_start, AnalysisHistory.date <= date_end)
                )
            )
        except Exception:
            pass
    else:
        # Si no hay fecha en el payload, limitar a los últimos días
        date_start = datetime.utcnow() - timedelta(days=3)
        query = query.filter(AnalysisHistory.date >= date_start)

    existing = query.order_by(AnalysisHistory.date.desc()).first()

    record_date = datetime.utcnow()

    if existing:
        existing.payload = json.dumps(cleaned_payload)
        existing.has_real_stats = False
        existing.count_in_profitability = False
        existing.competition = competition  # already extracted above
        existing.bookmaker = _extract_bookmaker(cleaned_payload)
        db.commit()
        _invalidate_stats_cache()
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
        count_in_profitability=False,
        competition=competition,
        bookmaker=_extract_bookmaker(cleaned_payload),
    )
    db.add(history)
    db.commit()
    _invalidate_stats_cache()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)

@app.delete("/api/v1/analysis/competition/{competition_name}", tags=["Analysis History"])
def delete_competition_matches(competition_name: str, db: Session = Depends(get_db)):
    """
    Borra todos los partidos (AnalysisHistory) que pertenezcan a una competición específica.
    """
    history_list = db.query(AnalysisHistory).all()
    deleted_count = 0
    
    for h in history_list:
        cname = h.competition
        if not cname and h.payload:
            try:
                pdata = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                cname = pdata.get("competition") or pdata.get("tournament", {}).get("name")
            except Exception:
                pass
        cname = cname or "Desconocida"
        
        if cname.lower() == competition_name.lower():
            db.delete(h)
            deleted_count += 1
                
    if deleted_count > 0:
        db.commit()
        _invalidate_stats_cache()
        
    return {
        "status": "ok", 
        "deleted_count": deleted_count, 
        "message": f"Se borraron {deleted_count} partidos de la competición '{competition_name}'."
    }

class RenameCompetitionRequest(BaseModel):
    new_name: str

@app.put("/api/v1/analysis/competition/{old_name}", tags=["Analysis History"])
def rename_competition_matches(old_name: str, new_name: str, db: Session = Depends(get_db)):
    """
    Cambia el nombre de una competición en el payload y en la columna desnormalizada 'competition' de todos los partidos asociados.
    """
    history_list = db.query(AnalysisHistory).all()
    updated_count = 0
    
    for h in history_list:
        cname = h.competition
        if not cname and h.payload:
            try:
                pdata = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                cname = pdata.get("competition") or pdata.get("tournament", {}).get("name")
            except Exception:
                pass
        cname = cname or "Desconocida"
        
        if cname.lower() == old_name.lower():
            h.competition = new_name
            if h.payload:
                try:
                    pdata = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                    pdata["competition"] = new_name
                    if "tournament" in pdata and isinstance(pdata["tournament"], dict):
                        pdata["tournament"]["name"] = new_name
                    h.payload = json.dumps(pdata)
                except Exception as e:
                    print(f"Error actualizando el payload de la competición (ID: {h.id}): {e}")
            updated_count += 1
                
    if updated_count > 0:
        db.commit()
        _invalidate_stats_cache()
        
    return {
        "status": "ok", 
        "updated_count": updated_count, 
        "message": f"Se actualizó la competición de '{old_name}' a '{new_name}' en {updated_count} partidos."
    }

@app.put("/api/v1/analysis/team/{old_name}", tags=["Analysis History"])
def rename_team_matches(
    old_name: str, 
    new_name: str, 
    competition: str = Query(None, description="Opcional. Renombra el equipo solo en esta competición."),
    db: Session = Depends(get_db)
):
    """
    Cambia el nombre de un equipo en el payload JSON y en el matchtitle
    de todos los partidos históricos asociados. Opcionalmente filtrado por liga.
    """
    # Filtrar solo los partidos cuyo título contenga el nombre antiguo
    history_list = db.query(AnalysisHistory).filter(AnalysisHistory.match_title.ilike(f"%{old_name}%")).all()
    updated_count = 0
    
    for h in history_list:
        if h.payload:
            try:
                # Decodificar el payload
                pdata = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                
                # Si se especificó competición, validar que coincida antes de modificar
                if competition:
                    cname = h.competition or pdata.get("competition") or pdata.get("tournament", {}).get("name") or "Desconocida"
                    if cname.lower() != competition.lower():
                        continue # Si no es de esta liga, saltar
                
                changed = False
                
                # 1. Actualizar dentro de los objetos 'home' y 'away'
                if isinstance(pdata.get("home"), dict) and pdata["home"].get("name", "").lower() == old_name.lower():
                    pdata["home"]["name"] = new_name
                    changed = True
                    
                if isinstance(pdata.get("away"), dict) and pdata["away"].get("name", "").lower() == old_name.lower():
                    pdata["away"]["name"] = new_name
                    changed = True
                    
                # 2. Actualizar en los campos directos 'hometeam' y 'awayteam'
                if str(pdata.get("hometeam", "")).lower() == old_name.lower():
                    pdata["hometeam"] = new_name
                    changed = True
                    
                if str(pdata.get("awayteam", "")).lower() == old_name.lower():
                    pdata["awayteam"] = new_name
                    changed = True
                    
                # 3. Guardar cambios en el JSON y actualizar el título (matchtitle)
                if changed:
                    h.payload = json.dumps(pdata)
                    
                    if h.match_title:
                        if " vs " in h.match_title:
                            parts = [p.strip() for p in h.match_title.split(" vs ")]
                            new_parts = [new_name if p.lower() == old_name.lower() else p for p in parts]
                            if len(new_parts) == 2:
                                h.match_title = f"{new_parts[0]} vs {new_parts[1]}"
                                
                        elif " - " in h.match_title:
                            parts = [p.strip() for p in h.match_title.split(" - ")]
                            new_parts = [new_name if p.lower() == old_name.lower() else p for p in parts]
                            if len(new_parts) == 2:
                                h.match_title = f"{new_parts[0]} - {new_parts[1]}"
                                
                    updated_count += 1
            except Exception as e:
                print(f"Error actualizando el nombre del equipo (ID: {h.id}): {e}")
                continue
                
    if updated_count > 0:
        db.commit()
        _invalidate_stats_cache()
        
    response_msg = f"Se actualizó el equipo de '{old_name}' a '{new_name}' en {updated_count} partidos"
    if competition:
        response_msg += f" de la competición '{competition}'."
    else:
        response_msg += " (Globalmente)."
        
    return {
        "status": "ok", 
        "updated_count": updated_count, 
        "message": response_msg
    }

@app.delete("/api/v1/analysis/competition/{competition_name}/deduplicate", tags=["Analysis History"])
def deduplicate_competition_matches(competition_name: str, db: Session = Depends(get_db)):
    """
    Busca partidos duplicados en una competición (mismo equipo local y visitante en la misma fecha).
    Elimina los duplicados que NO tengan cuotas ('odds' vacío o inexistente en el payload).
    """
    history_list = db.query(AnalysisHistory).all()
    
    # Agrupar partidos por liga, luego por título y fecha (ignorando horas)
    matches_by_key = {}
    
    for h in history_list:
        cname = h.competition
        if not cname and h.payload:
            try:
                pdata = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                cname = pdata.get("competition") or pdata.get("tournament", {}).get("name")
            except Exception:
                pass
        cname = cname or "Desconocida"
            
        if cname.lower() == competition_name.lower():
            # Crear una llave única basada en el título y la fecha (YYYY-MM-DD)
            match_date_str = h.match_date.strftime("%Y-%m-%d") if h.match_date else h.date.strftime("%Y-%m-%d")
            match_key = f"{h.match_title.lower().strip()}_{match_date_str}"
            
            if match_key not in matches_by_key:
                matches_by_key[match_key] = []
                
            matches_by_key[match_key].append(h)

    deleted_count = 0
    
    # Evaluar duplicados
    for key, matches in matches_by_key.items():
        if len(matches) > 1:
            # Hay duplicados. Determinar cuáles tienen cuotas.
            matches_with_odds = []
            matches_without_odds = []
            
            for m in matches:
                pdata = json.loads(m.payload) if isinstance(m.payload, str) else (m.payload or {})
                if not isinstance(pdata, dict):
                    pdata = {}

                # Verificar si tiene cuotas reales guardadas en odds o en fuentes (sources)
                odds_data = pdata.get("odds") if isinstance(pdata, dict) else {}
                has_odds_in_payload = bool(
                    isinstance(odds_data, dict) and 
                    (odds_data.get("home") is not None or odds_data.get("away") is not None or odds_data.get("draw") is not None)
                )
                
                sources_data = pdata.get("sources") if isinstance(pdata, dict) else None
                has_sources_odds = False
                if sources_data:
                    if isinstance(sources_data, dict):
                        for src_k, src_v in sources_data.items():
                            if isinstance(src_v, dict) and src_v.get("odds"):
                                src_odds = src_v.get("odds")
                                if isinstance(src_odds, dict) and (src_odds.get("home") is not None or src_odds.get("away") is not None or src_odds.get("draw") is not None):
                                    has_sources_odds = True
                                    break
                    elif isinstance(sources_data, list):
                        for src_item in sources_data:
                            if isinstance(src_item, dict) and src_item.get("odds"):
                                src_odds = src_item.get("odds")
                                if isinstance(src_odds, dict) and (src_odds.get("home") is not None or src_odds.get("away") is not None or src_odds.get("draw") is not None):
                                    has_sources_odds = True
                                    break

                has_odds = has_odds_in_payload or has_sources_odds

                if has_odds:
                    matches_with_odds.append(m)
                else:
                    matches_without_odds.append(m)
            
            # Si hay al menos un partido válido con cuotas, borramos TODOS los que no tienen
            if matches_with_odds:
                for m_del in matches_without_odds:
                    db.delete(m_del)
                    deleted_count += 1
                
                # Si aún así hay duplicados CON cuotas (raro), dejamos el más reciente
                if len(matches_with_odds) > 1:
                    matches_with_odds.sort(key=lambda x: x.date, reverse=True)
                    for m_del in matches_with_odds[1:]:
                        db.delete(m_del)
                        deleted_count += 1
            else:
                # Si ninguno tiene cuotas, igual borramos los duplicados y dejamos solo el más reciente
                matches_without_odds.sort(key=lambda x: x.date, reverse=True)
                for m_del in matches_without_odds[1:]:
                    db.delete(m_del)
                    deleted_count += 1

    if deleted_count > 0:
        db.commit()
        _invalidate_stats_cache()

    return {
        "status": "ok", 
        "deleted_count": deleted_count, 
        "message": f"Se eliminaron {deleted_count} registros duplicados (sin cuotas) en la competición '{competition_name}'."
    }

@app.get("/api/v1/analysis/teams/count", tags=["Analysis History"])
def list_teams_count(competition: str = Query(None, description="Filtra el conteo de equipos por una liga específica"), db: Session = Depends(get_db)):
    """
    Devuelve la lista de todos los equipos en la base de datos (o filtrados por liga) 
    y en cuántos partidos han participado.
    """
    cache_key = f"teams_count:{competition or 'all'}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    from sqlalchemy.orm import load_only
    query = db.query(AnalysisHistory).options(
        load_only(AnalysisHistory.match_title, AnalysisHistory.competition)
    )

    if competition:
        query = query.filter(AnalysisHistory.competition == competition)

    history_list = query.all()
    team_counts = {}
    
    for h in history_list:
        if not h.match_title:
            continue
            
        # Extraer equipos del match_title ("Local vs Visitante" o "Local - Visitante")
        teams = []
        if " vs " in h.match_title:
            teams = [t.strip() for t in h.match_title.split(" vs ")]
        elif " - " in h.match_title:
            teams = [t.strip() for t in h.match_title.split(" - ")]
            
        for team in teams:
            if team:
                # Normalizamos usando title() para evitar que "Bremen" y "bremen" se cuenten separados
                team_name = team.title() 
                if team_name in team_counts:
                    team_counts[team_name] += 1
                else:
                    team_counts[team_name] = 1

    # Ordenar el diccionario por cantidad de partidos (de mayor a menor)
    sorted_teams = dict(sorted(team_counts.items(), key=lambda item: item[1], reverse=True))
    
    response_msg = f"Se encontraron {len(sorted_teams)} equipos únicos"
    if competition:
        response_msg += f" en la competición '{competition}'"
        
    res = {
        "status": "ok",
        "message": response_msg,
        "total_unique_teams": len(sorted_teams),
        "teams": sorted_teams
    }
    _set_cache(cache_key, res)
    return res

@app.delete(
    "/api/v1/analysis/competition/{competition_name}/incomplete",
    tags=["Analysis History"],
)
def delete_incomplete_competition_matches(
    competition_name: str,
    dry_run: bool = Query(
        True,
        description="Si es true, solo informa qué eliminaría; no borra nada."
    ),
    db: Session = Depends(get_db),
):
    """
    Elimina partidos de una competición que no tengan cuotas válidas
    O que no tengan picks calculados.

    Se conserva un partido solo si:
    - Tiene odds válidas.
    - Tiene una lista no vacía en pickscalculados.
    """

    def get_competition_name(history: AnalysisHistory, payload: dict) -> str:
        if history.competition:
            return history.competition
        tournament = payload.get("tournament")
        tournament_name = (
            tournament.get("name")
            if isinstance(tournament, dict)
            else None
        )
        return (
            payload.get("competition")
            or payload.get("tournamentname")
            or tournament_name
            or "Desconocida"
        )

    def has_valid_odds(payload: dict) -> bool:
        """
        Considera válidas las cuotas si hay un objeto odds no vacío con,
        al menos, una cuota numérica mayor a 1.0, o fuentes por bookmaker.
        """
        odds = payload.get("odds")

        if not isinstance(odds, dict) or not odds:
            return False

        # Caso line-shopping: odds.sources = {betano: {...}, betplay: {...}}
        sources = odds.get("sources")
        if isinstance(sources, dict) and any(
            isinstance(source, dict) and source
            for source in sources.values()
        ):
            return True

        # Cuotas simples: home/draw/away, BTTS, líneas over/under, etc.
        for value in odds.values():
            if isinstance(value, (int, float)) and value > 1.0:
                return True

            if isinstance(value, dict):
                for nested_value in value.values():
                    try:
                        if float(nested_value) > 1.0:
                            return True
                    except (TypeError, ValueError):
                        pass

        return False

    def has_calculated_picks(raw_picks) -> bool:
        """Valida que pickscalculados contenga una lista no vacía."""
        if raw_picks is None:
            return False

        if isinstance(raw_picks, str):
            if not raw_picks.strip():
                return False

            try:
                picks = json.loads(raw_picks)
            except (json.JSONDecodeError, TypeError):
                return False
        else:
            picks = raw_picks

        return isinstance(picks, list) and len(picks) > 0

    history_list = db.query(AnalysisHistory).all()

    found_in_competition = 0
    deleted_count = 0
    no_odds_count = 0
    no_picks_count = 0
    no_odds_and_no_picks_count = 0
    candidates = []

    for history in history_list:
        if not history.payload:
            continue

        try:
            payload = (
                json.loads(history.payload)
                if isinstance(history.payload, str)
                else history.payload
            )

            if not isinstance(payload, dict):
                continue

            stored_competition = get_competition_name(history, payload)

            if stored_competition.casefold() != competition_name.casefold():
                continue

            found_in_competition += 1

            valid_odds = has_valid_odds(payload)
            valid_picks = has_calculated_picks(history.picks_calculados)

            # Borra si falta UNO de los dos requisitos.
            if valid_odds and valid_picks:
                continue

            if not valid_odds:
                no_odds_count += 1

            if not valid_picks:
                no_picks_count += 1

            if not valid_odds and not valid_picks:
                no_odds_and_no_picks_count += 1

            candidates.append({
                "id": str(history.id),
                "matchtitle": history.match_title,
                "matchdate": (
                    history.match_date.isoformat()
                    if history.match_date else None
                ),
                "has_valid_odds": valid_odds,
                "has_calculated_picks": valid_picks,
            })

            if not dry_run:
                db.delete(history)
                deleted_count += 1

        except Exception as exc:
            print(
                f"Error revisando partido incompleto "
                f"(ID: {history.id}): {exc}"
            )

    if not dry_run and deleted_count > 0:
        db.commit()
        _invalidate_stats_cache()

    return {
        "status": "ok",
        "dry_run": dry_run,
        "competition": competition_name,
        "total_matches_in_competition": found_in_competition,
        "matches_to_delete": len(candidates),
        "deleted_count": deleted_count,
        "without_valid_odds": no_odds_count,
        "without_calculated_picks": no_picks_count,
        "without_odds_and_picks": no_odds_and_no_picks_count,
        "candidates": candidates,
        "message": (
            f"Simulación: se eliminarían {len(candidates)} partidos "
            f"incompletos de '{competition_name}'."
            if dry_run
            else f"Se eliminaron {deleted_count} partidos incompletos "
                 f"de '{competition_name}'."
        ),
    }

@app.get("/api/v1/analysis", response_model=list[AnalysisHistoryOut], tags=["Analysis History"])
def list_analysis(
    sport: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    match_date_from: str | None = Query(None),
    match_date_to: str | None = Query(None),
    competition: str | None = Query(None),
    has_odds: bool | None = Query(None),  # Filtro para optimizar la carga en mercados
    limit: int = Query(5000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    use_stake: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[AnalysisHistoryOut]:
    """List saved analyses with optional filters and pagination."""
    query = db.query(AnalysisHistory).filter(AnalysisHistory.picks_calculados != None)
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

    # Competition filter via indexed column (with fallback for legacy records)
    if competition:
        comp_str = competition.strip()
        from sqlalchemy import or_, and_
        query = query.filter(
            or_(
                AnalysisHistory.competition == comp_str,
                and_(
                    or_(AnalysisHistory.competition == None, AnalysisHistory.competition == ""),
                    AnalysisHistory.payload.like(f'%"{comp_str}"%')
                )
            )
        )

    if has_odds is not None:
        query = query.filter(AnalysisHistory.has_odds == has_odds)

    from sqlalchemy.orm import load_only
    query = query.options(
        load_only(
            AnalysisHistory.id,
            AnalysisHistory.sport,
            AnalysisHistory.date,
            AnalysisHistory.match_date,
            AnalysisHistory.match_title,
            AnalysisHistory.competition,
            AnalysisHistory.payload,
            AnalysisHistory.picks_calculados,
            AnalysisHistory.count_in_profitability,
            AnalysisHistory.has_real_stats,
            AnalysisHistory.final_score_home,
            AnalysisHistory.final_score_away,
        )
    )

    query = query.order_by(AnalysisHistory.date.desc())
    history_list = query.offset(offset).limit(limit).all()
    
    results = []
    for h in history_list:
        out = AnalysisHistoryOut.model_validate(h)
        results.append(_populate_history_extra_fields(h, out, use_stake=use_stake))
    return results


@app.get("/api/v1/analysis/{analysis_id}", response_model=AnalysisHistoryOut, tags=["Analysis History"])
def get_analysis_by_id(
    analysis_id: str,
    use_stake: bool = Query(False),
    db: Session = Depends(get_db),
) -> AnalysisHistoryOut:
    """
    Obtiene toda la información necesaria para un partido en específico por su ID.
    """
    history = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Analysis not found")
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out, use_stake=use_stake)


@app.get("/api/v1/stats/leagues", tags=["Stats"])
def get_leagues_stats(
    use_stake: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Groups AnalysisHistory by competition inside the JSON payload and calculates stats.
    Also computes per-market hit rates and historical performance data for LRS computation.
    """
    cache_key = f"leagues:{use_stake}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    from sqlalchemy.orm import load_only
    history = (
        db.query(AnalysisHistory)
        # .filter(AnalysisHistory.picks_calculados != None)
        .options(load_only(
            AnalysisHistory.id,
            AnalysisHistory.competition,
            AnalysisHistory.payload,
            AnalysisHistory.match_date,
            AnalysisHistory.date,
            AnalysisHistory.picks_calculados,
            AnalysisHistory.final_score_home,
            AnalysisHistory.final_score_away,
            AnalysisHistory.final_corners_home,
            AnalysisHistory.final_corners_away,
            AnalysisHistory.final_yellow_cards_home,
            AnalysisHistory.final_yellow_cards_away,
            AnalysisHistory.final_red_cards_home,
            AnalysisHistory.final_red_cards_away,
            AnalysisHistory.final_shots_home,
            AnalysisHistory.final_shots_away,
            AnalysisHistory.final_shots_on_target_home,
            AnalysisHistory.final_shots_on_target_away,
            AnalysisHistory.final_fouls_home,
            AnalysisHistory.final_fouls_away,
            AnalysisHistory.final_offsides_home,
            AnalysisHistory.final_offsides_away,
        ))
        .all()
    )
    leagues_data = {}
    
    for h in history:
        # Resolve competition name using index column first
        comp_name = h.competition
        p_data = None
        if getattr(h, "payload", None):
            try:
                p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
            except:
                pass

        if not comp_name and p_data and isinstance(p_data, dict):
            comp_name = p_data.get("competition") or "Desconocida"

        if not comp_name:
            comp_name = "Desconocida"
                
        if comp_name not in leagues_data:
            leagues_data[comp_name] = {
                "name": comp_name,
                "is_profitable": is_league_profitable(comp_name),
                "total_matches": 0,
                "total_picks": 0,
                "total_hits": 0,
                "accuracy": 0.0,
                "total_profit": 0.0,
                "total_staked": 0.0,
                "roi": 0.0,
                "has_pending_matches": False,
                "odds_sum": 0.0,
                "odds_count": 0,
                # Per-market tracking: {family: {"hits": 0, "total": 0}}
                "_market_stats": {},
                "_detailed_markets": {},
                "_seasons": set(),
            }
            
        leagues_data[comp_name]["total_matches"] += 1
        
        # Extract season year for season filter
        s_year = None
        if p_data and isinstance(p_data, dict):
            s_year = p_data.get("season_year") or p_data.get("season")
        if not s_year:
            m_dt = getattr(h, "match_date", None) or getattr(h, "date", None)
            if m_dt:
                try:
                    s_year = m_dt.year
                except:
                    pass
        if s_year:
            leagues_data[comp_name]["_seasons"].add(str(s_year))
        
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
                        if pick.get("is_blacklisted") or pick.get("is_rule_blocked"):
                            continue
                        is_pub = pick.get("is_publishable", False)
                        is_und = pick.get("is_underdog", False)
                        
                        if not is_pub and not is_und:
                            if pick.get("is_value", False):
                                is_pub = True
                                
                        if not (is_pub or is_und):
                            continue
                        
                        # If resolving success
                        if has_result:
                            success = _check_pick_success(pick, res_dict)
                            if success is not None:
                                if use_stake:
                                    stake = _resolve_stake_from_pick(pick)
                                else:
                                    stake = MIN_STAKE
                                pick_profit = _calculate_pick_profit(success, pick.get("odds", 0.0)) * stake
                                leagues_data[comp_name]["total_profit"] += pick_profit
                                if success != "void":
                                    leagues_data[comp_name]["total_picks"] += 1
                                    leagues_data[comp_name]["total_staked"] += stake
                                    odds_val = float(pick.get("odds", 0.0) or 0.0)
                                    if odds_val > 0:
                                        leagues_data[comp_name]["odds_sum"] += odds_val
                                        leagues_data[comp_name]["odds_count"] += 1
                                    is_hit = _is_pick_hit(success)
                                    if is_hit:
                                        leagues_data[comp_name]["total_hits"] += 1
                                    
                                    # Track per-market stats and detailed breakdown
                                    sel_text = pick.get("selection", "")
                                    try:
                                        family = _market_family(sel_text)
                                    except Exception:
                                        family = "generic"
                                    
                                    # Normalizar selKey para mercados (Over Córners, Under Tarjetas, etc)
                                    lower_sel = sel_text.strip().lower()
                                    category = ""
                                    if "corner" in lower_sel or "córner" in lower_sel:
                                        category = "Córners"
                                    elif "tarjeta" in lower_sel or "card" in lower_sel or "amarilla" in lower_sel:
                                        category = "Tarjetas"
                                    elif "foul" in lower_sel or "falta" in lower_sel:
                                        category = "Faltas"
                                    elif "shot_target" in lower_sel or "tiro_a_puerta" in lower_sel or "shots_target" in lower_sel or "pta" in lower_sel:
                                        category = "Tiros a puerta"
                                    elif "shot" in lower_sel or "tiro" in lower_sel or "remate" in lower_sel:
                                        category = "Tiros"
                                    elif "goal" in lower_sel or "gol" in lower_sel:
                                        category = "Goles"
                                    
                                    sel_key = sel_text.strip()
                                    if category:
                                        if "over" in lower_sel or "más de" in lower_sel or "mas de" in lower_sel:
                                            sel_key = f"Over {category}"
                                        elif "under" in lower_sel or "menos de" in lower_sel:
                                            sel_key = f"Under {category}"
                                            
                                    mkt = leagues_data[comp_name]["_market_stats"]
                                    if family not in mkt:
                                        mkt[family] = {"hits": 0, "total": 0}
                                    mkt[family]["total"] += 1
                                    if is_hit:
                                        mkt[family]["hits"] += 1

                                    # Detailed market map by sel_key
                                    det_map = leagues_data[comp_name]["_detailed_markets"]
                                    if sel_key not in det_map:
                                        det_map[sel_key] = {
                                            "name": sel_key,
                                            "totalPicks": 0,
                                            "ganados": 0,
                                            "perdidos": 0,
                                            "nulos": 0,
                                            "profit": 0.0,
                                            "oddsSum": 0.0,
                                            "oddsCount": 0,
                                        }
                                    m_entry = det_map[sel_key]
                                    m_entry["totalPicks"] += 1
                                    odds_val = float(pick.get("odds", 0.0) or 0.0)
                                    if odds_val > 0:
                                        m_entry["oddsSum"] += odds_val
                                        m_entry["oddsCount"] += 1
                                    
                                    if success is True:
                                        m_entry["ganados"] += 1
                                        m_entry["profit"] += pick_profit
                                    elif success is False:
                                        m_entry["perdidos"] += 1
                                        m_entry["profit"] += pick_profit # pick_profit es negativo
                                    elif success == "void":
                                        m_entry["nulos"] += 1
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
        
        staked_amt = league.pop("total_staked", 0.0)
        roi_val = (league["total_profit"] / staked_amt * 100) if staked_amt > 0 else ((league["total_profit"] / picks_cnt * 100) if picks_cnt > 0 else 0.0)
        league["roi"] = round(roi_val, 1)
        
        odds_cnt = league.pop("odds_count", 0)
        odds_s = league.pop("odds_sum", 0.0)
        avg_odds = round(odds_s / odds_cnt, 2) if odds_cnt > 0 else 0.0
        league["avg_odds"] = avg_odds
        league["break_even_pct"] = round((1.0 / avg_odds * 100.0), 1) if avg_odds > 0 else 0.0

        # Build market_hit_rates dict: {family: rate}
        raw_mkt = league.pop("_market_stats", {})
        market_hit_rates = {}
        for family, stats in raw_mkt.items():
            if stats["total"] >= 3:  # mínimo 3 picks para considerar la tasa
                market_hit_rates[family] = round(stats["hits"] / stats["total"], 3)
        league["market_hit_rates"] = market_hit_rates
        
        # Detailed markets list
        det_markets_map = league.pop("_detailed_markets", {})
        detailed_markets = list(det_markets_map.values())
        detailed_markets.sort(key=lambda x: x["totalPicks"], reverse=True)
        league["markets"] = detailed_markets

        # Seasons list sorted descending
        raw_seasons = league.pop("_seasons", set())
        league["seasons"] = sorted(list(raw_seasons), reverse=True)

        # Historical data for LRS
        league["historical_matches"] = league["total_matches"]
        league["historical_picks"] = picks_cnt
        league["historical_hits"] = league["total_hits"]
        league["historical_profit"] = league["total_profit"]
        league["historical_roi"] = league["roi"]
        
        results.append(league)
        
    _set_cache(cache_key, results)
    return results


@app.get("/api/v1/leagues/{league_name}/matches", response_model=list[AnalysisHistoryOut], tags=["Leagues"])
def get_league_matches(
    league_name: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    use_stake: bool = Query(False),
    season: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[AnalysisHistoryOut]:
    """
    Obtiene los partidos de una liga en específico sin filtrar por picks_calculados != None,
    cargando únicamente los campos necesarios para la vista de la liga (picks, resultados, id, etc.).
    """
    from sqlalchemy.orm import load_only
    from sqlalchemy import or_, and_, func
    comp_str = league_name.strip()

    query = db.query(AnalysisHistory).filter(
        or_(
            AnalysisHistory.competition == comp_str,
            and_(
                or_(AnalysisHistory.competition == None, AnalysisHistory.competition == ""),
                AnalysisHistory.payload.like(f'%"{comp_str}"%')
            )
        )
    )

    if season and season.strip().lower() != "all":
        s_str = season.strip()
        season_conds = [
            AnalysisHistory.payload.like(f'%"season_year": {s_str}%'),
            AnalysisHistory.payload.like(f'%"season_year": "{s_str}"%'),
            AnalysisHistory.payload.like(f'%"season": "{s_str}"%'),
            AnalysisHistory.payload.like(f'%"season": {s_str}%'),
        ]
        if s_str.isdigit():
            season_conds.append(func.strftime('%Y', AnalysisHistory.match_date) == s_str)
            season_conds.append(func.strftime('%Y', AnalysisHistory.date) == s_str)
        query = query.filter(or_(*season_conds))

    query = query.options(
        load_only(
            AnalysisHistory.id,
            AnalysisHistory.sport,
            AnalysisHistory.date,
            AnalysisHistory.match_date,
            AnalysisHistory.match_title,
            AnalysisHistory.competition,
            AnalysisHistory.payload,
            AnalysisHistory.picks_calculados,
            AnalysisHistory.count_in_profitability,
            AnalysisHistory.has_real_stats,
            AnalysisHistory.final_score_home,
            AnalysisHistory.final_score_away,
            AnalysisHistory.final_corners_home,
            AnalysisHistory.final_corners_away,
            AnalysisHistory.final_yellow_cards_home,
            AnalysisHistory.final_yellow_cards_away,
            AnalysisHistory.final_red_cards_home,
            AnalysisHistory.final_red_cards_away,
            AnalysisHistory.final_shots_home,
            AnalysisHistory.final_shots_away,
            AnalysisHistory.final_shots_on_target_home,
            AnalysisHistory.final_shots_on_target_away,
            AnalysisHistory.final_fouls_home,
            AnalysisHistory.final_fouls_away,
            AnalysisHistory.final_offsides_home,
            AnalysisHistory.final_offsides_away,
        )
    ).order_by(AnalysisHistory.date.desc())

    history_list = query.offset(offset).limit(limit).all()
    results = []
    for h in history_list:
        out = AnalysisHistoryOut.model_validate(h)
        results.append(_populate_history_extra_fields(h, out, use_stake=use_stake))
    return results


@app.get("/api/v1/leagues/{league_name}/markets", tags=["Leagues"])
def get_league_markets(
    league_name: str,
    use_stake: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Obtiene las estadísticas agregadas de mercados (desglose por tipo)
    para una única competición directamente filtrada en BD.
    """
    from sqlalchemy.orm import load_only
    history = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.competition == league_name)
        .options(load_only(
            AnalysisHistory.id,
            AnalysisHistory.picks_calculados,
            AnalysisHistory.compare_response_snapshot,
            AnalysisHistory.count_in_profitability,
            AnalysisHistory.final_score_home,
            AnalysisHistory.final_score_away,
            AnalysisHistory.final_corners_home,
            AnalysisHistory.final_corners_away,
            AnalysisHistory.final_yellow_cards_home,
            AnalysisHistory.final_yellow_cards_away,
            AnalysisHistory.final_red_cards_home,
            AnalysisHistory.final_red_cards_away,
            AnalysisHistory.final_shots_home,
            AnalysisHistory.final_shots_away,
            AnalysisHistory.final_shots_on_target_home,
            AnalysisHistory.final_shots_on_target_away,
            AnalysisHistory.final_fouls_home,
            AnalysisHistory.final_fouls_away,
            AnalysisHistory.final_offsides_home,
            AnalysisHistory.final_offsides_away,
        ))
        .all()
    )

    det_map = {}
    for h in history:
        if getattr(h, "count_in_profitability", True) is False:
            continue
        if not h.picks_calculados:
            continue
        try:
            picks = json.loads(h.picks_calculados) if isinstance(h.picks_calculados, str) else h.picks_calculados
            if not isinstance(picks, list):
                continue

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
            has_result = h.final_score_home is not None

            for pick in picks:
                if pick.get("is_blacklisted") or pick.get("is_rule_blocked"):
                    continue
                is_pub = pick.get("is_publishable", False)
                is_und = pick.get("is_underdog", False)
                if not is_pub and not is_und:
                    if pick.get("is_value", False):
                        is_pub = True
                if not (is_pub or is_und):
                    continue

                if has_result:
                    success = _check_pick_success(pick, res_dict)
                    if success is not None:
                        stake = _resolve_stake_from_pick(pick) if use_stake else MIN_STAKE
                        pick_profit = _calculate_pick_profit(success, pick.get("odds", 0.0)) * stake

                        sel_text = pick.get("selection", "")
                        lower_sel = sel_text.strip().lower()
                        category = ""
                        if "corner" in lower_sel or "córner" in lower_sel:
                            category = "Córners"
                        elif "tarjeta" in lower_sel or "card" in lower_sel or "amarilla" in lower_sel:
                            category = "Tarjetas"
                        elif "foul" in lower_sel or "falta" in lower_sel:
                            category = "Faltas"
                        elif "shot_target" in lower_sel or "tiro_a_puerta" in lower_sel or "shots_target" in lower_sel or "pta" in lower_sel:
                            category = "Tiros a puerta"
                        elif "shot" in lower_sel or "tiro" in lower_sel or "remate" in lower_sel:
                            category = "Tiros"
                        elif "goal" in lower_sel or "gol" in lower_sel:
                            category = "Goles"

                        sel_key = sel_text.strip()
                        if category:
                            if "over" in lower_sel or "más de" in lower_sel or "mas de" in lower_sel:
                                sel_key = f"Over {category}"
                            elif "under" in lower_sel or "menos de" in lower_sel:
                                sel_key = f"Under {category}"

                        if sel_key not in det_map:
                            det_map[sel_key] = {
                                "name": sel_key,
                                "totalPicks": 0,
                                "ganados": 0,
                                "perdidos": 0,
                                "nulos": 0,
                                "profit": 0.0,
                                "oddsSum": 0.0,
                                "oddsCount": 0,
                            }
                        m_entry = det_map[sel_key]
                        m_entry["totalPicks"] += 1
                        odds_val = float(pick.get("odds", 0.0) or 0.0)
                        if odds_val > 0:
                            m_entry["oddsSum"] += odds_val
                            m_entry["oddsCount"] += 1

                        if success is True:
                            m_entry["ganados"] += 1
                            m_entry["profit"] += pick_profit
                        elif success is False:
                            m_entry["perdidos"] += 1
                            m_entry["profit"] += pick_profit
                        elif success == "void":
                            m_entry["nulos"] += 1
        except Exception:
            pass

    detailed_markets = list(det_map.values())
    detailed_markets.sort(key=lambda x: x["totalPicks"], reverse=True)
    return detailed_markets

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

    # Refresh stake_units from picks_calculados after result is set
    if history.picks_calculados:
        history.stake_units = _sum_stake_from_picks(history.picks_calculados)

    db.commit()
    _invalidate_stats_cache()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)


@app.get("/api/v1/competitions/pending-picks", tags=["Competitions"])
def get_pending_picks_competitions(db: Session = Depends(get_db)):
    """
    Retorna las ligas y los event_ids que tienen partidos con resultados pendientes (final_score_home is None).
    """
    from sqlalchemy.orm import load_only
    records = (
        db.query(AnalysisHistory)
        .options(load_only(
            AnalysisHistory.competition,
            AnalysisHistory.payload,
            AnalysisHistory.final_score_home,
        ))
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
                ext_id = p_dict.get("match", {}).get("external_id") or p_dict.get("event_id") or p_dict.get("eventId")
                if ext_id:
                    pending_event_ids.add(str(ext_id))
            except Exception:
                pass

    return {
        "pending_competitions": list(pending_set),
        "pending_event_ids": list(pending_event_ids),
    }


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
    _invalidate_stats_cache()
    db.refresh(history)
    out = AnalysisHistoryOut.model_validate(history)
    return _populate_history_extra_fields(history, out)


@app.post("/api/v1/analysis/recalculate-accuracy", tags=["Analysis History"])
def recalculate_accuracy_fast(db: Session = Depends(get_db)):
    """
    Recalcula accuracy_percentage y picks_hits_summary para todos los registros
    que tienen resultados registrados, usando los picks ya guardados (NO vuelve
    a correr el motor de predicción). Es muy rápido y se puede usar para 
    sincronizar los conteos sin re-analizar.
    """
    history_list = db.query(AnalysisHistory).filter(
        AnalysisHistory.final_score_home.isnot(None)
    ).all()

    updated = 0
    for history in history_list:
        if not history.picks_calculados:
            continue
        try:
            picks = json.loads(str(history.picks_calculados)) if isinstance(history.picks_calculados, str) else history.picks_calculados
            if not isinstance(picks, list) or len(picks) == 0:
                continue

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

            hits = 0
            total = 0
            hits_pub = 0
            total_pub = 0

            for pick in picks:
                if pick.get("is_blacklisted") or pick.get("is_rule_blocked"):
                    continue
                is_pub = pick.get("is_publishable", False)
                is_und = pick.get("is_underdog", False)
                is_val = pick.get("is_value", False)
                if not (is_pub or is_und or is_val):
                    continue

                success = _check_pick_success(pick, res_dict)
                if success is None or success == "void":
                    continue

                total += 1
                is_hit = _is_pick_hit(success)
                if is_hit:
                    hits += 1

                if is_pub or is_val:
                    total_pub += 1
                    if is_hit:
                        hits_pub += 1

            if total > 0:
                history.accuracy_percentage = round((hits / total) * 100, 1)  # type: ignore[bad-assignment]
                history.picks_hits_summary = f"{hits}/{total}"  # type: ignore[bad-assignment]
            else:
                history.accuracy_percentage = None  # type: ignore[bad-assignment]
                history.picks_hits_summary = None  # type: ignore[bad-assignment]

            updated += 1
        except Exception as e:
            print(f"Error recalculando accuracy para {history.id}: {e}")

    db.commit()
    return {
        "message": f"Accuracy recalculada para {updated} partidos con resultado registrado.",
        "updated": updated,
    }

@app.get("/api/v1/analysis/recalculate-count", tags=["Analysis History"])
def get_recalculate_count(
    threshold_date: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retorna la cantidad de registros que serán procesados al llamar a recalculate-all.
    Útil para estimar el tiempo de recálculo en el frontend.
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

    query = db.query(AnalysisHistory).filter(AnalysisHistory.has_odds == True)
    if threshold_dt:
        query = query.filter(
            or_(
                AnalysisHistory.match_date >= threshold_dt,
                and_(AnalysisHistory.match_date.is_(None), AnalysisHistory.date >= threshold_dt)
            )
        )
    count = query.count()
    # Estimación basada en ~0.29 segundos por partido
    estimated_seconds = count * 0.29
    return {
        "total": count,
        "estimated_seconds": estimated_seconds,
    }


@app.post("/api/v1/analysis/recalculate-all", tags=["Analysis History"])
async def recalculate_all_accuracy(
    use_general_stats: bool = Query(False),
    threshold_date: str | None = Query(None),
    parallel: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Re-analiza todos los registros del historial:
    1. Vuelve a calcular los picks usando el payload original (motor de predicción),
       aplicando line shopping si el payload trae odds.sources de varias casas.
    2. Actualiza los snapshots y los picks calculados.
    3. Si hay resultados finales, recalcula el acierto (accuracy_percentage).
    """
    import time, sys
    threshold_dt = None
    if threshold_date:
        try:
            threshold_dt = datetime.strptime(threshold_date, "%Y-%m-%d")
        except Exception:
            try:
                threshold_dt = datetime.fromisoformat(threshold_date)
            except Exception:
                pass

    from src.core.pick_rules_engine import evaluate_pick_rules, StatSource
    rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pick_rules.json")
    enabled_rules = []
    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as rf:
                all_rules = json.load(rf)
                if isinstance(all_rules, list):
                    enabled_rules = [r for r in all_rules if r.get("enabled", False)]
        except Exception:
            pass

    query = db.query(AnalysisHistory).filter(AnalysisHistory.picks_calculados != None)
    if threshold_dt:
        query = query.filter(
            or_(
                AnalysisHistory.match_date >= threshold_dt,
                and_(AnalysisHistory.match_date.is_(None), AnalysisHistory.date >= threshold_dt)
            )
        )
    history_list = query.all()
    total_to_process = len(history_list)
    count = 0
    updated_accuracy_count = 0

    from sqlalchemy import text as _sql_text
    _q_hist_batch = _sql_text("""
        SELECT id, match_title, match_date, competition,
               final_score_home, final_score_away,
               final_corners_home, final_corners_away,
               final_yellow_cards_home, final_yellow_cards_away,
               final_shots_home, final_shots_away,
               final_shots_on_target_home, final_shots_on_target_away,
               final_fouls_home, final_fouls_away
        FROM analysis_history
        WHERE final_score_home IS NOT NULL AND final_score_away IS NOT NULL
        ORDER BY match_date DESC
    """)
    shared_historical_records = [dict(r) for r in db.execute(_q_hist_batch).mappings().all()]

    if parallel:
        from concurrent.futures import ProcessPoolExecutor
        from src.core.parallel_recalc import split_into_chunks, _recalc_chunk

        n_workers = max((os.cpu_count() or 2) - 1, 1)

        matches_plain = []
        for h in history_list:
            m_date_val = h.match_date or h.date
            matches_plain.append({
                "id": h.id,
                "payload": h.payload,
                "match_date": m_date_val.isoformat() if m_date_val else None,
                "sport": h.sport.value if isinstance(h.sport, Sport) else str(h.sport),
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
            })

        chunks = split_into_chunks(matches_plain, n_workers)
        chunk_payloads = []
        for ch in chunks:
            chunk_payloads.append({
                "matches": ch,
                "shared_historical_records": shared_historical_records,
                "use_general_stats": use_general_stats,
                "threshold_dt_iso": threshold_dt.isoformat() if threshold_dt else None,
                "enabled_rules": enabled_rules,
            })

        print(
            f"Iniciando recalculate-all PARALELO con {n_workers} workers en {len(chunk_payloads)} chunks "
            f"({total_to_process} partidos totales)...",
            flush=True,
        )
        t_start = time.perf_counter()
        results_by_id = {}

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            for chunk_idx, chunk_results in enumerate(executor.map(_recalc_chunk, chunk_payloads), start=1):
                print(f"Chunk [{chunk_idx}/{len(chunk_payloads)}] completado ({len(chunk_results)} partidos)", flush=True)
                for res in chunk_results:
                    results_by_id[res["id"]] = res

        for history in history_list:
            res = results_by_id.get(history.id)
            if not res:
                continue
            if res.get("error"):
                print(f"Error re-analizando registro {history.id}: {res['error']}", flush=True)
                continue
            if res.get("has_odds") is False:
                history.has_odds = False
                continue
            if res.get("skipped"):
                continue

            history.picks_calculados = res["picks_calculados"]
            history.compare_response_snapshot = res["compare_response_snapshot"]
            history.accuracy_percentage = res["accuracy_percentage"]
            if res.get("has_final_score"):
                updated_accuracy_count += 1

            history.last_recalculated_at = datetime.utcnow()
            history.needs_recalc = False
            count += 1

        db.commit()
        t_total = time.perf_counter() - t_start
        print(f"Recalculate-all paralelo completado en {t_total:.2f}s ({count} procesados, {updated_accuracy_count} aciertos actualizados)", flush=True)
        return {
            "message": f"Se han re-analizado {count} partidos en modo paralelo ({n_workers} workers). Se actualizó el acierto en {updated_accuracy_count} de ellos.",
            "total_reanalyzed": count,
            "accuracy_updated": updated_accuracy_count,
            "total_to_recalculate": total_to_process,
            "execution_time_seconds": round(t_total, 2),
            "workers_used": n_workers,
            "mode": "parallel",
        }

    # ── FALLBACK SECUENCIAL (parallel=False) ──
    _team_index: dict[str, list] = {}
    for r in shared_historical_records:
        title = r.get("match_title", "") or ""
        comp = (r.get("competition") or "").strip().lower()
        ht = (r.get("home_team") or (title.split(" vs ")[0] if " vs " in title else "")).strip().lower()
        at = (r.get("away_team") or (title.split(" vs ")[1] if " vs " in title else "")).strip().lower()
        if ht:
            _team_index.setdefault(ht, []).append(r)
            if comp:
                _team_index.setdefault(f"{comp}::{ht}", []).append(r)
        if at:
            _team_index.setdefault(at, []).append(r)
            if comp:
                _team_index.setdefault(f"{comp}::{at}", []).append(r)

    import time, sys
    _timings = {"payload_load": 0.0, "engine_calc": 0.0, "eligibility": 0.0, "db_write": 0.0}
    _slowest = []

    for idx, history in enumerate(history_list, start=1):
        m_date = history.match_date or history.date
        print(
            f"[{idx}/{total_to_process}] Analizando (secuencial): {history.match_title} "
            f"({m_date.strftime('%Y-%m-%d') if m_date else 'sin fecha'}) — id={history.id}",
            flush=True,
        )
        try:
            if not history.payload:
                continue

            if not _check_payload_has_odds(history.payload):
                history.has_odds = False
                continue

            t0 = time.perf_counter()
            payload_dict = json.loads(str(history.payload))
            local_payload = dict(payload_dict)
            sport = history.sport
            _timings["payload_load"] += time.perf_counter() - t0

            target_use_gen = False
            if use_general_stats:
                if threshold_dt:
                    if m_date:
                        target_use_gen = m_date.date() >= threshold_dt.date()
                    else:
                        target_use_gen = True
                else:
                    target_use_gen = True

            local_payload["use_general_stats"] = target_use_gen

            new_response = None
            bookmaker_map: dict = {}
            t0 = time.perf_counter()
            try:
                if sport == Sport.FOOTBALL:
                    req = FootballCompareRequest(**local_payload)
                    req, bookmaker_map = _apply_line_shopping(req)
                    new_response = await compare_football(
                        req,
                        db=db,
                        exclude_match_id=history.id,
                        current_match_date=m_date,
                        precomputed_historical_records=shared_historical_records,
                        precomputed_team_index=_team_index,
                    )
            except Exception as comp_err:
                print(f"  -> Error en motor de comparación para {history.id} ({sport}): {comp_err}", flush=True)
                continue
            finally:
                dt = time.perf_counter() - t0
                _timings["engine_calc"] += dt
                _slowest.append((dt, history.id, history.match_title))
                print(f"  -> Terminado en {dt:.2f}s", flush=True)

            if new_response:
                if bookmaker_map:
                    _annotate_best_bookmaker(new_response, bookmaker_map, req.home.name, req.away.name)

                t0 = time.perf_counter()
                picks = [v.model_dump() if hasattr(v, 'model_dump') else v.__dict__ for v in new_response.values]

                if enabled_rules:
                    home_stats = local_payload.get("home", {})
                    away_stats = local_payload.get("away", {})
                    stat_src = StatSource.from_payload(home_stats, away_stats)
                    for pick in picks:
                        sel = pick.get("selection", "")
                        should_block, _ = evaluate_pick_rules(sel, stat_src, enabled_rules)
                        if should_block:
                            pick["is_rule_blocked"] = True
                            pick["is_publishable"] = False
                            pick["is_value"] = False
                            pick["quality_score"] = -1
                _timings["eligibility"] += time.perf_counter() - t0

                t0 = time.perf_counter()
                history.picks_calculados = json.dumps(picks)
                history.compare_response_snapshot = json.dumps(new_response.model_dump() if hasattr(new_response, 'model_dump') else new_response.__dict__)

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
                        if pick.get("is_blacklisted") or pick.get("is_rule_blocked"):
                            continue
                        if not (pick.get("is_publishable", pick.get("is_value", False))):
                            continue
                        success = _check_pick_success(pick, results_dict)
                        if success is not None and success != "void":
                            total += 1
                            if _is_pick_hit(success):
                                hits += 1

                    history.accuracy_percentage = (hits / total) * 100 if total > 0 else None
                    updated_accuracy_count += 1

                history.last_recalculated_at = datetime.utcnow()
                history.needs_recalc = False
                count += 1
                _timings["db_write"] += time.perf_counter() - t0
        except Exception as e:
            print(f"Error re-analizando registro {history.id}: {e}", flush=True)

    db.commit()
    _slowest.sort(reverse=True)
    print("TIMINGS TOTALES:", _timings, flush=True)
    print("TOP 10 MÁS LENTOS:", _slowest[:10], flush=True)
    return {
        "message": f"Se han re-analizado {count} partidos (secuencial). Se actualizó el acierto en {updated_accuracy_count} de ellos.",
        "total_reanalyzed": count,
        "accuracy_updated": updated_accuracy_count,
        "total_to_recalculate": total_to_process,
        "timings_debug": _timings,
        "slowest_5": [{"seconds": s, "id": i, "match": m} for s, i, m in _slowest[:5]],
        "mode": "sequential",
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
        get_market_stake_modifier_for_league,
        is_publishable_pick,
        is_value_pick,
        is_underdog_pick,
        score_pick_quality,
        _calculate_display_score,
        _frontend_style_strategic_score,
        ValueIndicator
    )
    import json

    history_list = db.query(AnalysisHistory).filter(AnalysisHistory.picks_calculados != None).all()
    updated_count = 0

    for history in history_list:
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
                        pick["is_underdog"] = False
                    else:
                        v = ValueIndicator(
                            selection=sel,
                            odds=pick.get("odds"),
                            model_prob=pick.get("model_prob", 0.0),
                            calibrated_prob=pick.get("calibrated_prob"),
                            edge_ev=pick.get("edge_ev", 0.0),
                            data_quality_score=pick.get("data_quality_score"),
                            sample_size_weight=pick.get("sample_size_weight"),
                            stake_units=pick.get("stake_units"),
                            is_blacklisted=False
                        )
                        pick["is_publishable"] = is_publishable_pick(v)
                        pick["is_value"] = is_value_pick(v)
                        pick["quality_score"] = score_pick_quality(v)
                        pick["display_score"] = _calculate_display_score(v)
                        pick["is_underdog"] = is_underdog_pick(v)
                        pick["strategic_score"] = _frontend_style_strategic_score(v)

                # Aplicar o revertir stake_modifier de la liga en picks no blacklisted
                if not pick.get("is_blacklisted"):
                    stake_mod = get_market_stake_modifier_for_league(league_name, sel)
                    if stake_mod is None:
                        stake_mod = 1.0

                    base_stake = pick.get("base_stake_units")
                    if base_stake is None:
                        base_stake = pick.get("stake_units") or 1.0
                        pick["base_stake_units"] = base_stake

                    target_stake = max(MIN_STAKE, round(base_stake * stake_mod)) if stake_mod != 1.0 else base_stake
                    if pick.get("stake_units") != target_stake:
                        pick["stake_units"] = target_stake
                        changed = True

            if changed:
                history.picks_calculados = json.dumps(picks)
                history.stake_units = _sum_stake_from_picks(picks)
                # Also update compare_response_snapshot if it exists
                if history.compare_response_snapshot:
                    try:
                        snap = json.loads(str(history.compare_response_snapshot))
                        if isinstance(snap, dict) and "values" in snap:
                            snap["values"] = picks
                            history.compare_response_snapshot = json.dumps(snap)
                    except Exception as snap_err:
                        print(f"Error updating snapshot in blacklist for history {history.id}: {snap_err}")
                
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
            traceback.print_exc(f"Error actualizando blacklist para {history.id}: {e}")

    if updated_count > 0:
        db.commit()
        _invalidate_stats_cache()

    return {
        "status": "ok",
        "message": f"Se actualizó la blacklist en {updated_count} partidos del historial.",
        "updated_count": updated_count
    }


# ---------------------------------------------------------------------------
# Pick Rules & Profitable Leagues
# ---------------------------------------------------------------------------
PICK_RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "pick_rules.json")
PROFITABLE_LEAGUES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "profitable_leagues.json")


def get_profitable_leagues() -> set[str]:
    if not os.path.exists(PROFITABLE_LEAGUES_PATH):
        return set()
    try:
        with open(PROFITABLE_LEAGUES_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
                if isinstance(data, list):
                    return set(data)
    except Exception:
        pass
    return set()


def save_profitable_leagues(leagues: set[str]) -> None:
    try:
        os.makedirs(os.path.dirname(PROFITABLE_LEAGUES_PATH), exist_ok=True)
        with open(PROFITABLE_LEAGUES_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(leagues)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving profitable leagues: {e}")


def is_league_profitable(league_name: str | None) -> bool:
    if not league_name:
        return True
    if not os.path.exists(PROFITABLE_LEAGUES_PATH):
        return True
    profitable = get_profitable_leagues()
    return any(p.lower() == league_name.lower() for p in profitable)


@app.post("/api/v1/leagues/{league_name}/profitability", tags=["Leagues"])
def update_league_profitability(
    league_name: str,
    count_in_profitability: bool = Query(...),
    db: Session = Depends(get_db)
):
    """
    Actualiza la rentabilidad de una liga completa y todos sus partidos en el historial.
    """
    history_list = db.query(AnalysisHistory).filter(AnalysisHistory.competition == league_name).all()
    profitable = get_profitable_leagues()
    if not os.path.exists(PROFITABLE_LEAGUES_PATH):
        for h in history_list:
            if h.payload and getattr(h, "count_in_profitability", True):
                try:
                    p = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                    cname = p.get("competition") or "Desconocida"
                    if cname != "Desconocida":
                        profitable.add(cname)
                except Exception:
                    pass

    normalized_target = league_name.strip()
    profitable = {p for p in profitable if p.lower() != normalized_target.lower()}
    if count_in_profitability:
        profitable.add(normalized_target)

    save_profitable_leagues(profitable)

    updated_count = 0
    for h in history_list:
        if h.payload:
            try:
                pdata = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                cname = pdata.get("competition") or pdata.get("tournament", {}).get("name") or "Desconocida"
                if cname.lower() == normalized_target.lower():
                    h.count_in_profitability = count_in_profitability
                    updated_count += 1
            except Exception:
                continue

    if updated_count > 0:
        db.commit()

    return {
        "status": "ok",
        "league_name": league_name,
        "count_in_profitability": count_in_profitability,
        "updated_count": updated_count,
        "message": f"Se actualizó la rentabilidad a '{count_in_profitability}' en {updated_count} partidos de '{league_name}'."
    }


class BlacklistMarketRequest(BaseModel):
    league: str
    market_name: str


class BlacklistMarketsBatchRequest(BaseModel):
    league: str
    markets: list[str]


@app.post("/api/v1/leagues/blacklist-markets", tags=["Leagues"])
def blacklist_markets_batch(req: BlacklistMarketsBatchRequest, db: Session = Depends(get_db)):
    """
    Agrega varios mercados de una liga específica a data/league_penalties.json
    y vuelve a aplicar la blacklist a todo el historial en una sola operación.
    """
    from src.ui.api.compare import _market_family, _market_side
    penalties_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "league_penalties.json")
    try:
        penalties = []
        if os.path.exists(penalties_path):
            try:
                with open(penalties_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        penalties = json.loads(content)
                        if not isinstance(penalties, list):
                            penalties = []
            except Exception:
                penalties = []

        added_count = 0
        for m_name in req.markets:
            if not m_name:
                continue
            family = _market_family(m_name)
            side = _market_side(m_name)

            exists = False
            for rule in penalties:
                if (rule.get("league", "").strip().lower() == req.league.strip().lower() and
                    rule.get("market_family", "").strip().lower() == family.lower() and
                    rule.get("market_side", "").strip().lower() == side.lower()):
                    exists = True
                    break

            if not exists:
                penalties.append({
                    "league": req.league.strip(),
                    "market_family": family,
                    "market_side": side
                })
                added_count += 1

        if added_count > 0:
            os.makedirs(os.path.dirname(penalties_path), exist_ok=True)
            with open(penalties_path, "w", encoding="utf-8") as f:
                json.dump(penalties, f, ensure_ascii=False, indent=2)

        res = apply_blacklist(db=db)
        return {
            "status": "ok",
            "message": f"Se añadieron {added_count} mercado(s) a blacklist para '{req.league}'. {res.get('message', '')}",
            "apply_blacklist_result": res
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al agregar mercados a blacklist: {e}")


@app.post("/api/v1/leagues/blacklist-market", tags=["Leagues"])
def blacklist_market(req: BlacklistMarketRequest, db: Session = Depends(get_db)):
    """
    Agrega un mercado de una liga específica a data/league_penalties.json
    y vuelve a aplicar la blacklist a todo el historial.
    """
    return blacklist_markets_batch(
        req=BlacklistMarketsBatchRequest(league=req.league, markets=[req.market_name]),
        db=db
    )



class ReduceStakeMarketRequest(BaseModel):
    league: str
    market_name: str
    stake_modifier: float = 0.5


@app.post("/api/v1/leagues/reduce-stake-market", tags=["Leagues"])
def reduce_stake_market(req: ReduceStakeMarketRequest, db: Session = Depends(get_db)):
    """
    Agrega o actualiza una regla de reducción de stake para un mercado en data/league_penalties.json
    y vuelve a aplicar el recálculo al historial de análisis.
    """
    from src.ui.api.compare import _market_family, _market_side
    penalties_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "league_penalties.json")
    try:
        penalties = []
        if os.path.exists(penalties_path):
            try:
                with open(penalties_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        penalties = json.loads(content)
                        if not isinstance(penalties, list):
                            penalties = []
            except Exception:
                penalties = []

        family = _market_family(req.market_name)
        side = _market_side(req.market_name)

        found = False
        for rule in penalties:
            if (rule.get("league", "").strip().lower() == req.league.strip().lower() and
                rule.get("market_family", "").strip().lower() == family.lower() and
                rule.get("market_side", "").strip().lower() == side.lower()):
                rule["stake_modifier"] = req.stake_modifier
                # Asegurarse de que no esté en blacklist si solo queremos reducir stake
                rule["blacklist"] = False
                found = True
                break

        if not found:
            penalties.append({
                "league": req.league.strip(),
                "market_family": family,
                "market_side": side,
                "stake_modifier": req.stake_modifier,
                "blacklist": False
            })

        os.makedirs(os.path.dirname(penalties_path), exist_ok=True)
        with open(penalties_path, "w", encoding="utf-8") as f:
            json.dump(penalties, f, ensure_ascii=False, indent=2)

        res = apply_blacklist(db=db)
        return {
            "status": "ok",
            "message": f"Stake reducido al {int(req.stake_modifier*100)}% para '{req.market_name}' en '{req.league}'. {res.get('message', '')}",
            "apply_blacklist_result": res
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al reducir stake de mercado: {e}")




@app.get("/api/v1/pick-rules", tags=["Pick Rules"])
def get_pick_rules():
    """Returns the list of configured pick rules."""
    try:
        if not os.path.exists(PICK_RULES_PATH):
            return []
        with open(PICK_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/pick-rules", tags=["Pick Rules"])
def save_pick_rules(rules: Any = Body(...)):
    """Saves the full list of pick rules and structural correlation rules (overwrite)."""
    try:
        os.makedirs(os.path.dirname(PICK_RULES_PATH), exist_ok=True)
        with open(PICK_RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        count = len(rules.get("rules", [])) if isinstance(rules, dict) else len(rules)
        return {"status": "ok", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RuleSimulationRequest(BaseModel):
    market_family: str
    market_side: str
    conditions: list[dict]


@app.post("/api/v1/pick-rules/simulate", tags=["Pick Rules"])
def simulate_pick_rules(req: RuleSimulationRequest, db: Session = Depends(get_db)):
    """
    Evaluates proposed conditions on the historical database to see the success rate.
    """
    history_list = db.query(AnalysisHistory).all()
    matched_count = 0
    success_count = 0
    matched_matches = []

    from src.core.pick_rules_engine import StatSource, _OPERATORS

    def check_market_success(market_family: str, market_side: str, history: AnalysisHistory) -> bool | None:
        score_h = history.final_score_home
        score_a = history.final_score_away
        corners_h = history.final_corners_home
        corners_a = history.final_corners_away

        if score_h is None or score_a is None:
            return None

        if market_family == "result":
            if market_side == "home":
                return score_h > score_a
            if market_side == "away":
                return score_a > score_h
            if market_side == "draw":
                return score_h == score_a
        elif market_family == "btts":
            both = score_h > 0 and score_a > 0
            return both if market_side == "yes" else not both
        elif market_family == "goals":
            total = score_h + score_a
            if market_side == "over":
                return total > 2.5
            if market_side == "under":
                return total < 2.5
        elif market_family == "corners":
            if corners_h is None or corners_a is None:
                return None
            total = corners_h + corners_a
            if market_side == "over":
                return total > 9.5
            if market_side == "under":
                return total < 9.5
        elif market_family == "cards":
            total_yellow = (history.final_yellow_cards_home or 0) + (history.final_yellow_cards_away or 0)
            if history.final_yellow_cards_home is None:
                return None
            if market_side == "over":
                return total_yellow > 4.5
            if market_side == "under":
                return total_yellow < 4.5
        return None

    for history in history_list:
        if not history.payload:
            continue
        try:
            payload = json.loads(str(history.payload)) if isinstance(history.payload, str) else history.payload
            if not isinstance(payload, dict):
                continue
            h_stats = payload.get("home_stats") or payload.get("home") or {}
            a_stats = payload.get("away_stats") or payload.get("away") or {}
            odds_payload = payload.get("odds") or {}

            stat_source = StatSource.from_payload(h_stats, a_stats, odds_payload)
            
            # Check conditions
            all_pass = True
            for cond in req.conditions:
                stat_key = cond.get("stat")
                operator = cond.get("operator", ">=")
                expected = cond.get("value")
                
                if expected is None:
                    continue
                    
                actual = stat_source.get(stat_key)
                if actual is None:
                    all_pass = False
                    break
                    
                # Evaluate using identical operator logic
                if operator not in _OPERATORS:
                    all_pass = False
                    break
                    
                try:
                    if not _OPERATORS[operator](actual, expected):
                        all_pass = False
                        break
                except Exception:
                    all_pass = False
                    break
            
            if all_pass:
                matched_count += 1
                success = check_market_success(req.market_family, req.market_side, history)
                is_hit = False
                has_result = success is not None
                if success is True:
                    success_count += 1
                    is_hit = True
                
                matched_matches.append({
                    "id": str(history.id),
                    "date": history.match_date.isoformat() if history.match_date else (history.date.isoformat() if history.date else ""),
                    "title": history.match_title or "Partido desconocido",
                    "score": f"{history.final_score_home} - {history.final_score_away}" if has_result else "Pendiente",
                    "has_result": has_result,
                    "success": is_hit
                })
        except Exception as err:
            print(f"Error simulando en partido {history.id}: {err}")

    accuracy = (success_count / matched_count * 100) if matched_count > 0 else 0.0
    return {
        "matched_count": matched_count,
        "success_count": success_count,
        "accuracy": round(accuracy, 1),
        "matches": matched_matches[:100]
    }



@app.post("/api/v1/analysis/apply-rules", tags=["Pick Rules"])
def apply_pick_rules(db: Session = Depends(get_db)):
    """
    Re-evaluates pick_rules.json against saved picks in the history.
    Blocks picks that violate enabled rules (marks is_rule_blocked=True, clears is_publishable/is_value).
    Also un-blocks picks for rules that are now disabled.
    """
    from src.ui.api.compare import (
        is_publishable_pick, is_value_pick, is_underdog_pick, score_pick_quality,
        _calculate_display_score, _frontend_style_strategic_score,
        ValueIndicator
    )
    from src.core.pick_rules_engine import evaluate_pick_rules, load_pick_rules_data, resolve_match_picks_correlation, StatSource

    try:
        rules_list, correlation_rules = load_pick_rules_data(PICK_RULES_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo reglas: {e}")

    enabled_rules = [r for r in rules_list if r.get("enabled", False)]

    history_list = db.query(AnalysisHistory).all()
    updated_count = 0

    for history in history_list:
        if not history.picks_calculados or not history.payload:
            continue
        try:
            picks = json.loads(str(history.picks_calculados))
            payload = json.loads(str(history.payload))
            if not isinstance(picks, list) or not isinstance(payload, dict):
                continue

            home_stats = payload.get("home", {})
            away_stats = payload.get("away", {})
            stat_source = StatSource.from_payload(home_stats, away_stats)

            changed = False
            for pick in picks:
                sel = pick.get("selection", "")
                should_block, _ = evaluate_pick_rules(sel, stat_source, enabled_rules)

                current_blocked = pick.get("is_rule_blocked", False)
                if should_block != current_blocked:
                    pick["is_rule_blocked"] = should_block
                    changed = True
                    if should_block:
                        pick["is_publishable"] = False
                        pick["is_value"] = False
                        pick["quality_score"] = -1
                    else:
                        v = ValueIndicator(
                            selection=sel,
                            odds=pick.get("odds"),
                            model_prob=pick.get("model_prob", 0.0),
                            calibrated_prob=pick.get("calibrated_prob"),
                            edge_ev=pick.get("edge_ev", 0.0),
                            data_quality_score=pick.get("data_quality_score"),
                            sample_size_weight=pick.get("sample_size_weight"),
                            stake_units=pick.get("stake_units"),
                            is_blacklisted=pick.get("is_blacklisted", False),
                        )
                        if not v.is_blacklisted:
                            pick["is_publishable"] = is_publishable_pick(v)
                            pick["is_value"] = is_value_pick(v)
                            pick["quality_score"] = score_pick_quality(v)
                            pick["is_underdog"] = is_underdog_pick(v)

            # Descorrelacionar picks del partido
            picks = resolve_match_picks_correlation(picks, correlation_rules=correlation_rules)
            changed = True

            if changed:
                history.picks_calculados = json.dumps(picks)
                if history.compare_response_snapshot:
                    try:
                        snap = json.loads(str(history.compare_response_snapshot))
                        if isinstance(snap, dict) and "values" in snap:
                            snap["values"] = picks
                            history.compare_response_snapshot = json.dumps(snap)
                    except Exception as snap_err:
                        print(f"Error updating snapshot for history {history.id}: {snap_err}")
                updated_count += 1
        except Exception as e:
            print(f"Error aplicando reglas para {history.id}: {e}")

    if updated_count > 0:
        db.commit()

    return {
        "status": "ok",
        "message": f"Reglas aplicadas a {updated_count} partidos del historial.",
        "updated_count": updated_count,
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
    # shots_target DEBE ir antes que shots (tiro/shot es subconjunto de shots_target)
    if any(k in s for k in ["pta", "a puerta", "target", "shots_target", "shot_target"]):
        return "Tiros a puerta: Over/Under"
    if any(k in s for k in ["shot", "shots", "tiros", "remates"]):
        return "Tiros: Over/Under"
    if any(k in s for k in ["over", "under", "más de", "menos de"]) and any(k in s for k in ["gol", "goles", "goal", "goals"]):
        return "Goles: Over/Under"
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
    cache_key = f"global:{date_from}:{date_to}:{use_stake}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    from sqlalchemy.orm import load_only
    query = db.query(AnalysisHistory).filter(AnalysisHistory.picks_calculados != None).options(
        load_only(
            AnalysisHistory.id,
            AnalysisHistory.sport,
            AnalysisHistory.date,
            AnalysisHistory.match_date,
            AnalysisHistory.match_title,
            AnalysisHistory.competition,
            AnalysisHistory.payload,
            AnalysisHistory.picks_calculados,
            AnalysisHistory.compare_response_snapshot,
            AnalysisHistory.count_in_profitability,
            AnalysisHistory.final_score_home,
            AnalysisHistory.final_score_away,
            AnalysisHistory.final_corners_home,
            AnalysisHistory.final_corners_away,
            AnalysisHistory.final_yellow_cards_home,
            AnalysisHistory.final_yellow_cards_away,
            AnalysisHistory.final_red_cards_home,
            AnalysisHistory.final_red_cards_away,
            AnalysisHistory.final_shots_home,
            AnalysisHistory.final_shots_away,
            AnalysisHistory.final_shots_on_target_home,
            AnalysisHistory.final_shots_on_target_away,
            AnalysisHistory.final_fouls_home,
            AnalysisHistory.final_fouls_away,
            AnalysisHistory.final_offsides_home,
            AnalysisHistory.final_offsides_away,
        )
    )
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
    
    categories = ["professional", "underdog"]
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
                league = h.competition
                if not league and h.payload:
                    try:
                        p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                        league = p_data.get("competition") or "Desconocida"
                    except: pass
                if not league:
                    league = "Desconocida"
                
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
                    
                    # Fallback for old picks that might only have is_value
                    if not is_pub and not is_und:
                        if pick.get("is_value", False):
                            is_pub = True
                            
                    if not (is_pub or is_und):
                        continue
                        
                    if is_pub:
                        cat = "professional"
                    elif is_und:
                        cat = "underdog"

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
                        stake = _resolve_stake_from_pick(pick)
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
                staked = data.get("staked", data["picks"])
                roi_v = (data.get("profit", 0.0) / staked * 100) if staked > 0 else 0.0
                result.append({
                    "name": name,
                    "picks": data["picks"],
                    "hits": data["hits"],
                    "accuracy": acc,
                    "profit": round(data.get("profit", 0.0), 2),
                    "roi": round(roi_v, 1)
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

    res = {
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
    _set_cache(cache_key, res)
    return res

def build_equity_curve(df_match_level: pd.DataFrame, bankroll_units: float = 100.0):
    """
    Construye la curva de equity y el drawdown correctamente, usando
    un bankroll base como referencia (no el pico de profit).

    Args:
        df_match_level: DataFrame con columnas "Fecha de Partido" y
                         "Beneficio Neto Partido (u)", ya ordenado o no.
        bankroll_units: bankroll base asumido, en las mismas unidades
                         que el profit (ver nota arriba).

    Returns:
        (df_equity, max_drawdown_u, max_drawdown_pct)
    """
    equity_rows = []
    max_drawdown_u = 0.0
    max_drawdown_pct = 0.0

    if df_match_level.empty:
        return pd.DataFrame(equity_rows), max_drawdown_u, max_drawdown_pct

    df = df_match_level.copy()
    df["Fecha de Partido"] = pd.to_datetime(df["Fecha de Partido"])
    df = df.sort_values("Fecha de Partido").reset_index(drop=True)

    cumulative_profit = 0.0
    # El bankroll arranca en bankroll_units, NUNCA en 0 — esto es lo que
    # evita la distorsión de porcentajes gigantes al inicio de la serie.
    running_max_bankroll = bankroll_units

    for _, row in df.iterrows():
        cumulative_profit += row["Beneficio Neto Partido (u)"]
        bankroll_value = bankroll_units + cumulative_profit

        running_max_bankroll = max(running_max_bankroll, bankroll_value)

        drawdown_u = bankroll_value - running_max_bankroll  # <= 0
        drawdown_pct = (drawdown_u / running_max_bankroll * 100.0) if running_max_bankroll > 0 else 0.0

        equity_rows.append({
            "Fecha": row["Fecha de Partido"].strftime("%Y-%m-%d"),
            "Partido": row["Partido"],
            "Beneficio Partido (u)": row["Beneficio Neto Partido (u)"],
            "Profit Acumulado (u)": round(cumulative_profit, 2),
            "Bankroll Estimado (u)": round(bankroll_value, 2),
            "Máximo Bankroll Histórico (u)": round(running_max_bankroll, 2),
            "Drawdown (u)": round(drawdown_u, 2),
            "Drawdown (%)": round(drawdown_pct, 2),
        })

        max_drawdown_u = min(max_drawdown_u, drawdown_u)
        max_drawdown_pct = min(max_drawdown_pct, drawdown_pct)

    return pd.DataFrame(equity_rows), max_drawdown_u, max_drawdown_pct

@app.get("/api/v1/report/excel", tags=["Stats"])
def export_excel_report(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    use_stake: bool = Query(False),
    bankroll_units: float = Query(
        100.0,
        description="Bankroll base en 'unidades', usado como referencia "
                     "para calcular el % de drawdown. Ej: si 1u = 1% de "
                     "tu bankroll real, usa 100. Si 1u = 0.5%, usa 200."
    ),
    db: Session = Depends(get_db)
):
    """Genera y descarga un reporte detallado en Excel (.xlsx) con los datos
    del modelo, partidos, picks, rentabilidad y análisis de significancia
    ajustado por clustering (a nivel de partido)."""

    query = db.query(AnalysisHistory).filter(AnalysisHistory.picks_calculados != None)
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

    history = query.filter(AnalysisHistory.count_in_profitability == True).all()

    matches_data = []
    picks_data = []
    match_level_data = []  # NUEVO: una fila por partido, para el análisis clustering-adjusted

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

    categories = ["professional", "underdog"]
    cat_accumulators = {
        cat: {
            "picks": 0, "hits": 0, "pending": 0, "profit": 0.0,
            "staked": 0, "odds": 0.0, "winning_odds": 0.0, "winning_count": 0
        }
        for cat in categories
    }

    league_counters = {}
    market_counters = {}

    for h in history:
        has_result = h.final_score_home is not None
        if has_result:
            matches_with_results += 1

        league = "Desconocida"
        if h.payload:
            try:
                p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                league = p_data.get("competition") or "Desconocida"
            except Exception:
                pass

        teams = []
        if h.match_title:
            if " vs " in h.match_title:
                teams = [t.strip() for t in h.match_title.split(" vs ")]
            elif " - " in h.match_title:
                teams = [t.strip() for t in h.match_title.split(" - ")]

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
            except Exception:
                pass

        matches_data.append({
            "ID Partido": h.id,
            "Fecha de Análisis": h.date.strftime("%Y-%m-%d %H:%M") if h.date else "",
            "Fecha de Partido": h.match_date.strftime("%Y-%m-%d %H:%M") if h.match_date else "",
            "Deporte": h.sport.value if hasattr(h.sport, 'value') else str(h.sport),
            "Partido": h.match_title,
            "Liga": league,
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

        # ── Acumuladores a nivel de PARTIDO (para el análisis clustering-adjusted) ──
        match_profit = 0.0
        match_picks_resolved = 0
        match_hits = 0
        match_pending = 0
        match_odds_list = []

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

                        if not is_pub and not is_und:
                            if pick.get("is_value", False):
                                is_pub = True

                        if not (is_pub or is_und):
                            continue

                        cat = "professional" if is_pub else "underdog"

                        odds = float(pick.get("odds", 0.0))
                        market = pick.get("market")
                        if not market or market == "N/A" or market == "Otro":
                            market = get_market_name(pick.get("selection", ""))

                        success = None
                        if has_result:
                            success = _check_pick_success(pick, results_dict)

                        success_str = "Pendiente"
                        pick_profit = 0.0

                        if use_stake:
                            stake = _resolve_stake_from_pick(pick)
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
                            match_pending += 1
                        else:
                            counts_for_accuracy = success != "void"
                            total_profit += pick_profit
                            cat_accumulators[cat]["profit"] += pick_profit
                            match_profit += pick_profit

                            if counts_for_accuracy:
                                total_picks += 1
                                total_staked_picks += stake
                                total_odds += odds
                                cat_accumulators[cat]["picks"] += 1
                                cat_accumulators[cat]["staked"] += stake
                                cat_accumulators[cat]["odds"] += odds
                                match_picks_resolved += 1
                                match_odds_list.append(odds)

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
                                    match_hits += 1

                                    league_counters[league]["hits"] += 1
                                    market_counters[market]["hits"] += 1

                        # ── Fila de pick individual (con fix de nomenclatura y placeholder CLV) ──
                        edge_prob = float(pick.get("edge", 0.0)) if pick.get("edge") is not None else None
                        edge_ev_frac = pick.get("edge_ev")
                        ev_real_pct = float(edge_ev_frac) * 100.0 if edge_ev_frac is not None else None

                        # Placeholder CLV: hoy no disponible. Cuando exista `closing_odds`
                        # en el pick, esto se calcula solo, sin más cambios en el exportador.
                        closing_odds = pick.get("closing_odds")
                        clv_pct = None
                        if closing_odds and odds:
                            try:
                                own_implied = 1.0 / odds
                                closing_implied = 1.0 / float(closing_odds)
                                clv_pct = round((closing_implied - own_implied) / closing_implied * 100.0, 2)
                            except Exception:
                                clv_pct = None

                        picks_data.append({
                            "ID Partido": h.id,
                            "Fecha": h.date.strftime("%Y-%m-%d %H:%M") if h.date else "",
                            "Partido": h.match_title,
                            "Liga": league,
                            "Deporte": h.sport.value if hasattr(h.sport, 'value') else str(h.sport),
                            "Selección": pick.get("selection", ""),
                            "Mercado": market,
                            "Línea": pick.get("line"),
                            "Cuota": odds,
                            "Cuota Cierre": closing_odds if closing_odds else "",   # placeholder CLV
                            "CLV (%)": clv_pct if clv_pct is not None else "",       # placeholder CLV
                            # ── Hit Rates básicos ──
                            "Hit Rate Local (%)": pick.get("home_hit_rate"),
                            "Hit Rate Visitante (%)": pick.get("away_hit_rate"),
                            "Hit Rate Total (%)": pick.get("empirical_hit_rate"),
                            "Hit Rate H2H (%)": pick.get("h2h_hit_rate"),
                            # ── Hit Rates de recencia (EWMA Bayesiano) ──
                            # Probabilidad suavizada con prior de liga + decaimiento exponencial
                            "HR Recencia Local (%)": pick.get("home_bayesian_ewma_hit_rate"),
                            "HR Recencia Visitante (%)": pick.get("away_bayesian_ewma_hit_rate"),
                            # Tendencia: improving / stable / deteriorating
                            "Tendencia Local": pick.get("home_trend_label"),
                            "Tendencia Visitante": pick.get("away_trend_label"),
                            # Delta en puntos porcentuales: recencia bayesiana vs. hit rate base
                            "Delta Tendencia Local (pp)": pick.get("home_trend_delta_pp"),
                            "Delta Tendencia Visitante (pp)": pick.get("away_trend_delta_pp"),
                            # Tamaño de muestra utilizado
                            "Muestra Local (n)": pick.get("home_matches_count"),
                            "Muestra Visitante (n)": pick.get("away_matches_count"),
                            # ── Probabilidades y criterios de selección ──
                            "Prob Calibrada (%)": float(pick.get("calibrated_prob", 0.0)) if pick.get("calibrated_prob") is not None else None,
                            "Prob Modelo (%)": float(pick.get("model_prob", 0.0)) if pick.get("model_prob") is not None else None,
                            "Edge Prob (%)": edge_prob,          # ANTES mal llamado "EV Edge (%)"
                            "EV Real (%)": ev_real_pct,          # AHORA sí es el EV real
                            "Fracción Kelly (%)": float(pick.get("kelly_fraction", 0.0)) * 100.0 if pick.get("kelly_fraction") is not None else None,
                            "Stake Sugerido (u)": pick.get("stake_units"),
                            "Resultado": success_str,
                            "Beneficio (u)": pick_profit if success is not None else None,
                            "Categoría": cat,
                            "Cuenta en Rentabilidad": "Sí" if getattr(h, "count_in_profitability", True) else "No"
                        })
            except Exception:
                pass

        # Fila agregada a nivel de partido (solo si hubo al menos un pick resuelto)
        if match_picks_resolved > 0:
            match_level_data.append({
                "ID Partido": h.id,
                "Fecha de Partido": h.match_date or h.date,
                "Partido": h.match_title,
                "Liga": league,
                "Picks Resueltos": match_picks_resolved,
                "Aciertos": match_hits,
                "% Acierto Partido": round(match_hits / match_picks_resolved * 100, 1) if match_picks_resolved else None,
                "Cuota Promedio Partido": round(sum(match_odds_list) / len(match_odds_list), 2) if match_odds_list else None,
                "Beneficio Neto Partido (u)": round(match_profit, 2),
                "Partido Ganador (Profit > 0)": match_profit > 0,
            })

    # ── DataFrames base ──
    global_accuracy = (total_hits / total_picks * 100) if total_picks > 0 else 0.0
    global_roi = (total_profit / total_staked_picks * 100) if total_staked_picks > 0 else 0.0
    global_avg_odds = (total_odds / total_picks) if total_picks > 0 else 0.0
    global_avg_winning_odds = (total_winning_odds / winning_picks_count) if winning_picks_count > 0 else 0.0
    exact_hit_rate = (total_exact_scores_hits / total_exact_scores_predicted * 100) if total_exact_scores_predicted > 0 else 0.0

    # ── NUEVO: Curva de equity y drawdown A NIVEL DE PARTIDO (clustering-adjusted) ──
    df_match_level = pd.DataFrame(match_level_data)
    df_equity, max_drawdown_u, max_drawdown_pct = build_equity_curve(
       df_match_level, bankroll_units=bankroll_units
    )

    # ── Test de significancia clustering-adjusted (a nivel de partido, no de pick) ──
    n_matches_clustered = len(df_match_level) if not df_match_level.empty else 0
    matches_won = int(df_match_level["Partido Ganador (Profit > 0)"].sum()) if not df_match_level.empty else 0
    match_level_winrate = round(matches_won / n_matches_clustered * 100, 1) if n_matches_clustered > 0 else 0.0

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
        {"Métrica": "── Análisis ajustado por clustering (a nivel de partido) ──", "Valor": ""},
        {"Métrica": "Partidos con picks resueltos", "Valor": n_matches_clustered},
        {"Métrica": "Partidos netos ganadores (%)", "Valor": match_level_winrate},
        {"Métrica": "Bankroll Base Asumido (u)", "Valor": bankroll_units},
        {"Métrica": "Máximo Drawdown (unidades)", "Valor": round(max_drawdown_u, 2)},
        {"Métrica": "Máximo Drawdown (%)", "Valor": round(max_drawdown_pct, 2)},
        {"Métrica": "Nota CLV", "Valor": "No disponible aún — columnas 'Cuota Cierre' y 'CLV (%)' quedan listas para cuando se implemente la captura de cuota de cierre."},
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

    # ── Escribir Excel ──
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_summary_general.to_excel(writer, sheet_name="Resumen", index=False, startrow=1)
        df_summary_categories.to_excel(writer, sheet_name="Resumen", index=False, startrow=len(summary_general_rows) + 3)

        df_matches.to_excel(writer, sheet_name="Partidos Analizados", index=False)
        df_picks.to_excel(writer, sheet_name="Detalle de Picks", index=False)
        df_leagues.to_excel(writer, sheet_name="Rentabilidad por Liga", index=False)
        df_markets.to_excel(writer, sheet_name="Rentabilidad por Mercado", index=False)

        # NUEVO: análisis clustering-adjusted (a nivel de partido)
        df_match_level.to_excel(writer, sheet_name="Análisis por Partido", index=False)
        df_equity.to_excel(writer, sheet_name="Curva de Equity", index=False)

        workbook = writer.book

        resumen_ws = workbook["Resumen"]
        resumen_ws["A1"] = "Estadísticas Generales Sherlock"
        resumen_ws["A1"].font = openpyxl.styles.Font(size=14, bold=True)
        cat_header_row = len(summary_general_rows) + 3
        resumen_ws[f"A{cat_header_row}"] = "Desglose por Categoría"
        resumen_ws[f"A{cat_header_row}"].font = openpyxl.styles.Font(size=14, bold=True)

        for sheet_name in workbook.sheetnames:
            ws = workbook[sheet_name]
            for col in ws.columns:
                max_len = 0
                for cell in col:
                    if cell.value:
                        if sheet_name == "Resumen" and cell.coordinate in ["A1", f"A{cat_header_row}"]:
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
                
                # Fallback for old picks that might only have is_value
                if not is_pub and not is_und:
                    if pick.get("is_value", False):
                        is_pub = True
                        
                if not (is_pub or is_und):
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
    
    # 1X2 / Winner (Common for all sports)
    if sel == "local":
        if h_score is not None and a_score is not None: return h_score > a_score
    if sel == "empate":
        if h_score is not None and a_score is not None: return h_score == a_score
    if sel == "visitante":
        if h_score is not None and a_score is not None: return a_score > h_score



    # Doble Oportunidad
    # IMPORTANT: usar lookahead/lookbehind negativo para evitar que "12" dentro de
    # un número como "12.5" (ej. "Over 12.5 Corners") dispare el check de Doble Oportunidad.
    # \b12\b FALLA porque el punto '.' es word boundary; la solución correcta es:
    # (?<!\d)12(?!\d|\.)  ->  "12" no precedido ni seguido de dígito o punto.
    import re as _re
    if "doble oportunidad 1x" in sel or "dc 1x" in sel or bool(_re.search(r'(?<!\w)1x(?!\w)', sel)):
        if h_score is not None and a_score is not None:
            return h_score >= a_score
    if "doble oportunidad x2" in sel or "dc x2" in sel or bool(_re.search(r'(?<!\w)x2(?!\w)', sel)):
        if h_score is not None and a_score is not None:
            return a_score >= h_score
    if "doble oportunidad 12" in sel or "dc 12" in sel or bool(_re.search(r'(?<!\d)12(?!\d|\.)', sel)):
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
        relevant_picks = [p for p in picks if (p.get("is_value") or p.get("is_publishable") or p.get("is_underdog")) and not p.get("is_blacklisted")]
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
        
        # Verificar si hay algún resultado disponible (score, tarjetas, tiros, etc.)
        has_any_result = (
            res_dict.get("final_score_home") is not None
            or res_dict.get("final_yellow_cards_home") is not None
            or res_dict.get("final_shots_home") is not None
            or res_dict.get("final_shots_on_target_home") is not None
            or res_dict.get("final_corners_home") is not None
        )
        if has_any_result:
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
                        stake = _resolve_stake_from_pick(p)
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



class _SkipPriorParams(Exception):
    """
    Los parámetros retrospectivos no se pueden calcular sin contaminar los datos.

    Es una excepción de control y no un `return` silencioso para que el motivo
    quede registrado: un análisis sin estos parámetros es una degradación
    conocida, no un caso normal.
    """


# ═══════════════════════════════════════════════════════════════════════
# ENTRENAMIENTO DEL CALIBRADOR
# ═══════════════════════════════════════════════════════════════════════

class TrainRequest(BaseModel):
    """
    Petición de reentrenamiento.

    `records` se acepta y se ignora por compatibilidad con el llamador antiguo
    (`train_model_retrospective.py`), que enviaba un dataset preparado para el
    GLM. El calibrador actual extrae sus muestras directamente de los picks ya
    liquidados en la base de datos, así que un dataset externo no solo es
    innecesario: aceptarlo como fuente permitiría entrenar con datos que no han
    pasado por el cutoff temporal.
    """

    records: list | None = None
    prior_strength: float | None = None
    min_samples: float | None = None
    n_folds: int = 5
    limit: int | None = None
    until_date: str | None = None
    allow_missing_timestamp: bool = False
    force: bool = False
    dry_run: bool = False


@app.post("/api/v1/ml/train", tags=["ML"])
def train_calibrator_endpoint(req: TrainRequest, db: Session = Depends(get_db)):
    """
    Reentrena el calibrador de probabilidades y publica el artefacto.

    Esta ruta faltaba: `src/core/train_model_retrospective.py` la invocaba y
    recibía 404, de modo que el pipeline de entrenamiento estaba roto de punta a
    punta.

    Reemplaza al entrenamiento GLM previsto originalmente. El calibrador es la
    Beta-Binomial jerárquica con isotónica PAVA, y solo se promueve el artefacto
    si mejora Brier Y log loss fuera de muestra: un reentrenamiento no puede
    empeorar el sistema por el simple hecho de haberse ejecutado.
    """
    from src.core.train_calibration import (
        DEFAULT_MIN_SAMPLES,
        DEFAULT_PRIOR_STRENGTH,
        run_training,
    )
    from src.ui.api.compare import reset_calibrator_cache

    try:
        report = run_training(
            prior_strength=req.prior_strength if req.prior_strength is not None else DEFAULT_PRIOR_STRENGTH,
            min_samples=req.min_samples if req.min_samples is not None else DEFAULT_MIN_SAMPLES,
            n_folds=req.n_folds,
            limit=req.limit,
            until_date=req.until_date,
            require_timestamp=not req.allow_missing_timestamp,
            force=req.force,
            dry_run=req.dry_run,
            session=db,
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Fallo al entrenar el calibrador: {err}")

    if report.promoted and not req.dry_run:
        # El artefacto en disco cambió; invalidar la cache para que las
        # siguientes peticiones usen el calibrador nuevo sin reiniciar.
        reset_calibrator_cache()

    payload = report.as_dict()
    payload["summary"] = report.summary()
    payload["ignored_records"] = len(req.records or [])
    return payload

if __name__ == "__main__":

    liga = "Primera Nacional"

    #----------Contar equipos de liga--------------------------------

    # db = next(get_db())

    # try:
    #     resultado = list_teams_count(liga, db)
    #     print(resultado)
    # finally:
    #     db.close()

    
    ##---------Cambiar nombre de liga---------------
    old_name = "Liga 1"
    new_name = "Liga 1 Te Apuesto"
    
    db = next(get_db())
    try:
        resultado = rename_competition_matches(old_name, new_name, db)
        print(resultado)
    finally:
        db.close()

    ##---------Eliminar liga--------------------------------

    # del_comp = "Bundesliga, Relegation/Promotion Playoffs"
    
    # db = next(get_db())
    # try:
    #     resultado = delete_competition_matches(del_comp, db)
    #     print(resultado)
    # finally:
    #     db.close()

    #------------------Eliminar duplicados-------------------

    # db = next(get_db())
    # try:
    #     resultado = deduplicate_competition_matches(liga, db)
    #     print(resultado)
    # finally:
    #     db.close()

    # -----------------Eliminar partidos--------------------
    # db = next(get_db())
    # try:
    #     resultado = delete_incomplete_competition_matches("HNL", dry_run=False, db=db)
    #     print(resultado)
    # finally:
    #     db.close()

    #----------Renombra equipos de una liga especifica---------------
    # db = next(get_db())
    # try:
                       
    #     # Puedes ir encadenando las demás correcciones usando kwargs:
    #     rename_team_matches(old_name="Técnico", new_name="Técnico U.", competition=liga, db=db)

    #     print("Equipos renombrados exitosamente.")
        
    # finally:
    #     db.close()