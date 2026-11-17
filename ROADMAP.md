# Sajilo Booking: Roadmap

Written on 2026-11-16, starting from `main` at commit `5a98553`.
Follow the phases in order. Each phase is a small PR (or a few), and each task has a "done when" so you know when to stop.

---

## 1. Where the project stands today

### Product idea
A booking app. A **business owner** signs up, creates a business, lists services (name, duration, price) and sets weekly opening hours. A **client** opens the business's public page, picks a service and a free time slot, enters their details and books.

### Done
| Area | State |
|---|---|
| Backend skeleton | FastAPI, async SQLAlchemy 2, asyncpg, pydantic-settings, `/health-check` |
| Layering | `routers` -> `services` -> `repositories` -> `models`, wired through `app/deps.py` |
| Database | Alembic set up, one migration covering `users`, `businesses`, `services`, `bookings`, `business_availability`, `refresh_tokens` |
| Auth endpoints | `POST /auth/signup`, `/auth/login`, `/auth/refresh` (rotating refresh tokens stored in the DB), `/auth/logout` |
| Security | Argon2 password hashing, JWT (HS256) access and refresh tokens with `jti` |
| Tests | 14 tests in `backend/tests/test_auth.py` (httpx + pytest-asyncio, separate `_test` database) |
| Docker | Dev `docker-compose.yml` (db with healthcheck and volume, backend runs migrations then `--reload`, frontend `pnpm dev`) |
| Git workflow | Feature branches, conventional commits, PRs merged to `main` |

### Not done
| Area | State |
|---|---|
| Protected routes | **Nothing verifies the access token yet.** There is no `get_current_user` dependency, so no endpoint is protected. |
| Business logic | No endpoints for businesses, services, availability or bookings (the tables exist, nothing uses them) |
| Frontend | Still the untouched `create-next-app` starter page. No API client, no env var for the API URL, no pages. |
| Tooling | No linter or formatter config, no CI (`.github/` does not exist), root and backend READMEs are essentially empty |
| Production | Docker setup is development-only |

### Known problems in what exists (fix these early)
1. **`bookings` has `start_time` and `end_time` but no date** (both are `Time` columns, see `backend/app/models/booking.py`). A booking for Monday and one for Tuesday at 10:00 look identical. This needs a new migration before any booking feature. See Phase 2.
2. **Emails are case-sensitive.** `A@x.com` and `a@x.com` can both sign up. Normalize to lowercase.
3. **Concurrent duplicate signup returns a 500.** The service checks for an existing email and then inserts. Two simultaneous requests can both pass the check, and the second hits the unique constraint and raises an uncaught `IntegrityError`.
4. **No password rules.** `UserCreate.password` accepts any string, including an empty one.
5. **Emails appear in log lines** (`auth_service.py`). That is personal data in logs. Log user IDs instead.
6. **`refresh_tokens.user_id` has no index**, and expired or revoked rows are never deleted.
7. **Tests build tables with `create_all`**, not Alembic, so a broken migration would not be caught by the tests.
8. Small things:
   - Typo in test name `test_signup_sucess`.
   - `uv:latest` in `backend/Dockerfile` is unpinned.
   - The refresh-token check in `refresh_tokens` does not distinguish "reused revoked token" from "unknown token".

---

## 2. The loop to follow for every task

1. `git checkout main && git pull`
2. `git checkout -b feat/<short-name>` (use `fix/`, `chore/` or `test/` when they fit)
3. Write the code in the usual order: **model/migration -> repository -> service -> schema -> router -> tests**
4. Run the tests (see "Useful commands" below)
5. Commit small and often, using conventional commits (`feat(scope): ...`, `test(scope): ...`)
6. Push, open a PR, merge, `git fetch --prune`, delete the local branch
7. Tick the box here

Rules that keep this codebase tidy:
- Routers only translate HTTP to and from service calls (status codes, schemas). Business rules live in services. Queries live in repositories.
- Every new endpoint gets tests for the success case, validation errors, auth (401/403) and not-found.
- Every schema change is an Alembic migration. Never edit an applied migration, always add a new one.
- Anything the user can pass in goes through a pydantic schema. Never accept raw dicts.

