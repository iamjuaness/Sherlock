"""
Script de evaluación OOF comparativa (Fase 16).

Genera un reporte antes/después sobre el histórico disponible comparando:
  A. Sistema antiguo (calibrador global)
  B. Sistema nuevo sin bloqueos temporales
  C. Sistema nuevo con reliability, market blend y governance

La comparación es walk-forward temporal, nunca mezcla aleatoria.

Uso:
    # Desde la DB (por defecto):
    python scripts/evaluate_oof_comparison.py --output reports/oof_comparison.json

    # Desde CSV (fallback explícito):
    python scripts/evaluate_oof_comparison.py \
        --data data/historical_picks.csv \
        --output reports/oof_comparison.json \
        --n-folds 5
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Añadir el root del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.calibration import (
    HierarchicalCalibrator,
    CalibrationSample,
    walk_forward_calibrate,
)
from src.domain.market_taxonomy import line_bucket_for, normalize_market_family, normalize_market_side


# ???????????????????????????????????????????????????????????????????????????
# Métricas comparativas
# ???????????????????????????????????????????????????????????????????????????

@dataclass
class SystemMetrics:
    """Métricas de un sistema en un fold o globales."""

    system_name: str
    n_picks: int
    n_settled: int
    hit_rate: float
    roi: float
    yield_pct: float
    profit: float
    staked: float
    avg_odds: float
    brier_score: float
    log_loss: float
    ece: float
    avg_clv: Optional[float]
    max_drawdown: float
    avg_drawdown: float
    segments: Dict[str, Dict]


@dataclass
class ComparisonReport:
    """Reporte comparativo completo de los tres sistemas."""

    timestamp: str
    n_folds: int
    data_source: str
    system_a: SystemMetrics   # Sistema antiguo
    system_b: SystemMetrics   # Nuevo sin bloqueos
    system_c: SystemMetrics   # Nuevo con governance + reliability

    # Deltas (C vs A)
    delta_roi: float
    delta_brier: float
    delta_log_loss: float
    delta_n_picks: int

    warnings: List[str]

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "n_folds": self.n_folds,
            "data_source": self.data_source,
            "system_a": asdict(self.system_a),
            "system_b": asdict(self.system_b),
            "system_c": asdict(self.system_c),
            "delta_roi_c_vs_a": round(self.delta_roi * 100, 2),
            "delta_brier_c_vs_a": round(self.delta_brier, 6),
            "delta_log_loss_c_vs_a": round(self.delta_log_loss, 6),
            "delta_n_picks_c_vs_a": self.delta_n_picks,
            "warnings": self.warnings,
        }


# ???????????????????????????????????????????????????????????????????????????
# Carga de datos
# ???????????????????????????????????????????????????????????????????????????

def load_historical_picks_from_db(
    db_url: Optional[str] = None,
    count_in_profitability_only: bool = True,
) -> Tuple[List[Dict], List[str]]:
    """
    Carga picks históricos directamente desde la base de datos SQLite.

    Lee `analysis_history` + `picks_calculados` y devuelve la misma
    estructura de dict que `load_historical_picks()` para que el resto
    del pipeline no cambie.

    Retorna (picks, warnings).
    """
    import json as _json
    import os
    from datetime import datetime, timezone

    warnings: List[str] = []
    picks: List[Dict] = []

    # Resolver DATABASE_URL
    if db_url is None:
        db_url = os.environ.get("DATABASE_URL", "sqlite:///data/sherlock.db")

    try:
        from sqlalchemy import create_engine, text as sa_text
        from sqlalchemy.orm import sessionmaker
    except ImportError:
        raise RuntimeError("sqlalchemy no está instalado")

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        query = "SELECT id, date, match_date, competition, picks_calculados, "\
                "final_score_home, final_score_away, stake_units, count_in_profitability "\
                "FROM analysis_history "\
                "WHERE picks_calculados IS NOT NULL AND picks_calculados != '[]'"
        if count_in_profitability_only:
            query += " AND count_in_profitability = 1"
        query += " ORDER BY COALESCE(match_date, date) ASC"

        rows = session.execute(sa_text(query)).fetchall()
    finally:
        session.close()

    for row in rows:
        (
            ah_id, date_raw, match_date_raw, competition,
            picks_json, score_home, score_away, stake_units,
            _count_in_prof,
        ) = row

        # Determinar timestamp del partido
        ts_raw = match_date_raw or date_raw
        if ts_raw is None:
            continue
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
            except ValueError:
                warnings.append(f"[{ah_id}] fecha inválida: {ts_raw!r}")
                continue
        else:
            ts = ts_raw  # ya es datetime

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Parsear picks_calculados
        try:
            parsed = _json.loads(picks_json)
        except Exception as exc:
            warnings.append(f"[{ah_id}] JSON inválido en picks_calculados: {exc}")
            continue

        if isinstance(parsed, dict):
            raw_picks = parsed.get("picks", [])
        elif isinstance(parsed, list):
            raw_picks = parsed
        else:
            continue

        has_result = score_home is not None and score_away is not None

        for idx, p in enumerate(raw_picks):
            if not isinstance(p, dict):
                continue

            # Filtrar picks sin valor
            if p.get("rating") == "? NO VALUE":
                continue
            if p.get("is_blacklisted") or p.get("is_rule_blocked"):
                continue
            # Sólo picks publicables
            is_pub = bool(
                p.get("is_publishable")
                or p.get("is_underdog")
                or p.get("is_value")
            )
            if not is_pub:
                continue

            # Odds
            odds_raw = p.get("odds") or p.get("cuota")
            try:
                odds = float(odds_raw) if odds_raw is not None else None
            except (ValueError, TypeError):
                odds = None

            # Probabilidad del modelo
            raw_prob = float(p.get("model_prob") or p.get("probability") or p.get("prob") or 0.0)
            if raw_prob > 1.0:
                model_prob = raw_prob / 100.0 if raw_prob <= 100.0 else 0.5
                while model_prob > 1.0:
                    model_prob /= 10.0
            else:
                model_prob = max(0.0, raw_prob)
            if model_prob == 0.0:
                model_prob = None

            # Stake
            stake = float(p.get("stake_units") or p.get("stake") or stake_units or 0.02)

            # Mercado (para taxonomy)
            market = p.get("market") or p.get("market_type") or p.get("market_name") or ""
            selection = (
                p.get("selection") or p.get("pick") or
                p.get("name") or p.get("pick_name") or ""
            )
            market_raw = f"{market} {selection}".strip() if selection else market

            # Resultado (settlement)
            succ = p.get("success") or p.get("status") or p.get("resultado") or p.get("result")

            if succ is None and has_result:
                try:
                    from src.ui.api.main import _check_pick_success
                    res_dict = {
                        "final_score_home": score_home,
                        "final_score_away": score_away,
                    }
                    succ = _check_pick_success(p, res_dict)
                except Exception:
                    succ = None

            if succ is True or str(succ).lower() in ("won", "ganada", "ganado", "win", "hit", "1"):
                result = 1.0
            elif succ is False or str(succ).lower() in ("lost", "perdida", "perdido", "loss", "miss", "0"):
                result = 0.0
            elif str(succ).lower() in ("half_win", "half_won"):
                result = 0.5  # tratar como semi-win para métricas
            else:
                result = None  # pendiente / push / cancelado

            picks.append({
                "timestamp": ts,
                "league": competition or "unknown",
                "market_raw": market_raw,
                "odds": odds,
                "result": result,
                "model_prob": model_prob,
                "stake": stake,
                "close_odds": None,
                "open_odds": odds,
                "analysis_id": ah_id,
            })

    picks.sort(key=lambda p: p["timestamp"])
    return picks, warnings


def load_historical_picks(csv_path: str) -> Tuple[List[Dict], List[str]]:
    """
    Carga picks históricos desde CSV (fallback).

    Columnas esperadas (mínimas):
        date, league, market_raw, odds, result (1=win, 0=loss, push/pending=None),
        model_prob, stake

    Retorna (picks, warnings).
    """
    import csv
    from datetime import datetime

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró: {csv_path}")

    picks = []
    warnings = []

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                date_raw = row.get("date", "")
                try:
                    ts = datetime.fromisoformat(date_raw)
                except ValueError:
                    ts = datetime.strptime(date_raw, "%Y-%m-%d")

                result_raw = row.get("result", "").strip().lower()
                if result_raw in ("1", "win", "true"):
                    result = 1.0
                elif result_raw in ("0", "loss", "false"):
                    result = 0.0
                else:
                    result = None  # push o pendiente

                prob_raw = row.get("model_prob", "")
                prob = float(prob_raw) if prob_raw else None

                picks.append({
                    "timestamp": ts,
                    "league": row.get("league", "unknown").strip(),
                    "market_raw": row.get("market_raw", row.get("market", "")).strip(),
                    "odds": float(row["odds"]) if row.get("odds") else None,
                    "result": result,
                    "model_prob": prob,
                    "stake": float(row.get("stake", 0.02)),
                    "close_odds": float(row["close_odds"]) if row.get("close_odds") else None,
                    "open_odds": float(row["open_odds"]) if row.get("open_odds") else
                                 float(row["odds"]) if row.get("odds") else None,
                })
            except Exception as e:
                warnings.append(f"Fila {i+2}: {e}")

    picks.sort(key=lambda p: p["timestamp"])
    return picks, warnings


# ???????????????????????????????????????????????????????????????????????????
# Calculadores de métricas
# ???????????????????????????????????????????????????????????????????????????

def _safe_log(p: float, eps: float = 1e-9) -> float:
    return math.log(max(p, eps))


def compute_metrics(
    picks: List[Dict],
    probs: List[Optional[float]],
    system_name: str,
    filter_blocked: bool = False,
) -> SystemMetrics:
    """Calcula métricas para un conjunto de picks + probabilidades calibradas."""
    settled = []
    skipped = 0

    for p, prob in zip(picks, probs):
        if filter_blocked and p.get("blocked", False):
            skipped += 1
            continue
        if p["result"] is None or prob is None or p["odds"] is None:
            continue
        settled.append((p, prob))

    n_picks = len(picks) - skipped
    n_settled = len(settled)
    n_wins = sum(1 for p, _ in settled if p["result"] > 0.5)

    staked = sum(p.get("stake", 0.02) for p, _ in settled)
    profit = sum(
        p.get("stake", 0.02) * (p["odds"] - 1.0) if p["result"] > 0.5
        else -p.get("stake", 0.02)
        for p, _ in settled
    )

    hit_rate = n_wins / n_settled if n_settled > 0 else 0.0
    roi = profit / staked if staked > 0 else 0.0
    yield_pct = profit / n_settled if n_settled > 0 else 0.0

    odds_list = [p["odds"] for p, _ in settled]
    avg_odds = sum(odds_list) / len(odds_list) if odds_list else 0.0

    brier = sum((prob - p["result"]) ** 2 for p, prob in settled) / n_settled if n_settled else 0.0
    ll = -sum(
        p["result"] * _safe_log(prob) + (1.0 - p["result"]) * _safe_log(1.0 - prob)
        for p, prob in settled
    ) / n_settled if n_settled else 0.0

    # ECE (10 bins)
    ece = 0.0
    if settled:
        bins: List[list] = [[] for _ in range(10)]
        for p, prob in settled:
            idx = min(int(prob * 10), 9)
            bins[idx].append((prob, p["result"]))
        for b in bins:
            if b:
                ac = sum(o for _, o in b) / len(b)
                co = sum(pr for pr, _ in b) / len(b)
                ece += (len(b) / n_settled) * abs(co - ac)

    # CLV
    clv_values = []
    for p, _ in settled:
        if p.get("open_odds") and p.get("close_odds"):
            clv = ((p["open_odds"] / p["close_odds"]) - 1.0) * 100.0
            clv_values.append(clv)
    avg_clv = sum(clv_values) / len(clv_values) if clv_values else None

    # Drawdown por pick
    running_profit = 0.0
    peak = 0.0
    drawdowns = []
    for p, _ in settled:
        running_profit += (
            p.get("stake", 0.02) * (p["odds"] - 1.0)
            if p["result"] > 0.5
            else -p.get("stake", 0.02)
        )
        peak = max(peak, running_profit)
        drawdown = peak - running_profit
        drawdowns.append(drawdown)

    max_dd = max(drawdowns) if drawdowns else 0.0
    avg_dd = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0

    return SystemMetrics(
        system_name=system_name,
        n_picks=n_picks,
        n_settled=n_settled,
        hit_rate=hit_rate,
        roi=roi,
        yield_pct=yield_pct,
        profit=profit,
        staked=staked,
        avg_odds=avg_odds,
        brier_score=brier,
        log_loss=ll,
        ece=ece,
        avg_clv=avg_clv,
        max_drawdown=max_dd,
        avg_drawdown=avg_dd,
        segments={},
    )


# ???????????????????????????????????????????????????????????????????????????
# Main
# ???????????????????????????????????????????????????????????????????????????

def build_comparison_report(
    picks: List[Dict],
    n_folds: int = 5,
    governance_config: str = "data/segment_governance.json",
) -> ComparisonReport:
    """
    Construye el reporte comparativo A/B/C en modo walk-forward.

    A: Probabilidad cruda del modelo (sin calibrar)
    B: Calibración jerárquica sin bloqueos de governance
    C: Calibración + governance + reliability
    """
    from datetime import datetime, timezone
    from src.models.segment_governance import evaluate_segment_status, SegmentStatus

    # Construir CalibrationSamples
    samples = []
    for p in picks:
        prob = p.get("model_prob")
        result = p.get("result")
        if prob is None or result is None:
            continue

        market_raw = p.get("market_raw", "")
        try:
            from src.domain.market_taxonomy import parse_market
            mk = parse_market(market_raw)
            family = mk.family.value
            side = mk.side.value
            bucket = mk.line_bucket
        except Exception:
            family = "goals"
            side = "over"
            bucket = "core_2_5"

        samples.append(CalibrationSample(
            prob=prob,
            hit_value=result,
            market_family=family,
            side=side,
            line_bucket=bucket,
            league=p.get("league", "unknown"),
            timestamp=p["timestamp"].replace(tzinfo=timezone.utc)
            if p["timestamp"].tzinfo is None else p["timestamp"],
        ))

    # Walk-forward calibración
    oof_result = walk_forward_calibrate(samples, n_folds=n_folds, min_train=100)

    # Probables calibradas OOF
    calibrated_probs: List[Optional[float]] = [None] * len(picks)
    sample_idx = 0
    for i, p in enumerate(picks):
        if p.get("model_prob") is not None and p.get("result") is not None:
            if sample_idx < len(oof_result.calibrated_probs):
                calibrated_probs[i] = oof_result.calibrated_probs[sample_idx]
                sample_idx += 1

    # Sistema C: marcar bloqueados por governance
    picks_c = []
    for p, cal_p in zip(picks, calibrated_probs):
        pc = dict(p)
        if cal_p is not None:
            market_raw = p.get("market_raw", "")
            try:
                from src.domain.market_taxonomy import parse_market
                mk = parse_market(market_raw)
                family = mk.family.value
                side = mk.side.value
                bucket = mk.line_bucket
            except Exception:
                family = "goals"
                side = "over"
                bucket = "core_2_5"

            st = evaluate_segment_status(
                p.get("league"), family, side, bucket,
                effective_n=30,
                config_path=governance_config,
            )
            pc["blocked"] = st == SegmentStatus.BLOCKED
        picks_c.append(pc)

    raw_probs = [p.get("model_prob") for p in picks]

    system_a = compute_metrics(picks, raw_probs, "A: Modelo crudo (sin calibrar)")
    system_b = compute_metrics(picks, calibrated_probs, "B: Calibración jerárquica sin governance")
    system_c = compute_metrics(picks_c, calibrated_probs, "C: Con governance + reliability", filter_blocked=True)

    warnings = []
    if system_c.brier_score > system_a.brier_score:
        warnings.append("WARN: Brier OOF empeoró en sistema C vs A")
    if system_c.log_loss > system_a.log_loss:
        warnings.append("WARN: Log loss OOF empeoró en sistema C vs A")
    if system_c.roi < -0.05:
        warnings.append("WARN: ROI del sistema C es negativo (> -5%)")

    from datetime import datetime
    return ComparisonReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        n_folds=n_folds,
        data_source="historical_picks",
        system_a=system_a,
        system_b=system_b,
        system_c=system_c,
        delta_roi=system_c.roi - system_a.roi,
        delta_brier=system_c.brier_score - system_a.brier_score,
        delta_log_loss=system_c.log_loss - system_a.log_loss,
        delta_n_picks=system_c.n_picks - system_a.n_picks,
        warnings=warnings,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluación OOF comparativa A/B/C")
    parser.add_argument(
        "--data",
        default=None,
        help="Ruta a CSV de picks históricos. Si se omite, se lee desde la DB.",
    )
    parser.add_argument("--db-url", default=None, help="DATABASE_URL SQLAlchemy (override .env)")
    parser.add_argument("--output", default="reports/oof_comparison.json")
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--governance", default="data/segment_governance.json")
    parser.add_argument(
        "--all-picks",
        action="store_true",
        help="Incluir picks con count_in_profitability=0 (por defecto solo los contables).",
    )
    args = parser.parse_args()

    if args.data is not None:
        print(f"[CSV] Cargando datos desde: {args.data}...")
        picks, load_warnings = load_historical_picks(args.data)
    else:
        import os
        # Cargar .env si existe
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

        db_url = args.db_url or os.environ.get("DATABASE_URL", "sqlite:///data/sherlock.db")
        print(f"[DB] Cargando datos desde: {db_url}...")
        picks, load_warnings = load_historical_picks_from_db(
            db_url=db_url,
            count_in_profitability_only=not args.all_picks,
        )

    if load_warnings:
        for w in load_warnings[:10]:
            print(f"  ? {w}")
        if len(load_warnings) > 10:
            print(f"  ... y {len(load_warnings) - 10} más")

    print(f">> {len(picks)} picks cargados. Generando reporte walk-forward ({args.n_folds} folds)...")
    report = build_comparison_report(picks, n_folds=args.n_folds, governance_config=args.governance)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"\nOK Reporte guardado en {output_path}")
    print("\n--------------- RESUMEN ---------------")
    for sys in [report.system_a, report.system_b, report.system_c]:
        print(f"\n{sys.system_name}")
        print(f"  Picks/Settled: {sys.n_picks}/{sys.n_settled}")
        print(f"  Hit rate:      {sys.hit_rate:.2%}")
        print(f"  ROI:           {sys.roi:.2%}")
        print(f"  Brier:         {sys.brier_score:.4f}")
        print(f"  Log loss:      {sys.log_loss:.4f}")
        print(f"  ECE:           {sys.ece:.4f}")
        clv_str = f"{sys.avg_clv:.2f}%" if sys.avg_clv is not None else "N/A"
        print(f"  CLV medio:     {clv_str}")

    print(f"\n--- DELTA C vs A ---")
    print(f"  dROI:       {report.delta_roi*100:+.2f}%")
    print(f"  dBrier:     {report.delta_brier:+.4f}")
    print(f"  dLog loss:  {report.delta_log_loss:+.4f}")
    print(f"  dPicks:     {report.delta_n_picks:+d}")

    if report.warnings:
        print("\nADVERTENCIAS:")
        for w in report.warnings:
            print(f"  {w}")


if __name__ == "__main__":
    main()
