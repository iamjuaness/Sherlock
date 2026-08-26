# Auditoría integral y plan de mejora de Sherlock

Fecha de auditoría: 21 de agosto de 2026  
Alcance: motor estadístico, selección y liquidación de picks, histórico y calibración, API y persistencia, interfaz web, extensión Watson, configuración, reproducibilidad y operación.

## Dictamen ejecutivo

Sherlock tiene una base prometedora: genera probabilidades por mercado, calcula picks de valor, separa categorías de apuesta, conserva histórico y ya dispone de una auditoría con resultados reales. Sin embargo, **todavía no debe usarse como motor autónomo de staking con dinero real**.

El problema principal no es que Poisson o Dixon-Coles necesiten otro coeficiente. Existen fallas anteriores y más graves:

1. El payoff de pushes y líneas asiáticas no se representa correctamente en EV y Kelly.
2. La liquidación histórica puede convertir datos faltantes en ceros y modificar retrospectivamente qué picks cuentan.
3. Los filtros históricos pueden incluir partidos futuros, otras ligas o registros no elegibles.
4. Un pick bloqueado o que falla filtros duros puede recuperar el estado `is_publishable=True`.
5. La calibración actual es una identidad y el entrenamiento llama a una ruta que no existe.
6. Los mercados de Binomial Negativa usan simulación aleatoria sin semilla y liquidan mal líneas de cuarto.
7. Watson no puede iniciar por un error de sintaxis.
8. La API carece de autenticación, usa estado global y puede asociar resultados al partido equivocado.
9. El proyecto no incluye dependencias fijadas, pruebas ni una forma reproducible de arrancar.
10. La base histórica utilizada por el notebook no está versionada, por lo que sus resultados no pueden reproducirse desde este repositorio.

La prioridad correcta es asegurar primero la integridad del retorno, del dato y de la evaluación temporal. Añadir mercados, variables o modelos más complejos antes de hacerlo aumentaría la falsa confianza.

## Evidencia disponible y sus límites

El notebook incluido fue ejecutado previamente sobre 889 partidos y 9.442 picks deserializados, de los cuales 8.524 tenían resultado. En esa ejecución:

- Todos los picks generados: 8.524, hit rate 41,22%, ROI flat -7,32%.
- Picks marcados `is_value` o `is_publishable`: 399, hit rate 58,40%, ROI flat +14,17%.
- Tarjetas publicables: 137 picks, ROI +30,30%.
- Doble oportunidad: 145 picks, ROI +7,15%.
- Corners: 23 picks, ROI +18,96%.
- Tiros: 88 picks, ROI -0,37%.

Esta evidencia es útil para formular hipótesis, pero no demuestra una ventaja futura porque:

- el archivo `analysis_history.csv` usado por el notebook no está en el repositorio;
- la política de publicación puede reescribirse después de conocer resultados;
- los picks de un mismo partido están correlacionados;
- no hay holdout final inmutable ni walk-forward documentado;
- el notebook prefiere `model_prob` sobre `calibrated_prob`;
- la curva de calibración muestra sobreconfianza fuerte en probabilidades altas;
- no hay CLV ni prueba de que la cuota registrada fuera realmente ejecutable;
- la liquidación y los flags históricos contienen defectos que afectan ROI y accuracy.

Por tanto, el ROI histórico debe tratarse como un resultado exploratorio potencialmente sesgado.

## Evaluación por área

| Área | Estado | Riesgo principal |
|---|---|---|
| Liquidación, EV y Kelly | Crítico | Retornos incorrectos en push, half-win, half-loss y líneas asiáticas |
| Integridad temporal y leakage | Crítico | Futuros, mismo partido, otras ligas o filas sin fecha pueden entrar al histórico |
| Elegibilidad y publicación | Crítico | Bloqueos y filtros duros no son invariantes |
| Entrenamiento y calibración | Crítico | Endpoint inexistente, calibración identidad y sin validación OOS |
| Calidad y procedencia de datos | Alto | Defaults e imputaciones se confunden con observaciones |
| Correlación y riesgo de cartera | Alto | Reglas estáticas y exposición configurable hasta 5 picks/10u por evento |
| API y seguridad | Crítico si sale de localhost | Sin auth, CORS abierto y operaciones destructivas públicas |
| Persistencia y matching | Alto | Estado global y asociación fuzzy pueden mezclar eventos |
| Watson | Crítico | `background.js` no parsea |
| Reproducibilidad y pruebas | Crítico | Sin manifiesto, lockfile, CI ni tests |
| Arquitectura y mantenibilidad | Alto | Archivos monolíticos, lógica duplicada y migraciones ad hoc |

