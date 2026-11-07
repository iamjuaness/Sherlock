# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install
uv sync
uv sync --extra dev  # include pytest + ruff

# Run server (dev)
uv run uvicorn src.ui.api.main:app --reload

# Tests
uv run pytest
uv run pytest tests/path/to/test_file.py::test_name  # single test
uv run pytest --cov=src tests

# Lint / format
uv run ruff check src
uv run ruff format src
```

Required `.env` variables: `DATABASE_URL` (default `sqlite:///data/sherlock.db`), `API_FOOTBALL_KEY`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`.

## Architecture

Multi-sport betting value detection platform. The system predicts match outcomes using Poisson + Dixon-Coles models, compares predictions against bookmaker odds, and surfaces value bets.

### Data flow

```
Watson Chrome Extension (SofaScore + Betano scraper)
  → POST /api/v1/prefill         (match stats)
  → POST /api/v1/prefill/odds    (bookmaker odds)
  → POST /api/v1/compare/football
  → Prediction engine (compare.py)
  → POST /api/v1/analysis        (persist to SQLite)
  → POST /api/v1/result          (record final score)
  → GET  /api/v1/stats/global    (dashboard KPIs)
```

### Core modules

| Path | Role |
|------|------|
| `src/ui/api/compare.py` | Prediction engine: Poisson lambdas, Dixon-Coles matrix, picks by market (4500+ lines) |
| `src/ui/api/main.py` | FastAPI app + all 30+ routes, lifespan init_db() (2700+ lines) |
| `src/ui/api/schemas.py` | Pydantic request/response models |
| `src/core/domain.py` | SQLAlchemy ORM: Team, Match, AnalysisHistory, Competition |
| `src/core/database.py` | Session factory, `init_db()`, engine |
| `src/core/math/` | Bayesian shrinkage, calibration (Platt + Isotonic), Kelly criterion, DC solver |
| `src/core/math_engine.py` | Orchestrates the math modules |
| `src/core/pick_rules_engine.py` | Categorizes picks: professional / underdog / high-confidence |
| `src/ui/api/admin_routes.py` | Admin endpoints (league penalties, rules) |
| `watson/background.js` | Chrome MV3 service worker: SofaScore extraction + API calls |
| `watson/sofaScoreToSherlock.js` | Maps SofaScore API schema → Sherlock request schema |
| `watson/betanoOdds.js` | Betano odds scraping |

### Markets covered

1X2, BTTS, Over/Under (goals, corners, cards, shots, fouls), Double Chance, Exact Score.

### Static data files

| File | Contents |
|------|----------|
| `data/league_penalties.json` | 337+ blacklist rules (market family + side per league) |
| `data/calculated_league_params.json` | League-wide priors (avg goals, corners, etc.) |
| `data/league_profiles.json` | LRS (League Reliability Score) + historical performance |
| `data/season_starts.json` | Season start dates per competition |

### Frontend

Vanilla JS + Jinja2 templates. No build step. Routes: `/compare` (comparator UI), `/main-dashboard` (KPIs + charts), `/leagues`, `/rules` (blacklist admin).

### Chrome extension (watson/)

Manifest V3. Load unpacked from `watson/` in `chrome://extensions`. `competitions.json` maps tournament names to SofaScore IDs.

## Key design notes

- **Bayesian shrinkage priors:** `prior_n=5` for goals/corners, `prior_n=10` for cards, `prior_n=2` for fouls/offsides. Changing these shifts all predictions.
- **Dixon-Coles correction** applies only when both lambdas < 1 (low-scoring markets). Do not apply it unconditionally.
- **League penalties** are enforced at pick-generation time in `pick_rules_engine.py`. Add new rules via `/rules` UI or directly in `league_penalties.json`.
- **SQLite WAL mode** is active (`sherlock.db-shm` / `sherlock.db-wal`). Never delete WAL files while the server is running.
- `compare.py` and `main.py` are intentionally large monoliths; extract only when a clear domain boundary exists.

## Vault de Obsidian (cerebro digital)

- El vault de este proyecto es `C:\Users\cardo\OneDrive\Escritorio\Juanes\Me\03_Memoria_Procedimental\Proyectos`. Es el cerebro digital del usuario en Obsidian.
- Contexto del proyecto: si en ese vault no existe una nota de contexto de Sherlock, crearla antes de seguir trabajando. Si ya existe, leerla y mantenerla actualizada.
- Cambios: tras cada cambio relevante en el repo, agregar una anotación breve en la nota de Sherlock del vault (qué cambió, archivos afectados, fecha absoluta).
