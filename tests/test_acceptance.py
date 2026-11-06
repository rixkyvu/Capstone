"""HTTP-level regression checks for the 27 CP2 acceptance criteria."""

import os
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from app import create_app
from conftest import EMAILS, TEST_PASSWORDS


ROOT = Path(__file__).resolve().parents[1]


def _inventory_form(**overrides):
    values = {
        "sku": "SKU-99999",
        "name": "Test Item",
        "vendor_id": "1",
        "department": "Test",
        "date_received": "2026-11-06",
        "quantity": "10",
        "reorder_threshold": "2",
        "max_threshold": "20",
    }
    values.update(overrides)
    return values


def _shipment_form(**overrides):
    values = {
        "code": "SHP-99999",
        "company": "Test Carrier",
        "item_count": "1",
        "expected_at": "2026-11-08T10:00",
        "direction": "inbound",
        "status": "expected",
        "vendor_id": "",
        "inventory_id": "",
        "quantity": "0",
    }
    values.update(overrides)
    return values


def test_01_three_seeded_roles_can_sign_in(client, login):
    for role, label in (
        ("supervisor", "Supervisor"),
        ("manager", "Manager"),
        ("team_member", "Team Member"),
    ):
        response = login(role)
        assert response.status_code == 200
        assert f"{EMAILS[role]} ({label})".encode() in response.data


def test_02_invalid_login_shows_same_error_and_does_not_authenticate(client):
    for email, password in (
        (EMAILS["supervisor"], "wrong-password"),
        ("unknown@bisonoperations.com", "wrong-password"),
    ):
        response = client.post(
            "/login", data={"email": email, "password": password}, follow_redirects=True
        )
        assert b"Invalid email or password." in response.data
        assert client.get("/inventory").status_code == 302


def test_03_protected_pages_redirect_anonymous_users(client):
    for url in ("/inventory", "/shipments", "/vendors"):
        response = client.get(url)
        assert response.status_code == 302
        assert response.location.endswith("/login")


def test_04_team_member_cannot_mutate_inventory(client, login, count_rows):
    login("team_member")
    response = client.get("/inventory")
    assert b"Organic Rolled Oats 25lb" in response.data
    assert b"Add Item" not in response.data
    assert b">Edit</a>" not in response.data
    assert b">Delete</button>" not in response.data
    assert b">Reorder</a>" not in response.data
    before = count_rows("inventory")
    assert client.post("/inventory/1/delete").status_code == 403
    assert count_rows("inventory") == before


def test_05_team_member_cannot_open_vendors(client, login):
    login("team_member")
    assert client.get("/vendors").status_code == 403
    assert client.get("/vendors/1").status_code == 403


def test_06_manager_cannot_reorder_or_delete_shipments(client, login, count_rows):
    login("manager")
    before = count_rows("purchase_orders")
    assert client.get("/inventory/2/reorder").status_code == 403
    assert client.post("/inventory/2/reorder", data={"quantity": "858"}).status_code == 403
    assert count_rows("purchase_orders") == before
    assert client.post("/shipments/1/delete").status_code == 403
    assert client.get("/shipments").data.find(b"SHP-10492") >= 0


def test_07_dashboard_has_four_low_stock_items(client, login):
    response = login("supervisor")
    for item in (
        b"Sparkling Water 24-pack", b"Cheddar Cheese Block 5lb",
        b"Instant Coffee 12oz", b"Hand Sanitizer 8oz",
    ):
        assert item in response.data
    assert response.data.count(b'class="attention-row low-stock-row"') == 4
    for quantity, threshold, item_id in (
        (b"42 on hand", b"reorder at 100", 2),
        (b"38 on hand", b"reorder at 150", 5),
        (b"56 on hand", b"reorder at 100", 8),
        (b"61 on hand", b"reorder at 125", 9),
    ):
        assert quantity in response.data and threshold in response.data
        assert f'href="/inventory/{item_id}/reorder"'.encode() in response.data


def test_08_reorder_cancel_returns_to_dashboard_without_creating_po(client, login, count_rows):
    login("supervisor")
    response = client.get("/inventory/2/reorder")
    assert b'value="858"' in response.data
    assert b"Jordan Lee" in response.data
    assert b'href="/"' in response.data
    assert count_rows("purchase_orders") == 0


