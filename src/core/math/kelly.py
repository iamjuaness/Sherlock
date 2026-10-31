"""
Kelly criterion staking calculation module.
"""
from __future__ import annotations

from typing import Tuple


def calculate_fractional_kelly(
    calibrated_prob: float,
    odds: float,
    fraction_divisor: float = 8.0,
    max_stake_cap: float = 0.03,
) -> Tuple[float, float]:
    """
    Computes fractional Kelly stake and edge percentage.
    b = odds - 1, q = 1 - p
    If (p * odds - 1) <= 0: stake = 0.0
    If positive edge:
        f* = (p * b - q) / b
        stake = min(max(0.0, f* / fraction_divisor), max_stake_cap)
    Returns:
        (stake_fraction, edge_pct)
        where edge_pct is in percentage (e.g. 5.2 for 5.2%) or decimal (p * odds - 1) * 100.
    """
    p = float(calibrated_prob)
    d = float(odds)

    if d <= 1.0 or p <= 0.0 or fraction_divisor <= 0:
        return 0.0, 0.0

    b = d - 1.0
    q = 1.0 - p
    edge = p * d - 1.0
    edge_pct = edge * 100.0

    if edge <= 0.0:
        return 0.0, edge_pct

    f_star = (p * b - q) / b
    fractional = f_star / fraction_divisor
    stake = min(max(0.0, fractional), max_stake_cap)

    return float(stake), float(edge_pct)

