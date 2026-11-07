# Graph Report - Sherlock  (2026-11-07)

## Corpus Check
- 165 files · ~800,593 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 3, .example 1, .db 1)

## Summary
- 2730 nodes · 6346 edges · 145 communities (113 shown, 32 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 463 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `07e801e8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- json
- AnalysisHistory
- stake_engine.py
- background.js
- comparator.js
- shared.py
- parallel_recalc.py
- compare_service.py
- test_eligibility.py
- manual_loader.py
- test_count_negative_binomial.py
- test_calibration.py
- test_prefill_corners.py
- pick_rules_routes.py
- test_regression_biases.py
- _explicit_market_support
- stats_routes.py
- Sport
- leagues.js
- test_calibration_temporal.py
- market_probability.py
- popup.js
- test_eligibility_wiring.py
- test_quantitative_math.py
- BlockReason
- admin.js
- Outcome
- ReturnDistribution
- pytest
- typing
- test_train_calibration.py
- test_risk.py
- models/calibration.py
- test_admin_panel.py
- eligibility.py
- test_calibration_wiring.py
- argparse
- test_settlement.py
- SegmentStatus
- is_market_blacklisted_for_league
- prueba90100.py
- test_compare_integration.py
- manifest.json
- pick_rules_engine.py
- joint_match_distribution.py
- compare.py
- LeagueMathEngine
- train_calibration.py
- extract_samples
- record_date
- dashboard_main.js
- calculate_league_params.py
- score_matrix.py
- .create
- admin_picks_service.py
- .compute_pick_hit_rate
- compare_batch_football
- evaluate_oof_comparison.py
- update_governance.py
- backtesting.py
- _value_indicator
- parse_utc
- h2h_shrinkage.py
- math_engine.py
- PickSnapshot
- admin_routes.py
- Watson popup UI
- compare_football
- math/calibration.py
- HierarchicalCalibrator
- dataclasses
- 🎯 Sistema de Valor y Picks
- train_model_retrospective.py
- 2. Paso a Paso del Nuevo Pipeline
- Ponytail
- caveman
- Gemini Notebook Automation
- Main dashboard KPI view (/main-dashboard)
- NotebookLMService
- get_pending_closing_odds_matches
- Rules
- main.py FastAPI app and routes
- league_penalties.json blacklist rules
- Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform
- AdminAuditLog
- count_models.py
- backup_db.py
- Comparator page (dashboard.html, /compare)
- 📈 Estadísticas Recolectadas (Fútbol)
- web_routes.py
- caveman
- notebooklm-py skill (Gemini Notebook)
- Admin header navigation tabs
- Leagues performance page (/leagues)
- ⚽ Motor de Predicción (Fútbol)
- 📊 Dashboard de Rendimiento
- CardsConvention
- submit_closing_odds
- .parse_json_fields
- TestMLSGoalsOverHighExtreme
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- TOKEN OPTIMIZATION & SKILLS PROTOCOL
- config.py
- 🔄 Flujo de Trabajo Completo
- _call_openrouter
- 🌐 API REST
- 🔌 Extensión Watson (Browser)
- distribution_for_total_line
- 🚀 Instalación
- is_hard
- save_pick_rules
- content.js
- _set_sqlite_pragma
- disable_cache_in_dev
- consume_result
- math/__init__.py
- test_threshold_families_match_the_legacy_sets
- Obsidian vault context note rule
- copy
- sherlock

## God Nodes (most connected - your core abstractions)
1. `AnalysisHistory` - 85 edges
2. `compare_football()` - 83 edges
3. `BlockReason` - 80 edges
4. `HierarchicalCalibrator` - 45 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 36 edges
8. `CalibrationSample` - 35 edges
9. `_value_indicator()` - 35 edges
10. `ReturnDistribution` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Calibración por Familia de Mercado (`apply_calibration`)` --references--> `apply_calibration()`  [INFERRED]
  README.md → src/ui/api/compare.py
- `2. Análisis del Partido` --references--> `FootballCompareRequest`  [INFERRED]
  README.md → src/ui/api/compare_models.py
- `Fase 2: Visualización de Fecha en UI de Datos Automáticos` --references--> `populateAppForm()`  [INFERRED]
  planning.md → src/ui/web/static/js/comparator.js
- `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` --references--> `AnalysisHistory`  [INFERRED]
  planning.md → src/core/domain.py
- `1. Goles (`_compute_team_goals_lambda`)` --references--> `_compute_team_goals_lambda()`  [INFERRED]
  README.md → src/core/prediction/lambdas.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Calibration and governance pipeline** — scripts_nuevo_flujo_calibracion_y_gobernanza_calibration_pipeline, scripts_nuevo_flujo_calibracion_y_gobernanza_train_calibration, scripts_update_governance, scripts_nuevo_flujo_calibracion_y_gobernanza_oof_comparison, scripts_list_governance [EXTRACTED 1.00]
- **Caveman skill components** — agents_skills_caveman_skill_caveman, agents_skills_caveman_skill_caveman_voice, agents_skills_caveman_skill_persistence, agents_skills_caveman_skill_pre_send_check, agents_skills_caveman_skill_payload_verbatim [EXTRACTED 1.00]
- **Watson extraction and odds flow** — watson_popup_popup, watson_popup_stats_section, watson_popup_no_match_actions, claude_watson_extension, claude_betano_odds, watson_popup_sofascore_mapper [INFERRED 0.75]

## Communities (145 total, 32 thin omitted)

### Community 0 - "json"
Cohesion: 0.05
Nodes (58): contextlib, datetime, DeclarativeBase, enum, FastAPI, fastapi_middleware_cors, fastapi_staticfiles, fastapi_testclient (+50 more)

### Community 1 - "AnalysisHistory"
Cohesion: 0.06
Nodes (72): delete, Exception, AnalysisHistory, History of manual analyses performed in the comparator., Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), _calculate_display_score(), apply_blacklist() (+64 more)

