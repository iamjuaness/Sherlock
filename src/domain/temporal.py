"""
Cutoff temporal en UTC. Impide que información posterior al saque inicial
entre en las features de un pick.

El problema que resuelve
───────────────────────
El filtro anti-leakage de `math_engine` era:

    if ref_date_only and m_dt and m_dt.date() >= ref_date_only:
        continue

Solo excluye cuando AMBAS fechas existen y se parsean. Falla ABIERTO en los dos
casos que importan:

  · Sin fecha de kickoff (`ref_date_only is None`): no filtra nada. Todo el
    histórico entra, incluidos partidos posteriores al que se está analizando.
  · Partido histórico sin fecha parseable (`m_dt is None`): se incluye. Puede
    ser del futuro y nadie lo sabe.

El docstring afirmaba "Previene data-leakage". Lo previene solo cuando los datos
están completos, que es precisamente cuando no hace falta.

Además comparaba con `.date()`, descartando la hora: dos partidos el mismo día
son indistinguibles, y con zonas horarias distintas el mismo instante puede caer
en días diferentes.

La política aquí
────────────────
FALLAR CERRADO. Un registro entra en el histórico solo si se puede demostrar
que ocurrió estrictamente antes del kickoff. Si falta el kickoff, o falta la
fecha del registro, o no se parsea: fuera. Un backtest con menos muestras es un
backtest honesto; uno con muestras del futuro es una mentira que además parece
buena.

Todo se normaliza a UTC con zona explícita. Una fecha naive se interpreta como
UTC en lugar de rechazarse, porque la BD (SQLite) guarda naive, pero se hace en
un único sitio y de forma declarada, no implícita en cada comparación.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

# Claves donde los distintos orígenes guardan la fecha del partido. `date` va
# al final a propósito: en AnalysisHistory suele ser la fecha de CREACIÓN del
# registro, no la del partido, así que solo se usa si no hay nada mejor.
DEFAULT_DATE_KEYS: tuple[str, ...] = ("match_date", "kickoff", "kickoff_utc", "date")


class CutoffRequired(ValueError):
    """
    Se pidió filtrar por cutoff sin un kickoff utilizable.

    Es un error explícito y no un filtro vacío silencioso para que el fallo se
    note en desarrollo en lugar de degradar la calidad de los datos sin aviso.
    """


def parse_utc(value: Any) -> datetime | None:
    """
    Normaliza cualquier representación de fecha a un `datetime` UTC con zona.

    Devuelve None si no se puede interpretar. Nunca lanza: quien decide qué
    hacer con lo inparseable es la política de cutoff, no el parser.

    Acepta datetime (naive o aware), date, ISO-8601 con 'Z' u offset, y
    'YYYY-MM-DD' suelto (que se ancla a medianoche UTC).
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        # Epoch en segundos. Se descartan valores absurdos en lugar de
        # producir fechas de 1970 que pasarían el cutoff por accidente.
        try:
            if value <= 0:
                return None
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip()
    if not text:
        return None

    candidate = text.replace("Z", "+00:00").replace("z", "+00:00")
    # SQLite y algunos orígenes usan espacio en vez de 'T'.
    if " " in candidate and "T" not in candidate:
        candidate = candidate.replace(" ", "T", 1)

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        # Último recurso: solo la parte de la fecha.
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except (ValueError, IndexError):
            return None

    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def record_date(
    record: Mapping[str, Any] | Any,
    date_keys: Sequence[str] = DEFAULT_DATE_KEYS,
) -> datetime | None:
    """
    Extrae la fecha de un registro probando varias claves en orden de fiabilidad.

    Devuelve la primera que se parsee. None si ninguna sirve, lo que con la
    política de cutoff significa que el registro se descarta.
    """
    for key in date_keys:
        raw = record.get(key) if isinstance(record, Mapping) else getattr(record, key, None)
        parsed = parse_utc(raw)
        if parsed is not None:
            return parsed
    return None


