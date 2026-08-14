"""
Motor de predicción GLM/ML para Sherlock.

Reemplaza los multiplicadores tácticos arbitrarios por modelos estadísticos
entrenados sobre datos históricos reales:

  - Regresión de Poisson   -> goles esperados (xG ofensivo/defensivo)
  - Regresión Binomial Neg. -> corners, tiros, tarjetas (distribución de cola larga)
  - Calibración Isotónica   -> ajusta probabilidades finales con sklearn.IsotonicRegression

Cuando no hay suficiente data para entrenar (< MIN_TRAIN_SAMPLES), el módulo
hace un fallback transparente a los valores heurísticos actuales del comparador.

Flujo típico:
    from src.core.glm_model import get_predictor

    predictor = get_predictor()
    mu_home, mu_away = predictor.predict_goals(home_stats, away_stats)  # lambda Poisson
    p_over = predictor.prob_over(mu_home + mu_away, line=2.5, market="goals")
"""

from __future__ import annotations

import logging
import math
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sherlock.glm_model")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MIN_TRAIN_SAMPLES = 80   # mínimo de partidos para entrenar un modelo real
MODEL_CACHE_DIR   = Path(__file__).parent.parent.parent / "data" / "models"
MODEL_CACHE_FILE  = MODEL_CACHE_DIR / "glm_predictor.pkl"

# Coeficientes de fallback (intercepts en escala log)
_FALLBACK_GOALS_INTERCEPT    = 1.15   # exp(1.15) ≈ 3.16 goles/partido total
_FALLBACK_CORNERS_INTERCEPT  = 2.15   # exp(2.15) ≈ 8.57 corners/partido total
_FALLBACK_CARDS_INTERCEPT    = 1.55   # exp(1.55) ≈ 4.71 tarjetas/partido total
_FALLBACK_SHOTS_INTERCEPT    = 3.00   # exp(3.00) ≈ 20.09 tiros/partido total


# ---------------------------------------------------------------------------
# Funciones de distribución
# ---------------------------------------------------------------------------

def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    except (OverflowError, ValueError):
        return 0.0


def _poisson_cdf(k_max: int, lam: float) -> float:
    return sum(_poisson_pmf(k, lam) for k in range(k_max + 1))


def prob_over_poisson(lam: float, line: float) -> float:
    """P(X > line) donde X ~ Poisson(lambda)."""
    k_floor = int(math.floor(line))
    return 1.0 - _poisson_cdf(k_floor, lam)


def prob_over_nb(mu: float, dispersion: float, line: float) -> float:
    """
    P(X > line) donde X ~ NegBin(mu, r).
    Usa aproximación Poisson cuando dispersion es muy pequeña.
    """
    if dispersion <= 0.05:
        return prob_over_poisson(mu, line)
    try:
        from scipy.stats import nbinom  # type: ignore
        r = 1.0 / dispersion
        p_success = r / (r + mu)
        k_floor = int(math.floor(line))
        return float(1.0 - nbinom.cdf(k_floor, r, p_success))
    except ImportError:
        logger.warning("[GLM] scipy no disponible — usando Poisson como fallback para NB")
        return prob_over_poisson(mu, line)


# ---------------------------------------------------------------------------
# Vectores de features
# ---------------------------------------------------------------------------

def _goals_features(home_stats: dict, away_stats: dict) -> list:
    """Features para predecir lambda de goles de un equipo."""
    def feat(atk: dict, def_: dict, is_home: int) -> list:
        return [
            float(atk.get("goals_per_game", 1.2)),
            float(def_.get("goals_conceded_per_game", 1.2)),
            float(atk.get("xg_per_game", atk.get("goals_per_game", 1.2))),
            float(atk.get("shots_on_target_per_game", 4.0)),
            float(atk.get("possession_pct", 50.0)) / 100.0,
            float(is_home),
        ]
    return feat(home_stats, away_stats, 1) + feat(away_stats, home_stats, 0)