def test_09_reorder_creates_pending_order_and_message(client, login, query):
    login("supervisor")
    response = client.post(
        "/inventory/2/reorder", data={"quantity": "858", "note": ""}
    )
    assert response.status_code == 302
    assert b"PO-1001 sent to Pacific Beverage Co." in client.get(
        response.location, follow_redirects=True
    ).data
    assert b"PO-1001" in client.get("/vendors/2").data
    assert b"Purchase order PO-1001: Sparkling Water 24-pack (SKU-10567)" in client.get(
        "/vendors/2"
    ).data
    assert query("SELECT quantity FROM inventory WHERE id = 2")[0]["quantity"] == 42
    assert query("SELECT status FROM purchase_orders WHERE code = 'PO-1001'")[0]["status"] == "pending"


def test_10_receiving_order_updates_quantity_once(client, login, query):
    login("supervisor")
    client.post("/inventory/2/reorder", data={"quantity": "858"})
    assert client.post("/purchase-orders/1/receive").status_code == 302
    assert query("SELECT quantity FROM inventory WHERE id = 2")[0]["quantity"] == 900
    assert query("SELECT status FROM purchase_orders WHERE id = 1")[0]["status"] == "received"
    client.post("/purchase-orders/1/receive")
    assert query("SELECT quantity FROM inventory WHERE id = 2")[0]["quantity"] == 900
    assert b"Sparkling Water 24-pack" not in client.get("/").data


@pytest.mark.parametrize("quantity", ["0", "-10", "10001", "lots"])
def test_11_invalid_reorder_quantity_is_rejected(client, login, count_rows, quantity):
    login("supervisor")
    response = client.post("/inventory/2/reorder", data={"quantity": quantity})
    assert b"Order quantity must be a whole number from 1 to 10,000." in response.data
    assert count_rows("purchase_orders") == 0


def test_12_search_cleanpro_returns_two_items(client, login):
    login("supervisor")
    response = client.get("/inventory?q=CleanPro")
    assert b"Multi-Surface Cleaner 32oz" in response.data
    assert b"Hand Sanitizer 8oz" in response.data
    assert b"Organic Rolled Oats 25lb" not in response.data
    assert response.data.count(b"<tr>") == 3


def test_13_inventory_search_and_low_stock_filter(client, login):
    login("supervisor")
    assert b"Sparkling Water 24-pack" in client.get("/inventory?q=SKU-10567").data
    dairy = client.get("/inventory?q=Dairy").data
    assert b"Cheddar Cheese Block 5lb" in dairy
    assert b"Sparkling Water 24-pack" not in dairy
    assert dairy.count(b"<tr>") == 2
    low = client.get("/inventory?status=low").data
    assert b"Sparkling Water 24-pack" in low and b"Hand Sanitizer 8oz" in low
    assert low.count(b"class=\"status low\"") == 4


@pytest.mark.parametrize("query", ["zzz", "' OR '1'='1"])
def test_14_empty_inventory_search_is_safe(client, login, query):
    login("supervisor")
    response = client.get("/inventory", query_string={"q": query})
    assert response.status_code == 200
    assert b"No items match your search." in response.data
    assert b"Organic Rolled Oats 25lb" not in response.data


def test_15_shipments_default_and_direction_filters(client, login):
    login("supervisor")
    inbound = client.get("/shipments")
    for code in (b"SHP-10492", b"SHP-10483", b"SHP-10471"):
        assert code in inbound.data
    assert b"SHP-20011" not in inbound.data
    outbound = client.get("/shipments?direction=outbound")
    assert b"SHP-20011" in outbound.data
    assert b"SHP-104" not in outbound.data


def test_16_shipment_row_lists_product_and_quantity(client, login):
    login("supervisor")
    assert b"Sparkling Water 24-pack (200)" in client.get("/shipments").data


