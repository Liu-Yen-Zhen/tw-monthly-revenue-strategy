# Phase 3.24 OOS sector and remove-winner stress for delay-aware rules

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because Phase 3.23 robust-selected rules beat same-delay equal S1 in two next-year tests, therefore the next gate is whether those OOS gains survive outside the dominant semiconductor/electronics exposure and after removing the largest OOS winners. If not, the rules are timing/sizing diagnostics, not promotable industry-survivable alpha.

### 前因後果

- Taiwan monthly-revenue SUR edge has repeatedly looked electronics/semiconductor supply-chain driven.
- A rule selected with train remove-winner penalty can still fail if the next-year improvement is supplied by a few OOS winners or by semiconductor-only exposure.

### 檢查

- Tested 2 Phase 3.23 selected split-specific rules; cost=1.0%; delayed official open entry; limit-up-risk rows excluded.
- OOS slices: all, electronics-only, non-electronics, semiconductor-only, no-semiconductor. OOS remove-top: 0/3/5/10 winners by weighted monthly contribution.

### 結果

#### train_2023_test_2024: `boost_quiet_no_large_black_200 | delay=2`
- sector `all`: return=14.73%, Sharpe=0.76, MDD=-15.86%, active=12/12, avg_pos=7.75
- sector `electronics_only`: return=22.11%, Sharpe=0.85, MDD=-19.98%, active=12/12, avg_pos=6.33
- sector `non_electronics`: return=20.28%, Sharpe=0.86, MDD=-8.43%, active=9/12, avg_pos=1.42
- sector `semiconductor_only`: return=59.83%, Sharpe=1.52, MDD=-26.42%, active=12/12, avg_pos=2.67
- sector `no_semiconductor`: return=-12.58%, Sharpe=-0.56, MDD=-26.03%, active=12/12, avg_pos=5.08
- remove-winner OOS stress:
  - remove_top_0: return=14.73%, Sharpe=0.76, MDD=-15.86%, avg_pos=7.75
  - remove_top_3: return=-5.73%, Sharpe=-0.17, MDD=-22.97%, avg_pos=7.50
  - remove_top_5: return=-12.74%, Sharpe=-0.50, MDD=-26.01%, avg_pos=7.33
  - remove_top_10: return=-24.73%, Sharpe=-1.24, MDD=-32.03%, avg_pos=6.92

#### train_2023_2024_test_2025: `boost_quiet_no_large_black_200 | delay=1`
- sector `all`: return=40.50%, Sharpe=1.17, MDD=-23.44%, active=11/11, avg_pos=7.27
- sector `electronics_only`: return=53.36%, Sharpe=1.34, MDD=-23.15%, active=11/11, avg_pos=6.18
- sector `non_electronics`: return=0.77%, Sharpe=0.13, MDD=-9.64%, active=8/11, avg_pos=1.09
- sector `semiconductor_only`: return=140.25%, Sharpe=2.59, MDD=-7.11%, active=9/11, avg_pos=2.09
- sector `no_semiconductor`: return=4.77%, Sharpe=0.31, MDD=-23.44%, active=10/11, avg_pos=5.18
- remove-winner OOS stress:
  - remove_top_0: return=40.50%, Sharpe=1.17, MDD=-23.44%, avg_pos=7.27
  - remove_top_3: return=15.07%, Sharpe=0.59, MDD=-23.44%, avg_pos=7.00
  - remove_top_5: return=6.68%, Sharpe=0.37, MDD=-23.44%, avg_pos=6.82
  - remove_top_10: return=-11.83%, Sharpe=-0.27, MDD=-23.44%, avg_pos=6.36

### 修正與結論

- 修正了什麼：Phase 3.23 只確認 selected rules 在 headline OOS return/Sharpe 勝過 same-delay equal S1；本輪補上 OOS sector survival 與 OOS remove-winner stress。
- 為什麼先前不夠好：train-side remove-winner penalty 不保證 test-side 不靠少數股票，也不保證非半導體可生存。
- 修正後結論是否改變：不改變 promotion 結論。若 no-semiconductor 或 remove-top-5 後 Sharpe 顯著低於 all-slice，Phase 3.23 的改善應描述為 semiconductor/electronics delayed-repricing sizing diagnostic，而非 broad industry-survivable strategy。

### 缺陷

- OOS 年度只有 2024/2025；sector labels are static current labels。
- remove-winner uses weighted monthly contribution proxy；沒有 full portfolio accounting with overlapping trades。
- Exact announcement timestamps and actual limit-up queue fills are still missing。

### 下一步

1. 將 Phase 3.24 結果接到 exact timestamp sourcing plan；不要再擴 grid 追 Sharpe。
2. 建立 2026 paper-trading schema：timestamp / planned entry / observed open / limit-up flag / non-fill reason / slippage。
3. 若繼續研究 selected boost=200，必須先做 position-cap/turnover-cap，避免過度放大少數 quiet names。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/delay_walkforward_oos_sector_stress.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/delay_walkforward_oos_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_24_delay_walkforward_oos_sector_stress_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
