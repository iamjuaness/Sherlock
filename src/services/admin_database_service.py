"""Service for Database Explorer & Controlled Admin Mutations in Sherlock Admin Panel."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text, Table, MetaData, select, func, or_
from fastapi import HTTPException, status

from src.core.database import engine, Base
from src.core.domain import (
    AnalysisHistory,
    Competition,
    Team,
    Match,
    Player,
    BettingLine,
    StatLineTeam,
    StatLinePlayer,
    AdminAuditLog,
)
from src.schemas.admin import (
    DatabaseTableInfo,
    DatabaseTableSchema,
    ColumnSchemaInfo,
    DatabaseRowsOut,
    PaginationMeta,
    DatabaseRowUpdate,
)
from src.services.admin_audit_service import log_admin_action


# Whitelist of allowed database tables
WHITELISTED_TABLES: Dict[str, Tuple[Any, str]] = {
    "analysis_history": (AnalysisHistory, "Histórico de análisis, picks, estadísticas y resultados finales de partidos."),
    "competitions": (Competition, "Competiciones, ligas y torneos registrados."),
    "teams": (Team, "Equipos de fútbol y entidades deportivas."),
    "matches": (Match, "Partidos y encuentros deportivos programados/finalizados."),
    "players": (Player, "Jugadores individuales asociados a equipos."),
    "betting_lines": (BettingLine, "Líneas de apuestas y cuotas de mercado por partido."),
    "stat_lines_team": (StatLineTeam, "Estadísticas agregadas por equipo por partido."),
    "stat_lines_player": (StatLinePlayer, "Estadísticas individuales de jugadores por partido."),
    "admin_audit_log": (AdminAuditLog, "Registro de auditoría de acciones administrativas."),
}

# Whitelist of allowed editable columns per table
EDITABLE_COLUMNS: Dict[str, List[str]] = {
    "analysis_history": [
        "match_date",
        "competition",
        "bookmaker",
        "stake_units",
        "count_in_profitability",
        "needs_recalc",
        "has_odds",
        "needs_reanalysis",
    ],
    "competitions": ["name", "country", "season"],
    "teams": ["name", "short_name", "country", "logo_url"],
    "matches": ["match_date", "status", "venue", "round", "home_score", "away_score"],
    "players": ["name", "position", "nationality"],
    "betting_lines": ["odds", "bookmaker", "line"],
    "stat_lines_team": ["shots", "shots_on_target", "possession", "fouls", "corners", "yellow_cards", "red_cards"],
    "stat_lines_player": ["minutes_played", "goals", "assists"],
    "admin_audit_log": [], # Read-only!
}

# Default search text columns per table
SEARCHABLE_COLUMNS: Dict[str, List[str]] = {
    "analysis_history": ["match_title", "competition", "bookmaker", "sport"],
    "competitions": ["name", "country", "season"],
    "teams": ["name", "short_name", "country"],
    "matches": ["status", "venue", "round"],
    "players": ["name", "position", "nationality"],
    "betting_lines": ["market_type", "selection", "bookmaker"],
    "stat_lines_team": [],
    "stat_lines_player": [],
    "admin_audit_log": ["action", "target_table", "record_id", "admin_user", "status"],
}


def list_whitelisted_tables(db: Session) -> List[DatabaseTableInfo]:
    """Return overview of all whitelisted tables with approximate record counts."""
    tables = []
    inspector = inspect(engine)
    has_tables = set(inspector.get_table_names()) if engine else set()

    for tbl_name, (model_cls, desc) in WHITELISTED_TABLES.items():
        try:
            cnt = db.query(func.count()).select_from(model_cls).scalar() or 0
        except Exception:
            cnt = 0

        if tbl_name in has_tables:
            try:
                cols_cnt = len(inspector.get_columns(tbl_name))
            except Exception:
                cols_cnt = len(inspect(model_cls).mapper.column_attrs)
        else:
            cols_cnt = len(inspect(model_cls).mapper.column_attrs)

        tables.append(
            DatabaseTableInfo(
                name=tbl_name,
                approx_rows=cnt,
                description=desc,
                columns_count=cols_cnt,
            )
        )
    return tables


def get_table_schema(db: Session, table_name: str) -> DatabaseTableSchema:
    """Return column definitions and schema information for a whitelisted table."""
    if table_name not in WHITELISTED_TABLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tabla '{table_name}' no está en la lista blanca de tablas permitidas.",
        )

    model_cls, desc = WHITELISTED_TABLES[table_name]
    inspector = inspect(engine)
    has_tables = set(inspector.get_table_names()) if engine else set()

    if table_name in has_tables:
        try:
            cols_meta = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = pk_constraint.get("constrained_columns", []) if pk_constraint else []
            fk_constraints = inspector.get_foreign_keys(table_name)
            indexes = inspector.get_indexes(table_name)
        except Exception:
            cols_meta = []
            pk_cols = ["id"]
            fk_constraints = []
            indexes = []
    else:
        cols_meta = []
        pk_cols = ["id"]
        fk_constraints = []
        indexes = []

    fk_map = {}
    for fk in fk_constraints:
        for local_c, remote_c in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
            fk_map[local_c] = f"{fk.get('referred_table')}.{remote_c}"

    indexed_cols = set()
    for idx in indexes:
        for c in idx.get("column_names", []):
            indexed_cols.add(c)

    editable_set = set(EDITABLE_COLUMNS.get(table_name, []))

    columns_info = []
    if cols_meta:
        for c in cols_meta:
            col_name = c["name"]
            columns_info.append(
                ColumnSchemaInfo(
                    name=col_name,
                    type=str(c["type"]),
                    nullable=c.get("nullable", True),
                    primary_key=(col_name in pk_cols),
                    default_value=str(c.get("default")) if c.get("default") is not None else None,
                    is_foreign_key=(col_name in fk_map),
                    foreign_target=fk_map.get(col_name),
                    is_indexed=(col_name in indexed_cols),
                    description="Editable" if col_name in editable_set else ("Primary Key (Bloqueado)" if col_name in pk_cols else "Solo Lectura"),
                )
            )
    else:
        # Fallback to SQLAlchemy ORM mapper attributes
        orm_mapper = inspect(model_cls)
        for col_attr in orm_mapper.column_attrs:
            col = col_attr.columns[0]
            col_name = col.name
            columns_info.append(
                ColumnSchemaInfo(
                    name=col_name,
                    type=str(col.type),
                    nullable=col.nullable if col.nullable is not None else True,
                    primary_key=col.primary_key,
                    default_value=str(col.default) if col.default is not None else None,
                    is_foreign_key=bool(col.foreign_keys),
                    foreign_target=None,
                    is_indexed=col.index or False,
                    description="Editable" if col_name in editable_set else ("Primary Key (Bloqueado)" if col.primary_key else "Solo Lectura"),
                )
            )

    try:
        approx_rows = db.query(func.count()).select_from(model_cls).scalar() or 0
    except Exception:
        approx_rows = 0

    return DatabaseTableSchema(
        table_name=table_name,
        description=desc,
        approx_rows=approx_rows,
        columns=columns_info,
    )



def query_table_rows(
    db: Session,
    table_name: str,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: str = "desc",
    column_filters: Optional[Dict[str, Any]] = None,
) -> DatabaseRowsOut:
    """Safe, paginated query over whitelisted database tables."""
    if table_name not in WHITELISTED_TABLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tabla '{table_name}' no está en la lista blanca de tablas permitidas.",
        )

    model_cls, _ = WHITELISTED_TABLES[table_name]
    query = db.query(model_cls)

    # Search filter over defined searchable text columns
    if search:
        search_cols = SEARCHABLE_COLUMNS.get(table_name, [])
        if search_cols:
            or_conds = []
            s_pat = f"%{search.strip()}%"
            for col_attr in search_cols:
                if hasattr(model_cls, col_attr):
                    or_conds.append(getattr(model_cls, col_attr).ilike(s_pat))
            if or_conds:
                query = query.filter(or_(*or_conds))

    # Apply column filters if provided
    if column_filters:
        for col_name, val in column_filters.items():
            if hasattr(model_cls, col_name) and val is not None:
                query = query.filter(getattr(model_cls, col_name) == val)

    # Validate sort column
    if sort_by and hasattr(model_cls, sort_by):
        sort_attr = getattr(model_cls, sort_by)
        if sort_dir.lower() == "asc":
            query = query.order_by(sort_attr.asc())
        else:
            query = query.order_by(sort_attr.desc())
    else:
        # Default order by primary key or id
        if hasattr(model_cls, "id"):
            query = query.order_by(model_cls.id.desc())

    total_records = query.count()

    allowed_page_sizes = [50, 100, 1000, 10000]
    if page_size not in allowed_page_sizes:
        page_size = 50

    warning_msg = None
    if page_size >= 1000:
        warning_msg = f"Cargando {page_size} registros de la base de datos. Esta operación puede demorar."

    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()

    # Convert ORM instances to dicts safely
    rows = []
    inspector = inspect(model_cls)
    col_names = [c.key for c in inspector.mapper.column_attrs]

    for r in records:
        row_dict = {}
        for c in col_names:
            val = getattr(r, c)
            if isinstance(val, datetime):
                row_dict[c] = val.isoformat()
            else:
                row_dict[c] = val
        rows.append(row_dict)

    schema_info = get_table_schema(db, table_name)

    total_pages = max(1, (total_records + page_size - 1) // page_size)
    meta = PaginationMeta(
        page=page,
        page_size=page_size,
        total_records=total_records,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
        warning=warning_msg,
    )

    return DatabaseRowsOut(
        table_name=table_name,
        columns=schema_info.columns,
        rows=rows,
        pagination=meta,
    )


def update_table_row(
    db: Session,
    table_name: str,
    record_id: str,
    update_payload: DatabaseRowUpdate,
    admin_user: str = "admin",
) -> Dict[str, Any]:
    """Controlled, safe update of a record in a whitelisted table."""
    if table_name not in WHITELISTED_TABLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tabla '{table_name}' no está en la lista blanca de tablas permitidas.",
        )

    allowed_cols = set(EDITABLE_COLUMNS.get(table_name, []))
    if not allowed_cols:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"La tabla '{table_name}' es de solo lectura y no permite modificaciones directas.",
        )

    # Validate that requested edit columns are strictly in whitelist
    for col_name in update_payload.updates.keys():
        if col_name not in allowed_cols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No está permitido editar la columna '{col_name}' en la tabla '{table_name}'. Columnas editables: {sorted(list(allowed_cols))}",
            )

    model_cls, _ = WHITELISTED_TABLES[table_name]
    record = db.query(model_cls).filter(model_cls.id == record_id).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_444_NOT_FOUND if hasattr(status, "HTTP_444_NOT_FOUND") else 404,
            detail=f"Registro con ID '{record_id}' no encontrado en la tabla '{table_name}'.",
        )

    old_vals = {}
    new_vals = {}

    for col_name, new_val in update_payload.updates.items():
        if hasattr(record, col_name):
            old_vals[col_name] = getattr(record, col_name)
            # Parse datetime fields if string is passed
            if ("date" in col_name.lower() or "time" in col_name.lower()) and isinstance(new_val, str) and new_val.strip():
                try:
                    parsed_dt = datetime.fromisoformat(new_val.strip())
                    setattr(record, col_name, parsed_dt)
                    new_vals[col_name] = parsed_dt.isoformat()
                    continue
                except Exception:
                    pass
            setattr(record, col_name, new_val)
            new_vals[col_name] = new_val

    db.commit()
    db.refresh(record)

    log_admin_action(
        db,
        action="database_row_edit",
        target_table=table_name,
        record_id=record_id,
        old_values=old_vals,
        new_values=new_vals,
        admin_user=admin_user,
    )

    inspector = inspect(model_cls)
    col_names = [c.key for c in inspector.mapper.column_attrs]
    updated_dict = {}
    for c in col_names:
        val = getattr(record, c)
        updated_dict[c] = val.isoformat() if isinstance(val, datetime) else val

    return updated_dict
