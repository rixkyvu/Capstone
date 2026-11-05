import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Flask, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

DATABASE = "bison.db"
PAGE_SIZE = 5
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-me"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def reset_db():
    """Drop and reseed every table. This is a prototype: nothing persists
    across a logout or a fresh launch, so every demo starts from the same
    known state."""
    db = get_db()
    db.executescript(
        """
        DROP TABLE IF EXISTS shifts;
        DROP TABLE IF EXISTS employees;
        DROP TABLE IF EXISTS shipments;
        DROP TABLE IF EXISTS inventory;
        DROP TABLE IF EXISTS vendor_messages;
        DROP TABLE IF EXISTS vendors;
        DROP TABLE IF EXISTS users;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE vendors (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            contact_name TEXT,
            phone TEXT,
            email TEXT,
            notes TEXT
        );
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            vendor_id INTEGER REFERENCES vendors(id),
            department TEXT,
            date_received TEXT,
            quantity INTEGER NOT NULL,
            reorder_threshold INTEGER NOT NULL,
            max_threshold INTEGER NOT NULL,
            on_clearance INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE vendor_messages (
            id INTEGER PRIMARY KEY,
            vendor_id INTEGER NOT NULL REFERENCES vendors(id),
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_at TEXT NOT NULL
        );
        CREATE TABLE shipments (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            company TEXT NOT NULL,
            item_count INTEGER NOT NULL,
            expected_at TEXT NOT NULL,
            direction TEXT NOT NULL DEFAULT 'inbound',
            status TEXT NOT NULL DEFAULT 'expected'
        );
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE shifts (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            weekday INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        );
        """
    )
    db.commit()

    db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("admin@bisonoperations.com", generate_password_hash("password123")),
    )

    vendors = [
        ("Golden Valley Farms", "Alexis Morgan", "(312) 555-0192",
         "alexis@goldenvalley.example",
         "Supplier of dry goods and snack products. Contract renewal scheduled for October 2026."),
        ("Pacific Beverage Co.", "Jordan Lee", "(206) 555-0143",
         "jordan@pacificbev.example", "Beverage distributor for the Pacific region."),
        ("Sunrise Foods Co.", "Pat Nguyen", "(414) 555-0110",
         "pat@sunrisefoods.example", "Frozen and dairy goods supplier."),
        ("CleanPro Supply", "Dana Reyes", "(773) 555-0199",
         "dana@cleanpro.example", "Cleaning and sanitation supplies."),
        ("Dairy Fresh Distributors", "Sam Carter", "(630) 555-0177",
         "sam@dairyfresh.example", "Regional dairy distributor."),
    ]
    db.executemany(
        "INSERT INTO vendors (name, contact_name, phone, email, notes) VALUES (?,?,?,?,?)",
        vendors,
    )

    vendor_ids = {row["name"]: row["id"] for row in db.execute("SELECT id, name FROM vendors")}
    items = [
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
    db.executemany(
        "INSERT INTO inventory (sku, name, vendor_id, department, date_received, quantity, reorder_threshold, max_threshold) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [(sku, name, vendor_ids[v], dept, dr, qty, rt, mt) for sku, name, v, dept, dr, qty, rt, mt in items],
    )

    shipments = [
        ("SHP-10492", "Midwest Steel Supply", 240, "2026-09-18 08:00", "inbound", "expected"),
        ("SHP-10483", "Crown Packaging Co.", 65, "2026-09-18 11:30", "inbound", "expected"),
        ("SHP-10471", "Vantage Fastener Corp", 550, "2026-09-18 13:00", "inbound", "expected"),
        ("SHP-10410", "Hoosier Rubber & Seal", 150, "2026-09-18 08:00", "inbound", "active"),
        ("SHP-10403", "Apex Bearing Distribution", 60, "2026-09-18 13:15", "inbound", "history"),
        ("SHP-10351", "Sterling Wire Products", 320, "2026-09-20 10:00", "inbound", "expected"),
        ("SHP-20011", "Great Lakes Freight", 300, "2026-09-19 09:00", "outbound", "expected"),
    ]
    db.executemany(
        "INSERT INTO shipments (code, company, item_count, expected_at, direction, status) VALUES (?,?,?,?,?,?)",
        shipments,
    )

    names = ["Michael Scott", "Lebron James", "Wilt Chamberlain", "Caitlin Clark",
             "Caleb Williams", "Kyle Monongai", "Leonardo Messi", "Josh Hoover"]
    db.executemany("INSERT INTO employees (name) VALUES (?)", [(n,) for n in names])

    emp_ids = {row["name"]: row["id"] for row in db.execute("SELECT id, name FROM employees")}
    shifts = [
        ("Michael Scott", 0, "6:00 AM", "4:30 PM"),
        ("Michael Scott", 1, "6:00 AM", "4:30 PM"),
        ("Michael Scott", 2, "6:00 AM", "4:30 PM"),
        ("Michael Scott", 3, "6:00 AM", "4:30 PM"),
        ("Michael Scott", 4, "6:00 AM", "4:30 PM"),
        ("Lebron James", 0, "6:00 AM", "4:30 PM"),
        ("Lebron James", 2, "6:00 AM", "4:30 PM"),
        ("Lebron James", 4, "6:00 AM", "4:30 PM"),
        ("Wilt Chamberlain", 0, "9:00 AM", "5:00 PM"),
        ("Wilt Chamberlain", 1, "9:00 AM", "5:00 PM"),
        ("Caitlin Clark", 0, "9:00 AM", "5:30 PM"),
        ("Caleb Williams", 0, "11:00 AM", "8:30 PM"),
    ]
    db.executemany(
        "INSERT INTO shifts (employee_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
        [(emp_ids[n], wd, s, e) for n, wd, s, e in shifts],
    )

    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def item_status(item):
    if item["quantity"] < item["reorder_threshold"]:
        return "low"
    if item["quantity"] > item["max_threshold"]:
        return "over"
    return "in-stock"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")
        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    reset_db()
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    db = get_db()
    total_items = db.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    low_stock = db.execute("SELECT COUNT(*) FROM inventory WHERE quantity < reorder_threshold").fetchone()[0]
    today = date.today().isoformat()
    expected_today = db.execute(
        "SELECT COUNT(*) FROM shipments WHERE expected_at LIKE ?", (today + "%",)
    ).fetchone()[0]
    delayed = db.execute("SELECT COUNT(*) FROM shipments WHERE status = 'history'").fetchone()[0]
    vendor_count = db.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]
    weekday_today = min(date.today().weekday(), 4)
    scheduled_today = db.execute(
        "SELECT COUNT(*) FROM shifts WHERE weekday = ?", (weekday_today,)
    ).fetchone()[0]
    return render_template(
        "dashboard.html",
        total_items=total_items,
        low_stock=low_stock,
        expected_today=expected_today,
        delayed=delayed,
        vendor_count=vendor_count,
        scheduled_today=scheduled_today,
    )


