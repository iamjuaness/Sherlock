"""Service for Picks Explorer & Audit in Sherlock Admin Panel."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, text

from src.core.domain import AnalysisHistory
from src.schemas.admin import (
    PickItemOut,
    PickDetailOut,
    PaginationMeta,
    OperationalFieldsUpdate,
)
from src.services.admin_audit_service import log_admin_action


ALLOWED_SORT_COLUMNS = {
    "match_date": AnalysisHistory.match_date,
    "date": AnalysisHistory.date,
    "competition": AnalysisHistory.competition,
    "match_title": AnalysisHistory.match_title,
    "bookmaker": AnalysisHistory.bookmaker,
    "stake_units": AnalysisHistory.stake_units,
    "count_in_profitability": AnalysisHistory.count_in_profitability,
    "id": AnalysisHistory.id,
}

# Threshold above which a pair of picks is considered correlated and the weaker one is removed.
_CORR_BLOCK_RHO = 0.3


def _dedup_correlated_picks(picks: List[Dict]) -> List[Dict]:
    """Filter out correlated picks within the same match (analysis_id).

    Uses ``market_group(market + ' ' + selection)`` to determine the pick's
    familia_lado key (same key used in ``data/market_correlation.json``) and
    then applies the correlation matrix: for any pair of picks in the same
    match whose |rho| >= _CORR_BLOCK_RHO, the pick with the lower edge is
    removed.  Picks from different matches are always kept independently.

    This mirrors the behaviour of ``resolve_match_picks_correlation`` but works
    on already-extracted picks (Dict) where ``market`` and ``selection`` are
    separate fields.
    """
    if len(picks) <= 1:
        return picks

    try:
        from src.core.pick_rules_engine import market_group, load_market_correlation_matrix
        matrix = load_market_correlation_matrix()
    except Exception:
        return picks

    if not matrix:
        return picks

    # Group picks by analysis_id (one match per group)
    from collections import defaultdict, OrderedDict
    by_match: Dict[str, List[Dict]] = OrderedDict()
    for p in picks:
        mid = str(p.get("analysis_id") or "")
        if not mid:
            raw_id = str(p.get("id") or "")
            mid = raw_id.rsplit("_", 1)[0] if "_" in raw_id else raw_id
        by_match.setdefault(mid, []).append(p)

    result: List[Dict] = []
    for match_picks in by_match.values():
        if len(match_picks) <= 1:
            result.extend(match_picks)
            continue

        # Compute familia_lado for each pick using market + selection text
        groups = []
        for p in match_picks:
            combined = f"{p.get('market', '')} {p.get('selection', '')}".strip()
            groups.append(market_group(combined))

        # Greedy filter: keep highest-edge pick; remove if correlated with an already-accepted pick
        # Sort by edge descending so we always keep the better pick
        indexed = sorted(enumerate(match_picks), key=lambda x: float(x[1].get("edge") or 0.0), reverse=True)

        accepted_indices: List[int] = []
        accepted_groups: List[str] = []

        for orig_idx, pick in indexed:
            grp = groups[orig_idx]
            excluded = False
            for acc_idx, acc_grp in zip(accepted_indices, accepted_groups):
                rho = matrix.get((grp, acc_grp)) or matrix.get((acc_grp, grp))
                if rho is not None and abs(rho) >= _CORR_BLOCK_RHO:
                    excluded = True
                    break
            if not excluded:
                accepted_indices.append(orig_idx)
                accepted_groups.append(grp)

        accepted_set = set(accepted_indices)
        result.extend(p for i, p in enumerate(match_picks) if i in accepted_set)

    return result


def _extract_picks_from_analysis(
    ah: AnalysisHistory,
    include_blacklisted: bool = False,
    include_non_publishable: bool = False,
) -> List[Dict[str, Any]]:
    """Extract individual picks from picks_calculados or payload."""
    raw_picks = []

    # Try picks_calculados JSON blob first
    if ah.picks_calculados:
        try:
            parsed = json.loads(ah.picks_calculados)
            if isinstance(parsed, list):
                raw_picks = parsed
            elif isinstance(parsed, dict) and "picks" in parsed:
                raw_picks = parsed.get("picks", [])
        except Exception:
            pass

    # Fallback to payload JSON blob
    if not raw_picks and ah.payload:
        try:
            payload = json.loads(ah.payload)
            if isinstance(payload, dict):
                raw_picks = payload.get("picks", []) or payload.get("recommended_picks", [])
        except Exception:
            pass

    # Result dict for settlement check
    has_result = ah.final_score_home is not None and ah.final_score_away is not None
    res_dict = {
        "final_score_home": ah.final_score_home,
        "final_score_away": ah.final_score_away,
        "final_corners_home": ah.final_corners_home,
        "final_corners_away": ah.final_corners_away,
        "final_yellow_cards_home": ah.final_yellow_cards_home,
        "final_yellow_cards_away": ah.final_yellow_cards_away,
        "final_red_cards_home": ah.final_red_cards_home,
        "final_red_cards_away": ah.final_red_cards_away,
        "final_shots_home": ah.final_shots_home,
        "final_shots_away": ah.final_shots_away,
        "final_shots_on_target_home": ah.final_shots_on_target_home,
        "final_shots_on_target_away": ah.final_shots_on_target_away,
        "final_fouls_home": ah.final_fouls_home,
        "final_fouls_away": ah.final_fouls_away,
        "final_offsides_home": ah.final_offsides_home,
        "final_offsides_away": ah.final_offsides_away,
    } if has_result else {}

    extracted = []
    for idx, p in enumerate(raw_picks):
        if not isinstance(p, dict):
            continue

        is_bl = bool(p.get("is_blacklisted"))
        is_blocked = bool(p.get("is_rule_blocked"))
        if (is_bl or is_blocked) and not include_blacklisted:
            continue

        # Excluir picks marcados explícitamente como "❌ NO VALUE"
        pick_rating = p.get("rating")
        if pick_rating is not None and pick_rating == "❌ NO VALUE":
            continue

        odds = float(p.get("odds") or p.get("cuota") or 1.0)
        is_und = bool(p.get("is_underdog") or p.get("underdog") or p.get("category") == "Underdog" or odds >= 3.0)
        is_val = bool(p.get("is_value", False))

        is_pub = p.get("is_publishable")
        if is_pub is None:
            is_pub = p.get("publishable")
        is_pub = bool(is_pub) if is_pub is not None else False

        # In Sherlock, picks are published if is_publishable, is_underdog or is_value is True
        is_published_pick = is_pub or is_und or is_val
        if not is_published_pick and not include_non_publishable and not include_blacklisted:
            continue

        selection = p.get("selection") or p.get("pick") or p.get("name") or p.get("pick_name") or p.get("label") or ""
        market = p.get("market") or p.get("market_type") or p.get("market_name")

        if not market or str(market).strip() in ("N/A", "Otro", "General", "None", "", "null"):
            try:
                from src.ui.api.main import get_market_name
                market = get_market_name(selection)
            except Exception:
                market = "Resultado Final (1X2)"

        if not selection or selection == "Análisis General":
            selection = p.get("pick_name") or p.get("label") or "Victoria Local"
        raw_prob = float(p.get("model_prob") or p.get("probability") or p.get("prob") or 0.0)
        
        # Normalize probability if expressed as percentage (> 1.0) or invalid
        if raw_prob > 1.0:
            if raw_prob <= 100.0:
                model_prob = raw_prob / 100.0
            else:
                model_prob = (raw_prob / 100.0) if raw_prob <= 10000.0 else 0.50
                while model_prob > 1.0:
                    model_prob /= 10.0
        elif raw_prob < 0:
            model_prob = 0.0
        else:
            model_prob = raw_prob

        # Calibrated probability fallback/extraction
        calibrated_prob = float(p.get("calibrated_prob") or p.get("prob_calibrated") or model_prob)
        if calibrated_prob > 1.0:
            calibrated_prob = calibrated_prob / 100.0 if calibrated_prob <= 100.0 else model_prob

        implied_prob = (1.0 / odds) if odds > 1.0 else 0.0
        edge = float(p.get("edge") or (model_prob - implied_prob))
        kelly = float(p.get("kelly") or p.get("kelly_fraction") or 0.0)
        stake = float(p.get("stake_units") or p.get("stake") or ah.stake_units or 1.0)
        is_value = bool(p.get("is_value", False) or edge > 0)

        # Dynamic settlement resolution
        succ = p.get("success") or p.get("status") or p.get("resultado") or p.get("result")

        if succ is None and has_result:
            try:
                from src.ui.api.main import _check_pick_success
                succ = _check_pick_success(p, res_dict)
            except Exception:
                succ = None

        if succ is True or succ in ("won", "ganada", "ganado", "win", "hit"):
            status_norm = "won"
            profit = round(stake * (odds - 1.0), 4)
        elif succ is False or succ in ("lost", "perdida", "perdido", "loss", "miss"):
            status_norm = "lost"
            profit = round(-stake, 4)
        elif succ in ("push", "nula", "nulo", "void", "empate"):
            status_norm = "push"
            profit = 0.0
        elif succ in ("half_win", "half_won"):
            status_norm = "won"
            profit = round(stake * (odds - 1.0) / 2.0, 4)
        elif succ in ("half_loss", "half_lost"):
            status_norm = "lost"
            profit = round(-stake / 2.0, 4)
        elif succ in ("cancelled", "anulada", "anulado"):
            status_norm = "cancelled"
            profit = 0.0
        else:
            status_norm = "pending"
            profit = 0.0

        roi = round((profit / stake) * 100.0, 2) if stake > 0 and status_norm in ("won", "lost", "push") else None
        is_und = bool(p.get("is_underdog") or p.get("underdog") or p.get("category") == "Underdog" or odds >= 3.0)
        category = p.get("category") or p.get("tag") or ("Underdog" if is_und else "Profesional")

        closing_odds = p.get("closing_odds")
        clv_pct = None
        if closing_odds and odds > 1.0:
            try:
                own_implied = 1.0 / odds
                closing_implied = 1.0 / float(closing_odds)
                clv_pct = round((closing_implied - own_implied) / closing_implied * 100.0, 2)
            except Exception:
                clv_pct = None

        synthetic_id = f"{ah.id}_{idx}"
        extracted.append({
            "id": synthetic_id,
            "analysis_id": ah.id,
            "match_date": ah.match_date or ah.date,
            "match_title": ah.match_title or "Sin título",
            "competition": ah.competition or "Sin Competición",
            "market": market,
            "selection": selection,
            "status": status_norm,
            "odds": round(odds, 3),
            "closing_odds": float(closing_odds) if closing_odds else None,
            "clv_pct": clv_pct,
            "model_prob": round(model_prob, 4),
            "calibrated_prob": round(calibrated_prob, 4),
            "implied_prob": round(implied_prob, 4),
            "edge": round(edge, 4),
            "kelly": round(kelly, 4),
            "stake": round(stake, 2),
            "profit": round(profit, 2),
            "roi": roi,
            "category": category,
            "bookmaker": ah.bookmaker or p.get("bookmaker") or "Genérico",
            "created_at": ah.date,
            "updated_at": ah.last_recalculated_at,
            "count_in_profitability": bool(ah.count_in_profitability if ah.count_in_profitability is not None else True),
            "needs_recalc": bool(ah.needs_recalc),
            "is_blacklisted": is_bl,
            "is_value": is_value,
            "is_publishable": is_pub,
            "is_underdog": is_und,
            "raw_pick": p,
        })

    # Fallback if no raw picks in JSON
    if not extracted:
        status_norm = "won" if (ah.final_score_home is not None and ah.final_score_home > ah.final_score_away) else ("lost" if has_result else "pending")
        stake = ah.stake_units or 1.0
        odds = 1.90
        profit = round(stake * (odds - 1.0), 4) if status_norm == "won" else (round(-stake, 4) if status_norm == "lost" else 0.0)
        roi = round((profit / stake) * 100.0, 2) if status_norm in ("won", "lost") else None

        extracted.append({
            "id": ah.id,
            "analysis_id": ah.id,
            "match_date": ah.match_date or ah.date,
            "match_title": ah.match_title or "Sin título",
            "competition": ah.competition or "Sin Competición",
            "market": "Resultado Final (1X2)",
            "selection": "Victoria Local",
            "status": status_norm,
            "odds": odds,
            "model_prob": 0.55,
            "calibrated_prob": 0.54,
            "implied_prob": 0.526,
            "edge": 0.024,
            "kelly": 0.05,
            "stake": stake,
            "profit": profit,
            "roi": roi,
            "category": "Profesional",
            "bookmaker": ah.bookmaker or "Genérico",
            "created_at": ah.date,
            "updated_at": ah.last_recalculated_at,
            "count_in_profitability": bool(ah.count_in_profitability if ah.count_in_profitability is not None else True),
            "needs_recalc": bool(ah.needs_recalc),
            "is_blacklisted": False,
            "is_value": True,
            "is_publishable": True,
            "is_underdog": False,
            "raw_pick": {},
        })

    return extracted



def query_picks(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    competition: Optional[str] = None,
    team: Optional[str] = None,
    market: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    bookmaker: Optional[str] = None,
    min_odds: Optional[float] = None,
    max_odds: Optional[float] = None,
    min_edge: Optional[float] = None,
    max_edge: Optional[float] = None,
    only_resolved: bool = False,
    only_pending: bool = False,
    count_in_profitability: Optional[bool] = None,
    needs_recalc: Optional[bool] = None,
    is_blacklisted: Optional[bool] = None,
    is_value: Optional[bool] = None,
    is_publishable: Optional[bool] = None,
    is_underdog: Optional[bool] = None,
    filter_correlated: bool = True,
    sort_by: str = "match_date",
    sort_dir: str = "desc",
) -> Tuple[List[PickItemOut], PaginationMeta]:
    """Server-side paginated & filtered query for picks."""
    query = db.query(AnalysisHistory)

    # Filtering on desnormalized columns
    if competition:
        query = query.filter(AnalysisHistory.competition.ilike(f"%{competition}%"))
    if bookmaker:
        query = query.filter(AnalysisHistory.bookmaker.ilike(f"%{bookmaker}%"))
    if count_in_profitability is not None:
        query = query.filter(AnalysisHistory.count_in_profitability == count_in_profitability)
    if needs_recalc is not None:
        query = query.filter(AnalysisHistory.needs_recalc == needs_recalc)

    # Date filters
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(or_(AnalysisHistory.match_date >= df, AnalysisHistory.date >= df))
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(or_(AnalysisHistory.match_date <= dt, AnalysisHistory.date <= dt))
        except Exception:
            pass

    # Free text search
    if search:
        s_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AnalysisHistory.match_title.ilike(s_pattern),
                AnalysisHistory.competition.ilike(s_pattern),
                AnalysisHistory.bookmaker.ilike(s_pattern),
            )
        )

    if team:
        t_pattern = f"%{team.strip()}%"
        query = query.filter(AnalysisHistory.match_title.ilike(t_pattern))

    if only_resolved:
        query = query.filter(
            AnalysisHistory.final_score_home.isnot(None),
            AnalysisHistory.final_score_away.isnot(None),
        )
    elif only_pending:
        query = query.filter(
            or_(
                AnalysisHistory.final_score_home.is_(None),
                AnalysisHistory.final_score_away.is_(None),
            )
        )

    # Validate sorting
    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, AnalysisHistory.match_date)
    if sort_dir.lower() == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    total_records = query.count()

    # Cap page_size to allowed bounds
    allowed_page_sizes = [50, 100, 1000, 10000]
    if page_size not in allowed_page_sizes:
        page_size = 50

    warning_msg = None
    if page_size >= 1000:
        warning_msg = f"Cargando {page_size} registros. Esta consulta puede tardar más en procesarse."

    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()

    all_raw_dicts: List[Dict[str, Any]] = []
    include_bl = bool(is_blacklisted)
    include_non_pub = (is_publishable is not False)
    for r in records:
        extracted = _extract_picks_from_analysis(r, include_blacklisted=include_bl, include_non_publishable=include_non_pub)
        for p_dict in extracted:
            if is_blacklisted is not None and bool(p_dict.get("is_blacklisted")) != is_blacklisted:
                continue
            if is_value is not None and bool(p_dict.get("is_value")) != is_value:
                continue
            if is_publishable is not None and bool(p_dict.get("is_publishable")) != is_publishable:
                continue
            if is_underdog is not None and bool(p_dict.get("is_underdog")) != is_underdog:
                continue
            # Apply memory filters for pick-level criteria
            if status and p_dict["status"] != status.lower():
                continue
            if market and market.lower() not in p_dict["market"].lower():
                continue
            if category and category.lower() not in p_dict["category"].lower():
                continue
            if min_odds is not None and p_dict["odds"] < min_odds:
                continue
            if max_odds is not None and p_dict["odds"] > max_odds:
                continue
            if min_edge is not None and p_dict["edge"] < min_edge:
                continue
            if max_edge is not None and p_dict["edge"] > max_edge:
                continue

            all_raw_dicts.append(p_dict)

    if filter_correlated:
        all_raw_dicts = _dedup_correlated_picks(all_raw_dicts)

    all_picks: List[PickItemOut] = []
    for p_dict in all_raw_dicts:
        p_out_dict = {k: v for k, v in p_dict.items() if k != "raw_pick"}
        all_picks.append(PickItemOut(**p_out_dict))

    total_pages = max(1, (total_records + page_size - 1) // page_size)
    meta = PaginationMeta(
        page=page,
        page_size=page_size,
        total_records=total_records,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
        warning=warning_msg,
    )
    return all_picks, meta


def export_picks_file(
    db: Session,
    export_format: str = "excel",
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    competition: Optional[str] = None,
    team: Optional[str] = None,
    market: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    bookmaker: Optional[str] = None,
    min_odds: Optional[float] = None,
    max_odds: Optional[float] = None,
    min_edge: Optional[float] = None,
    max_edge: Optional[float] = None,
    only_resolved: bool = False,
    only_pending: bool = False,
    count_in_profitability: Optional[bool] = None,
    needs_recalc: Optional[bool] = None,
    is_blacklisted: Optional[bool] = None,
    is_value: Optional[bool] = None,
    is_publishable: Optional[bool] = None,
    is_underdog: Optional[bool] = None,
    sort_by: str = "match_date",
    sort_dir: str = "desc",
) -> Tuple[bytes, str, str]:
    """Export filtered picks in Excel or CSV format using the exact schema as dashboard main Detalle de Picks."""
    import io
    import pandas as pd
    import openpyxl
    from openpyxl.utils import get_column_letter

    query = db.query(AnalysisHistory)

    if competition:
        query = query.filter(AnalysisHistory.competition.ilike(f"%{competition}%"))
    if bookmaker:
        query = query.filter(AnalysisHistory.bookmaker.ilike(f"%{bookmaker}%"))
    if count_in_profitability is not None:
        query = query.filter(AnalysisHistory.count_in_profitability == count_in_profitability)
    if needs_recalc is not None:
        query = query.filter(AnalysisHistory.needs_recalc == needs_recalc)

    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            query = query.filter(or_(AnalysisHistory.match_date >= df, AnalysisHistory.date >= df))
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.filter(or_(AnalysisHistory.match_date <= dt, AnalysisHistory.date <= dt))
        except Exception:
            pass

    if search:
        s_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AnalysisHistory.match_title.ilike(s_pattern),
                AnalysisHistory.competition.ilike(s_pattern),
                AnalysisHistory.bookmaker.ilike(s_pattern),
            )
        )

    if team:
        t_pattern = f"%{team.strip()}%"
        query = query.filter(AnalysisHistory.match_title.ilike(t_pattern))

    if only_resolved:
        query = query.filter(
            AnalysisHistory.final_score_home.isnot(None),
            AnalysisHistory.final_score_away.isnot(None),
        )
    elif only_pending:
        query = query.filter(
            or_(
                AnalysisHistory.final_score_home.is_(None),
                AnalysisHistory.final_score_away.is_(None),
            )
        )

    sort_col = ALLOWED_SORT_COLUMNS.get(sort_by, AnalysisHistory.match_date)
    if sort_dir.lower() == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    records = query.all()

    status_map = {
        "won": "Ganado",
        "lost": "Perdido",
        "push": "Push",
        "cancelled": "Cancelado",
        "pending": "Pendiente",
    }

    rows = []
    include_bl = (is_blacklisted is not False)
    include_non_pub = (is_publishable is not False)

    for ah in records:
        extracted = _extract_picks_from_analysis(ah, include_blacklisted=include_bl, include_non_publishable=include_non_pub)
        for p_dict in extracted:
            if is_blacklisted is not None and bool(p_dict.get("is_blacklisted")) != is_blacklisted:
                continue
            if is_value is not None and bool(p_dict.get("is_value")) != is_value:
                continue
            if is_publishable is not None and bool(p_dict.get("is_publishable")) != is_publishable:
                continue
            if is_underdog is not None and bool(p_dict.get("is_underdog")) != is_underdog:
                continue
            if status and p_dict["status"] != status.lower():
                continue
            if market and market.lower() not in p_dict["market"].lower():
                continue
            if category and category.lower() not in p_dict["category"].lower():
                continue
            if min_odds is not None and p_dict["odds"] < min_odds:
                continue
            if max_odds is not None and p_dict["odds"] > max_odds:
                continue
            if min_edge is not None and p_dict["edge"] < min_edge:
                continue
            if max_edge is not None and p_dict["edge"] > max_edge:
                continue

            raw_pick = p_dict.get("raw_pick") or {}
            edge_prob = float(p_dict.get("edge", 0.0)) if p_dict.get("edge") is not None else None
            edge_ev_frac = raw_pick.get("edge_ev")
            ev_real_pct = float(edge_ev_frac) * 100.0 if edge_ev_frac is not None else None

            closing_odds = raw_pick.get("closing_odds")
            clv_pct = None
            if closing_odds and p_dict.get("odds"):
                try:
                    own_implied = 1.0 / float(p_dict["odds"])
                    closing_implied = 1.0 / float(closing_odds)
                    clv_pct = round((closing_implied - own_implied) / closing_implied * 100.0, 2)
                except Exception:
                    clv_pct = None

            st_norm = p_dict.get("status", "pending")
            success_str = status_map.get(st_norm, st_norm.capitalize())

            match_date_str = ""
            m_dt = p_dict.get("match_date") or ah.match_date or ah.date
            if m_dt:
                if isinstance(m_dt, datetime):
                    match_date_str = m_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    match_date_str = str(m_dt)

            sport_val = ah.sport.value if hasattr(ah.sport, 'value') else str(ah.sport or "Football")

            rows.append({
                "ID Partido": ah.id,
                "Fecha": match_date_str,
                "Partido": p_dict.get("match_title") or ah.match_title or "",
                "Liga": p_dict.get("competition") or ah.competition or "",
                "Deporte": sport_val,
                "Selección": p_dict.get("selection", ""),
                "Mercado": p_dict.get("market", ""),
                "Línea": raw_pick.get("line"),
                "Cuota": p_dict.get("odds"),
                "Cuota Cierre": closing_odds if closing_odds else "",
                "CLV (%)": clv_pct if clv_pct is not None else "",
                "Hit Rate Local (%)": raw_pick.get("home_hit_rate"),
                "Hit Rate Visitante (%)": raw_pick.get("away_hit_rate"),
                "Hit Rate Total (%)": raw_pick.get("empirical_hit_rate"),
                "Hit Rate H2H (%)": raw_pick.get("h2h_hit_rate"),
                "HR Recencia Local (%)": raw_pick.get("home_bayesian_ewma_hit_rate"),
                "HR Recencia Visitante (%)": raw_pick.get("away_bayesian_ewma_hit_rate"),
                "Tendencia Local": raw_pick.get("home_trend_label"),
                "Tendencia Visitante": raw_pick.get("away_trend_label"),
                "Delta Tendencia Local (pp)": raw_pick.get("home_trend_delta_pp"),
                "Delta Tendencia Visitante (pp)": raw_pick.get("away_trend_delta_pp"),
                "Muestra Local (n)": raw_pick.get("home_matches_count"),
                "Muestra Visitante (n)": raw_pick.get("away_matches_count"),
                "Prob Calibrada (%)": float(p_dict["calibrated_prob"] * 100.0) if p_dict.get("calibrated_prob") is not None else None,
                "Prob Modelo (%)": float(p_dict["model_prob"] * 100.0) if p_dict.get("model_prob") is not None else None,
                "Edge Prob (%)": edge_prob * 100.0 if edge_prob is not None else None,
                "EV Real (%)": ev_real_pct,
                "Fracción Kelly (%)": float(p_dict["kelly"] * 100.0) if p_dict.get("kelly") is not None else None,
                "Stake Sugerido (u)": p_dict.get("stake"),
                "Resultado": success_str,
                "Beneficio (u)": p_dict.get("profit") if st_norm in ("won", "lost", "push") else None,
                "Categoría": p_dict.get("category"),
                "Cuenta en Rentabilidad": "Sí" if p_dict.get("count_in_profitability") else "No",
            })

    df_picks = pd.DataFrame(rows)
    fmt = (export_format or "excel").lower()

    if fmt in ("excel", "xlsx"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_picks.to_excel(writer, sheet_name="Detalle de Picks", index=False)
            workbook = writer.book
            ws = workbook["Detalle de Picks"]
            for col in ws.columns:
                max_len = 0
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 11)
        output.seek(0)
        filename = f"Detalle_Picks_Sherlock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename
    else:
        csv_str = df_picks.to_csv(index=False)
        content = csv_str.encode("utf-8-sig")
        filename = f"Detalle_Picks_Sherlock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return content, "text/csv; charset=utf-8", filename


def get_pick_detail(db: Session, analysis_id: str) -> Optional[PickDetailOut]:
    """Retrieve full detail for a single pick/analysis for auditing."""
    ah = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not ah:
        # Check if synthetic pick ID (e.g., uuid_0)
        base_id = analysis_id.split("_")[0] if "_" in analysis_id else analysis_id
        ah = db.query(AnalysisHistory).filter(AnalysisHistory.id == base_id).first()
        if not ah:
            return None

    extracted = _extract_picks_from_analysis(ah)
    pick_data = extracted[0] if extracted else {}

    # Parse payload if available
    payload_dict = {}
    if ah.payload:
        try:
            payload_dict = json.loads(ah.payload)
        except Exception:
            pass

    # Parse pre_match_stats & recent_form
    pre_match = {}
    if ah.pre_match_stats:
        try:
            pre_match = json.loads(ah.pre_match_stats)
        except Exception:
            pass

    recent_form = {}
    if ah.recent_form_stats:
        try:
            recent_form = json.loads(ah.recent_form_stats)
        except Exception:
            pass

    predictive_context = {
        "expected_goals_home": ah.expected_goals_home or payload_dict.get("expected_goals_home"),
        "expected_goals_away": ah.expected_goals_away or payload_dict.get("expected_goals_away"),
        "probabilities_1x2": payload_dict.get("probabilities_1x2") or payload_dict.get("prob_1x2"),
        "over_under_probs": payload_dict.get("over_under_probs") or payload_dict.get("prob_over_under"),
        "btts_probs": payload_dict.get("btts_probs") or payload_dict.get("prob_btts"),
        "poisson_output": payload_dict.get("poisson_output"),
        "raw_picks_count": len(extracted),
    }

    pre_match_evidence = {
        "pre_match_stats": pre_match,
        "recent_form": recent_form,
        "historical_rates": ah.historical_pick_rates,
    }

    # Generate objective audit explanation comparing prediction with actual result
    explanation = "Partido sin resultado final o pendiente de evaluación."
    if ah.final_score_home is not None and ah.final_score_away is not None:
        total_goals = ah.final_score_home + ah.final_score_away
        market_str = pick_data.get("market", "")
        status_str = pick_data.get("status", "")
        edge_str = f"{pick_data.get('edge', 0)*100:+.1f}%"

        explanation = (
            f"Partido finalizado {ah.final_score_home}-{ah.final_score_away} ({total_goals} goles totales). "
            f"El pick '{pick_data.get('selection')}' ({market_str}) con Edge estimado de {edge_str} resultó {status_str.upper()}."
        )
        if ah.expected_goals_home is not None and ah.expected_goals_away is not None:
            exp_total = ah.expected_goals_home + ah.expected_goals_away
            diff_goals = total_goals - exp_total
            explanation += f" xG acumulado previsto: {exp_total:.2f} (diferencia vs real: {diff_goals:+.2f} goles)."

    post_match_audit = {
        "final_score": f"{ah.final_score_home} - {ah.final_score_away}" if ah.final_score_home is not None else "N/A",
        "result_status": pick_data.get("status"),
        "profit_units": pick_data.get("profit"),
        "final_corners": f"{ah.final_corners_home} - {ah.final_corners_away}" if ah.final_corners_home is not None else "N/A",
        "final_cards": f"{ah.final_yellow_cards_home} - {ah.final_yellow_cards_away}" if ah.final_yellow_cards_home is not None else "N/A",
        "final_shots_on_target": f"{ah.final_shots_on_target_home} - {ah.final_shots_on_target_away}" if ah.final_shots_on_target_home is not None else "N/A",
        "expected_goals": f"{ah.expected_goals_home} - {ah.expected_goals_away}" if ah.expected_goals_home is not None else "N/A",
        "audit_explanation": explanation,
    }

    analysis_meta = {
        "id": ah.id,
        "match_title": ah.match_title,
        "competition": ah.competition,
        "date": ah.date.isoformat() if ah.date else None,
        "match_date": ah.match_date.isoformat() if ah.match_date else None,
        "bookmaker": ah.bookmaker,
        "needs_recalc": ah.needs_recalc,
        "count_in_profitability": ah.count_in_profitability,
    }

    return PickDetailOut(
        pick=PickItemOut(**pick_data),
        analysis=analysis_meta,
        predictive_context=predictive_context,
        pre_match_evidence=pre_match_evidence,
        post_match_audit=post_match_audit,
    )


def update_operational_fields(
    db: Session,
    analysis_id: str,
    update_payload: OperationalFieldsUpdate,
    admin_user: str = "admin",
) -> Optional[AnalysisHistory]:
    """Update authorized operational fields of an analysis with audit logging."""
    ah = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not ah:
        return None

    old_vals = {
        "competition": ah.competition,
        "bookmaker": ah.bookmaker,
        "stake_units": ah.stake_units,
        "count_in_profitability": ah.count_in_profitability,
        "needs_recalc": ah.needs_recalc,
    }

    changes = {}
    if update_payload.competition is not None:
        ah.competition = update_payload.competition
        changes["competition"] = update_payload.competition
    if update_payload.bookmaker is not None:
        ah.bookmaker = update_payload.bookmaker
        changes["bookmaker"] = update_payload.bookmaker
    if update_payload.stake_units is not None:
        if update_payload.stake_units >= 0:
            ah.stake_units = update_payload.stake_units
            changes["stake_units"] = update_payload.stake_units
    if update_payload.count_in_profitability is not None:
        ah.count_in_profitability = update_payload.count_in_profitability
        changes["count_in_profitability"] = update_payload.count_in_profitability
    if update_payload.needs_recalc is not None:
        ah.needs_recalc = update_payload.needs_recalc
        changes["needs_recalc"] = update_payload.needs_recalc

    ah.last_recalculated_at = datetime.utcnow()
    db.commit()
    db.refresh(ah)

    log_admin_action(
        db,
        action="update_operational_fields",
        target_table="analysis_history",
        record_id=analysis_id,
        old_values=old_vals,
        new_values=changes,
        admin_user=admin_user,
    )

    return ah


def mark_for_recalculation(db: Session, analysis_id: str, admin_user: str = "admin") -> bool:
    """Mark an analysis record for recalculation."""
    ah = db.query(AnalysisHistory).filter(AnalysisHistory.id == analysis_id).first()
    if not ah:
        return False

    old_val = ah.needs_recalc
    ah.needs_recalc = True
    db.commit()

    log_admin_action(
        db,
        action="mark_for_recalculation",
        target_table="analysis_history",
        record_id=analysis_id,
        old_values={"needs_recalc": old_val},
        new_values={"needs_recalc": True},
        admin_user=admin_user,
    )
    return True
