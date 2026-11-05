# Spec: Bison Operations Inventory

**Team members:** Michael Hartnett, Diya Kumar, Ricky Vu, Hillary Haine

## Changes since CP1

- **Team Members:** Added actual student names (Michael Hartnett, Diya Kumar, Ricky Vu, Hillary Haine).
- **Vendor Permissions:** Removed Vendor from the permissions table and added a "Vendor access" clarifying note specifying vendors are records in data.
- **Manage Records Feature Split:** Split Feature 5 into three narrower features: Feature 5 (Inventory maintenance), Feature 6 (Shipment maintenance), and Feature 7 (Vendor maintenance & messaging).
- **Criterion 26 (Defense):** Removed reliance on fixed string searches for secrets; updated criterion to check that the app refuses to start without `SECRET_KEY`.
- **Criterion 22 (Manual Check):** Tagged explicitly as a manual browser check for confirmation dialog interaction.
- **AI Use Note:** Updated to state which acceptance criteria were changed (26 and 22) and why.
## Intent

Warehouse staff at a consumer-packaged-goods distribution center use this application to track inventory, incoming and outgoing shipments, and low-stock items. Supervisors can reorder products and record vendor communications, while managers and floor team members can view operational information within their assigned permissions. The application brings inventory and shipment information together so staff can identify low stock and delayed shipments more reliably.

## Users and permissions

Every page except `/login` requires signing in. Each account has exactly one role. Permissions are checked on the server for every request; hiding a button does not enforce a permission. When a signed-in user requests an action or page their role may not access, the application returns a 403 page reading **"You do not have permission to do that."** and makes no changes.

| User type | May | May not |
|---|---|---|
| Supervisor | View all operational pages; add, edit, and delete inventory items and shipment records; reorder low-stock items by creating purchase orders; send vendor messages; mark purchase orders received; add, edit, and delete vendor records. | Create, edit, or delete user accounts or roles. |
| Manager | View the dashboard, inventory, shipments, vendors, vendor message history, and purchase orders; add and edit inventory items; add and edit shipment records; mark purchase orders received. | Delete records; reorder items or create purchase orders; send vendor messages; add, edit, or delete vendor records; create or change user accounts or roles. |
| Team member (including floor leads) | View the dashboard; search and filter inventory; view shipment records and statuses. | Add, edit, or delete records; reorder items; open `/vendors` or vendor detail pages; mark purchase orders received; send vendor messages; create or change user accounts or roles. |

**Vendor access:** Vendors are records in the application, not application users. They cannot sign in or open any page. Supervisors record vendor messages and purchase orders in the application; communication with vendors happens outside the application.

## In scope

1. **Reorder from dashboard** (`/`, `/inventory/<id>/reorder`): the dashboard lists low-stock inventory. A supervisor reviews and edits a suggested order quantity, then confirms to create a purchase order and a vendor message record.
2. **Inventory search and filters** (`/inventory`): search by SKU, name, vendor, or department and filter by All, In Stock, Low Stock, or Overstock.
3. **Inbound and outbound shipments** (`/shipments`): switch between inbound and outbound shipment lists; each shipment shows the products it carries.
4. **Shipment status tabs** (`/shipments`): view Expected, Active, Delayed, and History shipments; History contains completed shipments.
5. **Inventory record maintenance** (`/inventory`): supervisors add, edit, and delete inventory items; managers can add and edit but cannot delete; team members are read-only.
6. **Shipment record maintenance** (`/shipments`): supervisors add, edit, and delete shipment records; managers can add and edit but cannot delete; team members are read-only.
7. **Vendor records and purchase order/message history** (`/vendors`, `/vendors/<id>`): supervisors maintain vendor records and send/record messages; managers can view vendor records and message history but cannot modify vendor records or send messages. Purchase orders and messages are displayed on the related vendor page.

## Out of scope

- Sign-up, password reset, or any page that creates, edits, or deletes user accounts or changes roles; accounts are created by the seed step only.
- Vendor login or any vendor-facing page.
- Actually sending email or SMS; vendor messages are stored and displayed in the app only.
- More than one warehouse or facility, including transfers between locations.
- Prices, unit costs, invoices, payments, or demand forecasting.
- Overstock actions (clearance, transfer, promotion), perishable flags, and the notifications bell.
- A welcome screen that asks users what they want to do; signing in goes straight to the dashboard.
- Calls to any AI service or outside API, including screening message content.
- Barcode scanning and CSV import or export.

