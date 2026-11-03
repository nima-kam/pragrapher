from __future__ import annotations

import os
from pathlib import Path

import pytest
from flask_migrate import upgrade
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from extensions import db


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def app():
    database_url = os.getenv("PARAGRAPHER_TEST_DATABASE_URL", "")
    parsed = make_url(database_url) if database_url else None
    if not parsed or not parsed.database or not parsed.database.endswith("_test"):
        raise RuntimeError(
            "Set PARAGRAPHER_TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test."
        )
    if parsed.get_backend_name() != "postgresql":
        raise RuntimeError("The Paragrapher test suite requires PostgreSQL.")

    application = create_app({
        "TESTING": True,
        "ENVIRONMENT": "testing",
        "SECRET_KEY": "pytest-only-session-key",
        "SQLALCHEMY_DATABASE_URI": database_url,
        "FRONTEND_ORIGINS": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "UPLOAD_FOLDER": str(ROOT / "instance" / "test-uploads"),
        "DEMO_CREDITS_ENABLED": True,
        "MAIL_MODE": "console",
    })
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture(autouse=True)
def reset_test_database(app):
    with app.app_context():
        with db.engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
        upgrade(directory=str(ROOT / "migrations"))
    yield


@pytest.fixture
def client(app):
    return app.test_client()
