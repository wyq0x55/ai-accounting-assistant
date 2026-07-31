"""Pytest fixtures: app + client backed by an in-memory SQLite database."""

from __future__ import annotations

import os

import pytest

# Use an isolated in-memory DB and disable external integrations.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OPENAI_BASE_URL", "")
os.environ.setdefault("BRIDGE_BASE_URL", "")

from app import create_app  # noqa: E402
from config import Config  # noqa: E402


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LLM_BASE_URL = ""
    BRIDGE_BASE_URL = ""


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
