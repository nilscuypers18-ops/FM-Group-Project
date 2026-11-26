"""Financial-logic checks on small examples, independent of market downloads."""
import ast
import inspect
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
import strategy as sg


class BacktestChecks(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2020-01-31", periods=4, freq="ME")
        self.rets = pd.DataFrame({"A": [0, .1, -.2, .05],
                                  "B": [0, 0, .02, .01]}, index=self.dates)

    def test_lag_uses_previous_decision(self):
        target = pd.DataFrame({"A": [1., 0., 1., 0.], "B": [0., 1., 0., 1.]}, index=self.dates)
        out = sg.backtest(target, self.rets, self.dates[1], self.dates[-1], cost_bps=0)
        np.testing.assert_allclose(out["gross"], [.1, .02, .05])
        out2 = sg.backtest(target, self.rets, self.dates[2], self.dates[-1], cost_bps=0, execution_lag=2)
        np.testing.assert_allclose(out2["gross"], [-.2, .01])

    def test_drift_drives_rebalance_turnover(self):
        target = sg.fixed_weights(self.dates, {"A": .5, "B": .5})
        out = sg.backtest(target, self.rets, self.dates[1], self.dates[-1], cost_bps=10)
        # After 10% return on A: dollar holdings .55 and .50, total 1.05.
        expected_turnover = abs(.5 - .55/1.05) + abs(.5 - .50/1.05)
        self.assertAlmostEqual(out["turnover"].iloc[0], 1)
        self.assertAlmostEqual(out["turnover"].iloc[1], expected_turnover)
        self.assertAlmostEqual(out["net"].iloc[0], .05 - .001)

    def test_buy_hold_is_fixed_units_not_constant_weights(self):
        target = sg.fixed_weights(self.dates, {"A": .5, "B": .5})
        out = sg.backtest(target, self.rets, self.dates[1], self.dates[-1],
                          cost_bps=0, rebalance=False)
        np.testing.assert_allclose(out["turnover"].iloc[1:], 0, atol=1e-15)
        expected_wealth = .5 * 1.1 * .8 * 1.05 + .5 * 1.0 * 1.02 * 1.01
        self.assertAlmostEqual((1 + out["net"]).prod(), expected_wealth)
        self.assertAlmostEqual(out["weight_A"].iloc[1], .55 / 1.05)

    def test_missing_returns_are_not_zero(self):
        target = sg.fixed_weights(self.dates, {"A": .5, "B": .5})
        self.rets.loc[self.dates[2], "A"] = np.nan
        with self.assertRaises(ValueError):
            sg.backtest(target, self.rets, self.dates[1], self.dates[-1])

    def test_missing_target_does_not_compress_time(self):
        target = sg.fixed_weights(self.dates, {"A": .5, "B": .5}).drop(self.dates[1])
        with self.assertRaises(ValueError):
            sg.backtest(target, self.rets, self.dates[1], self.dates[-1])

    def test_no_prior_decision_raises_instead_of_negative_index_wrap(self):
        target = sg.fixed_weights(self.dates, {"A": 1.})
        with self.assertRaises(ValueError):
            sg.backtest(target, self.rets, self.dates[0], self.dates[-1])

    def test_first_month_loss_is_a_drawdown(self):
        returns = pd.Series([-.2, .1], index=self.dates[:2])
        self.assertAlmostEqual(sg.max_drawdown(returns), .2)
        self.assertAlmostEqual(sg.cumulative(returns).iloc[0], 1.)

    def test_invalid_weights_and_sample_are_rejected(self):
        target = sg.fixed_weights(self.dates, {"A": .7, "B": .5})
        with self.assertRaises(ValueError):
            sg.backtest(target, self.rets, self.dates[1], self.dates[-1])
        with self.assertRaises(ValueError):
            sg.month_grid("2020-01-01", "2020-04-30")


class SignalAndDataChecks(unittest.TestCase):
    def make_prices(self):
        dates = pd.date_range("2006-02-28", periods=30, freq="ME")
        rng = np.random.default_rng(2270)
        values = 100 * np.cumprod(1 + rng.normal(.002, .03, (30, 4)), axis=0)
        return pd.DataFrame(values, index=dates, columns=sg.ASSETS)

    def test_full_volatility_warmup(self):
        prices = self.make_prices()
        self.assertTrue(sg.rolling_vol(prices).iloc[:12].isna().all().all())
        self.assertEqual(sg.strategy_weights(prices).index[0], pd.Timestamp("2007-02-28"))
        with self.assertRaises(ValueError):
            sg.run_all(prices, pd.Series(.001, index=prices.index), start="2007-01-31", end="2008-07-31")

    def test_future_prices_cannot_change_past_decisions_or_returns(self):
        prices = self.make_prices()
        changed = prices.copy()
        changed.iloc[23:] *= 1.8
        cutoff = prices.index[22]
        pd.testing.assert_frame_equal(sg.strategy_weights(prices).loc[:cutoff],
                                      sg.strategy_weights(changed).loc[:cutoff])
        rf = pd.Series(.001, index=prices.index)
        old = sg.run_all(prices, rf, end=str(cutoff.date()))[0]
        new = sg.run_all(changed, rf, end=str(cutoff.date()))[0]
        pd.testing.assert_frame_equal(old, new)

    def test_all_satellites_off_goes_to_cash(self):
        prices = self.make_prices()
        for i, asset in enumerate(sg.SATELLITE):
            prices[asset] = 100 * np.exp(-np.linspace(0, 1+i*.2, len(prices))**1.2)
        weights = sg.strategy_weights(prices)
        np.testing.assert_allclose(weights[sg.CORE], .6)
        np.testing.assert_allclose(weights[sg.TBILL], .4)
        np.testing.assert_allclose(weights[sg.SATELLITE], 0)

    def test_cash_yield_is_lagged(self):
        yields = pd.Series([12., 24., 36.])
        out = sg.tbill_monthly_return(yields)
        self.assertTrue(pd.isna(out.iloc[0]))
        np.testing.assert_allclose(out.iloc[1:], [.01, .02])

    def test_missing_month_duplicate_and_stale_quotes_raise(self):
        dates = pd.to_datetime(["2020-01-31", "2020-02-28", "2020-03-31"])
        raw = pd.DataFrame(100., index=dates, columns=sg.ASSETS+[sg.RF_TICKER])
        prices, rf, audit = sg.prepare_data(raw, "2020-01-01", "2020-03-31")
        self.assertEqual(len(prices), 3)
        self.assertEqual(audit.loc["2020-02-29", "SPY age days"], 1)
        for bad in [raw.drop(dates[1]), pd.concat([raw, raw.iloc[:1]]),
                    raw.rename(index={dates[-1]: pd.Timestamp("2020-03-10")})]:
            with self.assertRaises(ValueError):
                sg.prepare_data(bad, "2020-01-01", "2020-03-31")

    def test_metrics_agree_with_ols_and_manual_ratios(self):
        prices = self.make_prices()
        rf = pd.Series(.001, index=prices.index)
        results, cash, _, _ = sg.run_all(prices, rf, end="2008-07-31")
        table = sg.performance_table(results, cash)
        p = results["Strategy"] - cash
        b = results[sg.BENCHMARK] - cash
        alpha, beta = np.linalg.lstsq(np.column_stack([np.ones(len(b)), b]), p, rcond=None)[0]
        self.assertAlmostEqual(table.loc["Strategy", "Beta"], beta)
        self.assertAlmostEqual(table.loc["Strategy", "Alpha (ann.)"], 12*alpha)
        self.assertAlmostEqual(table.loc["Strategy", "Sharpe"], np.sqrt(12)*p.mean()/p.std())
        self.assertAlmostEqual(table.loc[sg.BENCHMARK, "Beta"], 1.)
        self.assertTrue(pd.isna(table.loc[sg.BENCHMARK, "Information ratio"]))

    def test_notebook_embeds_every_shared_function_verbatim(self):
        root = Path(__file__).resolve().parents[1]
        nb = json.loads((root / "strategy_backtest.ipynb").read_text(encoding="utf-8"))
        embedded = {}
        for cell in nb["cells"]:
            if cell["cell_type"] == "code" and "shared-calculations" in cell["metadata"].get("tags", []):
                src = "".join(cell["source"])
                embedded.update({n.name: ast.get_source_segment(src, n) for n in ast.parse(src).body
                                 if isinstance(n, ast.FunctionDef)})
        for name, function in inspect.getmembers(sg, inspect.isfunction):
            self.assertIn(name, embedded)
            self.assertEqual(inspect.getsource(function).strip(), embedded[name].strip())


if __name__ == "__main__":
    unittest.main()
