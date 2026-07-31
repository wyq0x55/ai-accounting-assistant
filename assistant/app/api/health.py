"""Health and status endpoints."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    llm = current_app.config.get("LLM_CLIENT")
    bridge = current_app.config.get("BRIDGE_CLIENT")
    bridge_ok = False
    bridge_detail = "disabled"
    if bridge and bridge.enabled:
        try:
            bridge.health()
            bridge_ok = True
            bridge_detail = "ok"
        except Exception as exc:  # noqa: BLE001
            bridge_detail = str(exc)
    return jsonify(
        {
            "status": "ok",
            "llm_enabled": bool(llm and getattr(llm, "enabled", False)),
            "bridge_enabled": bool(bridge and bridge.enabled),
            "bridge_reachable": bridge_ok,
            "bridge_detail": bridge_detail,
        }
    )
