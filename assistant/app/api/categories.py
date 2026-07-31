"""Category management endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Category

categories_bp = Blueprint("categories", __name__)


@categories_bp.get("/categories")
def list_categories():
    items = Category.query.order_by(Category.id).all()
    return jsonify({"items": [c.to_dict() for c in items]})


@categories_bp.post("/categories")
def create_category():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "field 'name' is required"}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({"error": "category already exists"}), 409
    cat = Category(name=name, is_default=False)
    db.session.add(cat)
    db.session.commit()
    return jsonify(cat.to_dict()), 201


@categories_bp.patch("/categories/<int:cat_id>")
def rename_category(cat_id: int):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "field 'name' is required"}), 400
    cat = Category.query.get_or_404(cat_id)
    cat.name = name
    db.session.commit()
    return jsonify(cat.to_dict())


@categories_bp.delete("/categories/<int:cat_id>")
def delete_category(cat_id: int):
    cat = Category.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"status": "deleted", "id": cat_id})
