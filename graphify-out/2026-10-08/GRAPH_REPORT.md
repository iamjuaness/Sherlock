# Graph Report - Sherlock  (2026-10-08)

## Corpus Check
- 120 files · ~511,896 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 2258 nodes · 5320 edges · 123 communities (91 shown, 32 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 351 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3813a4b8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_calibration_temporal.py
- Web UI Comparator JS
- background.js
- test_eligibility.py
- test_count_negative_binomial.py
- evaluate_oof_comparison.py
- compare.py
- Outcome
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- admin_stats_service.py
- leagues.js
- .compute_league_averages
- Any
- domain.py
- test_calibration.py
- save_analysis
- get
- BlockReason
- _invalidate_stats_cache
- compute_segment_report
- _value_indicator
- Session
- risk.py
- line_bucket_for
- test_admin_panel.py
- test_settlement.py
- _explicit_market_support
- manifest.json
- test_invariants_and_eligibility.py
- LeagueMathEngine
- test_compare_integration.py
- CalibrationCurve
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- eligibility.py
- schemas.py
- typing
- parse_utc
- joint_match_distribution.py
- pick_rules_engine.py
- record_date
- calibration.py
- test_regression_biases.py
- train_model_retrospective.py
- _dc_score_matrix
- evaluate_pick_rules
- parallel_recalc.py
- test_train_calibration.py
- PickSnapshot
- CalibrationSample
- count_models.py
- calculate_league_params.py
- _check_pick_success
- database.py
- admin.js
- admin_routes.py
- CardsConvention
- resolve_match_picks_correlation
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- backtesting.py
- evaluate_segment_status
- AnalysisHistory
- HierarchicalCalibrator
- content.js
- update_governance.py
- market_group_key
- 2. Paso a Paso del Nuevo Pipeline
- load_pick_rules_data
- Sport
- sherlock
- math_engine.py
- prueba90100.py
- PredictionRecord
- dataclasses
- split_asian_line
- submit_closing_odds
- compare_football
- main.py
- stake_engine.py
- _get_governance_multiplier
- clean_env
- TestStakeEngine
- apply_blacklist
- PickTrace
- TestKellyFractional
- db_session
- test_threshold_families_match_the_legacy_sets

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 76 edges
2. `AnalysisHistory` - 71 edges
3. `compare_football()` - 61 edges
4. `HierarchicalCalibrator` - 42 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `CalibrationSample` - 34 edges
8. `_value_indicator()` - 33 edges
9. `ReturnDistribution` - 32 edges
10. `good_snapshot()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `calculate_parameters_per_match()` --uses--> `LeagueMathEngine`  [INFERRED]
  calculate_league_params.py → src/core/math_engine.py
- `build_comparison_report()` --uses--> `SegmentStatus`  [INFERRED]
  scripts/evaluate_oof_comparison.py → src/models/segment_governance.py
- `_classify()` --uses--> `SegmentStatus`  [INFERRED]
  scripts/update_governance.py → src/models/segment_governance.py
- `TestStructuralDecayAndProfiles` --uses--> `TemporalParameterOptimizer`  [INFERRED]
  tests/unit/test_structural_decay.py → src/core/backtesting.py
- `db_session()` --uses--> `Base`  [INFERRED]
  tests/unit/test_admin_panel.py → src/core/database.py

## Import Cycles
- None detected.

## Communities (123 total, 32 thin omitted)

### Community 0 - "test_calibration_temporal.py"
Cohesion: 0.16
Nodes (7): get_calibration_version_for_timestamp(), Retorna la versión de la calibración para un timestamp dado o 'unverified'., Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache(), tempfile, Pruebas unitarias para la trazabilidad temporal y la calibración probabilística…, TestCalibrationTemporalTraceability

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

### Community 5 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 6 - "compare.py"
Cohesion: 0.08
Nodes (31): dotenv, numpy, openai, pydantic_alias_generators, _are_contradictory(), _call_openrouter(), _canonical_pick_signature(), _combine_nb_params() (+23 more)

### Community 7 - "Outcome"
Cohesion: 0.08
Nodes (35): _combine_legs(), distribution_for_total_line(), Outcome, outcome_from_legacy(), outcome_hit_value(), outcome_probabilities_for_total(), outcome_return(), Enum (+27 more)

### Community 8 - "test_risk.py"
Cohesion: 0.12
Nodes (21): load_risk_limits(), PublicationMode, parametrize, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Un valor ininteligible no debe abrir la publicación real. `flase` es un typo…, Verifica que el archivo pick_rules.json contiene la lista de reglas., El defecto NO puede ser dinero real. La calibración solo está validada contra…, El stake se muestra como información del modelo, no como dinero. (+13 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (26): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+18 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (33): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+25 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "admin_stats_service.py"
Cohesion: 0.10
Nodes (36): io, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, ColumnSchemaInfo, DashboardChartsData (+28 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - ".compute_league_averages"
Cohesion: 0.14
Nodes (9): calculate_time_decay_weight(), estimate_nb_dispersion(), load_calculated_league_params(), Carga los parámetros matemáticos calculados por liga desde…, Calcula el peso temporal de un partido según la distancia entre su fecha y una…, Estima el parámetro de dispersión (alpha/k) de la Binomial Negativa por Método…, Calcula los promedios específicos de la liga ponderados por reciencia temporal.…, Pruebas unitarias completas para las mejoras estructurales de reciencia… (+1 more)

### Community 15 - "Any"
Cohesion: 0.27
Nodes (23): _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda(), _compute_team_corners_lambda() (+15 more)

### Community 16 - "domain.py"
Cohesion: 0.06
Nodes (39): ABC, DeclarativeBase, enum, pandas, Base, Declarative base for all ORM models., BettingLine, Competition (+31 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.09
Nodes (38): brier_score(), expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators. (+30 more)

### Community 18 - "save_analysis"
Cohesion: 0.13
Nodes (16): Exception, _check_payload_has_odds(), _has_valid(), _extract_bookmaker(), _extract_competition(), push_result(), Browser extension pushes match results here (e.g. from flashscore). Tries to…, Extract competition name from payload dict, avoiding json.loads in callers. (+8 more)

### Community 19 - "get"
Cohesion: 0.08
Nodes (29): middleware, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version(), get_pending_closing_odds_matches(), get_pending_picks_competitions() (+21 more)

### Community 20 - "BlockReason"
Cohesion: 0.08
Nodes (24): BlockReason, _coerce_reason(), describe(), EligibilityDecision, is_hard(), str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos. (+16 more)

### Community 21 - "_invalidate_stats_cache"
Cohesion: 0.10
Nodes (19): delete, put, deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches(), _invalidate_stats_cache(), Any (+11 more)

### Community 22 - "compute_segment_report"
Cohesion: 0.23
Nodes (7): compute_segment_report(), generate_segment_reports(), Reporte completo de un segmento league+family+side+bucket. Incluye: picks, hit…, Calcula el reporte completo de un segmento a partir de sus traces y resultados.…, Agrupa traces por segment_key y genera un SegmentReport para cada uno. Returns:…, SegmentReport, TestSegmentReports

### Community 23 - "_value_indicator"
Cohesion: 0.10
Nodes (30): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), apply_calibration(), _build_history_cache_key(), _calculate_stake_units(), calibration_is_active(), _calibration_line_bucket() (+22 more)

### Community 24 - "Session"
Cohesion: 0.08
Nodes (36): Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache(), score_pick_quality(), apply_pick_rules(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest (+28 more)

### Community 25 - "risk.py"
Cohesion: 0.13
Nodes (13): compute_final_stake(), _parse_bool_env(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, stake_final = stake_kelly * reliability_score * data_quality * drift *…, RiskPolicyConfig, StakeCalculationResult, compute_distribution_kelly(), compute_risk_decision() (+5 more)

### Community 26 - "line_bucket_for"
Cohesion: 0.12
Nodes (9): line_bucket_for(), load_line_buckets(), Determina la banda de línea (line_bucket) para una familia y número de línea…, Carga bandas de línea desde un archivo JSON si existe, o retorna las…, test_line_buckets(), Regression: Debe resolverse con banda core y calibración específica., Regression: Debe usar high/extreme bucket, no la curva genérica de goals over., TestArgentinaShotsTargetUnderCore (+1 more)

### Community 27 - "test_admin_panel.py"
Cohesion: 0.09
Nodes (37): fastapi_testclient, patch, DatabaseRowsOut, DatabaseRowUpdate, OperationalFieldsUpdate, PaginationMeta, get_table_schema(), list_whitelisted_tables() (+29 more)

### Community 28 - "test_settlement.py"
Cohesion: 0.17
Nodes (26): line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), _settle_simple_total(), settle_total() (+18 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.22
Nodes (24): _clip_0_100(), _explicit_market_support(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico., stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+16 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "test_invariants_and_eligibility.py"
Cohesion: 0.11
Nodes (22): pytest, blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Mezcla controlada: p_final = r * p_calibrated + (1 - r) * p_market donde r =… (+14 more)

### Community 32 - "LeagueMathEngine"
Cohesion: 0.08
Nodes (16): LeagueMathEngine, Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa…, Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás., Capa 3: Calcula estadísticas promedio del equipo `team_name` en ventanas… (+8 more)

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
Cohesion: 0.07
Nodes (21): Calcula el hit rate global a nivel de liga para un mercado específico para…, filter_before_cutoff(), Any, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff… (+13 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "eligibility.py"
Cohesion: 0.13
Nodes (18): _as_float(), hard_blocks_from_flags(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Lee todos los bloqueos duros ya presentes en un pick, sea dict u objeto.… (+10 more)

### Community 40 - "schemas.py"
Cohesion: 0.23
Nodes (16): pydantic, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut, CompetitionOut, Config (+8 more)

### Community 41 - "typing"
Cohesion: 0.08
Nodes (35): datetime, json, sqlalchemy, AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., market_group(), Clave familia_lado usada para consultar data/market_correlation.json., Módulo para la separación entre prediction_universe y selected_portfolio.… (+27 more)

### Community 42 - "parse_utc"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 44 - "pick_rules_engine.py"
Cohesion: 0.19
Nodes (12): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_line(), normalize_text(), Motor único de reglas de picks para Sherlock.… (+4 more)

### Community 45 - "record_date"
Cohesion: 0.10
Nodes (13): CutoffRequired, FilterReport, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Reparte los registros en admitidos, posteriores y sin fecha., Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y… (+5 more)

### Community 46 - "calibration.py"
Cohesion: 0.17
Nodes (21): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+13 more)

### Community 47 - "test_regression_biases.py"
Cohesion: 0.15
Nodes (19): extract_market_line(), MarketFamily, MarketKey, MarketSide, normalize_market_family(), normalize_market_side(), parse_market(), Enum (+11 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "_dc_score_matrix"
Cohesion: 0.20
Nodes (12): _dc_log_likelihood(), _dc_match_probs(), _dc_score_matrix(), _dc_tau(), _default_dc_rho(), fit_dixon_coles_rho(), _poisson_pmf(), Heurística original — se mantiene como fallback. (+4 more)

### Community 50 - "evaluate_pick_rules"
Cohesion: 0.16
Nodes (10): evaluate_pick_rules(), market_side(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio…, Devuelve (is_blocked, reason) si selection es una string. Si selection es una… (+2 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.16
Nodes (20): asyncio, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line() (+12 more)

### Community 52 - "test_train_calibration.py"
Cohesion: 0.06
Nodes (67): random, re, _coerce_cutoff_datetime(), _coerce_datetime(), extract_samples(), ExtractionStats, history_dir_for(), _league_already_calibrated() (+59 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.18
Nodes (12): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad final (final_prob) o calibrada (calibrated_prob)., test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_final_prob_and_calibrated_prob() (+4 more)

### Community 54 - "CalibrationSample"
Cohesion: 0.15
Nodes (11): CalibrationSample, evaluate(), Una observación histórica para ajustar la calibración., SegmentEvaluation, walk_forward_calibrate(), WalkForwardResult, test_improved_is_false_when_calibration_hurts(), test_walk_forward_empty_input() (+3 more)

### Community 55 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 56 - "calculate_league_params.py"
Cohesion: 0.15
Nodes (21): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+13 more)

### Community 57 - "_check_pick_success"
Cohesion: 0.08
Nodes (37): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), get_all_picks(), _get_cache() (+29 more)

### Community 58 - "database.py"
Cohesion: 0.13
Nodes (16): FastAPI, listens_for, sqlalchemy_orm, _column_exists(), create_indexes(), init_db(), Database engine, session factory and Base for SQLAlchemy models., Create indexes for analysis_history and related tables. (+8 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.11
Nodes (33): fastapi_responses, fastapi_templating, admin_dashboard_page(), admin_database_page(), admin_mark_recalculation(), admin_picks_page(), admin_root(), admin_stats_page() (+25 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "resolve_match_picks_correlation"
Cohesion: 0.18
Nodes (18): resolve_match_picks_correlation(), get_attr(), is_candidate_valid(), pick_merit_score(), _risk_imports(), is_hard_blocked(), True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., make_pick() (+10 more)

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
Cohesion: 0.14
Nodes (15): logging, calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de… (+7 more)

### Community 68 - "evaluate_segment_status"
Cohesion: 0.12
Nodes (20): main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str, Módulo para el monitor de drift y la gobernanza automática de segmentos. (+12 more)

### Community 69 - "AnalysisHistory"
Cohesion: 0.12
Nodes (22): field_validator, AnalysisHistory, History of manual analyses performed in the comparator., _check_projected_line_success(), get_analysis_by_id(), get_league_matches(), list_analysis(), _populate_history_extra_fields() (+14 more)

### Community 70 - "HierarchicalCalibrator"
Cohesion: 0.15
Nodes (14): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, make_samples(), Menos de min_samples -> identidad, nunca una corrección inventada., Genera muestras sintéticas con una relación conocida prob->acierto., test_apply_is_deterministic(), test_artifact_is_versioned() (+6 more)

### Community 72 - "update_governance.py"
Cohesion: 0.08
Nodes (31): argparse, backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup() (+23 more)

### Community 73 - "market_group_key"
Cohesion: 0.15
Nodes (14): market_group_key(), Genera la clave canónica del grupo/segmento de mercado., compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento…, R_sample = 1 - exp(-n / target_n) (+6 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 75 - "load_pick_rules_data"
Cohesion: 0.33
Nodes (6): load_pick_rules_data(), Carga el archivo pick_rules.json y devuelve tuple (rules_list,…, is_pick_blocked_by_rules(), Checks pick_rules.json using the unified pick_rules_engine. If a rule is…, Filtra picks correlacionados en un mismo evento garantizando la máxima…, resolve_match_picks_correlation()

### Community 76 - "Sport"
Cohesion: 0.13
Nodes (19): Sport, Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), CompareResponse, _annotate_best_bookmaker(), _apply_line_shopping(), compare_teams_football(), _enrich_with_results() (+11 more)

### Community 105 - "math_engine.py"
Cohesion: 0.15
Nodes (12): math, calculate_dixon_coles_matrix(), calculate_weighted_average(), dixon_coles_tau(), _poisson_pmf(), Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).…, Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0,…, Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste… (+4 more)

### Community 106 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 107 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones.

### Community 108 - "dataclasses"
Cohesion: 0.15
Nodes (13): dataclasses, _compute_ece(), Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, Expected Calibration Error con n_bins bins uniformes., Genera recomendación operativa simple basada en métricas., _recommend(), _safe_log(), evaluate_h2h_signal() (+5 more)

### Community 109 - "split_asian_line"
Cohesion: 0.29
Nodes (6): _neg_bin_pmf(), _neg_binomial_over_under(), _get_single_line_probs(), _poisson_over_under(), Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., split_asian_line()

### Community 110 - "submit_closing_odds"
Cohesion: 0.20
Nodes (8): match_closing_odds_to_pick(), _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…, Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…, Guarda las cuotas de cierre para los picks de un partido en…, submit_closing_odds()

### Community 111 - "compare_football"
Cohesion: 0.11
Nodes (13): apply_portfolio_exposure_cap(), Aplica Simultaneous Kelly Scaling sobre una lista de ValueIndicator…, compare_football(), FootballCompareRequest, get_nbinom_under_over_prob(), is_underdog_pick(), Preprocesa y sanea las estadísticas del equipo para garantizar consistencia…, NOTA DE FIX: Se agregaron los parámetros explícitos `exclude_match_id` y… (+5 more)

### Community 112 - "main.py"
Cohesion: 0.08
Nodes (28): contextlib, copy, fastapi_middleware_cors, fastapi_staticfiles, openpyxl, openpyxl_utils, _call_llm_for_result(), _get_or_create_team() (+20 more)

### Community 113 - "stake_engine.py"
Cohesion: 0.18
Nodes (9): pathlib, compute_edge(), EdgeResult, optimize_simultaneous_portfolio(), Motor de stake y gestión de riesgo institucional de Sherlock. Sustituye la…, Escala proporcionalmente las apuestas simultáneas para respetar la exposición…, RiskDecision, Tests del motor de stake y trazabilidad. (+1 more)

### Community 114 - "_get_governance_multiplier"
Cohesion: 0.50
Nodes (4): _get_governance_multiplier(), get_segment_governance(), Resuelve el status de gobernanza y el multiplicador de stake para un segmento.…, Devuelve el artefacto de gobernanza completo, recargandolo si cambio en disco.…

### Community 115 - "clean_env"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

### Community 116 - "TestStakeEngine"
Cohesion: 0.33
Nodes (3): compute_stake_final(), Calcula el stake final aplicando ajuste de factores, drawdown scale y límites., TestStakeEngine

### Community 117 - "apply_blacklist"
Cohesion: 0.21
Nodes (10): _calculate_display_score(), get_market_stake_modifier_for_league(), is_market_blacklisted_for_league(), _market_line(), _market_side(), _normalize_text(), Comprueba reglas de blacklist por: liga, familia, lado, línea y categoría. La…, Obtiene el multiplicador de stake para un mercado en una liga según… (+2 more)

### Community 118 - "PickTrace"
Cohesion: 0.32
Nodes (4): PickTrace, Snapshot inmutable de trazabilidad de un pick para audit y reportes. Contiene…, _make_trace(), TestPickTrace

### Community 121 - "db_session"
Cohesion: 0.67
Nodes (3): db_session(), fixture, Create a temporary SQLite DB session for testing admin functionality.

## Knowledge Gaps
- **40 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+35 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 789 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `compare.py`, `typing`, `prueba90100.py`, `admin_stats_service.py`, `Sport`, `submit_closing_odds`, `domain.py`, `train_model_retrospective.py`, `main.py`, `get`, `test_train_calibration.py`, `apply_blacklist`, `_invalidate_stats_cache`, `save_analysis`, `Session`, `_check_pick_success`, `database.py`, `test_admin_panel.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `backtesting.py`, `.create`, `.compute_pick_hit_rate`, `compare.py`, `math_engine.py`, `record_date`, `.compute_league_averages`, `compare_football`, `main.py`, `save_analysis`, `calculate_league_params.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `test_eligibility.py`, `evaluate_segment_status`, `compare.py`, `eligibility.py`, `test_risk.py`, `test_eligibility_wiring.py`, `pick_rules_engine.py`, `compare_football`, `evaluate_pick_rules`, `PickSnapshot`, `_value_indicator`, `resolve_match_picks_correlation`, `test_invariants_and_eligibility.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 59 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 59 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `compare_football()` (e.g. with `LeagueMathEngine` and `BlockReason`) actually correct?**
  _`compare_football()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `HierarchicalCalibrator` (e.g. with `train_calibrator()` and `get_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 19 INFERRED edges - model-reasoned connections that need verification._