"""
src/core/parallel_recalc.py

Módulo worker para paralelizar el endpoint /api/v1/analysis/recalculate-all
con ProcessPoolExecutor sin importar main.py (compatible con spawn en Windows).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Union

from src.core.domain import Sport
from src.core.pick_rules_engine import evaluate_pick_rules, StatSource
from src.ui.api.compare import (
    compare_football,
    FootballCompareRequest,
    CompareResponse,
    split_asian_line,
)


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

PickOutcome = Union[bool, str, None]


def split_into_chunks(items: list, n_workers: int) -> list[list]:
    """Reparte la lista de ítems en n_workers sublistas de tamaño similar."""
    if n_workers <= 0:
        n_workers = 1
    if not items:
        return []
    
    k, m = divmod(len(items), n_workers)
    chunks = []
    start = 0
    for i in range(n_workers):
        length = k + (1 if i < m else 0)
        if length > 0:
            chunks.append(items[start : start + length])
            start += length
    return chunks


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


def _apply_line_shopping(request: FootballCompareRequest) -> tuple[FootballCompareRequest, dict]:
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


def _annotate_best_bookmaker(res: CompareResponse, bookmaker_map: dict, home_name: str, away_name: str) -> None:
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


def _combine_split_outcomes(results: list[str]) -> PickOutcome:
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


def _extract_line(text: str, prefix: str) -> float | None:
    try:
        parts = text.split(prefix)
        if len(parts) > 1:
            match = re.search(r"(\d+(\.\d+)?)", parts[1])
            if match:
                return float(match.group(1))
    except Exception:
        pass
    return None


def _resolve_ou_outcome(total: float | None, line: float | None, side: str) -> PickOutcome:
    if total is None or line is None:
        return None
    lines = split_asian_line(line)
    results = [_settle_total_line(total, l, side) for l in lines]
    return _combine_split_outcomes(results)


def _is_pick_hit(outcome: PickOutcome) -> bool:
    return outcome is True or outcome == "half_win"


def _check_pick_success(pick: dict, res: dict) -> PickOutcome:
    sel = pick.get("selection", "").lower()
    h_score = res.get("final_score_home")
    a_score = res.get("final_score_away")
    
    if sel == "local":
        if h_score is not None and a_score is not None: return h_score > a_score
    if sel == "empate":
        if h_score is not None and a_score is not None: return h_score == a_score
    if sel == "visitante":
        if h_score is not None and a_score is not None: return a_score > h_score

    if "doble oportunidad 1x" in sel or "dc 1x" in sel or "1x" in sel:
        if h_score is not None and a_score is not None:
            return h_score >= a_score
    if "doble oportunidad x2" in sel or "dc x2" in sel or "x2" in sel:
        if h_score is not None and a_score is not None:
            return a_score >= h_score
    if "doble oportunidad 12" in sel or "dc 12" in sel or "12" in sel:
        if h_score is not None and a_score is not None:
            return h_score != a_score

    if "puntos" in sel or "points" in sel or "juegos" in sel or "games" in sel:
        total_p = (h_score + a_score) if (h_score is not None and a_score is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            return _resolve_ou_outcome(total_p, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_p, line, "under")

    if "btts sí" in sel or "btts yes" in sel:
        if h_score is not None and a_score is not None: return h_score > 0 and a_score > 0
    if "btts no" in sel:
        if h_score is not None and a_score is not None: return h_score == 0 or a_score == 0

    if "goles" in sel or "goals" in sel:
        total_g = (h_score + a_score) if (h_score is not None and a_score is not None) else None
        if "over" in sel:
            line = _extract_line(sel, "over")
            return _resolve_ou_outcome(total_g, line, "over")
        if "under" in sel:
            line = _extract_line(sel, "under")
            return _resolve_ou_outcome(total_g, line, "under")

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


def _recalc_chunk(chunk_data: dict) -> list[dict]:
    """
    Procesa un chunk de partidos en un proceso secundario (worker).
    """
    matches = chunk_data.get("matches", [])
    shared_historical_records = chunk_data.get("shared_historical_records", [])
    use_general_stats = chunk_data.get("use_general_stats", False)
    threshold_dt_iso = chunk_data.get("threshold_dt_iso")
    enabled_rules = chunk_data.get("enabled_rules", [])

    threshold_dt = None
    if threshold_dt_iso:
        try:
            threshold_dt = datetime.fromisoformat(threshold_dt_iso)
        except Exception:
            pass

    # Reconstruir team_index para O(1) lookups
    team_index: dict[str, list] = {}
    for r in shared_historical_records:
        title = r.get("match_title", "") or ""
        comp = (r.get("competition") or "").strip().lower()
        ht = (r.get("home_team") or (title.split(" vs ")[0] if " vs " in title else "")).strip().lower()
        at = (r.get("away_team") or (title.split(" vs ")[1] if " vs " in title else "")).strip().lower()
        if ht:
            team_index.setdefault(ht, []).append(r)
            if comp:
                team_index.setdefault(f"{comp}::{ht}", []).append(r)
        if at:
            team_index.setdefault(at, []).append(r)
            if comp:
                team_index.setdefault(f"{comp}::{at}", []).append(r)

    results = []

    for match in matches:
        match_id = match["id"]
        payload_raw = match.get("payload")
        if not payload_raw:
            continue

        if not _check_payload_has_odds(payload_raw):
            results.append({
                "id": match_id,
                "has_odds": False,
                "skipped": True,
                "error": None
            })
            continue

        m_date = None
        m_date_str = match.get("match_date") or match.get("date")
        if m_date_str:
            if isinstance(m_date_str, datetime):
                m_date = m_date_str
            else:
                try:
                    m_date = datetime.fromisoformat(str(m_date_str))
                except Exception:
                    pass

        try:
            payload_dict = json.loads(str(payload_raw)) if isinstance(payload_raw, str) else dict(payload_raw)
            local_payload = dict(payload_dict)
            sport = match.get("sport") or local_payload.get("sport", "football")
            if isinstance(sport, Sport):
                sport_val = sport.value
            else:
                sport_val = str(sport).lower()

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

            if sport_val != "football":
                continue

            req = FootballCompareRequest(**local_payload)
            req, bookmaker_map = _apply_line_shopping(req)

            new_response = asyncio.run(
                compare_football(
                    req,
                    db=None,
                    exclude_match_id=match_id,
                    current_match_date=m_date,
                    precomputed_historical_records=shared_historical_records,
                    precomputed_team_index=team_index,
                )
            )

            if new_response:
                if bookmaker_map:
                    _annotate_best_bookmaker(new_response, bookmaker_map, req.home.name, req.away.name)

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

                picks_json = json.dumps(picks)
                snapshot_json = json.dumps(new_response.model_dump() if hasattr(new_response, 'model_dump') else new_response.__dict__)

                accuracy_percentage = None
                has_final_score = match.get("final_score_home") is not None
                if has_final_score and match.get("final_score_away") is not None:
                    results_dict = {
                        "final_score_home": match.get("final_score_home"),
                        "final_score_away": match.get("final_score_away"),
                        "final_corners_home": match.get("final_corners_home"),
                        "final_corners_away": match.get("final_corners_away"),
                        "final_yellow_cards_home": match.get("final_yellow_cards_home"),
                        "final_yellow_cards_away": match.get("final_yellow_cards_away"),
                        "final_red_cards_home": match.get("final_red_cards_home"),
                        "final_red_cards_away": match.get("final_red_cards_away"),
                        "final_shots_home": match.get("final_shots_home"),
                        "final_shots_away": match.get("final_shots_away"),
                        "final_shots_on_target_home": match.get("final_shots_on_target_home"),
                        "final_shots_on_target_away": match.get("final_shots_on_target_away"),
                        "final_fouls_home": match.get("final_fouls_home"),
                        "final_fouls_away": match.get("final_fouls_away"),
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
                    accuracy_percentage = (hits / total) * 100 if total > 0 else None

                results.append({
                    "id": match_id,
                    "picks_calculados": picks_json,
                    "compare_response_snapshot": snapshot_json,
                    "accuracy_percentage": accuracy_percentage,
                    "has_final_score": has_final_score,
                    "has_odds": True,
                    "skipped": False,
                    "error": None
                })
        except Exception as e:
            results.append({
                "id": match_id,
                "has_odds": True,
                "skipped": False,
                "error": str(e)
            })

    return results
