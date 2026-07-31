"""Self-learning: persist and reuse merchant -> category mappings."""

from __future__ import annotations

import logging
from typing import Optional

from ..extensions import db
from ..models import LearningEvent, MerchantMapping
from .classifier import normalize_merchant

logger = logging.getLogger(__name__)


def mapping_lookup(merchant_key: str) -> Optional[str]:
    """Return the learned category for a normalized merchant key, or None."""
    if not merchant_key:
        return None
    row = MerchantMapping.query.filter_by(merchant_key=merchant_key).first()
    return row.category if row else None


def touch_mapping(merchant_key: str) -> None:
    """Increment hit counter when a mapping is successfully reused."""
    row = MerchantMapping.query.filter_by(merchant_key=merchant_key).first()
    if row:
        row.hit_count += 1
        db.session.commit()


def learn(merchant: Optional[str], category: str, *, from_correction: bool) -> None:
    """Create or update a merchant mapping and record a learning event."""
    key = normalize_merchant(merchant)
    if not key or not category:
        return

    row = MerchantMapping.query.filter_by(merchant_key=key).first()
    old_category = row.category if row else None

    if row is None:
        row = MerchantMapping(
            merchant_key=key,
            merchant_name=merchant,
            category=category,
            hit_count=1,
        )
        db.session.add(row)
    else:
        row.category = category
        if from_correction:
            row.hit_count = max(1, row.hit_count)

    if from_correction and old_category != category:
        db.session.add(
            LearningEvent(
                merchant_key=key,
                merchant_name=merchant,
                old_category=old_category,
                new_category=category,
            )
        )
        logger.info(
            "Learned correction: %s '%s' -> '%s'", merchant, old_category, category
        )
    db.session.commit()
