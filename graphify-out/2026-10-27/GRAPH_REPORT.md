# Graph Report - Sherlock  (2026-10-20)

## Corpus Check
- 123 files · ~494,070 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 2, .db 2, .example 1)

## Summary
- 2304 nodes · 5419 edges · 127 communities (96 shown, 31 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 360 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3813a4b8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- HierarchicalCalibrator
- Web UI Comparator JS
- background.js
- BlockReason
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
- test_temporal.py
- compare_football
- domain.py
- test_calibration.py
- test_train_calibration.py
- main.py
- EligibilityDecision
- save_analysis
- stake_engine.py
- StatSource
- evaluate_oof_comparison.py
- json
- load_rows_from_db
- admin_stats_service.py
- test_settlement.py
- _explicit_market_support
- manifest.json
- test_invariants_and_eligibility.py
- LeagueMathEngine
- _call_llm_for_result
- TestLeagueMathEngine
- test_calibration_wiring.py
- dashboard_main.js
- .create
- .compute_pick_hit_rate
- hard_blocks_from_flags
- schemas.py
- TestSegmentReports
- parse_utc
- joint_match_distribution.py
- AnalysisHistory
- record_date
- .fit
- calibration.py
- train_model_retrospective.py
- CalibrationCurve
- test_prefill_corners.py
- parallel_recalc.py
- CalibrationSample
- PickSnapshot
- walk_forward_calibrate
- count_models.py
- calculate_league_params.py
- _check_pick_success
- admin_picks_service.py
- admin.js
- admin_routes.py
- CardsConvention
- test_stake_and_traceability.py
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- .compute_league_averages
- SegmentStatus
- distribution_for_total_line
- pick_rules_engine.py
- content.js
- update_governance.py
- AdminAuditLog
- 2. Paso a Paso del Nuevo Pipeline
- backup_db.py
- TestStakeEngine
- sherlock
- typing
- prueba90100.py
- datetime
- h2h_shrinkage.py
- _value_indicator
- _normalize_betano_odds
- eligibility.py
- Session
- compute_edge
- _populate_history_extra_fields
- test_calibration_hierarchical.py
- RiskPolicyConfig
- kelly_fractional
- TestCalibrationTemporalTraceability
- PredictionRecord
- market_probability.py
- planning.md
- blend_model_and_market_probability
- apply_calibration
- test_threshold_families_match_the_legacy_sets
- pytest
- _get_governance_multiplier

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 79 edges
2. `AnalysisHistory` - 75 edges
3. `compare_football()` - 70 edges
4. `HierarchicalCalibrator` - 42 edges
5. `Outcome` - 40 edges
6. `LeagueMathEngine` - 37 edges
7. `good_snapshot()` - 36 edges
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

## Communities (127 total, 31 thin omitted)

### Community 0 - "HierarchicalCalibrator"
Cohesion: 0.17
Nodes (12): HierarchicalCalibrator, Path, Calibrador jerárquico de 9 niveles con resolución estricta y partial pooling.…, _build_history_cache_key(), get_calibrator(), get_calibrator_for_timestamp(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.…, Clave de caché basada en los paths y mtimes de los artefactos. (+4 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "background.js"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "BlockReason"
Cohesion: 0.09
Nodes (59): BlockReason, evaluate_eligibility(), evaluate_soft_filters(), is_hard(), PublicationThresholds, str, Umbrales de publicación, versionados y en un solo sitio., Aplica los umbrales recalculables. No conoce los bloqueos duros. (+51 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (41): functools, convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), Modelo de conteos (corners, tarjetas, tiros, faltas) con Binomial Negativa…, PMF de la suma de dos conteos independientes. Convolución discreta exacta:… (+33 more)

### Community 5 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1, usando final_prob (#42)., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 6 - "compare.py"
Cohesion: 0.05
Nodes (51): dotenv, numpy, openai, pydantic_alias_generators, _are_contradictory(), _calibration_line_bucket(), _call_openrouter(), _canonical_pick_signature() (+43 more)

### Community 7 - "Outcome"
Cohesion: 0.11
Nodes (26): _combine_legs(), Outcome, outcome_hit_value(), outcome_return(), Enum, str, Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de…, Combina los resultados de las piernas (cada una con media unidad). Solo se usan… (+18 more)

### Community 8 - "test_risk.py"
Cohesion: 0.07
Nodes (41): resolve_match_picks_correlation(), get_attr(), is_candidate_valid(), pick_merit_score(), load_risk_limits(), _parse_bool_env(), PublicationMode, clean_env() (+33 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (26): apply_portfolio_exposure_cap(), Aplica Simultaneous Kelly Scaling sobre una lista de ValueIndicator…, Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva. (+18 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (30): block_pick(), current_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta…, make_pick(), Tests del cableado de elegibilidad en `compare.py`. Reproducen la secuencia… (+22 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "test_admin_panel.py"
Cohesion: 0.13
Nodes (25): ColumnSchemaInfo, DatabaseRowsOut, DatabaseRowUpdate, DatabaseTableSchema, PaginationMeta, get_table_schema(), list_whitelisted_tables(), Any (+17 more)

### Community 13 - "leagues.js"
Cohesion: 0.12
Nodes (36): addMarketToBlacklist(), applyBulkGovernance(), buildLeagueMarketMap(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry() (+28 more)

### Community 14 - "test_temporal.py"
Cohesion: 0.11
Nodes (13): filter_before_cutoff(), FilterReport, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Invariantes del cutoff temporal. La propiedad que se defiende aquí es una sola…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior… (+5 more)

### Community 15 - "compare_football"
Cohesion: 0.17
Nodes (29): compare_football(), _vi(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda() (+21 more)

### Community 16 - "domain.py"
Cohesion: 0.07
Nodes (38): ABC, DeclarativeBase, enum, pandas, Base, Declarative base for all ORM models., BettingLine, Competition (+30 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.13
Nodes (25): random, brier_score(), expected_calibration_error(), log_loss(), pava(), Construye muestras desde filas liquidadas con soporte para taxonomía y recencia., Regresión isotónica ponderada por Pool Adjacent Violators., reliability_table() (+17 more)

### Community 18 - "test_train_calibration.py"
Cohesion: 0.06
Nodes (63): extract_samples(), ExtractionStats, history_dir_for(), _league_already_calibrated(), main(), _pick_probability(), Path, Un partido sirve si tiene al menos el marcador final. (+55 more)

### Community 19 - "main.py"
Cohesion: 0.06
Nodes (48): contextlib, copy, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io, middleware (+40 more)

### Community 20 - "EligibilityDecision"
Cohesion: 0.08
Nodes (16): describe(), EligibilityDecision, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno., Une dos decisiones sobre el mismo pick. Los bloqueos duros se unen (nunca se…, Devuelve el `quality_score` que corresponde publicar. Un pick con bloqueo duro…, Reconstruye una decisión desde una lista plana de motivos, separando duros de… (+8 more)

### Community 21 - "save_analysis"
Cohesion: 0.09
Nodes (26): Exception, str, Sport, Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), _check_payload_has_odds(), _has_valid(), _extract_bookmaker() (+18 more)

### Community 22 - "stake_engine.py"
Cohesion: 0.19
Nodes (16): compute_final_stake(), Módulo de política de riesgo, Kelly ponderado e inmutable y límites de…, Resultado estructurado del cálculo de stake. Usado por compute_final_stake., Calcula el stake final delegando en compute_risk_decision de stake_engine.…, StakeCalculationResult, compute_distribution_kelly(), compute_risk_decision(), optimize_simultaneous_portfolio() (+8 more)

### Community 23 - "StatSource"
Cohesion: 0.12
Nodes (13): load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio…, Carga el archivo pick_rules.json y devuelve tuple (rules_list,… (+5 more)

### Community 24 - "evaluate_oof_comparison.py"
Cohesion: 0.17
Nodes (15): build_comparison_report(), ComparisonReport, compute_metrics(), load_historical_picks(), load_historical_picks_from_db(), main(), Script de evaluación OOF comparativa (Fase 16). Genera un reporte antes/después…, Carga picks históricos directamente desde la base de datos SQLite. Lee… (+7 more)

### Community 25 - "json"
Cohesion: 0.09
Nodes (23): argparse, Connection, dividir_archivo(), main(), Divide un archivo .py en partes de N lineas y genera archivos .txt. Uso: python…, json, pathlib, main() (+15 more)

### Community 26 - "load_rows_from_db"
Cohesion: 0.38
Nodes (7): _coerce_cutoff_datetime(), _coerce_datetime(), load_rows_from_db(), Any, datetime, Como `_coerce_datetime` pero si el valor es solo una fecha (YYYY-MM-DD) la…, Lee `analysis_history` y devuelve dicts planos. Solo trae filas con marcador…

### Community 27 - "admin_stats_service.py"
Cohesion: 0.12
Nodes (30): AccumulatedYieldPoint, AuditLogCreate, AuditLogOut, CalibrationBand, ChartDataPoint, DashboardChartsData, DashboardKPIs, DashboardSummaryOut (+22 more)

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
Cohesion: 0.16
Nodes (11): compute_clv(), implied_probability(), Calcula las métricas de Closing Line Value (CLV)., Calcula la probabilidad implícita de una cuota decimal (1 / odds)., Elimina el margen (vigorish) de un mercado de 2 opciones por método…, remove_vig_two_way(), Tests de invariantes de mercado: calibración y eligibilidad. Verifica que: -…, No se puede calcular CLV sin cuota de cierre. (+3 more)

### Community 32 - "LeagueMathEngine"
Cohesion: 0.10
Nodes (17): calculate_weighted_average(), LeagueMathEngine, Any, Calcula el promedio con decay exponencial según antigüedad. half_life: número…, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula el promedio de córners de la última jornada completada antes de…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva/defensiva relativa…, Capa 2: Retorna (lambda_home, mu_away) para compatibilidad hacia atrás. (+9 more)

### Community 33 - "_call_llm_for_result"
Cohesion: 0.40
Nodes (5): _call_llm_for_result(), Llama al LLM usando las funciones internas de compare.py sin importarlas., Generador SSE genérico: calcula resultado + llama LLM + hace streaming., _sse_stream(), event_generator()

### Community 34 - "TestLeagueMathEngine"
Cohesion: 0.15
Nodes (3): Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, Calcula el hit rate enriquecido con ponderación por reciencia exponencial,…, TestLeagueMathEngine

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - ".create"
Cohesion: 0.11
Nodes (11): CutoffRequired, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, TemporalCutoff, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el… (+3 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "hard_blocks_from_flags"
Cohesion: 0.40
Nodes (5): hard_blocks_from_flags(), Traduce los flags booleanos legacy a motivos de bloqueo. Permite adoptar…, test_all_flags_combine(), test_flags_translate_to_reasons(), test_no_flags_means_no_blocks()

### Community 40 - "schemas.py"
Cohesion: 0.18
Nodes (19): field_validator, pydantic, AnalysisHistoryOut, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut (+11 more)

### Community 41 - "TestSegmentReports"
Cohesion: 0.24
Nodes (3): _make_trace(), TestPickTrace, TestSegmentReports

### Community 42 - "parse_utc"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "joint_match_distribution.py"
Cohesion: 0.12
Nodes (15): derive_joint_match_probabilities(), guardrail_away_win_recommendation(), MatchProbabilities, Modelo de Distribución Conjunta de Marcador Dixon-Coles con Validación de…, Guardrail para evitar que señales de doble oportunidad X2 se transformen…, Valida matemáticamente todos los invariantes requeridos., Deriva explícitamente todas las probabilidades de mercado desde la matriz…, test_guardrail_away_win() (+7 more)

### Community 44 - "AnalysisHistory"
Cohesion: 0.09
Nodes (25): delete, put, AnalysisHistory, History of manual analyses performed in the comparator., deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches() (+17 more)

### Community 45 - "record_date"
Cohesion: 0.17
Nodes (8): Any, datetime, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Reparte los registros en admitidos, posteriores y sin fecha., record_date(), En `analysis_history`, `date` es la fecha de CREACIÓN del registro, no la del…, TestRecordDate

### Community 46 - ".fit"
Cohesion: 0.20
Nodes (18): _clean_val(), family_key(), family_side_key(), league_family_key(), league_family_side_key(), league_key(), make_samples(), Menos de min_samples -> identidad, nunca una corrección inventada. (+10 more)

### Community 47 - "calibration.py"
Cohesion: 0.07
Nodes (34): Entrenamiento del calibrador de Sherlock a partir de picks liquidados. Flujo…, # NOTE: _extract_line_bucket, _resolve_market_side y market_family_fn, extract_market_line(), line_bucket_for(), load_line_buckets(), market_group_key(), MarketFamily, MarketKey (+26 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationCurve"
Cohesion: 0.15
Nodes (9): CalibrationCurve, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale(), test_curve_rejects_non_monotone_knots(), test_curve_roundtrip_serialization() (+1 more)

### Community 50 - "test_prefill_corners.py"
Cohesion: 0.15
Nodes (16): _compute_league_season_corners(), push_prefill(), Calcula el promedio de córners por partido para una liga y temporada (si está…, Browser extension pushes a (partial) form payload here. The Sherlock dashboard…, client(), fixture, Tests para verificar el cálculo de corners por partido de la liga/temporada en…, Verifica que para 'Primera A' y temporada '2026', se calcule el promedio real… (+8 more)

### Community 51 - "parallel_recalc.py"
Cohesion: 0.08
Nodes (37): asyncio, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line() (+29 more)

### Community 52 - "CalibrationSample"
Cohesion: 0.13
Nodes (16): CalibrationSample, fit_curve(), _quantile_edges(), Una observación histórica para ajustar la calibración., El audit: 'la curva de calibración muestra sobreconfianza fuerte en…, Si el modelo ya está calibrado, la curva debe quedarse cerca de la identidad., Clave del diseño: con poca muestra el ruido NO puede dominar. 8 observaciones…, test_corrects_systematic_overconfidence() (+8 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.18
Nodes (12): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad final (final_prob) o calibrada (calibrated_prob)., test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_final_prob_and_calibrated_prob() (+4 more)

### Community 54 - "walk_forward_calibrate"
Cohesion: 0.20
Nodes (9): evaluate(), SegmentEvaluation, walk_forward_calibrate(), WalkForwardResult, test_improved_is_false_when_calibration_hurts(), test_walk_forward_empty_input(), test_walk_forward_produces_oof_predictions(), test_walk_forward_skips_folds_without_enough_training_data() (+1 more)

### Community 55 - "count_models.py"
Cohesion: 0.31
Nodes (8): DirectCountPrediction, predict_cards_total(), predict_direct_total(), predict_shots_on_target_total(), Modelos directos de conteo para totales de goles, córners, tarjetas y tiros a…, Calcula la media total esperada del mercado con shrinkage hacia la media de…, Modelo específico de tarjetas integrando árbitro y disciplina., Modelo específico para remates a puerta (shots_target) enfocado en la banda…

### Community 56 - "calculate_league_params.py"
Cohesion: 0.15
Nodes (21): calculate_parameters(), calculate_parameters_per_match(), extract_match_competition(), fetch_historical_matches_by_league(), main(), normalize_league_name(), print_summary(), Any (+13 more)

### Community 57 - "_check_pick_success"
Cohesion: 0.07
Nodes (39): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), _enrich_with_results(), export_excel_report(), _extract_line(), get_all_picks() (+31 more)

### Community 58 - "admin_picks_service.py"
Cohesion: 0.11
Nodes (27): PickDetailOut, PickItemOut, _dedup_correlated_picks(), export_picks_file(), _extract_picks_from_analysis(), get_pick_detail(), mark_for_recalculation(), Session (+19 more)

### Community 59 - "admin.js"
Cohesion: 0.12
Nodes (26): adminState, bindFiltersBarEvents(), buildFilterQueryString(), chartInstances, closeAdminModal(), escapeHtml(), formatCellVal(), formatDate() (+18 more)

### Community 60 - "admin_routes.py"
Cohesion: 0.11
Nodes (33): export_stats_file(), Export filtered stats table to CSV or Excel bytes., admin_dashboard_page(), admin_database_page(), admin_mark_recalculation(), admin_picks_page(), admin_root(), admin_stats_page() (+25 more)

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "test_stake_and_traceability.py"
Cohesion: 0.18
Nodes (15): _compute_ece(), compute_segment_report(), generate_segment_reports(), PickTrace, Módulo de trazabilidad y reportes por segmento. Implementa la Fase 13 del…, Reporte completo de un segmento league+family+side+bucket. Incluye: picks, hit…, Snapshot inmutable de trazabilidad de un pick para audit y reportes. Contiene…, Calcula el reporte completo de un segmento a partir de sus traces y resultados.… (+7 more)

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

### Community 67 - ".compute_league_averages"
Cohesion: 0.08
Nodes (19): calculate_roi_and_yield(), compute_brier_score(), compute_calibration_curve(), compute_log_loss(), Any, Evaluador de hiperparámetros de reciencia y priors sobre un conjunto de…, Ejecuta la búsqueda en grilla mediante validación temporal expansiva (rolling…, Evalúa un conjunto específico de parámetros usando rolling origin sobre… (+11 more)

### Community 68 - "SegmentStatus"
Cohesion: 0.17
Nodes (13): evaluate_segment_status(), get_governance_multipliers(), Retorna los multiplicadores de stake y ajustes de edge según el estado de…, Evalúa el estado de gobernanza de un segmento según evidencia y configuración…, SegmentStatus, Un segmento BLOCKED debe emitir un hard block irrecuperable., TestGovernanceMultipliers, Regression: El segmento debe resolver su curva específica y ser bloqueable. (+5 more)

### Community 69 - "distribution_for_total_line"
Cohesion: 0.40
Nodes (4): distribution_for_total_line(), outcome_probabilities_for_total(), Convierte una PMF del total (determinista) en probabilidades de outcome para…, Atajo: PMF de totales -> ReturnDistribution lista para EV/Kelly.

### Community 70 - "pick_rules_engine.py"
Cohesion: 0.12
Nodes (17): re, classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line() (+9 more)

### Community 72 - "update_governance.py"
Cohesion: 0.21
Nodes (14): build_output(), _classify(), compute_governance_from_calibration(), main(), merge_with_existing(), _print_summary(), Path, update_governance.py ==================== Genera automaticamente… (+6 more)

### Community 73 - "AdminAuditLog"
Cohesion: 0.16
Nodes (15): patch, AdminAuditLog, Audit log for administrative actions in Sherlock Admin Panel., OperationalFieldsUpdate, get_audit_logs(), log_admin_action(), Any, Session (+7 more)

### Community 74 - "2. Paso a Paso del Nuevo Pipeline"
Cohesion: 0.17
Nodes (11): 1. ¿Qué cambió respecto al flujo antiguo?, 2. Paso a Paso del Nuevo Pipeline, 3. Resumen de Comandos de Operacion Periodica (Checklist Mensual), 4. Overrides Manuales de Governance, Flujo Antiguo:, Guía Operativa del Nuevo Flujo de Calibración, Gobernanza y Validación (Fase 1-16), Nuevo Flujo (Fase 1-16):, Paso 1: Entrenamiento de Calibración Jerárquica con Corte Temporal (+3 more)

### Community 75 - "backup_db.py"
Cohesion: 0.24
Nodes (9): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), os (+1 more)

### Community 76 - "TestStakeEngine"
Cohesion: 0.33
Nodes (3): compute_stake_final(), Calcula el stake final aplicando ajuste de factores, drawdown scale y límites., TestStakeEngine

### Community 105 - "typing"
Cohesion: 0.08
Nodes (29): dataclasses, logging, math, Módulo de Backtesting Temporal y Selección de Parámetros por Liga y Mercado.…, calculate_dixon_coles_matrix(), dixon_coles_tau(), estimate_nb_dispersion(), _poisson_pmf() (+21 more)

### Community 106 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 107 - "datetime"
Cohesion: 0.11
Nodes (19): datetime, FastAPI, listens_for, sqlalchemy, sqlalchemy_orm, _column_exists(), create_indexes(), init_db() (+11 more)

### Community 108 - "h2h_shrinkage.py"
Cohesion: 0.38
Nodes (6): evaluate_h2h_signal(), H2HShrinkageResult, Módulo para el suavizado Beta-Binomial de tasas H2H y eliminación de bloqueos…, Calcula el hit rate H2H suavizado por el prior Bayesiano (Beta-Binomial)., Evalúa la señal H2H sin emitir bloqueos duros para n < 8. Si n >= 8 y el hit…, shrunk_h2h_rate()

### Community 109 - "_value_indicator"
Cohesion: 0.08
Nodes (38): Any, Simula una versión de calibración alternativa sobre la probabilidad cruda…, run_counterfactual_analysis(), _calculate_display_score(), _calculate_kelly_fraction(), _calculate_stake_units(), calibration_is_active(), _calibration_side() (+30 more)

### Community 110 - "_normalize_betano_odds"
Cohesion: 0.33
Nodes (4): _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…

### Community 111 - "eligibility.py"
Cohesion: 0.19
Nodes (16): _risk_imports(), _as_float(), _coerce_reason(), is_hard_blocked(), _pget(), _pset(), Any, Enum (+8 more)

### Community 112 - "Session"
Cohesion: 0.08
Nodes (38): Fuerza la recarga del artefacto de gobernanza en la siguiente llamada (tests)., reset_governance_cache(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, _get_or_create_team(), match_closing_odds_to_pick() (+30 more)

### Community 113 - "compute_edge"
Cohesion: 0.31
Nodes (3): compute_edge(), EdgeResult, TestEdgeComputation

### Community 114 - "_populate_history_extra_fields"
Cohesion: 0.12
Nodes (15): _check_projected_line_success(), get_analysis_by_id(), get_league_matches(), list_analysis(), _populate_history_extra_fields(), Return the sum of stake_units for publishable picks of a match., List saved analyses with optional filters and pagination., Obtiene toda la información necesaria para un partido en específico por su ID. (+7 more)

### Community 115 - "test_calibration_hierarchical.py"
Cohesion: 0.19
Nodes (10): compute_sample_weight(), family_side_bucket_key(), league_family_side_bucket_key(), datetime, Calcula el peso por recencia temporal con la fórmula: w = 0.5 ** (edad /…, test_calibration_keys(), test_hierarchical_resolution(), test_recency_weighting() (+2 more)

### Community 117 - "kelly_fractional"
Cohesion: 0.39
Nodes (3): kelly_fractional(), Función directa de Kelly Bernoulli fraccionado., TestKellyFractional

### Community 118 - "TestCalibrationTemporalTraceability"
Cohesion: 0.10
Nodes (5): get_calibration_version_for_timestamp(), Retorna la versión de la calibración para un timestamp dado o 'unverified'., Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache(), TestCalibrationTemporalTraceability

### Community 119 - "PredictionRecord"
Cohesion: 0.33
Nodes (5): filter_selected_portfolio(), PredictionRecord, Any, Filtra y escala la cartera seleccionada resolviendo la exposición simultánea.…, Registro completo de una predicción evaluada en el universo de predicciones.

### Community 120 - "market_probability.py"
Cohesion: 0.23
Nodes (9): BlendResult, CLVResult, Módulo para el cálculo de probabilidades de mercado sin margen (no-vig),…, Elimina el margen (vigorish) usando el método de potencia (Shin / Power…, Elimina el margen (vigorish) de un mercado 1X2 por método proporcional., remove_vig_power(), remove_vig_three_way(), test_remove_vig_power() (+1 more)

### Community 121 - "planning.md"
Cohesion: 0.33
Nodes (5): 1. Datos e ingesta (Watson), 2. Modelo, 3. Calibración y taxonomía, 4. Valor, filtros, riesgo y correlación, 5. Liquidación, recálculo y operación

### Community 122 - "blend_model_and_market_probability"
Cohesion: 0.29
Nodes (4): blend_model_and_market_probability(), Mezcla controlada: p_final = r * p_calibrated + (1 - r) * p_market donde r =…, Sin p_market, el stake_multiplier se reduce vs tenerlo., test_blend_and_divergence()

### Community 123 - "apply_calibration"
Cohesion: 0.33
Nodes (6): apply_calibration(), _coerce_datetime(), datetime, Aplica la curva jerárquica de calibración al pick según la versión activa en…, Normaliza un datetime a naive-UTC para permitir comparaciones seguras entre…, _to_naive_utc()

### Community 125 - "pytest"
Cohesion: 0.40
Nodes (4): fastapi_testclient, pytest, Verifica que al guardar un análisis sin count_in_profitability explícito: - Si…, test_save_analysis_respects_profitable_leagues()

### Community 126 - "_get_governance_multiplier"
Cohesion: 0.50
Nodes (4): _get_governance_multiplier(), get_segment_governance(), Devuelve el artefacto de gobernanza completo, recargandolo si cambio en disco.…, Resuelve el status de gobernanza y el multiplicador de stake para un segmento.…

## Knowledge Gaps
- **43 isolated node(s):** `sherlock`, `adminState`, `chartInstances`, `sherlockBtn`, `BOOKMAKER_LABELS` (+38 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 808 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **31 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `compare.py`, `test_admin_panel.py`, `compare_football`, `domain.py`, `main.py`, `save_analysis`, `load_rows_from_db`, `admin_stats_service.py`, `calibration.py`, `train_model_retrospective.py`, `test_prefill_corners.py`, `_check_pick_success`, `admin_picks_service.py`, `AdminAuditLog`, `prueba90100.py`, `datetime`, `_value_indicator`, `Session`, `_populate_history_extra_fields`, `planning.md`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `SegmentStatus`, `pick_rules_engine.py`, `hard_blocks_from_flags`, `test_risk.py`, `compare.py`, `test_eligibility_wiring.py`, `_value_indicator`, `eligibility.py`, `compare_football`, `parallel_recalc.py`, `EligibilityDecision`, `PickSnapshot`, `test_invariants_and_eligibility.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `TestLeagueMathEngine`, `.compute_league_averages`, `.create`, `.compute_pick_hit_rate`, `compare.py`, `typing`, `test_temporal.py`, `compare_football`, `main.py`, `save_analysis`, `calculate_league_params.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `BlockReason` (e.g. with `evaluate_pick_rules()` and `resolve_match_picks_correlation()`) actually correct?**
  _`BlockReason` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `AnalysisHistory` (e.g. with `2. Modelo` and `migrate_picks_snapshots()`) actually correct?**
  _`AnalysisHistory` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `compare_football()` (e.g. with `AnalysisHistory` and `Sport`) actually correct?**
  _`compare_football()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `HierarchicalCalibrator` (e.g. with `train_calibrator()` and `get_calibrator()`) actually correct?**
  _`HierarchicalCalibrator` has 19 INFERRED edges - model-reasoned connections that need verification._