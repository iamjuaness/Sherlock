"""
Empirical Bayes and conjugate Gamma-Poisson inference for rate parameters.
"""
from __future__ import annotations

from typing import Sequence, Tuple
import numpy as np


def fit_gamma_prior_from_league(
    historical_series: Sequence[float],
    min_samples: int = 5,
    epsilon: float = 1e-9,
) -> Tuple[float, float]:
    """
    Fits Gamma prior (alpha, beta) using Empirical Bayes (method of moments)
    from historical team series of counts or rates per game.
    
    If var > mean:
        beta = mean / (var - mean)
        alpha = mean * beta
    If var <= mean (equidispersion or underdispersion):
        defensive non-informative / weakly-informative prior:
        beta = 2.0
        alpha = 2.0 * mean
    """
    arr = np.asarray(historical_series, dtype=np.float64)
    arr = arr[~np.isnan(arr)]

    if len(arr) < min_samples:
        mean_val = float(np.mean(arr)) if len(arr) > 0 else 1.35
        mean_val = max(mean_val, epsilon)
        return (2.0 * mean_val, 2.0)

    mean_val = float(np.mean(arr))
    var_val = float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0

    mean_val = max(mean_val, epsilon)

    if var_val > mean_val:
        beta = mean_val / (var_val - mean_val)
        alpha = mean_val * beta
    else:
        beta = 2.0
        alpha = 2.0 * mean_val

    return (float(alpha), float(beta))


def update_gamma_poisson(
    alpha_prior: float,
    beta_prior: float,
    observed_events: float,
    matches_played: float,
    epsilon: float = 1e-9,
) -> float:
    """
    Computes posterior expected rate lambda_post under conjugate Gamma-Poisson update:
    lambda_post = (alpha_prior + observed_events) / (beta_prior + matches_played)
    """
    denom = max(beta_prior + matches_played, epsilon)
    num = max(alpha_prior + observed_events, 0.0)
    return float(num / denom)

