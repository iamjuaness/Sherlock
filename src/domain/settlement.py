"""
Motor único de liquidación de Sherlock.

Este módulo es la ÚNICA fuente de verdad sobre:
  1. Qué resultado (outcome) produce una apuesta dado el resultado real.
  2. Cuánto retorna ese outcome por unidad apostada.
  3. Cómo se calcula EV y Kelly a partir de la distribución de retornos.

Reglas de diseño (ver docs/AUDITORIA_INTEGRAL_Y_PLAN_DE_MEJORA.md):

  - Se usa el MISMO código para vivo, backtest, ROI y reportes.
  - Falla CERRADO: si falta la estadística necesaria, el resultado es
    UNSETTLED. Nunca se inventa un cero.
  - Las líneas de cuarto (x.25 / x.75) se modelan como DOS piernas de media
    unidad cada una, produciendo half_win / half_loss reales.
  - EV y Kelly se calculan sobre la distribución completa de retornos, no
    sobre una Bernoulli ficticia que trata el push como pérdida.

Sin dependencias externas (solo stdlib) para que sea trivialmente testeable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence

# Tolerancia para comparar líneas en coma flotante (2.25 puede llegar como 2.2499999)
_EPS = 1e-9


class Outcome(str, Enum):
    """Resultados posibles de una apuesta liquidada."""

    WIN = "win"
    HALF_WIN = "half_win"
    PUSH = "push"
    HALF_LOSS = "half_loss"
    LOSS = "loss"
    UNSETTLED = "unsettled"

    @property
    def is_settled(self) -> bool:
        return self is not Outcome.UNSETTLED


class Side(str, Enum):
    OVER = "over"
    UNDER = "under"


# ═══════════════════════════════════════════════════════════════════════
# RETORNOS
# ═══════════════════════════════════════════════════════════════════════

def outcome_return(outcome: Outcome, odds: float) -> float:
    """
    Retorno NETO (profit) por 1 unidad apostada, en cuota decimal.

    WIN       -> +(odds - 1)
    HALF_WIN  -> +(odds - 1) / 2   (media apuesta gana, media empata)
    PUSH      ->  0.0              (devolución íntegra: el push NO es pérdida)
    HALF_LOSS -> -0.5              (media apuesta pierde, media empata)
    LOSS      -> -1.0

    Lanza ValueError si el outcome es UNSETTLED: un pick sin liquidar no
    tiene retorno definido y no debe entrar en ROI ni en accuracy.
    """
    if outcome is Outcome.UNSETTLED:
        raise ValueError(
            "UNSETTLED no tiene retorno definido; excluir del ROI en lugar de "
            "convertirlo en 0."
        )
    if odds is None or odds <= 1.0:
        raise ValueError(f"Cuota decimal inválida: {odds!r} (debe ser > 1.0)")

    b = odds - 1.0
    if outcome is Outcome.WIN:
        return b
    if outcome is Outcome.HALF_WIN:
        return b / 2.0
    if outcome is Outcome.PUSH:
        return 0.0
    if outcome is Outcome.HALF_LOSS:
        return -0.5
    if outcome is Outcome.LOSS:
        return -1.0
    raise ValueError(f"Outcome no soportado: {outcome!r}")


def outcome_hit_value(outcome: Outcome) -> float | None:
    """
    Valor de acierto para estadísticas de hit rate, en [0, 1].

    Un half_win NO es un acierto completo (el audit señala que contarlo como
    tal contamina el histórico). Un push se excluye del hit rate devolviendo
    None, igual que UNSETTLED.
    """
    if outcome is Outcome.WIN:
        return 1.0
    if outcome is Outcome.HALF_WIN:
        return 0.5
    if outcome is Outcome.HALF_LOSS:
        return 0.0
    if outcome is Outcome.LOSS:
        return 0.0
    # PUSH y UNSETTLED no cuentan en el denominador del hit rate.
    return None


# ═══════════════════════════════════════════════════════════════════════
# DESCOMPOSICIÓN DE LÍNEAS
# ═══════════════════════════════════════════════════════════════════════

def line_legs(line: float) -> tuple[float, ...]:
    """
    Descompone una línea en sus piernas efectivas.

    x.0  -> (x.0,)            una pierna, admite push
    x.5  -> (x.5,)            una pierna, no admite push
    x.25 -> (x.0, x.5)        dos piernas de media unidad
    x.75 -> (x.5, x+1.0)      dos piernas de media unidad

    >>> line_legs(2.0)
    (2.0,)
    >>> line_legs(2.25)
    (2.0, 2.5)
    >>> line_legs(2.75)
    (2.5, 3.0)
    """
    if line is None or not math.isfinite(line):
        raise ValueError(f"Línea inválida: {line!r}")

    quarters = round(line * 4.0)
    if abs(line * 4.0 - quarters) > 1e-6:
        raise ValueError(
            f"Línea {line!r} no es múltiplo de 0.25; convención de liquidación "
            "desconocida (fallar cerrado)."
        )

    rem = quarters % 4
    if rem == 0 or rem == 2:          # x.0 o x.5 -> una sola pierna
        return (quarters / 4.0,)
    if rem == 1:                      # x.25 -> x.0 y x.5
        return ((quarters - 1) / 4.0, (quarters + 1) / 4.0)
    return ((quarters - 1) / 4.0, (quarters + 1) / 4.0)  # x.75 -> x.5 y x+1.0


def _combine_legs(legs: Sequence[Outcome]) -> Outcome:
    """
    Combina los resultados de las piernas (cada una con media unidad).

    Solo se usan piernas simples, por lo que cada una es WIN, PUSH o LOSS.
    """
    if not legs:
        return Outcome.UNSETTLED
    if any(o is Outcome.UNSETTLED for o in legs):
        return Outcome.UNSETTLED
    if len(legs) == 1:
        return legs[0]

    wins = sum(1 for o in legs if o is Outcome.WIN)
    losses = sum(1 for o in legs if o is Outcome.LOSS)
    pushes = sum(1 for o in legs if o is Outcome.PUSH)

    if wins == 2:
        return Outcome.WIN
    if losses == 2:
        return Outcome.LOSS
    if wins == 1 and pushes == 1:
        return Outcome.HALF_WIN
    if losses == 1 and pushes == 1:
        return Outcome.HALF_LOSS
    if pushes == 2:
        return Outcome.PUSH
    # win + loss: imposible en líneas de cuarto reales (las piernas distan 0.5
    # y el total es entero), pero se neutraliza en vez de inventar retorno.
    return Outcome.PUSH


def _settle_simple_total(line: float, total: float, side: Side) -> Outcome:
    """Liquida una pierna simple (x.0 o x.5) de un mercado de totales."""
    diff = total - line
    if abs(diff) <= _EPS:
        return Outcome.PUSH          # solo alcanzable en líneas enteras
    if side is Side.OVER:
        return Outcome.WIN if diff > 0 else Outcome.LOSS
    return Outcome.WIN if diff < 0 else Outcome.LOSS


# ═══════════════════════════════════════════════════════════════════════
# LIQUIDACIÓN DE MERCADOS
# ═══════════════════════════════════════════════════════════════════════

def settle_total(line: float, total: float | None, side: Side | str) -> Outcome:
    """
    Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).

    `total` es la estadística REAL observada. Si es None, devuelve UNSETTLED:
    nunca se asume 0 por dato ausente.

    >>> settle_total(2.5, 3, "over")
    <Outcome.WIN: 'win'>
    >>> settle_total(2.0, 2, "over")
    <Outcome.PUSH: 'push'>
    >>> settle_total(2.25, 2, "over")
    <Outcome.HALF_LOSS: 'half_loss'>
    >>> settle_total(2.75, 3, "over")
    <Outcome.HALF_WIN: 'half_win'>
    """
    if total is None:
        return Outcome.UNSETTLED
    side = Side(side) if not isinstance(side, Side) else side
    try:
        legs = line_legs(line)
    except ValueError:
        return Outcome.UNSETTLED
    return _combine_legs([_settle_simple_total(lg, float(total), side) for lg in legs])


def settle_asian_handicap(line: float, margin: float | None) -> Outcome:
    """
    Liquida un hándicap asiático para el equipo apostado.

    `margin` = goles del equipo apostado - goles del rival (sin hándicap).
    `line`   = hándicap aplicado a ese equipo (p.ej. -0.75, +1.25).

    >>> settle_asian_handicap(-1.0, 1)
    <Outcome.PUSH: 'push'>
    >>> settle_asian_handicap(-0.75, 1)
    <Outcome.HALF_WIN: 'half_win'>
    >>> settle_asian_handicap(0.25, -1)
    <Outcome.HALF_LOSS: 'half_loss'>
    """
    if margin is None:
        return Outcome.UNSETTLED
    try:
        legs = line_legs(abs(line))
    except ValueError:
        return Outcome.UNSETTLED
    sign = -1.0 if line < 0 else 1.0
    legs = tuple(sign * lg for lg in legs)

    outcomes = []
    for lg in legs:
        adj = float(margin) + lg
        if abs(adj) <= _EPS:
            outcomes.append(Outcome.PUSH)
        elif adj > 0:
            outcomes.append(Outcome.WIN)
        else:
            outcomes.append(Outcome.LOSS)
    return _combine_legs(outcomes)


def settle_binary(predicted_true: bool, actual: bool | None) -> Outcome:
    """
    Liquida un mercado binario sin push (BTTS, 1X2, doble oportunidad).

    Falla cerrado si `actual` es None.
    """
    if actual is None:
        return Outcome.UNSETTLED
    return Outcome.WIN if bool(actual) is bool(predicted_true) else Outcome.LOSS


# ═══════════════════════════════════════════════════════════════════════
# CONVENCIÓN DE TARJETAS (explícita, el audit la exige)
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CardsConvention:
    """
    Convención explícita para contar tarjetas.

    `red_weight = 1.0`  -> una roja cuenta como 1 tarjeta.
    `red_weight = 2.0`  -> una roja cuenta como 2 (amarilla + roja).
    `second_yellow_counts_as` controla la doble amarilla.
    """

    red_weight: float = 1.0
    second_yellow_counts_as: float = 1.0
    name: str = "reds_count_as_one"

    def total(
        self,
        yellows: float | None,
        reds: float | None = 0.0,
        second_yellows: float | None = 0.0,
    ) -> float | None:
        """Total de tarjetas según la convención. None si falta la base."""
        if yellows is None:
            return None                      # falla cerrado, no asume 0
        r = 0.0 if reds is None else float(reds)
        sy = 0.0 if second_yellows is None else float(second_yellows)
        return float(yellows) + r * self.red_weight + sy * self.second_yellow_counts_as


CARDS_DEFAULT = CardsConvention()


# ═══════════════════════════════════════════════════════════════════════
# DISTRIBUCIÓN DE RETORNOS -> EV Y KELLY
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReturnDistribution:
    """
    Distribución de probabilidad sobre los outcomes de UNA apuesta.

    Las probabilidades van en [0, 1] (no en porcentaje) y deben sumar ~1.
    Es el objeto que consumen EV y Kelly: sustituye al par (prob, push_prob)
    que no podía representar half-win / half-loss.
    """

    odds: float
    p_win: float = 0.0
    p_half_win: float = 0.0
    p_push: float = 0.0
    p_half_loss: float = 0.0
    p_loss: float = 0.0

    # ── construcción ────────────────────────────────────────────────
    @classmethod
    def from_map(cls, odds: float, probs: Mapping[Outcome | str, float]) -> "ReturnDistribution":
        get = lambda k: float(probs.get(k, probs.get(Outcome(k), 0.0)) or 0.0)  # noqa: E731
        norm = {}
        for key, val in probs.items():
            k = key.value if isinstance(key, Outcome) else str(key)
            norm[k] = norm.get(k, 0.0) + float(val or 0.0)
        return cls(
            odds=odds,
            p_win=norm.get("win", 0.0),
            p_half_win=norm.get("half_win", 0.0),
            p_push=norm.get("push", 0.0),
            p_half_loss=norm.get("half_loss", 0.0),
            p_loss=norm.get("loss", 0.0),
        )

    @classmethod
    def simple(cls, odds: float, p_win: float, p_push: float = 0.0) -> "ReturnDistribution":
        """
        Mercado sin líneas de cuarto: solo win / push / loss.

        Acepta probabilidades en 0-1 o en 0-100 (se detecta por rango), igual
        que hacía el código legacy, para facilitar la migración.
        """
        if p_win > 1.0 or p_push > 1.0:
            p_win, p_push = p_win / 100.0, p_push / 100.0
        p_win = max(0.0, min(1.0, p_win))
        p_push = max(0.0, min(1.0, p_push))
        p_loss = max(0.0, 1.0 - p_win - p_push)
        return cls(odds=odds, p_win=p_win, p_push=p_push, p_loss=p_loss)

    # ── invariantes ─────────────────────────────────────────────────
    @property
    def total_probability(self) -> float:
        return self.p_win + self.p_half_win + self.p_push + self.p_half_loss + self.p_loss

    def validate(self, tol: float = 1e-6) -> None:
        """Invariante del audit: la suma de probabilidades de estados = 1."""
        for name, val in (
            ("p_win", self.p_win), ("p_half_win", self.p_half_win),
            ("p_push", self.p_push), ("p_half_loss", self.p_half_loss),
            ("p_loss", self.p_loss),
        ):
            if val < -tol or val > 1.0 + tol:
                raise ValueError(f"{name}={val!r} fuera de [0,1]")
        if abs(self.total_probability - 1.0) > tol:
            raise ValueError(
                f"Las probabilidades suman {self.total_probability!r}, no 1."
            )
        if self.odds is None or self.odds <= 1.0:
            raise ValueError(f"Cuota decimal inválida: {self.odds!r}")

    def outcomes(self) -> tuple[tuple[float, float], ...]:
        """Pares (probabilidad, retorno neto) con probabilidad > 0."""
        pairs = (
            (self.p_win, Outcome.WIN),
            (self.p_half_win, Outcome.HALF_WIN),
            (self.p_push, Outcome.PUSH),
            (self.p_half_loss, Outcome.HALF_LOSS),
            (self.p_loss, Outcome.LOSS),
        )
        return tuple(
            (p, outcome_return(o, self.odds)) for p, o in pairs if p > 0.0
        )

    # ── métricas económicas ─────────────────────────────────────────
    @property
    def expected_value(self) -> float:
        """
        EV correcto por unidad apostada:

            E[R] = Σ p_i · r_i

        Para win/push/loss esto equivale a  P(win)·(odds-1) - P(loss),
        con el push aportando retorno CERO (no pérdida escalada).
        """
        return sum(p * r for p, r in self.outcomes())

    @property
    def variance(self) -> float:
        ev = self.expected_value
        return sum(p * (r - ev) ** 2 for p, r in self.outcomes())

    @property
    def p_win_effective(self) -> float:
        """Probabilidad de acierto condicionada a que la apuesta resuelva."""
        resolved = 1.0 - self.p_push
        if resolved <= 0:
            return 0.0
        return (self.p_win + 0.5 * self.p_half_win) / resolved

    @property
    def fair_odds(self) -> float | None:
        """
        Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución.
        """
        gain = self.p_win + self.p_half_win / 2.0
        risk = self.p_loss + self.p_half_loss / 2.0
        if gain <= 0:
            return None
        return 1.0 + (risk / gain)

    def kelly_fraction(
        self,
        multiplier: float = 0.25,
        hard_cap: float = 0.25,
        tol: float = 1e-10,
    ) -> float:
        """
        Kelly sobre la distribución COMPLETA de retornos.

        Maximiza  E[log(1 + f·R)]  resolviendo  g(f) = Σ pᵢ·rᵢ/(1+f·rᵢ) = 0
        por bisección. g es estrictamente decreciente en el dominio válido,
        así que la raíz es única.

        A diferencia del Kelly Bernoulli anterior, un push NO consume
        bankroll: aporta r = 0 y por tanto no penaliza el crecimiento.
        """
        pairs = self.outcomes()
        if not pairs:
            return 0.0
        if self.expected_value <= 0:
            return 0.0                      # sin valor -> no apostar

        worst = min(r for _, r in pairs)
        if worst >= 0:
            f_hi = 1.0                      # sin riesgo de pérdida: tope lógico
        else:
            f_hi = 1.0 / abs(worst) - 1e-9  # mantener 1 + f·r > 0

        g = lambda f: sum(p * r / (1.0 + f * r) for p, r in pairs)  # noqa: E731

        if g(f_hi) > 0:
            f_full = f_hi
        else:
            lo, hi = 0.0, f_hi
            for _ in range(200):
                mid = (lo + hi) / 2.0
                if g(mid) > 0:
                    lo = mid
                else:
                    hi = mid
                if hi - lo < tol:
                    break
            f_full = (lo + hi) / 2.0

        if f_full <= 0:
            return 0.0
        return round(min(f_full * multiplier, hard_cap), 6)


# ═══════════════════════════════════════════════════════════════════════
# DISTRIBUCIÓN DE OUTCOMES A PARTIR DE UNA PMF DE TOTALES
# ═══════════════════════════════════════════════════════════════════════

def outcome_probabilities_for_total(
    line: float,
    pmf: Sequence[float] | Mapping[int, float],
    side: Side | str,
) -> dict[Outcome, float]:
    """
    Convierte una PMF del total (determinista) en probabilidades de outcome
    para una línea concreta, incluidas las de cuarto.

    Esto reemplaza el `np.mean(total_sims < line)` que trataba un Over 2.25
    con total 2 como pérdida completa en vez de half-loss.
    """
    side = Side(side) if not isinstance(side, Side) else side
    items: Iterable[tuple[int, float]]
    items = pmf.items() if isinstance(pmf, Mapping) else enumerate(pmf)

    acc: dict[Outcome, float] = {o: 0.0 for o in Outcome if o.is_settled}
    for k, prob in items:
        if not prob:
            continue
        acc[settle_total(line, k, side)] += float(prob)
    return acc


def distribution_for_total_line(
    odds: float,
    line: float,
    pmf: Sequence[float] | Mapping[int, float],
    side: Side | str,
) -> ReturnDistribution:
    """Atajo: PMF de totales -> ReturnDistribution lista para EV/Kelly."""
    probs = outcome_probabilities_for_total(line, pmf, side)
    total = sum(probs.values())
    if total > 0:                            # renormaliza cola truncada
        probs = {k: v / total for k, v in probs.items()}
    return ReturnDistribution.from_map(odds, probs)


# ═══════════════════════════════════════════════════════════════════════
# API DE CONVENIENCIA PARA LIQUIDAR PICKS PERSISTIDOS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SettlementResult:
    """Resultado de liquidar un pick, con trazabilidad de por qué."""

    outcome: Outcome
    profit_units: float | None = None      # retorno neto por unidad apostada
    hit_value: float | None = None         # 1.0 / 0.5 / 0.0 / None
    reasons: list[str] = field(default_factory=list)

    @property
    def is_settled(self) -> bool:
        return self.outcome.is_settled


def settle_pick(
    outcome: Outcome,
    odds: float | None,
    stake_units: float = 1.0,
) -> SettlementResult:
    """
    Convierte un outcome + cuota en retorno económico.

    Si el pick no puede liquidarse (dato faltante, cuota inválida) devuelve
    UNSETTLED con `profit_units=None`, de modo que el ROI lo EXCLUYA en lugar
    de sumar un cero inventado.
    """
    reasons: list[str] = []
    if outcome is Outcome.UNSETTLED:
        reasons.append("estadistica_faltante")
        return SettlementResult(Outcome.UNSETTLED, None, None, reasons)
    if odds is None or odds <= 1.0:
        reasons.append("cuota_invalida")
        return SettlementResult(Outcome.UNSETTLED, None, None, reasons)

    profit = outcome_return(outcome, odds) * float(stake_units)
    return SettlementResult(
        outcome=outcome,
        profit_units=profit,
        hit_value=outcome_hit_value(outcome),
        reasons=reasons,
    )


# ═══════════════════════════════════════════════════════════════════════
# PUENTE CON EL FORMATO LEGACY DE main.py
# ═══════════════════════════════════════════════════════════════════════
#
# `main.py::_check_pick_success` devuelve `PickOutcome = bool | str | None`:
#     True | False | "half_win" | "half_loss" | "void" | None
#
# Ese tipo no distingue "no se pudo liquidar" (None) de "push" de forma
# explícita y no es comparable entre módulos. Este puente lo traduce al enum
# único para que la calibración y el ROI usen la MISMA definición de acierto,
# en lugar de dos escalas paralelas que pueden divergir.

_LEGACY_OUTCOME_MAP: dict[object, "Outcome"] = {
    True: Outcome.WIN,
    False: Outcome.LOSS,
    "half_win": Outcome.HALF_WIN,
    "half_loss": Outcome.HALF_LOSS,
    "void": Outcome.PUSH,
    "push": Outcome.PUSH,
    None: Outcome.UNSETTLED,
}


def outcome_from_legacy(value: object) -> Outcome:
    """
    Traduce un `PickOutcome` legacy al enum `Outcome`.

    Un valor desconocido se trata como UNSETTLED (fallar cerrado): es preferible
    excluir el pick del histórico que contarlo como acierto o fallo inventado.
    """
    if isinstance(value, Outcome):
        return value
    # `True`/`False` deben resolverse antes que los strings porque en Python
    # `True == 1` y un dict lookup con bool es correcto, pero un str vacío no.
    if isinstance(value, bool):
        return Outcome.WIN if value else Outcome.LOSS
    if isinstance(value, str):
        return _LEGACY_OUTCOME_MAP.get(value.strip().lower(), Outcome.UNSETTLED)
    return _LEGACY_OUTCOME_MAP.get(value, Outcome.UNSETTLED)
