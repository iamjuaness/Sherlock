"""Matrices de marcador Dixon-Coles y distribuciones Poisson/binomial negativa.

Funciones puras (sin DB ni estado global). Extraídas de src/ui/api/compare.py.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.special import gammaln

from src.core.math.dixon_coles import build_dixon_coles_matrix


def _poisson_pmf(lam: float, k: int) -> float:
    return (lam**k * math.exp(-lam)) / math.factorial(k)


def _neg_bin_pmf(mu: float, r: float, k: int) -> float:
    if mu <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + mu)
    try:
        log_pmf = (
            math.lgamma(k + r)
            - math.lgamma(r)
            - math.lgamma(k + 1)
            + r * math.log(p)
            + k * math.log(1.0 - p)
        )
        return math.exp(log_pmf)
    except (ValueError, OverflowError):
        return 0.0


def _nbinom_pmf(k: int, mu: float, r: float) -> float:
    if mu <= 0 or r <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + mu)
    try:
        log_pmf = (
            math.lgamma(k + r)
            - math.lgamma(r)
            - math.lgamma(k + 1)
            + r * math.log(p)
            + k * math.log(1.0 - p)
        )
        return math.exp(log_pmf)
    except (ValueError, OverflowError):
        return 0.0


def get_dispersion_r(mu: float, variance: float) -> float:
    if variance <= mu * 1.01:
        return 100.0
    r = (mu**2) / (variance - mu)
    return max(0.1, min(r, 100.0))


def split_asian_line(line: float) -> list[float]:
    """Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)."""
    if abs(line * 4 % 2) != 0:
        return [line - 0.25, line + 0.25]
    return [line]


def _dc_tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    if x == 0 and y == 0:
        return 1.0 - (lam * mu * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lam * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def _default_dc_rho(h_lam: float, a_lam: float) -> float:
    """Heurística original — se mantiene como fallback."""
    total = h_lam + a_lam
    base = -0.13
    if total < 2.0:
        return max(-0.18, base - 0.03)
    if total > 3.0:
        return min(-0.08, base + 0.03)
    return base


def _dc_log_likelihood(rho: float, matches: list[tuple[int, int, float, float]]) -> float:
    """
    matches: lista de (goles_local, goles_visitante, lambda_local, lambda_visitante)
    de partidos históricos ya jugados de una liga.
    """
    ll = 0.0
    for hg, ag, lam, mu in matches:
        p = _poisson_pmf(lam, hg) * _poisson_pmf(mu, ag) * _dc_tau(hg, ag, lam, mu, rho)
        p = max(p, 1e-10)
        ll += math.log(p)
    return ll


def fit_dixon_coles_rho(
    matches: list[tuple[int, int, float, float]],
    min_matches: int = 100,
    rho_bounds: tuple[float, float] = (-0.30, 0.05),
    grid_steps: int = 71,
) -> float:
    """
    Ajusta rho por máxima verosimilitud (búsqueda en grilla, robusta y sin
    dependencias externas de optimización) sobre partidos históricos reales.

    Si no hay suficientes partidos (< min_matches), usa el promedio de
    lambdas del set para caer de vuelta en la heurística original — así
    nunca se comporta peor que antes.
    """
    if len(matches) < min_matches:
        if matches:
            avg_lam = sum(m[2] for m in matches) / len(matches)
            avg_mu = sum(m[3] for m in matches) / len(matches)
            return _default_dc_rho(avg_lam, avg_mu)
        return -0.13

    # Vectorizado: matriz (grid x partidos) en vez de grid x partidos bucles Python.
    lo, hi = rho_bounds
    arr = np.asarray(matches, dtype=np.float64)
    hg, ag = arr[:, 0], arr[:, 1]
    lam = np.maximum(arr[:, 2], 1e-300)
    mu = np.maximum(arr[:, 3], 1e-300)
    base = np.exp(
        hg * np.log(lam) - lam - gammaln(hg + 1.0) + ag * np.log(mu) - mu - gammaln(ag + 1.0)
    )
    rhos = lo + (hi - lo) * np.arange(grid_steps) / (grid_steps - 1)
    r = rhos[:, None]
    tau = np.ones((grid_steps, arr.shape[0]))
    z00 = (hg == 0) & (ag == 0)
    z01 = (hg == 0) & (ag == 1)
    z10 = (hg == 1) & (ag == 0)
    z11 = (hg == 1) & (ag == 1)
    tau[:, z00] = 1.0 - (lam * mu)[z00] * r
    tau[:, z01] = 1.0 + lam[z01] * r
    tau[:, z10] = 1.0 + mu[z10] * r
    tau[:, z11] = 1.0 - r
    ll = np.log(np.maximum(base * tau, 1e-10)).sum(axis=1)
    return round(float(rhos[int(np.argmax(ll))]), 4)


def _dc_score_matrix(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
) -> tuple[list[list[float]], float]:
    rho_used = _default_dc_rho(h_lam, a_lam) if rho is None else rho

    min_lam = min(h_lam, a_lam)
    if min_lam > 0:
        rho_used = max(rho_used, -1.0 / min_lam)
    else:
        rho_used = 0.0

    mat_np = build_dixon_coles_matrix(h_lam, a_lam, rho_used, max_goals=max_goals)
    matrix = mat_np.tolist()
    return matrix, rho_used


def _sum_score_matrix_1x2_and_markets(matrix: list[list[float]]) -> dict[str, float]:
    # Bucle en el mismo orden que antes: la suma en este orden mantiene bit a bit los resultados.
    h_win = 0.0
    draw = 0.0
    a_win = 0.0
    over_25 = 0.0
    under_25 = 0.0
    btts_yes = 0.0

    max_goals = len(matrix) - 1

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = matrix[i][j]

            if i > j:
                h_win += p
            elif i == j:
                draw += p
            else:
                a_win += p

            if i + j >= 3:
                over_25 += p
            else:
                under_25 += p

            if i >= 1 and j >= 1:
                btts_yes += p

    btts_no = max(0.0, 1.0 - btts_yes)

    return {
        "home_win_pct": h_win * 100.0,
        "draw_pct": draw * 100.0,
        "away_win_pct": a_win * 100.0,
        "over_25_pct": over_25 * 100.0,
        "under_25_pct": under_25 * 100.0,
        "btts_yes_pct": btts_yes * 100.0,
        "btts_no_pct": btts_no * 100.0,
    }


def _top_exact_scores(
    matrix: list[list[float]],
    top_n: int = 5,
) -> list[dict[str, float | str]]:
    picks: list[dict[str, float | str]] = []

    for i, row in enumerate(matrix):
        for j, p in enumerate(row):
            picks.append({"score": f"{i}-{j}", "probability_pct": round(p * 100.0, 2)})

    picks.sort(key=lambda x: x["probability_pct"], reverse=True)
    return picks[:top_n]


def _dc_match_probs(
    h_lam: float,
    a_lam: float,
    max_goals: int = 10,
    rho: float | None = None,
) -> dict[str, Any]:
    matrix, rho_used = _dc_score_matrix(
        h_lam=h_lam,
        a_lam=a_lam,
        max_goals=max_goals,
        rho=rho,
    )

    markets = _sum_score_matrix_1x2_and_markets(matrix)
    top_scores = _top_exact_scores(matrix, top_n=5)

    return {
        **markets,
        "rho_used": round(rho_used, 4),
        "home_lambda": round(h_lam, 4),
        "away_lambda": round(a_lam, 4),
        "top_exact_scores": top_scores,
        "score_matrix": matrix,
    }


def _combine_nb_params(mu1: float, r1: float, mu2: float, r2: float) -> tuple[float, float]:
    """Combina dos distribuciones Binomial Negativa independientes.

    Para X1 ~ NB(mu1, r1) y X2 ~ NB(mu2, r2) independientes:
      mu_total  = mu1 + mu2
      Var_total = Var1 + Var2  donde Var_i = mu_i + mu_i²/r_i
      r_total   = mu_total² / (Var_total - mu_total)

    Si la varianza combinada no excede la media (i.e. Var ≤ mu), se usa r → ∞
    (equivalente Poisson) como fallback.
    """
    var1 = mu1 + mu1**2 / r1 if r1 > 0 else mu1
    var2 = mu2 + mu2**2 / r2 if r2 > 0 else mu2
    mu_total = mu1 + mu2
    var_total = var1 + var2
    if var_total <= mu_total or mu_total <= 0:
        return mu_total, 50.0  # r grande ≈ Poisson como fallback seguro
    r_total = mu_total**2 / (var_total - mu_total)
    return mu_total, max(r_total, 0.5)


def _matrix_over_under(matrix: list[list[float]], line: float) -> tuple[float, float, float]:
    """
    Issue #19: Deriva Over, Push y Under de goles directamente de la matriz Dixon-Coles
    en lugar de un Poisson independiente no correlacionado.
    Soporta líneas estándar y líneas asiáticas divididas (ej. 2.25 -> 2.0 y 2.5).
    """

    def _single_line(l: float):
        p_u, p_p, p_o = 0.0, 0.0, 0.0
        max_i = len(matrix)
        for i in range(max_i):
            max_j = len(matrix[i])
            for j in range(max_j):
                tot = i + j
                p = matrix[i][j]
                if tot < l:
                    p_u += p
                elif tot > l:
                    p_o += p
                else:
                    p_p += p
        return p_o, p_p, p_u

    lines = split_asian_line(line)
    results = [_single_line(l) for l in lines]
    avg_over = sum(r[0] for r in results) / len(results)
    avg_push = sum(r[1] for r in results) / len(results)
    avg_under = sum(r[2] for r in results) / len(results)

    return avg_over * 100.0, avg_push * 100.0, avg_under * 100.0


def _poisson_over_under(lam: float, line: float, max_k: int = 40) -> tuple[float, float, float]:
    pmf = [(lam**k * math.exp(-lam)) / math.factorial(k) for k in range(max_k + 1)]

    def _get_single_line_probs(l: float):
        p_u, p_p, p_o = 0.0, 0.0, 0.0
        for k, p in enumerate(pmf):
            if k < l:
                p_u += p
            elif k > l:
                p_o += p
            else:
                p_p += p
        return p_o, p_p, p_u

    lines = split_asian_line(line)
    results = [_get_single_line_probs(l) for l in lines]

    avg_over = sum(r[0] for r in results) / len(results)
    avg_push = sum(r[1] for r in results) / len(results)
    avg_under = sum(r[2] for r in results) / len(results)

    return avg_over * 100.0, avg_push * 100.0, avg_under * 100.0


def _neg_binomial_over_under(
    mu: float, line: float, r: float, max_k: int = 60
) -> tuple[float, float, float]:
    pmf = [_neg_bin_pmf(mu, r, k) for k in range(max_k + 1)]

    def _get_single_line_probs(l: float):
        p_u, p_p, p_o = 0.0, 0.0, 0.0
        for k, p in enumerate(pmf):
            if k < l:
                p_u += p
            elif k > l:
                p_o += p
            else:
                p_p += p
        return p_o, p_p, p_u

    lines = split_asian_line(line)
    results = [_get_single_line_probs(l) for l in lines]

    avg_over = sum(r[0] for r in results) / len(results)
    avg_push = sum(r[1] for r in results) / len(results)
    avg_under = sum(r[2] for r in results) / len(results)

    return avg_over * 100.0, avg_push * 100.0, avg_under * 100.0


def fit_market_lambdas(
    p_home: float,
    p_draw: float,
    p_away: float,
    p_over25: float | None = None,
    rho: float = -0.10,
) -> tuple[float, float] | None:
    """Lambdas (local, visitante) cuya matriz Dixon-Coles reproduce las probabilidades
    sin margen del mercado (1X2 [+ Over 2.5]). Mínimos cuadrados sobre log-lambdas.
    Devuelve None si no converge o las entradas son inválidas."""
    from scipy.optimize import minimize

    if min(p_home, p_draw, p_away) <= 0 or abs(p_home + p_draw + p_away - 1.0) > 0.02:
        return None

    def loss(x: np.ndarray) -> float:
        m, _ = _dc_score_matrix(math.exp(x[0]), math.exp(x[1]), rho=rho)
        mk = _sum_score_matrix_1x2_and_markets(m)
        e = (
            (mk["home_win_pct"] / 100 - p_home) ** 2
            + (mk["draw_pct"] / 100 - p_draw) ** 2
            + (mk["away_win_pct"] / 100 - p_away) ** 2
        )
        if p_over25 is not None:
            e += (mk["over_25_pct"] / 100 - p_over25) ** 2
        return e

    res = minimize(loss, x0=np.log([1.4, 1.1]), method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-9})
    if not res.success or res.fun > 1e-3:
        return None
    lh, la = float(np.exp(res.x[0])), float(np.exp(res.x[1]))
    return (lh, la) if 0.1 <= lh <= 5.0 and 0.1 <= la <= 5.0 else None
