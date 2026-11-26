"""Small hand-checkable tests of the strategy functions (loaded from the notebook via app.py)."""
import unittest

import numpy as np
import pandas as pd
import app as sg


class BacktestChecks(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2020-01-31", periods=4, freq="ME")
        self.rets = pd.DataFrame({"A": [0, .1, -.2, .05], "B": [0, 0, .02, .01]}, index=self.dates)
        self.fixed = pd.DataFrame({"A": .5, "B": .5}, index=self.dates)

    def test_weights_decided_at_t_earn_returns_of_t_plus_1(self):
        target = pd.DataFrame({"A": [1., 0., 1., 0.], "B": [0., 1., 0., 1.]}, index=self.dates)
        out = sg.backtest(target, self.rets, self.dates[1], self.dates[-1], cost_bps=0)
        np.testing.assert_allclose(out["gross"], [.1, .02, .05])

    def test_turnover_uses_drifted_weights_and_first_month_buys_everything(self):
        out = sg.backtest(self.fixed, self.rets, self.dates[1], self.dates[-1], cost_bps=10)
        self.assertAlmostEqual(out["turnover"].iloc[0], 1)
        self.assertAlmostEqual(out["turnover"].iloc[1], abs(.5 - .55 / 1.05) + abs(.5 - .50 / 1.05))
        self.assertAlmostEqual(out["net"].iloc[0], .05 - .001)

    def test_buy_and_hold_trades_only_once(self):
        out = sg.backtest(self.fixed, self.rets, self.dates[1], self.dates[-1], cost_bps=0, rebalance=False)
        np.testing.assert_allclose(out["turnover"].iloc[1:], 0, atol=1e-15)
        self.assertAlmostEqual((1 + out["net"]).prod(), .5 * 1.1 * .8 * 1.05 + .5 * 1.02 * 1.01)

    def test_missing_returns_raise_instead_of_counting_as_zero(self):
        self.rets.loc[self.dates[2], "A"] = np.nan
        with self.assertRaises(ValueError):
            sg.backtest(self.fixed, self.rets, self.dates[1], self.dates[-1])

    def test_first_month_loss_counts_as_drawdown(self):
        r = pd.Series([-.2, .1], index=self.dates[:2])
        self.assertAlmostEqual(sg.drawdowns(r).max(), .2)
        self.assertAlmostEqual(sg.cumulative(r).iloc[0], 1.)


class StrategyChecks(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2006-02-28", periods=30, freq="ME")
        rng = np.random.default_rng(2270)
        self.prices = pd.DataFrame(100 * np.cumprod(1 + rng.normal(.002, .03, (30, 4)), axis=0),
                                   index=dates, columns=sg.ASSETS)
        self.rf = pd.Series(.001, index=dates)

    def test_weights_sum_to_one_and_start_after_full_warmup(self):
        w = sg.strategy_weights(self.prices)
        self.assertEqual(w.index[0], pd.Timestamp("2007-02-28"))
        np.testing.assert_allclose(w.sum(axis=1), 1)
        np.testing.assert_allclose(w[sg.CORE], .6)

    def test_all_satellites_off_means_60_agg_40_tbills(self):
        for i, asset in enumerate(sg.SATELLITE):
            self.prices[asset] = 100 * np.exp(-np.linspace(0, 1 + i * .2, len(self.prices)) ** 1.2)
        w = sg.strategy_weights(self.prices)
        np.testing.assert_allclose(w[sg.TBILL], .4)
        np.testing.assert_allclose(w[sg.SATELLITE], 0)

    def test_future_prices_cannot_change_past_results(self):
        changed = self.prices.copy()
        changed.iloc[23:] *= 1.8
        end = str(self.prices.index[22].date())
        pd.testing.assert_frame_equal(sg.run_all(self.prices, self.rf, end=end)[0],
                                      sg.run_all(changed, self.rf, end=end)[0])

    def test_metrics_match_regression_and_manual_sharpe(self):
        results, cash, _, _ = sg.run_all(self.prices, self.rf, end="2008-07-31")
        table = sg.performance_table(results, cash)
        p, b = results["Strategy"] - cash, results[sg.BENCHMARK] - cash
        alpha, beta = np.linalg.lstsq(np.column_stack([np.ones(len(b)), b]), p, rcond=None)[0]
        self.assertAlmostEqual(table.loc["Strategy", "Beta"], beta)
        self.assertAlmostEqual(table.loc["Strategy", "Alpha (ann.)"], 12 * alpha)
        self.assertAlmostEqual(table.loc["Strategy", "Sharpe"], np.sqrt(12) * p.mean() / p.std())
        self.assertTrue(pd.isna(table.loc[sg.BENCHMARK, "Information ratio"]))


if __name__ == "__main__":
    unittest.main()
