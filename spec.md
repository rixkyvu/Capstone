# Bison Operations Prototype – Iteration 2 Spec

## Context
- Stack: Flask + SQLite (`bison.db`), Jinja templates, single file `app.py`.
- `reset_db()` drops and reseeds all tables on launch/logout. Any new table or column MUST be added to `reset_db()` with seed data.
- Users: production managers (persona "Jonah Peck"). Main jobs: track inventory, act on low stock and overstock, coordinate with vendors.
- Core theme from usability testing: pages feel disconnected and the dashboard is passive. Goal: **connect inventory ↔ vendors ↔ shipments, and surface problems proactively.**
- Keep existing functionality working. Don't remove any routes.

---

## P0 – Must Have

### 1. Action-Oriented Dashboard (`/`, dashboard.html)
- Replace count-only cards with an "Needs Attention" section at the top listing:
  - Each low-stock item (name, qty vs. reorder threshold, vendor) with buttons: **Reorder**, **Contact Vendor**.
  - Each delayed shipment (code, company, products, new ETA), visually prominent (red/amber).
  - Each overstocked item (name, qty vs. max).
- Show linked alerts when a low-stock item has an inbound shipment from the same vendor, e.g. "Sparkling Water is below threshold. Pacific Beverage shipment SHP-xxxx arrives Sep 19."
- KPI cards stay, but each is clickable and links to the filtered view (e.g. "4 Low Stock" → `/inventory?status=low`).
- Remove or de-emphasize the Vendor Contacts card (testers called it redundant).
- Add a one-line company description/subtitle under the header.
- Use larger cards and fill the empty white space at the bottom.

### 2. Cross-Linking Inventory → Vendors
- On inventory, low-stock and overstock tables, make the vendor name a link to `/vendors/<id>`.
- Add a **Contact Vendor** action per row that opens the vendor message form **pre-filled**:
  - Subject: `Restock request: <item name> (<SKU>)`
  - Body: item, current qty, reorder threshold, suggested order qty.
- Store `inventory_id` (nullable) on `vendor_messages` so messages link to an item.

### 3. Reorder Flow (replace instant reorder)
- Currently `POST /inventory/<id>/reorder` silently sets qty = threshold × 2. Change to:
  - `GET /inventory/<id>/reorder` → review screen showing item, vendor and contact, suggested qty (default `max_threshold - quantity`, editable), and an optional note.
  - `POST` → create a `purchase_orders` record (status `pending`), log a vendor message automatically, then redirect to a confirmation page or show a flash message ("PO-#### sent to Pacific Beverage Co.").
  - Don't change inventory quantity until the PO is received (can be simulated with a "Mark Received" button).

### 4. Shipment Contents + Linkage
- New table `shipment_items (id, shipment_id, inventory_id, quantity)`.
- Add `vendor_id` (nullable) to `shipments`.
- Shipments table: show a products column (or expandable row) listing the items in each shipment.
- Inventory and low-stock pages: if an item has an inbound expected/active shipment, show "Incoming: 200 units on Sep 19" (in red if the shipment is delayed).
- Add `delayed` to the shipment status options, with its own color. Editing a shipment to `delayed` must immediately show on the dashboard.
- Fix the dashboard "delayed" count to use `status = 'delayed'` (currently it counts `history`).

### 5. Filter Visibility & Sorting (inventory.html)
- Move the "Low Stock / Overstock" filters to a segmented control or tabs **next to the search bar**: `All | In Stock | Low Stock | Overstock`. Support `?status=` on `/inventory`. Keep the old routes working.
- Clickable column headers to sort by SKU, name, vendor, department, date received, quantity and status (asc/desc via `?sort=&dir=`).
- Make pagination obvious ("Page 1 of 2", larger controls) or raise PAGE_SIZE.
- Search matches all columns (SKU, name, vendor, department).

### 6. Delete Confirmation
- Every delete action (inventory, shipments, vendors) requires a confirmation (modal or `confirm()` dialog): "Are you sure you want to delete <name>? This cannot be undone."

---

## P1 – Should Have

