"""Orquestación del comparador de fútbol: análisis, LLM y compare_football.

Extraído de src/ui/api/compare.py (Lote 3). Depende de compare.py para el motor.
"""

from __future__ import annotations

from typing import Optional, Any
from openai import AsyncOpenAI
from src.domain.eligibility import (
    BlockReason,
)
from src.ui.api.compare_models import (  # noqa: F401  (re-export)
    SportType,
    FootballTeamStats,
    LeagueStats,
    FootballOdds,
    FootballCompareRequest,
    ValueIndicator,
    StatComparison,
    ProjectedLine,
    CompareResponse,
)
from src.domain.stake_engine import (
    RiskPolicy,
)
from src.core.prediction.lambdas import (  # re-export: moved out of compare.py
    _compute_team_goals_lambda,
    _compute_team_corners_lambda,
    _compute_team_cards_lambda,
    _compute_team_shots_lambda,
    _compute_team_shots_target_lambda,
    _compute_team_fouls_lambda,
    _compute_team_offsides_lambda,
    _compute_corners_lambda,
    _compute_cards_lambda,
    _compute_shots_lambda,
    _compute_shots_target_lambda,
    _compute_fouls_lambda,
    _compute_offsides_lambda,
)
from src.core.prediction.score_matrix import (  # re-export: moved out of compare.py
    fit_dixon_coles_rho,
    _dc_score_matrix,
    _sum_score_matrix_1x2_and_markets,
    _matrix_over_under,
)
from src.domain.portfolio import apply_portfolio_exposure_cap
import asyncio
from datetime import datetime
from src.core.math.calibration import (
    normalize_categorical_market,
)
import os
from src.ui.api.compare import (
    MIN_STAKE,
    _are_contradictory,
    _calculate_kelly_fraction,
    _deduplicate_correlated_picks,
    _extract_line_number,
    _implied_prob_from_odds,
    _is_too_similar,
    _market_family,
    _market_side,
    _rate_pick_quality,
    _safe_num,
    _sanitize_and_fill_team_stats,
    _stat_comparison,
    _to_naive_utc,
    _use_general_stats,
    _value_indicator,
    block_pick,
    evaluate_pick_eligibility,
    get_data_quality_score,
    get_nbinom_under_over_prob,
    is_underdog_pick,
    is_value_pick,
    logger,
    resolve_match_picks_correlation,
)


