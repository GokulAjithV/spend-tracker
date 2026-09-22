# Spend Tracker

A small service to log expenses and get a monthly summary: total spend, spend by category, month over month change, and a flag when a category grows more than 20% vs the previous month.

Backend: FastAPI, SQLAlchemy 2, SQLite. UI: one plain HTML page served by FastAPI.

## Live demo

- UI: https://spend-tracker-igym.onrender.com
- API docs (Swagger): https://spend-tracker-igym.onrender.com/docs
- API key: shared in the submission email. Paste it into the UI, or use the **Authorize** button in `/docs`.

Notes on the free tier:
- If the app was idle, the first request can take ~50 seconds (cold start).
- SQLite lives on Render's temporary disk. Data resets on restart or redeploy. Demo data is seeded on startup, so the summary always has a current and a previous month to compare.

## Run locally

Needs Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cd server
cp .env.example .env          # then set API_KEY
uv sync
uv run uvicorn app.main:app --env-file .env
```

- UI: http://localhost:8000
- Docs: http://localhost:8000/docs

Generate a key with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Environment variables:

| Name | Required | Default | What it does |
|---|---|---|---|
| `API_KEY` | yes | - | The app won't start without it |
| `DATABASE_URL` | no | `sqlite:///./spend_tracker.db` | SQLAlchemy URL |
| `APP_TIMEZONE` | no | `Asia/Kolkata` | Decides the default "current month" |
| `SEED_ON_STARTUP` | no | `false` | `true` inserts demo data when the table is empty |

Run the tests:
```bash
cd server
uv run pytest
```

## API

All endpoints except `/health` need the header `X-API-Key: <key>`.
Money is sent and returned as a string (`"250.50"`). Dates are `YYYY-MM-DD`.

| Method | Path | What it does |
|---|---|---|
| POST | `/expenses` | Create an expense |
| GET | `/expenses` | List expenses. Filters: `category` (repeatable), `date_from`, `date_to` (inclusive), `limit` (1-100), `offset` |
| GET | `/summary` | Summary for `?month=YYYY-MM` (default: current month in IST) |
| GET | `/health` | Health check, no auth |

Examples:
```bash
BASE=http://localhost:8000
KEY=<your key>

curl -X POST $BASE/expenses -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"amount": "250.50", "category": "food", "note": "lunch", "spent_on": "2026-09-21"}'

curl "$BASE/expenses?category=food&date_from=2026-09-01&date_to=2026-09-30" -H "X-API-Key: $KEY"

curl "$BASE/summary?month=2026-09" -H "X-API-Key: $KEY"
```

Errors: `422` for bad input (one entry per bad field), `401` for a missing or wrong key.

Full contract, summary rules and edge cases: [server/DESIGN.md](server/DESIGN.md).

## Project layout

```
server/
  app/
    main.py      routes (kept thin) + serves the UI
    schemas.py   request/response models and validation
    repo.py      all SQL
    summary.py   summary maths, pure functions
    models.py    SQLAlchemy table
    auth.py      API key check
    seed.py      demo data
    config.py    timezone and env settings
  tests/
ui/
  index.html     the whole UI (HTML + CSS + JS, no build step)
```

## Key design decisions

- **Money is stored as integer paise.** Floats can't store some decimals exactly (0.1 + 0.2 != 0.3), so totals drift. SQLite has no exact decimal type. I convert rupees to paise at the API edge, all maths runs on integers.
- **Amount comes in as a string, not a JSON number.** A JSON number is already a float by the time it's parsed, so precision can be lost before my code sees it.
- **Dates are ISO (`YYYY-MM-DD`).** SQLite stores dates as text, and ISO text sorts in date order, so range filters work.
- **Monthly queries use a half open range** (`>= 1st of month AND < 1st of next month`) on the bare column, so the `spent_on` index is used. No `strftime()` on the column.
- **Summary = one month vs the previous month.** Totals come from SQL (`SUM ... GROUP BY`). The percent and flag logic is in pure functions in `summary.py` with no DB and no clock, so it's easy to unit test.
- **MoM percent is `null` when the previous month is 0.** 0% or infinity would both be misleading.
- **Insight rule:** flagged when `current * 100 > previous * 120`. Integer maths, so exactly +20% is not flagged ("more than 20%"). A brand new category isn't flagged.
- **Default month uses IST.** At 1 AM IST on the 1st, the server (UTC) is still in the previous month.
- **Categories are trimmed and lowercased,** so `"Food "` and `"food"` don't split into two totals.
- **Unknown fields and query params return 422.** A typo like `?categroy=food` fails instead of silently returning everything.
- **Auth is one API key** from an env var, compared in constant time. The spec is single user, so I only need "are you allowed in", not "who are you". Missing and wrong keys get the same 401.
- **The app fails at startup if `API_KEY` is missing,** instead of running with no auth.
- **UI is plain HTML served by FastAPI.** Design isn't evaluated. Same origin means no CORS, no build step, one command runs everything. The UI is in its own folder, so it can be replaced later without touching the backend. API data is rendered with `textContent`, so a note can't inject HTML.

## Testing

125 tests with pytest. Each test gets a fresh in-memory SQLite database.

Covered beyond the happy path:
- Amount: 0, negative, 3 decimals, non-numeric, JSON number, too many digits
- Dates: invalid calendar dates, wrong formats
- Category normalisation (`"Food "` -> `food`) and length limits
- Filters: inclusive boundaries, `date_from > date_to`, limit/offset bounds, unknown params
- Summary: empty DB, previous month = 0, negative change, the exact 20% boundary, January -> December rollover, category only in the previous month
- Paise precision (`0.10 + 0.20 = 0.30`)
- Auth: missing key, wrong key, `/health` without a key
- Seeding: only runs on an empty table, never duplicates, never creates future dates

## What I'd do with more time

- **Postgres + Alembic migrations.** SQLite allows one writer at a time and the free host's disk is temporary. With SQLAlchemy only `DATABASE_URL` changes.
- **Multi user:** a `users` table, JWT auth, and `user_id` on every expense and every query.
- **API keys in a table** (hashed, one per client, revocable) instead of one env var.
- **Cursor pagination** instead of offset, and a monthly rollup table if data grows large.
- **Edit and delete** endpoints, and a categories table.
- **One error shape** for 401 and 422 (right now they follow FastAPI's defaults).
- **Paid instance or a different host** so the app doesn't sleep.
- **React frontend** if the UI grows beyond one page.

## How I used AI

I used Claude Code to generate most of the code and tests from small, scoped prompts, and to draft the README and design doc. I wrote the design rules myself and reviewed each diff before committing. I rejected React for the UI (no build step or CORS needed for this spec) and picked tzdata over a fixed UTC offset to keep real timezone names. I caught a UI bug where the month picker defaulted to next month because of UTC date conversion, and had it fixed.