# Graph Report - Sherlock  (2026-10-19)

## Corpus Check
- 124 files · ~788,297 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 2, .db 2, .example 1)

## Summary
- 2278 nodes · 5368 edges · 125 communities (91 shown, 34 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 359 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3813a4b8`
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
- admin_database_service.py
- leagues.js
- test_train_calibration.py
- compare_football
- manual_loader.py
- test_calibration.py
- extract_samples
- main.py
- BlockReason
- save_analysis
- stake_engine.py
- evaluate_pick_rules
- evaluate_oof_comparison.py
- pathlib
- train_calibration.py
- typing
- test_settlement.py
- _explicit_market_support
- manifest.json
- market_probability.py
- LeagueMathEngine
- stream_football_analysis
- line_bucket_for
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- hard_blocks_from_flags
- schemas.py
- compute_segment_report
- parse_utc
- test_regression_biases.py
- _invalidate_stats_cache
- TemporalCutoff
- calibration.py
- market_taxonomy.py
- json
- CalibrationCurve
- apply_portfolio_exposure_cap
- parallel_recalc.py
- CalibrationSample
- test_invariants_and_eligibility.py
- walk_forward_calibrate
- count_models.py
- calculate_league_params.py
- AnalysisHistory
- test_admin_panel.py
- admin.js
- admin_routes.py
- CardsConvention
- test_stake_and_traceability.py
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- backtesting.py
- evaluate_segment_status
- settlement.py
- pick_rules_engine.py
- content.js
- update_governance.py
- market_group_key
- 2. Paso a Paso del Nuevo Pipeline
- backup_db.py
- TestStakeEngine
- sherlock
- math_engine.py
- logging
- domain.py
- h2h_shrinkage.py
- _value_indicator
- _normalize_betano_odds
- record_hard_block
- Session
- compute_edge
- make_pick
- _dc_score_matrix
- RiskPolicyConfig
- kelly_fractional
- PredictionRecord
- outcome_from_legacy
- planning.md
- ExtractionStats
- re
- test_threshold_families_match_the_legacy_sets

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 79 edges
2. `AnalysisHistory` - 73 edges
3. `compare_football()` - 67 edges
4. `HierarchicalCalibrator` - 42 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 35 edges
8. `CalibrationSample` - 34 edges
9. `_value_indicator()` - 33 edges
10. `ReturnDistribution` - 32 edges

## Surprising Connections (you probably didn't know these)
- `4. Valor, filtros, riesgo y correlación` --references--> `_team_strength_score()`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `2. Modelo` --references--> `AnalysisHistory`  [INFERRED]
  planning.md → src/core/domain.py
- `2. Modelo` --references--> `_estimate_league_variance()`  [INFERRED]
  planning.md → src/ui/api/compare.py
- `calculate_parameters_per_match()` --uses--> `LeagueMathEngine`  [INFERRED]
  calculate_league_params.py → src/core/math_engine.py
- `build_comparison_report()` --uses--> `SegmentStatus`  [INFERRED]
  scripts/evaluate_oof_comparison.py → src/models/segment_governance.py

## Import Cycles
- None detected.

## Communities (125 total, 34 thin omitted)

### Community 0 - "HierarchicalCalibrator"
Cohesion: 0.09
Nodes (19): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, _build_history_cache_key(), get_calibration_version_for_timestamp(), get_calibrator(), get_calibrator_for_timestamp(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.… (+11 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "test_eligibility.py"
Cohesion: 0.09
Nodes (50): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+42 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 6 - "compare.py"
Cohesion: 0.06
Nodes (43): dotenv, numpy, openai, pydantic_alias_generators, _are_contradictory(), _call_openrouter(), _canonical_pick_signature(), _combine_nb_params() (+35 more)

### Community 7 - "Outcome"
Cohesion: 0.16
Nodes (17): Outcome, outcome_hit_value(), outcome_return(), Enum, str, Resultados posibles de una apuesta liquidada., Convierte un outcome + cuota en retorno económico. Si el pick no puede…, Retorno NETO (profit) por 1 unidad apostada, en cuota decimal. WIN -> +(odds -… (+9 more)

### Community 8 - "test_risk.py"
Cohesion: 0.11
Nodes (24): load_risk_limits(), PublicationMode, clean_env(), fixture, parametrize, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Un valor ininteligible no debe abrir la publicación real. `flase` es un typo…, Verifica que el archivo pick_rules.json contiene la lista de reglas. (+16 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (24): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+16 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (33): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+25 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "admin_database_service.py"
Cohesion: 0.18
Nodes (18): ColumnSchemaInfo, DatabaseRowsOut, DatabaseRowUpdate, DatabaseTableInfo, DatabaseTableSchema, get_table_schema(), list_whitelisted_tables(), Any (+10 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - "test_train_calibration.py"
Cohesion: 0.20
Nodes (20): random, history_dir_for(), Ajusta, valida y (si mejora) promueve el calibrador. `force` publica el…, Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, train_calibrator(), _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra…, Si el modelo ya está bien calibrado, la curva no puede mejorar de forma… (+12 more)

### Community 15 - "compare_football"
Cohesion: 0.17
Nodes (28): compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda() (+20 more)

### Community 16 - "manual_loader.py"
Cohesion: 0.07
Nodes (30): ABC, pandas, BettingLine, Competition, Match, A single fixture / game between two teams or players., A single betting market line for a match., Aggregated team stats for a single match. (+22 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.09
Nodes (41): brier_score(), expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators. (+33 more)

### Community 18 - "extract_samples"
Cohesion: 0.24
Nodes (20): extract_samples(), Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _family(), Sin fecha no se puede garantizar ausencia de fuga temporal., Resolver falso: devuelve el outcome legacy asociado a cada selección., Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob., _resolver_map(), _row() (+12 more)

### Community 19 - "main.py"
Cohesion: 0.06
Nodes (49): contextlib, copy, fastapi_middleware_cors, fastapi_staticfiles, middleware, openpyxl, openpyxl_utils, consume_prefill() (+41 more)

### Community 20 - "BlockReason"
Cohesion: 0.08
Nodes (24): BlockReason, _coerce_reason(), describe(), EligibilityDecision, is_hard(), str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos. (+16 more)

### Community 21 - "save_analysis"
Cohesion: 0.12
Nodes (18): Exception, _check_payload_has_odds(), _has_valid(), _extract_bookmaker(), _extract_competition(), push_result(), quick_save_match(), Browser extension pushes match results here (e.g. from flashscore). Tries to… (+10 more)

### Community 22 - "stake_engine.py"
Cohesion: 0.17
Nodes (18): dataclasses, compute_final_stake(), _parse_bool_env(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly() (+10 more)

### Community 23 - "evaluate_pick_rules"
Cohesion: 0.18
Nodes (10): evaluate_pick_rules(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio…, Devuelve (is_blocked, reason) si selection es una string. Si selection es una…, StatSource (+2 more)

### Community 24 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 25 - "pathlib"
Cohesion: 0.15
Nodes (13): argparse, Connection, dividir_archivo(), main(), Divide un archivo .py en partes de N lineas y genera archivos .txt. Uso: python…, pathlib, Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, sqlite3 (+5 more)

### Community 26 - "train_calibration.py"
Cohesion: 0.11
Nodes (23): _coerce_cutoff_datetime(), _coerce_datetime(), _league_already_calibrated(), load_rows_from_db(), main(), _pick_probability(), Any, datetime (+15 more)

### Community 27 - "typing"
Cohesion: 0.10
Nodes (35): datetime, io, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData (+27 more)

### Community 28 - "test_settlement.py"
Cohesion: 0.16
Nodes (28): _combine_legs(), line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Combina los resultados de las piernas (cada una con media unidad). Solo se usan…, Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap() (+20 more)

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
Cohesion: 0.07
Nodes (18): LeagueMathEngine, Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa…, Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás., Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros,… (+10 more)

### Community 33 - "stream_football_analysis"
Cohesion: 0.29
Nodes (7): _call_llm_for_result(), Llama al LLM usando las funciones internas de compare.py sin importarlas., Generador SSE genérico: calcula resultado + llama LLM + hace streaming., Stream LLM analysis for a football match via SSE., _sse_stream(), event_generator(), stream_football_analysis()

### Community 34 - "line_bucket_for"
Cohesion: 0.12
Nodes (9): line_bucket_for(), load_line_buckets(), Determina la banda de línea (line_bucket) para una familia y número de línea…, Carga bandas de línea desde un archivo JSON si existe, o retorna las…, test_line_buckets(), Regression: Debe resolverse con banda core y calibración específica., Regression: Debe usar high/extreme bucket, no la curva genérica de goals over., TestArgentinaShotsTargetUnderCore (+1 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - ".create"
Cohesion: 0.09
Nodes (16): filter_before_cutoff(), Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el…, Un partido a las 20:00 en Bogotá es 01:00 UTC del día siguiente. Comparar…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no… (+8 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "hard_blocks_from_flags"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 40 - "schemas.py"
Cohesion: 0.18
Nodes (19): field_validator, pydantic, AnalysisHistoryOut, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut (+11 more)

### Community 41 - "compute_segment_report"
Cohesion: 0.22
Nodes (9): _compute_ece(), compute_segment_report(), Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, Calcula el reporte completo de un segmento a partir de sus traces y resultados.…, Expected Calibration Error con n_bins bins uniformes., Genera recomendación operativa simple basada en métricas., _recommend(), _safe_log() (+1 more)

### Community 42 - "parse_utc"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "test_regression_biases.py"
Cohesion: 0.12
Nodes (17): pytest, derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz… (+9 more)

### Community 44 - "_invalidate_stats_cache"
Cohesion: 0.09
Nodes (21): delete, put, deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches(), _invalidate_stats_cache(), Any (+13 more)

### Community 45 - "TemporalCutoff"
Cohesion: 0.08
Nodes (17): CutoffRequired, FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Instante a partir del cual la información no existe todavía. `kickoff` siempre… (+9 more)

### Community 46 - "calibration.py"
Cohesion: 0.23
Nodes (19): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+11 more)

### Community 47 - "market_taxonomy.py"
Cohesion: 0.15
Nodes (18): extract_market_line(), MarketFamily, MarketKey, MarketSide, normalize_market_family(), normalize_market_side(), parse_market(), Enum (+10 more)

### Community 48 - "json"
Cohesion: 0.18
Nodes (17): fastapi_testclient, json, requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data() (+9 more)

### Community 49 - "CalibrationCurve"
Cohesion: 0.15
Nodes (9): CalibrationCurve, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_curve_roundtrip_serialization() (+1 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.09
Nodes (39): asyncio, Sport, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes() (+31 more)

### Community 52 - "CalibrationSample"
Cohesion: 0.12
Nodes (10): CalibrationSample, Una observación histórica para ajustar la calibración., Clave del diseño: con poca muestra el ruido NO puede dominar. 8 observaciones…, test_large_sample_does_move(), test_prior_strength_controls_shrinkage(), test_small_sample_barely_moves_from_prior(), Timestamps futuros no producen peso > 1.0., Walk-forward: train siempre precede al test; no data leakage. (+2 more)

### Community 53 - "test_invariants_and_eligibility.py"
Cohesion: 0.12
Nodes (22): _as_float(), _pget(), PickSnapshot, _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de… (+14 more)

### Community 54 - "walk_forward_calibrate"
Cohesion: 0.24
Nodes (8): evaluate(), SegmentEvaluation, walk_forward_calibrate(), WalkForwardResult, test_improved_is_false_when_calibration_hurts(), test_walk_forward_empty_input(), test_walk_forward_produces_oof_predictions(), test_walk_forward_skips_folds_without_enough_training_data()

### Community 55 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 56 - "calculate_league_params.py"
Cohesion: 0.15
Nodes (21): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+13 more)

### Community 57 - "AnalysisHistory"
Cohesion: 0.06
Nodes (54): AnalysisHistory, History of manual analyses performed in the comparator., build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _check_projected_line_success(), _combine_split_outcomes(), export_excel_report() (+46 more)

### Community 58 - "test_admin_panel.py"
Cohesion: 0.07
Nodes (49): DeclarativeBase, patch, Base, Declarative base for all ORM models., AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., OperationalFieldsUpdate, PaginationMeta (+41 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.10
Nodes (37): fastapi_responses, fastapi_templating, get_audit_logs(), Session, Retrieve audit logs with optional filtering., admin_dashboard_page(), admin_database_page(), admin_mark_recalculation() (+29 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "test_stake_and_traceability.py"
Cohesion: 0.18
Nodes (9): generate_segment_reports(), PickTrace, Reporte completo de un segmento league+family+side+bucket. Incluye: picks, hit…, Snapshot inmutable de trazabilidad de un pick para audit y reportes. Contiene…, Agrupa traces por segment_key y genera un SegmentReport para cada uno. Returns:…, SegmentReport, _make_trace(), Tests del motor de stake y trazabilidad. (+1 more)

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
Cohesion: 0.15
Nodes (14): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling… (+6 more)

### Community 68 - "evaluate_segment_status"
Cohesion: 0.14
Nodes (18): main(), evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str, Módulo para el monitor de drift y la gobernanza automática de segmentos., Retorna los multiplicadores de stake y ajustes de edge según el estado de… (+10 more)

### Community 69 - "settlement.py"
Cohesion: 0.17
Nodes (12): functools, math, distribution_for_total_line(), outcome_probabilities_for_total(), Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de…, Liquida un mercado binario sin push (BTTS, 1X2, doble oportunidad). Falla…, Convierte una PMF del total (determinista) en probabilidades de outcome para…, Atajo: PMF de totales -> ReturnDistribution lista para EV/Kelly. (+4 more)

### Community 70 - "pick_rules_engine.py"
Cohesion: 0.12
Nodes (24): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), load_pick_rules_data(), market_correlation_rho(), market_family(), market_group(), market_line() (+16 more)

### Community 72 - "update_governance.py"
Cohesion: 0.21
Nodes (14): build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary(), Path, update_governance.py ==================== Genera automaticamente… (+6 more)

### Community 73 - "market_group_key"
Cohesion: 0.15
Nodes (14): market_group_key(), Genera la clave canónica del grupo/segmento de mercado., compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento…, R_sample = 1 - exp(-n / target_n) (+6 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 75 - "backup_db.py"
Cohesion: 0.24
Nodes (9): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), os (+1 more)

### Community 76 - "TestStakeEngine"
Cohesion: 0.33
Nodes (3): compute_stake_final(), Calcula el stake final aplicando ajuste de factores, drawdown scale y límites., TestStakeEngine

### Community 105 - "math_engine.py"
Cohesion: 0.08
Nodes (19): calculate_dixon_coles_matrix(), calculate_time_decay_weight(), calculate_weighted_average(), dixon_coles_tau(), estimate_nb_dispersion(), load_calculated_league_params(), _poisson_pmf(), Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).… (+11 more)

### Community 106 - "logging"
Cohesion: 0.20
Nodes (12): logging, parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload… (+4 more)

### Community 107 - "domain.py"
Cohesion: 0.09
Nodes (23): enum, FastAPI, listens_for, sqlalchemy, sqlalchemy_orm, _column_exists(), create_indexes(), init_db() (+15 more)

### Community 108 - "h2h_shrinkage.py"
Cohesion: 0.38
Nodes (6): evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)., Evalúa la señal H2H sin emitir bloqueos duros para n < 8. Si n >= 8 y el hit…, shrunk_h2h_rate()

### Community 109 - "_value_indicator"
Cohesion: 0.07
Nodes (37): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), apply_calibration(), _calculate_display_score(), _calculate_kelly_fraction(), _calculate_stake_units(), calibration_is_active() (+29 more)

### Community 110 - "_normalize_betano_odds"
Cohesion: 0.33
Nodes (4): _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…

### Community 111 - "record_hard_block"
Cohesion: 0.22
Nodes (9): _risk_imports(), is_hard_blocked(), Emite bloqueos duros sobre un pick dict-u-objeto. Irreversible. Escribe el…, True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., record_hard_block(), Un segmento BLOCKED debe emitir un hard block irrecuperable., test_record_hard_block_works_on_dict(), test_record_hard_block_works_on_object() (+1 more)

### Community 112 - "Session"
Cohesion: 0.06
Nodes (46): Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, is_underdog_pick(), Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., Score de Calidad Multidimensional (0 a 100) para clasificar y filtrar picks.…, reset_governance_cache(), score_pick_quality(), apply_blacklist(), apply_pick_rules() (+38 more)

### Community 113 - "compute_edge"
Cohesion: 0.31
Nodes (3): compute_edge(), EdgeResult, TestEdgeComputation

### Community 114 - "make_pick"
Cohesion: 0.24
Nodes (10): make_pick(), published(), REGRESIÓN: `is_candidate_valid` no miraba `correlation_blocked`, así que una…, test_clean_pick_is_not_hard_blocked(), test_correlated_pick_is_labelled_correlation(), test_correlation_is_idempotent_over_many_passes(), test_is_hard_blocked_detects_legacy_flag_only(), test_kill_switch_blocks_every_pick_in_the_engine() (+2 more)

### Community 115 - "_dc_score_matrix"
Cohesion: 0.28
Nodes (9): _dc_log_likelihood(), _dc_score_matrix(), _dc_tau(), _default_dc_rho(), fit_dixon_coles_rho(), _poisson_pmf(), Heurística original — se mantiene como fallback., matches: lista de (goles_local, goles_visitante, lambda_local,… (+1 more)

### Community 117 - "kelly_fractional"
Cohesion: 0.39
Nodes (3): kelly_fractional(), Función directa de Kelly Bernoulli fraccionado., TestKellyFractional

### Community 119 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones.

### Community 120 - "outcome_from_legacy"
Cohesion: 0.29
Nodes (7): outcome_from_legacy(), Traduce un `PickOutcome` legacy al enum `Outcome`. Un valor desconocido se…, Un valor raro se excluye, no se cuenta como acierto ni como fallo., test_outcome_from_legacy_is_case_insensitive(), test_outcome_from_legacy_is_idempotent(), test_outcome_from_legacy_maps_every_case(), test_outcome_from_legacy_unknown_fails_closed()

### Community 121 - "planning.md"
Cohesion: 0.33
Nodes (5): 1. Datos e ingesta (Watson), 2. Modelo, 3. Calibración y taxonomía, 4. Valor, filtros, riesgo y correlación, 5. Liquidación, recálculo y operación

### Community 122 - "ExtractionStats"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

## Knowledge Gaps
- **43 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+38 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 794 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `test_admin_panel.py`, `compare.py`, `logging`, `domain.py`, `admin_database_service.py`, `_invalidate_stats_cache`, `compare_football`, `json`, `Session`, `main.py`, `parallel_recalc.py`, `save_analysis`, `planning.md`, `train_calibration.py`, `typing`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `test_eligibility.py`, `evaluate_segment_status`, `pick_rules_engine.py`, `hard_blocks_from_flags`, `compare.py`, `test_risk.py`, `test_eligibility_wiring.py`, `_value_indicator`, `record_hard_block`, `compare_football`, `make_pick`, `test_invariants_and_eligibility.py`, `evaluate_pick_rules`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `backtesting.py`, `.compute_pick_hit_rate`, `compare.py`, `math_engine.py`, `TemporalCutoff`, `compare_football`, `main.py`, `save_analysis`, `calculate_league_params.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 52 inferred relationships involving `AnalysisHistory` (e.g. with `2. Modelo` and `migrate_picks_snapshots()`) actually correct?**
  _`AnalysisHistory` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `HierarchicalCalibrator` (e.g. with `train_calibrator()` and `get_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 19 INFERRED edges - model-reasoned connections that need verification._