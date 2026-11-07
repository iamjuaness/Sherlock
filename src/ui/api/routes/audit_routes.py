"""Rutas audit de la API (extraídas de main.py)."""

from __future__ import annotations

import json
from fastapi import HTTPException

from src.ui.api.shared import SeasonAuditPayload
from fastapi import APIRouter

router = APIRouter()


@router.post("/api/v1/audit/season", tags=["Audit"])
def save_season_audit(payload: SeasonAuditPayload):
    """Guarda reporte de auditoría de temporada en data/audit_season_{sId}.json"""
    import os

    os.makedirs("data", exist_ok=True)
    file_path = os.path.join("data", f"audit_season_{payload.season_id}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                payload.model_dump() if hasattr(payload, "model_dump") else payload.dict(),
                f,
                indent=2,
            )
        return {"status": "ok", "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
