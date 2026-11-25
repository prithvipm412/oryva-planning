# Phase 1 data dictionary

## Conventions

- SQLite `TEXT` stores identifiers, ISO dates (`YYYY-MM-DD`), and UTC timestamps (`YYYY-MM-DDTHH:MM:SS.sssZ`); `REAL` stores quantities/costs; `INTEGER` stores day counts.
- Required means `NOT NULL` or part of a primary key. Optional means nullable. For text fields, “non-empty” means trimmed length greater than zero where constrained.
- Quantities use each row's `uom`; the schema does not convert units. Cost currency is the purchase order's ISO 4217-style three-letter uppercase code.
- All IDs are text primary keys unless marked as a composite key. IDs are immutable for the main referenced entities. SQL `GLOB` checks enforce zero-padded shapes.
- Assignment IDs exactly: SKU `SKU-000001`; demand `DEM-<sku>-<location>-2026W01`; PO `PO-2026-000001`; shortage `SHORT-2026-000001`; mitigation `MIT-<shortage-id>-01`. In this schema, `<sku>` and `<location>` are full IDs, e.g. `SKU-000001` and `LOC-000001`, yielding `DEM-SKU-000001-LOC-000001-2026W01`. SKU/location/supplier dimensions use `SKU-`, `LOC-`, `SUP-` plus six digits. Other surrogate keys use their table prefix plus ten digits where constrained.
- Date ranges are inclusive by convention. A nullable `effective_to` means no known end date. End dates cannot precede starts.
- Relationships: `NOT NULL` FKs are mandatory; nullable FKs are optional. One parent to many child rows unless noted. Bridge tables implement N:M relations.
- Lifecycle history holds events; it does not overwrite the row's current state. `entity_type` plus its matching FK is checked so lifecycle links remain referentially valid.

## `sku` — SKU

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| sku_id | TEXT | Yes | `SKU-` + six digits | PK | Shape checked; immutable |
| name | TEXT | Yes | Non-empty label | No | Trimmed length > 0 |
| description | TEXT | No | Free text | No | None |
| base_uom | TEXT | Yes | Unit code/name | No | Non-empty |
| lifecycle_state | TEXT | Yes | DRAFT, ACTIVE, DISCONTINUED | No | Enum CHECK |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

## `location` — Location

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| location_id | TEXT | Yes | `LOC-` + six digits | PK | Shape checked; immutable |
| name | TEXT | Yes | Non-empty label | No | Trimmed length > 0 |
| location_type | TEXT | Yes | WAREHOUSE, STORE, FACTORY, DISTRIBUTION_CENTER | No | Enum CHECK |
| country_code | TEXT | Yes | Uppercase 2-letter country code | No | Two uppercase ASCII letters |
| timezone | TEXT | Yes | IANA timezone name | No | Non-null; IANA membership is app validation |
| lifecycle_state | TEXT | Yes | ACTIVE, INACTIVE | No | Enum CHECK |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

## `forecast_demand` — ForecastDemand

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| demand_id | TEXT | Yes | `DEM-<sku-id>-<location-id>-YYYYWww` (brief example year 2026) | PK | Shape plus equality to referenced sku/location/week_code |
| sku_id | TEXT | Yes | Existing SKU ID | No | FK to `sku` |
| location_id | TEXT | Yes | Existing location ID | No | FK to `location` |
| week_start | TEXT | Yes | ISO date; week start day is Monday by convention | No | SQLite date parse and canonical ISO check |
| week_code | TEXT | Yes | `YYYYW01`–`YYYYW53` | Composite with sku/location/version | Shape and week number range |
| forecast_qty | REAL | Yes | `uom` units | No | >= 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty; consistency with SKU is a Phase 2 validation |
| forecast_version | TEXT | Yes | Version label; default BASELINE | No | Default; future app-level controlled vocabulary |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

Unique: `(sku_id, location_id, week_code, forecast_version)`. Relationship: SKU 1:N demand and Location 1:N demand.

## `inventory` — Inventory

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| inventory_id | TEXT | Yes | `INV-` + ten digits | PK | Shape checked |
| sku_id | TEXT | Yes | Existing SKU ID | No | FK to `sku` |
| location_id | TEXT | Yes | Existing location ID | No | FK to `location` |
| as_of_date | TEXT | Yes | ISO date | Composite | Canonical ISO date |
| on_hand_qty | REAL | Yes | `uom` units | No | >= 0 |
| inbound_qty | REAL | Yes | `uom` units; default 0 | No | >= 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |
| source_reference | TEXT | No | Source record/reference | No | None |

