"""Parameterized SQLite reads and writes for Bison Operations routes."""

from datetime import date, datetime


PAGE_SIZE = 10


def _dict(row):
    return dict(row) if row is not None else None


def get_user_by_email(db, email):
    return _dict(db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())


def get_user_by_id(db, user_id):
    return _dict(db.execute("SELECT id, email, role FROM users WHERE id = ?", (user_id,)).fetchone())


def get_dashboard_data(db):
    today = date.today().isoformat()
    summary = {
        "total_items": db.execute("SELECT COUNT(*) FROM inventory").fetchone()[0],
        "low_stock": db.execute(
            "SELECT COUNT(*) FROM inventory WHERE quantity < reorder_threshold"
        ).fetchone()[0],
        "expected_today": db.execute(
            "SELECT COUNT(*) FROM shipments WHERE expected_at LIKE ?", (today + "%",)
        ).fetchone()[0],
        "delayed": db.execute(
            "SELECT COUNT(*) FROM shipments WHERE status = 'delayed'"
        ).fetchone()[0],
    }
    low_items = db.execute(
        """SELECT i.*, v.name AS vendor_name
           FROM inventory i JOIN vendors v ON v.id = i.vendor_id
           WHERE i.quantity < i.reorder_threshold ORDER BY i.name"""
    ).fetchall()
    result_low = []
    for row in low_items:
        item = _dict(row)
        item["incoming"] = _dict(db.execute(
            """SELECT s.code, s.company, s.expected_at
               FROM shipment_items si
               JOIN shipments s ON s.id = si.shipment_id
               WHERE si.inventory_id = ? AND s.vendor_id = ?
                 AND s.direction = 'inbound'
                 AND s.status IN ('expected', 'active', 'delayed')
               ORDER BY s.expected_at LIMIT 1""",
            (item["id"], item["vendor_id"]),
        ).fetchone())
        result_low.append(item)
    over_items = db.execute(
        """SELECT i.*, v.name AS vendor_name FROM inventory i
           JOIN vendors v ON v.id = i.vendor_id
           WHERE i.quantity > i.max_threshold ORDER BY i.name"""
    ).fetchall()
    delayed_shipments = db.execute(
        """SELECT s.*, GROUP_CONCAT(i.name || ' (' || si.quantity || ')', ', ') AS products
           FROM shipments s
           LEFT JOIN shipment_items si ON si.shipment_id = s.id
           LEFT JOIN inventory i ON i.id = si.inventory_id
           WHERE s.status = 'delayed' GROUP BY s.id ORDER BY s.expected_at"""
    ).fetchall()
    return {
        **summary,
        "low_items": result_low,
        "over_items": [_dict(row) for row in over_items],
        "delayed_shipments": [_dict(row) for row in delayed_shipments],
    }


