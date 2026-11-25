# Validation summary

## Starter source and planner validation (2026-11-25)

Commands run:

```bash
python3 generate_data.py validate --out-dir data/starter
python3 planner.py --data-dir data/starter
python3 db.py smoke
python3 -m unittest -v
```

Results: generator validation passed 40 checks; schema smoke passed all six checks; all four unit tests passed. The planner reconciled 1,308 weekly balances and generated 1,052 explainable shortages, 1,052 ranked shortage rows, 1,786 feasible mitigations (no more than three per shortage), and five separately stored labeled edge-case fixtures. All exported starter files are under 50 MB. Planner checksums and detailed booleans are saved in `data/starter/planner_validation.json`.

The edge fixtures point to relevant source IDs, but they describe isolated expected-rule cases rather than corrupting baseline rows. Automated fixture-specific detectors and issue links in SQLite are not implemented. See `docs/phase3-planning.md` for this and the production/BOM modeling limits.

## Phase 1 database validation record

Recorded locally on 2026-11-24 (macOS environment), after initializing `data/oryva_phase1_fresh.sqlite3` from `schema.sql`.

## Commands

```bash
python3 db.py init
python3 db.py smoke
```

The same commands work inside the documented `.venv` after activation. The project uses only Python's standard library.

## Actual results

```text
Initialized fresh database: /Users/prithvim/Documents/oryva-planning/data/oryva_phase1_fresh.sqlite3
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
