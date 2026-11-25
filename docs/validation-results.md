# Validation summary

## Starter source and planner validation (2026-11-25)

Commands run:

```bash
python3 generate_data.py validate --out-dir data/starter
python3 planner.py --data-dir data/starter
python3 db.py smoke
python3 -m unittest -v
```

Results: generator validation passed 41 checks; schema smoke passed all six checks; all six unit tests passed. The planner reconciled 1,308 weekly balances, emitted three BOM-constrained production plans across 288 weekly capacity rows, and generated 1,050 explainable shortages, 1,050 ranked rows, and 1,778 feasible mitigations (maximum three per shortage). Sixty-eight shortages name a production constraint. Generation inserted five issue cases linked to real source IDs. Each per-issue detector matched ground truth at precision/recall 1.0 (TP=1, FP=0, FN=0, TN=4). Labels are separately exported; planner features and hashes exclude `ground_truth.csv`. All exported starter files are under 50 MB. Planner checksums and detector metrics are in the corresponding files under `data/starter/`.

Anomaly values live in explicit scenario overlay records so the base operational rows remain valid and unrelated rows stay untouched. Each injection has `issue_type` and source links in SQLite and CSV. See `docs/phase3-planning.md` for production/BOM modeling limits.

## Full-scale planner run

One capped planner run completed on the seed `20261022` full dataset. It reconciled 6,021,600 balances and wrote 5,739,530 shortages, 5,739,530 ranked rows, and 9,626,115 feasible mitigation options, with all planner validation booleans passing. The machine-readable summary and hashes are `docs/full_planner_validation.json`; full CSVs remain in `/private/tmp/oryva-full-run2` and are excluded from the repository.

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
