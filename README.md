# Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform

Sherlock es una plataforma avanzada de análisis deportivo diseñada para identificar valor en mercados de apuestas mediante modelos matemáticos y estadísticas granulares. Actualmente centrada en **fútbol**, con soporte en desarrollo para NBA y Tenis.

---

## Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Flujo de Trabajo Completo](#flujo-de-trabajo-completo)
3. [Motor de Predicción (Fútbol)](#motor-de-predicción-fútbol)
4. [Sistema de Valor y Picks](#sistema-de-valor-y-picks)
5. [Dashboard de Rendimiento](#dashboard-de-rendimiento)
6. [Extensión Watson (Browser)](#extensión-watson-browser)
7. [API REST](#api-rest)
8. [Instalación](#instalación)
9. [Roadmap](#roadmap)

---

## Arquitectura General

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Extensión      │────▶│  FastAPI Backend │────▶│  SQLite (Historial) │
│  Watson         │     │  compare.py      │     │  analysis_history   │
│  (SofaScore /   │     │  main.py         │     └─────────────────────┘
│   Betano)       │     └────────┬─────────┘
└─────────────────┘              │
                                 ▼
                    ┌────────────────────────┐
                    │  Frontend Web          │
                    │  • Comparador          │
                    │  • Dashboard           │
                    │  • Ligas / Historial   │
                    └────────────────────────┘
```

| Componente                  | Ubicación                                  | Responsabilidad                               |
| --------------------------- | ------------------------------------------ | --------------------------------------------- |
| Motor Poisson + Dixon-Coles | `src/ui/api/compare.py`                    | Lambdas, probabilidades, value picks          |
| API REST                    | `src/ui/api/main.py`                       | Endpoints, historial, estadísticas            |
| Modelos de dominio          | `src/core/domain.py`                       | Entidades SQLAlchemy                          |
| Comparador UI               | `src/ui/web/templates/dashboard.html`      | Entrada manual / API-Football                 |
| Dashboard rendimiento       | `src/ui/web/templates/main_dashboard.html` | KPIs, gráficos, simulador                     |
| Extensión Watson            | `watson/`                                  | Scraping SofaScore + push de datos/resultados |

---

## Flujo de Trabajo Completo

### 1. Carga de Datos

- **Manual**: El usuario introduce estadísticas en el comparador (`/dashboard`).
- **API-Football**: Carga automática de stats de temporada por liga/equipo.
- **Watson (SofaScore)**: La extensión extrae stats segmentadas por local/visitante y las envía vía `POST /api/v1/prefill`.

### 2. Análisis del Partido

Al pulsar "Analizar", el frontend envía un `FootballCompareRequest` a `POST /api/v1/compare/football`. El motor:

1. Calcula lambdas (λ) por equipo y mercado.
2. Construye la matriz Dixon-Coles de marcadores.
3. Deriva probabilidades para 1X2, BTTS, DC, DNB, O/U, AH, corners, tarjetas, tiros, etc.
4. Compara probabilidades del modelo vs. cuotas de la casa.
5. Clasifica cada pick en categorías (profesional, underdog, alta confianza).

### 3. Guardado en Historial

`POST /api/v1/analysis` persiste el análisis en SQLite con:

- Payload original (stats + cuotas).
- Snapshot de la respuesta del motor.
- Picks calculados con todas sus métricas.

### 4. Registro de Resultados

- **Manual**: Formulario en la UI de historial.
- **Watson**: `POST /api/v1/result` con marcador y stats finales (corners, tarjetas, tiros…).
- Al registrar resultados, Sherlock recalcula automáticamente el acierto de cada pick.

### 5. Dashboard de Rendimiento

`GET /api/v1/stats/global` agrega todos los análisis resueltos y alimenta el dashboard (`/main-dashboard`) con KPIs, gráficos y rankings.

---

## Motor de Predicción (Fútbol)

### Granularidad Condicional (Local / Visitante)

Las estadísticas se segmentan por condición del partido:

- El equipo **local** aporta sus stats de **local** (`matches_home`, goles de local…).
- El equipo **visitante** aporta sus stats de **visita** (`matches_away`).

Esto evita mezclar rendimiento doméstico con rendimiento fuera de casa.

### Distribución de Poisson

Probabilidad de que ocurran `k` eventos:

$$P(k; \lambda) = \frac{\lambda^k e^{-\lambda}}{k!}$$

### Dixon-Coles (Matriz de Marcadores)

Corrige la subestimación de marcadores bajos (0-0, 1-0, 0-1, 1-1) con factor ρ:

| Marcador | τ(x,y)  |
| -------- | ------- |
| 0-0      | 1 − λμρ |
| 0-1      | 1 + λρ  |
| 1-0      | 1 + μρ  |
| 1-1      | 1 − ρ   |

De la matriz se derivan: 1X2, BTTS, Over/Under de goles, marcador exacto y Asian Handicap.

### Bayesian Shrinkage (Regresión a la Media)

Para estabilizar muestras pequeñas:

$$w = \frac{\text{prior}}{\text{prior} + n}$$
$$\lambda_{\text{final}} = \lambda_{\text{modelo}} \cdot (1 - w) + \lambda_{\text{liga}} \cdot w$$

### Cálculo de Lambdas (λ)

#### Goles

1. **Fuerza de ataque bayesiana**: hibridación Poisson-Gamma de goles reales + xG como prior (β=5).
2. **Debilidad defensiva rival**: goles concedidos + xGA del defensor.
3. **Lambda base**: `att_str × def_weakness × avg_team_goals`.
4. **Señal táctica**: ratio Big Chances creadas/falladas (±8% máx.).
5. **Shrinkage global**: regresión a media de liga según tamaño de muestra.

#### Corners

- Ratio de centros completados (`crosses_per_game / crosses_total_per_game`) como predictor principal.
- Corners históricos × debilidad defensiva del rival (corners concedidos).
- Shrinkage bayesiana segmentada por localía.

#### Tarjetas

- Base: amarillas + rojas ponderadas (1 roja = 2 amarillas).
- Modificadores: faltas propias, posesión/duelos del rival.
- **Factor árbitro**: ajuste del 50% según desviación del árbitro vs. media de liga.
- Shrinkage con prior de 5 partidos.

#### Tiros / Tiros a Puerta

- Producción ofensiva propia × factor defensivo del rival.
- Factor defensivo hibridado: 55% posesión rival baja + 45% xGA rival elevado.
- Shrinkage bayesiana por muestra segmentada.

#### Faltas / Offsides

- Tasa propia × factor de posesión (faltas: rival con más posesión → más faltas; offsides: más posesión propia → más offsides).
- Shrinkage a media de liga.

### Líneas Asiáticas (Over/Under y Handicap)

Las líneas `.25` y `.75` se dividen en dos componentes:

- **2.25** → 2.0 + 2.5
- **-0.75** → -0.5 + -1.0

Resultados posibles: win, loss, push (void), half_win, half_loss.

### Blend de Probabilidades 1X2

Las probabilidades crudas de la matriz DC se mezclan con priors de liga:

- **1X2**: 70% modelo + 30% prior de liga.
- **Doble Oportunidad**: 90% modelo + 10% prior (evita doble regresión a la media).

### Overround y Edge

El margen de la casa se elimina antes de calcular valor:

$$\text{overround} = \sum \frac{1}{\text{cuota}_i} \times 100$$

$$\text{implied\_no\_vig} = \frac{\text{implied\_raw}}{\text{overround} / 100}$$

$$\text{EV} = \frac{P_{\text{calibrada}}}{100} \times \text{cuota} - 1$$

---

## Sistema de Valor y Picks

### Métricas por Pick

| Métrica              | Descripción                                              |
| -------------------- | -------------------------------------------------------- |
| `model_prob`         | Probabilidad cruda del modelo (%)                        |
| `calibrated_prob`    | Probabilidad post-calibración por familia de mercado     |
| `implied_prob`       | Probabilidad implícita bruta de la cuota                 |
| `edge`               | Diferencia en puntos porcentuales: calibrada − implícita |
| `edge_ev`            | Expected Value: `(prob × cuota) − 1`                     |
| `fair_odds`          | Cuota justa: `100 / calibrated_prob`                     |
| `kelly_fraction`     | Kelly fraccional (1/8) para sizing                       |
| `display_score`      | Score compuesto 0–100 para ranking visual                |
| `data_quality_score` | Calidad de datos disponibles para ese mercado            |
| `stat_support`       | Respaldo estadístico directo (0–100)                     |
| `proj_support`       | Respaldo de proyección λ (0–100)                         |

### Categorías de Picks

| Categoría                          | Criterios principales                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------------ |
| **Profesional** (`is_publishable`) | Cuota 1.40–2.50, prob. ≥60% (binarios) o ≥35% (volátiles), EV ≥2%, calidad datos ≥50 |
| **Underdog** (`is_underdog`)       | Cuota 2.50–5.80, EV ≥5%, sin corners                                                 |

### Display Score (0–100)

```
score = prob_calibrada × 0.4
      + min(edge_ev, 15%) × 100 × 2.0
      + data_quality × 0.1
      + estabilidad × 0.2
```

La estabilidad combina el peso de muestra de ambos equipos (`sample_size_weight`) con ajuste por rango de cuota.

---

## Dashboard de Rendimiento

Ruta: `/main-dashboard` · API: `GET /api/v1/stats/global`

### Filtros

- Rango temporal: hoy, 7 días, 30 días, personalizado, o todo el historial.
- Pestañas: Global, Profesional, Underdog, Alta Confianza.

### KPIs Principales

| KPI                     | Cálculo                                                                      |
| ----------------------- | ---------------------------------------------------------------------------- |
| **Partidos analizados** | Total de registros en `analysis_history` (con `count_in_profitability=true`) |
| **Picks resueltos**     | Picks publicables/underdog/HC con resultado conocido                         |
| **Acierto (%)**         | `hits / picks_con_stake × 100` (excluye void/push)                           |
| **Beneficio (u)**       | Suma de profit por pick con stake plano de 1 unidad                          |
| **ROI (%)**             | `beneficio_total / picks_con_stake × 100`                                    |
| **Cuota media**         | Media aritmética de cuotas de picks resueltos                                |
| **Marcador exacto**     | Aciertos del `most_probable_score` vs. resultado real                        |

### Cálculo de Profit por Pick

Con stake plano de **1 unidad**:

| Resultado   | Profit                            |
| ----------- | --------------------------------- |
| Win         | `cuota − 1`                       |
| Loss        | `−1`                              |
| Void (push) | `0` (no cuenta en acierto ni ROI) |
| Half-win    | `(cuota − 1) / 2`                 |
| Half-loss   | `−0.5`                            |

### Mercados con Push/Void

- **DNB**: empate → void.
- **Asian Handicap** línea entera: empate ajustado → void.
- **Over/Under** línea entera (ej. Over 2.0 con exactamente 2 goles) → void.
- **Líneas .25/.75**: resultado half-win o half-loss.

### Gráficos

| Gráfico             | Datos                                                                          |
| ------------------- | ------------------------------------------------------------------------------ |
| Mercados            | Acierto % y beneficio neto por tipo de mercado                                 |
| Cuotas              | Acierto % por bucket de cuota (1.0–1.5, 1.5–2.0, 2.0–3.0, >3.0)                |
| Edge                | Acierto % por bucket de edge en puntos porcentuales (<5%, 5–10%, 10–15%, >15%) |
| Rentabilidad diaria | Unidades netas acumuladas por fecha de partido                                 |
| Rankings            | Top 5 ligas y equipos por beneficio neto                                       |

### Simulador de Capital

```
capital_final = capital_inicial + (beneficio_unidades × valor_por_unidad)
```

Asume staking plano (flat stake) sin reinversión compuesta.

---

## Extensión Watson (Browser)

Ubicación: `watson/` · Ver también `watson/README.md`

### Funciones

1. **Extracción SofaScore**: Stats de temporada segmentadas por local/visitante.
2. **Prefill**: Envía datos al comparador de Sherlock (`POST /api/v1/prefill`).
3. **Resultados**: Detecta marcadores finales y los envía (`POST /api/v1/result`).
4. **Betano**: Integración para captura de cuotas (content script).

### Flujo

```
SofaScore → sofaScoreToSherlock.js → background.js → Sherlock API → DB
```

---

## API REST

### Análisis

| Método | Ruta                               | Descripción                  |
| ------ | ---------------------------------- | ---------------------------- |
| `POST` | `/api/v1/compare/football`         | Ejecuta motor de comparación |
| `POST` | `/api/v1/analysis`                 | Guarda análisis en historial |
| `GET`  | `/api/v1/analysis`                 | Lista historial              |
| `POST` | `/api/v1/analysis/{id}/results`    | Registra resultado final     |
| `POST` | `/api/v1/analysis/recalculate-all` | Re-procesa todo el historial |

### Estadísticas

| Método | Ruta                    | Descripción                   |
| ------ | ----------------------- | ----------------------------- |
| `GET`  | `/api/v1/stats/global`  | KPIs globales + por categoría |
| `GET`  | `/api/v1/stats/leagues` | Rendimiento por liga          |
| `GET`  | `/api/v1/stats/picks`   | Listado detallado de picks    |

### Integración

| Método | Ruta              | Descripción                       |
| ------ | ----------------- | --------------------------------- |
| `POST` | `/api/v1/prefill` | Recibe datos de extensión         |
| `GET`  | `/api/v1/prefill` | Frontend consume último prefill   |
| `POST` | `/api/v1/result`  | Recibe resultados de extensión    |
| `GET`  | `/api/v1/result`  | Frontend consume último resultado |

### UI

| Ruta              | Descripción              |
| ----------------- | ------------------------ |
| `/dashboard`      | Comparador de equipos    |
| `/main-dashboard` | Dashboard de rendimiento |
| `/leagues`        | Vista por liga           |
| `/history`        | Historial de análisis    |

---

## Estadísticas Recolectadas (Fútbol)

### Ofensivas

- Goles/juego (local/visita), xG, Big Chances, remates, conversión.

### Defensivas

- Goles concedidos, xGA, clean sheets (home/away), atajadas.

### Control y Táctica

- Posesión, pases (completados, precisión, campo rival), centros.
- **Calculados**: pases totales = `(completados × 100) / precisión`.

### Disciplina

- Faltas, amarillas, rojas, corners generados y concedidos.

---

## Instalación

### Requisitos

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)

### Pasos

```bash
# 1. Instalar dependencias
uv sync

# 2. Configurar entorno
cp .env.example .env
# Editar .env con API keys:
#   API_FOOTBALL_KEY=...
#   OPENROUTER_API_KEY=...  (opcional, para análisis IA)
#   OPENROUTER_MODEL=...    (opcional)

# 3. Ejecutar servidor
uv run uvicorn src.ui.api.main:app --reload
```

Abrir `http://localhost:8000/dashboard` para el comparador o `http://localhost:8000/main-dashboard` para el dashboard de rendimiento.

### Extensión Watson

1. Abrir `chrome://extensions/`
2. Activar "Modo desarrollador"
3. "Cargar descomprimida" → seleccionar carpeta `watson/`

---

## Roadmap

- [ ] **NBA Engine**: Rating Ofensivo/Defensivo y Ritmo (Pace).
- [ ] **Tennis Engine**: Modelo basado en ELO y retención de servicios por superficie.
- [ ] **AI Agents**: Integración de LLMs para análisis cualitativo (noticias, lesiones, clima).
- [ ] **Database Persistence**: Migración a PostgreSQL para producción.
- [ ] **Backtesting**: Simulación histórica con walk-forward validation.
