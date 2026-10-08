"""
Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos duros injustificados.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class H2HShrinkageResult:
    h2h_raw_rate: float
    h2h_shrunk_rate: float
    sample_size: int
    prior_probability: float
    reliability_penalty: float  # [0.0, 1.0] multiplicador


def shrunk_h2h_rate(
    hits: float,
    n: float,
    prior_probability: float = 0.50,
    prior_strength: float = 8.0,
) -> float:
    """Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)."""
    if n <= 0:
        return prior_probability
    return (hits + prior_strength * prior_probability) / (n + prior_strength)


def evaluate_h2h_signal(
    hits: float,
    n: int,
    prior_probability: float = 0.50,
    prior_strength: float = 8.0,
) -> H2HShrinkageResult:
    """
    Evalúa la señal H2H sin emitir bloqueos duros para n < 8.
    Si n >= 8 y el hit rate suavizado es significativamente inferior al prior, aplica penalización suave.
    """
    raw_rate = (hits / float(n)) if n > 0 else prior_probability
    shrunk = shrunk_h2h_rate(hits, float(n), prior_probability, prior_strength)

    penalty = 1.0
    if n >= 8:
        if shrunk < prior_probability * 0.6:
            # Penalización suave de hasta 20% en reliability score
            penalty = max(0.80, 1.0 - (prior_probability - shrunk))

    return H2HShrinkageResult(
        h2h_raw_rate=raw_rate,
        h2h_shrunk_rate=shrunk,
        sample_size=n,
        prior_probability=prior_probability,
        reliability_penalty=penalty,
    )
