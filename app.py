"""Streamlit app for the core-satellite trend portfolio.
Run locally:  streamlit run app.py
The strategy functions below are the same as in strategy_backtest.ipynb.
If you change the logic here, make the same change in the notebook."""

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Default settings (change them here or pass them as function arguments)
# ---------------------------------------------------------------------------
CORE = "AGG"
SATELLITE = ["SPY", "GLD", "DBC"]
TBILL = "TBILL"                       # column name we use for the cash asset
RF_TICKER = "^IRX"                    # 13-week T-bill yield, in percent p.a.

DOWNLOAD_START = "2006-02-01"         # DBC starts trading Feb 2006
BACKTEST_START = "2007-01-31"         # first month with a portfolio return
BACKTEST_END = "2026-10-31"           # last month with a portfolio return

CORE_WEIGHT = 0.60
MA_MONTHS = 10
VOL_MONTHS = 12
COST_BPS = 10


# ---------------------------------------------------------------------------
# 1. Data
# ---------------------------------------------------------------------------
def download_data(start=DOWNLOAD_START, end=BACKTEST_END):
    """Download daily adjusted closes from Yahoo Finance and convert to
    month-end prices. Returns (prices, rf):
      prices : DataFrame of month-end adjusted close prices (USD)
      rf     : Series of monthly T-bill returns (decimal)
    """
    import yfinance as yf

    tickers = [CORE] + SATELLITE + [RF_TICKER]
    # yfinance's `end` is exclusive, so add one day to include the end date
    end_excl = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download(tickers, start=start, end=end_excl,
                      auto_adjust=True, progress=False)["Close"]
    monthly = raw.resample("ME").last()      # last trading day of each month

    prices = monthly[[CORE] + SATELLITE].dropna()
    rf = tbill_monthly_return(monthly[RF_TICKER]).reindex(prices.index)
    return prices, rf


def tbill_monthly_return(irx_yield):
    """Convert the ^IRX yield (percent per year) into a monthly return.
    The yield observed at the end of month t-1 is what an investor earns
    during month t, so we lag it by one month."""
    return (irx_yield / 100 / 12).shift(1)


def asset_returns(prices, rf):
    """Simple monthly returns of all assets, with T-bills as an extra column."""
    rets = prices.pct_change()
    rets[TBILL] = rf
    return rets


# ---------------------------------------------------------------------------
# 2. Signals
# ---------------------------------------------------------------------------
def trend_signal(prices, ma_months=MA_MONTHS):
    """1 if month-end price > its moving average over the last `ma_months`
    month-ends (including the current one), else 0."""
    ma = prices.rolling(ma_months).mean()
    signal = (prices > ma).astype(float)
    return signal.where(ma.notna())          # NaN until the MA is available


def rolling_vol(prices, vol_months=VOL_MONTHS):
    """Annualized volatility of monthly returns over the last `vol_months`.
    At least 10 returns are required (DBC data only starts in Feb 2006)."""
    rets = prices.pct_change()
    return rets.rolling(vol_months, min_periods=10).std() * np.sqrt(12)


# ---------------------------------------------------------------------------
# 3. Weights
# ---------------------------------------------------------------------------
def strategy_weights(prices, core_weight=CORE_WEIGHT, ma_months=MA_MONTHS,
                     vol_months=VOL_MONTHS):
    """Target weights decided at each month-end t (to be held during t+1)."""
    sat = prices[SATELLITE]
    signal = trend_signal(sat, ma_months)
    inv_vol = 1 / rolling_vol(sat, vol_months)

    # Each satellite asset's share of the satellite budget (sums to 1)
    share = inv_vol.div(inv_vol.sum(axis=1), axis=0)
    sat_budget = 1 - core_weight

    w = pd.DataFrame(index=prices.index)
    w[CORE] = core_weight
    for a in SATELLITE:
        w[a] = sat_budget * share[a] * signal[a]   # 0 if the asset is "off"
    w[TBILL] = 1 - w[[CORE] + SATELLITE].sum(axis=1)  # the rest sits in T-bills
    w[TBILL] = w[TBILL].clip(lower=0).round(12)       # remove tiny rounding noise

    # Only keep months where every input was available
    ready = signal.notna().all(axis=1) & inv_vol.notna().all(axis=1)
    return w[ready]


