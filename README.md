# Sherlock 🕵️‍♂️ – Multi-Sport Analytics Platform

Sherlock es una plataforma avanzada de análisis deportivo diseñada para identificar valor en mercados de apuestas mediante modelos matemáticos y estadísticas granulares. Actualmente centrada en **fútbol**, con soporte en desarrollo para NBA y Tenis.

## 🚀 Funcionalidades Principales

- **Dashboard Interactivo**: Interfaz web premium para la comparación de equipos en tiempo real.
- **Granularidad Condicional**: Análisis diferenciado de estadísticas según la condición del partido (**Local/Visitante**).
- **Motor Engine Poisson**: Cálculo probabilístico para mercados de 1X2, Over/Under, Marcador Exacto y Hándicaps.
- **Integración con API-Football**: Carga automática de estadísticas de ligas principales para evitar entrada manual.
- **Calculadora de Valor (Value Betting)**: Identificación de "Edge" comparando las probabilidades del modelo contra las cuotas de las casas de apuestas.
- **Adaptadores Extensibles**: Estructura preparada para múltiples fuentes de datos (TheSportsDB, BallDontLie, etc.).

---

## 📊 Estadísticas Recolectadas (Fútbol)

El modelo utiliza una amplia gama de métricas para alimentar el motor de inferencia:

### ⚔️ Ofensivas e Inferencia de Goles
- **Goles por Juego (Local/Visita)**: Promedio real de anotación.
- **xG (Expected Goals)**: Calidad de las ocasiones generadas.
- **Big Chances**: Grandes oportunidades creadas vs. falladas.
- **Remates**: Totales y a puerta (Shots on Target).
- **Conversión**: Porcentaje de efectividad frente al arco.

### 🛡️ Defensivas
- **Goles Concedidos (Local/Visita)**: Promedio de goles recibidos.
- **xGA (Expected Goals Against)**: Goles esperados en contra según la peligrosidad del rival.
- **Clean Sheets (Home/Away)**: Capacidad de mantener la portería a cero por condición.
- **Saves**: Atajadas del portero por juego.

### 🧠 Control y Táctica
- **Posesión**: Control del balón porcentual.
- **Pases**: Completados, Precisión total y Precisión en campo rival.
- **Manejo de Balón (Calculados)**: 
    - *Pases Totales Intentados*: `(Pases Completados * 100) / Precisión`.
    - *Pases Intentados Campo Rival*: `(Pases Campo Rival * 100) / Precisión Rival`.
    - *Centros Totales*: `(Centros Completados * 100) / Precisión de Centros`.

### 🟨 Disciplina y Otros
- **Faltas**: Promedio de infracciones cometidas.
- **Tarjetas Amarillas**: Promedio global de amonestaciones.
- **Tarjetas Rojas**: Impacto en la agresividad del equipo.
- **Corners**: Generados por el equipo y concedidos por el rival.

---

## 📐 Fórmulas y Modelado Matemático

### 1. Distribución de Poisson
Utilizada para calcular la probabilidad de que ocurran `k` eventos (goles, corners, tarjetas) en un tiempo determinado:
$$P(k; \lambda) = \frac{\lambda^k e^{-\lambda}}{k!}$$
Donde $\lambda$ es el promedio esperado de eventos.

### 2. Bayesian Shrinkage (Regresión a la Media)
Para estabilizar datos en muestras pequeñas (pocos partidos), Sherlock aplica una regresión hacia el promedio de la liga:
$$w = \frac{\text{prior\_n}}{\text{prior\_n} + n}$$
$$\lambda_{\text{final}} = \lambda_{\text{ajustado}} \cdot (1 - w) + \lambda_{\text{liga}} \cdot w$$
*Esto evita sobreestimar a equipos con rachas atípicas en muestras cortas.*

### 3. Cálculo de Lambdas ($\lambda$)
- **Goles ($\lambda_{goals}$)**:
  Se calcula cruzando la **Fuerza de Ataque** (hibridación de Goles y xG) del atacante con la **Debilidad Defensiva** del rival, ajustado por señales tácticas como la creación de *Big Chances*.
- **Corners ($\lambda_{corners}$)**:
  Hibridación del 70% del historial de corners y 30% del volumen de centros efectivos, cruzado con el ratio de corners concedidos del oponente.
- **Tarjetas ($\lambda_{cards}$)**:
  Basado en la agresividad propia (Faltas + Tarjetas) y un **Factor de Provocación** del rival (basado en posesión y duelos ganados en piso).

### 4. Análisis de Valor (Value Betting)
El sistema identifica valor si la probabilidad del modelo es significativamente mayor a la implícita en la cuota:
$$\text{Edge} = P(\text{modelo}) - P(\text{justa\_bookie})$$
*Donde $P(\text{justa\_bookie})$ se calcula eliminando el **overround** (margen) de la casa de apuestas.*

---

## 🛠️ Requisitos e Instalación

1. **Instalar dependencias**:
   ```bash
   uv sync
   ```
2. **Configurar Entorno**:
   Copiar `.env.example` a `.env` y configurar las API Keys de `API-FOOTBALL`.
3. **Ejecutar**:
   ```bash
   uv run uvicorn src.ui.api.main:app --reload
   ```

---

## 🗺️ Roadmap
- [ ] **NBA Engine**: Implementación de Rating Ofensivo/Defensivo y Ritmo (Pace).
- [ ] **Tennis Engine**: Modelo basado en ELO y retención de servicios por superficie.
- [ ] **AI Agents**: Integración de LLMs para análisis cualitativo (noticias, lesiones, clima).
- [ ] **Database Persistence**: Histórico de predicciones en SQLite.
