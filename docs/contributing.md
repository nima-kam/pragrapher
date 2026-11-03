# Contributing

## Local workflow

1. Create and activate a Python 3.12 virtual environment in Back-end/.
2. Install requirements.txt, create a local PostgreSQL database, and copy .env.example to .env.
3. Apply migrations with flask --app wsgi:application db upgrade, then add sample content with flask --app wsgi:application seed-demo.
4. Run the API with flask --app wsgi:application run --host 127.0.0.1 --port 5000.
5. Before changing a route or model, check the generated RESTX documentation at /docs and the React client in the sibling frontend repository.

## Changes and validation

- Add schema changes as Alembic migrations; do not create tables during app startup.
- Keep credentials and secrets in local environment files. Never commit .env, uploads, virtual environments, or database dumps.
- Require authentication and enforce ownership, role, and private-community access in the API. A hidden button is not authorization.
- Validate request data before persistence and keep each multi-row change inside a database transaction.
- Run backend tests only with a PostgreSQL database named with the _test suffix.
- For browser-visible changes, update the frontend tests and screenshots in the frontend repository.
- Keep the Persian RTL interface and update both repositories' documentation when setup or contract behavior changes.

Open a pull request with the behavior changed, any migration or API compatibility notes, and the commands used to validate it.
