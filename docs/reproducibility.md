# Reproducibility evidence

## Historical full planner summary (pre-production and pre-stock tuning)

Commands completed:

```bash
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-tuned1
python3 generate_data.py generate --preset full --seed 20261022 --out-dir /private/tmp/oryva-full-tuned2
python3 generate_data.py compare --left /private/tmp/oryva-full-tuned1 --right /private/tmp/oryva-full-tuned2
```

This earlier full source comparison was performed before anomaly injection and stock tuning; its hashes are retained only as historical evidence. The updated full generation comparison appears below.

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

This earlier planner output is retained in `docs/full_planner_validation.json` as historical evidence only. It predates BOM production planning and the revised opening stock; current full generation was repeated, but full planning was not rerun.

## Full preset after stock tuning: all output files

Both runs completed in under six minutes at the full preset scale. All 22 generated outputs matched (CSV row counts and SQLite table-row total included). The second dataset was deleted after hashing.

| Output | Rows | SHA-256 (both runs) |
|---|---:|---|
| bill_of_material.csv | 999 | `80f0a6f330af9aafc3eee729b2bfb21ce8d47fe49cfc3951deb3f31f076ccb36` |
| edge_case_detection.json | — | `0965a8562617b17dbeeeae087472a754241f72a3169cb3b953b521c99807a609` |
| edge_case_injections.csv | 5 | `f13cab9ef0c13383ae105d677b2886e5f5caaf34e2387418026ddbb32d5d17b1` |
| forecast_demand.csv | 6,021,600 | `adeeb033b2151a8ecec1a664748ed5f6931c51b4c77429962a977adf8e3c360f` |
| ground_truth.csv | 5 | `5e204a396d101255a8e0445ed652c60dd3b162146afa2f9c4c8a001cb5f187b5` |
| inventory.csv | 115,800 | `f48976f67166da78920ff2d148741d5edf3dfb6e292bd848a213022534f34c25` |
| issue_case.csv | 5 | `e8494e9c8238642a932721f345a71e24f4db182383c4e378b6126192711beeca` |
| issue_case_record.csv | 10 | `5266d29ce6a8c803aa1f5dec558ee9037b5a11fa99edb9156b96b74eae39e667` |
| lead_time.csv | 231,600 | `898e0b898c71847fa2c4a261c04b566e882e9bfdc35a805e6634ac4a59fa2b8a` |
| lifecycle_history.csv | 45,844 | `b0f471b251cd46b7ac523dfc7d334e34e7150e1615f21d0757554e488d52bc9b` |
| location.csv | 50 | `00023e57d9898ca509c49083bbdd0b952928763a33c8f4967b30561240f81191` |
| oryva.sqlite3 | 6,492,158 table rows | `c3ce2309e38ccadb7ca2b099026b9ae0d0c427afa3ba6dc81c48b64c865d11a1` |
| production_capacity.csv | 36,000 | `133418294975cbc6094b4f21f4ad1ffe5ed22bcaa71040bc96ac0ffdc7f507e3` |
| purchase_order.csv | 10,000 | `45b169852aa1ecc357fa721aee35462e22f2414c31ca2ec2bcb6d539ab8815eb` |
| purchase_order_line.csv | 10,000 | `c17e440d4fd3686da900ee6aa6a14d019dc2652264db73717318154a58ac632b` |
| sku.csv | 3,000 | `c78cacbdd3ad27ae833f8f766dd9a28f71a1882d8aded61963e0d4cceaed06b1` |
| sku_location_assortment.csv | 115,800 | `380e4387bfe2edfea989d7b2ce607d63221aaa75b302ee3bcaea85e3d7cce2aa` |
| sku_substitute.csv | 750 | `42f2b1e68f5c00bd34a400e6b4384e62ef43fcc46d7a488adde90bc2eee4a100` |
| source_manifest.json | — | `bc849ec8762f19651549a7a8e9cf67832c8921dd58a4ab841c2c63d9127e128c` |
| supplier.csv | 500 | `43b69c19b0154ab25cf4838a34092612ac7bc8dd90ea167bac0d92054df0f3ad` |
| supplier_capacity.csv | 6,000 | `6faac1c75a7d07898e1e8c7fab43dc9eb90527fde955af45db283f1861b2ebc4` |
| transport_delay.csv | 10,000 | `5acf8abe7b1e8906314d2d9a72494868b05d9ba2b7458ab375525fd83e55e549` |

## Starter preset: all-output reproducibility

Both runs used seed `20261022`, 24 SKUs, 6 locations, 12 weeks, 12 suppliers, 36 POs, then ran planner and generator validation. `generate_data.py compare` compared all 29 files: CSVs (including planner outputs), JSON summaries, the SQLite database, and source manifest. CSV row counts, SQLite total rows, and SHA-256 matched.

