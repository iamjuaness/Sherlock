"""Rutas analysis de la API (extraídas de main.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
import json
import traceback
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from src.core.database import get_db
from src.core.domain import Sport, AnalysisHistory
from src.ui.api.schemas import (
    AnalysisSave,
    AnalysisHistoryOut,
    AnalysisResultsUpdate,
)
from src.ui.api.compare_service import compare_football
from src.ui.api.compare_models import FootballCompareRequest
import os

from src.ui.api.shared import (
    MIN_STAKE,
    _API_DIR,
    _SkipPriorParams,
    _annotate_best_bookmaker,
    _apply_line_shopping,
    _check_payload_has_odds,
    _check_pick_success,
    _extract_bookmaker,
    _extract_competition,
    _get_cache,
    _invalidate_stats_cache,
    _is_pick_hit,
    _populate_history_extra_fields,
    _set_cache,
    _sum_stake_from_picks,
    is_league_profitable,
)
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/v1/analysis", response_model=AnalysisHistoryOut, tags=["Analysis History"])
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
                    and_(
                        AnalysisHistory.match_date >= date_start,
                        AnalysisHistory.match_date <= date_end,
                    ),
                    and_(
                        AnalysisHistory.match_date == None,
                        AnalysisHistory.date >= date_start,
                        AnalysisHistory.date <= date_end,
                    ),
                )
            )
        else:
            # Si no viene fecha, asume que es un partido reciente (evita mezclar con temporadas anteriores)
            date_start = datetime.utcnow() - timedelta(days=3)
            query = query.filter(AnalysisHistory.date >= date_start)

        existing = query.order_by(AnalysisHistory.date.desc()).first()

    # ── Calcular parámetros previos, ventanas de forma reciente (5, 10, 15) y hit rates empíricos ──
    from datetime import datetime, timezone
    from src.core.math_engine import LeagueMathEngine, get_league_profile
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
            AnalysisHistory.final_score_away.isnot(None),
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
                prior_records.append(
                    {
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
                    }
                )

        if prior_records:
            profile = get_league_profile(comp_name)
            l_hl = profile.get("league_prior_half_life_days", 420.0)
            t_hl = profile.get("team_half_life_matches", 10.0)
            min_ess = profile.get("min_effective_sample_size", 1.0)
            prior_str = profile.get("league_prior_strength", 12.0)

            if not pre_match_data:
                avg_engine = LeagueMathEngine.compute_league_averages(
                    prior_records,
                    reference_date=record_date,
                    half_life_days=l_hl,
                    min_effective_sample_size=min_ess,
                    competition_id=comp_name,
                )
                pre_match_data = {"league_averages": avg_engine, "sample_size": len(prior_records)}

            if not recent_form_data:
                recent_form_data = {
                    "home": LeagueMathEngine.compute_recent_form_windows(
                        prior_records, h_name, windows=[5, 10, 15]
                    ),
                    "away": LeagueMathEngine.compute_recent_form_windows(
                        prior_records, a_name, windows=[5, 10, 15]
                    ),
                }

            if not pick_rates_data:
                league_prior_over25 = LeagueMathEngine.compute_league_pick_hit_rate(
                    prior_records, "goals", 2.5, is_over=True, current_match_date=record_date
                )
                pick_rates_data = {
                    "home_over25_home": LeagueMathEngine.compute_pick_hit_rate_recency(
                        prior_records,
                        h_name,
                        "goals",
                        2.5,
                        is_over=True,
                        role_filter="home",
                        current_match_date=record_date,
                        prior_rate=league_prior_over25,
                        half_life=t_hl,
                        prior_strength=prior_str,
                    ),
                    "away_over25_away": LeagueMathEngine.compute_pick_hit_rate_recency(
                        prior_records,
                        a_name,
                        "goals",
                        2.5,
                        is_over=True,
                        role_filter="away",
                        current_match_date=record_date,
                        prior_rate=league_prior_over25,
                        half_life=t_hl,
                        prior_strength=prior_str,
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
            existing.pre_match_stats = (
                json.dumps(pre_match_data)
                if not isinstance(pre_match_data, str)
                else pre_match_data
            )
        if recent_form_data is not None:
            existing.recent_form_stats = (
                json.dumps(recent_form_data)
                if not isinstance(recent_form_data, str)
                else recent_form_data
            )
        if pick_rates_data is not None:
            existing.historical_pick_rates = (
                json.dumps(pick_rates_data)
                if not isinstance(pick_rates_data, str)
                else pick_rates_data
            )

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
        llm_timestamp=req.llm_timestamp
        or (datetime.now(timezone.utc) if req.llm_response else None),
        needs_reanalysis=req.needs_reanalysis or False,
        compare_response_snapshot=json.dumps(req.compare_response_snapshot)
        if req.compare_response_snapshot
        else None,
        count_in_profitability=count_in_prof_val,
        has_real_stats=has_real_stats_val,
        pre_match_stats=json.dumps(pre_match_data)
        if pre_match_data and not isinstance(pre_match_data, str)
        else (pre_match_data if isinstance(pre_match_data, str) else None),
        recent_form_stats=json.dumps(recent_form_data)
        if recent_form_data and not isinstance(recent_form_data, str)
        else (recent_form_data if isinstance(recent_form_data, str) else None),
        historical_pick_rates=json.dumps(pick_rates_data)
        if pick_rates_data and not isinstance(pick_rates_data, str)
        else (pick_rates_data if isinstance(pick_rates_data, str) else None),
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


@router.post(
    "/api/v1/analysis/quick-save", response_model=AnalysisHistoryOut, tags=["Analysis History"]
)
def quick_save_match(payload: dict, db: Session = Depends(get_db)) -> AnalysisHistoryOut:
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
        "odds": payload.get("odds", {}),
        **{k: payload[k] for k in ("season_id", "season_year", "season") if payload.get(k) is not None},
    }

    from datetime import timedelta, datetime

    # Intentar extraer match_date del payload para buscar coincidencias
    match_date_str = payload.get("match_date")

    query = db.query(AnalysisHistory).filter(
        AnalysisHistory.sport == sport_enum, AnalysisHistory.match_title == match_title
    )

    if match_date_str:
        try:
            # Parsear la fecha del payload
            if "T" in match_date_str:
                dt = datetime.fromisoformat(match_date_str)
            else:
                dt = datetime.strptime(match_date_str[:10], "%Y-%m-%d")

            date_start = dt - timedelta(days=1)
            date_end = dt + timedelta(days=1)
            query = query.filter(
                or_(
                    and_(
                        AnalysisHistory.match_date >= date_start,
                        AnalysisHistory.match_date <= date_end,
                    ),
                    and_(
                        AnalysisHistory.match_date == None,
                        AnalysisHistory.date >= date_start,
                        AnalysisHistory.date <= date_end,
                    ),
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


@router.delete("/api/v1/analysis/competition/{competition_name}", tags=["Analysis History"])
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
        "message": f"Se borraron {deleted_count} partidos de la competición '{competition_name}'.",
    }


@router.put("/api/v1/analysis/competition/{old_name}", tags=["Analysis History"])
def rename_competition_matches(old_name: str, new_name: str, db: Session = Depends(get_db)):
    """
    Cambia el nombre de una competición en el payload y en la columna desnormalizada 'competition' de todos los partidos asociados.
    """
    from sqlalchemy import func as _func
    from src.core.entity_resolver import purge_orphans

    # Solo las filas de esa liga (antes se cargaban las 47k con todo su payload).
    _cond = _func.lower(_func.trim(AnalysisHistory.competition)) == old_name.strip().lower()
    if old_name.strip().lower() == "desconocida":
        _cond = or_(_cond, AnalysisHistory.competition.is_(None))
    history_list = db.query(AnalysisHistory).filter(_cond).all()
    updated_count = 0

    for h in history_list:
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
        db.flush()
        purge_orphans(db)
        db.commit()
        _invalidate_stats_cache()

    return {
        "status": "ok",
        "updated_count": updated_count,
        "message": f"Se actualizó la competición de '{old_name}' a '{new_name}' en {updated_count} partidos.",
    }


@router.put("/api/v1/analysis/team/{old_name}", tags=["Analysis History"])
def rename_team_matches(
    old_name: str,
    new_name: str,
    competition: str = Query(
        None, description="Opcional. Renombra el equipo solo en esta competición."
    ),
    db: Session = Depends(get_db),
):
    """
    Cambia el nombre de un equipo en el payload JSON y en el matchtitle
    de todos los partidos históricos asociados. Opcionalmente filtrado por liga.
    """
    # Filtrar solo los partidos cuyo título contenga el nombre antiguo
    from src.core.entity_resolver import find_team_id, purge_orphans

    _tid = find_team_id(db, old_name)
    if _tid:
        _team_cond = or_(AnalysisHistory.home_team_id == _tid, AnalysisHistory.away_team_id == _tid)
    else:
        _team_cond = AnalysisHistory.match_title.ilike(f"%{old_name}%")
    history_list = db.query(AnalysisHistory).filter(_team_cond).all()
    updated_count = 0

    for h in history_list:
        if h.payload:
            try:
                # Decodificar el payload
                pdata = json.loads(h.payload) if isinstance(h.payload, str) else h.payload

                # Si se especificó competición, validar que coincida antes de modificar
                if competition:
                    cname = (
                        h.competition
                        or pdata.get("competition")
                        or pdata.get("tournament", {}).get("name")
                        or "Desconocida"
                    )
                    if cname.lower() != competition.lower():
                        continue  # Si no es de esta liga, saltar

                changed = False

                # 1. Actualizar dentro de los objetos 'home' y 'away'
                if (
                    isinstance(pdata.get("home"), dict)
                    and pdata["home"].get("name", "").lower() == old_name.lower()
                ):
                    pdata["home"]["name"] = new_name
                    changed = True

                if (
                    isinstance(pdata.get("away"), dict)
                    and pdata["away"].get("name", "").lower() == old_name.lower()
                ):
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
                            new_parts = [
                                new_name if p.lower() == old_name.lower() else p for p in parts
                            ]
                            if len(new_parts) == 2:
                                h.match_title = f"{new_parts[0]} vs {new_parts[1]}"

                        elif " - " in h.match_title:
                            parts = [p.strip() for p in h.match_title.split(" - ")]
                            new_parts = [
                                new_name if p.lower() == old_name.lower() else p for p in parts
                            ]
                            if len(new_parts) == 2:
                                h.match_title = f"{new_parts[0]} - {new_parts[1]}"

                    updated_count += 1
            except Exception as e:
                print(f"Error actualizando el nombre del equipo (ID: {h.id}): {e}")
                continue

    if updated_count > 0:
        db.flush()
        purge_orphans(db)
        db.commit()
        _invalidate_stats_cache()

    response_msg = (
        f"Se actualizó el equipo de '{old_name}' a '{new_name}' en {updated_count} partidos"
    )
    if competition:
        response_msg += f" de la competición '{competition}'."
    else:
        response_msg += " (Globalmente)."

    return {"status": "ok", "updated_count": updated_count, "message": response_msg}


@router.delete(
    "/api/v1/analysis/competition/{competition_name}/deduplicate", tags=["Analysis History"]
)
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
            match_date_str = (
                h.match_date.strftime("%Y-%m-%d") if h.match_date else h.date.strftime("%Y-%m-%d")
            )
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
                    isinstance(odds_data, dict)
                    and (
                        odds_data.get("home") is not None
                        or odds_data.get("away") is not None
                        or odds_data.get("draw") is not None
                    )
                )

                sources_data = pdata.get("sources") if isinstance(pdata, dict) else None
                has_sources_odds = False
                if sources_data:
                    if isinstance(sources_data, dict):
                        for src_k, src_v in sources_data.items():
                            if isinstance(src_v, dict) and src_v.get("odds"):
                                src_odds = src_v.get("odds")
                                if isinstance(src_odds, dict) and (
                                    src_odds.get("home") is not None
                                    or src_odds.get("away") is not None
                                    or src_odds.get("draw") is not None
                                ):
                                    has_sources_odds = True
                                    break
                    elif isinstance(sources_data, list):
                        for src_item in sources_data:
                            if isinstance(src_item, dict) and src_item.get("odds"):
                                src_odds = src_item.get("odds")
                                if isinstance(src_odds, dict) and (
                                    src_odds.get("home") is not None
                                    or src_odds.get("away") is not None
                                    or src_odds.get("draw") is not None
                                ):
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
        "message": f"Se eliminaron {deleted_count} registros duplicados (sin cuotas) en la competición '{competition_name}'.",
    }


@router.post("/api/v1/teams/sync", tags=["Analysis History"])
def sync_teams(payload: dict, db: Session = Depends(get_db)):
    """Watson envía los objetos team de SofaScore; se completan los equipos que ya existen en DB."""
    from src.core.entity_resolver import sync_sofascore_team

    teams = payload.get("teams") or []
    updated = sum(1 for t in teams if isinstance(t, dict) and sync_sofascore_team(db, t))
    db.commit()
    return {"status": "ok", "received": len(teams), "updated": updated, "unmatched": len(teams) - updated}


@router.get("/api/v1/teams/aliases", tags=["Analysis History"])
def team_aliases(ext_id: Optional[str] = None, name: Optional[str] = None, db: Session = Depends(get_db)):
    """Nombres conocidos de un equipo (para buscar en Betano/BetPlay). found=false si no existe."""
    from src.core.entity_resolver import get_team_names

    r = get_team_names(db, ext_id, name)
    return {"found": True, **r} if r else {"found": False}


@router.get("/api/v1/analysis/teams/count", tags=["Analysis History"])
def list_teams_count(
    competition: str = Query(
        None, description="Filtra el conteo de equipos por una liga específica"
    ),
    db: Session = Depends(get_db),
):
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
        "teams": sorted_teams,
    }
    _set_cache(cache_key, res)
    return res


@router.delete(
    "/api/v1/analysis/competition/{competition_name}/incomplete",
    tags=["Analysis History"],
)
def delete_incomplete_competition_matches(
    competition_name: str,
    dry_run: bool = Query(
        True, description="Si es true, solo informa qué eliminaría; no borra nada."
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
        tournament_name = tournament.get("name") if isinstance(tournament, dict) else None
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
            isinstance(source, dict) and source for source in sources.values()
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
                json.loads(history.payload) if isinstance(history.payload, str) else history.payload
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

            candidates.append(
                {
                    "id": str(history.id),
                    "matchtitle": history.match_title,
                    "matchdate": (history.match_date.isoformat() if history.match_date else None),
                    "has_valid_odds": valid_odds,
                    "has_calculated_picks": valid_picks,
                }
            )

            if not dry_run:
                db.delete(history)
                deleted_count += 1

        except Exception as exc:
            print(f"Error revisando partido incompleto (ID: {history.id}): {exc}")

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
            else f"Se eliminaron {deleted_count} partidos incompletos de '{competition_name}'."
        ),
    }


@router.get("/api/v1/analysis", response_model=list[AnalysisHistoryOut], tags=["Analysis History"])
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
                    AnalysisHistory.payload.like(f'%"{comp_str}"%'),
                ),
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


@router.get(
    "/api/v1/analysis/{analysis_id}", response_model=AnalysisHistoryOut, tags=["Analysis History"]
)
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


@router.post(
    "/api/v1/analysis/{analysis_id}/results",
    response_model=AnalysisHistoryOut,
    tags=["Analysis History"],
)
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


@router.get("/api/v1/history/matches", tags=["Analysis History"])
def get_history_matches(
    competition: str = Query(..., description="Nombre de la competición"),
    season: Optional[str] = Query(None, description="Temporada, ej. '2026' o '2025/2026'"),
    db: Session = Depends(get_db),
):
    """
    Tarea 3: retorna los partidos ya en DB para una competición/temporada.
    Watson usa esto para calcular la diferencia y extraer sólo los faltantes.
    Respuesta: { matches: [ {event_id, match_date, home, away, key} ] }
    """
    import re as _re
    import unicodedata as _ud

    def _norm(s: str) -> str:
        """Normalizar: minúsculas, sin tildes, trim."""
        if not s:
            return ""
        nfkd = _ud.normalize("NFKD", s)
        return "".join(c for c in nfkd if not _ud.combining(c)).lower().strip()

    q = db.query(
        AnalysisHistory.match_title,
        AnalysisHistory.match_date,
        AnalysisHistory.date,
        AnalysisHistory.payload,
        AnalysisHistory.id,
        AnalysisHistory.final_score_home,
        AnalysisHistory.final_score_away,
        AnalysisHistory.home_team_id,
        AnalysisHistory.away_team_id,
    ).filter(
        AnalysisHistory.competition == competition,
        AnalysisHistory.sport == Sport.FOOTBALL,
        # Sin resultado solo se listan partidos ya terminados (empezaron hace >= 4 h, UTC);
        # los futuros o en juego no se listan, así Watson no los toca ni los borra.
        or_(
            AnalysisHistory.final_score_home.isnot(None),
            and_(
                AnalysisHistory.match_date.isnot(None),
                AnalysisHistory.match_date <= datetime.utcnow() - timedelta(hours=4),
            ),
        ),
    )

    # Filtrar por temporada si se especifica
    if season:
        # "2026/2027" abarca ambos años (la temporada empieza en el primero);
        # también se aceptan filas antiguas con "26/27". Watson afina por season_id.
        years = _re.findall(r"\d{4}", season)
        short = _re.fullmatch(r"\s*(\d{2})\s*/\s*(\d{2})\s*", season)
        if short:
            years = [f"20{short.group(1)}", f"20{short.group(2)}"]
        if years:
            conds = []
            for y in years:
                conds += [
                    AnalysisHistory.date.like(f"{y}%"),
                    AnalysisHistory.match_date.like(f"{y}%"),
                    AnalysisHistory.season_year.like(f"{y}%"),
                    AnalysisHistory.season_label.like(f"{y}%"),
                ]
            if len(years) == 2:
                s_short = f"{years[0][2:]}/{years[1][2:]}"
                conds.append(AnalysisHistory.season_year == s_short)
            q = q.filter(or_(*conds))

    rows = q.all()
    # external_id (SofaScore) de los equipos: Watson empareja por id, no por nombre
    _tids = {i for r in rows for i in (r[7], r[8]) if i}
    team_ext = {}
    if _tids:
        for tid, ext in db.execute(
            text(
                "SELECT id, external_id FROM teams WHERE source='sofascore' AND external_id IS NOT NULL "
                f"AND id IN ({','.join(repr(str(i)) for i in _tids)})"
            )
        ):
            team_ext[tid] = ext
    matches = []
    for row in rows:
        match_title = row[0] or ""
        rec_date = row[1] or row[2]
        payload_str = row[3]
        event_id = None
        season_id = None
        season_year = None
        home = ""
        away = ""
        p: dict = {}

        # Parse payload for event_id and team names
        if payload_str:
            try:
                p = json.loads(str(payload_str))
                season_id = p.get("season_id")
                season_year = p.get("season_year") or p.get("season")
                event_id = (
                    p.get("event_id") or p.get("eventId") or p.get("match", {}).get("external_id")
                )
                home = p.get("home", {}).get("name") or p.get("home_team") or ""
                away = p.get("away", {}).get("name") or p.get("away_team") or ""
            except Exception:
                pass

        # Fallback: parse from match_title "Home vs Away"
        if not home and " vs " in match_title:
            parts = match_title.split(" vs ", 1)
            home = parts[0].strip()
            away = parts[1].strip()

        date_str = ""
        if rec_date:
            try:
                if isinstance(rec_date, str):
                    date_str = rec_date[:10]
                else:
                    date_str = rec_date.strftime("%Y-%m-%d")
            except Exception:
                pass

        # Normalized key for deduplication
        key = f"{date_str}|{_norm(home)}|{_norm(away)}"

        # Inicio en epoch UTC: el start_timestamp de SofaScore guardado, o match_date (UTC naive)
        start_ts = None
        try:
            start_ts = int(p["start_timestamp"]) if p.get("start_timestamp") else None
        except Exception:
            start_ts = None
        if start_ts is None and row[1] is not None and not isinstance(row[1], str):
            start_ts = int(row[1].replace(tzinfo=timezone.utc).timestamp())

        matches.append(
            {
                "id": row[4],
                "start_timestamp": start_ts,
                "has_result": row[5] is not None and row[6] is not None,
                "season_id": str(season_id) if season_id else None,
                "season_year": str(season_year) if season_year else None,
                "event_id": str(event_id) if event_id else None,
                "match_date": date_str,
                "home": home,
                "away": away,
                "home_ext": team_ext.get(row[7]),
                "away_ext": team_ext.get(row[8]),
                "key": key,
            }
        )

    return {"competition": competition, "season": season, "count": len(matches), "matches": matches}


@router.post("/api/v1/history/backfill-season", tags=["Analysis History"])
def backfill_history_season(items: list[dict], db: Session = Depends(get_db)):
    """
    Completa event_id / season_id / season_year en el payload de filas antiguas.
    items: [{id, event_id, season_id, season_year}]. Solo rellena campos vacíos.
    """
    updated = 0
    for it in items:
        h = db.query(AnalysisHistory).filter(AnalysisHistory.id == it.get("id")).first()
        if not h:
            continue
        try:
            p = json.loads(str(h.payload))
        except Exception:
            continue
        changed = False
        for k in ("event_id", "season_id", "season_year"):
            if it.get(k) and not p.get(k):
                p[k] = it[k]
                changed = True
        if changed:
            h.payload = json.dumps(p)
            updated += 1
    db.commit()
    return {"updated": updated}


@router.post("/api/v1/analysis/{analysis_id}/profitability", tags=["Analysis History"])
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


@router.post("/api/v1/analysis/recalculate-accuracy", tags=["Analysis History"])
def recalculate_accuracy_fast(db: Session = Depends(get_db)):
    """
    Recalcula accuracy_percentage y picks_hits_summary para todos los registros
    que tienen resultados registrados, usando los picks ya guardados (NO vuelve
    a correr el motor de predicción). Es muy rápido y se puede usar para
    sincronizar los conteos sin re-analizar.
    """
    history_list = (
        db.query(AnalysisHistory).filter(AnalysisHistory.final_score_home.isnot(None)).all()
    )

    updated = 0
    for history in history_list:
        if not history.picks_calculados:
            continue
        try:
            picks = (
                json.loads(str(history.picks_calculados))
                if isinstance(history.picks_calculados, str)
                else history.picks_calculados
            )
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


@router.get("/api/v1/analysis/recalculate-count", tags=["Analysis History"])
def get_recalculate_count(threshold_date: str | None = Query(None), db: Session = Depends(get_db)):
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
                and_(AnalysisHistory.match_date.is_(None), AnalysisHistory.date >= threshold_dt),
            )
        )
    count = query.count()
    # Estimación basada en ~0.29 segundos por partido
    estimated_seconds = count * 0.29
    return {
        "total": count,
        "estimated_seconds": estimated_seconds,
    }


@router.post("/api/v1/analysis/recalculate-all", tags=["Analysis History"])
async def recalculate_all_accuracy(
    use_general_stats: bool = Query(False),
    threshold_date: str | None = Query(None),
    parallel: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Re-analiza todos los registros del historial:
    1. Vuelve a calcular los picks usando el payload original (motor de predicción),
       aplicando line shopping si el payload trae odds.sources de varias casas.
    2. Actualiza los snapshots y los picks calculados.
    3. Si hay resultados finales, recalcula el acierto (accuracy_percentage).
    """
    import time

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

    rules_path = os.path.join(_API_DIR, "..", "..", "..", "data", "pick_rules.json")
    enabled_rules = []
    if os.path.exists(rules_path):
        try:
            with open(rules_path, "r", encoding="utf-8") as rf:
                all_rules = json.load(rf)
                if isinstance(all_rules, list):
                    enabled_rules = [r for r in all_rules if r.get("enabled", False)]
        except Exception:
            pass

    from sqlalchemy.orm import defer as _defer

    # Columnas pesadas que este endpoint solo escribe (nunca lee): no hidratarlas.
    query = (
        db.query(AnalysisHistory)
        .options(
            _defer(AnalysisHistory.picks_calculados),
            _defer(AnalysisHistory.compare_response_snapshot),
            _defer(AnalysisHistory.llm_response),
            _defer(AnalysisHistory.user_context),
            _defer(AnalysisHistory.pre_match_stats),
            _defer(AnalysisHistory.recent_form_stats),
            _defer(AnalysisHistory.historical_pick_rates),
        )
        .filter(AnalysisHistory.picks_calculados != None)
    )
    if threshold_dt:
        query = query.filter(
            or_(
                AnalysisHistory.match_date >= threshold_dt,
                and_(AnalysisHistory.match_date.is_(None), AnalysisHistory.date >= threshold_dt),
            )
        )
    history_list = query.all()
    total_to_process = len(history_list)
    count = 0
    updated_accuracy_count = 0

    from sqlalchemy import text as _sql_text
    from src.core.compressed_text import unpack as _unpack_text

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

    # ── OPTIMIZACIÓN: Precomputar estadísticas históricas por liga en una sola pasada en memoria ──
    # Evita que cada partido individual en paralelo o secuencial ejecute SELECTs adicionales a la BD
    def _compute_shared_league_stats() -> dict[str, dict]:
        """Estadísticas por liga en una pasada; en modo paralelo corre mientras los workers arrancan."""
        shared_league_stats: dict[str, dict] = {}
        try:
            from src.ui.api.shared import _check_pick_success, _calculate_pick_profit, _is_pick_hit

            _q_leagues_batch = _sql_text("""
                SELECT competition, picks_calculados,
                       final_score_home, final_score_away,
                       final_corners_home, final_corners_away,
                       final_yellow_cards_home, final_yellow_cards_away,
                       final_shots_home, final_shots_away,
                       final_shots_on_target_home, final_shots_on_target_away,
                       final_fouls_home, final_fouls_away
                FROM analysis_history
                WHERE picks_calculados IS NOT NULL AND competition IS NOT NULL AND sport = 'FOOTBALL'
            """)
            league_batch_rows = db.execute(_q_leagues_batch).mappings().all()
            for l_row in league_batch_rows:
                comp_name = (l_row.get("competition") or "").strip().lower()
                if not comp_name or comp_name in ("desconocida", "general"):
                    continue
                if comp_name not in shared_league_stats:
                    shared_league_stats[comp_name] = {
                        "historical_matches": 0,
                        "historical_picks": 0,
                        "historical_hits": 0,
                        "historical_profit": 0.0,
                    }
                l_entry = shared_league_stats[comp_name]
                l_entry["historical_matches"] += 1

                has_res = (
                    l_row.get("final_score_home") is not None
                    and l_row.get("final_score_away") is not None
                )
                res_d = dict(l_row) if has_res else None

                p_raw = _unpack_text(l_row.get("picks_calculados"))
                if p_raw:
                    try:
                        p_list = json.loads(p_raw) if isinstance(p_raw, str) else p_raw
                        if isinstance(p_list, list):
                            for pk in p_list:
                                if not isinstance(pk, dict):
                                    continue
                                stk = float(pk.get("stake", pk.get("stake_units", 0)) or 0)
                                if stk <= 0:
                                    continue
                                l_entry["historical_picks"] += 1
                                if has_res and res_d:
                                    outcome = _check_pick_success(pk, res_d)
                                    if _is_pick_hit(outcome):
                                        l_entry["historical_hits"] += 1
                                    odds_val = float(pk.get("odds", 1.0) or 1.0)
                                    l_entry["historical_profit"] += _calculate_pick_profit(
                                        outcome, odds_val
                                    )
                    except Exception:
                        pass
        except Exception as ex_ls:
            print(f"Advertencia optimizando league stats batch: {ex_ls}", flush=True)
        return shared_league_stats

    if parallel:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        from src.core.parallel_recalc import _recalc_chunk, init_worker, split_into_chunks, warmup

        n_workers = int(os.environ.get("SHERLOCK_RECALC_WORKERS") or max((os.cpu_count() or 2) - 1, 1))

        matches_plain = []
        for h in history_list:
            m_date_val = h.match_date or h.date
            matches_plain.append(
                {
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
                }
            )

        # Chunks pequeños (~12 partidos) para balancear la cola: el costo por partido varía mucho.
        chunks = split_into_chunks(matches_plain, max(n_workers * 4, -(-len(matches_plain) // 12)))

        print(
            f"Iniciando recalculate-all PARALELO con {n_workers} workers en {len(chunks)} chunks "
            f"({total_to_process} partidos totales)...",
            flush=True,
        )
        t_start = time.perf_counter()
        results_by_id = {}

        # El histórico y las reglas viajan UNA vez por worker (initializer), no en cada chunk.
        import pickle
        import tempfile

        with tempfile.NamedTemporaryFile(prefix="sherlock_hist_", suffix=".pkl", delete=False) as _tmp:
            pickle.dump(shared_historical_records, _tmp, protocol=pickle.HIGHEST_PROTOCOL)
            records_path = _tmp.name

        with ProcessPoolExecutor(
            max_workers=n_workers,
            initializer=init_worker,
            initargs=(records_path, enabled_rules),
        ) as executor:
            # Arranca los procesos ya (imports + índice + calibrador) mientras el principal calcula
            # las estadísticas por liga, que antes se hacían en serie antes de lanzar nada.
            warm = [executor.submit(warmup) for _ in range(n_workers)]
            shared_league_stats = _compute_shared_league_stats()
            for f in warm:
                f.result()

            futures = [
                executor.submit(
                    _recalc_chunk,
                    {
                        "matches": ch,
                        "shared_league_stats": shared_league_stats,
                        "use_general_stats": use_general_stats,
                        "threshold_dt_iso": threshold_dt.isoformat() if threshold_dt else None,
                        "compress_results": True,
                    },
                )
                for ch in chunks
            ]
            for done_idx, fut in enumerate(as_completed(futures), start=1):
                chunk_results = fut.result()
                if done_idx % n_workers == 0 or done_idx == len(futures):
                    print(f"Chunks completados [{done_idx}/{len(futures)}]", flush=True)
                for res in chunk_results:
                    results_by_id[res["id"]] = res

        try:
            os.remove(records_path)
        except OSError:
            pass

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
        print(
            f"Recalculate-all paralelo completado en {t_total:.2f}s ({count} procesados, {updated_accuracy_count} aciertos actualizados)",
            flush=True,
        )
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
    shared_league_stats = _compute_shared_league_stats()
    _team_index: dict[str, list] = {}
    for r in shared_historical_records:
        title = r.get("match_title", "") or ""
        comp = (r.get("competition") or "").strip().lower()
        ht = (
            (r.get("home_team") or (title.split(" vs ")[0] if " vs " in title else ""))
            .strip()
            .lower()
        )
        at = (
            (r.get("away_team") or (title.split(" vs ")[1] if " vs " in title else ""))
            .strip()
            .lower()
        )
        if ht:
            _team_index.setdefault(ht, []).append(r)
            if comp:
                _team_index.setdefault(f"{comp}::{ht}", []).append(r)
        if at:
            _team_index.setdefault(at, []).append(r)
            if comp:
                _team_index.setdefault(f"{comp}::{at}", []).append(r)

    import time

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
                        precomputed_league_stats=shared_league_stats,
                    )
            except Exception as comp_err:
                print(
                    f"  -> Error en motor de comparación para {history.id} ({sport}): {comp_err}",
                    flush=True,
                )
                continue
            finally:
                dt = time.perf_counter() - t0
                _timings["engine_calc"] += dt
                _slowest.append((dt, history.id, history.match_title))
                print(f"  -> Terminado en {dt:.2f}s", flush=True)

            if new_response:
                if bookmaker_map:
                    _annotate_best_bookmaker(
                        new_response, bookmaker_map, req.home.name, req.away.name
                    )

                t0 = time.perf_counter()
                picks = [
                    v.model_dump() if hasattr(v, "model_dump") else v.__dict__
                    for v in new_response.values
                ]

                if enabled_rules:
                    home_stats = local_payload.get("home", {})
                    away_stats = local_payload.get("away", {})
                    odds_stats = local_payload.get("odds", {})
                    stat_src = StatSource.from_payload(home_stats, away_stats, odds_stats)
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
                history.compare_response_snapshot = json.dumps(
                    new_response.model_dump()
                    if hasattr(new_response, "model_dump")
                    else new_response.__dict__
                )

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


@router.post("/api/v1/analysis/apply-blacklist", tags=["Analysis History"])
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
    )
    from src.ui.api.compare_models import ValueIndicator
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
                line = pick.get("line")
                if not sel:
                    continue

                # Comprobar si está en la blacklist
                should_be_blacklisted = is_market_blacklisted_for_league(
                    league_name,
                    sel,
                    line=line,
                )
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
                            empirical_hit_rate=pick.get("empirical_hit_rate"),
                            home_hit_rate=pick.get("home_hit_rate"),
                            away_hit_rate=pick.get("away_hit_rate"),
                            hit_rate_samples=pick.get("hit_rate_samples", 0),
                            h2h_hit_rate=pick.get("h2h_hit_rate"),
                            h2h_raw_hit_rate=pick.get("h2h_raw_hit_rate"),
                            h2h_samples=pick.get("h2h_samples", 0) or 0,
                            h2h_hits=pick.get("h2h_hits"),
                            is_rule_blocked=pick.get("is_rule_blocked", False),
                            correlation_blocked=pick.get("correlation_blocked", False),
                            is_blacklisted=False,
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

                    target_stake = (
                        max(MIN_STAKE, round(base_stake * stake_mod))
                        if stake_mod != 1.0
                        else base_stake
                    )
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
                        print(
                            f"Error updating snapshot in blacklist for history {history.id}: {snap_err}"
                        )

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
        "updated_count": updated_count,
    }


@router.delete("/api/v1/analysis/{analysis_id}", status_code=204, tags=["Analysis History"])
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