### Community 2 - "stake_engine.py"
Cohesion: 0.06
Nodes (38): compute_distribution_kelly(), compute_edge(), compute_risk_decision(), compute_stake_final(), EdgeResult, kelly_fractional(), optimize_simultaneous_portfolio(), Motor de stake y gestión de riesgo institucional de Sherlock. Sustituye la… (+30 more)

### Community 3 - "background.js"
Cohesion: 0.06
Nodes (58): 1. Contexto y Diagnóstico, 2. Plan de Implementación por Módulos, A. Backend Sherlock: `POST /api/v1/compare/batch`, B. Extensión Watson: Botón "Analizar Jornada Próxima", DIRECTIVA DE EJECUCIÓN TÉCNICA: SHERLOCK & WATSON INTEGRATION, Fase 1: Diccionario de Alias y Normalización Multilingüe, Fase 2: Visualización de Fecha en UI de Datos Automáticos, Fase 3: Pipeline Batch "One-Click" (Watson & Sherlock Backend) (+50 more)

### Community 4 - "comparator.js"
Cohesion: 0.06
Nodes (55): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), currentMatchDate() (+47 more)

### Community 5 - "shared.py"
Cohesion: 0.06
Nodes (59): os, Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache(), post, Guarda reporte de auditoría de temporada en data/audit_season_{sId}.json, save_season_audit(), blacklist_market(), blacklist_markets_batch() (+51 more)

### Community 6 - "parallel_recalc.py"
Cohesion: 0.10
Nodes (36): asyncio, pydantic_alias_generators, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes() (+28 more)

### Community 7 - "compare_service.py"
Cohesion: 0.16
Nodes (32): openai, 1. Goles (`_compute_team_goals_lambda`), 2. Corners (`_compute_team_corners_lambda`), 3. Tarjetas (`_compute_team_cards_lambda`), 4. Tiros / Tiros a Puerta (`_compute_team_shots_lambda`, `_compute_team_shots_target_lambda`), 5. Faltas / Offsides (`_compute_team_fouls_lambda`, `_compute_team_offsides_lambda`), Cálculo de Lambdas (λ) por Mercado, Computes posterior expected rate lambda_post under conjugate Gamma-Poisson… (+24 more)

### Community 8 - "test_eligibility.py"
Cohesion: 0.09
Nodes (50): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+42 more)

### Community 9 - "manual_loader.py"
Cohesion: 0.07
Nodes (32): ABC, pandas, BettingLine, Competition, MarketType, Match, str, A single fixture / game between two teams or players. (+24 more)

### Community 10 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (42): functools, math, convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa… (+34 more)

