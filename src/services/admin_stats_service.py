"""Service for Advanced Analytics, Segmentation, KPIs, Calibration, and Exports in Sherlock Admin Panel."""

from __future__ import annotations

import io
import json
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from src.core.domain import AnalysisHistory
from src.schemas.admin import (
    DashboardKPIs,
    ModelQualityMetrics,
    CalibrationBand,
    ChartDataPoint,
    AccumulatedYieldPoint,
    DashboardChartsData,
    DashboardSummaryOut,
    GroupedStatItem,
    StatsGroupedOut,
    DataAnomalyItem,
    StatsAnomaliesOut,
)
from src.services.admin_picks_service import _extract_picks_from_analysis


def _filter_analyses_by_params(
    db: Session,
    date_range: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    competition: Optional[str] = None,
    market: Optional[str] = None,
    category: Optional[str] = None,
    bookmaker: Optional[str] = None,
    status: Optional[str] = None,
    count_in_profitability: Optional[bool] = None,
) -> List[AnalysisHistory]:
    """Query AnalysisHistory records based on standard admin filter params."""
    query = db.query(AnalysisHistory)

    if count_in_profitability is True:
        query = query.filter(or_(AnalysisHistory.count_in_profitability == True, AnalysisHistory.count_in_profitability == 1, AnalysisHistory.count_in_profitability.is_(None)))
    elif count_in_profitability is False:
        query = query.filter(or_(AnalysisHistory.count_in_profitability == False, AnalysisHistory.count_in_profitability == 0))

    if competition:
        query = query.filter(AnalysisHistory.competition.ilike(f"%{competition}%"))
    if bookmaker:
        query = query.filter(AnalysisHistory.bookmaker.ilike(f"%{bookmaker}%"))

    # Preset date ranges
    now = datetime.utcnow()
    if date_range:
        dr = date_range.lower()
        if dr == "today" or dr == "hoy":
            start_d = datetime(now.year, now.month, now.day)
            query = query.filter(or_(AnalysisHistory.match_date >= start_d, AnalysisHistory.date >= start_d))
        elif dr == "3d" or dr == "3_days":
            start_d = now - timedelta(days=3)
            query = query.filter(or_(AnalysisHistory.match_date >= start_d, AnalysisHistory.date >= start_d))
        elif dr == "7d" or dr == "7_days":
            start_d = now - timedelta(days=7)
            query = query.filter(or_(AnalysisHistory.match_date >= start_d, AnalysisHistory.date >= start_d))
        elif dr == "30d" or dr == "30_days":
            start_d = now - timedelta(days=30)
            query = query.filter(or_(AnalysisHistory.match_date >= start_d, AnalysisHistory.date >= start_d))

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

    return query.order_by(AnalysisHistory.match_date.asc()).all()


def _get_flattened_picks(
    analyses: List[AnalysisHistory],
    status_filter: Optional[str] = None,
    market_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    is_blacklisted: Optional[bool] = None,
    is_value: Optional[bool] = None,
    is_publishable: Optional[bool] = None,
    is_underdog: Optional[bool] = None,
    include_blacklisted: bool = False,
) -> List[Dict[str, Any]]:
    """Flatten all analyses into individual pick records."""
    all_picks = []
    include_bl = include_blacklisted or (is_blacklisted is not None)
    include_non_pub = (is_publishable is not False)
    for ah in analyses:
        extracted = _extract_picks_from_analysis(ah, include_blacklisted=include_bl, include_non_publishable=include_non_pub)
        for p in extracted:
            if is_blacklisted is not None:
                if bool(p.get("is_blacklisted")) != is_blacklisted:
                    continue
            if is_value is not None:
                if bool(p.get("is_value")) != is_value:
                    continue
            if is_publishable is not None:
                if bool(p.get("is_publishable")) != is_publishable:
                    continue
            if is_underdog is not None:
                if bool(p.get("is_underdog")) != is_underdog:
                    continue
            if status_filter and p["status"] != status_filter.lower():
                continue
            if market_filter and market_filter.lower() not in p["market"].lower():
                continue
            if category_filter and category_filter.lower() not in p["category"].lower():
                continue
            all_picks.append(p)
    return all_picks


