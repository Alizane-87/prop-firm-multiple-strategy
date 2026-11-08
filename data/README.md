# Data (not committed)

Price files are too large for git. Put them here before running the backtests.

- `USTEC_PERIOD_M1.csv` — MT5 → Symbols → Bars → Export Bars (USTEC, M1, 2023-01-03 onwards).
  The owner's copy lives in `MQL5\Files\BarsExport\` on his PC.
- Broker clock is EET with EU daylight saving; `crt_core.server_to_et()` converts to New York time.
- Broker M1 data is frozen 2024-10-04 → 2025-01-05; the backtests skip 2024-10-04 → 2025-01-31.