## Fallas bloqueantes

### Liquidación, EV y stake

**EV con push incorrecto.** En `src/ui/api/compare.py:1098-1120`, el cálculo base trata el push como pérdida y después aplica un factor. El retorno correcto para una apuesta con push es:

\[
E[R] = P(win)(odds-1) - P(loss)
\]

El push aporta retorno cero. Para líneas de cuarto deben modelarse las dos piernas y sus retornos parciales.

**Kelly incorrecto con pushes.** En `compare.py:1052-1096`, \(q=1-p\) incluye pushes como pérdidas. Kelly debe calcularse sobre la distribución completa de retornos, no sobre una Bernoulli ficticia.

**Líneas asiáticas NB mal tratadas.** `compare.py:691-704` compara directamente el total simulado contra 2.25, 2.75, etc. Así, un Over 2.25 con total 2 se convierte en pérdida completa en vez de half-loss.

**Simulación no determinista.** Los mercados NB usan `np.random.negative_binomial` sin generador ni semilla. Dos recálculos idénticos pueden producir probabilidades y picks distintos.

**Liquidación histórica contaminada.** En `src/ui/api/main.py:4515-4517` y `4586-4598`, `half_win` cuenta como acierto completo y estadísticas de tarjetas ausentes pueden convertirse en cero.

### Leakage e histórico

**Consulta histórica insuficientemente filtrada.** `compare.py:3640-3694` no restringe de forma fiable por competición, deporte, temporada, calidad del dato y elegibilidad.

**Fallo abierto cuando falta fecha.** `compare.py:3621-3635` y `math_engine.py:456-494` permiten calcular soporte sin un cutoff válido. Un modelo prepartido debe fallar cerrado si no puede probar que cada registro ocurrió antes del kickoff.

**Forma reciente sin cutoff fiable.** `math_engine.py:299-351` no recibe una fecha objetivo y usa coincidencia parcial de nombres.

**Reescritura retrospectiva.** `main.py:3066-3139` permite aplicar reglas actuales sobre picks históricos. Esto sirve para una simulación, pero no debe reemplazar la decisión realmente disponible antes del partido.

### Publicación

**Filtros duros no vinculantes.** En `compare.py:3794-3801`, un `quality_score=-1` no impide necesariamente que `is_publishable_pick` devuelva verdadero.

**Bloqueos reversibles por accidente.** Un pick bloqueado por reglas puede recuperar `is_publishable=True` porque la función de publicación no conserva todos los bloqueos.

**Reglas estadísticas inactivas.** Las cuatro reglas de `data/pick_rules.json` tienen `enabled: false`.

**Exposición excesiva.** La configuración permite hasta 5 picks y 10 unidades por evento, por encima de los defaults conservadores del motor. Una lista fija de familias exclusivas no sustituye una medición de covarianza.

### Entrenamiento y calibración

**Pipeline roto.** `src/core/train_model_retrospective.py:282-296` llama a `POST /api/v1/ml/train`, pero esa ruta no existe.

**Componentes retirados.** Solo quedan bytecodes de `calibration.py`, `glm_model.py` y `stacking_engine.py`; no están sus fuentes. El modelo actual no puede auditarse ni mantenerse desde esos artefactos.

**Calibración inexistente.** `apply_calibration` retorna `raw_prob`. Los ajustes por edge son hardcodes dependientes de cuota, no calibración probabilística.

**Dataset inadecuado para decisión económica.** El pipeline descarta partidos con cuotas y no conserva snapshot de probabilidad, mercado, book, cuota ejecutable, versión de modelo ni decisión. Así no puede medir CLV, ROI OOS ni calibrar la política real.

### Watson, API y persistencia

**Watson no inicia.** `watson/background.js:512-522` deja un bloque sin cerrar; `node --check` termina con `Unexpected end of input`.

**BetPlay bloqueado por permisos.** El dominio Kambi utilizado no está en `host_permissions`.

**API sin control de acceso.** `src/ui/api/main.py:63-69` configura CORS abierto y no hay autenticación en operaciones de escritura, reglas, resultados y borrado.

**Buzón global de prefill.** Estadísticas, cuotas y estado de ventana usan variables globales sin usuario, evento, TTL ni transacción. Pueden mezclarse entre partidos, pestañas, usuarios o workers.