## Data

SQLite. Required means `NOT NULL`. The schema is created and seeded only when the database file does not already exist.

### `users`
- `id` INTEGER, primary key
- `email` TEXT, required, unique
- `password_hash` TEXT, required
- `role` TEXT, required: one of `supervisor`, `manager`, `team_member`

### `vendors`
- `id` INTEGER, primary key
- `name` TEXT, required
- `contact_name` TEXT
- `phone` TEXT
- `email` TEXT
- `notes` TEXT
- `category` TEXT: one of Dairy, Beverages, Dry Goods, Cleaning, Frozen

### `inventory`
- `id` INTEGER, primary key
- `sku` TEXT, required, unique
- `name` TEXT, required, unique
- `vendor_id` INTEGER, required, foreign key → `vendors.id`
- `department` TEXT
- `date_received` TEXT (YYYY-MM-DD)
- `quantity` INTEGER, required, 0 or more
- `reorder_threshold` INTEGER, required, 0 or more
- `max_threshold` INTEGER, required, greater than `reorder_threshold`

### `vendor_messages`
- `id` INTEGER, primary key
- `vendor_id` INTEGER, required, foreign key → `vendors.id`
- `subject` TEXT, required, 1–150 characters
- `body` TEXT, required, 1–2,000 characters
- `sent_at` TEXT, required
- `inventory_id` INTEGER, foreign key → `inventory.id` (optional link to an item)

### `shipments`
- `id` INTEGER, primary key
- `code` TEXT, required, unique
- `company` TEXT, required
- `item_count` INTEGER, required, 1 or more
- `expected_at` TEXT, required (YYYY-MM-DD HH:MM)
- `direction` TEXT, required, default `inbound`: one of `inbound`, `outbound`
- `status` TEXT, required, default `expected`: one of `expected`, `active`, `delayed`, `history`
- `vendor_id` INTEGER, foreign key → `vendors.id` (empty for outbound shipments to carriers)

### `shipment_items`
- `id` INTEGER, primary key
- `shipment_id` INTEGER, required, foreign key → `shipments.id`
- `inventory_id` INTEGER, required, foreign key → `inventory.id`
- `quantity` INTEGER, required, 1 or more

### `purchase_orders`
- `id` INTEGER, primary key
- `code` TEXT, required, unique (PO-1001, PO-1002, …)
- `inventory_id` INTEGER, required, foreign key → `inventory.id`
- `vendor_id` INTEGER, required, foreign key → `vendors.id`
- `quantity` INTEGER, required, 1–10,000
- `status` TEXT, required: one of `pending`, `received`
- `created_at` TEXT, required
- `note` TEXT

### How the tables connect
- `vendors` is the central table. One vendor can have many inventory items, messages, shipments, and purchase orders.
- `inventory.vendor_id` → `vendors.id`: each item belongs to one vendor.
- `vendor_messages.vendor_id` → `vendors.id`: each message belongs to one vendor. `vendor_messages.inventory_id` optionally links it to an inventory item.
- `shipments.vendor_id` → `vendors.id`: a shipment can be linked to a vendor.
- `shipment_items` links shipments and inventory (many-to-many), recording which items and quantities are in each shipment.
- `purchase_orders` → `inventory` and `vendors`: each order is for one item from one vendor.
- `users` stands alone, with no foreign keys to other tables.

**Seed data:** The five vendors, ten inventory items, and seven shipments currently in the prototype; one shipment item (SHP-10492 carries 200 Sparkling Water 24-pack); and three accounts: `supervisor@bisonoperations.com`, `manager@bisonoperations.com`, and `team@bisonoperations.com`.

## Acceptance criteria

All criteria assume a freshly seeded database unless stated otherwise. **Bad input** and **Permission** identify criteria in those categories. Criteria are numbered 1–27.

### Sign-in and permissions

1. Signing in at `/login` as `supervisor@bisonoperations.com` with the correct password opens `/`, and the navigation bar shows `supervisor@bisonoperations.com (Supervisor)`. Signing in as the manager and team accounts shows `(Manager)` and `(Team Member)` respectively.

2. **Bad input.** Signing in with a correct email and wrong password, or with an email that has no account, keeps the user on `/login` and displays **"Invalid email or password."** The message is identical in both cases, and no protected page can be opened afterward.

