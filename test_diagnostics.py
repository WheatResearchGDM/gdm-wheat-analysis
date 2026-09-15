import unittest

import numpy as np
import pandas as pd

from analysis import (GENOTYPE, TRIAL, diagnostic_data, environmental_data,
                      fit_trial_model, refit_without_outliers)
from trial_units import SOURCE_ROW
from test_analysis import trial_data


class DiagnosticTests(unittest.TestCase):
    def data(self):
        data = trial_data()
        data[SOURCE_ROW] = np.arange(len(data)) + 10
        data["plot_id"] = "DUPLICATED-ID"
        data.loc[0, "yield"] += 20000
        data.loc[1, "yield"] = np.nan
        data.index = [0] * len(data)  # Labels cannot be used as observation identity.
        return data

    def test_identity_after_missing_rows_and_qq_sort(self):
        data = self.data()
        fitted = fit_trial_model(data, method="BLUE", interaction=False)
        diag = diagnostic_data(fitted)
        self.assertEqual(fitted["omitted"], 1)
        self.assertNotIn(11, diag[SOURCE_ROW].values)
        self.assertEqual(diag.sort_values("residual").iloc[-1][SOURCE_ROW], 10)
        np.testing.assert_allclose(diag["observed"] - diag["fitted"], diag["residual"])
        np.testing.assert_allclose(diag["scaled_residual"], diag["residual"] / np.sqrt(fitted["result"].scale))
        self.assertEqual(diag.loc[diag[SOURCE_ROW].eq(10), "plot_label"].iloc[0], "DUPLICATED-ID")
        self.assertIn(10, diag.loc[diag["outlier"], SOURCE_ROW].tolist())

    def test_refit_excludes_row_not_all_duplicate_plot_ids(self):
        data = self.data()
        original = data.copy(deep=True)
        fitted = fit_trial_model(data, method="BLUE", interaction=False)
        new = refit_without_outliers(data, fitted, [10])
        self.assertTrue(data.equals(original))
        self.assertEqual(new["excluded_rows"], [10])
        self.assertEqual(new["nobs"], fitted["nobs"] - 1)
        self.assertEqual(new["omitted"], 1)
        self.assertNotIn(10, new["diagnostics"][SOURCE_ROW].values)
        self.assertEqual(new["genotypes"]["n"].sum(), new["nobs"])
        self.assertEqual(new["cells"]["n"].sum(), new["nobs"])
        self.assertEqual(new["exclusion_audit"][SOURCE_ROW].tolist(), [10])
        self.assertEqual(len(environmental_data(data, new)), len(new["cells"]))
        expected = fit_trial_model(data.loc[data[SOURCE_ROW].ne(10)], method="BLUE", interaction=False)
        np.testing.assert_allclose(new["genotypes"]["Estimativa"], expected["genotypes"]["Estimativa"])

    def test_invalid_exclusions_and_stale_data_do_not_mutate_fit(self):
        data = self.data()
        fitted = fit_trial_model(data, method="BLUE", interaction=False)
        with self.assertRaisesRegex(ValueError, "sinalizadas"):
            refit_without_outliers(data, fitted, [11])  # Missing response was not fitted.
        with self.assertRaisesRegex(ValueError, "datacut"):
            refit_without_outliers(data.iloc[1:], fitted, [10])
        self.assertEqual(fitted["excluded_rows"], [])
        self.assertTrue(fitted["exclusion_audit"].empty)
        self.assertFalse(diagnostic_data(fitted, 100)["outlier"].any())

    def test_zero_variance_cannot_flag_outliers(self):
        fitted = {"diagnostics": pd.DataFrame({"scaled_residual": [np.nan, np.nan]})}
        self.assertFalse(diagnostic_data(fitted)["outlier"].any())

    def test_blup_refit_preserves_effects_and_cumulative_audit(self):
        data = trial_data()
        data[SOURCE_ROW] = np.arange(len(data)) + 2
        data.loc[0, "yield"] += 20000
        data.loc[1, "yield"] -= 15000
        original = fit_trial_model(data, method="BLUP", interaction=False)
        first = refit_without_outliers(data, original, [2])
        second = refit_without_outliers(data, first, [3])
        self.assertEqual(second["excluded_rows"], [2, 3])
        self.assertEqual(second["exclusion_audit"][SOURCE_ROW].tolist(), [2, 3])
        self.assertEqual(second["nobs"], original["nobs"] - 2)
        self.assertEqual(second["method"], "BLUP")
        self.assertEqual(second["random"], original["random"])
        self.assertEqual(second["fixed"], original["fixed"])
        self.assertFalse(second["interaction"])
        # Every output is based on the new fit, not a row-filtered old prediction.
        independent = fit_trial_model(data.iloc[2:], method="BLUP", interaction=False)
        np.testing.assert_allclose(second["cells"]["predicted"], independent["cells"]["predicted"], atol=1e-6)


if __name__ == "__main__":
    unittest.main()
