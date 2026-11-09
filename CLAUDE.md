# Prop firm strategies — project notes (CRT backtests, EA, TradingView alerts)

Owner: wants a strategy with a real, proven edge that runs as an EA or sends signals (can't watch charts). No prop
challenge purchase until a strategy passes: 3 yrs, ≥200 trades, profitable every year, ≥ +0.15R/trade after costs,
prop sim passes, MT5 tester matches, 4-8 weeks demo signals. Explain results in plain words and tables; times in IST.

## Data
- data/USTEC_PERIOD_M1.csv = MT5 Symbols→Bars "Export Bars" (tab-separated <DATE>), 2023-01-03 → 2026-11-06, from
  owner's PC: C:\Users\hp\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\BarsExport
- Broker server clock = EET with EU daylight saving (NOT NY+7 all year) → crt_core.server_to_et(). Verified by the
  09:30 NY opening spike in the weeks US/EU DST differ.
- Broker M1 data FROZEN 2024-10-04 → 2025-01-05 (crt_core.frozen_days). Skip 2024-10-04 → 2025-01-31.
- Costs: CFD = bar spread (~1 pt); futures model = 0.25 spread + 0.25 commission.

## CRT (src/crt_core.py, src/run_crt_levels.py) — owner's rules
8am NY 1H candle = range → candle A (15m, 09:00-11:00) takes 8am high/low and closes back inside → second sweep of
candle A → 1m entry straight away (iFVG / CHoCH / OB = last opposite candle with body ≥30% of range) → stop beyond the
second-sweep extreme → 2R / 3R / other side. One trade/day, entry before 11:00, exit 15:55.
KEY LEVELS (owner 8 Nov): location filter — the SECOND SWEEP must trade into a previous day/week/month high (shorts)
or low (longs). NOT a separate key-level-sweep strategy (owner: that is a different strategy for later).

Results 2023-26 (frozen period excluded), stop beyond sweep extreme:
- Pure CRT: iFVG 3R +0.092R CFD / +0.124R fut (490 tr, all years +); iFVG 2R +0.065/+0.089; CHoCH ~+0.03-0.08; OB negative.
- Second sweep into any key level: iFVG 3R +0.130 CFD / +0.210 fut (140 tr ≈ 3.3/mo, fut all years +, DD 9R);
  iFVG 2R +0.167/+0.202 (2023 ≈ 0). Prev WEEK/MONTH only: iFVG 2R +0.40R, 3R +0.30/+0.44R (56 tr, all years +).
  Prev DAY only ≈ 0. CHoCH gets WORSE with levels. OB + week/month 3R +0.30/+0.39R on 38 tr (2024 neg, 5 tr).
- Many variants tested on the same data → confirm on unseen years (NQ futures 2019-2022, Databento ohlcv-1m).

## Key-level sweep + 1m iFVG, NO CRT (owner 8 Nov) — src/level_sweep.py, src/run_level_sweep.py
Prev day/week/month high (short) / low (long); first cross in the window; iFVG (last FVG from 30 min before the cross
to the extreme) closed through within 60 min → next 1m open; stop beyond sweep extreme; 2R/3R; max 2 trades/day.
Result: NO edge on its own. 08:00-12:00 NY: −0.00 to +0.05R (750 tr). London+NY 03:00-12:00, prev DAY, 2R, futures
costs: +0.086R (607 tr) best; all-day ≈ +0.06R. Week/month alone ≈ 0. → The +0.2R in CRT-at-key-level comes from the
COMBINATION (CRT structure + key-level location), not from the level sweep itself.

## CRT at other times (owner 8 Nov: "3am and 6am purges") — src/run_crt_times.py (crt_core.run rh/p0/p1)
Same rules, range candle shifted: 3am purge = 2am 1H range, candle A 03:00-05:00 NY; 6am purge = 5am range, 06:00-08:00.
iFVG, stop beyond sweep: 3am pure CRT −0.11/−0.05R (2R CFD/fut), 3R −0.02/+0.01; with key level only 46 trades, negative.
6am pure −0.10/−0.03 (2R), −0.12/−0.02 (3R); key level 34 trades, −0.2 to −0.3R. Only the 9am purge has an edge.
OWNER DECISION 8 Nov: keep ONLY the 9am CRT for now; 3am/6am dropped.

## 9am CRT, 2026 only (1 Jan → 6 Nov), iFVG, stop beyond sweep
- Pure: 2R +0.04 CFD / +0.09 fut, 3R +0.06/+0.09 (120 tr, DD ~20R).
- Any key level: 2R +0.18/+0.17 (38 tr, DD 9R); 3R −0.01/+0.10 (weakest year; Jul-Sep −7R).
- Week/month level: 2R +0.57/+0.56 (14 tr, DD 2R); 3R +0.37/+0.36.

## TradingView indicator plan (owner 8 Nov, not built yet — owner said don't draft yet)
One Pine indicator: monitors chosen forex pairs + futures, models switchable, auto-plots on the chart symbol,
dashboard table for all symbols, one alert() → Telegram webhook. ALERTS: only TWO — (1) "watch for iFVG" when the
second sweep trades into a key level (median ~13 min before entry; ~1 in 5 within 5 min), (2) entry with
entry/stop/2R/3R. Owner trades manually. Tools: official TradingView MCP + pinescript-mcp + browser pane.
Owner 8 Nov: the INDICATOR is the daily tool. A strategy() copy with identical rules exists only to check against
Python (chart symbol, recent weeks — Essential loads ~10k bars). Plan: TradingView Essential, no data packs; use free
real-time CFD feeds (broker's own if listed, else PEPPERSTONE:NAS100 / OANDA:NAS100USD) + free forex feeds. CME pack
only when a futures account exists and its TradingView connection doesn't give real-time CME data.
Build order: MCP connectors → CRT Pine (chart pass, then alerts pass) → demo alerts → next strategy backtest in Python.

## Owner's FundingPips accounts (bought 9 Nov 2026) — src/prop_sim.py
- 10k 2-Step Standard: targets 8% / 5%, max loss 10% static, daily 5% (higher of opening balance/equity, 00:00 server).
- 5k 2-Step Pro: targets 6% / 6%, max loss 6% static, daily 3%. No time limit on either.
- 30 calendar days without a fully CLOSED trade = breach (inactivity). Hedging banned, incl. across own accounts.
- Prop sim (bootstrap of the 140 key-level iFVG trades, CFD costs, 2R): 10k Std 1% risk → pass both ~76%, median ~15
  months; 1.5% → 64%, ~7.5 mo. 5k Pro 1% → 55%, ~11 mo; 0.5% → 79%, ~31 mo. 3R is worse on every row.
  In-sample, so real odds are lower. Bottleneck = ~3.3 trades/month → more tested symbols/strategies needed.

## Repo layout (run everything from the repo root)
- src/ — crt_core.py (engine), run_*.py (backtests → out/*.json, *.pkl), plot_*.py (charts → out/charts/)
- tools/ — mt5_download.py, databento_bars.py (no keys inside; databento_bars only converts downloaded files)
- mt5/ — ExportBars.mq5 (exports broker bars to MQL5\Files\BarsExport)
- data/ — NOT committed (too large). Put USTEC_PERIOD_M1.csv here; see data/README.md.
- Never commit: Telegram bot token, Databento key, broker logins, .env files.
