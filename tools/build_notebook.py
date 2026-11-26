"""Build a standalone, readable Colab notebook from the shared calculation code.

No GitHub download at run time. The source of each function is copied verbatim;
tests check that the submitted notebook and the Streamlit module stay aligned.
Run: python tools/build_notebook.py
"""
import ast
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "app.py").read_text(encoding="utf-8").split("# Streamlit user interface")[0]
tree = ast.parse(source)
functions = {node.name: ast.get_source_segment(source, node)
             for node in tree.body if isinstance(node, ast.FunctionDef)}
cells = []


def add(kind, text, tag=None):
    text = textwrap.dedent(text).strip() + "\n"
    cell = {"cell_type": kind, "id": f"course-{len(cells):03d}",
            "metadata": {"tags": [tag]} if tag else {},
            "source": text.splitlines(keepends=True)}
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    cells.append(cell)


def md(text):
    add("markdown", text)


def code(text, tag=None):
    add("code", text, tag)


def definitions(*names):
    code("\n\n\n".join(functions[name] for name in names), "shared-calculations")


md("""
# Core-satellite trend portfolio for a family office
**2270 Financial Modeling — Group Assignment**

Moodle group: **TO BE COMPLETED BY THE GROUP**  
Members: **TO BE COMPLETED BY THE GROUP**  
Repository: https://github.com/nilscuypers18-ops/FM-Group-Project  
Deployed Streamlit URL: **TO BE COMPLETED AFTER DEPLOYMENT**

## How to run
Open this file in a fresh Google Colab session and choose **Runtime → Run all**.
Only API data are needed. This notebook contains all calculation code and does
not download a changing Python file from GitHub. Locally, select the project's
`.venv` kernel. The app contains the same functions in `app.py`; a consistency test checks equality.

Our sequence follows the course: specify → download → inspect → clean →
construct positions → lag → backtest gross and net → evaluate → challenge.
Read each explanation and inspect its output before accepting the next step.
""")
code("%pip install -q 'numpy>=1.26,<3' 'pandas>=2.2,<4' 'matplotlib>=3.8,<4' 'yfinance>=0.2.54,<2'", "setup-install")
code("""
import sys
from pathlib import Path
from importlib.metadata import version
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from IPython.display import display

pd.options.display.float_format = "{:.4f}".format
plt.rcParams.update({"figure.figsize": (11, 5), "axes.grid": True,
                     "grid.alpha": 0.25, "font.size": 11})
print("Python:", sys.version.split()[0])
print({package: version(package) for package in ["numpy", "pandas", "matplotlib", "yfinance"]})
""")
md("""
## 0. Client, investment rule and assumptions
The existing group concept is a conservative family office with a long horizon,
seeking preservation and growth of wealth in USD. This is a nominal total-return
analysis: inflation, taxes and currency hedging are outside the model.

* Core: 60% AGG, a bond ETF with interest-rate and credit risk; it is **not cash**.
* Satellite: 40% allocated across SPY, GLD and DBC in inverse proportion to their
  trailing 12-month return volatilities. This is inverse volatility, **not** a
  covariance-based risk-parity optimization.
* At month-end, a satellite is on only if its adjusted price exceeds its trailing
  10-month simple moving average. An off asset's own share goes to the cash proxy.
  Active assets do not absorb off assets' shares. No short sales or leverage.
* Rebalance monthly. A signal at t first earns the return at t+1.
* Base transaction cost: 10 bps times traded weight, counting purchases and sales.
  The same convention applies to all three portfolios.

**Sample correction:** February 2006–February 2007 provides 13 prices and 12
returns. The first fully estimated target is February 2007; the first backtest
return is March 2007. The previous January 2007 start needed an undocumented
shorter volatility window. We retain the full window and disclose the new start.
""")
setup_source = source.split("# %% 0. Setup and explicit assumptions\n")[1].split("\ndef month_grid")[0]
code(setup_source, "shared-assumptions")
definitions("month_grid", "check_monthly_index", "check_window")
code("""
assumptions = pd.Series({"Download starts": DOWNLOAD_START, "First return": BACKTEST_START,
                         "Last return": BACKTEST_END, "AGG weight": CORE_WEIGHT,
                         "SMA months": MA_MONTHS, "Volatility months": VOL_MONTHS,
                         "Cost bps": COST_BPS, "Return periods/year": PERIODS_PER_YEAR})
display(assumptions.to_frame("Assumption"))
""")
md("""
## 1. Retrieve API data and run the four checks
**Course: Lecture 3, Part 1, §§3.2–3.3.** Yahoo Finance via `yfinance`;
daily split/dividend-adjusted ETF closes in USD. `end` is exclusive at the API,
so the request adds one day. `^IRX` is an annual quoted bill yield, in percent.
It must be inspected separately from prices.

Before cleaning, check **shape, date range, missing values and a plot**.
Investigate unusual returns; a crisis observation is not automatically bad data.
""")
definitions("download_raw", "data_summary")
code("raw = download_raw(DOWNLOAD_START, BACKTEST_END)", "api-download")
code("""
print("Shape:", raw.shape)
print("Requested:", DOWNLOAD_START, "to", BACKTEST_END)
print("Received:", raw.index.min(), "to", raw.index.max())
display(data_summary(raw))
display(raw.head())
display(raw.tail())
fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
raw[ASSETS].plot(ax=axes[0], title="Downloaded adjusted ETF prices")
axes[0].set_ylabel("Adjusted price (USD)")
raw[RF_TICKER].plot(ax=axes[1], title="Quoted 13-week T-bill yield")
axes[1].set_ylabel("Percent per year")
plt.tight_layout()
plt.show()
""")
md("""
## 2. Clean deliberately and calculate monthly returns
Normalize time zones, sort dates, reject duplicates and nonpositive ETF prices.
Keep the last valid observation in each calendar month and record its actual
source date. **No forward fill, outlier deletion or silent `dropna()` of months.**
A missing month or a quote over 7 calendar days old stops the analysis. The
7-day tolerance permits holidays but requires checking the source-date audit.

Cash proxy in month t = prior month-end `^IRX` / 100 / 12. This is an
approximation, not a bill total-return series: it omits discount-yield conversion
and price changes. It is used consistently for cash and excess returns.

Lecture 3 illustrates log returns. For a portfolio of several assets we use
**simple returns**, because `sum(weight * simple_return)` is the exact portfolio
return. Weighted asset log returns do not generally equal portfolio log returns.
We compound with `(1 + r).cumprod()`. Asset log returns are shown for comparison.
""")
definitions("tbill_monthly_return", "prepare_data", "download_data", "asset_returns")
code("""
prices, rf, source_audit = prepare_data(raw, DOWNLOAD_START, BACKTEST_END)
returns = asset_returns(prices, rf)
log_returns = np.log(prices).diff(1)
print("Monthly price shape:", prices.shape)
display(data_summary(prices))
display(source_audit.tail())
display(returns.head(3))  # First row is undefined, not a zero return.
display(returns.iloc[1:].describe().T)
display(returns.iloc[1:][ASSETS].corr())
display(returns.iloc[1:][ASSETS].abs().max().to_frame("Largest absolute monthly return"))
assert prices.index.equals(pd.date_range(prices.index[0], BACKTEST_END, freq="ME"))
assert returns.iloc[1:].notna().all().all()
np.testing.assert_allclose(np.expm1(log_returns.iloc[1:]), returns[ASSETS].iloc[1:])
""")
md("""
## 3. Construct the trend signal and inverse-volatility weights
**Course: Lecture 4, §4.2; Lecture 3, portfolio weights.** A rolling mean uses
only the current and preceding prices. The return-volatility window requires
all 12 monthly returns, with sample standard deviation (`ddof=1`).

Predict: if every satellite is off, what are the AGG and cash weights?
They should be 60% and 40%. Plot price, SMA and position before trusting metrics.
""")
definitions("trend_signal", "rolling_vol", "strategy_weights", "fixed_weights")
code("""
sma = prices[SATELLITE].rolling(MA_MONTHS, min_periods=MA_MONTHS).mean()
signal = trend_signal(prices[SATELLITE], MA_MONTHS)
volatility = rolling_vol(prices[SATELLITE], VOL_MONTHS)
inverse_volatility = 1 / volatility.where(volatility > 0)
satellite_shares = inverse_volatility.div(inverse_volatility.sum(axis=1, min_count=3), axis=0)
weights = strategy_weights(prices, CORE_WEIGHT, MA_MONTHS, VOL_MONTHS)
display(pd.concat({"Signal": signal, "Volatility": volatility,
                   "Satellite share": satellite_shares}, axis=1).tail())
display(weights.head())
assert weights.index[0] == prices.index[max(MA_MONTHS - 1, VOL_MONTHS)]
np.testing.assert_allclose(weights.sum(axis=1), 1.0)
np.testing.assert_allclose(weights[CORE], CORE_WEIGHT)
assert (weights >= -1e-12).all().all()

fig, axes = plt.subplots(3, 2, figsize=(13, 9), sharex=True)
for row, asset in enumerate(SATELLITE):
    preview = pd.DataFrame({asset: prices[asset], "SMA": sma[asset]}).loc["2020":"2023"]
    preview.plot(ax=axes[row, 0], title=f"{asset}: price and {MA_MONTHS}-month SMA")
    signal[asset].loc["2020":"2023"].plot(ax=axes[row, 1], drawstyle="steps-post",
                                                   title=f"{asset}: decision at month-end")
    axes[row, 0].set_ylabel("Adjusted USD")
    axes[row, 1].set_yticks([0, 1], ["Off", "On"])
plt.tight_layout()
plt.show()
""")
md("""
## 4. Backtest with lagged positions, drift and transaction costs
**Course: Lecture 4, §§4.1–4.3.** The crucial line is
`target_weights.reindex(returns.index).shift(1)`: decision t earns return t+1.
The engine checks every trading month's weights and returns; missing values
are never replaced by zero.

This follows the course's **signal-close execution assumption**, which is
optimistic: one cannot know the completed close and guarantee a fill at that
same price. An extra-month-delay sensitivity below challenges that assumption;
it does not simulate next-day-open execution.

Turnover = sum of absolute differences between target and **drifted** pretrade
weights. Selling 10% and buying 10% means 20% turnover. The opening book has
turnover 1; the funding leg is excluded. Proxy-cash purchases/sales are included.
Costs follow the course's additive convention, `net = gross - turnover * bps/10000`,
booked in the corresponding return month. No terminal liquidation charge.

Comparisons, with identical dates and cost conventions:
* **60/40 SPY/AGG:** fixed target weights, rebalanced monthly.
* **Buy & hold:** initially 60% AGG and 40% equally split across SPY, GLD, DBC;
  no subsequent rebalancing. Its weights drift. It controls for the asset mix,
  but does not isolate the trend filter from inverse-volatility weighting.
""")
definitions("backtest", "run_all", "cumulative", "drawdowns", "max_drawdown")
code("""
results, rf_bt, weights, detail = run_all(prices, rf, CORE_WEIGHT, MA_MONTHS, COST_BPS,
                                        BACKTEST_START, BACKTEST_END)
positions = detail.filter(like="weight_").rename(columns=lambda c: c.removeprefix("weight_"))
display(detail[["gross", "cost", "net", "turnover"]].head())
display(positions.head())
# Independently reconcile the first month with the preceding decision.
first_month = results.index[0]
prior_decision = first_month - pd.offsets.MonthEnd(1)
manual_gross = weights.loc[prior_decision].dot(returns.loc[first_month])
assert np.isclose(manual_gross, detail.loc[first_month, "gross"])
np.testing.assert_allclose(positions, weights.reindex(returns.index).shift(1).loc[results.index])
np.testing.assert_allclose(detail["net"], detail["gross"] - detail["cost"])
assert results.index.equals(month_grid(BACKTEST_START, BACKTEST_END))

wealth = cumulative(results)
ax = wealth.plot(title="Cumulative performance, net of costs (initial wealth = 1)")
ax.set_ylabel("Value of USD 1 invested")
plt.tight_layout()
plt.show()
ax = positions.plot.area(title="Weights actually held during each return month", ylim=(0, 1))
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.set_ylabel("Portfolio weight")
ax.legend(loc="upper left", ncol=5)
plt.tight_layout()
plt.show()
""")
code("""
gross_net = detail[["gross", "net"]].rename(columns={"gross": "Strategy gross", "net": "Strategy net"})
fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
cumulative(gross_net).plot(ax=axes[0], title="Strategy performance before and after costs")
axes[0].set_ylabel("Value of USD 1")
detail["turnover"].plot(ax=axes[1], title="Monthly traded weight (buys plus sells)")
axes[1].yaxis.set_major_formatter(PercentFormatter(1))
plt.tight_layout()
plt.show()
print(f"Average monthly turnover after opening: {detail['turnover'].iloc[1:].mean():.2%}")
print(f"Sum of monthly cost ratios: {detail['cost'].sum():.2%}")
print("This sum is not a percentage of initial wealth or the compounded wealth loss.")
print(f"Final gross/net wealth difference: {cumulative(gross_net).iloc[-1].diff().iloc[-1] * -1:.4f} per USD 1")
""")
md("""
## 5. Performance measures calculated by hand
**Course: Lecture 3, §§3.3–3.5 and the portfolio formula sheet.**

| Measure | Monthly-to-annual convention | Meaning for the client |
|---|---|---|
| Average return | 12 × mean(r) | Arithmetic reward, not compounded growth |
| CAGR | product(1+r)^(12/n) − 1 | Compounded growth of invested wealth |
| Volatility | sqrt(12) × std(r) | Variability, with sample std (ddof=1) |
| Sharpe | sqrt(12) × mean(r−rf) / std(r−rf) | Excess reward per unit of excess-return risk |
| Beta | cov(r−rf, b−rf) / var(b−rf) | Exposure to the 60/40 benchmark; not annualized |
| Alpha | 12 × [mean(r−rf) − beta × mean(b−rf)] | Return unexplained by this single benchmark |
| Tracking error | sqrt(12) × std(r−b) | Variability of benchmark-relative results |
| Information ratio | 12 × mean(r−b) / tracking error | Active reward per unit of active risk |
| Maximum drawdown | max(1 − wealth / running maximum) | Largest observed loss from a peak |

Drawdowns are **positive loss magnitudes**, matching the course formula sheet.
The high water mark includes initial capital 1, so a loss in month one counts.
An undefined ratio is shown as NaN, including the benchmark's own information
ratio. Alpha is descriptive, not evidence of skill or statistical significance.
Square-root-of-time annualization assumes sufficiently stable return behaviour;
serial correlation and non-normal tails limit its interpretation.
""")
definitions("performance_table")
code("""
table = performance_table(results, rf_bt)
percent_columns = ["Ann. return", "CAGR", "Volatility", "Alpha (ann.)", "Tracking error", "Max drawdown"]
formats = {c: "{:.2%}" for c in percent_columns}
formats.update({c: "{:.2f}" for c in ["Sharpe", "Beta", "Information ratio"]})
display(table.style.format(formats, na_rep="Undefined"))

# Cross-check covariance beta against an independent least-squares regression.
b = results[BENCHMARK] - rf_bt
p = results["Strategy"] - rf_bt
alpha_ols, beta_ols = np.linalg.lstsq(np.column_stack([np.ones(len(b)), b]), p, rcond=None)[0]
np.testing.assert_allclose([12 * alpha_ols, beta_ols], table.loc["Strategy", ["Alpha (ann.)", "Beta"]])

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for ax, metric in zip(axes, ["Ann. return", "Volatility", "Sharpe"]):
    table[metric].plot.bar(ax=ax, title=metric, rot=25)
    if metric != "Sharpe":
        ax.yaxis.set_major_formatter(PercentFormatter(1))
plt.tight_layout()
plt.show()
dd = drawdowns(results)
ax = dd.plot(title="Drawdown from the high water mark (positive = loss)")
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.set_ylabel("Loss from peak")
plt.tight_layout()
plt.show()
""")
md("""
### Interpret the evidence for the family office
The following statements describe the calculated sample, without asserting
future performance. Discuss whether the realised losses, bond concentration
and benchmark-relative outcomes suit the client. Capital preservation is an
objective; this allocation does not guarantee it.
""")
code("""
s = table.loc["Strategy"]
base = table.loc[BENCHMARK]
print(f"The strategy's arithmetic annual return is {s['Ann. return']:.2%}; its CAGR is {s['CAGR']:.2%}.")
print(f"Volatility is {s['Volatility']:.2%}, versus {base['Volatility']:.2%} for 60/40.")
print(f"Sharpe is {s['Sharpe']:.2f}, versus {base['Sharpe']:.2f}; this compares reward after the cash proxy.")
print(f"Beta {s['Beta']:.2f} measures co-movement with 60/40, not with an all-equity market.")
print(f"Annual alpha {s['Alpha (ann.)']:.2%} is the fitted intercept relative to that benchmark.")
print(f"Tracking error {s['Tracking error']:.2%} and IR {s['Information ratio']:.2f} describe active risk and reward.")
print(f"The largest observed peak loss is {s['Max drawdown']:.2%}; a wealth-preservation client must tolerate such losses.")
print("Full-sample estimates and historical drawdowns do not bound future losses.")
""")
md("""
## 6. Check risk through time
**Course: Lecture 3, §3.3; Lecture 4, §4.0.** A good final result can hide long
unacceptable periods. Use 60 complete monthly observations for rolling beta,
annualized alpha and Sharpe. The first 59 values are deliberately undefined.
Calendar-year returns compound simple returns; partial years are labelled.
""")
definitions("rolling_performance")
code("""
rolling = rolling_performance(results, rf_bt, window=60)
fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
for ax, metric in zip(axes, rolling.columns):
    rolling[metric].plot(ax=ax, title=f"60-month rolling {metric}")
    ax.axhline(0, color="black", linewidth=0.7)
    if metric == "Alpha (ann.)":
        ax.yaxis.set_major_formatter(PercentFormatter(1))
plt.tight_layout()
plt.show()
annual_returns = (1 + results).groupby(results.index.year).prod() - 1
year_counts = results.groupby(results.index.year).size()
annual_returns.index = [f"{year} ({year_counts.loc[year]} months)" for year in annual_returns.index]
display(annual_returns.style.format("{:.2%}"))
periods = {"Financial crisis": ("2007-03-31", "2009-12-31"),
           "Pandemic year": ("2020-01-31", "2020-12-31"),
           "Stock/bond selloff": ("2022-01-31", "2022-12-31")}
period_rows = {}
for label, (start, end) in periods.items():
    sample = results.loc[start:end]
    period_rows[label] = {"Months": len(sample),
                           "Strategy return": (1 + sample['Strategy']).prod() - 1,
                           "60/40 return": (1 + sample[BENCHMARK]).prod() - 1,
                           "Strategy max drawdown": max_drawdown(sample['Strategy'])}
display(pd.DataFrame(period_rows).T)
print("These are selected historical episodes, not an independent validation sample.")
""")
md("""
## 7. Challenge the assumptions without selecting a winning rule
**Course: Lecture 4, §4.3.** Keep the base rule fixed. Compare 8/10/12-month
SMAs and 0/10/25/50 bps costs on the same dates. These are descriptive
sensitivities, not an optimization or an out-of-sample test.

Execution sensitivity: compare lag 1 and lag 2 starting **April 2007 for both**,
so the slower implementation has enough history. A full extra month of delay
is a coarse stress, not a realistic next-day fill model.
""")
definitions("sensitivity_table")
code("""
sensitivity = sensitivity_table(prices, rf, core_weight=CORE_WEIGHT,
                                start=BACKTEST_START, end=BACKTEST_END)
display(sensitivity[["Ann. return", "Volatility", "Sharpe", "Max drawdown", "Monthly turnover"]])
ax = sensitivity["CAGR"].unstack("MA months").plot(marker="o", title="Cost and SMA sensitivity (same evaluation dates)")
ax.set_xlabel("Transaction cost (bps per unit of traded weight)")
ax.set_ylabel("CAGR")
ax.yaxis.set_major_formatter(PercentFormatter(1))
plt.tight_layout()
plt.show()
delay_rows = {}
for lag in [1, 2]:
    delayed, delayed_rf, _, _ = run_all(prices, rf, CORE_WEIGHT, MA_MONTHS, COST_BPS,
                                       start="2007-04-30", end=BACKTEST_END, execution_lag=lag)
    delay_rows[f"Lag {lag} month(s)"] = performance_table(delayed, delayed_rf).loc["Strategy"]
display(pd.DataFrame(delay_rows).T)
""")
md("""
## 8. Limitations and verification discussion
* **Timing:** shifted signals prevent earning the return that generated the
  signal. Signal-close fills are still optimistic. Spreads, next-open gaps,
  market impact and execution restrictions need more detailed daily modelling.
* **Selection/survivorship:** these ETFs were selected today. Their availability
  in the sample does not remove hindsight in the research choice. Do not
  describe this as a point-in-time, survivorship-free investment universe.
* **Data and cleaning:** adjusted prices can be revised by the vendor. Retain
  quote dates and retrieval time. Investigate extreme returns without deleting
  crisis observations. API coverage/quality can change.
* **Client risks:** a 60% bond core retains duration and credit risk; equity,
  gold and commodity exposures add their own risks. DBC includes futures/roll
  economics through its ETF price. ETF expenses are reflected in observed
  prices; personal tax, custody and management fees are not separately added.
* **Estimation:** backward-looking volatility and slow trend signals can whipsaw.
  Single-benchmark alpha is model-dependent; no significance claim is made.
* **Validation:** full-sample sensitivities and selected crises are descriptive.
  No genuinely unseen performance period has been established.

Lecture 5's Monte Carlo, private-loan and LBO models, and Lecture 2's individual
bond-pricing exercises were reviewed. They are not required by the assignment
and do not implement this ETF rule. We retain their lessons about explicit
assumptions, compounding, rate risk and verification rather than adding an
unrequested stochastic model or optimizer.

**Group discussion before the prospectus:** Which observed result most challenges
capital preservation? Is the cash proxy adequate? How sensitive is the conclusion
to costs and delay? Can each member explain the timing and the first-month check?
""")
md("""
## 9. Save reproducible figures and tables for the prospectus
Exports are generated locally, not required input files. Use the same tables and
figures in the prospectus; do not type independently rounded results into charts.
The provenance JSON records assumptions, retrieval time and package versions.
""")
code("""
import json
output = Path("output")
output.mkdir(exist_ok=True)
prices.to_csv(output / "monthly_prices.csv")
source_audit.to_csv(output / "source_date_audit.csv")
results.to_csv(output / "monthly_net_returns.csv")
positions.to_csv(output / "held_weights.csv")
detail.to_csv(output / "strategy_backtest_detail.csv")
table.to_csv(output / "performance_measures.csv")
annual_returns.to_csv(output / "calendar_year_returns.csv")
sensitivity.to_csv(output / "sensitivity.csv")
rolling.to_csv(output / "rolling_performance.csv")
provenance = {"source": "Yahoo Finance via yfinance", "currency": "USD",
              "retrieved_utc": pd.Timestamp.now(tz="UTC").isoformat(),
              "assumptions": assumptions.to_dict(),
              "monthly_price_rows": len(prices), "backtest_months": len(results),
              "cash": "Prior month-end ^IRX quoted yield / 100 / 12; approximation",
              "execution": "Signal-close assumption; targets shifted one month",
              "versions": {p: version(p) for p in ["numpy", "pandas", "matplotlib", "yfinance"]}}
(output / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
for filename, data, title, ylabel in [
    ("cumulative_performance", wealth, "Cumulative performance, net of costs", "Value of USD 1"),
    ("drawdowns", dd, "Drawdown from peak (positive = loss)", "Loss from peak"),
    ("gross_net", cumulative(gross_net), "Strategy before and after costs", "Value of USD 1")]:
    ax = data.plot(title=title)
    ax.set_ylabel(ylabel)
    if filename == "drawdowns":
        ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.figure.tight_layout()
    ax.figure.savefig(output / f"{filename}.png", dpi=180, bbox_inches="tight")
    plt.close(ax.figure)
ax = positions.plot.area(ylim=(0, 1), title="Weights held during each return month")
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.figure.tight_layout()
ax.figure.savefig(output / "held_weights.png", dpi=180, bbox_inches="tight")
plt.close(ax.figure)
print("Saved tables, figures and provenance under", output.resolve())
""")
md("""
## 10. References, AI disclosure and submission checks
Course references: Lecture 1 introduction and financial calculations; Lecture 2
NumPy and bond valuation; Lecture 3 APIs/pandas and portfolio strategies;
Lecture 4 backtesting; Lecture 5 Monte Carlo and private-loan exercise;
`2270_Formulae` and the syllabus. See `COURSE_ALIGNMENT.md` for the file/section map.

Technical references:
* [yfinance download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)
* [pandas pct_change](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html)

**AI disclosure draft — group to review:** OpenAI Codex assisted with restructuring
the existing group strategy implementation, data checks, notebook/app consistency,
plots and verification. Validation includes hand-computed timing/drift examples,
independent OLS checks, and documented test commands. The group must understand
and justify the rule and conclusions, complete the disclosure of all tools used,
and follow the assignment's requirement to ask instructors before using AI for
strategy idea generation or complete solutions. No instructor approval is asserted.

Before submission, fill in group/members, review every result and interpretation,
write the investor prospectus (at most 7 content pages plus optional cover), and
include references/AI disclosure. If claiming the optional app marks, deploy it
and add both accessible app and GitHub URLs to notebook and prospectus.
Submit only the prospectus PDF and this notebook, below 50 MB combined.
""")

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "name": "python3",
       "language": "python"}, "language_info": {"name": "python", "version": "3.12"},
       "colab": {"provenance": []}}, "nbformat": 4, "nbformat_minor": 5}
(ROOT / "strategy_backtest.ipynb").write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Built standalone notebook with {len(cells)} cells.")