**Matching de resultados inseguro.** El fallback usa substring, nombres parciales y ventana temporal; puede escoger el primer candidato ambiguo y alterar ROI del partido equivocado.

**XSS.** El editor de reglas y otros componentes insertan valores externos mediante `innerHTML` y handlers inline.

**Frontend roto.** `comparator.js` llama a `renderLineShoppingPanel`, que no existe, y espera campos que el backend no devuelve.

## Fallas altas y deuda estructural

- **Datos faltantes:** varios schemas convierten ausencia en valores plausibles, por ejemplo partidos=1, xG=1,5 o corners=4,5. El sistema no distingue observado, imputado y prior.
- **Tiros a puerta:** el ajuste reciente usa la clave de tiros totales, sesgando SOT al alza.
- **Doble oportunidad:** no siempre equivale a la suma de las probabilidades 1X2 mostradas.
- **Dixon-Coles:** existe ajuste de `rho`, pero el flujo no lo usa; se aplica una heurística.
- **Matriz truncada:** el score se corta y renormaliza, reasignando masa de cola.
- **Complementos imposibles:** algunos soportes usan `110 - probabilidad` en lugar de 100.
- **LRS sin muestra:** una liga sin histórico puede recibir confianza cercana a máxima por tener valores plausibles.
- **Convención de tarjetas:** modelado y liquidación no fijan si una roja vale 1, 2 o puntos de tarjeta.
- **Estimadores con denominador incorrecto:** medias de liga comparten un contador aunque cada métrica tenga distinta cobertura.
- **Migraciones desalineadas:** `picks_hits_summary` está en migración pero no en ORM; `has_real_stats` está en ORM pero no en migraciones históricas.
- **`has_odds`:** análisis nuevos pueden conservar `False` y quedar fuera del recálculo.
- **Loader manual abstracto:** no implementa todos los métodos obligatorios.
- **Ruta duplicada:** existen dos `GET /api/v1/competitions`.
- **Excel:** campos controlables pueden producir inyección de fórmulas.
- **Concurrencia:** SQLite, trabajo pesado síncrono y sesiones no cerradas no soportan una operación multiworker segura.
- **Monolitos:** `main.py` tiene 4.887 líneas y `compare.py` 3.908; mezclan HTTP, negocio, SQL, reporting y modelos.
- **Archivos generados:** se versionan `__pycache__` y `.pyc`, pero faltan dependencias, tests y documentación de arranque.

## Arquitectura objetivo

La separación mínima recomendada es:

```text
src/
  domain/
    markets.py
    settlement.py
    probability.py
    eligibility.py
    portfolio.py
  models/
    goals_dixon_coles.py
    count_negative_binomial.py
    calibration.py
  application/
    analyze_match.py
    settle_prediction.py
    evaluate_policy.py
  infrastructure/
    repositories/
    providers/
    jobs/
  api/
    routers/
    schemas/
  web/
tests/
  unit/
  integration/
  regression/
```

Principios:

- una sola función de liquidación para vivo, backtest, ROI y reportes;
- una sola decisión de elegibilidad, con razones inmutables;
- modelos probabilísticos separados de reglas de publicación y stake;
- snapshots prepartido append-only;
- IDs estables para proveedor, competición, temporada, equipo y evento;
- configuración y modelos versionados;
- evaluación temporal reproducible;
- fallar cerrado ante fecha, mercado o convención de liquidación desconocida.

## Plan priorizado

### Ahora: congelar y reparar integridad

Objetivo: que el mismo input produzca el mismo output y que cada retorno sea correcto.

1. Desactivar staking/publicación automática; usar Sherlock solo en paper trading.
2. Corregir el error de sintaxis de Watson y añadir `node --check` en CI.
3. Crear `settlement.py` con retornos `win`, `loss`, `push`, `half_win`, `half_loss`.
4. Reescribir EV y Kelly para consumir esa distribución de retornos.
5. Sustituir Monte Carlo NB por PMF/convolución determinista con cola controlada.
6. Hacer irreversible el bloqueo de un pick y centralizar `EligibilityDecision`.
7. Exigir cutoff UTC, IDs y filtros de liga/temporada/calidad en todo histórico.
8. No liquidar mercados si falta la estadística necesaria.
9. Bajar temporalmente la exposición a máximo 1 pick y 1 unidad por evento.
10. Añadir tests unitarios de invariantes antes de reactivar cualquier publicación.

