# Graph Report - Sherlock  (2026-10-12)

## Corpus Check
- 120 files · ~512,929 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 2, .db 2, .example 1)

## Summary
- 2268 nodes · 5354 edges · 110 communities (79 shown, 31 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 356 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3813a4b8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TestCalibrationTemporalTraceability
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
- typing
- leagues.js
- HierarchicalCalibrator
- compare_football
- domain.py
- test_calibration.py
- push_result
- main.py
- BlockReason
- AnalysisHistory
- stake_engine.py
- _value_indicator
- evaluate_oof_comparison.py
- split_asian_line
- test_train_calibration.py
- admin_stats_service.py
- test_settlement.py
- _explicit_market_support
- manifest.json
- test_invariants_and_eligibility.py
- LeagueMathEngine
- stream_football_analysis
- TestMLSGoalsOverHighExtreme
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- eligibility.py
- schemas.py
- admin_picks_service.py
- parse_utc
- joint_match_distribution.py
- _invalidate_stats_cache
- TemporalCutoff
- calibration.py
- test_regression_biases.py
- train_model_retrospective.py
- CalibrationCurve
- apply_portfolio_exposure_cap
- parallel_recalc.py
- PickSnapshot
- CalibrationSample
- count_models.py
- calculate_league_params.py
- _check_pick_success
- test_admin_panel.py
- admin.js
- admin_routes.py
- CardsConvention
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- backtesting.py
- evaluate_segment_status
- pick_rules_engine.py
- content.js
- update_governance.py
- market_group_key
- 2. Paso a Paso del Nuevo Pipeline
- backup_db.py
- sherlock
- math_engine.py
- prueba90100.py
- json
- dataclasses
- get_calibrator_for_timestamp
- submit_closing_odds
- Session
- _get_governance_multiplier
- is_market_blacklisted_for_league

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 79 edges
2. `AnalysisHistory` - 72 edges
3. `compare_football()` - 67 edges
4. `HierarchicalCalibrator` - 42 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 35 edges
8. `CalibrationSample` - 34 edges
9. `_value_indicator()` - 33 edges
10. `ReturnDistribution` - 32 edges

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

## Communities (110 total, 31 thin omitted)

### Community 0 - "TestCalibrationTemporalTraceability"
Cohesion: 0.11
Nodes (5): get_calibration_version_for_timestamp(), Retorna la versión de la calibración para un timestamp dado o 'unverified'., Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache(), TestCalibrationTemporalTraceability

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "test_eligibility.py"
Cohesion: 0.09
Nodes (49): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+41 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 6 - "compare.py"
Cohesion: 0.07
Nodes (36): dotenv, numpy, openai, pydantic_alias_generators, _are_contradictory(), _call_openrouter(), _canonical_pick_signature(), _combine_nb_params() (+28 more)

### Community 7 - "Outcome"
Cohesion: 0.09
Nodes (33): functools, math, _combine_legs(), distribution_for_total_line(), Outcome, outcome_hit_value(), outcome_probabilities_for_total(), outcome_return() (+25 more)

### Community 8 - "test_risk.py"
Cohesion: 0.06
Nodes (49): resolve_match_picks_correlation(), get_attr(), is_candidate_valid(), pick_merit_score(), _risk_imports(), is_hard_blocked(), Emite bloqueos duros sobre un pick dict-u-objeto. Irreversible. Escribe el…, True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse. (+41 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (26): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+18 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (32): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+24 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "typing"
Cohesion: 0.12
Nodes (27): sqlalchemy, AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., AuditLogCreate, AuditLogOut, ColumnSchemaInfo, DatabaseRowsOut, DatabaseTableInfo (+19 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - "HierarchicalCalibrator"
Cohesion: 0.11
Nodes (17): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, ReliabilityBin, make_samples(), Menos de min_samples -> identidad, nunca una corrección inventada., Genera muestras sintéticas con una relación conocida prob->acierto., test_apply_is_deterministic() (+9 more)

### Community 15 - "compare_football"
Cohesion: 0.17
Nodes (28): compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda() (+20 more)

### Community 16 - "domain.py"
Cohesion: 0.07
Nodes (38): ABC, DeclarativeBase, enum, pandas, Base, Declarative base for all ORM models., BettingLine, Competition (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.09
Nodes (37): brier_score(), expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators. (+29 more)

### Community 18 - "push_result"
Cohesion: 0.29
Nodes (7): _check_payload_has_odds(), _has_valid(), _extract_competition(), push_result(), Browser extension pushes match results here (e.g. from flashscore). Tries to…, Extract competition name from payload dict, avoiding json.loads in callers., Helper to determine if a payload dict or JSON string contains valid odds (>…

### Community 19 - "main.py"
Cohesion: 0.06
Nodes (49): contextlib, copy, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io, middleware (+41 more)

### Community 20 - "BlockReason"
Cohesion: 0.09
Nodes (23): BlockReason, _coerce_reason(), describe(), EligibilityDecision, str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno. (+15 more)

### Community 21 - "AnalysisHistory"
Cohesion: 0.09
Nodes (31): Exception, field_validator, AnalysisHistory, History of manual analyses performed in the comparator., _check_projected_line_success(), _extract_bookmaker(), get_analysis_by_id(), get_league_matches() (+23 more)

### Community 22 - "stake_engine.py"
Cohesion: 0.05
Nodes (44): pathlib, compute_final_stake(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly(), compute_edge() (+36 more)

### Community 23 - "_value_indicator"
Cohesion: 0.09
Nodes (33): load_pick_rules_data(), Carga el archivo pick_rules.json y devuelve tuple (rules_list,…, _calculate_display_score(), _calculate_stake_units(), _vi(), _compute_league_reliability_score(), _frontend_style_strategic_score(), get_data_quality_score() (+25 more)

### Community 24 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 25 - "split_asian_line"
Cohesion: 0.29
Nodes (6): _neg_bin_pmf(), _neg_binomial_over_under(), _get_single_line_probs(), _poisson_over_under(), Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., split_asian_line()

### Community 26 - "test_train_calibration.py"
Cohesion: 0.06
Nodes (73): random, _coerce_cutoff_datetime(), _coerce_datetime(), extract_samples(), ExtractionStats, history_dir_for(), _league_already_calibrated(), load_rows_from_db() (+65 more)

### Community 27 - "admin_stats_service.py"
Cohesion: 0.11
Nodes (28): AccumulatedYieldPoint, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs, DashboardSummaryOut, DataAnomalyItem, GroupedStatItem (+20 more)

### Community 28 - "test_settlement.py"
Cohesion: 0.19
Nodes (24): line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), settle_total(), Side, parametrize (+16 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.22
Nodes (24): _clip_0_100(), _explicit_market_support(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico., stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+16 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "test_invariants_and_eligibility.py"
Cohesion: 0.11
Nodes (21): blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Mezcla controlada: p_final = r * p_calibrated + (1 - r) * p_market donde r =…, Calcula la probabilidad implícita de una cuota decimal (1 / odds). (+13 more)

### Community 32 - "LeagueMathEngine"
Cohesion: 0.07
Nodes (18): LeagueMathEngine, Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa…, Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás., Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros,… (+10 more)

### Community 33 - "stream_football_analysis"
Cohesion: 0.29
Nodes (7): _call_llm_for_result(), Llama al LLM usando las funciones internas de compare.py sin importarlas., Generador SSE genérico: calcula resultado + llama LLM + hace streaming., Stream LLM analysis for a football match via SSE., _sse_stream(), event_generator(), stream_football_analysis()

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

### Community 39 - "eligibility.py"
Cohesion: 0.14
Nodes (17): _as_float(), hard_blocks_from_flags(), is_hard(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema… (+9 more)

### Community 40 - "schemas.py"
Cohesion: 0.18
Nodes (19): pydantic, list_matches(), List matches with filters., Return the number of matches for a specific competition., AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat (+11 more)

### Community 41 - "admin_picks_service.py"
Cohesion: 0.17
Nodes (18): PickDetailOut, PickItemOut, _dedup_correlated_picks(), export_picks_file(), _extract_picks_from_analysis(), get_pick_detail(), mark_for_recalculation(), Session (+10 more)

### Community 42 - "parse_utc"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 44 - "_invalidate_stats_cache"
Cohesion: 0.10
Nodes (19): delete, put, deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches(), _invalidate_stats_cache(), Any (+11 more)

### Community 45 - "TemporalCutoff"
Cohesion: 0.08
Nodes (17): CutoffRequired, FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Instante a partir del cual la información no existe todavía. `kickoff` siempre… (+9 more)

### Community 46 - "calibration.py"
Cohesion: 0.17
Nodes (21): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+13 more)

### Community 47 - "test_regression_biases.py"
Cohesion: 0.10
Nodes (27): pytest, extract_market_line(), line_bucket_for(), load_line_buckets(), MarketFamily, MarketKey, MarketSide, normalize_market_family() (+19 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationCurve"
Cohesion: 0.21
Nodes (7): CalibrationCurve, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_identity_curve_is_a_noop()

### Community 51 - "parallel_recalc.py"
Cohesion: 0.08
Nodes (39): asyncio, str, Sport, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success() (+31 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.18
Nodes (12): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad final (final_prob) o calibrada (calibrated_prob)., test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_final_prob_and_calibrated_prob() (+4 more)

### Community 54 - "CalibrationSample"
Cohesion: 0.13
Nodes (13): CalibrationSample, evaluate(), Una observación histórica para ajustar la calibración., SegmentEvaluation, walk_forward_calibrate(), WalkForwardResult, tempfile, Pruebas unitarias para la trazabilidad temporal y la calibración probabilística… (+5 more)

### Community 55 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 56 - "calculate_league_params.py"
Cohesion: 0.15
Nodes (21): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+13 more)

### Community 57 - "_check_pick_success"
Cohesion: 0.07
Nodes (39): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), get_all_picks(), _get_cache() (+31 more)

### Community 58 - "test_admin_panel.py"
Cohesion: 0.10
Nodes (29): patch, DatabaseRowUpdate, OperationalFieldsUpdate, Any, Controlled, safe update of a record in a whitelisted table., update_table_row(), Update authorized operational fields of an analysis with audit logging., update_operational_fields() (+21 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.12
Nodes (31): admin_dashboard_page(), admin_database_page(), admin_mark_recalculation(), admin_picks_page(), admin_root(), admin_stats_page(), export_admin_picks(), export_admin_stats() (+23 more)

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

### Community 67 - "backtesting.py"
Cohesion: 0.15
Nodes (14): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling… (+6 more)

### Community 68 - "evaluate_segment_status"
Cohesion: 0.12
Nodes (20): main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str, Módulo para el monitor de drift y la gobernanza automática de segmentos. (+12 more)

### Community 70 - "pick_rules_engine.py"
Cohesion: 0.08
Nodes (25): re, classify_correlation_severity(), clear_correlation_matrix_cache(), evaluate_pick_rules(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group() (+17 more)

### Community 72 - "update_governance.py"
Cohesion: 0.12
Nodes (21): argparse, Connection, build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary() (+13 more)

### Community 73 - "market_group_key"
Cohesion: 0.15
Nodes (14): market_group_key(), Genera la clave canónica del grupo/segmento de mercado., compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento…, R_sample = 1 - exp(-n / target_n) (+6 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 75 - "backup_db.py"
Cohesion: 0.22
Nodes (10): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), os (+2 more)

### Community 105 - "math_engine.py"
Cohesion: 0.08
Nodes (19): calculate_dixon_coles_matrix(), calculate_time_decay_weight(), calculate_weighted_average(), dixon_coles_tau(), estimate_nb_dispersion(), load_calculated_league_params(), _poisson_pmf(), Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).… (+11 more)

### Community 106 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 107 - "json"
Cohesion: 0.07
Nodes (28): datetime, FastAPI, fastapi_testclient, json, listens_for, logging, sqlalchemy_orm, _column_exists() (+20 more)

### Community 108 - "dataclasses"
Cohesion: 0.32
Nodes (7): dataclasses, evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)., Evalúa la señal H2H sin emitir bloqueos duros para n < 8. Si n >= 8 y el hit…, shrunk_h2h_rate()

### Community 109 - "get_calibrator_for_timestamp"
Cohesion: 0.10
Nodes (22): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), apply_calibration(), _build_history_cache_key(), calibration_is_active(), _calibration_line_bucket(), _calibration_side() (+14 more)

### Community 110 - "submit_closing_odds"
Cohesion: 0.20
Nodes (8): match_closing_odds_to_pick(), _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…, Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…, Guarda las cuotas de cierre para los picks de un partido en…, submit_closing_odds()

### Community 112 - "Session"
Cohesion: 0.08
Nodes (36): Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache(), apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, _get_or_create_team() (+28 more)

### Community 114 - "_get_governance_multiplier"
Cohesion: 0.50
Nodes (4): _get_governance_multiplier(), get_segment_governance(), Devuelve el artefacto de gobernanza completo, recargandolo si cambio en disco.…, Resuelve el status de gobernanza y el multiplicador de stake para un segmento.…

### Community 117 - "is_market_blacklisted_for_league"
Cohesion: 0.27
Nodes (7): get_market_stake_modifier_for_league(), is_market_blacklisted_for_league(), _market_line(), _market_side(), _normalize_text(), Comprueba reglas de blacklist por: liga, familia, lado, línea y categoría. La…, Obtiene el multiplicador de stake para un mercado en una liga según…

## Knowledge Gaps
- **40 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+35 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 790 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `compare.py`, `typing`, `compare_football`, `domain.py`, `push_result`, `main.py`, `_value_indicator`, `test_train_calibration.py`, `admin_stats_service.py`, `schemas.py`, `admin_picks_service.py`, `_invalidate_stats_cache`, `train_model_retrospective.py`, `parallel_recalc.py`, `_check_pick_success`, `test_admin_panel.py`, `prueba90100.py`, `json`, `submit_closing_odds`, `Session`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `HierarchicalCalibrator` connect `HierarchicalCalibrator` to `TestCalibrationTemporalTraceability`, `test_calibration_wiring.py`, `evaluate_segment_status`, `compare.py`, `get_calibrator_for_timestamp`, `calibration.py`, `test_regression_biases.py`, `test_calibration.py`, `CalibrationSample`, `evaluate_oof_comparison.py`, `test_train_calibration.py`, `test_invariants_and_eligibility.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `backtesting.py`, `.compute_pick_hit_rate`, `compare.py`, `math_engine.py`, `TemporalCutoff`, `compare_football`, `main.py`, `AnalysisHistory`, `calculate_league_params.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 51 inferred relationships involving `AnalysisHistory` (e.g. with `migrate_picks_snapshots()` and `purge_odds_before_cutoff()`) actually correct?**
  _`AnalysisHistory` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `HierarchicalCalibrator` (e.g. with `train_calibrator()` and `get_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 19 INFERRED edges - model-reasoned connections that need verification._