def get_inventory_page(db, query, status_filter, sort, sort_direction, page):
    sort_columns = {
        "sku": "i.sku", "name": "i.name", "vendor": "v.name",
        "department": "i.department", "date": "i.date_received",
        "quantity": "i.quantity", "status": "i.quantity",
    }
    order_column = sort_columns.get(sort, "i.id")
    direction = "DESC" if sort_direction == "desc" else "ASC"
    conditions = []
    params = []
    if query:
        conditions.append(
            "(i.name LIKE ? OR i.sku LIKE ? OR v.name LIKE ? OR i.department LIKE ?)"
        )
        params.extend([f"%{query}%"] * 4)
    if status_filter == "low":
        conditions.append("i.quantity < i.reorder_threshold")
    elif status_filter == "over":
        conditions.append("i.quantity > i.max_threshold")
    elif status_filter == "in-stock":
        conditions.append(
            "i.quantity >= i.reorder_threshold AND i.quantity <= i.max_threshold"
        )
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    total = db.execute(
        f"""SELECT COUNT(*) FROM inventory i
            JOIN vendors v ON v.id = i.vendor_id {where}""",
        params,
    ).fetchone()[0]
    rows = db.execute(
        f"""SELECT i.*, v.name AS vendor_name,
                   (SELECT si.quantity FROM shipment_items si
                    JOIN shipments s ON s.id = si.shipment_id
                    WHERE si.inventory_id = i.id AND s.direction = 'inbound'
                      AND s.status IN ('expected', 'active', 'delayed')
                    ORDER BY s.expected_at LIMIT 1) AS incoming_quantity,
                   (SELECT s.expected_at FROM shipment_items si
                    JOIN shipments s ON s.id = si.shipment_id
                    WHERE si.inventory_id = i.id AND s.direction = 'inbound'
                      AND s.status IN ('expected', 'active', 'delayed')
                    ORDER BY s.expected_at LIMIT 1) AS incoming_expected_at,
                   (SELECT s.status FROM shipment_items si
                    JOIN shipments s ON s.id = si.shipment_id
                    WHERE si.inventory_id = i.id AND s.direction = 'inbound'
                      AND s.status IN ('expected', 'active', 'delayed')
                    ORDER BY s.expected_at LIMIT 1) AS incoming_status
            FROM inventory i JOIN vendors v ON v.id = i.vendor_id {where}
            ORDER BY {order_column} {direction} LIMIT ? OFFSET ?""",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE],
    ).fetchall()
    items = []
    for row in rows:
        item = _dict(row)
        if item["quantity"] < item["reorder_threshold"]:
            item["status"] = "low"
        elif item["quantity"] > item["max_threshold"]:
            item["status"] = "over"
        else:
            item["status"] = "in-stock"
        item["incoming"] = None
        if item["incoming_quantity"] is not None:
            item["incoming"] = {
                "quantity": item["incoming_quantity"],
                "expected_at": item["incoming_expected_at"],
                "status": item["incoming_status"],
            }
        items.append(item)
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    return items, total_pages


def get_inventory_by_id(db, item_id):
    return _dict(db.execute(
        """SELECT i.*, v.name AS vendor_name, v.contact_name, v.email
           FROM inventory i LEFT JOIN vendors v ON v.id = i.vendor_id
           WHERE i.id = ?""",
        (item_id,),
    ).fetchone())


def get_inventory_stock(db, stock_status):
    operator = "<" if stock_status == "low" else ">"
    threshold = "reorder_threshold" if stock_status == "low" else "max_threshold"
    rows = db.execute(
        f"""SELECT i.*, v.name AS vendor_name FROM inventory i
            JOIN vendors v ON v.id = i.vendor_id
            WHERE i.quantity {operator} i.{threshold} ORDER BY i.name"""
    ).fetchall()
    return [_dict(row) for row in rows]


def list_vendors_for_form(db):
    return [_dict(row) for row in db.execute("SELECT * FROM vendors ORDER BY name").fetchall()]


def list_inventory_for_form(db):
    return [_dict(row) for row in db.execute("SELECT id, name FROM inventory ORDER BY name").fetchall()]


def inventory_name_exists(db, name, excluding_id=None):
    sql = "SELECT 1 FROM inventory WHERE name = ?"
    params = [name]
    if excluding_id is not None:
        sql += " AND id != ?"
        params.append(excluding_id)
    return db.execute(sql, params).fetchone() is not None


def inventory_sku_exists(db, sku, excluding_id=None):
    sql = "SELECT 1 FROM inventory WHERE sku = ?"
    params = [sku]
    if excluding_id is not None:
        sql += " AND id != ?"
        params.append(excluding_id)
    return db.execute(sql, params).fetchone() is not None


def vendor_exists(db, vendor_id):
    return db.execute("SELECT 1 FROM vendors WHERE id = ?", (vendor_id,)).fetchone() is not None


def inventory_exists(db, item_id):
    return db.execute("SELECT 1 FROM inventory WHERE id = ?", (item_id,)).fetchone() is not None


def shipment_code_exists(db, code, excluding_id=None):
    sql = "SELECT 1 FROM shipments WHERE code = ?"
    params = [code]
    if excluding_id is not None:
        sql += " AND id != ?"
        params.append(excluding_id)
    return db.execute(sql, params).fetchone() is not None


def user_by_email(db, email):
    return _dict(db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone())


