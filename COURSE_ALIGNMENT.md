# Course alignment review

Reviewed all eleven files in `inputs/course/` and the assignment PDF in the
repository root. Original inputs remain unchanged. This implementation preserves
the group's existing allocation rule and makes its assumptions and verification
visible in the style of the teaching notebooks.

## What each input contributes

| Input file | Relevant structure or lesson | Project application |
|---|---|---|
| `Lecture1_Intro (1).pdf` | Model purpose and client; specify, build, test, document; simple interfaces and transparent components; verify AI output | Notebook §0 assumptions/client, numbered modelling steps, explicit limitations, shared app calculations and financial checks |
| `Lecture1_financial_calculations (2).ipynb` | Inputs first; visible formulas; compounding and discounting; numerical and financial plausibility checks | Separate assumptions; exact simple-return compounding; initial wealth one; distinguish arithmetic return from CAGR |
| `Lecture2_python_numpy (1).ipynb` | Arrays, broadcasting, boolean selection, explicit copies, tolerant float comparisons | Vectorized returns/signals/weight construction; copies of raw data; `np.isclose`/`assert_allclose` checks |
| `Lecture2_bond_valuation (1).ipynb` | Rate-risk interpretation, duration and reinvestment risk; explicit scenario changes | Explain why the AGG core is not risk-free; examine 2022 and parameter sensitivities. Individual-bond cash-flow pricing is not an ETF backtest step |
| `Lecture3_apis_pandas.ipynb` | APIs and pandas; four checks: shape, dates, NaNs, plot; careless `dropna()` silently changes a sample | Raw daily inspection before cleaning; monthly grid, source-date audit, explicit missing-data failures, no silent sample deletion |
| `Lecture3_portfolio_strategies.ipynb` | Portfolio weights vs rebalancing; hand-calculated alpha/beta, Sharpe and IR; 60-month rolling measures; high water marks | Explicit target and held weights; beta via covariance/variance; alpha via excess-return means; 60-month alpha/beta/Sharpe; positive drawdowns including opening wealth |
| `Lecture4_backtesting.ipynb` | Top-to-bottom signal/SMA/position workflow; `shift(1)`; execution assumption; gross/net costs; turnover; drift; bias discussion | Visible signal panels; lagged positions; gross/net reconciliation; drift-based traded weights; true buy-and-hold comparison; cost and delay sensitivities; explicit research limitations |
| `Lecture5_monte_carlo.ipynb` | State distributions/independence, reproducible random seeds, means vs medians, correct volatility scaling, assumptions dominate precision | Retain correct square-root-of-time scaling and discuss model limits. No Monte Carlo added: it is not required by the assignment and would introduce a different model |
| `Lecture5_private_loan.ipynb` | Separate market data and terms; explicit timing of cash flows; distinction between promised yield and realized return | Label `^IRX` as a quoted yield and its monthly return conversion as an approximation. Private-loan valuation is outside this ETF strategy |
| `2270_Formulae (2).pdf` | Excess-return covariance beta; Sharpe/IR denominators; HWM; positive drawdown | Formula definitions match; drawdowns shown as positive loss magnitudes, beta not annualized |
| `Syllabus (3).pdf` | Course scope: readable Python, data acquisition, analysis, interpretation | Use pandas, NumPy and Matplotlib with explanatory cells; keep complexity proportional to this assignment |

The root assignment PDF requires API data, explicit sample dates, implementable
decisions, cumulative comparison portfolios starting at one, annualized return,
volatility, Sharpe, alpha, information ratio and beta, interpretations, costs,
risks and reproducibility in a fresh Colab session. These requirements determine
the notebook's main output. An optimizer, Monte Carlo, LBO or private-credit model
is not required just because it appears elsewhere in the course.

## Notebook flow

1. Setup and version reporting, client and explicit assumptions.
2. Download daily adjusted closes; inspect shape, dates, missing values and plots.
3. Clean without filling or silently removing a month; inspect actual quote dates.
4. Calculate simple returns, descriptive statistics and correlations.
5. Build SMA signals and inverse-volatility targets; show the intermediate values.
6. Apply targets with a one-month lag; track actual holdings, weight drift and costs.
7. Compare monthly-rebalanced 60/40 and true buy-and-hold on identical dates.
8. Show wealth, gross/net performance, holdings and turnover.
9. Calculate and interpret required metrics with the course's formulas.
10. Show drawdowns, 60-month rolling measures, calendar years and selected crises.
11. Challenge costs, SMA windows and execution lag without choosing a winning rule.
12. Export source dates, result tables, figures and provenance; document limitations.

## Deliberate adaptations and corrected issues

