# Graph Report - Sherlock  (2026-10-31)

## Corpus Check
- 137 files · ~547,777 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 3, .example 1, .db 1)

## Summary
- 2462 nodes · 5715 edges · 120 communities (89 shown, 31 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 378 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `51903f20`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HierarchicalCalibrator
- Web UI Comparator JS
- background.js
- BlockReason
- test_count_negative_binomial.py
- test_compare_integration.py
- compare_football
- Outcome
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- Session
- leagues.js
- test_train_calibration.py
- get
- manual_loader.py
- test_calibration.py
- extract_samples
- generate_football_analysis
- EligibilityDecision
- save_analysis
- test_stake_and_traceability.py
- Rules
- evaluate_oof_comparison.py
- backup_db.py
- train_calibration.py
- admin_stats_service.py
- test_settlement.py
- _explicit_market_support
- manifest.json
- market_probability.py
- datetime
- recalculate_all_accuracy
- schemas.py
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- TemporalCutoff
- TemporalParameterOptimizer
- test_quantitative_math.py
- .compute_league_averages
- derive_joint_match_probabilities
- AnalysisHistory
- parse_utc
- models/calibration.py
- test_regression_biases.py
- train_model_retrospective.py
- get_table_schema
- _compute_league_season_corners
- parallel_recalc.py
- Gemini Notebook Automation
- eligibility.py
- NotebookLMService
- count_models.py
- calculate_league_params.py
- _check_pick_success
- submit_closing_odds
- admin.js
- get
- CardsConvention
- _compute_league_reliability_score
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- typing
- test_invariants_and_eligibility.py
- FilterReport
- pick_rules_engine.py
- content.js
- json
- test_admin_panel.py
- 2. Paso a Paso del Nuevo Pipeline
- h2h_shrinkage.py
- TOKEN OPTIMIZATION & SKILLS PROTOCOL
- Ponytail
- _set_sqlite_pragma
- sherlock
- LeagueMathEngine
- prueba90100.py
- _value_indicator
- Session
- main.py
- portfolio.py
- RiskPolicyConfig
- outcome_from_legacy
- math/calibration.py
- ExtractionStats
- admin_routes.py
- TrainingReport
- math/__init__.py
- compare.py

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 79 edges
2. `AnalysisHistory` - 74 edges
3. `compare_football()` - 73 edges
4. `HierarchicalCalibrator` - 46 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 36 edges
8. `CalibrationSample` - 35 edges
9. `ReturnDistribution` - 32 edges
10. `_value_indicator()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `TAREA 3: CALIBRACIÓN EXCLUSIVA BASADA EN DATOS HISTÓRICOS` --references--> `extract_samples()`  [INFERRED]
  planning.md → src/core/train_calibration.py
- `REGLA DE ORO Y RESTRICCIONES DURAS` --references--> `LeagueStats`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `REGLA DE ORO Y RESTRICCIONES DURAS` --references--> `ValueIndicator`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `TAREA 6: CÁLCULO OBJETIVO DE `data_quality_score`` --references--> `get_data_quality_score()`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `TAREA 5: GESTIÓN DE STAKE (MÁXIMO 3% DEL CAPITAL / KELLY FRACCIONAL)` --references--> `_calculate_stake_units()`  [INFERRED]
  planning.md → src/ui/api/compare.py

## Import Cycles
- None detected.

## Communities (120 total, 31 thin omitted)

### Community 0 - "HierarchicalCalibrator"
Cohesion: 0.08
Nodes (20): TAREA 3: CALIBRACIÓN EXCLUSIVA BASADA EN DATOS HISTÓRICOS, HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, apply_calibration(), get_calibration_version_for_timestamp(), get_calibrator(), get_calibrator_for_timestamp() (+12 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.07
Nodes (46): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), buildMatchKey(), delay(), extractEventInfo(), fetchAllBookmakerOdds(), fetchSofaScore() (+38 more)

### Community 3 - "BlockReason"
Cohesion: 0.08
Nodes (63): BlockReason, _coerce_reason(), evaluate_eligibility(), evaluate_soft_filters(), is_hard(), PublicationThresholds, str, Umbrales de publicación, versionados y en un solo sitio. (+55 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (41): functools, convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa…, PMF de la suma de dos conteos independientes. Convolución discreta exacta:… (+33 more)

### Community 5 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1, usando final_prob (#42)., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 6 - "compare_football"
Cohesion: 0.18
Nodes (28): TAREA 2: DIVERSIFICACIÓN DINÁMICA DE `prior_n` (SHRINKAGE BAYESIANO), compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda() (+20 more)

### Community 7 - "Outcome"
Cohesion: 0.09
Nodes (30): _combine_legs(), distribution_for_total_line(), Outcome, outcome_hit_value(), outcome_probabilities_for_total(), outcome_return(), Enum, str (+22 more)

### Community 8 - "test_risk.py"
Cohesion: 0.08
Nodes (37): load_risk_limits(), _parse_bool_env(), PublicationMode, clean_env(), make_pick(), published(), fixture, parametrize (+29 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (24): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+16 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (32): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+24 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "Session"
Cohesion: 0.22
Nodes (9): Session, Test filtering picks by is_publishable and exporting to Excel and CSV formats., Test deduplication of correlated picks in the same match., Verify exact financial and statistical formulas (ROI, Hit Rate, Break-even, Net…, Test picks querying, server-side pagination, and column validation., test_admin_formulas_kpis(), test_filter_correlated_picks(), test_is_publishable_filter_and_picks_export() (+1 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - "test_train_calibration.py"
Cohesion: 0.18
Nodes (25): history_dir_for(), Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. Promoción: el candidato…, train_calibrator(), _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra…, Si el modelo ya está bien calibrado, la curva no puede mejorar de forma…, Regresión: el historial se derivaba de una constante global, así que entrenar… (+17 more)

### Community 15 - "get"
Cohesion: 0.08
Nodes (33): middleware, Sport, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version(), get_history_matches() (+25 more)

### Community 16 - "manual_loader.py"
Cohesion: 0.08
Nodes (26): ABC, pandas, Competition, MarketType, Match, str, A single fixture / game between two teams or players., Individual player stats for a single match. (+18 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.06
Nodes (58): brier_score(), CalibrationCurve, CalibrationSample, expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges() (+50 more)

### Community 18 - "extract_samples"
Cohesion: 0.24
Nodes (20): extract_samples(), Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _family(), Sin fecha no se puede garantizar ausencia de fuga temporal., Resolver falso: devuelve el outcome legacy asociado a cada selección., Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob., _resolver_map(), _row() (+12 more)

### Community 19 - "generate_football_analysis"
Cohesion: 0.09
Nodes (22): Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), _are_contradictory(), _calibration_line_bucket(), _calibration_side(), _call_openrouter(), _canonical_pick_signature(), _deduplicate_correlated_picks() (+14 more)

### Community 20 - "EligibilityDecision"
Cohesion: 0.09
Nodes (15): describe(), EligibilityDecision, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Une dos decisiones sobre el mismo pick. Los bloqueos duros se unen (nunca se…, Devuelve el `quality_score` que corresponde publicar. Un pick con bloqueo duro…, Reconstruye una decisión desde una lista plana de motivos, separando duros de…, Rehidratar un motivo desconocido no debe soltar el bloqueo. (+7 more)

### Community 21 - "save_analysis"
Cohesion: 0.09
Nodes (25): Exception, _check_projected_line_success(), _extract_bookmaker(), _extract_competition(), get_analysis_by_id(), get_league_matches(), _populate_history_extra_fields(), push_result() (+17 more)

### Community 22 - "test_stake_and_traceability.py"
Cohesion: 0.05
Nodes (43): compute_final_stake(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly(), compute_edge(), compute_risk_decision() (+35 more)

### Community 23 - "Rules"
Cohesion: 0.09
Nodes (20): caveman, Example output, How to invoke, See also, What it does, 1. Answer first, 2. Kill ceremony, 3. Short word (+12 more)

### Community 24 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 25 - "backup_db.py"
Cohesion: 0.24
Nodes (9): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), shutil (+1 more)

### Community 26 - "train_calibration.py"
Cohesion: 0.11
Nodes (28): random, _active_trained_until(), _coerce_cutoff_datetime(), _coerce_datetime(), compare_with_active(), _league_already_calibrated(), load_rows_from_db(), main() (+20 more)

### Community 27 - "admin_stats_service.py"
Cohesion: 0.09
Nodes (39): io, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, ColumnSchemaInfo, DashboardChartsData (+31 more)

### Community 28 - "test_settlement.py"
Cohesion: 0.19
Nodes (24): line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), settle_total(), Side, parametrize (+16 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.19
Nodes (25): _clip_0_100(), _explicit_market_support(), _poisson_over_under(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+17 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "market_probability.py"
Cohesion: 0.10
Nodes (23): blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Calcula las métricas de Closing Line Value (CLV)., Calcula la probabilidad implícita de una cuota decimal (1 / odds). (+15 more)

### Community 32 - "datetime"
Cohesion: 0.11
Nodes (18): datetime, fastapi_testclient, pytest, Ticket 1: Guardar partido sin fecha debe responder 400 Bad Request y detener el…, test_ticket1_missing_match_date_returns_400(), client(), fixture, Tarea 1: test que verifica que un payload de Watson con fecha queda persistido… (+10 more)

### Community 33 - "recalculate_all_accuracy"
Cohesion: 0.14
Nodes (15): _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), compare_teams_football(), _enrich_with_results(), _merge_best_odds(), Busca si el partido ya tiene resultados en la BD y marca acierto/fallo en el… (+7 more)

### Community 34 - "schemas.py"
Cohesion: 0.18
Nodes (19): field_validator, pydantic, AnalysisHistoryOut, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut (+11 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - ".create"
Cohesion: 0.08
Nodes (19): CutoffRequired, filter_before_cutoff(), Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el… (+11 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "TemporalCutoff"
Cohesion: 0.13
Nodes (10): Any, datetime, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Reparte los registros en admitidos, posteriores y sin fecha., record_date(), TemporalCutoff (+2 more)

### Community 40 - "TemporalParameterOptimizer"
Cohesion: 0.16
Nodes (13): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling…, Evalúa un conjunto específico de parámetros usando rolling origin sobre… (+5 more)

### Community 41 - "test_quantitative_math.py"
Cohesion: 0.07
Nodes (39): asyncio, numpy, scipy_optimize, scipy_stats, fit_gamma_prior_from_league(), Empirical Bayes and conjugate Gamma-Poisson inference for rate parameters., Fits Gamma prior (alpha, beta) using Empirical Bayes (method of moments) from…, Computes posterior expected rate lambda_post under conjugate Gamma-Poisson… (+31 more)

### Community 42 - ".compute_league_averages"
Cohesion: 0.17
Nodes (6): calculate_time_decay_weight(), load_calculated_league_params(), Carga los parámetros matemáticos calculados por liga desde…, Calcula el peso temporal de un partido según la distancia entre su fecha y una…, Calcula los promedios específicos de la liga ponderados por reciencia temporal.…, TestStructuralDecayAndProfiles

### Community 43 - "derive_joint_match_probabilities"
Cohesion: 0.12
Nodes (14): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win(), test_joint_match_invariants() (+6 more)

### Community 44 - "AnalysisHistory"
Cohesion: 0.09
Nodes (27): delete, put, AnalysisHistory, History of manual analyses performed in the comparator., deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches() (+19 more)

### Community 45 - "parse_utc"
Cohesion: 0.17
Nodes (7): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Invariantes del cutoff temporal. La propiedad que se defiende aquí es una sola…, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 46 - "models/calibration.py"
Cohesion: 0.10
Nodes (31): market_group_key(), Genera la clave canónica del grupo/segmento de mercado., _clean_val(), compute_sample_weight(), evaluate(), family_key(), family_side_bucket_key(), family_side_key() (+23 more)

### Community 47 - "test_regression_biases.py"
Cohesion: 0.11
Nodes (26): extract_market_line(), line_bucket_for(), load_line_buckets(), MarketFamily, MarketKey, MarketSide, normalize_market_family(), normalize_market_side() (+18 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "get_table_schema"
Cohesion: 0.17
Nodes (16): DatabaseRowUpdate, get_table_schema(), list_whitelisted_tables(), Any, Session, query_table_rows(), Return column definitions and schema information for a whitelisted table., Safe, paginated query over whitelisted database tables. (+8 more)

### Community 50 - "_compute_league_season_corners"
Cohesion: 0.15
Nodes (16): _compute_league_season_corners(), push_prefill(), Calcula el promedio de córners por partido para una liga y temporada, usando…, Browser extension pushes a (partial) form payload here. The Sherlock dashboard…, client(), fixture, Tests para verificar el cálculo de corners por partido de la liga/temporada en…, Verifica que para 'Primera A' y temporada '2026', se calcule el promedio real… (+8 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.07
Nodes (31): re, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line() (+23 more)

### Community 52 - "Gemini Notebook Automation"
Cohesion: 0.15
Nodes (12): Authorization Boundaries, Canonical Source-to-Artifact Workflow, Command Discovery, Deep Research, Failure Handling, Gemini Notebook Automation, Generation Notes, Operating Invariants (+4 more)

### Community 53 - "eligibility.py"
Cohesion: 0.08
Nodes (33): _risk_imports(), _as_float(), hard_blocks_from_flags(), is_hard_blocked(), _pget(), PickSnapshot, _pset(), Any (+25 more)

### Community 54 - "NotebookLMService"
Cohesion: 0.21
Nodes (7): NotebookLMService, Any, Cliente y helper para orquestar consultas a NotebookLM., Verifica si la librería está instalada y las credenciales mínimas existen., Envía una pregunta a un notebook específico o al configurado por defecto., Lista los notebooks disponibles en la cuenta., Sube un documento de texto o análisis al notebook para enriquecer la base de…

### Community 55 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 56 - "calculate_league_params.py"
Cohesion: 0.13
Nodes (23): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+15 more)

### Community 57 - "_check_pick_success"
Cohesion: 0.07
Nodes (41): Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., split_asian_line(), build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line() (+33 more)

### Community 58 - "submit_closing_odds"
Cohesion: 0.20
Nodes (8): match_closing_odds_to_pick(), _normalize_betano_odds(), push_prefill_odds(), Guarda las cuotas de cierre para los picks de un partido en…, Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…, Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…, submit_closing_odds()

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "get"
Cohesion: 0.18
Nodes (14): admin_dashboard_page(), admin_database_page(), admin_picks_page(), admin_root(), admin_stats_page(), get_current_admin_role(), get, Request (+6 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "_compute_league_reliability_score"
Cohesion: 0.39
Nodes (6): _compute_league_reliability_score(), Calcula un score de confiabilidad de la liga (LRS) en rango [0.15, 1.0]. 1.…, test_lrs_bounds(), test_lrs_high_matches_with_metrics_no_picks(), test_lrs_historical_performance_adjustment(), test_lrs_zero_matches_no_metrics()

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

### Community 67 - "typing"
Cohesion: 0.08
Nodes (30): dataclasses, logging, math, notebooklm, os, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, calculate_dixon_coles_matrix(), dixon_coles_tau() (+22 more)

### Community 68 - "test_invariants_and_eligibility.py"
Cohesion: 0.11
Nodes (16): evaluate_segment_status(), get_governance_multipliers(), Retorna los multiplicadores de stake y ajustes de edge según el estado de…, Evalúa el estado de gobernanza de un segmento según evidencia y configuración…, SegmentStatus, Tests de invariantes de mercado: calibración y eligibilidad. Verifica que: -…, TestGovernanceMultipliers, Regression: Debe usar high/extreme bucket, no la curva genérica de goals over. (+8 more)

### Community 70 - "pick_rules_engine.py"
Cohesion: 0.14
Nodes (19): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_line(), market_side(), normalize_text() (+11 more)

### Community 72 - "json"
Cohesion: 0.08
Nodes (34): argparse, Connection, dividir_archivo(), main(), Divide un archivo .py en partes de N lineas y genera archivos .txt. Uso: python…, json, pathlib, main() (+26 more)

### Community 73 - "test_admin_panel.py"
Cohesion: 0.07
Nodes (37): DeclarativeBase, enum, FastAPI, sqlalchemy, sqlalchemy_orm, Base, _column_exists(), create_indexes() (+29 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 75 - "h2h_shrinkage.py"
Cohesion: 0.38
Nodes (6): evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)., Evalúa la señal H2H sin emitir bloqueos duros para n < 8. Si n >= 8 y el hit…, shrunk_h2h_rate()

### Community 76 - "TOKEN OPTIMIZATION & SKILLS PROTOCOL"
Cohesion: 0.33
Nodes (5): 1. Entrada y Contexto (NotebookLM), 2. Implementación de Código (Ponytail), 3. Respuestas y Explicaciones (Caveman), Matriz de Decisión Rápida, TOKEN OPTIMIZATION & SKILLS PROTOCOL

### Community 81 - "Ponytail"
Cohesion: 0.40
Nodes (4): Before you write, Levels, Ponytail, The smallest complete change

### Community 82 - "_set_sqlite_pragma"
Cohesion: 0.67
Nodes (3): listens_for, Apply performance PRAGMAs on every new SQLite connection., _set_sqlite_pragma()

### Community 105 - "LeagueMathEngine"
Cohesion: 0.08
Nodes (18): calculate_weighted_average(), LeagueMathEngine, Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula el promedio con decay exponencial según antigüedad. half_life: número…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa… (+10 more)

### Community 107 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 109 - "_value_indicator"
Cohesion: 0.09
Nodes (30): load_pick_rules_data(), Carga el archivo pick_rules.json y devuelve tuple (rules_list,…, _calculate_display_score(), _calculate_kelly_fraction(), _vi(), _frontend_style_strategic_score(), get_market_confidence_tier(), get_market_variance_tier() (+22 more)

### Community 112 - "Session"
Cohesion: 0.10
Nodes (32): apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, _get_or_create_team(), BaseModel, post (+24 more)

### Community 114 - "main.py"
Cohesion: 0.08
Nodes (30): contextlib, copy, fastapi_middleware_cors, fastapi_staticfiles, openpyxl, openpyxl_utils, Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache() (+22 more)

### Community 115 - "portfolio.py"
Cohesion: 0.09
Nodes (18): LISTA DE CONTROL DE TAREAS, REGLA DE ORO Y RESTRICCIONES DURAS, TAREA 1: REFACTORIZACIÓN DEL LEAGUE RELIABILITY SCORE (LRS), TAREA 4: UMBRALES DE PUBLICACIÓN (`is_publishable` E `is_underdog`) Y RANGOS DE CUOTA, TAREA 5: GESTIÓN DE STAKE (MÁXIMO 3% DEL CAPITAL / KELLY FRACCIONAL), TAREA 6: CÁLCULO OBJETIVO DE `data_quality_score`, apply_portfolio_exposure_cap(), filter_selected_portfolio() (+10 more)

### Community 120 - "outcome_from_legacy"
Cohesion: 0.29
Nodes (7): outcome_from_legacy(), Traduce un `PickOutcome` legacy al enum `Outcome`. Un valor desconocido se…, Un valor raro se excluye, no se cuenta como acierto ni como fallo., test_outcome_from_legacy_is_case_insensitive(), test_outcome_from_legacy_is_idempotent(), test_outcome_from_legacy_maps_every_case(), test_outcome_from_legacy_unknown_fails_closed()

### Community 121 - "math/calibration.py"
Cohesion: 0.16
Nodes (9): sklearn_isotonic, sklearn_linear_model, IsotonicCalibrator, PlattCalibrator, ndarray, Probability calibration and market normalization modules. Provides…, Platt Scaling via logistic regression over log-odds (logit): logit(p) = ln(p /…, Robust wrapper around sklearn.isotonic.IsotonicRegression. (+1 more)

### Community 122 - "ExtractionStats"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

### Community 123 - "admin_routes.py"
Cohesion: 0.08
Nodes (47): fastapi_responses, fastapi_templating, patch, market_group(), Clave familia_lado usada para consultar data/market_correlation.json., OperationalFieldsUpdate, PaginationMeta, PickDetailOut (+39 more)

### Community 125 - "TrainingReport"
Cohesion: 0.40
Nodes (3): format_active_comparison(), Resultado auditable de un entrenamiento., TrainingReport

### Community 128 - "compare.py"
Cohesion: 0.06
Nodes (40): dotenv, openai, pydantic_alias_generators, _build_history_cache_key(), calibration_is_active(), _coerce_datetime(), _combine_nb_params(), _dc_component_weights() (+32 more)

## Knowledge Gaps
- **76 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 885 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `compare.py`, `compare_football`, `Session`, `get`, `save_analysis`, `train_calibration.py`, `admin_stats_service.py`, `recalculate_all_accuracy`, `train_model_retrospective.py`, `get_table_schema`, `_compute_league_season_corners`, `_check_pick_success`, `submit_closing_odds`, `test_admin_panel.py`, `prueba90100.py`, `_value_indicator`, `Session`, `main.py`, `admin_routes.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `compare.py`, `test_invariants_and_eligibility.py`, `pick_rules_engine.py`, `compare_football`, `test_risk.py`, `test_eligibility_wiring.py`, `_value_indicator`, `parallel_recalc.py`, `EligibilityDecision`, `eligibility.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `compare_football()` connect `compare_football` to `compare.py`, `BlockReason`, `test_eligibility_wiring.py`, `get`, `generate_football_analysis`, `test_stake_and_traceability.py`, `market_probability.py`, `recalculate_all_accuracy`, `.create`, `TemporalCutoff`, `test_quantitative_math.py`, `AnalysisHistory`, `_compute_league_season_corners`, `parallel_recalc.py`, `calculate_league_params.py`, `_check_pick_success`, `LeagueMathEngine`, `_value_indicator`, `main.py`, `portfolio.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `HierarchicalCalibrator` (e.g. with `TAREA 3: CALIBRACIÓN EXCLUSIVA BASADA EN DATOS HISTÓRICOS` and `compare_with_active()`) actually correct?**
  _`HierarchicalCalibrator` has 23 INFERRED edges - model-reasoned connections that need verification._