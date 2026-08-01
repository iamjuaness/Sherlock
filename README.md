# Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform

**Sherlock** es una plataforma avanzada de análisis deportivo diseñada para identificar valor en mercados de apuestas mediante modelos matemáticos y estadísticas granulares. Actualmente centrada en **fútbol**, con soporte en desarrollo para NBA y Tenis.

---

## 📋 Tabla de Contenidos

1. [Arquitectura General](#arquitectura-general)
2. [Flujo de Trabajo Completo](#flujo-de-trabajo-completo)
3. [Motor de Predicción (Fútbol)](#motor-de-predicción-fútbol)
4. [Sistema de Valor y Picks](#sistema-de-valor-y-picks)
5. [Dashboard de Rendimiento](#dashboard-de-rendimiento)
6. [Extensión Watson (Browser)](#extensión-watson-browser)
7. [API REST](#api-rest)
8. [Estadísticas Recolectadas](#estadísticas-recolectadas-fútbol)
9. [Configuración de Ligas (Blacklist/Penalties)](#configuración-de-ligas-blacklistpenalties)
10. [Instalación](#instalación)
11. [Roadmap](#roadmap)

---

## 🏗️ Arquitectura General

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

| Componente                          | Ubicación                                        | Responsabilidad                               |
| ----------------------------------- | ------------------------------------------------ | --------------------------------------------- |
| Motor Poisson + Dixon-Coles         | `src/ui/api/compare.py`                          | Lambdas, probabilidades, value picks          |
| API REST                            | `src/ui/api/main.py`                             | Endpoints, historial, estadísticas            |
| Modelos de dominio (SQLAlchemy)     | `src/core/domain.py`                             | Entidades: Match, Team, AnalysisHistory, etc. |
| Comparador UI                       | `src/ui/web/templates/dashboard.html`            | Entrada manual / API-Football / Watson        |
| Dashboard rendimiento               | `src/ui/web/templates/main_dashboard.html`       | KPIs, gráficos, simulador                     |
| Extensión Watson (SofaScore)        | `watson/` (background.js, content.js, etc.)      | Scraping SofaScore + push de datos/resultados |
| Extensión Watson (Betano)           | `watson/betano_content.js`                       | Scraping cuotas Betano API                    |
| Configuración ligas (blacklist)     | `data/league_penalties.json`                     | Penalizaciones por liga/mercado               |

---

## 🔄 Flujo de Trabajo Completo

### 1. Carga de Datos

| Fuente               | Método                                                         | Endpoint/API                                      |
| -------------------- | -------------------------------------------------------------- | ------------------------------------------------- |
| **Manual**           | Usuario introduce estadísticas en el comparador (`/dashboard`) | —                                                 |
| **API-Football**     | Carga automática de stats de temporada por liga/equipo         | `GET /api/v1/prefill` (consumido por frontend)    |
| **Watson (SofaScore)** | Extensión extrae stats segmentadas por local/visitante         | `POST /api/v1/prefill` (push desde background.js) |
| **Watson (Betano)**  | Extensión extrae cuotas desde API Betano                       | `POST /api/v1/prefill/odds`                       |

### 2. Análisis del Partido

Al pulsar **"Analizar"**, el frontend envía un `FootballCompareRequest` a `POST /api/v1/compare/football`. El motor ejecuta:

1. **Calcula lambdas (λ)** por equipo y mercado (goles, corners, tarjetas, tiros, faltas, offsides).
2. **Construye matriz Dixon-Coles** de marcadores corregida con factor ρ.
3. **Deriva probabilidades** para: 1X2, BTTS, DC, DNB, Over/Under goles, Asian Handicap, corners, tarjetas, tiros, tiros a puerta, faltas, offsides.
4. **Compara** probabilidades del modelo vs. cuotas de la casa (sin overround).
5. **Clasifica** cada pick en categorías: **Profesional**, **Underdog**, **Alta Confianza**.

### 3. Guardado en Historial

`POST /api/v1/analysis` persiste el análisis en SQLite con:
- Payload original (stats + cuotas).
- Snapshot de la respuesta del motor.
- Picks calculados con todas sus métricas.

### 4. Registro de Resultados

| Método    | Descripción                                                                    |
| --------- | ------------------------------------------------------------------------------ |
| **Manual**  | Formulario en la UI de historial (`/history`).                                 |
| **Watson**  | `POST /api/v1/result` con marcador y stats finales (corners, tarjetas, tiros). |

Al registrar resultados, Sherlock **recalcula automáticamente el acierto** de cada pick.

### 5. Dashboard de Rendimiento

`GET /api/v1/stats/global` agrega todos los análisis resueltos y alimenta el dashboard (`/main-dashboard`) con KPIs, gráficos y rankings.

---

## ⚽ Motor de Predicción (Fútbol)

### Granularidad Condicional (Local / Visitante)

Las estadísticas se segmentan por condición del partido:

- El equipo **local** aporta sus stats de **local** (`matches_home`, goles de local, etc.).
- El equipo **visitante** aporta sus stats de **visita** (`matches_away`).

Esto evita mezclar rendimiento doméstico con rendimiento fuera de casa.

> **Nota**: A partir del `2026-07-01` (configurable via `match_date` y `use_general_stats`), se pueden usar stats generales (sin segmentar) para ligas con poca muestra.

---

### Distribución de Poisson

Probabilidad de que ocurran `k` eventos con tasa `λ`:

$$P(k; \lambda) = \frac{\lambda^k e^{-\lambda}}{k!}$$

---

### Dixon-Coles (Matriz de Marcadores)

Corrige la subestimación de marcadores bajos (0-0, 1-0, 0-1, 1-1) con factor **ρ (rho)**:

| Marcador | τ(x,y)        |
| -------- | ------------- |
| 0-0      | 1 − λμρ       |
| 0-1      | 1 + λρ        |
| 1-0      | 1 + μρ        |
| 1-1      | 1 − ρ         |

**ρ dinámico**:
```python
def _default_dc_rho(h_lam, a_lam):
    total = h_lam + a_lam
    base = -0.13
    if total < 2.0: return max(-0.18, base - 0.03)
    if total > 3.0: return min(-0.08, base + 0.03)
    return base
```

De la matriz se derivan: **1X2, BTTS, Over/Under goles, Marcador Exacto, Asian Handicap**.

---

### Bayesian Shrinkage (Regresión a la Media)

Estabiliza muestras pequeñas mezclando la estimación del equipo con el prior de liga:

$$w = \frac{\text{prior}}{\text{prior} + n}$$

$$\lambda_{\text{final}} = \lambda_{\text{modelo}} \cdot (1 - w) + \lambda_{\text{liga}} \cdot w$$

- **Goles**: `prior_n = 5` (equivalente a 5 partidos ficticios de liga).
- **Corners**: `prior_n = 5`, segmentado por localía.
- **Tarjetas**: `prior_n = 10` (anclaje fuerte al promedio).
- **Tiros / Tiros a puerta**: `prior_n = 5`.
- **Faltas / Offsides**: `prior_n = 2`.

---

### Cálculo de Lambdas (λ) por Mercado

#### 1. Goles (`_compute_team_goals_lambda`)

1. **Fuerza de ataque bayesiana**: hibridación Poisson-Gamma de goles reales + xG como prior (β=5).
2. **Debilidad defensiva rival**: goles concedidos + xGA del defensor.
3. **Lambda base**: `att_str × def_weakness × avg_team_goals`.
4. **Señal táctica**: ratio Big Chances creadas/falladas (±8% máx.).
5. **Perfil de goles**: % goles fuera del área (+4% si >25%), % goles en contraataque (+5% si >15%).
6. **Penalizaciones**: posesión perdida excesiva (-6% si >120 pérdidas/juego).
7. **Errores rivales**: errores que llevan a gol/tiro (+8% máx.).
8. **Rating equipo**: ±3% por punto de rating respecto a 7.0.
9. **Portero rival**: save% ajusta λ (±15% máx.).
10. **Presión defensiva rival**: intercepciones + entradas (±12%).
11. **Asistencias**: proxy de juego construido (+6% máx.).
12. **Shrinkage global**: regresión a media de liga según tamaño de muestra.

#### 2. Corners (`_compute_team_corners_lambda`)

- **Señal principal**: ratio de centros completados (`crosses_per_game / crosses_total_per_game`).
- **Base**: corners históricos × debilidad defensiva rival (corners concedidos).
- **Factores avanzados** (cap global +12%): duelos aéreos, posesión, contraataques, tiros bloqueados rival, despejes en línea rival, despejes totales rival (presión), pases precisos rival (posesión rival → menos corners).
- **Shrinkage bayesiana** segmentada por localía (prior_n=5).

#### 3. Tarjetas (`_compute_team_cards_lambda`)

- **Base**: amarillas + rojas ponderadas (1 roja = 2 amarillas).
- **Shrinkage previo** a promedio liga (prior_n=10).
- **Modificadores** (cap ±15% total): faltas propias, posesión/duelos rival.
- **Factores secundarios** (cap ±12%): penales concedidos, errores a tiro, duelos totales, contraataques rival, tarjetas provocadas por estilo rival.
- **Factor árbitro**: ajuste del 35% según desviación del árbitro vs. media liga (cap 0.88–1.20).
- **Shrinkage final** post-modificadores (prior_n=10).

#### 4. Tiros / Tiros a Puerta (`_compute_team_shots_lambda`, `_compute_team_shots_target_lambda`)

- **Producción ofensiva propia** × factor defensivo rival.
- **Factor defensivo hibridado**: 30% posesión rival baja + 30% xGA rival elevado + 40% tiros concedidos (ponderado dentro/fuera área) × 0.87.
- **Ajuste defensas proactivas**: ratio bloqueos/intentos (±8%).
- **Shrinkage bayesiana** (prior_n=5).

#### 5. Faltas / Offsides (`_compute_team_fouls_lambda`, `_compute_team_offsides_lambda`)

- **Faltas**: tasa propia × factor posesión (rival con más posesión → más faltas) × intensidad física (km, sprints, duelos).
- **Offsides**: tasa propia × factor posesión (más posesión propia → más offsides) × contraataques + dribbles exitosos.
- **Shrinkage** a media de liga (prior_n=2).

---

### Líneas Asiáticas (Over/Under y Handicap)

Las líneas `.25` y `.75` se dividen en dos componentes:

| Línea  | Componentes |
| ------ | ----------- |
| 2.25   | 2.0 + 2.5   |
| -0.75  | -0.5 + -1.0 |

Resultados posibles: **win, loss, push (void), half_win, half_loss**.

---

### Blend de Probabilidades 1X2

Las probabilidades crudas de la matriz DC se mezclan con priors de liga:

| Mercado            | Peso Modelo | Peso Prior Liga |
| ------------------ | ----------- | --------------- |
| **1X2**            | 70%         | 30%             |
| **Doble Oportunidad** | 90%         | 10%             |

*La Doble Oportunidad usa menos prior para evitar doble regresión a la media.*

---

### Overround y Edge

El margen de la casa se elimina antes de calcular valor:

$$\text{overround} = \sum \frac{1}{\text{cuota}_i} \times 100$$

$$\text{implied\_no\_vig} = \frac{\text{implied\_raw}}{\text{overround} / 100}$$

$$\text{EV} = \frac{P_{\text{calibrada}}}{100} \times \text{cuota} - 1$$

---

## 🎯 Sistema de Valor y Picks

### Métricas por Pick (`ValueIndicator`)

| Métrica                      | Descripción                                              |
| ---------------------------- | -------------------------------------------------------- |
| `model_prob`                 | Probabilidad cruda del modelo (%)                        |
| `calibrated_prob`            | Probabilidad post-calibración por familia de mercado     |
| `implied_prob`               | Probabilidad implícita bruta de la cuota                 |
| `implied_prob_no_vig`        | Probabilidad implícita sin overround (fair market)       |
| `edge`                       | Diferencia en pp: calibrada − implícita                  |
| `edge_ev`                    | Expected Value real: `(prob × cuota) − 1`                |
| `fair_odds`                  | Cuota justa: `100 / calibrated_prob`                     |
| `kelly_fraction`             | Kelly fraccional (1/8) para sizing                       |
| `display_score`              | Score compuesto 0–100 para ranking visual                |
| `data_quality_score`         | Calidad de datos disponibles para ese mercado            |
| `stat_support`               | Respaldo estadístico directo (0–100)                     |
| `proj_support`               | Respaldo de proyección λ (0–100)                         |
| `league_reliability_score`   | LRS de la liga (0–1)                                     |
| `league_reliability_penalty` | EV descontado por LRS                                    |
| `market_confidence_tier`     | "segmented" / "hybrid" / "global"                        |
| `market_variance_tier`       | "low" / "medium" / "high"                                |
| `is_publishable`             | Flag: pick calidad profesional                           |
| `is_underdog`                | Flag: pick underdog                                      |
| `stake_units`                | Unidades de stake calculadas (0.5–5.0)                   |

---

### Categorías de Picks

| Categoría                          | Criterios principales                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------------ |
| **Profesional** (`is_publishable`) | Cuota 1.40–2.50, prob. ≥60% (binarios) o ≥35% (volátiles), EV ≥2%, calidad datos ≥50 |
| **Underdog** (`is_underdog`)       | Cuota 2.50–5.80, EV ≥5%, sin corners                                                 |

---

### Display Score (0–100)

```
score = prob_calibrada × 0.4
      + min(edge_ev, 15%) × 100 × 2.0
      + data_quality × 0.1
      + estabilidad × 0.2
```

La **estabilidad** combina el peso de muestra de ambos equipos (`sample_size_weight`) con ajuste por rango de cuota.

---

### Calibración por Familia de Mercado (`apply_calibration`)

Transformación potencial (power function) + shrinkage hacia 50%:

| Familia              | Exponente (b) | Shrinkage extra           |
| -------------------- | ------------- | ------------------------- |
| `result`, `btts`, `goals`, `handicap` | 0.85          | —                         |
| `corners`, `cards`, `shots`, `shots_target`, `fouls` | 0.75          | —                         |
| `double_chance`      | 0.70–0.78     | 7–12% hacia 50%           |
| `dnb`                | 0.82          | 5% hacia 50%              |
| Cuota > 3.0          | —             | ×0.90                     |
| Cuota > 2.0          | —             | ×0.94                     |

---

### League Reliability Score (LRS)

Score 0.25–1.0 que combina:

**A. Coherencia estadística interna** (rangos razonables de goles, corners, tarjetas, home advantage).
**B. Rendimiento histórico real** (acierto + beneficio), con **peso Bayesiano** proporcional a nº de picks:
- Con N=20 picks → 50% peso histórico.
- Con pocos datos (<10 picks), el histórico se ignora casi totalmente.

**Penalización al EV efectivo**:
- Mercados principales (result, goals, btts, handicap, dc, dnb): `EV_adj = EV × LRS`
- Mercados secundarios (corners, cards, shots): `EV_adj = EV × LRS^1.5` (penalización extra por alta varianza).

**Penalización adicional por mercado**: si la liga tiene historial por familia de mercado y rinde peor que referencia, factor extra (cap ±35%/-15%).

---

### Stake Sizing (`_calculate_stake_units`)

Sistema multi-capa con límites duros (0.5–5.0 unidades, redondeo 0.5):

```
stake = base_kelly × market_factor × odds_factor × league_factor × edge_factor
```

| Factor           | Detalle                                                                          |
| ---------------- | -------------------------------------------------------------------------------- |
| **Base (Kelly)** | `kelly_fraction × 100` (ej: 1/8 Kelly = 12.5% → 1.25u)                           |
| **Mercado**      | result/btts=1.0, goals=0.9, dc=0.85, dnb=0.9, hcap=0.75, corners=0.6, cards=0.55, shots=0.6, fouls=0.5 |
| **Cuota**        | <1.6=1.0, <2.0=0.9, <2.5=0.75, <3.5=0.5, ≥3.5=0.3                               |
| **Liga (LRS)**   | ≥0.85=1.0, ≥0.70=0.85, ≥0.60=0.70, ≥0.45=0.50, <0.45=0.30                       |
| **Edge**         | ≥12%=1.0, ≥8%=0.9, ≥5%=0.8, ≥3%=0.65, <3%=0.0                                   |

**Límites duros**:
- LRS < 0.50 → max 2.0u
- Cuota ≥ 3.0 → max 2.0u
- Mercados secundarios → max 3.0u

---

### Blacklist de Mercados por Liga (`data/league_penalties.json`)

Reglas de bloqueo (pick marcado `is_blacklisted=true`, `is_publishable=false`, `is_value=false`):

```json
{
  "league": "MLS",
  "market_family": "goals",
  "market_side": "over"
}
```

- `market_family`: goals, corners, cards, result, btts, handicap, double_chance, dnb, shots, shots_target, fouls.
- `market_side`: over, under, home, away, draw, yes, no, home_draw (1X), draw_away (X2), home_away (12).
- `category` (opcional): "profesional", "underdog", "high_confidence". Si se omite, aplica a todas.

---

## 📊 Dashboard de Rendimiento

**Ruta**: `/main-dashboard` · **API**: `GET /api/v1/stats/global`

### Filtros

- Rango temporal: hoy, 7 días, 30 días, personalizado, todo el historial.
- Pestañas: **Global**, **Profesional**, **Underdog**, **Alta Confianza**.

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

### Cálculo de Profit por Pick (Stake Plano = 1 unidad)

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
| Edge                | Acierto % por bucket de edge en pp (<5%, 5–10%, 10–15%, >15%)                  |
| Rentabilidad diaria | Unidades netas acumuladas por fecha de partido                                 |
| Rankings            | Top 5 ligas y equipos por beneficio neto                                       |

### Simulador de Capital

```
capital_final = capital_inicial + (beneficio_unidades × valor_por_unidad)
```

Asume staking plano (flat stake) sin reinversión compuesta.

---

## 🔌 Extensión Watson (Browser)

**Ubicación**: `watson/` · Ver también `watson/README.md`

### Funciones

1. **Extracción SofaScore**: Stats de temporada segmentadas por local/visitante.
2. **Prefill**: Envía datos al comparador de Sherlock (`POST /api/v1/prefill`).
3. **Resultados**: Detecta marcadores finales y los envía (`POST /api/v1/result`).
4. **Betano**: Integración para captura de cuotas (content script `betano_content.js`).

### Flujo SofaScore

```
SofaScore → sofaScoreToSherlock.js → background.js → Sherlock API → DB
```

**Endpoints SofaScore usados**:

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/event/{id}` | Información principal del partido |
| `/api/v1/event/{id}/lineups` | Alineaciones |
| `/api/v1/event/{id}/team-streaks` | Rachas y stats recientes |
| `/api/v1/team/{id}/unique-tournament/{tourId}/season/{seasonId}/statistics/overall` | Stats completas del equipo |
| `/api/v1/tournament/{tournamentId}/season/{seasonId}/standings/total` | Clasificación (para W/D/L reales) |

### Flujo Betano

```
Betano (página partido) → betano_content.js (fetch API interna) → POST /api/v1/prefill/odds
```

**URL API Betano**: `https://www.betano.co/api/cuotas-de-partido/{slug}/{id}?bt=13&req=s,stnf,c,mb,mbl`

**Mercados mapeados** (códigos Betano → Sherlock):

| Betano Type | Mercado Sherlock | Selections |
| ----------- | ---------------- | ---------- |
| `MRES`      | 1X2 (Moneyline)  | 1, X, 2    |
| `DBLC`      | Doble Oportunidad | 1X, X2, 12 |
| `BTSC`      | Ambos Marcan (BTTS) | Sí, No |
| `HCTG`      | Goles Totales O/U | Líneas .5 (Over/Under) |
| `CNOU`      | Corners O/U      | Líneas .5 |
| `TCOU`      | Tarjetas Totales O/U | Líneas .5 |
| `X002`      | Tiros a Puerta O/U | Líneas .5 |
| `4159`      | Remates Totales O/U | Líneas .5 |
| `DNOB`      | Draw No Bet      | Local, Visitante |
| `FHMR`/`AHRF`/`FHH1` | Asian Handicap | Líneas con handicap |

**Normalización**: `columnIndex=0` → Over, `columnIndex=1` → Under. Solo líneas `.5` (filtra enteras).

### Configuración Extensión

1. `chrome://extensions/` → Modo desarrollador → "Cargar descomprimida" → carpeta `watson/`.
2. Click icono → "Configurar Endpoint" → URL base (ej. `http://localhost:8000`).
3. En SofaScore: entrar a partido → click extensión → "Extraer Estadísticas Completas" → "Enviar a Endpoint".
4. En Betano: entrar a partido → odds se capturan auto y envían a Sherlock.

---

## 🌐 API REST

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

### Integración (Watson / Extensiones)

| Método | Ruta              | Descripción                       |
| ------ | ----------------- | --------------------------------- |
| `POST` | `/api/v1/prefill` | Recibe datos de extensión         |
| `GET`  | `/api/v1/prefill` | Frontend consume último prefill   |
| `POST` | `/api/v1/prefill/odds` | Recibe cuotas Betano          |
| `GET`  | `/api/v1/prefill/odds` | Frontend consume últimas odds |
| `POST` | `/api/v1/result`  | Recibe resultados de extensión    |
| `GET`  | `/api/v1/result`  | Frontend consume último resultado |

### UI (Server-Side Rendered)

| Ruta              | Descripción              |
| ----------------- | ------------------------ |
| `/dashboard`      | Comparador de equipos    |
| `/main-dashboard` | Dashboard de rendimiento |
| `/leagues`        | Vista por liga           |
| `/history`        | Historial de análisis    |

---

## 📈 Estadísticas Recolectadas (Fútbol)

### Ofensivas
- Goles/juego (local/visita), xG, Big Chances, remates, conversión.
- **Detalle goles**: dentro/fuera área, cabeza, falta, contraataque, penalti, autogoles.
- **Detalle tiros**: bloqueados, dentro/fuera área, palos, contraataque, falta, penaltis.
- **Acciones ofensivas**: % regates, contraataques, saques de banda.

### Defensivas
- Goles concedidos, xGA, clean sheets (home/away), atajadas, recuperaciones.
- **Avanzado**: despejes en línea, entradas último hombre.

### Control y Táctica
- Posesión, pases (completados, precisión, campo rival), centros.
- **Calculados**: pases totales = `(completados × 100) / precisión`.
- **Avanzado**: pérdidas de posesión.

### Disciplina
- Faltas, amarillas, rojas, corners generados y concedidos.

### Portería (Avanzado)
- % paradas, saques de meta.

### Físicas
- Km recorridos, sprints.

### Rating
- Rating promedio del equipo.

---

## ⚙️ Configuración de Ligas (Blacklist/Penalties)

Archivo: `data/league_penalties.json`

Lista de reglas que **bloquean picks** (`is_blacklisted=true`) para combinaciones específicas de liga + mercado + lado.

Ejemplos actuales:
- **MLS**: bloquea Over goles, Over tarjetas, Visitante (1X2/DNB/DC), BTTS Sí, Over tiros a puerta.
- **Bundesliga**: bloquea Under corners, Under tiros, Under tiros a puerta, tarjetas (general).
- **Premier League**: bloquea Under corners, Under tiros, Under tiros a puerta.
- **Brasileirão Série B**: bloquea Under corners, Under tiros, Visitante, Under goles, BTTS No, DC X2.
- **Serie A**: bloquea BTTS No, Over goles, Over tarjetas, Under tiros, Under tiros a puerta.
- **LaLiga**: bloquea Under corners, Over goles, tarjetas (general).
- **Y muchas más...** (337 reglas totales).

---

## 🚀 Instalación

### Requisitos
- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)

### Pasos

```bash
# 1. Instalar dependencias
uv sync

# 2. Configurar entorno
cp .env.example .env
# Editar .env con API keys:
#   API_FOOTBALL_KEY=...          (opcional, para API-Football)
#   OPENROUTER_API_KEY=...        (opcional, para análisis IA)
#   OPENROUTER_MODEL=...          (opcional)

# 3. Ejecutar servidor
uv run uvicorn src.ui.api.main:app --reload
```

Abrir:
- **Comparador**: `http://localhost:8000/dashboard`
- **Dashboard**: `http://localhost:8000/main-dashboard`

### Extensión Watson

1. Abrir `chrome://extensions/`
2. Activar "Modo desarrollador"
3. "Cargar descomprimida" → seleccionar carpeta `watson/`
4. Configurar endpoint en el popup de la extensión (default: `http://localhost:8000/api/v1/prefill`)

---

## 🗺️ Roadmap

- [ ] **NBA Engine**: Rating Ofensivo/Defensivo y Ritmo (Pace).
- [ ] **Tennis Engine**: Modelo basado en ELO y retención de servicios por superficie.
- [ ] **AI Agents**: Integración de LLMs para análisis cualitativo (noticias, lesiones, clima).
- [ ] **Database Persistence**: Migración a PostgreSQL para producción.
- [ ] **Backtesting**: Simulación histórica con walk-forward validation.

---

## 📁 Estructura del Proyecto

```
Sherlock/
├── src/
│   ├── config.py                    # Settings (pydantic-settings)
│   ├── core/
│   │   ├── database.py              # SQLAlchemy engine, session, migrations
│   │   └── domain.py                # ORM models (Team, Match, AnalysisHistory, etc.)
│   ├── datasources/
│   │   ├── base.py                  # Interfaz base DataSource
│   │   └── manual_loader.py         # Carga manual de stats
│   └── ui/
│       ├── api/
│       │   ├── main.py              # FastAPI app, endpoints, web UI routes
│       │   ├── compare.py           # MOTOR PRINCIPAL (Poisson, DC, lambdas, picks)
│       │   └── schemas.py           # Pydantic models (request/response)
│       └── web/
│           ├── static/
│           │   ├── css/styles.css
│           │   └── js/ (comparator.js, dashboard_main.js, leagues.js)
│           └── templates/
│               ├── dashboard.html   # Comparador
│               ├── main_dashboard.html # Dashboard rendimiento
│               └── leagues.html     # Vista por liga
├── watson/                          # Extensión Chrome (Manifest V3)
│   ├── background.js                # Service worker (SofaScore extraction)
│   ├── content.js                   # Content script (SofaScore page detection)
│   ├── betano_content.js            # Content script (Betano odds extraction)
│   ├── sofaScoreToSherlock.js       # Mapeo stats SofaScore → Sherlock schema
│   ├── popup.html / popup.js        # UI popup extensión
│   ├── settings.html / settings.js  # Configuración endpoint/auth
│   └── manifest.json
├── data/
│   ├── sherlock.db                  # SQLite DB
│   └── league_penalties.json        # Blacklist ligas/mercados
├── tests/                           # (vacío, pendiente)
├── pyproject.toml                   # Dependencias, config ruff/mypy/pytest
├── uv.lock
└── README.md                        # ← Este archivo
```

---

## 🔑 Variables de Entorno (`.env`)

| Variable             | Requerida | Descripción                              |
| -------------------- | --------- | ---------------------------------------- |
| `DATABASE_URL`       | No        | Default: `sqlite:///data/sherlock.db`    |
| `API_FOOTBALL_KEY`   | No        | API-Football (rapidapi) para stats auto  |
| `OPENROUTER_API_KEY` | No        | OpenRouter para análisis LLM             |
| `OPENROUTER_MODEL`   | No        | Modelo LLM (ej. `anthropic/claude-3.5-sonnet`) |

---

## 📝 Licencia

MIT — Uso libre para proyectos personales y comerciales.