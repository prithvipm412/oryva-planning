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
python3 generate_data.py generate --preset starter --seed 20261022 --out-dir /private/tmp/oryva-starter-generated
```

This writes a SQLite database, 19 source CSV files, edge-case detection JSON, and `source_manifest.json` under the chosen empty output directory. The committed, planned starter dataset is in `data/starter/`. The generator validates foreign keys, primary-key duplicates, ISO week/date alignment, UOM consistency, date order, lead-time-derived arrival dates, capacity/minimum quantities, PO lifecycle history, and injected-case detector metrics. Revalidate an existing output with:

```bash
python3 generate_data.py validate --out-dir data/starter
```

| Preset | SKUs | Locations | Weeks | Suppliers | POs |
|---|---:|---:|---:|---:|---:|
| starter | 24 | 6 | 12 | 12 | 36 |
| full | 3,000 | 50 | 52 | 500 | 10,000 |

Scale can be adjusted with `--skus`, `--locations`, `--weeks`, `--suppliers`, and `--orders` while using the same generator.

To reproduce the starter data, choose two new, empty directories and run:

```bash
python3 generate_data.py generate --preset starter --seed 20261022 --out-dir /private/tmp/oryva-starter-run-1
python3 generate_data.py generate --preset starter --seed 20261022 --out-dir /private/tmp/oryva-starter-run-2
python planner.py --data-dir /private/tmp/oryva-starter-run-1
python planner.py --data-dir /private/tmp/oryva-starter-run-2
python generate_data.py validate --out-dir /private/tmp/oryva-starter-run-1
python generate_data.py validate --out-dir /private/tmp/oryva-starter-run-2
python3 generate_data.py compare --left /private/tmp/oryva-starter-run-1 --right /private/tmp/oryva-starter-run-2
```

The compare command checks row counts for CSVs and SQLite tables, and SHA-256 for every output file, including CSVs, JSON, SQLite, and manifests. Current results are in `docs/reproducibility.md`.

## Plan shortages and mitigations

Run the planner after generating a dataset. It computes weekly projected balances from opening stock, dated PO receipts, demand, and feasible production. BOM component availability and weekly production capacity constrain production plans; any residual factory deficit includes a production-constraint cause. It ranks shortages by shortage share and quantity, then exports mitigation options with cost, service impact, and capacity/lead-time feasibility fields.

```bash
python3 planner.py --data-dir data/starter
```

Planner outputs are `projected_balance.csv`, `production_plan.csv`, `production_capacity_weekly.csv`, `shortages.csv`, `shortage_ranking.csv`, `mitigations.csv`, and `planner_validation.json`. Generation also inserts five isolated, labeled anomaly cases into `issue_case` and `issue_case_record`, exports their scenario overlays in `edge_case_injections.csv`, and keeps expected outcomes in `ground_truth.csv`. The planner reads neither ground truth nor anomaly overlays.

Only feasible mitigation options are exported, with no more than three per shortage. Options are ranked by lowest residual service impact, then incremental cost; supplier options require matching UOM, lead time of at most seven days, minimum order quantity, and remaining effective capacity. Demand allocation remains the no-capacity fallback and reports its service loss explicitly. Planner outputs plus source CSVs in `data/starter/` are kept below 50 MB each.

Run the committed validation suite:

```bash
python3 generate_data.py validate --out-dir data/starter
python3 planner.py --data-dir data/starter
python3 db.py smoke
python3 -m unittest -v
```

## Full fixed-seed reproducibility run

Generate two full-scale source datasets in separate clean directories and compare every generated file by row count and SHA-256:

```bash
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-tuned1
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-tuned2
python3 generate_data.py compare --left /private/tmp/oryva-full-tuned1 --right /private/tmp/oryva-full-tuned2
```

The complete run results and any remaining limitations are recorded in `docs/phase3-planning.md`.

See [`docs/reproducibility.md`](docs/reproducibility.md) for the full run row counts and checksums, and [`docs/validation-results.md`](docs/validation-results.md) for actual starter validation results.

## Entity and ERD summary

`schema.sql` defines the relational model and foreign keys. Main links:

| Relationship | Cardinality | Implementation |
|---|---|---|
| SKU → forecast, inventory, capacity, lead time, PO lines, plans, shortages | 1:N | SKU foreign keys |
| Location → forecast, inventory, lead-time destination, production, PO destination, shortages | 1:N | Location foreign keys |
| Supplier → capacity, lead time, purchase orders | 1:N | Supplier foreign keys |
| PurchaseOrder → lines and arrival events | 1:N | `purchase_order_line`, `transport_delay` |
| SKU ↔ substitute SKU | N:M | Effective-dated `sku_substitute` bridge |
| Parent SKU ↔ component SKU | N:M | Effective-dated `bill_of_material` bridge |
| Shortage → mitigation options | 1:N | `mitigation_option` |
| Issue case ↔ affected source records | N:M | `issue_case_record` bridge |

`lifecycle_history` stores state changes as events. Optional route origins, substitute effectivity, and mitigation resource links are documented in [`docs/data-dictionary.md`](docs/data-dictionary.md).

## Validation results

| Check | Result |
|---|---:|
| Generator validation metrics | 41 passed |
| Planner balances reconciled | 1,308 / 1,308 |
| Starter shortages | 147 / 1,308 demand rows (11.24%) |
| Production plans | 6; weekly capacity rows: 288 |
| Mitigation options | 211 feasible; maximum 3 per shortage |
| Five anomaly detectors | Precision 1.00 and recall 1.00 for each |
| Schema smoke checks | All passed |
| Unit tests | 7 passed |
| Full-scale planner balances | 6,021,600 / 6,021,600 reconciled |
| Full-scale shortages | 602,173 / 6,021,600 rows (10.0002%); mean 184.16, median 150.22 units |
| Full-scale mitigations | 998,008 feasible; maximum 3 per shortage |
| Committed output size | Every file below 50 MB |

## Edge-case detection

| `issue_type` | Expected decision | Precision | Recall |
|---|---|---:|---:|
| INBOUND_INVENTORY_COUNTED_TWICE | DEDUPE_DUPLICATE_RECEIPT | 1.00 | 1.00 |
| UNAPPROVED_SUBSTITUTE_SKU | REJECT_SUBSTITUTE | 1.00 | 1.00 |
| SUPPLIER_CAPACITY_EXCEEDED | REJECT_OVER_CAPACITY | 1.00 | 1.00 |
| SHORTAGE_WITHOUT_LEAD_TIME | RAISE_MISSING_LEAD_TIME_ALERT | 1.00 | 1.00 |
| UOM_MISMATCH | REJECT_UOM_MISMATCH | 1.00 | 1.00 |

The scenario overlays link to source records in `issue_case_record.csv`; expected labels are in `ground_truth.csv`. The planner does not load the ground-truth file.

## Reproducibility results

| Run | Files compared | Matching results |
|---|---:|---|
| Starter generator + planner, seed 20261022 | 29 | All CSV row counts, SQLite table counts, and output SHA-256 matched |
| Full generator, seed 20261022 | 22 | All CSV row counts, SQLite table counts, and output SHA-256 matched; run 2 deleted after comparison |

## Known limitations

- Full-scale planner outputs were validated once on the regenerated seed 20261022 dataset; full planner output reproducibility was not compared.
- The five anomaly detectors run against labeled scenario overlays linked to valid source records. They do not mutate baseline facts or test broad production anomaly streams.
- Production capacity is divided evenly across forecast weeks. Production plans are exported as CSV; planner execution does not persist plans into the SQLite lifecycle table.
- GitHub publishing and assignment form submission remain manual.

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
