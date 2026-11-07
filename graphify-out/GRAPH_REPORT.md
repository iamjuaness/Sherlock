# Graph Report - Sherlock  (2026-11-07)

## Corpus Check
- 128 files · ~805,007 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2708 nodes · 6188 edges · 169 communities (118 shown, 51 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 437 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 135
- Community 136
- Community 137
- Community 138
- Community 146
- Community 147
- Community 148
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157

## God Nodes (most connected - your core abstractions)
1. `AnalysisHistory` - 85 edges
2. `BlockReason` - 80 edges
3. `compare_football()` - 77 edges
4. `HierarchicalCalibrator` - 45 edges
5. `LeagueMathEngine` - 36 edges
6. `good_snapshot()` - 36 edges
7. `CalibrationSample` - 35 edges
8. `_value_indicator()` - 32 edges
9. `Outcome` - 31 edges
10. `EligibilityDecision` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Calibración por Familia de Mercado (`apply_calibration`)` --references--> `apply_calibration()`  [INFERRED]
  README.md → src/ui/api/compare.py
- `Fase 2: Visualización de Fecha en UI de Datos Automáticos` --references--> `populateAppForm()`  [INFERRED]
  planning.md → src/ui/web/static/js/comparator.js
- `Stake Sizing (`_calculate_stake_units`)` --references--> `_calculate_stake_units()`  [INFERRED]
  README.md → src/ui/api/compare.py
- `1. Contexto y Diagnóstico` --references--> `normalizeTeamName()`  [INFERRED]
  planning.md → watson/betanoOdds.js
- `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` --references--> `AnalysisHistory`  [INFERRED]
  planning.md → src/core/domain.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Calibration and governance pipeline** — scripts_nuevo_flujo_calibracion_y_gobernanza_calibration_pipeline, scripts_nuevo_flujo_calibracion_y_gobernanza_train_calibration, scripts_update_governance, scripts_nuevo_flujo_calibracion_y_gobernanza_oof_comparison, scripts_list_governance [EXTRACTED 1.00]
- **Caveman skill components** — agents_skills_caveman_skill_caveman, agents_skills_caveman_skill_caveman_voice, agents_skills_caveman_skill_persistence, agents_skills_caveman_skill_pre_send_check, agents_skills_caveman_skill_payload_verbatim [EXTRACTED 1.00]
- **Watson extraction and odds flow** — watson_popup_popup, watson_popup_stats_section, watson_popup_no_match_actions, claude_watson_extension, claude_betano_odds, watson_popup_sofascore_mapper [INFERRED 0.75]

## Communities (169 total, 51 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (88): datetime, DeclarativeBase, enum, fastapi_testclient, json, sqlalchemy, sqlalchemy_orm, Base (+80 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (84): delete, Exception, Sport, Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), _calculate_display_score(), CompareResponse, FootballCompareRequest (+76 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (42): ReturnDistribution, compute_final_stake(), Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly(), compute_edge(), compute_risk_decision() (+34 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (58): 1. Contexto y Diagnóstico, 2. Plan de Implementación por Módulos, A. Backend Sherlock: `POST /api/v1/compare/batch`, B. Extensión Watson: Botón "Analizar Jornada Próxima", DIRECTIVA DE EJECUCIÓN TÉCNICA: SHERLOCK & WATSON INTEGRATION, Fase 1: Diccionario de Alias y Normalización Multilingüe, Fase 2: Visualización de Fecha en UI de Datos Automáticos, Fase 3: Pipeline Batch "One-Click" (Watson & Sherlock Backend) (+50 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (55): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), currentMatchDate() (+47 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (57): Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache(), post, Rutas audit de la API (extraídas de main.py)., Guarda reporte de auditoría de temporada en data/audit_season_{sId}.json, save_season_audit(), blacklist_market(), blacklist_markets_batch() (+49 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (48): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), notebooklm (+40 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (46): openai, fit_gamma_prior_from_league(), Fits Gamma prior (alpha, beta) using Empirical Bayes (method of moments) from…, Computes posterior expected rate lambda_post under conjugate Gamma-Poisson…, update_gamma_poisson(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda() (+38 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (51): evaluate_eligibility(), evaluate_soft_filters(), PublicationThresholds, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, good_snapshot(), parametrize (+43 more)

### Community 9 - "Community 9"
Cohesion: 0.07
Nodes (33): ABC, pandas, BettingLine, Competition, MarketType, Match, str, A single fixture / game between two teams or players. (+25 more)

### Community 10 - "Community 10"
Cohesion: 0.08
Nodes (41): functools, convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa…, PMF de la suma de dos conteos independientes. Convolución discreta exacta:… (+33 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (46): brier_score(), expected_calibration_error(), fit_curve(), log_loss(), pava(), _quantile_edges(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators. (+38 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (39): contextlib, FastAPI, fastapi_middleware_cors, fastapi_staticfiles, _column_exists(), create_indexes(), init_db(), Create indexes for analysis_history and related tables. (+31 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (35): evaluate_pick_rules(), load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio… (+27 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (30): pytest, Entrenamiento del calibrador de Sherlock a partir de picks liquidados. Flujo…, # NOTE: _extract_line_bucket, _resolve_market_side y market_family_fn, extract_market_line(), line_bucket_for(), load_line_buckets(), market_group_key(), MarketFamily (+22 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (33): dotenv, _poisson_over_under(), _clip_0_100(), _dc_component_weights(), _explicit_market_support(), _frontend_style_strategic_score(), _market_risk_weight(), _odds_risk_penalty() (+25 more)

### Community 16 - "Community 16"
Cohesion: 0.09
Nodes (34): DataFrame, fastapi_responses, openpyxl, openpyxl_utils, export_excel_report(), get_all_picks(), get_global_stats(), get_leagues_stats() (+26 more)

### Community 17 - "Community 17"
Cohesion: 0.10
Nodes (34): field_validator, pydantic, Update final match results and calculate accuracy., update_analysis_results(), get_pending_picks_competitions(), list_competitions(), list_matches(), list_matches_count_for_competition() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (21): CalibrationSample, Una observación histórica para ajustar la calibración., SegmentEvaluation, walk_forward_calibrate(), _build_history_cache_key(), get_calibration_version_for_timestamp(), get_calibrator_for_timestamp(), Clave de caché basada en los paths y mtimes de los artefactos. (+13 more)

### Community 20 - "Community 20"
Cohesion: 0.10
Nodes (23): blend_model_and_market_probability(), BlendResult, CLVResult, compute_clv(), implied_probability(), Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Calcula las métricas de Closing Line Value (CLV)., Calcula la probabilidad implícita de una cuota decimal (1 / odds). (+15 more)

### Community 21 - "Community 21"
Cohesion: 0.13
Nodes (30): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkAnalyzeDayUI(), handleBulkExtractResultsUI() (+22 more)

### Community 22 - "Community 22"
Cohesion: 0.14
Nodes (33): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), ValueIndicator, Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye… (+25 more)

### Community 23 - "Community 23"
Cohesion: 0.09
Nodes (27): numpy, scipy_optimize, scipy_stats, sklearn_isotonic, sklearn_linear_model, Empirical Bayes and conjugate Gamma-Poisson inference for rate parameters., normalize_categorical_market(), Probability calibration and market normalization modules. Provides… (+19 more)

### Community 24 - "Community 24"
Cohesion: 0.09
Nodes (21): BlockReason, _coerce_reason(), describe(), EligibilityDecision, str, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno. (+13 more)

### Community 25 - "Community 25"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (28): _combine_legs(), Outcome, outcome_from_legacy(), outcome_hit_value(), outcome_return(), Enum, str, Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de… (+20 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (23): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]…, ReturnDistribution (+15 more)

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (25): asyncio, _are_contradictory(), _compute_league_reliability_score(), get_data_quality_score(), _implied_prob_from_odds(), FootballOdds, FootballTeamStats, LeagueStats (+17 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (24): io, AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs (+16 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (25): random, history_dir_for(), Directorio de versiones ANTIGUAS, siempre junto al artefacto activo. Se deriva…, Ajusta, valida y (si mejora) promueve el calibrador. Promoción: el candidato…, train_calibrator(), _overconfident_samples(), Tests del pipeline de entrenamiento del calibrador. Contrato: - Se calibra…, Si el modelo ya está bien calibrado, la curva no puede mejorar de forma… (+17 more)

### Community 31 - "Community 31"
Cohesion: 0.11
Nodes (23): load_risk_limits(), _parse_bool_env(), PublicationMode, Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, parametrize, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Un valor ininteligible no debe abrir la publicación real. `flase` es un typo…, Verifica que el archivo pick_rules.json contiene la lista de reglas. (+15 more)

### Community 32 - "Community 32"
Cohesion: 0.17
Nodes (21): _clean_val(), compute_sample_weight(), family_key(), family_side_bucket_key(), family_side_key(), league_family_key(), league_family_side_bucket_key(), league_family_side_key() (+13 more)

### Community 33 - "Community 33"
Cohesion: 0.12
Nodes (27): fastapi_templating, patch, ColumnSchemaInfo, DatabaseRowsOut, DatabaseRowUpdate, DatabaseTableInfo, DatabaseTableSchema, get_table_schema() (+19 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (20): _risk_imports(), _as_float(), is_hard_blocked(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema… (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "Community 36"
Cohesion: 0.11
Nodes (19): argparse, Connection, dividir_archivo(), main(), Divide un archivo .py en partes de N lineas y genera archivos .txt. Uso: python…, pathlib, main(), Script de utilidad para listar segmentos por estado de gobernanza. Uso: python… (+11 more)

### Community 37 - "Community 37"
Cohesion: 0.19
Nodes (24): line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), settle_total(), Side, parametrize (+16 more)

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (16): evaluate_segment_status(), get_governance_multipliers(), Retorna los multiplicadores de stake y ajustes de edge según el estado de…, Evalúa el estado de gobernanza de un segmento según evidencia y configuración…, SegmentStatus, _get_governance_multiplier(), get_segment_governance(), Devuelve el artefacto de gobernanza completo, recargandolo si cambio en disco.… (+8 more)

### Community 39 - "Community 39"
Cohesion: 0.11
Nodes (22): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), _calibration_line_bucket(), _calibration_side(), _canonical_pick_signature(), _deduplicate_correlated_picks(), _extract_line_number() (+14 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (19): Script CLI para calcular parámetros matemáticos (Dixon-Coles, promedios por…, logging, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, get_league_profile(), load_league_profiles_config(), Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).…, Carga perfiles y ligas desde data/league_profiles.json si existe., Obtiene los parámetros del perfil de histórico para una competición. Carga… (+11 more)

### Community 41 - "Community 41"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1, usando final_prob (#42)., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 42 - "Community 42"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (21): Blacklist de Mercados por Liga (`data/league_penalties.json`), classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line() (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (14): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win(), test_joint_match_invariants() (+6 more)

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (13): calculate_weighted_average(), LeagueMathEngine, Calcula el promedio con decay exponencial según antigüedad. half_life: número…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa…, Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás., Calcula el valor esperado para mercados secundarios (corners, tarjetas, tiros,… (+5 more)

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (6): Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Evalúa si un partido específico cumple con el criterio de un pick. Soporta:…, Calcula el hit rate global a nivel de liga para un mercado específico para…, Calcula el hit rate enriquecido con ponderación por reciencia exponencial,…, TemporalCutoff, TestLeagueMathEngine

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (21): _active_trained_until(), _coerce_cutoff_datetime(), _coerce_datetime(), compare_with_active(), _league_already_calibrated(), load_rows_from_db(), main(), _paired_bootstrap_brier() (+13 more)

### Community 48 - "Community 48"
Cohesion: 0.24
Nodes (20): extract_samples(), Convierte el histórico liquidado en muestras para calibración. La probabilidad…, _family(), Sin fecha no se puede garantizar ausencia de fuga temporal., Resolver falso: devuelve el outcome legacy asociado a cada selección., Calibrar sobre `calibrated_prob` compone el error. Debe usarse model_prob., _resolver_map(), _row() (+12 more)

### Community 49 - "Community 49"
Cohesion: 0.14
Nodes (12): CutoffRequired, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Reparte los registros en admitidos, posteriores y sin fecha., Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, record_date() (+4 more)

### Community 50 - "Community 50"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 51 - "Community 51"
Cohesion: 0.14
Nodes (17): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+9 more)

### Community 52 - "Community 52"
Cohesion: 0.14
Nodes (18): _combine_nb_params(), _dc_log_likelihood(), _dc_match_probs(), _dc_score_matrix(), _dc_tau(), _default_dc_rho(), fit_dixon_coles_rho(), _neg_bin_pmf() (+10 more)

### Community 53 - "Community 53"
Cohesion: 0.16
Nodes (6): Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el…, Un partido a las 20:00 en Bogotá es 01:00 UTC del día siguiente. Comparar…, TestTemporalCutoff

### Community 54 - "Community 54"
Cohesion: 0.13
Nodes (10): CalibrationCurve, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_curve_roundtrip_serialization() (+2 more)

### Community 55 - "Community 55"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 56 - "Community 56"
Cohesion: 0.17
Nodes (10): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los…, El informe se registra en logs; no debe arrastrar el histórico entero. (+2 more)

### Community 57 - "Community 57"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 58 - "Community 58"
Cohesion: 0.18
Nodes (16): Manual governance overrides (auto false), data/segment_governance.json, build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary() (+8 more)

### Community 59 - "Community 59"
Cohesion: 0.15
Nodes (13): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling…, Evalúa un conjunto específico de parámetros usando rolling origin sobre… (+5 more)

### Community 60 - "Community 60"
Cohesion: 0.12
Nodes (11): calculate_dixon_coles_matrix(), dixon_coles_tau(), estimate_nb_dispersion(), _poisson_pmf(), Factor de ajuste de Dixon-Coles para corregir empates / goles bajos (0-0, 1-0,…, Genera la matriz de probabilidad de marcadores P(Home=x, Away=y) con ajuste…, Estima el parámetro de dispersión (alpha/k) de la Binomial Negativa por Método…, apply_calibration() (+3 more)

### Community 61 - "Community 61"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 62 - "Community 62"
Cohesion: 0.17
Nodes (12): dataclasses, math, Kelly criterion staking calculation module., Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial). (+4 more)

### Community 63 - "Community 63"
Cohesion: 0.18
Nodes (7): calculate_time_decay_weight(), load_calculated_league_params(), Any, Carga los parámetros matemáticos calculados por liga desde…, Calcula el peso temporal de un partido según la distancia entre su fecha y una…, Calcula los promedios específicos de la liga ponderados por reciencia temporal.…, TestStructuralDecayAndProfiles

### Community 64 - "Community 64"
Cohesion: 0.18
Nodes (12): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad final (final_prob) o calibrada (calibrated_prob)., test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_final_prob_and_calibrated_prob() (+4 more)

### Community 65 - "Community 65"
Cohesion: 0.17
Nodes (16): get_audit_logs(), Session, Retrieve audit logs with optional filtering., admin_mark_recalculation(), admin_root(), export_admin_picks(), export_admin_stats(), get_admin_audit_logs_api() (+8 more)

### Community 66 - "Community 66"
Cohesion: 0.19
Nodes (15): watson/betanoOdds.js odds scraping, Watson Chrome extension (MV3), Phase 1 multilingual team alias map (TEAM_ALIASES), Phase 2 match date in UI, Phase 4 season reconciliation audit (SofaScore vs DB), Phase 5 fix HTTP 400 on POST /api/v1/analysis, Bookmaker odds section (1X2, DC, goals, corners, cards, shots), Auto-loaded data banner (prefill) (+7 more)

### Community 67 - "Community 67"
Cohesion: 0.16
Nodes (11): pydantic_alias_generators, filter_selected_portfolio(), PredictionRecord, Any, Módulo para la separación entre prediction_universe y selected_portfolio.…, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones., Enum (+3 more)

### Community 68 - "Community 68"
Cohesion: 0.21
Nodes (6): IsotonicCalibrator, PlattCalibrator, ndarray, Platt Scaling via logistic regression over log-odds (logit): logit(p) = ln(p /…, Robust wrapper around sklearn.isotonic.IsotonicRegression., test_platt_and_isotonic_calibrators()

### Community 69 - "Community 69"
Cohesion: 0.19
Nodes (9): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, calibration_is_active(), get_calibrator(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.…, True si hay una curva entrenada gobernando las probabilidades., test_save_load_roundtrip() (+1 more)

### Community 70 - "Community 70"
Cohesion: 0.20
Nodes (11): compute_calibration_factor(), compute_drift_factor(), compute_sample_factor(), compute_segment_reliability(), Módulo para el cálculo del score de fiabilidad por segmento…, R_sample = 1 - exp(-n / target_n), R_calibration = exp(- (ece + abs(gap))), R_drift = 1 / (1 + drift_score) (+3 more)

### Community 71 - "Community 71"
Cohesion: 0.18
Nodes (10): Calibración por Familia de Mercado (`apply_calibration`), Categorías de Picks, Display Score (0–100), League Reliability Score (LRS), Métricas por Pick (`ValueIndicator`), 🎯 Sistema de Valor y Picks, Stake Sizing (`_calculate_stake_units`), Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución. (+2 more)

### Community 72 - "Community 72"
Cohesion: 0.35
Nodes (11): requests, compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any, datetime, Determina si un partido tiene cuotas/mercados de apuestas asociados. Retorna… (+3 more)

### Community 73 - "Community 73"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 74 - "Community 74"
Cohesion: 0.20
Nodes (10): Quick decision matrix (phase to tool), Token optimization three-layer protocol, Before you write, Levels, Never-cut list (validation, data loss, security), Ponytail, Shortcut comment convention, Smallest complete change ladder (+2 more)

### Community 75 - "Community 75"
Cohesion: 0.18
Nodes (11): Auto-clarity exception rule, Caveman output-token benchmark, Caveman sibling skills (caveman, ultracave, megacave), When to break caveman rules, caveman, Caveman voice rules (answer first, kill ceremony), Payload verbatim rule (code, paths, errors), Persistence (+3 more)

### Community 76 - "Community 76"
Cohesion: 0.20
Nodes (10): Authorization Boundaries, Command Discovery, Deep Research, Failure Handling, Gemini Notebook Automation, Generation Notes, Output and Citations, Python API Baseline (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.18
Nodes (11): pick_rules_engine.py pick categorization, Rendimiento stats modal (analytics tabs), Category tabs (Global, Professional, Underdog), Market, odds, edge and daily profit charts, Date range filter (Rango de Rentabilidad), Export Excel report action, Summary KPI cards, Main dashboard KPI view (/main-dashboard) (+3 more)

### Community 78 - "Community 78"
Cohesion: 0.22
Nodes (10): export_stats_file(), _filter_analyses_by_params(), _get_flattened_picks(), get_grouped_stats(), Any, Session, Flatten all analyses into individual pick records., Group picks by specified dimension and compute detailed metrics per segment. (+2 more)

### Community 79 - "Community 79"
Cohesion: 0.18
Nodes (11): admin_dashboard_page(), admin_database_page(), admin_picks_page(), admin_stats_page(), get_current_admin_role(), Request, Render Database Explorer view., Dependency to check admin role permissions (read-only vs admin). (+3 more)

### Community 80 - "Community 80"
Cohesion: 0.20
Nodes (10): 1. Answer first, 2. Kill ceremony, 3. Short word, 4. Articles optional, meaning never, 5. One idea per sentence, 6. Payload verbatim, 7. Tool runs: bounded status, 8. User's language (+2 more)

### Community 81 - "Community 81"
Cohesion: 0.27
Nodes (10): compare.py prediction engine, Watson to Sherlock data flow, Dixon-Coles correction (low-scoring only), main.py FastAPI app and routes, Sherlock dev commands (uv, pytest, ruff), SQLite WAL mode, POST /api/v1/compare/batch, Phase 3 one-click batch pipeline (+2 more)

### Community 82 - "Community 82"
Cohesion: 0.27
Nodes (10): league_penalties.json blacklist rules, OOF promotion gate (Brier and LogLoss), Calibration and governance pipeline (Fase 1-16), Segment governance statuses (BLOCKED, REDUCED, WATCH, EXPERIMENTAL), 9-level hierarchical calibration, Invariant and eligibility test suite, evaluate_oof_comparison.py (Systems A/B/C), train_calibration module (walk-forward OOF) (+2 more)

### Community 83 - "Community 83"
Cohesion: 0.22
Nodes (8): 🏗️ Arquitectura General, ⚙️ Configuración de Ligas (Blacklist/Penalties), 📁 Estructura del Proyecto, 📝 Licencia, 🗺️ Roadmap, Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform, 📋 Tabla de Contenidos, 🔑 Variables de Entorno (`.env`)

### Community 85 - "Community 85"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 86 - "Community 86"
Cohesion: 0.28
Nodes (9): make_pick(), published(), REGRESIÓN: `is_candidate_valid` no miraba `correlation_blocked`, así que una…, test_clean_pick_is_not_hard_blocked(), test_correlated_pick_is_labelled_correlation(), test_correlation_is_idempotent_over_many_passes(), test_is_hard_blocked_detects_legacy_flag_only(), test_kill_switch_blocks_every_pick_in_the_engine() (+1 more)

### Community 87 - "Community 87"
Cohesion: 0.29
Nodes (8): Bayesian shrinkage priors (prior_n), Visitante team stats form, Comparator page (dashboard.html, /compare), Stats Generales toggle, Historial modal, Local team stats form, League parameter inputs (goals, corners, cards), Results modal

### Community 88 - "Community 88"
Cohesion: 0.25
Nodes (8): Control y Táctica, Defensivas, Disciplina, 📈 Estadísticas Recolectadas (Fútbol), Físicas, Ofensivas, Portería (Avanzado), Rating

### Community 90 - "Community 90"
Cohesion: 0.29
Nodes (5): caveman, Example output, How to invoke, See also, What it does

### Community 91 - "Community 91"
Cohesion: 0.43
Nodes (7): NotebookLM authentication and auth check, Canonical Source-to-Artifact Workflow, Chat citation offsets (UTF-16 passage resolution), Master token profile auth (master_token.json), notebooklm-py skill (Gemini Notebook), Operating Invariants, NotebookLMClient Python API baseline

### Community 92 - "Community 92"
Cohesion: 0.29
Nodes (7): admin_routes.py admin endpoints, Admin panel page, Base de Datos explorer tab (/admin/database), Admin detail drawer modal, Admin header navigation tabs, Explorador de Picks tab (/admin/picks), Estadisticas Avanzadas tab (/admin/stats)

### Community 93 - "Community 93"
Cohesion: 0.29
Nodes (7): Frontend routes (/compare, /main-dashboard, /leagues, /rules), Competiciones sidebar with search and stakes toggle, Delete competition action, League detail stats (matches, picks, ROI, break-even), Leagues performance page (/leagues), Count in profitability toggle, Season filter

### Community 94 - "Community 94"
Cohesion: 0.29
Nodes (7): Bayesian Shrinkage (Regresión a la Media), Blend de Probabilidades 1X2, Distribución de Poisson, Dixon-Coles (Matriz de Marcadores), Granularidad Condicional (Local / Visitante), ⚽ Motor de Predicción (Fútbol), Overround y Edge

### Community 95 - "Community 95"
Cohesion: 0.29
Nodes (7): Cálculo de Profit por Pick (Stake Plano = 1 unidad), 📊 Dashboard de Rendimiento, Filtros, Gráficos, KPIs Principales, Mercados con Push/Void, Simulador de Capital

### Community 96 - "Community 96"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 98 - "Community 98"
Cohesion: 0.29
Nodes (3): Instante a partir del cual la información no existe todavía. `kickoff` siempre…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, TemporalCutoff

### Community 100 - "Community 100"
Cohesion: 0.48
Nodes (5): buildSherlockPayload(), checkCurrentUrl(), extractMatchInfo(), fetchAndSendOdds(), parseBetanoOdds()

### Community 101 - "Community 101"
Cohesion: 0.62
Nodes (6): loadSettings(), resetSettings(), saveSettings(), setupEventListeners(), showStatus(), testConnection()

### Community 102 - "Community 102"
Cohesion: 0.48
Nodes (5): buildLeagueStats(), buildSherlockPayload(), extractRefereeStats(), findTeamInStandings(), mapSofaScoreToSherlockTeamStats()

### Community 103 - "Community 103"
Cohesion: 0.33
Nodes (5): 1. Entrada y Contexto (NotebookLM), 2. Implementación de Código (Ponytail), 3. Respuestas y Explicaciones (Caveman), Matriz de Decisión Rápida, TOKEN OPTIMIZATION & SKILLS PROTOCOL

### Community 104 - "Community 104"
Cohesion: 0.33
Nodes (5): BaseSettings, pydantic_settings, Application configuration using pydantic-settings., Sherlock platform configuration. Values are loaded from environment variables…, Settings

### Community 105 - "Community 105"
Cohesion: 0.33
Nodes (6): 1. Carga de Datos, 2. Análisis del Partido, 3. Guardado en Historial, 4. Registro de Resultados, 5. Dashboard de Rendimiento, 🔄 Flujo de Trabajo Completo

### Community 106 - "Community 106"
Cohesion: 0.33
Nodes (6): 1. Goles (`_compute_team_goals_lambda`), 2. Corners (`_compute_team_corners_lambda`), 3. Tarjetas (`_compute_team_cards_lambda`), 4. Tiros / Tiros a Puerta (`_compute_team_shots_lambda`, `_compute_team_shots_target_lambda`), 5. Faltas / Offsides (`_compute_team_fouls_lambda`, `_compute_team_offsides_lambda`), Cálculo de Lambdas (λ) por Mercado

### Community 107 - "Community 107"
Cohesion: 0.33
Nodes (6): _compute_league_season_corners(), Calcula el promedio de córners por partido para una liga y temporada, usando…, Verifica que para 'Primera A' y temporada '2026', se calcule el promedio real…, Verifica la función de cálculo con una sesión simulada en memoria para probar…, test_compute_league_season_corners_custom_session(), test_compute_league_season_corners_primera_a_real_db()

### Community 108 - "Community 108"
Cohesion: 0.40
Nodes (5): Análisis, 🌐 API REST, Estadísticas, Integración (Watson / Extensiones), UI (Server-Side Rendered)

### Community 109 - "Community 109"
Cohesion: 0.40
Nodes (5): Configuración Extensión, 🔌 Extensión Watson (Browser), Flujo Betano, Flujo SofaScore, Funciones

### Community 110 - "Community 110"
Cohesion: 0.40
Nodes (3): ExtractionStats, Contabilidad auditable de la extracción. Separa ausencia de picks de JSON…, test_extraction_stats_summary_is_readable()

### Community 111 - "Community 111"
Cohesion: 0.40
Nodes (3): format_active_comparison(), Resultado auditable de un entrenamiento., TrainingReport

### Community 112 - "Community 112"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 113 - "Community 113"
Cohesion: 0.40
Nodes (4): distribution_for_total_line(), outcome_probabilities_for_total(), Convierte una PMF del total (determinista) en probabilidades de outcome para…, Atajo: PMF de totales -> ReturnDistribution lista para EV/Kelly.

### Community 116 - "Community 116"
Cohesion: 0.50
Nodes (4): Extensión Watson, 🚀 Instalación, Pasos, Requisitos

### Community 117 - "Community 117"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 119 - "Community 119"
Cohesion: 0.50
Nodes (4): post, Session, Reentrena el calibrador de probabilidades y publica el artefacto. Esta ruta…, train_calibrator_endpoint()

### Community 120 - "Community 120"
Cohesion: 0.50
Nodes (4): Any, put, Saves the full list of pick rules and structural correlation rules (overwrite)., save_pick_rules()

### Community 122 - "Community 122"
Cohesion: 0.67
Nodes (3): listens_for, Apply performance PRAGMAs on every new SQLite connection., _set_sqlite_pragma()

### Community 123 - "Community 123"
Cohesion: 0.67
Nodes (3): middleware, disable_cache_in_dev(), Request

### Community 124 - "Community 124"
Cohesion: 0.67
Nodes (3): consume_result(), get, Dashboard/comparator polls this to detect pending match results. Returns the…

### Community 125 - "Community 125"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

## Knowledge Gaps
- **152 isolated node(s):** `🏗️ Arquitectura General`, `⚙️ Configuración de Ligas (Blacklist/Penalties)`, `📁 Estructura del Proyecto`, `📝 Licencia`, `🗺️ Roadmap` (+147 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1005 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `Community 0` to `Community 1`, `Community 33`, `Community 3`, `Community 5`, `Community 7`, `Community 40`, `Community 72`, `Community 107`, `Community 12`, `Community 13`, `Community 14`, `Community 47`, `Community 78`, `Community 17`, `Community 16`, `Community 29`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `Operating Invariants` connect `Community 91` to `Community 76`, `Community 53`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 55 inferred relationships involving `AnalysisHistory` (e.g. with `Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)` and `migrate_picks_snapshots()`) actually correct?**
  _`AnalysisHistory` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `HierarchicalCalibrator` (e.g. with `compare_with_active()` and `train_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 22 INFERRED edges - model-reasoned connections that need verification._