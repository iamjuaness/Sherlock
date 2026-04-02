# Sherlock – Multi-Sport Analytics Platform

Plataforma de análisis deportivo multi-deporte centrada en fútbol, NBA y tenis, con enfoque en mercados de apuestas y rendimiento de equipos/jugadores.

## Inicio rápido

```bash
# 1. Instalar dependencias
uv sync

# 2. Copiar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 3. Iniciar la API
uv run uvicorn src.ui.api.main:app --reload

# 4. Abrir la documentación
# http://localhost:8000/docs
```

## Estructura del proyecto

```
src/
  config.py              # Configuración (pydantic-settings)
  core/
    domain.py            # Modelo de dominio (SQLAlchemy ORM)
    database.py          # Motor y sesiones de BD
  datasources/
    base.py              # Clase abstracta para adaptadores
    football_api_football.py   # API-Football
    football_thesportsdb.py    # TheSportsDB (fútbol)
    nba_balldontlie.py         # BallDontLie (NBA)
    tennis_thesportsdb.py      # TheSportsDB (tenis)
    manual_loader.py           # Carga manual CSV/Excel
  agents/                # Agentes IA (Fase 5)
  ui/
    api/                 # FastAPI REST API
    cli/                 # CLI con Typer (Fase 4)
data/                    # Datos raw, processed, manual
docs/                    # Documentación del proyecto
notebooks/               # Prototipos y exploración
tests/                   # Tests automatizados
```

## Deportes soportados

- ⚽ **Fútbol**: Premier League, LaLiga, Serie A, UCL y más
- 🏀 **NBA**: Temporada regular y playoffs
- 🎾 **Tenis**: ATP y WTA (datos básicos)

## Documentación

- [Plan del proyecto](docs/PLAN.md)
- [APIs y fuentes de datos](docs/APIS.md)
- [Modelos estadísticos](docs/MODELS.md)
- [Agentes IA](docs/AGENTS.md)
- [Tenis – Futuras integraciones](docs/TENIS_FUTURO.md)
