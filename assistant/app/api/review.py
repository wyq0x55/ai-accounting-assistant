"""Pending-review queue and transaction actions."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..models import Transaction
from ..services import pipeline
from ..services import state_machine as sm

review_bp = Blueprint("review", __name__)


@review_bp.get("/transactions")
def list_transactions():
    """List transactions, optionally filtered by state or review bucket."""
    state = request.args.get("state")
    bucket = request.args.get("bucket")  # 'auto' | 'manual'
    query = Transaction.query.filter(Transaction.state != sm.DELETED)
    if state:
        query = query.filter_by(state=state)

    review_threshold = current_app.config["REVIEW_THRESHOLD"]
    items = query.order_by(Transaction.created_at.desc()).limit(500).all()

    result = []
    for tx in items:
        d = tx.to_dict()
        d["needs_manual"] = (tx.confidence or 0) < review_threshold
        if bucket == "manual" and not d["needs_manual"]:
            continue
        if bucket == "auto" and d["needs_manual"]:
            continue
        result.append(d)
    return jsonify({"count": len(result), "items": result})


@review_bp.get("/transactions/<int:tx_id>")
def get_transaction(tx_id: int):
    tx = Transaction.query.get_or_404(tx_id)
    return jsonify(tx.to_dict())


@review_bp.patch("/transactions/<int:tx_id>")
def update_transaction(tx_id: int):
    data = request.get_json(silent=True) or {}
    allowed = {"amount", "merchant", "category", "direction", "book", "date"}
    fields = {k: v for k, v in data.items() if k in allowed}
    tx = pipeline.update_transaction(tx_id, **fields)
    return jsonify(tx.to_dict())


@review_bp.post("/transactions/<int:tx_id>/confirm")
def confirm_transaction(tx_id: int):
    try:
        tx = pipeline.confirm_transaction(tx_id)
    except sm.InvalidTransition as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(tx.to_dict())


@review_bp.delete("/transactions/<int:tx_id>")
def delete_transaction(tx_id: int):
    pipeline.delete_transaction(tx_id)
    return jsonify({"status": "deleted", "id": tx_id})


@review_bp.post("/sync/retry")
def retry_sync():
    return jsonify(pipeline.retry_sync())
