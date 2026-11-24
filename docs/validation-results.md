# Phase 1 database validation record

Recorded locally on 2026-11-24 (macOS environment), after initializing `data/oryva_phase1_fresh.sqlite3` from `schema.sql`.

## Commands

```bash
python3 db.py init
python3 db.py smoke
```

The same commands work inside the documented `.venv` after activation. The project uses only Python's standard library.

## Actual results

```text
Initialized fresh database: /Users/prithvim/Documents/oryva-planning/data/oryva_phase1.sqlite3
PASS duplicate primary key rejected
PASS invalid enum rejected
PASS invalid calendar date rejected
PASS invalid foreign key rejected
PASS schema initialized (19 application tables)
PASS foreign-key enforcement enabled on each connection
```

The duplicate-key check attempted a second `SKU-000001`. The invalid-FK check attempted to insert demand referencing nonexistent `SKU-999999`; SQLite rejected it. Additional checks rejected an unsupported lifecycle enum and the impossible date `2026-02-30`. A separate opened connection reported `PRAGMA foreign_keys = 1` as well. Smoke-check fixtures are rolled back, so the initialized database remains empty.

## Scope of these checks

These are schema smoke checks, not full business-data validation. Generator-scale row counts, enum/date-edge suites, arithmetic reconciliation, lifecycle transition graph checks, anomaly outcomes, and deterministic checksums are assigned to later phases.
