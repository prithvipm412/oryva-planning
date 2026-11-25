# Phase 2 deterministic starter data

## Generator and presets

`generate_data.py` uses the Phase 1 `schema.sql` through `db.initialize()` and opens the generated database through `db.connect_db()`. It uses only the Python standard library.

| Preset | SKUs | Locations | Demand weeks | Suppliers | Inbound purchase orders | Status |
|---|---:|---:|---:|---:|---:|---|
| starter | 24 | 6 | 12 | 12 | 36 | Generated and validated |
| full | 3,000 | 50 | 52 | 500 | 10,000 | Defined for later use; not run in Phase 2 |

Default seed: `20261022`. The 2026 forecast calendar uses ISO weeks 01 through the configured number of weeks. ISO week 2026W01 begins on 2025-12-29; purchase orders use 2026 order dates to match the `PO-2026-######` ID convention.

## Generation rules

- **Assortment:** zero-based SKU/location pairs are included when `(sku_index * 7 + location_index * 3) % 10 < 7`, plus every factory location. IDs are traversed in stable order. Since Phase 1 has no explicit assortment table, this relationship is exported as `sku_location_assortment.csv` and is also represented by demand and opening inventory rows.
- **Forecasts:** each assortment pair gets one row per ISO week. Quantities start from a seeded pair baseline, receive bounded seasonal and week-level variation, and get a deterministic 1.8–2.7x spike on rows selected by a documented modular rule. Every record's `week_start` comes from `date.fromisocalendar(2026, week, 1)`.
- **Opening inventory:** exactly one opening row per assortment pair at the first forecast week's Monday, in the SKU base UOM. Opening stock is the seeded baseline weekly demand multiplied by configured weeks and a seeded 0.95–1.05 factor. `inventory.inbound_qty` is zero for every row.
- **Inbound supply:** each PO has exactly one linked `purchase_order_line`; its quantity is the sole inbound supply record for Phase 3. Capacity rows are created per supplier/SKU before POs. Their capacity covers the generated PO commitment plus slack; selected commitments have only 4% slack. Minimum order quantities are at most 15 units and below each generated PO quantity.
- **Lead times and arrivals:** each supplier/SKU/destination combination has a valid effective lead-time row. PO requested date is calculated from PO order date plus that lead time. `transport_delay.expected_delivery_date` repeats the PO promise; `revised_delivery_date` adds a deterministic 0–6 day delay. Each PO line has exactly one linked transport/arrival event. The PO lifecycle records its state path; `RECEIVED` is recorded on the revised date when that date is no later than the fixed data-as-of date, otherwise the current state remains in transit or earlier.
- **Other supply/product structure:** supplier capacity includes variation in tightness; factory SKUs have production capacity; selected SKUs have BOM component rows; selected SKU pairs have only APPROVED, effective-dated substitutions.
- **Out of scope:** no production plan, projected balance, shortage, mitigation, issue case, ground-truth labels, or deliberate negative cases are generated. Per the current instruction, negative cases and their ground truth are deferred to Phase 5.

## Commands

From the repository root with the macOS virtual environment activated:

```bash
python3 generate_data.py generate --preset starter --seed 20261022 --out-dir data/starter
python3 generate_data.py validate --out-dir data/starter
python3 generate_data.py generate --preset starter --seed 20261022 --out-dir /private/tmp/oryva-phase2-repro-final2
python3 generate_data.py compare --left data/starter --right /private/tmp/oryva-phase2-repro-final2
python3 db.py smoke
```

The generator requires a clean output directory and refuses to overwrite a database. `data/starter/` contains the SQLite file, all canonical CSVs, and `source_manifest.json`.

Full preset dimensions and configurable overrides:

```bash
python3 generate_data.py generate --preset full --seed 20261022 --out-dir data/full
python3 generate_data.py generate --preset starter --skus 30 --locations 8 --weeks 16 --suppliers 14 --orders 50 --seed 20261022 --out-dir data/custom
```

The full command is documented only; it was not run in this phase.

## Starter row counts

| CSV | Rows |
|---|---:|
| `sku.csv` | 24 |
| `location.csv` | 6 |
| `supplier.csv` | 12 |
| `sku_location_assortment.csv` | 109 |
| `forecast_demand.csv` | 1,308 |
| `inventory.csv` | 109 |
| `supplier_capacity.csv` | 48 |
| `lead_time.csv` | 218 |
| `production_capacity.csv` | 24 |
| `bill_of_material.csv` | 7 |
| `sku_substitute.csv` | 6 |
| `purchase_order.csv` | 36 |
| `purchase_order_line.csv` | 36 |
| `transport_delay.csv` | 36 |
| `lifecycle_history.csv` | 180 |

Observed variation: 100 forecast spike rows, 8 tight supplier-capacity records, 2 constrained suppliers, 11 delayed arrival events, and 25 on-time arrival events. These are valid baseline conditions, not deliberate anomaly injections.

## Validation and actual results

