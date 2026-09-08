"""
Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets, etc.)
en analysis_history para partidos anteriores al 1 de julio de 2026 
donde (has_odds == 1 O el payload contiene cuotas).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from src.core.database import SessionLocal
from src.core.domain import AnalysisHistory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_odds")

CUTOFF_DATE = datetime(2026, 7, 1, 0, 0, 0)

ODDS_KEYS_PATTERNS = {
    "odds", "cuotas", "sources", "bookmaker", "bookmakers",
    "betting_lines", "betting", "markets", "picks_odds",
    "prematchodds", "liveodds", "lines"
}


def parse_any_date(val) -> datetime | None:
    """Parsea formatos de fecha en string, timestamps o datetimes."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        if val > 1e11:
            val = val / 1000.0
        try:
            return datetime.utcfromtimestamp(val)
        except Exception:
            return None
    if isinstance(val, str):
        val_clean = val.strip().replace("Z", "")
        if val_clean.isdigit():
            ts = float(val_clean)
            if ts > 1e11:
                ts = ts / 1000.0
            try:
                return datetime.utcfromtimestamp(ts)
            except Exception:
                pass

        date_formats = [
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
        ]
        for fmt in date_formats:
            try:
                return datetime.strptime(val_clean, fmt)
            except Exception:
                pass
        try:
            return datetime.fromisoformat(val_clean)
        except Exception:
            pass
    return None


def payload_contains_odds(obj) -> bool:
    """Verifica recursivamente si el payload contiene alguna clave de cuotas."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ODDS_KEYS_PATTERNS:
                return True
            if payload_contains_odds(v):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if payload_contains_odds(item):
                return True
    return False


def purge_odds_recursively(obj) -> bool:
    """Recorre recursivamente un dict/list y elimina claves relacionadas a cuotas."""
    changed = False
    if isinstance(obj, dict):
        keys_to_del = [k for k in obj if k.lower() in ODDS_KEYS_PATTERNS]
        for k in keys_to_del:
            del obj[k]
            changed = True
        for v in obj.values():
            if purge_odds_recursively(v):
                changed = True
    elif isinstance(obj, list):
        for item in obj:
            if purge_odds_recursively(item):
                changed = True
    return changed


def purge_odds_before_cutoff(cutoff_date: datetime = CUTOFF_DATE, dry_run: bool = False) -> int:
    """Limpia registros previos a cutoff_date donde has_odds == 1 O el payload contenga cuotas."""
    session = SessionLocal()
    records_updated = 0

    try:
        records = session.query(AnalysisHistory).all()
        logger.info("Total registros evaluados en base de datos: %d", len(records))

        for record in records:
            payload_data = {}
            if record.payload:
                try:
                    payload_data = (
                        json.loads(record.payload)
                        if isinstance(record.payload, str)
                        else record.payload
                    )
                except Exception:
                    pass

            # 1. Extraer y evaluar fecha
            m_date = (
                parse_any_date(record.match_date)
                or parse_any_date(record.date)
                or (isinstance(payload_data, dict) and parse_any_date(payload_data.get("match_date")))
                or (isinstance(payload_data, dict) and parse_any_date(payload_data.get("date")))
                or (isinstance(payload_data, dict) and parse_any_date(payload_data.get("startTimestamp")))
            )

            # Filtro 1: Debe ser anterior al 1 de julio de 2026
            if m_date and m_date >= cutoff_date:
                continue

            # Filtro 2: has_odds == 1 (o True) O el payload contiene cuotas
            has_odds_flag = bool(record.has_odds == 1 or record.has_odds is True)
            has_odds_in_payload = payload_contains_odds(payload_data)

            if not (has_odds_flag or has_odds_in_payload):
                continue

            # 3. Limpiar recursivamente el payload
            purge_odds_recursively(payload_data)

            records_updated += 1
            logger.info(
                "Limpiando ID: %s | Partido: %s | Fecha: %s | has_odds: %s | en_payload: %s",
                record.id,
                record.match_title,
                m_date.strftime("%Y-%m-%d") if m_date else "Sin fecha",
                has_odds_flag,
                has_odds_in_payload,
            )

            if not dry_run:
                record.payload = json.dumps(payload_data, ensure_ascii=False)
                record.has_odds = False
                record.bookmaker = None
                record.stake_units = None
                record.needs_recalc = True

        if not dry_run:
            session.commit()
            logger.info("Operación exitosa: %d registros limpiados y guardados.", records_updated)
        else:
            session.rollback()
            logger.info("[DRY RUN] Se habrían actualizado %d registros (sin guardar cambios).", records_updated)

    except Exception as exc:
        session.rollback()
        logger.exception("Error durante la eliminación de cuotas: %s", exc)
        raise
    finally:
        session.close()

    return records_updated


if __name__ == "__main__":
    # Cambia dry_run a False para ejecutar y persistir los cambios
    purge_odds_before_cutoff(dry_run=True)