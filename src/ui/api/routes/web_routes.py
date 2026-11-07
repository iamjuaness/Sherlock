"""Rutas web de la API (extraídas de main.py)."""

from __future__ import annotations

from fastapi import Request
import os

from src.ui.api.shared import WEB_DIR, file_version, templates
from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["Web UI"])
def serve_main_dashboard(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    js_path = os.path.join(WEB_DIR, "static", "js", "dashboard_main.js")

    js_ver = "1"
    if os.path.exists(js_path):
        js_ver = file_version(js_path)

    return templates.TemplateResponse(
        request=request,
        name="main_dashboard.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
            "js_version": js_ver,
        },
    )


@router.get("/compare", tags=["Web UI"])
def serve_dashboard(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    js_path = os.path.join(WEB_DIR, "static", "js", "comparator.js")

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
            "js_version": file_version(js_path),
        },
    )


@router.get("/leagues", tags=["Web UI"])
def serve_leagues(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    js_path = os.path.join(WEB_DIR, "static", "js", "leagues.js")

    js_ver = "1"
    if os.path.exists(js_path):
        js_ver = file_version(js_path)

    return templates.TemplateResponse(
        request=request,
        name="leagues.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
            "js_version": js_ver,
        },
    )


@router.get("/rules", tags=["Web UI"])
def serve_rules(request: Request):
    css_path = os.path.join(WEB_DIR, "static", "css", "styles.css")
    return templates.TemplateResponse(
        request=request,
        name="rules.html",
        context={
            "request": request,
            "css_version": file_version(css_path),
        },
    )
