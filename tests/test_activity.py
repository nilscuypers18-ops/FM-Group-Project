"""Reconcile the activity audit to the engine, using deterministic prices."""
import unittest

import numpy as np
import pandas as pd

import app as model
from activity import rebalance_history


class ActivityChecks(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2006-02-28", periods=40, freq="ME")
        rng = np.random.default_rng(2270)
        self.prices = pd.DataFrame(100 * np.cumprod(1 + rng.normal(.002, .04, (40, 4)), axis=0),
                                   index=dates, columns=model.ASSETS)
        self.rf = pd.Series(.001, index=dates)

    def history(self, core=.6, cost=10, ma=10, capital=100_000.):
        detail = model.run_all(self.prices, self.rf, core, ma, cost,
                               end=str(self.prices.index[-1].date()))[-1]
        months, decisions = rebalance_history(model, self.prices, detail, ma, capital)
        return detail, months, decisions

    def test_every_trade_and_cost_reconciles_with_engine(self):
        detail, months, decisions = self.history(cost=25)
        grouped = decisions.groupby("return_month", sort=True)
        np.testing.assert_allclose(grouped.trade_pp.apply(lambda v: v.abs().sum()) / 100, detail.turnover)
        np.testing.assert_allclose(grouped.cost_usd.sum(), months.cost_usd, atol=1e-10)
        np.testing.assert_allclose(grouped.target_weight.sum(), 1)
        np.testing.assert_allclose(decisions.target_change_pp + decisions.drift_correction_pp, decisions.trade_pp)
        np.testing.assert_allclose(months.cost_usd, months.traded_usd * .0025)
        self.assertAlmostEqual(months.closing_value.iloc[-1], 100_000 * (1 + detail.net).prod())
        np.testing.assert_allclose(months.opening_value.iloc[1:], months.closing_value.iloc[:-1])
        self.assertEqual(months.signal_date.iloc[0], pd.Timestamp("2007-02-28"))
        self.assertEqual(months.return_month.iloc[0], pd.Timestamp("2007-03-31"))
        self.assertEqual(months.event.iloc[0], "Opening allocation")
        self.assertTrue((decisions.cost_bps == 25).all())
        self.assertTrue((months.initial_capital_usd == 100_000).all())
        self.assertAlmostEqual(months.turnover.iloc[0], 1)
        np.testing.assert_allclose(grouped.trade_pp.sum().iloc[1:], 0, atol=1e-12)

    def test_cash_and_trend_evidence_uses_signal_month_not_return_month(self):
        _, months, decisions = self.history()
        signals = model.trend_signal(self.prices[model.SATELLITE])
        for date, block in decisions.groupby("signal_date"):
            satellites = block.set_index("asset").loc[model.SATELLITE]
            expected = signals.loc[date].astype(bool)
            np.testing.assert_allclose(satellites.adjusted_close, self.prices.loc[date, model.SATELLITE])
            np.testing.assert_allclose(satellites.target_weight, satellites.satellite_budget * expected)
            cash = block.set_index("asset").loc[model.TBILL, "target_weight"]
            self.assertAlmostEqual(cash, satellites.loc[~expected, "satellite_budget"].sum())
        changed = self.prices.copy()
        changed.iloc[-1] *= 2
        detail = model.run_all(changed, self.rf, end=str(changed.index[-1].date()))[-1]
        _, revised = rebalance_history(model, changed, detail, 10)
        pd.testing.assert_frame_equal(decisions, revised)

    def test_constant_targets_still_explain_drift_trades(self):
        for i, asset in enumerate(model.SATELLITE):
            self.prices[asset] = 100 * np.exp(-np.linspace(0, 1 + i * .2, len(self.prices)) ** 1.2)
        _, _, decisions = self.history()
        later = decisions.loc[decisions.return_month > decisions.return_month.min()]
        core = later.loc[later.asset == model.CORE]
        np.testing.assert_allclose(core.target_change_pp, 0)
        self.assertTrue((core.action != "Hold").any())
        self.assertTrue(core.reason.str.contains("Correct market drift").all())
        off = later.loc[later.asset.isin(model.SATELLITE)]
        self.assertTrue((off.action == "Hold").all())
        self.assertTrue(off.reason.str.contains("Trend remains off").all())

    def test_all_core_zero_cost_and_capital_scaling(self):
        _, months, decisions = self.history(core=1, cost=0)
        self.assertTrue((months.event.iloc[1:] == "No trades").all())
        self.assertEqual((decisions.action != "Hold").sum(), 1)
        np.testing.assert_allclose(months.cost_usd, 0)
        _, doubled, larger = self.history(core=1, cost=0, capital=200_000.)
        np.testing.assert_allclose(doubled.closing_value, 2 * months.closing_value)
        np.testing.assert_allclose(larger.trade_usd, 2 * decisions.trade_usd)
        for invalid in [0, -100, np.nan, np.inf]:
            with self.assertRaises(ValueError):
                self.history(capital=invalid)


if __name__ == "__main__":
    unittest.main()
