"""Pydantic schemas for Sherlock Admin Panel."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Base & Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_records: int
    total_pages: int
    has_next: bool
    has_prev: bool
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditLogOut(BaseModel):
    id: str
    timestamp: datetime
    admin_user: Optional[str] = None
    action: str
    target_table: Optional[str] = None
    record_id: Optional[str] = None
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    origin: Optional[str] = None
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogCreate(BaseModel):
    admin_user: Optional[str] = "admin"
    action: str
    target_table: Optional[str] = None
    record_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    origin: Optional[str] = "web_admin"
    status: str = "success"
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Dashboard KPIs & Charts
# ---------------------------------------------------------------------------

class DashboardKPIs(BaseModel):
    total_analyses: int
    total_picks: int
    picks_resolved: int
    picks_pending: int
    picks_won: int
    picks_lost: int
    picks_push: int
    picks_void: int
    hit_rate: float          # won / picks_resolved_valid
    roi: float               # (net_profit / units_staked) * 100
    net_profit: float        # Sum profit/loss in units
    units_staked: float      # Sum stakes
    avg_odds: float          # Average odds of picks
    avg_winning_odds: float  # Average odds of winning picks
    break_even_rate: float   # (1 / avg_odds) * 100
    avg_edge: float          # Average model edge
    yield_rate: float        # Equal to ROI
    avg_kelly: float         # Average Kelly fraction
    clv: Optional[float] = None


class CalibrationBand(BaseModel):
    band: str                # e.g., "50-55%", "55-60%", "60-65%", "65-70%", "70%+"
    total_picks: int
    avg_model_prob: float
    actual_hit_rate: float
    diff: float


class ModelQualityMetrics(BaseModel):
    avg_model_prob: float
    avg_implied_prob: float
    avg_edge: float
    actual_vs_expected_diff: float
    brier_score: Optional[float] = None
    calibration_bands: List[CalibrationBand] = Field(default_factory=list)


class ChartDataPoint(BaseModel):
    label: str
    value: float
    extra: Optional[Dict[str, Any]] = None


class AccumulatedYieldPoint(BaseModel):
    date: str
    profit: float
    cumulative_profit: float
    picks_count: int


class DashboardChartsData(BaseModel):
    cumulative_yield: List[AccumulatedYieldPoint] = Field(default_factory=list)
    roi_by_league: List[ChartDataPoint] = Field(default_factory=list)
    roi_by_market: List[ChartDataPoint] = Field(default_factory=list)
    roi_by_team: List[ChartDataPoint] = Field(default_factory=list)
    performance_by_odds_range: List[ChartDataPoint] = Field(default_factory=list)
    performance_by_edge_range: List[ChartDataPoint] = Field(default_factory=list)
    outcome_distribution: Dict[str, int] = Field(default_factory=dict)
    expected_vs_actual_calibration: List[CalibrationBand] = Field(default_factory=list)


class DashboardSummaryOut(BaseModel):
    kpis: DashboardKPIs
    quality: ModelQualityMetrics
    charts: DashboardChartsData


# ---------------------------------------------------------------------------
# Picks Explorer
# ---------------------------------------------------------------------------

class PickItemOut(BaseModel):
    id: str                   # Analysis ID or Pick synthetic ID
    analysis_id: str
    match_date: Optional[datetime]
    match_title: str
    competition: Optional[str]
    market: str
    selection: str
    status: str               # pending, won, lost, push, void, cancelled
    odds: float
    model_prob: float
    calibrated_prob: Optional[float] = None
    implied_prob: float
    edge: float
    kelly: float
    stake: float
    profit: float
    roi: Optional[float] = None
    category: Optional[str] = "Normal"
    bookmaker: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    count_in_profitability: bool = True
    needs_recalc: bool = False
    is_blacklisted: bool = False
    is_value: bool = False
    is_publishable: bool = False
    is_underdog: bool = False


class PickDetailOut(BaseModel):
    pick: PickItemOut
    analysis: Dict[str, Any]
    predictive_context: Dict[str, Any]
    pre_match_evidence: Dict[str, Any]
    post_match_audit: Dict[str, Any]


class OperationalFieldsUpdate(BaseModel):
    competition: Optional[str] = None
    bookmaker: Optional[str] = None
    stake_units: Optional[float] = None
    count_in_profitability: Optional[bool] = None
    needs_recalc: Optional[bool] = None


# ---------------------------------------------------------------------------
# Advanced Stats
# ---------------------------------------------------------------------------

class GroupedStatItem(BaseModel):
    segment_name: str
    total_picks: int
    resolved_picks: int
    pending_picks: int
    won_picks: int
    lost_picks: int
    push_picks: int
    void_picks: int
    hit_rate: float
    avg_odds: float
    avg_winning_odds: float
    total_stake: float
    avg_stake: float
    net_profit: float
    roi: float
    yield_rate: float
    break_even_rate: float
    avg_edge: float
    avg_kelly: float
    avg_model_prob: float
    avg_implied_prob: float
    actual_vs_model_diff: float
    max_drawdown: float
    max_losing_streak: int
    max_winning_streak: int


class StatsGroupedOut(BaseModel):
    group_by: str
    min_sample: int
    items: List[GroupedStatItem]


class DataAnomalyItem(BaseModel):
    analysis_id: str
    match_title: str
    competition: Optional[str]
    anomaly_type: str
    description: str
    severity: str             # low, medium, high


class StatsAnomaliesOut(BaseModel):
    total_anomalies: int
    anomalies: List[DataAnomalyItem]


# ---------------------------------------------------------------------------
# Database Explorer
# ---------------------------------------------------------------------------

class ColumnSchemaInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default_value: Optional[str] = None
    is_foreign_key: bool = False
    foreign_target: Optional[str] = None
    is_indexed: bool = False
    description: Optional[str] = None


class DatabaseTableInfo(BaseModel):
    name: str
    approx_rows: int
    description: str
    columns_count: int


class DatabaseTableSchema(BaseModel):
    table_name: str
    description: str
    approx_rows: int
    columns: List[ColumnSchemaInfo]


class DatabaseRowsOut(BaseModel):
    table_name: str
    columns: List[ColumnSchemaInfo]
    rows: List[Dict[str, Any]]
    pagination: PaginationMeta


class DatabaseRowUpdate(BaseModel):
    updates: Dict[str, Any]
    reason: Optional[str] = None
