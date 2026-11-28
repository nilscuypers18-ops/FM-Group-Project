# Course alignment

How the notebook maps to the course notebooks in `inputs/course/`, and where it
deliberately differs. Use this to prepare for questions about the code.

## Follows the course

| Step in our notebook | Course source | What we reuse |
|---|---|---|
| Download with `yfinance`, check shape, dates, missing values, plot | Lecture 3 (APIs and pandas) | The four data checks; no silent `dropna()` |
| Price vs. moving average signal, preview chart of price, SMA and position | Lecture 4, §4.2 | `rolling(window).mean()`, position = price > SMA |
| `shift(1)`: a decision at t earns the return of t+1 | Lecture 4, §4.1 | The look-ahead fix |
| Net return = gross return − cost × traded weight; cost sensitivity | Lecture 4, §4.3 | Transaction costs and the breakeven-cost idea |
| 40/60 SPY/AGG benchmark rebalanced every period | Lecture 4, "hidden assumption" | Fixed weights imply rebalancing |
| Beta = cov / var, alpha from means, Sharpe and IR annualized with 12 and √12 | Lecture 3, §§3.3–3.4; formula sheet | Hand-written formulas, no black box |
| Drawdown from the high water mark | Lecture 3, §3.5; formula sheet | Positive loss from the running maximum |
| Monte Carlo wealth paths, percentile bands and terminal loss probability | Lecture 5, §§5.3 and 5.5 | 10,000 normal-return paths, monthly compounding, seed 2270; means scale with time and volatility with √time |

## Deliberate differences (be ready to explain)

* **Simple instead of log returns.** A portfolio return is the weighted sum of its
  assets' simple returns; with log returns that is not exact. Wealth = `(1 + r).cumprod()`.
* **T-bill rate instead of rf = 0.** Sharpe, alpha and beta use excess returns over `^IRX / 100 / 12`.
* **Formulas by hand instead of `quantstats`.** Same definitions, but every step is visible.
* **Daily prices resampled to month-end** instead of `interval="1mo"`, so the month-end
  close is exactly the price used for the signal.
* **Backtest loop with drifting weights.** The lectures use one-line vectorized returns
  with constant weights. Because we rebalance monthly and charge costs on actual trades,
  the weights must drift with returns between rebalancing dates; the short loop in
  `backtest()` does exactly that.
* **Sample starts in March 2007.** Twelve monthly returns (thirteen prices from February
  2006) are needed for the first volatility estimate.

## Monte Carlo extension

Section 6 and the portal's Monte Carlo page use the same `monte_carlo()` function from
the master notebook. The default is a USD 100,000 lump sum over 10 years. Monthly means
and sample volatilities are estimated from the full common backtest's net returns;
there are no contributions or withdrawals. The normal model simulates portfolio
returns, not future trend decisions or ETF weights. Costs are already in the inputs.

An explicit extension to the single-portfolio lecture example pairs strategy and
benchmark shocks using their historical monthly correlation: `z_strategy = z1` and
`z_benchmark = rho*z1 + sqrt(1-rho**2)*z2`, for independent standard normals z1 and z2.
Months are independent and the estimated parameters are fixed. The portal shows
the calibration, formulas, interpretation and limitations, and exports assumptions
and percentile bands. A normal return at or below -100% raises an error rather than
being silently clipped. These are scenarios under a model, not forecasts.

## Not included on purpose

Bond pricing (Lecture 2) and optimisation are not required by the assignment and
would add a different model. Interest-rate risk of the bond core is discussed in
the notebook's limitations.
