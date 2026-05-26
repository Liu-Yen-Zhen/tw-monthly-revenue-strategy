# Phase 3.22 exact-timing robustness: remove-winners and sector survival

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because Phase 3.21 found S1/quiet-boost did not collapse under 1–3 trading-day execution delay, therefore the next question is whether that resilience survives when the largest winners or the dominant electronics/semiconductor exposure are removed. If it fails these gates, delay robustness is a narrative support, not production robustness.

### 前因後果

- Monthly-revenue SUR alpha has repeatedly shown right-tail and Taiwan electronics / semiconductor supply-chain dependence.
- 本輪用 Phase 3.21 的 official-open、1.0% cost、exclude limit-up risk 設定，只檢查 delay=1 與 delay=3，並做 remove-top-5/10/20 winners 與 sector slices。

### 檢查

- Built robustness diagnostics from 872 delay-trade rows; cash months counted=30.
- Top-winner removal ranks trade-level monthly return contribution after variant weights, not raw stock returns.

### 結果：remove top winners

#### equal_s1 | delay=1
- remove_top_0: return=99.78%, Sharpe=1.16, MDD=-26.21%, avg_pos=7.27
- remove_top_5: return=45.27%, Sharpe=0.69, MDD=-26.21%, avg_pos=7.10
- remove_top_10: return=20.81%, Sharpe=0.43, MDD=-30.24%, avg_pos=6.93
- remove_top_20: return=-22.35%, Sharpe=-0.28, MDD=-38.54%, avg_pos=6.60
- top contributors: 3105 穩懋 2025-09 contrib=7.71%; 3260 威剛 2025-08 contrib=7.01%; 5274 信驊 2024-04 contrib=6.91%
#### equal_s1 | delay=3
- remove_top_0: return=123.66%, Sharpe=1.39, MDD=-19.38%, avg_pos=7.27
- remove_top_5: return=60.22%, Sharpe=0.87, MDD=-25.18%, avg_pos=7.10
- remove_top_10: return=26.88%, Sharpe=0.52, MDD=-25.18%, avg_pos=6.93
- remove_top_20: return=-6.63%, Sharpe=-0.04, MDD=-30.00%, avg_pos=6.60
- top contributors: 3105 穩懋 2025-09 contrib=8.22%; 8086 宏捷科 2023-07 contrib=7.08%; 3131 弘塑 2025-04 contrib=6.53%
#### boost_quiet_no_large_black_150 | delay=1
- remove_top_0: return=111.91%, Sharpe=1.24, MDD=-24.86%, avg_pos=7.27
- remove_top_5: return=53.89%, Sharpe=0.77, MDD=-30.32%, avg_pos=7.10
- remove_top_10: return=23.14%, Sharpe=0.45, MDD=-30.32%, avg_pos=6.93
- remove_top_20: return=-20.88%, Sharpe=-0.24, MDD=-37.00%, avg_pos=6.60
- top contributors: 3105 穩懋 2025-09 contrib=7.71%; 3260 威剛 2025-08 contrib=7.01%; 6683 雍智科技 2024-11 contrib=6.82%
#### boost_quiet_no_large_black_150 | delay=3
- remove_top_0: return=133.98%, Sharpe=1.45, MDD=-18.33%, avg_pos=7.27
- remove_top_5: return=63.32%, Sharpe=0.87, MDD=-26.14%, avg_pos=7.10
- remove_top_10: return=30.38%, Sharpe=0.57, MDD=-26.14%, avg_pos=6.93
- remove_top_20: return=-7.90%, Sharpe=-0.05, MDD=-31.01%, avg_pos=6.60
- top contributors: 6683 雍智科技 2024-11 contrib=8.67%; 3105 穩懋 2025-09 contrib=8.22%; 8086 宏捷科 2023-07 contrib=6.44%

### 結果：sector survival

