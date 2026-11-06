"""SQLite schema, seed data, and request-scoped database connections."""

import os
import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


DB_PATH = os.environ.get("DATABASE_PATH") or "bison.db"

SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('supervisor', 'manager', 'team_member'))
);
CREATE TABLE vendors (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    contact_name TEXT,
    phone TEXT,
    email TEXT,
    notes TEXT,
    category TEXT CHECK (category IN ('Dairy', 'Beverages', 'Dry Goods', 'Cleaning', 'Frozen'))
);
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    department TEXT,
    date_received TEXT,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    reorder_threshold INTEGER NOT NULL CHECK (reorder_threshold >= 0),
    max_threshold INTEGER NOT NULL CHECK (max_threshold > reorder_threshold)
);
CREATE TABLE vendor_messages (
    id INTEGER PRIMARY KEY,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    subject TEXT NOT NULL CHECK (length(subject) BETWEEN 1 AND 150),
    body TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 2000),
    sent_at TEXT NOT NULL,
    inventory_id INTEGER REFERENCES inventory(id) ON DELETE SET NULL
);
CREATE TABLE shipments (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    company TEXT NOT NULL,
    item_count INTEGER NOT NULL CHECK (item_count >= 1),
    expected_at TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'inbound' CHECK (direction IN ('inbound', 'outbound')),
    status TEXT NOT NULL DEFAULT 'expected' CHECK (status IN ('expected', 'active', 'delayed', 'history')),
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL
);
CREATE TABLE shipment_items (
    id INTEGER PRIMARY KEY,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    inventory_id INTEGER NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity >= 1)
);
CREATE TABLE purchase_orders (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    inventory_id INTEGER NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10000),
    status TEXT NOT NULL CHECK (status IN ('pending', 'received')),
    created_at TEXT NOT NULL,
    note TEXT
);
"""

VENDORS = [
    ("Golden Valley Farms", "Alexis Morgan", "(312) 555-0192", "alexis@goldenvalley.example",
     "Supplier of dry goods and snack products.", "Dry Goods"),
    ("Pacific Beverage Co.", "Jordan Lee", "(206) 555-0143", "jordan@pacificbev.example",
     "Beverage distributor for the Pacific region.", "Beverages"),
    ("Sunrise Foods Co.", "Pat Nguyen", "(414) 555-0110", "pat@sunrisefoods.example",
     "Frozen and dairy goods supplier.", "Frozen"),
    ("CleanPro Supply", "Dana Reyes", "(773) 555-0199", "dana@cleanpro.example",
     "Cleaning and sanitation supplies.", "Cleaning"),
    ("Dairy Fresh Distributors", "Sam Carter", "(630) 555-0177", "sam@dairyfresh.example",
     "Regional dairy distributor.", "Dairy"),
]

INVENTORY = [
    ("SKU-10234", "Organic Rolled Oats 25lb", "Golden Valley Farms", "Dry Goods", "2026-09-12", 480, 100, 800),
    ("SKU-10567", "Sparkling Water 24-pack", "Pacific Beverage Co.", "Beverages", "2026-09-10", 42, 100, 900),
    ("SKU-11029", "Frozen Chicken Breast 10lb", "Sunrise Foods Co.", "Frozen", "2026-09-14", 1240, 200, 1000),
    ("SKU-10812", "Multi-Surface Cleaner 32oz", "CleanPro Supply", "Cleaning Supplies", "2026-09-08", 610, 150, 1200),
    ("SKU-10445", "Cheddar Cheese Block 5lb", "Dairy Fresh Distributors", "Dairy", "2026-09-13", 38, 150, 900),
    ("SKU-10998", "Pretzel Snack Bags 1oz (case)", "Golden Valley Farms", "Snacks", "2026-09-09", 960, 200, 500),
    ("SKU-11156", "Paper Towel Rolls 12-pack", "Pacific Beverage Co.", "Cleaning Supplies", "2026-09-15", 205, 100, 900),
    ("SKU-11178", "Instant Coffee 12oz", "Sunrise Foods Co.", "Beverages", "2026-09-11", 56, 100, 900),
    ("SKU-11203", "Hand Sanitizer 8oz", "CleanPro Supply", "Cleaning Supplies", "2026-09-09", 61, 125, 900),
    ("SKU-10949", "Bottled Spring Water 16oz (case)", "Pacific Beverage Co.", "Beverages", "2026-09-08", 1800, 200, 1200),
]

SHIPMENTS = [
    ("SHP-10492", "Pacific Beverage Co.", 200, "2026-09-19 08:00", "inbound", "expected"),
    ("SHP-10483", "Crown Packaging Co.", 65, "2026-09-18 11:30", "inbound", "expected"),
    ("SHP-10471", "Vantage Fastener Corp", 550, "2026-09-18 13:00", "inbound", "expected"),
    ("SHP-10410", "Hoosier Rubber & Seal", 150, "2026-09-18 08:00", "inbound", "active"),
    ("SHP-10403", "Apex Bearing Distribution", 60, "2026-09-18 13:15", "inbound", "history"),
    ("SHP-10351", "Sterling Wire Products", 320, "2026-09-20 10:00", "inbound", "delayed"),
    ("SHP-20011", "Great Lakes Freight", 300, "2026-09-19 09:00", "outbound", "expected"),
]


def get_db():
    """Return one SQLite connection per Flask request or CLI app context."""
    if "db" not in g:
        db = sqlite3.connect(current_app.config.get("DATABASE", DB_PATH))
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path=None):
    """Create and seed a new database; never replace an existing database."""
    database_path = Path(path or current_app.config.get("DATABASE", DB_PATH))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists() and database_path.stat().st_size:
        with sqlite3.connect(database_path) as db:
            tables = {
                row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        required = {"users", "vendors", "inventory", "shipments", "shipment_items", "purchase_orders", "vendor_messages"}
        missing = required - tables
        if missing:
            raise RuntimeError(
                "Existing database is missing CP2 tables: "
                + ", ".join(sorted(missing))
                + ". Back up the file and initialize a new CP2 database."
            )
        required_columns = {
            "users": {"id", "email", "password_hash", "role"},
            "vendors": {"id", "name", "contact_name", "phone", "email", "notes", "category"},
            "inventory": {"id", "sku", "name", "vendor_id", "department", "date_received", "quantity", "reorder_threshold", "max_threshold"},
            "vendor_messages": {"id", "vendor_id", "subject", "body", "sent_at", "inventory_id"},
            "shipments": {"id", "code", "company", "item_count", "expected_at", "direction", "status", "vendor_id"},
            "shipment_items": {"id", "shipment_id", "inventory_id", "quantity"},
            "purchase_orders": {"id", "code", "inventory_id", "vendor_id", "quantity", "status", "created_at", "note"},
        }
        with sqlite3.connect(database_path) as db:
            incompatible = [
                table for table, expected in required_columns.items()
                if expected - {
                    row[1] for row in db.execute(f"PRAGMA table_info({table})")
                }
            ]
        if incompatible:
            raise RuntimeError(
                "Existing database does not match the CP2 schema ("
                + ", ".join(sorted(incompatible))
                + "). Back up the file and initialize a new CP2 database."
            )
        return

    required_passwords = {
        "supervisor": os.environ.get("SUPERVISOR_PASSWORD"),
        "manager": os.environ.get("MANAGER_PASSWORD"),
        "team_member": os.environ.get("TEAM_PASSWORD"),
    }
    if any(not password for password in required_passwords.values()):
        raise RuntimeError(
            "SUPERVISOR_PASSWORD, MANAGER_PASSWORD, and TEAM_PASSWORD must be set before first database initialization."
        )

    with sqlite3.connect(database_path) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(SCHEMA)
        db.executemany(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            [
                ("supervisor@bisonoperations.com", generate_password_hash(required_passwords["supervisor"]), "supervisor"),
                ("manager@bisonoperations.com", generate_password_hash(required_passwords["manager"]), "manager"),
                ("team@bisonoperations.com", generate_password_hash(required_passwords["team_member"]), "team_member"),
            ],
        )
        db.executemany(
            "INSERT INTO vendors (name, contact_name, phone, email, notes, category) VALUES (?, ?, ?, ?, ?, ?)",
            VENDORS,
        )
        vendor_ids = dict(db.execute("SELECT name, id FROM vendors").fetchall())
        db.executemany(
            """INSERT INTO inventory
               (sku, name, vendor_id, department, date_received, quantity, reorder_threshold, max_threshold)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (sku, name, vendor_ids[vendor], department, received, quantity, reorder, maximum)
                for sku, name, vendor, department, received, quantity, reorder, maximum in INVENTORY
            ],
        )
        db.executemany(
            """INSERT INTO shipments
               (code, company, item_count, expected_at, direction, status, vendor_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (code, company, count, expected, direction, status, vendor_ids.get(company))
                for code, company, count, expected, direction, status in SHIPMENTS
            ],
        )
        sparkling_id = db.execute(
            "SELECT id FROM inventory WHERE sku = ?", ("SKU-10567",)
        ).fetchone()[0]
        shipment_id = db.execute(
            "SELECT id FROM shipments WHERE code = ?", ("SHP-10492",)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO shipment_items (shipment_id, inventory_id, quantity) VALUES (?, ?, ?)",
            (shipment_id, sparkling_id, 200),
        )
