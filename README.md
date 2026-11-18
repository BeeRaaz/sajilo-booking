# Sajilo Booking

A booking app. Business owners create a business, list their services (name, duration, price) and set their weekly opening hours. Clients open the business's public page, pick a service and a free time slot, and book it.

The project is under active development. See [ROADMAP.md](ROADMAP.md) for what is done and what is next.

## Stack

- **Backend:** FastAPI (Python 3.12), async SQLAlchemy, Alembic, managed with [uv](https://docs.astral.sh/uv/)
- **Database:** PostgreSQL 18
- **Frontend:** Next.js 16, React 19, Tailwind CSS, managed with pnpm
- **Local development:** Docker Compose

## Project layout

```
backend/    FastAPI API, database models, migrations, tests
frontend/   Next.js website
docker-compose.yml   Runs the database, backend and frontend together
```

## Run everything with Docker

Requires Docker with Compose.

1. Create the backend env file (see [backend/README.md](backend/README.md#setup)):
   `cp backend/.env.example backend/.env`, then fill in the values.
2. Start everything:

   ```bash
   docker compose up --build
   ```

   Add `-d` to run in the background.

On start, the backend waits for the database, applies the migrations, then starts with auto-reload.

| What | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health-check |

Useful commands:

```bash
docker compose logs -f backend   # follow the backend logs
docker compose down              # stop everything (database data is kept)
docker compose down -v           # stop and DELETE the database data
```

The Docker setup is for development only: the database password is hardcoded in `docker-compose.yml` and the frontend runs the dev server.

## Backend

Setup, running tests, migrations and linting are covered in [backend/README.md](backend/README.md).

## Frontend

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:3000
pnpm lint
pnpm build
```
