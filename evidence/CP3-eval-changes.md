# CP3 Eval Changes Since CP2

This log records the automated acceptance checks in `tests/test_acceptance.py`.
The repository did not contain a runnable CP2 pytest suite to compare against;
the malformed former `conftest.py` was replaced with working isolated fixtures.
Consequently, the checks below are **added**, not edits to previously passing
evals. The exact final command and complete terminal result are in
[`CP3-final-pytest-run.txt`](./CP3-final-pytest-run.txt).

| Eval | Change | Reason |
|---|---|---|
| E01 | Added: `test_01_three_seeded_roles_can_sign_in` | Verify each required seeded role and navigation label. |
| E02 | Added: `test_02_invalid_login_shows_same_error_and_does_not_authenticate` | Verify indistinguishable login errors and no authenticated access. |
| E03 | Added: `test_03_protected_pages_redirect_anonymous_users` | Check authentication on protected routes. |
| E04 | Added: `test_04_team_member_cannot_mutate_inventory` | Check read-only UI and server-enforced mutation denial. |
| E05 | Added: `test_05_team_member_cannot_open_vendors` | Check role restrictions on vendor list and detail pages. |
| E06 | Added: `test_06_manager_cannot_reorder_or_delete_shipments` | Check manager restrictions and unchanged records. |
| E07 | Added: `test_07_dashboard_has_four_low_stock_items` | Check the exact low-stock entries, quantities, thresholds, and reorder links. |
| E08 | Added: `test_08_reorder_cancel_returns_to_dashboard_without_creating_po` | Check suggested reorder values, cancel destination, and no write. |
| E09 | Added: `test_09_reorder_creates_pending_order_and_message` | Check order, vendor message, and unchanged inventory before receiving. |
| E10 | Added: `test_10_receiving_order_updates_quantity_once` | Check receipt behavior and prevent double-counting. |
| E11 | Added: `test_11_invalid_reorder_quantity_is_rejected` (four inputs) | Check server-side integer/range validation and no order creation. |
| E12 | Added: `test_12_search_cleanpro_returns_two_items` | Check vendor search results. |
| E13 | Added: `test_13_inventory_search_and_low_stock_filter` | Check SKU/vendor search and stock filtering. |
| E14 | Added: `test_14_empty_inventory_search_is_safe` (two inputs) | Check exact empty state and safe handling of malformed search text. |
| E15 | Added: `test_15_shipments_default_and_direction_filters` | Check initial inbound view and direction switching. |
| E16 | Added: `test_16_shipment_row_lists_product_and_quantity` | Check shipment item association and display. |
| E17 | Added: `test_17_shipment_status_tabs_show_seeded_statuses` | Check the expected status-specific shipment records. |
| E18 | Added: `test_18_manager_can_edit_shipment_to_delayed` | Check manager edit permission and dashboard reflection. |
| E19 | Added: `test_19_inventory_validation_preserves_form_data` | Check server-side field errors, invalid outlines, retained values, and no write. |
| E20 | Added: `test_20_duplicate_inventory_name_is_rejected` | Check uniqueness and the required duplicate-name message. |
| E21 | Added: `test_21_missing_records_return_required_404` | Check missing-record response behavior. |
| E22 | Added: `test_22_deletes_are_post_only_and_confirmed`; additionally checked in the integrated browser | Check POST forms, confirmation text, GET rejection, deletion, and Cancel-dismiss behavior. |
| E23 | Added: `test_23_vendor_with_inventory_cannot_be_deleted` | Check referential business rule and refusal message. |
| E24 | Added: `test_24_vendor_message_validation_and_success` | Check message form validation, no invalid writes, and valid history entry. |
| E25 | Added: `test_25_inventory_persists_across_logout_and_restart` | Check database persistence across logout and a new app instance. |
| E26 | Added: `test_26_missing_secret_prevents_startup` | Check fail-closed startup without `SECRET_KEY`. |
| E27 | Added: `test_27_get_logout_does_not_mutate_and_post_logout_preserves_orders` | Check POST-only logout and purchase-order persistence. |
| Supplemental | Added: `test_existing_incompatible_database_is_rejected_without_overwrite` | Verify the new schema guard rejects incompatible databases without deleting existing data. |

No prior eval was marked changed or removed because no executable CP2 eval suite
was available in the repository. The final recorded run is **32 passed**.
Criterion 22 also received an integrated-browser Cancel-dialog check documented
in [`CP3-final-conformance.md`](./CP3-final-conformance.md).
