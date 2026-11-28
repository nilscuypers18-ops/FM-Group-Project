"""Presentation layer for the T Capital portal (Streamlit).

Calculations come from app.py (strategy cells of the notebook); trade history
logic lives in activity.py. Edit TEAM below to add local photo paths.
The two logins are one-click demo roles, not authentication.
"""
import base64
import calendar
from html import escape
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Streamlit renders images; no desktop plotting backend is needed.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator, PercentFormatter
import streamlit as st

from activity import rebalance_history
from fund_analytics import CRISES, calendar_returns, monthly_grid, crisis_summary


TEAM = [
    {"name": "Nils Andreas Cuypers", "initials": "NC", "photo": None, "student_id": "78681"},
    {"name": "Michelle de Kock", "initials": "MD", "photo": None, "student_id": "79818"},
    {"name": "Hanna Kiss", "initials": "HK", "photo": None, "student_id": "78909"},
    {"name": "Felix Michele Mellino", "initials": "FM", "photo": None, "student_id": "79820"},
    {"name": "Niklas Peter", "initials": "NP", "photo": None, "student_id": "78399"},
    {"name": "Leif Plötzky", "initials": "LP", "photo": None, "student_id": "78151"},
]
ROOT = Path(__file__).resolve().parent
ACCENT = "#F26B3A"
SERIES = {"Strategy": ACCENT, "40/60 SPY/AGG": "#0A0A0A"}
ASSETS = {  # ticker -> name, role, colour
    "AGG": ("US Aggregate Bonds", "Core", "#3F3F46"),
    "SPY": ("S&P 500", "Satellite", ACCENT),
    "GLD": ("Gold", "Satellite", "#D9A93A"),
    "DBC": ("Commodities", "Satellite", "#8C9BF5"),
    "TBILL": ("3M US T-Bills", "Cash", "#CFCFCB"),
}
PAGES = ["Overview", "Investment Approach", "Performance", "Fund Insights", "Crisis Analysis", "Monte Carlo",
         "Trade History", "Team Overview"]
LABELS = {"Team Overview": "Team"}


def html(value):
    st.html(value)


def set_role(role):
    st.session_state.portal_role = role
    st.session_state.portal_page = "Overview"


def styles():
    html(f"<style>{(ROOT / 'assets' / 'portal.css').read_text(encoding='utf-8')}</style>")


def brand():
    html('<div class="brand"><span class="brand-mark">T</span>'
         '<span>T Capital<small>Investment management</small></span></div>')


def footer():
    html('<div class="foot"><span>T Capital · 2270 Financial Modeling</span>'
         '<span>Historical backtest · not investment advice</span></div>')


def heading(eyebrow, title, grey=""):
    grey_html = f" <span>{escape(grey)}</span>" if grey else ""
    html(f'<div class="rise"><span class="eyebrow">{escape(eyebrow)}</span>'
         f'<h1 class="display">{escape(title)}{grey_html}</h1></div><div class="gap sm"></div>')


def cards(items, cols=3):
    body = "".join(f'<div class="card"><div class="num">{escape(n)}</div><h4>{escape(t)}</h4>'
                   f'<p>{escape(p)}</p></div>' for n, t, p in items)
    html(f'<div class="grid" style="--cols:{cols}">{body}</div>')


# --- landing ------------------------------------------------------------------
def landing():
    brand()
    html('''<div class="gap"></div><div class="rise"><span class="eyebrow">Core–satellite · Trend following · USD</span>
      <h1 class="display">A clear perspective. <span>A longer horizon.</span></h1>
      <p class="lead d1">60% bonds for stability. 40% in equities, gold and commodities,
      held only while their trend is up. Rebalanced monthly.</p></div><div class="gap"></div>''')
    investor, manager = st.columns(2, gap="medium")
    with investor, st.container(key="login_investor"):
        html('<div class="mono">For investors</div><h3 style="font-weight:400;margin:.5rem 0">'
             'Performance, holdings, trades and team.</h3>')
        st.button("Log in as investor", key="enter_investor", type="primary", width="stretch",
                  on_click=set_role, args=("Investor",))
    with manager, st.container(key="login_manager"):
        html('<div class="mono">For investment managers</div><h3 style="font-weight:400;margin:.5rem 0">'
             'Everything, plus adjustable assumptions.</h3>')
        st.button("Log in as manager", key="enter_manager", width="stretch",
                  on_click=set_role, args=("Investment Manager",))
    st.caption("Demo access: one click, no password.")
    footer()


# --- shell --------------------------------------------------------------------
def shell(m, role):
    """Sidebar: brand, navigation, manager assumptions, log out."""
    params = {"ma": m.MA_MONTHS, "core": m.CORE_WEIGHT, "cost": m.COST_BPS}
    with st.sidebar:
        brand()
        html(f'<span class="role">{escape(role)}</span>')
        page = st.radio("Navigation", PAGES, key="portal_page", label_visibility="collapsed",
                        format_func=lambda p: LABELS.get(p, p))
        if role == "Investment Manager":
            st.divider()
            html('<div class="mono">Assumptions</div>')
            params["ma"] = st.slider("Moving average (months)", 3, 12, m.MA_MONTHS, key="manager_ma")
            params["core"] = st.slider("Core weight in AGG", 0.0, 1.0, m.CORE_WEIGHT, .05, key="manager_core")
            params["cost"] = st.slider("Cost (bps per turnover)", 0, 50, m.COST_BPS, key="manager_cost")
            if (params["ma"], params["core"], params["cost"]) != (m.MA_MONTHS, m.CORE_WEIGHT, m.COST_BPS):
                st.caption("Scenario: differs from the base strategy.")
        st.divider()
        st.button("Log out", key="logout", on_click=set_role, args=(None,), width="stretch")
    return page, params


# --- data ---------------------------------------------------------------------
@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_data(_model):
    return _model.download_data(_model.DOWNLOAD_START, _model.BACKTEST_END)


def backtest(m, params):
    """(prices, rf, results, rf_bt, detail) for the scenario, or None after showing the error."""
    try:
        with st.spinner("Loading market data…"):
            prices, rf = load_data(m)
            results, rf_bt, _, detail = m.run_all(prices, rf, params["core"], params["ma"],
                                                  params["cost"])
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Data or calculation check failed: {exc}")
        if st.button("Retry"):
            load_data.clear()
            st.rerun()
        return None
    return prices, rf, results, rf_bt, detail


