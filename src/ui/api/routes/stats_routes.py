"""Rutas stats de la API (extraídas de main.py)."""

from __future__ import annotations

from datetime import datetime
import json
from fastapi.responses import StreamingResponse
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.domain import Sport, AnalysisHistory
from src.ui.api.schemas import (
    GlobalStatsOut,
    PickStat,
)
from src.ui.api.compare import _market_family
import io
import pandas as pd
import openpyxl
from openpyxl.utils import get_column_letter

from src.ui.api.shared import (
    MIN_STAKE,
    _calculate_pick_profit,
    _check_pick_success,
    _get_cache,
    _is_pick_hit,
    _resolve_stake_from_pick,
    _set_cache,
    build_equity_curve,
    get_market_name,
    is_league_profitable,
)
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/v1/stats/leagues", tags=["Stats"])
def get_leagues_stats(
    use_stake: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Groups AnalysisHistory by competition and calculates stats.
    Detailed markets are grouped by category, side and exact line.
    """
    import re
    from decimal import Decimal, InvalidOperation
    from sqlalchemy.orm import load_only

    # Nueva versión para no devolver los agregados antiguos sin línea.
    cache_key = f"leagues:market-lines-v1:{use_stake}"

    cached = _get_cache(cache_key)
    if cached:
        return cached

    def normalize_line(value):
        if value is None or isinstance(value, bool):
            return None

        text = str(value).strip().replace(",", ".")
        if not text:
            return None

        try:
            number = Decimal(text)
        except (InvalidOperation, ValueError):
            return None

        if not number.is_finite():
            return None

        if number == 0:
            return "0"

        result = format(number, "f")

        if "." in result:
            result = result.rstrip("0").rstrip(".")

        return result

    def build_market_key(pick):
        sel_text = str(pick.get("selection") or "").strip()
        lower_sel = sel_text.lower()

        category = ""

        # Detección de Tiros a Puerta vs Tiros
        is_shots_target = (
            "shot_target" in lower_sel
            or "shots_target" in lower_sel
            or "shots_on_target" in lower_sel
            or "tiro_a_puerta" in lower_sel
            or "tiros a puerta" in lower_sel
            or "tiro a puerta" in lower_sel
            or "tiros al arco" in lower_sel
            or "tiro al arco" in lower_sel
            or "remates a puerta" in lower_sel
            or "remates al arco" in lower_sel
            or "shots on target" in lower_sel
            or "tiros a pta" in lower_sel
            or "tiro a pta" in lower_sel
            or " a pta" in lower_sel
            or bool(re.search(r"\b(sot)\b", lower_sel))
        )

        # 1. Familias independientes para 1X2: Local, Empate, Visitante
        if lower_sel in ("empate", "draw") or re.search(r"\b(empate|draw)\b", lower_sel):
            return "Empate"
        elif (
            lower_sel in ("local", "home", "victoria local", "1")
            or lower_sel.startswith("local ")
            or lower_sel.endswith(" local")
            or re.search(r"\b(local|victoria local)\b", lower_sel)
        ):
            return "Local"
        elif (
            lower_sel in ("visitante", "away", "victoria visitante", "2")
            or lower_sel.startswith("visitante ")
            or lower_sel.endswith(" visitante")
            or re.search(r"\b(visitante|victoria visitante)\b", lower_sel)
        ):
            return "Visitante"

        # 2. Doble Oportunidad
        elif (
            "doble oportunidad" in lower_sel
            or "double chance" in lower_sel
            or re.search(r"\b(1x|x2|12)\b", lower_sel)
        ):
            category = "Doble Oportunidad"

        # 3. Resto de familias
        elif "corner" in lower_sel or "córner" in lower_sel:
            category = "Córners"
        elif "tarjeta" in lower_sel or "card" in lower_sel or "amarilla" in lower_sel:
            category = "Tarjetas"
        elif "foul" in lower_sel or "falta" in lower_sel:
            category = "Faltas"
        elif is_shots_target:
            category = "Tiros a puerta"
        elif "shot" in lower_sel or "tiro" in lower_sel or "remate" in lower_sel:
            category = "Tiros"
        elif (
            "btts" in lower_sel or "ambos marcan" in lower_sel or "both teams to score" in lower_sel
        ):
            category = "BTTS"
        elif (
            "gol" in lower_sel or "goal" in lower_sel or "over" in lower_sel or "under" in lower_sel
        ):
            category = "Goles"
        else:
            category = "Otros"

        # Lado (Side)
        side = ""
        if category == "BTTS":
            if (
                "yes" in lower_sel
                or "sí" in lower_sel
                or lower_sel == "si"
                or lower_sel.endswith(" si")
            ):
                side = "Sí"
            elif "no" in lower_sel:
                side = "No"
        elif category == "Doble Oportunidad":
            if (
                "homedraw" in lower_sel
                or "home draw" in lower_sel
                or re.search(r"\b1x\b", lower_sel)
            ):
                side = "1X"
            elif (
                "homeaway" in lower_sel
                or "home away" in lower_sel
                or re.search(r"\b12\b", lower_sel)
            ):
                side = "12"
            elif (
                "drawaway" in lower_sel
                or "draw away" in lower_sel
                or re.search(r"\bx2\b", lower_sel)
            ):
                side = "X2"
        else:
            if "over" in lower_sel or "más de" in lower_sel or "mas de" in lower_sel:
                side = "Over"
            elif "under" in lower_sel or "menos de" in lower_sel:
                side = "Under"

        line_val = pick.get("line")
        normalized_line = normalize_line(line_val)

        if normalized_line is None:
            match = re.search(r"(\d+(?:\.\d+)?)", sel_text)
            if match:
                normalized_line = normalize_line(match.group(1))

        if category in ("Doble Oportunidad", "BTTS"):
            normalized_line = None

        line_str = f" {normalized_line}" if normalized_line is not None else ""

        if category in ("Doble Oportunidad", "BTTS"):
            return f"{category} {side}".strip() if side else category

        if side:
            return f"{side}{line_str} {category}".strip()

        return f"{category}{line_str}".strip()

    result_fields = (
        "final_score_home",
        "final_score_away",
        "final_corners_home",
        "final_corners_away",
        "final_yellow_cards_home",
        "final_yellow_cards_away",
        "final_red_cards_home",
        "final_red_cards_away",
        "final_shots_home",
        "final_shots_away",
        "final_shots_on_target_home",
        "final_shots_on_target_away",
        "final_fouls_home",
        "final_fouls_away",
        "final_offsides_home",
        "final_offsides_away",
    )

    history = (
        db.query(AnalysisHistory)
        .options(
            load_only(
                AnalysisHistory.id,
                AnalysisHistory.competition,
                AnalysisHistory.payload,
                AnalysisHistory.match_date,
                AnalysisHistory.date,
                AnalysisHistory.picks_calculados,
                *(getattr(AnalysisHistory, field) for field in result_fields),
            )
        )
        .all()
    )

    leagues_data = {}

    for h in history:
        comp_name = h.competition
        p_data = None

        if getattr(h, "payload", None):
            try:
                p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
            except Exception:
                pass

        if not comp_name and isinstance(p_data, dict):
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
                "_market_stats": {},
                "_detailed_markets": {},
                "_seasons": set(),
            }

        league = leagues_data[comp_name]
        league["total_matches"] += 1

        s_year = None

        if isinstance(p_data, dict):
            s_year = p_data.get("season_year") or p_data.get("season")

        if not s_year:
            m_dt = getattr(h, "match_date", None) or getattr(h, "date", None)

            if m_dt:
                try:
                    s_year = m_dt.year
                except Exception:
                    pass

        if s_year:
            league["_seasons"].add(str(s_year))

        if not h.picks_calculados:
            continue

        try:
            picks = (
                json.loads(h.picks_calculados)
                if isinstance(h.picks_calculados, str)
                else h.picks_calculados
            )

            if not isinstance(picks, list):
                continue

            res_dict = {field: getattr(h, field) for field in result_fields}

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

                if not has_result:
                    league["has_pending_matches"] = True
                    sel_key = build_market_key(pick)
                    det_map = league["_detailed_markets"]
                    if sel_key not in det_map:
                        det_map[sel_key] = {
                            "name": sel_key,
                            "totalPicks": 0,
                            "ganados": 0,
                            "perdidos": 0,
                            "nulos": 0,
                            "pendientes": 0,
                            "profit": 0.0,
                            "oddsSum": 0.0,
                            "oddsCount": 0,
                        }
                    m_entry = det_map[sel_key]
                    m_entry["totalPicks"] += 1
                    m_entry["pendientes"] += 1
                    odds_val = float(pick.get("odds", 0.0) or 0.0)
                    if odds_val > 0:
                        m_entry["oddsSum"] += odds_val
                        m_entry["oddsCount"] += 1
                    continue

                success = _check_pick_success(pick, res_dict)

                if success is None:
                    continue

                stake = _resolve_stake_from_pick(pick) if use_stake else MIN_STAKE

                pick_profit = (
                    _calculate_pick_profit(
                        success,
                        pick.get("odds", 0.0),
                    )
                    * stake
                )

                league["total_profit"] += pick_profit

                # Conserva el criterio de tu función original.
                if success == "void":
                    continue

                league["total_picks"] += 1
                league["total_staked"] += stake

                odds_val = float(pick.get("odds", 0.0) or 0.0)

                if odds_val > 0:
                    league["odds_sum"] += odds_val
                    league["odds_count"] += 1

                is_hit = _is_pick_hit(success)

                if is_hit:
                    league["total_hits"] += 1

                sel_text = pick.get("selection", "")

                try:
                    family = _market_family(sel_text)
                except Exception:
                    family = "generic"

                # Mantener las métricas por familia para LRS.
                mkt = league["_market_stats"]

                if family not in mkt:
                    mkt[family] = {"hits": 0, "total": 0}

                mkt[family]["total"] += 1

                if is_hit:
                    mkt[family]["hits"] += 1

                # Cambio principal: agrupar por lado + categoría + línea.
                sel_key = build_market_key(pick)

                det_map = league["_detailed_markets"]

                if sel_key not in det_map:
                    det_map[sel_key] = {
                        "name": sel_key,
                        "totalPicks": 0,
                        "ganados": 0,
                        "perdidos": 0,
                        "nulos": 0,
                        "pendientes": 0,
                        "profit": 0.0,
                        "oddsSum": 0.0,
                        "oddsCount": 0,
                    }

                m_entry = det_map[sel_key]
                m_entry["totalPicks"] += 1

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

    results = []

    for league in leagues_data.values():
        picks_cnt = league["total_picks"]

        league["accuracy"] = (
            round(league["total_hits"] / picks_cnt * 100, 1) if picks_cnt > 0 else 0.0
        )

        league["total_profit"] = round(
            league["total_profit"],
            2,
        )

        staked_amt = league.pop("total_staked", 0.0)

        roi_val = (
            league["total_profit"] / staked_amt * 100
            if staked_amt > 0
            else (league["total_profit"] / picks_cnt * 100 if picks_cnt > 0 else 0.0)
        )

        league["roi"] = round(roi_val, 1)

        odds_cnt = league.pop("odds_count", 0)
        odds_s = league.pop("odds_sum", 0.0)

        avg_odds = round(odds_s / odds_cnt, 2) if odds_cnt > 0 else 0.0

        league["avg_odds"] = avg_odds

        league["break_even_pct"] = round(1.0 / avg_odds * 100.0, 1) if avg_odds > 0 else 0.0

        raw_mkt = league.pop("_market_stats", {})

        league["market_hit_rates"] = {
            family: round(stats["hits"] / stats["total"], 3)
            for family, stats in raw_mkt.items()
            if stats["total"] >= 3
        }

        det_markets_map = league.pop("_detailed_markets", {})
        detailed_markets = list(det_markets_map.values())

        detailed_markets.sort(
            key=lambda market: market["totalPicks"],
            reverse=True,
        )

        league["markets"] = detailed_markets

        raw_seasons = league.pop("_seasons", set())
        league["seasons"] = sorted(raw_seasons, reverse=True)

        league["historical_matches"] = league["total_matches"]
        league["historical_picks"] = picks_cnt
        league["historical_hits"] = league["total_hits"]
        league["historical_profit"] = league["total_profit"]
        league["historical_roi"] = league["roi"]

        results.append(league)

    _set_cache(cache_key, results)
    return results


@router.get("/api/v1/stats/global", response_model=GlobalStatsOut, tags=["Stats"])
def get_global_stats(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    use_stake: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Calculate global performance metrics across all sports with advanced analytics."""
    cache_key = f"global:{date_from}:{date_to}:{use_stake}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    from sqlalchemy.orm import load_only

    query = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.picks_calculados != None)
        .options(
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
    odds_buckets_cfg = [
        (1.0, 1.5, "1.0-1.5"),
        (1.5, 2.0, "1.5-2.0"),
        (2.0, 3.0, "2.0-3.0"),
        (3.0, 1000.0, ">3.0"),
    ]
    edge_buckets_cfg = [
        (-100.0, 5.0, "<5%"),
        (5.0, 10.0, "5-10%"),
        (10.0, 15.0, "10-15%"),
        (15.0, 1000.0, ">15%"),
    ]
    conf_buckets_cfg = [
        (0.0, 60.0, "<60%"),
        (60.0, 70.0, "60-70%"),
        (70.0, 80.0, "70-80%"),
        (80.0, 100.1, ">80%"),
    ]

    odds_b_stats = {
        label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0}
        for _, _, label in odds_buckets_cfg
    }
    edge_b_stats = {
        label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0}
        for _, _, label in edge_buckets_cfg
    }
    conf_b_stats = {
        label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0}
        for _, _, label in conf_buckets_cfg
    }

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
            "odds_b_stats": {
                label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0}
                for _, _, label in odds_buckets_cfg
            },
            "edge_b_stats": {
                label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0}
                for _, _, label in edge_buckets_cfg
            },
            "conf_b_stats": {
                label: {"count": 0, "hits": 0, "resolved": 0, "total_odds": 0.0}
                for _, _, label in conf_buckets_cfg
            },
            "daily_profit_dict": {},
        }

    for h in history:
        has_result = h.final_score_home is not None
        if has_result:
            matches_with_results += 1

        if h.picks_calculados:
            try:
                picks = json.loads(str(h.picks_calculados))
                if not isinstance(picks, list):
                    continue

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
                if (
                    h.final_score_home is not None
                    and h.final_score_away is not None
                    and h.compare_response_snapshot
                ):
                    try:
                        snap = (
                            json.loads(h.compare_response_snapshot)
                            if isinstance(h.compare_response_snapshot, str)
                            else h.compare_response_snapshot
                        )
                        if isinstance(snap, dict) and snap.get("most_probable_score"):
                            total_exact_scores_predicted += 1
                            predicted_parts = snap["most_probable_score"].split("-")
                            if len(predicted_parts) == 2:
                                pred_h = int(predicted_parts[0].strip())
                                pred_a = int(predicted_parts[1].strip())
                                if pred_h == h.final_score_home and pred_a == h.final_score_away:
                                    total_exact_scores_hits += 1
                    except:
                        pass

                sport = h.sport.value if hasattr(h.sport, "value") else str(h.sport)
                if sport not in sport_stats:
                    sport_stats[sport] = {"picks": 0, "hits": 0}

                # Extract league info
                league = h.competition
                if not league and h.payload:
                    try:
                        p_data = json.loads(h.payload) if isinstance(h.payload, str) else h.payload
                        league = p_data.get("competition") or "Desconocida"
                    except:
                        pass
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
                    match_day = (
                        (h.match_date or h.date).strftime("%Y-%m-%d")
                        if (h.match_date or h.date)
                        else None
                    )
                    if match_day:
                        daily_profit_dict[match_day] = (
                            daily_profit_dict.get(match_day, 0.0) + pick_profit
                        )
                        cat_accumulators[cat]["daily_profit_dict"][match_day] = (
                            cat_accumulators[cat]["daily_profit_dict"].get(match_day, 0.0)
                            + pick_profit
                        )

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
                                if _is_pick_hit(success):
                                    odds_b_stats[label]["hits"] += 1
                                break

                        for low, high, label in edge_buckets_cfg:
                            if low <= edge_val < high:
                                edge_b_stats[label]["count"] += 1
                                edge_b_stats[label]["total_odds"] += odds
                                edge_b_stats[label]["resolved"] += 1
                                if _is_pick_hit(success):
                                    edge_b_stats[label]["hits"] += 1
                                break

                        for low, high, label in conf_buckets_cfg:
                            if low <= conf < high:
                                conf_b_stats[label]["count"] += 1
                                conf_b_stats[label]["total_odds"] += odds
                                conf_b_stats[label]["resolved"] += 1
                                if _is_pick_hit(success):
                                    conf_b_stats[label]["hits"] += 1
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
                                if _is_pick_hit(success):
                                    cat_odds_b_stats[label]["hits"] += 1
                                break

                        cat_edge_b_stats = cat_acc["edge_b_stats"]
                        for low, high, label in edge_buckets_cfg:
                            if low <= edge_val < high:
                                cat_edge_b_stats[label]["count"] += 1
                                cat_edge_b_stats[label]["total_odds"] += odds
                                cat_edge_b_stats[label]["resolved"] += 1
                                if _is_pick_hit(success):
                                    cat_edge_b_stats[label]["hits"] += 1
                                break

                        cat_conf_b_stats = cat_acc["conf_b_stats"]
                        for low, high, label in conf_buckets_cfg:
                            if low <= conf < high:
                                cat_conf_b_stats[label]["count"] += 1  # type: ignore[bad-index]
                                cat_conf_b_stats[label]["total_odds"] += odds  # type: ignore[bad-index]
                                cat_conf_b_stats[label]["resolved"] += 1  # type: ignore[bad-index]
                                if _is_pick_hit(success):
                                    cat_conf_b_stats[label]["hits"] += 1  # type: ignore[bad-index]
                                break

            except Exception as e:
                print(f"Error in global stats loop: {e}")
                continue

    accuracy = (total_hits / total_picks * 100) if total_picks > 0 else 0.0
    roi = (total_profit / total_staked_picks * 100) if total_staked_picks > 0 else 0.0
    avg_odds = (total_odds / total_picks) if total_picks > 0 else 0.0
    avg_winning_odds = (
        (total_winning_odds / winning_picks_count) if winning_picks_count > 0 else 0.0
    )

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
                result.append(
                    {
                        "name": name,
                        "picks": data["picks"],
                        "hits": data["hits"],
                        "accuracy": acc,
                        "profit": round(data.get("profit", 0.0), 2),
                        "roi": round(roi_v, 1),
                    }
                )
        return result

    # Helper for buckets to list
    def bucket_to_list(stats_map):
        res = []
        for label, data in stats_map.items():
            avg_o = (data["total_odds"] / data["count"]) if data["count"] > 0 else 0.0
            acc = (data["hits"] / data["resolved"] * 100) if data["resolved"] > 0 else 0.0
            res.append(
                {
                    "bucket": label,
                    "count": data["count"],
                    "avg_odds": round(avg_o, 2),
                    "accuracy": round(acc, 1),
                }
            )
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
        cat_roi = (
            (cat_acc["total_profit"] / cat_acc["total_staked_picks"] * 100)
            if cat_acc["total_staked_picks"] > 0
            else 0.0
        )
        cat_avg_odds = (cat_acc["total_odds"] / cat_picks) if cat_picks > 0 else 0.0
        cat_winning_picks = cat_acc["winning_picks_count"]
        cat_avg_winning_odds = (
            (cat_acc["total_winning_odds"] / cat_winning_picks) if cat_winning_picks > 0 else 0.0
        )

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
            cat_daily_profit_series.append(
                {
                    "date": day,
                    "daily": round(cat_daily_profit_dict[day], 2),
                    "cumulative": round(cat_cumulative, 2),
                }
            )

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
            "daily_profit_series": cat_daily_profit_series,
        }

    # Build daily profit series sorted by date, with cumulative
    daily_profit_series = []
    cumulative = 0.0
    for day in sorted(daily_profit_dict.keys()):
        cumulative += daily_profit_dict[day]
        daily_profit_series.append(
            {
                "date": day,
                "daily": round(daily_profit_dict[day], 2),
                "cumulative": round(cumulative, 2),
            }
        )

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
        "category_stats": category_stats_out,
    }
    _set_cache(cache_key, res)
    return res


