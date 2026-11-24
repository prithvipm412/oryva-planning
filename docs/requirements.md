# Requirements and phase map

Phase boundaries follow the four-page assignment. Phase 1 below is the current implementation scope.

| Brief requirement | Intended phase | Evidence of completion |
|---|---:|---|
| Match forecast demand to inventory, supplier capacity, lead times, production constraints; prioritize shortages | 3 | Planning engine, documented rules, sample run, prioritized shortage output |
| Expose decisions/exceptions, traceability, measurable outputs | 3–4 | Explainable decision records, exception paths, evaluation metrics and report |
| Master data: SKU, Location, ForecastDemand, Inventory, Supplier | 2 | Deterministic generator, exported files, FK validation |
| Dependent transaction/event records use valid parent IDs | 2 | Generator dependency ordering and validation report |
| Weekly SKU-location demand, inventory, capacity, minimum quantities, lead times, production capacity and BOM | 2–3 | Generated records and planning calculation reconciled by week |
| Projected available balance, shortages and candidate mitigations | 3 | Calculated balances, shortage causes and options with trade-offs |
| Preserve state changes as explicit records/events | 1 (schema), 2–3 (population) | `lifecycle_history` schema; event rows and transition checks |
| Outcomes and ground-truth labels derived from documented rules | 2–3 | Reproducible labeled issue cases and separate ground-truth export |
| Eleven named entities and PK/FK/cardinality/optional/effective-date/lifecycle documentation | 1 | `schema.sql` and `docs/data-dictionary.md` |
| Bridge tables for many-to-many relationships | 1 | `sku_substitute`, `bill_of_material`, `purchase_order_line`; documented cardinality |
| Retain event history and validate joins | 1 (schema), 2 (data) | FK-enabled connection helper, lifecycle table, FK smoke check and future data validation |
| Label deliberate anomaly cases with issue_type/ground truth | 1 (schema), 2 (records) | `issue_case` and `issue_case_record`; later labeled examples |
| Exact IDs: SKU-000001; DEM-<sku>-<location>-2026W01; PO-2026-000001; SHORT-2026-000001; MIT-<shortage-id>-01 | 1 | SQL ID checks and detailed dictionary; assignment literal pattern retained with SKU/LOC values expanded in DEM IDs |
| Zero-padded, immutable IDs consistent across files | 1 (schema), 2 (generator) | SQL shape checks and immutable-ID triggers; later cross-file validation |
| Dictionary for all eleven named entities, every field specified | 1 | `docs/data-dictionary.md` |
| Generate 3,000 SKUs, 50 locations, 52 weeks, 500 suppliers, 10,000 inbound orders; parameterized scale, fixed seed | 2 | Generator CLI, full output counts and seed recorded |
| Demand spikes, constrained suppliers, substitutes, transport delays | 2 | Generated variation summary and validation evidence |
| Valid baseline first, then labeled edge cases | 2 | Generator stages and ground-truth rows |
| Derived totals, balances, scores, statuses, dates from source | 3 | Reconciliation checks and calculation evidence |
| Separate `ground_truth.csv` or JSON, excluded from input features | 2 | Separate export and feature-list check |
| Validation: keys, FKs, enums, date order, arithmetic, lifecycle transitions, duplicates | 1 (key/FK/schema constraints), 2–3 (data and derived checks) | Phase 1 `python db.py smoke`; later validation report for remaining checks |
| Edge cases: double-counted inbound; unapproved substitute; supplier over capacity; missing lead time; UOM mismatch | 2–3 | Five labeled scenario records and expected outcomes |
| Acceptance: weekly balance reconciliation; explainable shortage causes; policy/capacity-compliant mitigations; cost/service alternatives | 3 | Automated planning validation output and explainable scenario report |
| Realistic distributions/variation, valid joins, dependency/lifecycle consistency, derivation, edge coverage, isolated labels, fixed-seed reproducibility, lawful provenance | 2–4 | Data review summary, validation/reproducibility checksums, source manifest, and documentation |
| Lawful external data and source manifest where used | 2 | Source manifest with URL/version/date/license/attribution/transforms/discarded fields, or documented synthetic-only approach |
| Public GitHub repo and submission form | 5 | Public repository URL and submission confirmation (not part of Phase 1) |
| README install/configure/run; tests and validation output | 1 (setup/check command), 2–4 (full outputs) | README commands and observed Phase 1 smoke results; later test/validation reports |
| Data exports, schema/dictionary, generator command/seed, source manifest/summary | 1 (schema/dictionary), 2 (exports/generator/seed/manifest), 4 (summary) | Versioned project artifacts after their intended phases |
| Reproducibility with same seed | 2 | Two generator runs with equal row counts and checksums |
| Build and test locally; publish; submit; auditable explanations | 1–5 | Local phase checks now; repository/form evidence in final phase |

## Phase 1 completion boundary

Phase 1 includes schema design and enforcement, setup documentation, requirements traceability, field dictionary, a fresh database, and schema smoke checks. It does not generate business data or implement planning calculations, a dashboard, full-volume exports, or publishing.
