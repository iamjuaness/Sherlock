# Graph Report - Sherlock  (2026-09-19)

## Corpus Check
- 76 files · ~215,211 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 9 file(s) not represented in the graph (top: (none) 2, .example 1, .db 1)

## Summary
- 1631 nodes · 3658 edges · 105 communities (72 shown, 33 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 283 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3b27cd69`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Simulation & Comparison Scripts
- Web UI Comparator JS
- Watson Extension Background Service
- Domain Eligibility Logic
- Negative Binomial Model Core
- Pick Settlement & Profit API
- External Dependencies & Standard Tools
- Settlement Distribution Math
- Domain Risk Limits & Risk Tests
- Settlement Rationales & Edge Cases
- API Pick Eligibility Routes
- Watson Extension Popup UI
- API Line Shopping & Sport Models
- Web UI Leagues JS
- FastAPI Server Infrastructure
- compare_football
- manual_loader.py
- test_calibration.py
- save_analysis
- post
- EligibilityDecision
- test_settlement.py
- domain.py
- _value_indicator
- AnalysisHistory
- LeagueMathEngine
- get
- apply_pick_rules
- .create
- _explicit_market_support
- manifest.json
- math_engine.py
- resolve_match_picks_correlation
- test_compare_integration.py
- CalibrationCurve
- test_calibration_wiring.py
- dashboard_main.js
- test_temporal.py
- .compute_pick_hit_rate
- eligibility.py
- schemas.py
- ManualLoaderAdapter
- parse_utc
- HierarchicalCalibrator
- pick_rules_engine.py
- record_date
- calibration.py
- calculate_league_params.py
- train_model_retrospective.py
- CalibrationSample
- RiskLimits
- temporal.py
- walk_forward_calibrate
- PickSnapshot
- generate_football_analysis
- _dc_score_matrix
- make_samples
- backup_db.py
- prueba90100.py
- calculate_parameters
- risk.py
- CardsConvention
- split_asian_line
- betano_content.js
- settings.js
- sofaScoreToSherlock.js
- config.py
- _normalize_betano_odds
- pytest
- is_hard
- PublicationThresholds
- content.js
- _clean_calibrator
- clean_env
- test_no_artifact_keeps_legacy_082_shrink
- test_kelly_tiny_edge_is_tiny_but_positive
- test_threshold_families_match_the_legacy_sets
- sherlock

## God Nodes (most connected - your core abstractions)
1. `BlockReason` - 71 edges
2. `compare_football()` - 54 edges
3. `AnalysisHistory` - 47 edges
4. `Outcome` - 40 edges
5. `good_snapshot()` - 32 edges
6. `resolve_match_picks_correlation()` - 31 edges
7. `HierarchicalCalibrator` - 31 edges
8. `extract_samples()` - 29 edges
9. `load_risk_limits()` - 29 edges
10. `ReturnDistribution` - 29 edges

## Surprising Connections (you probably didn't know these)
- `calculate_parameters_per_match()` --uses--> `LeagueMathEngine`  [INFERRED]
  calculate_league_params.py → src/core/math_engine.py
- `test_promedio_corners_ultima_jornada()` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/test_corner_last_round.py → src/core/math_engine.py
- `TestEngineHitRates` --uses--> `LeagueMathEngine`  [INFERRED]
  tests/unit/test_temporal.py → src/core/math_engine.py
- `test_decision_is_immutable()` --uses--> `BlockReason`  [INFERRED]
  tests/unit/test_eligibility.py → src/domain/eligibility.py
- `test_every_reason_has_a_human_label()` --uses--> `BlockReason`  [INFERRED]
  tests/unit/test_eligibility.py → src/domain/eligibility.py

## Import Cycles
- None detected.

## Communities (105 total, 33 thin omitted)

### Community 0 - "Simulation & Comparison Scripts"
Cohesion: 0.05
Nodes (72): random, re, _coerce_datetime(), _extract_line_bucket(), extract_samples(), ExtractionStats, history_dir_for(), load_rows_from_db() (+64 more)

### Community 1 - "Web UI Comparator JS"
Cohesion: 0.07
Nodes (52): analyzeFootball(), apiCompare(), BOOKMAKER_LABELS, buildFootballPayloadFromForm(), cancelEditing(), checkPrefill(), copyPickAnalysis(), deleteHistoryEntry() (+44 more)

### Community 2 - "Watson Extension Background Service"
Cohesion: 0.08
Nodes (42): applyStatsToPayload(), BOOKMAKER_FETCHERS, buildHistoricalPayload(), delay(), fetchAllBookmakerOdds(), fetchSofaScore(), getStatsPeriod(), handleBulkExtractResults() (+34 more)

### Community 3 - "Domain Eligibility Logic"
Cohesion: 0.12
Nodes (46): BlockReason, evaluate_eligibility(), evaluate_soft_filters(), str, Aplica los umbrales recalculables. No conoce los bloqueos duros., Decisión única de elegibilidad. `previous` es la decisión anterior sobre el…, Motivos por los que un pick no se publica., good_snapshot() (+38 more)

### Community 4 - "Negative Binomial Model Core"
Cohesion: 0.08
Nodes (39): convolve(), CountPMF, dispersion_r(), nbinom_pmf(), nbinom_pmf_vector(), PMF de la suma de dos conteos independientes. Convolución discreta exacta:…, PMF del total del partido (local + visitante), determinista y cacheada. La…, Reemplazo DETERMINISTA de `get_nbinom_under_over_prob`. Devuelve `(p_under,… (+31 more)

### Community 5 - "Pick Settlement & Profit API"
Cohesion: 0.08
Nodes (37): PickOutcome, build_equity_curve(), _calculate_pick_profit(), _check_pick_success(), _combine_split_outcomes(), export_excel_report(), _extract_line(), get_all_picks() (+29 more)

### Community 6 - "External Dependencies & Standard Tools"
Cohesion: 0.08
Nodes (32): asyncio, dotenv, numpy, openai, pydantic_alias_generators, _combine_nb_params(), _compute_league_reliability_score(), _dc_component_weights() (+24 more)

### Community 7 - "Settlement Distribution Math"
Cohesion: 0.09
Nodes (32): dataclasses, functools, math, distribution_for_total_line(), Outcome, outcome_hit_value(), outcome_probabilities_for_total(), outcome_return() (+24 more)

### Community 8 - "Domain Risk Limits & Risk Tests"
Cohesion: 0.09
Nodes (35): load_risk_limits(), Any, Resuelve la política de riesgo efectiva. Precedencia: entorno >…, parametrize, Tests de límites de riesgo, kill switch y exposición por evento. Principio que…, Un valor ininteligible no debe abrir la publicación real. `flase` es un typo…, Un tope de 0 bloquearía todo silenciosamente: se trata como no puesto., Editar pick_rules.json no debe poder ampliar la exposición. Era justo el… (+27 more)

### Community 9 - "Settlement Rationales & Edge Cases"
Cohesion: 0.07
Nodes (26): Distribución de probabilidad sobre los outcomes de UNA apuesta. Las…, Mercado sin líneas de cuarto: solo win / push / loss. Acepta probabilidades en…, Invariante del audit: la suma de probabilidades de estados = 1., Pares (probabilidad, retorno neto) con probabilidad > 0., EV correcto por unidad apostada: E[R] = Σ p_i · r_i Para win/push/loss esto…, Probabilidad de acierto condicionada a que la apuesta resuelva., Cuota justa: la que hace EV = 0 manteniendo la forma de la distribución., Kelly sobre la distribución COMPLETA de retornos. Maximiza E[log(1 + f·R)]… (+18 more)

### Community 10 - "API Pick Eligibility Routes"
Cohesion: 0.13
Nodes (33): block_pick(), current_eligibility(), evaluate_pick_eligibility(), is_publishable_pick(), Reconstruye la decisión de elegibilidad ya acumulada sobre este pick. Une dos…, Evalúa la elegibilidad y ESCRIBE el resultado en el pick. Es el único punto que…, Emite uno o más bloqueos duros sobre un pick. Operación irreversible. Sustituye…, True si el pick es publicable AHORA, respetando todo bloqueo previo. Antes esta… (+25 more)

### Community 11 - "Watson Extension Popup UI"
Cohesion: 0.13
Nodes (29): _allMatchesCache, delay(), els, fetchSofaScoreAPI(), formatTimestamp(), getActiveCompetitions(), handleBulkExtractResultsUI(), handleBulkExtractStatsUI() (+21 more)

### Community 12 - "API Line Shopping & Sport Models"
Cohesion: 0.08
Nodes (34): Session, Sport, CompareResponse, _annotate_best_bookmaker(), _apply_line_shopping(), _check_payload_has_odds(), _has_valid(), compare_teams_football() (+26 more)

### Community 13 - "Web UI Leagues JS"
Cohesion: 0.13
Nodes (32): addMarketToBlacklist(), applyBulkBlacklist(), changeSelectedSeason(), currentMarketsList, currentMatchesCache, deleteCurrentLeague(), deleteHistoryEntry(), escapeAttr() (+24 more)

### Community 14 - "FastAPI Server Infrastructure"
Cohesion: 0.08
Nodes (30): contextlib, copy, datetime, FastAPI, fastapi_middleware_cors, fastapi_responses, fastapi_staticfiles, fastapi_templating (+22 more)

### Community 15 - "compare_football"
Cohesion: 0.18
Nodes (27): compare_football(), _compute_cards_lambda(), _compute_corners_lambda(), _compute_fouls_lambda(), _compute_offsides_lambda(), _compute_shots_lambda(), _compute_shots_target_lambda(), _compute_team_cards_lambda() (+19 more)

### Community 16 - "manual_loader.py"
Cohesion: 0.11
Nodes (19): ABC, pandas, Competition, Match, A single fixture / game between two teams or players., Aggregated team stats for a single match., Individual player stats for a single match., League, tournament or cup. (+11 more)

### Community 17 - "test_calibration.py"
Cohesion: 0.11
Nodes (28): brier_score(), expected_calibration_error(), log_loss(), pava(), Construye muestras desde filas liquidadas, excluyendo push y unsettled. Espera…, Regresión isotónica ponderada por Pool Adjacent Violators. Devuelve la…, Error cuadrático medio de la probabilidad. Menor es mejor., Log loss (entropía cruzada). Penaliza la sobreconfianza con fuerza. (+20 more)

### Community 18 - "save_analysis"
Cohesion: 0.09
Nodes (25): Exception, field_validator, _check_projected_line_success(), _extract_competition(), get_analysis_by_id(), get_league_matches(), _populate_history_extra_fields(), Extract competition name from payload dict, avoiding json.loads in callers. (+17 more)

### Community 19 - "post"
Cohesion: 0.10
Nodes (26): post, Fuerza la recarga del artefacto en la siguiente llamada (usado en tests)., reset_calibrator_cache(), apply_blacklist(), blacklist_market(), blacklist_markets_batch(), BlacklistMarketRequest, BlacklistMarketsBatchRequest (+18 more)

### Community 20 - "EligibilityDecision"
Cohesion: 0.08
Nodes (16): describe(), EligibilityDecision, Resultado inmutable de evaluar la elegibilidad. `hard_blocks` solo puede…, Motivos ordenados de forma estable: duros primero, luego blandos., Añade bloqueos duros. Nunca quita ninguno., Une dos decisiones sobre el mismo pick. Los bloqueos duros se unen (nunca se…, Devuelve el `quality_score` que corresponde publicar. Un pick con bloqueo duro…, Reconstruye una decisión desde una lista plana de motivos, separando duros de… (+8 more)

### Community 21 - "test_settlement.py"
Cohesion: 0.17
Nodes (26): _combine_legs(), line_legs(), Descompone una línea en sus piernas efectivas. x.0 -> (x.0,) una pierna, admite…, Combina los resultados de las piernas (cada una con media unidad). Solo se usan…, Liquida un mercado Over/Under (goles, corners, tarjetas, tiros, faltas...).…, Liquida un hándicap asiático para el equipo apostado. `margin` = goles del…, settle_asian_handicap(), settle_total() (+18 more)

### Community 22 - "domain.py"
Cohesion: 0.10
Nodes (21): DeclarativeBase, enum, listens_for, sqlalchemy, sqlalchemy_orm, Base, _column_exists(), create_indexes() (+13 more)

### Community 23 - "_value_indicator"
Cohesion: 0.12
Nodes (24): apply_calibration(), _calculate_display_score(), _calculate_stake_units(), calibration_is_active(), _calibration_side(), _vi(), get_data_quality_score(), get_market_confidence_tier() (+16 more)

### Community 24 - "AnalysisHistory"
Cohesion: 0.11
Nodes (21): delete, put, AnalysisHistory, History of manual analyses performed in the comparator., deduplicate_competition_matches(), delete_analysis(), delete_competition_matches(), delete_incomplete_competition_matches() (+13 more)

### Community 25 - "LeagueMathEngine"
Cohesion: 0.12
Nodes (11): LeagueMathEngine, Any, Calcula probabilidades de partido integrando promedios por liga, fuerza…, Calcula los promedios específicos de la liga basándose en los partidos…, Capa 3: Calcula estadísticas promedio del equipo `team_name` en ventanas…, Evalúa si un partido específico cumple con el criterio de un pick. Soporta:…, Calcula el Hit Rate específico en los enfrentamientos directos previos (H2H)…, test_promedio_corners_ultima_jornada() (+3 more)

### Community 26 - "get"
Cohesion: 0.11
Nodes (24): get, middleware, Request, consume_prefill(), consume_prefill_odds(), consume_result(), disable_cache_in_dev(), file_version() (+16 more)

### Community 27 - "apply_pick_rules"
Cohesion: 0.11
Nodes (17): evaluate_pick_rules(), load_pick_rules_data(), Any, Build StatSource from live FootballTeamStats objects. odds_obj: optional…, Build StatSource from saved payload dicts (AnalysisHistory). odds_payload: the…, Resuelve stat_key tal como aparece en pick_rules.json / rules.html: -…, Resuelve una clave de cuota (sin el prefijo 'odds_'). Claves simples directas…, Diferencia máxima entre |xG - xGA| de ambos equipos. Mide equilibrio… (+9 more)

### Community 28 - ".create"
Cohesion: 0.13
Nodes (8): Instante a partir del cual la información no existe todavía. `kickoff` siempre…, Construye el cutoff, o None si el kickoff no es utilizable., Igual que `create` pero exige un kickoff válido. Se usa en las rutas donde…, TemporalCutoff, `create` no puede inventar un kickoff por defecto. Devolver un cutoff en el…, Igualdad excluida: un partido no puede ser evidencia de sí mismo. Con `<=` el…, Un partido a las 20:00 en Bogotá es 01:00 UTC del día siguiente. Comparar…, TestTemporalCutoff

### Community 29 - "_explicit_market_support"
Cohesion: 0.22
Nodes (24): _clip_0_100(), _explicit_market_support(), _projected_value_by_keywords(), stat_support con penalización no lineal en colas extremas (Over > 3.5)., Soporte Under modelado independientemente con factor de ruido de partido…, Soporte probabilístico estricto y coherente para Doble Oportunidad. Evita…, stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico., stat_support = 0.60 * P_modelo_NB(over line) + 0.40 * HitRate_empírico. (+16 more)

### Community 30 - "manifest.json"
Cohesion: 0.08
Nodes (23): action, default_icon, default_popup, background, service_worker, content_scripts, 128, 16 (+15 more)

### Community 31 - "math_engine.py"
Cohesion: 0.11
Nodes (15): calculate_dixon_coles_matrix(), calculate_weighted_average(), dixon_coles_tau(), estimate_nb_dispersion(), _poisson_pmf(), Motor Estadístico Matemático por Liga para Sherlock (Watson Math Engine).…, Estima el parámetro de dispersión (alpha/k) de la Binomial Negativa por Método…, Capa 2: Calcula lambda_home y mu_away usando fuerza ofensiva y defensiva… (+7 more)

### Community 32 - "resolve_match_picks_correlation"
Cohesion: 0.16
Nodes (21): resolve_match_picks_correlation(), get_attr(), is_candidate_valid(), pick_merit_score(), _risk_imports(), is_hard_blocked(), True si el pick arrastra cualquier bloqueo duro. Nunca debe publicarse., make_pick() (+13 more)

### Community 33 - "test_compare_integration.py"
Cohesion: 0.09
Nodes (15): Regresión a nivel de `compare.py`: verifica que las correcciones P0 están…, Sin push, EV sigue siendo (p·odds) - 1., Dos recálculos idénticos deben dar exactamente el mismo resultado., Over x.25 debe conservar la misma probabilidad de acierto que x.0 pero con la…, Sin pushes el resultado no cambia: no rompemos el comportamiento previo., EV <= 0 -> no se apuesta. 1/2.46 = 40.65%, así que 40.0% es EV negativo., El push no consume banca, así que el stake óptimo es mayor., El bug: EV se calculaba como (p·odds - 1)·(1 - p_push), tratando el push como… (+7 more)

### Community 34 - "CalibrationCurve"
Cohesion: 0.12
Nodes (13): CalibrationCurve, Un bin de la curva de reliability, con su evidencia., Mapa monótono lineal por tramos de probabilidad raw -> calibrada. Los nodos…, Aplica la calibración. Acepta 0-1 o 0-100 y devuelve en la MISMA escala., Interpolación lineal entre nodos observados. Fuera del rango cubierto por los…, ReliabilityBin, Cuotas justas infinitas y log loss infinito son fallos de producción., 0-100 entra, 0-100 sale; 0-1 entra, 0-1 sale. (+5 more)

### Community 35 - "test_calibration_wiring.py"
Cohesion: 0.14
Nodes (15): src_ui_api, Tests del cableado de la calibración en compare.py. Contrato: - Sin artefacto…, Bajar la probabilidad calibrada debe bajar el EV y el stake. Si la calibración…, Artefacto entrenado con sobreconfianza conocida: real ≈ shrink · p., El 0.82 y la curva corrigen el MISMO sesgo. Aplicar ambos lo castiga dos veces,…, test_artifact_reloads_when_file_changes(), test_calibration_flows_into_ev_and_kelly(), test_calibration_is_deterministic_across_calls() (+7 more)

### Community 36 - "dashboard_main.js"
Cohesion: 0.18
Nodes (19): downloadExcelReport(), fetchGlobalStats(), getDashboardDateParams(), handleDashboardDateRangeChange(), handleDashboardGeneralStatsChange(), handleDashboardGeneralStatsDateChange(), reloadDashboardStats(), renderBucketsChart() (+11 more)

### Community 37 - "test_temporal.py"
Cohesion: 0.16
Nodes (11): filter_before_cutoff(), Filtra un histórico dejando solo lo anterior al kickoff. Sin un kickoff…, Invariantes del cutoff temporal. La propiedad que se defiende aquí es una sola…, Cada registro visto tiene que estar en exactamente una cesta. Si la suma no…, Son problemas distintos: futuro significa fuga de datos; sin fecha significa…, Ésta es la invariante central: sin kickoff, cero registros. La versión anterior…, `allow_missing_cutoff` no puede activarse por accidente pasando un posicional…, Con la escotilla abierta no hay filtrado de ningún tipo: entran incluso los… (+3 more)

### Community 38 - ".compute_pick_hit_rate"
Cohesion: 0.21
Nodes (7): Calcula el porcentaje histórico de acierto de cualquier pick para un equipo.…, _match(), Regresión directa del fallo: `current_match_date=None` devolvía las 5 muestras,…, Una muestra vacía por falta de cutoff no es lo mismo que una muestra vacía por…, Antes, comparar un `match_date` aware con un kickoff naive lanzaba TypeError…, Propiedad: adelantar el kickoff nunca puede ampliar la muestra. Si la muestra…, TestEngineHitRates

### Community 39 - "eligibility.py"
Cohesion: 0.17
Nodes (17): _as_float(), _coerce_reason(), hard_blocks_from_flags(), _pget(), _pset(), Any, Enum, Decisión única de elegibilidad de un pick, con razones inmutables. El problema… (+9 more)

### Community 40 - "schemas.py"
Cohesion: 0.23
Nodes (16): pydantic, AnalysisResultsUpdate, AnalysisSave, BettingLineOut, BucketStat, CategoryStatsOut, CompetitionOut, Config (+8 more)

### Community 41 - "ManualLoaderAdapter"
Cohesion: 0.17
Nodes (11): MarketType, str, Team (football) or player-as-team., Team, ManualLoaderAdapter, Any, DataFrame, Path (+3 more)

### Community 42 - "parse_utc"
Cohesion: 0.19
Nodes (6): parse_utc(), Normaliza cualquier representación de fecha a un `datetime` UTC con zona.…, parametrize, Un solo naive que se escape reintroduce el TypeError al comparar aware con…, `parse_utc` se llama en bucles sobre datos de terceros. Si lanzase, un registro…, TestParseUtc

### Community 43 - "HierarchicalCalibrator"
Cohesion: 0.19
Nodes (9): HierarchicalCalibrator, Path, Calibrador jerárquico y conservador. Orden de resolución: league × family ×…, Calibra una probabilidad y conserva su escala de entrada. Entrada 0-1 -> salida…, get_calibrator(), Devuelve el calibrador activo, recargándolo si el artefacto cambió en disco.…, test_load_rejects_unknown_format_version(), test_save_load_roundtrip() (+1 more)

### Community 44 - "pick_rules_engine.py"
Cohesion: 0.20
Nodes (14): classify_correlation_severity(), clear_correlation_matrix_cache(), load_market_correlation_matrix(), market_correlation_rho(), market_family(), market_group(), market_line(), market_side() (+6 more)

### Community 45 - "record_date"
Cohesion: 0.18
Nodes (7): Any, Extrae la fecha de un registro probando varias claves en orden de fiabilidad.…, True solo si `value` es demostrablemente anterior al kickoff. Una fecha ausente…, Reparte los registros en admitidos, posteriores y sin fecha., record_date(), En `analysis_history`, `date` es la fecha de CREACIÓN del registro, no la del…, TestRecordDate

### Community 46 - "calibration.py"
Cohesion: 0.30
Nodes (12): _clean_segment_value(), directional_key(), family_key(), league_key(), line_key(), Calibración probabilística real de Sherlock. SIN GLM. Por qué no GLM / stacking…, Devuelve la curva más específica disponible. Nunca crea una curva implícita. Si…, Ajusta la jerarquía completa con partial pooling. Los mínimos más altos evitan… (+4 more)

### Community 47 - "calculate_league_params.py"
Cohesion: 0.18
Nodes (11): argparse, Script CLI para calcular parámetros matemáticos (Dixon-Coles, promedios por…, Connection, json, logging, pathlib, sys, check_query() (+3 more)

### Community 48 - "train_model_retrospective.py"
Cohesion: 0.29
Nodes (13): requests, get_db(), FastAPI dependency that yields a DB session., compute_retrospective_stats(), _extract_team_names_and_payload(), get_training_data(), _has_odds(), Any (+5 more)

### Community 49 - "CalibrationSample"
Cohesion: 0.18
Nodes (13): CalibrationSample, fit_curve(), _quantile_edges(), Bordes de bin por cuantiles, garantizando ocupación mínima., Ajusta una curva por Beta-Binomial + isotónica PAVA. Mejoras frente a la…, Una observación histórica para ajustar la calibración. `prob` puede venir en…, Clave del diseño: con poca muestra el ruido NO puede dominar. 8 observaciones…, test_curve_clamps_to_unit_interval() (+5 more)

### Community 50 - "RiskLimits"
Cohesion: 0.17
Nodes (8): False solo cuando el kill switch está echado., Stake que se puede arriesgar de verdad. En PAPER y HALTED es siempre 0: el…, Política de riesgo efectiva. Inmutable: se resuelve una vez y se pasa., RiskLimits, test_describe_mentions_the_mode(), test_halted_mode_blocks_every_pick(), test_limits_are_immutable(), test_to_dict_exposes_the_mode()

### Community 51 - "temporal.py"
Cohesion: 0.15
Nodes (7): CutoffRequired, FilterReport, datetime, Cutoff temporal en UTC. Impide que información posterior al saque inicial entre…, Resultado de aplicar un cutoff, con el detalle de qué se descartó y por qué.…, Se pidió filtrar por cutoff sin un kickoff utilizable. Es un error explícito y…, ValueError

### Community 52 - "walk_forward_calibrate"
Cohesion: 0.17
Nodes (11): evaluate(), Resumen de calidad probabilística., Predicciones OOF y métricas antes/después de calibrar., Regla de promoción: la calibración solo se acepta si mejora Brier Y log loss…, Walk-forward estricto por grupos temporales. Un mismo timestamp se trata como…, walk_forward_calibrate(), WalkForwardResult, test_improved_is_false_when_calibration_hurts() (+3 more)

### Community 53 - "PickSnapshot"
Cohesion: 0.27
Nodes (10): PickSnapshot, Los datos mínimos para decidir elegibilidad. Es un DTO plano en lugar de…, Construye el snapshot desde un `ValueIndicator` o un dict. La probabilidad…, Se decide con la probabilidad calibrada, la misma que se muestra. Decidir con…, test_snapshot_falls_back_to_model_prob(), test_snapshot_handles_camel_case(), test_snapshot_of_empty_pick_fails_closed(), test_snapshot_prefers_calibrated_prob() (+2 more)

### Community 54 - "generate_football_analysis"
Cohesion: 0.18
Nodes (10): _are_contradictory(), _calibration_line_bucket(), _call_openrouter(), _canonical_pick_signature(), _deduplicate_correlated_picks(), _extract_line_number(), generate_football_analysis(), _implied_prob_from_odds() (+2 more)

### Community 55 - "_dc_score_matrix"
Cohesion: 0.20
Nodes (12): _dc_log_likelihood(), _dc_match_probs(), _dc_score_matrix(), _dc_tau(), _default_dc_rho(), fit_dixon_coles_rho(), _poisson_pmf(), Heurística original — se mantiene como fallback. (+4 more)

### Community 56 - "make_samples"
Cohesion: 0.17
Nodes (12): make_samples(), El audit: 'la curva de calibración muestra sobreconfianza fuerte en…, Si el modelo ya está calibrado, la curva debe quedarse cerca de la identidad., Menos de min_samples -> identidad, nunca una corrección inventada., Genera muestras sintéticas con una relación conocida prob->acierto., test_apply_is_deterministic(), test_artifact_is_versioned(), test_corrects_systematic_overconfidence() (+4 more)

### Community 57 - "backup_db.py"
Cohesion: 0.22
Nodes (10): backup_db(), _list_backup_files(), Backup y restauración segura de data/sherlock.db (modo WAL). Cambios sobre la…, Lista los nombres de backup válidos en BACKUP_DIR. Usa startswith/endswith…, Genera un backup consistente de data/sherlock.db en backup/., Restaura el backup más reciente sobre data/sherlock.db., restore_backup(), os (+2 more)

### Community 58 - "prueba90100.py"
Cohesion: 0.27
Nodes (10): parse_any_date(), payload_contains_odds(), purge_odds_before_cutoff(), purge_odds_recursively(), datetime, Script para eliminar parámetros de cuotas (odds, sources, bookmaker, markets,…, Limpia registros previos a cutoff_date donde has_odds == 1 O el payload…, Parsea formatos de fecha en string, timestamps o datetimes. (+2 more)

### Community 59 - "calculate_parameters"
Cohesion: 0.29
Nodes (10): calculate_parameters(), calculate_parameters_per_match(), fetch_historical_matches_by_league(), main(), print_summary(), Any, Calcula todos los parámetros matemáticos a partir de los datos históricos., Calcula por cada partido las estadísticas acumuladas de la liga y de los dos… (+2 more)

### Community 60 - "risk.py"
Cohesion: 0.25
Nodes (7): _env_bool(), _env_number(), PublicationMode, Enum, str, Límites de riesgo y kill switch de publicación. Por qué está separado de…, Lee un booleano de entorno. Un valor presente pero ininteligible NO se ignora…

### Community 61 - "CardsConvention"
Cohesion: 0.29
Nodes (6): CardsConvention, Convención explícita para contar tarjetas. `red_weight = 1.0` -> una roja…, Total de tarjetas según la convención. None si falta la base., El audit: estadísticas de tarjetas ausentes se convertían en cero., test_cards_convention_explicit(), test_cards_missing_yellows_is_none_not_zero()

### Community 62 - "split_asian_line"
Cohesion: 0.29
Nodes (6): _neg_bin_pmf(), _neg_binomial_over_under(), _get_single_line_probs(), _poisson_over_under(), Divide una línea asiática (ej. 2.25) en sus dos componentes (2.0 y 2.5)., split_asian_line()

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

### Community 67 - "_normalize_betano_odds"
Cohesion: 0.33
Nodes (4): _normalize_betano_odds(), push_prefill_odds(), Convert the snake_case payload from betano_content.js into the camelCase format…, Recibe cuotas de una o varias casas de apuestas para el mismo partido. Las…

### Community 68 - "pytest"
Cohesion: 0.40
Nodes (4): fastapi_testclient, pytest, Verifica que al guardar un análisis sin count_in_profitability explícito: - Si…, test_save_analysis_respects_profitable_leagues()

### Community 69 - "is_hard"
Cohesion: 0.50
Nodes (4): is_hard(), Fallar cerrado: un motivo que no reconocemos no puede ser un filtro laxo., test_known_soft_reason_is_not_hard(), test_unknown_reason_is_treated_as_hard()

### Community 72 - "_clean_calibrator"
Cohesion: 0.67
Nodes (3): _clean_calibrator(), fixture, Aísla cada test con su propia ruta de artefacto y caché limpia.

### Community 73 - "clean_env"
Cohesion: 0.67
Nodes (3): clean_env(), fixture, Ninguna variable de riesgo heredada del entorno del test runner.

## Knowledge Gaps
- **30 isolated node(s):** `sherlock`, `sherlockBtn`, `BOOKMAKER_LABELS`, `leaguesData`, `selectedMarketsSet` (+25 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 582 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AnalysisHistory` connect `AnalysisHistory` to `Simulation & Comparison Scripts`, `get`, `Pick Settlement & Profit API`, `External Dependencies & Standard Tools`, `API Line Shopping & Sport Models`, `FastAPI Server Infrastructure`, `train_model_retrospective.py`, `save_analysis`, `post`, `domain.py`, `prueba90100.py`, `apply_pick_rules`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `ReturnDistribution` connect `Settlement Rationales & Edge Cases` to `Negative Binomial Model Core`, `External Dependencies & Standard Tools`, `Settlement Distribution Math`, `test_settlement.py`, `_value_indicator`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `BlockReason` connect `Domain Eligibility Logic` to `resolve_match_picks_correlation`, `is_hard`, `External Dependencies & Standard Tools`, `eligibility.py`, `Domain Risk Limits & Risk Tests`, `API Pick Eligibility Routes`, `pick_rules_engine.py`, `compare_football`, `EligibilityDecision`, `PickSnapshot`, `_value_indicator`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `BlockReason` (e.g. with `resolve_match_picks_correlation()` and `_risk_imports()`) actually correct?**
  _`BlockReason` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `compare_football()` (e.g. with `LeagueMathEngine` and `BlockReason`) actually correct?**
  _`compare_football()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `AnalysisHistory` (e.g. with `purge_odds_before_cutoff()` and `load_rows_from_db()`) actually correct?**
  _`AnalysisHistory` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Outcome` (e.g. with `extract_samples()` and `under_over_probabilities()`) actually correct?**
  _`Outcome` has 17 INFERRED edges - model-reasoned connections that need verification._