| Output | Rows | SHA-256 (both runs) |
|---|---:|---|
| bill_of_material.csv | 7 | `64d63965b6254afa654ee1a21d2a1ef381d61ca33a54beda9c81d2c2ed9627a6` |
| edge_case_detection.json | — | `0965a8562617b17dbeeeae087472a754241f72a3169cb3b953b521c99807a609` |
| edge_case_injections.csv | 5 | `d271297dd1d27aaef75455a55bd468a72cdaf06e16e44f62d30c085269b56582` |
| forecast_demand.csv | 1,308 | `aaf233c7a1911a8ecec1a664748ed5f6931c51b4c77429962a977adf8e3c360f` |
| ground_truth.csv | 5 | `5e204a396d101255a8e0445ed652c60dd3b162146afa2f9c4c8a001cb5f187b5` |
| inventory.csv | 109 | `7694613c8d9312a1f26ec167f6f858848475ac4847095f8609272e9b0030e3a8` |
| issue_case.csv | 5 | `e8494e9c8238642a932721f345a71e24f4db182383c4e378b6126192711beeca` |
| issue_case_record.csv | 10 | `5266d29ce6a8c803aa1f5dec558ee9037b5a11fa99edb9156b96b74eae39e667` |
| lead_time.csv | 218 | `34e23fbcb252561b6f0fb51c3cc1289926d39f1729901cb15c27e598362e638f` |
| lifecycle_history.csv | 180 | `927dbac8f8ed87b7ff6c3a783f7598747e993c5fc87eec27a709e077e6e1f7ff` |
| location.csv | 6 | `c63216bcde1c9e40bf0477f019160ba4d6d6885564c66995b2b550ab5a9a44f5` |
| mitigations.csv | 211 | `2fcbeacf3a165196a699ff6ea7331c2c75567b8b1857e3d31b916a7ce67c66fa` |
| oryva.sqlite3 | 2,065 table rows | `8f7f4f92e94ccaf6b1f3cd4ebe869dc53273e4a73c885121b72792b3d1e4e811` |
| planner_validation.json | — | `8ac37fe94d5b183a357a4f8e8a2bb08a60a714875b6165dfc0ef11d44133b657` |
| production_capacity.csv | 24 | `93f668bee9cf4fd1b721110c057f65579c26df5349a2834f234df571f5f95e58` |
| production_capacity_weekly.csv | 288 | `c7629ebf2c1cb1d56a77edb34301191cad1753d5650479e30a02b581c151f3c3` |
| production_plan.csv | 6 | `b8ceec7f6e0a6075d3eed0a1d7bf7e669923d7cfaaed0fedf63d0edc6177d3fb` |
| projected_balance.csv | 1,308 | `6e80324b019ad14ba46ce35de0eecacd26f971f33fdd62e53d79de563be9ef3a` |
| purchase_order.csv | 36 | `19ec824eb7c20d40e7ad2763a1d348bc7501c328925610363f9fa9f4a8dd50a8` |
| purchase_order_line.csv | 36 | `1c1bc0d0026ac1e5ba4984f1ca85218d35a0737fec2e55ba5abfd366c5b5410a` |
| shortage_ranking.csv | 147 | `47dab7daecac74565fda247fe45bd415ae27142480167d98e9107b1b67e9763b` |
| shortages.csv | 147 | `cde2f270a296aef71f36adbbf54699edecfc1bd28542301f2497852c9371e3b8` |
| sku.csv | 24 | `9093ece8a3f69ce1e88c507f2d07c3309983e05093b5ed309d79f8598cf9512d` |
| sku_location_assortment.csv | 109 | `b5a3a0a679e51f8b63e3febeef0a5e704b094a7ad518e4612263221b57e22f5e` |
| sku_substitute.csv | 6 | `e0c3f49b864028c9e7d7d448625049739fcfb87f1eadae1a4566bbb5eb6a13fd` |
| source_manifest.json | — | `275668a613802db1fdfd85ac05b59c4683620ceba77102ba024b6636dfaa847b` |
| supplier.csv | 12 | `f381ea25fc53fbba75f00931307157e937521cfcd67b4f51ba166c2e8766dc96` |
| supplier_capacity.csv | 48 | `0b51172b0ac4c8832dccc4b0ed48d3738b53819c22d4e7e5e51772aa68b856a8` |
| transport_delay.csv | 36 | `c524100a8fbedd9b796c3e1ed3bdb8882e73ba32d491c6fbfc454c58b26` |

Run directories: `/private/tmp/oryva-repro-step4-1` and `/private/tmp/oryva-repro-step4-2`.
