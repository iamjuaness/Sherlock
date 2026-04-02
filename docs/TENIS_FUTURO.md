# Tenis – Futuras integraciones con APIs premium

## Limitaciones actuales

TheSportsDB ofrece datos básicos de tenis (resultados de torneos ATP/WTA, eventos por temporada), pero carece de:

- Stats detalladas por partido (aces, dobles faltas, % primer servicio, break points)
- Datos punto a punto / game a game
- Cuotas de apuestas
- Rankings ATP/WTA en tiempo real

---

## APIs premium para futuras integraciones

### Sportradar Tennis API
- **Sitio**: https://developer.sportradar.com/tennis/docs
- **Cobertura**: ATP, WTA, Grand Slams, Challenger, ITF
- **Datos**: resultado punto a punto, stats detalladas, rankings, odds pre-match
- **Precio**: Bajo consulta (plan Enterprise)
- **Prioridad**: Alta (mejor cobertura de tenis)

### LSports Tennis
- **Sitio**: https://www.lsports.eu/tennis-data-api/
- **Cobertura**: 2000+ torneos, pre-match e in-play
- **Datos**: scores en vivo, stats, odds de múltiples bookmakers
- **Precio**: Bajo consulta
- **Prioridad**: Alta (excelente para mercados de apuestas)

### SportsDataIO Tennis
- **Sitio**: https://sportsdata.io/developers/coverages/tennis
- **Cobertura**: ATP, WTA, Grand Slams
- **Datos**: resultados, stats, rankings, odds
- **Precio**: Desde $25/mes (plan básico)
- **Prioridad**: Media (más accesible en precio)

---

## Plan de integración

1. Validar el modelo de dominio con datos básicos de TheSportsDB
2. Cuando haya presupuesto, evaluar SportsDataIO como primera opción premium (más barato)
3. Para producción empresarial, Sportradar o LSports
4. Los adaptadores deben seguir la misma interfaz `DataSourceAdapter` de `datasources/base.py`
