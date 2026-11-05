import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import Flask, g, redirect, render_template, request, session, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash

DATABASE = "bison.db"
PAGE_SIZE = 5

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
        DROP TABLE IF EXISTS shipment_items;
        DROP TABLE IF EXISTS purchase_orders;
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
            notes TEXT,
            category TEXT
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
            on_clearance INTEGER NOT NULL DEFAULT 0,
            perishable INTEGER NOT NULL DEFAULT 0,
            overstock_action TEXT,
            unit_cost REAL DEFAULT 0
        );
        CREATE TABLE vendor_messages (
            id INTEGER PRIMARY KEY,
            vendor_id INTEGER NOT NULL REFERENCES vendors(id),
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            inventory_id INTEGER REFERENCES inventory(id)
        );
        CREATE TABLE shipments (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            company TEXT NOT NULL,
            item_count INTEGER NOT NULL,
            expected_at TEXT NOT NULL,
            direction TEXT NOT NULL DEFAULT 'inbound',
            status TEXT NOT NULL DEFAULT 'expected',
            vendor_id INTEGER REFERENCES vendors(id)
        );
        CREATE TABLE shipment_items (id INTEGER PRIMARY KEY, shipment_id INTEGER REFERENCES shipments(id), inventory_id INTEGER REFERENCES inventory(id), quantity INTEGER NOT NULL);
        CREATE TABLE purchase_orders (id INTEGER PRIMARY KEY, code TEXT NOT NULL, inventory_id INTEGER REFERENCES inventory(id), vendor_id INTEGER REFERENCES vendors(id), quantity INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, note TEXT);
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
         "Supplier of dry goods and snack products. Contract renewal scheduled for October 2026.", "Dry Goods"),
        ("Pacific Beverage Co.", "Jordan Lee", "(206) 555-0143",
         "jordan@pacificbev.example", "Beverage distributor for the Pacific region.", "Beverages"),
        ("Sunrise Foods Co.", "Pat Nguyen", "(414) 555-0110",
         "pat@sunrisefoods.example", "Frozen and dairy goods supplier.", "Frozen"),
        ("CleanPro Supply", "Dana Reyes", "(773) 555-0199",
         "dana@cleanpro.example", "Cleaning and sanitation supplies.", "Cleaning"),
        ("Dairy Fresh Distributors", "Sam Carter", "(630) 555-0177",
         "sam@dairyfresh.example", "Regional dairy distributor.", "Dairy"),
    ]
    db.executemany(
        "INSERT INTO vendors (name, contact_name, phone, email, notes, category) VALUES (?,?,?,?,?,?)",
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
        ("SHP-10492", "Pacific Beverage Co.", 200, "2026-09-19 08:00", "inbound", "expected"),
        ("SHP-10483", "Crown Packaging Co.", 65, "2026-09-18 11:30", "inbound", "expected"),
        ("SHP-10471", "Vantage Fastener Corp", 550, "2026-09-18 13:00", "inbound", "expected"),
        ("SHP-10410", "Hoosier Rubber & Seal", 150, "2026-09-18 08:00", "inbound", "active"),
        ("SHP-10403", "Apex Bearing Distribution", 60, "2026-09-18 13:15", "inbound", "history"),
        ("SHP-10351", "Sterling Wire Products", 320, "2026-09-20 10:00", "inbound", "delayed"),
        ("SHP-20011", "Great Lakes Freight", 300, "2026-09-19 09:00", "outbound", "expected"),
    ]
    db.executemany(
        "INSERT INTO shipments (code, company, item_count, expected_at, direction, status, vendor_id) VALUES (?,?,?,?,?,?,?)",
        [s + (vendor_ids.get(s[1]),) for s in shipments],
    )
    sparkling = db.execute("SELECT id FROM inventory WHERE name LIKE 'Sparkling Water%'").fetchone()[0]
    shipment_id = db.execute("SELECT id FROM shipments WHERE code='SHP-10492'").fetchone()[0]
    db.execute("INSERT INTO shipment_items (shipment_id, inventory_id, quantity) VALUES (?,?,?)", (shipment_id, sparkling, 200))

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