### Community 11 - "test_calibration.py"
Cohesion: 0.06
Nodes (50): random, brier_score(), CalibrationCurve, expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges() (+42 more)

### Community 12 - "test_prefill_corners.py"
Cohesion: 0.07
Nodes (30): consume_prefill(), consume_prefill_odds(), push_prefill(), push_prefill_odds(), get, post, Rutas prefill de la API (extraídas de main.py)., Devuelve el detalle crudo de cuotas por casa acumulado hasta ahora. Single-use:… (+22 more)

### Community 13 - "pick_rules_routes.py"
Cohesion: 0.09
Nodes (25): evaluate_pick_rules(), load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio… (+17 more)

### Community 14 - "test_regression_biases.py"
Cohesion: 0.11
Nodes (26): extract_market_line(), line_bucket_for(), load_line_buckets(), MarketFamily, MarketKey, MarketSide, normalize_market_family(), normalize_market_side() (+18 more)

### Community 15 - "_explicit_market_support"
Cohesion: 0.22
Nodes (24): _clip_0_100(), _explicit_market_support(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico., stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+16 more)

### Community 16 - "stats_routes.py"
Cohesion: 0.12
Nodes (24): fastapi_responses, openpyxl, openpyxl_utils, export_excel_report(), get_all_picks(), get_global_stats(), get_leagues_stats(), build_market_key() (+16 more)

### Community 17 - "Sport"
Cohesion: 0.12
Nodes (30): pydantic, Sport, get_pending_picks_competitions(), list_competitions(), list_matches(), list_matches_count_for_competition(), list_sports(), get (+22 more)

### Community 18 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 19 - "test_calibration_temporal.py"
Cohesion: 0.08
Nodes (11): get_calibration_version_for_timestamp(), Retorna la versión de la calibración para un timestamp dado o 'unverified'., Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache(), post, Session, Reentrena el calibrador de probabilidades y publica el artefacto. Esta ruta…, train_calibrator_endpoint() (+3 more)

### Community 20 - "market_probability.py"
Cohesion: 0.06
Nodes (39): Stake Sizing (`_calculate_stake_units`), _correlated_exposure(), filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Riesgo efectivo del libro del partido: sqrt(k' R k), con k = kelly_fraction por…, Registro completo de una predicción evaluada en el universo de predicciones. (+31 more)

### Community 21 - "popup.js"
Cohesion: 0.13
Nodes (30): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkAnalyzeDayUI(), handleBulkExtractResultsUI() (+22 more)

### Community 22 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (33): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), ValueIndicator, Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye… (+25 more)

### Community 23 - "test_quantitative_math.py"
Cohesion: 0.09
Nodes (28): numpy, scipy_optimize, scipy_stats, fit_gamma_prior_from_league(), Empirical Bayes and conjugate Gamma-Poisson inference for rate parameters., Fits Gamma prior (alpha, beta) using Empirical Bayes (method of moments) from…, normalize_categorical_market(), Guarantees that any exhaustive and mutually exclusive set of event outcomes… (+20 more)

### Community 24 - "BlockReason"
Cohesion: 0.09
Nodes (22): BlockReason, _coerce_reason(), describe(), EligibilityDecision, str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno. (+14 more)

### Community 25 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 26 - "Outcome"
Cohesion: 0.11
Nodes (27): _combine_legs(), line_legs(), Outcome, outcome_hit_value(), outcome_return(), Enum, str, Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de… (+19 more)

### Community 27 - "ReturnDistribution"
Cohesion: 0.08
Nodes (23): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]…, ReturnDistribution (+15 more)

### Community 28 - "pytest"
Cohesion: 0.22
Nodes (13): pytest, main(), clip(), metrics(), roi(), outcome(), _compute_league_reliability_score(), LeagueStats (+5 more)

### Community 29 - "typing"
Cohesion: 0.10
Nodes (34): io, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs (+26 more)

### Community 30 - "test_train_calibration.py"
Cohesion: 0.10
Nodes (36): ExtractionStats, history_dir_for(), Path, Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. Promoción: el candidato…, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, train_calibrator(), outcome_from_legacy() (+28 more)

