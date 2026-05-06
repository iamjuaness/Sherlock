# Refactorización Sherlock: Motor de Análisis Profesional (Fútbol)

Se ha completado la refactorización integral del sistema para cumplir con los estándares de un Quantitative Engineer senior. El sistema ahora es más conservador, matemáticamente preciso y transparente en cuanto a la calidad de los datos.

## 1. Consistencia Matemática (Poisson & Asian Handicap)
- **Liquidación Real de AH**: Implementación de `_compute_asian_handicap_probs` que utiliza la matriz de Poisson/Dixon-Coles para calcular probabilidades exactas de WIN, HALF-WIN, PUSH, HALF-LOSS y LOSS.
- **Poisson O/U Profesional**: Modificada la función `_poisson_over_under` para devolver el PUSH explícitamente en lugar de redistribuirlo artificialmente.
- **Cálculo de Edge (EV)**: El Edge ahora se calcula como Valor Esperado real: `(P_win * Cuota) + (P_push * 1) - 1`, asegurando sincronía total entre Backend y Frontend.

## 2. Modelo de Confianza y Calidad (Data Quality Score)
- **Tiers de Confianza**: Los mercados se clasifican en:
  - `segmented` (Alta): 1X2, Goles, AH (basados en stats Home/Away).
  - `hybrid` (Media): Corners.
  - `global` (Baja): Tarjetas, Tiros (basados en promedios globales).
- **Data Quality Score (0-100)**: Cada pick incluye un score de calidad que penaliza muestras pequeñas (< 12 partidos) y falta de métricas avanzadas (xG).
- **Variance Tiers**: Clasificación de volatilidad por mercado (`low`, `medium`, `high`).

## 3. Filtrado "Publishable" (Filtro Profesional)
- Se ha separado el **Value Matemático** del **Pick Publicable**.
- Un pick solo es `is_publishable` si:
  - Probabilidad > 54%.
  - Edge Real > 2.5% (superando el overround).
  - Data Quality > 45.
  - Penalizaciones dinámicas por cuotas altas (> 2.75) y mercados de alta varianza.

## 4. Optimización de Inteligencia Artificial (LLM)
- **Prioridad Absoluta**: El LLM solo recibe picks que han superado el filtro `is_publishable`.
- **Análisis Táctico**: El prompt ha sido reescrito para priorizar la ventaja de localía segmentada y prohibir la invención de picks si el sistema detecta "No Bet".
- **Transparencia**: El análisis ahora menciona explícitamente la solidez de los datos y el soporte estadístico.

## 5. Alineación de Interfaz (Frontend)
- **Visualización de Calidad**: El frontend ahora muestra el `% de Confianza de Datos` y el `Tier` del mercado.
- **Sincronización del Checker**: El calculador en tiempo real ha sido actualizado para usar la misma fórmula de Edge con PUSH que el backend.
- **Labels Profesionales**: Los picks se etiquetan como `🎯 PROFESIONAL` o `⚖️ VALOR` según su cumplimiento de los nuevos estándares.

---
**Resultado Final**: El motor Sherlock ha pasado de ser un estimador estadístico básico a un sistema de selección de picks con rigor profesional, minimizando falsos positivos en mercados volátiles.
