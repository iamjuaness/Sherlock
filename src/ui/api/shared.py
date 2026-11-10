"""Helpers y estado compartido de la API (extraídos de main.py)."""

from __future__ import annotations
from typing import Any

from datetime import datetime
from typing import Optional
import json
import asyncio
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import or_
from src.core.domain import Sport, AnalysisHistory
from src.core.entity_resolver import competition_filter
from src.ui.api.schemas import (
    AnalysisHistoryOut,
)
from src.ui.api.compare_models import FootballCompareRequest, CompareResponse
from src.core.prediction.score_matrix import split_asian_line
from fastapi.templating import Jinja2Templates
import os
import pandas as pd
import time
from threading import Lock
from typing import List


_API_DIR = os.path.dirname(__file__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
MAX_STAKE = 3
MIN_STAKE = 1
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
        picks = (
            json.loads(picks_calculados) if isinstance(picks_calculados, str) else picks_calculados
        )
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


_SEASON_STARTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "season_starts.json"
)
_SEASON_STARTS_CACHE: dict | None = None


def _load_season_starts() -> dict:
    global _SEASON_STARTS_CACHE
    if _SEASON_STARTS_CACHE is None:
        try:
            abs_path = os.path.abspath(_SEASON_STARTS_PATH)
            with open(abs_path, "r", encoding="utf-8") as f:
                _SEASON_STARTS_CACHE = json.load(f)
        except Exception:
            _SEASON_STARTS_CACHE = {}
    return _SEASON_STARTS_CACHE


def get_season_start(
    competition: str, season: str | None = None, tournament_id: str | int | None = None
) -> datetime | None:
    """
    Retorna la fecha de inicio real de la temporada para una competición.
    Usa season_starts.json (keyed por tournament_id o competition_name).
    Soporta temporadas tipo '2026' (calendar) y '2025/2026' o '25/26' (split).
    Fallback: None (el caller manejará el fallback a la fecha más antigua en DB).
    """
    import re

    starts = _load_season_starts()

    # Normalizar season: "25/26" → "2025/2026"
    if season:
        season = re.sub(r"^(\d{2})/(\d{2})$", lambda m: f"20{m.group(1)}/20{m.group(2)}", season)

    # Buscar entrada por tournament_id primero
    entry = None
    if tournament_id is not None:
        entry = starts.get(str(tournament_id))
    if entry is None:
        # Fallback: buscar por nombre de competición
        for v in starts.values():
            if v.get("competition_name", "").lower() == (competition or "").lower():
                entry = v
                break

    if entry is None:
        return None

    start_md = entry.get("start_month_day", "01-01")  # MM-DD
    season_type = entry.get("type", "calendar")

    try:
        month, day = [int(x) for x in start_md.split("-")]
    except Exception:
        return None

    # Determinar año de inicio
    if season_type == "calendar":
        # Año calendario: extraer primer año de la temporada
        years = re.findall(r"\d{4}", season or "")
        if years:
            year = int(years[0])
        else:
            year = datetime.utcnow().year
        return datetime(year, month, day)
    else:
        # Split season (ej. "2025/2026"): usa el primer año + mes/día de inicio
        years = re.findall(r"\d{4}", season or "")
        if years:
            year = int(years[0])
        else:
            year = datetime.utcnow().year
        return datetime(year, month, day)


