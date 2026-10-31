# Graph Report - Sherlock  (2026-10-30)

## Corpus Check
- 131 files · ~546,392 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 2398 nodes · 5640 edges · 131 communities (96 shown, 35 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 378 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b19a1805`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HierarchicalCalibrator
- Web UI Comparator JS
- background.js
- test_eligibility.py
- test_count_negative_binomial.py
- test_compare_integration.py
- compare.py
- test_settlement.py
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- test_admin_panel.py
- leagues.js
- test_train_calibration.py
- compare_football
- domain.py
- test_calibration.py
- extract_samples
- get
- BlockReason
- save_analysis
- stake_engine.py
- evaluate_pick_rules
- evaluate_oof_comparison.py
- pathlib
- train_calibration.py
- admin_stats_service.py
- Side
- _explicit_market_support
- manifest.json
- market_probability.py
- TestLeagueMathEngine
- _check_pick_success
- market_group_key
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- hard_blocks_from_flags
- schemas.py
- test_quantitative_math.py
- parse_utc
- joint_match_distribution.py
- AnalysisHistory
- record_date
- calibration.py
- test_regression_biases.py
- train_model_retrospective.py
- CalibrationCurve
- _compute_league_season_corners
- parallel_recalc.py
- CalibrationSample
- eligibility.py
- test_temporal.py
- dataclasses
- typing
- get_leagues_stats
- test_math_engine.py
- admin.js
- admin_routes.py
- CardsConvention
- test_stake_and_traceability.py
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- TemporalParameterOptimizer
- test_invariants_and_eligibility.py
- TestMLSGoalsOverHighExtreme
- pick_rules_engine.py
- content.js
- update_governance.py
- admin_database_service.py
- 2. Paso a Paso del Nuevo Pipeline
- FootballCompareRequest
- TestStakeEngine
- sherlock
- LeagueMathEngine
- TestCalibrationRecencyAndWalkForward
- prueba90100.py
- init_db
- _value_indicator
- submit_closing_odds
- record_hard_block
- Session
- compute_edge
- main.py
- PredictionRecord
- RiskPolicyConfig
- kelly_fractional
- distribution_for_total_line
- outcome_from_legacy
- PlattCalibrator
- ExtractionStats
- apply_calibration
- is_hard
- TrainingReport
- math/__init__.py
- apply_portfolio_exposure_cap
- split_asian_line
- clean_env
- db_session

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 79 edges
2. `AnalysisHistory` - 74 edges
3. `compare_football()` - 73 edges
4. `HierarchicalCalibrator` - 45 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 36 edges
8. `CalibrationSample` - 35 edges
9. `_value_indicator()` - 33 edges
10. `ReturnDistribution` - 32 edges

## Surprising Connections (you probably didn't know these)
- `1. RESTRICCIONES DE ARQUITECTURA Y COMPATIBILIDAD` --references--> `ValueIndicator`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `Tarea 6: Pruebas Unitarias` --references--> `update_gamma_poisson()`  [INFERRED]
  planning.md → src/core/math/bayesian.py
- `Tarea 5: Refactorizar `src/ui/api/compare.py`` --references--> `normalize_categorical_market()`  [INFERRED]
  planning.md → src/core/math/calibration.py
- `Tarea 5: Refactorizar `src/ui/api/compare.py`` --references--> `build_dixon_coles_matrix()`  [INFERRED]
  planning.md → src/core/math/dixon_coles.py
- `Tarea 4: Crear `src/core/math/kelly.py`` --references--> `_calculate_stake_units()`  [INFERRED]
  planning.md → src/ui/api/compare.py

## Import Cycles
- None detected.

## Communities (131 total, 35 thin omitted)

### Community 0 - "HierarchicalCalibrator"
Cohesion: 0.09
Nodes (20): os, HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, _build_history_cache_key(), get_calibration_version_for_timestamp(), get_calibrator(), get_calibrator_for_timestamp() (+12 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.07
Nodes (46): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), buildMatchKey(), delay(), extractEventInfo(), fetchAllBookmakerOdds(), fetchSofaScore() (+38 more)

### Community 3 - "test_eligibility.py"
Cohesion: 0.08
Nodes (54): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+46 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (41): functools, convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa…, PMF de la suma de dos conteos independientes. Convolución discreta exacta:… (+33 more)

### Community 5 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1, usando final_prob (#42)., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 6 - "compare.py"
Cohesion: 0.06
Nodes (43): dotenv, openai, pydantic_alias_generators, _are_contradictory(), _calibration_line_bucket(), _call_openrouter(), _canonical_pick_signature(), _combine_nb_params() (+35 more)

### Community 7 - "test_settlement.py"
Cohesion: 0.12
Nodes (31): _combine_legs(), line_legs(), Outcome, outcome_hit_value(), outcome_return(), Enum, Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de…, Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite… (+23 more)

### Community 8 - "test_risk.py"
Cohesion: 0.09
Nodes (33): load_risk_limits(), _parse_bool_env(), make_pick(), published(), parametrize, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Un valor ininteligible no debe abrir la publicación real. `flase` es un typo…, Verifica que el archivo pick_rules.json contiene la lista de reglas. (+25 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (26): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+18 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (33): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+25 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "test_admin_panel.py"
Cohesion: 0.07
Nodes (49): patch, AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., DatabaseRowUpdate, OperationalFieldsUpdate, PaginationMeta, PickDetailOut, PickItemOut (+41 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - "test_train_calibration.py"
Cohesion: 0.18
Nodes (25): history_dir_for(), Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. Promoción: el candidato…, train_calibrator(), _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra…, Si el modelo ya está bien calibrado, la curva no puede mejorar de forma…, Regresión: el historial se derivaba de una constante global, así que entrenar… (+17 more)

### Community 15 - "compare_football"
Cohesion: 0.16
Nodes (31): Tarea 5: Refactorizar `src/ui/api/compare.py`, Computes posterior expected rate lambda_post under conjugate Gamma-Poisson…, update_gamma_poisson(), compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda() (+23 more)

### Community 16 - "domain.py"
Cohesion: 0.07
Nodes (38): ABC, DeclarativeBase, enum, pandas, Base, Declarative base for all ORM models., BettingLine, Competition (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.10
Nodes (32): brier_score(), evaluate(), expected_calibration_error(), log_loss(), pava(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators., reliability_table() (+24 more)

### Community 18 - "extract_samples"
Cohesion: 0.24
Nodes (20): extract_samples(), Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _family(), Sin fecha no se puede garantizar ausencia de fuga temporal., Resolver falso: devuelve el outcome legacy asociado a cada selección., Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob., _resolver_map(), _row() (+12 more)

### Community 19 - "get"
Cohesion: 0.07
Nodes (34): middleware, str, Sport, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version() (+26 more)

### Community 20 - "BlockReason"
Cohesion: 0.09
Nodes (20): BlockReason, _coerce_reason(), describe(), EligibilityDecision, str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno. (+12 more)

### Community 21 - "save_analysis"
Cohesion: 0.08
Nodes (25): Exception, _check_projected_line_success(), _extract_bookmaker(), _extract_competition(), get_analysis_by_id(), get_league_matches(), list_analysis(), _populate_history_extra_fields() (+17 more)

### Community 22 - "stake_engine.py"
Cohesion: 0.16
Nodes (18): compute_final_stake(), PublicationMode, Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly(), compute_risk_decision() (+10 more)

### Community 23 - "evaluate_pick_rules"
Cohesion: 0.11
Nodes (17): evaluate_pick_rules(), load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio… (+9 more)

### Community 24 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 25 - "pathlib"
Cohesion: 0.10
Nodes (21): argparse, backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup() (+13 more)

### Community 26 - "train_calibration.py"
Cohesion: 0.11
Nodes (28): random, _active_trained_until(), _coerce_cutoff_datetime(), _coerce_datetime(), compare_with_active(), _league_already_calibrated(), load_rows_from_db(), main() (+20 more)

### Community 27 - "admin_stats_service.py"
Cohesion: 0.12
Nodes (30): AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs, DashboardSummaryOut (+22 more)

### Community 28 - "Side"
Cohesion: 0.20
Nodes (19): str, Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, _settle_simple_total(), settle_total(), Side, parametrize, Un lado gana exactamente lo que el otro pierde. (+11 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.22
Nodes (24): _clip_0_100(), _explicit_market_support(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico., stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+16 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "market_probability.py"
Cohesion: 0.10
Nodes (23): blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Calcula las métricas de Closing Line Value (CLV)., Calcula la probabilidad implícita de una cuota decimal (1 / odds). (+15 more)

### Community 32 - "TestLeagueMathEngine"
Cohesion: 0.15
Nodes (4): Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Evalúa si un partido específico cumple con el criterio de un pick. Soporta:…, Calcula el hit rate enriquecido con ponderación por reciencia exponencial,…, TestLeagueMathEngine

### Community 33 - "_check_pick_success"
Cohesion: 0.10
Nodes (25): Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _enrich_with_results(), _extract_line() (+17 more)

### Community 34 - "market_group_key"
Cohesion: 0.15
Nodes (14): market_group_key(), Genera la clave canónica del grupo/segmento de mercado., compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento…, R_sample = 1 - exp(-n / target_n) (+6 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - ".create"
Cohesion: 0.10
Nodes (12): Calcula el hit rate global a nivel de liga para un mercado específico para…, CutoffRequired, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, TemporalCutoff, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el… (+4 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "hard_blocks_from_flags"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 40 - "schemas.py"
Cohesion: 0.18
Nodes (19): field_validator, pydantic, AnalysisHistoryOut, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut (+11 more)

### Community 41 - "test_quantitative_math.py"
Cohesion: 0.08
Nodes (33): math, numpy, Tarea 6: Pruebas Unitarias, scipy_optimize, scipy_stats, sklearn_isotonic, sklearn_linear_model, fit_gamma_prior_from_league() (+25 more)

### Community 42 - "parse_utc"
Cohesion: 0.16
Nodes (7): parse_utc(), True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 44 - "AnalysisHistory"
Cohesion: 0.10
Nodes (23): delete, put, AnalysisHistory, History of manual analyses performed in the comparator., deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches() (+15 more)

### Community 45 - "record_date"
Cohesion: 0.11
Nodes (10): FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Reparte los registros en admitidos, posteriores y sin fecha., record_date() (+2 more)

### Community 46 - "calibration.py"
Cohesion: 0.23
Nodes (19): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+11 more)

### Community 47 - "test_regression_biases.py"
Cohesion: 0.10
Nodes (27): pytest, extract_market_line(), line_bucket_for(), load_line_buckets(), MarketFamily, MarketKey, MarketSide, normalize_market_family() (+19 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.35
Nodes (11): requests, compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any, datetime, Determina si un partido tiene cuotas/mercados de apuestas asociados. Retorna… (+3 more)

### Community 49 - "CalibrationCurve"
Cohesion: 0.15
Nodes (9): CalibrationCurve, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_curve_roundtrip_serialization() (+1 more)

### Community 50 - "_compute_league_season_corners"
Cohesion: 0.15
Nodes (16): _compute_league_season_corners(), push_prefill(), Calcula el promedio de córners por partido para una liga y temporada, usando…, Browser extension pushes a (partial) form payload here. The Sherlock dashboard…, client(), fixture, Tests para verificar el cálculo de corners por partido de la liga/temporada en…, Verifica que para 'Primera A' y temporada '2026', se calcule el promedio real… (+8 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.16
Nodes (20): asyncio, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line() (+12 more)

### Community 52 - "CalibrationSample"
Cohesion: 0.10
Nodes (24): CalibrationSample, fit_curve(), _quantile_edges(), Una observación histórica para ajustar la calibración., make_samples(), El audit: 'la curva de calibración muestra sobreconfianza fuerte en…, Si el modelo ya está calibrado, la curva debe quedarse cerca de la identidad., Clave del diseño: con poca muestra el ruido NO puede dominar. 8 observaciones… (+16 more)

### Community 53 - "eligibility.py"
Cohesion: 0.13
Nodes (20): _as_float(), _pget(), PickSnapshot, _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de… (+12 more)

### Community 54 - "test_temporal.py"
Cohesion: 0.16
Nodes (11): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Invariantes del cutoff temporal. La propiedad que se defiende aquí es una sola…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los… (+3 more)

### Community 55 - "dataclasses"
Cohesion: 0.15
Nodes (15): dataclasses, DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina. (+7 more)

### Community 56 - "typing"
Cohesion: 0.06
Nodes (50): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+42 more)

### Community 57 - "get_leagues_stats"
Cohesion: 0.10
Nodes (25): build_equity_curve(), _calculate_pick_profit(), export_excel_report(), get_all_picks(), _get_cache(), get_global_stats(), get_league_markets(), get_leagues_stats() (+17 more)

### Community 58 - "test_math_engine.py"
Cohesion: 0.14
Nodes (10): calculate_dixon_coles_matrix(), calculate_weighted_average(), dixon_coles_tau(), _poisson_pmf(), Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0,…, Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste…, Calcula el promedio con decay exponencial según antigüedad. half_life: número…, Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros,… (+2 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.10
Nodes (36): get_audit_logs(), Session, Retrieve audit logs with optional filtering., export_stats_file(), Export filtered stats table to CSV or Excel bytes., admin_dashboard_page(), admin_database_page(), admin_mark_recalculation() (+28 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "test_stake_and_traceability.py"
Cohesion: 0.12
Nodes (18): _compute_ece(), compute_segment_report(), generate_segment_reports(), PickTrace, Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, Reporte completo de un segmento league+family+side+bucket. Incluye: picks, hit…, Snapshot inmutable de trazabilidad de un pick para audit y reportes. Contiene…, Calcula el reporte completo de un segmento a partir de sus traces y resultados.… (+10 more)

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

### Community 68 - "test_invariants_and_eligibility.py"
Cohesion: 0.10
Nodes (25): main(), evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str, Módulo para el monitor de drift y la gobernanza automática de segmentos., Retorna los multiplicadores de stake y ajustes de edge según el estado de… (+17 more)

### Community 70 - "pick_rules_engine.py"
Cohesion: 0.11
Nodes (22): re, classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line() (+14 more)

### Community 72 - "update_governance.py"
Cohesion: 0.21
Nodes (14): build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary(), Path, update_governance.py ==================== Genera automaticamente… (+6 more)

### Community 73 - "admin_database_service.py"
Cohesion: 0.12
Nodes (22): FastAPI, listens_for, sqlalchemy, sqlalchemy_orm, get_db(), Database engine, session factory and Base for SQLAlchemy models., FastAPI dependency that yields a DB session., Apply performance PRAGMAs on every new SQLite connection. (+14 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 75 - "FootballCompareRequest"
Cohesion: 0.17
Nodes (16): CompareResponse, FootballCompareRequest, FootballOdds, BaseModel, _stat_comparison(), StatComparison, _use_general_stats(), _annotate_best_bookmaker() (+8 more)

### Community 76 - "TestStakeEngine"
Cohesion: 0.33
Nodes (3): compute_stake_final(), Calcula el stake final aplicando ajuste de factores, drawdown scale y límites., TestStakeEngine

### Community 105 - "LeagueMathEngine"
Cohesion: 0.09
Nodes (16): calculate_time_decay_weight(), LeagueMathEngine, load_calculated_league_params(), Any, Carga los parámetros matemáticos calculados por liga desde…, Calcula el peso temporal de un partido según la distancia entre su fecha y una…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de… (+8 more)

### Community 106 - "TestCalibrationRecencyAndWalkForward"
Cohesion: 0.25
Nodes (3): Timestamps futuros no producen peso > 1.0., Walk-forward: train siempre precede al test; no data leakage., TestCalibrationRecencyAndWalkForward

### Community 107 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 108 - "init_db"
Cohesion: 0.29
Nodes (7): _column_exists(), create_indexes(), init_db(), Create indexes for analysis_history and related tables., Check if a column exists in a table (SQLite-compatible)., Create all tables and run idempotent schema migrations., lifespan()

### Community 109 - "_value_indicator"
Cohesion: 0.10
Nodes (26): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), calibration_is_active(), _calibration_side(), _vi(), get_data_quality_score(), get_market_confidence_tier() (+18 more)

### Community 110 - "submit_closing_odds"
Cohesion: 0.20
Nodes (8): match_closing_odds_to_pick(), _normalize_betano_odds(), push_prefill_odds(), Guarda las cuotas de cierre para los picks de un partido en…, Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…, Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…, submit_closing_odds()

### Community 111 - "record_hard_block"
Cohesion: 0.30
Nodes (7): _risk_imports(), is_hard_blocked(), Emite bloqueos duros sobre un pick dict-u-objeto. Irreversible. Escribe el…, True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., record_hard_block(), TestEligibilityHardBlocks, test_rule_block_persistence_on_recalculate()

### Community 112 - "Session"
Cohesion: 0.09
Nodes (35): _calculate_display_score(), Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache(), apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest (+27 more)

### Community 114 - "main.py"
Cohesion: 0.07
Nodes (31): contextlib, copy, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io, openpyxl (+23 more)

### Community 115 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones.

### Community 117 - "kelly_fractional"
Cohesion: 0.39
Nodes (3): kelly_fractional(), Función directa de Kelly Bernoulli fraccionado., TestKellyFractional

### Community 119 - "distribution_for_total_line"
Cohesion: 0.40
Nodes (4): distribution_for_total_line(), outcome_probabilities_for_total(), Convierte una PMF del total (determinista) en probabilidades de outcome para…, Atajo: PMF de totales -> ReturnDistribution lista para EV/Kelly.

### Community 120 - "outcome_from_legacy"
Cohesion: 0.29
Nodes (7): outcome_from_legacy(), Traduce un `PickOutcome` legacy al enum `Outcome`. Un valor desconocido se…, Un valor raro se excluye, no se cuenta como acierto ni como fallo., test_outcome_from_legacy_is_case_insensitive(), test_outcome_from_legacy_is_idempotent(), test_outcome_from_legacy_maps_every_case(), test_outcome_from_legacy_unknown_fails_closed()

### Community 121 - "PlattCalibrator"
Cohesion: 0.11
Nodes (15): 1. RESTRICCIONES DE ARQUITECTURA Y COMPATIBILIDAD, 2. TAREAS ESPECÍFICAS DE IMPLEMENTACIÓN, 3. FORMATO DE ENTREGA, Tarea 1: Crear `src/core/math/dixon_coles.py`, Tarea 2: Crear `src/core/math/bayesian.py`, Tarea 3: Crear `src/core/math/calibration.py`, Tarea 4: Crear `src/core/math/kelly.py`, IsotonicCalibrator (+7 more)

### Community 122 - "ExtractionStats"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

### Community 123 - "apply_calibration"
Cohesion: 0.29
Nodes (6): apply_calibration(), _coerce_datetime(), datetime, Aplica la curva jerárquica de calibración al pick según la versión activa en…, Normaliza un datetime a naive-UTC para permitir comparaciones seguras entre…, _to_naive_utc()

### Community 124 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 125 - "TrainingReport"
Cohesion: 0.40
Nodes (3): format_active_comparison(), Resultado auditable de un entrenamiento., TrainingReport

### Community 128 - "split_asian_line"
Cohesion: 0.20
Nodes (8): _matrix_over_under(), _neg_bin_pmf(), _neg_binomial_over_under(), _get_single_line_probs(), _poisson_over_under(), Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., Issue #19: Deriva Over, Push y Under de goles directamente de la matriz Dixon-…, split_asian_line()

### Community 129 - "clean_env"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

### Community 130 - "db_session"
Cohesion: 0.67
Nodes (3): db_session(), fixture, Create a temporary SQLite DB session for testing admin functionality.

## Knowledge Gaps
- **43 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+38 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 841 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `compare.py`, `test_admin_panel.py`, `compare_football`, `domain.py`, `get`, `save_analysis`, `evaluate_pick_rules`, `train_calibration.py`, `admin_stats_service.py`, `_check_pick_success`, `train_model_retrospective.py`, `_compute_league_season_corners`, `typing`, `get_leagues_stats`, `admin_database_service.py`, `prueba90100.py`, `submit_closing_odds`, `Session`, `main.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `TestLeagueMathEngine`, `TemporalParameterOptimizer`, `.create`, `.compute_pick_hit_rate`, `compare.py`, `compare_football`, `main.py`, `save_analysis`, `test_temporal.py`, `typing`, `test_math_engine.py`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `test_eligibility.py`, `test_invariants_and_eligibility.py`, `pick_rules_engine.py`, `hard_blocks_from_flags`, `compare.py`, `test_risk.py`, `test_eligibility_wiring.py`, `_value_indicator`, `record_hard_block`, `compare_football`, `eligibility.py`, `evaluate_pick_rules`, `is_hard`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `HierarchicalCalibrator` (e.g. with `compare_with_active()` and `train_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 22 INFERRED edges - model-reasoned connections that need verification._