def test_17_shipment_status_tabs_show_seeded_statuses(client, login):
    login("supervisor")
    for status, code in (
        ("active", b"SHP-10410"),
        ("delayed", b"SHP-10351"),
        ("history", b"SHP-10403"),
    ):
        response = client.get(f"/shipments?status={status}")
        assert code in response.data
        assert b"SHP-10492" not in response.data


def test_18_manager_can_edit_shipment_to_delayed(client, login):
    login("manager")
    response = client.get("/shipments/1/edit")
    assert response.status_code == 200
    form = _shipment_form(
        code="SHP-10492", company="Pacific Beverage Co.", item_count="200",
        expected_at="2026-09-19T08:00", direction="inbound", status="delayed",
        vendor_id="2", inventory_id="2", quantity="200",
    )
    assert client.post("/shipments/1/edit", data=form).status_code == 302
    assert b"SHP-10492" not in client.get("/shipments?status=expected").data
    assert b"SHP-10492" in client.get("/shipments?status=delayed").data
    dashboard = client.get("/")
    assert b"SHP-10492" in dashboard.data
    assert b"Sparkling Water 24-pack (200)" in dashboard.data
    assert b"class=\"attention-row delayed\"" in dashboard.data


def test_19_inventory_validation_preserves_form_data(client, login, count_rows):
    login("supervisor")
    before = count_rows("inventory")
    response = client.post(
        "/inventory/add",
        data=_inventory_form(quantity="ten", reorder_threshold="-5"),
    )
    assert b"Quantity must be a whole number of 0 or more." in response.data
    assert b"Reorder threshold must be a whole number of 0 or more." in response.data
    assert b'value="ten"' in response.data and b'value="-5"' in response.data
    assert b'value="SKU-99999"' in response.data and b'value="Test Item"' in response.data
    assert response.data.count(b'class="field invalid"') == 2
    assert count_rows("inventory") == before


def test_20_duplicate_inventory_name_is_rejected(client, login, count_rows):
    login("supervisor")
    before = count_rows("inventory")
    response = client.post(
        "/inventory/add",
        data=_inventory_form(name="Sparkling Water 24-pack"),
    )
    assert b"An item named Sparkling Water 24-pack already exists." in response.data
    assert count_rows("inventory") == before


def test_21_missing_records_return_required_404(client, login):
    login("supervisor")
    for url in ("/inventory/999/edit", "/shipments/999/edit", "/vendors/999"):
        response = client.get(url)
        assert response.status_code == 404
        assert b"Record not found." in response.data


def test_22_deletes_are_post_only_and_confirmed(client, login, count_rows, query):
    login("supervisor")
    inventory_html = client.get("/inventory").data
    assert b'<form method="post" action="/inventory/10/delete"' in inventory_html
    assert b"Are you sure you want to delete Bottled Spring Water 16oz (case)? This cannot be undone." in inventory_html
    inventory_count = count_rows("inventory")
    assert client.get("/inventory/10/delete").status_code == 405
    assert count_rows("inventory") == inventory_count
    assert client.post("/inventory/10/delete").status_code == 302
    assert count_rows("inventory") == inventory_count - 1
    shipment_count = count_rows("shipments")
    shipments_html = client.get("/shipments").data
    assert b'<form method="post" action="/shipments/1/delete"' in shipments_html
    assert b"Are you sure you want to delete SHP-10492? This cannot be undone." in shipments_html
    assert client.get("/shipments/1/delete").status_code == 405
    assert client.post("/shipments/1/delete").status_code == 302
    assert count_rows("shipments") == shipment_count - 1
    assert b"SHP-10492" not in client.get("/shipments").data
    client.post("/vendors/add", data={
        "name": "Disposable Test Vendor", "contact_name": "Test Contact",
        "phone": "", "email": "", "notes": "", "category": "Dry Goods",
    })
    vendor_id = query("SELECT id FROM vendors WHERE name = ?", ("Disposable Test Vendor",))[0]["id"]
    new_vendor = client.get("/vendors").data
    assert f'<form method="post" action="/vendors/{vendor_id}/delete"'.encode() in new_vendor
    assert b"Are you sure you want to delete Disposable Test Vendor? This cannot be undone." in new_vendor
    assert client.get(f"/vendors/{vendor_id}/delete").status_code == 405
    assert client.post(f"/vendors/{vendor_id}/delete").status_code == 302
    assert b"Disposable Test Vendor" not in client.get("/vendors").data


