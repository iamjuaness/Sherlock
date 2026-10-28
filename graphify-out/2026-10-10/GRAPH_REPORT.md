# Graph Report - Sherlock  (2026-10-08)

## Corpus Check
- 120 files · ~511,889 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 2259 nodes · 5320 edges · 116 communities (84 shown, 32 thin omitted)
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
- BlockReason
- test_count_negative_binomial.py
- evaluate_oof_comparison.py
- compare.py
- Outcome
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- admin_routes.py
- leagues.js
- .compute_league_averages
- compare_football
- domain.py
- test_calibration.py
- save_analysis
- get
- EligibilityDecision
- _invalidate_stats_cache
- compute_segment_report
- _value_indicator
- Session
- stake_engine.py
- train_calibration.py
- calculate_dashboard_summary
- test_settlement.py
- _explicit_market_support
- manifest.json
- market_probability.py
- LeagueMathEngine
- test_compare_integration.py
- TestFiltering
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- test_invariants_and_eligibility.py
- schemas.py
- admin_picks_service.py
- parse_utc
- joint_match_distribution.py
- RiskPolicyConfig
- record_date
- calibration.py
- test_regression_biases.py
- train_model_retrospective.py
- hard_blocks_from_flags
- evaluate_pick_rules
- parallel_recalc.py
- test_train_calibration.py
- PickSnapshot
- CalibrationSample
- count_models.py
- calculate_league_params.py
- _check_pick_success
- test_admin_panel.py
- admin.js
- get
- CardsConvention
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- TemporalParameterOptimizer
- evaluate_segment_status
- AnalysisHistory
- content.js
- update_governance.py
- dataclasses
- 2. Paso a Paso del Nuevo Pipeline
- recalculate_all_accuracy
- sherlock
- typing
- prueba90100.py
- PredictionRecord
- h2h_shrinkage.py
- split_asian_line
- submit_closing_odds
- main.py
- compute_edge
- _get_governance_multiplier
- TestStakeEngine
- generate_football_analysis
- test_stake_and_traceability.py
- TestKellyFractional
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

## Communities (116 total, 32 thin omitted)

