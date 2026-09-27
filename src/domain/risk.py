"""
Límites de riesgo y kill switch de publicación.

Por qué está separado de `eligibility.py`
─────────────────────────────────────────
La elegibilidad responde "¿este pick cumple los criterios?". El riesgo responde
"¿cuánto dinero, si acaso, se pone detrás?". Son preguntas distintas. La
limitación de exposición por evento se maneja automáticamente mediante la
correlación entre picks.

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

ENV_PAPER_TRADING = "SHERLOCK_PAPER_TRADING"
ENV_PUBLISHING_ENABLED = "SHERLOCK_PUBLISHING_ENABLED"


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


@dataclass(frozen=True)
class RiskLimits:
    """Política de riesgo efectiva. Inmutable: se resuelve una vez y se pasa."""

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
            return "Paper trading: sin dinero real."
        return "EN VIVO con dinero real."

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "paper_trading": self.paper_trading,
            "publishing_enabled": self.publishing_enabled,
            "description": self.describe(),
        }


DEFAULT_RISK_LIMITS = RiskLimits()


def load_risk_limits(correlation_rules: Mapping[str, Any] | None = None) -> RiskLimits:
    """
    Resuelve la política de riesgo efectiva.

    Precedencia: entorno > defaults del código.
    """
    return RiskLimits(
        paper_trading=_env_bool(ENV_PAPER_TRADING, True),
        publishing_enabled=_env_bool(ENV_PUBLISHING_ENABLED, True),
    )
