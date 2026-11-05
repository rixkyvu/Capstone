# Agent context

## What this application is

Bison Operations is a local Flask prototype for internal operations work. The current code brings inventory, inbound and outbound shipments, vendor contacts, and employee schedules together behind a sign-in page. The coded prototype is in [app.py](./app.py), with its screens in [templates/](./templates/) and styling in [static/app.css](./static/app.css).

The code suggests internal operations staff use these workflows, but it does not establish the team's tested user roles, needs, or constraints. Do not present guesses about users as research findings.

## Run and test

Run commands from this directory; the SQLite database path is relative to the current working directory.

```powershell
.\venv\Scripts\python.exe app.py
```

If the included virtual environment is unavailable, use a Python environment with Flask installed and run `python app.py`. The app starts its Flask development server with debug enabled. It is a demo, not a production deployment.

No project-level automated tests or test instructions were present when this file was written. `python -m py_compile app.py` checks syntax only; it is not a substitute for exercising changed behavior. For changes, manually smoke-test the affected page and its relevant create/edit/delete or navigation flow. Add or update automated tests if a test suite is introduced.

## Where things go

- `app.py`: Flask app, routes, SQLite schema and seed data, and server startup.
- `templates/`: Jinja page templates; `base.html` supplies the shared navigation.
- `static/app.css`: stylesheet loaded by the templates.
- `static/styles.css`: currently not referenced by the templates; check its intended use before changing it or switching stylesheets.
- `bison.db`: local SQLite demo data. The schema and canonical seed data live in `reset_db()` in `app.py`, not in hand-edited database contents.

There is no migration framework or separate model/service layer. Keep related route, query, and template changes consistent with the existing structure unless a requested change calls for a broader refactor.

## Conventions

- Use the existing Flask route functions, `render_template`, `redirect`, and `url_for` patterns.
- Keep HTML in Jinja templates and presentation rules in the stylesheet used by those templates.
- Use `get_db()` for request-scoped SQLite access, commit writes, and bind SQL values with `?` parameters.
- Keep Python names in `snake_case` and template names aligned with the page or form they render.
- Preserve the current compact operations UI: shared horizontal navigation, data tables and forms, with restrained status-color accents. Avoid a broad visual redesign unless the current prototype or supplied design evidence calls for it.

## Fragile behavior and boundaries

- **Database reset is destructive and intentional for this demo.** `reset_db()` drops and recreates every table. It runs when `app.py` is imported and again on logout, so edits to demo data do not persist across those events. Do not remove, move, or expand these resets without confirming the desired data lifecycle; importing the module in tests also triggers a reset.
- Because `DATABASE` is a relative path, launching from a different working directory can create or use a different `bison.db`.
- The app uses a hard-coded development session secret and enables Flask debug mode. Keep it local and use synthetic data; do not treat it as production-ready or add real credentials or business data.
- Do not edit the local `venv/` or generated `__pycache__/` as part of application changes. Change source files and dependency manifests only when needed.
- `app.py` currently combines route handling, SQL, and seed data. Be careful that schema and seed changes stay in sync with all pages that read or write those tables.

## User research and design decisions

The coded prototype is the implementation reference in `app.py`, `templates/`, and `static/app.css`. The course prototype/wireframe, feedback grid, and Opportunity Assessment were not present in the project materials available when this file was written. Therefore, no user-tested design decisions are recorded here yet; do not invent them or treat current code as proof of a tested preference.

Before making a user-facing design change, use the team's supplied prototype and research artifacts, then record the decision itself here (and link the artifact), not just a pointer to the artifact. Include:

- Who the users are, their relevant goals, and constraints.
- Which feedback-grid decisions the build must respect.
- If CP0 changed the idea, which original feedback-grid decisions still apply and are carried over, and which are dropped, with a brief reason for each. Ground that mapping in the new Opportunity Assessment and wireframe.
- Links or repository-relative paths to the prototype/wireframe, feedback grid, and Opportunity Assessment.

Until those materials are supplied, preserve existing behavior and avoid claiming that a design choice came from feedback testing.
