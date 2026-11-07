"""Rutas prefill de la API (extraídas de main.py)."""

from __future__ import annotations


from src.ui.api.shared import _compute_league_season_corners, _normalize_betano_odds
from fastapi import APIRouter

router = APIRouter()

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


@router.post("/api/v1/prefill", tags=["Prefill"])
async def push_prefill(payload: dict) -> dict:
    """
    Browser extension pushes a (partial) form payload here.
    The Sherlock dashboard polls this endpoint and auto-fills the form.
    Calcula los corners por partido de la liga/temporada y los inyecta en league_stats.
    """
    global prefill_store

    competition = payload.get("competition") or ""
    season = payload.get("season")
    tournament_id = payload.get("tournament_id")
    if not season and isinstance(payload.get("league_stats"), dict):
        season = payload["league_stats"].get("season")

    computed_corners = _compute_league_season_corners(
        competition, season, tournament_id=tournament_id
    )
    if computed_corners is not None:
        if not isinstance(payload.get("league_stats"), dict):
            payload["league_stats"] = {}
        payload["league_stats"]["avg_corners_per_game"] = computed_corners

    prefill_store = payload
    return {"status": "ok", "message": "Datos recibidos. Sherlock los cargará en el formulario."}


@router.post("/api/v1/prefill/odds", tags=["Prefill"])
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
            f"Cuotas de {bookmaker} recibidas ({len(prefill_odds_store)} casa(s) acumulada(s))."
        ),
        "home_team": raw_odds.get("home_team"),
        "away_team": raw_odds.get("away_team"),
        "bookmakers_received": list(prefill_odds_store.keys()),
    }


@router.get("/api/v1/prefill", tags=["Prefill"])
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


@router.get("/api/v1/prefill/odds", tags=["Prefill"])
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
