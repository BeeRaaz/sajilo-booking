# Sajilo Booking: Backend

FastAPI API for Sajilo Booking. Code is organised in layers: `routers` (HTTP) -> `services` (business rules) -> `repositories` (database queries) -> `models` (tables).

## Setup

Requires Python 3.12, [uv](https://docs.astral.sh/uv/) and a running PostgreSQL.

```bash
cd backend
uv sync
cp .env.example .env
cp .env.test.example .env.test
```

Then edit both files. The main variables:

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | Connection string. Must use the `postgresql+asyncpg://` scheme. |
| `JWT_SECRET_KEY` | Secret used to sign tokens. Use a long random value, never commit it. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `CORS_ORIGINS` | Allowed frontend origins, as a JSON list, e.g. `["http://localhost:3000"]`. |
| `DEBUG` | `true` or `false` (default `false`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Optional token lifetimes (defaults 15 minutes / 3 days). |

`.env` and `.env.test` are git-ignored. Only the `.example` files are committed.

When running through Docker Compose, `DATABASE_URL` is overridden to point at the `db` container.

## Run the API

```bash
uv run alembic upgrade head                      # create/update the tables
uv run uvicorn app.main:app --reload             # http://localhost:8000
```

Interactive docs are at http://localhost:8000/docs.

## Tests

Tests use a separate database and read `.env.test`.

1. Create an empty PostgreSQL database for tests. **Its name must contain `_test`** (for example `sajilo_booking_test`). The app refuses to start in test mode otherwise, which protects your real data, because the tests drop all tables when they finish.
2. Put its URL in `.env.test`.
3. Run:

   ```bash
   uv run pytest             # all tests
   uv run pytest -x          # stop at the first failure
   uv run pytest -k refresh  # only tests whose name contains "refresh"
   ```

Note: if a local PostgreSQL and the Docker `db` service both use port 5432, stop one of them.

## Database migrations

Schema changes are made with Alembic. Never edit a migration that has already been merged; add a new one.

```bash
uv run alembic revision --autogenerate -m "describe the change"   # create
uv run alembic upgrade head                                       # apply
uv run alembic downgrade -1                                       # undo the last one
```

Always open the generated file in `alembic/versions/` and check it before applying it.

## Linting and formatting

```bash
uv run ruff check .        # lint (add --fix to auto-fix)
uv run ruff format .       # format
```

### Pre-commit hook

Ruff can run automatically every time you `git commit`. Install the hook once per clone:

```bash
uv run pre-commit install
```

After that, a commit that contains Python files in `backend/` runs `ruff check --fix` and `ruff format` first. If a hook changes a file, the commit is aborted so you can review the changes, then `git add` them and commit again. To run the hooks on everything without committing: `uv run pre-commit run --all-files`.
