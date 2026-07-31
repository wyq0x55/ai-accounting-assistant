"""Merchant mapping (self-learning store) management endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import LearningEvent, MerchantMapping
from ..services.classifier import normalize_merchant

mappings_bp = Blueprint("mappings", __name__)


@mappings_bp.get("/mappings")
def list_mappings():
    items = (
        MerchantMapping.query.order_by(MerchantMapping.hit_count.desc())
        .limit(500)
        .all()
    )
    return jsonify({"items": [m.to_dict() for m in items]})


@mappings_bp.post("/mappings")
def upsert_mapping():
    data = request.get_json(silent=True) or {}
    merchant = (data.get("merchant_name") or data.get("merchant") or "").strip()
    category = (data.get("category") or "").strip()
    if not merchant or not category:
        return jsonify({"error": "merchant and category are required"}), 400
    key = normalize_merchant(merchant)
    row = MerchantMapping.query.filter_by(merchant_key=key).first()
    if row is None:
        row = MerchantMapping(
            merchant_key=key, merchant_name=merchant, category=category, hit_count=0
        )
        db.session.add(row)
    else:
        row.category = category
    db.session.commit()
    return jsonify(row.to_dict()), 201


@mappings_bp.delete("/mappings/<int:mapping_id>")
def delete_mapping(mapping_id: int):
    row = MerchantMapping.query.get_or_404(mapping_id)
    db.session.delete(row)
    db.session.commit()
    return jsonify({"status": "deleted", "id": mapping_id})


@mappings_bp.get("/learning/events")
def list_learning_events():
    items = (
        LearningEvent.query.order_by(LearningEvent.created_at.desc()).limit(200).all()
    )
    return jsonify({"items": [e.to_dict() for e in items]})
