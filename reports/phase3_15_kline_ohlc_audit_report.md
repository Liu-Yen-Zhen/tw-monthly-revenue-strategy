# Phase 3.15 OHLC/K-line data audit and entry-state diagnostics

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 本輪假說

月營收 SUR 後，若 entry-day K 線已出現長上影、弱收盤位置或大黑 K，可能代表好消息公布後的供給壓力/出貨，後續 20D 報酬應較差；反之，沒有明顯供給壓力或窄幅整理，較符合 surprise 尚在被消化的延遲再定價。

## Data audit

- `twse`: raw_files=48, common_stock_rows=47748, OHLC coverage=100.00%, next-limit coverage=0.00%, scored entry OHLC matched=0/0
- `tpex`: raw_files=885, common_stock_rows=667388, OHLC coverage=100.00%, next-limit coverage=100.00%, scored entry OHLC matched=2002/2002
- overall scored entry rows matched: close=2002/2002, OHLC=2002/2002

## Thresholds from available entry-day OHLC

- upper-shadow high tercile = 0.3457
- close-location low tercile = 0.2222
- range-pct low tercile = 0.0290
- body-ratio high tercile = 0.6559

## Variant summary（20D fixed exit, inactive months counted as cash）

- `s1_baseline_ohlc_available`: return=161.94%, Sharpe=1.55, MDD=-21.16%, active=29/30, avg_pos=7.27, trades=218
- `kline_no_supply_pressure`: return=68.44%, Sharpe=0.77, MDD=-31.33%, active=27/30, avg_pos=4.57, trades=137
- `kline_supply_pressure`: return=104.56%, Sharpe=1.06, MDD=-28.78%, active=29/30, avg_pos=5.70, trades=171
- `kline_quiet_narrow_range`: return=94.69%, Sharpe=1.02, MDD=-18.63%, active=28/30, avg_pos=4.17, trades=125
- `kline_large_black`: return=20.07%, Sharpe=0.41, MDD=-23.86%, active=20/30, avg_pos=1.97, trades=59
- `kline_electronics_no_supply`: return=66.94%, Sharpe=0.75, MDD=-30.62%, active=27/30, avg_pos=4.07, trades=122
- `kline_nonelectronics_no_supply`: return=83.45%, Sharpe=0.89, MDD=-19.95%, active=14/30, avg_pos=0.77, trades=23

## Remove-winner stress

### s1_baseline_ohlc_available
- remove 0: return=161.94%, Sharpe=1.55, MDD=-21.16%, trades=218
- remove 5: return=97.08%, Sharpe=1.16, MDD=-21.16%, trades=213
- remove 10: return=67.60%, Sharpe=0.96, MDD=-21.16%, trades=208
- remove 20: return=16.27%, Sharpe=0.38, MDD=-25.64%, trades=198
### kline_no_supply_pressure
- remove 0: return=68.44%, Sharpe=0.77, MDD=-31.33%, trades=137
- remove 5: return=25.41%, Sharpe=0.46, MDD=-34.82%, trades=132
- remove 10: return=1.40%, Sharpe=0.16, MDD=-34.82%, trades=127
- remove 20: return=-25.11%, Sharpe=-0.31, MDD=-40.10%, trades=117
### kline_supply_pressure
- remove 0: return=104.56%, Sharpe=1.06, MDD=-28.78%, trades=171
- remove 5: return=50.33%, Sharpe=0.69, MDD=-29.77%, trades=166
- remove 10: return=13.67%, Sharpe=0.32, MDD=-33.00%, trades=161
- remove 20: return=-31.22%, Sharpe=-0.66, MDD=-41.35%, trades=151
### kline_quiet_narrow_range
- remove 0: return=94.69%, Sharpe=1.02, MDD=-18.63%, trades=125
- remove 5: return=13.46%, Sharpe=0.34, MDD=-25.48%, trades=120
- remove 10: return=-15.48%, Sharpe=-0.24, MDD=-28.60%, trades=115
- remove 20: return=-39.63%, Sharpe=-1.15, MDD=-42.64%, trades=105
### kline_large_black
- remove 0: return=20.07%, Sharpe=0.41, MDD=-23.86%, trades=59
- remove 5: return=-11.38%, Sharpe=-0.06, MDD=-30.33%, trades=54
- remove 10: return=-33.92%, Sharpe=-0.64, MDD=-38.23%, trades=49
- remove 20: return=-55.90%, Sharpe=-1.74, MDD=-55.90%, trades=39

## Year split

### s1_baseline_ohlc_available
- 2023: return=36.58%, Sharpe=3.41, MDD=-3.29%, active=6/6
- 2024: return=22.45%, Sharpe=1.03, MDD=-15.24%, active=12/12
- 2025: return=56.62%, Sharpe=1.51, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### kline_no_supply_pressure
- 2023: return=30.30%, Sharpe=2.77, MDD=-1.80%, active=5/6
- 2024: return=20.25%, Sharpe=0.72, MDD=-23.72%, active=12/12
- 2025: return=7.50%, Sharpe=0.39, MDD=-25.41%, active=10/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### kline_supply_pressure
- 2023: return=35.96%, Sharpe=3.58, MDD=-2.27%, active=6/6
- 2024: return=-10.20%, Sharpe=-0.39, MDD=-28.78%, active=12/12
- 2025: return=67.56%, Sharpe=1.51, MDD=-19.30%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### kline_quiet_narrow_range
- 2023: return=24.14%, Sharpe=2.25, MDD=-4.00%, active=6/6
- 2024: return=23.63%, Sharpe=1.06, MDD=-14.18%, active=12/12
- 2025: return=26.86%, Sharpe=0.78, MDD=-18.63%, active=10/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### kline_large_black
- 2023: return=25.15%, Sharpe=2.39, MDD=-4.31%, active=5/6
- 2024: return=-0.92%, Sharpe=0.07, MDD=-20.44%, active=7/12
- 2025: return=-3.17%, Sharpe=0.07, MDD=-23.79%, active=8/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1

## Interpretation

- 這是第一輪真正使用 raw official OHLC 的 K-line audit；若 coverage 足夠，後續可以把 Phase 3.13 的『不能測 K 線』限制縮小為『可以測日線 OHLC，但仍不能測盤中突破與真實成交排隊』。
- `kline_no_supply_pressure` 若優於 `kline_supply_pressure`，代表 K 線狀態可能是 fundamental surprise 後的供給壓力過濾器，而不是獨立 alpha。
- 若 `kline_large_black` 很差，符合 failed repricing / distribution 的市場結構敘事；但樣本數與 remove-winner 必須過關才可升級。
- 本輪仍未模擬公告時點、隔日開盤可成交性、漲跌停 non-fill 與 intraday slippage，因此不應升級為 production execution rule。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/kline_ohlc_audit_summary.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/kline_entry_state_variants.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/kline_entry_state_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/kline_entry_state_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_15_kline_ohlc_audit_report.md`