Criterios de salida:

- 100% de tests de settlement para líneas x.0, x.25, x.5 y x.75;
- mismos inputs producen JSON idéntico en ejecuciones repetidas;
- ningún registro con fecha \(\ge\) kickoff entra en features;
- ningún pick bloqueado aparece publicable;
- datos faltantes producen `unsettled`, nunca un cero inventado.

### Siguiente: asegurar datos, API y reproducibilidad

Objetivo: poder arrancar, operar y auditar un clon limpio.

1. Añadir `pyproject.toml`, lockfile, versión de Python, comandos de desarrollo y CI.
2. Crear migraciones Alembic y alinear ORM/esquema.
3. Añadir autenticación, autorización, CORS restringido y auditoría de mutaciones.
4. Reemplazar globals de prefill por almacenamiento correlacionado con TTL.
5. Requerir `provider + external_event_id` para resultados; ambigüedad va a revisión.
6. Definir schemas Pydantic estrictos y contrato JSON compartido con Watson.
7. Corregir permisos BetPlay, URL/auth unificada y errores visibles por proveedor.
8. Escapar contenido web, eliminar handlers inline y neutralizar fórmulas Excel.
9. Extraer routers, servicios y repositories desde los monolitos.
10. Mover recálculos y reportes a jobs idempotentes.

Criterios de salida:

- un clon limpio instala, migra, importa y arranca en CI;
- ninguna mutación funciona sin credencial y permiso;
- dos eventos simultáneos no pueden cruzar stats/cuotas;
- ningún resultado se aplica sin match único;
- smoke test Watson → API → análisis funciona para SofaScore, Betano y BetPlay.

### Después: construir validación estadística honesta

Objetivo: saber si existe edge fuera de muestra.

1. Persistir snapshot inmutable antes del kickoff:
   - inputs y cobertura;
   - fuente y timestamps;
   - cuotas por book;
   - probabilidad raw y calibrada;
   - versión de modelo, reglas y configuración;
   - decisión, razones y stake;
   - cuota realmente tomada.
2. Separar tres capas:
   - modelo del evento;
   - calibración probabilística;
   - política de value/stake.
3. Implementar walk-forward por liga, temporada y familia de mercado.
4. Mantener un holdout final bloqueado que nunca participe en ajustes.
5. Medir Brier, log loss, ECE, reliability, CLV, yield, ROI, max drawdown e intervalos bootstrap por partido.
6. Calibrar out-of-fold solo con muestra suficiente; usar priors jerárquicos para segmentos pequeños.
7. Estimar correlación de retornos y riesgo por evento/día/liga.
8. Ejecutar paper trading prospectivo de al menos 100-150 picks, sin cambiar reglas durante la ventana.

Criterios de salida:

- calibración y métricas calculadas únicamente sobre predicciones congeladas;
- intervalos reportados por partido, no tratando picks correlacionados como independientes;
- CLV positivo y estable;
- ROI OOS con intervalo y drawdown aceptables;
- resultados reproducibles por versión de dataset/modelo/política.

### Más adelante: mejorar modelos

Solo después de demostrar integridad:

1. Ajustar `rho` Dixon-Coles por liga/temporada con corte temporal.
2. Evaluar decay temporal, ventaja local dinámica y cambios de entrenador/plantilla.
3. Estimar NB por mercado y liga con dispersión coherente.
4. Comparar baseline simple contra GLM/GBM, siempre con walk-forward.
5. Incorporar alineaciones, lesiones y contexto solo si mejoran OOS.
6. Diseñar modelo conjunto o cópula/Monte Carlo correlacionado para cartera, no para ocultar fallas de liquidación.

Regla de promoción: un modelo nuevo solo reemplaza al baseline si mejora calibración y valor económico OOS sin degradar estabilidad.

## Backlog priorizado

