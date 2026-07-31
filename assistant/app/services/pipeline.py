"""End-to-end ingestion pipeline gluing parser, classifier, learning and state.

State flow: detected -> ai_classified -> pending_review -> confirmed -> archived
Confirmation pushes the transaction into Actual Budget via the bridge; if the
bridge is unavailable the item stays confirmed-but-unsynced and is retried.
"""

from __future__ import annotations

import logging
from datetime import date as date_cls, datetime
from typing import Optional

from flask import current_app

from ..extensions import db
from ..models import Category, Transaction
from . import learning, state_machine as sm
from .actual_bridge import BridgeError
from .classifier import classify
from .parser import parse_text

logger = logging.getLogger(__name__)


def _categories() -> list[str]:
    return [c.name for c in Category.query.order_by(Category.id).all()]


def _llm_client():
    return current_app.config.get("LLM_CLIENT")


def _bridge_client():
    return current_app.config.get("BRIDGE_CLIENT")


def ingest_text(
    text: str,
    *,
    book: str = "personal",
    source_channel: str = "text",
    tx_date: Optional[date_cls] = None,
) -> Transaction:
    """Parse, classify and persist one raw message as a queue item."""
    parsed = parse_text(text)

    tx = Transaction(
        raw_text=parsed.raw_text,
        source_channel=source_channel,
        amount=parsed.amount,
        merchant=parsed.merchant,
        direction=parsed.direction,
        pay_method=parsed.pay_method,
        book=book,
        state=sm.DETECTED,
        tx_date=tx_date or date_cls.today(),
    )

    # detected -> ai_classified
    result = classify(
        parsed.merchant,
        parsed.raw_text,
        mapping_lookup=learning.mapping_lookup,
        llm_client=_llm_client(),
        categories=_categories(),
    )
    tx.category = result.category
    tx.confidence = result.confidence
    tx.classify_source = result.source
    tx.state = sm.transition(tx.state, sm.AI_CLASSIFIED)

    if result.source == "mapping":
        key = learning.normalize_merchant(parsed.merchant)
        learning.touch_mapping(key)

    # ai_classified -> pending_review (always land in the review queue)
    tx.state = sm.transition(tx.state, sm.PENDING_REVIEW)

    db.session.add(tx)
    db.session.commit()
    logger.info(
        "Ingested tx#%s amount=%s merchant=%s cat=%s conf=%.2f via=%s",
        tx.id, tx.amount, tx.merchant, tx.category, tx.confidence, tx.classify_source,
    )
    return tx


def ingest_manual(
    *,
    amount: float,
    category: str,
    merchant: Optional[str] = None,
    direction: str = "expense",
    book: str = "personal",
    tx_date: Optional[date_cls] = None,
    note: Optional[str] = None,
    auto_confirm: bool = True,
) -> Transaction:
    """Create a fully user-specified entry from the quick-entry keypad.

    The user already chose amount and category, so the item is high-confidence
    and (by default) confirmed immediately, matching the "users only confirm"
    philosophy for manual entries.
    """
    tx = Transaction(
        raw_text=note or "",
        source_channel="manual",
        amount=float(amount),
        merchant=merchant,
        direction=direction,
        category=category,
        book=book,
        confidence=1.0,
        classify_source="manual",
        state=sm.PENDING_REVIEW,
        tx_date=tx_date or date_cls.today(),
    )
    db.session.add(tx)
    db.session.commit()

    # Manual entries teach the merchant mapping too.
    if merchant and category:
        learning.learn(merchant, category, from_correction=False)

    if auto_confirm:
        return confirm_transaction(tx.id)
    return tx


def update_transaction(tx_id: int, **fields) -> Transaction:
    """Apply user edits (amount/category/merchant/direction/book/date)."""
    tx = Transaction.query.get_or_404(tx_id)
    corrected_category = False

    if "amount" in fields and fields["amount"] is not None:
        tx.amount = float(fields["amount"])
    if "merchant" in fields:
        tx.merchant = fields["merchant"]
    if "direction" in fields and fields["direction"]:
        tx.direction = fields["direction"]
    if "book" in fields and fields["book"]:
        tx.book = fields["book"]
    if "date" in fields and fields["date"]:
        tx.tx_date = datetime.strptime(fields["date"], "%Y-%m-%d").date()
    if "category" in fields and fields["category"] and fields["category"] != tx.category:
        tx.category = fields["category"]
        corrected_category = True

    if corrected_category:
        # Self-learning: remember this correction for the merchant.
        learning.learn(tx.merchant, tx.category, from_correction=True)
        tx.classify_source = "mapping"
        tx.confidence = 0.98

    db.session.commit()
    return tx


def confirm_transaction(tx_id: int) -> Transaction:
    """Confirm a pending item and attempt to sync it into Actual Budget."""
    tx = Transaction.query.get_or_404(tx_id)
    if tx.state not in (sm.PENDING_REVIEW, sm.CONFIRMED):
        raise sm.InvalidTransition(f"cannot confirm from state '{tx.state}'")

    tx.state = sm.transition(tx.state, sm.CONFIRMED) if tx.state == sm.PENDING_REVIEW else tx.state

    # Reinforce learning on confirm (merchant -> chosen category).
    if tx.merchant and tx.category:
        learning.learn(tx.merchant, tx.category, from_correction=False)

    db.session.commit()
    _sync_one(tx)
    return tx


def delete_transaction(tx_id: int) -> None:
    tx = Transaction.query.get_or_404(tx_id)
    tx.state = sm.DELETED
    db.session.commit()


def _sync_one(tx: Transaction) -> None:
    """Push a confirmed transaction to Actual Budget; tolerate failure."""
    bridge = _bridge_client()
    account_id = current_app.config.get("ACTUAL_DEFAULT_ACCOUNT_ID")
    if not bridge or not bridge.enabled or not account_id:
        tx.sync_error = "bridge/account not configured; kept for retry"
        db.session.commit()
        return
    try:
        res = bridge.create_transaction(
            account_id=account_id,
            amount=tx.amount or 0.0,
            payee_name=tx.merchant,
            category_name=tx.category,
            date=(tx.tx_date or date_cls.today()).isoformat(),
            notes=tx.raw_text[:200] if tx.raw_text else None,
            direction=tx.direction,
        )
        tx.actual_txn_id = str(res.get("id") or res.get("transactionId") or "")
        tx.synced = True
        tx.sync_error = None
        tx.state = sm.transition(tx.state, sm.ARCHIVED)
        db.session.commit()
        logger.info("Synced tx#%s to Actual as %s", tx.id, tx.actual_txn_id)
    except BridgeError as exc:
        tx.synced = False
        tx.sync_error = str(exc)
        db.session.commit()
        logger.warning("Sync failed for tx#%s: %s", tx.id, exc)


def retry_sync() -> dict:
    """Retry all confirmed-but-unsynced transactions."""
    pending = Transaction.query.filter_by(state=sm.CONFIRMED, synced=False).all()
    for tx in pending:
        _sync_one(tx)
    synced = sum(1 for tx in pending if tx.synced)
    return {"attempted": len(pending), "synced": synced}