def holdings(detail):
    return detail.filter(like="weight_").rename(columns=lambda c: c.removeprefix("weight_"))


def investment_input(key):
    """Keep the illustrative capital across pages, including Streamlit widget cleanup."""
    def remember():
        st.session_state.investment_capital = st.session_state[key]
    return st.number_input("Initial investment (USD)", min_value=1_000.0,
                           max_value=1_000_000_000_000.0,
                           value=st.session_state.get("investment_capital", 100_000.0),
                           step=10_000.0, key=key, on_change=remember)


def scenario_note(m, params):
    changed = (params["core"], params["ma"], params["cost"]) != (m.CORE_WEIGHT, m.MA_MONTHS, m.COST_BPS)
    st.caption(f"{'Manager scenario' if changed else 'Base strategy'} · {params['core']:.0%} AGG core · "
               f"{params['ma']}-month trend · {params['cost']} bps costs · historical model, USD")


def line_chart(data, ylabel, percent=False, colors=None, invert=False):
    if hasattr(data, "to_frame"):
        data = data.to_frame()
    colors = colors or [SERIES.get(c, "#6B6B6B") for c in data.columns]
    with plt.rc_context({"font.size": 10, "axes.labelcolor": "#6B6B6B", "xtick.color": "#6B6B6B",
                         "ytick.color": "#6B6B6B", "axes.edgecolor": "#E6E6E3"}):
        fig, ax = plt.subplots(figsize=(11, 3.8))
        data.plot(ax=ax, linewidth=1.8, color=colors)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("")
        ax.grid(axis="y", color="#ECECE9", linewidth=.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1), ncol=3)
        if percent:
            ax.yaxis.set_major_formatter(PercentFormatter(1))
        if invert:
            ax.invert_yaxis()
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)


# --- overview -----------------------------------------------------------------
def overview(m, params):
    heading("Portfolio overview", "Your portfolio,", "at a glance.")
    data = backtest(m, params)
    if data is None:
        return
    prices, _, results, rf_bt, detail = data
    scenario_note(m, params)
    table = m.performance_table(results, rf_bt)
    s, b = table.loc["Strategy"], table.loc[m.BENCHMARK]
    c1, c2, c3 = st.columns(3)
    c1.metric("Annualised return", f"{s['Ann. return']:.2%}",
              f"{(s['Ann. return'] - b['Ann. return']) * 100:+.2f} pp vs 40/60")
    c2.metric("Sharpe ratio", f"{s['Sharpe']:.2f}", f"{s['Sharpe'] - b['Sharpe']:+.2f} vs 40/60")
    c3.metric("Maximum drawdown", f"{s['Max drawdown']:.2%}",
              f"{(s['Max drawdown'] - b['Max drawdown']) * 100:+.2f} pp vs 40/60", delta_color="inverse")

    with st.container(key="panel_growth"):
        st.subheader("What would your investment have become?")
        capital = investment_input("overview_capital")
        wealth = m.cumulative(results) * capital
        c1, c2, c3 = st.columns(3)
        c1.metric("Strategy ending value", f"${wealth['Strategy'].iloc[-1]:,.2f}",
                  f"${wealth['Strategy'].iloc[-1] - capital:+,.2f} total gain / loss")
        c2.metric("Benchmark ending value", f"${wealth[m.BENCHMARK].iloc[-1]:,.2f}")
        c3.metric("Compound annual growth · CAGR", f"{s['CAGR']:.2%}",
                  f"{(s['CAGR'] - b['CAGR']) * 100:+.2f} pp vs 40/60")
        html(f'<div class="mono">{results.index[0]:%b %Y} – {results.index[-1]:%b %Y} · net of model costs</div>')
        line_chart(wealth, "Portfolio value · USD")
        st.caption("Historical illustration with one initial investment, no deposits or withdrawals. "
                   "CAGR includes compounding; the annualised return above is 12 × the mean monthly return. "
                   "Taxes, management fees and inflation are excluded. This is not a forecast.")

    positions = holdings(detail)
    left, right = st.columns([1.1, 1], gap="medium")
    with left, st.container(key="panel_holdings"):
        signal_date = positions.index[-1] - pd.offsets.MonthEnd(1)
        signals = m.trend_signal(prices[m.SATELLITE], params["ma"]).loc[signal_date]
        html(f'<div class="mono">Historical model allocation · {positions.index[-1]:%B %Y}</div>'
             f'{allocation_rows(positions.iloc[-1], signals)}')
        st.caption(f"Target weights held for this return month; signal dated {signal_date:%d %b %Y}.")
    with right:
        cards([("01", f"{params['core']:.0%} bond core", "AGG, held at a fixed weight."),
               ("02", f"{params['ma']}-month trend filter",
                "SPY, GLD and DBC are held only above their moving average. Otherwise: T-bills."),
               ("03", "Risk-balanced satellite",
                "Calmer assets get a larger share (inverse 12-month volatility).")], cols=1)


def allocation_rows(latest, signals=None):
    rows = []
    for i, (ticker, (name, role, colour)) in enumerate(ASSETS.items()):
        w = float(latest.get(ticker, 0.0))
        if role == "Satellite":
            active = bool(signals[ticker]) if signals is not None else w > 0
            tag = '<span class="tag on">Trend on</span>' if active else '<span class="tag off">Trend off</span>'
        else:
            tag = f'<span class="tag neutral">{role}</span>'
        label = "CASH" if ticker == "TBILL" else ticker
        text = "#3A3A3A" if ticker == "TBILL" else "#fff"
        rows.append(f'<div class="row"><div class="badge" style="background:{colour};color:{text}">{label}</div>'
                    f'<div class="main"><div class="name">{name}</div><div class="meta">{label} · {role}</div>'
                    f'<div class="bar"><div style="width:{w:.1%};background:{colour};animation-delay:{.1 + i * .08:.2f}s">'
                    f'</div></div></div><div class="right"><div class="w">{w:.1%}</div>{tag}</div></div>')
    return f'<div class="rows">{"".join(rows)}</div>'