Both generated databases passed the generator validation. It checks application-table PK duplicates, `PRAGMA foreign_key_check`, ISO week/date alignment, UOM equality to the referenced SKU, date ordering, one line and one arrival event per PO, effective lead-time presence and arithmetic, supplier capacity/minimum compliance, zero duplicate inbound inventory quantities, and PO lifecycle current-state agreement.

Actual validation outcomes for `data/starter/`:

| Check | Result |
|---|---:|
| Foreign-key violations | 0 |
| Duplicate primary keys | 0 (validator raises on any duplicate) |
| Forecast ISO week/date rows checked | 1,308; all matched |
| Forecast, inventory, supplier capacity, production capacity, PO line, and BOM UOM mismatches | 0 |
| Invalid dates, capacity overcommitments, below-minimum orders | 0 |
| Missing effective lead times or PO arrival events | 0 |
| PO requested date inconsistent with lead time/promise | 0 |
| PO lifecycle current-state mismatches | 0 |
| Duplicate inbound quantities in inventory | 0 |

## Reproducibility record

Run 1 command:

```bash
python3 generate_data.py generate --preset starter --seed 20261022 --out-dir data/starter
```

Run 2 command:

```bash
python3 generate_data.py generate --preset starter --seed 20261022 --out-dir /private/tmp/oryva-phase2-repro-final2
```

Comparison command:

```bash
python3 generate_data.py compare --left data/starter --right /private/tmp/oryva-phase2-repro-final2
```

Actual comparison output (both row counts and SHA-256 values matched for every CSV):

| CSV | Rows | SHA-256 |
|---|---:|---|
| `bill_of_material.csv` | 7 | `64d63965b6254afa654ee1a21d2a1ef381d61ca33a54beda9c81d2c2ed9627a6` |
| `forecast_demand.csv` | 1,308 | `aaf233c7a1911a8ecec1a664748ed5f6931c51b4c77429962a977adf8e3c360f` |
| `inventory.csv` | 109 | `64481109ac636e4db22f58adc31598259baf38cf17867fb93bf2db191d6dd740` |
| `lead_time.csv` | 218 | `34e23fbcb252561b6f0fb51c3cc1289926d39f1729901cb15c27e598362e638f` |
| `lifecycle_history.csv` | 180 | `927dbac8f8ed87b7ff6c3a783f7598747e993c5fc87eec27a709e077e6e1f7ff` |
| `location.csv` | 6 | `c63216bcde1c9e40bf0477f019160ba4d6d6885564c66995b2b550ab5a9a44f5` |
| `production_capacity.csv` | 24 | `93f668bee9cf4fd1b721110c057f65579c26df5349a2834f234df571f5f95e58` |
| `purchase_order.csv` | 36 | `19ec824eb7c20d40e7ad2763a1d348bc7501c328925610363f9fa9f4a8dd50a8` |
| `purchase_order_line.csv` | 36 | `1c1bc0d0026ac1e5ba4984f1ca85218d35a0737fec2e55ba5abfd366c5b5410a` |
| `sku.csv` | 24 | `9093ece8a3f69ce1e88c507f2d07c3309983e05093b5ed309d79f8598cf9512d` |
| `sku_location_assortment.csv` | 109 | `b5a3a0a679e51f8b63e3febeef0a5e704b094a7ad518e4612263221b57e22f5e` |
| `sku_substitute.csv` | 6 | `e0c3f49b864028c9e7d7d448625049739fcfb87f1eadae1a4566bbb5eb6a13fd` |
| `supplier.csv` | 12 | `f381ea25fc53fbba75f00931307157e937521cfcd67b4f51ba166c2e8766dc96` |
| `supplier_capacity.csv` | 48 | `0b51172b0ac4c8832dccc4b0ed48d3738b53819c22d4e7e5e51772aa68b856a8` |
| `transport_delay.csv` | 36 | `c524100a8fbedd9b796c3e1ed3bdb8882e73ba32c5502d491c6fbfc454c58b26` |

Actual compare result: `PASS all row counts and SHA-256 checksums match`.

The final `python3 db.py smoke` run passed duplicate-PK rejection, invalid-enum rejection, impossible-calendar-date rejection, invalid-FK rejection, 19-table schema presence, and FK enablement on each project connection.

## Schema assumptions and Phase 3 handoff

- No schema change was needed. Assortment is represented by a deterministic CSV because Phase 1 has no dedicated assortment table; each row has matching forecast and opening inventory records.
- Purchase order line quantities are the single source of inbound supply. Opening inventory's `inbound_qty` remains zero, preventing Phase 3 from counting each PO line twice.
- The Phase 1 `transport_delay` fields hold promised and revised arrival dates. The PO's lifecycle history records `RECEIVED` on the revised date when delivery is no later than the fixed data-as-of date; a future revised date remains an estimate and the PO remains in its latest pre-receipt state.
- Forecast W01 is 2025-12-29 through 2026-01-04 because it is ISO week 1 of 2026. Purchase orders use actual 2026 dates to match their required 2026 IDs and capacity effective period.
- Production capacity and BOM inputs are present, but `production_plan` remains empty until planning logic. Projected available balances, shortages, mitigations, exception labels, and ground truth are intentionally deferred.
