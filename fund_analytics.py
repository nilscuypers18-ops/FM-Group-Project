"""Presentation analytics on existing net returns; no new investment rules."""
import pandas as pd


# Same return-month windows as crisis_analysis.ipynb: first month after SPY's peak.
CRISES = {
    "Financial crisis": ("2007-11", "2009-02"),
    "Covid crash": ("2020-01", "2020-03"),
    "Inflation shock": ("2022-01", "2022-09"),
}


def calendar_returns(returns):
    """Compound observed months; label incomplete years instead of annualising them."""
    annual = (1 + returns).groupby(returns.index.year).prod() - 1
    counts = returns.groupby(returns.index.year).count()
    annual.index = [f"{year}" if counts.loc[year].eq(12).all() else f"{year}*"
                    for year in annual.index]
    annual.index.name = "Year"
    return annual


def monthly_grid(returns):
    """Year x month grid; unobserved months remain NaN, never zero."""
    frame = returns.rename("return").to_frame()
    frame["year"], frame["month"] = frame.index.year, frame.index.month
    return frame.pivot(index="year", columns="month", values="return").reindex(columns=range(1, 13))


def crisis_summary(model, results, start, end):
    """Local drawdown; recovery from the crisis low to pre-crisis wealth 1.

    Recovery searches all later observed months, without resetting the portfolio.
    A portfolio never below its initial value has no recovery required.
    """
    window = results.loc[start:end]
    if window.empty:
        return pd.DataFrame()
    baseline = window.index[0] - pd.offsets.MonthEnd(1)
    expected = pd.date_range(pd.Period(start, freq="M").to_timestamp("M"),
                             pd.Period(end, freq="M").to_timestamp("M"), freq="ME")
    if not window.index.equals(expected):
        return pd.DataFrame()
    path = model.cumulative(results.loc[start:])
    crisis_path = path.loc[:window.index[-1]]
    rows = []
    for name in results.columns:
        low = crisis_path[name].idxmin()
        needs_recovery = crisis_path[name].min() < 1 - 1e-12
        recovered = path.loc[low:, name].ge(1 - 1e-12)
        recovery = recovered[recovered].index[0] if recovered.any() else pd.NaT
        months = ((recovery.year - low.year) * 12 + recovery.month - low.month
                  if pd.notna(recovery) and needs_recovery else (0 if not needs_recovery else None))
        rows.append({"Portfolio": name, "Crisis return": (1 + window[name]).prod() - 1,
                     "Max drawdown": model.drawdowns(window[name]).max(),
                     "Crisis low": low if needs_recovery else pd.NaT,
                     "Recovery date": recovery if needs_recovery else baseline,
                     "Months to recover": months})
    return pd.DataFrame(rows).set_index("Portfolio")
