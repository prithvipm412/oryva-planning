# Requirements and phase map

Status updated 2026-11-25. Schema, starter generation and planning deliverables are implemented locally. Full-scale source reproducibility passed; only full-scale planner comparison and issue-detector execution remain incomplete. GitHub publishing and form submission are user-owned final steps.

| Brief requirement | Intended phase | Evidence of completion |
|---|---:|---|
| Match forecast demand to inventory, supplier capacity, lead times, production constraints; prioritize shortages | 3 | Starter planner, balance/shortage exports and prioritized rankings; production/BOM planning remains a gap |
| Expose decisions/exceptions, traceability, measurable outputs | 3 | Causes, ranked shortages, trade-off options, source references and validation JSON |
| Master data: SKU, Location, ForecastDemand, Inventory, Supplier | 2 | Deterministic generator, exported files, FK validation |
| Dependent transaction/event records use valid parent IDs | 2 | Generator dependency ordering and validation report |
| Weekly SKU-location demand, inventory, capacity, minimum quantities, lead times, production capacity and BOM | 2–3 | Generated records and planning calculation reconciled by week |
| Projected available balance, shortages and candidate mitigations | 3 | Calculated balances, shortage causes and options with trade-offs |
| Preserve state changes as explicit records/events | 1 (schema), 2–3 (population) | `lifecycle_history` schema; event rows and transition checks |
| Outcomes and ground-truth labels derived from documented rules | 3 | Five separate source-referenced rule fixtures in ground_truth.csv; dedicated detectors are not implemented |
| Eleven named entities and PK/FK/cardinality/optional/effective-date/lifecycle documentation | 1 | `schema.sql` and `docs/data-dictionary.md` |
| Bridge tables for many-to-many relationships | 1 | `sku_substitute`, `bill_of_material`, `purchase_order_line`; documented cardinality |
| Retain event history and validate joins | 1 (schema), 2 (data) | FK-enabled connection helper, lifecycle table, FK smoke check and future data validation |
| Label deliberate anomaly cases with issue_type/ground truth | 1 (schema), 3 (fixtures) | `issue_case` schema plus separate ground_truth.csv fixtures; no deliberately corrupted baseline records |
| Exact IDs: SKU-000001; DEM-<sku>-<location>-2026W01; PO-2026-000001; SHORT-2026-000001; MIT-<shortage-id>-01 | 1 | SQL ID checks and detailed dictionary; assignment literal pattern retained with SKU/LOC values expanded in DEM IDs |
| Zero-padded, immutable IDs consistent across files | 1 (schema), 2 (generator) | SQL shape checks and immutable-ID triggers; later cross-file validation |
| Dictionary for all eleven named entities, every field specified | 1 | `docs/data-dictionary.md` |
| Generate 3,000 SKUs, 50 locations, 52 weeks, 500 suppliers, 10,000 inbound orders; parameterized scale, fixed seed | 2 | Two full runs completed at seed 20261022; source row counts and hashes in `docs/reproducibility.md` |
| Demand spikes, constrained suppliers, substitutes, transport delays | 2 | Generated variation summary and validation evidence |
| Valid baseline first, then labeled edge cases | 2 (baseline), 5 (injection) | Phase 2 starter is valid; labeled edge-case injection is deferred to Phase 5 |
| Derived totals, balances, scores, statuses, dates from source | 3 | Reconciliation checks and calculation evidence |
| Separate `ground_truth.csv` or JSON, excluded from input features | 3 | Separate starter export, with five labels and source_record_refs |
| Validation: keys, FKs, enums, date order, arithmetic, lifecycle transitions, duplicates | 1 (schema), 2 (generated source data), 3 (planning reconciliation) | Phase 1 smoke and Phase 2 row-level validation recorded in their documentation; derived checks later |
| Edge cases: double-counted inbound; unapproved substitute; supplier over capacity; missing lead time; UOM mismatch | 3 | Five labeled rule fixtures. Detector execution and SQLite issue links remain unimplemented |
| Acceptance: weekly balance reconciliation; explainable shortage causes; policy/capacity-compliant mitigations; cost/service alternatives | 3 | Automated planning validation output and explainable scenario report |
| Realistic distributions/variation, valid joins, dependency/lifecycle consistency, derivation, edge coverage, isolated labels, fixed-seed reproducibility, lawful provenance | 2–4 | Data review summary, validation/reproducibility checksums, source manifest, and documentation |
| Lawful external data and source manifest where used | 2 | Source manifest with URL/version/date/license/attribution/transforms/discarded fields, or documented synthetic-only approach |
| Public GitHub repo and submission form | 5 | Public repository URL and submission confirmation (not part of Phase 1) |
| README install/configure/run; tests and validation output | 1–3 | README includes install, generator, seed, validation and test commands; four unit tests pass |
| Data exports, schema/dictionary, generator command/seed, source manifest/summary | 1 (schema/dictionary), 2 (starter exports/generator/seed/manifest), 4 (final summary) | Starter artifacts and run evidence in `data/starter/` and `docs/phase2-data.md` |
| Reproducibility with same seed | 2 | Two starter runs with matching per-CSV row counts and SHA-256 in `docs/phase2-data.md` |
| Build and test locally; publish; submit; auditable explanations | 1–5 | Local phase checks now; repository/form evidence in final phase |

## Remaining limits

Mitigation options are recommendations, not executed orders. The planner does not model production capacity/BOM, dedicated issue-case detectors, or persisted issue links. Full source CSVs were compared, but full planner outputs were not compared. No dashboard was prioritized. Publishing and the submission form remain for the user.