def _compute_league_season_corners(
    competition: str,
    season: str | None = None,
    db_session: Session | None = None,
    tournament_id: str | int | None = None,
) -> float | None:
    """
    Calcula el promedio de córners por partido para una liga y temporada,
    usando sólo partidos a partir de la fecha real de inicio de la temporada
    (según season_starts.json). Excluye partidos sin corners del denominador.
    """
    if not competition or competition in ("", "Desconocida", "General"):
        return None

    import re
    from src.core.database import SessionLocal

    db_created = False
    s = db_session
    if s is None:
        s = SessionLocal()
        db_created = True

    try:
        q = s.query(
            AnalysisHistory.final_corners_home,
            AnalysisHistory.final_corners_away,
            AnalysisHistory.match_date,
            AnalysisHistory.date,
        ).filter(
            competition_filter(s, competition),
            AnalysisHistory.sport == Sport.FOOTBALL,
            AnalysisHistory.final_corners_home.isnot(None),
            AnalysisHistory.final_corners_away.isnot(None),
        )

        years = re.findall(r"\d{4}", str(season)) if season else []
        corner_totals: list[float] = []

        # Obtener la fecha real de inicio de la temporada
        season_start_dt = get_season_start(competition, season, tournament_id)

        if years:
            target_year = years[-1]
            q_season = q.filter(
                or_(
                    AnalysisHistory.date.like(f"{target_year}%"),
                    AnalysisHistory.match_date.like(f"{target_year}%"),
                    AnalysisHistory.season_label == target_year,
                    AnalysisHistory.season_year.like(f"{target_year}%"),
                )
            ).order_by(AnalysisHistory.date.desc())
            rows = q_season.all()
            # Filtrar por fecha real de inicio si disponible
            for r in rows:
                if r[0] is None or r[1] is None:
                    continue
                if season_start_dt is not None:
                    rec_date = r[2] or r[3]  # match_date, date
                    if rec_date is not None:
                        if isinstance(rec_date, str):
                            try:
                                rec_date = datetime.fromisoformat(rec_date.replace("Z", "+00:00"))
                            except Exception:
                                rec_date = None
                        if rec_date and rec_date.replace(tzinfo=None) < season_start_dt:
                            continue  # anterior al inicio real de temporada
                corner_totals.append(float(r[0]) + float(r[1]))

        # Si no hubo suficientes muestras por temporada o no se especificó temporada,
        # fallback a los últimos 200 partidos de la liga
        if len(corner_totals) < 8:
            if season_start_dt is not None:
                q_fallback = q.order_by(AnalysisHistory.date.desc()).limit(500)
            else:
                q_fallback = q.order_by(AnalysisHistory.date.desc()).limit(200)
            rows = q_fallback.all()
            corner_totals = []
            for r in rows:
                if r[0] is None or r[1] is None:
                    continue
                if season_start_dt is not None:
                    rec_date = r[2] or r[3]
                    if rec_date is not None:
                        if isinstance(rec_date, str):
                            try:
                                rec_date = datetime.fromisoformat(rec_date.replace("Z", "+00:00"))
                            except Exception:
                                rec_date = None
                        if rec_date and rec_date.replace(tzinfo=None) < season_start_dt:
                            continue
                corner_totals.append(float(r[0]) + float(r[1]))

        if len(corner_totals) >= 8:
            computed_avg = sum(corner_totals) / len(corner_totals)
            if 5.0 <= computed_avg <= 16.0:
                return round(computed_avg, 2)
        return None
    except Exception as exc:
        print(
            f"[Sherlock] Error calculando avg_corners_per_game para {competition} ({season}): {exc}"
        )
        return None
    finally:
        if db_created and s is not None:
            try:
                s.close()
            except Exception:
                pass


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
        "home": raw.get("home"),
        "draw": raw.get("draw"),
        "away": raw.get("away"),
        "btts_yes": raw.get("btts_yes"),
        "btts_no": raw.get("btts_no"),
        "dc_1x": raw.get("dc_1x"),
        "dc_x2": raw.get("dc_x2"),
        "dc_12": raw.get("dc_12"),
        # Lines (kept as snake_case — comparator reads goals_lines etc.)
        "goals_lines": _to_float_list(raw.get("goals_lines", [])),
        "corners_lines": _to_float_list(raw.get("corners_lines", [])),
        "cards_lines": _to_float_list(raw.get("cards_lines", [])),
        "shots_lines": _to_float_list(raw.get("shots_lines", [])),
        "shots_target_lines": _to_float_list(raw.get("shots_target_lines", [])),
        # Odds dicts — converted to camelCase for comparator.js
        "goalsOverOdds": _to_float_dict(raw.get("goals_over", {})),
        "goalsUnderOdds": _to_float_dict(raw.get("goals_under", {})),
        "cornersOverOdds": _to_float_dict(raw.get("corners_over", {})),
        "cornersUnderOdds": _to_float_dict(raw.get("corners_under", {})),
        "cardsOverOdds": _to_float_dict(raw.get("cards_over", {})),
        "cardsUnderOdds": _to_float_dict(raw.get("cards_under", {})),
        "shotsOverOdds": _to_float_dict(raw.get("shots_over", {})),
        "shotsUnderOdds": _to_float_dict(raw.get("shots_under", {})),
        "shotsTargetOverOdds": _to_float_dict(raw.get("shots_target_over", {})),
        "shotsTargetUnderOdds": _to_float_dict(raw.get("shots_target_under", {})),
    }

    # Derive over_25 / under_25 / over_15 / under_15 for legacy fields
    go = normalized["goalsOverOdds"]
    gu = normalized["goalsUnderOdds"]
    normalized["over_25"] = go.get("2.5")
    normalized["under_25"] = gu.get("2.5")
    normalized["over_15"] = go.get("1.5")
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
        ("goalsOverOdds", "goals_over_odds"),
        ("goalsUnderOdds", "goals_under_odds"),
        ("cornersOverOdds", "corners_over_odds"),
        ("cornersUnderOdds", "corners_under_odds"),
        ("cardsOverOdds", "cards_over_odds"),
        ("cardsUnderOdds", "cards_under_odds"),
        ("shotsOverOdds", "shots_over_odds"),
        ("shotsUnderOdds", "shots_under_odds"),
        ("shotsTargetOverOdds", "shots_target_over_odds"),
        ("shotsTargetUnderOdds", "shots_target_under_odds"),
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
            ("shots_target_lines", "shotsTargetLines"),
        ]:
            incoming_lines = odds.get(snake_k) or odds.get(camel_k) or []
            if not incoming_lines:
                continue
            merged = set(best.get(snake_k, [])) | set(incoming_lines)
            best[snake_k] = sorted(merged)

    return {"odds_update": best, "bookmaker_map": bookmaker_map}


