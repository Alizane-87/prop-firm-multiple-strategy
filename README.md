# prop-firm-multiple-strategy
CRT, CCT and other strategies for prop firm trading.

- **Main strategy (9am CRT):** 8am New York 1H candle = range → a 15m candle sweeps it and closes back inside →
  second sweep of that candle into a previous day/week/month level → 1m iFVG entry, stop beyond the sweep.
- **Plan:** one TradingView indicator that watches several forex pairs and futures, draws the setup and sends
  two Telegram alerts (get ready → entry). Trades are taken manually.
- Details, rules and all backtest results: [CLAUDE.md](CLAUDE.md).

## Run a backtest
```
pip install pandas numpy matplotlib
# put data/USTEC_PERIOD_M1.csv in place (see data/README.md)
python src/run_crt_levels.py
```
