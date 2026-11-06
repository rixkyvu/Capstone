# Bison Operations acceptance check — run 01

This evidence file records the single reviewer run required by the AiDD Capstone assignment. The request and the agent's returned output are preserved below; the check of that output is in [check-01.md](./check-01.md).

## Request sent to the reviewer agent

Review the entire repository against all numbered acceptance criteria in the current CP2 specification. For each criterion 1–27, mark PASS, FAIL, or UNVERIFIED, explain the evidence from code or a safe local run, and state what you actually ran. Do not ask follow-up questions. Do not modify anything. This is the only run.

## Agent output (verbatim)

# Acceptance review — run 1 of 1

**Target:** `spec-CP2.md`, criteria 1–27. The older `spec.md` describes an earlier prototype and conflicts with CP2 on persistence and secret handling; CP2 is the target.

**Checks actually run:** Read-only inspection of the skill, scope, specifications, source, templates, styles, tests/docs, and tracked-file inventory; `Get-ChildItem`, `git status --short`, `git ls-files`, and targeted `rg -n` searches. No application, test suite, or syntax check was run: importing or launching the app resets the database, and no permitted disposable working directory was established. Findings below are static, not runtime observations. No repository changes were made.

1. **FAIL** — `app.py:46–50, 99–102`: users have no role field; only `admin@bisonoperations.com` is seeded, not the three specified accounts.
2. **PASS** — `app.py:185–196`: unknown email and wrong password use the same error text; session assignment occurs only after valid credentials.
3. **PASS** — `app.py:161–166, 234–236, 397–399, 470–472`: the protected inventory, shipment, and vendor routes use `login_required`, which redirects unauthenticated requests to login.
4. **FAIL** — `app.py:161–166, 297–346`; `templates/inventory.html:2–3`: no role-specific permission check or 403 behavior; inventory controls are rendered.
5. **FAIL** — `app.py:470–537`: vendor routes require login but do not restrict access by role.
6. **FAIL** — `app.py:46–50, 349–376, 461–467`: no manager role or server-side role checks for reorder or shipment deletion.
7. **PASS** — `app.py:122–137, 208–230`; `templates/dashboard.html:4–5`: seed quantities yield the four specified low-stock items, and the dashboard renders quantity, threshold, Reorder, and Contact Vendor.
8. **FAIL** — `app.py:351–367`; `templates/reorder.html:1`: review details and suggested quantity are present, but Cancel links to inventory, not `/`.
9. **PASS** — `app.py:358–366`; `app.py:532–537`; `templates/vendor_detail.html:19–29`: reorder creates a PO and message, flashes the PO confirmation, and vendor detail displays orders and message history.
10. **PASS** — `app.py:369–376, 208–230`; `templates/vendor_detail.html:29`: receiving marks the PO received and adds its quantity to inventory; the dashboard queries low-stock items.
11. **FAIL** — `app.py:356–357`; `templates/reorder.html:1`: quantity is clamped to at least 1; invalid text raises during integer conversion, and the specified validation message is absent.
12. **PASS** — `app.py:122–137, 236–270`: seeded CleanPro items are searched by vendor name and fit within the five-row page size.
13. **PASS** — `app.py:122–137, 236–270`: search covers SKU and department; the low-stock filter uses the seeded threshold comparisons.
14. **FAIL** — `templates/inventory.html:3`: empty results display “No items found,” not the required “No items match your search.”
15. **PASS** — `app.py:142–148, 399–415`; `templates/shipments.html:1`: seeded expected inbound and outbound shipments match the specified codes; the route defaults to inbound/expected.
16. **PASS** — `app.py:153–156, 407–415`; `templates/shipments.html:1`: SHP-10492 is linked to Sparkling Water, and shipment rows render aggregated product names.
17. **PASS** — `app.py:142–148, 399–415`; `templates/shipments.html:1`: seed data and status filters include the specified Active, Delayed, and History shipments.
18. **FAIL** — `app.py:440–458, 208–230`: editing shipment status and displaying delayed shipments are implemented, but no manager account or role check exists.
19. **FAIL** — `app.py:299–315`; `templates/inventory_form.html:6–15`: server code directly converts inputs to integers and lacks field-error rendering and value-preserving validation.
20. **FAIL** — `app.py:60–64, 302–314`: item names are not unique in the schema and add has no duplicate-name check or required message.
21. **FAIL** — `app.py:320–337, 440–458, 527–531`: missing inventory/shipment records render forms; missing vendors redirect. The required 404 page is not implemented.
22. **FAIL** — `app.py:340–346, 461–467, 513–522`; inventory, shipment, and vendor templates contain POST forms with confirmation text, but the specified supervisor account/role is absent.
23. **FAIL** — `app.py:515–522`: vendor deletion proceeds and unassigns its inventory rather than refusing deletion when items remain.
24. **FAIL** — `app.py:540–552`; `templates/vendor_detail.html:22–25`: the route inserts messages without server-side subject/body validation or the specified errors.
25. **FAIL** — `app.py:199–202, 555–556`: logout and module initialization call `reset_db()`, contradicting persistence across sign-out/restart.
26. **FAIL** — `app.py:12`: the Flask secret is hard-coded; startup does not require `SECRET_KEY`.
27. **FAIL** — `app.py:199–202`; `templates/base.html:1`: logout accepts GET and resets the database; Sign Out is a link, not a POST form.

**Totals:** PASS 10 · FAIL 17 · UNVERIFIED 0
