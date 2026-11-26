"""Streamlit app for the core-satellite trend portfolio.
Run locally:  streamlit run app.py
All calculations come from strategy.py (same code as the notebook)."""

import altair as alt
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

# --- risk-adjusted overview --------------------------------------------------
st.subheader("Risk-adjusted returns")
risk = sg.risk_adjusted_table(results, rf_bt)
ratios = ["Calmar", "Sortino", "Sharpe", "Return / volatility"]
names = list(results.columns)
colors = alt.Scale(domain=names, range=["#257de0", "#f47230", "#00b894"])

# Which portfolio is best on each ratio (higher is better) - computed, not assumed
best = risk[ratios].idxmax()
wins = [m for m in ratios if best[m] == "Strategy"]
losses = [m for m in ratios if best[m] != "Strategy"]

r1, r2, r3 = st.columns(3)
r1.metric("Strategy Calmar (CAGR / max DD)", f"{risk.loc['Strategy', 'Calmar']:.2f}",
          f"{risk.loc['Strategy', 'Calmar'] - risk.loc['60/40 SPY/AGG', 'Calmar']:+.2f} vs 60/40")
r2.metric("Strategy Sortino", f"{risk.loc['Strategy', 'Sortino']:.2f}",
          f"{risk.loc['Strategy', 'Sortino'] - risk.loc['60/40 SPY/AGG', 'Sortino']:+.2f} vs 60/40")
r3.metric("Strategy return / volatility", f"{risk.loc['Strategy', 'Return / volatility']:.2f}",
          f"{risk.loc['Strategy', 'Return / volatility'] - risk.loc['60/40 SPY/AGG', 'Return / volatility']:+.2f} vs 60/40")

long = (risk[ratios].reset_index(names="Portfolio")
        .melt(id_vars="Portfolio", var_name="Measure", value_name="Value"))
base = alt.Chart(long).encode(
    x=alt.X("Portfolio:N", axis=None, sort=names),
    y=alt.Y("Value:Q", title="Ratio (higher is better)"),
)
bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
    color=alt.Color("Portfolio:N", scale=colors, sort=names,
                    legend=alt.Legend(orient="top", title=None)),
    tooltip=["Portfolio", "Measure", alt.Tooltip("Value:Q", format=".2f")],
)
labels = base.mark_text(dy=-6, fontSize=11).encode(text=alt.Text("Value:Q", format=".2f"))
chart = (bars + labels).properties(width=150, height=280).facet(
    column=alt.Column("Measure:N", sort=ratios, title=None,
                      header=alt.Header(labelFontSize=13, labelOrient="bottom")))
st.altair_chart(chart)

if wins:
    st.markdown("**The strategy ranks first on:** " + ", ".join(wins) + ".")
if losses:
    st.markdown("**Not first on:** " + ", ".join(f"{m} (best: {best[m]})" for m in losses) + ".")
st.caption("Calmar = CAGR / |max drawdown|. Sortino = excess return over T-bills per unit of "
           "downside deviation. Sharpe = excess return per unit of total volatility. "
           "All measures use the full backtest and net-of-cost monthly returns.")

st.subheader("Drawdown from previous peak")
dd = (sg.drawdowns(results).reset_index(names="Date")
      .melt(id_vars="Date", var_name="Portfolio", value_name="Drawdown"))
dd_chart = alt.Chart(dd).mark_line(strokeWidth=2).encode(
    x=alt.X("Date:T", title=None),
    y=alt.Y("Drawdown:Q", axis=alt.Axis(format="%"), title="Drawdown"),
    color=alt.Color("Portfolio:N", scale=colors, sort=names,
                    legend=alt.Legend(orient="top", title=None)),
    tooltip=[alt.Tooltip("Date:T", format="%b %Y"), "Portfolio",
             alt.Tooltip("Drawdown:Q", format=".1%")],
).properties(height=300)
st.altair_chart(dd_chart, width="stretch")

with st.expander("Risk-adjusted measures as a table"):
    st.dataframe(risk.style.format({c: "{:.2f}" for c in ratios}
                                   | {"CAGR": "{:.2%}", "Max drawdown": "{:.2%}"}))

st.subheader("Strategy weights over time")
st.area_chart(weights.loc[sg.BACKTEST_START:])