3. **Permission.** With no user signed in, requesting `/inventory`, `/shipments`, or `/vendors` redirects to `/login`.

4. **Permission.** Signed in as the team member, `/inventory` shows no Add, Edit, Delete, or Reorder controls. A direct POST to `/inventory/1/delete` returns the 403 page, and Organic Rolled Oats 25lb remains listed on `/inventory`.

5. **Permission.** Signed in as the team member, requesting `/vendors` or `/vendors/1` returns the 403 page.

6. **Permission.** Signed in as the manager, requesting `/inventory/2/reorder` by GET or POST returns the 403 page and no purchase order appears on `/vendors/2`. A POST to `/shipments/1/delete` also returns the 403 page, and SHP-10492 remains listed.

### Feature 1: Reorder from the dashboard

7. Signed in as the supervisor, the **Needs Attention** section on `/` lists exactly four low-stock items, each with its quantity, reorder threshold, and Reorder button: Sparkling Water 24-pack (42 / 100), Cheddar Cheese Block 5lb (38 / 150), Instant Coffee 12oz (56 / 100), and Hand Sanitizer 8oz (61 / 125).

8. Clicking Reorder for Sparkling Water 24-pack opens `/inventory/2/reorder`, showing Pacific Beverage Co., contact Jordan Lee, and an editable quantity prefilled with **858** (900 maximum − 42 on hand). Clicking Cancel returns to `/` and creates no purchase order.

9. Clicking Confirm with quantity 858 displays **"PO-1001 sent to Pacific Beverage Co."** `/vendors/2` lists PO-1001, quantity 858, status Pending, and Conversation History contains a message titled **"Purchase order PO-1001: Sparkling Water 24-pack (SKU-10567)"**. Sparkling Water's inventory quantity remains 42 until the order is received.

10. Clicking Mark Received on PO-1001 changes its status to Received and Sparkling Water's quantity to 900. Sparkling Water no longer appears in Needs Attention on `/`.

11. **Bad input.** Submitting the reorder form with quantity `0`, `-10`, `10001`, or `lots` creates no purchase order and displays **"Order quantity must be a whole number from 1 to 10,000."**

### Feature 2: Inventory search and filters

12. Searching `CleanPro` on `/inventory` returns exactly two rows: Multi-Surface Cleaner 32oz and Hand Sanitizer 8oz.

13. Searching `SKU-10567` returns only Sparkling Water 24-pack. Searching `Dairy` returns only Cheddar Cheese Block 5lb. Selecting the Low Stock filter with an empty search returns the same four items as criterion 7.

14. **Bad input.** Searching `zzz` or `' OR '1'='1` returns no rows and displays **"No items match your search."** No error page appears.

### Feature 3: Inbound and outbound shipments

15. `/shipments` initially opens on Inbound / Expected and lists SHP-10492, SHP-10483, and SHP-10471, but not SHP-20011. Switching to Outbound lists SHP-20011 and none of the SHP-104xx codes.

16. The SHP-10492 row shows **"Sparkling Water 24-pack (200)"** in its Products column.

### Feature 4: Shipment status tabs

17. On Inbound, the Active tab lists only SHP-10410, the Delayed tab lists only SHP-10351, and the History tab lists only SHP-10403.

18. Signed in as the manager, editing SHP-10492 to status Delayed and saving moves it from Expected to Delayed. SHP-10492 also appears in red, with Sparkling Water 24-pack, under Needs Attention on `/`.

### Feature 5: Inventory record maintenance

19. **Bad input.** On the Add Item form, entering `ten` for quantity and `-5` for reorder threshold and submitting saves nothing. The form displays **"Quantity must be a whole number of 0 or more."** under quantity and **"Reorder threshold must be a whole number of 0 or more."** under reorder threshold. Both fields have red outlines, and all other entered values remain filled in. The same server-side messages appear when the request bypasses browser validation.

20. **Bad input.** Adding an item named `Sparkling Water 24-pack` (already present) saves nothing and displays **"An item named Sparkling Water 24-pack already exists."**

21. **Bad input.** Requesting `/inventory/999/edit`, `/shipments/999/edit`, or `/vendors/999` displays a 404 page reading **"Record not found."** and creates no record.

### Feature 6: Shipment record maintenance