# --- performance --------------------------------------------------------------
def performance(m, params):
    heading("Performance", "The evidence,", "net of costs.")
    data = backtest(m, params)
    if data is None:
        return
    prices, _, results, rf_bt, detail = data
    scenario_note(m, params)
    table = m.performance_table(results, rf_bt)
    pct = ["Ann. return", "CAGR", "Volatility", "Alpha (ann.)", "Tracking error", "Max drawdown"]
    shown = table.T.astype(object)
    for row in shown.index:
        fmt = "{:.2%}" if row in pct else "{:.2f}"
        shown.loc[row] = ["–" if pd.isna(v) else fmt.format(v) for v in table[row]]
    with st.container(key="panel_measures"):
        html(f'<div class="mono">Performance measures · {results.index[0]:%b %Y} – {results.index[-1]:%b %Y}</div>')
        st.dataframe(shown.rename_axis("Measure"), width="stretch")
        st.caption("Volatility = √12 × std. Sharpe uses excess returns over T-bills. Alpha and beta vs "
                   "40/60 SPY/AGG on excess returns; beta not annualised. Drawdown shown as a positive loss.")
    with st.container(key="panel_drawdown"):
        html('<div class="mono">Loss from previous high</div>')
        line_chart(m.drawdowns(results), "Loss from peak", percent=True, invert=True)
    calendar_section(results)
    with st.container(key="panel_allocation"):
        html('<div class="mono">Allocation history</div>')
        positions = holdings(detail)
        fig, ax = plt.subplots(figsize=(11, 3.6))
        positions.plot.area(ax=ax, ylim=(0, 1), linewidth=0,
                            color=[ASSETS[c][2] for c in positions.columns])
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_xlabel("")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(ncol=5, loc="lower left", bbox_to_anchor=(0, 1), frameon=False)
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)
    with st.container(key="panel_costs"):
        html('<div class="mono">Before and after transaction costs</div>')
        gross_net = detail[["gross", "net"]].rename(columns={"gross": "Strategy gross", "net": "Strategy"})
        line_chart(m.cumulative(gross_net), "Value of USD 1", colors=["#A1A1AA", ACCENT])
        st.caption(f"Average monthly turnover after the first purchase: {detail['turnover'].iloc[1:].mean():.2%}.")
    with st.expander("Data and method"):
        st.write(f"Monthly prices: {len(prices)} ({prices.index[0]:%b %Y} – {prices.index[-1]:%b %Y}) · "
                 f"backtest months: {len(results)}")
        st.caption("Yahoo Finance adjusted closes, converted to month-end. Cash = previous ^IRX yield / 100 / 12 "
                   "(approximation). Signal-close execution is optimistic. Taxes and market impact are not modelled.")
    st.download_button("Download monthly returns", results.to_csv().encode("utf-8"),
                       file_name="monthly_net_returns.csv", mime="text/csv")


# --- investment approach ------------------------------------------------------
def approach_page(m, params):
    heading("Investment approach", "A steady core.", "A responsive satellite.")
    scenario_note(m, params)
    core, satellite = params["core"], 1 - params["core"]
    html(f'''<section class="approach-hero">
      <div><span class="section-kicker">Our investment philosophy</span>
        <h2>Preserve perspective.<br>Invest with discipline.</h2>
        <p>A rules-based portfolio for a USD-based family office seeking long-term wealth
        preservation and growth. A bond core anchors the allocation; a diversified satellite
        responds to monthly market trends.</p></div>
      <div class="allocation-split" aria-label="{core:.0%} bond core and {satellite:.0%} satellite">
        <div><strong>{core:.0%}</strong><span>Bond core</span><small>US aggregate bonds · AGG</small></div>
        <div class="satellite"><strong>{satellite:.0%}</strong><span>Adaptive satellite</span>
        <small>Equities · Gold · Commodities</small></div>
        <div class="split-track"><span style="width:{core:.2%}"></span></div>
      </div></section>''')
    st.subheader("One portfolio. Four clear decisions.")
    cards([
        ("The anchor", "Keep a fixed bond core",
         f"{core:.0%} is allocated to AGG at each monthly rebalance. Bonds remain invested even when satellite trends turn off."),
        ("The balance", "Size the satellite by volatility",
         f"The {satellite:.0%} satellite budget is shared across SPY, GLD and DBC using inverse trailing {m.VOL_MONTHS}-month volatility. Lower volatility receives a larger share."),
        ("The filter", "Follow the monthly trend",
         f"Each satellite is held only when its month-end adjusted price exceeds its {params['ma']}-month simple moving average. Its inactive share moves to the cash proxy."),
        ("The discipline", "Review once a month",
         f"Month-end signals determine next month's holdings. Model costs of {params['cost']} bps are charged on buys plus sells, including drift corrections."),
    ], cols=2)
    st.subheader("The investment universe")
    universe = pd.DataFrame([
        ("AGG", "US aggregate bonds", "Fixed core", "Income and diversification; exposed to interest-rate and credit risk."),
        ("SPY", "US large-cap equities", "Trend-filtered satellite", "Participation in equity growth; exposed to equity-market losses."),
        ("GLD", "Gold", "Trend-filtered satellite", "A different source of returns; no income and potentially sharp price swings."),
        ("DBC", "Broad commodities", "Trend-filtered satellite", "Commodity exposure; futures and roll effects can affect returns."),
        ("TBILL", "Cash-return proxy", "Inactive satellite allocation", "Previous ^IRX annual yield / 100 / 12; an approximation, not a traded fund."),
    ], columns=["Ticker", "Exposure", "Portfolio role", "What to understand"])
    st.dataframe(universe, hide_index=True, width="stretch")
    left, right = st.columns(2, gap="medium")
    with left, st.container(key="panel_approach_process"):
        st.subheader("From observation to allocation")
        st.markdown("**Month-end data → trend and volatility → target weights → next month's return.**")
        st.write("An inactive satellite does not hand its budget to the other risky assets. "
                 "That share stays in the cash proxy until the asset's trend turns positive again.")
        st.caption("The backtest assumes execution at the same close used to observe the signal. "
                   "This is optimistic; a real implementation would need an executable trading schedule.")
    with right, st.container(key="panel_approach_limits"):
        st.subheader("What the approach asks of investors")
        st.write("A long horizon and tolerance for losses. The bond core can fall, trend signals can reverse "
                 "repeatedly, and the strategy can lag during fast market rebounds. Capital is not guaranteed.")
        st.caption("Educational model portfolio, not a live regulated fund. No actual subscriptions, "
                   "NAV, assets under management or management-fee schedule are represented.")


