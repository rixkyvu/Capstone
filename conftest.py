"""
conftest.py: shared setup for the CP2 eval suite (Bison Operations Inventory).

pytest reads this file before any test runs. For every test it:
  1. Sets test values for SECRET_KEY and the three seed passwords, so no real
     .env is needed and no real password is ever typed in a test.
  2. Points database.py at a brand-new database file in a temporary folder,
     so the app seeds it fresh (the spec says it seeds only when the file
     does not exist). Your real database file is never touched.
  3. Hands the test a `client` (a pretend browser) and a `login(role)` helper.

EVERYTHING YOUR BUILD MIGHT NAME DIFFERENTLY IS IN THE SETTINGS BLOCK BELOW.
If a test fails with a 404 on a URL or a "field missing" error, check the
settings first before deciding the app is wrong.
"""

import importlib
import os
import sqlite3
import sys

import pytest

# ============================== SETTINGS ====================================
# Names in database.py
DB_PATH_SETTING = "DB_PATH"      # variable in database.py holding the file path
INIT_FUNCTION = "init_db"        # function that creates + seeds when file is missing

# Environment variable names (must match .env.example)
ENV_SECRET = "SECRET_KEY"
ENV_PASSWORDS = {
    "supervisor": "SUPERVISOR_PASSWORD",
    "manager": "MANAGER_PASSWORD",
    "team_member": "TEAM_PASSWORD",
}
EMAILS = {
    "supervisor": "supervisor@bisonoperations.com",
    "manager": "manager@bisonoperations.com",
    "team_member": "team@bisonoperations.com",
}

# Form field names
LOGIN_FIELDS = ("email", "password")
SEARCH_PARAM = "q"                 # /inventory?q=CleanPro
FILTER_PARAM = "filter"            # /inventory?filter=low
FILTER_LOW = "low"
SHIP_DIRECTION_PARAM = "direction"  # /shipments?direction=outbound
SHIP_STATUS_PARAM = "status"        # /shipments?status=active

# URLs the spec does not pin down
PO_RECEIVE_URL = "/purchase-orders/{id}/receive"   # Mark Received (POST)
VENDOR_MESSAGE_URL = "/vendors/{id}/message"        # send message (POST)
VENDOR_DELETE_URL = "/vendors/{id}/delete"          # delete vendor (POST)
# ============================================================================

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

TEST_SECRET = "test-only-secret-not-used-anywhere-else"
TEST_PASSWORDS = {role: f"Test-{role}-pw-123" for role in ENV_PASSWORDS}

# Env must be set BEFORE app.py is imported, or the app refuses to start.
os.environ[ENV_SECRET] = TEST_SECRET
for role, var in ENV_PASSWORDS.items():
    os.environ[var] = TEST_PASSWORDS[role]

import app as app_module  # noqa: E402
from app import app as flask_app  # noqa: E402

# The spec build has database.py + data_access.py. Until those exist, the suite
# runs against the old DT prototype (one app.py, DATABASE + reset_db()), so the
# Nov 5 run can still report what is and is not built.
try:
    import database  # noqa: E402
    import data_access  # noqa: E402
    PROTOTYPE_MODE = False
except ImportError:
    database = data_access = None
    PROTOTYPE_MODE = True


def _seed_fresh(path):
    if PROTOTYPE_MODE:
        app_module.DATABASE = path
        with flask_app.app_context():
            app_module.reset_db()
    else:
        setattr(database, DB_PATH_SETTING, path)
        if hasattr(data_access, DB_PATH_SETTING):
            setattr(data_access, DB_PATH_SETTING, path)
        getattr(database, INIT_FUNCTION)()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """A brand-new database file for one test, seeded by the app's own code."""
    path = str(tmp_path / "test.db")
    if PROTOTYPE_MODE:
        monkeypatch.setattr(app_module, "DATABASE", path)
    else:
        monkeypatch.setattr(database, DB_PATH_SETTING, path)
        # If data_access copied the path at import time, point it at the test file too.
        if hasattr(data_access, DB_PATH_SETTING):
            monkeypatch.setattr(data_access, DB_PATH_SETTING, path)
    _seed_fresh(path)
    return path


@pytest.fixture
def client(db_path):
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def login(client):
    """login("supervisor") signs that account in on `client` and returns the response."""
    def _login(role, password=None):
        email_field, pw_field = LOGIN_FIELDS
        return client.post(
            "/login",
            data={email_field: EMAILS[role], pw_field: password or TEST_PASSWORDS[role]},
            follow_redirects=True,
        )
    return _login


@pytest.fixture
def query(db_path):
    """query(sql, params) runs a SELECT on the test database and returns all rows."""
    def _query(sql, params=()):
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        rows = db.execute(sql, params).fetchall()
        db.close()
        return rows
    return _query


@pytest.fixture
def count_rows(query):
    def _count(table):
        return query(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"]
    return _count


@pytest.fixture
def restart_app(db_path):
    """Simulates stopping and starting the app against the same database file:
    reloads the modules and runs startup again. Returns a fresh client."""
    def _restart():
        if PROTOTYPE_MODE:
            # The prototype has no "seed only if missing" step to rerun.
            app_module.DATABASE = db_path
        else:
            importlib.reload(database)
            setattr(database, DB_PATH_SETTING, db_path)
            importlib.reload(data_access)
            if hasattr(data_access, DB_PATH_SETTING):
                setattr(data_access, DB_PATH_SETTING, db_path)
            getattr(database, INIT_FUNCTION)()  # must NOT reseed: the file exists
        flask_app.config["TESTING"] = True
        return flask_app.test_client()
    return _restart
