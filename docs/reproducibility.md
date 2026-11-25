# Reproducibility evidence

## Full preset, seed `20261022`

Commands completed:

```bash
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-run1
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-run2
python3 generate_data.py compare --left /private/tmp/oryva-full-run1 --right /private/tmp/oryva-full-run2
```

Both generation and validation runs passed at 3,000 SKUs, 50 locations, 52 weeks, 500 suppliers, 10,000 POs, 115,800 assortment pairs, and 6,021,600 forecast rows. All 15 canonical CSVs matched in row count and SHA-256:

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

The source data are synthetic and use no external data. Full-scale outputs remain in `/private/tmp`; only this concise evidence is included in the repository. A full-scale planner output comparison was not run.

## Starter preset

Seed `20261022`, 24 SKUs, 6 locations, 12 weeks, 12 suppliers, and 36 POs. Fresh generation in `/private/tmp/oryva-starter-verify` and validation of committed `data/starter/` both passed. The planner emitted 1,308 projected-balance rows, 1,052 shortages, 1,052 ranking rows, 1,786 feasible mitigation options (maximum three per shortage), and five separate ground-truth cases. Every committed data file is below 50 MB. Detailed source checksums remain in `docs/phase2-data.md`; planner checksums and checks are in `data/starter/planner_validation.json`.