# --- calendar performance -----------------------------------------------------
def calendar_section(results):
    with st.container(key="panel_calendar"):
        st.subheader("Year by year")
        st.write("Compare the compounded net return in each calendar year. This shows when the "
                 "strategy helped and when the benchmark did better.")
        annual = calendar_returns(results)
        fig, ax = plt.subplots(figsize=(11, 3.8))
        annual.plot.bar(ax=ax, color=[SERIES.get(c, "#6B6B6B") for c in annual.columns], width=.75)
        ax.axhline(0, color="#9A9A96", linewidth=.8)
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_xlabel("")
        ax.set_ylabel("Compounded net return")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, ncol=2)
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)
        st.caption("* Partial year: only observed months are compounded, without annualisation. "
                   f"Sample: {results.index[0]:%b %Y}–{results.index[-1]:%b %Y}.")
        with st.expander("View annual return table"):
            st.dataframe(annual.style.format("{:+.2%}"), width="stretch")
        st.download_button("Download annual returns", annual.to_csv().encode("utf-8"),
                           "annual_net_returns.csv", "text/csv", key="annual_download")
    with st.container(key="panel_heatmap"):
        st.subheader("Month by month")
        portfolio = st.selectbox("Heatmap portfolio", results.columns, key="heatmap_portfolio")
        grid = monthly_grid(results[portfolio])
        values = grid.to_numpy(dtype=float)
        limit = max(float(np.nanmax(np.abs(values))), .01)
        fig, ax = plt.subplots(figsize=(11, max(4, len(grid) * .32)))
        cmap = plt.get_cmap("RdYlGn").with_extremes(bad="#F0F0ED")
        im = ax.imshow(np.ma.masked_invalid(values), cmap=cmap, vmin=-limit, vmax=limit, aspect="auto")
        ax.set_xticks(range(12), list(calendar.month_abbr)[1:])
        ax.set_yticks(range(len(grid)), grid.index)
        for row in range(len(grid)):
            for col in range(12):
                value = values[row, col]
                ax.text(col, row, "—" if np.isnan(value) else f"{value:+.1%}",
                        ha="center", va="center", fontsize=8,
                        color="white" if abs(value) > limit * .65 else "#222222")
        ax.spines[:].set_visible(False)
        fig.colorbar(im, ax=ax, fraction=.025, pad=.025, format=PercentFormatter(1))
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)
        st.caption("Each cell is one month's net return, not an annualised figure. "
                   "Green indicates a gain, red a loss; signed values also show the direction. "
                   "Grey cells (—) are outside the sample, not zero-return months.")
        with st.expander("View monthly return table"):
            readable = grid.rename(columns=lambda month: calendar.month_abbr[month])
            st.dataframe(readable.style.format("{:+.2%}", na_rep="—"), width="stretch")


# --- fund insights ------------------------------------------------------------
def insights_page(m, params):
    heading("Fund insights", "Understand the portfolio.", "Beyond the headline return.")
    scenario_note(m, params)
    html('''<p class="lead">Explore the exposures behind the model, how they move together,
      and how portfolio risk changes through time. Each chart answers a different investment question.</p>''')
    data = backtest(m, params)
    if data is None:
        return
    prices, _, results, _, detail = data
    cards([
        ("Mandate", "Long-term wealth preservation & growth", "USD-based model portfolio with monthly rebalancing; no leverage or short positions."),
        ("Comparison", "40% SPY / 60% AGG", "A monthly rebalanced stock/bond benchmark, measured over the same dates and with the same cost assumptions."),
        ("Evidence", f"{len(results)} monthly observations", f"{results.index[0]:%b %Y} to {results.index[-1]:%b %Y}. Historical net returns; not a live fund track record."),
    ])
    with st.container(key="panel_assets"):
        st.subheader("Different assets. Different paths.")
        st.write("How did each underlying ETF develop over the backtest? All exposures start at 100 "
                 "at the month-end before the first portfolio return.")
        baseline = results.index[0] - pd.offsets.MonthEnd(1)
        sample = prices.loc[baseline:results.index[-1], m.ASSETS]
        line_chart(sample.div(sample.iloc[0]) * 100, "Indexed adjusted price · start = 100",
                   colors=[ASSETS[c][2] for c in sample.columns])
        st.caption("Standalone adjusted-price histories, without the strategy's weights or transaction costs. "
                   "This chart explains the investment universe; it is not the fund's performance.")
    with st.container(key="panel_correlation"):
        st.subheader("Do the assets move together?")
        st.write("Correlation compares monthly ETF returns. Values near +1 mean they tended to move "
                 "together; values near zero mean a weak linear relationship; negative values mean opposing movements.")
        asset_returns = prices.pct_change().reindex(results.index)[m.ASSETS]
        corr = asset_returns.corr()
        fig, ax = plt.subplots(figsize=(7, 3.5))
        im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr)), corr.columns)
        ax.set_yticks(range(len(corr)), corr.index)
        for i in range(len(corr)):
            for j in range(len(corr)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center",
                        color="white" if abs(corr.iloc[i, j]) > .6 else "#222")
        ax.spines[:].set_visible(False)
        fig.colorbar(im, ax=ax, fraction=.035, pad=.04)
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)
        st.caption("Computed from adjusted monthly ETF returns over the portfolio backtest sample. "
                   "Historical correlations can change, especially during crises; diversification does not guarantee protection.")
    with st.container(key="panel_rolling_risk"):
        st.subheader("Risk changes through time")
        st.write("Trailing 12-month volatility shows how much monthly portfolio returns fluctuated "
                 "in the preceding year. Compare the strategy with the benchmark through calm and stressed markets.")
        rolling = results.rolling(12, min_periods=12).std().dropna() * np.sqrt(12)
        line_chart(rolling, "Annualised 12-month volatility", percent=True)
        st.caption("Sample standard deviation of the last 12 monthly net returns × √12. "
                   "The first point needs a full year of observations. This is realised volatility, not a forecast or a loss limit.")
    with st.container(key="panel_exposure"):
        st.subheader("How much of the satellite stayed invested?")
        st.write("When satellite trends turn off, their budget moves to cash. The chart separates "
                 "the invested satellite from the cash proxy; the fixed AGG core is excluded.")
        positions = holdings(detail)
        exposure = pd.DataFrame({"Invested satellite": positions[m.SATELLITE].sum(axis=1),
                                 "Cash proxy": positions[m.TBILL]})
        line_chart(exposure, "Share of total portfolio", percent=True, colors=[ACCENT, "#707078"])
        st.caption(f"Both lines together equal the {1 - params['core']:.0%} satellite budget. "
                   "These are monthly target weights used for returns, rather than intramonth holdings.")
    with st.expander("Model facts and limitations", expanded=False):
        st.write(f"**Data:** Yahoo Finance adjusted ETF closes, sampled at month-end. "
                 f"**Signal:** {params['ma']}-month SMA. **Volatility window:** {m.VOL_MONTHS} months. "
                 f"**Trading costs:** {params['cost']} bps × buys plus sells, including initial investment.")
        st.write("Cash returns approximate the preceding ^IRX quoted annual yield divided by 100 and 12. "
                 "Signals are lagged by one return month; execution at the signal close is optimistic. "
                 "Taxes, management fees, inflation and additional market impact are excluded. "
                 "Asset selection uses hindsight, and this historical sample is not an out-of-sample validation.")


