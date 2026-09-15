import unittest

import numpy as np
import pandas as pd

from analysis import GENOTYPE, TRIAL, fit_trial_model
from reporting import cycle_data, head_to_head_wins, model_equation, reference_regression
from test_analysis import trial_data


class ReportingTests(unittest.TestCase):
    def test_wins_ties_and_unpaired_trials(self):
        values = pd.DataFrame({TRIAL: ["e1", "e1", "e2", "e2", "e3", "e3", "e4"],
            GENOTYPE: ["A", "B", "A", "B", "A", "B", "A"],
            "genotype_yield": [10, 9, 6, 8, 5, 5 + 1e-10, 50]})
        result = head_to_head_wins(values, "A", "B")
        self.assertEqual(result["Ensaios"].tolist(), [1, 1, 1])
        self.assertAlmostEqual(result["Percentual"].sum(), 100.)

    def test_cycle_links_gid_not_commercial_name_and_equal_trial_weights(self):
        data = pd.DataFrame({GENOTYPE: ["A", "A", "A", "B", "C"],
            "gid": ["1", "1", "1", "2", "3"], TRIAL: ["x", "x", "y", "x", "x"],
            "yield": [10, 10, 20, 30, 40]})
        materials = pd.DataFrame({"gid": ["1", "2", "3"], "days_to_spike": ["60,5", 80, None],
            "category": ["CHECK", "COMERCIAL", "EXPERIMENTAL"], "commercial_name": ["wrong1", "wrong2", "wrong3"]})
        points, excluded = cycle_data(data, materials)
        self.assertEqual(excluded, 1)
        self.assertEqual(points[GENOTYPE].tolist(), ["A", "B"])
        self.assertEqual(points["Estimativa"].tolist(), [15, 30])
        self.assertEqual(points["n"].tolist(), [3, 1])
        self.assertEqual(points["days_to_spike"].tolist(), [60.5, 80.])
        self.assertEqual(reference_regression(points)["n"], 2)
        # Ambiguous mapping is not silently assigned to the first GID.
        bad = pd.concat([data, data.iloc[[0]].assign(gid="other")])
        points, excluded = cycle_data(bad, materials)
        self.assertEqual(excluded, 2)
        self.assertEqual(points[GENOTYPE].tolist(), ["B"])

    def test_counts_only_used_records_and_estimated_cycle(self):
        data = trial_data(True)
        data["gid"] = data[GENOTYPE].str.removeprefix("G")
        data.loc[0, "yield"] = np.nan
        fit = fit_trial_model(data, method="BLUE", interaction=False)
        self.assertEqual(fit["genotypes"]["n"].sum(), fit["nobs"])
        self.assertEqual(fit["genotypes"].set_index(GENOTYPE).loc["G0", "n"],
                         data.loc[data[GENOTYPE].eq("G0"), "yield"].count())
        materials = pd.DataFrame({"gid": [str(i) for i in range(5)],
                                  "days_to_spike": range(60, 65), "category": ["CHECK"] * 5})
        points, excluded = cycle_data(data, materials, fit)
        self.assertEqual(excluded, 0)
        np.testing.assert_allclose(points["Estimativa"], fit["genotypes"]["Estimativa"])
        with self.assertRaises(ValueError):
            cycle_data(data.iloc[1:], materials, fit)

    def test_regression_only_selected_references_and_edge_cases(self):
        points = pd.DataFrame({"days_to_spike": [10, 20, 30], "Estimativa": [30, 50, 1000],
                               "Categoria": ["Check", "Comercial", "Experimental"]})
        regression = reference_regression(points)
        self.assertAlmostEqual(regression["slope"], 2.)
        self.assertEqual(regression["n"], 2)
        self.assertIsNone(reference_regression(points.iloc[1:]))
        self.assertIsNone(reference_regression(points.assign(days_to_spike=10)))

    def test_equation_follows_selected_effects(self):
        blue = model_equation("BLUE", [TRIAL], [], False)
        self.assertIn("G_{g(i)}", blue)
        self.assertIn("F_{1,i}", blue)
        self.assertNotIn("U_{1,i}", blue)
        self.assertNotIn("times", blue)
        blup = model_equation("BLUP", [], [TRIAL], True)
        self.assertIn("u_{g(i)}", blup)
        self.assertIn("U_{1,i}", blup)
        self.assertIn("times", blup)


if __name__ == "__main__":
    unittest.main()
