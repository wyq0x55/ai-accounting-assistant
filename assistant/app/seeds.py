"""Seed default data (categories)."""

from __future__ import annotations

import logging

from .extensions import db
from .models import Category
from .services.classifier import DEFAULT_CATEGORIES

logger = logging.getLogger(__name__)


def seed_categories() -> None:
    existing = {c.name for c in Category.query.all()}
    added = 0
    for name in DEFAULT_CATEGORIES:
        if name not in existing:
            db.session.add(Category(name=name, is_default=True))
            added += 1
    if added:
        db.session.commit()
        logger.info("Seeded %d default categories", added)
