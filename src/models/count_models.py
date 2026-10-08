"""
Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a puerta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class DirectCountPrediction:
    expected_total: float
    dispersion_alpha: float
    data_completeness: float
    model_version: str = "v1"
    details: Dict[str, float] = field(default_factory=dict)


def predict_direct_total(
    home_recent: List[float],
    away_recent: List[float],
    league_base_mean: float,
    shrinkage_factor: float = 0.3,
    half_life: float = 10.0,
) -> DirectCountPrediction:
    """Calcula la media total esperada del mercado con shrinkage hacia la media de liga."""
    if not home_recent and not away_recent:
        return DirectCountPrediction(
            expected_total=league_base_mean,
            dispersion_alpha=0.05,
            data_completeness=0.0,
            model_version="v1",
        )

    h_mean = sum(home_recent) / len(home_recent) if home_recent else (league_base_mean * 0.5)
    a_mean = sum(away_recent) / len(away_recent) if away_recent else (league_base_mean * 0.5)

    raw_total = h_mean + a_mean
    shrunk_total = (1.0 - shrinkage_factor) * raw_total + shrinkage_factor * league_base_mean

    n_samples = len(home_recent) + len(away_recent)
    data_comp = min(1.0, n_samples / 20.0)

    return DirectCountPrediction(
        expected_total=shrunk_total,
        dispersion_alpha=0.05,
        data_completeness=data_comp,
        model_version="v1",
        details={"raw_total": raw_total, "league_base_mean": league_base_mean},
    )


def predict_cards_total(
    home_fouls: Optional[float],
    away_fouls: Optional[float],
    referee_cards_mean: Optional[float],
    league_cards_mean: float = 4.5,
    expected_goal_diff: float = 0.0,
) -> DirectCountPrediction:
    """Modelo específico de tarjetas integrando árbitro y disciplina."""
    if referee_cards_mean is None:
        # Si falta el árbitro, se reduce la completitud de datos pero no se imputa silenciosamente
        base = league_cards_mean
        completeness = 0.6
    else:
        base = 0.6 * referee_cards_mean + 0.4 * league_cards_mean
        completeness = 0.9

    foul_adj = 0.0
    if home_fouls is not None and away_fouls is not None:
        tot_fouls = home_fouls + away_fouls
        foul_adj = (tot_fouls - 24.0) * 0.08
        completeness = min(1.0, completeness + 0.1)

    # Partidos parejos (goal diff cercano a 0) generan más tensión y tarjetas
    tension_adj = max(0.0, 0.5 - abs(expected_goal_diff) * 0.2)

    total = max(1.0, base + foul_adj + tension_adj)

    return DirectCountPrediction(
        expected_total=total,
        dispersion_alpha=0.08,
        data_completeness=completeness,
        model_version="v1_cards",
        details={"referee_mean": referee_cards_mean or league_cards_mean, "foul_adj": foul_adj},
    )


def predict_shots_on_target_total(
    expected_total_shots: float,
    sot_per_shot_rate: float = 0.33,
    league_sot_mean: float = 8.5,
) -> DirectCountPrediction:
    """Modelo específico para remates a puerta (shots_target) enfocado en la banda core 7.5-8.5."""
    raw_sot = expected_total_shots * sot_per_shot_rate
    shrunk_sot = 0.7 * raw_sot + 0.3 * league_sot_mean

    return DirectCountPrediction(
        expected_total=shrunk_sot,
        dispersion_alpha=0.06,
        data_completeness=0.85,
        model_version="v1_shots_target",
        details={"raw_sot": raw_sot, "league_sot_mean": league_sot_mean},
    )
