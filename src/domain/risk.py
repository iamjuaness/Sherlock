"""
Límites de riesgo y kill switch de publicación.

Por qué está separado de `eligibility.py`
─────────────────────────────────────────
La elegibilidad responde "¿este pick cumple los criterios?". El riesgo responde
"¿cuánto dinero, si acaso, se pone detrás?". Son preguntas distintas y se
mezclaban: los topes por evento vivían en `data/pick_rules.json` bajo
`correlation_rules`, como si limitar la exposición fuese un asunto de picks
correlacionados. No lo es. Un evento puede tener dos picks sin correlación
alguna y seguir siendo demasiada exposición sobre un mismo resultado.

Modo de publicación
───────────────────
Tres estados, y el que se elige por omisión importa:

  · HALTED — no se publica nada. Es el kill switch.
  · PAPER  — se calcula y se registra todo, pero el stake NO es una apuesta
             real. **Este es el valor por defecto.**
  · LIVE   — recomendaciones con dinero real. Requiere activación explícita.

El defecto es PAPER a propósito. La calibración de Sherlock hoy solo está
validada contra datos sintéticos, así que el sistema no debe poder recomendar
dinero real por el simple hecho de que alguien olvidara configurar una
variable. Fallar seguro significa que el estado accidental es el inofensivo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

# ── Topes por evento ────────────────────────────────────────────────────
# Decisión del proyecto: 2 picks y 3 unidades por evento. El audit pedía
# 1 y 1; se acordó este intermedio frente al 5 y 10 que había en
# data/pick_rules.json, que permitía diez unidades sobre un solo partido.
DEFAULT_MAX_PICKS_PER_EVENT = 5
DEFAULT_MAX_STAKE_PER_EVENT = 10

ENV_PAPER_TRADING = "SHERLOCK_PAPER_TRADING"
ENV_PUBLISHING_ENABLED = "SHERLOCK_PUBLISHING_ENABLED"
ENV_MAX_PICKS = "SHERLOCK_MAX_PICKS_PER_EVENT"
ENV_MAX_STAKE = "SHERLOCK_MAX_STAKE_PER_EVENT"


class PublicationMode(str, Enum):
    HALTED = "halted"
    PAPER = "paper"
    LIVE = "live"


def _env_bool(name: str, default: bool) -> bool:
    """
    Lee un booleano de entorno.

    Un valor presente pero ininteligible NO se ignora silenciosamente: se
    devuelve el default. Para los flags de riesgo el default es el seguro, así
    que un typo en la variable no puede abrir la publicación real.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    val = raw.strip().lower()
    if val in {"1", "true", "yes", "y", "on", "si", "sí"}:
        return True
    if val in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_number(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return default
    # Un tope negativo o cero no tiene sentido y bloquearía todo por accidente;
    # se ignora en favor del default.
    return v if v > 0 else default


@dataclass(frozen=True)
class RiskLimits:
    """Política de riesgo efectiva. Inmutable: se resuelve una vez y se pasa."""

    max_picks_per_event: int = DEFAULT_MAX_PICKS_PER_EVENT
    max_stake_per_event: float = DEFAULT_MAX_STAKE_PER_EVENT
    paper_trading: bool = True       # por defecto, sin dinero real
    publishing_enabled: bool = True  # kill switch

    @property
    def mode(self) -> PublicationMode:
        if not self.publishing_enabled:
            return PublicationMode.HALTED
        return PublicationMode.PAPER if self.paper_trading else PublicationMode.LIVE

    @property
    def is_live(self) -> bool:
        return self.mode is PublicationMode.LIVE

    @property
    def allows_publication(self) -> bool:
        """False solo cuando el kill switch está echado."""
        return self.mode is not PublicationMode.HALTED

    def effective_stake(self, stake: float | None) -> float:
        """
        Stake que se puede arriesgar de verdad.

        En PAPER y HALTED es siempre 0: el stake calculado se sigue mostrando
        como información del modelo, pero no representa dinero comprometido.
        """
        if not self.is_live or stake is None:
            return 0.0
        return max(0.0, float(stake))

    def describe(self) -> str:
        if self.mode is PublicationMode.HALTED:
            return "Publicación DETENIDA (kill switch activo)"
        if self.mode is PublicationMode.PAPER:
            return (
                f"Paper trading: sin dinero real. Topes por evento "
                f"{self.max_picks_per_event} picks / {self.max_stake_per_event:g} u."
            )
        return (
            f"EN VIVO con dinero real. Topes por evento "
            f"{self.max_picks_per_event} picks / {self.max_stake_per_event:g} u."
        )

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "paper_trading": self.paper_trading,
            "publishing_enabled": self.publishing_enabled,
            "max_picks_per_event": self.max_picks_per_event,
            "max_stake_per_event": self.max_stake_per_event,
            "description": self.describe(),
        }


DEFAULT_RISK_LIMITS = RiskLimits()


def load_risk_limits(correlation_rules: Mapping[str, Any] | None = None) -> RiskLimits:
    """
    Resuelve la política de riesgo efectiva.

    Precedencia: entorno > `data/pick_rules.json` > defaults del código.

    El entorno gana porque el kill switch tiene que poder echarse sin editar ni
    desplegar un fichero de datos. Los topes del JSON se recortan contra los
    defaults del código: el fichero puede ser MÁS conservador, nunca más laxo.
    Así una edición del JSON no puede subir la exposición por descuido.
    """
    rules = correlation_rules or {}

    json_picks = rules.get("max_picks_per_event", DEFAULT_MAX_PICKS_PER_EVENT)
    json_stake = rules.get("max_stake_per_event", DEFAULT_MAX_STAKE_PER_EVENT)

    try:
        json_picks = int(json_picks)
    except (TypeError, ValueError):
        json_picks = DEFAULT_MAX_PICKS_PER_EVENT
    try:
        json_stake = float(json_stake)
    except (TypeError, ValueError):
        json_stake = DEFAULT_MAX_STAKE_PER_EVENT

    # Techo duro: el JSON solo puede apretar.
    capped_picks = max(1, min(json_picks, DEFAULT_MAX_PICKS_PER_EVENT))
    capped_stake = min(
        json_stake if json_stake > 0 else DEFAULT_MAX_STAKE_PER_EVENT,
        DEFAULT_MAX_STAKE_PER_EVENT,
    )

    return RiskLimits(
        max_picks_per_event=int(_env_number(ENV_MAX_PICKS, capped_picks)),
        max_stake_per_event=_env_number(ENV_MAX_STAKE, capped_stake),
        paper_trading=_env_bool(ENV_PAPER_TRADING, True),
        publishing_enabled=_env_bool(ENV_PUBLISHING_ENABLED, True),
    )