### Community 31 - "test_risk.py"
Cohesion: 0.05
Nodes (51): Filtra picks correlacionados en un mismo evento resolviendo conflictos por…, resolve_match_picks_correlation(), get_attr(), is_candidate_valid(), pick_merit_score(), _risk_imports(), is_hard_blocked(), True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse. (+43 more)

### Community 32 - "models/calibration.py"
Cohesion: 0.12
Nodes (27): CalibrationSample, _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key() (+19 more)

### Community 33 - "test_admin_panel.py"
Cohesion: 0.12
Nodes (26): ColumnSchemaInfo, DatabaseRowsOut, DatabaseRowUpdate, DatabaseTableInfo, DatabaseTableSchema, get_table_schema(), list_whitelisted_tables(), Any (+18 more)

### Community 34 - "eligibility.py"
Cohesion: 0.13
Nodes (18): _as_float(), hard_blocks_from_flags(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema…, Lee todos los bloqueos duros ya presentes en un pick, sea dict u objeto.… (+10 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "argparse"
Cohesion: 0.12
Nodes (14): argparse, collections, Connection, dividir_archivo(), main(), Divide un archivo .py en partes de N lineas y genera archivos .txt. Uso: python…, CLV por familia de mercado desde picks con `closing_odds` (se cargan por…, Monte Carlo de bankroll: remuestrea (bootstrap) las apuestas publicadas del… (+6 more)

### Community 37 - "test_settlement.py"
Cohesion: 0.20
Nodes (23): Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un mercado binario sin push (BTTS, 1X2, doble oportunidad). Falla…, settle_binary(), _settle_simple_total(), settle_total(), Side, parametrize (+15 more)

### Community 38 - "SegmentStatus"
Cohesion: 0.10
Nodes (26): pathlib, main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python…, evaluate_segment_status(), get_governance_multipliers(), load_governance_config(), Enum, str (+18 more)

### Community 39 - "is_market_blacklisted_for_league"
Cohesion: 0.16
Nodes (12): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), _calibration_side(), get_market_stake_modifier_for_league(), is_market_blacklisted_for_league(), _market_line(), _market_side() (+4 more)

### Community 40 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 41 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1, usando final_prob (#42)., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 42 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 43 - "pick_rules_engine.py"
Cohesion: 0.12
Nodes (16): re, Blacklist de Mercados por Liga (`data/league_penalties.json`), classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_line() (+8 more)

### Community 44 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 45 - "compare.py"
Cohesion: 0.11
Nodes (24): dotenv, _poisson_over_under(), _are_contradictory(), _build_history_cache_key(), calibration_is_active(), _calibration_line_bucket(), _canonical_pick_signature(), _dc_component_weights() (+16 more)

### Community 46 - "LeagueMathEngine"
Cohesion: 0.08
Nodes (16): LeagueMathEngine, Any, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa…, Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás., Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros,… (+8 more)

### Community 47 - "train_calibration.py"
Cohesion: 0.09
Nodes (33): concurrent_futures, itertools, Grid search de --folds/--prior-strength/--min-samples por corte temporal (solo…, run_cutoff(), _active_trained_until(), _coerce_cutoff_datetime(), _coerce_datetime(), compare_with_active() (+25 more)

### Community 48 - "extract_samples"
Cohesion: 0.18
Nodes (24): extract_samples(), _pick_probability(), Un partido sirve si tiene al menos el marcador final., Extrae la probabilidad CRUDA del modelo, nunca la ya calibrada. Calibrar sobre…, Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _row_has_results(), _family(), Sin fecha no se puede garantizar ausencia de fuga temporal. (+16 more)

### Community 49 - "record_date"
Cohesion: 0.11
Nodes (10): FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Reparte los registros en admitidos, posteriores y sin fecha., record_date() (+2 more)

### Community 50 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 51 - "calculate_league_params.py"
Cohesion: 0.15
Nodes (21): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+13 more)

### Community 52 - "score_matrix.py"
Cohesion: 0.09
Nodes (26): scipy_special, _combine_nb_params(), _dc_log_likelihood(), _dc_match_probs(), _dc_score_matrix(), _dc_tau(), _default_dc_rho(), fit_dixon_coles_rho() (+18 more)

### Community 53 - ".create"
Cohesion: 0.07
Nodes (22): CutoffRequired, filter_before_cutoff(), Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, TemporalCutoff (+14 more)

### Community 54 - "admin_picks_service.py"
Cohesion: 0.13
Nodes (23): market_group(), Clave familia_lado usada para consultar data/market_correlation.json., PaginationMeta, PickDetailOut, PickItemOut, _dedup_correlated_picks(), export_picks_file(), _extract_picks_from_analysis() (+15 more)

### Community 55 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 56 - "compare_batch_football"
Cohesion: 0.10
Nodes (24): compare_batch_football(), compare_teams_football(), post, Session, Stream LLM analysis for a football match via SSE., Analiza el partido y calcula TODOS los picks, aplicando line shopping…, Procesamiento batch masivo de partidos: compara, guarda en historial y extrae…, stream_football_analysis() (+16 more)

### Community 57 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 58 - "update_governance.py"
Cohesion: 0.18
Nodes (16): Manual governance overrides (auto false), data/segment_governance.json, build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary() (+8 more)

### Community 59 - "backtesting.py"
Cohesion: 0.15
Nodes (14): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling… (+6 more)

### Community 60 - "_value_indicator"
Cohesion: 0.17
Nodes (16): apply_calibration(), _calculate_kelly_fraction(), _coerce_datetime(), get_market_confidence_tier(), get_market_variance_tier(), is_underdog_pick(), is_value_pick(), _market_family() (+8 more)

### Community 61 - "parse_utc"
Cohesion: 0.16
Nodes (7): parse_utc(), True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 62 - "h2h_shrinkage.py"
Cohesion: 0.38
Nodes (6): evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)., Evalúa la señal H2H sin emitir bloqueos duros para n < 8. Si n >= 8 y el hit…, shrunk_h2h_rate()

### Community 63 - "math_engine.py"
Cohesion: 0.08
Nodes (19): calculate_dixon_coles_matrix(), calculate_time_decay_weight(), calculate_weighted_average(), dixon_coles_tau(), estimate_nb_dispersion(), load_calculated_league_params(), _poisson_pmf(), Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).… (+11 more)