### Community 0 - "test_calibration_temporal.py"
Cohesion: 0.09
Nodes (11): _build_history_cache_key(), get_calibration_version_for_timestamp(), get_calibrator_for_timestamp(), Clave de caché basada en los paths y mtimes de los artefactos., Devuelve el calibrador activo en el momento predicted_at según el historial de…, Retorna la versión de la calibración para un timestamp dado o 'unverified'., Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache() (+3 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "BlockReason"
Cohesion: 0.10
Nodes (53): BlockReason, evaluate_eligibility(), evaluate_soft_filters(), is_hard(), PublicationThresholds, str, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros. (+45 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 6 - "compare.py"
Cohesion: 0.06
Nodes (40): dotenv, numpy, openai, pydantic_alias_generators, apply_portfolio_exposure_cap(), Aplica Simultaneous Kelly Scaling sobre una lista de ValueIndicator…, _combine_nb_params(), _compute_league_reliability_score() (+32 more)

### Community 7 - "Outcome"
Cohesion: 0.09
Nodes (33): functools, math, _combine_legs(), distribution_for_total_line(), Outcome, outcome_hit_value(), outcome_probabilities_for_total(), outcome_return() (+25 more)

### Community 8 - "test_risk.py"
Cohesion: 0.06
Nodes (54): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_line(), market_side(), normalize_text() (+46 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (26): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+18 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (32): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+24 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "admin_routes.py"
Cohesion: 0.11
Nodes (42): FastAPI, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ColumnSchemaInfo, DashboardChartsData, DashboardKPIs (+34 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - ".compute_league_averages"
Cohesion: 0.18
Nodes (6): calculate_time_decay_weight(), load_calculated_league_params(), Carga los parámetros matemáticos calculados por liga desde…, Calcula el peso temporal de un partido según la distancia entre su fecha y una…, Calcula los promedios específicos de la liga ponderados por reciencia temporal.…, TestStructuralDecayAndProfiles

### Community 15 - "compare_football"
Cohesion: 0.17
Nodes (28): compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda() (+20 more)

### Community 16 - "domain.py"
Cohesion: 0.07
Nodes (38): ABC, DeclarativeBase, enum, pandas, Base, Declarative base for all ORM models., BettingLine, Competition (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.06
Nodes (45): brier_score(), CalibrationCurve, expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia. (+37 more)

### Community 18 - "save_analysis"
Cohesion: 0.17
Nodes (13): Exception, _extract_bookmaker(), _extract_competition(), push_result(), Browser extension pushes match results here (e.g. from flashscore). Tries to…, Extract competition name from payload dict, avoiding json.loads in callers., Extract primary bookmaker from payload dict., Return the sum of stake_units for publishable picks of a match. (+5 more)

### Community 19 - "get"
Cohesion: 0.07
Nodes (34): middleware, str, Sport, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version() (+26 more)

### Community 20 - "EligibilityDecision"
Cohesion: 0.09
Nodes (16): _coerce_reason(), describe(), EligibilityDecision, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno., Une dos decisiones sobre el mismo pick. Los bloqueos duros se unen (nunca se…, Devuelve el `quality_score` que corresponde publicar. Un pick con bloqueo duro… (+8 more)

### Community 21 - "_invalidate_stats_cache"
Cohesion: 0.10
Nodes (19): delete, put, deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches(), _invalidate_stats_cache(), Any (+11 more)

### Community 22 - "compute_segment_report"
Cohesion: 0.22
Nodes (9): _compute_ece(), compute_segment_report(), Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, Calcula el reporte completo de un segmento a partir de sus traces y resultados.…, Expected Calibration Error con n_bins bins uniformes., Genera recomendación operativa simple basada en métricas., _recommend(), _safe_log() (+1 more)

### Community 23 - "_value_indicator"
Cohesion: 0.13
Nodes (24): apply_calibration(), _calculate_display_score(), _calculate_stake_units(), calibration_is_active(), _coerce_datetime(), _vi(), get_data_quality_score(), get_market_confidence_tier() (+16 more)

### Community 24 - "Session"
Cohesion: 0.10
Nodes (32): apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, BaseModel, post, Session (+24 more)

### Community 25 - "stake_engine.py"
Cohesion: 0.19
Nodes (16): compute_final_stake(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly(), compute_risk_decision(), optimize_simultaneous_portfolio() (+8 more)

### Community 26 - "train_calibration.py"
Cohesion: 0.11
Nodes (20): re, _coerce_cutoff_datetime(), _coerce_datetime(), _league_already_calibrated(), load_rows_from_db(), main(), Any, datetime (+12 more)

### Community 27 - "calculate_dashboard_summary"
Cohesion: 0.12
Nodes (16): ChartDataPoint, calculate_dashboard_summary(), _calc_rankings(), export_stats_file(), _filter_analyses_by_params(), _get_flattened_picks(), get_grouped_stats(), Any (+8 more)

### Community 28 - "test_settlement.py"
Cohesion: 0.19
Nodes (24): line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), settle_total(), Side, parametrize (+16 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.21
Nodes (25): _clip_0_100(), _dc_component_weights(), _explicit_market_support(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+17 more)

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

### Community 34 - "TestFiltering"
Cohesion: 0.16
Nodes (10): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los…, El informe se registra en logs; no debe arrastrar el histórico entero. (+2 more)

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
Cohesion: 0.18
Nodes (15): _risk_imports(), is_hard_blocked(), _pget(), _pset(), Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Lee todos los bloqueos duros ya presentes en un pick, sea dict u objeto.…, Emite bloqueos duros sobre un pick dict-u-objeto. Irreversible. Escribe el… (+7 more)

### Community 40 - "schemas.py"
Cohesion: 0.23
Nodes (16): pydantic, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut, CompetitionOut, Config (+8 more)

### Community 41 - "admin_picks_service.py"
Cohesion: 0.07
Nodes (41): patch, AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., market_group(), Clave familia_lado usada para consultar data/market_correlation.json., OperationalFieldsUpdate, PickItemOut, get_audit_logs() (+33 more)

### Community 42 - "parse_utc"
Cohesion: 0.16
Nodes (7): parse_utc(), True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 45 - "record_date"
Cohesion: 0.10
Nodes (14): CutoffRequired, FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Reparte los registros en admitidos, posteriores y sin fecha. (+6 more)

### Community 46 - "calibration.py"
Cohesion: 0.11
Nodes (35): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), HierarchicalCalibrator, league_family_key(), league_family_side_bucket_key() (+27 more)

### Community 47 - "test_regression_biases.py"
Cohesion: 0.08
Nodes (32): pytest, extract_market_line(), line_bucket_for(), load_line_buckets(), market_group_key(), MarketFamily, MarketKey, MarketSide (+24 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "hard_blocks_from_flags"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 50 - "evaluate_pick_rules"
Cohesion: 0.18
Nodes (10): evaluate_pick_rules(), load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Carga el archivo pick_rules.json y devuelve tuple (rules_list,…, Devuelve (is_blocked, reason) si selection es una string. Si selection es una…, is_pick_blocked_by_rules(), Checks pick_rules.json using the unified pick_rules_engine. If a rule is… (+2 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.07
Nodes (34): asyncio, backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup() (+26 more)

### Community 52 - "test_train_calibration.py"
Cohesion: 0.08
Nodes (54): random, extract_samples(), ExtractionStats, history_dir_for(), _pick_probability(), Un partido sirve si tiene al menos el marcador final., Extrae la probabilidad CRUDA del modelo, nunca la ya calibrada. Calibrar sobre…, Convierte el histórico liquidado en muestras para calibración. La probabilidad… (+46 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.17
Nodes (14): _as_float(), PickSnapshot, Any, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad final (final_prob) o calibrada (calibrated_prob)., test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case() (+6 more)

### Community 54 - "CalibrationSample"
Cohesion: 0.10
Nodes (15): CalibrationSample, evaluate(), Una observación histórica para ajustar la calibración., SegmentEvaluation, walk_forward_calibrate(), WalkForwardResult, test_improved_is_false_when_calibration_hurts(), test_large_sample_does_move() (+7 more)

### Community 55 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 56 - "calculate_league_params.py"
Cohesion: 0.13
Nodes (23): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+15 more)

### Community 57 - "_check_pick_success"
Cohesion: 0.08
Nodes (37): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), get_all_picks(), _get_cache() (+29 more)

### Community 58 - "test_admin_panel.py"
Cohesion: 0.10
Nodes (22): listens_for, sqlalchemy, sqlalchemy_orm, _column_exists(), create_indexes(), init_db(), Database engine, session factory and Base for SQLAlchemy models., Create indexes for analysis_history and related tables. (+14 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "get"
Cohesion: 0.11
Nodes (28): admin_dashboard_page(), admin_database_page(), admin_mark_recalculation(), admin_picks_page(), admin_root(), admin_stats_page(), export_admin_picks(), export_admin_stats() (+20 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

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
Cohesion: 0.11
Nodes (21): pathlib, main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str (+13 more)

### Community 69 - "AnalysisHistory"
Cohesion: 0.12
Nodes (22): field_validator, AnalysisHistory, History of manual analyses performed in the comparator., _check_projected_line_success(), get_analysis_by_id(), get_league_matches(), list_analysis(), _populate_history_extra_fields() (+14 more)

### Community 72 - "update_governance.py"
Cohesion: 0.11
Nodes (22): argparse, Connection, build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary() (+14 more)

### Community 73 - "dataclasses"
Cohesion: 0.18
Nodes (12): dataclasses, compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento…, R_sample = 1 - exp(-n / target_n), R_calibration = exp(- (ece + abs(gap))) (+4 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 76 - "recalculate_all_accuracy"
Cohesion: 0.10
Nodes (26): Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), CompareResponse, FootballCompareRequest, _annotate_best_bookmaker(), _apply_line_shopping(), _call_llm_for_result(), _check_payload_has_odds() (+18 more)

### Community 105 - "typing"
Cohesion: 0.15
Nodes (14): datetime, fastapi_testclient, json, logging, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).…, Módulo para la separación entre prediction_universe y selected_portfolio.…, Audit Logging Service for Sherlock Admin Panel. (+6 more)

### Community 106 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 107 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones.

### Community 108 - "h2h_shrinkage.py"
Cohesion: 0.38
Nodes (6): evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)., Evalúa la señal H2H sin emitir bloqueos duros para n < 8. Si n >= 8 y el hit…, shrunk_h2h_rate()

### Community 109 - "split_asian_line"
Cohesion: 0.29
Nodes (6): _neg_bin_pmf(), _neg_binomial_over_under(), _get_single_line_probs(), _poisson_over_under(), Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., split_asian_line()

### Community 110 - "submit_closing_odds"
Cohesion: 0.20
Nodes (8): match_closing_odds_to_pick(), _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…, Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…, Guarda las cuotas de cierre para los picks de un partido en…, submit_closing_odds()

### Community 112 - "main.py"
Cohesion: 0.08
Nodes (26): contextlib, copy, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io, openpyxl (+18 more)

### Community 113 - "compute_edge"
Cohesion: 0.31
Nodes (3): compute_edge(), EdgeResult, TestEdgeComputation

### Community 114 - "_get_governance_multiplier"
Cohesion: 0.50
Nodes (4): _get_governance_multiplier(), get_segment_governance(), Resuelve el status de gobernanza y el multiplicador de stake para un segmento.…, Devuelve el artefacto de gobernanza completo, recargandolo si cambio en disco.…

### Community 116 - "TestStakeEngine"
Cohesion: 0.33
Nodes (3): compute_stake_final(), Calcula el stake final aplicando ajuste de factores, drawdown scale y límites., TestStakeEngine

### Community 117 - "generate_football_analysis"
Cohesion: 0.10
Nodes (21): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), _are_contradictory(), _calibration_line_bucket(), _calibration_side(), _call_openrouter(), _canonical_pick_signature() (+13 more)

### Community 118 - "test_stake_and_traceability.py"
Cohesion: 0.18
Nodes (9): generate_segment_reports(), PickTrace, Reporte completo de un segmento league+family+side+bucket. Incluye: picks, hit…, Snapshot inmutable de trazabilidad de un pick para audit y reportes. Contiene…, Agrupa traces por segment_key y genera un SegmentReport para cada uno. Returns:…, SegmentReport, _make_trace(), Tests del motor de stake y trazabilidad. (+1 more)

## Knowledge Gaps
- **40 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+35 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 790 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `train_calibration.py`, `compare.py`, `admin_picks_service.py`, `prueba90100.py`, `admin_routes.py`, `recalculate_all_accuracy`, `submit_closing_odds`, `domain.py`, `train_model_retrospective.py`, `main.py`, `get`, `save_analysis`, `_invalidate_stats_cache`, `_value_indicator`, `Session`, `_check_pick_success`, `test_admin_panel.py`, `calculate_dashboard_summary`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `TemporalParameterOptimizer`, `.create`, `.compute_pick_hit_rate`, `compare.py`, `typing`, `record_date`, `.compute_league_averages`, `compare_football`, `main.py`, `save_analysis`, `calculate_league_params.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `evaluate_segment_status`, `compare.py`, `test_invariants_and_eligibility.py`, `test_risk.py`, `test_eligibility_wiring.py`, `compare_football`, `hard_blocks_from_flags`, `evaluate_pick_rules`, `EligibilityDecision`, `PickSnapshot`, `_value_indicator`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 59 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 59 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `compare_football()` (e.g. with `LeagueMathEngine` and `BlockReason`) actually correct?**
  _`compare_football()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `HierarchicalCalibrator` (e.g. with `train_calibrator()` and `get_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 19 INFERRED edges - model-reasoned connections that need verification._