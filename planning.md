## 1. Datos e ingesta (Watson)

| #   | Problema                                                                              | Corregir                                                      |
| --- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| 1   | xG casero con categorías solapadas y coeficientes fijos                               | Usar xG real por partido o ajustar coeficientes con regresión |
| 2   | `expectedGoals` se promedia al fusionar periodos (queda a la mitad)                   | Sumarlo, no promediarlo                                       |
| 3   | Dato ausente = 0 y defaults del modelo (xg 1.5, corners 4.5, posesión 50, rating 6.5) | Usar `null` y bandera de dato ausente                         |
| 4   | xG imputado desde goles cuenta como real en la calidad de datos                       | Separar xG real de imputado                                   |
| 5   | Sin standings inventa 50/25/25; `matches=0` se vuelve 1                               | Marcar "sin datos" y no calcular                              |
| 6   | Totales enviados como "por juego" (`shots_inside_box`, `big_chances_created`, etc.)   | Convertir a por partido en el mapeador                        |
| 7   | `matches_home/away` aproximados; vallas invictas en un solo lado                      | Tomarlos de standings por localía                             |
| 8   | Estadísticas solo `overall`, sin localía, rival ni decaimiento                        | Calcular desde partidos individuales                          |
| 9   | `league_stats` incompleto (corners, tiros, faltas, 1X2) y localía por victorias       | Calcular promedios de liga desde tu base; localía por goles   |
| 10  | Liga identificada solo por nombre                                                     | Enviar IDs de torneo, temporada y país                        |
| 11  | Sin `extractedAt` ni `match_date` UTC; temporada "25/26"                              | Enviar ambos y normalizar la temporada                        |
| 12  | Alineaciones y rachas se descargan y se descartan                                     | Enviarlas y usarlas, o desactivar la descarga                 |
| 13  | Guarda de "sin datos" depende de valores falsos (50 y 6.5)                            | Campo explícito `has_stats` por equipo                        |
| 14  | Resultados: `normaltime \|\| 0` sin estado del evento; rojas sin doble amarilla       | Validar que el evento terminó y contar `yellowRed`            |
| 15  | `/result` empareja por prefijo de 5 letras y descarta fuera de ventana                | Emparejar por `eventId`                                       |
| 16  | Line shopping mezcla reglas de liquidación distintas                                  | Comparar solo mercados equivalentes                           |
| 17  | Líneas de cuota por defecto                                                           | Usar las líneas reales de la casa                             |

## 2. Modelo

| #   | Problema                                                                                      | Corregir                                                     |
| --- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 18  | Sin localía en el lambda general; parche 70/30 con % de liga por defecto                      | Añadir factor local por liga y quitar el parche              |
| 19  | 1X2, doble oportunidad y BTTS usan la matriz DC; Over/Under de goles un Poisson independiente | Derivar todo de la misma matriz                              |
| 20  | xG como prior de fuerza fija (β≈5) y doble shrinkage                                          | Ponderar goles y xG por varianza y aplicar un solo shrinkage |
| 21  | `recent_form` no existe: el ajuste por forma nunca se aplica                                  | Definir el campo o eliminar el código                        |
| 22  | rho de Dixon-Coles heurístico; no hay ajuste por rival ni tiempo                              | Ajustar rho y fuerzas con verosimilitud conjunta             |
| 23  | Dispersión de conteos casi Poisson (`var/4` y piso)                                           | Varianza = Fano × media por equipo                           |
| 24  | Equipos de conteo independientes                                                              | Modelar correlación entre local y visitante                  |
| 25  | `_estimate_league_variance` consulta tablas legacy                                            | Estimar desde `AnalysisHistory`                              |
| 26  | Sesgos en corners (Under bajo y Over alto)                                                    | Revisar el nivel (media) de los lambdas por liga             |
| 27  | Faltas, offsides y tarjetas con constantes y doble shrinkage                                  | Reemplazar por estimación con datos                          |
| 28  | Conteos simétricos local/visitante                                                            | Aplicar factores de liga por métrica                         |
| 29  | Módulos legacy (`math_engine`, `count_models`) con fallbacks y subcadenas                     | Consolidar o eliminar                                        |
| 30  | Optimizador de parámetros no evalúa el modelo real                                            | Evaluar el modelo completo con rolling origin                |

## 3. Calibración y taxonomía

| #   | Problema                                                                                   | Corregir                                                          |
| --- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| 31  | Claves distintas en entrenamiento y ejecución (`home_draw` vs `1x`, `core_2_5` vs `"2.5"`) | Usar las funciones de la taxonomía en ambos                       |
| 32  | "Tiros a Pta" cae en `shots`; "Over 12.5 Corners" cae en doble oportunidad                 | Añadir "pta" y evaluar corners antes que doble oportunidad        |
| 33  | Líneas de cuarto sin bucket; "-" y "+" como lado                                           | Ampliar buckets y exigir "over/under" explícito                   |
| 34  | Probabilidades calibradas por lado no suman 1                                              | Renormalizar o derivar el lado contrario                          |
| 35  | 798 segmentos, ~16 picks/partido, bins de 8 a 10                                           | Ponderar por partido y reducir segmentos                          |
| 36  | Solo ~5% de filas con resultado tiene picks                                                | Recalcular probabilidades retrospectivas                          |
| 37  | Validación con otra configuración y claves distintas                                       | Validar el mismo artefacto y camino de inferencia                 |
| 38  | Compuerta agregada, sin poda, intervalo ni comparación con el vigente                      | Podar por segmento, bootstrap por partido, comparar con el activo |
| 39  | `force` escribe directo en `active.json`; escritura no atómica                             | Escribir a ruta candidata y renombrar                             |
| 40  | Versiones del modelo mezcladas                                                             | Guardar `model_version` y entrenar con la vigente                 |
| 41  | Evalúa todo el universo                                                                    | Evaluar en la región de decisión                                  |

