"""
Dixon-Coles bivariate Poisson model with low-score correlation adjustment
and exponential time decay weighting.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson


def tau(x: int, y: int, lambda_val: float, mu_val: float, rho: float) -> float:
    """
    Dixon-Coles adjustment factor tau(x, y, lambda, mu, rho) for low scores.
    tau(0, 0) = 1 - lambda * mu * rho
    tau(0, 1) = 1 + lambda * rho
    tau(1, 0) = 1 + mu * rho
    tau(1, 1) = 1 - rho
    tau(x, y) = 1.0 otherwise.
    """
    if x == 0 and y == 0:
        return 1.0 - lambda_val * mu_val * rho
    elif x == 0 and y == 1:
        return 1.0 + lambda_val * rho
    elif x == 1 and y == 0:
        return 1.0 + mu_val * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def time_decay_weight(days_ago: float, xi: float = 0.0055) -> float:
    """
    Exponential time decay weighting: phi(t) = exp(-xi * t)
    where t is days ago and xi is the decay rate.
    """
    return float(np.exp(-xi * days_ago))


def build_dixon_coles_matrix(
    lambda_h: float,
    mu_a: float,
    rho: float,
    max_goals: int = 10,
    epsilon: float = 1e-9,
) -> np.ndarray:
    """
    Generates a normalized bivariate score matrix (max_goals + 1) x (max_goals + 1)
    using Dixon-Coles adjusted Poisson probabilities.
    Guarantees sum_{x,y} P(X=x, Y=y) = 1.0.
    """
    lambda_h = max(lambda_h, epsilon)
    mu_a = max(mu_a, epsilon)

    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=np.float64)

    # Precompute 1D Poisson PMFs
    goals = np.arange(max_goals + 1)
    p_h = poisson.pmf(goals, lambda_h)
    p_a = poisson.pmf(goals, mu_a)

    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            adj = tau(x, y, lambda_h, mu_a, rho)
            # Ensure prob factor does not go negative due to rho bounds
            prob = max(p_h[x] * p_a[y] * adj, 0.0)
            matrix[x, y] = prob

    total = np.sum(matrix)
    if total > 0:
        matrix /= total
    else:
        matrix[0, 0] = 1.0

    return matrix


def solve_dixon_coles_mle(
    matches: Sequence[Union[Dict[str, Union[str, float, int]], Tuple]],
    teams: Optional[Sequence[str]] = None,
    xi: float = 0.0055,
) -> Dict[str, Union[Dict[str, float], float]]:
    """
    Fits Dixon-Coles attack, defence, home advantage (gamma), and rho parameters
    using weighted Maximum Likelihood Estimation with L-BFGS-B.
    
    Each match can be a dict:
        {"home_team": str, "away_team": str, "home_goals": int, "away_goals": int, "days_ago": float}
    or a tuple:
        (home_team, away_team, home_goals, away_goals, days_ago)
        
    Identifiability constraint: sum(alpha_i) = 0.
    """
    # Parse matches
    parsed_matches = []
    unique_teams = set()
    for m in matches:
        if isinstance(m, dict):
            h = str(m["home_team"])
            a = str(m["away_team"])
            hg = int(m["home_goals"])
            ag = int(m["away_goals"])
            t = float(m.get("days_ago", 0.0))
        else:
            h = str(m[0])
            a = str(m[1])
            hg = int(m[2])
            ag = int(m[3])
            t = float(m[4]) if len(m) > 4 else 0.0
        parsed_matches.append((h, a, hg, ag, t))
        unique_teams.add(h)
        unique_teams.add(a)

    if teams is not None:
        team_list = sorted(list(set(teams).union(unique_teams)))
    else:
        team_list = sorted(list(unique_teams))

    n_teams = len(team_list)
    if n_teams == 0 or len(parsed_matches) == 0:
        return {
            "attack": {},
            "defence": {},
            "home_advantage": 0.25,
            "rho": -0.05,
        }

    team_idx = {name: i for i, name in enumerate(team_list)}

    # Pre-encode matches into numeric arrays
    home_indices = np.array([team_idx[m[0]] for m in parsed_matches], dtype=np.int32)
    away_indices = np.array([team_idx[m[1]] for m in parsed_matches], dtype=np.int32)
    home_goals = np.array([m[2] for m in parsed_matches], dtype=np.int32)
    away_goals = np.array([m[3] for m in parsed_matches], dtype=np.int32)
    weights = np.array([time_decay_weight(m[4], xi=xi) for m in parsed_matches], dtype=np.float64)

    # Parameters layout in vector:
    # alpha: n_teams - 1 (the last team alpha is -sum(alpha[:-1]))
    # beta: n_teams
    # gamma: 1 (home advantage in log scale)
    # rho: 1 (dependence parameter)
    # Total: (n_teams - 1) + n_teams + 2 = 2 * n_teams + 1

    init_alpha = np.zeros(n_teams - 1, dtype=np.float64)
    init_beta = np.zeros(n_teams, dtype=np.float64)
    init_gamma = 0.25
    init_rho = -0.05

    init_params = np.concatenate([init_alpha, init_beta, [init_gamma, init_rho]])

    bounds = []
    # alpha bounds
    for _ in range(n_teams - 1):
        bounds.append((-3.0, 3.0))
    # beta bounds
    for _ in range(n_teams):
        bounds.append((-3.0, 3.0))
    # gamma bounds
    bounds.append((-1.0, 1.5))
    # rho bounds
    bounds.append((-0.3, 0.3))

    def _neg_log_likelihood(params: np.ndarray) -> float:
        alphas_part = params[: n_teams - 1]
        last_alpha = -np.sum(alphas_part)
        alphas = np.append(alphas_part, last_alpha)
        betas = params[n_teams - 1 : 2 * n_teams - 1]
        gamma = params[2 * n_teams - 1]
        rho = params[2 * n_teams]

        # lambda_i = exp(alpha_h + beta_a + gamma)
        # mu_j = exp(alpha_a + beta_h)
        log_lambda = alphas[home_indices] + betas[away_indices] + gamma
        log_mu = alphas[away_indices] + betas[home_indices]

        # Clip log lambdas to prevent overflow/underflow
        log_lambda = np.clip(log_lambda, -10.0, 10.0)
        log_mu = np.clip(log_mu, -10.0, 10.0)

        lambdas = np.exp(log_lambda)
        mus = np.exp(log_mu)

        # Poisson log pmf: k * log(lambda) - lambda - log(k!)
        # Since log(k!) is constant w.r.t parameters, we can include or omit it. Including it for exactness.
        from scipy.special import gammaln
        ll_h = home_goals * log_lambda - lambdas - gammaln(home_goals + 1)
        ll_a = away_goals * log_mu - mus - gammaln(away_goals + 1)

        # Dixon-Coles tau adjustment
        # Vectorized or loop over low scores
        n_m = len(home_goals)
        tau_vals = np.ones(n_m, dtype=np.float64)
        m00 = (home_goals == 0) & (away_goals == 0)
        m01 = (home_goals == 0) & (away_goals == 1)
        m10 = (home_goals == 1) & (away_goals == 0)
        m11 = (home_goals == 1) & (away_goals == 1)

        tau_vals[m00] = 1.0 - lambdas[m00] * mus[m00] * rho
        tau_vals[m01] = 1.0 + lambdas[m01] * rho
        tau_vals[m10] = 1.0 + mus[m10] * rho
        tau_vals[m11] = 1.0 - rho

        # Protect against non-positive tau
        tau_vals = np.maximum(tau_vals, 1e-9)

        match_ll = (ll_h + ll_a + np.log(tau_vals)) * weights
        return -float(np.sum(match_ll))

    res = minimize(_neg_log_likelihood, init_params, method="L-BFGS-B", bounds=bounds)

    best_params = res.x if res.success or res.x is not None else init_params
    alphas_part = best_params[: n_teams - 1]
    last_alpha = -np.sum(alphas_part)
    alphas = np.append(alphas_part, last_alpha)
    betas = best_params[n_teams - 1 : 2 * n_teams - 1]
    gamma = float(best_params[2 * n_teams - 1])
    rho = float(best_params[2 * n_teams])

    attack_dict = {team_list[i]: float(alphas[i]) for i in range(n_teams)}
    defence_dict = {team_list[i]: float(betas[i]) for i in range(n_teams)}

    return {
        "attack": attack_dict,
        "defence": defence_dict,
        "home_advantage": gamma,
        "rho": rho,
    }