async def generate_football_analysis(
    h: FootballTeamStats,
    a: FootballTeamStats,
    vp: list[ValueIndicator],
    proj: list[ProjectedLine],
    league_stats: LeagueStats,
    competition: str = "Desconocida",
    user_context: str = "",
) -> str:
    MAX_MARKETS_FOR_LLM = 4
    MAX_PROJ_FOR_LLM = 4

    scored_picks = []
    for v in vp:
        if not v.is_publishable:
            continue

        score = v.quality_score if v.quality_score is not None else -1
        strat_score = v.strategic_score if v.strategic_score is not None else -1
        scored_picks.append((v, score, v.stat_support or 0.0, v.proj_support or 0.0, strat_score))

    scored_picks.sort(
        key=lambda x: (
            _safe_num(x[0].data_quality_score),
            _safe_num(x[0].model_prob),
            x[1],
            x[4],
            _safe_num(x[0].edge),
        ),
        reverse=True,
    )

    filtered_ranked = []
    for v, score, stat_support, proj_support, strategic_score in scored_picks:
        if not v.is_publishable:
            continue
        if any(
            _are_contradictory(v.selection, prev.selection) for prev, _, _, _, _ in filtered_ranked
        ):
            continue
        if any(
            _is_too_similar(v.selection, prev.selection) for prev, _, _, _, _ in filtered_ranked
        ):
            continue
        filtered_ranked.append((v, score, stat_support, proj_support, strategic_score))
        if len(filtered_ranked) >= 3:
            break

    vp_text = (
        "\n".join(
            [
                (
                    f"- {v.selection}: "
                    f"cuota={v.odds if v.odds is not None else 'N/A'} | "
                    f"modelo={_safe_num(v.model_prob):.1f}% | "
                    f"implícita={(_safe_num(v.implied_prob, None) if v.implied_prob is not None else _implied_prob_from_odds(v.odds)) or 'N/A'} | "
                    f"edge={_safe_num(v.edge):.1f}% | "
                    f"rating={v.rating} | "
                    f"solidez_backend={score} | "
                    f"score_rentabilidad={strategic_score} | "
                    f"respaldo_stats={stat_support:.1f}/100 | "
                    f"respaldo_proyeccion={proj_support:.1f}/100"
                )
                for v, score, stat_support, proj_support, strategic_score in filtered_ranked
            ]
        )
        if filtered_ranked
        else "- No hay mercados suficientemente sólidos. Debes decir claramente que no recomiendas apostar en este partido."
    )

    proj_text = (
        "\n".join(
            [
                f"- {p.label}: {p.value:.2f}"
                + (f" | prob={p.prob:.1f}%" if p.prob is not None else "")
                for p in proj[:MAX_PROJ_FOR_LLM]
            ]
        )
        if proj
        else "- No hay líneas proyectadas disponibles."
    )

    additional_context_block = ""
    if user_context:
        additional_context_block = f"""
CONTEXTO ADICIONAL DEL USUARIO:
{user_context}

INSTRUCCIONES OBLIGATORIAS SOBRE EL CONTEXTO:
- Este contexto DEBE modificar directamente tu análisis táctico y tus recomendaciones.
- No lo trates como información decorativa: úsalo para ajustar qué mercados tienen sentido dado el escenario real.
- Ejemplos de cómo aplicarlo:
    * Si es una eliminatoria (ida/vuelta) y un equipo tiene ventaja en el global, considera que el favorito puede bajar el ritmo o especular, y el otro necesita atacar sí o sí → esto afecta corners, goles, BTTS y resultado.
    * Si hay equipos que necesitan ganar por obligación (descenso, clasificación), espera más presión, más tarjetas, más corners.
    * Si el partido es intrascendente para ambos (ya clasificados, ya descendidos), penaliza picks que dependen de intensidad alta.
    * Si hay información sobre bajas confirmadas, alineaciones, clima o contexto emocional del equipo, intégrala al análisis.
- Nunca contradigas el contexto dado. Si el contexto invalida un pick del modelo, dilo explícitamente y descártalo.
""".strip()

    prompt = f"""
Eres un analista táctico y de apuestas de élite. Tu trabajo es explicar el partido con claridad, criterio estadístico y lenguaje natural, sin exagerar ni repetir números innecesariamente.

REGLAS:
- Usa SOLO la información entregada.
- No inventes lesiones, rachas recientes, contexto histórico ni alineaciones.
- No digas que un mercado tiene valor si no aparece en "MERCADOS FINALISTAS".
- Si no hay suficiente seguridad, dilo explícitamente y no fuerces picks.
- Sé concreto: máximo 420 palabras.
- Prioriza interpretación sobre repetir cifras.
- Los mercados listados en "MERCADOS DE VALOR" ya fueron prefiltrados y ordenados aproximadamente por solidez. Usa ese orden como pista secundaria, pero decide con criterio propio según estadísticas y proyecciones.

OBJETIVO PRINCIPAL:
No debes elegir picks solo porque tengan más edge.
Debes seleccionar los picks que tengan MAYOR PROBABILIDAD REAL DE CUMPLIRSE dentro de los mercados de valor disponibles.

JERARQUÍA OBLIGATORIA PARA ESCOGER PICKS:
1. Primero, prioriza la probabilidad real de acierto del mercado.
2. Después, verifica que esté claramente respaldado por las estadísticas de ambos equipos.
3. Luego, confirma que la proyección del partido y de las líneas vaya en la misma dirección.
4. Solo después de eso, usa la diferencia entre probabilidad del modelo y probabilidad implícita de la casa para validar el value.
5. El edge por sí solo NO convierte un pick en uno de los mejores.

CRITERIOS ESTRICTOS:
- Favorece mercados con probabilidad del modelo alta y sostenida por el perfil estadístico del partido.
- Penaliza mercados con cuota alta y probabilidad absoluta baja, aunque tengan edge positivo.
- Penaliza mercados atractivos en precio, pero débiles en respaldo estadístico.
- Penaliza mercados que dependan de demasiada varianza o de un guion poco sólido.
- Entre dos picks parecidos, elige el más probable de cumplirse, no el que más paga.
- No elijas picks contradictorios entre sí.
- Si un pick tiene edge alto pero parece menos probable de salir que otro mercado más sólido, NO lo selecciones.
- Tu meta no es encontrar los picks con más value bruto, sino los 2 picks más fuertes y confiables que además tengan value.
- Prefiere 1 pick muy sólido antes que 2 picks mediocres.
- Si ningún pick supera un estándar alto de seguridad, no recomiendes apostar.

PARTIDO:
Competencia: {competition}
Local: {h.name}
Visitante: {a.name}
Árbitro: {league_stats.referee_avg_yellow} amarillas/j | {league_stats.referee_avg_red} rojas/j

SEÑALES CLAVE LOCAL:
- Partidos jugados: {h.matches_played}
- Victorias: {h.wins} | Empates: {h.draws} | Derrotas: {h.losses}
- Goles p/j: {h.goals_per_game} de local | Goles concedidos p/j: {h.goals_conceded_per_game} de local
- xG p/j: {h.xg_per_game} de local | xGA p/j: {h.xga_per_game} de local
- Goles dentro/fuera área: {h.goals_inside_box}/{h.goals_outside_box}
- Goles contraataque: {h.fast_break_goals} | Goles cabeza: {h.headed_goals}
- Grandes chances creadas p/j: {h.big_chances_created} | Creadas/Recibidas: {h.big_chances_per_game}/{h.big_chances_missed_per_game}
- Tiros totales p/j: {h.shots_per_game} | Tiros a puerta p/j: {h.shots_on_target_per_game}
- Tiros dentro/fuera área: {h.shots_inside_box}/{h.shots_outside_box} | Tiros al palo: {h.hit_woodwork}
- Dribbles exitosos %: {h.dribble_success_pct} | Contraataques: {h.fast_breaks}
- Posesión: {h.possession_pct}% | Pérdidas posesión: {h.possession_lost}
- Corners p/j: {h.corners_per_game} de local | Corners concedidos p/j: {h.corners_conceded_per_game} de local
- Duelos aéreos ganados: {h.aerial_duels_won_per_game} | Duelos totales: {h.duels_total_per_game}
- Disciplina: {h.yellow_cards_per_game} Amarillas p/j | {h.fouls_per_game} Faltas p/j | {h.red_cards_total}/{h.matches_played} Rojas p/j
- Penales concedidos: {h.penalties_conceded} | Errores a gol: {h.errors_leading_to_goal} | Errores a tiro: {h.errors_leading_to_shot}
- Defensa: {h.clean_sheets_home} Vallas invictas de local | {h.saves_per_game} Paradas p/j | Save%: {h.save_pct}
- Despejes línea: {h.clearances_off_line} | Entradas último hombre: {h.last_man_tackles}
- Kilómetros: {h.kilometers_covered} | Sprints: {h.number_of_sprints}
- Rating: {h.avg_rating}

SEÑALES CLAVE VISITANTE:
- Partidos jugados: {a.matches_played}
- Victorias: {a.wins} | Empates: {a.draws} | Derrotas: {a.losses}
- Goles p/j: {a.goals_per_game} de visitante | Goles concedidos p/j: {a.goals_conceded_per_game} de visitante
- xG p/j: {a.xg_per_game} de visitante | xGA p/j: {a.xga_per_game} de visitante
- Goles dentro/fuera área: {a.goals_inside_box}/{a.goals_outside_box}
- Goles contraataque: {a.fast_break_goals} | Goles cabeza: {a.headed_goals}
- Grandes chances creadas p/j: {a.big_chances_created} | Creadas/Recibidas: {a.big_chances_per_game}/{a.big_chances_missed_per_game}
- Tiros totales p/j: {a.shots_per_game} | Tiros a puerta p/j: {a.shots_on_target_per_game}
- Tiros dentro/fuera área: {a.shots_inside_box}/{a.shots_outside_box} | Tiros al palo: {a.hit_woodwork}
- Dribbles exitosos %: {a.dribble_success_pct} | Contraataques: {a.fast_breaks}
- Posesión: {a.possession_pct}% | Pérdidas posesión: {a.possession_lost}
- Corners p/j: {a.corners_per_game} de visitante | Corners concedidos p/j: {a.corners_conceded_per_game} de visitante
- Duelos aéreos ganados: {a.aerial_duels_won_per_game} | Duelos totales: {a.duels_total_per_game}
- Disciplina: {a.yellow_cards_per_game} Amarillas p/j | {a.fouls_per_game} Faltas p/j | {a.red_cards_total}/{a.matches_played} Rojas p/j
- Penales concedidos: {a.penalties_conceded} | Errores a gol: {a.errors_leading_to_goal} | Errores a tiro: {a.errors_leading_to_shot}
- Defensa: {a.clean_sheets_away} Vallas invictas de visitante | {a.saves_per_game} Paradas p/j | Save%: {a.save_pct}
- Despejes línea: {a.clearances_off_line} | Entradas último hombre: {a.last_man_tackles}
- Kilómetros: {a.kilometers_covered} | Sprints: {a.number_of_sprints}
- Rating: {a.avg_rating}

LÍNEAS PROYECTADAS:
{proj_text}

MERCADOS FINALISTAS:
{vp_text}

{additional_context_block}

## PROTOCOLO DE ANÁLISIS (ejecuta en este orden mental)

Paso 1 - Filtro de contexto: Aplica el contexto situacional para ajustar expectativas base de goles, intensidad y riesgo.
Paso 2 - Filtro estadístico: Cruza xG, tiros a puerta, corners y disciplina para validar si las líneas proyectadas son coherentes.
Paso 3 - Filtro de probabilidad: De los mercados finalistas, identifica cuáles tienen probabilidad de modelo >60% y soporte estadístico directo.
Paso 4 - Filtro de valor: Entre los supervivientes, verifica que la cuota implícita no sobreprecie el riesgo.
Paso 5 - Filtro de correlación: Si hay 2 picks, confirma que no son mutuamente excluyentes ni del mismo mercado escalonado.

## FORMATO DE RESPUESTA OBLIGATORIO

**Diagnóstico táctico:** Explica el choque de estilos usando posesión, xG y generación de juego. Si hay contexto situacional, debe ser el eje conductor.

**Evaluación de mercados:** Solo menciona goles, BTTS, corners o tarjetas si las proyecciones y estadísticas lo justifican con números concretos. Si el contexto altera la lógica (ej: ventaja en eliminatoria reduce intensidad), declara el ajuste explícito.

**Pronósticos recomendados (máximo 2):**
Para cada pick usa exactamente esta estructura:
- **Pick:** [texto exacto del mercado]
- **Probabilidad:** Modelo [X]% | Implícita casa [Y]%
- **Justificación estadística:** [2 frases con datos concretos]
- **Respaldo proyección:** [cómo la línea proyectada respalda el pick]
- **Validación contextual:** [cómo el contexto refuerza o invalida el pick]
- **Value:** [por qué la cuota no refleja completamente la probabilidad real]

**Regla de cantidad:** Prefiere 1 pick sólido sobre 2 picks dudosos. Si ninguno supera el umbral de confianza, escribe exactamente: "No recomiendo apostar en este partido."

**Combinada sugerida (solo si hay exactamente 2 picks recomendados):**
- Picks combinados: [lista]
- Cuota combinada estimada: [producto de ambas cuotas]
- Probabilidad combinada estimada: [producto de ambas probabilidades del modelo]%
- Justificación de independencia: [1-2 frases explicando por qué no están correlacionados negativamente]
- Si están correlacionados negativamente, omite este bloque y explica brevemente por qué no se sugiere.
""".strip()

    return await _call_openrouter(prompt)


