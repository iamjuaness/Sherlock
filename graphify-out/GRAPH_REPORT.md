# Graph Report - Sherlock  (2026-10-03)

## Corpus Check
- 94 files · ~265,343 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 1921 nodes · 4478 edges · 113 communities (81 shown, 32 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 314 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dac56fc7`
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
- load_risk_limits
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- admin_stats_service.py
- Web UI Leagues JS
- Session
- compare_football
- domain.py
- test_calibration.py
- save_analysis
- main.py
- EligibilityDecision
- test_settlement.py
- database.py
- _value_indicator
- AnalysisHistory
- test_calibration_temporal.py
- get
- admin_database_service.py
- .create
- _explicit_market_support
- manifest.json
- math_engine.py
- LeagueMathEngine
- test_compare_integration.py
- CalibrationCurve
- test_calibration_wiring.py
- dashboard_main.js
- BlockReason
- .compute_pick_hit_rate
- eligibility.py
- schemas.py
- test_admin_panel.py
- parse_utc
- HierarchicalCalibrator
- pick_rules_engine.py
- TemporalCutoff
- calibration.py
- backup_db.py
- train_model_retrospective.py
- CalibrationSample
- test_risk.py
- parallel_recalc.py
- extract_samples
- PickSnapshot
- test_train_calibration.py
- settlement.py
- calculate_league_params.py
- prueba90100.py
- datetime
- admin.js
- admin_routes.py
- CardsConvention
- recalculate_all_accuracy
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- backtesting.py
- generate_football_analysis
- is_hard
- _normalize_betano_odds
- content.js
- Sport
- walk_forward_calibrate
- .test_10_train_calibration_until_date_cutoff
- hard_blocks_from_flags
- re
- sherlock
- pytest
- _clean_calibrator
- RiskLimits
- test_no_artifact_keeps_legacy_082_shrink
- test_kelly_tiny_edge_is_tiny_but_positive
- make_samples
- outcome_from_legacy
- ExtractionStats

## God Nodes (most connected - your core abstractions)
1. `AnalysisHistory` - 71 edges
2. `BlockReason` - 70 edges
3. `compare_football()` - 58 edges
4. `Outcome` - 40 edges
5. `LeagueMathEngine` - 37 edges
6. `HierarchicalCalibrator` - 36 edges
7. `good_snapshot()` - 32 edges
8. `extract_samples()` - 29 edges
9. `ReturnDistribution` - 29 edges
10. `resolve_match_picks_correlation()` - 28 edges

## Surprising Connections (you probably didn't know these)
- `test_hard_and_soft_reasons_are_disjoint()` --uses--> `BlockReason`  [INFERRED]
  tests/unit/test_eligibility.py → src/domain/eligibility.py
- `calculate_parameters_per_match()` --uses--> `LeagueMathEngine`  [INFERRED]
  calculate_league_params.py → src/core/math_engine.py
- `db_session()` --uses--> `Base`  [INFERRED]
  tests/unit/test_admin_panel.py → src/core/database.py
- `test_operational_fields_update_and_audit()` --uses--> `AdminAuditLog`  [INFERRED]
  tests/unit/test_admin_panel.py → src/core/domain.py
- `TestStructuralDecayAndProfiles` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/unit/test_structural_decay.py → src/core/math_engine.py

## Import Cycles
- None detected.

## Communities (113 total, 32 thin omitted)

### Community 0 - "train_calibration.py"
Cohesion: 0.11
Nodes (20): _extract_line_bucket(), _league_already_calibrated(), main(), _normalize_market_text(), _pick_probability(), Path, Entrenamiento del calibrador de Sherlock a partir de picks liquidados. Flujo…, Un partido sirve si tiene al menos el marcador final. (+12 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "test_eligibility.py"
Cohesion: 0.11
Nodes (34): evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., good_snapshot(), parametrize, Tests del dominio de elegibilidad. Invariante central: la elegibilidad es…, Centralizar los umbrales no debe cambiar qué mercados se publican. (+26 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "_check_pick_success"
Cohesion: 0.07
Nodes (41): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _check_projected_line_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), get_all_picks() (+33 more)

### Community 6 - "compare.py"
Cohesion: 0.06
Nodes (44): dotenv, numpy, openai, pydantic_alias_generators, _combine_nb_params(), _compute_league_reliability_score(), _dc_component_weights(), _dc_log_likelihood() (+36 more)

### Community 7 - "Outcome"
Cohesion: 0.16
Nodes (17): Outcome, outcome_hit_value(), outcome_return(), Enum, str, Resultados posibles de una apuesta liquidada., Convierte un outcome + cuota en retorno económico. Si el pick no puede…, Retorno NETO (profit) por 1 unidad apostada, en cuota decimal. WIN -> +(odds -… (+9 more)

### Community 8 - "load_risk_limits"
Cohesion: 0.09
Nodes (26): os, _env_bool(), load_risk_limits(), PublicationMode, Any, Enum, str, Límites de riesgo y kill switch de publicación. Por qué está separado de… (+18 more)

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
Nodes (32): AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs, DashboardSummaryOut (+24 more)

### Community 13 - "Web UI Leagues JS"
Cohesion: 0.13
Nodes (32): addMarketToBlacklist(), applyBulkBlacklist(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry(), escapeAttr() (+24 more)

### Community 14 - "Session"
Cohesion: 0.10
Nodes (29): apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, BaseModel, post, Session (+21 more)

### Community 15 - "compare_football"
Cohesion: 0.17
Nodes (28): compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda() (+20 more)

### Community 16 - "domain.py"
Cohesion: 0.07
Nodes (38): ABC, DeclarativeBase, enum, pandas, Base, Declarative base for all ORM models., BettingLine, Competition (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.11
Nodes (29): random, brier_score(), expected_calibration_error(), log_loss(), pava(), Construye muestras desde filas liquidadas, excluyendo push y unsettled. Espera…, Regresión isotónica ponderada por Pool Adjacent Violators. Devuelve la…, Error cuadrático medio de la probabilidad. Menor es mejor. (+21 more)

### Community 18 - "save_analysis"
Cohesion: 0.12
Nodes (18): Exception, _check_payload_has_odds(), _has_valid(), _extract_bookmaker(), _extract_competition(), push_result(), quick_save_match(), Browser extension pushes match results here (e.g. from flashscore). Tries to… (+10 more)

### Community 19 - "main.py"
Cohesion: 0.07
Nodes (31): contextlib, copy, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io, openpyxl (+23 more)

### Community 20 - "EligibilityDecision"
Cohesion: 0.09
Nodes (14): describe(), EligibilityDecision, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Une dos decisiones sobre el mismo pick. Los bloqueos duros se unen (nunca se…, Devuelve el `quality_score` que corresponde publicar. Un pick con bloqueo duro…, Reconstruye una decisión desde una lista plana de motivos, separando duros de…, Rehidratar un motivo desconocido no debe soltar el bloqueo. (+6 more)

### Community 21 - "test_settlement.py"
Cohesion: 0.16
Nodes (28): _combine_legs(), line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Combina los resultados de las piernas (cada una con media unidad). Solo se usan…, Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap() (+20 more)

### Community 22 - "database.py"
Cohesion: 0.16
Nodes (13): FastAPI, listens_for, sqlalchemy, _column_exists(), create_indexes(), init_db(), Database engine, session factory and Base for SQLAlchemy models., Create indexes for analysis_history and related tables. (+5 more)

### Community 23 - "_value_indicator"
Cohesion: 0.09
Nodes (30): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), apply_calibration(), _calculate_display_score(), _calculate_kelly_fraction(), _calculate_stake_units(), calibration_is_active() (+22 more)

### Community 24 - "AnalysisHistory"
Cohesion: 0.11
Nodes (21): delete, put, AnalysisHistory, History of manual analyses performed in the comparator., deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches() (+13 more)

### Community 25 - "test_calibration_temporal.py"
Cohesion: 0.13
Nodes (11): _build_history_cache_key(), get_calibration_version_for_timestamp(), get_calibrator_for_timestamp(), Retorna la versión de la calibración para un timestamp dado o 'unverified'., Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., Clave de caché basada en los paths y mtimes de los artefactos., Devuelve el calibrador activo en el momento predicted_at según el historial de…, reset_calibrator_cache() (+3 more)

### Community 26 - "get"
Cohesion: 0.08
Nodes (29): middleware, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version(), get_analysis_by_id(), get_league_matches() (+21 more)

### Community 27 - "admin_database_service.py"
Cohesion: 0.18
Nodes (18): patch, ColumnSchemaInfo, DatabaseRowUpdate, DatabaseTableSchema, get_table_schema(), list_whitelisted_tables(), Any, Session (+10 more)

### Community 28 - ".create"
Cohesion: 0.08
Nodes (20): CutoffRequired, filter_before_cutoff(), Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, Invariantes del cutoff temporal. La propiedad que se defiende aquí es una sola…, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el… (+12 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.19
Nodes (25): _clip_0_100(), _explicit_market_support(), _poisson_over_under(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+17 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "math_engine.py"
Cohesion: 0.15
Nodes (11): calculate_dixon_coles_matrix(), calculate_weighted_average(), dixon_coles_tau(), _poisson_pmf(), Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).…, Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0,…, Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste…, Calcula el promedio con decay exponencial según antigüedad. half_life: número… (+3 more)

### Community 32 - "LeagueMathEngine"
Cohesion: 0.07
Nodes (18): fastapi_testclient, LeagueMathEngine, Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa…, Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás. (+10 more)

### Community 33 - "test_compare_integration.py"
Cohesion: 0.09
Nodes (15): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., El push no consume banca, así que el stake óptimo es mayor., El bug: EV se calculaba como (p·odds - 1)·(1 - p_push), tratando el push como… (+7 more)

### Community 34 - "CalibrationCurve"
Cohesion: 0.16
Nodes (10): CalibrationCurve, Mapa monótono lineal por tramos de probabilidad raw -> calibrada. Los nodos…, Aplica la calibración. Acepta 0-1 o 0-100 y devuelve en la MISMA escala., Interpolación lineal entre nodos observados. Fuera del rango cubierto por los…, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale() (+2 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.14
Nodes (15): src_ui_api, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., El 0.82 y la curva corrigen el MISMO sesgo. Aplicar ambos lo castiga dos veces,…, test_artifact_reloads_when_file_changes(), test_calibration_flows_into_ev_and_kelly(), test_calibration_is_deterministic_across_calls() (+7 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - "BlockReason"
Cohesion: 0.16
Nodes (19): BlockReason, _coerce_reason(), evaluate_eligibility(), str, Añade bloqueos duros. Nunca quita ninguno., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, Motivos por los que un pick no se publica., EL BUG ORIGINAL: recalcular con un pick que pasa todos los filtros devolvía… (+11 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "eligibility.py"
Cohesion: 0.22
Nodes (13): dataclasses, _risk_imports(), _as_float(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema… (+5 more)

### Community 40 - "schemas.py"
Cohesion: 0.18
Nodes (19): field_validator, pydantic, AnalysisHistoryOut, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut (+11 more)

### Community 41 - "test_admin_panel.py"
Cohesion: 0.08
Nodes (40): OperationalFieldsUpdate, PaginationMeta, PickDetailOut, PickItemOut, _dedup_correlated_picks(), export_picks_file(), _extract_picks_from_analysis(), get_pick_detail() (+32 more)

### Community 42 - "parse_utc"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "HierarchicalCalibrator"
Cohesion: 0.19
Nodes (9): HierarchicalCalibrator, Path, Calibrador jerárquico que prioriza evidencia de liga manteniendo control…, Calibra una probabilidad y conserva su escala de entrada. Entrada 0-1 -> salida…, get_calibrator(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.…, test_load_rejects_unknown_format_version(), test_save_load_roundtrip() (+1 more)

### Community 44 - "pick_rules_engine.py"
Cohesion: 0.18
Nodes (18): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line(), market_side() (+10 more)

### Community 45 - "TemporalCutoff"
Cohesion: 0.09
Nodes (13): FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente… (+5 more)

### Community 46 - "calibration.py"
Cohesion: 0.30
Nodes (12): _clean_segment_value(), directional_key(), family_key(), league_key(), line_key(), Calibración probabilística real de Sherlock. SIN GLM. Por qué no GLM / stacking…, Devuelve la curva más específica disponible. Prioriza los datos de la liga…, Ajusta la jerarquía completa con partial pooling. (+4 more)

### Community 47 - "backup_db.py"
Cohesion: 0.24
Nodes (9): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), shutil (+1 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationSample"
Cohesion: 0.15
Nodes (14): CalibrationSample, fit_curve(), _quantile_edges(), Un bin de la curva de reliability, con su evidencia., Bordes de bin por cuantiles, garantizando ocupación mínima., Ajusta una curva por Beta-Binomial + isotónica PAVA. Mejoras frente a la…, Una observación histórica para ajustar la calibración. `prob` puede venir en…, ReliabilityBin (+6 more)

### Community 50 - "test_risk.py"
Cohesion: 0.17
Nodes (19): is_hard_blocked(), True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., clean_env(), make_pick(), published(), fixture, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Verifica que el archivo pick_rules.json contiene la lista de reglas. (+11 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.12
Nodes (23): asyncio, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line() (+15 more)

### Community 52 - "extract_samples"
Cohesion: 0.24
Nodes (20): extract_samples(), Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _family(), Sin fecha no se puede garantizar ausencia de fuga temporal., Resolver falso: devuelve el outcome legacy asociado a cada selección., Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob., _resolver_map(), _row() (+12 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.27
Nodes (10): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad calibrada, la misma que se muestra. Decidir con…, test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_calibrated_prob() (+2 more)

### Community 54 - "test_train_calibration.py"
Cohesion: 0.22
Nodes (19): history_dir_for(), Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. `force` publica el…, train_calibrator(), _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra…, Si el modelo ya está bien calibrado, la curva no puede mejorar de forma…, Regresión: el historial se derivaba de una constante global, así que entrenar… (+11 more)

### Community 55 - "settlement.py"
Cohesion: 0.17
Nodes (12): functools, math, distribution_for_total_line(), outcome_probabilities_for_total(), Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de…, Liquida un mercado binario sin push (BTTS, 1X2, doble oportunidad). Falla…, Convierte una PMF del total (determinista) en probabilidades de outcome para…, Atajo: PMF de totales -> ReturnDistribution lista para EV/Kelly. (+4 more)

### Community 56 - "calculate_league_params.py"
Cohesion: 0.10
Nodes (27): argparse, calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary() (+19 more)

### Community 57 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 58 - "datetime"
Cohesion: 0.14
Nodes (15): datetime, json, sqlalchemy_orm, AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., migrate_picks_snapshots(), Session, Script de migración aditiva e idempotente para snapshots de calibración en… (+7 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.11
Nodes (33): export_stats_file(), Export filtered stats table to CSV or Excel bytes., admin_dashboard_page(), admin_database_page(), admin_mark_recalculation(), admin_picks_page(), admin_root(), admin_stats_page() (+25 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "recalculate_all_accuracy"
Cohesion: 0.09
Nodes (28): Procesa un chunk de partidos en un proceso secundario (worker)., _recalc_chunk(), evaluate_pick_rules(), load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -… (+20 more)

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

### Community 67 - "backtesting.py"
Cohesion: 0.07
Nodes (26): logging, calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de… (+18 more)

### Community 68 - "generate_football_analysis"
Cohesion: 0.16
Nodes (12): _are_contradictory(), _call_openrouter(), _canonical_pick_signature(), _deduplicate_correlated_picks(), generate_football_analysis(), get_market_stake_modifier_for_league(), is_market_blacklisted_for_league(), _is_too_similar() (+4 more)

### Community 69 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 70 - "_normalize_betano_odds"
Cohesion: 0.33
Nodes (4): _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…

### Community 72 - "Sport"
Cohesion: 0.14
Nodes (14): str, Sport, _enrich_with_results(), list_analysis(), list_competitions(), list_matches(), list_sports(), List competitions with optional sport filter. (+6 more)

### Community 73 - "walk_forward_calibrate"
Cohesion: 0.17
Nodes (11): evaluate(), Walk-forward estricto por grupos temporales. Un mismo timestamp se trata como…, Resumen de calidad probabilística., Predicciones OOF y métricas antes/después de calibrar., Regla de promoción: la calibración solo se acepta si mejora Brier Y log loss…, walk_forward_calibrate(), WalkForwardResult, test_improved_is_false_when_calibration_hurts() (+3 more)

### Community 74 - ".test_10_train_calibration_until_date_cutoff"
Cohesion: 0.15
Nodes (7): _coerce_cutoff_datetime(), _coerce_datetime(), load_rows_from_db(), Any, datetime, Como `_coerce_datetime` pero si el valor es solo una fecha (YYYY-MM-DD) la…, Lee `analysis_history` y devuelve dicts planos. Solo trae filas con marcador…

### Community 75 - "hard_blocks_from_flags"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 105 - "pytest"
Cohesion: 0.50
Nodes (3): pytest, Verifica que al guardar un análisis sin count_in_profitability explícito: - Si…, test_save_analysis_respects_profitable_leagues()

### Community 106 - "_clean_calibrator"
Cohesion: 0.67
Nodes (3): _clean_calibrator(), fixture, Aísla cada test con su propia ruta de artefacto y caché limpia.

### Community 107 - "RiskLimits"
Cohesion: 0.17
Nodes (8): Política de riesgo efectiva. Inmutable: se resuelve una vez y se pasa., False solo cuando el kill switch está echado., Stake que se puede arriesgar de verdad. En PAPER y HALTED es siempre 0: el…, RiskLimits, test_describe_mentions_the_mode(), test_halted_mode_blocks_every_pick(), test_limits_are_immutable(), test_to_dict_exposes_the_mode()

### Community 110 - "make_samples"
Cohesion: 0.14
Nodes (14): make_samples(), El audit: 'la curva de calibración muestra sobreconfianza fuerte en…, Si el modelo ya está calibrado, la curva debe quedarse cerca de la identidad., Menos de min_samples -> identidad, nunca una corrección inventada., Genera muestras sintéticas con una relación conocida prob->acierto., test_apply_is_deterministic(), test_artifact_is_versioned(), test_corrects_systematic_overconfidence() (+6 more)

### Community 111 - "outcome_from_legacy"
Cohesion: 0.29
Nodes (7): outcome_from_legacy(), Traduce un `PickOutcome` legacy al enum `Outcome`. Un valor desconocido se…, Un valor raro se excluye, no se cuenta como acierto ni como fallo., test_outcome_from_legacy_is_case_insensitive(), test_outcome_from_legacy_is_idempotent(), test_outcome_from_legacy_maps_every_case(), test_outcome_from_legacy_unknown_fails_closed()

### Community 112 - "ExtractionStats"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

## Knowledge Gaps
- **32 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 686 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `backtesting.py`, `.compute_pick_hit_rate`, `compare.py`, `TemporalCutoff`, `compare_football`, `save_analysis`, `main.py`, `calculate_league_params.py`, `.create`, `math_engine.py`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `test_eligibility.py`, `is_hard`, `compare.py`, `eligibility.py`, `test_eligibility_wiring.py`, `hard_blocks_from_flags`, `pick_rules_engine.py`, `compare_football`, `test_risk.py`, `EligibilityDecision`, `PickSnapshot`, `_value_indicator`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `compare_football()` connect `compare_football` to `LeagueMathEngine`, `backtesting.py`, `generate_football_analysis`, `BlockReason`, `compare.py`, `test_eligibility_wiring.py`, `TemporalCutoff`, `parallel_recalc.py`, `main.py`, `_value_indicator`, `.create`, `_explicit_market_support`, `recalculate_all_accuracy`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 50 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 55 inferred relationships involving `BlockReason` (e.g. with `resolve_match_picks_correlation()` and `_risk_imports()`) actually correct?**
  _`BlockReason` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `compare_football()` (e.g. with `LeagueMathEngine` and `BlockReason`) actually correct?**
  _`compare_football()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Outcome` (e.g. with `extract_samples()` and `under_over_probabilities()`) actually correct?**
  _`Outcome` has 17 INFERRED edges - model-reasoned connections that need verification._