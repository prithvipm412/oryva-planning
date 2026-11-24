# ORYVA AI Demand, Inventory & Supply Planning

Phase 1 delivers the SQLite schema, requirements map, data dictionary, and schema smoke checks. Data generation, planning calculations, dashboard, full dataset, and GitHub publishing are later phases.

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

## Phase 1 files

- `schema.sql` — normalized schema, constraints, lifecycle history, issue labeling, and immutable IDs.
- `db.py` — initialization and smoke-check commands. Every connection enables `PRAGMA foreign_keys=ON`.
- `docs/requirements.md` — requirement-to-phase mapping and completion evidence.
- `docs/data-dictionary.md` — columns, types, requiredness, allowed values, units, uniqueness, validation, and relationships.