async def _call_openrouter(prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "Para ver el análisis con IA, configura OPENROUTER_API_KEY en tu .env"

    primary_model = os.environ.get("OPENROUTER_MODEL")
    if not primary_model:
        return "Para generar el análisis con IA, configura OPENROUTER_MODEL en tu .env"

    fallback_model = os.environ.get("OPENROUTER_FALLBACK_MODEL")
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    retry_delays = [1.5, 3, 5]
    last_error = None

    def _extract_content(response) -> str | None:
        if response is None:
            return None

        err = getattr(response, "error", None)
        if err:
            return None

        choices = getattr(response, "choices", None)
        if not choices:
            return None

        message = getattr(choices[0], "message", None)
        if message is None:
            return None

        content = getattr(message, "content", None)

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("text"):
                        text_parts.append(part["text"])
                else:
                    txt = getattr(part, "text", None)
                    if txt:
                        text_parts.append(txt)

            joined = "\n".join(x.strip() for x in text_parts if x and str(x).strip())
            if joined:
                return joined

        return None

    def _response_error_info(response):
        err = getattr(response, "error", None)
        if isinstance(err, dict):
            return str(err.get("code", "N/A")), str(err.get("message", "Error desconocido"))
        if err:
            return "N/A", str(err)
        return None, None

    for attempt, delay in enumerate(retry_delays, start=1):
        try:
            extra_body = {}
            if fallback_model and fallback_model != primary_model:
                extra_body["models"] = [fallback_model]

            r = await client.chat.completions.create(
                model=primary_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5000,
                temperature=0.15,
                extra_headers={
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "football-analysis",
                },
                extra_body=extra_body if extra_body else None,
            )

            content = _extract_content(r)
            if content:
                return content

            code, msg = _response_error_info(r)
            if code:
                last_error = f"Error del modelo ({code}): {msg}"
            else:
                last_error = "⚠️ El modelo no devolvió contenido válido."

        except Exception as e:
            msg = str(e)
            last_error = msg

            retryable_markers = [
                "429",
                "500",
                "502",
                "503",
                "504",
                "524",
                "529",
                "rate limit",
                "timeout",
                "temporarily unavailable",
                "internal server error",
                "bad gateway",
                "service unavailable",
            ]

            if not any(marker.lower() in msg.lower() for marker in retryable_markers):
                return f"Error al generar análisis IA: {e}"

        if attempt < len(retry_delays):
            await asyncio.sleep(delay)

    return last_error or "⚠️ No se pudo generar el análisis con IA tras varios intentos."


# ───────────────────────────────────────────────────────────────
# compare_football
# ───────────────────────────────────────────────────────────────
async def compare_football(
    req: FootballCompareRequest,
    db: Any = None,
    exclude_match_id: Optional[Any] = None,
    current_match_date: Optional[Any] = None,
    precomputed_historical_records: Optional[list] = None,
    precomputed_team_index: Optional[dict] = None,
    precomputed_league_stats: Optional[dict] = None,
) -> CompareResponse:
    """
    NOTA DE FIX:
    Se agregaron los parámetros explícitos `exclude_match_id` y `current_match_date`.
    Tienen PRIORIDAD sobre cualquier valor que venga dentro de `req` (req.id,
    req.analysis_id, req.match_id, req.exclude_match_id, req.match_date, req.date).
    Esto es necesario porque en el flujo de RE-ANÁLISIS (main.py) el `req` se
    reconstruye desde el `payload` histórico guardado, el cual casi nunca trae
    poblado el `id` real de la fila en `analysis_history` ni una fecha confiable.
    Si el llamador pasa estos dos parámetros explícitamente (ej. exclude_match_id=history.id,
    current_match_date=history.match_date), se garantiza que el propio partido
    quede excluido del hit rate y del H2H, evitando el data leakage.
    """
    # Enriquecer league_stats con estadísticas históricas de la BD o precomputadas
    db_created = False
    db_session = None
    try:
        from src.core.database import SessionLocal
        from src.core.domain import AnalysisHistory, Sport
        from src.ui.api.shared import _check_pick_success, _calculate_pick_profit, _is_pick_hit
        import json as _json

        comp_key = (req.competition or "").strip().lower()
        if (
            precomputed_league_stats
            and comp_key in precomputed_league_stats
            and req.league_stats.historical_picks <= 0
        ):
            ls_data = precomputed_league_stats[comp_key]
            req = req.model_copy(
                update={
                    "league_stats": req.league_stats.model_copy(
                        update={
                            "historical_matches": ls_data.get("historical_matches", 0),
                            "historical_picks": ls_data.get("historical_picks", 0),
                            "historical_hits": ls_data.get("historical_hits", 0),
                            "historical_profit": round(ls_data.get("historical_profit", 0.0), 4),
                        }
                    )
                }
            )
        elif (
            req.league_stats.historical_picks <= 0
            and req.competition
            and req.competition not in ("", "Desconocida", "General")
        ):
            db_session = db if db is not None else SessionLocal()
            db_created = db is None
            league_rows = (
                db_session.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.competition == req.competition,
                    AnalysisHistory.sport == Sport.FOOTBALL,
                    AnalysisHistory.picks_calculados.isnot(None),
                )
                .all()
            )

            total_matches = len(league_rows)
            total_picks = 0
            total_hits = 0
            total_profit = 0.0

            for row in league_rows:
                # Resultado del partido (necesario para calcular hits)
                res_dict = {
                    "final_score_home": row.final_score_home,
                    "final_score_away": row.final_score_away,
                    "final_corners_home": row.final_corners_home,
                    "final_corners_away": row.final_corners_away,
                    "final_yellow_cards_home": row.final_yellow_cards_home,
                    "final_yellow_cards_away": row.final_yellow_cards_away,
                    "final_red_cards_home": row.final_red_cards_home,
                    "final_red_cards_away": row.final_red_cards_away,
                    "final_shots_home": row.final_shots_home,
                    "final_shots_away": row.final_shots_away,
                    "final_shots_on_target_home": row.final_shots_on_target_home,
                    "final_shots_on_target_away": row.final_shots_on_target_away,
                }
                # Solo contar picks si el partido tiene resultado real
                has_result = (
                    res_dict["final_score_home"] is not None
                    and res_dict["final_score_away"] is not None
                )

                try:
                    picks_raw = _json.loads(row.picks_calculados) if row.picks_calculados else []
                except Exception:
                    picks_raw = []

                for pick in picks_raw:
                    if not isinstance(pick, dict):
                        continue
                    stake = float(pick.get("stake", pick.get("stake_units", 0)) or 0)
                    if stake <= 0:
                        continue  # solo contar picks publicados
                    total_picks += 1
                    if has_result:
                        outcome = _check_pick_success(pick, res_dict)
                        if _is_pick_hit(outcome):
                            total_hits += 1
                        odds_val = float(pick.get("odds", 1.0) or 1.0)
                        total_profit += _calculate_pick_profit(outcome, odds_val)

            if total_matches > 0 or total_picks > 0:
                req = req.model_copy(
                    update={
                        "league_stats": req.league_stats.model_copy(
                            update={
                                "historical_matches": total_matches,
                                "historical_picks": total_picks,
                                "historical_hits": total_hits,
                                "historical_profit": round(total_profit, 4),
                            }
                        )
                    }
                )
                logger.debug(
                    "League %s enriched: matches=%d picks=%d hits=%d profit=%.2f",
                    req.competition,
                    total_matches,
                    total_picks,
                    total_hits,
                    total_profit,
                )

        # ── Issue #63: Calcular avg_corners_per_game desde la BD si Sofascore no lo envía ──
        # Si el valor es el default (9.5), intentar calcularlo desde los resultados históricos.
        _DEFAULT_CORNERS_PER_GAME = 9.5
        if (
            abs(req.league_stats.avg_corners_per_game - _DEFAULT_CORNERS_PER_GAME) < 0.01
            and req.competition
            and req.competition not in ("", "Desconocida", "General")
        ):
            try:
                if db_session is None:
                    db_session = db if db is not None else SessionLocal()
                    db_created = db is None

                from src.ui.api.shared import _compute_league_season_corners

                season_val = getattr(req, "season", None) or getattr(
                    req.league_stats, "season", None
                )
                computed_avg = _compute_league_season_corners(
                    req.competition, season_val, db_session=db_session
                )
                if computed_avg is not None and 5.0 <= computed_avg <= 16.0:
                    req = req.model_copy(
                        update={
                            "league_stats": req.league_stats.model_copy(
                                update={
                                    "avg_corners_per_game": round(computed_avg, 2),
                                }
                            )
                        }
                    )
                    logger.info(
                        "League %s avg_corners_per_game calculado desde BD: %.2f",
                        req.competition,
                        computed_avg,
                    )
            except Exception as ex_corners:
                logger.warning(
                    "Error calculando avg_corners desde BD para %s: %s", req.competition, ex_corners
                )

    except Exception as ex:
        logger.warning("Error enriching league stats from DB: %s", ex)
    finally:
        if db_created and db_session is not None:
            try:
                db_session.close()
            except Exception:
                pass

    h = _sanitize_and_fill_team_stats(req.home)
    a = _sanitize_and_fill_team_stats(req.away)
    req = req.model_copy(update={"home": h, "away": a})

    h_matches = max(h.matches_played, 1)
    a_matches = max(a.matches_played, 1)

    # ── COMPARACIONES AMPLIADAS CON STATS AVANZADAS ──
    comparisons = [
        # Ataque Básico
        _stat_comparison("Goles por juego", "goals_per_game", h.goals_per_game, a.goals_per_game),
        _stat_comparison(
            "Goles dentro área", "goals_inside_box", h.goals_inside_box, a.goals_inside_box
        ),
        _stat_comparison(
            "Goles fuera área", "goals_outside_box", h.goals_outside_box, a.goals_outside_box
        ),
        _stat_comparison("Goles cabeza", "headed_goals", h.headed_goals, a.headed_goals),
        _stat_comparison(
            "Goles contraataque", "fast_break_goals", h.fast_break_goals, a.fast_break_goals
        ),
        _stat_comparison(
            "% Conversión Gol", "goal_conversion_pct", h.goal_conversion_pct, a.goal_conversion_pct
        ),
        _stat_comparison(
            "Grandes chances",
            "big_chances_per_game",
            h.big_chances_per_game,
            a.big_chances_per_game,
        ),
        _stat_comparison(
            "G. Chances Creadas",
            "big_chances_created",
            h.big_chances_created,
            a.big_chances_created,
        ),
        _stat_comparison(
            "G. Chances Falladas",
            "big_chances_missed_per_game",
            h.big_chances_missed_per_game,
            a.big_chances_missed_per_game,
            False,
        ),
        # Tiros
        _stat_comparison(
            "Tiros al arco",
            "shots_on_target_per_game",
            h.shots_on_target_per_game,
            a.shots_on_target_per_game,
        ),
        _stat_comparison(
            "Tiros dentro área", "shots_inside_box", h.shots_inside_box, a.shots_inside_box
        ),
        _stat_comparison(
            "Tiros fuera área", "shots_outside_box", h.shots_outside_box, a.shots_outside_box
        ),
        _stat_comparison("Tiros al palo", "hit_woodwork", h.hit_woodwork, a.hit_woodwork),
        _stat_comparison("Tiros bloqueados", "shots_blocked", h.shots_blocked, a.shots_blocked),
        # Calidad Individual
        _stat_comparison(
            "Dribbles exitosos %",
            "dribble_success_pct",
            h.dribble_success_pct,
            a.dribble_success_pct,
        ),
        _stat_comparison("Contraataques", "fast_breaks", h.fast_breaks, a.fast_breaks),
        # Posesión
        _stat_comparison("Posesión %", "possession_pct", h.possession_pct, a.possession_pct),
        _stat_comparison(
            "Pérdidas posesión", "possession_lost", h.possession_lost, a.possession_lost, False
        ),
        _stat_comparison(
            "Pases acertados", "passes_completed", h.passes_completed, a.passes_completed
        ),
        _stat_comparison("Precisión pases %", "pass_accuracy", h.pass_accuracy, a.pass_accuracy),
        _stat_comparison(
            "Pases campo rival %",
            "pass_accuracy_opp_half",
            h.pass_accuracy_opp_half,
            a.pass_accuracy_opp_half,
        ),
        _stat_comparison(
            "Centros completos", "crosses_per_game", h.crosses_per_game, a.crosses_per_game
        ),
        _stat_comparison(
            "Precisión de centros %", "cross_accuracy", h.cross_accuracy, a.cross_accuracy
        ),
        _stat_comparison(
            "Corners por juego", "corners_per_game", h.corners_per_game, a.corners_per_game
        ),
        # Defensa
        _stat_comparison(
            "Goles concedidos",
            "goals_conceded_per_game",
            h.goals_conceded_per_game,
            a.goals_conceded_per_game,
            False,
        ),
        _stat_comparison(
            "% Vallas Invictas",
            "clean_sheets_pct",
            (h.clean_sheets / h_matches) * 100,
            (a.clean_sheets / a_matches) * 100,
        ),
        _stat_comparison(
            "Errores a Gol/juego",
            "errors_leading_to_goal_pg",
            h.errors_leading_to_goal / h_matches,
            a.errors_leading_to_goal / a_matches,
            False,
        ),
        _stat_comparison(
            "Errores a Tiro/juego",
            "errors_leading_to_shot_pg",
            h.errors_leading_to_shot / h_matches,
            a.errors_leading_to_shot / a_matches,
            False,
        ),
        _stat_comparison(
            "Recuperaciones/j",
            "balls_recovered_per_game",
            h.balls_recovered_per_game,
            a.balls_recovered_per_game,
        ),
        _stat_comparison(
            "Despejes línea", "clearances_off_line", h.clearances_off_line, a.clearances_off_line
        ),
        _stat_comparison(
            "Entradas último hombre", "last_man_tackles", h.last_man_tackles, a.last_man_tackles
        ),
        _stat_comparison("Save %", "save_pct", h.save_pct * 100, a.save_pct * 100),
        # Duelos
        _stat_comparison(
            "Duelos ganados", "duels_won_per_game", h.duels_won_per_game, a.duels_won_per_game
        ),
        _stat_comparison(
            "Duelos aéreos ganados",
            "aerial_duels_won_per_game",
            h.aerial_duels_won_per_game,
            a.aerial_duels_won_per_game,
        ),
        _stat_comparison(
            "Duelos en piso",
            "ground_duels_won_per_game",
            h.ground_duels_won_per_game,
            a.ground_duels_won_per_game,
        ),
        # Disciplina
        _stat_comparison("Faltas/j", "fouls_per_game", h.fouls_per_game, a.fouls_per_game),
        _stat_comparison(
            "Penales concedidos",
            "penalties_conceded",
            h.penalties_conceded,
            a.penalties_conceded,
            False,
        ),
        _stat_comparison(
            "Amarillas/j",
            "yellow_cards_per_game",
            h.yellow_cards_per_game,
            a.yellow_cards_per_game,
            False,
        ),
        # Físicas
        _stat_comparison(
            "Kilómetros/j", "kilometers_covered", h.kilometers_covered, a.kilometers_covered
        ),
        _stat_comparison(
            "Sprints/j", "number_of_sprints", h.number_of_sprints, a.number_of_sprints
        ),
        # Rating
        _stat_comparison("Rating equipo", "avg_rating", h.avg_rating, a.avg_rating),
    ]

    use_general = _use_general_stats(req)  # True para partidos >= 2026-01-01

    # ── Tarea 2: data_quality_score general para shrinkage bayesiano ──
    _dq_h = get_data_quality_score("goles", h, a) if h and a else None
    _dq_a = _dq_h  # simétrico: calidad del dato es del partido completo

    h_lam = _compute_team_goals_lambda(
        h, a, req.league_stats, is_home=True, general=use_general, db=db, data_quality_score=_dq_h
    )
    a_lam = _compute_team_goals_lambda(
        a, h, req.league_stats, is_home=False, general=use_general, db=db, data_quality_score=_dq_a
    )
    h_lam_corners, h_r_corners, a_lam_corners, a_r_corners = _compute_corners_lambda(
        h, a, req.league_stats, general=use_general, db=db
    )
    lam_corners = h_lam_corners + a_lam_corners
    h_lam_cards, h_r_cards, a_lam_cards, a_r_cards = _compute_cards_lambda(
        h, a, req.league_stats, general=use_general, db=db
    )
    lam_cards = h_lam_cards + a_lam_cards
    h_lam_shots, h_r_shots, a_lam_shots, a_r_shots = _compute_shots_lambda(
        h, a, req.league_stats, general=use_general, db=db
    )
    lam_shots = h_lam_shots + a_lam_shots
    h_lam_shots_target, h_r_shots_target, a_lam_shots_target, a_r_shots_target = (
        _compute_shots_target_lambda(h, a, req.league_stats, general=use_general, db=db)
    )
    lam_shots_target = h_lam_shots_target + a_lam_shots_target

    h_goals_lam = h_lam
    a_goals_lam = a_lam
    h_corners_lam, _h_corners_r = _compute_team_corners_lambda(
        h, a, req.league_stats, is_home=True, general=use_general, db=db, data_quality_score=_dq_h
    )
    a_corners_lam, _a_corners_r = _compute_team_corners_lambda(
        a, h, req.league_stats, is_home=False, general=use_general, db=db, data_quality_score=_dq_a
    )
    h_cards_lam, _h_cards_r = _compute_team_cards_lambda(
        h, a, req.league_stats, is_home=True, general=use_general, db=db, data_quality_score=_dq_h
    )
    a_cards_lam, _a_cards_r = _compute_team_cards_lambda(
        a, h, req.league_stats, is_home=False, general=use_general, db=db, data_quality_score=_dq_a
    )
    h_shots_lam, _h_shots_r = _compute_team_shots_lambda(
        h, a, req.league_stats, is_home=True, general=use_general, db=db, data_quality_score=_dq_h
    )
    a_shots_lam, _a_shots_r = _compute_team_shots_lambda(
        a, h, req.league_stats, is_home=False, general=use_general, db=db, data_quality_score=_dq_a
    )
    h_shots_target_lam, _h_shots_target_r = _compute_team_shots_target_lambda(
        h, a, req.league_stats, is_home=True, general=use_general, db=db, data_quality_score=_dq_h
    )
    a_shots_target_lam, _a_shots_target_r = _compute_team_shots_target_lambda(
        a, h, req.league_stats, is_home=False, general=use_general, db=db, data_quality_score=_dq_a
    )

    # ── Issue #22: Ajustar rho desde verosimilitud conjunta sobre historial de la liga ──
    # Si hay DB disponible, extraemos partidos históricos de AnalysisHistory y ajustamos rho
    # por máxima verosimilitud (búsqueda en grilla). Si no hay datos suficientes, cae en
    # la heurística original (_default_dc_rho), que es peor pero nunca explota.
    fitted_rho: float | None = None
    if db is not None and req.competition and req.competition not in ("", "Desconocida", "General"):
        try:
            from src.core.domain import AnalysisHistory

            hist_rows = (
                db.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.competition == req.competition,
                    AnalysisHistory.final_score_home.isnot(None),
                    AnalysisHistory.final_score_away.isnot(None),
                )
                .order_by(AnalysisHistory.date.desc())
                .limit(200)
                .all()
            )
            # Build match tuples (home_goals, away_goals, h_lambda, a_lambda)
            # We use the league average lambdas as approximation since we don't store
            # the original lambdas — the key signal is the score distribution shape.
            avg_lambda = req.league_stats.avg_goals_per_game / 2.0
            match_tuples: list[tuple[int, int, float, float]] = []
            for row in hist_rows:
                hg = row.final_score_home
                ag = row.final_score_away
                if hg is None or ag is None:
                    continue
                try:
                    match_tuples.append((int(hg), int(ag), h_lam, a_lam))
                except (ValueError, TypeError):
                    continue
            if len(match_tuples) >= 100:
                fitted_rho = fit_dixon_coles_rho(match_tuples)
                logger.debug(
                    "Liga %s: rho ajustado por MV = %.4f (n=%d partidos).",
                    req.competition,
                    fitted_rho,
                    len(match_tuples),
                )
        except Exception as _rho_err:
            logger.debug("Error ajustando rho para %s: %s", req.competition, _rho_err)
            fitted_rho = None

    matrix, _ = _dc_score_matrix(h_lam, a_lam, rho=fitted_rho)
    markets = _sum_score_matrix_1x2_and_markets(matrix)

    # Exact categorical market normalization
    norm_1x2 = normalize_categorical_market(
        {
            "home": markets["home_win_pct"] / 100.0,
            "draw": markets["draw_pct"] / 100.0,
            "away": markets["away_win_pct"] / 100.0,
        }
    )
    h_prob_raw = norm_1x2["home"]
    d_prob_raw = norm_1x2["draw"]
    a_prob_raw = norm_1x2["away"]

    norm_btts = normalize_categorical_market(
        {
            "yes": markets["btts_yes_pct"] / 100.0,
            "no": markets["btts_no_pct"] / 100.0,
        }
    )
    p_btts_yes = norm_btts["yes"]
    p_btts_no = norm_btts["no"]

    h_prob = h_prob_raw
    d_prob = d_prob_raw
    a_prob = a_prob_raw

    def _overround(*odds_list: float | None) -> float:
        raw = [1.0 / o for o in odds_list if o and o > 1.0]
        return sum(raw) * 100.0 if raw else 100.0

    m_date_eval = (
        current_match_date or getattr(req, "match_date", None) or getattr(req, "date", None)
    )

    def _vi(
        sel: str,
        odds: float | None,
        modelp: float,
        overround: float = 100.0,
        push_p: float = 0.0,
        market_novig_pct: float | None = None,
    ) -> ValueIndicator:
        return _value_indicator(
            sel,
            odds,
            modelp,
            h=h,
            a=a,
            overround=overround,
            push_p=push_p,
            league=req.league_stats,
            league_name=req.competition,
            odds_obj=req.odds,
            match_date=m_date_eval,
            market_novig_pct=market_novig_pct,
        )

    _or_1x2 = _overround(req.odds.home, req.odds.draw, req.odds.away)
    _or_btts = _overround(req.odds.btts_yes, req.odds.btts_no)

    # ── Issue #19: Derivar Doble Oportunidad exactamente de la matriz Dixon-Coles ──
    p_dc_1x = (h_prob_raw + d_prob_raw) * 100.0
    p_dc_x2 = (d_prob_raw + a_prob_raw) * 100.0
    p_dc_12 = (h_prob_raw + a_prob_raw) * 100.0

    _or_dc_raw = _overround(req.odds.dc_1x, req.odds.dc_x2, req.odds.dc_12)
    _or_dc = _or_dc_raw if _or_dc_raw > 100.5 else _or_1x2

    # Issue #44: No-vig de Doble Oportunidad por método de potencia
    from src.models.market_probability import remove_vig_power

    _dc_odds_list = [req.odds.dc_1x, req.odds.dc_x2, req.odds.dc_12]
    _dc_novig_probs = (
        remove_vig_power(_dc_odds_list) if all(o and o > 1.0 for o in _dc_odds_list) else []
    )
    _dc_novig_1x = (_dc_novig_probs[0] * 100.0) if len(_dc_novig_probs) == 3 else None
    _dc_novig_x2 = (_dc_novig_probs[1] * 100.0) if len(_dc_novig_probs) == 3 else None
    _dc_novig_12 = (_dc_novig_probs[2] * 100.0) if len(_dc_novig_probs) == 3 else None

    market_configs: list[tuple[str, float | None, float, float, float, float | None]] = [
        ("Local", req.odds.home, h_prob * 100, _or_1x2, 0.0, None),
        ("Empate", req.odds.draw, d_prob * 100, _or_1x2, 0.0, None),
        ("Visitante", req.odds.away, a_prob * 100, _or_1x2, 0.0, None),
        ("BTTS Sí", req.odds.btts_yes, p_btts_yes * 100, _or_btts, 0.0, None),
        ("BTTS No", req.odds.btts_no, p_btts_no * 100, _or_btts, 0.0, None),
        ("Doble Oportunidad 1X", req.odds.dc_1x, p_dc_1x, _or_dc, 0.0, _dc_novig_1x),
        ("Doble Oportunidad X2", req.odds.dc_x2, p_dc_x2, _or_dc, 0.0, _dc_novig_x2),
        ("Doble Oportunidad 12", req.odds.dc_12, p_dc_12, _or_dc, 0.0, _dc_novig_12),
    ]
    # Issue #34: Track Over/Under complementary pairs for post-calibration renormalization.
    # Each entry is (over_index, under_index, push_prob_pct) in market_configs.
    _ou_pairs: list[tuple[int, int, float]] = []

    projected_lines: list[ProjectedLine] = []
    projected_total_goals = h_lam + a_lam

    projected_lines.append(
        ProjectedLine(
            label="Goles Totales (λ)",
            value=round(projected_total_goals, 2),
            type="goals",
            prob=None,
        )
    )
    projected_lines.append(
        ProjectedLine(
            label="Doble Oportunidad 1X",
            value=round(p_dc_1x, 1),
            type="double_chance",
            prob=round(p_dc_1x, 1),
        )
    )
    projected_lines.append(
        ProjectedLine(
            label="Doble Oportunidad X2",
            value=round(p_dc_x2, 1),
            type="double_chance",
            prob=round(p_dc_x2, 1),
        )
    )
    projected_lines.append(
        ProjectedLine(
            label="Doble Oportunidad 12",
            value=round(p_dc_12, 1),
            type="double_chance",
            prob=round(p_dc_12, 1),
        )
    )
    projected_lines.append(
        ProjectedLine(
            label="BTTS Sí",
            value=round(p_btts_yes * 100, 1),
            type="btts",
            prob=round(p_btts_yes * 100, 1),
        )
    )

    # ── Over/Under GOLES: Issue #19 derivado directamente de la matriz Dixon-Coles ─────
    for line in req.odds.goals_lines:
        p_over, p_push, p_under = _matrix_over_under(matrix, line)
        key = str(line)
        overOdds = req.odds.goals_over_odds.get(key)
        underOdds = req.odds.goals_under_odds.get(key)
        _or_goals = _overround(overOdds, underOdds)

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
        market_configs.append((f"Over {line} Goles", overOdds, p_over, _or_goals, p_push))
        market_configs.append((f"Under {line} Goles", underOdds, p_under, _or_goals, p_push))

        projected_lines.append(
            ProjectedLine(
                label=f"Over {line} Goles",
                value=round(p_over, 1),
                type="goals",
                prob=round(p_over, 1),
            )
        )

    # ── Over/Under CORNERS (Binomial Negativa con r combinado por equipo) ───────────────────
    projected_lines.append(
        ProjectedLine(
            label="Corners Totales (λ)", value=round(lam_corners, 1), type="corners", prob=None
        )
    )
    for line in req.odds.corners_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(
            line, h_lam_corners, h_r_corners, a_lam_corners, a_r_corners
        )
        key = str(line)
        over_odds = req.odds.corners_over_odds.get(key)
        under_odds = req.odds.corners_under_odds.get(key)
        _or_corn = _overround(over_odds, under_odds)

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
        market_configs.append((f"Over {line} Corners", over_odds, p_over, _or_corn, p_push))
        market_configs.append((f"Under {line} Corners", under_odds, p_under, _or_corn, p_push))

    # ── Over/Under TARJETAS ──────────────────
    projected_lines.append(
        ProjectedLine(
            label="Tarjetas Totales (λ)", value=round(lam_cards, 1), type="cards", prob=None
        )
    )
    for line in req.odds.cards_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(
            line, h_lam_cards, h_r_cards, a_lam_cards, a_r_cards
        )
        key = str(line)
        over_odds = req.odds.cards_over_odds.get(key)
        under_odds = req.odds.cards_under_odds.get(key)
        _or_cards = _overround(over_odds, under_odds)

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
        market_configs.append((f"Over {line} Tarjetas", over_odds, p_over, _or_cards, p_push))
        market_configs.append((f"Under {line} Tarjetas", under_odds, p_under, _or_cards, p_push))

    # ── Over/Under TIROS TOTALES (Binomial Negativa con r combinado por equipo) ──────────────────
    projected_lines.append(
        ProjectedLine(label="Tiros Totales (λ)", value=round(lam_shots, 1), type="shots", prob=None)
    )
    for line in req.odds.shots_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(
            line, h_lam_shots, h_r_shots, a_lam_shots, a_r_shots
        )
        key = str(line)
        over_odds = req.odds.shots_over_odds.get(key)
        under_odds = req.odds.shots_under_odds.get(key)
        _or_shots = _overround(over_odds, under_odds)

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
        market_configs.append((f"Over {line} Tiros", over_odds, p_over, _or_shots, p_push))
        market_configs.append((f"Under {line} Tiros", under_odds, p_under, _or_shots, p_push))

    # ── Over/Under TIROS A PUERTA ──────────────────
    projected_lines.append(
        ProjectedLine(
            label="Tiros a Puerta (λ)",
            value=round(lam_shots_target, 1),
            type="shots_target",
            prob=None,
        )
    )
    for line in req.odds.shots_target_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(
            line, h_lam_shots_target, h_r_shots_target, a_lam_shots_target, a_r_shots_target
        )
        key = str(line)
        over_odds = req.odds.shots_target_over_odds.get(key)
        under_odds = req.odds.shots_target_under_odds.get(key)
        _or_shots_t = _overround(over_odds, under_odds)

        _ou_pairs.append((len(market_configs), len(market_configs) + 1, p_push))
        market_configs.append((f"Over {line} Tiros a Pta", over_odds, p_over, _or_shots_t, p_push))
        market_configs.append(
            (f"Under {line} Tiros a Pta", under_odds, p_under, _or_shots_t, p_push)
        )

    # ── Values: Cálculo masivo ─────────────
    values = [
        _vi(cfg[0], cfg[1], cfg[2], cfg[3], cfg[4], cfg[5] if len(cfg) > 5 else None)
        for cfg in market_configs
    ]

    # ── Issue #34: Renormalizar pares Over/Under tras calibración independiente ──
    # La calibración jerárquica se aplica por separado a Over y Under, lo que puede
    # romper la condición P(over) + P(push) + P(under) = 100%. Renormalizamos el par
    # calibrado conservando la ratio over/under del modelo crudo cuando hay push,
    # o derivando un lado del otro (under = 100 - push - over) cuando no hay push.
    for _oi, _ui, _push_pct in _ou_pairs:
        if _oi >= len(values) or _ui >= len(values):
            continue
        vo, vu = values[_oi], values[_ui]
        cal_o = vo.calibrated_prob
        cal_u = vu.calibrated_prob
        if cal_o is None or cal_u is None:
            continue
        available = max(0.0, 100.0 - _push_pct)  # probability budget excluding push
        raw_sum = cal_o + cal_u
        if raw_sum > 0.01 and abs(raw_sum - available) > 0.5:  # only fix if out of balance
            scale = available / raw_sum
            new_cal_o = round(max(0.0, min(available, cal_o * scale)), 1)
            new_cal_u = round(max(0.0, min(available, available - new_cal_o)), 1)
            vo.calibrated_prob = new_cal_o
            vu.calibrated_prob = new_cal_u
            # Also normalize model_prob to be consistent
            mp_o = vo.model_prob or 0.0
            mp_u = vu.model_prob or 0.0
            mp_sum = mp_o + mp_u
            if mp_sum > 0.01 and abs(mp_sum - available) > 0.5:
                mp_scale = available / mp_sum
                vo.model_prob = round(max(0.0, min(available, mp_o * mp_scale)), 1)
                vu.model_prob = round(max(0.0, min(available, available - vo.model_prob)), 1)

    # ── Deduplicación de picks correlacionados ──────────────────
    # Se elimina redundancia dentro del mismo mercado (p.ej. Over 1.5 + Over 2.5 Goles)
    # conservando únicamente la línea con mejor EV por dirección (over/under) y familia.
    values = _deduplicate_correlated_picks(values)

    # ── Sincronización de Calidad, Hit Rate Empírico y Publicabilidad ─────────────
    # Obtener historial de partidos de la liga para calcular Hit Rates reales (Filtro temporal estricto sin data leakage)
    # ── 1. Extraer ID del partido actual ──
    # FIX: se prioriza el parámetro explícito exclude_match_id (pasado por el llamador,
    # ej. history.id en el batch de re-análisis) sobre lo que venga dentro de req,
    # porque req suele reconstruirse desde un payload histórico que NO trae el id real.
    exclude_analysis_id = None
    if exclude_match_id is not None:
        exclude_analysis_id = exclude_match_id
    elif hasattr(req, "id") and req.id:
        exclude_analysis_id = req.id
    elif hasattr(req, "analysis_id") and req.analysis_id:
        exclude_analysis_id = req.analysis_id
    elif hasattr(req, "match_id") and req.match_id:
        exclude_analysis_id = req.match_id
    elif hasattr(req, "exclude_match_id") and req.exclude_match_id:
        exclude_analysis_id = req.exclude_match_id
    elif isinstance(req, dict):
        exclude_analysis_id = (
            req.get("id")
            or req.get("analysis_id")
            or req.get("match_id")
            or req.get("exclude_match_id")
        )

    # ── 2. Extraer Fecha/Hora del partido actual ──
    # FIX: mismo criterio de prioridad que arriba para current_match_date.
    raw_date = None
    if current_match_date is not None:
        raw_date = current_match_date
    elif hasattr(req, "match_date") and req.match_date:
        raw_date = req.match_date
    elif hasattr(req, "date") and req.date:
        raw_date = req.date
    elif isinstance(req, dict):
        raw_date = req.get("match_date") or req.get("date")

    current_match_time = None
    if raw_date:
        try:
            if isinstance(raw_date, datetime):
                current_match_time = raw_date
            else:
                date_str = str(raw_date).strip().replace("Z", "+00:00")
                if "T" in date_str or " " in date_str:
                    current_match_time = datetime.fromisoformat(date_str)
                elif len(date_str) >= 10:
                    current_match_time = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception as e:
            print(f"[DEBUG COMPARE] Error parseando raw_date: {e}")

    # ── Extraer Competición / Liga actual ──
    target_competition = None
    if hasattr(req, "competition") and req.competition:
        target_competition = str(req.competition).strip().lower()
    elif hasattr(req, "league") and req.league:
        target_competition = str(req.league).strip().lower()
    elif isinstance(req, dict):
        target_competition = (req.get("competition") or req.get("league") or "").strip().lower()

    current_match_time = _to_naive_utc(current_match_time)
    curr_date_only = current_match_time.date() if current_match_time else None
    historical_records = []
    if precomputed_historical_records is not None:
        source_rows = precomputed_historical_records
    elif db is not None:
        try:
            from sqlalchemy import text

            q_hist = text("""
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
            source_rows = [dict(r) for r in db.execute(q_hist).mappings().all()]
        except Exception:
            source_rows = []
    else:
        source_rows = []

    if source_rows:
        for r_dict in source_rows:
            m_id = r_dict.get("id")

            if (
                exclude_analysis_id
                and m_id
                and str(m_id).strip() == str(exclude_analysis_id).strip()
            ):
                continue

            # Filtro por competición/liga para evitar contaminar con estadísticas de otras ligas/homónimos
            if target_competition:
                r_comp = (r_dict.get("competition") or "").strip().lower()
                if (
                    r_comp
                    and r_comp != target_competition
                    and target_competition not in r_comp
                    and r_comp not in target_competition
                ):
                    continue

            m_date = r_dict.get("match_date")
            m_dt = None
            if m_date:
                try:
                    if isinstance(m_date, datetime):
                        m_dt = m_date
                    else:
                        m_s = str(m_date).replace("Z", "+00:00")
                        if "T" in m_s or " " in m_s:
                            m_dt = datetime.fromisoformat(m_s)
                        elif len(m_s) >= 10:
                            m_dt = datetime.strptime(m_s[:10], "%Y-%m-%d")
                except Exception:
                    m_dt = None

            m_dt = _to_naive_utc(m_dt)

            if current_match_time and m_dt and m_dt >= current_match_time:
                continue

            if curr_date_only and m_dt and m_dt.date() >= curr_date_only:
                continue

            historical_records.append(r_dict)

    from src.core.math_engine import LeagueMathEngine, get_league_profile
    from src.domain.temporal import TemporalCutoff

    _shared_cutoff = TemporalCutoff.create(current_match_time)

    target_profile = get_league_profile(target_competition)
    prof_half_life = float(target_profile.get("team_half_life_matches", 10.0))
    prof_prior_strength = float(target_profile.get("league_prior_strength", 12.0))

    # ── Check 6 (planning.txt): Omitir partidos si un equipo solo tiene Rating y Posesión ──
    def _team_has_only_rating_and_possession(team: Any) -> bool:
        if team is None:
            return False
        goals = getattr(team, "goals_per_game", 0.0) or getattr(team, "goals_scored", 0.0) or 0.0
        xg = getattr(team, "xg_per_game", 0.0) or 0.0
        shots = getattr(team, "shots_per_game", 0.0) or getattr(team, "shots", 0.0) or 0.0
        corners = getattr(team, "corners_per_game", 0.0) or getattr(team, "corners", 0.0) or 0.0
        cards = (
            getattr(team, "yellow_cards_per_game", 0.0) or getattr(team, "yellow_cards", 0.0) or 0.0
        )
        possession = getattr(team, "possession_pct", 0.0) or 0.0
        rating = getattr(team, "team_rating", 0.0) or getattr(team, "rating", 0.0) or 0.0
        no_core_stats = (
            goals == 0.0 and xg == 0.0 and shots == 0.0 and corners == 0.0 and cards == 0.0
        )
        has_basic_info = possession > 0.0 or rating > 0.0
        return no_core_stats and has_basic_info

    match_incomplete_stats = _team_has_only_rating_and_possession(
        h
    ) or _team_has_only_rating_and_possession(a)

    # ── Filtro de relevancia: solo records que involucren a H o A en la misma liga ──
    _h_lower = h.name.strip().lower()
    _a_lower = a.name.strip().lower()

    def _record_involves_team(rec: dict) -> bool:
        title = rec.get("match_title", "") or ""
        ht = (
            (rec.get("home_team") or (title.split(" vs ")[0] if " vs " in title else ""))
            .strip()
            .lower()
        )
        at = (
            (rec.get("away_team") or (title.split(" vs ")[1] if " vs " in title else ""))
            .strip()
            .lower()
        )
        return (
            _h_lower == ht
            or _h_lower == at
            or _h_lower in ht
            or _h_lower in at
            or _a_lower == ht
            or _a_lower == at
            or _a_lower in ht
            or _a_lower in at
        )

    if precomputed_team_index is not None:

        def _lookup_team(team_lower: str) -> list:
            if target_competition:
                exact_comp = precomputed_team_index.get(f"{target_competition}::{team_lower}")
                if exact_comp is not None:
                    return exact_comp
            exact = precomputed_team_index.get(team_lower)
            if exact is not None:
                if target_competition:
                    return [
                        r
                        for r in exact
                        if not r.get("competition")
                        or target_competition in str(r.get("competition")).lower()
                        or str(r.get("competition")).lower() in target_competition
                    ]
                return exact
            # Fallback: solo si el nombre no está en el índice
            return [r for r in historical_records if team_lower in r.get("match_title", "").lower()]

        _seen_ids = set()
        relevant_records = []
        for r in _lookup_team(_h_lower) + _lookup_team(_a_lower):
            rid = r.get("id")
            if rid in _seen_ids:
                continue
            _seen_ids.add(rid)
            relevant_records.append(r)
    else:
        relevant_records = [r for r in historical_records if _record_involves_team(r)]

    # ── Filtro por Temporada Actual para Hit Rates de Equipos ──
    target_year = current_match_time.year if current_match_time else datetime.now().year
    if isinstance(req, dict) and req.get("season_year"):
        try:
            target_year = int(req.get("season_year"))
        except Exception:
            pass

    def _is_current_season_record(rec: dict) -> bool:
        s_year = rec.get("season_year") or rec.get("season")
        if s_year is not None:
            if str(target_year) in str(s_year):
                return True
        m_date = rec.get("match_date")
        if m_date:
            try:
                if isinstance(m_date, datetime):
                    return m_date.year == target_year
                m_s = str(m_date)
                return str(target_year) in m_s[:4]
            except Exception:
                pass
        return False

    season_records = [r for r in relevant_records if _is_current_season_record(r)]
    team_hr_records = season_records if season_records else relevant_records

    for v in values:
        v.home_team = h.name
        v.away_team = a.name
        if match_incomplete_stats:
            block_pick(
                v,
                BlockReason.RULE_BLOCKED,
                detail="Partido omitido por datos insuficientes: al menos un equipo solo tiene Rating de equipo y Posesión",
            )
            continue

        # ── Hit Rate empírico (% de acierto real en partidos históricos de LA TEMPORADA ACTUAL para TODOS los mercados) ──
        if relevant_records:
            fam = _market_family(v.selection)
            side = _market_side(v.selection)
            line = _extract_line_number(v.selection)
            is_ov = side == "over"

            # Mapeo según familia de mercado
            if (
                fam in {"goals", "corners", "cards", "shots", "shots_target", "fouls"}
                and line is not None
            ):
                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records,
                    fam,
                    line=line,
                    is_over=is_ov,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    h.name,
                    fam,
                    line=line,
                    is_over=is_ov,
                    role_filter="home",
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    a.name,
                    fam,
                    line=line,
                    is_over=is_ov,
                    role_filter="away",
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(
                    relevant_records,
                    h.name,
                    a.name,
                    fam,
                    line=line,
                    is_over=is_ov,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
                # Ponderación de Hit Rate H2H por tamaño de muestra (planning.txt punto 3):
                # Si H2H tiene menos de 3 partidos se excluye (ruido), si tiene 3-4 se exige muestra mínima
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)

            elif fam in {"btts", "btts_yes", "btts_no"}:
                btts_fam = "btts_no" if "no" in side or "no" in v.selection.lower() else "btts_yes"
                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records,
                    btts_fam,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    h.name,
                    btts_fam,
                    role_filter="home",
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    a.name,
                    btts_fam,
                    role_filter="away",
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(
                    relevant_records,
                    h.name,
                    a.name,
                    btts_fam,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)

            elif fam in {"result", "moneyline", "1x2"}:
                sel_lower = v.selection.lower()
                if "home" in side or "local" in sel_lower:
                    tside = "home"
                elif "away" in side or "visitante" in sel_lower:
                    tside = "away"
                else:
                    tside = "draw"

                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records,
                    "1x2",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    h.name,
                    "1x2",
                    role_filter="home",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    a.name,
                    "1x2",
                    role_filter="away",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(
                    relevant_records,
                    h.name,
                    a.name,
                    "1x2",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                # Combinación equilibrada de la muestra de ambos equipos
                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)
                else:
                    v.empirical_hit_rate = None

            elif fam in {"double_chance", "doublechance"}:
                sel_lower = v.selection.lower()
                if "1x" in sel_lower or side in {"home_draw", "homedraw"}:
                    tside = "1x"
                elif "x2" in sel_lower or side in {"draw_away", "drawaway"}:
                    tside = "x2"
                else:
                    tside = "12"

                league_prior = LeagueMathEngine.compute_league_pick_hit_rate(
                    team_hr_records,
                    "double_chance",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )
                hr_h = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    h.name,
                    "double_chance",
                    role_filter="home",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_a = LeagueMathEngine.compute_pick_hit_rate_recency(
                    team_hr_records,
                    a.name,
                    "double_chance",
                    role_filter="away",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                    prior_rate=league_prior,
                    half_life=prof_half_life,
                    prior_strength=prof_prior_strength,
                )
                hr_h2h = LeagueMathEngine.compute_h2h_hit_rate(
                    relevant_records,
                    h.name,
                    a.name,
                    "double_chance",
                    target_side=tside,
                    exclude_match_id=exclude_analysis_id,
                    current_match_date=current_match_time,
                    cutoff=_shared_cutoff,
                )

                v.home_team = h.name
                v.away_team = a.name
                v.home_hit_rate = hr_h.get("hit_rate_pct")
                v.away_hit_rate = hr_a.get("hit_rate_pct")
                v.home_bayesian_ewma_hit_rate = hr_h.get("bayesian_ewma_hit_rate_pct")
                v.away_bayesian_ewma_hit_rate = hr_a.get("bayesian_ewma_hit_rate_pct")
                v.home_trend_label = hr_h.get("trend_label")
                v.away_trend_label = hr_a.get("trend_label")
                v.home_trend_delta_pp = hr_h.get("trend_delta_pp")
                v.away_trend_delta_pp = hr_a.get("trend_delta_pp")
                v.home_hits = hr_h.get("hits")
                v.home_matches_count = hr_h.get("sample_size")
                v.away_hits = hr_a.get("hits")
                v.away_matches_count = hr_a.get("sample_size")
                h2h_n = hr_h2h.get("sample_size", 0)
                v.h2h_samples = h2h_n
                v.h2h_hits = hr_h2h.get("hits")
                v.h2h_raw_hit_rate = hr_h2h.get("hit_rate_pct")
                v.h2h_hit_rate = hr_h2h.get("hit_rate_pct") if h2h_n >= 3 else None
                v.h2h_matches = hr_h2h.get("h2h_matches", [])

                # Combinación equilibrada de la muestra de ambos equipos
                tot_samples = hr_h.get("sample_size", 0) + hr_a.get("sample_size", 0)
                v.hit_rate_samples = tot_samples
                if tot_samples > 0:
                    tot_hits = hr_h.get("hits", 0) + hr_a.get("hits", 0)
                    v.empirical_hit_rate = round((tot_hits / tot_samples) * 100.0, 1)
                else:
                    v.empirical_hit_rate = None

        # #50: Veto por hit rate solo con muestra real y suficiente (emp_n >= 15).
        # Evitar falsos positivos por muestras cortas de 5-10 partidos con alta varianza.
        fam_v = _market_family(v.selection)
        emp_n = getattr(v, "hit_rate_samples", 0) or 0
        if v.empirical_hit_rate is not None and v.model_prob is not None and emp_n >= 15:
            gap = abs(v.model_prob - v.empirical_hit_rate)
            if fam_v in {"shots", "corners", "shots_target"} and gap > 20.0:
                block_pick(
                    v,
                    BlockReason.RULE_BLOCKED,
                    detail=f"Veto por brecha Prob Modelo ({v.model_prob}%) vs Hit Rate Total ({v.empirical_hit_rate}% en {emp_n} partidos) > 20 pts",
                )
            elif gap > 30.0 or (v.empirical_hit_rate < 15.0 and v.model_prob >= 50.0):
                block_pick(
                    v,
                    BlockReason.RULE_BLOCKED,
                    detail=f"Veto por inconsistencia empírica: Prob Modelo ({v.model_prob}%) vs Hit Rate Real ({v.empirical_hit_rate}% en {emp_n} partidos)",
                )

        q_score, s_support, p_support, strat_score = _rate_pick_quality(v, h, a, projected_lines)
        # quality_score siempre se almacena como métrica analítica.
        # Ya no es gate de publicación; el pick se muestra si tiene valor
        # (EV/edge/stake) y no está bloqueado por blacklist o correlación.
        v.quality_score = q_score
        v.strategic_score = strat_score
        v.stat_support = round(s_support, 1)
        v.proj_support = round(p_support, 1)
        evaluate_pick_eligibility(v)
        v.is_value = is_value_pick(v) and v.is_publishable
        # Los underdogs tienen cuotas > 2.50 que superan el max_odds del sistema
        # de eligibilidad (pensado para value picks), por lo que is_publishable
        # siempre les devuelve False (ODDS_TOO_HIGH). Se verifica únicamente que
        # no haya bloqueos duros activos.
        _not_hard_blocked = (
            not v.is_blacklisted
            and not v.is_rule_blocked
            and not getattr(v, "correlation_blocked", False)
        )
        v.is_underdog = is_underdog_pick(v) and _not_hard_blocked

    # ── Descorrelación de picks del mismo partido (reglas estructurales) ──
    values = resolve_match_picks_correlation(values)

    # ── Control de sobreexposición simultánea (Simultaneous Kelly Scaling) ──
    # Aplica el portfolio cap definido en RiskPolicy sobre todos los picks
    # publicables del análisis. Si la suma de kelly_fractions supera max_total_exposure,
    # todos se escalan proporcionalmente; picks que quedan bajo MIN_STAKE se
    # bloquean de forma irreversible con trazabilidad en eligibility_hard_blocks.
    _policy = RiskPolicy.from_json()
    values = apply_portfolio_exposure_cap(
        value_indicators=values,
        max_total_exposure=_policy.max_total_exposure,
        min_stake_threshold=float(MIN_STAKE),  # unidades absolutas (no fracción bankroll)
    )

    h_adv = sum(1 for c in comparisons if c.advantage == "home")
    a_adv = sum(1 for c in comparisons if c.advantage == "away")
    vp = [
        v
        for v in values
        if v.is_value
        and v.is_publishable
        and not getattr(v, "is_rule_blocked", False)
        and not getattr(v, "correlation_blocked", False)
    ]

    # ── Faltas y Offsides Lambdas ─────────────────────────────
    lam_fouls = _compute_fouls_lambda(h, a, req.league_stats, general=use_general, db=db)
    h_fouls_lam = _compute_team_fouls_lambda(
        h, a, req.league_stats, is_home=True, general=use_general, db=db
    )
    a_fouls_lam = _compute_team_fouls_lambda(
        a, h, req.league_stats, is_home=False, general=use_general, db=db
    )

    lam_offsides = _compute_offsides_lambda(h, a, req.league_stats, general=use_general, db=db)
    h_offsides_lam = _compute_team_offsides_lambda(
        h, a, req.league_stats, is_home=True, general=use_general, db=db
    )
    a_offsides_lam = _compute_team_offsides_lambda(
        a, h, req.league_stats, is_home=False, general=use_general, db=db
    )

    # ── Most Probable Score (mejorado) ──
    # Se elige el marcador con mayor probabilidad puntual de la distribución Dixon-Coles.
    # Adicionalmente se calcula un "score de confianza" ponderando el entorno de la moda.
    max_p = -1.0
    best_h, best_a = 0, 0
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            if matrix[i][j] > max_p:
                max_p = matrix[i][j]
                best_h, best_a = i, j

    # Probabilidad acumulada del marcador y sus vecinos directos (±1 gol) como medida de estabilidad
    _mps_neighborhood = 0.0
    for di in range(-1, 2):
        for dj in range(-1, 2):
            _ni, _nj = best_h + di, best_a + dj
            if 0 <= _ni < len(matrix) and 0 <= _nj < len(matrix[_ni]):
                _mps_neighborhood += matrix[_ni][_nj]
    _mps_confidence = round(_mps_neighborhood * 100.0, 1)

    most_probable_score = f"{best_h} - {best_a}"

    # ── Proyecciones por Equipo ───────────────────────────────
    projected_lines.append(
        ProjectedLine(label=f"Goles {h.name}", value=h_goals_lam, type="goals_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Goles {a.name}", value=a_goals_lam, type="goals_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Corners {h.name}", value=h_corners_lam, type="corners_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Corners {a.name}", value=a_corners_lam, type="corners_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Tarjetas {h.name}", value=h_cards_lam, type="cards_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Tarjetas {a.name}", value=a_cards_lam, type="cards_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Tiros {h.name}", value=h_shots_lam, type="shots_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Tiros {a.name}", value=a_shots_lam, type="shots_team")
    )
    projected_lines.append(
        ProjectedLine(
            label=f"Tiros a Pta {h.name}", value=h_shots_target_lam, type="shots_target_team"
        )
    )
    projected_lines.append(
        ProjectedLine(
            label=f"Tiros a Pta {a.name}", value=a_shots_target_lam, type="shots_target_team"
        )
    )

    projected_lines.append(
        ProjectedLine(
            label="Faltas Totales (λ)", value=round(lam_fouls, 1), type="fouls", prob=None
        )
    )
    projected_lines.append(
        ProjectedLine(label=f"Faltas {h.name}", value=h_fouls_lam, type="fouls_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Faltas {a.name}", value=a_fouls_lam, type="fouls_team")
    )
    projected_lines.append(
        ProjectedLine(
            label="Offsides Totales (λ)", value=round(lam_offsides, 1), type="offsides", prob=None
        )
    )
    projected_lines.append(
        ProjectedLine(label=f"Offsides {h.name}", value=h_offsides_lam, type="offsides_team")
    )
    projected_lines.append(
        ProjectedLine(label=f"Offsides {a.name}", value=a_offsides_lam, type="offsides_team")
    )

    summary = (
        f"Sherlock Analytics | λ Goles: {h.name} {h_lam:.2f} - {a.name} {a_lam:.2f}\\n"
        f"Proyección Total: {projected_total_goals:.2f} Goles | {lam_corners:.1f} Corners | {lam_cards:.1f} Tarjetas | {lam_shots:.1f} Tiros | {lam_shots_target:.1f} a Pta\\n"
        f"Goles por equipo: {h.name} {h_goals_lam:.2f} | {a.name} {a_goals_lam:.2f}\\n"
        f"Corners por equipo: {h.name} {h_corners_lam:.1f} | {a.name} {a_corners_lam:.1f}\\n"
        f"Tarjetas por equipo: {h.name} {h_cards_lam:.1f} | {a.name} {a_cards_lam:.1f}\\n"
        + (
            f"✅ Value detectado en: {', '.join(v.selection for v in vp)}"
            if vp
            else "⚖️ Sin value claro en las cuotas actuales."
        )
    )

    llm = None
    if req.generate_llm_analysis:
        llm = await generate_football_analysis(
            h, a, vp, projected_lines, req.league_stats, competition=req.competition
        )

    return CompareResponse(
        sport="football",
        home_name=h.name,
        away_name=a.name,
        h_lam=h_goals_lam,
        a_lam=a_goals_lam,
        h_corners_lam=h_corners_lam,
        a_corners_lam=a_corners_lam,
        h_cards_lam=h_cards_lam,
        a_cards_lam=a_cards_lam,
        h_fouls_lam=h_fouls_lam,
        a_fouls_lam=a_fouls_lam,
        h_offsides_lam=h_offsides_lam,
        a_offsides_lam=a_offsides_lam,
        most_probable_score=most_probable_score,
        mps_confidence=_mps_confidence,
        comparisons=comparisons,
        values=values,
        projected_lines=projected_lines,
        summary=summary,
        llm_analysis=llm,
    )


if __name__ == "__main__":
    casos = [
        ("Cuota baja, prob alta", 82.1, 1.55),
        ("Cuota media", 50.0, 2.46),
        ("Cuota alta, prob baja", 28.7, 5.40),
        ("Sin valor (prob = implícita)", 40.7, 2.46),
    ]
    for nombre, prob, odds in casos:
        kf = _calculate_kelly_fraction(prob, odds)
        implied = 1 / odds * 100
        ev = (prob / 100 * odds) - 1
        print(
            f"{nombre:35s} | prob={prob:5.1f}% odds={odds:4.2f} "
            f"implied={implied:5.1f}% EV={ev:+.3f} -> Kelly 1/4={kf * 100:5.2f}%"
        )
