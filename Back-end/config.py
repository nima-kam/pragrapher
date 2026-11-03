"""Environment based configuration; copy .env.example for local development."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


class Config:
    ENVIRONMENT = os.getenv("PARAGRAPHER_ENV", "development").lower()
    SECRET_KEY_CONFIGURED = bool(os.getenv("SECRET_KEY"))
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg:///paragrapher"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    FRONTEND_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    SESSION_COOKIE_NAME = "paragrapher_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = ENVIRONMENT == "production"
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(ROOT / "instance" / "uploads"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    DEMO_CREDITS_ENABLED = ENVIRONMENT != "production" and os.getenv("DEMO_CREDITS_ENABLED", "true").lower() == "true"
    MAIL_MODE = os.getenv("MAIL_MODE", "console").lower()
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "Paragrapher <noreply@example.test>")
