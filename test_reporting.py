import unittest

import numpy as np
import pandas as pd

from analysis import GENOTYPE, TRIAL, fit_trial_model
from reporting import (
    connectivity_cell_style, cycle_data, genotype_connectivity, genotype_count,
    head_to_head_wins, model_equation, protein_data, reference_regression,
    selection_tiers,
)
from test_analysis import trial_data


class ReportingTests(unittest.TestCase):
    def test_connectivity_counts_unique_gids_shared_between_trials(self):
        data = pd.DataFrame({
            TRIAL: ["T1", "T1", "T1", "T2", "T2", "T3"],
            "gid": ["G1", "G1", "G2", "G2", "G3", "G4"],
        })
        matrix = genotype_connectivity(data)
        self.assertEqual(matrix.loc["T1", "T1"], 2)
        self.assertEqual(matrix.loc["T1", "T2"], 1)
        self.assertEqual(matrix.loc["T1", "T3"], 0)
        self.assertTrue(matrix.equals(matrix.T))
        self.assertIn("#F2A09A", connectivity_cell_style(3, 12))
        self.assertIn("rgb(246, 205, 73)", connectivity_cell_style(4, 12))
        self.assertIn("rgb(91, 166, 86)", connectivity_cell_style(12, 12))

    def test_genotype_count_uses_gid_instead_of_collapsing_equal_names(self):
        data = pd.DataFrame({
            "gid": [101, 101, 202, 202],
            GENOTYPE: ["Mesmo nome", "Mesmo nome", "Mesmo nome", "Mesmo nome"],
        })
        self.assertEqual(genotype_count(data), 2)
        self.assertEqual(genotype_count(data.drop(columns="gid")), 1)

    def test_protein_is_raw_trial_weighted_with_raw_or_estimated_yield(self):
        data = pd.DataFrame({
            GENOTYPE: ["A", "A", "A", "B", "B"],
            "gid": ["1", "1", "1", "2", "2"],
            TRIAL: ["T1", "T1", "T2", "T1", "T2"],
            "yield": [100, 100, 300, 200, 400],
            "protein": ["10,0", "14,0", "20,0", "11,0", "13,0"],
        })
        materials = pd.DataFrame({
            "gid": ["1", "2"], "category": ["CHECK", "EXPERIMENTAL"],
        })
        raw, excluded = protein_data(data, materials)
        self.assertEqual(excluded, 0)
        raw = raw.set_index(GENOTYPE)
        self.assertEqual(raw.loc["A", "Proteína"], 16)
        self.assertEqual(raw.loc["A", "Estimativa"], 200)
        self.assertEqual(raw.loc["A", "n_proteína"], 3)

        fit_data = pd.concat([data] * 5, ignore_index=True)
        fit_data[TRIAL] = [f"{trial}-{copy}" for copy in range(5) for trial in data[TRIAL]]
        fit = fit_trial_model(fit_data, method="BLUE", interaction=False)
        estimated, _ = protein_data(fit_data, materials, fit)
        expected = fit["genotypes"].set_index(GENOTYPE)["Estimativa"]
        np.testing.assert_allclose(
            estimated.set_index(GENOTYPE)["Estimativa"].sort_index(), expected.sort_index(),
        )

    def test_selection_tiers_and_check_baseline(self):
        points = pd.DataFrame({
            GENOTYPE: ["Check", "Comercial", "Verde", "Amarelo", "Vermelho"],
            "Categoria": ["Check", "Comercial", "Experimental", "Experimental", "Experimental"],
            "Estimativa": [100, 140, 106, 103, 100],
        })
        classified, check_mean = selection_tiers(points)
        tiers = classified.set_index(GENOTYPE)["Tier"]
        self.assertEqual(check_mean, 100)
        self.assertEqual(tiers["Check"], "Checks + Comerciais")
        self.assertEqual(tiers["Comercial"], "Checks + Comerciais")
        self.assertEqual(tiers["Verde"], "Tier > 5%")
        self.assertEqual(tiers["Amarelo"], "Tier 0,1% a 5%")
        self.assertEqual(tiers["Vermelho"], "Tier ≤ 0%")

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
