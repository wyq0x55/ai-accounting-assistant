"""API blueprint registration (all under /api)."""

from __future__ import annotations

from flask import Blueprint

from .categories import categories_bp
from .health import health_bp
from .ingest import ingest_bp
from .mappings import mappings_bp
from .review import review_bp
from .stats import stats_bp

api_bp = Blueprint("api", __name__, url_prefix="/api")

for _bp in (health_bp, ingest_bp, review_bp, categories_bp, mappings_bp, stats_bp):
    api_bp.register_blueprint(_bp)