# --- historical crisis analysis ----------------------------------------------
def crisis_page(m, params):
    heading("Crisis analysis", "When markets fall,", "look closer.")
    scenario_note(m, params)
    html('''<p class="lead">Three historical stress periods. The same portfolio rules.
      Explore losses, diversification and the path back to the starting value.</p>''')
    data = backtest(m, params)
    if data is None:
        return
    _, _, results, _, _ = data
    name = st.selectbox("Historical crisis", list(CRISES), key="selected_crisis")
    start, end = CRISES[name]
    descriptions = {
        "Financial crisis": "A prolonged equity-market decline. The window follows SPY's October 2007 month-end peak to its February 2009 month-end low.",
        "Covid crash": "A rapid sell-off followed by a fast rebound. The window follows SPY's December 2019 month-end peak to March 2020.",
        "Inflation shock": "A difficult period for both stocks and bonds. The window follows SPY's December 2021 month-end peak to September 2022.",
    }
    st.write(descriptions[name])
    summary = crisis_summary(m, results, start, end)
    if summary.empty:
        st.info("The complete crisis window is not available in this backtest sample.")
        return
    window = results.loc[start:end]
    st.caption(f"Return months: {window.index[0]:%b %Y}–{window.index[-1]:%b %Y}. "
               "Each path starts at 1 at the preceding month-end. All returns are net of model trading costs.")
    left, right = st.columns(2)
    for col, portfolio in zip((left, right), results.columns):
        row = summary.loc[portfolio]
        with col, st.container(key=f"panel_crisis_{portfolio.split()[0]}"):
            st.subheader(portfolio)
            st.metric("Return during crisis", f"{row['Crisis return']:+.2%}")
            st.metric("Maximum drawdown in window", f"{row['Max drawdown']:.2%}")
            if row["Months to recover"] == 0:
                recovery_text = "No recovery needed"
            elif pd.isna(row["Months to recover"]):
                recovery_text = "Not recovered"
            else:
                recovery_text = f"{int(row['Months to recover'])} months"
            st.metric("From crisis low to starting value", recovery_text)
            if pd.notna(row["Recovery date"]) and row["Months to recover"] != 0:
                st.caption(f"Crisis low: {row['Crisis low']:%b %Y} · recovery: {row['Recovery date']:%b %Y}")
            elif pd.isna(row["Months to recover"]):
                st.caption(f"Below the pre-crisis starting value through {results.index[-1]:%b %Y}.")
    with st.container(key="panel_crisis_path"):
        st.subheader("Inside the crisis")
        line_chart(m.cumulative(window), "Value of USD 1")
        st.caption("A value of 0.80 means USD 1 became USD 0.80. Maximum drawdown measures the "
                   "largest peak-to-trough loss within this window, including the initial value of 1.")
    with st.container(key="panel_recovery_path"):
        st.subheader("The path back")
        # Retain the original start and holdings; do not restart a backtest at the crisis.
        recovery_dates = summary["Recovery date"]
        last_date = (results.index[-1] if recovery_dates.isna().any()
                     else max(window.index[-1], recovery_dates.max()))
        path = m.cumulative(results.loc[start:last_date])
        fig, ax = plt.subplots(figsize=(11, 3.8))
        path.plot(ax=ax, color=[SERIES[c] for c in path.columns], linewidth=1.8)
        ax.axhline(1, color="#9A9A96", linestyle="--", linewidth=.9, label="Pre-crisis starting value")
        ax.axvspan(path.index[0], window.index[-1], color=ACCENT, alpha=.07)
        ax.set_xlabel("")
        ax.set_ylabel("Value of USD 1")
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1), ncol=2)
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)
        st.caption("Shading marks the crisis window. Recovery counts calendar months from each portfolio's "
                   "lowest value inside that window until it first regains its pre-crisis starting value. "
                   "It is not recovery to a later portfolio peak. The search uses all subsequent available returns.")
    st.subheader("Across all three crises")
    comparisons = []
    for crisis, (first, last) in CRISES.items():
        report = crisis_summary(m, results, first, last)
        if not report.empty:
            report = report.reset_index()
            report.insert(0, "Crisis", crisis)
            comparisons.append(report)
    combined = pd.concat(comparisons, ignore_index=True)
    shown = combined[["Crisis", "Portfolio", "Crisis return", "Max drawdown", "Months to recover"]].copy()
    shown["Months to recover"] = shown["Months to recover"].map(
        lambda v: "Not recovered" if pd.isna(v) else ("Not needed" if v == 0 else f"{int(v)}"))
    st.dataframe(shown.style.format({"Crisis return": "{:+.2%}", "Max drawdown": "{:.2%}"}),
                 hide_index=True, width="stretch")
    st.download_button("Download crisis analysis", combined.to_csv(index=False).encode("utf-8"),
                       "historical_crisis_analysis.csv", "text/csv")
    st.caption("Historical windows follow the project's crisis notebook and are defined using SPY month-end peaks "
               "and lows. Monthly observations hide intramonth losses. These selected episodes do not represent "
               "every possible stress scenario or establish future protection.")