@dataclass(frozen=True)
class FilterReport:
    """
    Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.

    Los contadores no son decorativos: `dropped_undated` alto significa que el
    origen de datos tiene fechas ausentes y las muestras que quedan no son
    representativas. Sin este desglose, un histórico degradado es
    indistinguible de un histórico pequeño.
    """

    kept: list[Any]
    dropped_future: int = 0
    dropped_undated: int = 0

    @property
    def dropped_total(self) -> int:
        return self.dropped_future + self.dropped_undated

    @property
    def kept_count(self) -> int:
        return len(self.kept)

    @property
    def total_seen(self) -> int:
        return self.kept_count + self.dropped_total

    def summary(self) -> str:
        return (
            f"{self.kept_count}/{self.total_seen} registros admitidos "
            f"(descartados: {self.dropped_future} posteriores al cutoff, "
            f"{self.dropped_undated} sin fecha utilizable)"
        )

    def to_dict(self) -> dict:
        return {
            "kept": self.kept_count,
            "dropped_future": self.dropped_future,
            "dropped_undated": self.dropped_undated,
            "total_seen": self.total_seen,
        }


@dataclass(frozen=True)
class TemporalCutoff:
    """
    Instante a partir del cual la información no existe todavía.

    `kickoff` siempre es UTC con zona. La comparación es ESTRICTAMENTE anterior:
    un registro con la misma marca temporal que el saque inicial se descarta,
    porque no se puede demostrar que estuviera disponible antes.
    """

    kickoff: datetime

    def __post_init__(self):
        if self.kickoff.tzinfo is None:
            raise ValueError("TemporalCutoff exige un kickoff con zona horaria; usa TemporalCutoff.create()")

    # ── construcción ────────────────────────────────────────────────
    @classmethod
    def create(cls, value: Any) -> "TemporalCutoff | None":
        """Construye el cutoff, o None si el kickoff no es utilizable."""
        parsed = parse_utc(value)
        return cls(kickoff=parsed) if parsed else None

    @classmethod
    def require(cls, value: Any, *, context: str = "") -> "TemporalCutoff":
        """
        Igual que `create` pero exige un kickoff válido.

        Se usa en las rutas donde entrenar o publicar sin cutoff sería un error
        silencioso con consecuencias económicas.
        """
        cutoff = cls.create(value)
        if cutoff is None:
            suffix = f" ({context})" if context else ""
            raise CutoffRequired(
                f"Se requiere una fecha de partido válida para aplicar el cutoff temporal{suffix}; "
                f"se recibió {value!r}"
            )
        return cutoff

    # ── decisión ────────────────────────────────────────────────────
    def allows(self, value: Any) -> bool:
        """
        True solo si `value` es demostrablemente anterior al kickoff.

        Una fecha ausente o inparseable devuelve False: fallar cerrado.
        """
        parsed = parse_utc(value)
        return parsed is not None and parsed < self.kickoff

    def allows_record(
        self,
        rec: Mapping[str, Any] | Any,
        date_keys: Sequence[str] = DEFAULT_DATE_KEYS,
    ) -> bool:
        parsed = record_date(rec, date_keys)
        return parsed is not None and parsed < self.kickoff

    # ── filtrado ────────────────────────────────────────────────────
    def filter_records(
        self,
        records: Iterable[Any],
        date_keys: Sequence[str] = DEFAULT_DATE_KEYS,
    ) -> FilterReport:
        """Reparte los registros en admitidos, posteriores y sin fecha."""
        kept: list[Any] = []
        future = 0
        undated = 0

        for rec in records or []:
            parsed = record_date(rec, date_keys)
            if parsed is None:
                undated += 1
            elif parsed < self.kickoff:
                kept.append(rec)
            else:
                future += 1

        return FilterReport(kept=kept, dropped_future=future, dropped_undated=undated)

    def isoformat(self) -> str:
        return self.kickoff.isoformat()


def filter_before_cutoff(
    records: Iterable[Any],
    kickoff: Any,
    date_keys: Sequence[str] = DEFAULT_DATE_KEYS,
    *,
    allow_missing_cutoff: bool = False,
) -> FilterReport:
    """
    Filtra un histórico dejando solo lo anterior al kickoff.

    Sin un kickoff utilizable devuelve un informe VACÍO: no se puede garantizar
    que ningún registro sea anterior, así que no se admite ninguno. Esta es la
    corrección central del fail-open — antes, no tener kickoff significaba
    aceptar todo.

    `allow_missing_cutoff=True` desactiva esa protección y solo debe usarse en
    análisis exploratorio, nunca al entrenar ni al publicar. Es un parámetro
    keyword-only para que aparezca escrito en el sitio de llamada y sea visible
    en cualquier revisión de código.
    """
    cutoff = TemporalCutoff.create(kickoff)

    if cutoff is None:
        if not allow_missing_cutoff:
            all_records = list(records or [])
            return FilterReport(kept=[], dropped_undated=len(all_records))
        return FilterReport(kept=list(records or []))

    return cutoff.filter_records(records, date_keys)
