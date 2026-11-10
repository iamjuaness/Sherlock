"""Rutas leagues de la API (extraídas de main.py)."""

from __future__ import annotations

import json
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.domain import AnalysisHistory
from src.ui.api.schemas import (
    AnalysisHistoryOut,
)
import os

from src.ui.api.routes.analysis_routes import apply_blacklist
from src.ui.api.shared import (
    BlacklistMarketRequest,
    BlacklistMarketsBatchRequest,
    MIN_STAKE,
    PROFITABLE_LEAGUES_PATH,
    ReduceStakeMarketRequest,
    SegmentGovernanceActionRequest,
    SegmentGovernanceBatchActionRequest,
    _API_DIR,
    _calculate_pick_profit,
    _check_pick_success,
    _populate_history_extra_fields,
    _resolve_stake_from_pick,
    _update_segment_governance_file,
    get_profitable_leagues,
    save_profitable_leagues,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/api/v1/leagues/{league_name}/matches",
    response_model=list[AnalysisHistoryOut],
    tags=["Leagues"],
)
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
                AnalysisHistory.payload.like(f'%"{comp_str}"%'),
            ),
        )
    )

    if season and season.strip().lower() != "all":
        s_str = season.strip()
        season_conds = [
            AnalysisHistory.season_year == s_str,
            AnalysisHistory.season_label == s_str,
        ]
        if s_str.isdigit():
            season_conds.append(func.strftime("%Y", AnalysisHistory.match_date) == s_str)
            season_conds.append(func.strftime("%Y", AnalysisHistory.date) == s_str)
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


@router.get("/api/v1/leagues/{league_name}/markets", tags=["Leagues"])
def get_league_markets(
    league_name: str, use_stake: bool = Query(False), db: Session = Depends(get_db)
):
    """
    Obtiene las estadísticas agregadas de mercados (desglose por tipo)
    para una única competición directamente filtrada en BD, incluyendo
    mercados resueltos y pendientes.
    """
    import re
    from sqlalchemy.orm import load_only

    history = (
        db.query(AnalysisHistory)
        .filter(AnalysisHistory.competition == league_name)
        .options(
            load_only(
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
            )
        )
        .all()
    )

    det_map = {}
    for h in history:
        if getattr(h, "count_in_profitability", True) is False:
            continue
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

                # ── Resolución de categoría y nombre canónico de mercado ──
                sel_text = pick.get("selection", "")
                lower_sel = sel_text.strip().lower()
                category = ""
                if "corner" in lower_sel or "córner" in lower_sel:
                    category = "Córners"
                elif "tarjeta" in lower_sel or "card" in lower_sel or "amarilla" in lower_sel:
                    category = "Tarjetas"
                elif "foul" in lower_sel or "falta" in lower_sel:
                    category = "Faltas"
                elif (
                    "shot_target" in lower_sel
                    or "tiro_a_puerta" in lower_sel
                    or "shots_target" in lower_sel
                    or "pta" in lower_sel
                ):
                    category = "Tiros a puerta"
                elif "shot" in lower_sel or "tiro" in lower_sel or "remate" in lower_sel:
                    category = "Tiros"
                elif "goal" in lower_sel or "gol" in lower_sel:
                    category = "Goles"

                line_val = pick.get("line")
                line_bucket = pick.get("line_bucket")
                if line_val is None:
                    num_match = re.search(r"(\d+(?:\.\d+)?)", sel_text)
                    if num_match:
                        try:
                            line_val = float(num_match.group(1))
                        except ValueError:
                            pass

                bucket_str = f" ({line_bucket})" if line_bucket and line_bucket != "no_line" else ""
                line_str = f" {line_val}" if line_val is not None else ""

                sel_key = sel_text.strip()
                if category:
                    if "over" in lower_sel or "más de" in lower_sel or "mas de" in lower_sel:
                        sel_key = f"Over {category}{line_str}{bucket_str}"
                    elif "under" in lower_sel or "menos de" in lower_sel:
                        sel_key = f"Under {category}{line_str}{bucket_str}"
                    else:
                        sel_key = f"{category}{line_str}{bucket_str}"

                if sel_key not in det_map:
                    det_map[sel_key] = {
                        "name": sel_key,
                        "totalPicks": 0,
                        "pendientes": 0,
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

                # ── Si no tiene resultado aún, se contabiliza como pendiente ──
                if not has_result:
                    m_entry["pendientes"] += 1
                    continue

                # ── Si ya tiene resultado, se evalúa éxito/fracaso/profit ──
                success = _check_pick_success(pick, res_dict)
                if success is not None:
                    stake = _resolve_stake_from_pick(pick) if use_stake else MIN_STAKE
                    pick_profit = _calculate_pick_profit(success, odds_val) * stake

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


@router.post("/api/v1/leagues/{league_name}/profitability", tags=["Leagues"])
def update_league_profitability(
    league_name: str, count_in_profitability: bool = Query(...), db: Session = Depends(get_db)
):
    """
    Actualiza la rentabilidad de una liga completa y todos sus partidos en el historial.
    """
    history_list = (
        db.query(AnalysisHistory).filter(AnalysisHistory.competition == league_name).all()
    )
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
                cname = (
                    pdata.get("competition")
                    or pdata.get("tournament", {}).get("name")
                    or "Desconocida"
                )
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
        "message": f"Se actualizó la rentabilidad a '{count_in_profitability}' en {updated_count} partidos de '{league_name}'.",
    }


