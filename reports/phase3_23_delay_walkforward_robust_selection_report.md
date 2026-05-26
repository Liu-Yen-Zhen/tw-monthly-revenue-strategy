# Phase 3.23 delay-aware walk-forward robust-selection gate

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because Phase 3.20 found small OOS gains for quiet dynamic sizing but Phase 3.22 showed severe remove-winner fragility, therefore a more credible sizing/timing rule should be selectable using only prior years after penalizing top-winner dependence and should still beat equal S1 in the next year under delayed official-open execution.

### 前因後果

- Monthly-revenue SUR repricing may persist for several days, but exact timestamp uncertainty means delay=1/2/3 trading days are more honest than assuming perfect first tradability.
- Quiet-digestion boosts may simply overweight the same few OTC electronics winners; selection must therefore include train-only remove-top-5/10 winner stress before evaluating OOS.

### 檢查

- Built delay trades from Phase 3.21: 872 rows; cost=1.0%; official open entry; 20D close exit; possible limit-up non-fill flags excluded.
- Candidate grid: 8 sizing variants × delays [1, 2, 3]; split count=2.
- Selection score = 0.50 × train Sharpe + 0.35 × train remove-top-5 Sharpe + 0.15 × train remove-top-10 Sharpe, with sparse-position / large-MDD penalties.

### 結果

#### train_2023_test_2024
- train-selected robust rule: `boost_quiet_no_large_black_200 | delay=2`; score=1.97
- train base: return=36.32%, Sharpe=2.83, MDD=-3.25%, avg_pos=7.50
- train remove-top-5 / remove-top-10 Sharpe: 2.09 / -1.21
- OOS selected: return=14.73%, Sharpe=0.76, MDD=-15.86%, avg_pos=7.75
- OOS equal_s1 same delay: return=9.42%, Sharpe=0.51; delta return=5.32%, delta Sharpe=0.25
- Reference equal_s1 delay=1 OOS: return=12.91%, Sharpe=0.67

#### train_2023_2024_test_2025
- train-selected robust rule: `boost_quiet_no_large_black_200 | delay=1`; score=1.04
- train base: return=58.52%, Sharpe=1.54, MDD=-14.89%, avg_pos=7.67
- train remove-top-5 / remove-top-10 Sharpe: 0.71 / 0.16
- OOS selected: return=40.50%, Sharpe=1.17, MDD=-23.44%, avg_pos=7.27
- OOS equal_s1 same delay: return=35.45%, Sharpe=1.08; delta return=5.06%, delta Sharpe=0.09
- Reference equal_s1 delay=1 OOS: return=35.45%, Sharpe=1.08

### 修正與結論

- 修正了什麼：Phase 3.20 的 walk-forward selection only optimized train Sharpe under one next-open proxy；本輪把 delay=1/2/3 納入候選，且用 train-only remove-top-5/10 winners 懲罰來降低 right-tail overfit。
- 為什麼先前不夠好：若不懲罰 winner dependence，dynamic sizing 可能只是事後加碼少數大贏家；若只看 delay=1，仍未反映 exact timestamp unknown 的進場延遲風險。
- 修正後結論是否改變：2/2 splits 的 robust-selected rule 在 OOS return 與 Sharpe 同時勝過 same-delay equal S1。即使通過，因樣本只涵蓋 2023–2025 且 Phase 3.22 remove-winner/sector fragility 未解，結論仍是 **research-only sizing/timing hypothesis，不 promotion**；S1 equal remains incumbent。

### 缺陷

- 只有兩個 next-year OOS splits；2026 尚未形成完整年度 OOS。
- Remove-winner penalty 在 train set 上計算，仍是 monthly contribution proxy，不是真實重疊持倉 PnL attribution。
- Current sector/industry labels are static；沒有公司級公告 timestamp、order-book queue、limit-up fill evidence。

### 下一步

1. 尋找/保存 company-level monthly revenue exact announcement timestamps，將 delay proxy 換成真正 data-available timestamp gate。
2. 把 Phase 3.23 selected rules 做 sector/no-semiconductor OOS stress；若只靠 semiconductor-only，不應做 broad strategy promotion。
3. 對 2026 paper-trading log 加入 signal timestamp、planned vs observable entry、limit-up non-fill reason、slippage estimate。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/delay_walkforward_robust_selection_summary.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/delay_walkforward_robust_selection_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/delay_walkforward_robust_selection_contrib.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_23_delay_walkforward_robust_selection_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