### Community 64 - "PickSnapshot"
Cohesion: 0.18
Nodes (12): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad final (final_prob) o calibrada (calibrated_prob)., test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_final_prob_and_calibrated_prob() (+4 more)

### Community 65 - "admin_routes.py"
Cohesion: 0.10
Nodes (34): fastapi_templating, patch, get_audit_logs(), Session, Retrieve audit logs with optional filtering., export_stats_file(), Export filtered stats table to CSV or Excel bytes., admin_dashboard_page() (+26 more)

### Community 66 - "Watson popup UI"
Cohesion: 0.19
Nodes (15): watson/betanoOdds.js odds scraping, Watson Chrome extension (MV3), Phase 1 multilingual team alias map (TEAM_ALIASES), Phase 2 match date in UI, Phase 4 season reconciliation audit (SofaScore vs DB), Phase 5 fix HTTP 400 on POST /api/v1/analysis, Bookmaker odds section (1X2, DC, goals, corners, cards, shots), Auto-loaded data banner (prefill) (+7 more)

### Community 67 - "compare_football"
Cohesion: 0.09
Nodes (17): apply_portfolio_exposure_cap(), Aplica Simultaneous Kelly Scaling sobre una lista de ValueIndicator…, get_data_quality_score(), get_nbinom_under_over_prob(), Filtra picks correlacionados en un mismo evento garantizando la máxima…, Normaliza un datetime a naive-UTC para permitir comparaciones seguras entre…, Probabilidades Under/Over/Push para un mercado de conteo. DETERMINISTA. Antes…, Preprocesa y sanea las estadísticas del equipo para garantizar consistencia… (+9 more)

