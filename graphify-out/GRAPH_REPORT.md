# Graph Report - Sherlock  (2026-11-01)

## Corpus Check
- 138 files · ~794,580 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 3, .example 1, .db 1)

## Summary
- 2541 nodes · 5838 edges · 135 communities (104 shown, 31 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 397 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `622b9ac5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestCalibrationTemporalTraceability
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
- popup.js
- AnalysisHistory
- leagues.js
- test_train_calibration.py
- get
- typing
- test_calibration.py
- extract_samples
- run_counterfactual_analysis
- EligibilityDecision
- save_analysis
- stake_engine.py
- Rules
- evaluate_oof_comparison.py
- test_calibration_temporal.py
- train_calibration.py
- admin_stats_service.py
- test_settlement.py
- _explicit_market_support
- manifest.json
- market_probability.py
- test_stake_and_traceability.py
- line_bucket_for
- schemas.py
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- TestFiltering
- .evaluate_parameters
- test_quantitative_math.py
- .compute_league_averages
- joint_match_distribution.py
- _invalidate_stats_cache
- parse_utc
- models/calibration.py
- test_regression_biases.py
- train_model_retrospective.py
- admin_database_service.py
- _compute_league_season_corners
- parallel_recalc.py
- Gemini Notebook Automation
- test_invariants_and_eligibility.py
- NotebookLMService
- count_models.py
- calculate_league_params.py
- _check_pick_success
- submit_closing_odds
- admin.js
- admin_routes.py
- CardsConvention
- _compute_league_reliability_score
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- dataclasses
- SegmentStatus
- FilterReport
- pick_rules_engine.py
- content.js
- update_governance.py
- json
- 2. Paso a Paso del Nuevo Pipeline
- h2h_shrinkage.py
- TOKEN OPTIMIZATION & SKILLS PROTOCOL
- Ponytail
- CalibrationCurve
- sherlock
- LeagueMathEngine
- TestStakeEngine
- prueba90100.py
- HierarchicalCalibrator
- _value_indicator
- get_calibrator_for_timestamp
- TestSegmentReports
- Session
- test_math_engine.py
- main.py
- PredictionRecord
- RiskPolicyConfig
- compute_edge
- Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform
- 🎯 Sistema de Valor y Picks
- 📈 Estadísticas Recolectadas (Fútbol)
- PlattCalibrator
- ExtractionStats
- test_admin_panel.py
- kelly_fractional
- ⚽ Motor de Predicción (Fútbol)
- math/__init__.py
- 📊 Dashboard de Rendimiento
- compare.py
- 🔄 Flujo de Trabajo Completo
- 🌐 API REST
- 🔌 Extensión Watson (Browser)
- 🚀 Instalación
- clean_env
- test_threshold_families_match_the_legacy_sets

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 79 edges
2. `AnalysisHistory` - 76 edges
3. `compare_football()` - 74 edges
4. `HierarchicalCalibrator` - 45 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 36 edges
8. `CalibrationSample` - 35 edges
9. `ReturnDistribution` - 32 edges
10. `_value_indicator()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `2. Análisis del Partido` --references--> `FootballCompareRequest`  [INFERRED]
  README.md → src/ui/api/compare.py
- `Calibración por Familia de Mercado (`apply_calibration`)` --references--> `apply_calibration()`  [INFERRED]
  README.md → src/ui/api/compare.py
- `Fase 2: Visualización de Fecha en UI de Datos Automáticos` --references--> `populateAppForm()`  [INFERRED]
  planning.md → src/ui/web/static/js/comparator.js
- `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` --references--> `AnalysisHistory`  [INFERRED]
  planning.md → src/core/domain.py
- `B. Extensión Watson: Botón "Analizar Jornada Próxima"` --references--> `FootballCompareRequest`  [INFERRED]
  planning.md → src/ui/api/compare.py

## Import Cycles
- None detected.

## Communities (135 total, 31 thin omitted)

### Community 0 - "TestCalibrationTemporalTraceability"
Cohesion: 0.11
Nodes (5): get_calibration_version_for_timestamp(), Retorna la versión de la calibración para un timestamp dado o 'unverified'., Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache(), TestCalibrationTemporalTraceability

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.06
Nodes (58): 1. Contexto y Diagnóstico, 2. Plan de Implementación por Módulos, A. Backend Sherlock: `POST /api/v1/compare/batch`, B. Extensión Watson: Botón "Analizar Jornada Próxima", DIRECTIVA DE EJECUCIÓN TÉCNICA: SHERLOCK & WATSON INTEGRATION, Fase 1: Diccionario de Alias y Normalización Multilingüe, Fase 2: Visualización de Fecha en UI de Datos Automáticos, Fase 3: Pipeline Batch "One-Click" (Watson & Sherlock Backend) (+50 more)

### Community 3 - "BlockReason"
Cohesion: 0.08
Nodes (66): BlockReason, describe(), evaluate_eligibility(), evaluate_soft_filters(), is_hard(), PublicationThresholds, str, Umbrales de publicación, versionados y en un solo sitio. (+58 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1, usando final_prob (#42)., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 6 - "compare_football"
Cohesion: 0.12
Nodes (38): 1. Goles (`_compute_team_goals_lambda`), 2. Corners (`_compute_team_corners_lambda`), 3. Tarjetas (`_compute_team_cards_lambda`), 4. Tiros / Tiros a Puerta (`_compute_team_shots_lambda`, `_compute_team_shots_target_lambda`), 5. Faltas / Offsides (`_compute_team_fouls_lambda`, `_compute_team_offsides_lambda`), Cálculo de Lambdas (λ) por Mercado, fit_gamma_prior_from_league(), Fits Gamma prior (alpha, beta) using Empirical Bayes (method of moments) from… (+30 more)

### Community 7 - "Outcome"
Cohesion: 0.09
Nodes (31): functools, math, _combine_legs(), distribution_for_total_line(), Outcome, outcome_hit_value(), outcome_probabilities_for_total(), outcome_return() (+23 more)

### Community 8 - "test_risk.py"
Cohesion: 0.06
Nodes (48): pytest, Filtra picks correlacionados en un mismo evento resolviendo conflictos por…, resolve_match_picks_correlation(), get_attr(), is_candidate_valid(), pick_merit_score(), _risk_imports(), is_hard_blocked() (+40 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (25): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]…, ReturnDistribution (+17 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (32): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+24 more)

### Community 11 - "popup.js"
Cohesion: 0.13
Nodes (30): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkAnalyzeDayUI(), handleBulkExtractResultsUI() (+22 more)

### Community 12 - "AnalysisHistory"
Cohesion: 0.12
Nodes (20): AnalysisHistory, History of manual analyses performed in the comparator., _check_projected_line_success(), get_analysis_by_id(), get_league_matches(), get_pending_closing_odds_matches(), list_analysis(), _populate_history_extra_fields() (+12 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - "test_train_calibration.py"
Cohesion: 0.13
Nodes (32): history_dir_for(), Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. Promoción: el candidato…, train_calibrator(), outcome_from_legacy(), Traduce un `PickOutcome` legacy al enum `Outcome`. Un valor desconocido se…, _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra… (+24 more)

### Community 15 - "get"
Cohesion: 0.08
Nodes (31): middleware, Sport, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version(), get_history_matches() (+23 more)

### Community 16 - "typing"
Cohesion: 0.05
Nodes (47): ABC, datetime, DeclarativeBase, enum, logging, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Base, Declarative base for all ORM models. (+39 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.07
Nodes (53): random, brier_score(), CalibrationSample, expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges() (+45 more)

### Community 18 - "extract_samples"
Cohesion: 0.18
Nodes (24): extract_samples(), _pick_probability(), Un partido sirve si tiene al menos el marcador final., Extrae la probabilidad CRUDA del modelo, nunca la ya calibrada. Calibrar sobre…, Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _row_has_results(), _family(), Sin fecha no se puede garantizar ausencia de fuga temporal. (+16 more)

### Community 19 - "run_counterfactual_analysis"
Cohesion: 0.25
Nodes (8): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), _calibration_line_bucket(), _calibration_side(), _extract_line_number(), Extrae y normaliza una línea numérica presente en el texto del pick., Normaliza la polaridad del pick para resolver correctamente la curva jerárquica…

### Community 20 - "EligibilityDecision"
Cohesion: 0.10
Nodes (12): _coerce_reason(), EligibilityDecision, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno., Une dos decisiones sobre el mismo pick. Los bloqueos duros se unen (nunca se…, Devuelve el `quality_score` que corresponde publicar. Un pick con bloqueo duro…, Reconstruye una decisión desde una lista plana de motivos, separando duros de… (+4 more)

### Community 21 - "save_analysis"
Cohesion: 0.12
Nodes (18): Exception, _check_payload_has_odds(), _has_valid(), _extract_bookmaker(), _extract_competition(), push_result(), Browser extension pushes match results here (e.g. from flashscore). Tries to…, Extract competition name from payload dict, avoiding json.loads in callers. (+10 more)

### Community 22 - "stake_engine.py"
Cohesion: 0.19
Nodes (16): compute_final_stake(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly(), compute_risk_decision(), optimize_simultaneous_portfolio() (+8 more)

### Community 23 - "Rules"
Cohesion: 0.09
Nodes (20): caveman, Example output, How to invoke, See also, What it does, 1. Answer first, 2. Kill ceremony, 3. Short word (+12 more)

### Community 24 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 25 - "test_calibration_temporal.py"
Cohesion: 0.09
Nodes (23): argparse, backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup() (+15 more)

### Community 26 - "train_calibration.py"
Cohesion: 0.10
Nodes (28): _active_trained_until(), _coerce_cutoff_datetime(), _coerce_datetime(), compare_with_active(), format_active_comparison(), _league_already_calibrated(), load_rows_from_db(), main() (+20 more)

### Community 27 - "admin_stats_service.py"
Cohesion: 0.11
Nodes (31): pandas, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs (+23 more)

### Community 28 - "test_settlement.py"
Cohesion: 0.17
Nodes (26): line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), _settle_simple_total(), settle_total() (+18 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.19
Nodes (25): _clip_0_100(), _explicit_market_support(), _poisson_over_under(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+17 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "market_probability.py"
Cohesion: 0.10
Nodes (23): blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Calcula las métricas de Closing Line Value (CLV)., Calcula la probabilidad implícita de una cuota decimal (1 / odds). (+15 more)

### Community 32 - "test_stake_and_traceability.py"
Cohesion: 0.18
Nodes (15): _compute_ece(), compute_segment_report(), generate_segment_reports(), PickTrace, Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, Reporte completo de un segmento league+family+side+bucket. Incluye: picks, hit…, Snapshot inmutable de trazabilidad de un pick para audit y reportes. Contiene…, Calcula el reporte completo de un segmento a partir de sus traces y resultados.… (+7 more)

### Community 33 - "line_bucket_for"
Cohesion: 0.12
Nodes (9): line_bucket_for(), load_line_buckets(), Determina la banda de línea (line_bucket) para una familia y número de línea…, Carga bandas de línea desde un archivo JSON si existe, o retorna las…, test_line_buckets(), Regression: Debe resolverse con banda core y calibración específica., Regression: Debe usar high/extreme bucket, no la curva genérica de goals over., TestArgentinaShotsTargetUnderCore (+1 more)

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
Cohesion: 0.10
Nodes (12): Calcula el hit rate global a nivel de liga para un mercado específico para…, CutoffRequired, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, TemporalCutoff, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el… (+4 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "TestFiltering"
Cohesion: 0.17
Nodes (10): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los…, El informe se registra en logs; no debe arrastrar el histórico entero. (+2 more)

### Community 40 - ".evaluate_parameters"
Cohesion: 0.16
Nodes (11): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling…, Evalúa un conjunto específico de parámetros usando rolling origin sobre…, Calcula la pérdida logarítmica (Log Loss) binaria. (+3 more)

### Community 41 - "test_quantitative_math.py"
Cohesion: 0.08
Nodes (32): asyncio, numpy, scipy_optimize, scipy_stats, sklearn_isotonic, sklearn_linear_model, Empirical Bayes and conjugate Gamma-Poisson inference for rate parameters., Computes posterior expected rate lambda_post under conjugate Gamma-Poisson… (+24 more)

### Community 42 - ".compute_league_averages"
Cohesion: 0.13
Nodes (11): Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, TemporalParameterOptimizer, calculate_time_decay_weight(), estimate_nb_dispersion(), load_calculated_league_params(), Carga los parámetros matemáticos calculados por liga desde…, Calcula el peso temporal de un partido según la distancia entre su fecha y una…, Estima el parámetro de dispersión (alpha/k) de la Binomial Negativa por Método… (+3 more)

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 44 - "_invalidate_stats_cache"
Cohesion: 0.10
Nodes (19): delete, put, deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches(), _invalidate_stats_cache(), Any (+11 more)

### Community 45 - "parse_utc"
Cohesion: 0.09
Nodes (15): parse_utc(), Any, datetime, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Reparte los registros en admitidos, posteriores y sin fecha., Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, record_date() (+7 more)

### Community 46 - "models/calibration.py"
Cohesion: 0.15
Nodes (22): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+14 more)

### Community 47 - "test_regression_biases.py"
Cohesion: 0.15
Nodes (19): extract_market_line(), MarketFamily, MarketKey, MarketSide, normalize_market_family(), normalize_market_side(), parse_market(), Enum (+11 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.35
Nodes (11): requests, compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any, datetime, Determina si un partido tiene cuotas/mercados de apuestas asociados. Retorna… (+3 more)

### Community 49 - "admin_database_service.py"
Cohesion: 0.18
Nodes (18): ColumnSchemaInfo, DatabaseRowsOut, DatabaseRowUpdate, DatabaseTableInfo, DatabaseTableSchema, get_table_schema(), list_whitelisted_tables(), Any (+10 more)

### Community 50 - "_compute_league_season_corners"
Cohesion: 0.15
Nodes (16): _compute_league_season_corners(), push_prefill(), Calcula el promedio de córners por partido para una liga y temporada, usando…, Browser extension pushes a (partial) form payload here. The Sherlock dashboard…, client(), fixture, Tests para verificar el cálculo de corners por partido de la liga/temporada en…, Verifica que para 'Primera A' y temporada '2026', se calcule el promedio real… (+8 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.06
Nodes (48): _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line(), _is_pick_hit() (+40 more)

### Community 52 - "Gemini Notebook Automation"
Cohesion: 0.15
Nodes (12): Authorization Boundaries, Canonical Source-to-Artifact Workflow, Command Discovery, Deep Research, Failure Handling, Gemini Notebook Automation, Generation Notes, Operating Invariants (+4 more)

### Community 53 - "test_invariants_and_eligibility.py"
Cohesion: 0.11
Nodes (24): _as_float(), hard_blocks_from_flags(), _pget(), PickSnapshot, _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema… (+16 more)

### Community 54 - "NotebookLMService"
Cohesion: 0.16
Nodes (9): notebooklm, NotebookLMService, Any, Servicio de integración con NotebookLM (via notebooklm-py). Permite consultar…, Cliente y helper para orquestar consultas a NotebookLM., Verifica si la librería está instalada y las credenciales mínimas existen., Envía una pregunta a un notebook específico o al configurado por defecto., Lista los notebooks disponibles en la cuenta. (+1 more)

### Community 55 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 56 - "calculate_league_params.py"
Cohesion: 0.15
Nodes (21): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+13 more)

### Community 57 - "_check_pick_success"
Cohesion: 0.07
Nodes (41): Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., split_asian_line(), build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line() (+33 more)

### Community 58 - "submit_closing_odds"
Cohesion: 0.20
Nodes (8): match_closing_odds_to_pick(), _normalize_betano_odds(), push_prefill_odds(), Guarda las cuotas de cierre para los picks de un partido en…, Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…, Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…, submit_closing_odds()

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.09
Nodes (39): patch, get_audit_logs(), Session, Retrieve audit logs with optional filtering., export_stats_file(), Export filtered stats table to CSV or Excel bytes., admin_dashboard_page(), admin_database_page() (+31 more)

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

### Community 67 - "dataclasses"
Cohesion: 0.14
Nodes (15): dataclasses, market_group_key(), Genera la clave canónica del grupo/segmento de mercado., compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento… (+7 more)

### Community 68 - "SegmentStatus"
Cohesion: 0.13
Nodes (20): main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str, Módulo para el monitor de drift y la gobernanza automática de segmentos. (+12 more)

### Community 70 - "pick_rules_engine.py"
Cohesion: 0.12
Nodes (18): re, Blacklist de Mercados por Liga (`data/league_penalties.json`), classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group() (+10 more)

### Community 72 - "update_governance.py"
Cohesion: 0.21
Nodes (14): build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary(), Path, update_governance.py ==================== Genera automaticamente… (+6 more)

### Community 73 - "json"
Cohesion: 0.06
Nodes (36): FastAPI, fastapi_testclient, json, listens_for, sqlalchemy, sqlalchemy_orm, _column_exists(), create_indexes() (+28 more)

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

### Community 82 - "CalibrationCurve"
Cohesion: 0.15
Nodes (9): CalibrationCurve, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_curve_roundtrip_serialization() (+1 more)

### Community 105 - "LeagueMathEngine"
Cohesion: 0.07
Nodes (17): calculate_weighted_average(), LeagueMathEngine, Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula el promedio con decay exponencial según antigüedad. half_life: número…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa… (+9 more)

### Community 106 - "TestStakeEngine"
Cohesion: 0.33
Nodes (3): compute_stake_final(), Calcula el stake final aplicando ajuste de factores, drawdown scale y límites., TestStakeEngine

### Community 107 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 108 - "HierarchicalCalibrator"
Cohesion: 0.19
Nodes (8): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, Menos de min_samples -> identidad, nunca una corrección inventada., test_insufficient_data_yields_identity(), test_load_rejects_unknown_format_version(), test_save_load_roundtrip(), test_untrained_calibrator_is_identity()

### Community 109 - "_value_indicator"
Cohesion: 0.09
Nodes (27): Stake Sizing (`_calculate_stake_units`), _calculate_stake_units(), _vi(), _get_governance_multiplier(), get_market_confidence_tier(), get_market_stake_modifier_for_league(), get_market_variance_tier(), get_segment_governance() (+19 more)

### Community 110 - "get_calibrator_for_timestamp"
Cohesion: 0.16
Nodes (14): apply_calibration(), _build_history_cache_key(), calibration_is_active(), _coerce_datetime(), get_calibrator(), get_calibrator_for_timestamp(), datetime, Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.… (+6 more)

### Community 111 - "TestSegmentReports"
Cohesion: 0.24
Nodes (3): _make_trace(), TestPickTrace, TestSegmentReports

### Community 112 - "Session"
Cohesion: 0.08
Nodes (39): apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, compare_batch_football(), _enrich_with_results(), _get_or_create_team() (+31 more)

### Community 113 - "test_math_engine.py"
Cohesion: 0.22
Nodes (7): calculate_dixon_coles_matrix(), dixon_coles_tau(), _poisson_pmf(), Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0,…, Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste…, Tests unitarios para el motor estadístico matemático por liga (Sherlock Math…, unittest

### Community 114 - "main.py"
Cohesion: 0.07
Nodes (34): contextlib, copy, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io, openpyxl (+26 more)

### Community 115 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones.

### Community 117 - "compute_edge"
Cohesion: 0.31
Nodes (3): compute_edge(), EdgeResult, TestEdgeComputation

### Community 118 - "Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform"
Cohesion: 0.22
Nodes (8): 🏗️ Arquitectura General, ⚙️ Configuración de Ligas (Blacklist/Penalties), 📁 Estructura del Proyecto, 📝 Licencia, 🗺️ Roadmap, Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform, 📋 Tabla de Contenidos, 🔑 Variables de Entorno (`.env`)

### Community 119 - "🎯 Sistema de Valor y Picks"
Cohesion: 0.25
Nodes (7): Calibración por Familia de Mercado (`apply_calibration`), Categorías de Picks, Display Score (0–100), League Reliability Score (LRS), Métricas por Pick (`ValueIndicator`), 🎯 Sistema de Valor y Picks, Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución.

### Community 120 - "📈 Estadísticas Recolectadas (Fútbol)"
Cohesion: 0.25
Nodes (8): Control y Táctica, Defensivas, Disciplina, 📈 Estadísticas Recolectadas (Fútbol), Físicas, Ofensivas, Portería (Avanzado), Rating

### Community 121 - "PlattCalibrator"
Cohesion: 0.21
Nodes (6): IsotonicCalibrator, PlattCalibrator, ndarray, Platt Scaling via logistic regression over log-odds (logit): logit(p) = ln(p /…, Robust wrapper around sklearn.isotonic.IsotonicRegression., test_platt_and_isotonic_calibrators()

### Community 122 - "ExtractionStats"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

### Community 123 - "test_admin_panel.py"
Cohesion: 0.08
Nodes (42): AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., OperationalFieldsUpdate, PaginationMeta, PickDetailOut, PickItemOut, log_admin_action(), Any (+34 more)

### Community 124 - "kelly_fractional"
Cohesion: 0.39
Nodes (3): kelly_fractional(), Función directa de Kelly Bernoulli fraccionado., TestKellyFractional

### Community 125 - "⚽ Motor de Predicción (Fútbol)"
Cohesion: 0.29
Nodes (7): Bayesian Shrinkage (Regresión a la Media), Blend de Probabilidades 1X2, Distribución de Poisson, Dixon-Coles (Matriz de Marcadores), Granularidad Condicional (Local / Visitante), ⚽ Motor de Predicción (Fútbol), Overround y Edge

### Community 127 - "📊 Dashboard de Rendimiento"
Cohesion: 0.29
Nodes (7): Cálculo de Profit por Pick (Stake Plano = 1 unidad), 📊 Dashboard de Rendimiento, Filtros, Gráficos, KPIs Principales, Mercados con Push/Void, Simulador de Capital

### Community 128 - "compare.py"
Cohesion: 0.05
Nodes (51): dotenv, openai, pydantic_alias_generators, load_pick_rules_data(), Carga el archivo pick_rules.json y devuelve tuple (rules_list,…, apply_portfolio_exposure_cap(), Aplica Simultaneous Kelly Scaling sobre una lista de ValueIndicator…, _are_contradictory() (+43 more)

### Community 129 - "🔄 Flujo de Trabajo Completo"
Cohesion: 0.33
Nodes (6): 1. Carga de Datos, 2. Análisis del Partido, 3. Guardado en Historial, 4. Registro de Resultados, 5. Dashboard de Rendimiento, 🔄 Flujo de Trabajo Completo

### Community 130 - "🌐 API REST"
Cohesion: 0.40
Nodes (5): Análisis, 🌐 API REST, Estadísticas, Integración (Watson / Extensiones), UI (Server-Side Rendered)

### Community 131 - "🔌 Extensión Watson (Browser)"
Cohesion: 0.40
Nodes (5): Configuración Extensión, 🔌 Extensión Watson (Browser), Flujo Betano, Flujo SofaScore, Funciones

### Community 132 - "🚀 Instalación"
Cohesion: 0.50
Nodes (4): Extensión Watson, 🚀 Instalación, Pasos, Requisitos

### Community 133 - "clean_env"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

## Knowledge Gaps
- **120 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+115 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 936 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `compare.py`, `background.js`, `compare_football`, `get`, `typing`, `save_analysis`, `train_calibration.py`, `admin_stats_service.py`, `_invalidate_stats_cache`, `train_model_retrospective.py`, `admin_database_service.py`, `_compute_league_season_corners`, `parallel_recalc.py`, `_check_pick_success`, `submit_closing_odds`, `json`, `prueba90100.py`, `_value_indicator`, `Session`, `main.py`, `test_admin_panel.py`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` connect `background.js` to `AnalysisHistory`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 55 inferred relationships involving `AnalysisHistory` (e.g. with `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` and `migrate_picks_snapshots()`) actually correct?**
  _`AnalysisHistory` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `HierarchicalCalibrator` (e.g. with `compare_with_active()` and `train_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 22 INFERRED edges - model-reasoned connections that need verification._
- **What connects `sherlock`, `adminState`, `chartInstances` to the rest of the system?**
  _120 weakly-connected nodes found - possible documentation gaps or missing edges._