Unique: `(sku_id, location_id, as_of_date)`. Relationships: SKU 1:N inventory and Location 1:N inventory.

## `supplier` — Supplier

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| supplier_id | TEXT | Yes | `SUP-` + six digits | PK | Shape checked; immutable |
| name | TEXT | Yes | Non-empty label | No | Trimmed length > 0 |
| country_code | TEXT | No | Uppercase 2-letter country code | No | Two uppercase ASCII letters if present |
| lifecycle_state | TEXT | Yes | ACTIVE, ON_HOLD, INACTIVE | No | Enum CHECK |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

## `supplier_capacity` — SupplierCapacity

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| supplier_capacity_id | TEXT | Yes | `SCAP-` + ten digits | PK | Shape checked |
| supplier_id | TEXT | Yes | Existing supplier | No | FK to `supplier` |
| sku_id | TEXT | Yes | Existing SKU | No | FK to `sku` |
| period_start | TEXT | Yes | ISO date | Composite | Canonical ISO date |
| period_end | TEXT | Yes | ISO date | Composite | Canonical date; >= start |
| capacity_qty | REAL | Yes | `uom` units per period | No | >= 0 |
| minimum_order_qty | REAL | Yes | `uom` units; default 0 | No | 0 <= minimum <= capacity |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |

Unique: `(supplier_id, sku_id, period_start, period_end)`. A Supplier/SKU pair can have multiple non-overlapping effective capacity periods; overlap detection is app validation.

## `lead_time` — LeadTime

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| lead_time_id | TEXT | Yes | `LT-` + ten digits | PK | Shape checked |
| supplier_id | TEXT | Yes | Existing supplier | No | FK to `supplier` |
| sku_id | TEXT | Yes | Existing SKU | No | FK to `sku` |
| origin_location_id | TEXT | No | Existing location | No | Optional FK to `location` |
| destination_location_id | TEXT | Yes | Existing location | No | FK to `location` |
| effective_from | TEXT | Yes | ISO date | Composite | Canonical date |
| effective_to | TEXT | No | ISO date or open-ended | No | Canonical date; >= start |
| lead_time_days | INTEGER | Yes | Calendar days | No | >= 0 |

Unique: supplier, SKU, origin, destination and effective-from date. Nullable origin allows source routes without a modeled origin.

## `purchase_order` — PurchaseOrder

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| purchase_order_id | TEXT | Yes | `PO-YYYY-` + six digits; brief example `PO-2026-000001` | PK | Shape checked; immutable |
| supplier_id | TEXT | Yes | Existing supplier | No | FK to `supplier` |
| destination_location_id | TEXT | Yes | Existing location | No | FK to `location` |
| order_date | TEXT | Yes | ISO date | No | Canonical date |
| requested_delivery_date | TEXT | Yes | ISO date | No | Canonical date; >= order date |
| status | TEXT | Yes | DRAFT, SUBMITTED, CONFIRMED, IN_TRANSIT, RECEIVED, CANCELLED | No | Enum CHECK; history in lifecycle table |
| currency_code | TEXT | Yes | Three uppercase letters | No | ISO 4217 membership is app validation |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

Supplier and Location are each 1:N PurchaseOrder. PurchaseOrder has 1:N lines.

## `production_plan` — ProductionPlan

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| production_plan_id | TEXT | Yes | `PP-` + ten digits | PK | Shape checked |
| sku_id | TEXT | Yes | Existing SKU | No | FK to `sku` |
| location_id | TEXT | Yes | Existing production location | No | FK to `location` |
| planned_start_date | TEXT | Yes | ISO date | No | Canonical date |
| planned_end_date | TEXT | Yes | ISO date | No | Canonical date; >= start |
| planned_qty | REAL | Yes | `uom` units | No | > 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |
| status | TEXT | Yes | DRAFT, RELEASED, IN_PROGRESS, COMPLETED, CANCELLED | No | Enum CHECK; history in lifecycle table |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