@router.get("/api/v1/report/excel", tags=["Stats"])
def export_excel_report(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    use_stake: bool = Query(False),
    bankroll_units: float = Query(
        100.0,
        description="Bankroll base en 'unidades', usado como referencia "
        "para calcular el % de drawdown. Ej: si 1u = 1% de "
        "tu bankroll real, usa 100. Si 1u = 0.5%, usa 200.",
    ),
    db: Session = Depends(get_db),
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
            "picks": 0,
            "hits": 0,
            "pending": 0,
            "profit": 0.0,
            "staked": 0,
            "odds": 0.0,
            "winning_odds": 0.0,
            "winning_count": 0,
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
        if (
            h.final_score_home is not None
            and h.final_score_away is not None
            and h.compare_response_snapshot
        ):
            try:
                snap = (
                    json.loads(h.compare_response_snapshot)
                    if isinstance(h.compare_response_snapshot, str)
                    else h.compare_response_snapshot
                )
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

        matches_data.append(
            {
                "ID Partido": h.id,
                "Fecha de Análisis": h.date.strftime("%Y-%m-%d %H:%M") if h.date else "",
                "Fecha de Partido": h.match_date.strftime("%Y-%m-%d %H:%M") if h.match_date else "",
                "Deporte": h.sport.value if hasattr(h.sport, "value") else str(h.sport),
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
                "Cuenta en Rentabilidad": "Sí"
                if getattr(h, "count_in_profitability", True)
                else "No",
                "Tiene Stats Reales": "Sí" if getattr(h, "has_real_stats", True) else "No",
            }
        )

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
                        edge_prob = (
                            float(pick.get("edge", 0.0)) if pick.get("edge") is not None else None
                        )
                        edge_ev_frac = pick.get("edge_ev")
                        ev_real_pct = (
                            float(edge_ev_frac) * 100.0 if edge_ev_frac is not None else None
                        )

                        # Placeholder CLV: hoy no disponible. Cuando exista `closing_odds`
                        # en el pick, esto se calcula solo, sin más cambios en el exportador.
                        closing_odds = pick.get("closing_odds")
                        clv_pct = None
                        if closing_odds and odds:
                            try:
                                own_implied = 1.0 / odds
                                closing_implied = 1.0 / float(closing_odds)
                                clv_pct = round(
                                    (closing_implied - own_implied) / closing_implied * 100.0, 2
                                )
                            except Exception:
                                clv_pct = None

                        picks_data.append(
                            {
                                "ID Partido": h.id,
                                "Fecha": h.date.strftime("%Y-%m-%d %H:%M") if h.date else "",
                                "Partido": h.match_title,
                                "Liga": league,
                                "Deporte": h.sport.value
                                if hasattr(h.sport, "value")
                                else str(h.sport),
                                "Selección": pick.get("selection", ""),
                                "Mercado": market,
                                "Línea": pick.get("line"),
                                "Cuota": odds,
                                "Cuota Cierre": closing_odds
                                if closing_odds
                                else "",  # placeholder CLV
                                "CLV (%)": clv_pct
                                if clv_pct is not None
                                else "",  # placeholder CLV
                                # ── Hit Rates básicos ──
                                "Hit Rate Local (%)": pick.get("home_hit_rate"),
                                "Hit Rate Visitante (%)": pick.get("away_hit_rate"),
                                "Hit Rate Total (%)": pick.get("empirical_hit_rate"),
                                "Hit Rate H2H (%)": pick.get("h2h_hit_rate"),
                                # ── Hit Rates de recencia (EWMA Bayesiano) ──
                                # Probabilidad suavizada con prior de liga + decaimiento exponencial
                                "HR Recencia Local (%)": pick.get("home_bayesian_ewma_hit_rate"),
                                "HR Recencia Visitante (%)": pick.get(
                                    "away_bayesian_ewma_hit_rate"
                                ),
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
                                "Prob Calibrada (%)": float(pick.get("calibrated_prob", 0.0))
                                if pick.get("calibrated_prob") is not None
                                else None,
                                "Prob Modelo (%)": float(pick.get("model_prob", 0.0))
                                if pick.get("model_prob") is not None
                                else None,
                                "Edge Prob (%)": edge_prob,  # ANTES mal llamado "EV Edge (%)"
                                "EV Real (%)": ev_real_pct,  # AHORA sí es el EV real
                                "Fracción Kelly (%)": float(pick.get("kelly_fraction", 0.0)) * 100.0
                                if pick.get("kelly_fraction") is not None
                                else None,
                                "Stake Sugerido (u)": pick.get("stake_units"),
                                "Resultado": success_str,
                                "Beneficio (u)": pick_profit if success is not None else None,
                                "Categoría": cat,
                                "Cuenta en Rentabilidad": "Sí"
                                if getattr(h, "count_in_profitability", True)
                                else "No",
                            }
                        )
            except Exception:
                pass

        # Fila agregada a nivel de partido (solo si hubo al menos un pick resuelto)
        if match_picks_resolved > 0:
            match_level_data.append(
                {
                    "ID Partido": h.id,
                    "Fecha de Partido": h.match_date or h.date,
                    "Partido": h.match_title,
                    "Liga": league,
                    "Picks Resueltos": match_picks_resolved,
                    "Aciertos": match_hits,
                    "% Acierto Partido": round(match_hits / match_picks_resolved * 100, 1)
                    if match_picks_resolved
                    else None,
                    "Cuota Promedio Partido": round(sum(match_odds_list) / len(match_odds_list), 2)
                    if match_odds_list
                    else None,
                    "Beneficio Neto Partido (u)": round(match_profit, 2),
                    "Partido Ganador (Profit > 0)": match_profit > 0,
                }
            )

    # ── DataFrames base ──
    global_accuracy = (total_hits / total_picks * 100) if total_picks > 0 else 0.0
    global_roi = (total_profit / total_staked_picks * 100) if total_staked_picks > 0 else 0.0
    global_avg_odds = (total_odds / total_picks) if total_picks > 0 else 0.0
    global_avg_winning_odds = (
        (total_winning_odds / winning_picks_count) if winning_picks_count > 0 else 0.0
    )
    exact_hit_rate = (
        (total_exact_scores_hits / total_exact_scores_predicted * 100)
        if total_exact_scores_predicted > 0
        else 0.0
    )

    # ── NUEVO: Curva de equity y drawdown A NIVEL DE PARTIDO (clustering-adjusted) ──
    df_match_level = pd.DataFrame(match_level_data)
    df_equity, max_drawdown_u, max_drawdown_pct = build_equity_curve(
        df_match_level, bankroll_units=bankroll_units
    )

    # ── Test de significancia clustering-adjusted (a nivel de partido, no de pick) ──
    n_matches_clustered = len(df_match_level) if not df_match_level.empty else 0
    matches_won = (
        int(df_match_level["Partido Ganador (Profit > 0)"].sum()) if not df_match_level.empty else 0
    )
    match_level_winrate = (
        round(matches_won / n_matches_clustered * 100, 1) if n_matches_clustered > 0 else 0.0
    )

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
        {
            "Métrica": "Nota CLV",
            "Valor": "No disponible aún — columnas 'Cuota Cierre' y 'CLV (%)' quedan listas para cuando se implemente la captura de cuota de cierre.",
        },
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
        cat_avg_winning_odds = (
            (cat_acc["winning_odds"] / cat_acc["winning_count"])
            if cat_acc["winning_count"] > 0
            else 0.0
        )

        category_summary_rows.append(
            {
                "Categoría": cat.capitalize(),
                "Picks Evaluados": cat_picks,
                "Aciertos (Hits)": cat_hits,
                "Pendientes": cat_acc["pending"],
                "Rentabilidad (u)": round(cat_acc["profit"], 2),
                "ROI (%)": round(cat_roi, 2),
                "Precisión (%)": round(cat_accuracy, 2),
                "Cuota Promedio": round(cat_avg_odds, 2),
                "Cuota Ganadora Promedio": round(cat_avg_winning_odds, 2),
            }
        )
    df_summary_categories = pd.DataFrame(category_summary_rows)

    df_matches = pd.DataFrame(matches_data)
    df_picks = pd.DataFrame(picks_data)

    league_rows = []
    for league, stats in league_counters.items():
        l_picks = stats["picks"]
        l_hits = stats["hits"]
        l_acc = (l_hits / l_picks * 100) if l_picks > 0 else 0.0
        league_rows.append(
            {
                "Liga / Competición": league,
                "Picks Evaluados": l_picks,
                "Aciertos (Hits)": l_hits,
                "Precisión (%)": round(l_acc, 2),
                "Rentabilidad (u)": round(stats["profit"], 2),
            }
        )
    df_leagues = pd.DataFrame(league_rows)
    if not df_leagues.empty:
        df_leagues = df_leagues.sort_values(by="Rentabilidad (u)", ascending=False)

    market_rows = []
    for market, stats in market_counters.items():
        m_picks = stats["picks"]
        m_hits = stats["hits"]
        m_acc = (m_hits / m_picks * 100) if m_picks > 0 else 0.0
        market_rows.append(
            {
                "Mercado": market,
                "Picks Evaluados": m_picks,
                "Aciertos (Hits)": m_hits,
                "Precisión (%)": round(m_acc, 2),
                "Rentabilidad (u)": round(stats["profit"], 2),
            }
        )
    df_markets = pd.DataFrame(market_rows)
    if not df_markets.empty:
        df_markets = df_markets.sort_values(by="Rentabilidad (u)", ascending=False)

    # ── Escribir Excel ──
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_summary_general.to_excel(writer, sheet_name="Resumen", index=False, startrow=1)
        df_summary_categories.to_excel(
            writer, sheet_name="Resumen", index=False, startrow=len(summary_general_rows) + 3
        )

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
                        if sheet_name == "Resumen" and cell.coordinate in [
                            "A1",
                            f"A{cat_header_row}",
                        ]:
                            continue
                        max_len = max(max_len, len(str(cell.value)))
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

    output.seek(0)

    filename = f"Reporte_Sherlock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/api/v1/stats/picks", response_model=list[PickStat], tags=["Stats"])
def get_all_picks(
    limit: int = 100,
    sport: str | None = None,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: Session = Depends(get_db),
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
        if not h.picks_calculados:
            continue
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

                all_picks.append(
                    {
                        "match_id": h.id,
                        "match_title": h.match_title,
                        "sport": h.sport.value if hasattr(h.sport, "value") else str(h.sport),
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
                        "proj_support": pick.get("proj_support"),
                    }
                )

        except Exception as err:
            print(f"Error packing picks: {err}")
            continue

    return all_picks
