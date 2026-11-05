# Spec: Bison Operations Inventory

Team members: [Name 1], [Name 2], [Name 3], [Name 4]

## Intent

Warehouse staff at a consumer-packaged-goods distribution center use this application to track what is on the shelves, what is arriving and leaving, and which items are running low. Supervisors can reorder low-stock items and message suppliers from the same place they see the problem. Managers and floor team members can check counts and shipment status without being able to change things that are not theirs to change. It is worth building because today these jobs are spread across separate lists, so low stock and delayed shipments are noticed late.

## Users and permissions

Every page except `/login` requires signing in. Each account has exactly one role. Permissions are checked on the server for every request. Hiding a button does not count as enforcing a permission. When a signed-in user requests something their role may not do, the application returns a 403 page reading "You do not have permission to do that." and changes nothing.

| User type | May | May not |
|---|---|---|
| Supervisor | View every page. Add, edit and delete inventory items, shipments and vendors. Reorder low-stock items (create purchase orders). Send messages to vendors. Mark purchase orders received. | Create, edit or delete user accounts or roles. |
| Manager | View the dashboard, inventory, shipments and vendor pages, including vendor message history and purchase orders. Add and edit inventory items. Add and edit shipments. Mark purchase orders received. | Delete any record. Reorder items or create purchase orders. Send vendor messages. Add, edit or delete vendors. |
| Team member (includes floor leads) | View the dashboard, search and filter `/inventory`, and view `/shipments`. | Add, edit or delete anything. Reorder. Open `/vendors` or any vendor page. Mark purchase orders received. |
| Vendor (no login) | Exist as a record on `/vendors`. Be the recipient of the purchase orders and restock messages a supervisor records in the app. Those messages are delivered outside the app by email or phone. | Sign in, or open any page of the application. |

## In scope

1. **Reorder from the dashboard** (`/`, then `/inventory/<id>/reorder`): the dashboard lists every low-stock item under "Needs Attention". A supervisor clicks Reorder and sees a review screen with an editable suggested quantity. Confirming creates a purchase order and records a message to the vendor. Both show on `/vendors/<id>`.
2. **Inventory search** (`/inventory`): search by SKU, name, vendor or department, and filter by All / In Stock / Low Stock / Overstock.
3. **Inbound and outbound shipments** (`/shipments`): a toggle switches between shipments coming in and shipments going out. Each row shows the products it carries.
4. **Shipment status tabs** (`/shipments`): tabs for Expected, Active, Delayed and History, with History showing completed shipments.
5. **Manage records** (`/inventory`, `/shipments`, `/vendors`, `/vendors/<id>`): view, add, edit and delete inventory items, shipments and vendors, and send a message to a vendor from its page. Each action is limited to the roles above.

## Out of scope

- Sign-up, password reset, or any page that creates, edits or deletes user accounts or changes roles. Accounts are created by the seed step only.
- A vendor login or any vendor-facing page.
- Actually sending email or SMS. Vendor messages are stored and displayed in the app only.
- More than one warehouse or facility, including transfers between locations.
- Prices, unit costs, invoices, payments or demand forecasting.
- Overstock actions (clearance, transfer, promotion), perishable flags, and the notifications bell.
- A welcome screen that asks users what they want to do. Signing in goes straight to the dashboard.
- Calls to any AI service or outside API, including screening message content.
- Barcode scanning and CSV import or export.

## Data

SQLite. Required means NOT NULL. The schema is created and seeded only when the database file does not already exist.

**users**
- `id` INTEGER, primary key
- `email` TEXT, required, unique
- `password_hash` TEXT, required
- `role` TEXT, required: one of `supervisor`, `manager`, `team_member`

**vendors**
- `id` INTEGER, primary key
- `name` TEXT, required
- `contact_name` TEXT
- `phone` TEXT
- `email` TEXT
- `notes` TEXT
- `category` TEXT: one of Dairy, Beverages, Dry Goods, Cleaning, Frozen

