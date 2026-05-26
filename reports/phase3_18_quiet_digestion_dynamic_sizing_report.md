# Phase 3.18 S1 + quiet digestion dynamic sizing

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 本輪假說

Phase 3.17 顯示 quiet digestion 作為 standalone slice 雖然報酬高，但樣本少且 remove-winner 脆弱。因此本輪不把它當替代策略，而是測它能否作為 S1 fixed-20 proxy 的動態加權 / 風險閘門：quiet digestion 代表延遲再定價，應可小幅加權；large black K 代表 failed repricing / 供給壓力，應降權或排除。

## Signal coverage

- S1 selected signals/trades = 226 / 218
- quiet_core signals = 30; large_black signals = 30; quiet_and_large_black = 3
- abnormal turnover low tercile = 0.7705; entry range low tercile = 0.0290; body high tercile = 0.6559

## Variant summary（20D fixed exit, inactive months counted as cash）

- `equal_s1`: return=161.94%, Sharpe=1.55, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=13.33%, black_w=12.84%
- `boost_quiet_125`: return=166.95%, Sharpe=1.58, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=15.81%, black_w=12.75%
- `boost_quiet_150`: return=171.60%, Sharpe=1.61, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=18.05%, black_w=12.66%
- `boost_quiet_200`: return=179.93%, Sharpe=1.65, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=21.98%, black_w=12.51%
- `boost_quiet_no_large_black_150`: return=174.35%, Sharpe=1.62, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=17.61%, black_w=12.22%
- `downweight_large_black_050`: return=150.86%, Sharpe=1.47, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=13.57%, black_w=7.79%
- `exclude_large_black`: return=124.47%, Sharpe=1.26, MDD=-22.17%, active=29/30, avg_pos=6.30, quiet_w=13.97%, black_w=0.00%
- `boost_quiet150_down_black050`: return=163.59%, Sharpe=1.55, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=18.34%, black_w=7.66%
- `boost_quiet150_exclude_black`: return=141.08%, Sharpe=1.36, MDD=-21.92%, active=29/30, avg_pos=6.30, quiet_w=18.74%, black_w=0.00%
- `boost_quiet_liq100_150`: return=168.03%, Sharpe=1.58, MDD=-21.16%, active=29/30, avg_pos=7.27, quiet_w=16.26%, black_w=12.76%

## Remove-winner stress（focus variants）

### equal_s1
- remove 0: return=161.94%, Sharpe=1.55, MDD=-21.16%
- remove 3: return=120.74%, Sharpe=1.32, MDD=-21.16%
- remove 5: return=97.08%, Sharpe=1.16, MDD=-21.16%
- remove 10: return=67.60%, Sharpe=0.96, MDD=-21.16%
- remove 15: return=43.45%, Sharpe=0.74, MDD=-21.16%
- remove 20: return=16.27%, Sharpe=0.38, MDD=-25.64%
### boost_quiet_150
- remove 0: return=171.60%, Sharpe=1.61, MDD=-21.16%
- remove 3: return=130.14%, Sharpe=1.38, MDD=-21.16%
- remove 5: return=103.87%, Sharpe=1.20, MDD=-21.16%
- remove 10: return=75.50%, Sharpe=1.03, MDD=-21.16%
- remove 15: return=48.49%, Sharpe=0.80, MDD=-21.16%
- remove 20: return=22.00%, Sharpe=0.47, MDD=-25.41%
### boost_quiet_no_large_black_150
- remove 0: return=174.35%, Sharpe=1.62, MDD=-21.16%
- remove 3: return=132.47%, Sharpe=1.39, MDD=-21.16%
- remove 5: return=105.93%, Sharpe=1.22, MDD=-21.16%
- remove 10: return=76.97%, Sharpe=1.04, MDD=-21.16%
- remove 15: return=49.73%, Sharpe=0.82, MDD=-21.16%
- remove 20: return=22.56%, Sharpe=0.48, MDD=-25.12%
### exclude_large_black
- remove 0: return=124.47%, Sharpe=1.26, MDD=-22.17%
- remove 3: return=105.28%, Sharpe=1.18, MDD=-22.17%
- remove 5: return=81.35%, Sharpe=1.00, MDD=-22.93%
- remove 10: return=53.13%, Sharpe=0.80, MDD=-22.93%
- remove 15: return=31.75%, Sharpe=0.58, MDD=-22.93%
- remove 20: return=3.85%, Sharpe=0.19, MDD=-28.75%
### boost_quiet150_exclude_black
- remove 0: return=141.08%, Sharpe=1.36, MDD=-21.92%
- remove 3: return=121.67%, Sharpe=1.29, MDD=-21.92%
- remove 5: return=93.90%, Sharpe=1.09, MDD=-22.34%
- remove 10: return=65.44%, Sharpe=0.91, MDD=-22.34%
- remove 15: return=38.67%, Sharpe=0.67, MDD=-22.34%
- remove 20: return=10.88%, Sharpe=0.30, MDD=-27.68%
### boost_quiet_liq100_150
- remove 0: return=168.03%, Sharpe=1.58, MDD=-21.16%
- remove 3: return=127.11%, Sharpe=1.35, MDD=-21.16%
- remove 5: return=100.27%, Sharpe=1.17, MDD=-21.16%
- remove 10: return=71.11%, Sharpe=0.98, MDD=-21.16%
- remove 15: return=45.91%, Sharpe=0.77, MDD=-21.16%
- remove 20: return=19.42%, Sharpe=0.43, MDD=-26.15%