## `shortage` — Shortage

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| shortage_id | TEXT | Yes | `SHORT-YYYY-` + six digits; brief example `SHORT-2026-000001` | PK | Shape checked; immutable |
| sku_id | TEXT | Yes | Existing SKU | No | FK to `sku` |
| location_id | TEXT | Yes | Existing location | No | FK to `location` |
| week_start | TEXT | Yes | ISO date | No | Canonical date |
| demand_id | TEXT | No | Associated demand row | No | Optional FK to `forecast_demand` |
| shortage_qty | REAL | Yes | `uom` units | No | > 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |
| cause_summary | TEXT | Yes | Explainable cause text | No | Non-empty |
| status | TEXT | Yes | OPEN, MITIGATED, ACCEPTED, CLOSED | No | Enum CHECK; history in lifecycle table |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

SKU and Location each 1:N Shortage; demand may relate to zero or multiple shortage records (optional 1:N).

## `mitigation_option` — MitigationOption

| Field | SQLite type | Required | Allowed values / units | Unique | Validation |
|---|---|---|---|---|---|
| mitigation_option_id | TEXT | Yes | `MIT-<shortage-id>-NN`; brief example `MIT-SHORT-2026-000001-01` | PK | Matches its shortage ID and two-digit suffix |
| shortage_id | TEXT | Yes | Existing shortage | No | FK to `shortage` |
| option_type | TEXT | Yes | EXPEDITE, ALTERNATE_SUPPLIER, SUBSTITUTE_SKU, TRANSFER, OVERTIME, DEMAND_ALLOCATION | No | Enum CHECK |
| status | TEXT | Yes | PROPOSED, SELECTED, REJECTED, EXECUTED, EXPIRED | No | Enum CHECK; history in lifecycle table |
| mitigation_qty | REAL | Yes | `uom` units | No | > 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |
| incremental_cost | REAL | No | PO currency amount | No | >= 0 if present |
| service_impact_qty | REAL | No | Units of service impact | No | >= 0 if present |
| supplier_id | TEXT | No | Supplier involved in option | No | Optional FK to `supplier` |
| substitute_sku_id | TEXT | No | Substitute SKU involved | No | Optional FK to `sku`; approval/effectivity is business validation |
| source_location_id | TEXT | No | Transfer source | No | Optional FK to `location` |
| target_location_id | TEXT | No | Transfer target | No | Optional FK to `location` |
| resulting_delivery_date | TEXT | No | ISO date | No | Canonical date if present |
| rationale | TEXT | Yes | Explainable rationale | No | Non-empty |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC timestamp |

Shortage 1:N MitigationOption. Option resource links are optional and depend on `option_type`.

## Supporting tables

### `edge_case_injections.csv` and `ground_truth.csv`

These synthetic scenario overlays reference real source rows and are excluded from planner features. `edge_case_injections.csv` carries the `issue_case_id`, `issue_type`, affected record IDs, and scenario-specific values used by the validator. `ground_truth.csv` contains `issue_case_id`, `issue_type`, `affected_record_ids`, `expected_decision`, and `ground_truth_label`; the planner never reads this file. `edge_case_detection.json` stores per-issue TP/FP/FN/TN counts and precision/recall.

The following field tables enumerate every column of the supporting tables.

### `sku_substitute`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| primary_sku_id | TEXT | Yes | SKU ID | Composite PK/FK | FK to sku; not same as substitute |
| substitute_sku_id | TEXT | Yes | SKU ID | Composite PK/FK | FK to sku; not same as primary |
| approval_state | TEXT | Yes | PENDING, APPROVED, REJECTED, REVOKED | No | Enum CHECK |
| effective_from | TEXT | Yes | ISO date | Composite PK | Canonical date |
| effective_to | TEXT | No | ISO date or open-ended | No | Canonical date; >= effective_from |

Composite PK `(primary_sku_id, substitute_sku_id, effective_from)`; temporal SKU-to-SKU N:M bridge.

### `production_capacity`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| production_capacity_id | TEXT | Yes | `PCAP-` plus ten digits | PK | Shape check |
| sku_id | TEXT | Yes | SKU ID | No | FK to sku |
| location_id | TEXT | Yes | Location ID | No | FK to location |
| period_start | TEXT | Yes | ISO date | Composite | Canonical date |
| period_end | TEXT | Yes | ISO date | Composite | Canonical date; >= period_start |
| capacity_qty | REAL | Yes | UOM units per period | No | >= 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |

Unique `(sku_id, location_id, period_start, period_end)`.

### `bill_of_material`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| parent_sku_id | TEXT | Yes | Parent SKU ID | Composite PK/FK | FK to sku; not same as component |
| component_sku_id | TEXT | Yes | Component SKU ID | Composite PK/FK | FK to sku; not same as parent |
| quantity_per | REAL | Yes | Component UOM per parent unit | No | > 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |
| effective_from | TEXT | Yes | ISO date | Composite PK | Canonical date |
| effective_to | TEXT | No | ISO date or open-ended | No | Canonical date; >= effective_from |

