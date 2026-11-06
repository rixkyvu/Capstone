# Bison Operations

Bison Operations is a local Flask and SQLite prototype for warehouse operations. It supports inventory lookup, inbound/outbound shipment tracking, vendor records, purchase orders, and role-based workflows for supervisors, managers, and team members. Vendor messages are recorded locally; the app does not send email or contact outside services.

## Requirements

- Python 3.9 or newer
- PowerShell on Windows (or an equivalent shell)
- No external database service

## Install and configure

Run commands from the repository root; the default SQLite path is relative to the current working directory.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit `.env` and set a random `SECRET_KEY` and unique local passwords for all three roles. For example, generate a signing key with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set `SECRET_KEY`, `SUPERVISOR_PASSWORD`, `MANAGER_PASSWORD`, and `TEAM_PASSWORD` in `.env`. The three seed users are:

| Role | Sign-in email | Password source |
|---|---|---|
| Supervisor | `supervisor@bisonoperations.com` | Local-only `SUPERVISOR_PASSWORD` in `.env` |
| Manager | `manager@bisonoperations.com` | Local-only `MANAGER_PASSWORD` in `.env` |
| Team Member | `team@bisonoperations.com` | Local-only `TEAM_PASSWORD` in `.env` |

There are deliberately no shared or committed application passwords. The automated test suite uses synthetic, test-only values from `conftest.py`; those are not application login defaults. `.env` is ignored by Git and must not be submitted or committed. `.env.example` contains variable names only.

Optionally set `DATABASE_PATH` in `.env` to an absolute path for the SQLite file. Otherwise the app uses `bison.db` in the current working directory.

## Database and sample data

The first launch creates the SQLite schema and synthetic sample data in `database.py`: three role accounts, five vendors, ten inventory items, seven shipments, and a linked shipment item. Passwords are stored as Werkzeug hashes. Startup leaves an existing CP2 database intact; logout never resets it.

An existing database with missing CP2 tables or columns is not overwritten or migrated automatically. Back it up before choosing a migration or reset. To start a fresh disposable demo database, stop the app and remove the selected `bison.db` only after confirming the path and backing up any data:

```powershell
Remove-Item .\bison.db
```

This reset is explicit and destructive. Do not run it against data you need.

## Run

From the repository root, after `.env` has been configured:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:5000`. This is a local coursework prototype, not a production deployment.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .pytest-tmp
```

The test fixtures create isolated SQLite databases under `.pytest-tmp` and use synthetic credentials. They do not use or reset the developer's `bison.db`.

## CP3 verification records

- [`evidence/CP3-final-pytest-run.txt`](evidence/CP3-final-pytest-run.txt) contains the final test command and complete terminal result.
- [`evidence/CP3-final-conformance.md`](evidence/CP3-final-conformance.md) maps all 27 CP2 criteria to evidence and status.
- [`evidence/CP3-eval-changes.md`](evidence/CP3-eval-changes.md) records the new acceptance checks.

Criterion 22's POST-only behavior, confirmation markup, and browser Cancel
behavior were checked; see the conformance record.

## Troubleshooting

- **`SECRET_KEY is not set.`** Confirm `.env` exists in the working directory and contains a non-empty `SECRET_KEY`.
- **Missing seed-password error.** Set all three role password variables before the first database initialization.
- **Database missing CP2 tables/schema.** The app refuses to use it rather than overwriting it. Do not delete it blindly. Back it up and follow the explicit reset/migration decision made by the team.
- **Login rejected.** Use the email above and the matching local password value from `.env`; there are no default application passwords.
- **Module import errors.** Activate the project environment or run the commands using `.\.venv\Scripts\python.exe` and reinstall from the appropriate requirements file.
- **Wrong database appears.** The default database path depends on the shell's current directory. Run from the repository root or configure an absolute `DATABASE_PATH`.
