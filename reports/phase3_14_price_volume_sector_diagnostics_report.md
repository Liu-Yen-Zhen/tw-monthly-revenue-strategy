# Phase 3.14 價量確認的產業條件診斷

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 本輪假說

Phase 3.13 顯示 high abnormal turnover 全期報酬較高，但 remove-winner 很脆弱。本輪檢查：成交值擴張是否只是半導體/電子供應鏈再定價的外顯狀態，而不是全市場有效的價量確認。

## 前因後果 / 邏輯

月營收 surprise 公布後，若法人與供應鏈投資人需要重新配置，電子/半導體鏈可能更容易出現成交值擴張與延續買盤；非電子族群若沒有同樣的產業敘事與資金池，放量可能只是事件日擁擠或短線出貨。因此同一個 abnormal turnover 條件必須分 electronics / non-electronics / semiconductor / no-semiconductor 檢查。

## Data / anti-look-ahead

- 使用既有 `daily_market_history_2023_present.csv`，只有 close 與 turnover_value；仍不能宣稱 K 線、ATR、長上影、長黑或盤中突破。
- 進場仍使用月營收可用日後的 proxy entry；成交值條件使用 entry 前可觀察的 20D/120D turnover ratio。
- 本輪所有 Sharpe 都把沒有訊號的月份列為 0% cash month，避免 active-month-only 高估。

## Thresholds

- `abnormal_turnover_low_tercile` = 0.7705
- `abnormal_turnover_high_tercile` = 1.3921
- `sur_3m_high_tercile` = 0.4965
- `momentum_120_20_high_tercile` = 0.2880

## Summary（20D fixed exit proxy, cash months counted）

- `baseline_s1_fixed20`: return=161.94%, Sharpe=1.55, MDD=-21.16%, active_months=29/30, avg_pos_all_months=7.27, trades=218
- `baseline_semiconductor`: return=248.88%, Sharpe=1.49, MDD=-22.84%, active_months=28/30, avg_pos_all_months=2.70, trades=81
- `baseline_no_semiconductor`: return=62.88%, Sharpe=0.83, MDD=-25.92%, active_months=28/30, avg_pos_all_months=6.30, trades=189
- `vol_high_electronics`: return=222.72%, Sharpe=1.53, MDD=-26.20%, active_months=26/30, avg_pos_all_months=3.20, trades=96
- `vol_high_non_electronics`: return=86.82%, Sharpe=0.89, MDD=-15.22%, active_months=15/30, avg_pos_all_months=0.77, trades=23
- `vol_high_semiconductor`: return=144.76%, Sharpe=0.92, MDD=-32.57%, active_months=20/30, avg_pos_all_months=1.27, trades=38
- `vol_high_no_semiconductor`: return=117.99%, Sharpe=1.02, MDD=-27.79%, active_months=27/30, avg_pos_all_months=2.67, trades=80
- `vol_low_electronics`: return=150.75%, Sharpe=1.21, MDD=-28.47%, active_months=29/30, avg_pos_all_months=3.37, trades=101
- `vol_low_non_electronics`: return=-33.45%, Sharpe=-0.49, MDD=-43.31%, active_months=13/30, avg_pos_all_months=0.60, trades=18

## Remove-winner stress

### baseline_s1_fixed20
- remove 0: return=161.94%, Sharpe=1.55, MDD=-21.16%, trades=218
- remove 5: return=97.08%, Sharpe=1.16, MDD=-21.16%, trades=213
- remove 10: return=67.60%, Sharpe=0.96, MDD=-21.16%, trades=208
- remove 20: return=16.27%, Sharpe=0.38, MDD=-25.64%, trades=198
### baseline_semiconductor
- remove 0: return=248.88%, Sharpe=1.49, MDD=-22.84%, trades=81
- remove 5: return=89.17%, Sharpe=0.88, MDD=-26.62%, trades=76
- remove 10: return=37.64%, Sharpe=0.55, MDD=-32.07%, trades=71
- remove 20: return=-40.49%, Sharpe=-0.68, MDD=-45.57%, trades=61
### baseline_no_semiconductor
- remove 0: return=62.88%, Sharpe=0.83, MDD=-25.92%, trades=189
- remove 5: return=34.04%, Sharpe=0.61, MDD=-25.92%, trades=184
- remove 10: return=15.98%, Sharpe=0.39, MDD=-25.92%, trades=179
- remove 20: return=-13.88%, Sharpe=-0.19, MDD=-28.16%, trades=169
### vol_high_electronics
- remove 0: return=222.72%, Sharpe=1.53, MDD=-26.20%, trades=96
- remove 5: return=58.32%, Sharpe=0.75, MDD=-32.52%, trades=91
- remove 10: return=12.41%, Sharpe=0.31, MDD=-32.52%, trades=86
- remove 20: return=-25.13%, Sharpe=-0.34, MDD=-40.43%, trades=76
### vol_high_non_electronics
- remove 0: return=86.82%, Sharpe=0.89, MDD=-15.22%, trades=23
- remove 5: return=-19.32%, Sharpe=-0.37, MDD=-19.32%, trades=18
- remove 10: return=-39.77%, Sharpe=-1.31, MDD=-39.77%, trades=13
- remove 20: return=-31.35%, Sharpe=-0.89, MDD=-31.35%, trades=3
### vol_high_semiconductor
- remove 0: return=144.76%, Sharpe=0.92, MDD=-32.57%, trades=38
- remove 5: return=-3.12%, Sharpe=0.12, MDD=-32.57%, trades=33
- remove 10: return=-49.24%, Sharpe=-0.94, MDD=-54.67%, trades=28
- remove 20: return=-69.23%, Sharpe=-1.95, MDD=-69.23%, trades=18
### vol_high_no_semiconductor
- remove 0: return=117.99%, Sharpe=1.02, MDD=-27.79%, trades=80
- remove 5: return=37.60%, Sharpe=0.60, MDD=-27.79%, trades=75
- remove 10: return=-9.80%, Sharpe=-0.01, MDD=-31.09%, trades=70
- remove 20: return=-41.67%, Sharpe=-0.77, MDD=-47.06%, trades=60
### vol_low_electronics
- remove 0: return=150.75%, Sharpe=1.21, MDD=-28.47%, trades=101
- remove 5: return=93.34%, Sharpe=0.92, MDD=-33.97%, trades=96
- remove 10: return=63.59%, Sharpe=0.74, MDD=-33.97%, trades=91
- remove 20: return=-28.53%, Sharpe=-0.43, MDD=-40.31%, trades=81
### vol_low_non_electronics
- remove 0: return=-33.45%, Sharpe=-0.49, MDD=-43.31%, trades=18
- remove 5: return=-51.16%, Sharpe=-1.13, MDD=-51.58%, trades=13
- remove 10: return=-56.76%, Sharpe=-1.28, MDD=-56.76%, trades=8
- remove 20: return=0.00%, Sharpe=NA, MDD=0.00%, trades=0