---

## 3. Phases

### Phase 0: Tooling and housekeeping (do first, about 1 evening)

- [ ] **0.1 Linting and formatting (backend).** `cd backend && uv add --dev ruff`. Add a `[tool.ruff]` section to `pyproject.toml` (line length 88, select `E,F,I,UP,B`). Run `uv run ruff check --fix . && uv run ruff format .` and commit the result separately.
  *Done when:* `ruff check` and `ruff format --check` pass.
- [ ] **0.2 README files.** Root README: what the project is, the stack, and the 3 commands to run everything (`docker compose up --build`, URLs, how to run tests). Backend README: env vars (copy `.env.example` to `.env`), how to make a migration.
  *Done when:* a stranger could run the project from the README alone.
- [ ] **0.3 Test commands via Docker.** Decide how you run tests (locally with `uv run pytest`, or `docker compose exec backend ...`). Document it in the README. The test database needs a name containing `_test` (the config enforces this). Create it once with `docker compose exec db createdb -U postgres sajilo_test`, then point `backend/.env.test` at it.
- [ ] **0.4 CI.** Add `.github/workflows/ci.yml` that runs on every PR: start a Postgres service container, `uv sync`, `ruff check`, `pytest`. Add a second job for the frontend: `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm build`. Then, in the GitHub repo settings, require CI to pass before merging.
  *Done when:* a PR shows green checks.
- [ ] **0.5 Make tests exercise migrations.** In the test setup, run `alembic upgrade head` instead of `create_all` (or add one CI step that does it against an empty database). This catches migration bugs.
- [ ] **0.6 Pin the uv image** in `backend/Dockerfile`, for example `ghcr.io/astral-sh/uv:0.5` (check the current version on GitHub first).

### Phase 1: Finish authentication (about 2-3 days)

- [ ] **1.1 Normalize emails.** Lowercase and strip in the `UserCreate` and `UserLogin` schemas (a pydantic validator) so signup and login agree. Add a test that `A@x.com` and `a@x.com` conflict.
- [ ] **1.2 Password rules.** Minimum length (12 is a good default) via `Field(min_length=...)` on `UserCreate.password`. Test that a short password returns 422.
- [ ] **1.3 Handle the signup race.** Catch `sqlalchemy.exc.IntegrityError` around the insert, roll back, and raise the same "already exists" error (409). Keep the pre-check for the friendly path.
- [ ] **1.4 Stop logging emails.** Replace email in log messages with the user ID or nothing.
- [ ] **1.5 `get_current_user` dependency.** In `app/deps.py`: use `fastapi.security.HTTPBearer` to read the token, call `decode_token`, check `type == "access"`, load the user by `sub` with `UserRepository.get_by_id`, return it. On any failure raise `HTTPException(401)` with the header `WWW-Authenticate: Bearer`.
- [ ] **1.6 `GET /auth/me`** returning `UserRead`, protected by that dependency. This is your test endpoint for 1.5.
  *Tests:* no header -> 401, garbage token -> 401, expired token -> 401, **refresh token used as access token -> 401**, valid token -> 200.
- [ ] **1.7 Refresh token hygiene.**
  - Add an index on `refresh_tokens.user_id` (new migration).
  - Add `POST /auth/logout-all`, which revokes every token of the current user.
  - If a revoked token is presented to `/refresh` (reuse), revoke all of that user's tokens. This is standard "token theft" protection.
  - A cleanup function that deletes expired rows (a script you can run, or call it later from a scheduled job).
- [ ] **1.7b (decision)** Decide how the frontend will store tokens. Simple: keep tokens in memory and refresh via the API. More secure: send the refresh token as an `HttpOnly`, `Secure`, `SameSite` cookie. Decide before Phase 9; changing later is painful. For a first version, the JSON-body approach you already have is fine.
- [ ] **1.8 Basic rate limiting** on `/auth/login` and `/auth/signup` (e.g. `slowapi`, or a small Postgres/Redis-based counter). Optional now, required before production.

### Phase 2: Fix the booking schema (about 1 day)

