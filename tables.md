# CP2 Database Tables

This file documents the SQLite schema initialized by `database.py`. SQL
definitions and seed data belong there; request-level SQL operations belong in
`data_access.py`.

| Table | Responsibility |
|---|---|
| `users` | Synthetic demo accounts and one of the `supervisor`, `manager`, or `team_member` roles. |
| `vendors` | Vendor contact details and category. |
| `inventory` | SKU, item name, vendor, department, received date, quantity, reorder threshold, and maximum threshold. |
| `shipments` | Inbound and outbound shipment records, status, carrier, expected arrival, and associated vendor where applicable. |
| `shipment_items` | Inventory items and quantities associated with shipments. |
| `purchase_orders` | Reorder requests and their status. |
| `vendor_messages` | Vendor messages and optional related inventory item. |

The demo initializes the schema and sample data only when the configured
database file does not exist. It does not reset or overwrite an existing
database at startup or logout. Existing databases with an incompatible schema
are rejected with an actionable error rather than migrated or erased. Back up
existing data before changing database files.

The schema intentionally excludes features marked out of scope by CP2,
including employee schedules, overstock-management actions, price/cost fields,
and an alert counter.