def fixed_weights(index, weights):
    """Constant target weights, e.g. {'SPY': 0.6, 'AGG': 0.4}."""
    return pd.DataFrame(weights, index=index)


# ---------------------------------------------------------------------------
# 4. Backtest
# ---------------------------------------------------------------------------
def backtest(target_weights, rets, start=BACKTEST_START, end=BACKTEST_END,
             cost_bps=COST_BPS, rebalance=True):
    """Monthly backtest.

    target_weights : weights decided at month-end t (rows) per asset (cols)
    rets           : monthly asset returns (incl. TBILL)
    rebalance      : True  -> trade back to the target every month
                     False -> buy once at the start, then let weights drift
                              (buy & hold)

    Timing: weights chosen at end of month t earn the returns of month t+1.
    Cost: cost_bps / 10,000 * turnover, deducted in the month of the trade.
    Turnover = sum over assets of |new weight - weight before trading|.
    The initial purchase (from cash) counts as turnover of 1.

    Returns a DataFrame with columns: gross, cost, net, turnover.
    """
    cols = target_weights.columns
    rets = rets[cols]
    months = rets.loc[start:end].index
    cost_rate = cost_bps / 10_000

    out = []
    held = pd.Series(0.0, index=cols)          # start from nothing
    for i, month in enumerate(months):
        decision_date = rets.index[rets.index.get_loc(month) - 1]   # end of t
        if rebalance or i == 0:
            new_w = target_weights.loc[decision_date]
        else:
            new_w = held
        turnover = (new_w - held).abs().sum()
        r = rets.loc[month].fillna(0.0)
        gross = (new_w * r).sum()
        cost = turnover * cost_rate
        out.append({"date": month, "gross": gross, "cost": cost,
                    "net": gross - cost, "turnover": turnover})
        # weights drift with returns until the next rebalance
        held = new_w * (1 + r) / (1 + gross)

    return pd.DataFrame(out).set_index("date")


def run_all(prices, rf, core_weight=CORE_WEIGHT, ma_months=MA_MONTHS,
            cost_bps=COST_BPS, start=BACKTEST_START, end=BACKTEST_END):
    """Run the strategy and the comparison portfolios.
    Returns (net monthly returns DataFrame, strategy weights, strategy result)."""
    rets = asset_returns(prices, rf)

    w_strat = strategy_weights(prices, core_weight, ma_months)

    # Same assets without the trend filter: core + equal satellite split
    sat_each = (1 - core_weight) / len(SATELLITE)
    static = {CORE: core_weight, **{a: sat_each for a in SATELLITE}}
    w_static = fixed_weights(rets.index, static)

    w_6040 = fixed_weights(rets.index, {"SPY": 0.60, "AGG": 0.40})

    res_strat = backtest(w_strat, rets, start, end, cost_bps)
    results = pd.DataFrame({
        "Strategy": res_strat["net"],
        "60/40 SPY/AGG": backtest(w_6040, rets, start, end, cost_bps)["net"],
        "Buy & hold (same assets)": backtest(w_static, rets, start, end,
                                             cost_bps, rebalance=False)["net"],
    })
    rf_bt = rets[TBILL].loc[results.index]
    return results, rf_bt, w_strat.loc[: results.index[-1]], res_strat


# ---------------------------------------------------------------------------
# 5. Metrics
# ---------------------------------------------------------------------------
def cumulative(returns):
    """Growth of 1 unit of capital, starting at 1 before the first month."""
    growth = (1 + returns).cumprod()
    first = growth.index[0] - pd.offsets.MonthEnd(1)
    start_row = pd.DataFrame(1.0, index=[first], columns=growth.columns) \
        if isinstance(growth, pd.DataFrame) else pd.Series(1.0, index=[first])
    return pd.concat([start_row, growth])