def _secondary_features(home_stats: dict, away_stats: dict, market: str) -> list:
    """Features para mercados secundarios (corners, tiros, tarjetas)."""
    h = home_stats
    a = away_stats
    if market == "corners":
        return [
            float(h.get("corners_per_game", 5.0)),
            float(a.get("corners_per_game", 5.0)),
            float(h.get("possession_pct", 50.0)) / 100.0,
            float(a.get("possession_pct", 50.0)) / 100.0,
            float(h.get("shots_per_game", 12.0)),
            float(a.get("shots_per_game", 12.0)),
        ]
    elif market == "cards":
        return [
            float(h.get("yellow_cards_per_game", 2.0)),
            float(a.get("yellow_cards_per_game", 2.0)),
            float(h.get("balls_recovered_per_game", 12.0)),
            float(a.get("balls_recovered_per_game", 12.0)),
        ]
    elif market in ("shots", "shots_target"):
        key = "shots_on_target_per_game" if market == "shots_target" else "shots_per_game"
        return [
            float(h.get(key, 12.0)),
            float(a.get(key, 12.0)),
            float(h.get("xg_per_game", 1.2)),
            float(a.get("xg_per_game", 1.2)),
        ]
    return [1.0, 1.0]


# ---------------------------------------------------------------------------
# Calibración isotónica
# ---------------------------------------------------------------------------

@dataclass
class IsotonicCalibrator:
    """
    Calibrador de probabilidades usando sklearn.IsotonicRegression.
    Se entrena con (y_prob_predicted, y_true) donde y_true in {0, 1}.
    """
    _model: object = field(default=None, repr=False)
    is_trained: bool = False
    n_samples: int = 0

    def fit(self, y_prob: list, y_true: list) -> "IsotonicCalibrator":
        if len(y_prob) < 20:
            logger.warning("[GLM] IsotonicCalibrator: insuficientes muestras (%d)", len(y_prob))
            return self
        try:
            from sklearn.isotonic import IsotonicRegression  # type: ignore
            ir = IsotonicRegression(out_of_bounds="clip")
            ir.fit(y_prob, y_true)
            self._model = ir
            self.is_trained = True
            self.n_samples = len(y_prob)
            logger.info("[GLM] IsotonicCalibrator entrenado con %d muestras", self.n_samples)
        except ImportError:
            logger.warning("[GLM] sklearn no disponible — calibración isotónica desactivada")
        return self

    def calibrate(self, prob: float) -> float:
        if not self.is_trained or self._model is None:
            return prob
        try:
            result = float(self._model.predict([max(0.0, min(1.0, prob))])[0])
            return max(0.0, min(1.0, result))
        except Exception as exc:
            logger.warning("[GLM] Error en calibración isotónica: %s", exc)
            return prob


# ---------------------------------------------------------------------------
# Modelo lineal simple (Poisson/NB)
# ---------------------------------------------------------------------------

@dataclass
class _LinearModel:
    """Regresión log-lineal para Poisson/NB."""
    coefficients: list
    intercept: float
    dispersion: float = 0.0   # 0 = Poisson; >0 = Binomial Negativa
    is_trained: bool = False
    n_samples: int = 0

    def predict_mu(self, features: list) -> float:
        if not self.is_trained:
            return math.exp(self.intercept)
        linear = self.intercept + sum(c * x for c, x in zip(self.coefficients, features))
        return math.exp(min(linear, 4.0))

    @classmethod
    def fallback(cls, intercept: float) -> "_LinearModel":
        return cls(coefficients=[], intercept=intercept, is_trained=False)


# ---------------------------------------------------------------------------
# Predictor GLM principal
# ---------------------------------------------------------------------------