def create_inventory(db, values):
    cursor = db.execute(
        """INSERT INTO inventory
           (sku, name, vendor_id, department, date_received, quantity,
            reorder_threshold, max_threshold)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            values["sku"], values["name"], values["vendor_id"], values["department"],
            values["date_received"], values["quantity"], values["reorder_threshold"],
            values["max_threshold"],
        ),
    )
    return cursor.lastrowid


def update_inventory(db, item_id, values):
    return db.execute(
        """UPDATE inventory SET sku = ?, name = ?, vendor_id = ?, department = ?,
           date_received = ?, quantity = ?, reorder_threshold = ?, max_threshold = ?
           WHERE id = ?""",
        (
            values["sku"], values["name"], values["vendor_id"], values["department"],
            values["date_received"], values["quantity"], values["reorder_threshold"],
            values["max_threshold"], item_id,
        ),
    ).rowcount


def delete_inventory(db, item_id):
    return db.execute("DELETE FROM inventory WHERE id = ?", (item_id,)).rowcount


def get_reorder_item(db, item_id):
    return get_inventory_by_id(db, item_id)


def create_purchase_order(db, item, quantity, note):
    next_number = db.execute(
        """SELECT COALESCE(MAX(CAST(SUBSTR(code, 4) AS INTEGER)), 1000) + 1
           FROM purchase_orders WHERE code LIKE 'PO-%'"""
    ).fetchone()[0]
    code = f"PO-{next_number}"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    db.execute(
        """INSERT INTO purchase_orders
           (code, inventory_id, vendor_id, quantity, status, created_at, note)
           VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
        (code, item["id"], item["vendor_id"], quantity, now, note),
    )
    subject = f"Purchase order {code}: {item['name']} ({item['sku']})"
    body = (
        f"Please fulfill {quantity} units of {item['name']} ({item['sku']}). "
        f"Current quantity: {item['quantity']}."
        + (f" Note: {note}" if note else "")
    )
    db.execute(
        """INSERT INTO vendor_messages (vendor_id, subject, body, sent_at, inventory_id)
           VALUES (?, ?, ?, ?, ?)""",
        (item["vendor_id"], subject, body, datetime.now().strftime("%b %d, %Y %H:%M"), item["id"]),
    )
    return code