#### equal_s1 | delay=1
- all: return=99.78%, Sharpe=1.16, MDD=-26.21%, active=29/30, avg_pos=7.27
- electronics_only: return=174.49%, Sharpe=1.37, MDD=-28.73%, active=29/30, avg_pos=6.03
- non_electronics: return=38.49%, Sharpe=0.68, MDD=-10.24%, active=22/30, avg_pos=1.23
- semiconductor_only: return=396.12%, Sharpe=2.02, MDD=-22.75%, active=27/30, avg_pos=2.37
- no_semiconductor: return=15.00%, Sharpe=0.34, MDD=-33.14%, active=28/30, avg_pos=4.90
#### equal_s1 | delay=3
- all: return=123.66%, Sharpe=1.39, MDD=-19.38%, active=29/30, avg_pos=7.27
- electronics_only: return=192.36%, Sharpe=1.48, MDD=-23.05%, active=29/30, avg_pos=6.03
- non_electronics: return=116.27%, Sharpe=1.23, MDD=-18.08%, active=22/30, avg_pos=1.23
- semiconductor_only: return=366.24%, Sharpe=1.86, MDD=-18.94%, active=27/30, avg_pos=2.37
- no_semiconductor: return=32.09%, Sharpe=0.56, MDD=-28.72%, active=28/30, avg_pos=4.90
#### boost_quiet_no_large_black_150 | delay=1
- all: return=111.91%, Sharpe=1.24, MDD=-24.86%, active=29/30, avg_pos=7.27
- electronics_only: return=177.89%, Sharpe=1.39, MDD=-28.11%, active=29/30, avg_pos=6.03
- non_electronics: return=38.65%, Sharpe=0.68, MDD=-10.24%, active=22/30, avg_pos=1.23
- semiconductor_only: return=429.21%, Sharpe=2.08, MDD=-22.75%, active=27/30, avg_pos=2.37
- no_semiconductor: return=16.67%, Sharpe=0.36, MDD=-33.12%, active=28/30, avg_pos=4.90
#### boost_quiet_no_large_black_150 | delay=3
- all: return=133.98%, Sharpe=1.45, MDD=-18.33%, active=29/30, avg_pos=7.27
- electronics_only: return=192.52%, Sharpe=1.50, MDD=-22.75%, active=29/30, avg_pos=6.03
- non_electronics: return=115.45%, Sharpe=1.22, MDD=-18.08%, active=22/30, avg_pos=1.23
- semiconductor_only: return=410.61%, Sharpe=1.96, MDD=-18.94%, active=27/30, avg_pos=2.37
- no_semiconductor: return=30.43%, Sharpe=0.54, MDD=-29.92%, active=28/30, avg_pos=4.90

### 修正與結論

- 修正了什麼：Phase 3.21 只看 timing delay 後的 headline return/Sharpe；本輪加入 remove-winner 與 sector survival，避免把少數 right-tail winners 誤讀成 robust exact-timing edge。
- 為什麼先前不夠好：延後進場不崩潰仍可能只是幾筆大贏家或半導體供應鏈 exposure 撐住。
- 修正後結論是否改變：不改變 promotion 結論。quiet boost delay=1 remove-top-10 後為 `23.14%` / Sharpe `0.45`；delay=3 remove-top-10 後為 `30.38%` / Sharpe `0.57`。non-electronics delay=1 為 `38.65%` / Sharpe `0.68`，no-semiconductor delay=1 為 `16.67%` / Sharpe `0.36`。因此 timing resilience 可作為 S1 narrative support，但仍不是 industry-survivable promotion。

### 缺陷

- Remove-winner contribution uses monthly weighted contribution proxy；真實 portfolio PnL attribution with overlapping holdings / cash drag still simplified。
- Sector classifications are current/static labels, not fully historical；semiconductor supply-chain names outside the formal semiconductor industry may still dominate。
- Still no exact company announcement timestamp or order-book fill evidence。

### 下一步

1. Exact timestamp sourcing remains the highest-priority gate.
2. If delay>=2 becomes the realistic timing assumption, rerun Phase 3.20 walk-forward selection under delay=2/3 plus remove-winner penalty.
3. Add historical sector / supply-chain tags to separate formal semiconductor from broader electronics exposure.

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/exact_timing_robustness_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/exact_timing_robustness_sector.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_22_exact_timing_robustness_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
