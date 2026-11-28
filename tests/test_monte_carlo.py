"""Check wealth compounding, scaling, calibration and reproducible scenarios."""
import unittest

import numpy as np
import pandas as pd

import app as model


class MonteCarloChecks(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(43)
        self.returns = pd.DataFrame(
            rng.normal([.004, .003], [.025, .02], (120, 2)),
            index=pd.date_range("2010-01-31", periods=120, freq="ME"),
            columns=["Strategy", model.BENCHMARK],
        )

    def test_constant_returns_compound_exactly_from_month_zero(self):
        returns = self.returns.copy()
        returns[:] = [.01, -.005]
        result = model.monte_carlo(returns, years=2, n_sim=100)
        for name, rate in zip(returns, [.01, -.005]):
            expected = 100_000 * (1 + rate) ** np.arange(25)
            for column in result["bands"][name]:
                np.testing.assert_allclose(result["bands"][name][column], expected)
        self.assertEqual(result["summary"].loc["Strategy", "Probability of loss"], 0)
        self.assertEqual(result["summary"].loc[model.BENCHMARK, "Probability of loss"], 1)

    def test_monthly_scaling_matches_analytical_mean(self):
        result = model.monte_carlo(self.returns, years=1, n_sim=20_000)
        mu = self.returns.mean().to_numpy()
        sigma = self.returns.std(ddof=1).to_numpy()
        calibration = result["calibration"]
        np.testing.assert_allclose(calibration["Monthly mean"], mu)
        np.testing.assert_allclose(calibration["Monthly volatility"], sigma)
        np.testing.assert_allclose(calibration["Annualised mean"], mu * 12)
        np.testing.assert_allclose(calibration["Annualised volatility"], sigma * np.sqrt(12))
        expected_mean = 100_000 * (1 + mu) ** 12
        expected_var = 100_000**2 * (((1 + mu)**2 + sigma**2)**12 - (1 + mu)**24)
        error = np.abs(result["summary"]["Mean end wealth"].to_numpy() - expected_mean)
        self.assertTrue((error < 5 * np.sqrt(expected_var / 20_000)).all())

    def test_identical_portfolios_share_the_same_worlds(self):
        self.returns[model.BENCHMARK] = self.returns["Strategy"]
        result = model.monte_carlo(self.returns, years=1, n_sim=100)
        self.assertAlmostEqual(result["correlation"], 1.)
        np.testing.assert_allclose(result["bands"]["Strategy"], result["bands"][model.BENCHMARK])

    def test_seed_and_capital_scaling_and_ordered_percentiles(self):
        a = model.monte_carlo(self.returns, n_sim=100, years=1)
        repeat = model.monte_carlo(self.returns, n_sim=100, years=1)
        doubled = model.monte_carlo(self.returns, initial=200_000, n_sim=100, years=1)
        pd.testing.assert_frame_equal(a["summary"], repeat["summary"])
        for name, band in a["bands"].items():
            pd.testing.assert_frame_equal(band, repeat["bands"][name])
            np.testing.assert_allclose(doubled["bands"][name], 2 * band)
            self.assertTrue((np.diff(band.to_numpy(), axis=1) >= 0).all())
            self.assertTrue(band.iloc[0].eq(100_000).all())
        np.testing.assert_array_equal(a["summary"]["Probability of loss"],
                                      doubled["summary"]["Probability of loss"])
        different = model.monte_carlo(self.returns, n_sim=100, years=1, seed=17)
        self.assertFalse(a["summary"].equals(different["summary"]))

    def test_missing_invalid_or_unordered_returns_are_rejected(self):
        invalid = [self.returns.iloc[:23], self.returns.iloc[::-1], self.returns.drop(self.returns.index[20]),
                   self.returns.iloc[:, :1], self.returns.rename(columns={model.BENCHMARK: "Strategy"})]
        for value in [np.nan, np.inf, -1.]:
            frame = self.returns.copy()
            frame.iloc[0, 0] = value
            invalid.append(frame)
        for frame in invalid:
            with self.subTest(frame=frame.shape), self.assertRaises(ValueError):
                model.monte_carlo(frame, n_sim=100)
        for kwargs in [{"initial": 0}, {"initial": np.inf}, {"years": 0}, {"years": 1.5},
                       {"n_sim": 10}, {"seed": -1}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                model.monte_carlo(self.returns, **kwargs)

    def test_impossible_normal_draws_raise_instead_of_silent_clipping(self):
        high_vol = self.returns.copy()
        high_vol.iloc[::2] = -.9
        high_vol.iloc[1::2] = 2.
        with self.assertRaisesRegex(ValueError, "no returns were clipped"):
            model.monte_carlo(high_vol, n_sim=100)


if __name__ == "__main__":
    unittest.main()
