# Phase 3.20 dynamic sizing walk-forward gate

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because quiet-digestion sizing was discovered on the full sample, therefore it may be an overfit right-tail amplifier. If it is robust information, a sizing rule selected using past years should improve the next year versus equal-weight S1 under the same conservative execution proxy.

### 前因後果

- 使用 Phase 3.19 conservative proxy: `next_open`, cost `1.0%`, policy `exclude_limitup_risk`。
- 每個 split 只用 train years 在 candidate sizing rules 中選擇，然後在下一年 test；inactive months counted as cash。

### 檢查與結果

#### train_2023_test_2024
- train selected: `boost_quiet_no_large_black_125` (train return=31.57%, Sharpe=2.71, MDD=-5.04%, avg_pos=7.50)
- selected OOS 2024: return=14.45%, Sharpe=0.74, MDD=-15.69%, avg_pos=7.75
- equal S1 OOS 2024: return=12.91%, Sharpe=0.67, MDD=-16.01%, avg_pos=7.75
- OOS delta vs equal: return=1.54%, Sharpe delta=0.07
#### train_2023_2024_test_2025
- train selected: `boost_quiet_no_large_black_200` (train return=58.52%, Sharpe=1.54, MDD=-14.89%, avg_pos=7.67)
- selected OOS 2025: return=40.50%, Sharpe=1.17, MDD=-23.44%, avg_pos=7.27
- equal S1 OOS 2025: return=35.45%, Sharpe=1.08, MDD=-22.94%, avg_pos=7.27
- OOS delta vs equal: return=5.06%, Sharpe delta=0.09

### 修正與結論

- 修正了什麼：Phase 3.18/3.19 的 quiet boost 仍是 full-sample rule；本輪改成 train-selected / next-year OOS 檢查。
- 為什麼先前不夠好：full-sample Sharpe 小幅提高可能只是在同一批 winners 上加權，不能證明未來可用。
- 修正後結論是否改變：2/2 個 walk-forward split 同時在 OOS return 與 Sharpe 贏 equal S1。若未穩定通過，quiet boost 仍不得 promotion；S1 equal 保持 incumbent。
- 若 selected rule 只是 liq100 或 exclude/downweight 類型，代表 sizing signal 可能在訓練期補償 drawdown，而非穩定 alpha。

### 缺陷

- 只有 2023–2025 三個 revenue-year，walk-forward split 很少；這是防 overfit gate，不是充分 OOS 證明。
- 仍使用 monthly revenue available-date proxy 與 official open/close proxy，未含真實 intraday order-book fills。
- Candidate set 很小且手工設計；不能宣稱已找到最優 sizing。

### 下一步

1. 補 exact announcement timestamp 後重跑 Phase 3.19/3.20。
2. 若資料延伸到更多年份，改成 rolling 2-year train / 1-year test，並把 selection objective 加入 remove-winner penalty。
3. 若 quiet boost OOS 不穩，保留為 narrative diagnostic，不用作 sizing。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/dynamic_sizing_walkforward_summary.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/dynamic_sizing_walkforward_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_20_dynamic_sizing_walkforward_report.md`