| Prioridad | Iniciativa | Valor | Esfuerzo | Dependencia |
|---|---|---:|---:|---|
| P0 | Motor único de settlement asiático | Muy alto | Medio | Ninguna |
| P0 | EV/Kelly por distribución de retornos | Muy alto | Medio | Settlement |
| P0 | Cutoff temporal e IDs estables | Muy alto | Medio | Esquema |
| P0 | Elegibilidad inmutable | Muy alto | Medio | Settlement |
| P0 | Reparar Watson y smoke test | Alto | Bajo | Ninguna |
| P0 | Dependencias, CI y tests | Muy alto | Medio | Ninguna |
| P1 | Snapshots prepartido append-only | Muy alto | Alto | Migraciones |
| P1 | Auth y correlación de prefill | Alto | Alto | Contratos |
| P1 | Matching exacto de resultados | Muy alto | Medio | IDs externos |
| P1 | Walk-forward y holdout | Muy alto | Alto | Snapshots |
| P1 | Calibración OOF | Alto | Medio | Walk-forward |
| P1 | CLV y line shopping persistente | Alto | Medio | Snapshots/cuotas |
| P2 | Refactor de monolitos | Medio | Alto | Tests |
| P2 | PostgreSQL y jobs | Medio | Alto | Repositories |
| P2 | Modelo de correlación | Alto | Alto | Retornos OOS |
| P3 | Nuevas features/modelos | Incierto | Alto | Todo lo anterior |

## Suite mínima de pruebas

### Settlement

- Over/Under 2.0 con win, push y loss.
- Over/Under 2.25 y 2.75 con half-win/half-loss.
- Handicap asiático positivo y negativo.
- Convención de tarjetas explícita.
- Campos faltantes devuelven `unsettled`.
- Invariante: suma de probabilidades de estados = 1.
- Invariante: EV por suma de retornos coincide con enumeración manual.

### Modelos

- PMF suma 1 dentro de tolerancia.
- Masa de cola menor al umbral.
- 1X2 suma 1.
- DC coincide con 1X2 final.
- Mismo input/versión produce mismo output.
- Cambiar tiros totales no altera SOT si SOT no cambia.

### Histórico

- Se excluye el mismo partido y cualquier fecha posterior.
- Se excluyen otras ligas, temporadas y deportes.
- Nombres similares no se mezclan.
- Missing no se cuenta como cero.
- Política histórica no cambia al editar reglas actuales.

### API y Watson

- Import y startup en entorno limpio.
- Auth en cada endpoint mutable.
- Dos prefills concurrentes no se cruzan.
- Resultado ambiguo no actualiza nada.
- Contrato OpenAPI coincide con payload de Watson.
- Parser fixtures por proveedor.
- XSS y formula injection neutralizados.

## Métricas de control

### Integridad

- porcentaje de predicciones con snapshot completo;
- porcentaje de resultados asociados por ID exacto;
- porcentaje de picks `unsettled` por datos faltantes;
- tasa de fallbacks/imputaciones por mercado;
- reproducibilidad hash input → output.

### Calidad probabilística

- Brier y log loss;
- ECE y curva reliability;
- error por banda de probabilidad;
- calibración por mercado, liga y rango de cuota;
- cobertura de intervalos predictivos.

### Valor económico

- CLV mediano y promedio;
- yield/ROI flat y por stake;
- max drawdown;
- turnover;
- retorno y riesgo agregados por partido;
- intervalo bootstrap por partido;
- desempeño por versión de política.

### Operación

- éxito de extracción por proveedor;
- latencia y errores por endpoint/job;
- eventos ambiguos pendientes;
- antigüedad de datos;
- discrepancias frontend/backend;
- cantidad de reglas/modelos activos sin evaluación vigente.

## Decisión recomendada

Sherlock debe entrar en una fase de **estabilización y paper trading**, no de expansión. El orden es:

1. corregir settlement, EV, Kelly, determinismo y elegibilidad;
2. asegurar cutoff, snapshots, IDs y liquidación;
3. hacer reproducible y segura la plataforma;
4. validar prospectivamente fuera de muestra;
5. solo entonces optimizar modelos y ampliar mercados.

El éxito inmediato no debe medirse por ROI histórico recalculado, sino por cinco invariantes: retorno correcto, ausencia de leakage, decisión inmutable, ejecución reproducible y trazabilidad completa.

## Limitaciones de esta auditoría

La revisión fue principalmente estática. Los módulos Python compilan, pero la aplicación no pudo importarse porque el repositorio no declara ni instala `sqlalchemy` y `pydantic_settings`. El notebook conserva salidas previas, pero no el dataset usado; la base `data/sherlock.db` fue eliminada del commit actual. Por ello no se recalculó el backtest ni se cuantificó el efecto económico de cada defecto. Las fallas señaladas en liquidación, rutas, flags, sintaxis y flujo se derivan directamente del código y deben resolverse independientemente de la magnitud histórica observada.