def _annotate_best_bookmaker(
    res: CompareResponse, bookmaker_map: dict, home_name: str, away_name: str
) -> None:
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
        ("goals_over_odds", "Over {line} Goles"),
        ("goals_under_odds", "Under {line} Goles"),
        ("corners_over_odds", "Over {line} Corners"),
        ("corners_under_odds", "Under {line} Corners"),
        ("cards_over_odds", "Over {line} Tarjetas"),
        ("cards_under_odds", "Under {line} Tarjetas"),
        ("shots_over_odds", "Over {line} Tiros"),
        ("shots_under_odds", "Under {line} Tiros"),
        ("shots_target_over_odds", "Over {line} Tiros a Pta"),
        ("shots_target_under_odds", "Under {line} Tiros a Pta"),
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

    # #51: Maldición del ganador (Winner's Curse)
    # Al escoger la mejor cuota entre K casas, la cuota máxima tiende a sobreestimar el valor por ruido estadístico.
    # Descontamos incertidumbre: discount = 0.01 / sqrt(n_sources) sobre EV y edge.
    n_sources = len(bookmaker_map) if bookmaker_map else 0
    # Si hay múltiples casas mapeadas
    has_shopping = (
        any(isinstance(v, dict) and len(v) > 1 for v in bookmaker_map.values())
        or len(bookmaker_map) > 1
    )

    for v in res.values:
        bk = label_to_bookmaker.get(v.selection)
        if bk:
            v.bookmaker = bk
            if has_shopping:
                # Descuento del ganador: 0.5% - 1.0% de edge/EV por incertidumbre de selección de cuota extrema
                # 0.0075 = 0.75 puntos porcentuales de penalización en edge_ev
                curse_discount = 0.0075
                if v.edge_ev is not None:
                    v.edge_ev = round(max(0.0, v.edge_ev - curse_discount), 3)
                if v.edge is not None:
                    v.edge = round(max(0.0, v.edge - (curse_discount * 100.0)), 2)


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
        dict_over = (
            normalized_odds.get("shotsTargetOverOdds", {})
            if is_target
            else normalized_odds.get("shotsOverOdds", {})
        )
        dict_under = (
            normalized_odds.get("shotsTargetUnderOdds", {})
            if is_target
            else normalized_odds.get("shotsUnderOdds", {})
        )
        if is_over:
            val = dict_over.get(line_str) or dict_over.get(str(line))
            return float(val) if val else None
        elif is_under:
            val = dict_under.get(line_str) or dict_under.get(str(line))
            return float(val) if val else None

    # 6. BTTS / Ambos anotan
    if "ambos" in market or "btts" in market:
        if "sí" in selection or "yes" in selection or "si" in selection:
            return (
                float(normalized_odds.get("btts_yes")) if normalized_odds.get("btts_yes") else None
            )
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


