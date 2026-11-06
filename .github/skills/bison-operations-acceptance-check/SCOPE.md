# Bison Operations Acceptance Check: Scope

This file is the scope definition for `bison-operations-acceptance-check` and is part of the AiDD Capstone assignment deliverable.

## Purpose

Review the entire AiDD Capstone repository for observable conformance to its written Bison Operations acceptance criteria. The current CP2 specification is the primary target when the request is to check the assignment build. The older `spec.md` is relevant history and must be called out if it conflicts; it must not silently override CP2.

## May read

- Repository specifications, acceptance criteria, `AGENTS.md`, README files, and data-model documentation.
- Tracked application source, templates, styles, tests, fixtures, and project configuration that are relevant to a criterion.
- Git status and file names needed to determine scope. Do not read secrets or unrelated files outside this repository.

## May run

- Existing project tests, linters, syntax checks, and narrowly targeted application checks that do not modify tracked files or persistent project data.
- For this prototype, use synthetic test data and a disposable working directory. Before importing or launching `app.py`, establish that its relative SQLite database path resolves outside the repository; the module's startup reset is destructive.
- Commands must remain local. Do not install packages, start a persistent service, or access an outside endpoint.

## Must never

1. Edit, create, delete, stage, or commit application source, tests, configuration, or user data as part of a review.
2. Import or launch the application with its working directory in the repository when that can create, reset, or alter `bison.db`; never reset or otherwise alter the user's database.
3. Use real credentials, real business data, external APIs, or external services.
4. Treat a hidden UI control as a server-side permission check, or describe static inspection as a runtime test.
5. Invent acceptance criteria, user research, test results, or fixes; mark absent evidence `UNVERIFIED`.
6. Ask follow-up questions or perform a second review run for the same request.

## Maintenance owner

Hillary Haine is responsible for repairing this skill if its instructions, scope, or review procedure break. The owner was selected from the AiDD team members identified by the requester.

## Stop conditions

Stop before any command that could mutate the repository database or other persistent project data. If a safe disposable setup cannot be established, continue with read-only evidence only and mark runtime-dependent criteria `UNVERIFIED`.
