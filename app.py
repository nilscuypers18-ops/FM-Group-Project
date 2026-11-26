"""Streamlit app for the core-satellite trend portfolio.
Run locally:  streamlit run app.py
All calculations come from strategy.py (same code as the notebook)."""

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import streamlit as st
import strategy as sg

st.set_page_config(page_title="Family Office Trend Portfolio", layout="wide")
st.title("Core-satellite trend portfolio")
st.caption("Monthly trend and inverse-volatility allocation for a family office. "
           "Unused satellite weight goes to an approximate T-bill cash return.")


@st.cache_data(ttl=24 * 3600)
def load_data():
    raw = sg.download_raw(sg.DOWNLOAD_START, sg.BACKTEST_END)
    prices, rf, audit = sg.prepare_data(raw, sg.DOWNLOAD_START, sg.BACKTEST_END)
    return raw, prices, rf, audit


# --- user inputs ------------------------------------------------------------
st.sidebar.header("Assumptions")
ma_months = st.sidebar.slider("Moving-average length (months)", 3, 12, sg.MA_MONTHS)
core_weight = st.sidebar.slider("Core weight in AGG", 0.0, 1.0, sg.CORE_WEIGHT, 0.05)
cost_bps = st.sidebar.slider("Transaction cost (bps per unit turnover)", 0, 50, sg.COST_BPS)
st.sidebar.caption(f"Backtest: {sg.BACKTEST_START} to {sg.BACKTEST_END}, monthly, USD.")
st.sidebar.caption("Volatility: 12 complete monthly returns. Benchmark remains 60% SPY / 40% AGG.")

# --- calculations -----------------------------------------------------------
try:
    raw, prices, rf, audit = load_data()
    results, rf_bt, weights, res_strat = sg.run_all(prices, rf, core_weight, ma_months, cost_bps)
except (ValueError, KeyError, OSError) as exc:
    st.error(f"Data or calculation check failed: {exc}")
    st.info("Check the source data and connection, then reload. Missing returns are never replaced with zero.")
    st.stop()
table = sg.performance_table(results, rf_bt)

# --- output -----------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Strategy ann. return", f"{table.loc['Strategy', 'Ann. return']:.2%}")
c2.metric("Strategy Sharpe", f"{table.loc['Strategy', 'Sharpe']:.2f}",
          f"{table.loc['Strategy', 'Sharpe'] - table.loc['60/40 SPY/AGG', 'Sharpe']:+.2f} vs 60/40")
c3.metric("Strategy max drawdown", f"{table.loc['Strategy', 'Max drawdown']:.2%}")
st.caption(f"Current allocation rule: {core_weight:.0%} AGG core; {1-core_weight:.0%} satellite, "
           f"{ma_months}-month SMA; {cost_bps} bps costs. Drawdowns are positive losses from a peak.")


def show_lines(data, title, ylabel, percent=False):
    fig, ax = plt.subplots(figsize=(11, 4.5))
    data.plot(ax=ax, title=title)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    if percent:
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

st.subheader("Cumulative performance (start = 1, net of costs)")
show_lines(sg.cumulative(results), "Cumulative performance, net of costs", "Value of USD 1")

st.subheader("Performance measures")
pct = ["Ann. return", "CAGR", "Volatility", "Alpha (ann.)", "Tracking error", "Max drawdown"]
st.dataframe(table.style.format({c: "{:.2%}" for c in pct}
                                | {c: "{:.2f}" for c in ["Sharpe", "Beta", "Information ratio"]}))
st.caption("Arithmetic return = 12 × monthly mean; volatility = √12 × sample standard deviation. "
           "Sharpe uses excess returns over the cash proxy. Alpha/beta use excess returns vs 60/40. "
           "Beta is not annualized. Information ratio uses active returns / tracking error.")

st.subheader("Weights actually held during each return month")
positions = res_strat.filter(like="weight_").rename(columns=lambda c: c.removeprefix("weight_"))
fig, ax = plt.subplots(figsize=(11, 4))
positions.plot.area(ax=ax, ylim=(0, 1))
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.set_ylabel("Portfolio weight")
ax.legend(ncol=5, loc="upper left")
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

st.subheader("Drawdowns")
show_lines(sg.drawdowns(results), "Loss from the high water mark", "Loss from peak", percent=True)

st.subheader("Implementation: turnover and costs")
gross_net = res_strat[["gross", "net"]].rename(columns={"gross": "Strategy gross", "net": "Strategy net"})
show_lines(sg.cumulative(gross_net), "Before and after transaction costs", "Value of USD 1")
st.write(f"Average monthly turnover after opening: {res_strat['turnover'].iloc[1:].mean():.2%}")
st.caption("Turnover counts buys plus sells relative to drifted holdings, including proxy-cash trades. "
           "The opening purchase costs one unit of turnover. Net return = gross return − turnover × cost rate. "
           "Buy & hold trades only at inception; 60/40 rebalances monthly. No final liquidation charge.")

with st.expander("Rolling risk measures (60 months)"):
    rolling = sg.rolling_performance(results, rf_bt)
    for metric in rolling:
        show_lines(rolling[metric], f"60-month rolling {metric}", metric, metric == "Alpha (ann.)")

with st.expander("Data checks and assumptions"):
    st.write(f"Raw daily data: {raw.shape[0]} rows; monthly prices: {len(prices)} rows; "
             f"backtest: {len(results)} months.")
    st.dataframe(sg.data_summary(raw))
    st.dataframe(audit.tail())
    st.caption("Yahoo Finance adjusted ETF closes, daily to calendar month-end; no forward fill or dropped months. "
               "Source quotes older than seven calendar days cause an error. Check the recorded quote dates. "
               "Cash return = preceding ^IRX annual quoted yield / 100 / 12. This is an approximation, "
               "not an investable T-bill total-return index.")
    st.caption("Signal-close execution is optimistic; a shift avoids crediting the signal month's return, "
               "but cannot guarantee the assumed fill. Taxes, inflation and market impact are omitted. "
               "ETF selection has hindsight risk; these results are historical, not an unseen validation sample. "
               "A large AGG allocation retains duration and credit risk and does not guarantee capital preservation.")

st.download_button("Download monthly net returns", results.to_csv().encode("utf-8"),
                   file_name="monthly_net_returns.csv", mime="text/csv")
