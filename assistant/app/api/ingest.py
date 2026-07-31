"""Ingestion endpoints: manual text share and CSV import."""

from __future__ import annotations

import csv
import io
import logging

from flask import Blueprint, jsonify, request

from ..services import pipeline

logger = logging.getLogger(__name__)
ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.post("/ingest/text")
def ingest_text():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "field 'text' is required"}), 400
    book = data.get("book") or "personal"
    tx = pipeline.ingest_text(text, book=book, source_channel="text")
    return jsonify(tx.to_dict()), 201


@ingest_bp.post("/ingest/manual")
def ingest_manual():
    """Structured quick-entry from the keypad page."""
    data = request.get_json(silent=True) or {}
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify({"error": "field 'amount' must be a number"}), 400
    category = (data.get("category") or "").strip()
    if not category:
        return jsonify({"error": "field 'category' is required"}), 400
    if amount <= 0:
        return jsonify({"error": "amount must be greater than 0"}), 400

    tx = pipeline.ingest_manual(
        amount=amount,
        category=category,
        merchant=(data.get("merchant") or "").strip() or None,
        direction=data.get("direction") or "expense",
        book=data.get("book") or "personal",
        note=(data.get("note") or "").strip() or None,
        auto_confirm=bool(data.get("auto_confirm", True)),
    )
    return jsonify(tx.to_dict()), 201


@ingest_bp.post("/ingest/csv")
def ingest_csv():
    """Import a CSV of raw messages.

    Accepts either a multipart file field named 'file' or a JSON body with a
    'csv' string. Expected columns (header, case-insensitive): text[, book].
    A single 'text' column is enough; amount/merchant are parsed from it.
    """
    content = None
    if "file" in request.files:
        content = request.files["file"].read().decode("utf-8", "ignore")
    else:
        data = request.get_json(silent=True) or {}
        content = data.get("csv")
    if not content:
        return jsonify({"error": "provide a 'file' upload or 'csv' text"}), 400

    reader = csv.DictReader(io.StringIO(content))
    created = []
    for row in reader:
        norm = {k.lower().strip(): v for k, v in row.items() if k}
        text = (norm.get("text") or "").strip()
        if not text:
            continue
        book = (norm.get("book") or "personal").strip()
        tx = pipeline.ingest_text(text, book=book, source_channel="csv")
        created.append(tx.to_dict())
    return jsonify({"imported": len(created), "items": created}), 201
