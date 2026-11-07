"""Rutas pick_rules de la API (extraídas de main.py)."""

from __future__ import annotations
from typing import Any

import json
from fastapi import Body, Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.domain import AnalysisHistory
import os

from src.ui.api.shared import PICK_RULES_PATH, RuleSimulationRequest
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/pick-rules", tags=["Pick Rules"])
def get_pick_rules():
    """Returns the list of configured pick rules."""
    try:
        if not os.path.exists(PICK_RULES_PATH):
            return []
        with open(PICK_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/v1/pick-rules", tags=["Pick Rules"])
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


@router.post("/api/v1/pick-rules/simulate", tags=["Pick Rules"])
def simulate_pick_rules(req: RuleSimulationRequest, db: Session = Depends(get_db)):
    """
    Evaluates proposed conditions on the historical database to see the success rate.
    """
    history_list = db.query(AnalysisHistory).all()
    matched_count = 0
    success_count = 0
    matched_matches = []

    from src.core.pick_rules_engine import StatSource, _OPERATORS

    def check_market_success(
        market_family: str, market_side: str, history: AnalysisHistory
    ) -> bool | None:
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
            total_yellow = (history.final_yellow_cards_home or 0) + (
                history.final_yellow_cards_away or 0
            )
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
            payload = (
                json.loads(str(history.payload))
                if isinstance(history.payload, str)
                else history.payload
            )
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

                matched_matches.append(
                    {
                        "id": str(history.id),
                        "date": history.match_date.isoformat()
                        if history.match_date
                        else (history.date.isoformat() if history.date else ""),
                        "title": history.match_title or "Partido desconocido",
                        "score": f"{history.final_score_home} - {history.final_score_away}"
                        if has_result
                        else "Pendiente",
                        "has_result": has_result,
                        "success": is_hit,
                    }
                )
        except Exception as err:
            print(f"Error simulando en partido {history.id}: {err}")

    accuracy = (success_count / matched_count * 100) if matched_count > 0 else 0.0
    return {
        "matched_count": matched_count,
        "success_count": success_count,
        "accuracy": round(accuracy, 1),
        "matches": matched_matches[:100],
    }


@router.post("/api/v1/analysis/apply-rules", tags=["Pick Rules"])
def apply_pick_rules(db: Session = Depends(get_db)):
    """
    Re-evaluates pick_rules.json against saved picks in the history.
    Blocks picks that violate enabled rules (marks is_rule_blocked=True, clears is_publishable/is_value).
    Also un-blocks picks for rules that are now disabled.
    """
    from src.ui.api.compare import (
        is_publishable_pick,
        is_value_pick,
        is_underdog_pick,
        score_pick_quality,
    )
    from src.ui.api.compare_models import ValueIndicator
    from src.core.pick_rules_engine import (
        evaluate_pick_rules,
        load_pick_rules_data,
        resolve_match_picks_correlation,
        StatSource,
    )

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
                            empirical_hit_rate=pick.get("empirical_hit_rate"),
                            home_hit_rate=pick.get("home_hit_rate"),
                            away_hit_rate=pick.get("away_hit_rate"),
                            hit_rate_samples=pick.get("hit_rate_samples", 0),
                            h2h_hit_rate=pick.get("h2h_hit_rate"),
                            h2h_raw_hit_rate=pick.get("h2h_raw_hit_rate"),
                            h2h_samples=pick.get("h2h_samples", 0) or 0,
                            h2h_hits=pick.get("h2h_hits"),
                            correlation_blocked=pick.get("correlation_blocked", False),
                            is_rule_blocked=False,
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