def receive_purchase_order(db, order_id):
    order = db.execute(
        "SELECT * FROM purchase_orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order is None:
        return None
    order = _dict(order)
    if order["status"] == "pending":
        db.execute(
            "UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
            (order["quantity"], order["inventory_id"]),
        )
        db.execute(
            "UPDATE purchase_orders SET status = 'received' WHERE id = ?",
            (order_id,),
        )
    return order["vendor_id"]


def get_shipments(db, direction, status, query):
    conditions = ["s.direction = ?", "s.status = ?"]
    params = [direction, status]
    if query:
        conditions.append("(s.company LIKE ? OR s.code LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])
    rows = db.execute(
        f"""SELECT s.*, GROUP_CONCAT(i.name || ' (' || si.quantity || ')', ', ') AS products
            FROM shipments s
            LEFT JOIN shipment_items si ON si.shipment_id = s.id
            LEFT JOIN inventory i ON i.id = si.inventory_id
            WHERE {' AND '.join(conditions)}
            GROUP BY s.id ORDER BY s.expected_at""",
        params,
    ).fetchall()
    return [_dict(row) for row in rows]


def get_shipment_by_id(db, shipment_id):
    return _dict(db.execute(
        """SELECT s.*,
                  (SELECT inventory_id FROM shipment_items WHERE shipment_id = s.id LIMIT 1) AS inventory_id,
                  (SELECT quantity FROM shipment_items WHERE shipment_id = s.id LIMIT 1) AS product_quantity
           FROM shipments s WHERE s.id = ?""",
        (shipment_id,),
    ).fetchone())


def _save_shipment_items(db, shipment_id, values):
    db.execute("DELETE FROM shipment_items WHERE shipment_id = ?", (shipment_id,))
    if values.get("inventory_id"):
        db.execute(
            "INSERT INTO shipment_items (shipment_id, inventory_id, quantity) VALUES (?, ?, ?)",
            (shipment_id, values["inventory_id"], values["quantity"]),
        )


def create_shipment(db, values):
    cursor = db.execute(
        """INSERT INTO shipments
           (code, company, item_count, expected_at, direction, status, vendor_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            values["code"], values["company"], values["item_count"],
            values["expected_at"], values["direction"], values["status"],
            values.get("vendor_id"),
        ),
    )
    shipment_id = cursor.lastrowid
    _save_shipment_items(db, shipment_id, values)
    return shipment_id


def update_shipment(db, shipment_id, values):
    changed = db.execute(
        """UPDATE shipments SET code = ?, company = ?, item_count = ?, expected_at = ?,
           direction = ?, status = ?, vendor_id = ? WHERE id = ?""",
        (
            values["code"], values["company"], values["item_count"],
            values["expected_at"], values["direction"], values["status"],
            values.get("vendor_id"), shipment_id,
        ),
    ).rowcount
    if changed:
        _save_shipment_items(db, shipment_id, values)
    return changed


def delete_shipment(db, shipment_id):
    return db.execute("DELETE FROM shipments WHERE id = ?", (shipment_id,)).rowcount


def get_vendors(db, query, category):
    conditions = []
    params = []
    if query:
        conditions.append("name LIKE ?")
        params.append(f"%{query}%")
    if category:
        conditions.append("category = ?")
        params.append(category)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    return [_dict(row) for row in db.execute(
        f"SELECT * FROM vendors {where} ORDER BY name", params
    ).fetchall()]


def get_vendor_by_id(db, vendor_id):
    return _dict(db.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone())


def get_vendor_detail_data(db, vendor_id):
    messages = db.execute(
        """SELECT m.*, i.name AS item_name, i.sku FROM vendor_messages m
           LEFT JOIN inventory i ON i.id = m.inventory_id
           WHERE m.vendor_id = ? ORDER BY m.sent_at DESC, m.id DESC""",
        (vendor_id,),
    ).fetchall()
    products = db.execute(
        "SELECT * FROM inventory WHERE vendor_id = ? ORDER BY name", (vendor_id,)
    ).fetchall()
    orders = db.execute(
        """SELECT p.*, i.name AS item_name FROM purchase_orders p
           JOIN inventory i ON i.id = p.inventory_id
           WHERE p.vendor_id = ? ORDER BY p.created_at DESC, p.id DESC""",
        (vendor_id,),
    ).fetchall()
    shipments = db.execute(
        "SELECT * FROM shipments WHERE vendor_id = ? ORDER BY expected_at DESC",
        (vendor_id,),
    ).fetchall()
    return {
        "messages": [_dict(row) for row in messages],
        "products": [_dict(row) for row in products],
        "orders": [_dict(row) for row in orders],
        "shipments": [_dict(row) for row in shipments],
        "stats": {
            "shipments": len(shipments),
            "delayed": sum(row["status"] == "delayed" for row in shipments),
            "last_message": messages[0]["sent_at"] if messages else "—",
        },
    }


def create_vendor(db, values):
    cursor = db.execute(
        """INSERT INTO vendors (name, contact_name, phone, email, notes, category)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            values["name"], values["contact_name"], values.get("phone", ""),
            values.get("email", ""), values.get("notes", ""), values["category"],
        ),
    )
    return cursor.lastrowid


def update_vendor(db, vendor_id, values):
    return db.execute(
        """UPDATE vendors SET name = ?, contact_name = ?, phone = ?, email = ?,
           notes = ?, category = ? WHERE id = ?""",
        (
            values["name"], values["contact_name"], values.get("phone", ""),
            values.get("email", ""), values.get("notes", ""), values["category"],
            vendor_id,
        ),
    ).rowcount


def count_vendor_inventory(db, vendor_id):
    return db.execute(
        "SELECT COUNT(*) FROM inventory WHERE vendor_id = ?", (vendor_id,)
    ).fetchone()[0]


def delete_vendor(db, vendor_id):
    return db.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,)).rowcount


def create_vendor_message(db, vendor_id, values):
    db.execute(
        """INSERT INTO vendor_messages
           (vendor_id, subject, body, sent_at, inventory_id)
           VALUES (?, ?, ?, ?, ?)""",
        (
            vendor_id, values["subject"], values["body"],
            datetime.now().strftime("%b %d, %Y %H:%M"), values.get("inventory_id") or None,
        ),
    )
