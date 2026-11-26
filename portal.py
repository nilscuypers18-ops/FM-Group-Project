"""Presentation layer for the T Capital portal (Streamlit).

Calculations come from app.py (strategy cells of the notebook); trade history
logic lives in activity.py. Edit TEAM below to add photos or student IDs.
The two logins are one-click demo roles, not authentication.
"""
import base64
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter
import streamlit as st

from activity import rebalance_history


TEAM = [
    {"name": "Nils Andreas Cuypers", "initials": "NC", "photo": None, "student_id": None},
    {"name": "Michelle De Kock", "initials": "MD", "photo": None, "student_id": None},
    {"name": "Hanna Kiss", "initials": "HK", "photo": None, "student_id": None},
    {"name": "Felix Michele Mellino", "initials": "FM", "photo": None, "student_id": None},
    {"name": "Niklas Peter", "initials": "NP", "photo": None, "student_id": None},
    {"name": "Leif Plotzky", "initials": "LP", "photo": None, "student_id": None},
]
ROOT = Path(__file__).resolve().parent
ACCENT = "#F26B3A"
SERIES = {"Strategy": ACCENT, "60/40 SPY/AGG": "#0A0A0A", "Buy & hold (same assets)": "#A1A1AA"}
ASSETS = {  # ticker -> name, role, colour
    "AGG": ("US Aggregate Bonds", "Core", "#3F3F46"),
    "SPY": ("S&P 500", "Satellite", ACCENT),
    "GLD": ("Gold", "Satellite", "#D9A93A"),
    "DBC": ("Commodities", "Satellite", "#8C9BF5"),
    "TBILL": ("3M US T-Bills", "Cash", "#CFCFCB"),
}
PAGES = ["Overview", "Performance", "Trade History", "Team Overview"]
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
    _, _, results, rf_bt, detail = data
    table = m.performance_table(results, rf_bt)
    s, b = table.loc["Strategy"], table.loc[m.BENCHMARK]
    c1, c2, c3 = st.columns(3)
    c1.metric("Annualised return", f"{s['Ann. return']:.2%}",
              f"{(s['Ann. return'] - b['Ann. return']) * 100:+.2f} pp vs 60/40")
    c2.metric("Sharpe ratio", f"{s['Sharpe']:.2f}", f"{s['Sharpe'] - b['Sharpe']:+.2f} vs 60/40")
    c3.metric("Maximum drawdown", f"{s['Max drawdown']:.2%}",
              f"{(s['Max drawdown'] - b['Max drawdown']) * 100:+.2f} pp vs 60/40", delta_color="inverse")

    with st.container(key="panel_growth"):
        html(f'<div class="mono">Growth of USD 1 · {results.index[0]:%b %Y} – {results.index[-1]:%b %Y}'
             ' · net of costs</div>')
        line_chart(m.cumulative(results), "Value of USD 1")

    positions = holdings(detail)
    left, right = st.columns([1.1, 1], gap="medium")
    with left, st.container(key="panel_holdings"):
        html(f'<div class="mono">Holdings · {positions.index[-1]:%B %Y}</div>'
             f'{allocation_rows(positions.iloc[-1])}')
    with right:
        cards([("01", f"{params['core']:.0%} bond core", "AGG, held at a fixed weight."),
               ("02", f"{params['ma']}-month trend filter",
                "SPY, GLD and DBC are held only above their moving average. Otherwise: T-bills."),
               ("03", "Risk-balanced satellite",
                "Calmer assets get a larger share (inverse 12-month volatility).")], cols=1)


def allocation_rows(latest):
    rows = []
    for i, (ticker, (name, role, colour)) in enumerate(ASSETS.items()):
        w = float(latest.get(ticker, 0.0))
        if role == "Satellite":
            tag = '<span class="tag on">Trend on</span>' if w > 0 else '<span class="tag off">Trend off</span>'
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
                   "60/40 on excess returns; beta not annualised. Drawdown shown as a positive loss.")
    with st.container(key="panel_drawdown"):
        html('<div class="mono">Loss from previous high</div>')
        line_chart(m.drawdowns(results), "Loss from peak", percent=True, invert=True)
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
    capital = left.number_input("Initial investment (USD)", min_value=1_000.0,
                                max_value=1_000_000_000_000.0, value=100_000.0,
                                step=10_000.0, key="history_capital")
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
        sid = f'<p>Student ID {escape(str(person["student_id"]))}</p>' if person["student_id"] else ""
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
    elif page == "Performance":
        performance(model, params)
    elif page == "Trade History":
        trade_page(model, params)
    else:
        team_page()
    footer()
