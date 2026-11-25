# Validation summary

## Starter source and planner validation (2026-11-25)

Commands run:

```bash
python3 generate_data.py validate --out-dir data/starter
python3 planner.py --data-dir data/starter
python3 db.py smoke
python3 -m unittest -v
```

Results: generator validation passed 41 checks; schema smoke passed all six checks; all seven unit tests passed. The planner reconciled 1,308 weekly balances, emitted six BOM-constrained production plans across 288 weekly capacity rows, and generated 147 explainable shortages, 147 ranked rows, and 211 feasible mitigations (maximum three per shortage). Shortage rate is 11.24%; mean/median shortage quantity are 50.12/40.43 units. Generation inserted five issue cases linked to real source IDs. Each detector matched ground truth at precision/recall 1.0 (TP=1, FP=0, FN=0, TN=4). Labels are separately exported; planner features and hashes exclude `ground_truth.csv`. All exported starter files are under 50 MB. Planner checksums and detector metrics are in the corresponding files under `data/starter/`.

Anomaly values live in explicit scenario overlay records so the base operational rows remain valid and unrelated rows stay untouched. Each injection has `issue_type` and source links in SQLite and CSV. See `docs/phase3-planning.md` for production/BOM modeling limits.

## Full-scale generation after stock tuning

Two full generator runs completed in under six minutes each and passed source validation. `generate_data.py compare` matched all 22 generated outputs, including the SQLite DB, source manifest, issue fixtures, all CSV row counts, and SHA-256. See `docs/reproducibility.md`. `docs/full_planner_validation.json` is historical and predates the production and stock-tuning changes; no full planner run was done after those changes.

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