Composite PK `(parent_sku_id, component_sku_id, effective_from)`; effective-dated SKU-to-SKU N:M bridge.

### `purchase_order_line`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| purchase_order_line_id | TEXT | Yes | `POL-` plus ten digits | PK | Shape check |
| purchase_order_id | TEXT | Yes | PO ID | No | FK to purchase_order; cascades on PO deletion |
| sku_id | TEXT | Yes | SKU ID | No | FK to sku |
| quantity | REAL | Yes | UOM units | No | > 0 |
| uom | TEXT | Yes | Unit code/name | No | Non-empty |
| unit_cost | REAL | No | PO currency per unit | No | >= 0 if present |

Unique `(purchase_order_id, sku_id)`; resolves PurchaseOrder-to-SKU N:M.

### `transport_delay`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| transport_delay_id | TEXT | Yes | `TD-` plus ten digits | PK | Shape check |
| purchase_order_id | TEXT | Yes | PO ID | No | FK to purchase_order |
| purchase_order_line_id | TEXT | No | PO line ID | No | Optional FK to purchase_order_line |
| carrier_name | TEXT | No | Carrier name | No | None |
| expected_delivery_date | TEXT | Yes | ISO date | No | Canonical date |
| revised_delivery_date | TEXT | Yes | ISO date | No | Canonical date; >= expected date |
| reason | TEXT | No | Free text | No | None |

PurchaseOrder 1:N delay events; line reference is optional for order-wide delays.

### `lifecycle_history`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| lifecycle_history_id | TEXT | Yes | `LCH-` plus ten digits | PK | Shape check |
| entity_type | TEXT | Yes | SKU, LOCATION, SUPPLIER, PURCHASE_ORDER, PRODUCTION_PLAN, SHORTAGE, MITIGATION_OPTION | No | Enum CHECK |
| sku_id | TEXT | Conditional | SKU ID | No | FK; required only for SKU entity |
| location_id | TEXT | Conditional | Location ID | No | FK; required only for LOCATION entity |
| supplier_id | TEXT | Conditional | Supplier ID | No | FK; required only for SUPPLIER entity |
| purchase_order_id | TEXT | Conditional | PO ID | No | FK; required only for PURCHASE_ORDER entity |
| production_plan_id | TEXT | Conditional | Production plan ID | No | FK; required only for PRODUCTION_PLAN entity |
| shortage_id | TEXT | Conditional | Shortage ID | No | FK; required only for SHORTAGE entity |
| mitigation_option_id | TEXT | Conditional | Mitigation ID | No | FK; required only for MITIGATION_OPTION entity |
| from_state | TEXT | No | Prior state | No | If set, differs from to_state |
| to_state | TEXT | Yes | Entity's lifecycle state | No | Non-null; entity-specific enum checked by application |
| changed_at | TEXT | Yes | UTC timestamp | No | Default current UTC |
| changed_by | TEXT | Yes | Actor label | No | Default `system` |
| note | TEXT | No | Free text | No | None |

The table CHECK requires exactly one entity FK matching entity_type. Each event belongs to one entity; each entity may have zero or many events.

### `issue_case`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| issue_case_id | TEXT | Yes | `ISSUE-` plus six digits | PK | Shape check |
| issue_type | TEXT | Yes | INBOUND_INVENTORY_COUNTED_TWICE, UNAPPROVED_SUBSTITUTE_SKU, SUPPLIER_CAPACITY_EXCEEDED, SHORTAGE_WITHOUT_LEAD_TIME, UOM_MISMATCH | No | Enum CHECK |
| ground_truth_label | TEXT | Yes | EXPECTED_EXCEPTION, EXPECTED_ALERT, EXPECTED_REJECTION | No | Enum CHECK |
| description | TEXT | Yes | Traceable explanation | No | Non-empty |
| created_at | TEXT | Yes | UTC timestamp | No | Default current UTC |

### `issue_case_record`

