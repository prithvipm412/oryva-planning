"""Phase 1 database setup and smoke checks for ORYVA planning."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "schema.sql"
DEFAULT_DB = ROOT / "data" / "oryva_phase1_fresh.sqlite3"


def connect_db(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    """Open a SQLite connection with FK enforcement enabled every time."""
    connection = sqlite3.connect(str(path))
    connection.execute("PRAGMA foreign_keys = ON")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError("SQLite foreign-key enforcement could not be enabled")
    return connection


def initialize(path: str | Path = DEFAULT_DB) -> None:
    """Create a fresh database, refusing to overwrite an existing one."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with connect_db(target) as connection:
            connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    except Exception:
        target.unlink(missing_ok=True)
        raise


def smoke_checks(path: str | Path = DEFAULT_DB) -> None:
    """Verify schema presence, FK enforcement, and expected constraint failures."""
    with connect_db(path) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        connection.execute("SAVEPOINT smoke_checks")
        table_count = connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
        assert table_count == 19, f"Expected 19 application tables, found {table_count}"

        connection.execute(
            "INSERT INTO sku(sku_id,name,base_uom) VALUES ('SKU-000001','Widget','EA')"
        )
        try:
            connection.execute(
                "INSERT INTO sku(sku_id,name,base_uom) VALUES ('SKU-000001','Duplicate','EA')"
            )
        except sqlite3.IntegrityError:
            print("PASS duplicate primary key rejected")
        else:
            raise AssertionError("Duplicate primary key was accepted")

        try:
            connection.execute(
                "INSERT INTO sku(sku_id,name,base_uom,lifecycle_state) VALUES ('SKU-000002','Bad state','EA','UNKNOWN')"
            )
        except sqlite3.IntegrityError:
            print("PASS invalid enum rejected")
        else:
            raise AssertionError("Invalid lifecycle enum was accepted")

        connection.execute(
            "INSERT INTO location(location_id,name,location_type,country_code,timezone) "
            "VALUES ('LOC-000001','Smoke location','WAREHOUSE','US','UTC')"
        )
        try:
            connection.execute(
                "INSERT INTO forecast_demand(demand_id,sku_id,location_id,week_start,week_code,forecast_qty,uom) "
                "VALUES ('DEM-SKU-000001-LOC-000001-2026W01','SKU-000001','LOC-000001','2026-02-30','2026W01',10,'EA')"
            )
        except sqlite3.IntegrityError:
            print("PASS invalid calendar date rejected")
        else:
            raise AssertionError("Invalid calendar date was accepted")

        try:
            connection.execute(
                "INSERT INTO forecast_demand(demand_id,sku_id,location_id,week_start,week_code,forecast_qty,uom) "
                "VALUES ('DEM-SKU-000001-LOC-000001-2026W01','SKU-999999','LOC-000001','2026-01-05','2026W01',10,'EA')"
            )
        except sqlite3.IntegrityError:
            print("PASS invalid foreign key rejected")
        else:
            raise AssertionError("Invalid foreign key was accepted")

        # A second connection must also turn FK checks on.
        with connect_db(path) as second:
            assert second.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        connection.execute("ROLLBACK TO smoke_checks")
        connection.execute("RELEASE smoke_checks")
        print(f"PASS schema initialized ({table_count} application tables)")
        print("PASS foreign-key enforcement enabled on each connection")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "smoke"))
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    args = parser.parse_args()
    if args.command == "init":
        initialize(args.db)
        print(f"Initialized fresh database: {args.db}")
    else:
        smoke_checks(args.db)


if __name__ == "__main__":
    main()
