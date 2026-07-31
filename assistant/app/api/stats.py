"""Statistics and AI monthly report endpoints."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from ..models import Transaction
from ..services import state_machine as sm
from ..services.report import compute_stats, generate_monthly_report

stats_bp = Blueprint("stats", __name__)

# States that count as real, user-approved money movements.
_COUNTED = (sm.CONFIRMED, sm.ARCHIVED)


def _load_transactions() -> list[dict]:
    rows = Transaction.query.filter(Transaction.state.in_(_COUNTED)).all()
    return [
        {
            "amount": r.amount,
            "category": r.category,
            "direction": r.direction,
            "date": r.tx_date.isoformat() if r.tx_date else "",
            "merchant": r.merchant,
        }
        for r in rows
    ]


def _prev_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    m -= 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y:04d}-{m:02d}"


@stats_bp.get("/stats")
def stats():
    month = request.args.get("month")  # YYYY-MM; default current month
    if not month:
        month = date.today().strftime("%Y-%m")
    txs = _load_transactions()
    return jsonify(compute_stats(txs, month=month))


@stats_bp.get("/report/monthly")
def monthly_report():
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    txs = _load_transactions()
    stats_now = compute_stats(txs, month=month)
    stats_prev = compute_stats(txs, month=_prev_month(month))
    report = generate_monthly_report(
        stats_now, prev_stats=stats_prev, llm_client=current_app.config.get("LLM_CLIENT")
    )
    return jsonify(report)
