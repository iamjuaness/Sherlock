# Fuentes de datos – APIs

## Fútbol

### API-Football (api-sports.io)

- **Sitio**: https://www.api-football.com
- **Base URL**: `https://v3.football.api-sports.io`
- **Auth**: Header `x-apisports-key`
- **Plan gratuito**: 100 requests/día
- **Endpoints principales**:
  - `GET /leagues` – ligas y copas disponibles
  - `GET /fixtures` – partidos por liga, fecha, temporada
  - `GET /fixtures/statistics` – stats de un partido
  - `GET /standings` – tabla de posiciones
  - `GET /teams/statistics` – stats de equipo en temporada
  - `GET /odds` – cuotas (planes premium)
- **Rate limit**: 10 req/min (plan free)
- **Cobertura**: 1200+ ligas

### TheSportsDB

- **Sitio**: https://www.thesportsdb.com
- **Base URL**: `https://www.thesportsdb.com/api/v1/json/3`
- **Auth**: API key en URL (key `3` = demo gratuita)
- **Endpoints principales**:
  - `searchallleagues.php?s=Soccer` – ligas de fútbol
  - `eventsseason.php?id={league_id}&s={season}` – eventos de temporada
  - `lookupevent.php?id={event_id}` – detalle de evento
  - `lookupteam.php?id={team_id}` – info de equipo
- **Límites**: sin rate limit documentado, uso razonable

---

## NBA

### BallDontLie API

- **Sitio**: https://www.balldontlie.io
- **Base URL**: `https://api.balldontlie.io/v1`
- **Auth**: Header `Authorization`
- **Endpoints principales**:
  - `GET /teams` – todos los equipos NBA
  - `GET /players` – jugadores (paginado)
  - `GET /games` – partidos por temporada/fecha
  - `GET /stats` – stats de jugador por partido
  - `GET /season_averages` – promedios de temporada
- **Rate limit**: 30 req/min (plan free)
- **Cobertura**: NBA desde 1946

---

## Tenis

### TheSportsDB (Tenis)

- Misma API que fútbol, filtrado por `s=Tennis`
- **Endpoints**:
  - `searchallleagues.php?s=Tennis` – torneos ATP/WTA
  - `eventsseason.php?id={league_id}&s={season}` – eventos de torneo
- **Limitaciones**: datos básicos (resultados, no stats detalladas)

---

## Carga manual

- Formato: CSV o Excel (.xlsx)
- Columnas mínimas para partidos:
  - `sport`, `competition`, `date`, `home_team` / `player_1`, `away_team` / `player_2`, `home_score`, `away_score`
- Columnas opcionales: `odds_home`, `odds_draw`, `odds_away`, `over_under_line`, `over_odds`, `under_odds`