- [ ] **2.1 Add a date to bookings.** New migration. Preferred design: replace the two `Time` columns with two `DateTime(timezone=True)` columns, `starts_at` and `ends_at`, stored in UTC. (Alternative: keep times and add a `booking_date` column. The timestamp version is better because it avoids midnight-crossing bugs and supports time zones.) Update `models/booking.py`, then generate the migration with `uv run alembic revision --autogenerate -m "..."` and **read the generated file before applying it**.
- [ ] **2.2 Add `timezone` to `businesses`** (IANA string like `Asia/Kathmandu`, default to what you serve). Opening hours are "local" times, so slot generation needs this.
- [ ] **2.3 Add database constraints.**
  - `CHECK (end_time > start_time)` on `business_availability`.
  - `CHECK (ends_at > starts_at)` on `bookings`.
  - `CHECK (duration > 0 AND price >= 0)` on `services`.
  - A unique constraint on `(business_id, day_of_week)` only if you allow one window per day. If you want split shifts (9-12 and 14-18), don't add it.
- [ ] **2.4 Prevent double-booking at the database level** (important). Use a PostgreSQL exclusion constraint so overlapping active bookings for the same business are impossible even under concurrent requests. This needs `business_id` on `bookings` (or denormalized) and the `btree_gist` extension. Alembic has no helper for this, so write it with `op.execute(...)`. Research "postgresql exclusion constraint tstzrange" first. If it feels too big, do the check in the service inside a transaction with `SELECT ... FOR UPDATE` on the business row. Either way, write a test that fires two simultaneous bookings for the same slot and asserts one fails.

### Phase 3: Businesses (about 2 days)

