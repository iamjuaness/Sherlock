"""Rutas ml de la API (extraídas de main.py)."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db

from src.ui.api.shared import TrainRequest
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/v1/ml/train", tags=["ML"])
def train_calibrator_endpoint(req: TrainRequest, db: Session = Depends(get_db)):
    """
    Reentrena el calibrador de probabilidades y publica el artefacto.

    Esta ruta faltaba: `src/core/train_model_retrospective.py` la invocaba y
    recibía 404, de modo que el pipeline de entrenamiento estaba roto de punta a
    punta.

    Reemplaza al entrenamiento GLM previsto originalmente. El calibrador es la
    Beta-Binomial jerárquica con isotónica PAVA, y solo se promueve el artefacto
    si mejora Brier Y log loss fuera de muestra: un reentrenamiento no puede
    empeorar el sistema por el simple hecho de haberse ejecutado.
    """
    from src.core.train_calibration import run_training
    from src.ui.api.compare import reset_calibrator_cache

    try:
        report = run_training(
            prior_strength=req.prior_strength,  # None → búsqueda automática
            min_samples=req.min_samples,
            n_folds=req.n_folds,
            limit=req.limit,
            until_date=req.until_date,
            require_timestamp=not req.allow_missing_timestamp,
            force=req.force,
            dry_run=req.dry_run,
            session=db,
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Fallo al entrenar el calibrador: {err}")

    if report.promoted and not req.dry_run:
        # El artefacto en disco cambió; invalidar la cache para que las
        # siguientes peticiones usen el calibrador nuevo sin reiniciar.
        reset_calibrator_cache()

    payload = report.as_dict()
    payload["summary"] = report.summary()
    payload["ignored_records"] = len(req.records or [])
    return payload
