-- ORYVA Phase 1 relational schema. Applied by db.py with foreign keys enabled.
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS sku (
    sku_id TEXT PRIMARY KEY CHECK (sku_id GLOB 'SKU-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT,
    base_uom TEXT NOT NULL CHECK (length(trim(base_uom)) > 0),
    lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (lifecycle_state IN ('DRAFT','ACTIVE','DISCONTINUED')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS location (
    location_id TEXT PRIMARY KEY CHECK (location_id GLOB 'LOC-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    location_type TEXT NOT NULL CHECK (location_type IN ('WAREHOUSE','STORE','FACTORY','DISTRIBUTION_CENTER')),
    country_code TEXT NOT NULL CHECK (length(country_code) = 2 AND country_code GLOB '[A-Z][A-Z]'),
    timezone TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (lifecycle_state IN ('ACTIVE','INACTIVE')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS supplier (
    supplier_id TEXT PRIMARY KEY CHECK (supplier_id GLOB 'SUP-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    country_code TEXT CHECK (country_code IS NULL OR (length(country_code) = 2 AND country_code GLOB '[A-Z][A-Z]')),
    lifecycle_state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (lifecycle_state IN ('ACTIVE','ON_HOLD','INACTIVE')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Approved SKU substitutes are explicitly many-to-many and effective-dated.
CREATE TABLE IF NOT EXISTS sku_substitute (
    primary_sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    substitute_sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    approval_state TEXT NOT NULL CHECK (approval_state IN ('PENDING','APPROVED','REJECTED','REVOKED')),
    effective_from TEXT NOT NULL CHECK (date(julianday(effective_from)) IS NOT NULL AND date(julianday(effective_from)) = effective_from),
    effective_to TEXT CHECK (effective_to IS NULL OR (date(julianday(effective_to)) IS NOT NULL AND date(julianday(effective_to)) = effective_to AND effective_to >= effective_from)),
    PRIMARY KEY (primary_sku_id, substitute_sku_id, effective_from),
    CHECK (primary_sku_id <> substitute_sku_id)
);

CREATE TABLE IF NOT EXISTS forecast_demand (
    demand_id TEXT PRIMARY KEY CHECK (demand_id GLOB 'DEM-SKU-[0-9][0-9][0-9][0-9][0-9][0-9]-LOC-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]W[0-9][0-9]'),
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    location_id TEXT NOT NULL REFERENCES location(location_id),
    week_start TEXT NOT NULL CHECK (date(julianday(week_start)) IS NOT NULL AND date(julianday(week_start)) = week_start),
    week_code TEXT NOT NULL CHECK (week_code GLOB '[0-9][0-9][0-9][0-9]W[0-9][0-9]' AND CAST(substr(week_code,6,2) AS INTEGER) BETWEEN 1 AND 53),
    forecast_qty REAL NOT NULL CHECK (forecast_qty >= 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    forecast_version TEXT NOT NULL DEFAULT 'BASELINE',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (sku_id, location_id, week_code, forecast_version),
    CHECK (demand_id = 'DEM-' || sku_id || '-' || location_id || '-' || week_code)
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id TEXT PRIMARY KEY CHECK (inventory_id GLOB 'INV-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    location_id TEXT NOT NULL REFERENCES location(location_id),
    as_of_date TEXT NOT NULL CHECK (date(julianday(as_of_date)) IS NOT NULL AND date(julianday(as_of_date)) = as_of_date),
    on_hand_qty REAL NOT NULL CHECK (on_hand_qty >= 0),
    inbound_qty REAL NOT NULL DEFAULT 0 CHECK (inbound_qty >= 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    source_reference TEXT,
    UNIQUE (sku_id, location_id, as_of_date)
);

CREATE TABLE IF NOT EXISTS supplier_capacity (
    supplier_capacity_id TEXT PRIMARY KEY CHECK (supplier_capacity_id GLOB 'SCAP-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    supplier_id TEXT NOT NULL REFERENCES supplier(supplier_id),
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    period_start TEXT NOT NULL CHECK (date(julianday(period_start)) IS NOT NULL AND date(julianday(period_start)) = period_start),
    period_end TEXT NOT NULL CHECK (date(julianday(period_end)) IS NOT NULL AND date(julianday(period_end)) = period_end AND period_end >= period_start),
    capacity_qty REAL NOT NULL CHECK (capacity_qty >= 0),
    minimum_order_qty REAL NOT NULL DEFAULT 0 CHECK (minimum_order_qty >= 0 AND minimum_order_qty <= capacity_qty),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    UNIQUE (supplier_id, sku_id, period_start, period_end)
);

CREATE TABLE IF NOT EXISTS lead_time (
    lead_time_id TEXT PRIMARY KEY CHECK (lead_time_id GLOB 'LT-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    supplier_id TEXT NOT NULL REFERENCES supplier(supplier_id),
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    origin_location_id TEXT REFERENCES location(location_id),
    destination_location_id TEXT NOT NULL REFERENCES location(location_id),
    effective_from TEXT NOT NULL CHECK (date(julianday(effective_from)) IS NOT NULL AND date(julianday(effective_from)) = effective_from),
    effective_to TEXT CHECK (effective_to IS NULL OR (date(julianday(effective_to)) IS NOT NULL AND date(julianday(effective_to)) = effective_to AND effective_to >= effective_from)),
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 0),
    UNIQUE (supplier_id, sku_id, origin_location_id, destination_location_id, effective_from)
);

CREATE TABLE IF NOT EXISTS production_capacity (
    production_capacity_id TEXT PRIMARY KEY CHECK (production_capacity_id GLOB 'PCAP-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    location_id TEXT NOT NULL REFERENCES location(location_id),
    period_start TEXT NOT NULL CHECK (date(julianday(period_start)) IS NOT NULL AND date(julianday(period_start)) = period_start),
    period_end TEXT NOT NULL CHECK (date(julianday(period_end)) IS NOT NULL AND date(julianday(period_end)) = period_end AND period_end >= period_start),
    capacity_qty REAL NOT NULL CHECK (capacity_qty >= 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    UNIQUE (sku_id, location_id, period_start, period_end)
);

CREATE TABLE IF NOT EXISTS bill_of_material (
    parent_sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    component_sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    quantity_per REAL NOT NULL CHECK (quantity_per > 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    effective_from TEXT NOT NULL CHECK (date(julianday(effective_from)) IS NOT NULL AND date(julianday(effective_from)) = effective_from),
    effective_to TEXT CHECK (effective_to IS NULL OR (date(julianday(effective_to)) IS NOT NULL AND date(julianday(effective_to)) = effective_to AND effective_to >= effective_from)),
    PRIMARY KEY (parent_sku_id, component_sku_id, effective_from),
    CHECK (parent_sku_id <> component_sku_id)
);

CREATE TABLE IF NOT EXISTS purchase_order (
    purchase_order_id TEXT PRIMARY KEY CHECK (purchase_order_id GLOB 'PO-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    supplier_id TEXT NOT NULL REFERENCES supplier(supplier_id),
    destination_location_id TEXT NOT NULL REFERENCES location(location_id),
    order_date TEXT NOT NULL CHECK (date(julianday(order_date)) IS NOT NULL AND date(julianday(order_date)) = order_date),
    requested_delivery_date TEXT NOT NULL CHECK (date(julianday(requested_delivery_date)) IS NOT NULL AND date(julianday(requested_delivery_date)) = requested_delivery_date AND requested_delivery_date >= order_date),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','SUBMITTED','CONFIRMED','IN_TRANSIT','RECEIVED','CANCELLED')),
    currency_code TEXT NOT NULL CHECK (length(currency_code) = 3 AND currency_code GLOB '[A-Z][A-Z][A-Z]'),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS purchase_order_line (
    purchase_order_line_id TEXT PRIMARY KEY CHECK (purchase_order_line_id GLOB 'POL-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    purchase_order_id TEXT NOT NULL REFERENCES purchase_order(purchase_order_id) ON DELETE CASCADE,
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    quantity REAL NOT NULL CHECK (quantity > 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    unit_cost REAL CHECK (unit_cost IS NULL OR unit_cost >= 0),
    UNIQUE (purchase_order_id, sku_id)
);

CREATE TABLE IF NOT EXISTS transport_delay (
    transport_delay_id TEXT PRIMARY KEY CHECK (transport_delay_id GLOB 'TD-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    purchase_order_id TEXT NOT NULL REFERENCES purchase_order(purchase_order_id),
    purchase_order_line_id TEXT REFERENCES purchase_order_line(purchase_order_line_id),
    carrier_name TEXT,
    expected_delivery_date TEXT NOT NULL CHECK (date(julianday(expected_delivery_date)) IS NOT NULL AND date(julianday(expected_delivery_date)) = expected_delivery_date),
    revised_delivery_date TEXT NOT NULL CHECK (date(julianday(revised_delivery_date)) IS NOT NULL AND date(julianday(revised_delivery_date)) = revised_delivery_date AND revised_delivery_date >= expected_delivery_date),
    reason TEXT
);

CREATE TABLE IF NOT EXISTS production_plan (
    production_plan_id TEXT PRIMARY KEY CHECK (production_plan_id GLOB 'PP-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    location_id TEXT NOT NULL REFERENCES location(location_id),
    planned_start_date TEXT NOT NULL CHECK (date(julianday(planned_start_date)) IS NOT NULL AND date(julianday(planned_start_date)) = planned_start_date),
    planned_end_date TEXT NOT NULL CHECK (date(julianday(planned_end_date)) IS NOT NULL AND date(julianday(planned_end_date)) = planned_end_date AND planned_end_date >= planned_start_date),
    planned_qty REAL NOT NULL CHECK (planned_qty > 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','RELEASED','IN_PROGRESS','COMPLETED','CANCELLED')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS shortage (
    shortage_id TEXT PRIMARY KEY CHECK (shortage_id GLOB 'SHORT-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    sku_id TEXT NOT NULL REFERENCES sku(sku_id),
    location_id TEXT NOT NULL REFERENCES location(location_id),
    week_start TEXT NOT NULL CHECK (date(julianday(week_start)) IS NOT NULL AND date(julianday(week_start)) = week_start),
    demand_id TEXT REFERENCES forecast_demand(demand_id),
    shortage_qty REAL NOT NULL CHECK (shortage_qty > 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    cause_summary TEXT NOT NULL CHECK (length(trim(cause_summary)) > 0),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','MITIGATED','ACCEPTED','CLOSED')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (sku_id, location_id, week_start, shortage_id)
);

CREATE TABLE IF NOT EXISTS mitigation_option (
    mitigation_option_id TEXT PRIMARY KEY CHECK (mitigation_option_id GLOB 'MIT-SHORT-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9]'),
    shortage_id TEXT NOT NULL REFERENCES shortage(shortage_id),
    option_type TEXT NOT NULL CHECK (option_type IN ('EXPEDITE','ALTERNATE_SUPPLIER','SUBSTITUTE_SKU','TRANSFER','OVERTIME','DEMAND_ALLOCATION')),
    status TEXT NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED','SELECTED','REJECTED','EXECUTED','EXPIRED')),
    mitigation_qty REAL NOT NULL CHECK (mitigation_qty > 0),
    uom TEXT NOT NULL CHECK (length(trim(uom)) > 0),
    incremental_cost REAL CHECK (incremental_cost IS NULL OR incremental_cost >= 0),
    service_impact_qty REAL CHECK (service_impact_qty IS NULL OR service_impact_qty >= 0),
    supplier_id TEXT REFERENCES supplier(supplier_id),
    substitute_sku_id TEXT REFERENCES sku(sku_id),
    source_location_id TEXT REFERENCES location(location_id),
    target_location_id TEXT REFERENCES location(location_id),
    resulting_delivery_date TEXT CHECK (resulting_delivery_date IS NULL OR (date(julianday(resulting_delivery_date)) IS NOT NULL AND date(julianday(resulting_delivery_date)) = resulting_delivery_date)),
    rationale TEXT NOT NULL CHECK (length(trim(rationale)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (mitigation_option_id = 'MIT-' || shortage_id || '-' || substr(mitigation_option_id, -2))
);

-- Entity-specific nullable FKs avoid an unenforced polymorphic entity_id.
CREATE TABLE IF NOT EXISTS lifecycle_history (
    lifecycle_history_id TEXT PRIMARY KEY CHECK (lifecycle_history_id GLOB 'LCH-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('SKU','LOCATION','SUPPLIER','PURCHASE_ORDER','PRODUCTION_PLAN','SHORTAGE','MITIGATION_OPTION')),
    sku_id TEXT REFERENCES sku(sku_id),
    location_id TEXT REFERENCES location(location_id),
    supplier_id TEXT REFERENCES supplier(supplier_id),
    purchase_order_id TEXT REFERENCES purchase_order(purchase_order_id),
    production_plan_id TEXT REFERENCES production_plan(production_plan_id),
    shortage_id TEXT REFERENCES shortage(shortage_id),
    mitigation_option_id TEXT REFERENCES mitigation_option(mitigation_option_id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    changed_by TEXT NOT NULL DEFAULT 'system',
    note TEXT,
    CHECK (
      (entity_type='SKU' AND sku_id IS NOT NULL AND location_id IS NULL AND supplier_id IS NULL AND purchase_order_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (entity_type='LOCATION' AND location_id IS NOT NULL AND sku_id IS NULL AND supplier_id IS NULL AND purchase_order_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (entity_type='SUPPLIER' AND supplier_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND purchase_order_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (entity_type='PURCHASE_ORDER' AND purchase_order_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND supplier_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (entity_type='PRODUCTION_PLAN' AND production_plan_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND supplier_id IS NULL AND purchase_order_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (entity_type='SHORTAGE' AND shortage_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND supplier_id IS NULL AND purchase_order_id IS NULL AND production_plan_id IS NULL AND mitigation_option_id IS NULL) OR
      (entity_type='MITIGATION_OPTION' AND mitigation_option_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND supplier_id IS NULL AND purchase_order_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL)
    ),
    CHECK (from_state IS NULL OR from_state <> to_state)
);

CREATE TABLE IF NOT EXISTS issue_case (
    issue_case_id TEXT PRIMARY KEY CHECK (issue_case_id GLOB 'ISSUE-[0-9][0-9][0-9][0-9][0-9][0-9]'),
    issue_type TEXT NOT NULL CHECK (issue_type IN ('INBOUND_INVENTORY_COUNTED_TWICE','UNAPPROVED_SUBSTITUTE_SKU','SUPPLIER_CAPACITY_EXCEEDED','SHORTAGE_WITHOUT_LEAD_TIME','UOM_MISMATCH')),
    ground_truth_label TEXT NOT NULL CHECK (ground_truth_label IN ('EXPECTED_EXCEPTION','EXPECTED_ALERT','EXPECTED_REJECTION')),
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- A case can point at multiple records and each link has a real FK.
CREATE TABLE IF NOT EXISTS issue_case_record (
    issue_case_record_id INTEGER PRIMARY KEY,
    issue_case_id TEXT NOT NULL REFERENCES issue_case(issue_case_id) ON DELETE CASCADE,
    record_type TEXT NOT NULL CHECK (record_type IN ('SKU','LOCATION','FORECAST_DEMAND','INVENTORY','SUPPLIER','SUPPLIER_CAPACITY','LEAD_TIME','PURCHASE_ORDER','PURCHASE_ORDER_LINE','PRODUCTION_PLAN','SHORTAGE','MITIGATION_OPTION')),
    sku_id TEXT REFERENCES sku(sku_id),
    location_id TEXT REFERENCES location(location_id),
    demand_id TEXT REFERENCES forecast_demand(demand_id),
    inventory_id TEXT REFERENCES inventory(inventory_id),
    supplier_id TEXT REFERENCES supplier(supplier_id),
    supplier_capacity_id TEXT REFERENCES supplier_capacity(supplier_capacity_id),
    lead_time_id TEXT REFERENCES lead_time(lead_time_id),
    purchase_order_id TEXT REFERENCES purchase_order(purchase_order_id),
    purchase_order_line_id TEXT REFERENCES purchase_order_line(purchase_order_line_id),
    production_plan_id TEXT REFERENCES production_plan(production_plan_id),
    shortage_id TEXT REFERENCES shortage(shortage_id),
    mitigation_option_id TEXT REFERENCES mitigation_option(mitigation_option_id),
    CHECK (
      (record_type='SKU' AND sku_id IS NOT NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='LOCATION' AND location_id IS NOT NULL AND sku_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='FORECAST_DEMAND' AND demand_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='INVENTORY' AND inventory_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='SUPPLIER' AND supplier_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='SUPPLIER_CAPACITY' AND supplier_capacity_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='LEAD_TIME' AND lead_time_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='PURCHASE_ORDER' AND purchase_order_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='PURCHASE_ORDER_LINE' AND purchase_order_line_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='PRODUCTION_PLAN' AND production_plan_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND shortage_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='SHORTAGE' AND shortage_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND mitigation_option_id IS NULL) OR
      (record_type='MITIGATION_OPTION' AND mitigation_option_id IS NOT NULL AND sku_id IS NULL AND location_id IS NULL AND demand_id IS NULL AND inventory_id IS NULL AND supplier_id IS NULL AND supplier_capacity_id IS NULL AND lead_time_id IS NULL AND purchase_order_id IS NULL AND purchase_order_line_id IS NULL AND production_plan_id IS NULL AND shortage_id IS NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS issue_case_record_unique_link ON issue_case_record (
    issue_case_id, record_type,
    ifnull(sku_id,''), ifnull(location_id,''), ifnull(demand_id,''), ifnull(inventory_id,''),
    ifnull(supplier_id,''), ifnull(supplier_capacity_id,''), ifnull(lead_time_id,''),
    ifnull(purchase_order_id,''), ifnull(purchase_order_line_id,''), ifnull(production_plan_id,''),
    ifnull(shortage_id,''), ifnull(mitigation_option_id,'')
);

-- IDs referenced by other records are immutable.
CREATE TRIGGER IF NOT EXISTS sku_id_immutable BEFORE UPDATE OF sku_id ON sku BEGIN SELECT RAISE(ABORT, 'sku_id is immutable'); END;
CREATE TRIGGER IF NOT EXISTS location_id_immutable BEFORE UPDATE OF location_id ON location BEGIN SELECT RAISE(ABORT, 'location_id is immutable'); END;
CREATE TRIGGER IF NOT EXISTS supplier_id_immutable BEFORE UPDATE OF supplier_id ON supplier BEGIN SELECT RAISE(ABORT, 'supplier_id is immutable'); END;
CREATE TRIGGER IF NOT EXISTS demand_id_immutable BEFORE UPDATE OF demand_id ON forecast_demand BEGIN SELECT RAISE(ABORT, 'demand_id is immutable'); END;
CREATE TRIGGER IF NOT EXISTS purchase_order_id_immutable BEFORE UPDATE OF purchase_order_id ON purchase_order BEGIN SELECT RAISE(ABORT, 'purchase_order_id is immutable'); END;
CREATE TRIGGER IF NOT EXISTS shortage_id_immutable BEFORE UPDATE OF shortage_id ON shortage BEGIN SELECT RAISE(ABORT, 'shortage_id is immutable'); END;
CREATE TRIGGER IF NOT EXISTS mitigation_option_id_immutable BEFORE UPDATE OF mitigation_option_id ON mitigation_option BEGIN SELECT RAISE(ABORT, 'mitigation_option_id is immutable'); END;
