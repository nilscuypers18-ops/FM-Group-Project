"""Check compounding, missing months, and crisis recovery conventions."""
import unittest

import numpy as np
import pandas as pd

import app as model
from fund_analytics import calendar_returns, monthly_grid, crisis_summary


class FundAnalyticsChecks(unittest.TestCase):
    def test_calendar_compounds_and_distinguishes_missing_from_flat_months(self):
        dates = pd.date_range("2020-03-31", periods=12, freq="ME")
        returns = pd.DataFrame({"Strategy": [.1, -.1, 0.] + [.01] * 9}, index=dates)
        annual = calendar_returns(returns)
        self.assertEqual(annual.index.tolist(), ["2020*", "2021*"])
        self.assertAlmostEqual(annual.loc["2020*", "Strategy"], 1.1 * .9 * 1.01 ** 7 - 1)
        grid = monthly_grid(returns.Strategy)
        self.assertTrue(np.isnan(grid.loc[2020, 1]))
        self.assertEqual(grid.loc[2020, 5], 0)
        self.assertAlmostEqual((1 + annual.Strategy).prod(), (1 + returns.Strategy).prod())

    def test_complete_year_has_no_partial_marker(self):
        dates = pd.date_range("2020-01-31", periods=12, freq="ME")
        self.assertEqual(calendar_returns(pd.DataFrame({"Strategy": .01}, index=dates)).index.tolist(), ["2020"])

    def test_crisis_includes_initial_loss_and_searches_later_recovery(self):
        dates = pd.date_range("2020-01-31", periods=6, freq="ME")
        # Starting value 1 -> .8 -> .72 -> .9 -> .99 -> 1.089.
        results = pd.DataFrame({"Strategy": [-.2, -.1, .25, .1, .1, 0],
                                "No loss": [.1] * 6, "Unrecovered": [-.1] * 6}, index=dates)
        summary = crisis_summary(model, results, "2020-01", "2020-03")
        self.assertAlmostEqual(summary.loc["Strategy", "Crisis return"], -.1)
        self.assertAlmostEqual(summary.loc["Strategy", "Max drawdown"], .28)
        self.assertEqual(summary.loc["Strategy", "Months to recover"], 3)
        self.assertEqual(summary.loc["Strategy", "Recovery date"], pd.Timestamp("2020-05-31"))
        self.assertEqual(summary.loc["No loss", "Months to recover"], 0)
        self.assertTrue(pd.isna(summary.loc["Unrecovered", "Months to recover"]))
        self.assertTrue(crisis_summary(model, results.iloc[1:], "2020-01", "2020-03").empty)
        self.assertTrue(crisis_summary(model, results, "2019-01", "2019-03").empty)


if __name__ == "__main__":
    unittest.main()
