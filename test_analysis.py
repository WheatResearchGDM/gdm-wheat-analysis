"""Regression checks with balanced and unbalanced replicated trials."""
import unittest

import numpy as np
import pandas as pd

from analysis import (
    BLOCK, GENOTYPE, NESTED_BLOCK, TRIAL, data_fingerprint,
    environmental_data, fit_trial_model,
)


def trial_data(unbalanced=False):
    rng = np.random.default_rng(241)
    rows = []
    for g in range(5):
        for e in range(5):
            ge = rng.normal(0, 150)
            n = 8 if not unbalanced or (g + e) % 2 == 0 else 2
            for rep in range(n):
                rows.append({GENOTYPE: f"G{g}", TRIAL: f"VCU | Local {e}",
                             "year": 2025 + (e >= 2), BLOCK: rep + 1,
                             "yield": 3000 + 200 * g + 250 * e + ge + rng.normal(0, 250),
                             "rep": str(rep)})
    return pd.DataFrame(rows)


class ModelTests(unittest.TestCase):
    def test_blue_balanced_equals_marginal_means_without_interaction(self):
        data = trial_data()
        fit = fit_trial_model(data, method="BLUE", interaction=False)
        expected = data.groupby(GENOTYPE)["yield"].mean().sort_index()
        actual = fit["genotypes"].set_index(GENOTYPE)["Estimativa"].sort_index()
        np.testing.assert_allclose(actual, expected, rtol=1e-9)
        self.assertNotIn("Efeito genotípico", fit["genotypes"])

    def test_unbalanced_blue_is_adjusted_not_raw_mean(self):
        data = trial_data(True)
        fit = fit_trial_model(data, method="BLUE", interaction=False)
        actual = fit["genotypes"].set_index(GENOTYPE)["Estimativa"].sort_index()
        raw = data.groupby(GENOTYPE)["yield"].mean().sort_index()
        self.assertGreater(np.max(np.abs(actual - raw)), 10)
        # Independent reference: OLS fitted on a balanced genotype/trial grid.
        import statsmodels.formula.api as smf
        result = smf.ols('Q("yield") ~ C(germplasm_name) + C(trial_unit_label)', data).fit()
        grid = data[[GENOTYPE, TRIAL]].drop_duplicates().copy()
        grid["p"] = result.predict(grid)
        np.testing.assert_allclose(actual, grid.groupby(GENOTYPE)["p"].mean(), rtol=1e-9)

    def test_blup_shrinkage_and_cell_prediction(self):
        data = trial_data()
        fit = fit_trial_model(data, method="BLUP", interaction=False)
        effects = fit["genotypes"].set_index(GENOTYPE)["Efeito genotípico"].sort_index()
        raw = data.groupby(GENOTYPE)["yield"].mean().sort_index()
        variances = fit["variance"].set_index("Componente")["Variância"]
        shrinkage = variances[GENOTYPE] / (variances[GENOTYPE] + variances["Residual"] / 40)
        np.testing.assert_allclose(effects, shrinkage * (raw - raw.mean()), atol=1e-5)
        self.assertEqual(len(fit["cells"]), 25)
        self.assertTrue(np.isfinite(fit["cells"]["predicted"]).all())

    def test_interaction_predictions_include_random_effects(self):
        data = trial_data()
        fit = fit_trial_model(data, method="BLUP", interaction=True)
        by_cell = data.assign(fitted=fit["fitted"]).groupby([GENOTYPE, TRIAL])["fitted"].mean()
        cells = fit["cells"].set_index([GENOTYPE, TRIAL])["predicted"]
        np.testing.assert_allclose(cells.sort_index(), by_cell.sort_index(), atol=1e-5)
        self.assertIn("Genótipo × ensaio", fit["variance"]["Componente"].tolist())
        # Independent dense formula implementation checks coefficient ordering.
        import statsmodels.formula.api as smf
        ref_data = data.assign(pair=data[GENOTYPE] + "__" + data[TRIAL])
        reference = smf.mixedlm(
            'Q("yield") ~ C(trial_unit_label)', ref_data,
            groups=np.ones(len(data)), re_formula="0",
            vc_formula={"ge": "0 + C(pair)", "geno": "0 + C(germplasm_name)"},
        ).fit(reml=True, method="lbfgs", disp=False)
        np.testing.assert_allclose(fit["fitted"], reference.fittedvalues, atol=.01)

    def test_random_trial_and_no_observed_pair_extrapolation(self):
        data = trial_data()
        data = data.loc[~(data[GENOTYPE].eq("G0") & data[TRIAL].eq("VCU | Local 0"))]
        fit = fit_trial_model(data, method="BLUE", fixed=[], random=[TRIAL], interaction=False)
        self.assertEqual(len(fit["cells"]), 24)
        self.assertEqual(len(environmental_data(data, fit)), 24)
        changed = data.iloc[:-1]
        with self.assertRaisesRegex(ValueError, "Reajuste"):
            environmental_data(changed, fit)

    def test_year_is_categorical_and_blocks_are_nested_in_trials(self):
        data = trial_data()
        fit = fit_trial_model(
            data, method="BLUP", fixed=["year"],
            random=[TRIAL, BLOCK], interaction=False,
        )
        coefficient_names = fit["fixed_coefficients"]["Efeito"].tolist()
        self.assertTrue(any("C(Q('year'))" in name for name in coefficient_names))
        self.assertIn(NESTED_BLOCK, fit["variance"]["Componente"].tolist())
        self.assertEqual(fit["random_level_counts"][NESTED_BLOCK], 5 * 8)
        self.assertIn(BLOCK, fit["random"])
        self.assertNotIn(NESTED_BLOCK, fit["random"])

    def test_block_requires_repetitions_within_trial(self):
        data = trial_data().assign(num_repetitions=1)
        with self.assertRaisesRegex(ValueError, "mais de um bloco"):
            fit_trial_model(
                data, method="BLUP", fixed=["year"],
                random=[TRIAL, BLOCK], interaction=False,
            )

    def test_invalid_fixed_effects_and_missing_values(self):
        data = trial_data()
        data["duplicate_trial"] = data[TRIAL]
        with self.assertRaisesRegex(ValueError, "confundidos"):
            fit_trial_model(data, fixed=[TRIAL, "duplicate_trial"])
        data.loc[0, "yield"] = np.nan
        data.loc[1, "yield"] = np.inf
        fit = fit_trial_model(data, method="BLUE", interaction=False)
        self.assertEqual(fit["omitted"], 2)

    def test_raw_index_weights_each_genotype_once(self):
        data = pd.DataFrame({GENOTYPE: ["A", "A", "B"], TRIAL: ["T | X"] * 3,
                             "yield": [100, 100, 400]})
        cells = environmental_data(data)
        self.assertEqual(cells["yield"].mean(), 250)
        self.assertNotEqual(data_fingerprint(data), data_fingerprint(data.iloc[:-1]))


if __name__ == "__main__":
    unittest.main()