def calculate_dashboard_summary(
    db: Session,
    date_range: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    competition: Optional[str] = None,
    market: Optional[str] = None,
    category: Optional[str] = None,
    bookmaker: Optional[str] = None,
    status: Optional[str] = None,
    count_in_profitability: Optional[bool] = None,
    is_blacklisted: Optional[bool] = None,
    is_value: Optional[bool] = None,
    is_publishable: Optional[bool] = None,
    is_underdog: Optional[bool] = None,
    min_sample: int = 10,
) -> DashboardSummaryOut:
    """Calculate complete dashboard KPIs, model quality/calibration metrics, and charts."""
    analyses = _filter_analyses_by_params(
        db, date_range, date_from, date_to, competition, market, category, bookmaker, status, count_in_profitability
    )
    picks = _get_flattened_picks(
        analyses,
        status_filter=status,
        market_filter=market,
        category_filter=category,
        is_blacklisted=is_blacklisted,
        is_value=is_value,
        is_publishable=is_publishable,
        is_underdog=is_underdog,
    )

    total_analyses = len(analyses)
    total_picks = len(picks)

    picks_won = [p for p in picks if p["status"] == "won"]
    picks_lost = [p for p in picks if p["status"] == "lost"]
    picks_push = [p for p in picks if p["status"] == "push"]
    picks_void = [p for p in picks if p["status"] == "cancelled"]
    picks_pending = [p for p in picks if p["status"] == "pending"]

    resolved_valid = picks_won + picks_lost + picks_push
    picks_resolved_count = len(resolved_valid)

    won_count = len(picks_won)
    lost_count = len(picks_lost)
    push_count = len(picks_push)
    void_count = len(picks_void)
    pending_count = len(picks_pending)

    hit_rate = (won_count / len(picks_won + picks_lost)) * 100.0 if (won_count + lost_count) > 0 else 0.0

    total_profit = sum(p["profit"] for p in resolved_valid)
    units_staked = sum(p["stake"] for p in resolved_valid)
    roi = (total_profit / units_staked * 100.0) if units_staked > 0 else 0.0
    yield_rate = roi

    # ── Ajustado: Stake Flat = 1.0 ──
    def _calc_adj_profit(p):
        st = p["status"]
        odds = float(p["odds"])
        if st == "won":
            return odds - 1.0
        elif st == "lost":
            return -1.0
        return 0.0

    total_profit_adj = sum(_calc_adj_profit(p) for p in resolved_valid)
    units_staked_adj = float(len(resolved_valid))
    yield_rate_adj = (total_profit_adj / units_staked_adj * 100.0) if units_staked_adj > 0 else 0.0

    # ── Cálculo CLV Promedio ──
    clv_values = []
    for p in picks:
        raw_p = p.get("raw_pick") or {}
        cl_odds = raw_p.get("closing_odds") or p.get("closing_odds")
        odds = p.get("odds", 0.0)
        if cl_odds and odds > 1.0:
            try:
                own_implied = 1.0 / float(odds)
                closing_implied = 1.0 / float(cl_odds)
                clv_pct = (closing_implied - own_implied) / closing_implied * 100.0
                clv_values.append(clv_pct)
            except Exception:
                pass
    avg_clv = round(sum(clv_values) / len(clv_values), 2) if clv_values else None

    avg_odds = (sum(p["odds"] for p in picks) / total_picks) if total_picks > 0 else 0.0
    avg_winning_odds = (sum(p["odds"] for p in picks_won) / won_count) if won_count > 0 else 0.0
    break_even_rate = (1.0 / avg_odds * 100.0) if avg_odds > 1.0 else 0.0

    avg_edge = (sum(p["edge"] for p in picks) / total_picks) if total_picks > 0 else 0.0
    avg_kelly = (sum(p["kelly"] for p in picks) / total_picks) if total_picks > 0 else 0.0

    kpis = DashboardKPIs(
        total_analyses=total_analyses,
        total_picks=total_picks,
        picks_resolved=picks_resolved_count,
        picks_pending=pending_count,
        picks_won=won_count,
        picks_lost=lost_count,
        picks_push=push_count,
        picks_void=void_count,
        hit_rate=round(hit_rate, 2),
        roi=round(roi, 2),
        net_profit=round(total_profit, 2),
        units_staked=round(units_staked, 2),
        avg_odds=round(avg_odds, 3),
        avg_winning_odds=round(avg_winning_odds, 3),
        break_even_rate=round(break_even_rate, 2),
        avg_edge=round(avg_edge, 4),
        yield_rate=round(yield_rate, 2),
        avg_kelly=round(avg_kelly, 4),
        clv=avg_clv,
        net_profit_adjusted=round(total_profit_adj, 2),
        yield_rate_adjusted=round(yield_rate_adj, 2),
        units_staked_adjusted=round(units_staked_adj, 2),
        avg_clv=avg_clv,
    )

    # ── Model Quality & Calibration Bands ──
    avg_model_prob = (sum(p["model_prob"] for p in picks) / total_picks) if total_picks > 0 else 0.0
    avg_implied_prob = (sum(p["implied_prob"] for p in picks) / total_picks) if total_picks > 0 else 0.0

    # Calibration bands: 50-55%, 55-60%, 60-65%, 65-70%, 70%+
    bands_def = [
        ("50-55%", 0.50, 0.55),
        ("55-60%", 0.55, 0.60),
        ("60-65%", 0.60, 0.65),
        ("65-70%", 0.65, 0.70),
        ("70%+", 0.70, 1.00),
    ]

    calibration_bands: List[CalibrationBand] = []
    brier_sq_errors = []

    for label, b_min, b_max in bands_def:
        b_picks = [p for p in resolved_valid if b_min <= p["model_prob"] < (b_max if b_max < 1.0 else 1.01)]
        b_total = len(b_picks)
        if b_total > 0:
            b_won = len([p for p in b_picks if p["status"] == "won"])
            b_actual_hit = (b_won / b_total) * 100.0
            b_avg_prob = (sum(p["model_prob"] for p in b_picks) / b_total) * 100.0
            diff = b_actual_hit - b_avg_prob
        else:
            b_actual_hit = 0.0
            b_avg_prob = ((b_min + b_max) / 2.0) * 100.0
            diff = 0.0

        calibration_bands.append(
            CalibrationBand(
                band=label,
                total_picks=b_total,
                avg_model_prob=round(b_avg_prob, 2),
                actual_hit_rate=round(b_actual_hit, 2),
                diff=round(diff, 2),
            )
        )

    for p in resolved_valid:
        if p["status"] in ("won", "lost"):
            actual_binary = 1.0 if p["status"] == "won" else 0.0
            brier_sq_errors.append((p["model_prob"] - actual_binary) ** 2)

    brier_score = (sum(brier_sq_errors) / len(brier_sq_errors)) if brier_sq_errors else None

    actual_vs_exp_diff = (hit_rate - (avg_model_prob * 100.0))

    quality = ModelQualityMetrics(
        avg_model_prob=round(avg_model_prob * 100.0, 2),
        avg_implied_prob=round(avg_implied_prob * 100.0, 2),
        avg_edge=round(avg_edge * 100.0, 2),
        actual_vs_expected_diff=round(actual_vs_exp_diff, 2),
        brier_score=round(brier_score, 4) if brier_score is not None else None,
        calibration_bands=calibration_bands,
    )

    # ── Cumulative Yield Curve (Daily) ──
    daily_profit_map: Dict[str, Tuple[float, int]] = {}
    for p in resolved_valid:
        d_str = p["match_date"].strftime("%Y-%m-%d") if isinstance(p["match_date"], datetime) else str(p["match_date"])[:10]
        cur_prof, cur_cnt = daily_profit_map.get(d_str, (0.0, 0))
        daily_profit_map[d_str] = (cur_prof + p["profit"], cur_cnt + 1)

    sorted_dates = sorted(daily_profit_map.keys())
    cumulative_points: List[AccumulatedYieldPoint] = []
    running_tot = 0.0

    for d in sorted_dates:
        p_day, c_day = daily_profit_map[d]
        running_tot += p_day
        cumulative_points.append(
            AccumulatedYieldPoint(
                date=d,
                profit=round(p_day, 2),
                cumulative_profit=round(running_tot, 2),
                picks_count=c_day,
            )
        )

    # Helper for grouped rankings
    def _calc_rankings(key_func, label_name, filter_min_sample=True) -> List[ChartDataPoint]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for p in resolved_valid:
            k = key_func(p) or "Desconocido"
            groups.setdefault(k, []).append(p)

        res = []
        for k, p_list in groups.items():
            if filter_min_sample and len(p_list) < min_sample:
                continue
            stk = sum(x["stake"] for x in p_list)
            prof = sum(x["profit"] for x in p_list)
            g_roi = (prof / stk * 100.0) if stk > 0 else 0.0
            g_hits = len([x for x in p_list if x["status"] == "won"])
            g_hit_rate = (g_hits / len(p_list) * 100.0) if p_list else 0.0
            res.append(
                ChartDataPoint(
                    label=k,
                    value=round(g_roi, 2),
                    extra={
                        "picks": len(p_list),
                        "profit": round(prof, 2),
                        "staked": round(stk, 2),
                        "hit_rate": round(g_hit_rate, 2),
                    },
                )
            )
        return sorted(res, key=lambda x: x.value, reverse=True)

    roi_by_league = _calc_rankings(lambda p: p["competition"], "Liga")
    roi_by_market = _calc_rankings(lambda p: p["market"], "Mercado")
    
    # Team ROI parsing from title
    def _extract_team(p):
        title = p["match_title"]
        if " vs " in title:
            return title.split(" vs ")[0].strip()
        elif " - " in title:
            return title.split(" - ")[0].strip()
        return title

    roi_by_team = _calc_rankings(_extract_team, "Equipo")

    # Range Performance
    def _odds_bucket(odds):
        if odds < 1.50:
            return "< 1.50"
        elif odds < 1.80:
            return "1.50 - 1.80"
        elif odds < 2.20:
            return "1.80 - 2.20"
        elif odds < 3.00:
            return "2.20 - 3.00"
        return "3.00+"

    def _edge_bucket(edge):
        if edge < 0.02:
            return "< 2%"
        elif edge < 0.05:
            return "2% - 5%"
        elif edge < 0.10:
            return "5% - 10%"
        return "10%+"

    perf_by_odds = _calc_rankings(lambda p: _odds_bucket(p["odds"]), "Cuota", filter_min_sample=False)
    perf_by_edge = _calc_rankings(lambda p: _edge_bucket(p["edge"]), "Edge", filter_min_sample=False)

    charts = DashboardChartsData(
        cumulative_yield=cumulative_points,
        roi_by_league=roi_by_league,
        roi_by_market=roi_by_market,
        roi_by_team=roi_by_team,
        performance_by_odds_range=perf_by_odds,
        performance_by_edge_range=perf_by_edge,
        outcome_distribution={
            "won": won_count,
            "lost": lost_count,
            "push": push_count,
            "void": void_count,
            "pending": pending_count,
        },
        expected_vs_actual_calibration=calibration_bands,
    )

    return DashboardSummaryOut(kpis=kpis, quality=quality, charts=charts)