@app.route("/inventory")
@login_required
def inventory_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    where = ""
    params = []
    if q:
        where = "WHERE i.name LIKE ? OR i.sku LIKE ? OR v.name LIKE ?"
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    total = db.execute(
        f"SELECT COUNT(*) FROM inventory i JOIN vendors v ON v.id = i.vendor_id {where}", params
    ).fetchone()[0]
    rows = db.execute(
        f"""SELECT i.*, v.name AS vendor_name FROM inventory i
            JOIN vendors v ON v.id = i.vendor_id {where}
            ORDER BY i.id LIMIT ? OFFSET ?""",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE],
    ).fetchall()
    items = [dict(r, status=item_status(r)) for r in rows]
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    return render_template(
        "inventory.html", items=items, q=q, page=page, total_pages=total_pages
    )


@app.route("/inventory/low-stock")
@login_required
def inventory_low_stock():
    db = get_db()
    rows = db.execute(
        """SELECT i.*, v.name AS vendor_name FROM inventory i
           JOIN vendors v ON v.id = i.vendor_id
           WHERE i.quantity < i.reorder_threshold ORDER BY i.id"""
    ).fetchall()
    return render_template("inventory_low.html", items=rows)


@app.route("/inventory/overstock")
@login_required
def inventory_overstock():
    db = get_db()
    rows = db.execute(
        """SELECT i.*, v.name AS vendor_name FROM inventory i
           JOIN vendors v ON v.id = i.vendor_id
           WHERE i.quantity > i.max_threshold ORDER BY i.id"""
    ).fetchall()
    return render_template("inventory_over.html", items=rows)


