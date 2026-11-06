"""Flask routes for the Bison Operations prototype."""

import os
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash

load_dotenv()

import data_access
import database
from validations import (
    inventory_values, reorder_quantity, shipment_values, validate_inventory_form,
    validate_login, validate_reorder_form, validate_shipment_form,
    validate_vendor_form, validate_vendor_message, vendor_values,
)


ROLE_LABELS = {
    "supervisor": "Supervisor",
    "manager": "Manager",
    "team_member": "Team Member",
}
VENDOR_VIEW_ROLES = ("supervisor", "manager")
INVENTORY_EDIT_ROLES = ("supervisor", "manager")
SHIPMENT_EDIT_ROLES = ("supervisor", "manager")


def create_app(test_config=None):
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        print("SECRET_KEY is not set.")
        raise SystemExit("SECRET_KEY is not set.")

    application = Flask(__name__)
    application.config.update(SECRET_KEY=secret_key)
    if test_config:
        application.config.update(test_config)
    application.teardown_appcontext(database.close_db)
    register_error_handlers(application)
    register_routes(application)
    with application.app_context():
        database.init_db()
    return application


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login"))
            if session.get("role") not in allowed_roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def register_error_handlers(application):
    @application.errorhandler(403)
    def forbidden(error):
        return render_template(
            "error.html", code=403, message="You do not have permission to do that."
        ), 403

    @application.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="Record not found."), 404


