"""
Invariantes del cutoff temporal.

La propiedad que se defiende aquí es una sola y no admite excepciones: ningún
registro con fecha igual o posterior al saque inicial puede entrar en el cálculo
de una feature. Un dato futuro filtrado en el histórico infla el hit rate, la
calibración lo hereda y el sistema apuesta con una ventaja que no existe. El
fallo no es visible: los números salen mejores, no peores.

De ahí la asimetría deliberada de estos tests: comprueban sobre todo que el
sistema devuelve MENOS de lo pedido cuando no puede demostrar que un dato es
anterior. Sin kickoff no hay muestra, no hay muestra completa.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.math_engine import LeagueMathEngine
from src.domain.temporal import (
    CutoffRequired,
    DEFAULT_DATE_KEYS,
    FilterReport,
    TemporalCutoff,
    filter_before_cutoff,
    parse_utc,
    record_date,
)

KICKOFF = datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════════════
# parse_utc
# ══════════════════════════════════════════════════════════════════════

class TestParseUtc:
    def test_aware_datetime_is_converted_not_rejected(self):
        bogota = timezone(timedelta(hours=-5))
        got = parse_utc(datetime(2026, 3, 15, 13, 0, tzinfo=bogota))
        assert got == KICKOFF

    def test_naive_datetime_is_assumed_utc(self):
        got = parse_utc(datetime(2026, 3, 15, 18, 0))
        assert got == KICKOFF
        assert got.tzinfo is timezone.utc

    def test_every_result_is_aware(self):
        """
        Un solo naive que se escape reintroduce el TypeError al comparar
        aware con naive, que era un crash sin capturar en el motor.
        """
        for value in [
            datetime(2026, 3, 15, 18, 0),
            datetime(2026, 3, 15, 18, 0, tzinfo=timezone.utc),
            date(2026, 3, 15),
            "2026-03-15",
            "2026-03-15T18:00:00Z",
            "2026-03-15 18:00:00",
            1773597600,
        ]:
            got = parse_utc(value)
            assert got is not None, value
            assert got.tzinfo is not None, value
            assert got.utcoffset() == timedelta(0), value

    def test_z_suffix(self):
        assert parse_utc("2026-03-15T18:00:00Z") == KICKOFF

    def test_explicit_offset(self):
        assert parse_utc("2026-03-15T13:00:00-05:00") == KICKOFF

    def test_space_separator(self):
        assert parse_utc("2026-03-15 18:00:00") == KICKOFF

    def test_date_only_lands_at_midnight(self):
        assert parse_utc("2026-03-15") == datetime(2026, 3, 15, tzinfo=timezone.utc)

    def test_date_object(self):
        assert parse_utc(date(2026, 3, 15)) == datetime(2026, 3, 15, tzinfo=timezone.utc)

    def test_epoch_seconds(self):
        assert parse_utc(KICKOFF.timestamp()) == KICKOFF

    @pytest.mark.parametrize("value", [None, "", "   ", "manana", "N/A", 0, -1, [], {}])
    def test_unusable_values_yield_none(self, value):
        assert parse_utc(value) is None

    def test_never_raises(self):
        """
        `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un
        registro corrupto tumbaría el análisis completo en vez de descartarse.
        """
        for value in [object(), float("nan"), float("inf"), b"2026", "2026-13-45"]:
            parse_utc(value)  # no debe lanzar


# ══════════════════════════════════════════════════════════════════════
# record_date: orden de claves
# ══════════════════════════════════════════════════════════════════════

class TestRecordDate:
    def test_match_date_wins_over_date(self):
        """
        En `analysis_history`, `date` es la fecha de CREACIÓN del registro, no la
        del partido. Un análisis creado el día 1 para un partido del día 20 tiene
        `date` anterior al cutoff y `match_date` posterior: si se prioriza `date`,
        el partido futuro entra.
        """
        rec = {"date": "2026-03-01T00:00:00Z", "match_date": "2026-03-20T00:00:00Z"}
        assert record_date(rec) == datetime(2026, 3, 20, tzinfo=timezone.utc)

    def test_date_is_the_last_resort(self):
        assert DEFAULT_DATE_KEYS[-1] == "date"

    def test_falls_through_unusable_keys(self):
        rec = {"match_date": None, "kickoff": "", "kickoff_utc": "2026-03-10T12:00:00Z"}
        assert record_date(rec) == datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)

    def test_no_usable_key_yields_none(self):
        assert record_date({"match_date": None, "date": "basura"}) is None

    def test_empty_record(self):
        assert record_date({}) is None


# ══════════════════════════════════════════════════════════════════════
# TemporalCutoff
# ══════════════════════════════════════════════════════════════════════

class TestTemporalCutoff:
    def test_rejects_naive_kickoff_at_construction(self):
        with pytest.raises(ValueError):
            TemporalCutoff(kickoff=datetime(2026, 3, 15, 18, 0))

    def test_create_returns_none_instead_of_a_permissive_cutoff(self):
        """
        `create` no puede inventar un kickoff por defecto. Devolver un cutoff en
        el infinito o en `now()` convertiría el fallo en fuga silenciosa.
        """
        for value in [None, "", "manana", 0]:
            assert TemporalCutoff.create(value) is None

    def test_require_raises_on_unusable_kickoff(self):
        with pytest.raises(CutoffRequired):
            TemporalCutoff.require(None, context="prueba")

    def test_require_mentions_the_context(self):
        with pytest.raises(CutoffRequired, match="calculo de forma"):
            TemporalCutoff.require("", context="calculo de forma")

    def test_strictly_before(self):
        c = TemporalCutoff.create(KICKOFF)
        assert c.allows(KICKOFF - timedelta(seconds=1)) is True
        assert c.allows(KICKOFF) is False
        assert c.allows(KICKOFF + timedelta(seconds=1)) is False

    def test_the_match_itself_is_excluded(self):
        """
        Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con
        `<=` el propio resultado entraría en su propia feature.
        """
        assert TemporalCutoff.create(KICKOFF).allows(KICKOFF) is False

    def test_timezone_cannot_shift_the_verdict(self):
        """
        Un partido a las 20:00 en Bogotá es 01:00 UTC del día siguiente. Comparar
        fechas como texto lo situaría antes del cutoff; comparar instantes UTC no.
        """
        c = TemporalCutoff.create("2026-03-15T23:00:00Z")
        bogota = timezone(timedelta(hours=-5))
        assert c.allows(datetime(2026, 3, 15, 20, 0, tzinfo=bogota)) is False
        assert c.allows(datetime(2026, 3, 15, 17, 0, tzinfo=bogota)) is True

    def test_record_without_usable_date_is_rejected(self):
        c = TemporalCutoff.create(KICKOFF)
        assert c.allows_record({}) is False
        assert c.allows_record({"match_date": None}) is False
        assert c.allows_record({"match_date": "basura"}) is False

    def test_allows_none_is_false(self):
        assert TemporalCutoff.create(KICKOFF).allows(None) is False

    def test_isoformat_is_utc(self):
        assert TemporalCutoff.create(KICKOFF).isoformat().endswith("+00:00")

    def test_is_immutable(self):
        c = TemporalCutoff.create(KICKOFF)
        with pytest.raises(Exception):
            c.kickoff = KICKOFF + timedelta(days=1)


# ══════════════════════════════════════════════════════════════════════
# Filtrado y contabilidad
# ══════════════════════════════════════════════════════════════════════

def _records():
    return [
        {"id": 1, "match_date": "2026-03-01T18:00:00Z"},   # antes
        {"id": 2, "match_date": "2026-03-14T23:59:59Z"},   # antes, al límite
        {"id": 3, "match_date": "2026-03-15T18:00:00Z"},   # el propio partido
        {"id": 4, "match_date": "2026-03-20T18:00:00Z"},   # futuro
        {"id": 5, "match_date": None},                      # sin fecha
        {"id": 6},                                          # sin clave
    ]


class TestFiltering:
    def test_keeps_only_the_past(self):
        rep = TemporalCutoff.create(KICKOFF).filter_records(_records())
        assert [r["id"] for r in rep.kept] == [1, 2]

    def test_accounting_is_exhaustive(self):
        """
        Cada registro visto tiene que estar en exactamente una cesta. Si la suma
        no cuadra, hay registros perdidos o contados dos veces y el informe deja
        de servir para auditar.
        """
        rep = TemporalCutoff.create(KICKOFF).filter_records(_records())
        assert rep.kept_count + rep.dropped_total == rep.total_seen == 6
        assert rep.dropped_future == 2   # ids 3 y 4
        assert rep.dropped_undated == 2  # ids 5 y 6

    def test_future_and_undated_are_counted_apart(self):
        """
        Son problemas distintos: futuro significa fuga de datos; sin fecha
        significa datos incompletos. Mezclarlos oculta cuál de los dos ocurre.
        """
        rep = TemporalCutoff.create(KICKOFF).filter_records(_records())
        assert rep.dropped_future != rep.dropped_total

    def test_missing_cutoff_yields_nothing(self):
        """
        Ésta es la invariante central: sin kickoff, cero registros. La versión
        anterior desactivaba el filtro y devolvía el histórico completo.
        """
        rep = filter_before_cutoff(_records(), None)
        assert rep.kept == []
        assert rep.kept_count == 0

    def test_the_escape_hatch_is_keyword_only(self):
        """
        `allow_missing_cutoff` no puede activarse por accidente pasando un
        posicional de más.
        """
        with pytest.raises(TypeError):
            filter_before_cutoff(_records(), None, DEFAULT_DATE_KEYS, True)

    def test_the_escape_hatch_disables_filtering_entirely(self):
        """
        Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso
        los registros sin fecha. Es intencionadamente todo o nada, para que no
        exista un modo intermedio que parezca seguro sin serlo.
        """
        rep = filter_before_cutoff(_records(), None, allow_missing_cutoff=True)
        assert [r["id"] for r in rep.kept] == [1, 2, 3, 4, 5, 6]

    def test_empty_input(self):
        rep = TemporalCutoff.create(KICKOFF).filter_records([])
        assert rep.total_seen == 0 and rep.kept == []

    def test_report_is_serializable(self):
        rep = TemporalCutoff.create(KICKOFF).filter_records(_records())
        d = rep.to_dict()
        assert d["dropped_future"] == 2
        assert isinstance(rep.summary(), str) and rep.summary()

    def test_report_dict_carries_counts_not_records(self):
        """El informe se registra en logs; no debe arrastrar el histórico entero."""
        d = TemporalCutoff.create(KICKOFF).filter_records(_records()).to_dict()
        assert d["kept"] == 2
        assert all(isinstance(v, int) for v in d.values())


# ══════════════════════════════════════════════════════════════════════
# Regresión sobre el motor
# ══════════════════════════════════════════════════════════════════════

def _match(mid, when, home, away, gh, ga):
    return {
        "id": mid,
        "match_date": when,
        "home_team": home,
        "away_team": away,
        "match_title": f"{home} vs {away}",
        "final_score_home": gh,
        "final_score_away": ga,
    }


class TestEngineHitRates:
    def _history(self):
        # Tres partidos previos con pocos goles y dos posteriores con muchos.
        # Si el cutoff falla, el hit rate de Over 2.5 se dispara.
        return [
            _match(1, "2026-02-01T18:00:00Z", "Alfa", "Beta", 0, 1),
            _match(2, "2026-02-10T18:00:00Z", "Alfa", "Gamma", 1, 0),
            _match(3, "2026-03-01T18:00:00Z", "Delta", "Alfa", 1, 1),
            _match(4, "2026-03-20T18:00:00Z", "Alfa", "Beta", 4, 3),
            _match(5, "2026-04-01T18:00:00Z", "Alfa", "Gamma", 5, 2),
        ]

    def test_future_matches_do_not_enter_the_sample(self):
        got = LeagueMathEngine.compute_pick_hit_rate(
            self._history(), "Alfa", "goals", line=2.5, is_over=True,
            current_match_date=KICKOFF,
        )
        assert got["sample_size"] == 3
        assert got["hits"] == 0
        assert got["hit_rate_pct"] == 0.0

    def test_without_cutoff_the_sample_is_empty_not_complete(self):
        """
        Regresión directa del fallo: `current_match_date=None` devolvía las 5
        muestras, dos de ellas del futuro.
        """
        got = LeagueMathEngine.compute_pick_hit_rate(
            self._history(), "Alfa", "goals", line=2.5, is_over=True,
            current_match_date=None,
        )
        assert got["sample_size"] == 0
        assert got["cutoff_missing"] is True

    def test_the_missing_cutoff_is_flagged_not_hidden(self):
        """
        Una muestra vacía por falta de cutoff no es lo mismo que una muestra
        vacía por falta de historial. Quien consuma el resultado debe poder
        distinguirlas.
        """
        con_cutoff = LeagueMathEngine.compute_pick_hit_rate(
            [], "Alfa", "goals", line=2.5, current_match_date=KICKOFF
        )
        sin_cutoff = LeagueMathEngine.compute_pick_hit_rate(
            [], "Alfa", "goals", line=2.5, current_match_date=None
        )
        assert con_cutoff.get("cutoff_missing") is None
        assert sin_cutoff.get("cutoff_missing") is True

    def test_aware_and_naive_mix_does_not_crash(self):
        """
        Antes, comparar un `match_date` aware con un kickoff naive lanzaba
        TypeError sin capturar en mitad del análisis.
        """
        history = [
            _match(1, datetime(2026, 2, 1, 18, 0, tzinfo=timezone.utc), "Alfa", "Beta", 0, 1),
            _match(2, datetime(2026, 2, 10, 18, 0), "Alfa", "Gamma", 1, 0),
        ]
        got = LeagueMathEngine.compute_pick_hit_rate(
            history, "Alfa", "goals", line=2.5,
            current_match_date=datetime(2026, 3, 15, 18, 0),  # naive
        )
        assert got["sample_size"] == 2

    def test_h2h_excludes_the_future_too(self):
        got = LeagueMathEngine.compute_h2h_hit_rate(
            self._history(), "Alfa", "Beta", "goals", line=2.5, is_over=True,
            current_match_date=KICKOFF,
        )
        assert got["sample_size"] == 1  # solo el partido 1
        assert got["hits"] == 0

    def test_h2h_without_cutoff_returns_no_matches(self):
        got = LeagueMathEngine.compute_h2h_hit_rate(
            self._history(), "Alfa", "Beta", "goals", line=2.5,
            current_match_date=None,
        )
        assert got["sample_size"] == 0
        assert got["h2h_matches"] == []
        assert got["cutoff_missing"] is True

    def test_undated_records_are_dropped_not_assumed_past(self):
        history = self._history() + [
            _match(9, None, "Alfa", "Beta", 3, 3),
            _match(10, "", "Alfa", "Gamma", 4, 4),
        ]
        got = LeagueMathEngine.compute_pick_hit_rate(
            history, "Alfa", "goals", line=2.5, is_over=True,
            current_match_date=KICKOFF,
        )
        assert got["sample_size"] == 3  # los sin fecha no suben la muestra
        assert got["hits"] == 0

    def test_monotonic_in_the_cutoff(self):
        """
        Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la
        muestra crece al restringir el cutoff, el filtro está invertido.
        """
        history = self._history()
        previous = None
        for day in range(1, 32):
            got = LeagueMathEngine.compute_pick_hit_rate(
                history, "Alfa", "goals", line=2.5,
                current_match_date=datetime(2026, 4, day if day <= 30 else 30,
                                            tzinfo=timezone.utc),
            )
            if previous is not None:
                assert got["sample_size"] >= previous
            previous = got["sample_size"]

    def test_exclude_match_id_still_works_with_the_cutoff(self):
        got = LeagueMathEngine.compute_pick_hit_rate(
            self._history(), "Alfa", "goals", line=2.5, is_over=True,
            exclude_match_id=1, current_match_date=KICKOFF,
        )
        assert got["sample_size"] == 2
