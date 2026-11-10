"""Lambdas (goles, córners, tarjetas, tiros, faltas, offsides) por equipo y partido.

Extraídas de src/ui/api/compare.py. `db` se inyecta por parámetro; no hay
imports de FastAPI ni de src.ui. Los DTOs se tipan como Any a propósito.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.core.math.bayesian import update_gamma_poisson
from src.core.prediction.score_matrix import get_dispersion_r

_FINAL_STAT_COLS = (
    "final_score_home", "final_score_away",
    "final_corners_home", "final_corners_away",
    "final_yellow_cards_home", "final_yellow_cards_away",
    "final_red_cards_home", "final_red_cards_away",
    "final_shots_home", "final_shots_away",
    "final_shots_on_target_home", "final_shots_on_target_away",
    "final_fouls_home", "final_fouls_away",
    "final_offsides_home", "final_offsides_away",
)


def _estimate_league_variance(
    competition_name: str, metric: str, mean_val: float, db: Any = None
) -> float:
    fano_factors = {
        "goals": 1.15,
        "corners": 1.40,
        "cards": 1.80,
        "shots": 2.50,
        "shots_target": 2.00,
        "fouls": 1.50,
        "offsides": 1.30,
    }
    fallback_fano = fano_factors.get(metric, 1.20)

    # ── Issue #25: Estimar varianza real desde AnalysisHistory en lugar de tablas legacy ──
    if (
        db is not None
        and competition_name
        and competition_name not in ("Desconocida", "General", "")
    ):
        try:
            from src.core.domain import AnalysisHistory
            from src.core.entity_resolver import competition_filter

            # Solo columnas de resultado: evita hidratar payload/snapshots JSON de cada fila.
            rows = (
                db.query(*[getattr(AnalysisHistory, c) for c in _FINAL_STAT_COLS])
                .filter(
                    competition_filter(db, competition_name),
                    AnalysisHistory.final_score_home.isnot(None),
                    AnalysisHistory.final_score_away.isnot(None),
                )
                .order_by(AnalysisHistory.date.desc())
                .limit(100)
                .all()
            )

            if len(rows) >= 8:
                vals: list[float] = []
                for r in rows:
                    if metric == "goals":
                        if r.final_score_home is not None:
                            vals.append(float(r.final_score_home))
                        if r.final_score_away is not None:
                            vals.append(float(r.final_score_away))
                    elif metric == "corners":
                        if r.final_corners_home is not None:
                            vals.append(float(r.final_corners_home))
                        if r.final_corners_away is not None:
                            vals.append(float(r.final_corners_away))
                    elif metric == "cards":
                        if (
                            r.final_yellow_cards_home is not None
                            or r.final_red_cards_home is not None
                        ):
                            vals.append(
                                float(
                                    (r.final_yellow_cards_home or 0)
                                    + (r.final_red_cards_home or 0) * 2.0
                                )
                            )
                        if (
                            r.final_yellow_cards_away is not None
                            or r.final_red_cards_away is not None
                        ):
                            vals.append(
                                float(
                                    (r.final_yellow_cards_away or 0)
                                    + (r.final_red_cards_away or 0) * 2.0
                                )
                            )
                    elif metric == "shots":
                        if r.final_shots_home is not None:
                            vals.append(float(r.final_shots_home))
                        if r.final_shots_away is not None:
                            vals.append(float(r.final_shots_away))
                    elif metric == "shots_target":
                        if r.final_shots_on_target_home is not None:
                            vals.append(float(r.final_shots_on_target_home))
                        if r.final_shots_on_target_away is not None:
                            vals.append(float(r.final_shots_on_target_away))
                    elif metric == "fouls":
                        if r.final_fouls_home is not None:
                            vals.append(float(r.final_fouls_home))
                        if r.final_fouls_away is not None:
                            vals.append(float(r.final_fouls_away))
                    elif metric == "offsides":
                        if r.final_offsides_home is not None:
                            vals.append(float(r.final_offsides_home))
                        if r.final_offsides_away is not None:
                            vals.append(float(r.final_offsides_away))

                if len(vals) >= 8:
                    avg = sum(vals) / len(vals)
                    var = sum((x - avg) ** 2 for x in vals) / (len(vals) - 1)
                    if var > 0.05:
                        return var
        except Exception:
            pass

    return mean_val * fallback_fano


def estimate_empirical_bayes_prior_n(
    league_variance: float,
    league_mean: float,
    team_matches: int = 10,
    data_quality_score: float | None = None,
    baseline_prior_n: float = 6.0,
    min_prior_n: float = 2.0,
    max_prior_n: float = 14.0,
) -> float:
    """
    Estima dinámicamente prior_n para Empirical Bayes shrinkage:
    - Fano Factor F = league_variance / max(league_mean, 0.1)
    - Factor de calidad de datos DQ_adj in [0.8, 1.4]:
        DQ_adj = 1.0 + (1.0 - clip(data_quality_score, 0, 100) / 100.0) * 0.4
    - Factor de muestra del equipo N_adj in [0.8, 1.3]:
        N_adj = max(0.8, min(1.3, 10.0 / max(team_matches, 1)))
    - prior_n = baseline_prior_n * F * DQ_adj * N_adj acotado a [min_prior_n, max_prior_n].
    """
    if league_mean <= 0:
        return round(float(np.clip(baseline_prior_n, min_prior_n, max_prior_n)), 2)

    fano = league_variance / max(league_mean, 0.1)

    dq_val = 50.0 if data_quality_score is None else float(np.clip(data_quality_score, 0.0, 100.0))
    dq_adj = 1.0 + (1.0 - (dq_val / 100.0)) * 0.4

    n_matches = max(int(team_matches), 1)
    n_adj = max(0.8, min(1.3, 10.0 / float(n_matches)))

    prior_n = baseline_prior_n * fano * dq_adj * n_adj
    return round(float(np.clip(prior_n, min_prior_n, max_prior_n)), 2)


def _compute_team_goals_lambda(
    attacker: Any,
    defender: Any,
    league: Any,
    is_home: bool,
    general: bool = False,
    db: Any = None,
    data_quality_score: float | None = None,
) -> float:
    avg_team_goals = league.avg_goals_per_game / 2.0

    prior_att_xg = attacker.xg_per_game
    actual_att_g = attacker.goals_per_game
    prior_def_xga = defender.xga_per_game
    actual_def_g = defender.goals_conceded_per_game

    # ── Determinar nº de partidos (att_n, def_n) — necesario para conversiones por juego
    if general:
        att_n = max(attacker.matches_played, 1)
        def_n = max(defender.matches_played, 1)
    else:
        if is_home:
            att_n = max(attacker.matches_home, 1)
            def_n = max(defender.matches_away, 1)
        else:
            att_n = max(attacker.matches_away, 1)
            def_n = max(defender.matches_home, 1)

    # Dynamic prior_n estimation using Empirical Bayes
    goals_mean = league.avg_goals_per_game
    goals_var = _estimate_league_variance(
        getattr(league, "name", "Desconocida"), "goals", goals_mean, db=db
    )
    fano = goals_var / max(goals_mean, 0.1)

    # ── Issue #20: Ponderación de goles y xG por varianza observada ──
    # En muestras pequeñas el xG predice mejor que los goles reales (menor varianza);
    # conforme aumentan los partidos, los goles reales ganan peso según la varianza.
    w_xg = 1.0 / (1.0 + (att_n / max(5.0 * fano, 1.0)))
    if prior_att_xg is not None and prior_att_xg > 0:
        att_rate = (1.0 - w_xg) * actual_att_g + w_xg * prior_att_xg
    else:
        att_rate = actual_att_g

    w_xga = 1.0 / (1.0 + (def_n / max(5.0 * fano, 1.0)))
    if prior_def_xga is not None and prior_def_xga > 0:
        def_rate = (1.0 - w_xga) * actual_def_g + w_xga * prior_def_xga
    else:
        def_rate = actual_def_g

    # ── Issue #20: Un solo shrinkage Bayesiano hacia la media de liga ──
    # Empirical Bayes Gamma-Poisson shrinkage for attack and defense rates
    # Prior Gamma: media = media de liga por equipo, fuerza k = prior_n empírico (Fano/calidad/muestra).
    k_prior = estimate_empirical_bayes_prior_n(
        goals_var, goals_mean, min(att_n, def_n), data_quality_score,
        baseline_prior_n=5.0, max_prior_n=8.0,  # CLAUDE.md: prior_n=5 para goles
    )
    alpha_prior, beta_prior = avg_team_goals * k_prior, k_prior
    post_att_rate = update_gamma_poisson(alpha_prior, beta_prior, att_rate * att_n, att_n)
    post_def_rate = update_gamma_poisson(alpha_prior, beta_prior, def_rate * def_n, def_n)

    att_str = post_att_rate / max(avg_team_goals, 0.1)
    def_weakness = post_def_rate / max(avg_team_goals, 0.1)

    # ── Issue #18: Factor de localía derivado de la liga incorporado directamente al lambda ──
    home_factor = league.home_advantage_factor if is_home else league.away_disadvantage_factor

    # ── Lambda Base ──
    lam_base = att_str * def_weakness * avg_team_goals * home_factor

    # ── 5. Ajuste por forma reciente (ventanas 5 / 10 / 15) — Issue #21 ──
    form_factor_att = 1.0
    form_factor_def = 1.0

    att_recent = getattr(attacker, "recent_form", None) or getattr(
        attacker, "recent_form_stats", None
    )
    if att_recent and isinstance(att_recent, dict):
        w5 = att_recent.get("last_5", {}).get("goals_scored", avg_team_goals)
        w10 = att_recent.get("last_10", {}).get("goals_scored", avg_team_goals)
        w15 = att_recent.get("last_15", {}).get("goals_scored", avg_team_goals)
        form_avg_att = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        # Forma relativa a la tasa de temporada del propio equipo (no a la liga: ya está en att_str),
        # amortiguada con exponente 0.35 para no contar dos veces la misma información.
        form_factor_att = (form_avg_att / max(att_rate, 0.10)) ** 0.35
        form_factor_att = max(0.85, min(1.15, form_factor_att))

    def_recent = getattr(defender, "recent_form", None) or getattr(
        defender, "recent_form_stats", None
    )
    if def_recent and isinstance(def_recent, dict):
        w5 = def_recent.get("last_5", {}).get("goals_conceded", avg_team_goals)
        w10 = def_recent.get("last_10", {}).get("goals_conceded", avg_team_goals)
        w15 = def_recent.get("last_15", {}).get("goals_conceded", avg_team_goals)
        form_avg_def = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor_def = (form_avg_def / max(def_rate, 0.10)) ** 0.35
        form_factor_def = max(0.85, min(1.15, form_factor_def))

    lam_final = lam_base * form_factor_att * form_factor_def
    return max(lam_final, 0.10)


def _compute_team_corners_lambda(
    team: Any,
    opponent: Any,
    league: Any,
    is_home: bool,
    general: bool = False,
    db: Any = None,
    data_quality_score: float | None = None,
) -> tuple[float, float]:
    """Retorna (mu, r) de la distribución Binomial Negativa para corners del equipo.

    La sobredispersión es intrínseca a corners (Var > Media), por lo que se usa
    Binomial Negativa en lugar de Poisson. El parámetro r = mu / (fano - 1).
    """
    avg_team_corners = league.avg_corners_per_game / 2.0

    # ── 1. Fuerza de generación de corners: normalizada contra media de liga ──
    att_str = team.corners_per_game / max(avg_team_corners, 0.5)
    att_str = max(0.40, min(2.0, att_str))

    # ── 2. Capacidad del rival de conceder corners: normalizada contra media ──
    opp_conceded = opponent.corners_conceded_per_game / max(avg_team_corners, 0.5)
    opp_conceded = max(0.40, min(2.0, opp_conceded))

    # ── 3. Lambda base: ataque x debilidad rival, anclado a media de liga ──
    lam = att_str * opp_conceded * avg_team_corners

    # ── 4. Ajuste por forma reciente de corners (ventanas 5 / 10 / 15) ──
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5 = team_recent.get("last_5", {}).get("corners", avg_team_corners)
        w10 = team_recent.get("last_10", {}).get("corners", avg_team_corners)
        w15 = team_recent.get("last_15", {}).get("corners", avg_team_corners)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_corners, 0.5)
        # Acotar factor de forma para evitar distorsionar el histórico base en mercados de conteo
        form_factor = max(0.85, min(1.15, form_factor))

    lam = lam * form_factor

    # ── 5. Shrinkage bayesiana con Empirical Bayes ──
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away
    corners_mean = league.avg_corners_per_game
    corners_var = _estimate_league_variance(
        getattr(league, "name", "Desconocida"), "corners", corners_mean, db=db
    )
    n = max(m_count, 1)
    prior_n_c = estimate_empirical_bayes_prior_n(
        corners_var,
        corners_mean,
        team_matches=n,
        data_quality_score=data_quality_score,
        baseline_prior_n=5.0,
    )
    shrink_w_c = prior_n_c / (prior_n_c + n)
    lam = lam * (1.0 - shrink_w_c) + avg_team_corners * shrink_w_c

    # ── Issue #28: Factor de localía por métrica de corners ──
    # local genera más corners que visitante (~+10-15% de promedio de liga)
    home_corner_factor = (
        league.home_advantage_factor if is_home else league.away_disadvantage_factor
    )
    lam = lam * home_corner_factor
    mu = max(lam, 0.5)

    # ── Issue #23: Varianza por equipo = Fano × mu (no var/4) ──
    fano_corners = corners_var / max(corners_mean, 0.1)
    team_var = fano_corners * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))

    return mu, r


def _compute_team_cards_lambda(
    team: Any,
    opponent: Any,
    league: Any,
    is_home: bool,
    general: bool = False,
    db: Any = None,
    data_quality_score: float | None = None,
) -> float:
    if general:
        actual_matches = max(team.matches_played, 1)
        opp_matches = max(opponent.matches_played, 1)
    else:
        actual_matches = max(team.matches_home if is_home else team.matches_away, 1)
        opp_matches = max(opponent.matches_away if is_home else opponent.matches_home, 1)

    # Determinar promedio de liga (tarjetas equivalentes ponderadas)
    if league.avg_yellow_cards_per_game > 0 and league.avg_red_cards_per_game > 0:
        league_cards_avg = league.avg_yellow_cards_per_game + (league.avg_red_cards_per_game * 2.0)
    else:
        league_cards_avg = league.avg_cards_per_game
    avg_team_cards = league_cards_avg / 2.0

    # Dynamic prior_n estimation using Empirical Bayes
    cards_mean = league_cards_avg
    cards_var = _estimate_league_variance(
        getattr(league, "name", "Desconocida"), "cards", cards_mean, db=db
    )
    prior_n = estimate_empirical_bayes_prior_n(
        cards_var,
        cards_mean,
        team_matches=actual_matches,
        data_quality_score=data_quality_score,
        baseline_prior_n=10.0,
    )

    # 1. Fuerza de disciplina del equipo normalizada contra la media de liga
    red_card_weight = 2.0
    team_reds_per_game = (team.red_cards_total / actual_matches) * red_card_weight
    own_cards_avg = team.yellow_cards_per_game + team_reds_per_game

    # Shrinkage bayesiana al promedio de liga (primer paso)
    shrink_w_pre = prior_n / (prior_n + actual_matches)
    own_cards_avg = own_cards_avg * (1.0 - shrink_w_pre) + avg_team_cards * shrink_w_pre

    # 2. Ratio de disciplina del equipo vs media de liga (continuo, sin escalones)
    team_card_ratio = own_cards_avg / max(avg_team_cards, 0.5)
    team_card_ratio = max(0.50, min(1.50, team_card_ratio))

    # 3. Ratio de tarjetas provocadas del rival (cuánto genera el rival)
    rival_draw_cards_avg = (
        opponent.yellow_cards_against + (opponent.red_cards_against * 2.0)
    ) / opp_matches
    rival_ratio = rival_draw_cards_avg / max(avg_team_cards, 0.5)
    rival_ratio = max(0.50, min(1.50, rival_ratio))

    lam = own_cards_avg * rival_ratio

    # 4. Ajuste por forma reciente de tarjetas (ventanas 5 / 10 / 15)
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5 = team_recent.get("last_5", {}).get("yellow_cards", avg_team_cards)
        w10 = team_recent.get("last_10", {}).get("yellow_cards", avg_team_cards)
        w15 = team_recent.get("last_15", {}).get("yellow_cards", avg_team_cards)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_cards, 0.5)
        form_factor = max(0.70, min(1.30, form_factor))

    lam = lam * form_factor

    # 5. Integración del Árbitro (dato real — conservar)
    if league.referee_avg_yellow > 0:
        ref_baseline = league.referee_avg_yellow + (league.referee_avg_red * 2.0)
        ref_dev_ratio = ref_baseline / max(league_cards_avg, 1.0)
        ref_modifier = 1.0 + (ref_dev_ratio - 1.0) * 0.50
        ref_modifier = max(0.70, min(1.30, ref_modifier))
        lam *= ref_modifier

    # 6. Shrinkage final al promedio de liga
    k_cd = estimate_empirical_bayes_prior_n(cards_var, cards_mean, actual_matches)
    alpha_prior_cd, beta_prior_cd = avg_team_cards * k_cd, k_cd
    lam = update_gamma_poisson(alpha_prior_cd, beta_prior_cd, lam * actual_matches, actual_matches)

    # ── Issue #28: Factor de localía para tarjetas (visitante recibe más amarillas) ──
    # El equipo visitante suele cometer más faltas y recibir más tarjetas (~+8%)
    card_home_factor = 0.95 if is_home else 1.05
    lam = lam * card_home_factor

    mu = max(lam, 0.4)
    # ── Issue #23: Varianza por equipo = Fano × mu ──
    fano_cards = cards_var / max(cards_mean, 0.1)
    team_var = fano_cards * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))
    return mu, r


def _compute_team_shots_lambda(
    team: Any,
    opponent: Any,
    league: Any,
    is_home: bool,
    general: bool = False,
    db: Any = None,
    data_quality_score: float | None = None,
) -> tuple[float, float]:
    """Retorna (mu, r) de la distribución Binomial Negativa para tiros del equipo.

    La sobredispersión es intrínseca a los tiros (Var >> Media, Fano ~2.5), por lo
    que se usa Binomial Negativa en lugar de Poisson para modelar las colas correctamente.
    """
    avg_team_shots = league.avg_shots_per_game / 2.0

    # ── 1. Fuerza de tiros del equipo normalizada contra media de liga ──
    att_str = team.shots_per_game / max(avg_team_shots, 1.0)
    att_str = max(0.40, min(2.0, att_str))

    # ── 2. Debilidad defensiva del rival: tiros concedidos vs media de liga ──
    opp_shots_conceded = opponent.shots_against_per_game
    def_weakness = opp_shots_conceded / max(avg_team_shots, 1.0)
    def_weakness = max(0.40, min(2.0, def_weakness))

    # ── 3. Lambda base ──
    lam = att_str * def_weakness * avg_team_shots

    # ── 4. Ajuste por forma reciente de tiros (ventanas 5 / 10 / 15) ──
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5 = team_recent.get("last_5", {}).get("shots", avg_team_shots)
        w10 = team_recent.get("last_10", {}).get("shots", avg_team_shots)
        w15 = team_recent.get("last_15", {}).get("shots", avg_team_shots)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_shots, 1.0)
        # Acotar factor de forma para evitar distorsionar el histórico base en mercados de conteo
        form_factor = max(0.85, min(1.15, form_factor))

    lam = lam * form_factor

    # ── 5. Shrinkage bayesiana con Empirical Bayes ──
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away

    shots_mean = league.avg_shots_per_game
    shots_var = _estimate_league_variance(
        getattr(league, "name", "Desconocida"), "shots", shots_mean, db=db
    )
    n = max(m_count, 1)
    prior_n = estimate_empirical_bayes_prior_n(
        shots_var,
        shots_mean,
        team_matches=n,
        data_quality_score=data_quality_score,
        baseline_prior_n=5.0,
    )

    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_shots * shrink_w
    mu = max(lam, 1.0)

    # ── Issue #23: Varianza por equipo = Fano × mu ──
    fano_shots = shots_var / max(shots_mean, 0.1)
    team_var = fano_shots * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))

    return mu, r


def _compute_team_shots_target_lambda(
    team: Any,
    opponent: Any,
    league: Any,
    is_home: bool,
    general: bool = False,
    db: Any = None,
    data_quality_score: float | None = None,
) -> tuple[float, float]:
    avg_team_sot = league.avg_shots_target_per_game / 2.0

    # ── 1. Fuerza de tiros a puerta normalizada ──
    att_str = team.shots_on_target_per_game / max(avg_team_sot, 0.5)
    att_str = max(0.40, min(2.0, att_str))

    # ── 2. Debilidad defensiva del rival en tiros a puerta ──
    def_weakness = opponent.shots_on_target_against_per_game / max(avg_team_sot, 0.5)
    def_weakness = max(0.40, min(2.0, def_weakness))

    # ── 3. Lambda base ──
    lam = att_str * def_weakness * avg_team_sot

    # ── 4. Ajuste por forma reciente (ventanas 5 / 10 / 15) ──
    form_factor = 1.0
    team_recent = getattr(team, "recent_form", None)
    if team_recent and isinstance(team_recent, dict):
        w5 = team_recent.get("last_5", {}).get("shots_target") or team_recent.get("last_5", {}).get(
            "shots_on_target", avg_team_sot
        )
        w10 = team_recent.get("last_10", {}).get("shots_target") or team_recent.get(
            "last_10", {}
        ).get("shots_on_target", avg_team_sot)
        w15 = team_recent.get("last_15", {}).get("shots_target") or team_recent.get(
            "last_15", {}
        ).get("shots_on_target", avg_team_sot)
        form_avg = 0.50 * w5 + 0.30 * w10 + 0.20 * w15
        form_factor = form_avg / max(avg_team_sot, 0.5)
        # Acotar factor de forma para evitar distorsionar el histórico base en mercados de conteo
        form_factor = max(0.85, min(1.15, form_factor))

    lam = lam * form_factor

    # ── 5. Shrinkage bayesiana con Empirical Bayes ──
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away

    sot_mean = league.avg_shots_target_per_game
    sot_var = _estimate_league_variance(
        getattr(league, "name", "Desconocida"), "shots_target", sot_mean, db=db
    )
    n = max(m_count, 1)
    prior_n = estimate_empirical_bayes_prior_n(
        sot_var,
        sot_mean,
        team_matches=n,
        data_quality_score=data_quality_score,
        baseline_prior_n=5.0,
    )

    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_sot * shrink_w
    mu = max(lam, 0.5)
    # ── Issue #23: Varianza por equipo = Fano × mu ──
    fano_sot = sot_var / max(sot_mean, 0.1)
    team_var = fano_sot * mu
    r = get_dispersion_r(mu, max(team_var, mu * 1.05))
    return mu, r


def _compute_corners_lambda(
    h: Any, a: Any, league: Any, general: bool = False, db: Any = None
) -> tuple[float, float, float, float]:
    """Retorna (h_mu, h_r, a_mu, a_r) para corners de cada equipo (Binomial Negativa)."""
    h_mu, h_r = _compute_team_corners_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_corners_lambda(a, h, league, is_home=False, general=general, db=db)

    # Fallback si la suma total es demasiado baja
    if (h_mu + a_mu) < 2.0:
        avg = league.avg_corners_per_game / 2.0
        corners_var = _estimate_league_variance(
            getattr(league, "name", "Desconocida"), "corners", avg
        )
        fallback_r = get_dispersion_r(avg, max(corners_var, avg + 0.01))
        h_mu = avg
        h_r = fallback_r
        a_mu = avg
        a_r = fallback_r

    return h_mu, h_r, a_mu, a_r


def _compute_cards_lambda(
    h: Any, a: Any, league: Any, general: bool = False, db: Any = None
) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_cards_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_cards_lambda(a, h, league, is_home=False, general=general, db=db)

    h_r = max(4.0, h_r)
    a_r = max(4.0, a_r)

    if (h_mu + a_mu) < 1.0:
        factor = league.avg_cards_per_game / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r


def _compute_shots_lambda(
    h: Any, a: Any, league: Any, general: bool = False, db: Any = None
) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_shots_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_lambda(a, h, league, is_home=False, general=general, db=db)

    min_total = league.avg_shots_per_game * 0.5
    if (h_mu + a_mu) < min_total:
        factor = min_total / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r


def _compute_shots_target_lambda(
    h: Any, a: Any, league: Any, general: bool = False, db: Any = None
) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_shots_target_lambda(
        h, a, league, is_home=True, general=general, db=db
    )
    a_mu, a_r = _compute_team_shots_target_lambda(
        a, h, league, is_home=False, general=general, db=db
    )

    min_total = league.avg_shots_target_per_game * 0.5
    if (h_mu + a_mu) < min_total:
        factor = min_total / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r


def _compute_team_fouls_lambda(
    team: Any,
    opponent: Any,
    league: Any,
    is_home: bool,
    general: bool = False,
    db: Any = None,
) -> float:
    avg_league_fouls = getattr(league, "avg_fouls_per_game", 22.0)
    avg_team_fouls = avg_league_fouls / 2.0
    gen_str = team.fouls_per_game if team.fouls_per_game > 0 else avg_team_fouls

    # NUEVO: Factor de intensidad física
    physical_intensity = 1.0
    if team.kilometers_covered > 105:
        physical_intensity = 1.08
    elif team.kilometers_covered > 95:
        physical_intensity = 1.04

    if team.number_of_sprints > 300:
        physical_intensity *= 1.05

    # NUEVO: Duelos totales como proxy de contacto físico
    duel_factor = 1.0 + (team.duels_total_per_game - 45.0) * 0.003  # 45 es referencia

    # NUEVO: Posesión rival (más posesión rival = más faltas para recuperar)
    opp_possession = (
        opponent.possession_pct
        if (opponent.possession_pct is not None and opponent.possession_pct > 0)
        else 50.0
    )
    opp_factor = max(opp_possession / 50.0, 0.5)

    lam = gen_str * opp_factor * physical_intensity * duel_factor
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away

    # Dynamic prior_n from Negative Binomial dispersion: r = mu² / (var - mu)
    fouls_mean = avg_team_fouls
    fouls_var = _estimate_league_variance(
        getattr(league, "name", "Desconocida"), "fouls", fouls_mean, db=db
    )
    if fouls_var > fouls_mean:
        prior_n = max(1.0, min(8.0, fouls_mean**2 / (fouls_var - fouls_mean)))
    else:
        prior_n = 2.0

    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_fouls * shrink_w
    return max(lam, 1.0)


def _compute_fouls_lambda(
    h: Any, a: Any, league: Any, general: bool = False, db: Any = None
) -> float:
    h_f_exp = _compute_team_fouls_lambda(h, a, league, is_home=True, general=general, db=db)
    a_f_exp = _compute_team_fouls_lambda(a, h, league, is_home=False, general=general, db=db)
    lam_fouls = h_f_exp + a_f_exp
    avg_league_fouls = getattr(league, "avg_fouls_per_game", 22.0)
    return max(lam_fouls, avg_league_fouls * 0.5)


def _compute_team_offsides_lambda(
    team: Any,
    opponent: Any,
    league: Any,
    is_home: bool,
    general: bool = False,
    db: Any = None,
) -> float:
    avg_league_offsides = getattr(league, "avg_offsides_per_game", 3.5)
    avg_team_offsides = avg_league_offsides / 2.0
    gen_str = team.offside_per_game if team.offside_per_game > 0 else avg_team_offsides

    team_possession = (
        team.possession_pct
        if (team.possession_pct is not None and team.possession_pct > 0)
        else 50.0
    )
    pos_factor = max(team_possession / 50.0, 0.5)

    # NUEVO: Contraataques aumentan offsides (línea defensiva alta del rival)
    fastbreak_factor = 1.0 + min(team.fast_breaks / 15.0, 0.10)

    # NUEVO: Dribbles exitosos = más penetración = más offsides potenciales
    dribble_factor = 1.0 + min(team.dribble_success_pct / 300.0, 0.05)

    lam = gen_str * pos_factor * fastbreak_factor * dribble_factor
    if general:
        m_count = team.matches_played
    else:
        m_count = team.matches_home if is_home else team.matches_away

    # Dynamic prior_n from Negative Binomial dispersion: r = mu² / (var - mu)
    offsides_mean = avg_team_offsides
    offsides_var = _estimate_league_variance(
        getattr(league, "name", "Desconocida"), "offsides", offsides_mean, db=db
    )
    if offsides_var > offsides_mean:
        prior_n = max(1.0, min(8.0, offsides_mean**2 / (offsides_var - offsides_mean)))
    else:
        prior_n = 2.0

    n = max(m_count, 1)
    shrink_w = prior_n / (prior_n + n)
    lam = lam * (1.0 - shrink_w) + avg_team_offsides * shrink_w
    return max(lam, 0.1)


def _compute_offsides_lambda(
    h: Any, a: Any, league: Any, general: bool = False, db: Any = None
) -> float:
    h_o_exp = _compute_team_offsides_lambda(h, a, league, is_home=True, general=general, db=db)
    a_o_exp = _compute_team_offsides_lambda(a, h, league, is_home=False, general=general, db=db)
    lam_offsides = h_o_exp + a_o_exp
    avg_league_offsides = getattr(league, "avg_offsides_per_game", 3.5)
    return max(lam_offsides, avg_league_offsides * 0.5)
