"""Aplicación FastAPI: app, middlewares, lifespan y registro de routers."""

from __future__ import annotations

from fastapi import FastAPI
from src.core.database import get_db, init_db
from fastapi.staticfiles import StaticFiles
from fastapi import Request
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.ui.api.admin_routes import admin_router
from src.ui.api.routes.analysis_routes import rename_competition_matches
from src.ui.api.shared import WEB_DIR
from src.ui.api.routes import (
    web_routes,
    catalog_routes,
    prefill_routes,
    closing_odds_routes,
    results_routes,
    comparator_routes,
    analysis_routes,
    stats_routes,
    leagues_routes,
    audit_routes,
    pick_rules_routes,
    ml_routes,
)

"""FastAPI application – Sherlock REST API."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Sherlock – Multi-Sport Analytics",
    description="API for football analytics with betting market analysis.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(admin_router)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "SHERLOCK_ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_cache_in_dev(request: Request, call_next):
    response = await call_next(request)

    if request.url.path.startswith("/static") or request.url.path == "/compare":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")
if __name__ == "__main__":
    liga = "Primera A"

    # ----------Contar equipos de liga--------------------------------

    # db = next(get_db())

    # try:
    #     resultado = list_teams_count(liga, db)
    #     print(resultado)
    # finally:
    #     db.close()

    # ---------Cambiar nombre de liga---------------
    old_name = "Liga MX, Apertura"
    new_name = "Liga MX"

    db = next(get_db())
    try:
        resultado = rename_competition_matches(old_name, new_name, db)
        print(resultado)
    finally:
        db.close()

app.include_router(web_routes.router)
app.include_router(catalog_routes.router)
app.include_router(prefill_routes.router)
app.include_router(closing_odds_routes.router)
app.include_router(results_routes.router)
app.include_router(comparator_routes.router)
app.include_router(analysis_routes.router)
app.include_router(stats_routes.router)
app.include_router(leagues_routes.router)
app.include_router(audit_routes.router)
app.include_router(pick_rules_routes.router)
app.include_router(ml_routes.router)
