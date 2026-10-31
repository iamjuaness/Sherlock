# Graph Report - Sherlock  (2026-10-31)

## Corpus Check
- 132 files · ~546,162 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 2403 nodes · 5655 edges · 121 communities (86 shown, 35 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 377 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `51903f20`
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
- Outcome
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- test_admin_panel.py
- leagues.js
- test_train_calibration.py
- planning.md
- domain.py
- test_calibration.py
- extract_samples
- re
- BlockReason
- test_threshold_families_match_the_legacy_sets
- stake_engine.py
- StatSource
- evaluate_oof_comparison.py
- backup_db.py
- train_calibration.py
- typing
- test_settlement.py
- _explicit_market_support
- manifest.json
- market_probability.py
- TestLeagueMathEngine
- recalculate_all_accuracy
- market_group_key
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- hard_blocks_from_flags
- dixon_coles.py
- joint_match_distribution.py
- main.py
- parse_utc
- models/calibration.py
- test_regression_biases.py
- train_model_retrospective.py
- CalibrationCurve
- test_prefill_corners.py
- parallel_recalc.py
- CalibrationSample
- test_invariants_and_eligibility.py
- dataclasses
- calculate_league_params.py
- _check_pick_success
- admin.js
- admin_routes.py
- CardsConvention
- compute_segment_report
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- math_engine.py
- SegmentStatus
- line_bucket_for
- pick_rules_engine.py
- content.js
- json
- database.py
- 2. Paso a Paso del Nuevo Pipeline
- TestStakeEngine
- sherlock
- LeagueMathEngine
- TestCalibrationRecencyAndWalkForward
- prueba90100.py
- _value_indicator
- record_hard_block
- post
- compute_edge
- stream_football_analysis
- PredictionRecord
- RiskPolicyConfig
- kelly_fractional
- outcome_from_legacy
- PlattCalibrator
- ExtractionStats
- admin_picks_service.py
- is_hard
- TrainingReport
- math/__init__.py
- test_stake_and_traceability.py
- split_asian_line

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 79 edges
2. `AnalysisHistory` - 74 edges
3. `compare_football()` - 72 edges
4. `HierarchicalCalibrator` - 46 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 36 edges
8. `CalibrationSample` - 35 edges
9. `_value_indicator()` - 33 edges
10. `ReturnDistribution` - 32 edges

## Surprising Connections (you probably didn't know these)
- `TAREA 6: CÁLCULO OBJETIVO DE `data_quality_score`` --references--> `get_data_quality_score()`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `TAREA 3: CALIBRACIÓN EXCLUSIVA BASADA EN DATOS HISTÓRICOS` --references--> `extract_samples()`  [INFERRED]
  planning.md → src/core/train_calibration.py
- `REGLA DE ORO Y RESTRICCIONES DURAS` --references--> `LeagueStats`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `REGLA DE ORO Y RESTRICCIONES DURAS` --references--> `ValueIndicator`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `TAREA 5: GESTIÓN DE STAKE (MÁXIMO 3% DEL CAPITAL / KELLY FRACCIONAL)` --references--> `_calculate_stake_units()`  [INFERRED]
  planning.md → src/ui/api/compare.py

## Import Cycles
- None detected.

## Communities (121 total, 35 thin omitted)

### Community 0 - "HierarchicalCalibrator"
Cohesion: 0.08
Nodes (22): TAREA 3: CALIBRACIÓN EXCLUSIVA BASADA EN DATOS HISTÓRICOS, HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, apply_calibration(), _build_history_cache_key(), get_calibration_version_for_timestamp(), get_calibrator() (+14 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.07
Nodes (46): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), buildMatchKey(), delay(), extractEventInfo(), fetchAllBookmakerOdds(), fetchSofaScore() (+38 more)

### Community 3 - "test_eligibility.py"
Cohesion: 0.09
Nodes (51): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+43 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (41): functools, convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa…, PMF de la suma de dos conteos independientes. Convolución discreta exacta:… (+33 more)

### Community 5 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1, usando final_prob (#42)., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 6 - "compare.py"
Cohesion: 0.05
Nodes (88): asyncio, dotenv, numpy, openai, TAREA 2: DIVERSIFICACIÓN DINÁMICA DE `prior_n` (SHRINKAGE BAYESIANO), pydantic, pydantic_alias_generators, sklearn_isotonic (+80 more)

### Community 7 - "Outcome"
Cohesion: 0.09
Nodes (30): _combine_legs(), distribution_for_total_line(), Outcome, outcome_hit_value(), outcome_probabilities_for_total(), outcome_return(), Enum, str (+22 more)

### Community 8 - "test_risk.py"
Cohesion: 0.08
Nodes (36): load_risk_limits(), _parse_bool_env(), PublicationMode, clean_env(), make_pick(), published(), fixture, parametrize (+28 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (24): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+16 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (32): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+24 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "test_admin_panel.py"
Cohesion: 0.08
Nodes (36): patch, AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., DatabaseRowUpdate, OperationalFieldsUpdate, log_admin_action(), Any, Session (+28 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - "test_train_calibration.py"
Cohesion: 0.18
Nodes (25): history_dir_for(), Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. Promoción: el candidato…, train_calibrator(), _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra…, Si el modelo ya está bien calibrado, la curva no puede mejorar de forma…, Regresión: el historial se derivaba de una constante global, así que entrenar… (+17 more)

### Community 15 - "planning.md"
Cohesion: 0.15
Nodes (11): ENTREGABLE REQUERIDO, REGLA DE ORO Y RESTRICCIONES DURAS, TAREA 1: REFACTORIZACIÓN DEL LEAGUE RELIABILITY SCORE (LRS), TAREA 5: GESTIÓN DE STAKE (MÁXIMO 3% DEL CAPITAL / KELLY FRACCIONAL), TAREA 6: CÁLCULO OBJETIVO DE `data_quality_score`, calculate_fractional_kelly(), Kelly criterion staking calculation module., Computes fractional Kelly stake and edge percentage. b = odds - 1, q = 1 - p If… (+3 more)

### Community 16 - "domain.py"
Cohesion: 0.07
Nodes (38): ABC, DeclarativeBase, enum, Base, Declarative base for all ORM models., BettingLine, Competition, MarketType (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.10
Nodes (32): brier_score(), evaluate(), expected_calibration_error(), log_loss(), pava(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators., reliability_table() (+24 more)

### Community 18 - "extract_samples"
Cohesion: 0.24
Nodes (20): extract_samples(), Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _family(), Sin fecha no se puede garantizar ausencia de fuga temporal., Resolver falso: devuelve el outcome legacy asociado a cada selección., Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob., _resolver_map(), _row() (+12 more)

### Community 20 - "BlockReason"
Cohesion: 0.09
Nodes (21): BlockReason, _coerce_reason(), describe(), EligibilityDecision, str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno. (+13 more)

### Community 22 - "stake_engine.py"
Cohesion: 0.14
Nodes (20): dividir_archivo(), main(), Divide un archivo .py en partes de N lineas y genera archivos .txt. Uso: python…, pathlib, compute_final_stake(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.… (+12 more)

### Community 23 - "StatSource"
Cohesion: 0.22
Nodes (6): Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio…, StatSource

### Community 24 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 25 - "backup_db.py"
Cohesion: 0.22
Nodes (10): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), os (+2 more)

### Community 26 - "train_calibration.py"
Cohesion: 0.11
Nodes (28): random, _active_trained_until(), _coerce_cutoff_datetime(), _coerce_datetime(), compare_with_active(), _league_already_calibrated(), load_rows_from_db(), main() (+20 more)

### Community 27 - "typing"
Cohesion: 0.10
Nodes (35): datetime, io, pandas, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint (+27 more)

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
Cohesion: 0.10
Nodes (23): blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Calcula las métricas de Closing Line Value (CLV)., Calcula la probabilidad implícita de una cuota decimal (1 / odds). (+15 more)

### Community 32 - "TestLeagueMathEngine"
Cohesion: 0.15
Nodes (4): Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Evalúa si un partido específico cumple con el criterio de un pick. Soporta:…, Calcula el hit rate enriquecido con ponderación por reciencia exponencial,…, TestLeagueMathEngine

### Community 33 - "recalculate_all_accuracy"
Cohesion: 0.12
Nodes (16): Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), compare_teams_football() (+8 more)

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
Cohesion: 0.08
Nodes (19): Calcula el hit rate global a nivel de liga para un mercado específico para…, filter_before_cutoff(), Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, TemporalCutoff, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el… (+11 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "hard_blocks_from_flags"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 41 - "dixon_coles.py"
Cohesion: 0.13
Nodes (15): scipy_optimize, scipy_stats, build_dixon_coles_matrix(), ndarray, Dixon-Coles bivariate Poisson model with low-score correlation adjustment and…, Dixon-Coles adjustment factor tau(x, y, lambda, mu, rho) for low scores. tau(0,…, Exponential time decay weighting: phi(t) = exp(-xi * t) where t is days ago and…, Generates a normalized bivariate score matrix (max_goals + 1) x (max_goals + 1)… (+7 more)

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 44 - "main.py"
Cohesion: 0.03
Nodes (117): contextlib, copy, delete, Exception, fastapi_middleware_cors, fastapi_staticfiles, field_validator, openpyxl (+109 more)

### Community 45 - "parse_utc"
Cohesion: 0.07
Nodes (21): CutoffRequired, FilterReport, parse_utc(), Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.… (+13 more)

### Community 46 - "models/calibration.py"
Cohesion: 0.25
Nodes (18): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+10 more)

### Community 47 - "test_regression_biases.py"
Cohesion: 0.15
Nodes (20): pytest, extract_market_line(), MarketFamily, MarketKey, MarketSide, normalize_market_family(), normalize_market_side(), parse_market() (+12 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationCurve"
Cohesion: 0.15
Nodes (9): CalibrationCurve, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_curve_roundtrip_serialization() (+1 more)

### Community 50 - "test_prefill_corners.py"
Cohesion: 0.15
Nodes (12): client(), fixture, Tests para verificar el cálculo de corners por partido de la liga/temporada en…, Verifica que para 'Primera A' y temporada '2026', se calcule el promedio real…, Verifica la función de cálculo con una sesión simulada en memoria para probar…, Verifica que al mandar datos desde Watson a /api/v1/prefill: 1. Obtiene el…, Prueba el endpoint HTTP POST /api/v1/prefill y GET /api/v1/prefill., test_compute_league_season_corners_custom_session() (+4 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.17
Nodes (19): _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line(), _is_pick_hit() (+11 more)

### Community 52 - "CalibrationSample"
Cohesion: 0.09
Nodes (25): CalibrationSample, fit_curve(), _quantile_edges(), Una observación histórica para ajustar la calibración., test_hierarchical_resolution(), make_samples(), El audit: 'la curva de calibración muestra sobreconfianza fuerte en…, Si el modelo ya está calibrado, la curva debe quedarse cerca de la identidad. (+17 more)

### Community 53 - "test_invariants_and_eligibility.py"
Cohesion: 0.12
Nodes (22): _as_float(), _pget(), PickSnapshot, _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de… (+14 more)

### Community 55 - "dataclasses"
Cohesion: 0.15
Nodes (15): dataclasses, DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina. (+7 more)

### Community 56 - "calculate_league_params.py"
Cohesion: 0.17
Nodes (19): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+11 more)

### Community 57 - "_check_pick_success"
Cohesion: 0.06
Nodes (51): middleware, build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), consume_prefill(), consume_prefill_odds(), consume_result() (+43 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.07
Nodes (50): fastapi_responses, fastapi_templating, ColumnSchemaInfo, DatabaseRowsOut, DatabaseTableInfo, DatabaseTableSchema, get_audit_logs(), Retrieve audit logs with optional filtering. (+42 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "compute_segment_report"
Cohesion: 0.22
Nodes (9): _compute_ece(), compute_segment_report(), Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, Calcula el reporte completo de un segmento a partir de sus traces y resultados.…, Expected Calibration Error con n_bins bins uniformes., Genera recomendación operativa simple basada en métricas., _recommend(), _safe_log() (+1 more)

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

### Community 67 - "math_engine.py"
Cohesion: 0.07
Nodes (32): logging, math, calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.… (+24 more)

### Community 68 - "SegmentStatus"
Cohesion: 0.13
Nodes (20): main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str, Módulo para el monitor de drift y la gobernanza automática de segmentos. (+12 more)

### Community 69 - "line_bucket_for"
Cohesion: 0.12
Nodes (9): line_bucket_for(), load_line_buckets(), Determina la banda de línea (line_bucket) para una familia y número de línea…, Carga bandas de línea desde un archivo JSON si existe, o retorna las…, test_line_buckets(), Regression: Debe resolverse con banda core y calibración específica., Regression: Debe usar high/extreme bucket, no la curva genérica de goals over., TestArgentinaShotsTargetUnderCore (+1 more)

### Community 70 - "pick_rules_engine.py"
Cohesion: 0.14
Nodes (21): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line(), market_side() (+13 more)

### Community 72 - "json"
Cohesion: 0.06
Nodes (36): argparse, Connection, fastapi_testclient, json, build_output(), _classify(), compute_governance_from_calibration(), main() (+28 more)

### Community 73 - "database.py"
Cohesion: 0.12
Nodes (17): FastAPI, listens_for, sqlalchemy, sqlalchemy_orm, _column_exists(), create_indexes(), init_db(), Database engine, session factory and Base for SQLAlchemy models. (+9 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 76 - "TestStakeEngine"
Cohesion: 0.33
Nodes (3): compute_stake_final(), Calcula el stake final aplicando ajuste de factores, drawdown scale y límites., TestStakeEngine

### Community 105 - "LeagueMathEngine"
Cohesion: 0.08
Nodes (18): calculate_weighted_average(), LeagueMathEngine, load_calculated_league_params(), Any, Carga los parámetros matemáticos calculados por liga desde…, Calcula el promedio con decay exponencial según antigüedad. half_life: número…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de… (+10 more)

### Community 106 - "TestCalibrationRecencyAndWalkForward"
Cohesion: 0.25
Nodes (3): Timestamps futuros no producen peso > 1.0., Walk-forward: train siempre precede al test; no data leakage., TestCalibrationRecencyAndWalkForward

### Community 107 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 109 - "_value_indicator"
Cohesion: 0.05
Nodes (59): load_pick_rules_data(), Carga el archivo pick_rules.json y devuelve tuple (rules_list,…, apply_portfolio_exposure_cap(), Módulo para la separación entre prediction_universe y selected_portfolio.…, Aplica Simultaneous Kelly Scaling sobre una lista de ValueIndicator…, _calculate_display_score(), _calculate_kelly_fraction(), calibration_is_active() (+51 more)

### Community 111 - "record_hard_block"
Cohesion: 0.22
Nodes (10): evaluate_pick_rules(), Devuelve (is_blocked, reason) si selection es una string. Si selection es una…, _risk_imports(), is_hard_blocked(), Emite bloqueos duros sobre un pick dict-u-objeto. Irreversible. Escribe el…, True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., record_hard_block(), Un segmento BLOCKED debe emitir un hard block irrecuperable. (+2 more)

### Community 112 - "post"
Cohesion: 0.06
Nodes (39): Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, match_closing_odds_to_pick(), _normalize_betano_odds() (+31 more)

### Community 114 - "stream_football_analysis"
Cohesion: 0.29
Nodes (7): _call_llm_for_result(), Llama al LLM usando las funciones internas de compare.py sin importarlas., Generador SSE genérico: calcula resultado + llama LLM + hace streaming., Stream LLM analysis for a football match via SSE., _sse_stream(), event_generator(), stream_football_analysis()

### Community 115 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones.

### Community 117 - "kelly_fractional"
Cohesion: 0.39
Nodes (3): kelly_fractional(), Función directa de Kelly Bernoulli fraccionado., TestKellyFractional

### Community 120 - "outcome_from_legacy"
Cohesion: 0.29
Nodes (7): outcome_from_legacy(), Traduce un `PickOutcome` legacy al enum `Outcome`. Un valor desconocido se…, Un valor raro se excluye, no se cuenta como acierto ni como fallo., test_outcome_from_legacy_is_case_insensitive(), test_outcome_from_legacy_is_idempotent(), test_outcome_from_legacy_maps_every_case(), test_outcome_from_legacy_unknown_fails_closed()

### Community 121 - "PlattCalibrator"
Cohesion: 0.21
Nodes (6): IsotonicCalibrator, PlattCalibrator, ndarray, Platt Scaling via logistic regression over log-odds (logit): logit(p) = ln(p /…, Robust wrapper around sklearn.isotonic.IsotonicRegression., test_platt_and_isotonic_calibrators()

### Community 122 - "ExtractionStats"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

### Community 123 - "admin_picks_service.py"
Cohesion: 0.16
Nodes (19): PaginationMeta, PickDetailOut, PickItemOut, _dedup_correlated_picks(), _extract_picks_from_analysis(), get_pick_detail(), mark_for_recalculation(), Any (+11 more)

### Community 124 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 125 - "TrainingReport"
Cohesion: 0.40
Nodes (3): format_active_comparison(), Resultado auditable de un entrenamiento., TrainingReport

### Community 127 - "test_stake_and_traceability.py"
Cohesion: 0.15
Nodes (11): TAREA 4: UMBRALES DE PUBLICACIÓN (`is_publishable` E `is_underdog`) Y RANGOS DE CUOTA, EdgeResult, generate_segment_reports(), PickTrace, Reporte completo de un segmento league+family+side+bucket. Incluye: picks, hit…, Snapshot inmutable de trazabilidad de un pick para audit y reportes. Contiene…, Agrupa traces por segment_key y genera un SegmentReport para cada uno. Returns:…, SegmentReport (+3 more)

### Community 128 - "split_asian_line"
Cohesion: 0.20
Nodes (8): _matrix_over_under(), _neg_bin_pmf(), _neg_binomial_over_under(), _get_single_line_probs(), _poisson_over_under(), Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., Issue #19: Deriva Over, Push y Under de goles directamente de la matriz Dixon-…, split_asian_line()

## Knowledge Gaps
- **42 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+37 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 841 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `main.py` to `recalculate_all_accuracy`, `compare.py`, `typing`, `database.py`, `prueba90100.py`, `test_admin_panel.py`, `_value_indicator`, `domain.py`, `train_model_retrospective.py`, `post`, `_check_pick_success`, `train_calibration.py`, `admin_picks_service.py`, `admin_routes.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `test_eligibility.py`, `SegmentStatus`, `pick_rules_engine.py`, `hard_blocks_from_flags`, `compare.py`, `test_risk.py`, `test_eligibility_wiring.py`, `_value_indicator`, `record_hard_block`, `test_invariants_and_eligibility.py`, `is_hard`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `TestLeagueMathEngine`, `math_engine.py`, `.create`, `.compute_pick_hit_rate`, `compare.py`, `main.py`, `parse_utc`, `calculate_league_params.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `HierarchicalCalibrator` (e.g. with `TAREA 3: CALIBRACIÓN EXCLUSIVA BASADA EN DATOS HISTÓRICOS` and `compare_with_active()`) actually correct?**
  _`HierarchicalCalibrator` has 23 INFERRED edges - model-reasoned connections that need verification._