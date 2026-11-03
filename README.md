# Paragrapher API

<p align="center">
  <img src="docs/assets/book-page-mark.png" alt="Open book with a torn page and remembered quote marks" width="180" />
</p>

Paragrapher is a Persian, social reading space for people who want to keep a line that matters and share the conversation around it. Readers create or join communities around books and topics, post quotes in a character’s voice, and discuss them through replies and likes. Quote-of-the-day and popular feeds make memorable passages easier to discover. The book market adds listings, reservations, purchases with local non-cash book coins, and lending requests; reading groups, chat, and notifications help the conversation continue.

This repository contains the Flask API and data model for that experience. The React frontend is maintained separately in [paragrapher_frontend](https://github.com/nima-kam/paragrapher_frontend), with the interface and screenshots documented in its [README](https://github.com/nima-kam/paragrapher_frontend#readme).

## The reader experience

```mermaid
flowchart LR
    Reader[Reader] --> Communities[Book and topic communities]
    Communities --> Quotes[Character and book quotes]
    Quotes --> Discussion[Replies and likes]
    Quotes --> Discovery[Daily and popular discovery]
    Communities --> Groups[Reading groups]
    Groups --> Chat[Group and direct chat]
    Reader --> Market[Book exchange and lending]
    Chat --> Notices[Notifications]
```

The store is a local book-exchange experience. Its coins have no cash value, and the project has no payment provider.

## How the pieces connect

```mermaid
flowchart LR
    Frontend[React and Vite frontend] -->|JSON API, session cookie, and CSRF| API[Flask and RESTX at /api/v1]
    API --> Models[SQLAlchemy data layer]
    Models --> Database[(PostgreSQL 16)]
    Migrations[Alembic migrations] --> Database
    API --> Uploads[Validated image uploads]
    API --> Outbox[Email outbox and optional SMTP]
```

## Stack

- Python 3.12
- Flask 3.1.3 and Flask-RESTX 1.3.2
- SQLAlchemy 2.0, Flask-Migrate/Alembic, Psycopg 3
- PostgreSQL 16

Flask-RESTX serves the versioned JSON contract at /api/v1 and interactive API documentation at /docs.

## Quick start

Create a local PostgreSQL database owned by the current operating-system user. For example, on a local PostgreSQL installation:

    createuser --createdb "$USER"   # only when this PostgreSQL role does not exist
    createdb paragrapher

Then install and initialize the API:

    cd Back-end
    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    cp .env.example .env

Edit .env and set a private SECRET_KEY. The default database URL uses the current local PostgreSQL role; set DATABASE_URL if your local connection differs. Then:

    flask --app wsgi:application db upgrade
    flask --app wsgi:application seed-demo
    flask --app wsgi:application run --host 127.0.0.1 --port 5000

The API health check is [http://127.0.0.1:5000/health](http://127.0.0.1:5000/health), and the RESTX docs are [http://127.0.0.1:5000/docs](http://127.0.0.1:5000/docs).

### Demo accounts

The repeatable local seed creates admin, nima_reader, sara_books, and arman_quotes. Their shared local-only password is ParagrapherDemo123!. These accounts, credits, quotes, books, and messages are original sample data. Do not use demo credentials in a public deployment.

## Configuration

All settings come from environment variables or Back-end/.env:

| Variable | Purpose |
| --- | --- |
| PARAGRAPHER_ENV | development, testing, or production |
| SECRET_KEY | Flask session signing key; use a random secret outside local development |
| DATABASE_URL | SQLAlchemy URL; PostgreSQL is the supported database |
| FRONTEND_ORIGINS | Comma-separated exact origins allowed to make credentialed browser requests |
| UPLOAD_FOLDER | Private local image storage directory |
| DEMO_CREDITS_ENABLED | Local-only switch for adding non-cash demo credits |
| MAIL_MODE | console stores announcements in the outbox; smtp enables configured SMTP delivery |
| SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM | Optional mail transport settings |

The API uses an HttpOnly session cookie, exact-origin credentialed CORS, and a CSRF token required on state-changing API calls. Production mode requires a non-default secret and disables demo credit top-ups.

## API overview

All application routes are under /api/v1. Flask-RESTX's live schema and endpoint descriptions are served at /docs.

| Area | Routes |
| --- | --- |
| Session and profile | /auth/register, /auth/login, /auth/logout, /auth/me, /me, /me/password, /me/avatar |
| Communities | /communities, /communities/top, /communities/{slug}, membership, likes, categories, members, and avatar routes |
| Quotes | /quotes, /quotes/daily, /quotes/popular, /quotes/{id}, community quotes, replies, and likes |
| Discovery | /search, /search/suggestions, /communities/{slug}/search, /users/{username} |
| Book exchange | /books, listings, images, reservations, purchases, /credits/demo, discounts, and loans |
| Conversation | /groups, group membership/messages, and /chat/messages |
| Notifications | /notifications and read/clear operations |

The response envelope is {"data": ...} for successful requests and {"error":{"code":"...","message":"..."}} for API errors. Collection routes include pagination metadata where relevant. Purchases transfer demo credits only; no payment provider is configured.

## Data model and migrations

The SQLAlchemy models cover users, communities and memberships, categories, quotes/replies/likes, books and demo-credit transactions, loans, discounts, notifications, group membership and messages, and an email outbox. Entity IDs use stable integer or UUID string keys with PostgreSQL constraints and foreign keys.

The checked-out legacy repositories did not include a database export. The initial migration creates a fresh PostgreSQL schema, and `seed-demo` fills it with original Persian sample data; it does not import old MySQL users or records.

Schema creation is migration-driven. Never use startup-time create_all() for an application database. Create and apply a schema change with:

    flask --app wsgi:application db migrate -m "describe the schema change"
    flask --app wsgi:application db upgrade

The demo seed uses deterministic fixture keys and checks for existing rows, so running seed-demo repeatedly does not duplicate its sample records.

## Tests

Tests deliberately refuse to run against a database whose name does not end in _test. Create a separate PostgreSQL database, then:

    createdb paragrapher_test
    export PARAGRAPHER_TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/paragrapher_test'
    pytest

The test setup resets only the dedicated test database schema, applies the committed Alembic migrations, and then checks authentication, authorization, validation, repeatable seeding, and the API feature areas.

## Architecture and contribution

See [docs/architecture.md](docs/architecture.md) for request, session, and data-flow details and [docs/contributing.md](docs/contributing.md) for local development and change guidelines. Cross-repository changes should keep API field names and UI behavior aligned; the frontend repository links back to this one.

## License

MIT. See [LICENSE](LICENSE).
