import unittest

import pandas as pd

from trial_units import add_trial_unit_columns, TRIAL_KEY, TRIAL_LABEL, SOURCE_ROW
from analysis import fit_trial_model, environmental_data


class TrialUnitTests(unittest.TestCase):
    def test_prod_groups_by_dev_not_location_or_trial_id(self):
        data = pd.DataFrame({"area": ["PROD-PLACEMENT"] * 4,
            "trial_id": ["1", "1", "2", "3"], "trial_name": ["T"] * 4,
            "year": [2025] * 4,
            "location_name": ["L1", "L1", "L2", "L3"], "environment_dev_file": ["E1", "E2", "E1", "E1"]})
        result = add_trial_unit_columns(data)
        self.assertEqual(result[TRIAL_LABEL].tolist(), [
            "2025 | T | E1", "2025 | T | E2", "2025 | T | E1", "2025 | T | E1",
        ])
        self.assertEqual(result[TRIAL_KEY].nunique(), 2)
        self.assertEqual(result[SOURCE_ROW].tolist(), [2, 3, 4, 5])
        self.assertNotIn(TRIAL_KEY, data)

    def test_regular_areas_remain_trial_location(self):
        data = pd.DataFrame({"area": ["Trigo", None], "trial_id": [1, 2], "trial_name": ["T", "T"],
                             "year": [2025, 2026],
                             "location_name": ["L1", "L2"], "environment_dev_file": ["E", "E"]})
        result = add_trial_unit_columns(data)
        self.assertEqual(result[TRIAL_LABEL].tolist(), ["2025 | T | L1", "2026 | T | L2"])
        with self.assertRaisesRegex(ValueError, "fora de PROD-PLACEMENT"):
            add_trial_unit_columns(data.assign(trial_id=1))

    def test_missing_dev_is_not_replaced_by_location(self):
        data = pd.DataFrame({"area": [" prod-placement "], "trial_id": [1], "trial_name": ["T"],
                             "year": [2025],
                             "location_name": ["L"], "environment_dev_file": [" "]})
        with self.assertRaisesRegex(ValueError, "substituto"):
            add_trial_unit_columns(data)
        with self.assertRaisesRegex(ValueError, "environment_dev_file"):
            add_trial_unit_columns(data.drop(columns="environment_dev_file"))
        result = add_trial_unit_columns(data.assign(environment_dev_file="E").drop(columns="location_name"))
        self.assertEqual(result[TRIAL_LABEL].iloc[0], "2025 | T | E")

    def test_mixed_rules_and_separator_collisions_stay_distinct(self):
        data = pd.DataFrame({"area": ["PROD-PLACEMENT", "Trigo", "Trigo", "Trigo"],
            "trial_id": [1, 2, 3, 4], "trial_name": ["T", "T", "A | B", "A"],
            "year": [2025] * 4,
            "location_name": ["ignored", "E", "C", "B | C"], "environment_dev_file": ["E"] * 4})
        result = add_trial_unit_columns(data)
        self.assertEqual(result[TRIAL_KEY].nunique(), 4)
        self.assertEqual(result[TRIAL_LABEL].nunique(), 4)
        self.assertIn("[DEV]", result[TRIAL_LABEL].iloc[0])
        self.assertIn("[Local]", result[TRIAL_LABEL].iloc[1])

    def test_dev_units_reach_model_predictions_and_environmental_index(self):
        records = []
        for env in range(3):
            for genotype in range(3):
                for rep in range(4):
                    records.append({"area": "PROD-PLACEMENT", "trial_name": "T", "trial_id": 1,
                        "year": 2025,
                        "location_name": "L", "environment_dev_file": f"E{env}",
                        "germplasm_name": f"G{genotype}", "yield": 3000 + env * 300 + genotype * 100 + rep * 10})
        data = add_trial_unit_columns(pd.DataFrame(records))
        fit = fit_trial_model(data, method="BLUE", interaction=False)
        self.assertEqual(len(fit["cells"]), 9)
        self.assertEqual(fit["genotypes"]["Ensaios"].tolist(), [3, 3, 3])
        self.assertEqual(environmental_data(data, fit)[TRIAL_LABEL].nunique(), 3)

    def test_year_separates_otherwise_identical_trial_units(self):
        data = pd.DataFrame({
            "area": ["Trigo", "Trigo"],
            "year": [2025, 2026],
            "trial_id": [1, 2],
            "trial_name": ["T", "T"],
            "location_name": ["L", "L"],
        })
        result = add_trial_unit_columns(data)
        self.assertEqual(result[TRIAL_KEY].nunique(), 2)
        self.assertEqual(result[TRIAL_LABEL].tolist(), ["2025 | T | L", "2026 | T | L"])

    def test_year_is_required_and_cannot_be_empty(self):
        data = pd.DataFrame({"trial_id": [1], "trial_name": ["T"], "location_name": ["L"]})
        with self.assertRaisesRegex(ValueError, "year"):
            add_trial_unit_columns(data)
        with self.assertRaisesRegex(ValueError, "year"):
            add_trial_unit_columns(data.assign(year=None))


if __name__ == "__main__":
    unittest.main()