**inventory**
- `id` INTEGER, primary key
- `sku` TEXT, required, unique
- `name` TEXT, required, unique
- `vendor_id` INTEGER, required, foreign key → `vendors.id`
- `department` TEXT
- `date_received` TEXT (YYYY-MM-DD)
- `quantity` INTEGER, required, 0 or more
- `reorder_threshold` INTEGER, required, 0 or more
- `max_threshold` INTEGER, required, greater than `reorder_threshold`

**vendor_messages**
- `id` INTEGER, primary key
- `vendor_id` INTEGER, required, foreign key → `vendors.id`
- `subject` TEXT, required, 1–150 characters
- `body` TEXT, required, 1–2,000 characters
- `sent_at` TEXT, required
- `inventory_id` INTEGER, foreign key → `inventory.id` (set when the message is about one item)

**shipments**
- `id` INTEGER, primary key
- `code` TEXT, required, unique
- `company` TEXT, required
- `item_count` INTEGER, required, 1 or more
- `expected_at` TEXT, required (YYYY-MM-DD HH:MM)
- `direction` TEXT, required, default `inbound`: one of `inbound`, `outbound`
- `status` TEXT, required, default `expected`: one of `expected`, `active`, `delayed`, `history`
- `vendor_id` INTEGER, foreign key → `vendors.id` (empty for outbound shipments to carriers)

**shipment_items**
- `id` INTEGER, primary key
- `shipment_id` INTEGER, required, foreign key → `shipments.id`
- `inventory_id` INTEGER, required, foreign key → `inventory.id`
- `quantity` INTEGER, required, 1 or more

**purchase_orders**
- `id` INTEGER, primary key
- `code` TEXT, required, unique (PO-1001, PO-1002, …)
- `inventory_id` INTEGER, required, foreign key → `inventory.id`
- `vendor_id` INTEGER, required, foreign key → `vendors.id`
- `quantity` INTEGER, required, 1–10,000
- `status` TEXT, required: one of `pending`, `received`
- `created_at` TEXT, required
- `note` TEXT

**How the tables connect**
- `vendors` is the central table. One vendor has many inventory items, messages, shipments and purchase orders.
- `inventory.vendor_id` → `vendors.id`: each item comes from exactly one vendor.
- `vendor_messages.vendor_id` → `vendors.id`: every message belongs to one vendor. `vendor_messages.inventory_id` → `inventory.id` optionally ties it to one item.
- `shipments.vendor_id` → `vendors.id`: an inbound shipment can be linked to one vendor.
- `shipment_items` links `shipments` and `inventory` (many-to-many): which items, and how many of each, are in a shipment.
- `purchase_orders` → `inventory` and `vendors`: each order is for one item from one vendor.
- `users` stands alone, with no foreign keys.

**Seed data** (the acceptance criteria below depend on it): the five vendors, ten inventory items and seven shipments currently in the prototype, plus one shipment item (SHP-10492 carries 200 Sparkling Water 24-pack), plus three accounts: `supervisor@bisonoperations.com`, `manager@bisonoperations.com`, `team@bisonoperations.com`.

## Acceptance criteria

All criteria assume a freshly seeded database. "Bad input" and "Permission" mark the criteria in those categories.

**Signing in and permissions**

1. Signing in at `/login` as `supervisor@bisonoperations.com` with the correct password opens `/`, and the nav bar shows "supervisor@bisonoperations.com (Supervisor)". Signing in as the manager and team accounts shows "(Manager)" and "(Team Member)".
2. *Bad input.* Signing in with a correct email and a wrong password, or with an email that has no account, keeps the user on `/login` with the message "Invalid email or password." The message is identical in both cases, and no page other than `/login` can be opened afterward.
3. *Permission.* With no one signed in, requesting `/inventory`, `/shipments` or `/vendors` redirects to `/login`.
4. *Permission.* Signed in as the team member, `/inventory` shows no Add, Edit, Delete or Reorder buttons. Sending a POST to `/inventory/1/delete` returns the 403 page, and Organic Rolled Oats 25lb is still listed on `/inventory`.
5. *Permission.* Signed in as the team member, requesting `/vendors` or `/vendors/1` returns the 403 page.
6. *Permission.* Signed in as the manager, requesting `/inventory/2/reorder` (GET or POST) returns the 403 page, and no purchase order appears on `/vendors/2`. A POST to `/shipments/1/delete` also returns the 403 page, and SHP-10492 is still listed.

