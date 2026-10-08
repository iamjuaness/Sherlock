"""
Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de Invariantes
y Guardrails para 1X2 / Doble Oportunidad.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from src.core.math_engine import calculate_dixon_coles_matrix


@dataclass(frozen=True)
class MatchProbabilities:
    p_home_win: float
    p_draw: float
    p_away_win: float

    p_1x: float
    p_x2: float
    p_12: float

    p_btts_yes: float
    p_btts_no: float

    over_under_lines: Dict[float, Tuple[float, float, float]]  # line -> (over, under, push)

    def validate_invariants(self, tol: float = 1e-4) -> bool:
        """Valida matemáticamente todos los invariantes requeridos."""
        # 1. 1X2 suma 1
        if abs((self.p_home_win + self.p_draw + self.p_away_win) - 1.0) > tol:
            return False

        # 2. Doble oportunidad consistente con 1X2
        if abs(self.p_1x - (self.p_home_win + self.p_draw)) > tol:
            return False
        if abs(self.p_x2 - (self.p_draw + self.p_away_win)) > tol:
            return False
        if abs(self.p_12 - (self.p_home_win + self.p_away_win)) > tol:
            return False

        # 3. BTTS suma 1
        if abs((self.p_btts_yes + self.p_btts_no) - 1.0) > tol:
            return False

        # 4. Over / Under / Push suma 1 por línea
        for line, (over, under, push) in self.over_under_lines.items():
            if abs((over + under + push) - 1.0) > tol:
                return False

        return True


def derive_joint_match_probabilities(
    lambda_home: float,
    mu_away: float,
    max_goals: int = 10,
    rho: float = -0.05,
    lines: Tuple[float, ...] = (0.5, 1.5, 2.5, 3.5, 4.5),
) -> MatchProbabilities:
    """Deriva explícitamente todas las probabilidades de mercado desde la matriz conjunta de marcadores Dixon-Coles."""
    matrix = calculate_dixon_coles_matrix(lambda_home, mu_away, max_goals=max_goals, rho=rho)

    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0
    p_btts_yes = 0.0
    p_btts_no = 0.0

    for h in range(len(matrix)):
        for a in range(len(matrix[0])):
            prob = matrix[h][a]
            if h > a:
                p_home += prob
            elif h < a:
                p_away += prob
            else:
                p_draw += prob

            if h > 0 and a > 0:
                p_btts_yes += prob
            else:
                p_btts_no += prob

    p_1x = p_home + p_draw
    p_x2 = p_draw + p_away
    p_12 = p_home + p_away

    ou_map: Dict[float, Tuple[float, float, float]] = {}
    for line in lines:
        p_over = 0.0
        p_under = 0.0
        p_push = 0.0
        for h in range(len(matrix)):
            for a in range(len(matrix[0])):
                tot = h + a
                prob = matrix[h][a]
                if tot > line:
                    p_over += prob
                elif tot < line:
                    p_under += prob
                else:
                    p_push += prob
        ou_map[line] = (p_over, p_under, p_push)

    res = MatchProbabilities(
        p_home_win=p_home,
        p_draw=p_draw,
        p_away_win=p_away,
        p_1x=p_1x,
        p_x2=p_x2,
        p_12=p_12,
        p_btts_yes=p_btts_yes,
        p_btts_no=p_btts_no,
        over_under_lines=ou_map,
    )

    if not res.validate_invariants():
        raise ValueError("Violación de invariantes probabilísticos en el modelo conjunto de marcador")

    return res


def guardrail_away_win_recommendation(
    p_away: float,
    p_draw: float,
    p_x2: float,
    away_odds: float,
    segment_reliability: float = 1.0,
    segment_blocked_or_reduced: bool = False,
    has_clv_confirmation: bool = True,
) -> Tuple[bool, str]:
    """Guardrail para evitar que señales de doble oportunidad X2 se transformen erróneamente en victoria visitante (Away Win 1X2)."""
    if away_odds <= 1.0:
        return False, "Cuota visitante inválida"

    break_even = 1.0 / away_odds
    edge = p_away - break_even

    # 1. Proporción de empate dominante en X2
    if p_x2 > 0 and (p_draw / p_x2) > 0.45:
        return False, "Guardrail 1X2 Visitante: El empate domina la probabilidad de X2"

    # 2. Edge insuficiente respecto al break-even
    if edge < 0.02:
        return False, f"Guardrail 1X2 Visitante: Edge insuficiente vs break-even ({edge*100:.1f}%)"

    # 3. Fiabilidad reducida o bloqueada
    if segment_reliability < 0.50 or segment_blocked_or_reduced:
        return False, "Guardrail 1X2 Visitante: Fiabilidad de segmento reducida o bloqueada"

    # 4. Sin confirmación de mercado/CLV
    if not has_clv_confirmation:
        return False, "Guardrail 1X2 Visitante: Sin confirmación de movimiento de mercado (CLV)"

    return True, "Aprobado"
