import csv
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent
STARTER = ROOT / "data" / "starter"


class StarterPlannerEvidence(unittest.TestCase):
    def test_validation_passed(self):
        evidence = json.loads((STARTER / "planner_validation.json").read_text())
        for key in ("balances_reconciled", "all_five_cases_labeled", "shortages_explainable",
                    "mitigation_tradeoffs_present", "mitigations_all_feasible", "max_three_mitigations_per_shortage"):
            self.assertTrue(evidence[key], key)

    def test_mitigations_are_feasible_and_capped(self):
        with (STARTER / "mitigations.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        counts = Counter(row["shortage_id"] for row in rows)
        self.assertTrue(rows)
        self.assertLessEqual(max(counts.values()), 3)
        self.assertTrue(all(row["feasible"] == "1" for row in rows))
        self.assertTrue(all(row["mitigation_option_id"].endswith(("-01", "-02", "-03")) for row in rows))

    def test_ground_truth_is_separate_and_complete(self):
        with (STARTER / "ground_truth.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        expected = {"INBOUND_INVENTORY_COUNTED_TWICE", "UNAPPROVED_SUBSTITUTE_SKU",
                    "SUPPLIER_CAPACITY_EXCEEDED", "SHORTAGE_WITHOUT_LEAD_TIME", "UOM_MISMATCH"}
        self.assertEqual({row["issue_type"] for row in rows}, expected)
        self.assertTrue(all(row["source_record_refs"] for row in rows))

    def test_source_manifest_is_synthetic_and_seeded(self):
        manifest = json.loads((STARTER / "source_manifest.json").read_text())
        self.assertEqual(manifest["seed"], 20261022)
        self.assertEqual(manifest["source"]["type"], "synthetic")
        self.assertEqual(manifest["source"]["external_sources"], [])

    def test_repository_exports_are_under_50mb(self):
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or not path.is_file():
                continue
            self.assertLess(path.stat().st_size, 50 * 1024 * 1024, str(path.relative_to(ROOT)))


if __name__ == "__main__":
    unittest.main()
