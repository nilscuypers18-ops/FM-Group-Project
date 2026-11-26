"""Presentation layer for the T Capital portal (Streamlit).

Calculations come from app.py. Edit TEAM below to add photos or student IDs.
The two logins are one-click demo roles, not authentication.
"""
import base64
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter
import streamlit as st


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
    raw = _model.download_raw(_model.DOWNLOAD_START, _model.BACKTEST_END)
    prices, rf, audit = _model.prepare_data(raw, _model.DOWNLOAD_START, _model.BACKTEST_END)
    return raw, prices, rf, audit


def backtest(m, params):
    """Returns (raw, prices, rf, audit, results, rf_bt, res_strat) or None after showing the error."""
    try:
        with st.spinner("Loading market data…"):
            raw, prices, rf, audit = load_data(m)
            results, rf_bt, _, res_strat = m.run_all(prices, rf, params["core"], params["ma"],
                                                     params["cost"])
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Data or calculation check failed: {exc}")
        if st.button("Retry"):
            load_data.clear()
            st.rerun()
        return None
    return raw, prices, rf, audit, results, rf_bt, res_strat


def holdings(res_strat):
    return res_strat.filter(like="weight_").rename(columns=lambda c: c.removeprefix("weight_"))


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


# --- pages --------------------------------------------------------------------
def overview(m, params):
    heading("Portfolio overview", "Your portfolio,", "at a glance.")
    data = backtest(m, params)
    if data is None:
        return
    _, _, _, _, results, rf_bt, res_strat = data
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

    positions = holdings(res_strat)
    latest = positions.iloc[-1]
    left, right = st.columns([1.1, 1], gap="medium")
    with left, st.container(key="panel_holdings"):
        html(f'<div class="mono">Holdings · {positions.index[-1]:%B %Y}</div>{allocation_rows(latest)}')
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


def performance(m, params, role):
    heading("Performance", "The evidence,", "net of costs.")
    data = backtest(m, params)
    if data is None:
        return
    raw, prices, _, audit, results, rf_bt, res_strat = data
    table = m.performance_table(results, rf_bt)
    pct = ["Ann. return", "CAGR", "Volatility", "Alpha (ann.)", "Tracking error", "Max drawdown"]
    shown = table.T.astype(object)
    for row in shown.index:
        fmt = "{:.2%}" if row in pct else "{:.2f}"
        shown.loc[row] = ["–" if pd.isna(v) else fmt.format(v) for v in table[row]]
    with st.container(key="panel_measures"):
        html('<div class="mono">Performance measures · Mar 2007 – Oct 2026</div>')
        st.dataframe(shown.rename_axis("Measure"), width="stretch")
        st.caption("Volatility = √12 × std. Sharpe uses excess returns over T-bills. Alpha and beta vs "
                   "60/40 on excess returns; beta not annualised. Drawdown shown as a positive loss.")
    with st.container(key="panel_drawdown"):
        html('<div class="mono">Loss from previous high</div>')
        line_chart(m.drawdowns(results), "Loss from peak", percent=True, invert=True)
    with st.container(key="panel_allocation"):
        html('<div class="mono">Allocation history</div>')
        positions = holdings(res_strat)
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
        gross_net = res_strat[["gross", "net"]].rename(columns={"gross": "Strategy gross",
                                                                 "net": "Strategy"})
        line_chart(m.cumulative(gross_net), "Value of USD 1", colors=["#A1A1AA", ACCENT])
        st.caption(f"Average monthly turnover after the first purchase: "
                   f"{res_strat['turnover'].iloc[1:].mean():.2%}.")

    if role == "Investment Manager":
        with st.expander("Rolling 60-month measures"):
            for metric, values in m.rolling_performance(results, rf_bt).items():
                st.markdown(f"**{metric}**")
                line_chart(values, metric, metric == "Alpha (ann.)")
        with st.expander("Data and method"):
            st.write(f"Daily rows: {raw.shape[0]} · monthly prices: {len(prices)} · "
                     f"backtest months: {len(results)}")
            st.dataframe(m.data_summary(raw), width="stretch")
            st.dataframe(audit.tail(), width="stretch")
            st.caption("Yahoo Finance adjusted closes, converted to month-end. Cash = previous ^IRX "
                       "yield / 100 / 12 (approximation). Signal-close execution is optimistic. Taxes "
                       "and market impact are not modelled.")
    st.download_button("Download monthly returns", results.to_csv().encode("utf-8"),
                       file_name="monthly_net_returns.csv", mime="text/csv")


def trade_log(res_strat):
    """Model trades: first purchase, then every month a satellite asset's trend switches."""
    positions = holdings(res_strat)
    rows = []
    first = positions.index[0]
    for asset in positions.columns:
        if positions.loc[first, asset] > 0:
            rows.append((first, asset, "Buy", "Initial investment", 100 * positions.loc[first, asset]))
    for asset in ["SPY", "GLD", "DBC"]:
        held = positions[asset] > 0
        switched = held != held.shift(1)
        for month in positions.index[switched][1:]:
            if held[month]:
                rows.append((month, asset, "Buy", "Trend turned up", 100 * positions.loc[month, asset]))
            else:
                rows.append((month, asset, "Sell", "Trend turned down → T-bills", 0.0))
    log = pd.DataFrame(rows, columns=["Month", "Asset", "Action", "Reason", "Weight after"])
    return log.sort_values("Month", ascending=False, kind="stable").reset_index(drop=True)


def trade_page(m, params):
    heading("Trade history", "Every switch,", "month by month.")
    data = backtest(m, params)
    if data is None:
        return
    res_strat = data[-1]
    log = trade_log(res_strat)
    switches = log[log["Reason"] != "Initial investment"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Trend switches", f"{len(switches)}")
    c2.metric("Per year", f"{len(switches) / (len(res_strat) / 12):.1f}")
    c3.metric("Avg. monthly turnover", f"{res_strat['turnover'].iloc[1:].mean():.1%}")
    with st.container(key="panel_trades"):
        assets = st.pills("Asset", ["SPY", "GLD", "DBC"], selection_mode="multi",
                          default=["SPY", "GLD", "DBC"], key="trade_assets")
        shown = log[log["Asset"].isin(list(assets or []) + ["AGG", "TBILL"])]
        st.dataframe(shown, hide_index=True, width="stretch", height=420, column_config={
            "Month": st.column_config.DateColumn(format="MMM YYYY"),
            "Weight after": st.column_config.NumberColumn(format="%.1f%%"),
        })
        st.caption("Model trades, placed at the previous month-end close. Small monthly rebalancing "
                   "trades back to target weights are not listed; they are included in turnover and costs.")


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
        performance(model, params, role)
    elif page == "Trade History":
        trade_page(model, params)
    else:
        team_page()
    footer()