## 4. Valor, filtros, riesgo y correlación

| #   | Problema                                                                                             | Corregir                                                                                                                                                                                                                                                        |
| --- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 42  | Tres probabilidades distintas (cruda, calibrada, final)                                              | Una sola para EV, edge, Kelly y elegibilidad                                                                                                                                                                                                                    |
| 43  | Mezcla con el mercado fija 80/20; módulo de fiabilidad sin usar                                      | Usar el módulo o calibrar el peso                                                                                                                                                                                                                               |
| 44  | No-vig de doble oportunidad mal calculado; proporcional                                              | Normalizar por mercado; método de potencia                                                                                                                                                                                                                      |
| 45  | Hueco entre probabilidad mínima y tope de edge                                                       | Rediseñar los umbrales juntos                                                                                                                                                                                                                                   |
| 46  | Bloqueo por H2H con una sola muestra                                                                 | Exigir n ≥ 8 o usar solo el shrinkage                                                                                                                                                                                                                           |
| 47  | Unidades de probabilidad mezcladas (% y fracción)                                                    | Una sola unidad en todo el pipeline                                                                                                                                                                                                                             |
| 48  | Soportes "110 −" y `_team_strength_score` con totales                                                | Usar probabilidades del modelo                                                                                                                                                                                                                                  |
| 49  | Cuatro puntajes superpuestos y gates fijos                                                           | Unificar en uno                                                                                                                                                                                                                                                 |
| 50  | Veto por hit rate con 5–10 partidos y "temporada" = año calendario                                   | Quitar el veto o exigir muestra y temporada real                                                                                                                                                                                                                |
| 51  | Línea de mejor EV (maldición del ganador)                                                            | Descontar incertidumbre al elegir                                                                                                                                                                                                                               |
| 52  | Incertidumbre contada varias veces en el stake; piso de 1u                                           | Aplicarla una sola vez                                                                                                                                                                                                                                          |
| 53  | LRS y Kelly con 5 picks o ROI de 60; acierto sin ajustar por cuota                                   | Mínimos de muestra y comparar con la cuota                                                                                                                                                                                                                      |
| 54  | `risk.py` no carga el JSON (TypeError tragado); tres sistemas de stake y tres Kelly                  | Arreglar el constructor y dejar uno solo                                                                                                                                                                                                                        |
| 55  | `max_picks_per_match` y `max_total_stake` sin aplicar                                                | Eliminarlos por completo, para limitar esto se usa la correlacion entre picks.                                                                                                                                                                                  |
| 56  | Gobernanza con umbrales dentro del ruido; CLV nunca disponible                                       | Usar CLV y mínimos de muestra reales                                                                                                                                                                                                                            |
| 57  | Multiplicadores de gobernanza distintos entre módulos; `min_edge_add` sin aplicar                    | Unificar tabla                                                                                                                                                                                                                                                  |
| 58  | Correlación con valor absoluto; recorte fijo ×0.25; orden voraz                                      | Usar signo, ajuste proporcional y orden por EV                                                                                                                                                                                                                  |
| 59  | Matriz de correlación global, sin líneas, estática, con identidades lógicas                          | Calcular desde la matriz de marcadores y por línea                                                                                                                                                                                                              |
| 60  | Pares `shotstarget_*` inalcanzables; faltas/offsides sin cobertura                                   | Arreglar clasificación y añadir familias                                                                                                                                                                                                                        |
| 61  | Umbrales 0.3/0.2 por defecto; los sugeridos nunca se leen                                            | Decidir y leer de un solo lugar                                                                                                                                                                                                                                 |
| 62  | Motor de reglas: error deja pasar el pick; clave desconocida bloquea todo; `NameError` en modo lista | Fallar cerrado, validar claves, importar bien                                                                                                                                                                                                                   |
| 63  | Sofascore no manda promedio de corners en la liga                                                    | Para solucionar esto debemos calcular el promedio de corners de la liga con los datos que hay en la BD, por temporada para validar los calculos para un partido de Liga MX, Apertura para un partido que se vaya a jugar hoy el promedio de corners es de 10.94 |

## 5. Liquidación, recálculo y operación

| #   | Problema                                                                  | Corregir                                                                       |
| --- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| 64  | Tres copias de la liquidación; tarjetas ausentes = 0                      | Usar solo `settlement.py` (fail-closed)                                        |
| 65  | Convención de tarjetas inconsistente (roja ×2 vs ×1)                      | Una convención explícita                                                       |
| 66  | Half-win vale 0.5 en calibración y 1.0 en estadísticas                    | Unificar                                                                       |
| 67  | `calculate_pick_profit` con `stake` y firma de 2 argumentos               | Corregir la firma o la llamada                                                 |
| 68  | Recálculo paralelo y secuencial difieren; reglas sin cuotas; posible fuga | Un solo camino con corte temporal                                              |
| 69  | CLV (cuotas de cierre) sin usar como validación                           | Registrarlo y medir con él                                                     |
| 70  | CORS abierto, borrado sin autenticación, ruta duplicada, estado global    | Autenticación, orígenes y rutas únicas                                         |
| 71  | Dos clasificaciones de familia por pick                                   | Una sola (la taxonomía)                                                        |
| 72  | `max_picks_per_match` y `max_total_stake` aplicados                       | Eliminarlos por completo, para limitar esto se usa la correlacion entre picks. |
