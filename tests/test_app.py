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
        # A new session with no cache must expose the source error to the user.
        import streamlit as st
        st.cache_data.clear()
        with patch("yfinance.download", side_effect=ValueError("API test failure")):
            failed = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            failed.run(timeout=60)
            self.assertEqual(len(failed.exception), 0)
            self.assertIn("API test failure", failed.error[0].value)


if __name__ == "__main__":
    unittest.main()
