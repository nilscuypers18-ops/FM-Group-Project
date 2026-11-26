"""Presentation layer for the credential-free T Capital project portal.

Team content lives in TEAM; add a local photo path and student ID when ready.
Roles are session-only navigation choices, not authentication or authorization.
"""
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
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
PALETTE = ["#147b79", "#a9764d", "#8b9fa9", "#b4c8c5", "#ded9cc"]


def html(value):
    st.html(value)


def set_role(role):
    st.session_state.portal_role = role
    st.session_state.portal_page = "Overview"


def styles():
    html(f"<style>{(ROOT / 'assets' / 'portal.css').read_text(encoding='utf-8')}</style>")


def brand():
    html('<div class="brand"><span class="brand-mark">T</span><span>T CAPITAL'
         '<small>INVESTMENT MANAGEMENT</small></span></div>')


def footer():
    html('<footer><span>T CAPITAL <b>·</b> A long-term perspective.</span>'
         '<span>2270 Financial Modeling · Academic project</span></footer>')


def landing():
    left, right = st.columns([3, 1], vertical_alignment="center")
    with left:
        brand()
    with right:
        html('<div class="top-note">A considered approach to capital.</div>')
    html('''<section class="hero">
      <div class="hero-copy"><div class="eyebrow">DISCIPLINE. PERSPECTIVE. PURPOSE.</div>
      <h1>A clear perspective.<br><span>A longer horizon.</span></h1>
      <p>A systematic approach to preserving and growing wealth.
      Built on a diversified core, guided by a disciplined investment process.</p>
      <div class="hero-note">Core–satellite investing <span>Monthly perspective</span></div></div>
      <div class="hero-art" aria-hidden="true"><div class="orbit orbit-one"></div>
      <div class="orbit orbit-two"></div><div class="art-block block-one"></div>
      <div class="art-block block-two"></div><div class="art-block block-three"></div>
      <div class="art-line"></div><span class="art-caption">STRUCTURE MEETS PERSPECTIVE</span></div>
    </section>''')
    html('<div class="section-intro"><div class="eyebrow">YOUR PORTAL</div>'
         '<h2>Choose your perspective.</h2><p>One strategy. Two ways to explore it.</p></div>')
    investor, manager = st.columns(2, gap="large")
    with investor, st.container(border=True):
        html('<div class="access-icon">◈</div><h3>For investors</h3>'
             '<p class="muted">Explore portfolio performance, understand our approach '
             'and meet the team behind the strategy.</p>'
             '<div class="access-detail">Performance &nbsp; / &nbsp; Portfolio &nbsp; / &nbsp; Team</div>')
        st.button("Investor login", key="enter_investor", type="primary", width="stretch",
                  on_click=set_role, args=("Investor",))
    with manager, st.container(border=True):
        html('<div class="access-icon">▥</div><h3>For investment managers</h3>'
             '<p class="muted">Review the strategy, explore allocation assumptions '
             'and examine the portfolio’s risk and return.</p>'
             '<div class="access-detail">Analysis &nbsp; / &nbsp; Parameters &nbsp; / &nbsp; Team</div>')
        st.button("Investment Manager login", key="enter_manager", width="stretch",
                  on_click=set_role, args=("Investment Manager",))
    html('<p class="demo-note">Demo access · Click to enter. No account, password or login details required.</p>')
    with st.expander("Our investment approach"):
        st.write("A bond ETF core is paired with a satellite allocation across equities, gold and commodities. "
                 "Monthly trend signals and inverse-volatility weights guide the satellite; inactive shares "
                 "move to an approximate cash-return proxy. The portal presents historical backtests, not a live fund.")
    footer()


def shell(role):
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        brand()
    with right:
        st.button("Switch portal", on_click=set_role, args=(None,), width="stretch")
    html(f'<div class="portal-context">{escape(role)} portal <span>DEMO ACCESS</span></div>')
    return st.radio("Portal navigation", ["Overview", "Trade History", "Team Overview"],
                    key="portal_page", horizontal=True, label_visibility="collapsed")


def page_heading(kicker, title, description):
    html(f'<div class="page-heading"><div class="eyebrow">{escape(kicker)}</div>'
         f'<h1>{escape(title)}</h1><p>{escape(description)}</p></div>')


def team_page():
    page_heading("THE PEOPLE BEHIND THE PROCESS", "Different perspectives. Shared conviction.",
                 "Meet the six members of our Financial Modeling project team.")
    for start in range(0, len(TEAM), 3):
        for column, person in zip(st.columns(3, gap="large"), TEAM[start:start + 3]):
            with column, st.container(border=True):
                if person["photo"]:
                    st.image(str(ROOT / person["photo"]), width="stretch")
                else:
                    html(f'<div class="portrait"><span>{escape(person["initials"])}</span>'
                         '<small>PHOTO TO FOLLOW</small></div>')
                html(f'<h3 class="team-name">{escape(person["name"])}</h3>'
                     '<p class="team-role">Project team</p>')
                st.caption(f"Student ID: {person['student_id']}" if person["student_id"]
                           else "Student ID · to be added")


