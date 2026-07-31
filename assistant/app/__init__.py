"""Flask application factory."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from config import Config
from .extensions import db
from .logging_config import configure_logging
from .services.actual_bridge import ActualBridgeClient
from .services.llm import LLMConfig, build_client

logger = logging.getLogger(__name__)

# Directory holding the built Vite frontend (frontend/dist copied here in Docker).
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(config_object: type[Config] = Config) -> Flask:
    Config.ensure_dirs()
    configure_logging(config_object.LOG_DIR, config_object.LOG_LEVEL)

    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_object)

    db.init_app(app)

    # Build integration clients once and stash on config.
    app.config["LLM_CLIENT"] = build_client(
        LLMConfig(
            base_url=config_object.LLM_BASE_URL,
            api_key=config_object.LLM_API_KEY,
            model=config_object.LLM_MODEL,
            timeout=config_object.LLM_TIMEOUT,
        )
    )
    app.config["BRIDGE_CLIENT"] = ActualBridgeClient(config_object.BRIDGE_BASE_URL)

    from .api import api_bp  # imported here to avoid circular imports

    app.register_blueprint(api_bp)

    _register_error_handlers(app)
    _register_frontend(app)

    with app.app_context():
        db.create_all()
        from .seeds import seed_categories

        seed_categories()

    logger.info("Assistant app initialized (llm=%s, bridge=%s)",
                bool(app.config["LLM_CLIENT"]),
                app.config["BRIDGE_CLIENT"].enabled)
    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_exc(exc: HTTPException):
        return jsonify({"error": exc.description, "code": exc.code}), exc.code or 500

    @app.errorhandler(Exception)
    def handle_uncaught(exc: Exception):  # noqa: BLE001
        logger.exception("Unhandled error: %s", exc)
        return jsonify({"error": "internal server error"}), 500


def _register_frontend(app: Flask) -> None:
    """Serve the built SPA if present; otherwise return an API-only hint."""

    @app.get("/")
    @app.get("/<path:path>")
    def serve_spa(path: str = ""):
        if path.startswith("api/"):
            return jsonify({"error": "not found"}), 404
        target = STATIC_DIR / path
        if path and target.is_file():
            return send_from_directory(STATIC_DIR, path)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return send_from_directory(STATIC_DIR, "index.html")
        return jsonify(
            {
                "service": "ai-accounting-assistant",
                "message": "Frontend build not found; API is available under /api.",
            }
        )