- [ ] **3.1 Schemas, repository, service** for `Business`: `BusinessCreate` (name, optional timezone), `BusinessRead`, `BusinessUpdate`.
- [ ] **3.2 Slug generation.** Lowercase the name, replace spaces with `-`, strip special characters, and append `-2`, `-3` on collisions. Unit-test this function on its own.
- [ ] **3.3 Owner endpoints** (all require `get_current_user`):
  - `POST /businesses`
  - `GET /businesses` (only the caller's)
  - `GET /businesses/{id}`
  - `PATCH /businesses/{id}`
  - `DELETE /businesses/{id}` (note: `owner_id` uses `RESTRICT`, and bookings do too, so decide what delete means. Soft delete with a `deleted_at` or `is_active` flag is usually right.)
- [ ] **3.4 Ownership check helper.** One reusable dependency or service method: "get business `id` that belongs to the current user, else 404". Use it everywhere. Return 404, not 403, so you don't leak which IDs exist.
  *Tests:* user B cannot read, update or delete user A's business.

### Phase 4: Services (about 1-2 days)

- [ ] **4.1 Owner CRUD** under `/businesses/{business_id}/services` (list, create, get, patch, delete). Validate `duration > 0` (minutes) and `price >= 0` in the schemas as well as the DB.
- [ ] **4.2 Deleting a service that has bookings** is blocked by `RESTRICT`. Return a clear 409, or add an `is_active` flag so services can be hidden instead of deleted (recommended).
- [ ] **4.3 Public read endpoint:** `GET /public/businesses/{slug}` returning business name plus active services. No auth. Return only fields that are safe to show publicly (never owner ID or email).

### Phase 5: Availability (about 1-2 days)

- [ ] **5.1 Owner endpoints** under `/businesses/{business_id}/availability`: list, create (day, start, end), delete (or replace-all per day).
- [ ] **5.2 Validation:** `end > start`; windows on the same day must not overlap each other (service-level check, with a test for overlapping windows).
- [ ] **5.3 (optional, later)** Days off or holiday exceptions: a new `business_time_off` table (business, date range, reason).

### Phase 6: Slot calculation (about 2-3 days, the core logic)

- [ ] **6.1 Write the algorithm as a pure function first** (no database), for example in `app/services/slots.py`:
  `generate_slots(windows, service_duration, existing_bookings, date, tz, step=15) -> list[datetime]`
  - Take the business's windows for that weekday.
  - Walk through each window in `step`-minute increments; a slot is valid if `slot_start + duration <= window_end`.
  - Remove slots that overlap an existing non-cancelled booking.
  - Remove slots in the past (and optionally inside a "minimum notice" period).
  - Convert local times to UTC with `zoneinfo.ZoneInfo(business.timezone)`.
- [ ] **6.2 Unit-test it heavily:** empty day, full day, back-to-back bookings, duration longer than the window, booking at the edge of a window, cancelled booking frees its slot, DST change day if your time zone has one.
- [ ] **6.3 Public endpoint:** `GET /public/businesses/{slug}/slots?service_id=...&date=YYYY-MM-DD`. Validate the date (not in the past, not more than ~60 days ahead).

### Phase 7: Creating bookings (about 2-3 days)

- [ ] **7.1 `POST /public/businesses/{slug}/bookings`** (no auth): body has `service_id`, `starts_at`, client name, email, phone. The service computes `ends_at` from the service's duration. **Never trust the client to send `ends_at`.**
- [ ] **7.2 Re-validate inside the transaction** that the slot is still free (the slots endpoint can be stale). Combine with the constraint from 2.4. On conflict return 409 with "slot no longer available".
- [ ] **7.3 Validate input:** email format, phone format (keep it lenient), starts_at is one of the valid generated slots, the service belongs to that business.
- [ ] **7.4 Abuse protection** on this public endpoint: rate limit per IP, and consider a CAPTCHA before launch.
- [ ] **7.5 Tests:** happy path, slot taken, slot outside opening hours, service from another business, two concurrent requests for one slot.

### Phase 8: Owner booking management (about 2 days)

- [ ] **8.1 `GET /businesses/{id}/bookings`** with filters (`status`, `from`, `to`) and pagination (`limit`, `offset`, and a `total` count).
- [ ] **8.2 Status transitions** `PATCH /businesses/{id}/bookings/{booking_id}/status`. Allowed moves only: `pending -> confirmed | cancelled`, `confirmed -> completed | cancelled`. Anything else is a 409. Put the allowed-transitions table in one place in the service and unit-test it.
- [ ] **8.3 (optional)** Cancellation by the client through a signed link or a token emailed to them (needs Phase 10).

### Phase 9: Frontend (start once Phase 3 exists; can run in parallel with 4-8)

Read `frontend/AGENTS.md` before writing code. **This version of Next.js (16) has breaking changes**, so read the guides in `frontend/node_modules/next/dist/docs/` first rather than relying on tutorials.

- [ ] **9.1 Foundation.** Replace the starter page. Add `NEXT_PUBLIC_API_URL` (put it in `frontend/.env.local` and pass it through compose). Create a small typed API client in `src/lib/api.ts` (fetch wrapper that adds the bearer token, parses errors, and retries once after a 401 by calling `/auth/refresh`). Add `http://localhost:3000` to `CORS_ORIGINS` in `backend/.env`.
- [ ] **9.2 Generate types from the API.** FastAPI serves `/openapi.json`. Use `openapi-typescript` to generate types so the frontend and backend never drift.
- [ ] **9.3 Auth pages:** signup, login, logout, and a protected layout that redirects to login when there is no session. Use a form library (`react-hook-form` + `zod`) for validation.
- [ ] **9.4 Owner dashboard:** business setup form, services list/editor, weekly hours editor, bookings table with status actions.
- [ ] **9.5 Public booking flow** at `/b/[slug]`: pick service -> pick date -> pick slot -> client details form -> confirmation page. This is the page your customers see, so spend design time here (mobile first).
- [ ] **9.6 Basics:** loading and error states on every fetch, accessible form labels, page `<title>`s and metadata, a custom 404 page.
- [ ] **9.7 Tests:** a few component tests (Vitest + Testing Library) and one end-to-end happy path (Playwright) for the public booking flow.

### Phase 10: Notifications (optional, about 2 days)

- [ ] **10.1** Pick an email provider (Resend, Postmark, SES). Send "booking received" to the client and "new booking" to the owner. Use FastAPI `BackgroundTasks` first; move to a real queue only if you need retries.
- [ ] **10.2** Keep emails behind a small interface (`send_email(to, subject, html)`) so tests use a fake sender.
- [ ] **10.3** A reminder email 24 hours before a booking needs a scheduled job. Postpone until you have a reason to add a worker.

### Phase 11: Production readiness (about 3-5 days)

- [ ] **11.1 Production Dockerfiles.**
  - Frontend: multi-stage (`pnpm build`, then run `pnpm start`, or use Next's `output: "standalone"`).
  - Backend: no `--reload`, runs as a non-root user, dev dependencies excluded.
  - Add `HEALTHCHECK`s.
- [ ] **11.2 Separate dev and prod compose files** (`docker-compose.yml` plus `docker-compose.prod.yml`, or just deploy images without compose). Remove bind mounts and hardcoded credentials in prod.
- [ ] **11.3 Secrets.** Real `JWT_SECRET_KEY` (at least 32 random bytes: `python -c "import secrets; print(secrets.token_urlsafe(48))"`), real DB password, set through the host's secret manager or environment, never committed.
- [ ] **11.4 Migrations in deploy.** Decide where `alembic upgrade head` runs: a one-off release step, not on every app start when you have more than one replica.
- [ ] **11.5 Hosting.** Easy options: Railway, Render or Fly.io for the API plus managed Postgres, Vercel for the frontend. Set `CORS_ORIGINS` to the real frontend URL, use HTTPS only, and make sure `DEBUG=false`.
- [ ] **11.6 Backups.** Turn on automated Postgres backups and try one restore.
- [ ] **11.7 Observability.** Structured logs, an error tracker (Sentry), and an uptime check on `/health-check`.
- [ ] **11.8 CD.** A workflow that builds and deploys on merge to `main` after CI passes.
- [ ] **11.9 Security pass before launch:** rate limits on public endpoints, security headers, dependency audit (`uv pip list --outdated`, `pnpm audit`), confirm no endpoint returns another user's data, confirm no secrets in git history.

---

## 4. Suggested order and rough effort

| Order | Phase | Effort |
|---|---|---|
| 1 | 0 Tooling | 1 evening |
| 2 | 1 Auth | 2-3 days |
| 3 | 2 Booking schema fix | 1 day |
| 4 | 3 Businesses, 4 Services, 5 Availability | 4-5 days |
| 5 | 9.1-9.3 Frontend foundation and auth pages (alongside the above) | 3-4 days |
| 6 | 6 Slots, 7 Bookings, 8 Booking management | 6-8 days |
| 7 | 9.4-9.7 Frontend dashboard and public flow | 5-7 days |
| 8 | 10 Notifications (optional) | 2 days |
| 9 | 11 Production | 3-5 days |

Treat these as estimates for part-time work; the slot logic (Phase 6) and the double-booking guard (2.4, 7.2) are where you are most likely to spend longer.

---

## 5. Useful commands

```bash
# Run everything
docker compose up --build            # add -d to run in the background
docker compose down                  # stop (keeps database data)
docker compose down -v               # stop and DELETE database data
docker compose logs -f backend       # follow logs

# Backend (from backend/)
uv sync                              # install dependencies
uv run pytest                        # run tests (uses backend/.env.test)
uv run pytest -k refresh -x          # run matching tests, stop at first failure
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run alembic downgrade -1          # undo the last migration
uv run ruff check --fix . && uv run ruff format .

# Inside the running containers
docker compose exec backend uv run alembic upgrade head
docker compose exec db psql -U postgres -d sajilo

# Frontend (from frontend/)
pnpm install && pnpm dev
pnpm lint && pnpm build

# URLs
# API docs (Swagger):  http://localhost:8000/docs
# Health check:        http://localhost:8000/health-check
# Frontend:            http://localhost:3000
```

## 6. When you get stuck

- **A migration looks wrong:** `alembic downgrade -1`, fix the model, delete the bad migration file, regenerate. Only do this for migrations that were never merged or applied elsewhere.
- **Tests pass locally but fail in CI:** usually a missing env var, a missing `_test` database, or test order dependence. Run `pytest -p no:randomly` and read the first failure, not the last.
- **Docker acts strangely:** `docker compose down`, then `docker compose up --build`. If the database is in a bad state and you don't need its data, `docker compose down -v`.
- **Next.js behaves differently from tutorials:** read `frontend/node_modules/next/dist/docs/` for this version.
