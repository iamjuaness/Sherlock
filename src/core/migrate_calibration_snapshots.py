"""
Script de migración aditiva e idempotente para snapshots de calibración en Sherlock.

Reglas:
- No altera resultados, cuotas, ni decisiones originales de la recomendación.
- Agrega campos de snapshot inmutable (`pick_id`, `predicted_at_utc`, `model_prob_raw`,
  `calibration_version`) a cada pick en `AnalysisHistory.picks_calculados`.
- Para registros antiguos donde la versión exacta no pueda demostrarse, asigna `calibration_version="unverified"`.
- Es idempotente y auditable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from src.core.database import SessionLocal, engine
from src.core.domain import AnalysisHistory

logger = logging.getLogger("sherlock.migrate_calibration_snapshots")


def migrate_picks_snapshots(db: Session) -> dict:
    records = db.query(AnalysisHistory).filter(AnalysisHistory.picks_calculados.isnot(None)).all()
    migrated_records = 0
    total_picks_migrated = 0

    for ah in records:
        if not ah.picks_calculados:
            continue

        raw = ah.picks_calculados
        if isinstance(raw, str):
            try:
                picks_data = json.loads(raw)
            except Exception:
                continue
        else:
            picks_data = raw

        if isinstance(picks_data, dict):
            picks_list = picks_data.get("picks") or picks_data.get("value_picks") or []
        elif isinstance(picks_data, list):
            picks_list = picks_data
        else:
            continue

        modified = False
        match_ts = ah.match_date or ah.date
        default_predicted_at = match_ts.isoformat() if match_ts else datetime.now(timezone.utc).isoformat()

        for idx, p in enumerate(picks_list):
            if not isinstance(p, dict):
                continue

            if "pick_id" not in p:
                p["pick_id"] = f"{ah.id}_{idx}"
                modified = True

            if "predicted_at_utc" not in p:
                p["predicted_at_utc"] = default_predicted_at
                modified = True

            if "model_prob_raw" not in p:
                prob = p.get("model_prob") or p.get("probability") or p.get("prob") or 0.5
                p["model_prob_raw"] = float(prob)
                modified = True

            if "calibration_version" not in p:
                p["calibration_version"] = "unverified"
                modified = True

            total_picks_migrated += 1

        if modified:
            ah.picks_calculados = json.dumps(picks_data)
            migrated_records += 1

    if migrated_records > 0:
        db.commit()

    return {
        "migrated_records": migrated_records,
        "total_picks_migrated": total_picks_migrated,
    }


if __name__ == "__main__":
    db = SessionLocal()
    try:
        res = migrate_picks_snapshots(db)
        print(f"Migración completada con éxito: {res}")
    finally:
        db.close()
