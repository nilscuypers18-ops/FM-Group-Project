# FM Group Project

Python project for 2270 Financial Modeling. The notebook follows the course's
sequence: assumptions → API data → four data checks → deliberate cleaning →
signals and weights → lagged backtest → costs → performance and risk → verification.

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
The former January 2007 start used only ten returns; that exception was removed.
The 60/40 SPY/AGG benchmark rebalances monthly; the same-assets buy-and-hold
comparison trades once and lets weights drift.

Data: Yahoo Finance API via `yfinance`, adjusted daily ETF closes converted to
calendar month-end. Cash return is the preceding `^IRX` annual quoted yield
divided by 100 and 12. This is an approximation, not an investable bill
total-return index. No forward fill, silent deletion of months or zero-filled
missing returns. Inspect the four checks and quote-date audit after every refresh.

## Files

| File | Purpose |
|---|---|
| `strategy_backtest.ipynb` | Standalone Colab notebook, with visible calculations and course-style pandas/Matplotlib figures |
| `app.py` | Self-contained strategy calculations and Streamlit controls; safe to import for tests |
| `portal.py` | Credential-free investor/manager entry, portfolio overview, trade-history placeholder and team content |
| `assets/portal.css` | Responsive T Capital presentation and visual styling |
| `COURSE_ALIGNMENT.md` | Review of every input file, course mapping, methodological differences and submission checklist |
| `tools/build_notebook.py` | Copies shared functions into the notebook; no GitHub download at notebook run time |
| `tests/test_strategy.py` | Small hand-checkable financial logic, data quality and notebook consistency checks |
| `tools/run_notebook.py` | Executes analysis in a fresh local Jupyter kernel with live API data |
| `requirements.txt` | Notebook/app packages |
| `requirements-dev.txt` | Additional packages for automated notebook execution |
| `inputs/course/` | Unchanged course reference materials |
| `2270_FM_group_assignment_v2 (1).pdf` | Assignment specification |

The notebook shows raw data checks, source dates, descriptive returns/correlations,
price/SMA/position panels, lagged holdings, cumulative wealth starting at one,
gross/net costs, required metrics, positive drawdowns, rolling 60-month metrics,
calendar-year returns and selected crisis episodes. SMA/cost/delay sensitivities
challenge the fixed base rule; they do not select a winning parameter or constitute
an unseen validation sample.

Generated CSVs, figures, an executed notebook and provenance are under `output/`
and are ignored by Git. These are outputs, not input data required for submission.

## Run in Google Colab

Open `strategy_backtest.ipynb` in a fresh Colab session and select **Runtime → Run all**.
The setup cell installs the analysis packages. All calculation code is contained
inside the notebook. No repository checkout or separate Python/data file is needed.
Internet access and working Yahoo API coverage are required. API/data failures stop
the analysis; inspect them instead of replacing observations with fabricated data.

## Run locally

Use Python 3.12. From this repository folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Select `.venv` as the notebook kernel. To edit shared calculations, update
`app.py` and regenerate the notebook. Edit notebook narrative/figures in
`tools/build_notebook.py`, since regeneration replaces the notebook's contents.

The app opens on a **T Capital** landing page (working brand for Group T).
**Investor login** and **Investment Manager login** are one-click demo navigation:
there are no credential fields, user accounts or authentication records. The role
exists only in the active Streamlit session and is not an access-control boundary.
Investors see the base strategy; managers can adjust scenario parameters in the
sidebar. **Switch portal** returns to the entry screen. Team and trade-history
pages remain available even if the market-data source is unavailable.

Edit `TEAM` in `portal.py` to add the six members' student IDs and local photo paths
(for example `assets/team/nils.jpg`). Initials appear until photos are supplied.
Trade History is a clearly marked placeholder for a later data integration.
The financial calculations and standalone submission notebook are unchanged.

```powershell
.\.venv\Scripts\python.exe tools/build_notebook.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools/run_notebook.py
```

The last command skips only the installation cell, because packages are already
installed, and executes every analysis cell in a fresh local kernel. It is a local
reproduction check, not a claim that Google Colab itself was tested.

## Submission work still owned by the group

Review all outputs and explain every reported metric for the target client.
Write the investor prospectus: at most seven content pages plus optional cover,
including references and any optional-app evidence. Complete the Moodle group,
members and AI disclosure. The assignment asks instructors to be consulted before
using AI for strategy idea generation or complete solutions; no such approval is
asserted here.

For optional app marks, deploy `app.py` on Streamlit Community Cloud and put both
the accessible app URL and GitHub URL in notebook and prospectus. Source code alone
does not meet that requirement. Deployment has not been performed by this refactor.
Submit only the prospectus PDF and notebook, under 50 MB combined.

## Working together with GitHub Desktop

Each member uses their own clone. Pull current changes, create an individual branch,
review and commit local edits, push and open a pull request for group review.
Keep course originals unchanged and coordinate edits to the notebook.
The repository shares files and commits; it does not share local chats.

Technical references:
[yfinance download API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html),
[pandas pct_change](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pct_change.html).
