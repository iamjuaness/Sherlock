# Modelos estadísticos por deporte

## Fútbol

### Modelo de goles (Poisson bivariado)

- **Input**: fuerza ofensiva/defensiva por equipo, factor localía, forma reciente
- **Output**: distribución de probabilidad de goles local/visitante
- **Derivados**:
  - Prob. resultado 1X2 (moneyline)
  - Prob. over/under (2.5, 3.5, etc.)
  - Prob. hándicap de goles

### Ratings ELO

- K-factor ajustable (sugerido: K=20 para ligas regulares)
- Incluye diferencia de goles como factor multiplicativo
- ELO inicial: 1500

---

## NBA

### Modelo de puntos de equipo

- **Método**: Regresión (Poisson/NegBin o lineal)
- **Features**: ritmo de juego, rating ofensivo/defensivo, días de descanso, localía
- **Derivados**:
  - Prob. ML (ganador)
  - Prob. spread de puntos
  - Prob. over/under puntos totales

### Ratings ELO (basket)

- Adaptado para diferencia de puntos
- K-factor: 20
- ELO inicial: 1500

---

## Tenis

### Ratings ELO por superficie

- Superficies: dura, arcilla, césped
- Stats auxiliares: % victorias, promedio juegos por set
- ELO inicial: 1500

### Modelo de victoria

- Prob. basada en ELO + stats básicas
- Derivar over/under de juegos/sets con modelo simple de sets

---

## Métricas de evaluación

- **Log-loss**: para probabilidades de eventos binarios
- **Brier score**: para calibración de probabilidades
- **ROI simulado**: returns si se apostara contra la línea de cierre
