# Graph Report - Sherlock  (2026-09-23)

## Corpus Check
- 77 files · ~218,996 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 1661 nodes · 3741 edges · 100 communities (68 shown, 32 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 288 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6789275e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_train_calibration.py
- Web UI Comparator JS
- Watson Extension Background Service
- BlockReason
- test_count_negative_binomial.py
- _check_pick_success
- compare.py
- test_settlement.py
- test_risk.py
- ReturnDistribution
- test_eligibility_wiring.py
- Watson Extension Popup UI
- recalculate_all_accuracy
- Web UI Leagues JS
- main.py
- compare_football
- manual_loader.py
- test_calibration.py
- save_analysis
- Session
- EligibilityDecision
- Side
- domain.py
- _value_indicator
- AnalysisHistory
- TestLeagueMathEngine
- get
- StatSource
- .create
- _explicit_market_support
- manifest.json
- LeagueMathEngine
- resolve_match_picks_correlation
- test_compare_integration.py
- CalibrationCurve
- test_calibration_wiring.py
- dashboard_main.js
- TestFiltering
- .compute_pick_hit_rate
- eligibility.py
- schemas.py
- ManualLoaderAdapter
- parse_utc
- HierarchicalCalibrator
- pick_rules_engine.py
- record_date
- calibration.py
- json
- train_model_retrospective.py
- CalibrationSample
- RiskLimits
- parallel_recalc.py
- evaluate
- PickSnapshot
- _populate_history_extra_fields
- settlement.py
- calculate_league_params.py
- prueba90100.py
- _normalize_betano_odds
- record_hard_block
- risk.py
- CardsConvention
- test_shipped_pick_rules_json_respects_the_agreed_limits
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- test_shipped_rules_remain_disabled
- is_hard
- content.js
- clean_env
- test_threshold_families_match_the_legacy_sets
- sherlock

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 71 edges
2. `compare_football()` - 57 edges
3. `AnalysisHistory` - 47 edges
4. `Outcome` - 40 edges
5. `good_snapshot()` - 32 edges
6. `resolve_match_picks_correlation()` - 31 edges
7. `HierarchicalCalibrator` - 31 edges
8. `LeagueMathEngine` - 29 edges
9. `extract_samples()` - 29 edges
10. `load_risk_limits()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `calculate_parameters_per_match()` --uses--> `LeagueMathEngine`  [INFERRED]
  calculate_league_params.py → src/core/math_engine.py
- `test_promedio_corners_ultima_jornada()` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/test_corner_last_round.py → src/core/math_engine.py
- `TestLeagueMathEngine` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/test_math_engine.py → src/core/math_engine.py
- `TestEngineHitRates` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/unit/test_temporal.py → src/core/math_engine.py
- `test_decision_is_immutable()` --uses--> `BlockReason`  [INFERRED]
  tests/unit/test_eligibility.py → src/domain/eligibility.py

## Import Cycles
- None detected.

## Communities (100 total, 32 thin omitted)

### Community 0 - "test_train_calibration.py"
Cohesion: 0.06
Nodes (71): random, _coerce_datetime(), _extract_line_bucket(), extract_samples(), ExtractionStats, history_dir_for(), load_rows_from_db(), main() (+63 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "Watson Extension Background Service"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "BlockReason"
Cohesion: 0.12
Nodes (47): BlockReason, evaluate_eligibility(), evaluate_soft_filters(), str, Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, Motivos por los que un pick no se publica., good_snapshot() (+39 more)

### Community 4 - "test_count_negative_binomial.py"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "_check_pick_success"
Cohesion: 0.08
Nodes (35): build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), get_all_picks(), _get_cache() (+27 more)

### Community 6 - "compare.py"
Cohesion: 0.06
Nodes (49): dotenv, numpy, openai, pydantic_alias_generators, _are_contradictory(), _call_openrouter(), _canonical_pick_signature(), _combine_nb_params() (+41 more)

### Community 7 - "test_settlement.py"
Cohesion: 0.12
Nodes (29): _combine_legs(), line_legs(), Outcome, outcome_hit_value(), outcome_return(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Combina los resultados de las piernas (cada una con media unidad). Solo se usan…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del… (+21 more)

### Community 8 - "test_risk.py"
Cohesion: 0.10
Nodes (31): load_risk_limits(), Any, Resuelve la política de riesgo efectiva. Precedencia: entorno >…, parametrize, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Un valor ininteligible no debe abrir la publicación real. `flase` es un typo…, Un tope de 0 bloquearía todo silenciosamente: se trata como no puesto., Editar pick_rules.json no debe poder ampliar la exposición. Era justo el… (+23 more)

### Community 9 - "ReturnDistribution"
Cohesion: 0.07
Nodes (24): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+16 more)

### Community 10 - "test_eligibility_wiring.py"
Cohesion: 0.14
Nodes (32): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+24 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "recalculate_all_accuracy"
Cohesion: 0.20
Nodes (10): Reparte la lista de ítems en n_workers sublistas de tamaño similar., split_into_chunks(), _annotate_best_bookmaker(), _apply_line_shopping(), _merge_best_odds(), Re-analiza todos los registros del historial: 1. Vuelve a calcular los picks…, Recorre las cuotas crudas de todas las casas (formato de prefill_odds_store /…, Anota en cada ValueIndicator.bookmaker qué casa ofreció la mejor cuota para ese… (+2 more)

### Community 13 - "Web UI Leagues JS"
Cohesion: 0.13
Nodes (32): addMarketToBlacklist(), applyBulkBlacklist(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry(), escapeAttr() (+24 more)

### Community 14 - "main.py"
Cohesion: 0.07
Nodes (33): contextlib, copy, FastAPI, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating, io (+25 more)

### Community 15 - "compare_football"
Cohesion: 0.16
Nodes (30): compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda() (+22 more)

### Community 16 - "manual_loader.py"
Cohesion: 0.10
Nodes (21): ABC, logging, pandas, Competition, Match, A single fixture / game between two teams or players., Aggregated team stats for a single match., Individual player stats for a single match. (+13 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.14
Nodes (22): pava(), Construye muestras desde filas liquidadas, excluyendo push y unsettled. Espera…, Regresión isotónica ponderada por Pool Adjacent Violators. Devuelve la…, Tabla de reliability: confianza declarada vs acierto observado por bin., Walk-forward estricto por grupos temporales. Un mismo timestamp se trata como…, reliability_table(), samples_from_settlements(), walk_forward_calibrate() (+14 more)

### Community 18 - "save_analysis"
Cohesion: 0.09
Nodes (25): Exception, Sport, _check_payload_has_odds(), _has_valid(), _extract_bookmaker(), _extract_competition(), list_competitions(), list_matches() (+17 more)

### Community 19 - "Session"
Cohesion: 0.10
Nodes (30): post, Session, apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest, compare_teams_football() (+22 more)

### Community 20 - "EligibilityDecision"
Cohesion: 0.10
Nodes (14): _coerce_reason(), EligibilityDecision, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno., Une dos decisiones sobre el mismo pick. Los bloqueos duros se unen (nunca se…, Devuelve el `quality_score` que corresponde publicar. Un pick con bloqueo duro…, Reconstruye una decisión desde una lista plana de motivos, separando duros de… (+6 more)

### Community 21 - "Side"
Cohesion: 0.23
Nodes (17): str, Liquida una pierna simple (x.0 o x.5) de un mercado de totales., Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, _settle_simple_total(), settle_total(), Side, parametrize, Una línea que no es múltiplo de 0.25 no se liquida a ciegas. (+9 more)

### Community 22 - "domain.py"
Cohesion: 0.10
Nodes (21): DeclarativeBase, enum, listens_for, sqlalchemy, sqlalchemy_orm, Base, _column_exists(), create_indexes() (+13 more)

### Community 23 - "_value_indicator"
Cohesion: 0.09
Nodes (32): apply_calibration(), _calculate_display_score(), _calculate_kelly_fraction(), _calculate_stake_units(), calibration_is_active(), _calibration_line_bucket(), _calibration_side(), _vi() (+24 more)

### Community 24 - "AnalysisHistory"
Cohesion: 0.11
Nodes (21): delete, put, AnalysisHistory, History of manual analyses performed in the comparator., deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches() (+13 more)

### Community 25 - "TestLeagueMathEngine"
Cohesion: 0.10
Nodes (8): Any, Calcula los promedios específicos de la liga basándose en los partidos…, Capa 3: Calcula estadísticas promedio del equipo `team_name` en ventanas…, Evalúa si un partido específico cumple con el criterio de un pick. Soporta:…, Calcula el hit rate global a nivel de liga para un mercado específico para…, Calcula el hit rate enriquecido con ponderación por reciencia exponencial,…, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, TestLeagueMathEngine

### Community 26 - "get"
Cohesion: 0.12
Nodes (22): get, middleware, Request, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version() (+14 more)

### Community 27 - "StatSource"
Cohesion: 0.12
Nodes (13): load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio…, Carga el archivo pick_rules.json y devuelve tuple (rules_list,… (+5 more)

### Community 28 - ".create"
Cohesion: 0.11
Nodes (11): CutoffRequired, Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, TemporalCutoff, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el… (+3 more)

### Community 29 - "_explicit_market_support"
Cohesion: 0.22
Nodes (24): _clip_0_100(), _explicit_market_support(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico., stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+16 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "LeagueMathEngine"
Cohesion: 0.07
Nodes (27): datetime, fastapi_testclient, pytest, calculate_dixon_coles_matrix(), calculate_weighted_average(), dixon_coles_tau(), estimate_nb_dispersion(), LeagueMathEngine (+19 more)

### Community 32 - "resolve_match_picks_correlation"
Cohesion: 0.19
Nodes (19): resolve_match_picks_correlation(), get_attr(), is_candidate_valid(), pick_merit_score(), _risk_imports(), is_hard_blocked(), True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., make_pick() (+11 more)

### Community 33 - "test_compare_integration.py"
Cohesion: 0.08
Nodes (17): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., 40.7% con cuota 2.46 sí tiene edge (implícita 40.65%), muy pequeño., El push no consume banca, así que el stake óptimo es mayor. (+9 more)

### Community 34 - "CalibrationCurve"
Cohesion: 0.16
Nodes (10): CalibrationCurve, Mapa monótono lineal por tramos de probabilidad raw -> calibrada. Los nodos…, Aplica la calibración. Acepta 0-1 o 0-100 y devuelve en la MISMA escala., Interpolación lineal entre nodos observados. Fuera del rango cubierto por los…, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale., test_curve_never_returns_exactly_zero_or_one(), test_curve_preserves_scale() (+2 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.10
Nodes (20): src_ui_api, _clean_calibrator(), fixture, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Aísla cada test con su propia ruta de artefacto y caché limpia., Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., Con edge >= 20 puntos y sin curva, se conserva el recorte antiguo. (+12 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - "TestFiltering"
Cohesion: 0.17
Nodes (10): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los…, El informe se registra en logs; no debe arrastrar el histórico entero. (+2 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "eligibility.py"
Cohesion: 0.12
Nodes (17): _as_float(), describe(), hard_blocks_from_flags(), _pget(), _pset(), PublicationThresholds, Any, Enum (+9 more)

### Community 40 - "schemas.py"
Cohesion: 0.18
Nodes (19): field_validator, pydantic, AnalysisHistoryOut, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut (+11 more)

### Community 41 - "ManualLoaderAdapter"
Cohesion: 0.17
Nodes (11): MarketType, str, Team (football) or player-as-team., Team, ManualLoaderAdapter, Any, DataFrame, Path (+3 more)

### Community 42 - "parse_utc"
Cohesion: 0.16
Nodes (7): parse_utc(), True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "HierarchicalCalibrator"
Cohesion: 0.13
Nodes (17): HierarchicalCalibrator, Path, Calibrador jerárquico y conservador. Orden de resolución: league × family ×…, get_calibrator(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.…, make_samples(), Menos de min_samples -> identidad, nunca una corrección inventada., Genera muestras sintéticas con una relación conocida prob->acierto. (+9 more)

### Community 44 - "pick_rules_engine.py"
Cohesion: 0.15
Nodes (15): re, classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line() (+7 more)

### Community 45 - "record_date"
Cohesion: 0.11
Nodes (10): FilterReport, Any, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Reparte los registros en admitidos, posteriores y sin fecha., record_date() (+2 more)

### Community 46 - "calibration.py"
Cohesion: 0.24
Nodes (13): _clean_segment_value(), directional_key(), family_key(), league_key(), line_key(), Calibración probabilística real de Sherlock. SIN GLM. Por qué no GLM / stacking…, Devuelve la curva más específica disponible. Nunca crea una curva implícita. Si…, Calibra una probabilidad y conserva su escala de entrada. Entrada 0-1 -> salida… (+5 more)

### Community 47 - "json"
Cohesion: 0.11
Nodes (18): argparse, backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup() (+10 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationSample"
Cohesion: 0.11
Nodes (19): CalibrationSample, fit_curve(), _quantile_edges(), Un bin de la curva de reliability, con su evidencia., Bordes de bin por cuantiles, garantizando ocupación mínima., Ajusta una curva por Beta-Binomial + isotónica PAVA. Mejoras frente a la…, Una observación histórica para ajustar la calibración. `prob` puede venir en…, ReliabilityBin (+11 more)

### Community 50 - "RiskLimits"
Cohesion: 0.17
Nodes (8): False solo cuando el kill switch está echado., Stake que se puede arriesgar de verdad. En PAPER y HALTED es siempre 0: el…, Política de riesgo efectiva. Inmutable: se resuelve una vez y se pasa., RiskLimits, test_describe_mentions_the_mode(), test_halted_mode_blocks_every_pick(), test_limits_are_immutable(), test_to_dict_exposes_the_mode()

### Community 51 - "parallel_recalc.py"
Cohesion: 0.12
Nodes (26): asyncio, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), _check_pick_success(), _combine_split_outcomes(), _extract_line() (+18 more)

### Community 52 - "evaluate"
Cohesion: 0.12
Nodes (17): brier_score(), evaluate(), expected_calibration_error(), log_loss(), Error cuadrático medio de la probabilidad. Menor es mejor., Log loss (entropía cruzada). Penaliza la sobreconfianza con fuerza., ECE: desvío absoluto medio entre confianza y acierto, ponderado por bin. 0 =…, Resumen de calidad probabilística. (+9 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.27
Nodes (10): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad calibrada, la misma que se muestra. Decidir con…, test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_calibrated_prob() (+2 more)

### Community 54 - "_populate_history_extra_fields"
Cohesion: 0.12
Nodes (15): _check_projected_line_success(), get_analysis_by_id(), get_league_matches(), list_analysis(), _populate_history_extra_fields(), Return the sum of stake_units for publishable picks of a match., List saved analyses with optional filters and pagination., Obtiene toda la información necesaria para un partido en específico por su ID. (+7 more)

### Community 55 - "settlement.py"
Cohesion: 0.18
Nodes (12): dataclasses, functools, math, distribution_for_total_line(), outcome_probabilities_for_total(), Enum, Motor único de liquidación de Sherlock. Este módulo es la ÚNICA fuente de…, Convierte una PMF del total (determinista) en probabilidades de outcome para… (+4 more)

### Community 56 - "calculate_league_params.py"
Cohesion: 0.29
Nodes (11): calculate_parameters(), calculate_parameters_per_match(), fetch_historical_matches_by_league(), main(), print_summary(), Any, Script CLI para calcular parámetros matemáticos (Dixon-Coles, promedios por…, Calcula todos los parámetros matemáticos a partir de los datos históricos. (+3 more)

### Community 57 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 58 - "_normalize_betano_odds"
Cohesion: 0.33
Nodes (4): _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…

### Community 59 - "record_hard_block"
Cohesion: 0.40
Nodes (5): Emite bloqueos duros sobre un pick dict-u-objeto. Irreversible. Escribe el…, record_hard_block(), test_record_hard_block_accumulates(), test_record_hard_block_works_on_dict(), test_record_hard_block_works_on_object()

### Community 60 - "risk.py"
Cohesion: 0.22
Nodes (8): os, _env_bool(), _env_number(), PublicationMode, Enum, str, Límites de riesgo y kill switch de publicación. Por qué está separado de…, Lee un booleano de entorno. Un valor presente pero ininteligible NO se ignora…

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

### Community 69 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 73 - "clean_env"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

## Knowledge Gaps
- **30 isolated node(s):** `sherlock`, `sherlockBtn`, `BOOKMAKER_LABELS`, `leaguesData`, `selectedMarketsSet` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 589 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HierarchicalCalibrator` connect `HierarchicalCalibrator` to `test_train_calibration.py`, `test_calibration_wiring.py`, `compare.py`, `calibration.py`, `test_calibration.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `BlockReason` to `resolve_match_picks_correlation`, `is_hard`, `compare.py`, `eligibility.py`, `test_risk.py`, `test_eligibility_wiring.py`, `pick_rules_engine.py`, `compare_football`, `EligibilityDecision`, `PickSnapshot`, `_value_indicator`, `record_hard_block`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `LeagueMathEngine` connect `LeagueMathEngine` to `.compute_pick_hit_rate`, `compare.py`, `main.py`, `compare_football`, `save_analysis`, `calculate_league_params.py`, `TestLeagueMathEngine`, `.create`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `BlockReason` (e.g. with `resolve_match_picks_correlation()` and `_risk_imports()`) actually correct?**
  _`BlockReason` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `compare_football()` (e.g. with `LeagueMathEngine` and `BlockReason`) actually correct?**
  _`compare_football()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `AnalysisHistory` (e.g. with `purge_odds_before_cutoff()` and `load_rows_from_db()`) actually correct?**
  _`AnalysisHistory` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Outcome` (e.g. with `extract_samples()` and `under_over_probabilities()`) actually correct?**
  _`Outcome` has 17 INFERRED edges - model-reasoned connections that need verification._