# --- Monte Carlo (shared calculations in the master notebook) -----------------
@st.cache_data(show_spinner=False, max_entries=6)
def simulation_data(_model, results, initial, years):
    return _model.monte_carlo(results, initial=initial, years=years)


def simulation_chart(simulation, selected):
    """Pointwise wealth percentiles, with the other portfolio's median for context."""
    band = simulation["bands"][selected]
    other = next(name for name in simulation["bands"] if name != selected)
    color = SERIES.get(selected, ACCENT)
    x = band.index.to_numpy() / 12
    with plt.rc_context({"font.size": 12, "axes.labelcolor": "#55555E",
                         "xtick.color": "#55555E", "ytick.color": "#55555E"}):
        fig, ax = plt.subplots(figsize=(11, 4.8))
        ax.fill_between(x, band["5th"], band["95th"], color=color, alpha=.10,
                        linewidth=0, label="5th–95th percentile")
        ax.fill_between(x, band["25th"], band["75th"], color=color, alpha=.20,
                        linewidth=0, label="25th–75th percentile")
        ax.plot(x, band["Median"], color=color, linewidth=2.5, label=f"{selected} median")
        ax.plot(x, simulation["bands"][other]["Median"], color=SERIES.get(other, "#656575"),
                linewidth=1.6, linestyle="--", label=f"{other} median")
        ax.axhline(simulation["initial"], color="#77777F", linewidth=1, linestyle=":",
                   label="Initial capital")
        ax.set(xlabel="Years from investment", ylabel="Portfolio value · USD",
               xlim=(0, simulation["years"]))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"${value:,.0f}"))
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
        ax.grid(axis="y", color="#ECECE9", linewidth=.7)
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#DDDDE0")
        ax.tick_params(axis="both", length=0, pad=9)
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.03), ncol=2,
                  frameon=False, fontsize=10)
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)


def monte_carlo_page(m, params):
    heading("Monte Carlo · Lecture 5", "One investment.", "Many possible paths.")
    scenario_note(m, params)
    html('<p class="lead">What might your capital be worth in the future? Explore 10,000 '
         'simulated outcomes for our strategy and the 40/60 benchmark, using the method from Lecture 5.</p>')
    data = backtest(m, params)
    if data is None:
        return
    results = data[2]
    with st.container(key="panel_mc_controls"):
        left, right = st.columns(2, gap="large")
        with left:
            capital = investment_input("mc_capital")
        years = right.slider("Investment horizon (years)", 1, 30, 10, key="mc_years",
                             help="One initial investment, with no further deposits or withdrawals.")
        st.caption("10,000 paths · monthly compounding · fixed seed 2270 · nominal USD · no deposits or withdrawals")
    try:
        with st.spinner("Simulating possible wealth paths…"):
            simulation = simulation_data(m, results, capital, years)
    except (ValueError, OverflowError) as exc:
        st.error(f"Simulation check failed: {exc}")
        return

    summary = simulation["summary"]
    strategy = summary.loc["Strategy"]
    html(f'<div class="mc-context"><span class="mc-pill">Modelled scenarios</span>'
         f'<p>Starting with <strong>${capital:,.0f}</strong> for <strong>{years} '
         f'{"year" if years == 1 else "years"}</strong>. Parameters are estimated from '
         f'<strong>{len(results)} monthly returns</strong>, {results.index[0]:%b %Y}–{results.index[-1]:%b %Y}, '
         'after backtest transaction costs.</p></div>')
    c1, c2, c3 = st.columns(3)
    c1.metric("Median end wealth", f"${strategy['Median end wealth']:,.0f}",
              help="Half of simulated final values fall below the median and half above it.")
    c2.metric("5th percentile", f"${strategy['5th percentile']:,.0f}",
              help="About 5% of simulated final values fall below this amount. It is not a worst case.")
    c3.metric("End-loss frequency", f"{strategy['Probability of loss']:.2%}",
              help="Fraction of paths whose final nominal wealth is below the initial investment. "
                   "Temporary losses during the investment are not counted by this measure.")
    loss_paths = int(round(strategy["Probability of loss"] * simulation["n_sim"]))
    st.caption(f"Strategy outcomes · {loss_paths:,} of {simulation['n_sim']:,} paths ended below "
               "initial capital. Zero simulated losses would not mean that future losses are impossible.")

    with st.container(key="panel_mc_paths"):
        st.subheader("The range of possible outcomes")
        selected = st.radio("Show outcome bands for", list(results.columns), horizontal=True,
                            key="mc_portfolio")
        simulation_chart(simulation, selected)
        band = simulation["bands"][selected]
        st.write(f"**Reading the chart:** after {years} {'year' if years == 1 else 'years'}, "
                 f"the middle 90% of simulated **{selected}** outcomes lie between "
                 f"**${band['5th'].iloc[-1]:,.0f}** and **${band['95th'].iloc[-1]:,.0f}**. "
                 "The darker area contains the middle 50%; the solid line is the median.")
        st.caption("The bands are percentiles at each month, not a guarantee that an entire path stays inside them. "
                   "The dashed line shows the other portfolio's median; the dotted line marks your starting capital.")

    with st.container(key="panel_mc_comparison"):
        st.subheader("Same capital. Same horizon.")
        st.write("Compare the full end-wealth distributions, rather than relying on one average.")
        formats = {column: "${:,.0f}" for column in summary.columns if column != "Probability of loss"}
        formats["Probability of loss"] = "{:.2%}"
        labels = {"Median end wealth": "Median", "Mean end wealth": "Mean",
                  "Probability of loss": "Loss frequency"}
        view = summary.rename(columns=labels)
        formats = {labels.get(column, column): fmt for column, fmt in formats.items()}
        st.dataframe(view.style.format(formats), width="stretch")
        st.caption("Mean end wealth can exceed the median because a small number of strong outcomes pull it up. "
                   "The 5th percentile is a downside scenario, not the maximum possible loss. "
                   "Loss means ending below initial capital in nominal USD; inflation is excluded.")

    st.subheader("How we get from history to scenarios")
    cards([
        ("Estimate", "Start with our backtest", "Measure each portfolio's average monthly net return and "
         "monthly volatility over the same historical sample."),
        ("Simulate", "Draw 10,000 possible futures", "Draw normal monthly returns with those fixed parameters. "
         "Compound your capital month by month, following Lecture 5."),
        ("Interpret", "Count outcomes, show the spread", "Sort final values to find the percentiles. "
         "Count how many finish below your initial investment to estimate the chance of loss."),
    ])
    with st.expander("See the inputs, formulas and course connection"):
        st.write(f"**Calibration:** {results.index[0]:%b %Y}–{results.index[-1]:%b %Y}, "
                 f"{len(results)} common monthly observations. Manager changes in the sidebar "
                 "rerun the backtest and update these inputs.")
        st.dataframe(simulation["calibration"].style.format("{:.2%}"), width="stretch")
        st.caption("Annualised mean = monthly arithmetic mean × 12; annualised volatility = monthly "
                   "volatility × √12. The mean is not CAGR. Simulation uses monthly inputs directly.")
        st.latex(r"r_{t,p} = \mu_{m,p} + \sigma_{m,p} z_{t,p},\qquad "
                 r"W_{t,p} = W_{t-1,p}(1+r_{t,p})")
        st.write("μ is the historical arithmetic monthly mean; σ is the sample monthly standard deviation "
                 "(ddof = 1); z is a standard normal random shock. Months are independent.")
        st.write(f"**Shared market shocks:** historical strategy–benchmark return correlation is "
                 f"**{simulation['correlation']:.3f}**. For each month we draw independent standard normals "
                 "z₁ and z₂. Strategy uses z₁; benchmark uses ρz₁ + √(1 − ρ²)z₂. "
                 "This preserves their historical same-month correlation in the model. "
                 "It does not model future ETF holdings.")
        st.code('mu = monthly_net_returns.mean()\n'
                'sigma = monthly_net_returns.std(ddof=1)\n'
                '# For each simulated month and each portfolio:\n'
                'monthly_return = mu + sigma * correlated_normal_shock\n'
                'wealth = wealth * (1 + monthly_return)\n'
                '# After the final month:\n'
                'probability_of_loss = (final_wealth < initial_capital).mean()', language="python")
        st.write("**Course connection:** Lecture 5 §5.3, retirement wealth paths and percentile bands; "
                 "§5.5, monthly mean and volatility scaling. We replace regular contributions with one "
                 "initial investment and estimate parameters from our portfolios. The paired shocks are "
                 "an extension of the lecture's single-portfolio example.")
        st.caption("Seed 2270 makes the random draws reproducible. Identical inputs give identical results. "
                   "Costs are already reflected in historical net returns and are not subtracted again.")
    html('<div class="mc-note"><strong>What this model can tell you</strong>'
         '<p>These are scenarios under fixed historical assumptions, not forecasts. We simulate portfolio '
         'returns; we do not rerun the trend filter, future ETF weights or trades. Normal returns can '
         'understate extreme losses; independent months miss volatility clustering and changing regimes. '
         'Historical estimates are uncertain. Inflation, taxes and additional management fees are excluded. '
         'More simulated paths reduce sampling noise, not these modelling limits.</p></div>')

    report = summary.join(simulation["calibration"])
    report["Initial capital USD"] = capital
    report["Horizon years"] = years
    report["Paths"] = simulation["n_sim"]
    report["Seed"] = simulation["seed"]
    report["Historical correlation"] = simulation["correlation"]
    report["Sample start"] = results.index[0].date().isoformat()
    report["Sample end"] = results.index[-1].date().isoformat()
    report["Return model"] = "Normal monthly net returns; independent months; fixed parameters"
    report["Observations"] = len(results)
    bands = pd.concat(simulation["bands"], names=["Portfolio", "Month"])
    left, right = st.columns(2)
    left.download_button("Download results and assumptions", report.to_csv().encode("utf-8"),
                         file_name="monte_carlo_summary.csv", mime="text/csv")
    right.download_button("Download monthly outcome bands", bands.to_csv().encode("utf-8"),
                          file_name="monte_carlo_bands.csv", mime="text/csv")


