# Backend architecture

## Runtime and request flow

Back-end/app.py is the Flask application factory. It configures SQLAlchemy, Flask-Migrate, exact-origin credentialed CORS, session cookies, CSRF checks, health and error handlers, and the Flask-RESTX API. Back-end/wsgi.py is the WSGI entry point.

The React client sends credentialed requests to /api/v1. The API uses an HttpOnly signed session cookie to identify a reader. Before a state-changing API operation, the client fetches /auth/csrf and includes the returned token in X-CSRF-Token. CORS permits only configured frontend origins.

Flask-RESTX resources hold request validation and route behavior in Back-end/api.py. Responses use a stable data envelope; failures use a structured error object. OpenAPI/Swagger documentation is generated from the namespace models and route metadata.

## Persistence

SQLAlchemy models are in Back-end/models.py. PostgreSQL is the supported database; connection details come from DATABASE_URL. Alembic migrations under Back-end/migrations are the source of truth for schema changes.

Relationships use foreign keys and uniqueness/check constraints for memberships, likes, listing prices and statuses, loan states, and discount codes. Purchases lock the book and user rows in one transaction, transfer demo credits, write both ledger entries, update the listing, and create notifications.

The seed-demo CLI inserts only original local sample data and uses stable natural keys to be repeatable. It refuses to run with PARAGRAPHER_ENV=production.

## Uploads and mail

Uploads are limited by request size, accepted by decoded image format, re-encoded through Pillow, and stored below the configured upload directory. They are served through the API upload route. Email notifications are recorded in email_outbox; SMTP is optional and disabled by default.

## Repository boundary

The frontend is maintained separately at [paragrapher_frontend](https://github.com/nima-kam/paragrapher_frontend). Keep routes, request names, response fields, cookie/CSRF behavior, and UI expectations synchronized across the two repositories.