### Community 68 - "math/calibration.py"
Cohesion: 0.16
Nodes (9): sklearn_isotonic, sklearn_linear_model, IsotonicCalibrator, PlattCalibrator, ndarray, Probability calibration and market normalization modules. Provides…, Platt Scaling via logistic regression over log-odds (logit): logit(p) = ln(p /…, Robust wrapper around sklearn.isotonic.IsotonicRegression. (+1 more)

### Community 69 - "HierarchicalCalibrator"
Cohesion: 0.13
Nodes (18): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, get_calibrator(), get_calibrator_for_timestamp(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.…, Devuelve el calibrador activo en el momento predicted_at según el historial de…, make_samples() (+10 more)

### Community 70 - "dataclasses"
Cohesion: 0.14
Nodes (15): dataclasses, market_group_key(), Genera la clave canónica del grupo/segmento de mercado., compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento… (+7 more)

### Community 71 - "🎯 Sistema de Valor y Picks"
Cohesion: 0.25
Nodes (7): Calibración por Familia de Mercado (`apply_calibration`), Categorías de Picks, Display Score (0–100), League Reliability Score (LRS), Métricas por Pick (`ValueIndicator`), 🎯 Sistema de Valor y Picks, Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución.

### Community 72 - "train_model_retrospective.py"
Cohesion: 0.35
Nodes (11): requests, compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any, datetime, Determina si un partido tiene cuotas/mercados de apuestas asociados. Retorna… (+3 more)

### Community 73 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 74 - "Ponytail"
Cohesion: 0.20
Nodes (10): Quick decision matrix (phase to tool), Token optimization three-layer protocol, Before you write, Levels, Never-cut list (validation, data loss, security), Ponytail, Shortcut comment convention, Smallest complete change ladder (+2 more)

### Community 75 - "caveman"
Cohesion: 0.18
Nodes (11): Auto-clarity exception rule, Caveman output-token benchmark, Caveman sibling skills (caveman, ultracave, megacave), When to break caveman rules, caveman, Caveman voice rules (answer first, kill ceremony), Payload verbatim rule (code, paths, errors), Persistence (+3 more)

### Community 76 - "Gemini Notebook Automation"
Cohesion: 0.20
Nodes (10): Authorization Boundaries, Command Discovery, Deep Research, Failure Handling, Gemini Notebook Automation, Generation Notes, Output and Citations, Python API Baseline (+2 more)

### Community 77 - "Main dashboard KPI view (/main-dashboard)"
Cohesion: 0.18
Nodes (11): pick_rules_engine.py pick categorization, Rendimiento stats modal (analytics tabs), Category tabs (Global, Professional, Underdog), Market, odds, edge and daily profit charts, Date range filter (Rango de Rentabilidad), Export Excel report action, Summary KPI cards, Main dashboard KPI view (/main-dashboard) (+3 more)

### Community 78 - "NotebookLMService"
Cohesion: 0.16
Nodes (9): notebooklm, NotebookLMService, Any, Servicio de integración con NotebookLM (via notebooklm-py). Permite consultar…, Cliente y helper para orquestar consultas a NotebookLM., Verifica si la librería está instalada y las credenciales mínimas existen., Envía una pregunta a un notebook específico o al configurado por defecto., Lista los notebooks disponibles en la cuenta. (+1 more)

### Community 79 - "get_pending_closing_odds_matches"
Cohesion: 0.15
Nodes (13): get_pending_closing_odds_matches(), get, Session, Retorna los partidos sin resultado (final_score_home IS NULL) y próximos a…, Session, Test deduplication of correlated picks in the same match., Test get_pending_closing_odds_matches and submit_closing_odds logic., Verify exact financial and statistical formulas (ROI, Hit Rate, Break-even, Net… (+5 more)

### Community 80 - "Rules"
Cohesion: 0.20
Nodes (10): 1. Answer first, 2. Kill ceremony, 3. Short word, 4. Articles optional, meaning never, 5. One idea per sentence, 6. Payload verbatim, 7. Tool runs: bounded status, 8. User's language (+2 more)

### Community 81 - "main.py FastAPI app and routes"
Cohesion: 0.27
Nodes (10): compare.py prediction engine, Watson to Sherlock data flow, Dixon-Coles correction (low-scoring only), main.py FastAPI app and routes, Sherlock dev commands (uv, pytest, ruff), SQLite WAL mode, POST /api/v1/compare/batch, Phase 3 one-click batch pipeline (+2 more)

### Community 82 - "league_penalties.json blacklist rules"
Cohesion: 0.27
Nodes (10): league_penalties.json blacklist rules, OOF promotion gate (Brier and LogLoss), Calibration and governance pipeline (Fase 1-16), Segment governance statuses (BLOCKED, REDUCED, WATCH, EXPERIMENTAL), 9-level hierarchical calibration, Invariant and eligibility test suite, evaluate_oof_comparison.py (Systems A/B/C), train_calibration module (walk-forward OOF) (+2 more)

### Community 83 - "Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform"
Cohesion: 0.22
Nodes (8): 🏗️ Arquitectura General, ⚙️ Configuración de Ligas (Blacklist/Penalties), 📁 Estructura del Proyecto, 📝 Licencia, 🗺️ Roadmap, Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform, 📋 Tabla de Contenidos, 🔑 Variables de Entorno (`.env`)

### Community 84 - "AdminAuditLog"
Cohesion: 0.22
Nodes (10): AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., OperationalFieldsUpdate, log_admin_action(), Any, Log an administrative action safely into DB., Update authorized operational fields of an analysis with audit logging., update_operational_fields() (+2 more)

### Community 85 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 86 - "backup_db.py"
Cohesion: 0.28
Nodes (8): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), shutil

### Community 87 - "Comparator page (dashboard.html, /compare)"
Cohesion: 0.29
Nodes (8): Bayesian shrinkage priors (prior_n), Visitante team stats form, Comparator page (dashboard.html, /compare), Stats Generales toggle, Historial modal, Local team stats form, League parameter inputs (goals, corners, cards), Results modal

### Community 88 - "📈 Estadísticas Recolectadas (Fútbol)"
Cohesion: 0.25
Nodes (8): Control y Táctica, Defensivas, Disciplina, 📈 Estadísticas Recolectadas (Fútbol), Físicas, Ofensivas, Portería (Avanzado), Rating

### Community 89 - "web_routes.py"
Cohesion: 0.50
Nodes (8): get, Request, Rutas web de la API (extraídas de main.py)., serve_dashboard(), serve_leagues(), serve_main_dashboard(), serve_rules(), file_version()

### Community 90 - "caveman"
Cohesion: 0.29
Nodes (5): caveman, Example output, How to invoke, See also, What it does

### Community 91 - "notebooklm-py skill (Gemini Notebook)"
Cohesion: 0.43
Nodes (7): NotebookLM authentication and auth check, Canonical Source-to-Artifact Workflow, Chat citation offsets (UTF-16 passage resolution), Master token profile auth (master_token.json), notebooklm-py skill (Gemini Notebook), Operating Invariants, NotebookLMClient Python API baseline

### Community 92 - "Admin header navigation tabs"
Cohesion: 0.29
Nodes (7): admin_routes.py admin endpoints, Admin panel page, Base de Datos explorer tab (/admin/database), Admin detail drawer modal, Admin header navigation tabs, Explorador de Picks tab (/admin/picks), Estadisticas Avanzadas tab (/admin/stats)

### Community 93 - "Leagues performance page (/leagues)"
Cohesion: 0.29
Nodes (7): Frontend routes (/compare, /main-dashboard, /leagues, /rules), Competiciones sidebar with search and stakes toggle, Delete competition action, League detail stats (matches, picks, ROI, break-even), Leagues performance page (/leagues), Count in profitability toggle, Season filter

### Community 94 - "⚽ Motor de Predicción (Fútbol)"
Cohesion: 0.29
Nodes (7): Bayesian Shrinkage (Regresión a la Media), Blend de Probabilidades 1X2, Distribución de Poisson, Dixon-Coles (Matriz de Marcadores), Granularidad Condicional (Local / Visitante), ⚽ Motor de Predicción (Fútbol), Overround y Edge

### Community 95 - "📊 Dashboard de Rendimiento"
Cohesion: 0.29
Nodes (7): Cálculo de Profit por Pick (Stake Plano = 1 unidad), 📊 Dashboard de Rendimiento, Filtros, Gráficos, KPIs Principales, Mercados con Push/Void, Simulador de Capital

### Community 96 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 97 - "submit_closing_odds"
Cohesion: 0.40
Nodes (5): post, Guarda las cuotas de cierre para los picks de un partido en…, submit_closing_odds(), match_closing_odds_to_pick(), Dada una cuota normalizada (de _normalize_betano_odds o _merge_best_odds) y un…

### Community 100 - "betano_content.js"
Cohesion: 0.48
Nodes (5): buildSherlockPayload(), checkCurrentUrl(), extractMatchInfo(), fetchAndSendOdds(), parseBetanoOdds()

### Community 101 - "settings.js"
Cohesion: 0.62
Nodes (6): loadSettings(), resetSettings(), saveSettings(), setupEventListeners(), showStatus(), testConnection()

### Community 102 - "sofaScoreToSherlock.js"
Cohesion: 0.48
Nodes (5): buildLeagueStats(), buildSherlockPayload(), extractRefereeStats(), findTeamInStandings(), mapSofaScoreToSherlockTeamStats()

### Community 103 - "TOKEN OPTIMIZATION & SKILLS PROTOCOL"
Cohesion: 0.33
Nodes (5): 1. Entrada y Contexto (NotebookLM), 2. Implementación de Código (Ponytail), 3. Respuestas y Explicaciones (Caveman), Matriz de Decisión Rápida, TOKEN OPTIMIZATION & SKILLS PROTOCOL

### Community 104 - "config.py"
Cohesion: 0.33
Nodes (5): BaseSettings, pydantic_settings, Application configuration using pydantic-settings., Sherlock platform configuration. Values are loaded from environment variables…, Settings

### Community 105 - "🔄 Flujo de Trabajo Completo"
Cohesion: 0.33
Nodes (6): 1. Carga de Datos, 2. Análisis del Partido, 3. Guardado en Historial, 4. Registro de Resultados, 5. Dashboard de Rendimiento, 🔄 Flujo de Trabajo Completo

### Community 108 - "🌐 API REST"
Cohesion: 0.40
Nodes (5): Análisis, 🌐 API REST, Estadísticas, Integración (Watson / Extensiones), UI (Server-Side Rendered)

### Community 109 - "🔌 Extensión Watson (Browser)"
Cohesion: 0.40
Nodes (5): Configuración Extensión, 🔌 Extensión Watson (Browser), Flujo Betano, Flujo SofaScore, Funciones

### Community 113 - "distribution_for_total_line"
Cohesion: 0.40
Nodes (4): distribution_for_total_line(), outcome_probabilities_for_total(), Convierte una PMF del total (determinista) en probabilidades de outcome para…, Atajo: PMF de totales -> ReturnDistribution lista para EV/Kelly.

### Community 116 - "🚀 Instalación"
Cohesion: 0.50
Nodes (4): Extensión Watson, 🚀 Instalación, Pasos, Requisitos

### Community 117 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 120 - "save_pick_rules"
Cohesion: 0.50
Nodes (4): Any, put, Saves the full list of pick rules and structural correlation rules (overwrite)., save_pick_rules()

### Community 122 - "_set_sqlite_pragma"
Cohesion: 0.67
Nodes (3): listens_for, Apply performance PRAGMAs on every new SQLite connection., _set_sqlite_pragma()

### Community 123 - "disable_cache_in_dev"
Cohesion: 0.67
Nodes (3): middleware, disable_cache_in_dev(), Request

### Community 124 - "consume_result"
Cohesion: 0.67
Nodes (3): consume_result(), get, Dashboard/comparator polls this to detect pending match results. Returns the…

## Knowledge Gaps
- **146 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+141 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1005 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `json`, `background.js`, `shared.py`, `compare_service.py`, `test_prefill_corners.py`, `pick_rules_routes.py`, `stats_routes.py`, `Sport`, `typing`, `test_admin_panel.py`, `prueba90100.py`, `train_calibration.py`, `admin_picks_service.py`, `compare_batch_football`, `compare_football`, `train_model_retrospective.py`, `get_pending_closing_odds_matches`, `AdminAuditLog`, `submit_closing_odds`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Why does `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` connect `background.js` to `AnalysisHistory`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `compare_football()` connect `compare_football` to `json`, `AnalysisHistory`, `stake_engine.py`, `shared.py`, `parallel_recalc.py`, `compare_service.py`, `test_prefill_corners.py`, `Sport`, `market_probability.py`, `test_eligibility_wiring.py`, `test_quantitative_math.py`, `BlockReason`, `pytest`, `test_risk.py`, `is_market_blacklisted_for_league`, `compare.py`, `LeagueMathEngine`, `calculate_league_params.py`, `score_matrix.py`, `.create`, `compare_batch_football`, `_value_indicator`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `AnalysisHistory` (e.g. with `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` and `migrate_picks_snapshots()`) actually correct?**
  _`AnalysisHistory` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `HierarchicalCalibrator` (e.g. with `compare_with_active()` and `train_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 22 INFERRED edges - model-reasoned connections that need verification._