# --- trade history (logic in activity.py) ---------------------------------------
def activity_table(data, columns, formats=None):
    """Readable labels for display; values stay numeric for export."""
    view = data[list(columns)].rename(columns=columns)
    formatting = {columns[k]: v for k, v in (formats or {}).items() if k in columns}
    st.dataframe(view.style.format(formatting, na_rep="—"), hide_index=True, width="stretch")


def trade_page(m, params):
    heading("Trade history", "Every rebalance,", "month by month.")
    ma_months, core_weight, cost_bps = params["ma"], params["core"], params["cost"]
    st.caption(f"Model trades, not broker orders · {core_weight:.0%} AGG core · {ma_months}-month trend · "
               f"{cost_bps} bps costs · signal at month-end, return in the following month.")
    data = backtest(m, params)
    if data is None:
        return
    prices, _, _, _, detail = data

    left, right = st.columns([1, 2])
    with left:
        capital = investment_input("history_capital")
    months, decisions = rebalance_history(m, prices, detail, ma_months, capital)
    first, last = months.signal_date.iloc[0].date(), months.signal_date.iloc[-1].date()
    dates = right.date_input("Signal dates", value=(first, last), min_value=first,
                             max_value=last, key="history_dates")
    if len(dates) != 2:
        st.info("Choose both a start and an end date.")
        return
    start, end = map(pd.Timestamp, dates)
    selected = months.loc[months.signal_date.between(start, end)]
    records = decisions.loc[decisions.signal_date.between(start, end)]
    if selected.empty:
        st.info("No monthly signal dates fall in this range.")
        return
    trades = records.loc[records.action != "Hold"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rebalances", str(int((selected.event == "Rebalance").sum())))
    c2.metric("Asset trades", f"{len(trades):,}")
    c3.metric("Traded notional · USD", f"${selected.traded_usd.sum():,.2f}")
    c4.metric("Model costs · USD", f"${selected.cost_usd.sum():,.2f}")

    st.subheader("Monthly rebalance log")
    date_formats = {"signal_date": "{:%d %b %Y}", "return_month": "{:%b %Y}"}
    money_formats = {c: "${:,.2f}" for c in ("traded_usd", "cost_usd", "opening_value", "closing_value", "trade_usd")}
    activity_table(selected.sort_values("signal_date", ascending=False), {
        "signal_date": "Signal date", "return_month": "Return month", "event": "Activity",
        "assets_traded": "Assets traded", "turnover": "Turnover", "traded_usd": "Traded · USD",
        "cost_usd": "Costs · USD", "net_return": "Month net return", "closing_value": "Month-end value · USD",
    }, date_formats | money_formats | {"turnover": "{:.2%}", "net_return": "{:+.2%}"})

    st.subheader("Inside a rebalance")
    options = selected.signal_date.sort_values(ascending=False).tolist()
    if st.session_state.get("history_month") not in options:
        st.session_state.history_month = options[0]
    chosen = st.selectbox("Signal date", options,
                          format_func=lambda d: f"{d:%d %b %Y} → {(d + pd.offsets.MonthEnd(1)):%b %Y} return",
                          key="history_month")
    event = selected.loc[selected.signal_date == chosen].iloc[0]
    allocation = records.loc[records.signal_date == chosen].copy()
    with st.container(key="panel_rebalance"):
        st.write(f"**{event.event}** · bought {event.buys:.2%}, sold {event.sells:.2%} of the portfolio · "
                 f"cost ${event.cost_usd:,.2f} · {event.return_month:%B %Y} return {event.net_return:+.2%} after costs.")
        activity_table(allocation, {
            "asset": "Asset", "action": "Action", "previous_target": "Previous target",
            "pretrade_weight": "Before trade · drifted", "target_weight": "After trade · target",
            "trade_pp": "Trade · pp", "trade_usd": "Signed trade · USD", "cost_usd": "Cost · USD",
        }, money_formats | {c: "{:.2%}" for c in ("previous_target", "pretrade_weight", "target_weight")}
           | {"trade_pp": "{:+.3f}"})
        activity_table(allocation, {"asset": "Asset", "status": "Rule status", "reason": "Why"})
    with st.expander("Signal inputs"):
        satellites = allocation.loc[allocation.asset.isin(m.SATELLITE)]
        activity_table(satellites, {
            "asset": "Asset", "adjusted_close": "Adjusted close · USD",
            "moving_average": f"{ma_months}-month SMA · USD", "annual_volatility": "12-month volatility",
            "satellite_budget": "Share before trend filter", "status": "Trend status",
        }, {"adjusted_close": "{:,.2f}", "moving_average": "{:,.2f}",
            "annual_volatility": "{:.2%}", "satellite_budget": "{:.2%}"})
        activity_table(allocation, {
            "asset": "Asset", "target_change_pp": "Target change · pp",
            "drift_correction_pp": "Drift correction · pp", "trade_pp": "Total trade · pp",
        }, {c: "{:+.3f}" for c in ("target_change_pp", "drift_correction_pp", "trade_pp")})
        st.caption("Trade = target change + drift correction, in percentage points of portfolio value.")

    st.subheader("Trade ledger")
    left, right = st.columns(2)
    assets = left.multiselect("Assets", allocation.asset.tolist(), default=allocation.asset.tolist(),
                              key="history_assets")
    actions = right.multiselect("Actions", ["Buy", "Sell", "Hold"], default=["Buy", "Sell"],
                                key="history_actions")
    ledger = records.loc[records.asset.isin(assets) & records.action.isin(actions)].sort_values(
        ["signal_date", "asset"], ascending=[False, True])
    if ledger.empty:
        st.info("No records match these filters.")
    else:
        activity_table(ledger, {
            "signal_date": "Signal date", "return_month": "Return month", "asset": "Asset", "action": "Action",
            "pretrade_weight": "Before trade", "target_weight": "Target", "trade_pp": "Trade · pp",
            "trade_usd": "Signed trade · USD", "cost_usd": "Cost · USD", "reason": "Reason",
        }, date_formats | money_formats | {"pretrade_weight": "{:.2%}", "target_weight": "{:.2%}", "trade_pp": "{:+.3f}"})
    left, right = st.columns(2)
    left.download_button("Download trade ledger", ledger.to_csv(index=False).encode("utf-8"),
                         file_name="rebalance_decisions.csv", mime="text/csv", key="download_history_trades")
    right.download_button("Download monthly log", selected.to_csv(index=False).encode("utf-8"),
                          file_name="monthly_rebalances.csv", mime="text/csv", key="download_history_months")
    st.caption("USD amounts are illustrative notionals, not ETF share counts. TBILL is a cash-return proxy, "
               "not a traded security.")


# --- team -----------------------------------------------------------------------
def team_page():
    heading("Team", "Six people,", "one portfolio.")
    body = []
    for i, person in enumerate(TEAM):
        sid = (f'<p style="margin-top:.4rem">Student ID {escape(str(person["student_id"]))}</p>'
               if person["student_id"] else "")
        if person["photo"]:
            path = ROOT / person["photo"]
            src = f"data:image/{path.suffix.lstrip('.')};base64,{base64.b64encode(path.read_bytes()).decode()}"
            photo = f'<img src="{src}" class="avatar" style="object-fit:cover">'
        else:
            photo = f'<div class="avatar {"alt" if i % 2 else ""}">{escape(person["initials"])}</div>'
        body.append(f'<div class="card">{photo}<h4 style="margin-top:1rem">{escape(person["name"])}</h4>'
                    f'<div class="mono">Project team</div>{sid}</div>')
    html(f'<div class="grid" style="--cols:3">{"".join(body)}</div>')


def render_app(model):
    st.set_page_config(page_title="T Capital", page_icon="◈", layout="wide",
                       initial_sidebar_state="expanded")
    styles()
    role = st.session_state.get("portal_role")
    if role not in ("Investor", "Investment Manager"):
        landing()
        return
    page, params = shell(model, role)
    if page == "Overview":
        overview(model, params)
    elif page == "Investment Approach":
        approach_page(model, params)
    elif page == "Performance":
        performance(model, params)
    elif page == "Fund Insights":
        insights_page(model, params)
    elif page == "Crisis Analysis":
        crisis_page(model, params)
    elif page == "Monte Carlo":
        monte_carlo_page(model, params)
    elif page == "Trade History":
        trade_page(model, params)
    else:
        team_page()
    footer()
