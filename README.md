# ORYVA AI Demand, Inventory & Supply Planning

The project includes a normalized SQLite schema, deterministic data generation, a shortage planner, labeled exception fixtures, and CSV/JSON evidence. GitHub publishing and form submission are manual steps.

## macOS setup

From the project directory, create and activate a Python virtual environment (Python 3.10 or newer):

```bash
cd ~/Documents/oryva-planning
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

Phase 1 uses only Python's standard library; no package installation is needed.

## Initialize a fresh database

Initialization refuses to overwrite an existing database. Remove or choose a different path only when you intentionally want a fresh database.

```bash
mkdir -p data
python db.py init
```

The default database path is `data/oryva_phase1_fresh.sqlite3` and is gitignored. To initialize another new path:

```bash
python db.py init --db data/oryva-check.sqlite3
```

## Run schema smoke checks

```bash
python db.py smoke
```

The checks confirm application tables exist, foreign-key enforcement is on for every opened connection, duplicate primary keys are rejected, and invalid foreign keys are rejected. `schema.sql` is the schema source of truth.

## Generate Phase 2 synthetic data

The starter preset is 24 SKUs, 6 locations, 12 demand weeks, 12 suppliers, and 36 inbound purchase orders. It uses seed `20261022` by default. Generation reuses `schema.sql` and `connect_db()` and refuses to write into a non-empty output directory.

```bash
python generate_data.py generate --preset starter --seed 20261022 --out-dir data/starter
```

This writes a SQLite database, 15 canonical CSV files, and `source_manifest.json` under `data/starter/`. The generator validates foreign keys, primary-key duplicates, ISO week/date alignment, UOM consistency, date order, lead-time-derived arrival dates, capacity/minimum quantities, and PO lifecycle history. Revalidate an existing output with:

```bash
python generate_data.py validate --out-dir data/starter
```

The shared full preset is defined for later use at 3,000 SKUs, 50 locations, 52 demand weeks, 500 suppliers, and 10,000 inbound purchase orders. It was not run in Phase 2. Scale can be adjusted with `--skus`, `--locations`, `--weeks`, `--suppliers`, and `--orders` while using the same generator.

To reproduce the starter data, choose two new, empty directories and run:

```bash
python generate_data.py generate --preset starter --seed 20261022 --out-dir /private/tmp/oryva-starter-run-1
python generate_data.py generate --preset starter --seed 20261022 --out-dir /private/tmp/oryva-starter-run-2
python generate_data.py compare --left /private/tmp/oryva-starter-run-1 --right /private/tmp/oryva-starter-run-2
```

The compare command checks row counts and SHA-256 for every canonical CSV. Actual Phase 2 commands and checksums are recorded in `docs/phase2-data.md`.

## Plan shortages and mitigations

Run the planner after generating a dataset. It computes weekly projected balances from opening stock, dated PO receipts, and demand; ranks shortages by shortage share and quantity; and exports mitigation options with cost, service impact, and capacity/lead-time feasibility fields.

```bash
python3 planner.py --data-dir data/starter
```

Outputs are `projected_balance.csv`, `shortages.csv`, `shortage_ranking.csv`, `mitigations.csv`, `ground_truth.csv`, and `planner_validation.json`. The five required edge cases are separate rule fixtures in `ground_truth.csv`, excluded from baseline planner inputs; they document expected detection outcomes and traceability semantics. They are not represented as deliberately corrupted operational rows.

Only feasible mitigation options are exported, with no more than three per shortage. Options are ranked by lowest residual service impact, then incremental cost; supplier options require matching UOM, lead time of at most seven days, minimum order quantity, and remaining effective capacity. Demand allocation remains the no-capacity fallback and reports its service loss explicitly. Planner outputs plus source CSVs in `data/starter/` are kept below 50 MB each.

Run the committed validation suite:

```bash
python3 generate_data.py validate --out-dir data/starter
python3 planner.py --data-dir data/starter
python3 db.py smoke
python3 -m unittest -v
```

## Full fixed-seed reproducibility run

Generate two full-scale source datasets in separate clean directories, compare every canonical input CSV by row count and SHA-256, and plan each run:

```bash
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-run1
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-run2
python3 generate_data.py compare --left /private/tmp/oryva-full-run1 --right /private/tmp/oryva-full-run2
```

The complete run results and any remaining limitations are recorded in `docs/phase3-planning.md`.

See [`docs/reproducibility.md`](docs/reproducibility.md) for the full run row counts and checksums, and [`docs/validation-results.md`](docs/validation-results.md) for actual starter validation results.

## Phase 2 files and outputs

- `generate_data.py` — shared starter/full generator, validation, CSV export, and reproducibility comparison CLI.
- `data/starter/` — starter SQLite database, deterministic CSVs, and synthetic source manifest.
- `docs/phase2-data.md` — scale definitions, assortment/inbound rules, validation results, and per-file checksums.
- `docs/validation-results.md` — Phase 1 smoke-check record.
- `planner.py`, `test_planner.py` — deterministic planning exports and starter evidence tests.
- `docs/phase3-planning.md`, `docs/reproducibility.md` — planning rules, known limits, full-scale reproducibility evidence.

## Phase 1 files

- `schema.sql` — normalized schema, constraints, lifecycle history, issue labeling, and immutable IDs.
- `db.py` — initialization and smoke-check commands. Every project connection enables `PRAGMA foreign_keys=ON`.
- `docs/requirements.md` — requirement-to-phase mapping and completion evidence.
- `docs/data-dictionary.md` — columns, types, requiredness, allowed values, units, uniqueness, validation, and relationships.