@app.route("/inventory/add", methods=["GET", "POST"])
@login_required
def inventory_add():
    db = get_db()
    vendors = db.execute("SELECT * FROM vendors ORDER BY name").fetchall()
    if request.method == "POST":
        db.execute(
            """INSERT INTO inventory (sku, name, vendor_id, department, date_received, quantity, reorder_threshold, max_threshold)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                request.form["sku"], request.form["name"], request.form["vendor_id"],
                request.form["department"], request.form["date_received"],
                int(request.form["quantity"]), int(request.form["reorder_threshold"]),
                int(request.form["max_threshold"]),
            ),
        )
        db.commit()
        return redirect(url_for("inventory_list"))
    return render_template("inventory_form.html", item=None, vendors=vendors)


@app.route("/inventory/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def inventory_edit(item_id):
    db = get_db()
    vendors = db.execute("SELECT * FROM vendors ORDER BY name").fetchall()
    item = db.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if request.method == "POST":
        db.execute(
            """UPDATE inventory SET sku=?, name=?, vendor_id=?, department=?, date_received=?,
               quantity=?, reorder_threshold=?, max_threshold=? WHERE id=?""",
            (
                request.form["sku"], request.form["name"], request.form["vendor_id"],
                request.form["department"], request.form["date_received"],
                int(request.form["quantity"]), int(request.form["reorder_threshold"]),
                int(request.form["max_threshold"]), item_id,
            ),
        )
        db.commit()
        return redirect(url_for("inventory_list"))
    return render_template("inventory_form.html", item=item, vendors=vendors)


@app.route("/inventory/<int:item_id>/delete", methods=["POST"])
@login_required
def inventory_delete(item_id):
    db = get_db()
    db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    db.commit()
    return redirect(url_for("inventory_list"))


@app.route("/inventory/<int:item_id>/reorder", methods=["POST"])
@login_required
def inventory_reorder(item_id):
    db = get_db()
    item = db.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if item:
        new_qty = item["reorder_threshold"] * 2
        db.execute("UPDATE inventory SET quantity = ? WHERE id = ?", (new_qty, item_id))
        db.commit()
    return redirect(url_for("inventory_low_stock"))


@app.route("/inventory/<int:item_id>/clearance", methods=["POST"])
@login_required
def inventory_clearance(item_id):
    db = get_db()
    db.execute("UPDATE inventory SET on_clearance = 1 WHERE id = ?", (item_id,))
    db.commit()
    return redirect(url_for("inventory_overstock"))


@app.route("/shipments")
@login_required
def shipments_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    direction = request.args.get("direction", "inbound")
    status_filter = request.args.get("status", "expected")
    where = ["direction = ?", "status = ?"]
    params = [direction, status_filter]
    if q:
        where.append("(company LIKE ? OR code LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    rows = db.execute(
        f"SELECT * FROM shipments WHERE {' AND '.join(where)} ORDER BY expected_at", params
    ).fetchall()
    return render_template(
        "shipments.html", shipments=rows, q=q, direction=direction, status_filter=status_filter
    )


@app.route("/shipments/add", methods=["GET", "POST"])
@login_required
def shipments_add():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO shipments (code, company, item_count, expected_at, direction, status) VALUES (?,?,?,?,?,?)",
            (
                request.form["code"], request.form["company"], int(request.form["item_count"]),
                request.form["expected_at"], request.form["direction"], request.form["status"],
            ),
        )
        db.commit()
        return redirect(url_for("shipments_list"))
    return render_template("shipment_form.html", shipment=None)


@app.route("/shipments/<int:shipment_id>/edit", methods=["GET", "POST"])
@login_required
def shipments_edit(shipment_id):
    db = get_db()
    shipment = db.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
    if request.method == "POST":
        db.execute(
            """UPDATE shipments SET code=?, company=?, item_count=?, expected_at=?, direction=?, status=?
               WHERE id=?""",
            (
                request.form["code"], request.form["company"], int(request.form["item_count"]),
                request.form["expected_at"], request.form["direction"], request.form["status"],
                shipment_id,
            ),
        )
        db.commit()
        return redirect(url_for("shipments_list"))
    return render_template("shipment_form.html", shipment=shipment)


@app.route("/shipments/<int:shipment_id>/delete", methods=["POST"])
@login_required
def shipments_delete(shipment_id):
    db = get_db()
    db.execute("DELETE FROM shipments WHERE id = ?", (shipment_id,))
    db.commit()
    return redirect(url_for("shipments_list"))


@app.route("/vendors")
@login_required
def vendors_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    where = ""
    params = []
    if q:
        where = "WHERE name LIKE ?"
        params = [f"%{q}%"]
    vendors = db.execute(f"SELECT * FROM vendors {where} ORDER BY name", params).fetchall()
    return render_template("vendors.html", vendors=vendors, q=q)


@app.route("/vendors/add", methods=["GET", "POST"])
@login_required
def vendors_add():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO vendors (name, contact_name, phone, email, notes) VALUES (?,?,?,?,?)",
            (
                request.form["name"], request.form["contact_name"],
                request.form["phone"], request.form["email"], request.form["notes"],
            ),
        )
        db.commit()
        return redirect(url_for("vendors_list"))
    return render_template("vendor_form.html")


@app.route("/vendors/<int:vendor_id>")
@login_required
def vendor_detail(vendor_id):
    db = get_db()
    vendor = db.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if vendor is None:
        return redirect(url_for("vendors_list"))
    messages = db.execute(
        "SELECT * FROM vendor_messages WHERE vendor_id = ? ORDER BY sent_at DESC", (vendor_id,)
    ).fetchall()
    return render_template("vendor_detail.html", vendor=vendor, messages=messages)


@app.route("/vendors/<int:vendor_id>/message", methods=["POST"])
@login_required
def vendor_message(vendor_id):
    db = get_db()
    vendor = db.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if vendor is None:
        return redirect(url_for("vendors_list"))
    db.execute(
        "INSERT INTO vendor_messages (vendor_id, subject, body, sent_at) VALUES (?,?,?,?)",
        (vendor_id, request.form["subject"], request.form["body"], datetime.now().strftime("%b %d, %Y %H:%M")),
    )
    db.commit()
    return redirect(url_for("vendor_detail", vendor_id=vendor_id))


@app.route("/employees")
@login_required
def employees_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    where = ""
    params = []
    if q:
        where = "WHERE name LIKE ?"
        params = [f"%{q}%"]
    employees = db.execute(f"SELECT * FROM employees {where} ORDER BY name", params).fetchall()

    weekday = request.args.get("weekday", type=int)
    if weekday is None or not (0 <= weekday <= 4):
        weekday = min(date.today().weekday(), 4)

    roster = db.execute(
        """SELECT e.name, s.start_time, s.end_time FROM shifts s
           JOIN employees e ON e.id = s.employee_id
           WHERE s.weekday = ? ORDER BY s.start_time""",
        (weekday,),
    ).fetchall()

    selected_id = request.args.get("employee", type=int)
    selected = None
    if selected_id:
        selected = db.execute("SELECT * FROM employees WHERE id = ?", (selected_id,)).fetchone()
    if selected is None and employees:
        selected = employees[0]

    return render_template(
        "employees.html",
        employees=employees,
        selected=selected,
        roster=roster,
        weekday=weekday,
        weekday_label=WEEKDAYS[weekday],
        weekdays=list(enumerate(WEEKDAYS)),
        q=q,
    )


@app.route("/schedule/<int:employee_id>")
@login_required
def schedule_view(employee_id):
    db = get_db()
    employee = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if employee is None:
        return redirect(url_for("employees_list"))
    shifts = db.execute(
        "SELECT * FROM shifts WHERE employee_id = ? ORDER BY weekday", (employee_id,)
    ).fetchall()
    shifts_by_day = {s["weekday"]: s for s in shifts}
    return render_template(
        "schedule.html", employee=employee, shifts_by_day=shifts_by_day, weekdays=list(enumerate(WEEKDAYS))
    )


@app.route("/schedule/<int:employee_id>/edit", methods=["GET", "POST"])
@login_required
def schedule_edit(employee_id):
    db = get_db()
    employee = db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if employee is None:
        return redirect(url_for("employees_list"))
    if request.method == "POST":
        for wd in range(5):
            start = request.form.get(f"start_{wd}", "").strip()
            end = request.form.get(f"end_{wd}", "").strip()
            existing = db.execute(
                "SELECT id FROM shifts WHERE employee_id = ? AND weekday = ?", (employee_id, wd)
            ).fetchone()
            if not start or not end:
                if existing:
                    db.execute("DELETE FROM shifts WHERE id = ?", (existing["id"],))
                continue
            if existing:
                db.execute(
                    "UPDATE shifts SET start_time=?, end_time=? WHERE id=?",
                    (start, end, existing["id"]),
                )
            else:
                db.execute(
                    "INSERT INTO shifts (employee_id, weekday, start_time, end_time) VALUES (?,?,?,?)",
                    (employee_id, wd, start, end),
                )
        db.commit()
        return redirect(url_for("schedule_view", employee_id=employee_id))

    shifts = db.execute(
        "SELECT * FROM shifts WHERE employee_id = ? ORDER BY weekday", (employee_id,)
    ).fetchall()
    shifts_by_day = {s["weekday"]: s for s in shifts}
    return render_template(
        "schedule_form.html", employee=employee, shifts_by_day=shifts_by_day,
        weekdays=list(enumerate(WEEKDAYS)),
    )


with app.app_context():
    reset_db()

if __name__ == "__main__":
    app.run(debug=True)