def trade_page():
    page_heading("PORTFOLIO ACTIVITY", "Trade history", "A dedicated home for past portfolio transactions.")
    with st.container(border=True):
        html('''<div class="empty-state"><div class="empty-icon">▤</div>
        <div class="eyebrow">COMING NEXT</div><h2>The full picture, trade by trade.</h2>
        <p>Historical transactions will be added here in a later update.<br>
        This view is prepared; no trade records have been connected yet.</p>
        <div class="trade-preview"><span>Trade date</span><span>Asset</span><span>Buy / Sell</span>
        <span>Quantity</span><span>Execution price</span></div></div>''')
    st.caption("This section will display past trades. It does not place or execute orders.")


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_data(_model):
    return _model.download_data(_model.DOWNLOAD_START, _model.BACKTEST_END)


def line_chart(data, ylabel, percent=False):
    if hasattr(data, "to_frame"):
        data = data.to_frame()
    with plt.rc_context({"axes.prop_cycle": plt.cycler(color=PALETTE),
                         "font.family": "DejaVu Sans", "font.size": 10,
                         "axes.labelcolor": "#647775", "xtick.color": "#647775",
                         "ytick.color": "#647775", "axes.edgecolor": "#e3eae8"}):
        fig, ax = plt.subplots(figsize=(11, 3.8))
        data.plot(ax=ax, linewidth=2, legend=True)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("")
        ax.grid(axis="y", color="#e3eae8", linewidth=.7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False, loc="upper left", ncol=min(3, len(data.columns)))
        if percent:
            ax.yaxis.set_major_formatter(PercentFormatter(1))
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        plt.close(fig)