@app.context_processor
def global_alerts():
    if not session.get('user_id'): return {'alert_count': 0}
    db=get_db()
    return {'alert_count': db.execute("SELECT (SELECT COUNT(*) FROM inventory WHERE quantity<reorder_threshold)+(SELECT COUNT(*) FROM shipments WHERE status='delayed')").fetchone()[0]}


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
    delayed = db.execute("SELECT COUNT(*) FROM shipments WHERE status = 'delayed'").fetchone()[0]
    lows = db.execute("SELECT i.*,v.name vendor_name FROM inventory i LEFT JOIN vendors v ON v.id=i.vendor_id WHERE quantity < reorder_threshold ORDER BY name").fetchall()
    overs = db.execute("SELECT i.*,v.name vendor_name FROM inventory i LEFT JOIN vendors v ON v.id=i.vendor_id WHERE quantity > max_threshold ORDER BY name").fetchall()
    delayed_shipments = db.execute("SELECT s.*,GROUP_CONCAT(i.name, ', ') products FROM shipments s LEFT JOIN shipment_items si ON si.shipment_id=s.id LEFT JOIN inventory i ON i.id=si.inventory_id WHERE s.status='delayed' GROUP BY s.id ORDER BY expected_at").fetchall()
    lows = [dict(item) for item in lows]
    for item in lows:
        item_in = db.execute("SELECT s.code,s.company,s.expected_at FROM shipment_items si JOIN shipments s ON s.id=si.shipment_id WHERE si.inventory_id=? AND s.vendor_id=? AND s.status IN ('expected','active','delayed') ORDER BY s.expected_at LIMIT 1", (item['id'],item['vendor_id'])).fetchone()
        item['incoming'] = item_in
    return render_template(
        "dashboard.html",
        total_items=total_items,
        low_stock=low_stock,
        expected_today=expected_today,
        delayed=delayed,
        low_items=lows, over_items=overs, delayed_shipments=delayed_shipments,
    )