## Year split

### baseline_s1_fixed20
- 2023: return=36.58%, Sharpe=3.41, MDD=-3.29%, active=6/6
- 2024: return=22.45%, Sharpe=1.03, MDD=-15.24%, active=12/12
- 2025: return=56.62%, Sharpe=1.51, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### baseline_semiconductor
- 2023: return=32.14%, Sharpe=1.78, MDD=-6.87%, active=6/6
- 2024: return=61.79%, Sharpe=1.63, MDD=-22.29%, active=12/12
- 2025: return=63.19%, Sharpe=1.30, MDD=-22.84%, active=10/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### baseline_no_semiconductor
- 2023: return=25.80%, Sharpe=2.51, MDD=-2.06%, active=6/6
- 2024: return=3.22%, Sharpe=0.25, MDD=-17.47%, active=12/12
- 2025: return=25.44%, Sharpe=0.81, MDD=-21.16%, active=10/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_high_electronics
- 2023: return=47.26%, Sharpe=4.08, MDD=0.00%, active=5/6
- 2024: return=65.54%, Sharpe=1.49, MDD=-20.92%, active=11/12
- 2025: return=32.39%, Sharpe=0.96, MDD=-26.20%, active=10/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_high_non_electronics
- 2023: return=-0.66%, Sharpe=-0.09, MDD=-4.77%, active=2/6
- 2024: return=10.69%, Sharpe=0.55, MDD=-14.10%, active=7/12
- 2025: return=69.90%, Sharpe=1.40, MDD=-15.22%, active=6/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_high_semiconductor
- 2023: return=26.21%, Sharpe=2.07, MDD=-1.86%, active=5/6
- 2024: return=36.86%, Sharpe=0.95, MDD=-27.08%, active=8/12
- 2025: return=41.70%, Sharpe=0.81, MDD=-32.57%, active=7/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_high_no_semiconductor
- 2023: return=48.08%, Sharpe=3.18, MDD=-4.77%, active=6/6
- 2024: return=41.51%, Sharpe=1.14, MDD=-15.40%, active=11/12
- 2025: return=4.02%, Sharpe=0.31, MDD=-27.79%, active=10/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_low_electronics
- 2023: return=57.04%, Sharpe=2.83, MDD=-9.07%, active=6/6
- 2024: return=25.35%, Sharpe=0.84, MDD=-13.99%, active=12/12
- 2025: return=27.39%, Sharpe=0.83, MDD=-24.25%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_low_non_electronics
- 2023: return=12.99%, Sharpe=1.33, MDD=-3.58%, active=4/6
- 2024: return=-11.30%, Sharpe=-0.76, MDD=-12.13%, active=5/12
- 2025: return=-33.60%, Sharpe=-1.00, MDD=-34.12%, active=4/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1

## Interpretation

- 若 `vol_high_semiconductor` 明顯強於 `vol_high_no_semiconductor`，成交值擴張較像半導體供應鏈 repricing confirmation，而不是普遍技術面放量規則。
- 若 `vol_high_non_electronics` 的 active months 少、MDD 大或 remove-winner 後崩壞，下一輪不應把非電子放量追價升級為 candidate。
- 若 baseline 在 no-semiconductor 仍弱於 semiconductor，S1 的 interview framing 應繼續定位為 Taiwan electronics / semiconductor monthly-revenue surprise + fundamental momentum。
- 目前資料仍不足以研究真正 K 線供給壓力；下一步要補 OHLC/limit-up-down 後再測 long upper shadow / long black candle。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_sector_diagnostics.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_sector_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_sector_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_14_price_volume_sector_diagnostics_report.md`
