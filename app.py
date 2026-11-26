"""Streamlit app for the core-satellite trend portfolio.
Run locally:  streamlit run app.py
All calculations come from strategy.py (same code as the notebook)."""

import streamlit as st
import strategy as sg

st.set_page_config(page_title="Family Office Trend Portfolio", layout="wide")
st.title("Core-satellite trend portfolio")
st.caption("60% AGG core, 40% satellite in SPY, GLD and DBC with a trend filter "
           "and inverse-volatility weights. Unused satellite weight goes to T-bills.")


@st.cache_data(ttl=24 * 3600)
def load_data():
    return sg.download_data(sg.DOWNLOAD_START, sg.BACKTEST_END)


# --- user inputs ------------------------------------------------------------
st.sidebar.header("Assumptions")
ma_months = st.sidebar.slider("Moving-average length (months)", 3, 12, sg.MA_MONTHS)
core_weight = st.sidebar.slider("Core weight in AGG", 0.0, 1.0, sg.CORE_WEIGHT, 0.05)
cost_bps = st.sidebar.slider("Transaction cost (bps per unit turnover)", 0, 50, sg.COST_BPS)
st.sidebar.caption(f"Backtest: {sg.BACKTEST_START} to {sg.BACKTEST_END}, monthly, USD.")

# --- calculations -----------------------------------------------------------
prices, rf = load_data()
results, rf_bt, weights, res_strat = sg.run_all(prices, rf, core_weight, ma_months, cost_bps)
table = sg.performance_table(results, rf_bt)

# --- output -----------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Strategy ann. return", f"{table.loc['Strategy', 'Ann. return']:.2%}")
c2.metric("Strategy Sharpe", f"{table.loc['Strategy', 'Sharpe']:.2f}",
          f"{table.loc['Strategy', 'Sharpe'] - table.loc['60/40 SPY/AGG', 'Sharpe']:+.2f} vs 60/40")
c3.metric("Strategy max drawdown", f"{table.loc['Strategy', 'Max drawdown']:.2%}")

st.subheader("Cumulative performance (start = 1, net of costs)")
st.line_chart(sg.cumulative(results))

st.subheader("Performance measures")
pct = ["Ann. return", "CAGR", "Volatility", "Alpha (ann.)", "Tracking error", "Max drawdown"]
st.dataframe(table.style.format({c: "{:.2%}" for c in pct}
                                | {c: "{:.2f}" for c in ["Sharpe", "Beta", "Information ratio"]}))
st.caption("Beta and alpha vs the 60/40 SPY/AGG benchmark (excess returns over T-bills). "
           "Beta is not annualized.")

st.subheader("Strategy weights over time")
st.area_chart(weights.loc[sg.BACKTEST_START:])
