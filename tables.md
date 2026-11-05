# Database Tables and Attributes

The application uses SQLite. The tables below are defined in `reset_db()` in `app.py`.

## `users`

- `id` — INTEGER, primary key
- `email` — TEXT, unique, required
- `password_hash` — TEXT, required

## `vendors`

- `id` — INTEGER, primary key
- `name` — TEXT, required
- `contact_name` — TEXT
- `phone` — TEXT
- `email` — TEXT
- `notes` — TEXT
- `category` — TEXT

## `inventory`

- `id` — INTEGER, primary key
- `sku` — TEXT, required
- `name` — TEXT, required
- `vendor_id` — INTEGER, foreign key to `vendors.id`
- `department` — TEXT
- `date_received` — TEXT
- `quantity` — INTEGER, required
- `reorder_threshold` — INTEGER, required
- `max_threshold` — INTEGER, required
- `on_clearance` — INTEGER, default `0`
- `perishable` — INTEGER, default `0`
- `overstock_action` — TEXT
- `unit_cost` — REAL, default `0`

## `vendor_messages`

- `id` — INTEGER, primary key
- `vendor_id` — INTEGER, required, foreign key to `vendors.id`
- `subject` — TEXT, required
- `body` — TEXT, required
- `sent_at` — TEXT, required
- `inventory_id` — INTEGER, foreign key to `inventory.id`

## `shipments`

- `id` — INTEGER, primary key
- `code` — TEXT, required
- `company` — TEXT, required
- `item_count` — INTEGER, required
- `expected_at` — TEXT, required
- `direction` — TEXT, default `inbound`
- `status` — TEXT, default `expected`
- `vendor_id` — INTEGER, foreign key to `vendors.id`

## `shipment_items`

- `id` — INTEGER, primary key
- `shipment_id` — INTEGER, foreign key to `shipments.id`
- `inventory_id` — INTEGER, foreign key to `inventory.id`
- `quantity` — INTEGER, required

## `purchase_orders`

- `id` — INTEGER, primary key
- `code` — TEXT, required
- `inventory_id` — INTEGER, foreign key to `inventory.id`
- `vendor_id` — INTEGER, foreign key to `vendors.id`
- `quantity` — INTEGER, required
- `status` — TEXT, required
- `created_at` — TEXT, required
- `note` — TEXT