def register_routes(application):
    @application.context_processor
    def shared_context():
        if not session.get("user_id"):
            return {"current_role": None, "role_label": None}
        role = session.get("role")
        return {
            "current_role": role,
            "role_label": ROLE_LABELS.get(role, ""),
        }

    @application.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            errors = validate_login(request.form)
            email = request.form.get("email", "").strip().lower()
            user = data_access.get_user_by_email(database.get_db(), email)
            if errors or user is None or not check_password_hash(
                user["password_hash"], request.form.get("password", "")
            ):
                return render_template("login.html", error="Invalid email or password.")
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["email"] = user["email"]
            return redirect(url_for("dashboard"))
        return render_template("login.html", error=None)

    @application.route("/logout", methods=["POST"])
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @application.route("/")
    @login_required
    def dashboard():
        return render_template("dashboard.html", **data_access.get_dashboard_data(database.get_db()))

    @application.route("/inventory")
    @login_required
    def inventory_list():
        query = request.args.get("q", "").strip()
        status_filter = request.args.get("status", request.args.get("filter", "all"))
        if status_filter not in {"all", "in-stock", "low", "over"}:
            status_filter = "all"
        sort = request.args.get("sort", "id")
        sort_direction = request.args.get("dir", "asc").lower()
        if sort_direction not in {"asc", "desc"}:
            sort_direction = "asc"
        try:
            page = max(int(request.args.get("page", "1")), 1)
        except ValueError:
            page = 1
        items, total_pages = data_access.get_inventory_page(
            database.get_db(), query, status_filter, sort, sort_direction, page
        )
        return render_template(
            "inventory.html", items=items, q=query, page=page, total_pages=total_pages,
            status_filter=status_filter, sort=sort, sort_dir=sort_direction,
        )

    @application.route("/inventory/low-stock")
    @login_required
    def inventory_low_stock():
        return render_template(
            "inventory_low.html",
            items=data_access.get_inventory_stock(database.get_db(), "low"),
        )

    @application.route("/inventory/overstock")
    @login_required
    def inventory_overstock():
        return render_template(
            "inventory_over.html",
            items=data_access.get_inventory_stock(database.get_db(), "over"),
        )

    def inventory_form_context(item=None, form_data=None, errors=None):
        return {
            "item": item,
            "vendors": data_access.list_vendors_for_form(database.get_db()),
            "form_data": form_data or {},
            "errors": errors or {},
        }

    @application.route("/inventory/add", methods=["GET", "POST"])
    @role_required(*INVENTORY_EDIT_ROLES)
    def inventory_add():
        if request.method == "POST":
            db = database.get_db()
            errors = validate_inventory_form(
                request.form,
                lambda name, excluding: data_access.inventory_name_exists(db, name, excluding),
                lambda sku, excluding: data_access.inventory_sku_exists(db, sku, excluding),
                lambda vendor_id: data_access.vendor_exists(db, vendor_id),
            )
            if errors:
                return render_template(
                    "inventory_form.html",
                    **inventory_form_context(form_data=request.form, errors=errors),
                )
            data_access.create_inventory(db, inventory_values(request.form))
            db.commit()
            flash("Inventory item added.")
            return redirect(url_for("inventory_list"))
        return render_template("inventory_form.html", **inventory_form_context())

    @application.route("/inventory/<int:item_id>/edit", methods=["GET", "POST"])
    @role_required(*INVENTORY_EDIT_ROLES)
    def inventory_edit(item_id):
        db = database.get_db()
        item = data_access.get_inventory_by_id(db, item_id)
        if item is None:
            abort(404)
        if request.method == "POST":
            errors = validate_inventory_form(
                request.form,
                lambda name, excluding: data_access.inventory_name_exists(db, name, excluding),
                lambda sku, excluding: data_access.inventory_sku_exists(db, sku, excluding),
                lambda vendor_id: data_access.vendor_exists(db, vendor_id),
                excluding_id=item_id,
            )
            if errors:
                return render_template(
                    "inventory_form.html",
                    **inventory_form_context(item, request.form, errors),
                )
            data_access.update_inventory(db, item_id, inventory_values(request.form))
            db.commit()
            flash("Inventory item updated.")
            return redirect(url_for("inventory_list"))
        return render_template("inventory_form.html", **inventory_form_context(item))

    @application.route("/inventory/<int:item_id>/delete", methods=["POST"])
    @role_required("supervisor")
    def inventory_delete(item_id):
        db = database.get_db()
        if not data_access.delete_inventory(db, item_id):
            abort(404)
        db.commit()
        flash("Inventory item deleted.")
        return redirect(url_for("inventory_list"))

    @application.route("/inventory/<int:item_id>/reorder", methods=["GET", "POST"])
    @role_required("supervisor")
    def inventory_reorder(item_id):
        db = database.get_db()
        item = data_access.get_reorder_item(db, item_id)
        if item is None:
            abort(404)
        suggested = max(item["max_threshold"] - item["quantity"], 1)
        if request.method == "POST":
            errors = validate_reorder_form(request.form)
            if errors:
                return render_template(
                    "reorder.html", item=item, suggested=suggested,
                    errors=errors, form_data=request.form,
                )
            code = data_access.create_purchase_order(
                db, item, reorder_quantity(request.form),
                request.form.get("note", "").strip(),
            )
            db.commit()
            flash(f"{code} sent to {item['vendor_name']}.")
            return redirect(url_for("vendor_detail", vendor_id=item["vendor_id"]))
        return render_template(
            "reorder.html", item=item, suggested=suggested, errors={}, form_data={},
        )

    @application.route("/purchase-orders/<int:order_id>/receive", methods=["POST"])
    @role_required("supervisor", "manager")
    def purchase_order_receive(order_id):
        db = database.get_db()
        vendor_id = data_access.receive_purchase_order(db, order_id)
        if vendor_id is None:
            abort(404)
        db.commit()
        flash("Purchase order marked received.")
        return redirect(url_for("vendor_detail", vendor_id=vendor_id))

    @application.route("/inventory/<int:item_id>/contact")
    @role_required("supervisor")
    def inventory_contact(item_id):
        item = data_access.get_inventory_by_id(database.get_db(), item_id)
        if item is None:
            abort(404)
        body = (
            f"Please restock {item['name']} ({item['sku']}). Current quantity: "
            f"{item['quantity']}; reorder threshold: {item['reorder_threshold']}; "
            f"suggested order quantity: "
            f"{max(item['max_threshold'] - item['quantity'], 1)}."
        )
        return redirect(url_for(
            "vendor_detail", vendor_id=item["vendor_id"],
            subject=f"Restock request: {item['name']} ({item['sku']})",
            body=body, item_id=item_id,
        ))

    @application.route("/shipments")
    @login_required
    def shipments_list():
        direction = request.args.get("direction", "inbound")
        status_filter = request.args.get("status", "expected")
        if direction not in {"inbound", "outbound"}:
            direction = "inbound"
        if status_filter not in {"expected", "active", "delayed", "history"}:
            status_filter = "expected"
        query = request.args.get("q", "").strip()
        return render_template(
            "shipments.html",
            shipments=data_access.get_shipments(
                database.get_db(), direction, status_filter, query
            ),
            q=query, direction=direction, status_filter=status_filter,
        )

    def shipment_form_context(shipment=None, form_data=None, errors=None):
        db = database.get_db()
        return {
            "shipment": shipment,
            "vendors": data_access.list_vendors_for_form(db),
            "products": data_access.list_inventory_for_form(db),
            "form_data": form_data or {},
            "errors": errors or {},
        }

    def shipment_errors(db, form, excluding_id=None):
        return validate_shipment_form(
            form,
            lambda code, excluding: data_access.shipment_code_exists(db, code, excluding),
            excluding_id,
            lambda item_id: data_access.inventory_exists(db, item_id),
            lambda vendor_id: data_access.vendor_exists(db, vendor_id),
        )

    @application.route("/shipments/add", methods=["GET", "POST"])
    @role_required(*SHIPMENT_EDIT_ROLES)
    def shipments_add():
        if request.method == "POST":
            db = database.get_db()
            errors = shipment_errors(db, request.form)
            if errors:
                return render_template(
                    "shipment_form.html",
                    **shipment_form_context(form_data=request.form, errors=errors),
                )
            data_access.create_shipment(db, shipment_values(request.form))
            db.commit()
            flash("Shipment added.")
            return redirect(url_for("shipments_list"))
        return render_template("shipment_form.html", **shipment_form_context())

    @application.route("/shipments/<int:shipment_id>/edit", methods=["GET", "POST"])
    @role_required(*SHIPMENT_EDIT_ROLES)
    def shipments_edit(shipment_id):
        db = database.get_db()
        shipment = data_access.get_shipment_by_id(db, shipment_id)
        if shipment is None:
            abort(404)
        if request.method == "POST":
            errors = shipment_errors(db, request.form, shipment_id)
            if errors:
                return render_template(
                    "shipment_form.html",
                    **shipment_form_context(shipment, request.form, errors),
                )
            data_access.update_shipment(db, shipment_id, shipment_values(request.form))
            db.commit()
            flash("Shipment updated.")
            return redirect(url_for("shipments_list"))
        return render_template("shipment_form.html", **shipment_form_context(shipment))

    @application.route("/shipments/<int:shipment_id>/delete", methods=["POST"])
    @role_required("supervisor")
    def shipments_delete(shipment_id):
        db = database.get_db()
        if not data_access.delete_shipment(db, shipment_id):
            abort(404)
        db.commit()
        flash("Shipment deleted.")
        return redirect(url_for("shipments_list"))

    @application.route("/vendors")
    @role_required(*VENDOR_VIEW_ROLES)
    def vendors_list():
        query = request.args.get("q", "").strip()
        category = request.args.get("category", "")
        if category and category not in {"Dairy", "Beverages", "Dry Goods", "Cleaning", "Frozen"}:
            category = ""
        return render_template(
            "vendors.html", vendors=data_access.get_vendors(database.get_db(), query, category),
            q=query, category_filter=category,
        )

    def vendor_form_context(vendor=None, form_data=None, errors=None):
        return {
            "vendor": vendor, "form_data": form_data or {}, "errors": errors or {},
        }

    @application.route("/vendors/add", methods=["GET", "POST"])
    @role_required("supervisor")
    def vendors_add():
        if request.method == "POST":
            errors = validate_vendor_form(request.form)
            if errors:
                return render_template(
                    "vendor_form.html",
                    **vendor_form_context(form_data=request.form, errors=errors),
                )
            db = database.get_db()
            data_access.create_vendor(db, vendor_values(request.form))
            db.commit()
            flash("Vendor added.")
            return redirect(url_for("vendors_list"))
        return render_template("vendor_form.html", **vendor_form_context())

    @application.route("/vendors/<int:vendor_id>/edit", methods=["GET", "POST"])
    @role_required("supervisor")
    def vendor_edit(vendor_id):
        db = database.get_db()
        vendor = data_access.get_vendor_by_id(db, vendor_id)
        if vendor is None:
            abort(404)
        if request.method == "POST":
            errors = validate_vendor_form(request.form)
            if errors:
                return render_template(
                    "vendor_form.html",
                    **vendor_form_context(vendor, request.form, errors),
                )
            data_access.update_vendor(db, vendor_id, vendor_values(request.form))
            db.commit()
            flash("Vendor updated.")
            return redirect(url_for("vendor_detail", vendor_id=vendor_id))
        return render_template("vendor_form.html", **vendor_form_context(vendor))

    @application.route("/vendors/<int:vendor_id>/delete", methods=["POST"])
    @role_required("supervisor")
    def vendor_delete(vendor_id):
        db = database.get_db()
        vendor = data_access.get_vendor_by_id(db, vendor_id)
        if vendor is None:
            abort(404)
        item_count = data_access.count_vendor_inventory(db, vendor_id)
        if item_count:
            flash(
                f"{vendor['name']} still supplies {item_count} inventory items. "
                "Reassign or delete them first."
            )
            return redirect(url_for("vendors_list"))
        data_access.delete_vendor(db, vendor_id)
        db.commit()
        flash("Vendor deleted.")
        return redirect(url_for("vendors_list"))

    @application.route("/vendors/<int:vendor_id>")
    @role_required(*VENDOR_VIEW_ROLES)
    def vendor_detail(vendor_id):
        db = database.get_db()
        vendor = data_access.get_vendor_by_id(db, vendor_id)
        if vendor is None:
            abort(404)
        detail = data_access.get_vendor_detail_data(db, vendor_id)
        pre_item = request.args.get("item_id", "")
        if pre_item and not pre_item.isdigit():
            abort(400)
        return render_template(
            "vendor_detail.html", vendor=vendor, **detail,
            pre_subject=request.args.get("subject", ""),
            pre_body=request.args.get("body", ""), pre_item=pre_item,
            errors={}, form_data={},
        )

    @application.route("/vendors/<int:vendor_id>/message", methods=["POST"])
    @role_required("supervisor")
    def vendor_message(vendor_id):
        db = database.get_db()
        vendor = data_access.get_vendor_by_id(db, vendor_id)
        if vendor is None:
            abort(404)
        errors = validate_vendor_message(request.form)
        inventory_id = request.form.get("inventory_id", "").strip()
        if inventory_id:
            if not inventory_id.isdigit():
                errors["inventory_id"] = "Choose a valid inventory item."
            else:
                item = data_access.get_inventory_by_id(db, int(inventory_id))
                if item is None or item["vendor_id"] != vendor_id:
                    errors["inventory_id"] = "Choose a valid inventory item."
        if errors:
            detail = data_access.get_vendor_detail_data(db, vendor_id)
            return render_template(
                "vendor_detail.html", vendor=vendor, **detail,
                pre_subject="", pre_body="", pre_item="",
                errors=errors, form_data=request.form,
            )
        data_access.create_vendor_message(
            db, vendor_id,
            {
                "subject": request.form.get("subject", "").strip(),
                "body": request.form.get("body", "").strip(),
                "inventory_id": int(inventory_id) if inventory_id else None,
            },
        )
        db.commit()
        flash("Message recorded.")
        return redirect(url_for("vendor_detail", vendor_id=vendor_id))


app = create_app()


if __name__ == "__main__":
    app.run(debug=False)
