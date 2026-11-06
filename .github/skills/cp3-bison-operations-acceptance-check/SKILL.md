---
name: cp3-bison-operations-acceptance-check
description: "Use when checking the AiDD Capstone Bison Operations repository against its CP2 acceptance criteria, including routes, permissions, inventory, shipments, vendors, persistence, security defenses, and test evidence."
argument-hint: "Review the repository against the applicable acceptance criteria and report evidence."
user-invocable: true
---

# Bison Operations Acceptance Check

This CP3-named skill reviews the whole AiDD Capstone repository against its written acceptance criteria. It is an evidence-producing reviewer, not an implementation or remediation agent.

## Scope and limits

Read [CP3-SCOPE.md](./CP3-SCOPE.md) before reviewing. It defines what may be read or run, the prohibition list, and the maintainer responsible for this skill.

## Review procedure

1. Read the repository's current assignment/specification and identify which acceptance criteria apply. Prefer the latest explicitly numbered criteria; call out conflicting or superseded specs rather than silently combining them.
2. Inspect all relevant tracked application files: route and data code, templates, styles, test setup, fixtures, and supporting documentation. Search the whole repository when a criterion crosses layers.
3. Use existing tests and narrowly targeted local checks when useful. Do not install dependencies or alter project files, application data, or configuration.
4. If importing or launching this prototype can reset its relative-path SQLite database, run from a disposable working directory and confirm the resolved database path is outside the repository before any app import. Use synthetic data only.
5. Make one review run per request. Do not ask follow-up questions or launch a second review run. If a necessary detail is absent, mark the affected item `UNVERIFIED` and state what evidence is missing.
6. For every criterion in scope, report `PASS`, `FAIL`, or `UNVERIFIED`, with direct evidence. A `PASS` for an acceptance outcome that requires observable app behavior requires an actual safe request or interaction; static code alone cannot establish that the outcome works. If it was not exercised, mark it `UNVERIFIED`. Static evidence may support `FAIL` when the implementation plainly contradicts the criterion. Never call static inference a runtime test.
7. Return concise, numbered findings and verification steps. Do not modify the application or claim a fix was made.

## Required output

- Name the specification and criterion range reviewed.
- State commands/checks actually run and any that could not be run.
- List each criterion once with status, evidence, and a short reason.
- End with a count of `PASS`, `FAIL`, and `UNVERIFIED` items.

## Evidence discipline

Use synthetic accounts and records only. Quote short exact UI text where relevant. A claim about a permission must be supported by both the route's server-side behavior and a request when safely testable; hiding a control alone is not proof. A claim about persistence must test across the relevant lifecycle or be marked unverified. Report no user research or production readiness conclusions unless the repository supplies evidence for them.
