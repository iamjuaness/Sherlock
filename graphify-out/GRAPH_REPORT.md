# Graph Report - Sherlock  (2026-09-25)

## Corpus Check
- 85 files · ~231,900 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 1816 nodes · 4210 edges · 106 communities (73 shown, 33 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 304 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bee0f6b1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_train_calibration.py
- Web UI Comparator JS
- background.js
- test_eligibility.py
- test_count_negative_binomial.py
- _check_pick_success
- compare.py
- test_settlement.py
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- admin_stats_service.py
- Web UI Leagues JS
- main.py
- compare_football
- domain.py
- test_calibration.py
- save_analysis
- recalculate_all_accuracy
- BlockReason
- Side
- database.py
- _value_indicator
- AnalysisHistory
- .compute_h2h_hit_rate
- get
- admin_database_service.py
- .create
- _explicit_market_support
- manifest.json
- test_math_engine.py
- LeagueMathEngine
- test_compare_integration.py
- CalibrationCurve
- test_calibration_wiring.py
- dashboard_main.js
- TestFiltering
- .compute_pick_hit_rate
- eligibility.py
- schemas.py
- test_admin_panel.py
- parse_utc
- HierarchicalCalibrator
- resolve_match_picks_correlation
- test_temporal.py
- calibration.py
- typing
- train_model_retrospective.py
- CalibrationSample
- RiskLimits
- parallel_recalc.py
- evaluate
- PickSnapshot
- TestLeagueMathEngine
- settlement.py
- calculate_parameters
- prueba90100.py
- _dc_score_matrix
- admin.js
- admin_routes.py
- CardsConvention
- StatSource
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- backup_db.py
- risk.py
- is_hard
- calculate_weighted_average
- content.js
- FilterReport
- clean_env
- TemporalCutoff
- simulate_pick_rules
- test_threshold_families_match_the_legacy_sets
- sherlock
- get_nbinom_under_over_prob

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 70 edges
2. `AnalysisHistory` - 65 edges
3. `compare_football()` - 57 edges
4. `Outcome` - 40 edges
5. `good_snapshot()` - 32 edges
6. `HierarchicalCalibrator` - 31 edges
7. `LeagueMathEngine` - 30 edges
8. `resolve_match_picks_correlation()` - 30 edges
9. `extract_samples()` - 29 edges
10. `ReturnDistribution` - 29 edges

## Surprising Connections (you probably didn't know these)
- `calculate_parameters_per_match()` --uses--> `LeagueMathEngine`  [INFERRED]
  calculate_league_params.py → src/core/math_engine.py
- `db_session()` --uses--> `Base`  [INFERRED]
  tests/unit/test_admin_panel.py → src/core/database.py
- `test_operational_fields_update_and_audit()` --uses--> `AdminAuditLog`  [INFERRED]
  tests/unit/test_admin_panel.py → src/core/domain.py
- `TestLeagueMathEngine` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/test_math_engine.py → src/core/math_engine.py
- `TestEngineHitRates` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/unit/test_temporal.py → src/core/math_engine.py

## Import Cycles
- None detected.

## Communities (106 total, 33 thin omitted)

### Community 0 - "test_train_calibration.py"
Cohesion: 0.05
Nodes (71): re, _coerce_datetime(), _extract_line_bucket(), extract_samples(), ExtractionStats, history_dir_for(), load_rows_from_db(), main() (+63 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "test_eligibility.py"
Cohesion: 0.10
Nodes (44): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+36 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "_check_pick_success"
Cohesion: 0.07
Nodes (43): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _check_projected_line_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), get_all_picks() (+35 more)

### Community 6 - "compare.py"
Cohesion: 0.06
Nodes (42): dotenv, numpy, openai, pydantic_alias_generators, _are_contradictory(), _calibration_line_bucket(), _call_openrouter(), _canonical_pick_signature() (+34 more)

### Community 7 - "test_settlement.py"
Cohesion: 0.12
Nodes (29): _combine_legs(), line_legs(), Outcome, outcome_hit_value(), outcome_return(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Combina los resultados de las piernas (cada una con media unidad). Solo se usan…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del… (+21 more)

### Community 8 - "test_risk.py"
Cohesion: 0.10
Nodes (33): is_hard_blocked(), True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., load_risk_limits(), Any, Resuelve la política de riesgo efectiva. Precedencia: entorno > defaults del…, make_pick(), published(), parametrize (+25 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (24): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+16 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (33): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+25 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "admin_stats_service.py"
Cohesion: 0.11
Nodes (33): io, pandas, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData (+25 more)

### Community 13 - "Web UI Leagues JS"
Cohesion: 0.13
Nodes (32): addMarketToBlacklist(), applyBulkBlacklist(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry(), escapeAttr() (+24 more)

### Community 14 - "main.py"
Cohesion: 0.07
Nodes (45): contextlib, copy, fastapi_middleware_cors, fastapi_staticfiles, openpyxl, openpyxl_utils, Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache() (+37 more)

### Community 15 - "compare_football"
Cohesion: 0.18
Nodes (27): compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda() (+19 more)

### Community 16 - "domain.py"
Cohesion: 0.07
Nodes (38): ABC, DeclarativeBase, enum, Base, Declarative base for all ORM models., BettingLine, Competition, MarketType (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.13
Nodes (23): random, pava(), Construye muestras desde filas liquidadas, excluyendo push y unsettled. Espera…, Regresión isotónica ponderada por Pool Adjacent Violators. Devuelve la…, Tabla de reliability: confianza declarada vs acierto observado por bin., Walk-forward estricto por grupos temporales. Un mismo timestamp se trata como…, reliability_table(), samples_from_settlements() (+15 more)

### Community 18 - "save_analysis"
Cohesion: 0.17
Nodes (13): Exception, _extract_bookmaker(), _extract_competition(), push_result(), Extract competition name from payload dict, avoiding json.loads in callers., Extract primary bookmaker from payload dict., Save or update an analysis in history., Return the sum of stake_units for publishable picks of a match. (+5 more)

### Community 19 - "recalculate_all_accuracy"
Cohesion: 0.09
Nodes (25): Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), CompareResponse, _annotate_best_bookmaker(), _apply_line_shopping(), _call_llm_for_result(), _check_payload_has_odds(), _has_valid() (+17 more)

### Community 20 - "BlockReason"
Cohesion: 0.09
Nodes (21): BlockReason, _coerce_reason(), describe(), EligibilityDecision, str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno. (+13 more)

### Community 21 - "Side"
Cohesion: 0.23
Nodes (17): str, Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, _settle_simple_total(), settle_total(), Side, parametrize, Una línea que no es múltiplo de 0.25 no se liquida a ciegas. (+9 more)

### Community 22 - "database.py"
Cohesion: 0.16
Nodes (13): FastAPI, listens_for, sqlalchemy_orm, _column_exists(), create_indexes(), init_db(), Database engine, session factory and Base for SQLAlchemy models., Create indexes for analysis_history and related tables. (+5 more)

### Community 23 - "_value_indicator"
Cohesion: 0.10
Nodes (27): apply_calibration(), _calculate_display_score(), _calculate_kelly_fraction(), _calculate_stake_units(), calibration_is_active(), _calibration_side(), _vi(), get_data_quality_score() (+19 more)

### Community 24 - "AnalysisHistory"
Cohesion: 0.08
Nodes (36): delete, put, AnalysisHistory, History of manual analyses performed in the comparator., deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches() (+28 more)

### Community 25 - ".compute_h2h_hit_rate"
Cohesion: 0.18
Nodes (5): Any, Calcula los promedios específicos de la liga basándose en los partidos…, Evalúa si un partido específico cumple con el criterio de un pick. Soporta:…, Calcula el hit rate global a nivel de liga para un mercado específico para…, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…

### Community 26 - "get"
Cohesion: 0.09
Nodes (30): middleware, Sport, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version(), get_analysis_by_id() (+22 more)

### Community 27 - "admin_database_service.py"
Cohesion: 0.19
Nodes (17): ColumnSchemaInfo, DatabaseRowUpdate, DatabaseTableSchema, PaginationMeta, get_table_schema(), list_whitelisted_tables(), Any, Session (+9 more)

### Community 28 - ".create"
Cohesion: 0.16
Nodes (6): Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el…, Un partido a las 20:00 en Bogotá es 01:00 UTC del día siguiente. Comparar…, TestTemporalCutoff

### Community 29 - "_explicit_market_support"
Cohesion: 0.19
Nodes (25): _clip_0_100(), _explicit_market_support(), _poisson_over_under(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+17 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "test_math_engine.py"
Cohesion: 0.17
Nodes (9): calculate_dixon_coles_matrix(), dixon_coles_tau(), estimate_nb_dispersion(), _poisson_pmf(), Estima el parámetro de dispersión (alpha/k) de la Binomial Negativa por Método…, Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0,…, Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste…, Tests unitarios para el motor estadístico matemático por liga (Sherlock Math… (+1 more)

### Community 32 - "LeagueMathEngine"
Cohesion: 0.19
Nodes (9): fastapi_testclient, LeagueMathEngine, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, test_promedio_corners_ultima_jornada(), Ticket 3: Promedio de corners toma la última jornada o temporada actual sin 9.5…, Ticket 1: Guardar partido sin fecha debe responder 400 Bad Request y detener el…, test_ticket1_missing_match_date_returns_400() (+1 more)

### Community 33 - "test_compare_integration.py"
Cohesion: 0.07
Nodes (20): pytest, Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño. (+12 more)

### Community 34 - "CalibrationCurve"
Cohesion: 0.12
Nodes (13): CalibrationCurve, Un bin de la curva de reliability, con su evidencia., Mapa monótono lineal por tramos de probabilidad raw -> calibrada. Los nodos…, Aplica la calibración. Acepta 0-1 o 0-100 y devuelve en la MISMA escala., Interpolación lineal entre nodos observados. Fuera del rango cubierto por los…, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale. (+5 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - "TestFiltering"
Cohesion: 0.17
Nodes (10): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los…, El informe se registra en logs; no debe arrastrar el histórico entero. (+2 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "eligibility.py"
Cohesion: 0.18
Nodes (16): _as_float(), hard_blocks_from_flags(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Lee todos los bloqueos duros ya presentes en un pick, sea dict u objeto.… (+8 more)

### Community 40 - "schemas.py"
Cohesion: 0.18
Nodes (19): field_validator, pydantic, AnalysisHistoryOut, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut (+11 more)

### Community 41 - "test_admin_panel.py"
Cohesion: 0.10
Nodes (34): json, OperationalFieldsUpdate, PickDetailOut, PickItemOut, export_picks_file(), _extract_picks_from_analysis(), get_pick_detail(), mark_for_recalculation() (+26 more)

### Community 42 - "parse_utc"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "HierarchicalCalibrator"
Cohesion: 0.19
Nodes (9): HierarchicalCalibrator, Path, Calibrador jerárquico y conservador. Orden de resolución: league × family ×…, Calibra una probabilidad y conserva su escala de entrada. Entrada 0-1 -> salida…, get_calibrator(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.…, test_load_rejects_unknown_format_version(), test_save_load_roundtrip() (+1 more)

### Community 44 - "resolve_match_picks_correlation"
Cohesion: 0.13
Nodes (25): classify_correlation_severity(), clear_correlation_matrix_cache(), evaluate_pick_rules(), load_market_correlation_matrix(), load_pick_rules_data(), market_correlation_rho(), market_family(), market_group() (+17 more)

### Community 45 - "test_temporal.py"
Cohesion: 0.14
Nodes (12): CutoffRequired, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Reparte los registros en admitidos, posteriores y sin fecha., Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, record_date() (+4 more)

### Community 46 - "calibration.py"
Cohesion: 0.18
Nodes (20): _clean_segment_value(), directional_key(), family_key(), league_key(), line_key(), Calibración probabilística real de Sherlock. SIN GLM. Por qué no GLM / stacking…, Devuelve la curva más específica disponible. Nunca crea una curva implícita. Si…, Ajusta la jerarquía completa con partial pooling. Los mínimos más altos evitan… (+12 more)

### Community 47 - "typing"
Cohesion: 0.09
Nodes (24): argparse, Script CLI para calcular parámetros matemáticos (Dixon-Coles, promedios por…, Connection, datetime, logging, pathlib, sqlalchemy, sqlite3 (+16 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationSample"
Cohesion: 0.13
Nodes (17): CalibrationSample, fit_curve(), _quantile_edges(), Bordes de bin por cuantiles, garantizando ocupación mínima., Ajusta una curva por Beta-Binomial + isotónica PAVA. Mejoras frente a la…, Una observación histórica para ajustar la calibración. `prob` puede venir en…, El audit: 'la curva de calibración muestra sobreconfianza fuerte en…, Si el modelo ya está calibrado, la curva debe quedarse cerca de la identidad. (+9 more)

### Community 50 - "RiskLimits"
Cohesion: 0.17
Nodes (8): Política de riesgo efectiva. Inmutable: se resuelve una vez y se pasa., False solo cuando el kill switch está echado., Stake que se puede arriesgar de verdad. En PAPER y HALTED es siempre 0: el…, RiskLimits, test_describe_mentions_the_mode(), test_halted_mode_blocks_every_pick(), test_limits_are_immutable(), test_to_dict_exposes_the_mode()

### Community 51 - "parallel_recalc.py"
Cohesion: 0.15
Nodes (21): asyncio, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line() (+13 more)

### Community 52 - "evaluate"
Cohesion: 0.12
Nodes (17): brier_score(), evaluate(), expected_calibration_error(), log_loss(), Error cuadrático medio de la probabilidad. Menor es mejor., Log loss (entropía cruzada). Penaliza la sobreconfianza con fuerza., ECE: desvío absoluto medio entre confianza y acierto, ponderado por bin. 0 =…, Resumen de calidad probabilística. (+9 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.27
Nodes (10): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad calibrada, la misma que se muestra. Decidir con…, test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_calibrated_prob() (+2 more)

### Community 55 - "settlement.py"
Cohesion: 0.18
Nodes (12): dataclasses, functools, math, distribution_for_total_line(), outcome_probabilities_for_total(), Enum, Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de…, Convierte una PMF del total (determinista) en probabilidades de outcome para… (+4 more)

### Community 56 - "calculate_parameters"
Cohesion: 0.21
Nodes (11): calculate_parameters(), calculate_parameters_per_match(), fetch_historical_matches_by_league(), main(), print_summary(), Any, Calcula todos los parámetros matemáticos a partir de los datos históricos., Calcula por cada partido las estadísticas acumuladas de la liga y de los dos… (+3 more)

### Community 57 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 58 - "_dc_score_matrix"
Cohesion: 0.20
Nodes (12): _dc_log_likelihood(), _dc_match_probs(), _dc_score_matrix(), _dc_tau(), _default_dc_rho(), fit_dixon_coles_rho(), _poisson_pmf(), Heurística original — se mantiene como fallback. (+4 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.10
Nodes (38): fastapi_responses, fastapi_templating, patch, export_stats_file(), Export filtered stats table to CSV or Excel bytes., admin_dashboard_page(), admin_database_page(), admin_mark_recalculation() (+30 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "StatSource"
Cohesion: 0.22
Nodes (6): Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio…, StatSource

### Community 63 - "betano_content.js"
Cohesion: 0.48
Nodes (5): buildSherlockPayload(), checkCurrentUrl(), extractMatchInfo(), fetchAndSendOdds(), parseBetanoOdds()

### Community 64 - "settings.js"
Cohesion: 0.62
Nodes (6): loadSettings(), resetSettings(), saveSettings(), setupEventListeners(), showStatus(), testConnection()

### Community 65 - "sofaScoreToSherlock.js"
Cohesion: 0.48
Nodes (5): buildLeagueStats(), buildSherlockPayload(), extractRefereeStats(), findTeamInStandings(), mapSofaScoreToSherlockTeamStats()

### Community 66 - "config.py"
Cohesion: 0.33
Nodes (5): BaseSettings, pydantic_settings, Application configuration using pydantic-settings., Sherlock platform configuration. Values are loaded from environment variables…, Settings

### Community 67 - "backup_db.py"
Cohesion: 0.24
Nodes (9): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), os (+1 more)

### Community 68 - "risk.py"
Cohesion: 0.22
Nodes (8): _env_bool(), PublicationMode, Enum, str, Límites de riesgo y kill switch de publicación. Por qué está separado de…, Lee un booleano de entorno. Un valor presente pero ininteligible NO se ignora…, El defecto NO puede ser dinero real. La calibración solo está validada contra…, test_default_mode_is_paper_not_live()

### Community 69 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 70 - "calculate_weighted_average"
Cohesion: 0.29
Nodes (4): calculate_weighted_average(), Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva y defensiva…, Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros,…, Calcula el promedio con decay exponencial según antigüedad. half_life: número…

### Community 73 - "clean_env"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

### Community 74 - "TemporalCutoff"
Cohesion: 0.29
Nodes (3): Instante a partir del cual la información no existe todavía. `kickoff` siempre…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, TemporalCutoff

### Community 75 - "simulate_pick_rules"
Cohesion: 0.33
Nodes (3): Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Evaluates proposed conditions on the historical database to see the success…, simulate_pick_rules()

## Knowledge Gaps
- **32 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 640 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `test_train_calibration.py`, `_check_pick_success`, `compare.py`, `test_admin_panel.py`, `simulate_pick_rules`, `admin_stats_service.py`, `main.py`, `domain.py`, `train_model_retrospective.py`, `save_analysis`, `recalculate_all_accuracy`, `prueba90100.py`, `get`, `admin_database_service.py`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `HierarchicalCalibrator` connect `HierarchicalCalibrator` to `test_train_calibration.py`, `test_calibration_wiring.py`, `compare.py`, `calibration.py`, `test_calibration.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `test_eligibility.py`, `is_hard`, `compare.py`, `eligibility.py`, `test_risk.py`, `test_eligibility_wiring.py`, `resolve_match_picks_correlation`, `compare_football`, `PickSnapshot`, `_value_indicator`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `BlockReason` (e.g. with `resolve_match_picks_correlation()` and `_risk_imports()`) actually correct?**
  _`BlockReason` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 47 inferred relationships involving `AnalysisHistory` (e.g. with `purge_odds_before_cutoff()` and `load_rows_from_db()`) actually correct?**
  _`AnalysisHistory` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `compare_football()` (e.g. with `LeagueMathEngine` and `BlockReason`) actually correct?**
  _`compare_football()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Outcome` (e.g. with `extract_samples()` and `under_over_probabilities()`) actually correct?**
  _`Outcome` has 17 INFERRED edges - model-reasoned connections that need verification._