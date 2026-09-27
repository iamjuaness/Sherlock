"""Audit Logging Service for Sherlock Admin Panel."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.core.domain import AdminAuditLog
from src.schemas.admin import AuditLogCreate, AuditLogOut


def log_admin_action(
    db: Session,
    action: str,
    target_table: Optional[str] = None,
    record_id: Optional[str] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    admin_user: Optional[str] = "admin",
    origin: Optional[str] = "web_admin",
    status: str = "success",
    error_message: Optional[str] = None,
) -> AdminAuditLog:
    """Log an administrative action safely into DB."""
    try:
        old_json = json.dumps(old_values, ensure_ascii=False, default=str) if old_values is not None else None
        new_json = json.dumps(new_values, ensure_ascii=False, default=str) if new_values is not None else None

        log_entry = AdminAuditLog(
            timestamp=datetime.utcnow(),
            admin_user=admin_user,
            action=action,
            target_table=target_table,
            record_id=str(record_id) if record_id else None,
            old_values=old_json,
            new_values=new_json,
            origin=origin,
            status=status,
            error_message=error_message,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        db.rollback()
        # Fallback log creation in case transaction error occurred
        log_entry = AdminAuditLog(
            timestamp=datetime.utcnow(),
            admin_user=admin_user,
            action=action,
            target_table=target_table,
            record_id=str(record_id) if record_id else None,
            origin=origin,
            status="error",
            error_message=f"Logging error: {str(e)}",
        )
        try:
            db.add(log_entry)
            db.commit()
        except Exception:
            db.rollback()
        return log_entry


def get_audit_logs(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    action: Optional[str] = None,
    target_table: Optional[str] = None,
    record_id: Optional[str] = None,
) -> List[AdminAuditLog]:
    """Retrieve audit logs with optional filtering."""
    query = db.query(AdminAuditLog)

    if action:
        query = query.filter(AdminAuditLog.action == action)
    if target_table:
        query = query.filter(AdminAuditLog.target_table == target_table)
    if record_id:
        query = query.filter(AdminAuditLog.record_id == record_id)

    query = query.order_by(desc(AdminAuditLog.timestamp))
    offset = (page - 1) * page_size
    return query.offset(offset).limit(page_size).all()