async def _enrich_with_results(
    sport: Sport,
    home: str,
    away: str,
    response: CompareResponse,
    db: Session,
    match_date: Optional[str] = None,
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
                (
                    (AnalysisHistory.match_date >= date_start)
                    & (AnalysisHistory.match_date <= date_end)
                )
                | (
                    (AnalysisHistory.match_date == None)
                    & (AnalysisHistory.date >= date_start)
                    & (AnalysisHistory.date <= date_end)
                )
            ),
        )
        .order_by(AnalysisHistory.date.desc())
        .first()
    )

    # 2. Si no hay exacto, buscar con ambos nombres pero respetando orden + fecha cercana
    if not history:
        from sqlalchemy import and_, or_
        from src.core.entity_resolver import find_team_id

        _hid, _aid = find_team_id(db, home), find_team_id(db, away)
        if _hid and _aid:
            _teams_filter = or_(
                and_(AnalysisHistory.home_team_id == _hid, AnalysisHistory.away_team_id == _aid),
                and_(AnalysisHistory.home_team_id == _aid, AnalysisHistory.away_team_id == _hid),
            )
        else:
            _teams_filter = and_(
                AnalysisHistory.match_title.ilike(f"%{home}%"),
                AnalysisHistory.match_title.ilike(f"%{away}%"),
            )
        candidates = (
            db.query(AnalysisHistory)
            .filter(
                AnalysisHistory.sport == sport,
                _teams_filter,
                AnalysisHistory.final_score_home != None,
                (
                    (
                        (AnalysisHistory.match_date >= date_start)
                        & (AnalysisHistory.match_date <= date_end)
                    )
                    | (
                        (AnalysisHistory.match_date == None)
                        & (AnalysisHistory.date >= date_start)
                        & (AnalysisHistory.date <= date_end)
                    )
                ),
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


async def _call_llm_for_result(sport: str, result: CompareResponse, request) -> str:
    """Llama al LLM usando las funciones internas de compare.py sin importarlas."""
    from src.ui.api.compare_service import generate_football_analysis

    vp = [v for v in result.values if v.is_value]
    user_context = getattr(request, "user_context", "") or ""

    if sport == "football":
        return await generate_football_analysis(
            request.home,
            request.away,
            vp,
            result.projected_lines,
            request.league_stats,
            request.competition,
            user_context,
        )

    return "⚠️ No se pudo encontrar el generador de análisis LLM."


async def _sse_stream(sport: str, request, compare_fn):
    """Generador SSE genérico: calcula resultado + llama LLM + hace streaming."""

    async def event_generator():
        try:
            result = await compare_fn(request)
            text = await _call_llm_for_result(sport, result, request)
            chunk_size = 60
            for i in range(0, len(text), chunk_size):
                yield f"data: {json.dumps({'chunk': text[i : i + chunk_size]})}\n\n"
                await asyncio.sleep(0.01)
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class RenameCompetitionRequest(BaseModel):
    new_name: str


class SeasonAuditPayload(BaseModel):
    season_id: int | str
    competition: str | None = None
    total_sofascore: int
    total_db: int
    total_sofascore_all: int | None = None  # total_sofascore = solo terminados
    db_with_result: int | None = None
    db_without_result: int | None = None
    pending_not_due: int | None = None  # sin resultado y empezaron hace < 2 h
    missing_in_db: list[Any] = []
    extra_in_db: list[Any] = []


# ---------------------------------------------------------------------------
# Pick Rules & Profitable Leagues
# ---------------------------------------------------------------------------
PICK_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "pick_rules.json"
)
PROFITABLE_LEAGUES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "data", "profitable_leagues.json"
)


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


class BlacklistMarketRequest(BaseModel):
    league: str
    market_name: str


class BlacklistMarketsBatchRequest(BaseModel):
    league: str
    markets: List[str]


class SegmentGovernanceActionRequest(BaseModel):
    league: str
    market_name: str
    action: str  # "block", "reduce", "reset"
    stake_multiplier: Optional[float] = None


class SegmentGovernanceBatchActionRequest(BaseModel):
    league: str
    markets: List[str]
    action: str  # "block", "reduce", "reset"
    stake_multiplier: Optional[float] = None