## Year split

### equal_s1
- 2023: return=36.58%, Sharpe=3.41, MDD=-3.29%, active=6/6
- 2024: return=22.45%, Sharpe=1.03, MDD=-15.24%, active=12/12
- 2025: return=56.62%, Sharpe=1.51, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### boost_quiet_150
- 2023: return=38.16%, Sharpe=3.38, MDD=-3.30%, active=6/6
- 2024: return=24.95%, Sharpe=1.14, MDD=-14.50%, active=12/12
- 2025: return=57.34%, Sharpe=1.53, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### boost_quiet_no_large_black_150
- 2023: return=38.01%, Sharpe=3.36, MDD=-3.30%, active=6/6
- 2024: return=25.65%, Sharpe=1.17, MDD=-14.50%, active=12/12
- 2025: return=58.21%, Sharpe=1.54, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### exclude_large_black
- 2023: return=25.90%, Sharpe=2.78, MDD=-4.00%, active=6/6
- 2024: return=24.91%, Sharpe=1.08, MDD=-15.86%, active=12/12
- 2025: return=42.74%, Sharpe=1.14, MDD=-22.17%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### boost_quiet150_exclude_black
- 2023: return=29.19%, Sharpe=2.87, MDD=-3.96%, active=6/6
- 2024: return=28.64%, Sharpe=1.25, MDD=-14.95%, active=12/12
- 2025: return=45.06%, Sharpe=1.18, MDD=-21.92%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### boost_quiet_liq100_150
- 2023: return=37.08%, Sharpe=3.40, MDD=-3.30%, active=6/6
- 2024: return=23.72%, Sharpe=1.07, MDD=-14.87%, active=12/12
- 2025: return=58.05%, Sharpe=1.54, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1

## Interpretation

- Promotion gate: dynamic sizing should improve Sharpe or MDD without increasing top-winner dependence. A small full-sample improvement is not enough.
- If quiet boosts improve return but worsen remove-winner results, quiet digestion is still a right-tail amplifier rather than robust sizing information.
- If excluding large black K improves MDD and remove-winner stability, it can be retained as a risk gate candidate. If it only lifts full-sample return, keep it diagnostic.
- This remains fixed-20 daily OHLC proxy research, not executable stop/limit/open-fill simulation.

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_dynamic_sizing_variants.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_dynamic_sizing_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_dynamic_sizing_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_dynamic_sizing_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_dynamic_sizing_exposure.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_18_quiet_digestion_dynamic_sizing_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/charts/phase3_18_dynamic_sizing_nav_zh.png`