22. **Manual browser check.** Signed in as the supervisor, clicking Delete on shipment SHP-10492 displays the browser confirmation dialog **"Are you sure you want to delete SHP-10492? This cannot be undone."** Clicking Cancel leaves SHP-10492 listed; clicking OK removes it from `/shipments`. This criterion must be verified manually because it depends on a browser confirmation dialog.

### Feature 7: Vendor records and vendor communication

23. **Bad input.** Deleting Pacific Beverage Co., which still supplies three inventory items, is refused with **"Pacific Beverage Co. still supplies 3 inventory items. Reassign or delete them first."** The vendor remains listed on `/vendors`.

24. **Bad input.** On `/vendors/4`, sending a message with an empty subject or a body over 2,000 characters saves nothing and displays **"Subject is required."** or **"Message must be 2,000 characters or fewer."** respectively. A valid message appears at the top of Conversation History with today's date.

### Persistence and security defenses

25. Signed in as the supervisor, add an item named `Test Item` with SKU `SKU-99999`, sign out, stop and restart the application, and sign back in. `Test Item` remains listed on `/inventory`.

26. The application refuses to start when `SECRET_KEY` is not set in the environment or `.env`, and prints **"SECRET_KEY is not set."** No Flask session secret is supplied as a hard-coded fallback. This verifies that startup requires an externally configured secret rather than relying on a specific string search.

27. Sign Out is a button in a form that sends POST to `/logout`. A GET request to `/logout` returns **405 Method Not Allowed** and does not reset or modify the database. After creating PO-1001 (criterion 9), visiting `/logout` by GET, then signing out with the button and signing back in, PO-1001 remains listed on `/vendors/2`.

## Constraints

- Python 3 with Flask. Pages are Jinja templates in `templates/`; styles are in `static/`. The only packages that may be installed are Flask and python-dotenv. No ORM such as SQLAlchemy, no JavaScript framework, and no CDN links.
- Database: one SQLite file. Schema and seed data live in `database.py`. Seeding runs only when the file does not exist, never on sign-out or every launch. To reset the demo, delete the database file.
- SQL lives only in `database.py` (schema and seed) and `data_access.py` (one function per read, create, update, or delete). `app.py` contains routes only, no SQL, and calls `data_access.py`. Every query uses `?` placeholders. Values for column names in `ORDER BY` come only from a fixed list.
- Server-side validation lives in `validations.py`, with one function per form returning a dictionary of field → error message. A route saves only when that dictionary is empty. Client-side checks (`required`, `type="number"`, `min`) live in templates but are never the only validation.
- Roles are checked on the server by one decorator (for example, `@role_required("supervisor")`) on every route that changes data or opens `/vendors`.
- Any route that creates, changes, or deletes data accepts POST only. Deletes and sign-out are buttons inside forms, never links.
- Secrets: `SECRET_KEY` and the three seed account passwords are read from `.env`. `.env` is not committed or included in the submitted zip. `.env.example` lists variable names without values. Passwords are stored only as Werkzeug password hashes.

## Risks

1. **Hard-coded secret or demo password.** The prototype has a Flask secret key hard-coded in `app.py` (`app.secret_key = "dev-secret-key-change-me"`) and a demo password (`password123`) in the seed step. Anyone with a copy of the project could potentially forge a session or use the demo credentials, undermining role checks. **Criterion 26** catches this by requiring the application to refuse startup when `SECRET_KEY` is missing, rather than relying on searching for particular strings.

2. **Data-changing action on GET.** In the prototype, Sign Out is a link to `/logout`, and the route calls `reset_db()`, dropping and reseeding tables. Visiting the URL from a bookmark, browser history, or pasted link can erase edits, orders, and messages. **Criterion 27** checks that GET `/logout` is rejected and sign-out uses POST; **criterion 25** checks that data persists through sign-out and restart. Criteria 4 and 22 also verify that restricted deletes are refused and that a delete requires an explicit confirmation interaction.

## AI Use Note

AI was used to reorganize and refine the specification against the assignment feedback, clarify role permissions, split the broad record-management feature into narrower features, and make acceptance criteria more specific and independently testable. **Acceptance criterion 26 was changed** from searching for a few known secret strings to checking that the application refuses to start without `SECRET_KEY`; this is stronger because a string search could miss a different hard-coded secret. **Criterion 22 was also made explicit as a manual browser check** because the acceptance test depends on a browser confirmation dialog. The team reviewed the resulting requirements and remains responsible for verifying them against the prototype and assignment.