def _update_segment_governance_file(
    league: str, market_name: str, action: str, stake_multiplier: Optional[float] = None
) -> str:
    """Actualiza data/segment_governance.json para un mercado o segmento determinado."""
    from src.domain.market_taxonomy import parse_market
    from src.ui.api.compare import reset_governance_cache

    gov_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "segment_governance.json"
    )

    parsed = parse_market(market_name)
    clean_league = league.strip().lower()

    # Claves candidatas a registrar en segment_governance
    keys_to_update = []
    if parsed.line_bucket and parsed.line_bucket != "no_line":
        keys_to_update.append(
            f"league:{clean_league}|family:{parsed.family}|side:{parsed.side}|bucket:{parsed.line_bucket}"
        )
    if parsed.side and parsed.side != "generic":
        keys_to_update.append(f"league:{clean_league}|family:{parsed.family}|side:{parsed.side}")
    keys_to_update.append(f"league:{clean_league}|family:{parsed.family}")

    # Elegimos la clave más específica
    target_key = keys_to_update[0]

    data = {}
    if os.path.exists(gov_path) and os.path.getsize(gov_path) > 0:
        # Sin try/except: un archivo corrupto no debe reemplazarse por uno casi vacío.
        with open(gov_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    if "segments" not in data or not isinstance(data["segments"], dict):
        data["segments"] = {}
    if "segment_meta" not in data or not isinstance(data["segment_meta"], dict):
        data["segment_meta"] = {}

    action_lower = action.lower()
    if action_lower in ["block", "blocked"]:
        data["segments"][target_key] = "blocked"
        data["segment_meta"][target_key] = {
            "source": "manual_governance",
            "market_name": market_name,
        }
    elif action_lower in ["reduce", "reduced"]:
        data["segments"][target_key] = "reduced"
        data["segment_meta"][target_key] = {
            "source": "manual_governance",
            "market_name": market_name,
            "stake_multiplier": stake_multiplier if stake_multiplier is not None else 0.25,
        }
    elif action_lower in ["reset", "active"]:
        data["segments"].pop(target_key, None)
        data["segment_meta"].pop(target_key, None)

    # Actualizar conteos
    counts = {"active": 0, "watch": 0, "reduced": 0, "blocked": 0, "experimental": 0}
    for st in data["segments"].values():
        st_low = str(st).lower()
        if st_low in counts:
            counts[st_low] += 1
    data["status_counts"] = counts
    data["total_segments"] = len(data["segments"])

    os.makedirs(os.path.dirname(gov_path), exist_ok=True)
    tmp_path = gov_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, gov_path)  # escritura atómica

    reset_governance_cache()
    return target_key


def _normalize_blacklist_line(value):
    """
    Devuelve una cadena numérica canónica o None si no hay línea.

    Ejemplos:
    11.5    -> "11.5"
    "11.50" -> "11.5"
    "11,5"  -> "11.5"
    0       -> "0"
    None    -> None
    ""      -> None
    """
    from decimal import Decimal, InvalidOperation

    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError("La línea no puede ser un booleano.")

    text = str(value).strip().replace(",", ".")

    if not text:
        return None

    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Línea de mercado inválida: {value!r}") from exc

    if not number.is_finite():
        raise ValueError(f"Línea de mercado inválida: {value!r}")

    if number == 0:
        return "0"

    normalized = format(number, "f")

    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")

    return normalized


class ReduceStakeMarketRequest(BaseModel):
    league: str
    market_name: str
    stake_modifier: float = 0.5


class RuleSimulationRequest(BaseModel):
    market_family: str
    market_side: str
    conditions: list[dict]


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
    if any(k in s for k in ["over", "under", "más de", "menos de"]) and any(
        k in s for k in ["gol", "goles", "goal", "goals"]
    ):
        return "Goles: Over/Under"
    if any(k in s for k in ["double chance", "doble oportunidad", "1x", "x2", "12"]):
        return "Doble Oportunidad"
    if s in ["local", "visitante", "empate", "home", "away", "draw"] or any(
        k in s for k in ["moneyline", "ml", "1x2", "ganador"]
    ):
        return "1x2"
    if any(k in s for k in ["gol", "goles", "goal", "goals"]):
        return "Goles: Over/Under"
    return "Otros"


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
        drawdown_pct = (
            (drawdown_u / running_max_bankroll * 100.0) if running_max_bankroll > 0 else 0.0
        )

        equity_rows.append(
            {
                "Fecha": row["Fecha de Partido"].strftime("%Y-%m-%d"),
                "Partido": row["Partido"],
                "Beneficio Partido (u)": row["Beneficio Neto Partido (u)"],
                "Profit Acumulado (u)": round(cumulative_profit, 2),
                "Bankroll Estimado (u)": round(bankroll_value, 2),
                "Máximo Bankroll Histórico (u)": round(running_max_bankroll, 2),
                "Drawdown (u)": round(drawdown_u, 2),
                "Drawdown (%)": round(drawdown_pct, 2),
            }
        )

        max_drawdown_u = min(max_drawdown_u, drawdown_u)
        max_drawdown_pct = min(max_drawdown_pct, drawdown_pct)

    return pd.DataFrame(equity_rows), max_drawdown_u, max_drawdown_pct


