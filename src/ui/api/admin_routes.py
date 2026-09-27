"""FastAPI router for Sherlock Admin Panel API & HTML Page Views."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.schemas.admin import (
    DashboardSummaryOut,
    PickItemOut,
    PickDetailOut,
    PaginationMeta,
    OperationalFieldsUpdate,
    StatsGroupedOut,
    StatsAnomaliesOut,
    DatabaseTableInfo,
    DatabaseTableSchema,
    DatabaseRowsOut,
    DatabaseRowUpdate,
    AuditLogOut,
)
from src.services.admin_picks_service import (
    query_picks,
    get_pick_detail,
    update_operational_fields,
    mark_for_recalculation,
    export_picks_file,
)
from src.services.admin_stats_service import (
    calculate_dashboard_summary,
    get_grouped_stats,
    detect_data_anomalies,
    export_stats_file,
)
from src.services.admin_database_service import (
    list_whitelisted_tables,
    get_table_schema,
    query_table_rows,
    update_table_row,
)
from src.services.admin_audit_service import get_audit_logs

admin_router = APIRouter(tags=["Admin Panel"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
templates = Jinja2Templates(directory=os.path.join(WEB_DIR, "templates"))


def get_current_admin_role(request: Request) -> str:
    """Dependency to check admin role permissions (read-only vs admin)."""
    # Header or query param authorization check
    role = request.headers.get("X-Admin-Role") or request.query_params.get("admin_role") or "admin"
    return role.lower()


def require_admin_write(role: str = Depends(get_current_admin_role)) -> str:
    """Enforce write permissions for administrative mutations."""
    if role not in ("admin", "superuser", "write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes: Se requiere rol de Administrador para modificar datos.",
        )
    return role


# ---------------------------------------------------------------------------
# HTML Page Views
# ---------------------------------------------------------------------------

@admin_router.get("/admin", include_in_schema=False)
async def admin_root():
    """Redirect /admin to /admin/dashboard."""
    return RedirectResponse(url="/admin/dashboard", status_code=307)


@admin_router.get("/admin/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard_page(request: Request):
    """Render Admin Dashboard view."""
    return templates.TemplateResponse(request=request, name="admin_panel.html", context={"active_tab": "dashboard", "embedded_in_admin": True, "css_version": "1", "js_version": "1"})


@admin_router.get("/admin/picks", response_class=HTMLResponse, include_in_schema=False)
async def admin_picks_page(request: Request):
    """Render Picks Explorer view."""
    return templates.TemplateResponse(request=request, name="admin_panel.html", context={"active_tab": "picks", "embedded_in_admin": True, "css_version": "1", "js_version": "1"})


@admin_router.get("/admin/stats", response_class=HTMLResponse, include_in_schema=False)
async def admin_stats_page(request: Request):
    """Render Advanced Analytics view."""
    return templates.TemplateResponse(request=request, name="admin_panel.html", context={"active_tab": "stats", "embedded_in_admin": True, "css_version": "1", "js_version": "1"})


@admin_router.get("/admin/database", response_class=HTMLResponse, include_in_schema=False)
async def admin_database_page(request: Request):
    """Render Database Explorer view."""
    return templates.TemplateResponse(request=request, name="admin_panel.html", context={"active_tab": "database", "embedded_in_admin": True, "css_version": "1", "js_version": "1"})



# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

# ── Dashboard API ──

@admin_router.get("/api/v1/admin/dashboard/summary", response_model=DashboardSummaryOut)
def get_admin_dashboard_summary(
    date_range: Optional[str] = Query(None, description="Preset date range (today, 3d, 7d, 30d, all)"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    competition: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    bookmaker: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    count_in_profitability: Optional[bool] = Query(None),
    is_blacklisted: Optional[bool] = Query(None),
    is_value: Optional[bool] = Query(None),
    is_publishable: Optional[bool] = Query(None),
    is_underdog: Optional[bool] = Query(None),
    min_sample: int = Query(10, ge=1),
    db: Session = Depends(get_db),
):
    return calculate_dashboard_summary(
        db=db,
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
        competition=competition,
        market=market,
        category=category,
        bookmaker=bookmaker,
        status=status_filter,
        count_in_profitability=count_in_profitability,
        is_blacklisted=is_blacklisted,
        is_value=is_value,
        is_publishable=is_publishable,
        is_underdog=is_underdog,
        min_sample=min_sample,
    )


# ── Picks API ──

@admin_router.get("/api/v1/admin/picks")
def get_admin_picks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    competition: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    bookmaker: Optional[str] = Query(None),
    min_odds: Optional[float] = Query(None),
    max_odds: Optional[float] = Query(None),
    min_edge: Optional[float] = Query(None),
    max_edge: Optional[float] = Query(None),
    only_resolved: bool = Query(False),
    only_pending: bool = Query(False),
    count_in_profitability: Optional[bool] = Query(None),
    needs_recalc: Optional[bool] = Query(None),
    is_blacklisted: Optional[bool] = Query(None),
    is_value: Optional[bool] = Query(None),
    is_publishable: Optional[bool] = Query(None),
    is_underdog: Optional[bool] = Query(None),
    filter_correlated: bool = Query(True),
    sort_by: str = Query("match_date"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
):
    picks, meta = query_picks(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        date_from=date_from,
        date_to=date_to,
        competition=competition,
        team=team,
        market=market,
        status=status_filter,
        category=category,
        bookmaker=bookmaker,
        min_odds=min_odds,
        max_odds=max_odds,
        min_edge=min_edge,
        max_edge=max_edge,
        only_resolved=only_resolved,
        only_pending=only_pending,
        count_in_profitability=count_in_profitability,
        needs_recalc=needs_recalc,
        is_blacklisted=is_blacklisted,
        is_value=is_value,
        is_publishable=is_publishable,
        is_underdog=is_underdog,
        filter_correlated=filter_correlated,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return {"picks": picks, "pagination": meta}


@admin_router.get("/api/v1/admin/picks/export")
def export_admin_picks(
    export_format: str = Query("excel"),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    competition: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    bookmaker: Optional[str] = Query(None),
    min_odds: Optional[float] = Query(None),
    max_odds: Optional[float] = Query(None),
    min_edge: Optional[float] = Query(None),
    max_edge: Optional[float] = Query(None),
    only_resolved: bool = Query(False),
    only_pending: bool = Query(False),
    count_in_profitability: Optional[bool] = Query(None),
    needs_recalc: Optional[bool] = Query(None),
    is_blacklisted: Optional[bool] = Query(None),
    is_value: Optional[bool] = Query(None),
    is_publishable: Optional[bool] = Query(None),
    is_underdog: Optional[bool] = Query(None),
    sort_by: str = Query("match_date"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
):
    content, mime_type, filename = export_picks_file(
        db=db,
        export_format=export_format,
        search=search,
        date_from=date_from,
        date_to=date_to,
        competition=competition,
        team=team,
        market=market,
        status=status_filter,
        category=category,
        bookmaker=bookmaker,
        min_odds=min_odds,
        max_odds=max_odds,
        min_edge=min_edge,
        max_edge=max_edge,
        only_resolved=only_resolved,
        only_pending=only_pending,
        count_in_profitability=count_in_profitability,
        needs_recalc=needs_recalc,
        is_blacklisted=is_blacklisted,
        is_value=is_value,
        is_publishable=is_publishable,
        is_underdog=is_underdog,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_router.get("/api/v1/admin/picks/{analysis_id}", response_model=PickDetailOut)
def get_admin_pick_detail(analysis_id: str, db: Session = Depends(get_db)):
    detail = get_pick_detail(db, analysis_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Pick no encontrado.")
    return detail


@admin_router.post("/api/v1/admin/picks/{analysis_id}/mark-for-recalculation")
def admin_mark_recalculation(
    analysis_id: str,
    db: Session = Depends(get_db),
    role: str = Depends(require_admin_write),
):
    success = mark_for_recalculation(db, analysis_id, admin_user=role)
    if not success:
        raise HTTPException(status_code=404, detail="Pick no encontrado.")
    return {"status": "success", "message": "Registro marcado para recálculo exitosamente."}


@admin_router.patch("/api/v1/admin/picks/{analysis_id}/operational-fields")
def admin_update_pick_operational(
    analysis_id: str,
    payload: OperationalFieldsUpdate,
    db: Session = Depends(get_db),
    role: str = Depends(require_admin_write),
):
    updated = update_operational_fields(db, analysis_id, payload, admin_user=role)
    if not updated:
        raise HTTPException(status_code=404, detail="Pick no encontrado.")
    return {"status": "success", "message": "Campos operativos actualizados exitosamente."}


# ── Stats API ──

@admin_router.get("/api/v1/admin/stats/grouped", response_model=StatsGroupedOut)
def get_admin_stats_grouped(
    group_by: str = Query("competition"),
    min_sample: int = Query(1, ge=1),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return get_grouped_stats(db, group_by=group_by, min_sample=min_sample, date_from=date_from, date_to=date_to)


@admin_router.get("/api/v1/admin/stats/anomalies", response_model=StatsAnomaliesOut)
def get_admin_stats_anomalies(db: Session = Depends(get_db)):
    return detect_data_anomalies(db)


@admin_router.get("/api/v1/admin/stats/export")
def export_admin_stats(
    export_format: str = Query("csv"),
    group_by: str = Query("competition"),
    db: Session = Depends(get_db),
):
    content, mime_type, filename = export_stats_file(db, export_format=export_format, group_by=group_by)
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Database Explorer API ──

@admin_router.get("/api/v1/admin/database/tables", response_model=List[DatabaseTableInfo])
def get_admin_database_tables(db: Session = Depends(get_db)):
    return list_whitelisted_tables(db)


@admin_router.get("/api/v1/admin/database/tables/{table_name}/schema", response_model=DatabaseTableSchema)
def get_admin_database_schema(table_name: str, db: Session = Depends(get_db)):
    return get_table_schema(db, table_name)


@admin_router.get("/api/v1/admin/database/tables/{table_name}/rows", response_model=DatabaseRowsOut)
def get_admin_database_rows(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
):
    return query_table_rows(
        db=db,
        table_name=table_name,
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@admin_router.patch("/api/v1/admin/database/tables/{table_name}/rows/{record_id}")
def update_admin_database_row(
    table_name: str,
    record_id: str,
    payload: DatabaseRowUpdate,
    db: Session = Depends(get_db),
    role: str = Depends(require_admin_write),
):
    updated = update_table_row(db, table_name=table_name, record_id=record_id, update_payload=payload, admin_user=role)
    return {"status": "success", "record": updated}


# ── Audit Log API ──

@admin_router.get("/api/v1/admin/audit-log", response_model=List[AuditLogOut])
def get_admin_audit_logs_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(50),
    action: Optional[str] = Query(None),
    target_table: Optional[str] = Query(None),
    record_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return get_audit_logs(
        db=db,
        page=page,
        page_size=page_size,
        action=action,
        target_table=target_table,
        record_id=record_id,
    )