@app.route("/inventory")
@login_required
def inventory_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "all")
    sort = request.args.get("sort", "id")
    direction = "DESC" if request.args.get("dir", "asc").lower() == "desc" else "ASC"
    sort_columns = {"sku":"i.sku", "name":"i.name", "vendor":"v.name", "department":"i.department", "date":"i.date_received", "quantity":"i.quantity", "status":"i.quantity"}
    order = sort_columns.get(sort, "i.id")
    page = max(int(request.args.get("page", 1)), 1)
    where = ""
    params = []
    conditions=[]
    if q:
        conditions.append("(i.name LIKE ? OR i.sku LIKE ? OR v.name LIKE ? OR i.department LIKE ? OR i.date_received LIKE ? OR CAST(i.quantity AS TEXT) LIKE ?)")
        params = [f"%{q}%"]*6
    if status_filter == "low": conditions.append("i.quantity < i.reorder_threshold")
    elif status_filter == "over": conditions.append("i.quantity > i.max_threshold")
    elif status_filter in ("in-stock", "in_stock"): conditions.append("i.quantity >= i.reorder_threshold AND i.quantity <= i.max_threshold")
    if conditions: where="WHERE " + " AND ".join(conditions)
    total = db.execute(
        f"SELECT COUNT(*) FROM inventory i JOIN vendors v ON v.id = i.vendor_id {where}", params
    ).fetchone()[0]
    rows = db.execute(
        f"""SELECT i.*, v.name AS vendor_name FROM inventory i
            JOIN vendors v ON v.id = i.vendor_id {where}
            ORDER BY {order} {direction} LIMIT ? OFFSET ?""",
        params + [PAGE_SIZE, (page - 1) * PAGE_SIZE],
    ).fetchall()
    items = [dict(r, status=item_status(r)) for r in rows]
    for item in items:
        item['incoming'] = db.execute("SELECT si.quantity,s.expected_at,s.status FROM shipment_items si JOIN shipments s ON s.id=si.shipment_id WHERE si.inventory_id=? AND s.status IN ('expected','active','delayed') ORDER BY s.expected_at LIMIT 1", (item['id'],)).fetchone()
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    return render_template(
        "inventory.html", items=items, q=q, page=page, total_pages=total_pages, status_filter=status_filter, sort=sort, sort_dir=direction.lower()
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


@app.route("/inventory/<int:item_id>/reorder", methods=["GET", "POST"])
@login_required
def inventory_reorder(item_id):
    db = get_db()
    item = db.execute("SELECT i.*,v.name vendor_name,v.contact_name,v.email FROM inventory i LEFT JOIN vendors v ON v.id=i.vendor_id WHERE i.id=?", (item_id,)).fetchone()
    if not item: return redirect(url_for("inventory_list"))
    suggested = max(item['max_threshold'] - item['quantity'], 1)
    if request.method == "POST":
        qty = max(int(request.form.get('quantity', suggested)), 1)
        code = f"PO-{db.execute('SELECT COUNT(*) FROM purchase_orders').fetchone()[0]+1001}"
        note = request.form.get('note','').strip()
        db.execute("INSERT INTO purchase_orders (code,inventory_id,vendor_id,quantity,status,created_at,note) VALUES (?,?,?,?,?,?,?)", (code,item_id,item['vendor_id'],qty,'pending',datetime.now().strftime('%Y-%m-%d %H:%M'),note))
        subject=f"Purchase order {code}: {item['name']} ({item['sku']})"
        body=f"Please fulfill {qty} units of {item['name']} ({item['sku']}). Current quantity: {item['quantity']}." + (f" Note: {note}" if note else "")
        db.execute("INSERT INTO vendor_messages (vendor_id,subject,body,sent_at,inventory_id) VALUES (?,?,?,?,?)", (item['vendor_id'],subject,body,datetime.now().strftime('%b %d, %Y %H:%M'),item_id))
        db.commit()
        flash(f"{code} sent to {item['vendor_name']}.")
        return redirect(url_for('vendor_detail',vendor_id=item['vendor_id']))
    return render_template('reorder.html', item=item, suggested=suggested)

@app.route('/purchase-orders/<int:order_id>/receive', methods=['POST'])
@login_required
def purchase_order_receive(order_id):
    db=get_db(); po=db.execute('SELECT * FROM purchase_orders WHERE id=?',(order_id,)).fetchone()
    if po and po['status']=='pending':
        db.execute('UPDATE inventory SET quantity=quantity+? WHERE id=?',(po['quantity'],po['inventory_id']))
        db.execute("UPDATE purchase_orders SET status='received' WHERE id=?",(order_id,)); db.commit()
    return redirect(url_for('vendor_detail',vendor_id=po['vendor_id'])) if po else redirect(url_for('vendors_list'))

@app.route('/inventory/<int:item_id>/contact')
@login_required
def inventory_contact(item_id):
    db=get_db(); item=db.execute('SELECT * FROM inventory WHERE id=?',(item_id,)).fetchone()
    if not item: return redirect(url_for('inventory_list'))
    vendor_id=item['vendor_id']; body=f"Please restock {item['name']} ({item['sku']}). Current quantity: {item['quantity']}; reorder threshold: {item['reorder_threshold']}; suggested order quantity: {max(item['max_threshold']-item['quantity'],1)}."
    return redirect(url_for('vendor_detail',vendor_id=vendor_id,subject=f"Restock request: {item['name']} ({item['sku']})",body=body,item_id=item_id))


@app.route("/inventory/<int:item_id>/clearance", methods=["POST"])
@login_required
def inventory_clearance(item_id):
    db = get_db()
    action=request.form.get('action','Mark for Clearance')
    db.execute("UPDATE inventory SET on_clearance = ?, overstock_action = ? WHERE id = ?", (1 if action=='Mark for Clearance' else 0, action, item_id))
    db.commit()
    return redirect(url_for("inventory_overstock"))


@app.route("/shipments")
@login_required
def shipments_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    direction = request.args.get("direction", "inbound")
    status_filter = request.args.get("status", "expected")
    if status_filter not in ('expected','active','delayed','history'): status_filter='expected'
    where = ["direction = ?", "status = ?"]
    params = [direction, status_filter]
    if q:
        where.append("(company LIKE ? OR code LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    rows = db.execute(
        f"SELECT s.*, GROUP_CONCAT(i.name, ', ') products FROM shipments s LEFT JOIN shipment_items si ON si.shipment_id=s.id LEFT JOIN inventory i ON i.id=si.inventory_id WHERE {' AND '.join('s.'+x if x in ('direction = ?', 'status = ?') else x.replace('company','s.company').replace('code','s.code') for x in where)} GROUP BY s.id ORDER BY s.expected_at", params
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
            "INSERT INTO shipments (code, company, item_count, expected_at, direction, status, vendor_id) VALUES (?,?,?,?,?,?,?)",
            (
                request.form["code"], request.form["company"], int(request.form["item_count"]),
                request.form["expected_at"].replace('T',' '), request.form["direction"], request.form["status"], request.form.get('vendor_id') or None,
            ),
        )
        sid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        if request.form.get('inventory_id'):
            db.execute("INSERT INTO shipment_items (shipment_id, inventory_id, quantity) VALUES (?,?,?)", (sid, int(request.form['inventory_id']), int(request.form.get('quantity') or 0)))
        db.commit()
        return redirect(url_for("shipments_list"))
    return render_template("shipment_form.html", shipment=None, vendors=db.execute("SELECT * FROM vendors ORDER BY name").fetchall(), products=db.execute("SELECT * FROM inventory ORDER BY name").fetchall())


@app.route("/shipments/<int:shipment_id>/edit", methods=["GET", "POST"])
@login_required
def shipments_edit(shipment_id):
    db = get_db()
    shipment = db.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
    if request.method == "POST":
        db.execute(
            """UPDATE shipments SET code=?, company=?, item_count=?, expected_at=?, direction=?, status=?, vendor_id=?
               WHERE id=?""",
            (
                request.form["code"], request.form["company"], int(request.form["item_count"]),
                request.form["expected_at"].replace('T',' '), request.form["direction"], request.form["status"], request.form.get('vendor_id') or None,
                shipment_id,
            ),
        )
        db.execute("DELETE FROM shipment_items WHERE shipment_id=?", (shipment_id,))
        if request.form.get('inventory_id'):
            db.execute("INSERT INTO shipment_items (shipment_id, inventory_id, quantity) VALUES (?,?,?)", (shipment_id, int(request.form['inventory_id']), int(request.form.get('quantity') or 0)))
        db.commit()
        return redirect(url_for("shipments_list"))
    return render_template("shipment_form.html", shipment=shipment, vendors=db.execute("SELECT * FROM vendors ORDER BY name").fetchall(), products=db.execute("SELECT * FROM inventory ORDER BY name").fetchall())


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
    category=request.args.get('category','')
    where = ""
    params = []
    if q:
        where = "WHERE name LIKE ?"
        params = [f"%{q}%"]
    if category:
        where += (' AND ' if where else 'WHERE ')+'category = ?'; params.append(category)
    vendors = db.execute(f"SELECT * FROM vendors {where} ORDER BY name", params).fetchall()
    return render_template("vendors.html", vendors=vendors, q=q, category=category)


@app.route("/vendors/add", methods=["GET", "POST"])
@login_required
def vendors_add():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO vendors (name, contact_name, phone, email, notes, category) VALUES (?,?,?,?,?,?)",
            (
                request.form["name"], request.form["contact_name"],
                request.form["phone"], request.form["email"], request.form["notes"], request.form.get('category','Dry Goods'),
            ),
        )
        db.commit()
        return redirect(url_for("vendors_list"))
    return render_template("vendor_form.html")

