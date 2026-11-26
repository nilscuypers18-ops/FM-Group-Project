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

## Not included on purpose

Monte Carlo (Lecture 5), bond pricing (Lecture 2) and optimisation are not required by
the assignment and would add a different model. Their lessons (explicit assumptions,
interest-rate risk of the bond core) are discussed in the notebook's limitations.
