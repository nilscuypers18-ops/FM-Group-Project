"""Explain recorded backtest trades without changing the investment rule.

Dollar values illustrate an initial investment, compounded with the engine's
net returns. They are model notionals, not broker fills or a share ledger.
"""
import numpy as np
import pandas as pd


TRADE_TOLERANCE = 1e-12


def rebalance_history(model, prices, detail, ma_months, initial_capital=100_000.0):
    """Return monthly events and per-asset decisions, including unchanged assets.

    The standard app uses a one-month lag: a February signal is assumed to
    execute at that close and earns March's return. Calendar labels are not
    claims of actual exchange trading dates. Costs follow the additive engine.
    """
    if not np.isfinite(initial_capital) or initial_capital <= 0:
        raise ValueError("Illustrative initial investment must be positive and finite.")
    signals = model.trend_signal(prices[model.SATELLITE], ma_months)
    sma = prices[model.SATELLITE].rolling(ma_months, min_periods=ma_months).mean()
    vol = model.rolling_vol(prices[model.SATELLITE])
    inverse = 1 / vol.where(vol > 0)
    shares = inverse.div(inverse.sum(axis=1, min_count=len(model.SATELLITE)), axis=0)
    assets = [c.removeprefix("weight_") for c in detail if c.startswith("weight_")]
    previous = pd.Series(0.0, index=assets)
    capital = float(initial_capital)
    scenario = {
        "initial_capital_usd": float(initial_capital), "ma_months": ma_months,
        "vol_months": model.VOL_MONTHS,
        "core_weight": detail[f"weight_{model.CORE}"].iloc[0],
        "cost_bps": detail.cost.iloc[0] / detail.turnover.iloc[0] * 10000,
    }
    months, decisions = [], []
    for i, (month, result) in enumerate(detail.iterrows()):
        signal_date = month - pd.offsets.MonthEnd(1)
        prior_date = signal_date - pd.offsets.MonthEnd(1)
        target = pd.Series({a: result[f"weight_{a}"] for a in assets})
        pretrade = pd.Series({a: result[f"pretrade_{a}"] for a in assets})
        delta = pd.Series({a: result[f"trade_{a}"] for a in assets})
        traded = delta.abs() > TRADE_TOLERANCE
        event = "Opening allocation" if i == 0 else ("Rebalance" if traded.any() else "No trades")
        months.append({
            "signal_date": signal_date, "return_month": month, "event": event,
            "assets_traded": int(traded.sum()), "buys": delta.clip(lower=0).sum(),
            "sells": -delta.clip(upper=0).sum(), "turnover": result["turnover"],
            "traded_usd": result["turnover"] * capital, "cost_rate": result["cost"],
            "cost_usd": result["cost"] * capital, "opening_value": capital,
            "closing_value": capital * (1 + result["net"]),
            "gross_return": result["gross"], "net_return": result["net"],
            "cash_weight": target.get(model.TBILL, 0.0),
        })
        for asset in assets:
            change = target[asset] - previous[asset]
            drift_correction = previous[asset] - pretrade[asset]
            action = ("Buy" if delta[asset] > 0 else "Sell") if traded[asset] else "Hold"
            price = moving_average = volatility = budget = np.nan
            if asset in model.SATELLITE:
                active = bool(signals.loc[signal_date, asset])
                prior_active = signals.loc[prior_date, asset] if prior_date in signals.index else np.nan
                status = "On · above moving average" if active else "Off · at/below moving average"
                price = prices.loc[signal_date, asset]
                moving_average = sma.loc[signal_date, asset]
                volatility = vol.loc[signal_date, asset]
                budget = (1 - target[model.CORE]) * shares.loc[signal_date, asset]
                if budget <= TRADE_TOLERANCE:
                    reason = "No satellite budget under the 100% bond-core scenario."
                elif i == 0:
                    reason = "Opening allocation; trend on." if active else "Trend off; satellite share assigned to cash proxy."
                elif pd.notna(prior_active) and active != bool(prior_active):
                    reason = ("Trend switched on; restore inverse-volatility allocation." if active
                              else "Trend switched off; move this asset's allocation to cash proxy.")
                elif active and abs(change) > TRADE_TOLERANCE:
                    reason = "Trend remains on; inverse-volatility sizing changed."
                elif active:
                    reason = "Trend remains on; target unchanged."
                else:
                    reason = "Trend remains off; satellite share stays in cash proxy."
            elif asset == model.CORE:
                status = "Fixed bond core"
                reason = "Establish fixed bond core." if i == 0 else "Maintain fixed bond-core target."
            else:
                status = "Cash-return proxy"
                reason = ("Fund inactive satellites' shares in the cash proxy." if i == 0
                          else "Cash target follows inactive satellite shares and their inverse-volatility sizing.")
            if i > 0 and abs(drift_correction) > TRADE_TOLERANCE:
                reason += " Also correct market drift." if abs(change) > TRADE_TOLERANCE else " Correct market drift."
            if action == "Hold":
                reason += " No trade required."
            decisions.append({
                "signal_date": signal_date, "return_month": month, "asset": asset,
                "action": action, "previous_target": previous[asset], "pretrade_weight": pretrade[asset],
                "target_weight": target[asset], "target_change_pp": 100 * change,
                "drift_correction_pp": 100 * drift_correction, "trade_pp": 100 * delta[asset],
                "trade_usd": delta[asset] * capital,
                "cost_usd": (abs(delta[asset]) / result["turnover"] * result["cost"] * capital
                             if result["turnover"] > 0 else 0.0),
                "status": status, "reason": reason, "adjusted_close": price,
                "moving_average": moving_average, "annual_volatility": volatility,
                "satellite_budget": budget,
            })
        previous = target
        capital *= 1 + result["net"]
    monthly_log, asset_log = pd.DataFrame(months), pd.DataFrame(decisions)
    for key, value in scenario.items():
        monthly_log[key] = value
        asset_log[key] = value
    return monthly_log, asset_log