def overview(m, role):
    page_heading("CORE–SATELLITE STRATEGY", "Portfolio overview",
                 "A considered view of performance, allocation and risk.")
    ma_months, core_weight, cost_bps = m.MA_MONTHS, m.CORE_WEIGHT, m.COST_BPS
    if role == "Investment Manager":
        with st.sidebar:
            html('<div class="eyebrow">MANAGER WORKSPACE</div>')
            st.header("Strategy parameters")
            st.caption("Explore alternative assumptions. Changes affect this session’s backtest only.")
            ma_months = st.slider("Moving-average length (months)", 3, 12, m.MA_MONTHS, key="manager_ma")
            core_weight = st.slider("Core weight in AGG", 0.0, 1.0, m.CORE_WEIGHT, .05, key="manager_core")
            cost_bps = st.slider("Transaction cost (bps per unit turnover)", 0, 50, m.COST_BPS, key="manager_cost")
            st.caption("Volatility: 12 monthly returns. Benchmark: 60% SPY / 40% AGG.")
            if (ma_months, core_weight, cost_bps) != (m.MA_MONTHS, m.CORE_WEIGHT, m.COST_BPS):
                st.info("Scenario analysis · parameters differ from the base strategy.")
    html(f'<div class="period-strip"><span>HISTORICAL BACKTEST</span>'
         f'<b>Mar 2007 – Oct 2026</b><span>Monthly · USD · Net of costs</span></div>')
    try:
        with st.spinner("Preparing your portfolio overview…"):
            prices, rf = load_data(m)
            results, rf_bt, weights, res_strat = m.run_all(prices, rf, core_weight, ma_months, cost_bps)
    except (ValueError, KeyError, OSError) as exc:
        st.error(f"Data or calculation check failed: {exc}")
        st.info("Check the source data and connection, then reload. Missing returns are never replaced with zero.")
        if st.button("Retry data connection"):
            load_data.clear()
            st.rerun()
        return
    table = m.performance_table(results, rf_bt)
    c1, c2, c3 = st.columns(3)
    c1.metric("Annualised return", f"{table.loc['Strategy', 'Ann. return']:.2%}")
    c2.metric("Sharpe ratio", f"{table.loc['Strategy', 'Sharpe']:.2f}",
              f"{table.loc['Strategy', 'Sharpe'] - table.loc[m.BENCHMARK, 'Sharpe']:+.2f} vs 60/40")
    c3.metric("Maximum drawdown", f"{table.loc['Strategy', 'Max drawdown']:.2%}")
    st.caption("Annualised return is the arithmetic monthly mean × 12. Drawdown is shown as a positive loss from a peak.")
    with st.container(border=True):
        st.subheader("A long-term perspective")
        st.caption("Growth of USD 1 · historical performance after transaction costs")
        line_chart(m.cumulative(results), "Value of USD 1")
    left, right = st.columns([1, 1], gap="large")
    with left, st.container(border=True):
        st.subheader("The investment framework")
        html(f'<div class="allocation-number">{core_weight:.0%}<span>bond ETF core</span></div>'
             f'<p class="muted">{1-core_weight:.0%} satellite budget across equities, gold and commodities, '
             'with inactive shares assigned to the cash proxy.</p>')
        st.caption(f"{ma_months}-month moving average · 12-month volatility · {cost_bps} bps transaction costs")
    with right, st.container(border=True):
        st.subheader("Latest model holdings")
        positions = res_strat.filter(like="weight_").rename(columns=lambda c: c.removeprefix("weight_"))
        latest = positions.iloc[-1].rename("Weight").to_frame()
        st.dataframe(latest.style.format("{:.1%}"), width="stretch")
        st.caption(f"Weights held in {positions.index[-1]:%B %Y}; historical model allocations.")
    with st.expander("Performance measures", expanded=False):
        pct = ["Ann. return", "CAGR", "Volatility", "Alpha (ann.)", "Tracking error", "Max drawdown"]
        st.dataframe(table.style.format({c: "{:.2%}" for c in pct}
                                       | {c: "{:.2f}" for c in ["Sharpe", "Beta", "Information ratio"]}), width="stretch")
        st.caption("Volatility = √12 × sample standard deviation. Sharpe uses excess returns over the cash proxy. "
                   "Alpha/beta use excess returns vs 60/40. Beta is not annualized. "
                   "Information ratio uses active returns / tracking error.")
    details = st.expander("Allocation history", key="details_allocation", on_change="rerun")
    if details.open:
        with details:
            fig, ax = plt.subplots(figsize=(11, 3.8))
            positions.plot.area(ax=ax, ylim=(0, 1), color=PALETTE, linewidth=0)
            ax.yaxis.set_major_formatter(PercentFormatter(1))
            ax.set_ylabel("Portfolio weight")
            ax.set_xlabel("")
            ax.legend(ncol=5, loc="upper left", frameon=False)
            fig.tight_layout()
            st.pyplot(fig, width="stretch")
            plt.close(fig)
    details = st.expander("Drawdowns and implementation costs", key="details_costs", on_change="rerun")
    if details.open:
        with details:
            st.subheader("Loss from the high water mark")
            line_chart(m.drawdowns(results), "Loss from peak", percent=True)
            st.subheader("Before and after transaction costs")
            gross_net = res_strat[["gross", "net"]].rename(columns={"gross": "Strategy gross", "net": "Strategy net"})
            line_chart(m.cumulative(gross_net), "Value of USD 1")
            st.write(f"Average monthly turnover after opening: {res_strat['turnover'].iloc[1:].mean():.2%}")
            st.caption("Turnover counts buys plus sells relative to drifted holdings, including proxy-cash trades. "
                       "Opening turnover is one. Net return = gross return − turnover × cost rate. "
                       "Buy & hold trades only at inception; 60/40 rebalances monthly. No final liquidation charge.")
    with st.expander("Data sources and methodology"):
        st.write(f"Monthly prices: {len(prices)} rows ({prices.index[0]:%b %Y} – {prices.index[-1]:%b %Y}); "
                 f"backtest: {len(results)} months.")
        st.caption("Yahoo Finance adjusted ETF closes, daily to calendar month-end; missing months stop the calculation. "
                   "Cash return = preceding ^IRX annual quoted yield / 100 / 12: an approximation, "
                   "not an investable T-bill total-return index.")
        st.caption("Signal-close execution is optimistic; a shift avoids crediting the signal month's return, "
                   "but cannot guarantee the assumed fill. Taxes, inflation and market impact are omitted. "
                   "ETF selection has hindsight risk; these results are historical, not an unseen validation sample. "
                   "A large AGG allocation retains duration and credit risk and does not guarantee capital preservation.")
    st.download_button("Download monthly returns", results.to_csv().encode("utf-8"),
                       file_name="monthly_net_returns.csv", mime="text/csv")
    st.caption("Historical backtest · Academic project · Past performance does not guarantee future results.")


def render_app(model):
    st.set_page_config(page_title="T Capital | Investment Management", page_icon="◈",
                       layout="wide", initial_sidebar_state="auto")
    styles()
    role = st.session_state.get("portal_role")
    if role not in ("Investor", "Investment Manager"):
        landing()
        return
    page = shell(role)
    if page == "Overview":
        overview(model, role)
    elif page == "Trade History":
        trade_page()
    else:
        team_page()
    footer()