**Return definition.** Course examples often use asset log returns. Here,
`portfolio_return = sum(weights * simple_returns)` is exact for a multi-asset
portfolio. Compounding uses `(1 + return).cumprod()`. Asset log returns are also
shown and reconciled to simple returns. Directly averaging asset log returns would
not reproduce the same portfolio wealth.

**Warm-up.** February 2006 through February 2007 provides thirteen month-end
prices and twelve returns. First complete signal: February 2007. First backtest
return: March 2007. The former January start used a ten-observation exception
inside a nominal twelve-month volatility window. That exception was removed;
all comparison portfolios start on the corrected common date.

**Data cleaning.** Do not delete an entire month or replace a missing return by
zero. Reject duplicate dates and invalid prices. Keep daily NaNs unfilled and use
the last valid quote per month with recorded source dates. Quotes over seven
calendar days old stop execution. This threshold tolerates weekends/holidays;
it does not certify final-session coverage. Inspect the audit rather than treating
a successful calculation as proof of data quality.

**Cash.** Prior month-end `^IRX / 100 / 12` is retained as a transparent approximation.
It is not an ETF or a bill total-return index. Discount-yield conversion, maturity,
day counts and mark-to-market effects are omitted. Use the same series for
portfolio cash and excess-return metrics; do not call it exact realized T-bill
performance.

**Timing.** Reindex on the full returns calendar before `shift(1)`. This prevents
missing target rows from compressing time. A signal-close fill remains optimistic,
as the lecture explicitly explains. The extra-month-delay comparison uses a common
April 2007 start for both lag variants. It is a coarse timing stress, not a
simulation of a next-day opening trade.

**Turnover and costs.** Count buys plus sells relative to drifted pretrade weights,
not just changes in consecutive targets. Opening turnover is one and costs include
proxy-cash trades. Apply the course-style additive return deduction to every
portfolio; no terminal liquidation. The sum of monthly cost ratios is not the
compounded loss in wealth. Show gross and net wealth separately.

**Metrics.** Covariance beta and mean-based alpha follow Lecture 3 and are
cross-checked with independent least squares. Sharpe uses excess-return volatility.
IR uses active returns and tracking error. Drawdown includes initial capital one,
so a loss in the first month is counted; signs now match the positive course
definition. An undefined denominator yields NaN rather than a fabricated ratio.

**Readable reproduction.** All calculation functions are visible in the notebook.
The builder copies them verbatim from `app.py`; the notebook does not fetch
a Python module from a mutable GitHub branch. A consistency test detects divergence.
The Streamlit app contains these functions inline and displays held-month weights. The interface runs only under the main guard, so tests can import the functions safely.

**Scope.** No additional optimization or simulation is needed for this strategy.
Course examples include intentionally wrong code to teach verification. Reproduce
the corrected methods and their explanations, not the instructional bugs.

## Verification commands and interpretation

```powershell
.\.venv\Scripts\python.exe tools/build_notebook.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools/run_notebook.py
```

Tests use hand-checkable examples for lags, first purchase costs, drift, buy-and-hold
wealth, missing data, full warm-up, cash timing, first-month losses and OLS.
They also check that changing future prices leaves past decisions/results unchanged,
and that notebook functions match the app's module. The notebook independently
reconciles its first return, held weights and net returns.

The execution helper starts a fresh local Jupyter kernel and skips only package
installation, which is already handled by requirements. Its executed notebook is
saved under `output/`. This is not a claim that execution inside Google Colab was
observed. Any API failure or unexecuted validation must be reported explicitly.

## Verification observed on 26 November 2026

All 16 automated tests passed, including the Streamlit app's changed assumptions,
0%/100% core-weight boundaries and source-error handling. The notebook's 22 analysis
code cells ran in a fresh local kernel using live Yahoo API data; the installation
cell was skipped because dependencies had already been installed. The data covered
249 monthly price observations (February 2006–October 2026) and 236 return months
(March 2007–October 2026). There were no error outputs in the completed notebook.
All nine displayed figures were visually reviewed. The executed copy, exported
tables/figures and version/source provenance are saved under the ignored output
directory. Course inputs have no changes. Google Colab itself and a deployed
Streamlit website were not exercised.

## Remaining submission items

The group must complete its name/members, review the financial interpretations and
prepare the investor prospectus (maximum seven content pages plus optional cover).
Do not claim that the optional app is complete until an accessible Streamlit URL
and GitHub URL are included in both deliverables. The AI disclosure must describe
all tools used and how outputs were checked. The assignment says to ask instructors
before AI strategy idea generation or complete solutions; this refactor does not
assert that permission has been obtained.

External technical references:
[yfinance API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html),
[pandas pct_change](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html).
