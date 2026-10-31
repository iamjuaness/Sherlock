Eres un Ingeniero Cuantitativo Senior y Desarrollador Backend especializado en Python, SciPy y Modelado Estadístico para Mercados Deportivos.

Tu objetivo es refactorizar el motor matemático y probabilístico de Sherlock en el repositorio `iamjuaness/Sherlock`, eliminando heurísticas arbitrarias, sumas fijas de porcentajes y multiplicadores empíricos, y reemplazándolos por un motor cuantitativo riguroso y modular.

---

### 1. RESTRICCIONES DE ARQUITECTURA Y COMPATIBILIDAD

1. **Preservación de Esquemas:** No modifiques los esquemas Pydantic públicos de respuesta en `src/ui/api/compare.py` (`FootballCompareResponse`, `ValueIndicator`, `MatchAnalysis`). La API hacia Watson y la UI debe responder exactamente con las mismas llaves y tipos.
2. **Modularización:** Toda la lógica matemática pura debe ubicarse en `src/core/math/`. No dejes optimizadores numéricos ni solvers implementados directamente dentro de endpoints de FastAPI o controladores.
3. **Control Numérico:** Asegúrate de que todas las matrices y probabilidades sumen exactamente 1.0 (dentro de tolerancia flotante `1e-6`) y prevén divisiones por cero (`epsilon = 1e-9`).
4. **Dependencias:** Utiliza las librerías científicas ya instaladas en el entorno (`numpy`, `scipy.optimize`, `scipy.stats`, `scikit-learn`).

---

### 2. TAREAS ESPECÍFICAS DE IMPLEMENTACIÓN

#### Tarea 1: Crear `src/core/math/dixon_coles.py`

- Implementa la función de factor de ajuste $\tau(x, y, \lambda, \mu, \rho)$:
  - $\tau(0, 0) = 1 - \lambda \mu \rho$
  - $\tau(0, 1) = 1 + \lambda \rho$
  - $\tau(1, 0) = 1 + \mu \rho$
  - $\tau(1, 1) = 1 - \rho$
  - $\tau(x, y) = 1.0$ para cualquier otro marcador.
- Implementa la función de ponderación por decaimiento temporal exponencial:
  $$\phi(t) = \exp(-\xi \cdot t)$$
  donde $t$ es la antigüedad en días y $\xi = 0.0055$ por defecto.
- Implementa `solve_dixon_coles_mle(matches, teams, xi=0.0055)`:
  - Optimiza parámetros de ataque ($\alpha$), defensa ($\beta$), ventaja de localía ($\gamma$) y dependencia ($\rho$) minimizando la Log-Verosimilitud Negativa ponderada con `scipy.optimize.minimize(method='L-BFGS-B')`.
  - Aplica la restricción de identificabilidad: $\sum \alpha_i = 0$ (o media 1 en escala original).
- Implementa `build_dixon_coles_matrix(lambda_h, mu_a, rho, max_goals=10)`:
  - Genera la matriz bivariada $(max\_goals + 1) \times (max\_goals + 1)$.
  - Normaliza la matriz para que $\sum_{x,y} P(X=x, Y=y) = 1.0$.

#### Tarea 2: Crear `src/core/math/bayesian.py`

- Elimina los valores hardcodeados de pseudo-muestras (`prior_n = 5, 10, 2`).
- Implementa la inferencia conjugada Gamma-Poisson con Empirical Bayes:
  - `fit_gamma_prior_from_league(historical_series)`:
    - Calcula la media muestral ($\mu$) y varianza muestral ($\sigma^2$) de la liga.
    - Si $\sigma^2 > \mu$, deriva:
      $$\beta = \frac{\mu}{\sigma^2 - \mu}, \quad \alpha = \mu \cdot \beta$$
    - Si $\sigma^2 \le \mu$ (subdispersión o equidipersión), usa prior defensivo no informativo ($\beta = 2.0, \alpha = 2 \mu$).
  - `update_gamma_poisson(alpha_prior, beta_prior, observed_events, matches_played)`:
    - Retorna el valor esperado a posteriori:
      $$\lambda_{\text{post}} = \frac{\alpha_{\text{prior}} + \text{observed\_events}}{\beta_{\text{prior}} + \text{matches\_played}}$$

