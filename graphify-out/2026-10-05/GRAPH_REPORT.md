# Graph Report - Sherlock  (2026-10-05)

## Corpus Check
- 115 files · ~328,358 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 2209 nodes · 5179 edges · 119 communities (86 shown, 33 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 342 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e883c745`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- train_calibration.py
- Web UI Comparator JS
- background.js
- test_eligibility.py
- test_count_negative_binomial.py
- _check_pick_success
- compare.py
- Outcome
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- admin_stats_service.py
- Web UI Leagues JS
- post
- compare_football
- manual_loader.py
- test_calibration.py
- save_analysis
- main.py
- BlockReason
- test_settlement.py
- test_stake_and_traceability.py
- _value_indicator
- AnalysisHistory
- HierarchicalCalibrator
- test_regression_biases.py
- admin_database_service.py
- TestFiltering
- _explicit_market_support
- manifest.json
- market_probability.py
- LeagueMathEngine
- test_compare_integration.py
- CalibrationCurve
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- test_invariants_and_eligibility.py
- schemas.py
- test_admin_panel.py
- parse_utc
- joint_match_distribution.py
- pick_rules_engine.py
- record_date
- calibration.py
- backup_db.py
- train_model_retrospective.py
- CalibrationSample
- is_hard_blocked
- parallel_recalc.py
- extract_samples
- PickSnapshot
- test_train_calibration.py
- math
- calculate_league_params.py
- prueba90100.py
- domain.py
- admin.js
- admin_routes.py
- CardsConvention
- StatSource
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- TemporalParameterOptimizer
- evaluate_segment_status
- is_hard
- submit_closing_odds
- content.js
- segment_governance.py
- walk_forward_calibrate
- hard_blocks_from_flags
- re
- sherlock
- typing
- market_group_key
- risk.py
- evaluate_oof_comparison.py
- .compute_league_averages
- _dc_score_matrix
- outcome_from_legacy
- ExtractionStats
- dataclasses
- PredictionRecord
- stream_football_analysis
- TestMLSGoalsOverHighExtreme
- clean_env
- test_threshold_families_match_the_legacy_sets

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 76 edges
2. `AnalysisHistory` - 71 edges
3. `compare_football()` - 58 edges
4. `HierarchicalCalibrator` - 42 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `CalibrationSample` - 34 edges
8. `good_snapshot()` - 32 edges
9. `EligibilityDecision` - 30 edges
10. `extract_samples()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `calculate_parameters_per_match()` --uses--> `LeagueMathEngine`  [INFERRED]
  calculate_league_params.py → src/core/math_engine.py
- `build_comparison_report()` --uses--> `SegmentStatus`  [INFERRED]
  scripts/evaluate_oof_comparison.py → src/models/segment_governance.py
- `TestStructuralDecayAndProfiles` --uses--> `TemporalParameterOptimizer`  [INFERRED]
  tests/unit/test_structural_decay.py → src/core/backtesting.py
- `test_operational_fields_update_and_audit()` --uses--> `AdminAuditLog`  [INFERRED]
  tests/unit/test_admin_panel.py → src/core/domain.py
- `TestStructuralDecayAndProfiles` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/unit/test_structural_decay.py → src/core/math_engine.py

## Import Cycles
- None detected.

## Communities (119 total, 33 thin omitted)

### Community 0 - "train_calibration.py"
Cohesion: 0.10
Nodes (27): _coerce_cutoff_datetime(), _coerce_datetime(), _extract_line_bucket(), _league_already_calibrated(), load_rows_from_db(), main(), _normalize_market_text(), _pick_probability() (+19 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "test_eligibility.py"
Cohesion: 0.10
Nodes (45): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+37 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (41): functools, convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa…, PMF de la suma de dos conteos independientes. Convolución discreta exacta:… (+33 more)

### Community 5 - "_check_pick_success"
Cohesion: 0.08
Nodes (34): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), _get_cache(), get_global_stats() (+26 more)

### Community 6 - "compare.py"
Cohesion: 0.07
Nodes (38): dotenv, numpy, openai, pydantic_alias_generators, _are_contradictory(), _call_openrouter(), _canonical_pick_signature(), _combine_nb_params() (+30 more)

### Community 7 - "Outcome"
Cohesion: 0.09
Nodes (30): _combine_legs(), distribution_for_total_line(), Outcome, outcome_hit_value(), outcome_probabilities_for_total(), outcome_return(), Enum, str (+22 more)

### Community 8 - "test_risk.py"
Cohesion: 0.12
Nodes (20): load_risk_limits(), parametrize, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Un valor ininteligible no debe abrir la publicación real. `flase` es un typo…, Verifica que el archivo pick_rules.json contiene la lista de reglas., El defecto NO puede ser dinero real. La calibración solo está validada contra…, El stake se muestra como información del modelo, no como dinero., Detener la publicación no puede ser anulado por pedir modo real. (+12 more)

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
Cohesion: 0.12
Nodes (31): AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs, DashboardSummaryOut (+23 more)

### Community 13 - "Web UI Leagues JS"
Cohesion: 0.13
Nodes (32): addMarketToBlacklist(), applyBulkBlacklist(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry(), escapeAttr() (+24 more)

### Community 14 - "post"
Cohesion: 0.08
Nodes (29): Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, is_underdog_pick(), score_pick_quality(), apply_blacklist(), apply_pick_rules(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest (+21 more)

### Community 15 - "compare_football"
Cohesion: 0.17
Nodes (29): compare_football(), _vi(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda() (+21 more)

### Community 16 - "manual_loader.py"
Cohesion: 0.06
Nodes (38): ABC, DeclarativeBase, pandas, Base, Declarative base for all ORM models., BettingLine, Competition, MarketType (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.09
Nodes (41): brier_score(), expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators. (+33 more)

### Community 18 - "save_analysis"
Cohesion: 0.13
Nodes (16): Exception, _check_payload_has_odds(), _has_valid(), _extract_bookmaker(), _extract_competition(), push_result(), Browser extension pushes match results here (e.g. from flashscore). Tries to…, Extract competition name from payload dict, avoiding json.loads in callers. (+8 more)

### Community 19 - "main.py"
Cohesion: 0.07
Nodes (44): contextlib, copy, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io, middleware (+36 more)

### Community 20 - "BlockReason"
Cohesion: 0.09
Nodes (20): BlockReason, _coerce_reason(), describe(), EligibilityDecision, str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno. (+12 more)

### Community 21 - "test_settlement.py"
Cohesion: 0.19
Nodes (24): line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), settle_total(), Side, parametrize (+16 more)

### Community 22 - "test_stake_and_traceability.py"
Cohesion: 0.05
Nodes (38): compute_edge(), compute_risk_decision(), compute_stake_final(), EdgeResult, kelly_fractional(), Motor de stake y gestión de riesgo. Implementa el cálculo completo de stake…, Descomposición del edge según probabilidades disponibles., Calcula las tres versiones de edge. El edge definitivo (edge_final) usa SIEMPRE… (+30 more)

### Community 23 - "_value_indicator"
Cohesion: 0.08
Nodes (33): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), apply_calibration(), _calculate_display_score(), _calculate_kelly_fraction(), _calculate_stake_units(), calibration_is_active() (+25 more)

### Community 24 - "AnalysisHistory"
Cohesion: 0.06
Nodes (53): delete, field_validator, put, AnalysisHistory, History of manual analyses performed in the comparator., _check_projected_line_success(), deduplicate_competition_matches(), delete_analysis() (+45 more)

### Community 25 - "HierarchicalCalibrator"
Cohesion: 0.09
Nodes (19): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, _build_history_cache_key(), get_calibration_version_for_timestamp(), get_calibrator(), get_calibrator_for_timestamp(), Retorna la versión de la calibración para un timestamp dado o 'unverified'. (+11 more)

### Community 26 - "test_regression_biases.py"
Cohesion: 0.11
Nodes (26): extract_market_line(), line_bucket_for(), load_line_buckets(), MarketFamily, MarketKey, MarketSide, normalize_market_family(), normalize_market_side() (+18 more)

### Community 27 - "admin_database_service.py"
Cohesion: 0.18
Nodes (18): patch, ColumnSchemaInfo, DatabaseRowUpdate, DatabaseTableSchema, get_table_schema(), list_whitelisted_tables(), Any, Session (+10 more)

### Community 28 - "TestFiltering"
Cohesion: 0.16
Nodes (10): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los…, El informe se registra en logs; no debe arrastrar el histórico entero. (+2 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.19
Nodes (25): _clip_0_100(), _explicit_market_support(), _poisson_over_under(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+17 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "market_probability.py"
Cohesion: 0.11
Nodes (20): blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Mezcla controlada: p_final = r * p_calibrated + (1 - r) * p_market donde r =…, Calcula la probabilidad implícita de una cuota decimal (1 / odds). (+12 more)

### Community 32 - "LeagueMathEngine"
Cohesion: 0.06
Nodes (24): calculate_dixon_coles_matrix(), calculate_weighted_average(), dixon_coles_tau(), LeagueMathEngine, _poisson_pmf(), Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0,… (+16 more)

### Community 33 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 34 - "CalibrationCurve"
Cohesion: 0.15
Nodes (9): CalibrationCurve, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_curve_roundtrip_serialization() (+1 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - ".create"
Cohesion: 0.12
Nodes (9): Calcula el hit rate global a nivel de liga para un mercado específico para…, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, TemporalCutoff, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el…, Un partido a las 20:00 en Bogotá es 01:00 UTC del día siguiente. Comparar… (+1 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "test_invariants_and_eligibility.py"
Cohesion: 0.16
Nodes (15): pytest, _as_float(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Lee todos los bloqueos duros ya presentes en un pick, sea dict u objeto.… (+7 more)

### Community 40 - "schemas.py"
Cohesion: 0.23
Nodes (16): pydantic, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut, CompetitionOut, Config (+8 more)

### Community 41 - "test_admin_panel.py"
Cohesion: 0.09
Nodes (37): OperationalFieldsUpdate, PaginationMeta, PickDetailOut, PickItemOut, _dedup_correlated_picks(), export_picks_file(), _extract_picks_from_analysis(), get_pick_detail() (+29 more)

### Community 42 - "parse_utc"
Cohesion: 0.16
Nodes (7): parse_utc(), True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 44 - "pick_rules_engine.py"
Cohesion: 0.18
Nodes (18): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line(), market_side() (+10 more)

### Community 45 - "record_date"
Cohesion: 0.10
Nodes (14): CutoffRequired, FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Reparte los registros en admitidos, posteriores y sin fecha. (+6 more)

### Community 46 - "calibration.py"
Cohesion: 0.23
Nodes (19): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+11 more)

### Community 47 - "backup_db.py"
Cohesion: 0.22
Nodes (10): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), os (+2 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationSample"
Cohesion: 0.12
Nodes (10): CalibrationSample, Una observación histórica para ajustar la calibración., Clave del diseño: con poca muestra el ruido NO puede dominar. 8 observaciones…, test_large_sample_does_move(), test_prior_strength_controls_shrinkage(), test_small_sample_barely_moves_from_prior(), Timestamps futuros no producen peso > 1.0., Walk-forward: train siempre precede al test; no data leakage. (+2 more)

### Community 50 - "is_hard_blocked"
Cohesion: 0.19
Nodes (14): _risk_imports(), is_hard_blocked(), True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., make_pick(), published(), REGRESIÓN: `is_candidate_valid` no miraba `correlation_blocked`, así que una…, test_clean_pick_is_not_hard_blocked(), test_correlated_pick_is_labelled_correlation() (+6 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.08
Nodes (42): asyncio, str, Sport, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success() (+34 more)

### Community 52 - "extract_samples"
Cohesion: 0.24
Nodes (20): extract_samples(), Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _family(), Sin fecha no se puede garantizar ausencia de fuga temporal., Resolver falso: devuelve el outcome legacy asociado a cada selección., Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob., _resolver_map(), _row() (+12 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.18
Nodes (12): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad calibrada, la misma que se muestra. Decidir con…, test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_calibrated_prob() (+4 more)

### Community 54 - "test_train_calibration.py"
Cohesion: 0.20
Nodes (20): random, history_dir_for(), Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. `force` publica el…, train_calibrator(), _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra…, Si el modelo ya está bien calibrado, la curva no puede mejorar de forma… (+12 more)

### Community 55 - "math"
Cohesion: 0.27
Nodes (9): math, DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina. (+1 more)

### Community 56 - "calculate_league_params.py"
Cohesion: 0.13
Nodes (23): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+15 more)

### Community 57 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 58 - "domain.py"
Cohesion: 0.08
Nodes (29): enum, FastAPI, listens_for, sqlalchemy, sqlalchemy_orm, _column_exists(), create_indexes(), init_db() (+21 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.11
Nodes (33): export_stats_file(), Export filtered stats table to CSV or Excel bytes., admin_dashboard_page(), admin_database_page(), admin_mark_recalculation(), admin_picks_page(), admin_root(), admin_stats_page() (+25 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "StatSource"
Cohesion: 0.16
Nodes (10): load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio…, Carga el archivo pick_rules.json y devuelve tuple (rules_list,…, StatSource (+2 more)

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

### Community 67 - "TemporalParameterOptimizer"
Cohesion: 0.15
Nodes (13): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling…, Evalúa un conjunto específico de parámetros usando rolling origin sobre… (+5 more)

### Community 68 - "evaluate_segment_status"
Cohesion: 0.18
Nodes (12): evaluate_segment_status(), get_governance_multipliers(), Evalúa el estado de gobernanza de un segmento según evidencia y configuración…, Retorna los multiplicadores de stake y ajustes de edge según el estado de…, SegmentStatus, Un segmento BLOCKED debe emitir un hard block irrecuperable., TestGovernanceMultipliers, Regression: El segmento debe resolver su curva específica y ser bloqueable. (+4 more)

### Community 69 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 70 - "submit_closing_odds"
Cohesion: 0.20
Nodes (8): match_closing_odds_to_pick(), _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…, Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…, Guarda las cuotas de cierre para los picks de un partido en…, submit_closing_odds()

### Community 72 - "segment_governance.py"
Cohesion: 0.13
Nodes (16): argparse, Connection, pathlib, main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, load_governance_config(), Enum, str (+8 more)

### Community 73 - "walk_forward_calibrate"
Cohesion: 0.24
Nodes (8): evaluate(), SegmentEvaluation, walk_forward_calibrate(), WalkForwardResult, test_improved_is_false_when_calibration_hurts(), test_walk_forward_empty_input(), test_walk_forward_produces_oof_predictions(), test_walk_forward_skips_folds_without_enough_training_data()

### Community 75 - "hard_blocks_from_flags"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 105 - "typing"
Cohesion: 0.16
Nodes (13): datetime, fastapi_testclient, json, logging, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).…, Módulo para la separación entre prediction_universe y selected_portfolio., Ticket 1: Guardar partido sin fecha debe responder 400 Bad Request y detener el… (+5 more)

### Community 106 - "market_group_key"
Cohesion: 0.15
Nodes (14): market_group_key(), Genera la clave canónica del grupo/segmento de mercado., compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento…, R_sample = 1 - exp(-n / target_n) (+6 more)

### Community 107 - "risk.py"
Cohesion: 0.15
Nodes (9): calculate_kelly_stake(), compute_final_stake(), _parse_bool_env(), PublicationMode, Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Calcula la fracción de Kelly base: f* = (b*p - q) / b, stake_final = stake_kelly * reliability_score * data_quality * drift *…, RiskPolicyConfig (+1 more)

### Community 108 - "evaluate_oof_comparison.py"
Cohesion: 0.19
Nodes (13): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos desde CSV. Columnas esperadas (mínimas): date, league,…, Calcula métricas para un conjunto de picks + probabilidades calibradas. (+5 more)

### Community 109 - ".compute_league_averages"
Cohesion: 0.18
Nodes (6): calculate_time_decay_weight(), load_calculated_league_params(), Carga los parámetros matemáticos calculados por liga desde…, Calcula el peso temporal de un partido según la distancia entre su fecha y una…, Calcula los promedios específicos de la liga ponderados por reciencia temporal.…, TestStructuralDecayAndProfiles

### Community 110 - "_dc_score_matrix"
Cohesion: 0.20
Nodes (12): _dc_log_likelihood(), _dc_match_probs(), _dc_score_matrix(), _dc_tau(), _default_dc_rho(), fit_dixon_coles_rho(), _poisson_pmf(), Heurística original — se mantiene como fallback. (+4 more)

### Community 111 - "outcome_from_legacy"
Cohesion: 0.29
Nodes (7): outcome_from_legacy(), Traduce un `PickOutcome` legacy al enum `Outcome`. Un valor desconocido se…, Un valor raro se excluye, no se cuenta como acierto ni como fallo., test_outcome_from_legacy_is_case_insensitive(), test_outcome_from_legacy_is_idempotent(), test_outcome_from_legacy_maps_every_case(), test_outcome_from_legacy_unknown_fails_closed()

### Community 112 - "ExtractionStats"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

### Community 113 - "dataclasses"
Cohesion: 0.32
Nodes (7): dataclasses, evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)., Evalúa la señal H2H sin emitir bloqueos duros para n < 8. Si n >= 8 y el hit…, shrunk_h2h_rate()

### Community 114 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Registro completo de una predicción evaluada en el universo de predicciones., Filtra únicamente las predicciones publicables (cartera seleccionada).

### Community 115 - "stream_football_analysis"
Cohesion: 0.29
Nodes (7): _call_llm_for_result(), Llama al LLM usando las funciones internas de compare.py sin importarlas., Generador SSE genérico: calcula resultado + llama LLM + hace streaming., Stream LLM analysis for a football match via SSE., _sse_stream(), event_generator(), stream_football_analysis()

### Community 117 - "clean_env"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

## Knowledge Gaps
- **32 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 764 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BlockReason` connect `BlockReason` to `test_eligibility.py`, `evaluate_segment_status`, `is_hard`, `compare.py`, `test_invariants_and_eligibility.py`, `test_risk.py`, `test_eligibility_wiring.py`, `hard_blocks_from_flags`, `pick_rules_engine.py`, `compare_football`, `is_hard_blocked`, `parallel_recalc.py`, `PickSnapshot`, `_value_indicator`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `AnalysisHistory` connect `AnalysisHistory` to `train_calibration.py`, `_check_pick_success`, `compare.py`, `submit_closing_odds`, `test_admin_panel.py`, `admin_stats_service.py`, `post`, `manual_loader.py`, `train_model_retrospective.py`, `save_analysis`, `main.py`, `parallel_recalc.py`, `prueba90100.py`, `domain.py`, `admin_database_service.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `compare_football()` connect `compare_football` to `LeagueMathEngine`, `.create`, `compare.py`, `test_eligibility_wiring.py`, `_dc_score_matrix`, `post`, `parallel_recalc.py`, `BlockReason`, `main.py`, `stream_football_analysis`, `_value_indicator`, `calculate_league_params.py`, `_explicit_market_support`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 59 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 59 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `compare_football()` (e.g. with `LeagueMathEngine` and `BlockReason`) actually correct?**
  _`compare_football()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `HierarchicalCalibrator` (e.g. with `train_calibrator()` and `get_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 19 INFERRED edges - model-reasoned connections that need verification._