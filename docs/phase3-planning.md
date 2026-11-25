# Phase 3 planning evidence

## Planner

`planner.py` calculates weekly closing projected availability as opening balance plus PO lines arriving during that ISO week minus forecast demand. Closing balance rolls into the next week. Each shortage links to its demand ID, SKU, location, date and unit, and includes a cause summary. Ranking is descending shortage share, then shortage quantity, with stable IDs as tie breakers. Mitigations report cost, residual service impact, lead-time/capacity feasibility and rationale.

## Starter run evidence

Command: `python3 planner.py --data-dir data/starter` (seeded source dataset `20261022`).

| Output | Data rows |
|---|---:|
| projected_balance.csv | 1,308 |
| shortages.csv | 1,052 |
| shortage_ranking.csv | 1,052 |
| mitigations.csv | 3,156 |
| ground_truth.csv | 5 |

All planner validation checks passed. Of 1,052 shortages, 1,786 feasible options were retained (at most three per shortage); demand allocation provides a policy-feasible fallback. Starter output SHA-256: projected balance `131eb831b261772e71dd04b5b8c215a81a1e78700da230e45b9e7ca4315acdea`; shortages `1479fd69b8ee8cfc0f98777d1eb8e35e7a4877fa64521f29af6d339855c4c828`; ranking `cdd84d6d595bef19664d49d568e499ef4841792060280195b9b0c5f579da8b0b`; capped mitigations `7bb3445258a29d613ebdebde3dc835361298a167abf72f0f19a9a70b8cf69cae`; ground truth with source references `73539b7eb9f3af3be3c12670a3e98908a1e0326ad5821b2a22ab012a2d344185`.

## Full-scale source reproducibility

Both full generation commands used seed `20261022`, preset `full`, and completed successfully. Each has 3,000 SKUs, 50 locations, 52 ISO weeks, 500 suppliers, 10,000 purchase orders, 115,800 assortment pairs, and 6,021,600 demand rows. Both validated with zero FK/duplicate/date/UOM/capacity/lifecycle failures. The compare command passed row counts and SHA-256 for all 15 canonical CSVs:

| CSV | Rows | SHA-256 (both runs) |
|---|---:|---|
| bill_of_material.csv | 999 | `80f0a6f330af9aafc3eee729b2bfb21ce8d47fe49cfc3951deb3f31f076ccb36` |
| forecast_demand.csv | 6,021,600 | `adeeb033b215b3b5e17969b3a5da153245f4efdda54ed0c0bc1fe33de1c17613` |
| inventory.csv | 115,800 | `22a3147925508a268c328c3d26dcfaedc7e0a1150329cc5f3da26e8c73c0e321` |
| lead_time.csv | 231,600 | `898e0b898c71847fa2c4a261c04b566e882e9bfdc35a805e6634ac4a59fa2b8a` |
| lifecycle_history.csv | 45,844 | `b0f471b251cd46b7ac523dfc7d334e34e7150e1615f21d0757554e488d52bc9b` |
| location.csv | 50 | `00023e57d9898ca509c49083bbdd0b952928763a33c8f4967b30561240f81191` |
| production_capacity.csv | 36,000 | `133418294975cbc6094b4f21f4ad1ffe5ed22bcaa71040bc96ac0ffdc7f507e3` |
| purchase_order.csv | 10,000 | `45b169852aa1ecc357fa721aee35462e22f2414c31ca2ec2bcb6d539ab8815eb` |
| purchase_order_line.csv | 10,000 | `c17e440d4fd3686da900ee6aa6a14d019dc2652264db73717318154a58ac632b` |
| sku.csv | 3,000 | `c78cacbdd3ad27ae833f8f766dd9a28f71a1882d8aded61963e0d4cceaed06b1` |
| sku_location_assortment.csv | 115,800 | `380e4387bfe2edfea989d7b2ce607d63221aaa75b302ee3bcaea85e3d7cce2aa` |
| sku_substitute.csv | 750 | `42f2b1e68f5c00bd34a400e6b4384e62ef43fcc46d7a488adde90bc2eee4a100` |
| supplier.csv | 500 | `43b69c19b0154ab25cf4838a34092612ac7bc8dd90ea167bac0d92054df0f3ad` |
| supplier_capacity.csv | 6,000 | `6faac1c75a7d07898e1e8c7fab43dc9eb90527fde955af45db283f1861b2ebc4` |
| transport_delay.csv | 10,000 | `5acf8abe7b1e8906314d2d9a72494868b05d9ba2b7458ab375525fd83e55e549` |

The two generated source directories are `/private/tmp/oryva-full-run1` and `/private/tmp/oryva-full-run2`. An uncapped planner attempt was stopped before ranking completed because its mitigation export exceeded 17 million rows. A capped planner attempt was started on run 2 in `/private/tmp`; if it does not finish by 18:10 IST, it is not acceptance evidence. The committed capped planner passed on the starter dataset. Full source CSV reproducibility evidence is in `docs/reproducibility.md`.

## Edge-case coverage and limits

`ground_truth.csv` is separate from baseline features and contains one row for each required class: duplicate inbound counting, unapproved substitute, supplier capacity exceeded, shortage without lead time, and UOM mismatch. `source_record_refs` points at relevant starter source records or explicitly names the absent relation/route or counterfactual unit. These are isolated labeled rule fixtures, not injected corrupt operational rows. The current planner exports expected labels but does not execute a dedicated detector against each fixture or persist issue links into SQLite; that remains a validation gap.

The current balance planner uses receipts by actual revised arrival date and opening stock only; it does not consume production capacity/BOM into production plans. Mitigation options are recommendations with modeled policy checks, not committed purchase orders or production. Re-run planner after changes before relying on recorded hashes.
