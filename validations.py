"""Server-side form validation for application routes."""

from datetime import datetime


def _text(form, field):
    return form.get(field, "").strip()


def _whole_number(form, field, label, minimum, maximum=None):
    raw = _text(form, field)
    if maximum is not None:
        error_message = (
            f"{label} must be a whole number from {minimum:,} to {maximum:,}."
        )
    else:
        error_message = f"{label} must be a whole number of {minimum} or more."
    if not raw:
        return None, error_message
    try:
        value = int(raw)
    except ValueError:
        return None, error_message
    if value < minimum or (maximum is not None and value > maximum):
        return None, error_message
    return value, None


def validate_login(form):
    errors = {}
    if not _text(form, "email") or not form.get("password", ""):
        errors["form"] = "Invalid email or password."
    return errors


def validate_inventory_form(form, name_exists, sku_exists, vendor_exists, excluding_id=None):
    errors = {}
    values = {}
    for field, label in (("sku", "SKU"), ("name", "Item name"), ("vendor_id", "Vendor"),
                         ("department", "Department"), ("date_received", "Date received")):
        if not _text(form, field):
            errors[field] = f"{label} is required."
    name = _text(form, "name")
    sku = _text(form, "sku")
    if name and name_exists(name, excluding_id):
        errors["name"] = f"An item named {name} already exists."
    if sku and sku_exists(sku, excluding_id):
        errors["sku"] = f"An item with SKU {sku} already exists."
    vendor_id = _text(form, "vendor_id")
    try:
        if not vendor_id or not vendor_exists(int(vendor_id)):
            errors["vendor_id"] = "Choose a valid vendor."
    except ValueError:
        errors["vendor_id"] = "Choose a valid vendor."
    try:
        datetime.strptime(_text(form, "date_received"), "%Y-%m-%d")
    except ValueError:
        if _text(form, "date_received"):
            errors["date_received"] = "Enter a valid date."
    for field, label in (("quantity", "Quantity"), ("reorder_threshold", "Reorder threshold"),
                         ("max_threshold", "Max threshold")):
        value, error = _whole_number(form, field, label, 0)
        if error:
            errors[field] = error
        else:
            values[field] = value
    if not errors.get("reorder_threshold") and not errors.get("max_threshold"):
        if values["max_threshold"] <= values["reorder_threshold"]:
            errors["max_threshold"] = "Max threshold must be greater than reorder threshold."
    return errors


def inventory_values(form):
    return {
        "sku": _text(form, "sku"),
        "name": _text(form, "name"),
        "vendor_id": int(_text(form, "vendor_id")),
        "department": _text(form, "department"),
        "date_received": _text(form, "date_received"),
        "quantity": int(_text(form, "quantity")),
        "reorder_threshold": int(_text(form, "reorder_threshold")),
        "max_threshold": int(_text(form, "max_threshold")),
    }


def form_values(form, fields):
    return {field: _text(form, field) for field in fields}


def validate_reorder_form(form):
    _, error = _whole_number(form, "quantity", "Order quantity", 1, 10000)
    return {"quantity": error} if error else {}


def reorder_quantity(form):
    return int(_text(form, "quantity"))


def validate_vendor_message(form):
    errors = {}
    subject = _text(form, "subject")
    body = _text(form, "body")
    if not subject:
        errors["subject"] = "Subject is required."
    elif len(subject) > 150:
        errors["subject"] = "Subject must be 150 characters or fewer."
    if not body:
        errors["body"] = "Message is required."
    elif len(body) > 2000:
        errors["body"] = "Message must be 2,000 characters or fewer."
    return errors


def validate_vendor_form(form):
    errors = {}
    if not _text(form, "name"):
        errors["name"] = "Company name is required."
    if not _text(form, "contact_name"):
        errors["contact_name"] = "Primary contact name is required."
    if _text(form, "category") not in {"Dairy", "Beverages", "Dry Goods", "Cleaning", "Frozen"}:
        errors["category"] = "Choose a valid category."
    return errors


def validate_shipment_form(form, code_exists=None, excluding_id=None, inventory_exists=None, vendor_exists=None):
    errors = {}
    if not _text(form, "code"):
        errors["code"] = "Shipment code is required."
    elif code_exists and code_exists(_text(form, "code"), excluding_id):
        errors["code"] = "A shipment with this code already exists."
    if not _text(form, "company"):
        errors["company"] = "Company is required."
    _, error = _whole_number(form, "item_count", "Item count", 1)
    if error:
        errors["item_count"] = error
    expected_at = _text(form, "expected_at")
    try:
        datetime.strptime(expected_at, "%Y-%m-%dT%H:%M")
    except ValueError:
        errors["expected_at"] = "Enter a valid expected date and time."
    if _text(form, "direction") not in {"inbound", "outbound"}:
        errors["direction"] = "Choose a valid shipment direction."
    if _text(form, "status") not in {"expected", "active", "delayed", "history"}:
        errors["status"] = "Choose a valid shipment status."
    inventory_id = _text(form, "inventory_id")
    if inventory_id:
        try:
            parsed_inventory_id = int(inventory_id)
            if parsed_inventory_id < 1 or (inventory_exists and not inventory_exists(parsed_inventory_id)):
                raise ValueError
        except ValueError:
            errors["inventory_id"] = "Choose a valid product."
        _, quantity_error = _whole_number(form, "quantity", "Product quantity", 1)
        if quantity_error:
            errors["quantity"] = quantity_error
    vendor_id = _text(form, "vendor_id")
    if vendor_id:
        try:
            if vendor_exists and not vendor_exists(int(vendor_id)):
                raise ValueError
        except ValueError:
            errors["vendor_id"] = "Choose a valid vendor."
    return errors


def shipment_values(form):
    inventory_id = _text(form, "inventory_id")
    vendor_id = _text(form, "vendor_id")
    return {
        "code": _text(form, "code"),
        "company": _text(form, "company"),
        "item_count": int(_text(form, "item_count")),
        "expected_at": _text(form, "expected_at").replace("T", " "),
        "direction": _text(form, "direction"),
        "status": _text(form, "status"),
        "vendor_id": int(vendor_id) if vendor_id else None,
        "inventory_id": int(inventory_id) if inventory_id else None,
        "quantity": int(_text(form, "quantity")) if inventory_id else None,
    }


def vendor_values(form):
    return {
        "name": _text(form, "name"),
        "contact_name": _text(form, "contact_name"),
        "phone": _text(form, "phone"),
        "email": _text(form, "email"),
        "notes": _text(form, "notes"),
        "category": _text(form, "category"),
    }
