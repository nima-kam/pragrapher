"""Paragrapher Flask application factory."""

from __future__ import annotations

import hmac
import logging
import secrets
from pathlib import Path

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restx import Api
from sqlalchemy.exc import IntegrityError

from config import Config
from extensions import db

migrate = Migrate()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=app.config["LOG_LEVEL"])

    if app.config["ENVIRONMENT"] == "production" and (
        not app.config["SECRET_KEY_CONFIGURED"] or len(app.config["SECRET_KEY"]) < 32
    ):
        raise RuntimeError("Set a private SECRET_KEY of at least 32 characters in production.")

    db.init_app(app)
    migrate.init_app(app, db, directory=str(Path(__file__).resolve().parent / "migrations"))

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGINS"]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "X-CSRF-Token"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    @app.before_request
    def csrf_guard():
        if request.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            expected = session.get("csrf_token", "")
            supplied = request.headers.get("X-CSRF-Token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                return jsonify(error={"code": "csrf_failed", "message": "Refresh the page and try again."}), 403
        return None

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="paragrapher-api")

    api = Api(
        app,
        version="1.0",
        title="Paragrapher API",
        description="Versioned API for the Paragrapher reading and community app.",
        prefix="/api/v1",
        doc="/docs",
        validate=True,
        catch_all_404s=True,
    )

    from api import register_resources
    from models import User  # noqa: F401 - registers model metadata for migrations

    register_resources(api)
    from seed import register_cli
    register_cli(app)

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        db.session.rollback()
        app.logger.info("Database constraint rejected a request: %s", error.__class__.__name__)
        return jsonify(error={"code": "conflict", "message": "That change conflicts with existing data."}), 409

    @app.errorhandler(413)
    def file_too_large(_error):
        return jsonify(error={"code": "file_too_large", "message": "Images must be 3 MB or smaller."}), 413

    @app.get("/api/v1/auth/csrf")
    def csrf_token():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return jsonify(csrf_token=token)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["ENVIRONMENT"] == "development")
