"""
Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa
DETERMINISTA por convolución de PMF.

Sustituye el uso de `np.random.negative_binomial(...)` sin semilla, que hacía
que dos recálculos idénticos produjeran probabilidades y picks distintos.

Propiedades garantizadas:
  - Mismo input -> mismo output, bit a bit (no hay aleatoriedad).
  - La PMF suma 1 dentro de tolerancia y la masa de cola se controla y reporta.
  - Las líneas de cuarto (x.25 / x.75) se resuelven vía el motor único de
    settlement, produciendo half-win / half-loss en vez de pérdida completa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from src.domain.settlement import (
    Outcome,
    ReturnDistribution,
    Side,
    distribution_for_total_line,
    outcome_probabilities_for_total,
)

# Cola máxima admitida antes de renormalizar (invariante de test del audit).
DEFAULT_TAIL_TOL = 1e-9
DEFAULT_MAX_K = 60


def nbinom_pmf(k: int, mu: float, r: float) -> float:
    """
    P(X = k) para una Binomial Negativa con media `mu` y dispersión `r`.

    Parametrización por media: p = r / (r + mu).
    Calculada en espacio logarítmico para evitar overflow con r grande.
    """
    if k < 0:
        return 0.0
    if mu <= 0 or r <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + mu)
    try:
        log_pmf = (
            math.lgamma(k + r)
            - math.lgamma(r)
            - math.lgamma(k + 1.0)
            + r * math.log(p)
            + k * math.log1p(-p)
        )
    except (ValueError, OverflowError):
        return 0.0
    if log_pmf < -745.0:                     # underflow de exp()
        return 0.0
    return math.exp(log_pmf)


@dataclass(frozen=True)
class CountPMF:
    """PMF de un conteo entero, con la masa de cola descartada registrada."""

    probs: tuple[float, ...]
    tail_mass: float

    @property
    def mean(self) -> float:
        return sum(k * p for k, p in enumerate(self.probs))

    def total(self) -> float:
        return sum(self.probs)

    def validate(self, tol: float = 1e-6) -> None:
        if abs(self.total() - 1.0) > tol:
            raise ValueError(f"La PMF suma {self.total()!r}, no 1.")


def nbinom_pmf_vector(
    mu: float,
    r: float,
    max_k: int = DEFAULT_MAX_K,
    tail_tol: float = DEFAULT_TAIL_TOL,
) -> CountPMF:
    """
    Vector PMF truncado y renormalizado, con la cola controlada.

    Crece hasta acumular 1 - `tail_tol` o alcanzar `max_k`. La masa restante se
    reporta en `tail_mass` y la PMF se renormaliza para sumar exactamente 1.
    """
    probs: list[float] = []
    acc = 0.0
    for k in range(max_k + 1):
        pk = nbinom_pmf(k, mu, r)
        probs.append(pk)
        acc += pk
        if acc >= 1.0 - tail_tol and k >= max(2, int(mu)):
            break

    tail = max(0.0, 1.0 - acc)
    if acc > 0:
        probs = [p / acc for p in probs]      # renormaliza la cola truncada
    return CountPMF(tuple(probs), tail)


def convolve(a: CountPMF, b: CountPMF) -> CountPMF:
    """
    PMF de la suma de dos conteos independientes.

    Convolución discreta exacta: O(len(a)·len(b)) y totalmente determinista.
    """
    out = [0.0] * (len(a.probs) + len(b.probs) - 1)
    for i, pa in enumerate(a.probs):
        if pa == 0.0:
            continue
        for j, pb in enumerate(b.probs):
            if pb == 0.0:
                continue
            out[i + j] += pa * pb
    total = sum(out)
    if total > 0:
        out = [p / total for p in out]
    return CountPMF(tuple(out), a.tail_mass + b.tail_mass)


@lru_cache(maxsize=4096)
def total_count_pmf(
    h_mu: float,
    h_r: float,
    a_mu: float,
    a_r: float,
    max_k: int = DEFAULT_MAX_K,
) -> CountPMF:
    """
    PMF del total del partido (local + visitante), determinista y cacheada.

    La caché es segura porque la función es pura: mismos argumentos, mismo
    resultado siempre.
    """
    home = nbinom_pmf_vector(h_mu, h_r, max_k=max_k)
    away = nbinom_pmf_vector(a_mu, a_r, max_k=max_k)
    return convolve(home, away)


# ═══════════════════════════════════════════════════════════════════════
# API DE MERCADO
# ═══════════════════════════════════════════════════════════════════════

def under_over_probabilities(
    line: float,
    h_mu: float,
    h_r: float,
    a_mu: float,
    a_r: float,
) -> tuple[float, float, float]:
    """
    Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`.

    Devuelve `(p_under, p_over, p_push)` en PORCENTAJE (0-100) para mantener
    la firma que ya consumen los llamadores de `compare.py`.

    Para líneas de cuarto, la masa de half-win/half-loss se reparte de forma
    consistente con el settlement: media unidad a cada pierna. Así
    `p_over + p_under + p_push` sigue sumando 100 y el EV posterior es correcto.

    NOTA: para EV y Kelly exactos en líneas de cuarto, prefiere
    `return_distribution()`, que conserva half_win / half_loss sin colapsar.
    """
    pmf = total_count_pmf(h_mu, h_r, a_mu, a_r)

    over = outcome_probabilities_for_total(line, pmf.probs, Side.OVER)
    under = outcome_probabilities_for_total(line, pmf.probs, Side.UNDER)

    def _collapse(acc: dict[Outcome, float]) -> tuple[float, float]:
        """Colapsa a (acierto, push): un half_win = media unidad de cada uno."""
        win = acc[Outcome.WIN] + 0.5 * acc[Outcome.HALF_WIN]
        push = (
            acc[Outcome.PUSH]
            + 0.5 * acc[Outcome.HALF_WIN]
            + 0.5 * acc[Outcome.HALF_LOSS]
        )
        return win, push

    p_over, over_push = _collapse(over)
    p_under, under_push = _collapse(under)

    # El push del mercado es común a ambos lados.
    p_push = (over_push + under_push) / 2.0

    norm = p_under + p_over + p_push
    if norm > 0:
        p_under, p_over, p_push = p_under / norm, p_over / norm, p_push / norm

    return p_under * 100.0, p_over * 100.0, p_push * 100.0


def return_distribution(
    odds: float,
    line: float,
    side: Side | str,
    h_mu: float,
    h_r: float,
    a_mu: float,
    a_r: float,
) -> ReturnDistribution:
    """
    Distribución de retornos EXACTA para un Over/Under de conteo.

    Es la vía recomendada para EV y Kelly: conserva half_win y half_loss en
    lugar de colapsarlos en win/push.
    """
    pmf = total_count_pmf(h_mu, h_r, a_mu, a_r)
    return distribution_for_total_line(odds, line, pmf.probs, side)


def dispersion_r(mu: float, variance: float) -> float:
    """
    Estima el parámetro de dispersión r a partir de media y varianza.

    r -> grande cuando la varianza tiende a la media (Poisson).
    """
    if mu <= 0:
        return 100.0
    if variance <= mu * 1.01:
        return 100.0
    r = (mu**2) / (variance - mu)
    return max(0.1, min(r, 100.0))