def test_23_vendor_with_inventory_cannot_be_deleted(client, login, count_rows):
    login("supervisor")
    before = count_rows("vendors")
    response = client.post("/vendors/2/delete", follow_redirects=True)
    assert b"Pacific Beverage Co. still supplies 3 inventory items. Reassign or delete them first." in response.data
    assert count_rows("vendors") == before
    assert b"Pacific Beverage Co." in client.get("/vendors").data


def test_24_vendor_message_validation_and_success(client, login, query):
    login("supervisor")
    empty_subject = client.post(
        "/vendors/4/message", data={"subject": "", "body": "Restock needed"}
    )
    assert b"Subject is required." in empty_subject.data
    too_long = client.post(
        "/vendors/4/message",
        data={"subject": "Restock", "body": "x" * 2001},
    )
    assert b"Message must be 2,000 characters or fewer." in too_long.data
    assert query("SELECT COUNT(*) AS n FROM vendor_messages")[0]["n"] == 0
    client.post(
        "/vendors/4/message",
        data={"subject": "Restock", "body": "Please restock soon."},
    )
    message = query("SELECT subject, sent_at FROM vendor_messages")[0]
    assert message["subject"] == "Restock"
    assert date.today().strftime("%b %d, %Y") in message["sent_at"]
    assert b"Restock" in client.get("/vendors/4").data


def test_25_inventory_persists_across_logout_and_restart(client, login, restart_app):
    login("supervisor")
    assert client.post("/inventory/add", data=_inventory_form()).status_code == 302
    assert client.post("/logout").status_code == 302
    restarted_client = restart_app()
    response = restarted_client.post(
        "/login",
        data={
            "email": EMAILS["supervisor"],
            "password": TEST_PASSWORDS["supervisor"],
        },
        follow_redirects=True,
    )
    assert b"Test Item" in restarted_client.get("/inventory?q=Test+Item").data


def test_26_missing_secret_prevents_startup(tmp_path):
    env = os.environ.copy()
    for name in ("SECRET_KEY", "SUPERVISOR_PASSWORD", "MANAGER_PASSWORD", "TEAM_PASSWORD"):
        env.pop(name, None)
    env["PYTHONPATH"] = str(ROOT)
    env["DATABASE_PATH"] = str(tmp_path / "must-not-be-created.db")
    env["PYTHON_DOTENV_DISABLED"] = "true"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=tmp_path, env=env, text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert "SECRET_KEY is not set." in result.stdout + result.stderr
    assert not (tmp_path / "must-not-be-created.db").exists()


def test_27_get_logout_does_not_mutate_and_post_logout_preserves_orders(client, login, query):
    login("supervisor")
    client.post("/inventory/2/reorder", data={"quantity": "858"})
    before = query("SELECT COUNT(*) AS n FROM purchase_orders")[0]["n"]
    assert client.get("/logout").status_code == 405
    assert query("SELECT COUNT(*) AS n FROM purchase_orders")[0]["n"] == before == 1
    assert client.post("/logout").status_code == 302
    client.post(
        "/login",
        data={
            "email": EMAILS["supervisor"],
            "password": TEST_PASSWORDS["supervisor"],
        },
        follow_redirects=True,
    )
    assert b"PO-1001" in client.get("/vendors/2").data
    assert query("SELECT COUNT(*) AS n FROM purchase_orders")[0]["n"] == 1


def test_existing_incompatible_database_is_rejected_without_overwrite(tmp_path):
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, marker TEXT)")
        db.execute("INSERT INTO users (marker) VALUES ('keep-this-row')")
        for table in (
            "vendors", "inventory", "shipments", "shipment_items",
            "purchase_orders", "vendor_messages",
        ):
            db.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)")

    with pytest.raises(RuntimeError, match="does not match the CP2 schema"):
        create_app({"DATABASE": str(database_path), "TESTING": True})

    with sqlite3.connect(database_path) as db:
        assert db.execute("SELECT marker FROM users").fetchone()[0] == "keep-this-row"