def _check_projected_line_success(
    p_line: dict, res: dict, home_name: str, away_name: str
) -> bool | None:
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

    elif (
        t in ("shots_target", "shots_target_team")
        or "pta" in label
        or "target" in label
        or "puerta" in label
    ):
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

    elif (
        t in ("offsides", "offsides_team")
        or "offsides" in label
        or "fuera de juego" in label
        or "fueras" in label
    ):
        h_o = res.get("final_offsides_home")
        a_o = res.get("final_offsides_away")
        if (
            "totales" in label
            or "offsides totales" in label
            or "fuera de juego totales" in label
            or "fueras de juego totales" in label
        ):
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


def _calculate_pick_profit(outcome: PickOutcome, odds: float, stake: float = 1.0) -> float:
    """Calcula beneficio en unidades (por defecto stake plano de 1u)."""
    if outcome is None:
        return 0.0
    if outcome is True:
        unit_profit = odds - 1.0
    elif outcome is False:
        unit_profit = -1.0
    elif outcome == "void":
        unit_profit = 0.0
    elif outcome == "half_win":
        unit_profit = (odds - 1.0) / 2.0
    elif outcome == "half_loss":
        unit_profit = -0.5
    else:
        unit_profit = 0.0
    return unit_profit * stake


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
        if h_score is not None and a_score is not None:
            return h_score > a_score
    if sel == "empate":
        if h_score is not None and a_score is not None:
            return h_score == a_score
    if sel == "visitante":
        if h_score is not None and a_score is not None:
            return a_score > h_score

    # Doble Oportunidad
    # IMPORTANT: usar lookahead/lookbehind negativo para evitar que "12" dentro de
    # un número como "12.5" (ej. "Over 12.5 Corners") dispare el check de Doble Oportunidad.
    # \b12\b FALLA porque el punto '.' es word boundary; la solución correcta es:
    # (?<!\d)12(?!\d|\.)  ->  "12" no precedido ni seguido de dígito o punto.
    import re as _re

    if "doble oportunidad 1x" in sel or "dc 1x" in sel or bool(_re.search(r"(?<!\w)1x(?!\w)", sel)):
        if h_score is not None and a_score is not None:
            return h_score >= a_score
    if "doble oportunidad x2" in sel or "dc x2" in sel or bool(_re.search(r"(?<!\w)x2(?!\w)", sel)):
        if h_score is not None and a_score is not None:
            return a_score >= h_score
    if (
        "doble oportunidad 12" in sel
        or "dc 12" in sel
        or bool(_re.search(r"(?<!\d)12(?!\d|\.)", sel))
    ):
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
        if h_score is not None and a_score is not None:
            return h_score > 0 and a_score > 0
    if "btts no" in sel:
        if h_score is not None and a_score is not None:
            return h_score == 0 or a_score == 0

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
    h_y_raw = res.get("final_yellow_cards_home")
    a_y_raw = res.get("final_yellow_cards_away")
    h_r_raw = res.get("final_red_cards_home")
    a_r_raw = res.get("final_red_cards_away")
    has_card_data = any(x is not None for x in (h_y_raw, a_y_raw, h_r_raw, a_r_raw))
    h_y = h_y_raw or 0
    a_y = a_y_raw or 0
    h_r = h_r_raw or 0
    a_r = a_r_raw or 0
    total_cards = (h_y + a_y) + ((h_r + a_r) * 2) if has_card_data else None
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
    except:
        pass
    return None


def _populate_history_extra_fields(
    h: AnalysisHistory, out: AnalysisHistoryOut, use_stake: bool = False
) -> AnalysisHistoryOut:
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
        relevant_picks = [
            p
            for p in picks
            if (p.get("is_value") or p.get("is_publishable") or p.get("is_underdog"))
            and not p.get("is_blacklisted")
        ]
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
                    pick_profit = (
                        _calculate_pick_profit(success, float(p.get("odds") or 0.0)) * stake
                    )
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
                            p_line["success"] = _check_projected_line_success(
                                p_line, res_dict, home_name, away_name
                            )

    except Exception as e:
        print(f"Error populating history extra fields: {e}")
        out.has_picks = False

    return out


class _SkipPriorParams(Exception):
    """
    Los parámetros retrospectivos no se pueden calcular sin contaminar los datos.

    Es una excepción de control y no un `return` silencioso para que el motivo
    quede registrado: un análisis sin estos parámetros es una degradación
    conocida, no un caso normal.
    """


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