**Feature 1: Reorder from the dashboard**

7. Signed in as the supervisor, the "Needs Attention" section on `/` lists exactly four low-stock items, each with its quantity and reorder threshold and a Reorder button: Sparkling Water 24-pack (42 / 100), Cheddar Cheese Block 5lb (38 / 150), Instant Coffee 12oz (56 / 100), Hand Sanitizer 8oz (61 / 125).
8. Clicking Reorder on Sparkling Water 24-pack opens `/inventory/2/reorder`, which shows Pacific Beverage Co., the contact Jordan Lee, and an editable quantity field filled with 858 (max 900 − quantity 42). Clicking Cancel returns to `/` and creates no purchase order.
9. Clicking Confirm with 858 shows "PO-1001 sent to Pacific Beverage Co.". `/vendors/2` then lists PO-1001, 858, Pending, and its Conversation History shows a message titled "Purchase order PO-1001: Sparkling Water 24-pack (SKU-10567)". Sparkling Water's quantity on `/inventory` is still 42.
10. Clicking Mark Received on PO-1001 changes its status to Received and Sparkling Water's quantity to 900. Sparkling Water no longer appears under Needs Attention on `/`.
11. *Bad input.* Submitting the reorder form with a quantity of 0, -10, 10001 or "lots" creates no purchase order and shows "Order quantity must be a whole number from 1 to 10,000."

**Feature 2: Inventory search**

12. Searching "CleanPro" on `/inventory` shows exactly two rows: Multi-Surface Cleaner 32oz and Hand Sanitizer 8oz.
13. Searching "SKU-10567" shows only Sparkling Water 24-pack. Searching "Dairy" shows only Cheddar Cheese Block 5lb. Choosing the Low Stock filter with an empty search shows the same four items as criterion 7.
14. *Bad input.* Searching "zzz" or `' OR '1'='1` shows no rows and the message "No items match your search." No error page appears.

**Feature 3: Inbound and outbound shipments**

15. `/shipments` opens on Inbound / Expected and lists SHP-10492, SHP-10483 and SHP-10471, but not SHP-20011. Switching to Outbound lists SHP-20011 and none of the SHP-104xx codes.
16. The SHP-10492 row shows "Sparkling Water 24-pack (200)" in its Products column.

**Feature 4: Shipment status tabs**

17. On Inbound, the Active tab lists only SHP-10410, the Delayed tab lists only SHP-10351, and the History tab lists only SHP-10403.
18. Signed in as the manager, editing SHP-10492 to the status Delayed and saving moves it from the Expected tab to the Delayed tab. SHP-10492 also appears in red, with Sparkling Water 24-pack, under Needs Attention on `/`.

**Feature 5: Manage records**

19. *Bad input.* On the Add Item form, entering "ten" for quantity and -5 for reorder threshold and submitting saves nothing. The form shows "Quantity must be a whole number of 0 or more." under the quantity field and "Reorder threshold must be a whole number of 0 or more." under the reorder threshold field, both fields have a red outline, and the other values typed in are still filled in. The same messages appear when the request is sent directly with the browser's checks bypassed.
20. *Bad input.* Adding an item named "Sparkling Water 24-pack" (which already exists) saves nothing and shows "An item named Sparkling Water 24-pack already exists."
21. *Bad input.* Requesting `/inventory/999/edit`, `/shipments/999/edit` or `/vendors/999` shows a 404 page reading "Record not found." and creates no record.
22. Signed in as the supervisor, clicking Delete on Bottled Spring Water 16oz (case) shows the dialog "Are you sure you want to delete Bottled Spring Water 16oz (case)? This cannot be undone." Clicking Cancel leaves it listed. Clicking OK removes it from `/inventory`. Shipments and vendors behave the same way.
23. *Bad input.* Deleting Pacific Beverage Co., which still supplies three items, is refused with "Pacific Beverage Co. still supplies 3 inventory items. Reassign or delete them first.", and the vendor stays on `/vendors`.
24. *Bad input.* On `/vendors/4`, sending a message with an empty subject, or with a body over 2,000 characters, saves nothing and shows "Subject is required." or "Message must be 2,000 characters or fewer.". A valid message appears at the top of Conversation History with today's date.
25. Signed in as the supervisor, adding an item "Test Item" with SKU-99999, signing out, stopping and restarting the application, and signing back in still shows Test Item on `/inventory`.