@router.post("/api/v1/leagues/governance/action", tags=["Leagues Governance"])
def segment_governance_action(req: SegmentGovernanceActionRequest, db: Session = Depends(get_db)):
    """Aplica una acción de gobernanza (block, reduce, reset) a un mercado de una liga sin recalcular historial."""
    try:
        key = _update_segment_governance_file(
            req.league, req.market_name, req.action, req.stake_multiplier
        )
        return {
            "status": "ok",
            "target_key": key,
            "message": f"Acción '{req.action}' registrada en segment_governance para '{key}' de '{req.league}'.",
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en gobernanza de segmento: {e}")


@router.post("/api/v1/leagues/governance/batch-action", tags=["Leagues Governance"])
def segment_governance_batch_action(
    req: SegmentGovernanceBatchActionRequest, db: Session = Depends(get_db)
):
    """Aplica una acción de gobernanza en lote a varios mercados de una liga sin recalcular historial."""
    try:
        updated_keys = []
        for m_name in req.markets:
            if m_name:
                k = _update_segment_governance_file(
                    req.league, m_name, req.action, req.stake_multiplier
                )
                updated_keys.append(k)
        return {
            "status": "ok",
            "updated_keys": updated_keys,
            "message": f"Acción '{req.action}' registrada en segment_governance para {len(updated_keys)} mercados de '{req.league}'.",
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en gobernanza de segmento en lote: {e}")


@router.post("/api/v1/leagues/blacklist-markets", tags=["Leagues"])
def blacklist_markets_batch(
    req: BlacklistMarketsBatchRequest,
    db: Session = Depends(get_db),
):
    """
    Agrega mercados a la blacklist con la estructura canónica original (lista de dicts):
    [
      {
        "league": "...",
        "market_family": "result",
        "market_side": "away", # o "home", "draw", "over", "under"
        "line": null           # o float para mercados con línea
      }
    ]
    Garantiza compatibilidad total con is_market_blacklisted_for_league y apply_blacklist.
    """
    import json
    import os
    import re
    import traceback
    from fastapi import HTTPException

    from src.ui.api.compare import (
        _market_family,
        _market_side,
        _market_line,
    )

    penalties_path = os.path.join(
        _API_DIR,
        "..",
        "..",
        "..",
        "data",
        "league_penalties.json",
    )

    try:
        entries: list = []
        if os.path.exists(penalties_path):
            # Si el archivo existe pero no se puede leer, abortar: seguir con []
            # sobrescribiría todas las reglas previas y apply_blacklist las desbloquearía.
            with open(penalties_path, "r", encoding="utf-8") as f:
                raw_content = f.read().strip()
            if raw_content:
                loaded = json.loads(raw_content)
                if not isinstance(loaded, list):
                    raise ValueError("league_penalties.json no contiene una lista")
                entries = loaded

        added_count = 0

        for market_str in req.markets:
            clean_market = str(market_str).strip()
            lower_mkt = clean_market.lower()

            family = None
            side = None
            line = None

            # 1. Tratamiento canónico de Resultado Final: Local, Empate, Visitante
            if lower_mkt in ("local", "home", "victoria local", "1") or re.search(
                r"\b(local|victoria local)\b", lower_mkt
            ):
                family = "result"
                side = "home"
                line = None
            elif lower_mkt in ("empate", "draw", "x") or re.search(r"\b(empate|draw)\b", lower_mkt):
                family = "result"
                side = "draw"
                line = None
            elif lower_mkt in ("visitante", "away", "victoria visitante", "2") or re.search(
                r"\b(visitante|victoria visitante)\b", lower_mkt
            ):
                family = "result"
                side = "away"
                line = None
            else:
                # 2. Tiros a puerta vs Tiros generales
                is_shots_target = (
                    "shot_target" in lower_mkt
                    or "shots_target" in lower_mkt
                    or "shots_on_target" in lower_mkt
                    or "tiros a puerta" in lower_mkt
                    or "tiro a puerta" in lower_mkt
                    or "tiro_a_puerta" in lower_mkt
                    or "tiros al arco" in lower_mkt
                    or "tiro al arco" in lower_mkt
                    or "remates a puerta" in lower_mkt
                    or "remates al arco" in lower_mkt
                    or "shots on target" in lower_mkt
                    or "tiros a pta" in lower_mkt
                    or "tiro a pta" in lower_mkt
                    or " a pta" in lower_mkt
                    or bool(re.search(r"\b(sot)\b", lower_mkt))
                )

                if is_shots_target:
                    family = "shots_target"
                else:
                    family = _market_family(clean_market)
                    if not family or family == "generic":
                        if "tiro" in lower_mkt or "shot" in lower_mkt or "remate" in lower_mkt:
                            family = "shots"

                side = _market_side(clean_market)
                line = _market_line(clean_market)

            canonical_side = side.lower() if side and side.lower() != "generic" else None

            new_rule = {
                "league": req.league.strip(),
                "market_family": family,
                "market_side": canonical_side,
                "line": float(line) if line is not None else None,
            }

            # Evitar reglas duplicadas
            already_exists = any(
                r.get("league") == new_rule["league"]
                and r.get("market_family") == new_rule["market_family"]
                and r.get("market_side") == new_rule["market_side"]
                and r.get("line") == new_rule["line"]
                for r in entries
                if isinstance(r, dict)
            )

            if not already_exists:
                entries.append(new_rule)
                added_count += 1

        os.makedirs(os.path.dirname(penalties_path), exist_ok=True)
        tmp_path = penalties_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, penalties_path)  # escritura atómica

        # Aplicar blacklist automáticamente al historial
        res = apply_blacklist(db=db)

        return {
            "status": "ok",
            "message": (
                f"{added_count} mercados agregados a la blacklist de '{req.league}'. "
                f"{res.get('message', '')}"
            ),
            "apply_blacklist_result": res,
        }

    except HTTPException:
        raise

    except Exception as exc:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(f"Error al agregar mercados a la blacklist: {exc}"),
        )


@router.post("/api/v1/leagues/blacklist-market", tags=["Leagues"])
def blacklist_market(
    req: BlacklistMarketRequest,
    db: Session = Depends(get_db),
):
    """
    Agrega un mercado con línea opcional a la blacklist
    y vuelve a aplicarla al historial.
    """
    return blacklist_markets_batch(
        req=BlacklistMarketsBatchRequest(
            league=req.league,
            markets=[req.market_name],
        ),
        db=db,
    )


@router.post("/api/v1/leagues/reduce-stake-market", tags=["Leagues"])
def reduce_stake_market(req: ReduceStakeMarketRequest, db: Session = Depends(get_db)):
    return segment_governance_action(
        req=SegmentGovernanceActionRequest(
            league=req.league,
            market_name=req.market_name,
            action="reduce",
            stake_multiplier=req.stake_modifier,
        ),
        db=db,
    )
