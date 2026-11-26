"""Core-satellite portfolio following Lectures 3 and 4.

The app and submitted notebook are self-contained, following the upstream
structure. Rebuild the notebook with tools/build_notebook.py after editing
the calculation functions below. Importing this module does not run the UI.
"""

# %% 0. Setup and explicit assumptions
import numpy as np
import pandas as pd

CORE = "AGG"
SATELLITE = ["SPY", "GLD", "DBC"]
ASSETS = [CORE] + SATELLITE
TBILL = "TBILL"
RF_TICKER = "^IRX"
DOWNLOAD_START = "2006-02-01"
# Thirteen prices are needed for twelve returns. First signal: February 2007.
BACKTEST_START = "2007-03-31"
BACKTEST_END = "2026-10-31"
CORE_WEIGHT = 0.60
MA_MONTHS = 10
VOL_MONTHS = 12
COST_BPS = 10
BENCHMARK = "60/40 SPY/AGG"
PERIODS_PER_YEAR = 12


def month_grid(start, end):
    """Require explicit calendar month-ends rather than silently truncate."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if not start.is_month_end or not end.is_month_end or start > end:
        raise ValueError("Use ordered calendar month-end start/end dates.")
    return pd.date_range(start, end, freq="ME")


def check_monthly_index(data):
    if data.empty or not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("Expected a nonempty time series with a DatetimeIndex.")
    expected = month_grid(data.index[0], data.index[-1])
    if not data.index.equals(expected):
        raise ValueError("Monthly index must be sorted, unique and without gaps.")
    if not np.isfinite(data.to_numpy(dtype=float)).all():
        raise ValueError("Missing or nonfinite observations; inspect the data first.")


def check_window(window, minimum=1):
    if isinstance(window, bool) or not isinstance(window, (int, np.integer)) or window < minimum:
        raise ValueError(f"Window must be an integer >= {minimum}.")


# %% 1. API data and deliberate cleaning (Lecture 3, Part 1)
def download_raw(start=DOWNLOAD_START, end=BACKTEST_END):
    """Daily adjusted closes. Yahoo's end is exclusive; include end explicitly."""
    import yfinance as yf

    raw = yf.download(
        ASSETS + [RF_TICKER], start=start,
        end=(pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        interval="1d", auto_adjust=True, progress=False, keepna=True, threads=False,
    )
    if raw is None or raw.empty or "Close" not in raw:
        raise ValueError("Yahoo returned no close data. Check connection and ticker availability.")
    closes = raw["Close"].copy()
    failed = [ticker for ticker in ASSETS + [RF_TICKER]
              if ticker not in closes or closes[ticker].isna().all()]
    if failed:
        raise ValueError(f"No observations for {failed}. Inspect the API error and retry the download.")
    return closes


def data_summary(data):
    """Three of the course's four checks; the fourth is a price plot."""
    return pd.DataFrame({
        "observations": data.count(),
        "first valid": [data[c].first_valid_index() for c in data],
        "last valid": [data[c].last_valid_index() for c in data],
        "missing": data.isna().sum(),
    })


def prepare_data(raw, start=DOWNLOAD_START, end=BACKTEST_END):
    """Keep every requested month; never fill prices or delete a gap.

    Return prices, lagged cash-return proxy and monthly source-date audit.
    Daily NaNs (holidays or unavailable quotes) are left unfilled.
    Last valid quotes must be within 7 calendar days of month-end.
    This tolerance allows weekends/holidays, but does not guarantee that
    a quote is from the final trading session; inspect the audit dates.
    """
    required = ASSETS + [RF_TICKER]
    if not isinstance(raw.index, pd.DatetimeIndex) or raw.empty:
        raise ValueError("Raw data need a nonempty daily DatetimeIndex.")
    if raw.columns.has_duplicates or not set(required).issubset(raw.columns):
        raise ValueError(f"Expected one column for each of {required}.")
    daily = raw[required].copy()
    daily.index = daily.index.tz_localize(None).normalize()
    if daily.index.has_duplicates:
        raise ValueError("Duplicate daily dates. Investigate before aggregating.")
    daily = daily.sort_index().loc[start:end].apply(pd.to_numeric, errors="raise")
    if daily.empty or np.isinf(daily.to_numpy()).any():
        raise ValueError("Empty sample or infinite daily observations.")
    if (daily[ASSETS] <= 0).any().any():
        raise ValueError("Adjusted ETF prices must be strictly positive.")
    first = pd.Timestamp(start) + pd.offsets.MonthEnd(0)
    grid = month_grid(first, end)
    monthly = daily.resample("ME").last().reindex(grid)
    if monthly.isna().any().any():
        bad = monthly.index[monthly.isna().any(axis=1)].strftime("%Y-%m").tolist()
        raise ValueError(f"Missing month/ticker data in {len(bad)} month(s), starting {bad[:8]}. "
                         "No months were dropped or filled.")
    source_dates = pd.DataFrame(index=grid)
    for ticker in required:
        dates = pd.Series(daily.index, index=daily.index).where(daily[ticker].notna())
        source_dates[ticker] = dates.resample("ME").last().reindex(grid)
    age_days = source_dates.apply(lambda s: (pd.Series(grid, index=grid) - s).dt.days)
    if (age_days > 7).any().any():
        raise ValueError("Stale month-end quote (>7 calendar days). Inspect the raw data.")
    prices = monthly[ASSETS].copy()
    rf = tbill_monthly_return(monthly[RF_TICKER])
    audit = source_dates.add_suffix(" source date").join(age_days.add_suffix(" age days"))
    return prices, rf, audit


def download_data(start=DOWNLOAD_START, end=BACKTEST_END):
    prices, rf, _ = prepare_data(download_raw(start, end), start, end)
    return prices, rf


def tbill_monthly_return(irx_yield):
    """Prior annual quoted yield / 100 / 12, an approximate cash return.

    ^IRX is a quoted bill yield, not a total-return index. This proxy ignores
    discount-yield conversion and bill price changes. It is lagged one month.
    """
    return (irx_yield.shift(1) / 100 / PERIODS_PER_YEAR).rename(TBILL)


def asset_returns(prices, rf):
    check_monthly_index(prices)
    if (prices <= 0).any().any() or not rf.index.equals(prices.index):
        raise ValueError("Prices must be positive and cash dates must match price dates.")
    rets = prices.pct_change(fill_method=None)
    rets[TBILL] = rf
    # Only the first row has no preceding observation.
    if not np.isfinite(rets.iloc[1:].to_numpy()).all():
        raise ValueError("Missing asset or cash returns after the first observation.")
    return rets


# %% 2. Rolling signals and target weights (Lectures 3 and 4)
def trend_signal(prices, ma_months=MA_MONTHS):
    check_window(ma_months)
    ma = prices.rolling(window=ma_months, min_periods=ma_months).mean()
    return (prices > ma).astype(float).where(ma.notna())


def rolling_vol(prices, vol_months=VOL_MONTHS):
    check_window(vol_months, minimum=2)
    rets = prices.pct_change(fill_method=None)
    return rets.rolling(window=vol_months, min_periods=vol_months).std(ddof=1) * np.sqrt(12)


def strategy_weights(prices, core_weight=CORE_WEIGHT, ma_months=MA_MONTHS,
                     vol_months=VOL_MONTHS):
    check_monthly_index(prices)
    if not np.isfinite(core_weight) or not 0 <= core_weight <= 1:
        raise ValueError("Core weight must lie between 0 and 1.")
    satellite = prices[SATELLITE]
    signal = trend_signal(satellite, ma_months)
    vol = rolling_vol(satellite, vol_months)
    inv_vol = 1 / vol.where(vol > 0)
    shares = inv_vol.div(inv_vol.sum(axis=1, min_count=len(SATELLITE)), axis=0)
    weights = pd.DataFrame(index=prices.index)
    weights[CORE] = core_weight
    weights[SATELLITE] = (1 - core_weight) * shares * signal
    weights[TBILL] = (1 - core_weight) - weights[SATELLITE].sum(axis=1, min_count=len(SATELLITE))
    ready = signal.notna().all(axis=1) & np.isfinite(shares).all(axis=1)
    return weights.loc[ready].clip(lower=0)


def fixed_weights(index, weights):
    return pd.DataFrame(weights, index=index, dtype=float)


# %% 3. Lagged positions, drift, costs and benchmarks (Lecture 4)
def backtest(target_weights, rets, start=BACKTEST_START, end=BACKTEST_END,
             cost_bps=COST_BPS, rebalance=True, execution_lag=1):
    """Weights decided at t earn returns at t+execution_lag.

    Lag 1 assumes fills at the signal close (optimistic, as in Lecture 4).
    Lag 2 is a conservative extra MONTH of delay, not next-day execution.
    Costs use the course's additive convention: net = gross - rate*turnover.
    Turnover = sum(abs(target - drifted pretrade weights)), counting buys
    AND sells, including cash-proxy trades. Opening the book costs one unit;
    the external funding leg is excluded. No final liquidation.
    Costs are booked in that return month; pro-rata expense withdrawals
    leave relative end weights unchanged. No tax or market-impact model.
    """
    check_window(execution_lag)
    if not np.isfinite(cost_bps) or not 0 <= cost_bps < 10000:
        raise ValueError("Cost must be finite and between 0 and 10,000 bps (exclusive).")
    if target_weights.empty or target_weights.columns.has_duplicates:
        raise ValueError("Provide a nonempty table of target weights.")
    if not target_weights.index.is_unique or not target_weights.index.is_monotonic_increasing:
        raise ValueError("Target dates must be sorted and unique.")
    if len(target_weights.index.difference(rets.index)):
        raise ValueError("Target dates must belong to the returns calendar.")
    # Reindex BEFORE shifting: a missing target must not compress time.
    positions = target_weights.reindex(rets.index).shift(execution_lag)
    cols = target_weights.columns
    sample = rets.reindex(month_grid(start, end))[cols]
    check_monthly_index(sample)
    if (sample <= -1).any().any():
        raise ValueError("This engine requires asset returns greater than -100%.")
    selected = positions.reindex(sample.index)
    needed = selected if rebalance else selected.iloc[:1]
    if not np.isfinite(needed.to_numpy()).all():
        raise ValueError("Target unavailable before a trade. Extend warm-up or move the start date.")
    if (needed < -1e-12).any().any() or not np.allclose(needed.sum(axis=1), 1):
        raise ValueError("Targets must be long-only and sum to one.")
    held = pd.Series(0.0, index=cols)
    rows = []
    for i, (month, returns) in enumerate(sample.iterrows()):
        new_weights = selected.loc[month] if rebalance or i == 0 else held
        turnover = (new_weights - held).abs().sum()
        gross = new_weights.dot(returns)
        cost = cost_bps / 10000 * turnover
        if gross - cost <= -1:
            raise ValueError("Costs exhaust the portfolio's capital.")
        row = {"gross": gross, "cost": cost, "net": gross - cost, "turnover": turnover}
        row.update({f"weight_{asset}": new_weights[asset] for asset in cols})
        rows.append(row)
        held = new_weights * (1 + returns) / (1 + gross)
    return pd.DataFrame(rows, index=sample.index).rename_axis("date")


def run_all(prices, rf, core_weight=CORE_WEIGHT, ma_months=MA_MONTHS,
            cost_bps=COST_BPS, start=BACKTEST_START, end=BACKTEST_END,
            vol_months=VOL_MONTHS, execution_lag=1):
    rets = asset_returns(prices, rf)
    weights = strategy_weights(prices, core_weight, ma_months, vol_months)
    sat_each = (1 - core_weight) / len(SATELLITE)
    static = {CORE: core_weight, **{asset: sat_each for asset in SATELLITE}}
    detail = backtest(weights, rets, start, end, cost_bps, execution_lag=execution_lag)
    benchmark_result = backtest(fixed_weights(rets.index, {"SPY": .6, CORE: .4}),
                                rets, start, end, cost_bps, execution_lag=execution_lag)
    buy_hold_result = backtest(fixed_weights(rets.index, static), rets, start, end,
                               cost_bps, rebalance=False, execution_lag=execution_lag)
    results = pd.DataFrame({"Strategy": detail["net"],
                            BENCHMARK: benchmark_result["net"],
                            "Buy & hold (same assets)": buy_hold_result["net"]})
    return results, rf.loc[results.index], weights.loc[:results.index[-1]], detail


# %% 4. Performance measures by hand (Lecture 3, Part 2)
def cumulative(returns):
    check_monthly_index(returns)
    if (returns <= -1).any().any():
        raise ValueError("Returns must be greater than -100%.")
    growth = (1 + returns).cumprod()
    first = growth.index[0] - pd.offsets.MonthEnd(1)
    if isinstance(growth, pd.DataFrame):
        initial = pd.DataFrame(1.0, index=[first], columns=growth.columns)
    else:
        initial = pd.Series(1.0, index=[first], name=growth.name)
    return pd.concat([initial, growth])


def drawdowns(returns):
    """Positive loss from high water mark, including initial capital = 1."""
    wealth = cumulative(returns)
    return (1 - wealth / wealth.cummax()).iloc[1:]


def max_drawdown(returns):
    return drawdowns(returns).max()


def performance_table(results, rf, benchmark=BENCHMARK):
    """Course formulas on monthly simple returns; ddof=1.

    Beta = cov(portfolio excess, benchmark excess) / var(benchmark excess).
    Alpha = mean(portfolio excess) - beta*mean(benchmark excess), times 12.
    IR = annualized mean active return / annualized tracking error.
    """
    check_monthly_index(results)
    if len(results) < 2 or not rf.index.equals(results.index) or not np.isfinite(rf).all():
        raise ValueError("Need >=2 complete, identically dated portfolio and cash returns.")
    if (results <= -1).any().any():
        raise ValueError("Invalid returns for compounding.")
    benchmark_excess = results[benchmark] - rf
    benchmark_var = benchmark_excess.var(ddof=1)
    rows = {}
    for name, returns in results.items():
        excess = returns - rf
        beta = excess.cov(benchmark_excess) / benchmark_var if benchmark_var > 1e-15 else np.nan
        alpha_monthly = excess.mean() - beta * benchmark_excess.mean()
        active = returns - results[benchmark]
        tracking_error = active.std(ddof=1) * np.sqrt(12)
        excess_vol = excess.std(ddof=1) * np.sqrt(12)
        rows[name] = {
            "Ann. return": returns.mean() * 12,
            "CAGR": (1 + returns).prod() ** (12 / len(returns)) - 1,
            "Volatility": returns.std(ddof=1) * np.sqrt(12),
            "Sharpe": excess.mean() * 12 / excess_vol if excess_vol > 1e-12 else np.nan,
            "Alpha (ann.)": alpha_monthly * 12,
            "Beta": beta,
            "Tracking error": tracking_error,
            "Information ratio": active.mean() * 12 / tracking_error if tracking_error > 1e-12 else np.nan,
            "Max drawdown": max_drawdown(returns),
        }
    return pd.DataFrame(rows).T


def rolling_performance(results, rf, window=60, benchmark=BENCHMARK):
    """Course-style 60-month risk diagnostics, using excess returns."""
    check_window(window, minimum=2)
    performance_table(results, rf, benchmark)
    p = results["Strategy"] - rf
    b = results[benchmark] - rf
    beta = p.rolling(window).cov(b) / b.rolling(window).var().replace(0, np.nan)
    alpha = 12 * (p.rolling(window).mean() - beta * b.rolling(window).mean())
    sharpe = np.sqrt(12) * p.rolling(window).mean() / p.rolling(window).std().replace(0, np.nan)
    return pd.DataFrame({"Beta": beta, "Alpha (ann.)": alpha, "Sharpe": sharpe})


# %% 5. Sensitivity checks, not parameter optimization (Lecture 4)
def sensitivity_table(prices, rf, ma_values=(8, 10, 12), cost_values=(0, 10, 25, 50),
                      core_weight=CORE_WEIGHT, start=BACKTEST_START, end=BACKTEST_END):
    rows = []
    for ma in ma_values:
        for cost in cost_values:
            returns, cash, _, detail = run_all(prices, rf, core_weight, ma, cost, start, end)
            row = performance_table(returns, cash).loc["Strategy"].to_dict()
            row.update({"MA months": ma, "Cost bps": cost,
                        "Monthly turnover": detail["turnover"].iloc[1:].mean()})
            rows.append(row)
    return pd.DataFrame(rows).set_index(["MA months", "Cost bps"])


# Streamlit user interface
# Keep the presentation layer separate from the shared notebook calculations.
def main():
    import sys
    from portal import render_app

    render_app(sys.modules[__name__])


if __name__ == "__main__":
    main()
