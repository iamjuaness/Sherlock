Perfecto, entonces el foco inicial será:

- Deportes: **fútbol**, **NBA** y **tenis** (ligas que permita cada API). [api-football](https://www.api-football.com/coverage)
- Análisis: mercados de apuestas (over/under, moneyline, hándicaps) + rendimiento de equipos/jugadores.

A continuación te dejo la planificación ya adaptada para que la puedas pegar casi tal cual en tu `.md` raíz y usarla como guía para el agente de programación.

---

## 1. Objetivo del proyecto

Construir una plataforma de **análisis deportivo multi‑deporte** centrada en:

- Fútbol (ligas de API‑Football / TheSportsDB).
- NBA (BallDontLie u otra API gratuita similar). [mcpmarket](https://mcpmarket.com/es/server/balldontlie-sports)
- Tenis (principalmente con APIs gratuitas tipo TheSportsDB; proveedores premium como LSports/SportsDataIO pueden quedar documentados como futuros upgrades). [developer.sportradar](https://developer.sportradar.com/tennis/docs/ig-data-coverage-tiers)

El foco principal:

- Mercados de apuestas:
  - Over/Under totales, resultado ML (moneyline), hándicaps, etc.
- Análisis de rendimiento de equipos y jugadores.
- Agentes de IA (Nemotron vía OpenRouter) para análisis natural‑language y ayuda en modelado. [openrouter](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free)

No es obligatorio que sea comercial, pero el diseño debe ser lo más limpio y extensible posible.

---

## 2. Alcance inicial (v1)

### Deportes y competiciones

- Fútbol:
  - Usar API‑Football (API‑Sports) para ligas principales (Premier, LaLiga, Serie A, UCL, etc.). [api-football](https://www.api-football.com)
  - Fallback con TheSportsDB donde sea útil (IDs, artwork, algunas ligas extra). [thesportsdb](https://www.thesportsdb.com/sport/leagues)
- NBA:
  - Usar BallDontLie API (gratuita) para partidos, equipos y stats de jugadores. [youtube](https://www.youtube.com/watch?v=kglgtu9uAQM)
- Tenis:
  - Usar TheSportsDB para torneos WTA/ATP básicos (resultados, eventos simples). [thesportsdb](https://www.thesportsdb.com)
  - Documentar en `TENIS_FUTURO.md` posibles integraciones con APIs premium (Sportradar, LSports, SportsDataIO) para cuando haya presupuesto. [lsports](https://www.lsports.eu/tennis-data-api/)

### Tipos de análisis

Para cada deporte, priorizar:

- Mercados:
  - Over/Under de goles/puntos/games/sets (según deporte).
  - Moneyline (ganador del partido).
  - Hándicaps (spread en basket, hándicap de goles/games).
- Métricas:
  - Nivel equipo/jugador (ELO/rating similar).
  - Tendencias de anotación (media, varianza, distribución de goles/puntos).
  - Relación entre rendimiento “real” y líneas de mercado.

---

## 3. Fuentes de datos (gratuitas y legales)

### Fútbol

- **API‑Football (API‑Sports)**
  - Cubre +1200 ligas y copas con livescore, standings, estadísticas y odds en algunos planes. [api-sports](https://api-sports.io/sports/football)
  - Usar el plan gratuito para ligas principales y tests.

- **TheSportsDB**
  - Base de datos crowdsourced con resultados, TV listings, artwork y API JSON gratuita. [thesportsdb](https://www.thesportsdb.com/browse_tv)

### NBA

- **BallDontLie API**
  - API gratuita para datos de NBA: partidos, equipos, stats de jugadores. [youtube](https://www.youtube.com/watch?v=YzZGKhBdBWA)

### Tenis

- **TheSportsDB (básico)**: torneos y resultados para WTA/ATP. [thesportsdb](https://www.thesportsdb.com/sport/leagues)
- APIs premium para futura integración (solo documentar por ahora): Sportradar Tennis, LSports Tennis, SportsDataIO Tennis. [sportsdata](https://sportsdata.io/developers/coverages/tennis)

### Carga manual

Siempre debe existir un camino de **carga manual** (CSV/Excel) para:

- Partidos (fecha, competición, participantes, resultado, cuotas si se tienen, estadística básica).
- Eventos relevantes (goles/points/sets, etc.), si se requiere mayor granularidad.

Estos archivos manuales deben mapearse al mismo modelo de dominio que las APIs.

---

## 4. Modelo de dominio

Definir un modelo de dominio común que soporte fútbol, NBA y tenis.

Entidades principales:

- `Sport` (football, basketball, tennis).
- `Competition` (liga, torneo).
- `Team` / `Player` (en tenis, `Player` puede representar al competidor principal).
- `Match` / `Game` / `Fixture`.
- `BettingLine` (mercado, tipo, línea, cuota, libro, timestamp).
- `StatLineTeam` / `StatLinePlayer` (stats agregadas de partido).

Reglas:

- Cada proveedor (API‑Football, TheSportsDB, BallDontLie, CSV manual) se mapea a estas entidades.
- No se debe usar directamente el formato de las APIs en el resto del sistema.

---

## 5. Arquitectura del software

Estructura de carpetas recomendada:

- `datasources/`
  - `football_api_football.py`
  - `football_thesportsdb.py`
  - `nba_balldontlie.py`
  - `tennis_thesportsdb.py`
  - `manual_loader.py`
- `core/`
  - `domain.py` (clases/DTOs del modelo de dominio).
  - `features.py` (ingeniería de features por deporte/mercado).
  - `models_odds.py` (modelos de over/under, ML, hándicap).
  - `ratings.py` (ELO y ratings similares).
- `agents/`
  - `nemotron_client.py` (cliente OpenRouter).
  - `data_agent.py` (ETL/limpieza).
  - `modeling_agent.py` (features/modelos).
  - `user_analyst_agent.py` (Q&A de usuario).
- `ui/`
  - `api/` (FastAPI/Node).
  - `web/` (React/Next).
  - `cli/` (Typer/Click).
- `data/`
  - `raw/`, `processed/`, `manual/`.
- `docs/`
  - `PLAN.md` (este documento).
  - `APIS.md`, `MODELS.md`, `AGENTS.md`, `TENIS_FUTURO.md`.
- `notebooks/`
  - Prototipos y exploración.

---

## 6. Modelos y métricas por deporte

### 6.1. Fútbol

Objetivo: modelos para mercados de partido (over/under, ML, hándicap).

- **Modelos de goles**:
  - Poisson o bivariado para goles local/visitante, con inputs como fuerza ofensiva/defensiva, localía, forma reciente. [opensource.pysport](https://opensource.pysport.org)
  - De ese modelo se deriva la distribución de goles totales para over/under y prob. de resultado (1X2/ML).

- **Ratings de equipos**:
  - ELO basado en resultado y diferencia de goles.
  - Usar ELO como feature clave para modelos de odds.

- **Métricas de rendimiento**:
  - Goles a favor/en contra, media de goles por partido, distribución de goles, rachas.

Si más adelante tienes datos de tiros, se integran modelos de xG, pero el v1 puede trabajar sin xG detallado.

### 6.2. NBA

Objetivo: modelos para puntos totales (over/under), ML y spread.

- **Modelo de puntos de equipo**:
  - Modelo de regresión para puntos de cada equipo (Poisson/NegBin o regresión clásica), usando ritmo, rating ofensivo/defensivo, descanso, localía.
- **Ratings de equipos**:
  - ELO adaptado a basket (diferencia de puntos), o ratings tipo ORtg/DRtg.
- **Rendimiento de jugadores**:
  - StatLines por jugador (pts, reb, ast, etc.) y métricas de regularidad/uso; esto sirve para análisis, no necesariamente para v1 de mercados, pero se deja la estructura.

### 6.3. Tenis

Objetivo inicial: moneyline y over/under de juegos/sets sencillo.

- **Ratings de jugadores**:
  - ELO por superficie (dura, arcilla, césped).
  - Estadísticas simples: % victorias, promedio de juegos por set.
- **Modelos de partido**:
  - Prob. de victoria usando ELO y stats básicas.
  - Derivar prob. de over/under de juegos/sets a partir de un modelo simple de sets.

---

## 7. Mercados de apuestas soportados

Para que el agente no se disperse, lista explícita:

- Fútbol:
  - ML (local/empate/visitante o moneyline sin empate según liga).
  - Over/Under goles totales (líneas típicas: 2.5, 3.5, etc.).
  - Handicap de goles (–1.5, +1.5, etc.).

- NBA:
  - ML (ganador del partido).
  - Spread de puntos.
  - Over/Under puntos totales.

- Tenis:
  - ML (ganador del partido).
  - Over/Under juegos totales (según disponibilidad de datos).

Nota: la ingestión de **odds reales** dependerá de si encuentras alguna API free con cuotas; si no, debes permitir entrada manual de líneas/cuotas y usarlas solo para análisis de closing line value, acierto, etc.

---

## 8. Agentes de IA con Nemotron

### 8.1. Integración Nemotron (OpenRouter)

- Modelo: `nvidia/nemotron-3-super-120b-a12b:free`. [openrouter](https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b:free/pricing)
- Variables de entorno:
  - `OPENROUTER_API_KEY`
  - `OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free`

`nemotron_client.py` debe exponer una función genérica:

- `call_nemotron(messages, system_prompt, tools=None) -> respuesta`.

### 8.2. Roles de agentes

1. **Data Agent**
   - Ayuda a:
     - Diseñar mapeos de nuevas APIs/CSVs al modelo de dominio.
     - Generar código ETL y tests.
   - Nunca debe inventar campos no definidos en `domain.py` o `APIS.md`.

2. **Modeling Agent**
   - Enfocado en modelos para mercados:
     - Proponer features para ML, Poisson, ELO.
     - Analizar resultados de validación y sugerir mejoras.

3. **User Analyst Agent**
   - Interfaz conversacional para ti:
     - Preguntas tipo “¿quién está sobreperformando en over 2.5 goles en la Premier?” con respuesta apoyada en datos.
   - Debe ser capaz de responder “no hay datos suficientes” si el dataset no cubre la pregunta.

En `AGENTS.md` define los system prompts y restricciones de cada uno.

---

## 9. Flujo general de uso

1. Usuario elige deporte, liga/torneo y rango temporal.
2. Sistema descarga datos desde APIs y/o carga CSVs manuales.
3. Normaliza datos al modelo de dominio y los guarda en BD.
4. Calcula métricas básicas (stats, ratings ELO, etc.).
5. Genera features y entrena/actualiza modelos por deporte/mercado.
6. Produce probabilidades para over/under, ML, hándicap según deporte.
7. UI/CLI muestran métricas, gráficos y resultados.
8. User Analyst Agent responde preguntas sobre esos datos usando Nemotron.

---

## 10. Plan de desarrollo por fases (adaptado a fútbol + NBA + tenis + mercados)

### Fase 0 – Setup

- Crear repo y estructura de carpetas.
- Configurar entorno Python (poetry/uv) + FastAPI + Postgres/SQLite.
- Configurar ejecución con un solo comando para unificar todo.
- Crear `docs/PLAN.md`, `APIS.md`, `MODELS.md`, `AGENTS.md`.

### Fase 1 – Data & dominio (fútbol/NBA/tenis)

- Implementar `core/domain.py` con entidades comunes.
- Implementar adaptadores:
  - `football_api_football.py` y/o `football_thesportsdb.py`. [api-football](https://www.api-football.com)
  - `nba_balldontlie.py`. [mcpmarket](https://mcpmarket.com/es/server/balldontlie-sports)
  - `tennis_thesportsdb.py`.
- Implementar `manual_loader.py` para CSV/Excel.
- Persistencia en BD y endpoints mínimos para listar partidos.

### Fase 2 – Métricas y ratings

- Fútbol: stats simples y ELO por equipo.
- NBA: stats de partido por equipo y rating tipo ELO.
- Tenis: stats básicas y ELO por superficie.
- Endpoints/consultas para ver rankings y evolución.

### Fase 3 – Modelos de partido (ML, over/under, hándicaps)

- Fútbol: modelo de goles (Poisson/bivariado) y derivar prob. para ML y over/under típico. [opensource.pysport](https://opensource.pysport.org)
- NBA: modelo de puntos de equipo y derivar prob. de spread y totales.
- Tenis: modelo simple de victoria basados en ELO y datos básicos.
- Guardar predicciones en BD + métricas de performance (logloss/Brier).

### Fase 4 – UI básica + CLI

- API REST para: buscar partidos, ver predicciones, ver métricas.
- Dashboard web con:
  - Listado de partidos y predicciones por mercado.
  - Vistas de equipos/jugadores con métricas clave.
- CLI para ejecutar pipelines y generar reportes offline.

### Fase 5 – Integración Nemotron y agentes

- Implementar `nemotron_client.py`.
- Implementar Data Agent y Modeling Agent con prompts en `AGENTS.md`.
- Implementar User Analyst Agent + endpoint `/analysis/chat`.
- Añadir una pestaña de “Análisis IA” en el dashboard.

### Fase 6 – Refinamiento y extensiones

- Mejorar features, tuning de modelos, curvas de calibración.
- Añadir más ligas/torneos y campos específicos por deporte.
- Explorar integración con APIs de cuotas (aunque sea solo para un par de casas o entrada manual).

---

## 11. Instrucciones para el agente de programación

- No inventes entidades, columnas ni endpoints: usa solo lo definido en `core/domain.py` y `docs/*.md`.
- Antes de crear una nueva fuente de datos o modelo, actualiza primero el documento correspondiente en `docs/`.
- Si no existe una API gratuita fiable para cierto dato, implementa un importador manual (CSV) en lugar de simular datos.
- Si `OPENROUTER_API_KEY` no está configurado, las llamadas a Nemotron deben estar mockeadas y devolver un mensaje de ejemplo.
- Para changes grandes:
  1. Actualiza diseño en `docs/`.
  2. Crea interfaces.
  3. Implementa.
  4. Añade tests.

---