def max_drawdown(returns):
    growth = (1 + returns).cumprod()
    return (growth / growth.cummax() - 1).min()


def performance_table(results, rf, benchmark="60/40 SPY/AGG"):
    """Performance measures from monthly returns.

    Assumptions:
      * Annualized average return = 12 x mean monthly return (arithmetic).
      * Volatility = sqrt(12) x std of monthly returns.
      * Sharpe = annualized mean excess return over T-bills / annualized
        std of excess returns.
      * Beta and alpha from an OLS regression of monthly excess returns of
        the portfolio on monthly excess returns of the benchmark.
        Beta is NOT annualized; alpha = 12 x monthly intercept.
      * Information ratio = annualized mean active return / annualized
        tracking error (active return = portfolio - benchmark).
    """
    bench = results[benchmark]
    rows = {}
    for name in results.columns:
        r = results[name]
        ex = r - rf
        ex_b = bench - rf
        beta, alpha_m = np.polyfit(ex_b, ex, 1)
        active = r - bench
        te = active.std() * np.sqrt(12)
        rows[name] = {
            "Ann. return": r.mean() * 12,
            "CAGR": (1 + r).prod() ** (12 / len(r)) - 1,
            "Volatility": r.std() * np.sqrt(12),
            "Sharpe": ex.mean() * 12 / (ex.std() * np.sqrt(12)),
            "Alpha (ann.)": alpha_m * 12,
            "Beta": beta,
            "Tracking error": te,
            "Information ratio": active.mean() * 12 / te if te > 1e-12 else np.nan,
            "Max drawdown": max_drawdown(r),
        }
    return pd.DataFrame(rows).T


# ===========================================================================
# Streamlit user interface
# ===========================================================================
st.set_page_config(page_title="Family Office Trend Portfolio", layout="wide")
st.title("Core-satellite trend portfolio")
st.caption("60% AGG core, 40% satellite in SPY, GLD and DBC with a trend filter "
           "and inverse-volatility weights. Unused satellite weight goes to T-bills.")


@st.cache_data(ttl=24 * 3600)
def load_data():
    return download_data(DOWNLOAD_START, BACKTEST_END)


# --- user inputs ------------------------------------------------------------
st.sidebar.header("Assumptions")
ma_months = st.sidebar.slider("Moving-average length (months)", 3, 12, MA_MONTHS)
core_weight = st.sidebar.slider("Core weight in AGG", 0.0, 1.0, CORE_WEIGHT, 0.05)
cost_bps = st.sidebar.slider("Transaction cost (bps per unit turnover)", 0, 50, COST_BPS)
st.sidebar.caption(f"Backtest: {BACKTEST_START} to {BACKTEST_END}, monthly, USD.")

# --- calculations -----------------------------------------------------------
prices, rf = load_data()
results, rf_bt, weights, res_strat = run_all(prices, rf, core_weight, ma_months, cost_bps)
table = performance_table(results, rf_bt)

# --- output -----------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Strategy ann. return", f"{table.loc['Strategy', 'Ann. return']:.2%}")
c2.metric("Strategy Sharpe", f"{table.loc['Strategy', 'Sharpe']:.2f}",
          f"{table.loc['Strategy', 'Sharpe'] - table.loc['60/40 SPY/AGG', 'Sharpe']:+.2f} vs 60/40")
c3.metric("Strategy max drawdown", f"{table.loc['Strategy', 'Max drawdown']:.2%}")

st.subheader("Cumulative performance (start = 1, net of costs)")
st.line_chart(cumulative(results))

st.subheader("Performance measures")
pct = ["Ann. return", "CAGR", "Volatility", "Alpha (ann.)", "Tracking error", "Max drawdown"]
st.dataframe(table.style.format({c: "{:.2%}" for c in pct}
                                | {c: "{:.2f}" for c in ["Sharpe", "Beta", "Information ratio"]}))
st.caption("Beta and alpha vs the 60/40 SPY/AGG benchmark (excess returns over T-bills). "
           "Beta is not annualized.")

st.subheader("Strategy weights over time")
st.area_chart(weights.loc[BACKTEST_START:])
