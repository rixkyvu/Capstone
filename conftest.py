"""Isolated test setup for the CP2 acceptance suite."""

import os
import sqlite3
import sys
import tempfile

import pytest


sys.dont_write_bytecode = True
TEST_DATA_DIR = tempfile.TemporaryDirectory(prefix="bison-operations-tests-")
os.environ["SECRET_KEY"] = "test-only-secret-not-used-anywhere-else"
os.environ["SUPERVISOR_PASSWORD"] = "Test-supervisor-pw-123"
os.environ["MANAGER_PASSWORD"] = "Test-manager-pw-123"
os.environ["TEAM_PASSWORD"] = "Test-team_member-pw-123"
os.environ["DATABASE_PATH"] = os.path.join(TEST_DATA_DIR.name, "import.db")

from app import create_app  # noqa: E402


EMAILS = {
    "supervisor": "supervisor@bisonoperations.com",
    "manager": "manager@bisonoperations.com",
    "team_member": "team@bisonoperations.com",
}
TEST_PASSWORDS = {
    "supervisor": os.environ["SUPERVISOR_PASSWORD"],
    "manager": os.environ["MANAGER_PASSWORD"],
    "team_member": os.environ["TEAM_PASSWORD"],
}


@pytest.fixture
def app(tmp_path):
    path = str(tmp_path / "test.db")
    return create_app({"DATABASE": path, "TESTING": True})


@pytest.fixture
def db_path(app):
    path = app.config["DATABASE"]
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys = ON")
    return path


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def _login(role, password=None):
        return client.post(
            "/login",
            data={
                "email": EMAILS[role],
                "password": password or TEST_PASSWORDS[role],
            },
            follow_redirects=True,
        )
    return _login


@pytest.fixture
def query(db_path):
    def _query(sql, params=()):
        with sqlite3.connect(db_path) as db:
            db.row_factory = sqlite3.Row
            return db.execute(sql, params).fetchall()
    return _query


@pytest.fixture
def count_rows(query):
    def _count(table):
        return query(f"SELECT COUNT(*) AS n FROM {table}")[0]["n"]
    return _count


@pytest.fixture
def restart_app(app, db_path):
    def _restart():
        return create_app({"DATABASE": db_path, "TESTING": True}).test_client()
    return _restart