@app.route('/vendors/<int:vendor_id>/edit', methods=['GET','POST'])
@login_required
def vendor_edit(vendor_id):
    db=get_db(); vendor=db.execute('SELECT * FROM vendors WHERE id=?',(vendor_id,)).fetchone()
    if not vendor: return redirect(url_for('vendors_list'))
    if request.method=='POST':
        db.execute('UPDATE vendors SET name=?,contact_name=?,phone=?,email=?,notes=?,category=? WHERE id=?',(request.form['name'],request.form['contact_name'],request.form['phone'],request.form['email'],request.form['notes'],request.form.get('category','Dry Goods'),vendor_id)); db.commit()
        return redirect(url_for('vendor_detail',vendor_id=vendor_id))
    return render_template('vendor_form.html',vendor=vendor)

@app.route('/vendors/<int:vendor_id>/delete', methods=['POST'])
@login_required
def vendor_delete(vendor_id):
    db=get_db()
    db.execute('DELETE FROM vendor_messages WHERE vendor_id=?',(vendor_id,))
    db.execute('DELETE FROM purchase_orders WHERE vendor_id=?',(vendor_id,))
    db.execute('UPDATE inventory SET vendor_id=NULL WHERE vendor_id=?',(vendor_id,))
    db.execute('UPDATE shipments SET vendor_id=NULL WHERE vendor_id=?',(vendor_id,))
    db.execute('DELETE FROM vendors WHERE id=?',(vendor_id,)); db.commit()
    return redirect(url_for('vendors_list'))