class GLMPredictor:
    """
    Predictor estadístico unificado para fútbol.

    Expone:
      predict_goals(home_stats, away_stats)       -> (mu_home, mu_away)
      predict_secondary(home_stats, away_stats, market) -> mu_total
      prob_over(mu, line, market)                 -> float [0-1]
      calibrate(prob, market)                     -> float [0-1]

    Fallback automático a heurísticas cuando no hay suficientes datos de entrenamiento.
    """

    def __init__(self) -> None:
        self._goals_home_model = _LinearModel.fallback(_FALLBACK_GOALS_INTERCEPT)
        self._goals_away_model = _LinearModel.fallback(_FALLBACK_GOALS_INTERCEPT - 0.15)
        self._secondary_models: dict = {
            "corners":      _LinearModel.fallback(_FALLBACK_CORNERS_INTERCEPT),
            "cards":        _LinearModel.fallback(_FALLBACK_CARDS_INTERCEPT),
            "shots":        _LinearModel.fallback(_FALLBACK_SHOTS_INTERCEPT),
            "shots_target": _LinearModel.fallback(math.log(7.5)),
        }
        self._calibrators: dict = {}
        self.n_training_samples: int = 0
        self.is_trained: bool = False

    # --- Persistencia -------------------------------------------------------

    def save(self, path: Path = MODEL_CACHE_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("[GLM] Modelo guardado en %s", path)

    @classmethod
    def load(cls, path: Path = MODEL_CACHE_FILE) -> Optional["GLMPredictor"]:
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                obj = pickle.load(f)
            logger.info("[GLM] Modelo cargado desde %s (%d muestras)", path, obj.n_training_samples)
            return obj
        except Exception as exc:
            logger.warning("[GLM] No se pudo cargar: %s — se creará uno nuevo", exc)
            return None

    @classmethod
    def load_or_create(cls) -> "GLMPredictor":
        cached = cls.load()
        return cached if cached is not None else cls()

    # --- Entrenamiento ------------------------------------------------------

    def train(self, records: list) -> "GLMPredictor":
        """
        Entrena todos los modelos con datos históricos.

        Cada registro debe contener:
          home_stats / away_stats: dict con métricas por partido
          final_score_home / away, final_corners_home / away,
          final_yellow_cards_home / away, final_shots_home / away,
          final_shots_on_target_home / away
        """
        valid = [r for r in records if r.get("home_stats") and r.get("away_stats")]
        n = len(valid)
        self.n_training_samples = n

        if n < MIN_TRAIN_SAMPLES:
            logger.info(
                "[GLM] Solo %d registros (mínimo %d) — usando coeficientes de fallback",
                n, MIN_TRAIN_SAMPLES,
            )
            self.is_trained = False
            return self

        logger.info("[GLM] Entrenando con %d registros...", n)
        try:
            self._train_goals(valid)
            self._train_secondary(valid, "corners",
                lambda r: (r.get("final_corners_home", 0) or 0) +
                           (r.get("final_corners_away", 0) or 0))
            self._train_secondary(valid, "cards",
                lambda r: (r.get("final_yellow_cards_home", 0) or 0) +
                           (r.get("final_yellow_cards_away", 0) or 0))
            self._train_secondary(valid, "shots",
                lambda r: (r.get("final_shots_home", 0) or 0) +
                           (r.get("final_shots_away", 0) or 0))
            self._train_secondary(valid, "shots_target",
                lambda r: (r.get("final_shots_on_target_home", 0) or 0) +
                           (r.get("final_shots_on_target_away", 0) or 0))
            self._train_calibrators(valid)
            self.is_trained = True
            logger.info("[GLM] Entrenamiento completado.")
        except Exception as exc:
            logger.error("[GLM] Error durante entrenamiento: %s", exc, exc_info=True)
            self.is_trained = False

        return self

    def _train_goals(self, records: list) -> None:
        try:
            import numpy as np  # type: ignore
            import statsmodels.api as sm  # type: ignore

            X_home, X_away, y_home, y_away = [], [], [], []
            for r in records:
                try:
                    feats = _goals_features(r["home_stats"], r["away_stats"])
                    mid = len(feats) // 2
                    X_home.append(feats[:mid])
                    X_away.append(feats[mid:])
                    y_home.append(int(r.get("final_score_home", 0) or 0))
                    y_away.append(int(r.get("final_score_away", 0) or 0))
                except Exception:
                    pass

            for model_attr, X_list, y_list in [
                ("_goals_home_model", X_home, y_home),
                ("_goals_away_model", X_away, y_away),
            ]:
                if len(X_list) < MIN_TRAIN_SAMPLES:
                    continue
                X = sm.add_constant(np.array(X_list, dtype=float))
                y = np.array(y_list, dtype=float)
                glm = sm.GLM(y, X, family=sm.families.Poisson()).fit(disp=False)
                m = _LinearModel(
                    coefficients=list(glm.params[1:]),
                    intercept=float(glm.params[0]),
                    dispersion=0.0,
                    is_trained=True,
                    n_samples=len(X_list),
                )
                setattr(self, model_attr, m)
                logger.info("[GLM] Goles (%s): %d muestras, AIC=%.1f", model_attr, len(X_list), glm.aic)
        except ImportError:
            logger.warning("[GLM] statsmodels no disponible — fallback para goles")

    def _train_secondary(self, records: list, market: str, y_extractor) -> None:
        try:
            import numpy as np  # type: ignore
            import statsmodels.api as sm  # type: ignore

            X_list, y_list = [], []
            for r in records:
                try:
                    feats = _secondary_features(r["home_stats"], r["away_stats"], market)
                    y_val = y_extractor(r)
                    if y_val is not None and y_val >= 0:
                        X_list.append(feats)
                        y_list.append(int(y_val))
                except Exception:
                    pass

            if len(X_list) < MIN_TRAIN_SAMPLES:
                return

            X = sm.add_constant(np.array(X_list, dtype=float))
            y = np.array(y_list, dtype=float)
            try:
                glm = sm.GLM(y, X, family=sm.families.NegativeBinomial()).fit(disp=False)
                disp = float(getattr(glm, "scale", 0.0))
            except Exception:
                glm = sm.GLM(y, X, family=sm.families.Poisson()).fit(disp=False)
                disp = 0.0

            self._secondary_models[market] = _LinearModel(
                coefficients=list(glm.params[1:]),
                intercept=float(glm.params[0]),
                dispersion=disp,
                is_trained=True,
                n_samples=len(X_list),
            )
            logger.info("[GLM] %s: %d muestras", market, len(X_list))
        except ImportError:
            logger.warning("[GLM] statsmodels no disponible — fallback para %s", market)

    def _train_calibrators(self, records: list) -> None:
        lines = {
            "goals": 2.5, "corners": 9.5,
            "cards": 3.5, "shots": 20.5, "shots_target": 7.5,
        }
        for market, line in lines.items():
            y_prob: list = []
            y_true: list = []
            for r in records:
                try:
                    hs, aws = r["home_stats"], r["away_stats"]
                    if market == "goals":
                        mu_h, mu_a = self.predict_goals(hs, aws)
                        mu = mu_h + mu_a
                        p = prob_over_poisson(mu, line)
                        total = (r.get("final_score_home", 0) or 0) + (r.get("final_score_away", 0) or 0)
                    elif market == "corners":
                        mu = self.predict_secondary(hs, aws, market)
                        m = self._secondary_models.get(market)
                        p = prob_over_nb(mu, m.dispersion if m else 0.0, line)
                        total = (r.get("final_corners_home", 0) or 0) + (r.get("final_corners_away", 0) or 0)
                    elif market == "cards":
                        mu = self.predict_secondary(hs, aws, market)
                        m = self._secondary_models.get(market)
                        p = prob_over_nb(mu, m.dispersion if m else 0.0, line)
                        total = (r.get("final_yellow_cards_home", 0) or 0) + (r.get("final_yellow_cards_away", 0) or 0)
                    elif market == "shots":
                        mu = self.predict_secondary(hs, aws, market)
                        m = self._secondary_models.get(market)
                        p = prob_over_nb(mu, m.dispersion if m else 0.0, line)
                        total = (r.get("final_shots_home", 0) or 0) + (r.get("final_shots_away", 0) or 0)
                    elif market == "shots_target":
                        mu = self.predict_secondary(hs, aws, market)
                        m = self._secondary_models.get(market)
                        p = prob_over_nb(mu, m.dispersion if m else 0.0, line)
                        total = (r.get("final_shots_on_target_home", 0) or 0) + (r.get("final_shots_on_target_away", 0) or 0)
                    else:
                        continue

                    y_prob.append(p)
                    y_true.append(1 if total > line else 0)
                except Exception:
                    pass

            if len(y_prob) >= 20:
                cal = IsotonicCalibrator()
                cal.fit(y_prob, y_true)
                self._calibrators[market] = cal
                logger.info("[GLM] Calibrador %s: %d muestras", market, len(y_prob))

    # --- Predicción ---------------------------------------------------------

    def predict_goals(self, home_stats: dict, away_stats: dict) -> tuple:
        """
        Predice lambda de Poisson para cada equipo.
        Returns (mu_home, mu_away).
        """
        try:
            feats_all = _goals_features(home_stats, away_stats)
            mid = len(feats_all) // 2
            mu_home = self._goals_home_model.predict_mu(feats_all[:mid])
            mu_away = self._goals_away_model.predict_mu(feats_all[mid:])
        except Exception as exc:
            logger.warning("[GLM] predict_goals error: %s", exc)
            mu_home = float(home_stats.get("goals_per_game", 1.3))
            mu_away = float(away_stats.get("goals_per_game", 1.1))
        return max(0.1, min(mu_home, 5.0)), max(0.1, min(mu_away, 5.0))

    def predict_secondary(self, home_stats: dict, away_stats: dict, market: str) -> float:
        """
        Predice mu total del partido para mercados secundarios.
        market: "corners" | "cards" | "shots" | "shots_target"
        """
        model = self._secondary_models.get(market)
        if model is None:
            return self._fallback_secondary(home_stats, away_stats, market)
        try:
            feats = _secondary_features(home_stats, away_stats, market)
            return max(0.1, model.predict_mu(feats))
        except Exception as exc:
            logger.warning("[GLM] predict_secondary(%s) error: %s", market, exc)
            return self._fallback_secondary(home_stats, away_stats, market)

    def _fallback_secondary(self, home_stats: dict, away_stats: dict, market: str) -> float:
        if market == "corners":
            return (float(home_stats.get("corners_per_game", 5.0)) +
                    float(away_stats.get("corners_per_game", 5.0)))
        elif market == "cards":
            return (float(home_stats.get("yellow_cards_per_game", 2.0)) +
                    float(away_stats.get("yellow_cards_per_game", 2.0)))
        elif market == "shots":
            return (float(home_stats.get("shots_per_game", 12.0)) +
                    float(away_stats.get("shots_per_game", 12.0)))
        elif market == "shots_target":
            return (float(home_stats.get("shots_on_target_per_game", 4.5)) +
                    float(away_stats.get("shots_on_target_per_game", 4.5)))
        return 5.0

    def prob_over(self, mu: float, line: float, market: str = "goals") -> float:
        """
        P(X > line) bajo la distribución del mercado dado, con calibración isotónica.
        Goles -> Poisson; corners/cards/shots -> Binomial Negativa (fallback a Poisson).
        """
        model = self._secondary_models.get(market) if market != "goals" else None
        disp  = model.dispersion if model else 0.0
        raw_p = prob_over_nb(mu, disp, line) if disp > 0 else prob_over_poisson(mu, line)
        return max(0.0, min(1.0, self.calibrate(raw_p, market)))

    def calibrate(self, prob: float, market: str = "goals") -> float:
        """Aplica calibración isotónica. Sin cambios si no está entrenado."""
        cal = self._calibrators.get(market)
        return cal.calibrate(prob) if cal else prob


# ---------------------------------------------------------------------------
# Singleton global
# ---------------------------------------------------------------------------

_GLOBAL_PREDICTOR: Optional[GLMPredictor] = None


def get_predictor() -> GLMPredictor:
    """Devuelve el predictor singleton (carga desde disco si existe)."""
    global _GLOBAL_PREDICTOR
    if _GLOBAL_PREDICTOR is None:
        _GLOBAL_PREDICTOR = GLMPredictor.load_or_create()
    return _GLOBAL_PREDICTOR


def retrain_predictor(records: list) -> GLMPredictor:
    """
    Reentrena el predictor global y lo guarda en disco.
    Llamar desde el endpoint POST /api/v1/ml/train (background task).
    """
    global _GLOBAL_PREDICTOR
    predictor = GLMPredictor()
    predictor.train(records)
    predictor.save()
    _GLOBAL_PREDICTOR = predictor
    return predictor
