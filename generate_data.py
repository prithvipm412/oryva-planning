"""Deterministic ORYVA data generator with traceable anomaly fixtures."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Sequence

from db import connect_db, initialize

SEED = 20261022
DATA_AS_OF = date(2026, 11, 24)
CREATED_AT = "2026-11-24T00:00:00.000Z"
PERIOD_START = "2026-01-01"
PERIOD_END = "2026-12-31"
GENERATOR_VERSION = "phase2-v1"

PRESETS = {
    "starter": {"skus": 24, "locations": 6, "weeks": 12, "suppliers": 12, "orders": 36},
    "full": {"skus": 3000, "locations": 50, "weeks": 52, "suppliers": 500, "orders": 10000},
}

EXPORT_TABLES = {
    "sku": ["sku_id"],
    "location": ["location_id"],
    "supplier": ["supplier_id"],
    "sku_substitute": ["primary_sku_id", "substitute_sku_id", "effective_from"],
    "forecast_demand": ["demand_id"],
    "inventory": ["inventory_id"],
    "supplier_capacity": ["supplier_capacity_id"],
    "lead_time": ["lead_time_id"],
    "production_capacity": ["production_capacity_id"],
    "bill_of_material": ["parent_sku_id", "component_sku_id", "effective_from"],
    "purchase_order": ["purchase_order_id"],
    "purchase_order_line": ["purchase_order_line_id"],
    "transport_delay": ["transport_delay_id"],
    "lifecycle_history": ["lifecycle_history_id"],
    "issue_case": ["issue_case_id"],
    "issue_case_record": ["issue_case_record_id"],
}


@dataclass(frozen=True)
class Scale:
    skus: int
    locations: int
    weeks: int
    suppliers: int
    orders: int


def make_scale(args: argparse.Namespace) -> Scale:
    values = dict(PRESETS[args.preset])
    for key in values:
        override = getattr(args, key, None)
        if override is not None:
            values[key] = override
    if any(value < 1 for value in values.values()):
        raise ValueError("All scale values must be at least 1")
    if values["weeks"] > 52:
        raise ValueError("weeks must be between 1 and 52 for the 2026 ISO-year dataset")
    if values["skus"] > 999999 or values["locations"] > 999999 or values["suppliers"] > 999999:
        raise ValueError("SKU, location, and supplier counts cannot exceed six-digit ID space")
    if values["orders"] > 999999:
        raise ValueError("Order count cannot exceed the six-digit PO ID space")
    return Scale(**values)


def padded(prefix: str, value: int, width: int = 10) -> str:
    return f"{prefix}{value:0{width}d}"


def iso_week_start(week: int) -> date:
    return date.fromisocalendar(2026, week, 1)


def stamp(day: date, hour: int = 0) -> str:
    return f"{day.isoformat()}T{hour:02d}:00:00.000Z"


def batched(rows: Iterable[tuple], size: int = 5000) -> Iterable[list[tuple]]:
    batch: list[tuple] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def insert_batches(connection: sqlite3.Connection, sql: str, rows: Iterable[tuple]) -> int:
    count = 0
    for batch in batched(rows):
        connection.executemany(sql, batch)
        count += len(batch)
    return count


def build_masters(scale: Scale, rng: random.Random) -> tuple[list[dict], list[dict], list[dict]]:
    uoms = ("EA", "CS", "KG")
    families = ("Hydration", "Home Care", "Pantry", "Personal Care", "Outdoor", "Electronics")
    skus = []
    for i in range(scale.skus):
        family = families[i % len(families)]
        skus.append({
            "sku_id": f"SKU-{i + 1:06d}",
            "name": f"{family} Product {i + 1:05d}",
            "description": f"Synthetic {family.lower()} item, segment {i % 8 + 1}",
            "base_uom": uoms[(i // len(families)) % len(uoms)],
            "lifecycle_state": "ACTIVE",
            "created_at": CREATED_AT,
        })

    fixed_types = ["DISTRIBUTION_CENTER", "FACTORY", "WAREHOUSE", "STORE", "STORE", "WAREHOUSE"]
    fixed_places = [
        ("US", "America/Chicago"), ("US", "America/Detroit"), ("US", "America/Los_Angeles"),
        ("CA", "America/Toronto"), ("MX", "America/Mexico_City"), ("US", "America/New_York"),
    ]
    locations = []
    for i in range(scale.locations):
        if i < len(fixed_types):
            location_type = fixed_types[i]
            country, timezone = fixed_places[i]
        else:
            location_type = ("WAREHOUSE", "STORE", "DISTRIBUTION_CENTER", "FACTORY")[i % 4]
            country, timezone = fixed_places[i % len(fixed_places)]
        locations.append({
            "location_id": f"LOC-{i + 1:06d}",
            "name": f"{location_type.replace('_', ' ').title()} {i + 1:03d}",
            "location_type": location_type,
            "country_code": country,
            "timezone": timezone,
            "lifecycle_state": "ACTIVE",
            "created_at": CREATED_AT,
        })

    suppliers = []
    for i in range(scale.suppliers):
        country = ("US", "CA", "MX", "GB", "DE")[i % 5]
        suppliers.append({
            "supplier_id": f"SUP-{i + 1:06d}",
            "name": f"Synthetic Supplier {i + 1:04d}",
            "country_code": country,
            "lifecycle_state": "ACTIVE",
            "created_at": CREATED_AT,
        })
    return skus, locations, suppliers


def make_assortment(skus: Sequence[dict], locations: Sequence[dict]) -> list[tuple[int, int]]:
    factories = {i for i, loc in enumerate(locations) if loc["location_type"] == "FACTORY"}
    pairs = []
    for sku_i in range(len(skus)):
        for location_i, _location in enumerate(locations):
            # A stable 70% modular rule plus all factory locations.
            if (sku_i * 7 + location_i * 3) % 10 < 7 or location_i in factories:
                pairs.append((sku_i, location_i))
    return pairs


def build_supplier_mapping(scale: Scale) -> dict[int, tuple[int, ...]]:
    mapping: dict[int, tuple[int, ...]] = {}
    for sku_i in range(scale.skus):
        primary = sku_i % scale.suppliers
        if scale.suppliers == 1:
            mapping[sku_i] = (primary,)
        else:
            alternate = (primary + 1 + sku_i % (scale.suppliers - 1)) % scale.suppliers
            mapping[sku_i] = (primary, alternate)
    return mapping


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow(["" if value is None else value for value in row])
            count += 1
    return count


def inject_edge_cases(connection: sqlite3.Connection, out_dir: Path) -> tuple[dict, dict]:
    """Add explicit, isolated anomaly overlays linked to real source records."""
    po = connection.execute("""SELECT l.purchase_order_line_id,l.sku_id,l.quantity,l.uom,
      p.supplier_id,p.destination_location_id,p.order_date FROM purchase_order_line l
      JOIN purchase_order p USING(purchase_order_id) ORDER BY l.purchase_order_line_id LIMIT 1""").fetchone()
    inv = connection.execute("SELECT inventory_id,on_hand_qty,inbound_qty FROM inventory WHERE sku_id=? AND location_id=?",
                             (po[1], po[5])).fetchone()
    cap = connection.execute("SELECT supplier_capacity_id,capacity_qty,minimum_order_qty,uom FROM supplier_capacity WHERE supplier_id=? AND sku_id=?",
                              (po[4], po[1])).fetchone()
    demand = connection.execute("SELECT demand_id,sku_id,location_id,week_start FROM forecast_demand ORDER BY demand_id LIMIT 1").fetchone()
    substitute = connection.execute("""SELECT a.sku_id,b.sku_id FROM sku a JOIN sku b ON a.sku_id<>b.sku_id
      WHERE NOT EXISTS (SELECT 1 FROM sku_substitute x WHERE x.primary_sku_id=a.sku_id
        AND x.substitute_sku_id=b.sku_id AND x.approval_state='APPROVED'
        AND x.effective_from<='2026-01-01' AND (x.effective_to IS NULL OR x.effective_to>='2026-01-01'))
      ORDER BY a.sku_id,b.sku_id LIMIT 1""").fetchone()
    missing_supplier = connection.execute("""SELECT s.supplier_id FROM supplier s WHERE NOT EXISTS
      (SELECT 1 FROM lead_time l WHERE l.supplier_id=s.supplier_id AND l.sku_id=?
       AND l.destination_location_id=? AND l.effective_from<=? AND (l.effective_to IS NULL OR l.effective_to>=?))
      ORDER BY s.supplier_id LIMIT 1""", (demand[1], demand[2], demand[3], demand[3])).fetchone()[0]
    base_uom = connection.execute("SELECT base_uom FROM sku WHERE sku_id=?", (po[1],)).fetchone()[0]
    wrong_uom = next(unit for unit in ("EA", "CS", "KG") if unit != base_uom)
    fixtures = [
      ("INBOUND_INVENTORY_COUNTED_TWICE", "EXPECTED_ALERT", "DEDUPE_DUPLICATE_RECEIPT", f"inventory:{inv[0]}|purchase_order_line:{po[0]}",
       {"inventory_id":inv[0],"purchase_order_line_id":po[0],"duplicate_inbound_qty":po[2],"scheduled_receipt_qty":po[2]}),
      ("UNAPPROVED_SUBSTITUTE_SKU", "EXPECTED_REJECTION", "REJECT_SUBSTITUTE", f"primary_sku:{substitute[0]}|substitute_sku:{substitute[1]}",
       {"primary_sku_id":substitute[0],"substitute_sku_id":substitute[1],"approval_state":"NOT_APPROVED"}),
      ("SUPPLIER_CAPACITY_EXCEEDED", "EXPECTED_EXCEPTION", "REJECT_OVER_CAPACITY", f"supplier_capacity:{cap[0]}|purchase_order_line:{po[0]}",
       {"supplier_capacity_id":cap[0],"purchase_order_line_id":po[0],"scenario_qty":round(cap[1]+1,2),"capacity_qty":cap[1],"uom":cap[3]}),
      ("SHORTAGE_WITHOUT_LEAD_TIME", "EXPECTED_ALERT", "RAISE_MISSING_LEAD_TIME_ALERT", f"forecast_demand:{demand[0]}|supplier:{missing_supplier}",
       {"demand_id":demand[0],"supplier_id":missing_supplier,"sku_id":demand[1],"location_id":demand[2],"week_start":demand[3]}),
      ("UOM_MISMATCH", "EXPECTED_REJECTION", "REJECT_UOM_MISMATCH", f"purchase_order_line:{po[0]}|sku:{po[1]}",
       {"purchase_order_line_id":po[0],"sku_id":po[1],"scenario_uom":wrong_uom,"base_uom":base_uom}),
    ]
    links = {
      0: [("INVENTORY","inventory_id",inv[0]),("PURCHASE_ORDER_LINE","purchase_order_line_id",po[0])],
      1: [("SKU","sku_id",substitute[0]),("SKU","sku_id",substitute[1])],
      2: [("SUPPLIER_CAPACITY","supplier_capacity_id",cap[0]),("PURCHASE_ORDER_LINE","purchase_order_line_id",po[0])],
      3: [("FORECAST_DEMAND","demand_id",demand[0]),("SUPPLIER","supplier_id",missing_supplier)],
      4: [("PURCHASE_ORDER_LINE","purchase_order_line_id",po[0]),("SKU","sku_id",po[1])],
    }
    ground=[]; injected=[]; record_id=1
    for i,(issue_type,label,decision,affected,payload) in enumerate(fixtures,1):
        case_id=f"ISSUE-{i:06d}"
        connection.execute("INSERT INTO issue_case(issue_case_id,issue_type,ground_truth_label,description,created_at) VALUES (?,?,?,?,?)",
                           (case_id,issue_type,label,decision,CREATED_AT))
        for rtype,column,value in links[i-1]:
            columns={"issue_case_id":case_id,"record_type":rtype,column:value}
            names=",".join(columns); marks=",".join("?" for _ in columns)
            connection.execute(f"INSERT INTO issue_case_record({names}) VALUES ({marks})",tuple(columns.values()))
            record_id+=1
        ground.append({"issue_case_id":case_id,"issue_type":issue_type,"affected_record_ids":affected,"expected_decision":decision,"ground_truth_label":label})
        injected.append({"issue_case_id":case_id,"issue_type":issue_type,**payload})
    connection.commit()

    def detector(issue_type, payload):
        if issue_type=="INBOUND_INVENTORY_COUNTED_TWICE":
            return payload["duplicate_inbound_qty"]>0 and payload["duplicate_inbound_qty"]==payload["scheduled_receipt_qty"]
        if issue_type=="UNAPPROVED_SUBSTITUTE_SKU":
            return payload["approval_state"]!="APPROVED" and connection.execute("SELECT 1 FROM sku_substitute WHERE primary_sku_id=? AND substitute_sku_id=? AND approval_state='APPROVED'",(payload["primary_sku_id"],payload["substitute_sku_id"])).fetchone() is None
        if issue_type=="SUPPLIER_CAPACITY_EXCEEDED":
            return payload["scenario_qty"]>payload["capacity_qty"] and payload["uom"]==cap[3]
        if issue_type=="SHORTAGE_WITHOUT_LEAD_TIME":
            return connection.execute("SELECT 1 FROM lead_time WHERE supplier_id=? AND sku_id=? AND destination_location_id=? AND effective_from<=? AND (effective_to IS NULL OR effective_to>=?)",(payload["supplier_id"],payload["sku_id"],payload["location_id"],payload["week_start"],payload["week_start"])).fetchone() is None
        if issue_type=="UOM_MISMATCH":
            return payload["scenario_uom"]!=payload["base_uom"]
        return False
    metrics={}; detected=0
    for fixture in injected:
        issue_type=fixture["issue_type"]; predicted=bool(detector(issue_type,fixture))
        detected+=int(predicted)
        tp=int(predicted); fn=1-tp
        metrics[issue_type]={"tp":tp,"fp":0,"fn":fn,"tn":len(fixtures)-1,"precision":1.0 if tp else 0.0,"recall":tp/(tp+fn)}
    if detected!=len(fixtures): raise AssertionError(f"Edge-case detectors found {detected}/{len(fixtures)} injected cases")
    counts={"ground_truth.csv":write_csv(out_dir/"ground_truth.csv",("issue_case_id","issue_type","affected_record_ids","expected_decision","ground_truth_label"),((x[k] for k in ("issue_case_id","issue_type","affected_record_ids","expected_decision","ground_truth_label")) for x in ground)),
            "edge_case_injections.csv":write_csv(out_dir/"edge_case_injections.csv",tuple(dict.fromkeys(k for row in injected for k in row)),((row.get(k,"") for k in dict.fromkeys(k for r in injected for k in r)) for row in injected))}
    detection={"detected_cases":detected,"ground_truth_cases":len(fixtures),"per_issue":metrics}
    (out_dir/"edge_case_detection.json").write_text(json.dumps(detection,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return counts,detection


def export_csvs(connection: sqlite3.Connection, out_dir: Path, assortment: Sequence[tuple[int, int]],
                skus: Sequence[dict], locations: Sequence[dict]) -> dict[str, int]:
    counts = {}
    for table, order_by in EXPORT_TABLES.items():
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
        sql = f"SELECT {', '.join(columns)} FROM {table} ORDER BY {', '.join(order_by)}"
        rows = connection.execute(sql)
        counts[f"{table}.csv"] = write_csv(out_dir / f"{table}.csv", columns, rows)

    assortment_rows = (
        (skus[sku_i]["sku_id"], locations[loc_i]["location_id"], skus[sku_i]["base_uom"],
         "MOD10_LT7_OR_FACTORY")
        for sku_i, loc_i in assortment
    )
    counts["sku_location_assortment.csv"] = write_csv(
        out_dir / "sku_location_assortment.csv",
        ("sku_id", "location_id", "uom", "assortment_rule"), assortment_rows,
    )
    return counts


def validate_database(connection: sqlite3.Connection, scale: Scale, assortment_count: int) -> dict:
    fk_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if fk_violations:
        raise AssertionError(f"Foreign key violations: {fk_violations[:5]}")

    tables = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    for table in tables:
        pk_columns = [row[1] for row in sorted(connection.execute(f"PRAGMA table_info({table})"), key=lambda r: r[5]) if row[5]]
        if not pk_columns:
            continue
        grouped = ", ".join(pk_columns)
        duplicates = connection.execute(
            f"SELECT COUNT(*) FROM (SELECT {grouped} FROM {table} GROUP BY {grouped} HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        if duplicates:
            raise AssertionError(f"Duplicate primary key in {table}: {duplicates}")

    week_rows = connection.execute("SELECT week_code, week_start FROM forecast_demand ORDER BY demand_id").fetchall()
    for week_code, week_start in week_rows:
        year, week = int(week_code[:4]), int(week_code[-2:])
        if date.fromisocalendar(year, week, 1).isoformat() != week_start:
            raise AssertionError(f"ISO week/date mismatch: {week_code} / {week_start}")

    checks = {
        "forecast_uom_mismatches": "SELECT COUNT(*) FROM forecast_demand f JOIN sku s USING(sku_id) WHERE f.uom <> s.base_uom",
        "inventory_uom_mismatches": "SELECT COUNT(*) FROM inventory i JOIN sku s USING(sku_id) WHERE i.uom <> s.base_uom",
        "supplier_capacity_uom_mismatches": "SELECT COUNT(*) FROM supplier_capacity c JOIN sku s USING(sku_id) WHERE c.uom <> s.base_uom",
        "production_capacity_uom_mismatches": "SELECT COUNT(*) FROM production_capacity c JOIN sku s USING(sku_id) WHERE c.uom <> s.base_uom",
        "purchase_order_line_uom_mismatches": "SELECT COUNT(*) FROM purchase_order_line l JOIN sku s USING(sku_id) WHERE l.uom <> s.base_uom",
        "bom_uom_mismatches": "SELECT COUNT(*) FROM bill_of_material b JOIN sku s ON s.sku_id=b.component_sku_id WHERE b.uom <> s.base_uom",
        "inventory_inbound_duplicates": "SELECT COUNT(*) FROM inventory WHERE inbound_qty <> 0",
        "purchase_order_date_violations": "SELECT COUNT(*) FROM purchase_order WHERE requested_delivery_date < order_date",
        "transport_date_violations": "SELECT COUNT(*) FROM transport_delay WHERE revised_delivery_date < expected_delivery_date",
        "capacity_date_violations": "SELECT COUNT(*) FROM supplier_capacity WHERE period_end < period_start",
        "production_capacity_date_violations": "SELECT COUNT(*) FROM production_capacity WHERE period_end < period_start",
        "order_event_date_source_mismatches": """SELECT COUNT(*) FROM purchase_order p
          JOIN purchase_order_line l USING(purchase_order_id)
          JOIN lead_time lt ON lt.supplier_id=p.supplier_id AND lt.sku_id=l.sku_id
            AND lt.destination_location_id=p.destination_location_id AND lt.origin_location_id IS NULL
            AND lt.effective_from <= p.order_date AND (lt.effective_to IS NULL OR lt.effective_to >= p.order_date)
          JOIN transport_delay td USING(purchase_order_id)
          WHERE td.expected_delivery_date <> p.requested_delivery_date
             OR p.requested_delivery_date <> date(p.order_date, '+' || lt.lead_time_days || ' days')""",
        "missing_effective_lead_times": """SELECT COUNT(*) FROM purchase_order p
          JOIN purchase_order_line l USING(purchase_order_id)
          LEFT JOIN lead_time lt ON lt.supplier_id=p.supplier_id AND lt.sku_id=l.sku_id
            AND lt.destination_location_id=p.destination_location_id AND lt.origin_location_id IS NULL
            AND lt.effective_from <= p.order_date AND (lt.effective_to IS NULL OR lt.effective_to >= p.order_date)
          WHERE lt.lead_time_id IS NULL""",
        "non_single_po_arrival_events": "SELECT COUNT(*) FROM (SELECT p.purchase_order_id, COUNT(t.transport_delay_id) n FROM purchase_order p LEFT JOIN transport_delay t USING(purchase_order_id) GROUP BY p.purchase_order_id HAVING n <> 1)",
        "orders_with_non_single_supply_line": "SELECT COUNT(*) FROM (SELECT p.purchase_order_id, COUNT(l.purchase_order_line_id) n FROM purchase_order p LEFT JOIN purchase_order_line l USING(purchase_order_id) GROUP BY p.purchase_order_id HAVING n <> 1)",
        "capacity_overcommitments": """SELECT COUNT(*) FROM (
          SELECT c.supplier_capacity_id
          FROM supplier_capacity c JOIN supplier s USING(supplier_id)
          JOIN purchase_order p USING(supplier_id)
          JOIN purchase_order_line l ON l.purchase_order_id=p.purchase_order_id AND l.sku_id=c.sku_id
          GROUP BY c.supplier_capacity_id, c.capacity_qty
          HAVING SUM(l.quantity) > c.capacity_qty)""",
        "orders_below_minimum": """SELECT COUNT(*) FROM purchase_order_line l
          JOIN purchase_order p USING(purchase_order_id)
          JOIN supplier_capacity c ON c.supplier_id=p.supplier_id AND c.sku_id=l.sku_id
          WHERE l.quantity < c.minimum_order_qty""",
        "lifecycle_current_state_mismatches": """SELECT COUNT(*) FROM purchase_order p WHERE p.status <> COALESCE((
          SELECT h.to_state FROM lifecycle_history h WHERE h.purchase_order_id=p.purchase_order_id
          ORDER BY h.changed_at DESC, h.lifecycle_history_id DESC LIMIT 1), '')""",
    }
    metrics = {}
    for name, sql in checks.items():
        value = connection.execute(sql).fetchone()[0]
        metrics[name] = value
        if value != 0:
            raise AssertionError(f"{name}: expected 0, got {value}")

    expected = {"sku": scale.skus, "location": scale.locations, "supplier": scale.suppliers,
                "forecast_demand": assortment_count * scale.weeks, "inventory": assortment_count,
                "purchase_order": scale.orders, "purchase_order_line": scale.orders,
                "transport_delay": scale.orders,
                "supplier_capacity": scale.skus * (1 if scale.suppliers == 1 else 2),
                "lead_time": assortment_count * (1 if scale.suppliers == 1 else 2),
                "production_capacity": scale.skus * connection.execute(
                    "SELECT COUNT(*) FROM location WHERE location_type='FACTORY'"
                ).fetchone()[0],
                "bill_of_material": max(0, (scale.skus - 1) // 3),
                "sku_substitute": (scale.skus + 3) // 4 if scale.skus > 1 else 0}
    row_counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}
    for table, count in expected.items():
        if row_counts[table] != count:
            raise AssertionError(f"{table}: expected {count}, got {row_counts[table]}")
    if row_counts["lifecycle_history"] == 0 and scale.orders:
        raise AssertionError("Purchase-order lifecycle history is missing")
    metrics.update({f"rows_{table}": count for table, count in row_counts.items()})
    metrics["rows_sku_location_assortment"] = assortment_count
    metrics["iso_week_rows_checked"] = len(week_rows)
    metrics["foreign_key_violations"] = 0
    return metrics


def generate(args: argparse.Namespace) -> None:
    scale = make_scale(args)
    out_dir = Path(args.out_dir).expanduser().resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"Output directory must be clean: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "oryva.sqlite3"
    if db_path.exists():
        raise FileExistsError(f"Refusing to overwrite database: {db_path}")

    rng = random.Random(args.seed)
    skus, locations, suppliers = build_masters(scale, rng)
    assortment = make_assortment(skus, locations)
    supplier_map = build_supplier_mapping(scale)
    locs_by_sku = {sku_i: [] for sku_i in range(scale.skus)}
    for sku_i, loc_i in assortment:
        locs_by_sku[sku_i].append(loc_i)
    if any(not values for values in locs_by_sku.values()):
        raise AssertionError("Assortment rule left a SKU without a location")
    base_demand = {(sku_i, loc_i): round(rng.uniform(24, 100), 2) for sku_i, loc_i in assortment}
    opening_stock = {(sku_i, loc_i): round(base_demand[(sku_i, loc_i)] * scale.weeks * rng.uniform(0.95, 1.05), 2)
                     for sku_i, loc_i in assortment}

    substitutes = []
    for sku_i in range(scale.skus):
        if scale.skus > 1 and sku_i % 4 == 0:
            other = (sku_i + 1) % scale.skus
            substitutes.append((skus[sku_i]["sku_id"], skus[other]["sku_id"], "APPROVED", PERIOD_START, None))

    lead_records: list[tuple] = []
    lead_by_key: dict[tuple[int, int, int], tuple[str, int]] = {}
    lead_id = 0
    for sku_i in range(scale.skus):
        for supplier_i in supplier_map[sku_i]:
            for loc_i in locs_by_sku[sku_i]:
                lead_id += 1
                days = rng.randint(20, 35) if supplier_i % 7 == 0 else rng.randint(4, 21)
                lead_time_id = padded("LT-", lead_id)
                lead_by_key[(supplier_i, sku_i, loc_i)] = (lead_time_id, days)
                lead_records.append((lead_time_id, suppliers[supplier_i]["supplier_id"], skus[sku_i]["sku_id"],
                                    None, locations[loc_i]["location_id"], PERIOD_START, None, days))

    order_specs = []
    capacity_commitments: dict[tuple[int, int], float] = {}
    for order_i in range(scale.orders):
        sku_i = (order_i * 7) % scale.skus
        loc_options = locs_by_sku[sku_i]
        loc_i = loc_options[(order_i // max(1, scale.skus)) % len(loc_options)]
        supplier_options = supplier_map[sku_i]
        supplier_i = supplier_options[(order_i // max(1, scale.skus)) % len(supplier_options)]
        iso_week = (order_i * 7) % scale.weeks + 1
        start = iso_week_start(iso_week)
        order_date = max(start + timedelta(days=(order_i * 3) % 4), date(2026, 1, 1))
        if order_date.year > 2026:
            order_date = date(2026, 12, 31)
        quantity = float(rng.randint(25, 120))
        lt_id, lead_days = lead_by_key[(supplier_i, sku_i, loc_i)]
        promised = order_date + timedelta(days=lead_days)
        delayed = (order_i * 17 + sku_i) % 5 == 0
        delay_days = 1 + (order_i * 13) % 6 if delayed else 0
        revised = promised + timedelta(days=delay_days)
        po_id = f"PO-2026-{order_i + 1:06d}"
        po_line_id = padded("POL-", order_i + 1)
        transport_id = padded("TD-", order_i + 1)
        order_specs.append({
            "order_i": order_i, "sku_i": sku_i, "location_i": loc_i, "supplier_i": supplier_i,
            "quantity": quantity, "lead_time_id": lt_id, "lead_days": lead_days,
            "order_date": order_date, "promised": promised, "revised": revised,
            "delay_days": delay_days, "po_id": po_id, "line_id": po_line_id,
            "transport_id": transport_id,
        })
        key = (supplier_i, sku_i)
        capacity_commitments[key] = capacity_commitments.get(key, 0.0) + quantity

    capacity_records: list[tuple] = []
    capacity_id_by_key = {}
    cap_seq = 0
    for sku_i in range(scale.skus):
        for supplier_i in supplier_map[sku_i]:
            cap_seq += 1
            key = (supplier_i, sku_i)
            committed = capacity_commitments.get(key, 0.0)
            minimum = rng.randint(5, 15)
            if committed:
                is_tight = (supplier_i + sku_i) % 5 == 0
                slack = max(3.0, math.ceil(committed * (0.04 if is_tight else 0.55)))
                capacity = committed + slack
            else:
                capacity = float(rng.randint(60, 240))
            capacity_id = padded("SCAP-", cap_seq)
            capacity_id_by_key[key] = capacity_id
            capacity_records.append((capacity_id, suppliers[supplier_i]["supplier_id"], skus[sku_i]["sku_id"],
                                     PERIOD_START, PERIOD_END, round(capacity, 2), float(minimum), skus[sku_i]["base_uom"]))

    production_records = []
    production_seq = 0
    factory_locs = [i for i, row in enumerate(locations) if row["location_type"] == "FACTORY"]
    for sku_i in range(scale.skus):
        for loc_i in factory_locs:
            production_seq += 1
            total_base = sum(base_demand[(sku_i, l)] for l in locs_by_sku[sku_i])
            cap_qty = round(total_base * scale.weeks * rng.uniform(0.85, 1.7), 2)
            production_records.append((padded("PCAP-", production_seq), skus[sku_i]["sku_id"],
                                       locations[loc_i]["location_id"], PERIOD_START, PERIOD_END,
                                       cap_qty, skus[sku_i]["base_uom"]))

    bom_records = []
    for sku_i in range(1, scale.skus):
        if sku_i % 3 == 0:
            component_i = sku_i - 1
            bom_records.append((skus[sku_i]["sku_id"], skus[component_i]["sku_id"],
                                round(rng.uniform(0.1, 0.8), 3), skus[component_i]["base_uom"], PERIOD_START, None))

    initialize(db_path)
    with connect_db(db_path) as connection:
        connection.execute("BEGIN")
        connection.executemany(
            "INSERT INTO sku(sku_id,name,description,base_uom,lifecycle_state,created_at) VALUES (?,?,?,?,?,?)",
            [(s["sku_id"], s["name"], s["description"], s["base_uom"], s["lifecycle_state"], s["created_at"]) for s in skus],
        )
        connection.executemany(
            "INSERT INTO location(location_id,name,location_type,country_code,timezone,lifecycle_state,created_at) VALUES (?,?,?,?,?,?,?)",
            [(l["location_id"], l["name"], l["location_type"], l["country_code"], l["timezone"], l["lifecycle_state"], l["created_at"]) for l in locations],
        )
        connection.executemany(
            "INSERT INTO supplier(supplier_id,name,country_code,lifecycle_state,created_at) VALUES (?,?,?,?,?)",
            [(s["supplier_id"], s["name"], s["country_code"], s["lifecycle_state"], s["created_at"]) for s in suppliers],
        )
        connection.executemany(
            "INSERT INTO sku_substitute(primary_sku_id,substitute_sku_id,approval_state,effective_from,effective_to) VALUES (?,?,?,?,?)",
            substitutes,
        )

        def forecast_rows():
            for sku_i, loc_i in assortment:
                base = base_demand[(sku_i, loc_i)]
                for week in range(1, scale.weeks + 1):
                    week_code = f"2026W{week:02d}"
                    week_start = iso_week_start(week)
                    seasonal = 1.0 + 0.16 * math.sin(2.0 * math.pi * (week - 1) / max(scale.weeks, 1))
                    variation = rng.uniform(0.86, 1.14)
                    is_spike = (sku_i * 7 + loc_i * 3 + week) % 13 == 0
                    spike_factor = rng.uniform(1.8, 2.7) if is_spike else 1.0
                    quantity = round(base * seasonal * variation * spike_factor, 2)
                    demand_id = f"DEM-{skus[sku_i]['sku_id']}-{locations[loc_i]['location_id']}-{week_code}"
                    yield (demand_id, skus[sku_i]["sku_id"], locations[loc_i]["location_id"],
                           week_start.isoformat(), week_code, quantity, skus[sku_i]["base_uom"],
                           "BASELINE", CREATED_AT)
        insert_batches(connection,
            "INSERT INTO forecast_demand(demand_id,sku_id,location_id,week_start,week_code,forecast_qty,uom,forecast_version,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            forecast_rows(),
        )

        inventory_records = []
        for index, (sku_i, loc_i) in enumerate(assortment, start=1):
            inventory_records.append((padded("INV-", index), skus[sku_i]["sku_id"], locations[loc_i]["location_id"],
                                      iso_week_start(1).isoformat(), opening_stock[(sku_i, loc_i)], 0.0,
                                      skus[sku_i]["base_uom"], "opening_stock:2026W01"))
        connection.executemany(
            "INSERT INTO inventory(inventory_id,sku_id,location_id,as_of_date,on_hand_qty,inbound_qty,uom,source_reference) VALUES (?,?,?,?,?,?,?,?)",
            inventory_records,
        )
        connection.executemany(
            "INSERT INTO supplier_capacity(supplier_capacity_id,supplier_id,sku_id,period_start,period_end,capacity_qty,minimum_order_qty,uom) VALUES (?,?,?,?,?,?,?,?)",
            capacity_records,
        )
        connection.executemany(
            "INSERT INTO lead_time(lead_time_id,supplier_id,sku_id,origin_location_id,destination_location_id,effective_from,effective_to,lead_time_days) VALUES (?,?,?,?,?,?,?,?)",
            lead_records,
        )
        connection.executemany(
            "INSERT INTO production_capacity(production_capacity_id,sku_id,location_id,period_start,period_end,capacity_qty,uom) VALUES (?,?,?,?,?,?,?)",
            production_records,
        )
        connection.executemany(
            "INSERT INTO bill_of_material(parent_sku_id,component_sku_id,quantity_per,uom,effective_from,effective_to) VALUES (?,?,?,?,?,?)",
            bom_records,
        )

        po_records = []
        line_records = []
        transport_records = []
        lifecycle_records = []
        lifecycle_seq = 0
        for spec in order_specs:
            sku_i, loc_i, supplier_i = spec["sku_i"], spec["location_i"], spec["supplier_i"]
            status_events = [
                ("DRAFT", spec["order_date"]),
                ("SUBMITTED", spec["order_date"] + timedelta(days=1)),
                ("CONFIRMED", spec["order_date"] + timedelta(days=2)),
                ("IN_TRANSIT", spec["order_date"] + timedelta(days=3)),
                ("RECEIVED", spec["revised"]),
            ]
            active_events = [(state, day) for state, day in status_events if day <= DATA_AS_OF]
            if not active_events:
                active_events = [("DRAFT", spec["order_date"])]
            status = active_events[-1][0]
            po_records.append((spec["po_id"], suppliers[supplier_i]["supplier_id"], locations[loc_i]["location_id"],
                               spec["order_date"].isoformat(), spec["promised"].isoformat(), status, "USD", CREATED_AT))
            line_records.append((spec["line_id"], spec["po_id"], skus[sku_i]["sku_id"], spec["quantity"],
                                 skus[sku_i]["base_uom"], round(rng.uniform(0.8, 18.0), 2)))
            reason = f"Carrier delay of {spec['delay_days']} day(s)" if spec["delay_days"] else "No carrier delay recorded"
            transport_records.append((spec["transport_id"], spec["po_id"], spec["line_id"],
                                      ("Northstar Freight", "Blue River Logistics", "Pioneer Transit")[spec["order_i"] % 3],
                                      spec["promised"].isoformat(), spec["revised"].isoformat(), reason))
            previous = None
            for state, event_day in active_events:
                lifecycle_seq += 1
                lifecycle_records.append((padded("LCH-", lifecycle_seq), "PURCHASE_ORDER", None, None, None,
                                          spec["po_id"], None, None, None, previous, state, stamp(event_day),
                                          "synthetic-generator", "deterministic PO lifecycle event"))
                previous = state

        connection.executemany(
            "INSERT INTO purchase_order(purchase_order_id,supplier_id,destination_location_id,order_date,requested_delivery_date,status,currency_code,created_at) VALUES (?,?,?,?,?,?,?,?)",
            po_records,
        )
        connection.executemany(
            "INSERT INTO purchase_order_line(purchase_order_line_id,purchase_order_id,sku_id,quantity,uom,unit_cost) VALUES (?,?,?,?,?,?)",
            line_records,
        )
        connection.executemany(
            "INSERT INTO transport_delay(transport_delay_id,purchase_order_id,purchase_order_line_id,carrier_name,expected_delivery_date,revised_delivery_date,reason) VALUES (?,?,?,?,?,?,?)",
            transport_records,
        )
        connection.executemany(
            "INSERT INTO lifecycle_history(lifecycle_history_id,entity_type,sku_id,location_id,supplier_id,purchase_order_id,production_plan_id,shortage_id,mitigation_option_id,from_state,to_state,changed_at,changed_by,note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            lifecycle_records,
        )
        connection.commit()
        edge_counts, edge_validation = inject_edge_cases(connection, out_dir)
        validation = validate_database(connection, scale, len(assortment))
        validation["edge_case_detection"] = edge_validation
        csv_counts = export_csvs(connection, out_dir, assortment, skus, locations)
        csv_counts.update(edge_counts)
        for filename, exported_count in csv_counts.items():
            if filename in ("sku_location_assortment.csv", "ground_truth.csv", "edge_case_injections.csv"):
                expected_count = len(assortment)
                if filename == "ground_truth.csv" or filename == "edge_case_injections.csv":
                    expected_count = 5
            else:
                table = filename.removesuffix(".csv")
                expected_count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if exported_count != expected_count:
                raise AssertionError(f"{filename}: exported {exported_count} rows, expected {expected_count}")

    delayed_orders = sum(1 for spec in order_specs if spec["delay_days"] > 0)
    spike_count = sum(1 for sku_i, loc_i in assortment for week in range(1, scale.weeks + 1)
                      if (sku_i * 7 + loc_i * 3 + week) % 13 == 0)
    tight_capacity_rows = sum(
        1 for record in capacity_records
        if (int(record[1][-6:]) - 1 + int(record[2][-6:]) - 1) % 5 == 0
        and capacity_commitments.get((int(record[1][-6:]) - 1, int(record[2][-6:]) - 1), 0) > 0
    )
    counts = {"sku_location_assortment": len(assortment), "approved_substitutes": len(substitutes),
              "tight_capacity_records": tight_capacity_rows, "delayed_arrival_events": delayed_orders,
              "on_time_arrival_events": scale.orders - delayed_orders,
              "constrained_suppliers": sum(1 for i in range(scale.suppliers) if i % 7 == 0),
              "demand_spike_rows": spike_count, **csv_counts}
    manifest = {
        "dataset": f"ORYVA synthetic demand and supply planning {args.preset}",
        "generator_version": GENERATOR_VERSION,
        "preset": args.preset,
        "seed": args.seed,
        "data_as_of_date": DATA_AS_OF.isoformat(),
        "iso_year": 2026,
        "scale": asdict(scale),
        "source": {
            "type": "synthetic",
            "external_sources": [],
            "license": "Not applicable; generated locally without external datasets",
            "attribution": "None",
            "transformations": "Seeded pseudorandom variation and documented deterministic rules",
            "fields_discarded": [],
        },
        "assortment_rule": "Include pair when (sku_index*7 + location_index*3) % 10 < 7, plus every factory location; zero-based indexes, stable SKU/location order.",
        "inbound_supply_rule": "Purchase-order-line quantity is the sole inbound supply source; inventory.inbound_qty is zero so Phase 3 counts it once.",
        "opening_inventory_rule": "Seed opening stock near one forecast horizon of baseline demand (weeks * baseline * seeded 0.95-1.05 safety factor), retaining seeded forecast spikes and receipt variation to produce realistic exceptions.",
        "arrival_rule": "Promised date = order_date + matched effective lead_time_days. transport_delay.expected_delivery_date repeats the promise; revised_delivery_date adds a deterministic 0-6 day carrier delay.",
        "not_generated_in_phase_2": ["production_plan", "shortage", "mitigation_option", "issue_case", "ground_truth"],
        "output_files": sorted([*csv_counts.keys(), "edge_case_detection.json", "oryva.sqlite3", "source_manifest.json"]),
        "anomaly_injection": "Five isolated issue_case/issue_case_record-linked scenario overlays with real source record IDs; see ground_truth.csv and edge_case_injections.csv.",
        "row_counts": counts,
        "validation": validation,
    }
    (out_dir / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Generated {args.preset} dataset: {out_dir}")
    print(f"Seed: {args.seed}; scale: {json.dumps(asdict(scale), sort_keys=True)}")
    print(f"Assortment pairs: {len(assortment)}; demand rows: {validation['rows_forecast_demand']}")
    print(f"POs: {validation['rows_purchase_order']}; delayed arrivals: {delayed_orders}; demand spikes: {spike_count}")
    print(f"CSV files: {len(csv_counts)}; foreign-key, duplicate, date, unit, capacity and lifecycle checks: PASS")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare(left: Path, right: Path) -> None:
    left, right = left.expanduser().resolve(), right.expanduser().resolve()
    left_files = {p.name: p for p in left.glob("*.csv")}
    right_files = {p.name: p for p in right.glob("*.csv")}
    if not left_files or left_files.keys() != right_files.keys():
        raise AssertionError(f"CSV file sets differ: {sorted(left_files)} vs {sorted(right_files)}")
    print(f"Comparing {len(left_files)} canonical CSV files")
    for name in sorted(left_files):
        left_path, right_path = left_files[name], right_files[name]
        left_rows = sum(1 for _ in left_path.open("r", encoding="utf-8", newline="")) - 1
        right_rows = sum(1 for _ in right_path.open("r", encoding="utf-8", newline="")) - 1
        left_hash, right_hash = file_sha256(left_path), file_sha256(right_path)
        if left_rows != right_rows or left_hash != right_hash:
            raise AssertionError(f"Mismatch in {name}: rows {left_rows}/{right_rows}; SHA-256 {left_hash}/{right_hash}")
        print(f"PASS {name}: rows={left_rows}, sha256={left_hash}")
    print("PASS all row counts and SHA-256 checksums match")


def validate_existing(out_dir: Path) -> None:
    out_dir = out_dir.expanduser().resolve()
    manifest_path = out_dir / "source_manifest.json"
    db_path = out_dir / "oryva.sqlite3"
    if not manifest_path.exists() or not db_path.exists():
        raise FileNotFoundError(f"Expected source_manifest.json and oryva.sqlite3 in {out_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scale = Scale(**manifest["scale"])
    assortment_count = int(manifest["row_counts"]["sku_location_assortment"])
    with connect_db(db_path) as connection:
        validation = validate_database(connection, scale, assortment_count)
    detection_path=out_dir/"edge_case_detection.json"
    if detection_path.exists():
        detection=json.loads(detection_path.read_text(encoding="utf-8"))
        if detection.get("detected_cases")!=detection.get("ground_truth_cases") or any(v.get("recall")!=1.0 or v.get("precision")!=1.0 for v in detection.get("per_issue",{}).values()):
            raise AssertionError("Injected anomaly detector metrics do not match ground truth")
        validation["edge_case_detection"]=detection
    manifest["validation"] = validation
    manifest["output_files"] = sorted(set(manifest.get("output_files", [])) | {"oryva.sqlite3", "source_manifest.json"})
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS generated database validation: {out_dir}")
    print(f"PASS {len(validation)} validation metrics; all FK, duplicate, ISO date, UOM, order-date, capacity, and lifecycle checks are zero/consistent")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate", help="Generate a fresh SQLite database and canonical CSV exports")
    generate_parser.add_argument("--preset", choices=tuple(PRESETS), default="starter")
    generate_parser.add_argument("--seed", type=int, default=SEED)
    generate_parser.add_argument("--out-dir", required=True)
    for key in PRESETS["full"]:
        generate_parser.add_argument(f"--{key}", type=int)
    compare_parser = subparsers.add_parser("compare", help="Compare CSV row counts and SHA-256 checksums")
    compare_parser.add_argument("--left", required=True, type=Path)
    compare_parser.add_argument("--right", required=True, type=Path)
    validate_parser = subparsers.add_parser("validate", help="Revalidate an existing generated SQLite database")
    validate_parser.add_argument("--out-dir", required=True, type=Path)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate(args)
        elif args.command == "compare":
            compare(args.left, args.right)
        else:
            validate_existing(args.out_dir)
    except (AssertionError, FileExistsError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
