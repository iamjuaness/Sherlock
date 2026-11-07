# DIRECTIVA DE EJECUCIÓN TÉCNICA: SHERLOCK & WATSON INTEGRATION

> **Directivas de Operación del Agente:**
>
> - **Skills de NotebookLM / Pensamiento Profundo:** Razona internamente la arquitectura antes de tocar código. Evita verbosidad, divagaciones y consumo innecesario de tokens.
> - **Skill Caveman:** Comunicación directa, concisa y sin relleno. Cero texto superficial.
> - **Skill Ponytail:** Precisión de ingeniería, cambios limpios, código modular y tipado estricto.
> - **Regla de Entrega:** Siempre devolver el código completo de la función a reemplazar y detallar exactamente los archivos y líneas donde se invoca.

---

## 1. Contexto y Diagnóstico

1. **Discrepancia en Matching de Nombres (Betano vs Betplay vs SofaScore):**
   - Nombres multi-idioma (ej. `Niza` en español vs `Nice` en Betano/Kambi, `Bayern Múnich` vs `Bayern München`, `Sporting Lisboa` vs `Sporting CP`).
   - El sistema actual solo usa `normalizeTeamName()`. Al fallar las palabras clave base, una casa descarta el partido y la otra sí lo encuentra.
2. **Fecha de Partido en UI:**
   - La sección de _"Datos cargados Automáticamente"_ en el dashboard no muestra la fecha/hora del encuentro (`startTimestamp`).
3. **Flujo Batch One-Click (Watson + Sherlock):**
   - No existe procesamiento masivo automático de una jornada completa hacia el comparador.
4. **Reporte de Auditoría de Temporada (SofaScore vs DB):**
   - Al sincronizar partidos históricos vía `/events/last/{page}`, no hay conciliación que alerte sobre partidos faltantes o sobrantes.
5. **Fallo HTTP 400 en `POST /api/v1/analysis`:**
   - La carga útil enviada desde Watson o el frontend tiene campos nulos o con nombres no conformes con el esquema Pydantic de Sherlock.

---

## 2. Plan de Implementación por Módulos

### Fase 1: Diccionario de Alias y Normalización Multilingüe

**Archivos objetivo:** `watson/betanoOdds.js`, `watson/betplayOdds.js`

- **Objetivo:** Resolver discrepancias de nombres entre idiomas y abreviaturas sin perder partidos en Betano o BetPlay.
- **Acciones:**
  1. Crear un mapa global `TEAM_ALIASES` en memoria para equivalencias conocidas de clubes y traducciones comunes (ej. `niza: ["nice"]`, `munich: ["munchen", "muenchen"]`, `sevilla: ["seville"]`, `inter: ["internazionale"]`, `sporting lisboa: ["sporting cp", "sporting portugal"]`).
  2. Extender `getNameVariants(teamOrName)`:
     - Extraer `teamOrName.name`, `teamOrName.shortName`, y el `slug` del equipo (ej. de `deportivo-pereira-boyaca-chico-fc` o `team.slug`).
     - Si alguna palabra coincide con `TEAM_ALIASES`, inyectar automáticamente sus variantes alternativas al array de búsqueda.
  3. En `pickBestBetanoEvent` y `pickBestKambiEvent`:
     - Mantener el requisito estricto de `homeHit && awayHit`.
     - Comparar palabras clave expandidas mediante los alias para validar partidos en ambas casas de apuestas.

---

### Fase 2: Visualización de Fecha en UI de Datos Automáticos

**Archivos objetivo:** `watson/popup.html`, `watson/popup.js`, frontend de Sherlock (`dashboard.html` / `comparator.js`)

- **Objetivo:** Mostrar la fecha y hora legible del partido cargado.
- **Acciones:**
  1. En `sofaScoreToSherlock.js`: Extraer `startTimestamp` del evento de SofaScore e incluir en el payload `match_date: new Date(startTimestamp * 1000).toLocaleString()`.
  2. En el panel de "Datos cargados Automáticamente" de la UI:
     - Añadir un elemento badge/label visible: `<span id="prefill-match-date" class="badge">Fecha: --</span>`.
     - Vincular el valor en `populateAppForm()` para renderizar la fecha formateada (`DD/MM/YYYY HH:mm`).

---

### Fase 3: Pipeline Batch "One-Click" (Watson & Sherlock Backend)

**Archivos objetivo:** `src/ui/api/main.py`, `src/ui/api/compare.py`, `watson/background.js`, `watson/popup.js`

#### A. Backend Sherlock: `POST /api/v1/compare/batch`

1. Crear el endpoint en `src/ui/api/main.py`:
   - Entrada: `payload: List[FootballCompareRequest]`.
   - Lógica:
     - Iterar cada partido procesando `compare_teams_football(req)`.
     - Guardar automáticamente en SQLite (`analysis_history`) cada resultado con EV positivo y métricas calculadas.
   - Respuesta: JSON con total procesados, lista de picks con valor y conteo de fallos.

#### B. Extensión Watson: Botón "Analizar Jornada Próxima"

1. En `popup.html`: Crear botón `#btnBulkAnalyzeDay` ("Analizar Jornada Próxima").
2. En `background.js`:
   - Al pulsar el botón, consultar la cartelera de eventos del día vía SofaScore API.
   - Iterar los partidos extrayendo estadísticas + cuotas en paralelo (`fetchAllBookmakerOdds`).
   - Ensamblar el array de `FootballCompareRequest` y despacharlo en un único POST a `/api/v1/compare/batch`.
   - Al finalizar, disparar notificación o redirigir automáticamente al dashboard (`/main-dashboard`).

---

### Fase 4: Conciliación y Reporte de Temporada (SofaScore vs DB)

**Archivos objetivo:** `watson/background.js` (en `handleExtractHistoricalData`), script de auditoría en `src/`

- **Objetivo:** Auditar la completitud de partidos por temporada y detectar omisiones o duplicados.
- **Acciones:**
  1. Durante la paginación (`/unique-tournament/{tId}/season/{sId}/events/last/{page}`), acumular el conjunto de `event.id` de SofaScore.
  2. Consultar a la base de datos de Sherlock (`AnalysisHistory` o tabla de resultados) todos los `event_id` registrados para esa temporada.
  3. Generar un objeto de reporte estructurado:
     ```json
     {
       "season_id": 88503,
       "total_sofascore": 180,
       "total_db": 178,
       "missing_in_db": [1027911635, 1027911640],
       "extra_in_db": []
     }
     ```
  4. Imprimir el resumen en logs y guardar el reporte en `data/audit_season_{sId}.json`.

---

### Fase 5: Corrección del Error 400 en `POST /api/v1/analysis`

**Archivos objetivo:** `watson/background.js` (en `handleExtractResults`), `src/ui/api/main.py`

- **Objetivo:** Eliminar el Bad Request 400.
- **Acciones:**
  1. Revisar el esquema Pydantic en `src/ui/api/` para `POST /api/v1/analysis` y `POST /api/v1/result`.
  2. Verificar campos obligatorios que SofaScore pueda omitir (ej. `event_id`, tipos numéricos en vez de cadenas, o ausencia de `competition`).
  3. Asegurar que `handleExtractResults` valide y castee todos los campos antes del envío (`normaltime` a enteros, `home_team` y `away_team` como strings no vacíos).
  4. Manejar un mejor log de error para saber a que se debe el error.