#### Tarea 3: Crear `src/core/math/calibration.py`

- Elimina cualquier transformación de potencia artificial (`p ** 0.85` o `p ** 0.75`).
- Implementa dos calibradores con interfaz unificada (`fit` y `predict`/`predict_proba`):
  - `PlattCalibrator`: Regresión logística sobre log-odds:
    $$\text{logit}(p) = \ln\left(\frac{p}{1 - p}\right)$$
  - `IsotonicCalibrator`: Envoltura robusta alrededor de `sklearn.isotonic.IsotonicRegression(out_of_bounds="clip", y_min=0.001, y_max=0.999)`.
- Implementa `normalize_categorical_market(prob_dict)`:
  - Garantiza que cualquier conjunto de eventos exhaustivos y mutuamente excluyentes (ej. `{"home": p1, "draw": p2, "away": p3}` o `{"over": p1, "under": p2}`) sea reescalado para sumar exactamente $1.0$.

#### Tarea 4: Crear `src/core/math/kelly.py`

- Elimina la cascada de 5 multiplicadores discretos en `_calculate_stake_units`.
- Implementa `calculate_fractional_kelly(calibrated_prob, odds, fraction_divisor=8.0, max_stake_cap=0.03)`:
  - Calcula el edge esperado: $b = \text{odds} - 1$, $q = 1 - p$.
  - Si $(p \cdot \text{odds} - 1) \le 0$, retorna `stake = 0.0`.
  - Si hay edge positivo:
    $$f^* = \frac{p \cdot b - q}{b}$$
    $$\text{stake} = \min\left(\max\left(0.0, \frac{f^*}{\text{fraction\_divisor}}\right), \text{max\_stake\_cap}\right)$$
  - Retorna `(stake_fraction, edge_pct)`.

#### Tarea 5: Refactorizar `src/ui/api/compare.py`

- Importa y delega en los módulos de `src/core/math/`:
  - En `_compute_team_goals_lambda`, `_compute_team_corners_lambda` y `_compute_team_cards_lambda`: retira todas las sumas/restas de porcentajes fijos ($\pm 8\%$ por Big Chances, $\pm 15\%$ por arquero, etc.). Sustitúyelas por la contracción Bayesiana Gamma-Poisson de eventos por partido ponderada por la media de la liga.
  - Reemplaza `_default_dc_rho` por el $\rho$ derivado u optimizado de la liga.
  - Utiliza `build_dixon_coles_matrix` para obtener las probabilidades 1X2 y Over/Under.
  - Pasa las probabilidades crudas por `normalize_categorical_market` y el calibrador.
  - Reemplaza `_calculate_stake_units` por el cálculo de Fractional Kelly (1/8 de Kelly, cap 3%).

#### Tarea 6: Pruebas Unitarias

- Crea `tests/test_quantitative_math.py` con pruebas para:
  1. Que la matriz de Dixon-Coles sume 1.0 y $\tau$ corrija correctamente los marcadores $(0,0)$, $(1,0)$, $(0,1)$ y $(1,1)$.
  2. Que `update_gamma_poisson` contraiga equipos con $n=1$ hacia la media de la liga y dé mayor peso al equipo cuando $n \ge 25$.
  3. Que `normalize_categorical_market` garantice sumatoria unitaria.
  4. Que `calculate_fractional_kelly` retorne 0 cuando cuota $\times$ probabilidad $\le 1.0$ y respete estrictamente el límite superior del 3%.
  5. Que el endpoint `/compare/football` procese una solicitud mock y retorne un `FootballCompareResponse` válido.

---

### 3. FORMATO DE ENTREGA

Implementa los cambios por completo sin crear un plan de impelemntacion extra.
