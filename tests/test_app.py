"""Exercise the app's actual controls with deterministic data, without an API."""
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest
import app as sg


class AppChecks(unittest.TestCase):
    def test_controls_recompute_shared_results_and_handle_data_failure(self):
        dates = pd.bdate_range(sg.DOWNLOAD_START, sg.BACKTEST_END)
        rng = np.random.default_rng(2270)
        raw = pd.DataFrame(100 * np.cumprod(1 + rng.normal(.0002, .008, (len(dates), 4)), axis=0),
                           index=dates, columns=sg.ASSETS)
        raw[sg.RF_TICKER] = 3.0
        prices, rf, _ = sg.prepare_data(raw)
        with patch("yfinance.download", return_value=pd.concat({"Close": raw}, axis=1)):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            app.run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            app.button(key="enter_manager").click().run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            expected = sg.performance_table(*sg.run_all(prices, rf)[:2]).loc["Strategy"]
            self.assertEqual(app.metric[0].value, f"{expected['Ann. return']:.2%}")
            app.sidebar.slider[0].set_value(12)
            app.sidebar.slider[1].set_value(.8)
            app.sidebar.slider[2].set_value(25)
            app.run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            expected = sg.performance_table(*sg.run_all(prices, rf, .8, 12, 25)[:2]).loc["Strategy"]
            self.assertEqual(app.metric[0].value, f"{expected['Ann. return']:.2%}")
            self.assertEqual(app.metric[2].value, f"{expected['Max drawdown']:.2%}")
            for core in [0., 1.]:
                app.sidebar.slider[1].set_value(core)
                app.run(timeout=60)
                self.assertEqual(len(app.exception), 0)
            # Deferred chart sections must also render when opened.
            for section in ("details_allocation", "details_costs", "details_rolling"):
                app.session_state[section] = True
            app.run(timeout=60)
            self.assertEqual(len(app.exception), 0)
        # A new session with no cache must expose the source error to the user.
        import streamlit as st
        st.cache_data.clear()
        with patch("yfinance.download", side_effect=ValueError("API test failure")):
            failed = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            failed.run(timeout=60)
            failed.button(key="enter_investor").click().run(timeout=60)
            self.assertEqual(len(failed.exception), 0)
            self.assertIn("API test failure", failed.error[0].value)

    def test_portals_navigation_and_investor_defaults(self):
        import streamlit as st
        st.cache_data.clear()
        dates = pd.bdate_range(sg.DOWNLOAD_START, sg.BACKTEST_END)
        rng = np.random.default_rng(2270)
        raw = pd.DataFrame(100 * np.cumprod(1 + rng.normal(.0002, .008, (len(dates), 4)), axis=0),
                           index=dates, columns=sg.ASSETS)
        raw[sg.RF_TICKER] = 3.0
        with patch("yfinance.download", return_value=pd.concat({"Close": raw}, axis=1)) as download:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            app.run(timeout=60)
            download.assert_not_called()
            self.assertEqual(len(app.text_input), 0)
            app.button(key="enter_manager").click().run(timeout=60)
            app.sidebar.slider[1].set_value(.8).run(timeout=60)
            app.radio(key="portal_page").set_value("Team Overview").run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.metric), 0)
            self.assertTrue(any("Nils Andreas Cuypers" in item.value for item in app.get("html")))
            app.radio(key="portal_page").set_value("Trade History").run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.sidebar.slider[1].value, .8)
            self.assertTrue(any("Monthly rebalance log" in item.value for item in app.subheader))
            self.assertGreater(len(app.dataframe), 4)
            app.button[0].click().run(timeout=60)
            app.button(key="enter_investor").click().run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.sidebar.slider), 0)
            prices, rf, _ = sg.prepare_data(raw)
            expected = sg.performance_table(*sg.run_all(prices, rf)[:2]).loc["Strategy"]
            self.assertEqual(app.metric[0].value, f"{expected['Ann. return']:.2%}")

    def test_informational_pages_work_when_market_data_are_unavailable(self):
        import streamlit as st
        st.cache_data.clear()
        with patch("yfinance.download", side_effect=ValueError("Offline")) as download:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            app.run(timeout=60)
            app.button(key="enter_investor").click().run(timeout=60)
            self.assertIn("Offline", app.error[0].value)
            calls = download.call_count
            app.radio(key="portal_page").set_value("Team Overview").run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 0)
            self.assertEqual(download.call_count, calls)
            app.radio(key="portal_page").set_value("Trade History").run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertIn("Offline", app.error[0].value)
            self.assertEqual(len(app.dataframe), 0)

    def test_trade_history_filters_details_and_manager_scenario(self):
        import streamlit as st
        st.cache_data.clear()
        dates = pd.bdate_range(sg.DOWNLOAD_START, sg.BACKTEST_END)
        rng = np.random.default_rng(2270)
        raw = pd.DataFrame(100 * np.cumprod(1 + rng.normal(.0002, .008, (len(dates), 4)), axis=0),
                           index=dates, columns=sg.ASSETS)
        raw[sg.RF_TICKER] = 3.0
        with patch("yfinance.download", return_value=pd.concat({"Close": raw}, axis=1)):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            app.run(timeout=60)
            app.button(key="enter_manager").click().run(timeout=60)
            app.radio(key="portal_page").set_value("Trade History").run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.dataframe[0].value), 236)
            app.sidebar.slider[1].set_value(1.).run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("100% AGG core" in item.value for item in app.caption))
            self.assertEqual(app.metric[0].value, "0")
            self.assertEqual(app.metric[1].value, "1")
            # Latest month has no trades, but the review and holdings remain visible.
            self.assertEqual(app.dataframe[0].value.iloc[0]["Activity"], "No trades")
            app.multiselect(key="history_assets").set_value(["SPY"]).run(timeout=60)
            self.assertTrue(any("No records match" in item.value for item in app.info))
            app.multiselect(key="history_actions").set_value(["Hold"]).run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.dataframe[-1].value), 236)
            app.number_input(key="history_capital").set_value(200_000.).run(timeout=60)
            self.assertEqual(app.metric[2].value, "$200,000.00")
            app.date_input(key="history_dates").set_value((pd.Timestamp("2007-02-28").date(),
                                                           pd.Timestamp("2007-02-28").date())).run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.dataframe[0].value), 1)
            self.assertEqual(app.dataframe[1].value.loc[0, "Before trade · drifted"], 0)
            app.date_input(key="history_dates").set_value((pd.Timestamp("2007-03-01").date(),
                                                           pd.Timestamp("2007-03-02").date())).run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any("No monthly signal dates" in item.value for item in app.info))
            app.radio(key="portal_page").set_value("Overview").run(timeout=60)
            self.assertEqual(app.sidebar.slider[1].value, 1.)


if __name__ == "__main__":
    unittest.main()