| Field | Type | Required | Values / units | Unique | Validation |
|---|---|---|---|---|---|
| issue_case_record_id | INTEGER | Yes | SQLite row identifier | PK | Auto-assigned |
| issue_case_id | TEXT | Yes | Issue case ID | No | FK to issue_case; cascade delete |
| record_type | TEXT | Yes | SKU, LOCATION, FORECAST_DEMAND, INVENTORY, SUPPLIER, SUPPLIER_CAPACITY, LEAD_TIME, PURCHASE_ORDER, PURCHASE_ORDER_LINE, PRODUCTION_PLAN, SHORTAGE, MITIGATION_OPTION | No | Enum CHECK |
| sku_id | TEXT | Conditional | SKU ID | No | FK; only non-null for SKU |
| location_id | TEXT | Conditional | Location ID | No | FK; only non-null for LOCATION |
| demand_id | TEXT | Conditional | Demand ID | No | FK; only non-null for FORECAST_DEMAND |
| inventory_id | TEXT | Conditional | Inventory ID | No | FK; only non-null for INVENTORY |
| supplier_id | TEXT | Conditional | Supplier ID | No | FK; only non-null for SUPPLIER |
| supplier_capacity_id | TEXT | Conditional | Capacity ID | No | FK; only non-null for SUPPLIER_CAPACITY |
| lead_time_id | TEXT | Conditional | Lead-time ID | No | FK; only non-null for LEAD_TIME |
| purchase_order_id | TEXT | Conditional | PO ID | No | FK; only non-null for PURCHASE_ORDER |
| purchase_order_line_id | TEXT | Conditional | PO line ID | No | FK; only non-null for PURCHASE_ORDER_LINE |
| production_plan_id | TEXT | Conditional | Production-plan ID | No | FK; only non-null for PRODUCTION_PLAN |
| shortage_id | TEXT | Conditional | Shortage ID | No | FK; only non-null for SHORTAGE |
| mitigation_option_id | TEXT | Conditional | Mitigation ID | No | FK; only non-null for MITIGATION_OPTION |

Exactly one entity FK must be set and match record_type. An expression unique index rejects duplicate case/record links. IssueCase-to-source-record is N:M through this bridge.

## Cardinality and optional relationships

- SKU 1:N ForecastDemand, Inventory, SupplierCapacity, LeadTime, ProductionCapacity, ProductionPlan, Shortage, PurchaseOrderLine, and BOM parent/component rows.
- Location 1:N ForecastDemand, Inventory, LeadTime destination, ProductionCapacity, ProductionPlan, PurchaseOrder destination, Shortage, and optional MitigationOption transfer endpoints.
- Supplier 1:N SupplierCapacity, LeadTime, PurchaseOrder, and optional MitigationOption.
- ForecastDemand optionally relates 1:N to Shortage. Shortage 1:N MitigationOption.
- PurchaseOrder 1:N PurchaseOrderLine and 1:N TransportDelay; PurchaseOrderLine optionally relates 1:N TransportDelay.
- SKU↔SKU substitutions use `sku_substitute` (N:M, effective-dated). SKU↔SKU BOM uses `bill_of_material` (N:M, effective-dated). PurchaseOrder↔SKU uses `purchase_order_line` (N:M).
- LifecycleHistory rows each refer to exactly one lifecycle-bearing entity via the FK matching `entity_type`. IssueCase↔business records is N:M through `issue_case_record`.

## Lifecycle states

`sku`: DRAFT→ACTIVE→DISCONTINUED by documented business rules; `location`: ACTIVE→INACTIVE; `supplier`: ACTIVE↔ON_HOLD and then INACTIVE; `purchase_order`: DRAFT→SUBMITTED→CONFIRMED→IN_TRANSIT→RECEIVED, with cancellation permitted before receipt; `production_plan`: DRAFT→RELEASED→IN_PROGRESS→COMPLETED, or CANCELLED before completion; `shortage`: OPEN→MITIGATED/ACCEPTED→CLOSED; `mitigation_option`: PROPOSED→SELECTED/REJECTED/EXPIRED→EXECUTED only when selected. Phase 1 constrains state values and stores history, but transition graph validation is planned with Phase 2 data validation.

## Database-enforced versus application validation

SQLite enforces primary/foreign keys, ID shapes for the assignment's named IDs, enum values, non-negative quantities/costs, unique business keys, canonical ISO date strings, and end-date ordering. Week codes are constrained to week numbers 01–53; ISO year/week agreement with `week_start`, actual IANA timezone/currency codes, UOM equivalence, overlapping effective date ranges, lead-time completeness for shortage explanations, capacity consumption across multiple orders, and permitted lifecycle transition sequences require application-level validation in later phases.