**Defenses (see Risks)**

26. Searching every project file for `dev-secret-key`, `password123` and `secret_key = "` returns no matches. Starting the application without `SECRET_KEY` set in `.env` stops it with the message "SECRET_KEY is not set."
27. Sign Out is a button that sends a POST to `/logout`. Typing `/logout` into the address bar (a GET request) returns 405 Method Not Allowed. After creating PO-1001 (criterion 9), visiting `/logout` by GET, then signing out with the button and signing back in, PO-1001 is still listed on `/vendors/2`.

## Constraints

- Python 3 with Flask. Pages are Jinja templates in `templates/` and styles are in `static/`. The only packages that may be installed are Flask and python-dotenv. No ORM such as SQLAlchemy, no JavaScript framework, and no CDN links.
- Database: one SQLite file. The schema and seed data live in `database.py`. Seeding runs only when the file does not exist, never on sign-out or on every launch. To reset the demo, delete the file.
- SQL lives only in `database.py` (schema and seed) and `data_access.py` (one function per read, create, update or delete). `app.py` contains routes only, has no SQL, and calls `data_access.py`. Every query uses `?` placeholders. Values for column names in ORDER BY come only from a fixed list.
- Server-side validation lives in `validations.py`, with one function per form that returns a dictionary of field → error message. A route saves only when that dictionary is empty. Client-side checks (`required`, `type="number"`, `min`) live in the templates but are never the only check.
- Roles are checked on the server by one decorator (for example `@role_required("supervisor")`) on every route that changes data or opens `/vendors`.
- Any route that creates, changes or deletes data accepts POST only. Deletes and sign-out are buttons inside forms, never links.
- Secrets: `SECRET_KEY` and the three seed account passwords are read from a `.env` file. `.env` is not committed or included in the submitted zip. A `.env.example` lists the variable names with no values. Passwords are stored only as Werkzeug password hashes.

## Risks

1. **A secret in the code.** In the current prototype the Flask secret key is typed into `app.py` (`app.secret_key = "dev-secret-key-change-me"`), and so is the demo password `password123` in the seed step. Anyone with a copy of the zip or repository could sign session cookies and act as any user, which also defeats every role check. The defect would reappear in `app.py` or `database.py` if an agent "simplifies" setup. **Criterion 26** catches it.
2. **A data change that runs on GET.** In the current prototype Sign Out is a plain link to `/logout`, and that route calls `reset_db()`, which drops and reseeds every table. Opening `/logout` from a bookmark, the browser history or a pasted link erases every edit, purchase order and message with no confirmation. The same defect would appear on any delete or reorder route built as a link. **Criteria 27 and 25** catch it (27 for the GET route itself, 25 for data surviving a sign-out and restart). Criteria 4 and 22 check that deletes require a POST button.

---

## AI Use Note

**Tools and sections.** The team used Claude (with our lecture PDFs and slide decks uploaded as context) to turn our working requirements document into this template's format. It helped draft the Data section from our existing schema, consolidate the Users and Permissions table, write the Risks from the Session 18 defects found in our prototype code, and rewrite our acceptance criteria so that each one names an input and a visible result using our seed data. The team wrote the Intent, In Scope and Out of Scope content and chose the roles. We reviewed every section against our running prototype.

**A criterion the team changed.** [TEAM: replace this with a real example. Name one criterion the AI drafted, what you changed, and why. For example: "The AI drafted criterion __ as '…'. We changed it to '…' because …"]