def get_grouped_stats(
    db: Session,
    group_by: str = "competition",
    min_sample: int = 1,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> StatsGroupedOut:
    """Group picks by specified dimension and compute detailed metrics per segment."""
    analyses = _filter_analyses_by_params(db, date_from=date_from, date_to=date_to)
    picks = _get_flattened_picks(analyses)

    def _group_key(p: Dict[str, Any]) -> str:
        gb = group_by.lower()
        if gb == "competition" or gb == "liga":
            return p.get("competition") or "Sin Competición"
        elif gb == "market" or gb == "mercado":
            return p.get("market") or "General"
        elif gb == "category" or gb == "categoria":
            return p.get("category") or "Normal"
        elif gb == "bookmaker" or gb == "casa":
            return p.get("bookmaker") or "Genérico"
        elif gb == "status" or gb == "estado":
            return p.get("status") or "desconocido"
        elif gb == "odds_range":
            odds = p.get("odds", 1.0)
            if odds < 1.50: return "< 1.50"
            if odds < 1.80: return "1.50-1.80"
            if odds < 2.20: return "1.80-2.20"
            if odds < 3.00: return "2.20-3.00"
            return "3.00+"
        elif gb == "edge_range":
            edge = p.get("edge", 0.0)
            if edge < 0.02: return "< 2%"
            if edge < 0.05: return "2%-5%"
            if edge < 0.10: return "5%-10%"
            return "10%+"
        return p.get("competition") or "Otros"

    segments: Dict[str, List[Dict[str, Any]]] = {}
    for p in picks:
        k = _group_key(p)
        segments.setdefault(k, []).append(p)

    items: List[GroupedStatItem] = []
    for seg_name, seg_picks in segments.items():
        if len(seg_picks) < min_sample:
            continue

        tot = len(seg_picks)
        won = [x for x in seg_picks if x["status"] == "won"]
        lost = [x for x in seg_picks if x["status"] == "lost"]
        push = [x for x in seg_picks if x["status"] == "push"]
        void = [x for x in seg_picks if x["status"] == "cancelled"]
        pending = [x for x in seg_picks if x["status"] == "pending"]

        resolved = won + lost + push
        res_cnt = len(resolved)

        w_cnt = len(won)
        l_cnt = len(lost)
        p_cnt = len(push)
        v_cnt = len(void)
        pend_cnt = len(pending)

        hit_rate = (w_cnt / (w_cnt + l_cnt) * 100.0) if (w_cnt + l_cnt) > 0 else 0.0
        tot_stk = sum(x["stake"] for x in resolved)
        avg_stk = (tot_stk / res_cnt) if res_cnt > 0 else 0.0
        net_prof = sum(x["profit"] for x in resolved)
        roi = (net_prof / tot_stk * 100.0) if tot_stk > 0 else 0.0
        avg_odds = (sum(x["odds"] for x in seg_picks) / tot) if tot > 0 else 0.0
        avg_win_odds = (sum(x["odds"] for x in won) / w_cnt) if w_cnt > 0 else 0.0
        be_rate = (1.0 / avg_odds * 100.0) if avg_odds > 1.0 else 0.0

        avg_edge = (sum(x["edge"] for x in seg_picks) / tot) if tot > 0 else 0.0
        avg_kelly = (sum(x["kelly"] for x in seg_picks) / tot) if tot > 0 else 0.0
        avg_mod_prob = (sum(x["model_prob"] for x in seg_picks) / tot) if tot > 0 else 0.0
        avg_imp_prob = (sum(x["implied_prob"] for x in seg_picks) / tot) if tot > 0 else 0.0

        act_vs_mod = hit_rate - (avg_mod_prob * 100.0)

        # Drawdown & streaks calculation
        peak = 0.0
        curr_cum = 0.0
        max_dd = 0.0
        max_win_streak = 0
        max_lose_streak = 0
        curr_win_streak = 0
        curr_lose_streak = 0

        for r in resolved:
            prof = r["profit"]
            curr_cum += prof
            if curr_cum > peak:
                peak = curr_cum
            dd = peak - curr_cum
            if dd > max_dd:
                max_dd = dd

            if r["status"] == "won":
                curr_win_streak += 1
                curr_lose_streak = 0
                if curr_win_streak > max_win_streak:
                    max_win_streak = curr_win_streak
            elif r["status"] == "lost":
                curr_lose_streak += 1
                curr_win_streak = 0
                if curr_lose_streak > max_lose_streak:
                    max_lose_streak = curr_lose_streak

        items.append(
            GroupedStatItem(
                segment_name=seg_name,
                total_picks=tot,
                resolved_picks=res_cnt,
                pending_picks=pend_cnt,
                won_picks=w_cnt,
                lost_picks=l_cnt,
                push_picks=p_cnt,
                void_picks=v_cnt,
                hit_rate=round(hit_rate, 2),
                avg_odds=round(avg_odds, 3),
                avg_winning_odds=round(avg_win_odds, 3),
                total_stake=round(tot_stk, 2),
                avg_stake=round(avg_stk, 2),
                net_profit=round(net_prof, 2),
                roi=round(roi, 2),
                yield_rate=round(roi, 2),
                break_even_rate=round(be_rate, 2),
                avg_edge=round(avg_edge, 4),
                avg_kelly=round(avg_kelly, 4),
                avg_model_prob=round(avg_mod_prob * 100.0, 2),
                avg_implied_prob=round(avg_imp_prob * 100.0, 2),
                actual_vs_model_diff=round(act_vs_mod, 2),
                max_drawdown=round(max_dd, 2),
                max_losing_streak=max_lose_streak,
                max_winning_streak=max_win_streak,
            )
        )

    items.sort(key=lambda x: x.roi, reverse=True)
    return StatsGroupedOut(group_by=group_by, min_sample=min_sample, items=items)


def detect_data_anomalies(db: Session) -> StatsAnomaliesOut:
    """Scan database for operational data anomalies (invalid odds, negative stakes, probability out of bounds)."""
    analyses = db.query(AnalysisHistory).all()
    anomalies: List[DataAnomalyItem] = []

    for ah in analyses:
        extracted = _extract_picks_from_analysis(ah)
        for p in extracted:
            if p["odds"] <= 1.0:
                anomalies.append(
                    DataAnomalyItem(
                        analysis_id=ah.id,
                        match_title=ah.match_title,
                        competition=ah.competition,
                        anomaly_type="invalid_odds",
                        description=f"Cuota inválida ({p['odds']}) registrada para {p['selection']}",
                        severity="high",
                    )
                )
            if p["stake"] <= 0.0:
                anomalies.append(
                    DataAnomalyItem(
                        analysis_id=ah.id,
                        match_title=ah.match_title,
                        competition=ah.competition,
                        anomaly_type="invalid_stake",
                        description=f"Stake nulo o negativo ({p['stake']}) registrado para {p['selection']}",
                        severity="medium",
                    )
                )
            if p["model_prob"] < 0.0 or p["model_prob"] > 1.0:
                anomalies.append(
                    DataAnomalyItem(
                        analysis_id=ah.id,
                        match_title=ah.match_title,
                        competition=ah.competition,
                        anomaly_type="invalid_probability",
                        description=f"Probabilidad fuera del rango 0-1 ({p['model_prob']}) para {p['selection']}",
                        severity="high",
                    )
                )
            if abs(p["edge"]) > 0.5:
                anomalies.append(
                    DataAnomalyItem(
                        analysis_id=ah.id,
                        match_title=ah.match_title,
                        competition=ah.competition,
                        anomaly_type="extreme_edge",
                        description=f"Edge extremo detectado ({p['edge']*100:.1f}%) para {p['selection']}",
                        severity="medium",
                    )
                )

    return StatsAnomaliesOut(total_anomalies=len(anomalies), anomalies=anomalies)


def export_stats_file(
    db: Session,
    export_format: str = "csv",
    group_by: str = "competition",
) -> Tuple[bytes, str, str]:
    """Export filtered stats table to CSV or Excel bytes."""
    grouped = get_grouped_stats(db, group_by=group_by, min_sample=1)
    df = pd.DataFrame([item.model_dump() for item in grouped.items])

    filename = f"sherlock_admin_stats_{group_by}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if export_format.lower() == "excel" or export_format.lower() == "xlsx":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Estadísticas")
        content = output.getvalue()
        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        full_filename = f"{filename}.xlsx"
    else:
        content = df.to_csv(index=False).encode("utf-8")
        mime_type = "text/csv"
        full_filename = f"{filename}.csv"

    return content, mime_type, full_filename
