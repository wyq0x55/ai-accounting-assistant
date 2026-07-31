"""Transaction lifecycle state machine.

Flow:
    DETECTED -> AI_CLASSIFIED -> PENDING_REVIEW -> CONFIRMED -> ARCHIVED

CONFIRMED means the user approved the entry; ARCHIVED means it was
successfully pushed into Actual Budget. Any state may be DELETED.
"""

from __future__ import annotations

DETECTED = "detected"
AI_CLASSIFIED = "ai_classified"
PENDING_REVIEW = "pending_review"
CONFIRMED = "confirmed"
ARCHIVED = "archived"
DELETED = "deleted"

ALL_STATES = (DETECTED, AI_CLASSIFIED, PENDING_REVIEW, CONFIRMED, ARCHIVED, DELETED)

_ALLOWED: dict[str, set[str]] = {
    DETECTED: {AI_CLASSIFIED, DELETED},
    AI_CLASSIFIED: {PENDING_REVIEW, DELETED},
    PENDING_REVIEW: {CONFIRMED, PENDING_REVIEW, DELETED},  # self: edits allowed
    CONFIRMED: {ARCHIVED, PENDING_REVIEW, DELETED},        # re-open before sync
    ARCHIVED: {DELETED},
    DELETED: set(),
}


class InvalidTransition(Exception):
    """Raised when an illegal state transition is attempted."""


def can_transition(current: str, target: str) -> bool:
    return target in _ALLOWED.get(current, set())


def transition(current: str, target: str) -> str:
    if not can_transition(current, target):
        raise InvalidTransition(f"cannot move from '{current}' to '{target}'")
    return target
