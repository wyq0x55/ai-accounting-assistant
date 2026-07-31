"""SQLAlchemy models for the assistant's local database.

The assistant owns: the parsing queue / local transaction mirror, learned
merchant mappings, categories, and learning events. Actual Budget remains the
canonical ledger for balances, budgets and family sharing.
"""

from __future__ import annotations

from datetime import datetime, date as date_cls

from .extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "is_default": self.is_default}


class MerchantMapping(db.Model):
    """Learned merchant -> category mapping (self-learning store)."""

    __tablename__ = "merchant_mappings"

    id = db.Column(db.Integer, primary_key=True)
    merchant_key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    merchant_name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    hit_count = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "merchant_key": self.merchant_key,
            "merchant_name": self.merchant_name,
            "category": self.category,
            "hit_count": self.hit_count,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Transaction(db.Model):
    """Local transaction / pending-review queue item."""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    raw_text = db.Column(db.Text, default="")
    source_channel = db.Column(db.String(32), default="text")  # text|csv|api

    amount = db.Column(db.Float, nullable=True)
    merchant = db.Column(db.String(128), nullable=True)
    direction = db.Column(db.String(16), default="expense")  # expense|income|transfer
    pay_method = db.Column(db.String(32), nullable=True)
    category = db.Column(db.String(64), nullable=True)
    book = db.Column(db.String(64), default="personal")

    confidence = db.Column(db.Float, default=0.0)
    classify_source = db.Column(db.String(16), default="fallback")
    state = db.Column(db.String(24), default="detected", index=True)

    tx_date = db.Column(db.Date, default=date_cls.today, nullable=False)

    # Sync to Actual Budget.
    synced = db.Column(db.Boolean, default=False, nullable=False)
    actual_txn_id = db.Column(db.String(64), nullable=True)
    sync_error = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "raw_text": self.raw_text,
            "source_channel": self.source_channel,
            "amount": self.amount,
            "merchant": self.merchant,
            "direction": self.direction,
            "pay_method": self.pay_method,
            "category": self.category,
            "book": self.book,
            "confidence": round(self.confidence or 0, 3),
            "classify_source": self.classify_source,
            "state": self.state,
            "date": self.tx_date.isoformat() if self.tx_date else None,
            "synced": self.synced,
            "actual_txn_id": self.actual_txn_id,
            "sync_error": self.sync_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LearningEvent(db.Model):
    """Audit trail of user corrections that drive self-learning."""

    __tablename__ = "learning_events"

    id = db.Column(db.Integer, primary_key=True)
    merchant_key = db.Column(db.String(128), index=True)
    merchant_name = db.Column(db.String(128))
    old_category = db.Column(db.String(64), nullable=True)
    new_category = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "merchant_key": self.merchant_key,
            "merchant_name": self.merchant_name,
            "old_category": self.old_category,
            "new_category": self.new_category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