### 7. Overstock Actions (inventory_over.html)
- Replace the single "Mark for Clearance" button with an action menu: **Mark for Clearance**, **Transfer**, **Reduce Next Order**, **Flag for Review**, **Promotion**.
- Store the chosen action in a new column `overstock_action TEXT` (replaces or extends `on_clearance`) and show it as a badge.
- The banner text must match the available actions.
- Add an optional `perishable` boolean on inventory, and show a hint ("Perishable: clearance recommended" vs. "Non-perishable: consider reducing next order").

### 8. Vendor Detail Enhancements (vendor_detail.html)
- "Products from this vendor" table: items supplied, current qty and status (with low-stock badges), plus a Reorder button.
- "Open orders / upcoming shipments" from this vendor.
- Simple performance stats: number of shipments, number delayed, last message date.
- Message history: move it near the top, label it clearly as "Conversation History", and show the linked item if there is one.
- Add a `category` field to vendors (Dairy, Beverages, Dry Goods, Cleaning, Frozen) and a category filter on `/vendors`.
- Add an **Edit Vendor** route/form.
- Make phone and email clickable (`tel:` / `mailto:`).
- On the Add Vendor form, relabel the fields "Company Name" and "Primary Contact Name" to avoid confusion.

### 9. Navigation & Page Identity
- Every page gets a clear H1 title (Inventory, Shipments, Vendors) and the active nav item is highlighted.
- Add a "← Back to Inventory" link on the low-stock and overstock pages.
- Shipment form: use `<input type="datetime-local">` (date picker) for the expected date.

---

## P2 – Nice to Have / Visual Polish
- Increase base font size (≥ 16px), nav link size and table text, for accessibility.
- Reduce empty white space, use a bit more color, and keep a consistent status color system:
  - Low Stock / Delayed = red, In Stock / Delivered = green, Overstock = amber, Active = blue, Expected = gray, History = neutral/slate. **Active and History must not share a color.**
- Login page: show the Bison Operations name/logo and a one-line tagline, fix misaligned graphics, add a non-functional "Request access / Sign up" link.
- Item detail view (`/inventory/<id>`): all fields plus unit cost, linked shipments and message history.
- Simulated notifications bell in the nav showing the count of active alerts (low stock and delayed shipments).

---

## Data Model Changes (all in `reset_db()`, with seed data)
- `vendors`: + `category TEXT`
- `inventory`: + `perishable INTEGER DEFAULT 0`, + `overstock_action TEXT`, + `unit_cost REAL` (optional)
- `vendor_messages`: + `inventory_id INTEGER NULL`
- `shipments`: + `vendor_id INTEGER NULL`; status values: `expected | active | delayed | history`
- NEW `shipment_items (id, shipment_id, inventory_id, quantity)`
- NEW `purchase_orders (id, code, inventory_id, vendor_id, quantity, status, created_at, note)`
- Seed at least one inbound shipment from Pacific Beverage containing Sparkling Water and one delayed shipment, so the linked-alert demo works.

---

## Acceptance Criteria (Test Scenarios)
1. Log in → the dashboard lists Sparkling Water, Cheddar, Instant Coffee and Hand Sanitizer as low stock, each with Reorder and Contact Vendor buttons.
2. Click Contact Vendor on Hand Sanitizer → land on CleanPro Supply's page with the message pre-filled → send → it appears in Conversation History, tagged with the item.
3. Click Reorder → a review screen shows vendor, suggested qty and contact → confirm → a confirmation with a PO number appears, and the PO shows on the vendor page.
4. Edit SHP-10492 to status `delayed` → the dashboard shows it in red under Needs Attention, along with its products.
5. On the inventory page, the status filter is beside search, and sorting by Date Received works.
6. Overstock page: Bottled Water offers Transfer / Reduce Next Order, not only Clearance.
7. Deleting any record prompts a confirmation first.
8. Every page has a visible title, and the active nav tab is highlighted.

## Out of Scope (this iteration)
- Real email sending, real authentication or sign-up, importing from external systems, multi-location inventory data (Transfer can be a status label only).