@app.route("/vendors/<int:vendor_id>")
@login_required
def vendor_detail(vendor_id):
    db = get_db()
    vendor = db.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if vendor is None:
        return redirect(url_for("vendors_list"))
    messages = db.execute("SELECT m.*,i.name item_name,i.sku FROM vendor_messages m LEFT JOIN inventory i ON i.id=m.inventory_id WHERE m.vendor_id = ? ORDER BY sent_at DESC", (vendor_id,)).fetchall()
    products=db.execute("SELECT * FROM inventory WHERE vendor_id=? ORDER BY name",(vendor_id,)).fetchall()
    orders=db.execute("SELECT p.*,i.name item_name FROM purchase_orders p JOIN inventory i ON i.id=p.inventory_id WHERE p.vendor_id=? ORDER BY p.created_at DESC",(vendor_id,)).fetchall()
    shipments=db.execute("SELECT * FROM shipments WHERE vendor_id=? ORDER BY expected_at DESC",(vendor_id,)).fetchall()
    stats={'shipments':len(shipments),'delayed':sum(s['status']=='delayed' for s in shipments),'last_message':messages[0]['sent_at'] if messages else '—'}
    return render_template("vendor_detail.html", vendor=vendor, messages=messages, products=products, orders=orders, shipments=shipments, stats=stats, pre_subject=request.args.get('subject',''), pre_body=request.args.get('body',''), pre_item=request.args.get('item_id',''))


@app.route("/vendors/<int:vendor_id>/message", methods=["POST"])
@login_required
def vendor_message(vendor_id):
    db = get_db()
    vendor = db.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    if vendor is None:
        return redirect(url_for("vendors_list"))
    db.execute(
        "INSERT INTO vendor_messages (vendor_id, subject, body, sent_at, inventory_id) VALUES (?,?,?,?,?)",
        (vendor_id, request.form["subject"], request.form["body"], datetime.now().strftime("%b %d, %Y %H:%M"), request.form.get('inventory_id') or None),
    )
    db.commit()
    return redirect(url_for("vendor_detail", vendor_id=vendor_id))


with app.app_context():
    reset_db()

if __name__ == "__main__":
    app.run(debug=True)
