"""
Probability calibration and market normalization modules.
Provides PlattCalibrator (logistic regression on logit) and IsotonicCalibrator,
plus exact categorical market probability normalization.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence, Union
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression


def normalize_categorical_market(prob_dict: Dict[str, float], epsilon: float = 1e-9) -> Dict[str, float]:
    """
    Guarantees that any exhaustive and mutually exclusive set of event outcomes
    (e.g., {'home': p1, 'draw': p2, 'away': p3} or {'over': p1, 'under': p2})
    is rescaled so their sum is exactly 1.0 (within float tolerance 1e-6).
    """
    if not prob_dict:
        return {}

    cleaned = {k: max(float(v), 0.0) for k, v in prob_dict.items()}
    total = sum(cleaned.values())

    if total <= epsilon:
        # Uniform fallback
        n = len(cleaned)
        return {k: 1.0 / n for k in cleaned}

    return {k: v / total for k, v in cleaned.items()}


class PlattCalibrator:
    """
    Platt Scaling via logistic regression over log-odds (logit):
    logit(p) = ln(p / (1 - p))
    """

    def __init__(self, epsilon: float = 1e-6):
        self.epsilon = epsilon
        self.model: Optional[LogisticRegression] = None
        self._is_fitted = False

    def _to_logit(self, p: np.ndarray) -> np.ndarray:
        p_clipped = np.clip(p, self.epsilon, 1.0 - self.epsilon)
        return np.log(p_clipped / (1.0 - p_clipped))

    def fit(self, probs: Sequence[float], y_true: Sequence[int]) -> PlattCalibrator:
        p_arr = np.asarray(probs, dtype=np.float64)
        y_arr = np.asarray(y_true, dtype=np.int32)
        if len(np.unique(y_arr)) < 2:
            # Cannot fit binary classifier with single class
            self._is_fitted = False
            return self

        logits = self._to_logit(p_arr).reshape(-1, 1)
        self.model = LogisticRegression(solver="lbfgs", C=1.0)
        self.model.fit(logits, y_arr)
        self._is_fitted = True
        return self

    def predict_proba(self, probs: Union[float, Sequence[float], np.ndarray]) -> np.ndarray:
        p_arr = np.atleast_1d(np.asarray(probs, dtype=np.float64))
        if not self._is_fitted or self.model is None:
            # Identity fallback if not fitted
            return np.clip(p_arr, 0.0, 1.0)

        logits = self._to_logit(p_arr).reshape(-1, 1)
        # Class 1 probability
        calibrated = self.model.predict_proba(logits)[:, 1]
        return np.clip(calibrated, 0.0, 1.0)

    def predict(self, probs: Union[float, Sequence[float], np.ndarray]) -> np.ndarray:
        return self.predict_proba(probs)


class IsotonicCalibrator:
    """
    Robust wrapper around sklearn.isotonic.IsotonicRegression.
    """

    def __init__(self, out_of_bounds: str = "clip", y_min: float = 0.001, y_max: float = 0.999):
        self.out_of_bounds = out_of_bounds
        self.y_min = y_min
        self.y_max = y_max
        self.model = IsotonicRegression(
            out_of_bounds=self.out_of_bounds,
            y_min=self.y_min,
            y_max=self.y_max,
        )
        self._is_fitted = False

    def fit(self, probs: Sequence[float], y_true: Sequence[int]) -> IsotonicCalibrator:
        p_arr = np.asarray(probs, dtype=np.float64)
        y_arr = np.asarray(y_true, dtype=np.float64)
        if len(p_arr) < 2:
            self._is_fitted = False
            return self

        self.model.fit(p_arr, y_arr)
        self._is_fitted = True
        return self

    def predict_proba(self, probs: Union[float, Sequence[float], np.ndarray]) -> np.ndarray:
        p_arr = np.atleast_1d(np.asarray(probs, dtype=np.float64))
        if not self._is_fitted:
            return np.clip(p_arr, self.y_min, self.y_max)

        calibrated = self.model.predict(p_arr)
        return np.clip(calibrated, self.y_min, self.y_max)

    def predict(self, probs: Union[float, Sequence[float], np.ndarray]) -> np.ndarray:
        return self.predict_proba(probs)

