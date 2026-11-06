# Agent context

## Application and source of truth

Bison Operations is a local Flask/SQLite coursework prototype. The CP2
acceptance criteria and role matrix in [spec-CP2.md](./spec-CP2.md) are the
behavioral source of truth. Do not treat implementation details as evidence of
user research or tested user preferences.

## Architecture

- `app.py`: Flask application factory and route/controller logic only.
- `database.py`: SQLite schema, seed data, initialization, and request-scoped connection lifecycle.
- `data_access.py`: parameterized SQL queries and database operations.
- `validations.py`: server-side validation.
- `templates/`: Jinja pages; `base.html` supplies shared navigation.
- `static/app.css`: stylesheet loaded by templates.
- `tests/`: CP2 acceptance tests and shared pytest fixtures.

Keep schema, data access, routes, forms, and templates consistent. Bind SQL
values with placeholders; do not interpolate user-controlled values into SQL.
Use role guards on the server, not just hidden UI controls.

## Run and test

Use Python 3.9 or newer. From the repository root in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set a non-empty `SECRET_KEY` and unique local `SUPERVISOR_PASSWORD`,
`MANAGER_PASSWORD`, and `TEAM_PASSWORD` values in `.env`, then run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp
.\.venv\Scripts\python.exe app.py
```

The app is a local demo, not a production deployment. Never commit `.env` or
real business data. Tests use temporary SQLite databases under `.pytest-tmp`
and synthetic credentials; they must not reset or modify the repository's
`bison.db`.

## Data lifecycle and boundaries

- Database initialization seeds data only when the configured database file
  does not exist. Startup and logout must never drop or recreate an existing
  database.
- Incompatible existing databases fail with an actionable error. Do not add a
  destructive automatic migration or reset.
- `DATABASE_PATH` may be absolute or relative to the process working directory.
  Run commands from the repository root unless using an absolute path.
- Logout and delete actions must use POST. Keep the configured session secret
  in the environment; never add a hard-coded fallback secret.
- Keep synthetic seed credentials sourced from `.env` and store only password
  hashes.
- Do not edit the local `venv/`, `.venv/`, generated `__pycache__/`, `.env`, or
  local database contents as part of application changes.
- Preserve CP2 scope. In particular, do not add employee schedules,
  overstock-management actions, item prices/costs, or an alerts feature.

## Research and visual design

The checked-in prototype is the implementation reference, not evidence that a
design decision was user-tested. The course wireframe, feedback grid, and
Opportunity Assessment were not present in the materials inspected for this
context. Do not claim user research findings or introduce a broad visual
redesign without those artifacts. If they are supplied, record the actual
decision and link the relevant artifacts here.
