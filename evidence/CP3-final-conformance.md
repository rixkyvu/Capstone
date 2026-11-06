# CP3 Final CP2 Conformance Check

This table checks the application against all 27 criteria in `spec-CP2.md`.
The evidence is the final automated run recorded in
[`CP3-final-pytest-run.txt`](./CP3-final-pytest-run.txt), using isolated
temporary SQLite databases. "Met" means the listed HTTP-level regression test
passed. Criterion 22 was additionally checked in the integrated browser.

The application was also started with synthetic environment values and a
temporary database. A real HTTP request to `/login` returned 200, and an
anonymous request to `/inventory` returned 302 as required. The smoke-test
process was stopped afterward. For criterion 22, the browser displayed the
expected native confirmation dialog for Bottled Spring Water 16oz (case);
dismissing it left the item visible on `/inventory`.

| Criterion | Status | Test and evidence | Deviation |
|---|---|---|---|
| 1 | Met | `test_01_three_seeded_roles_can_sign_in` authenticates each role and checks the role label in navigation. | None. |
| 2 | Met | `test_02_invalid_login_shows_same_error_and_does_not_authenticate` checks both wrong-password and unknown-account cases and then verifies inventory remains protected. | None. |
| 3 | Met | `test_03_protected_pages_redirect_anonymous_users` checks anonymous requests to inventory, shipments, and vendors. | None. |
| 4 | Met | `test_04_team_member_cannot_mutate_inventory` checks read-only controls, item visibility, forbidden direct deletion, and unchanged inventory. | None. |
| 5 | Met | `test_05_team_member_cannot_open_vendors` checks vendor-list and detail requests return 403. | None. |
| 6 | Met | `test_06_manager_cannot_reorder_or_delete_shipments` checks denied reorder requests, unchanged purchase orders, denied deletion, and shipment visibility. | None. |
| 7 | Met | `test_07_dashboard_has_four_low_stock_items` checks the four exact low-stock rows, quantities, thresholds, and reorder links. | None. |
| 8 | Met | `test_08_reorder_cancel_returns_to_dashboard_without_creating_po` checks suggested quantity, contact, dashboard cancel link, and no new order. | None. |
| 9 | Met | `test_09_reorder_creates_pending_order_and_message` checks PO-1001, vendor history, message title, status, and unchanged inventory quantity. | None. |
| 10 | Met | `test_10_receiving_order_updates_quantity_once` checks quantity and status updates exactly once and removal from dashboard low stock. | None. |
| 11 | Met | `test_11_invalid_reorder_quantity_is_rejected` is parameterized for `0`, `-10`, `10001`, and `lots`; each case checks the required message and no created order. | None. |
| 12 | Met | `test_12_search_cleanpro_returns_two_items` checks both CleanPro items and excludes an unrelated item. | None. |
| 13 | Met | `test_13_inventory_search_and_low_stock_filter` checks SKU and vendor searches and the four low-stock results. | None. |
| 14 | Met | `test_14_empty_inventory_search_is_safe` is parameterized for `zzz` and the SQL-like search string; each response shows the exact empty-state text. | None. |
| 15 | Met | `test_15_shipments_default_and_direction_filters` checks initial inbound/expected and outbound results. | None. |
| 16 | Met | `test_16_shipment_row_lists_product_and_quantity` checks SHP-10492's product and quantity text. | None. |
| 17 | Met | `test_17_shipment_status_tabs_show_seeded_statuses` checks active, delayed, and history rows. | None. |
| 18 | Met | `test_18_manager_can_edit_shipment_to_delayed` updates SHP-10492 and checks the delayed dashboard row and product quantity. | None. |
| 19 | Met | `test_19_inventory_validation_preserves_form_data` checks server-side messages, both invalid field outlines, retained values, and no database write. | None. |
| 20 | Met | `test_20_duplicate_inventory_name_is_rejected` checks the required duplicate-name message and unchanged row count. | None. |
| 21 | Met | `test_21_missing_records_return_required_404` checks all three missing-record URLs, 404 status, and required text. | None. |
| 22 | Met | `test_22_deletes_are_post_only_and_confirmed` checks inventory/shipment/vendor POST forms, confirmation text, GET 405 responses, and POST deletion. In the integrated browser, the inventory delete button opened the expected native dialog; Cancel was clicked and the item remained visible. | None. |
| 23 | Met | `test_23_vendor_with_inventory_cannot_be_deleted` checks the exact refusal message and that the vendor remains. | None. |
| 24 | Met | `test_24_vendor_message_validation_and_success` checks invalid subject/body requests create no message and valid messages appear with today's date. | None. |
| 25 | Met | `test_25_inventory_persists_across_logout_and_restart` adds an item, logs out, constructs a new app instance against the same database, and finds the item after login. | None. |
| 26 | Met | `test_26_missing_secret_prevents_startup` starts a subprocess without secret or passwords, checks the required startup message, and verifies no database was created. | None. |
| 27 | Met | `test_27_get_logout_does_not_mutate_and_post_logout_preserves_orders` checks GET 405, POST logout, and purchase-order persistence after re-login. | None. |

Additional safeguard (not an extra CP2 criterion): `test_existing_incompatible_database_is_rejected_without_overwrite` verifies startup rejects an incompatible schema and preserves a sentinel row. The final suite reports 32 passed, including parameterized cases and this safeguard.
