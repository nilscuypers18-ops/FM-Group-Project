X# FM Group Project

Python project for 2270 Financial Modeling. The notebook follows the course's
sequence: assumptions → API data and checks → signals and weights → lagged
backtest with costs → performance measures → sensitivity → limitations.

## Project team

| Member | Student ID |
|---|---|
| Nils Andreas Cuypers | 78681 |
| Michelle de Kock | 79818 |
| Hanna Kiss | 78909 |
| Felix Michele Mellino | 79820 |
| Niklas Peter | 78399 |
| Leif Plötzky | 78151 |

## Investment rule

The existing group concept is a family office seeking long-term wealth preservation
and growth in USD. The base rule keeps 60% in AGG and allocates a 40% satellite
budget across SPY, GLD and DBC using inverse trailing 12-month volatility.
An asset is held only above its trailing 10-month simple moving average.
Its inactive share goes to the cash proxy; active assets do not absorb that share.

Signals use month-end information and earn the following month's return.
The backtest assumes execution at the signal close, an optimistic assumption
explained in the notebook. Transaction costs are 10 bps times buys plus sells,
measured relative to drifted pretrade weights. Initial turnover is one; final
liquidation is not charged. All portfolios use the same conventions.

Prices start in February 2006. **Backtest returns start in March 2007 and end
in October 2026.** Thirteen prices are needed to estimate twelve monthly returns.
The benchmark is 40/60 SPY/AGG (40% equity, 60% bonds), rebalanced monthly.
It has the same 60% bond share as the strategy's core.

Data: Yahoo Finance API via `yfinance`, adjusted daily ETF closes converted to
calendar month-end. Cash return is the preceding `^IRX` annual quoted yield
divided by 100 and 12. This is an approximation, not an investable bill
total-return index. A missing month stops the calculation instead of being filled.

## Historical crisis stress test

Historical stress test on the existing monthly backtest; no new model, no Monte
Carlo, only code patterns from `inputs/course/`. Crises: the three largest SPY
month-end drawdowns since March 2007.

| Crisis | Window | SPY |
|---|---|---|
| Financial crisis | Oct 2007 – Feb 2009 | −51% |
| Covid crash | Dec 2019 – Mar 2020 | −19% |
| Inflation/rate shock | Dec 2021 – Sep 2022 | −24% |

The portal's **Crisis Analysis** page uses the notebook's return windows:
Nov 2007–Feb 2009, Jan–Mar 2020 and Jan–Sep 2022. The preceding month-end is
the starting value of 1. It compares net returns, local maximum drawdown and
recovery for the strategy and 40/60 benchmark. Recovery counts months from
the lowest value inside the crisis to the first subsequent return to the
pre-crisis starting value; unrecovered paths are labelled through the sample end.
Month-end observations understate intramonth losses.

## Files

| File | Purpose |
|---|---|
| `strategy_backtest.ipynb` | **The master copy.** Submitted notebook; runs on its own in Google Colab |
| `app.py` | Streamlit entry point. Loads the strategy functions straight from the notebook |
| `portal.py`, `assets/portal.css`, `.streamlit/config.toml` | App pages and styling (T Capital portal), including Trade History |
| `activity.py` | Trade History logic: monthly rebalance log, per-asset trade explanations, illustrative USD values |
| `fund_analytics.py` | Calendar compounding, monthly heatmap data and historical crisis/recovery summaries; no investment rules |
| `crisis_analysis.ipynb` | Crisis stress test (2008, Covid, 2022) on the same backtest, imported from `app.py` |
| `tests/` | Small checks of timing, costs, weights and metrics, the app pages, and `test_activity.py` (trade history reconciles with the backtest) |
| `COURSE_ALIGNMENT.md` | How the code maps to the course notebooks |
| `requirements.txt` | Python packages for notebook and app |
| `inputs/course/` | Unchanged course notebooks and slides |

## How the notebook and the app stay in sync

Write all strategy code **in the notebook only**. Every code cell that starts with
`# STRATEGY FUNCTIONS` is read and executed by `app.py` when the app starts, so the
app automatically uses the latest notebook code. Keep those cells free of plots and
`display()`; put analysis and charts in normal cells.

## Run in Google Colab

Open `strategy_backtest.ipynb` in a fresh Colab session and select **Runtime → Run all**.
Internet access for the Yahoo Finance API is required; no other files are needed.

## Run locally

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The app opens on a **T Capital** landing page. **Log in as investor** and **Log in
as manager** are one-click demo navigation without passwords or accounts. After login,
a side navigation shows Overview, Investment Approach, Performance, Fund Insights,
Crisis Analysis, Trade History and Team. Investors see
the base strategy; managers can change the MA length, core weight and costs in the
sidebar. The Team page shows all six members and their student
IDs. Edit `TEAM` in `portal.py` to add local photo paths.

**Investment Approach** explains the mandate, core/satellite allocation, asset universe,
trend filter, volatility sizing, implementation and limitations without a data download.
**Fund Insights** explains indexed asset paths, monthly return correlations, rolling
12-month volatility and invested satellite vs cash exposure. Manager assumptions
apply throughout, and pages label scenarios that differ from the base strategy.

**Overview** accepts an illustrative initial investment and shows the strategy and
benchmark ending values, USD wealth paths and CAGR. The amount is retained when
switching to Trade History. **Performance** includes compounded calendar-year
returns (partial years marked with `*`) and a portfolio-selectable monthly heatmap;
unobserved months remain blank. Annual returns and crisis summaries have CSV exports.

**Trade History** shows the opening allocation and every monthly review: drifted
holdings before the trade, new targets, buys/sells, costs, trend inputs and a short
explanation per asset, with CSV export. Dollar amounts illustrate an initial
investment (USD 100,000 by default); they are model notionals, not broker orders.
The backtest records pretrade weights and trade sizes for this page; this does not
change any returns.

## Submission work still owned by the group

Review all outputs and explain every reported metric for the target client.
Write the investor prospectus: at most seven content pages plus optional cover,
including references and any optional-app evidence. Complete the Moodle group,
members and AI disclosure. The assignment asks instructors to be consulted before
using AI for strategy idea generation or complete solutions; no such approval is
asserted here.

For optional app marks, deploy `app.py` on Streamlit Community Cloud and put both
the accessible app URL and GitHub URL in notebook and prospectus. Source code alone
does not meet that requirement.
Submit only the prospectus PDF and notebook, under 50 MB combined.

## Working together with GitHub Desktop

Each member uses their own clone. Pull current changes, create an individual branch,
review and commit local edits, push and open a pull request for group review.
Keep course originals unchanged and coordinate edits to the notebook.
The repository shares files and commits; it does not share local chats.

Technical references:
[yfinance download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html),
[pandas pct_change](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html).
