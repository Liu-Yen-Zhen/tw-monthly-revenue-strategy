# Phase 3.17 quiet digestion deep dive

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 本輪假說

月營收 SUR 強、但進場前成交值偏低且 entry day 日內區間偏窄，可能代表市場尚未擁擠、消息仍在被消化；後續 20D 若由延遲再定價推動，應該比單純低成交值或單純窄幅 K 線更穩。反過來，若效果只存在少數半導體大贏家或低流動性標的，則它只是 winner concentration / liquidity artifact。

## Thresholds and coverage

- abnormal turnover low/high tercile = 0.7705 / 1.3921
- entry range low tercile = 0.0290; upper-shadow high tercile = 0.3457; close-location low tercile = 0.2222; body high tercile = 0.6559
- scored rows with entry OHLC matched = 2002/2002

## Variant summary（20D fixed exit, inactive months counted as cash）

- `s1_baseline`: return=161.94%, Sharpe=1.55, MDD=-21.16%, active=29/30, avg_pos=7.27, trades=218, trade_win=52.29%
- `vol_low_only`: return=138.74%, Sharpe=1.21, MDD=-28.76%, active=29/30, avg_pos=3.93, trades=118, trade_win=55.08%
- `narrow_only`: return=94.69%, Sharpe=1.02, MDD=-18.63%, active=28/30, avg_pos=4.17, trades=125, trade_win=50.40%
- `quiet_core`: return=312.56%, Sharpe=1.77, MDD=-13.13%, active=26/30, avg_pos=1.87, trades=56, trade_win=53.57%
- `quiet_electronics`: return=213.97%, Sharpe=1.48, MDD=-13.99%, active=25/30, avg_pos=1.60, trades=48, trade_win=52.08%
- `quiet_non_electronics`: return=31.92%, Sharpe=0.68, MDD=-7.10%, active=7/30, avg_pos=0.27, trades=8, trade_win=62.50%
- `quiet_semiconductor`: return=185.13%, Sharpe=1.22, MDD=-14.51%, active=17/30, avg_pos=0.70, trades=21, trade_win=52.38%
- `quiet_no_semiconductor`: return=116.17%, Sharpe=1.10, MDD=-12.66%, active=20/30, avg_pos=1.17, trades=35, trade_win=54.29%
- `quiet_liq100m`: return=172.99%, Sharpe=1.38, MDD=-14.15%, active=20/30, avg_pos=1.13, trades=34, trade_win=55.88%
- `quiet_pullback20`: return=89.06%, Sharpe=1.01, MDD=-21.77%, active=19/30, avg_pos=1.07, trades=32, trade_win=53.12%
- `quiet_no_supply`: return=97.03%, Sharpe=1.20, MDD=-14.47%, active=19/30, avg_pos=1.03, trades=31, trade_win=54.84%
- `quiet_supply_pressure`: return=77.29%, Sharpe=0.83, MDD=-26.96%, active=18/30, avg_pos=0.87, trades=26, trade_win=53.85%
- `quiet_no_large_black`: return=348.73%, Sharpe=1.87, MDD=-12.08%, active=25/30, avg_pos=1.67, trades=50, trade_win=56.00%
- `quiet_large_black`: return=1.92%, Sharpe=0.15, MDD=-7.07%, active=6/30, avg_pos=0.23, trades=7, trade_win=42.86%

## Remove-winner stress（核心 variants）

### s1_baseline
- remove 0: return=161.94%, Sharpe=1.55, MDD=-21.16%, trades=218
- remove 3: return=120.74%, Sharpe=1.32, MDD=-21.16%, trades=215
- remove 5: return=97.08%, Sharpe=1.16, MDD=-21.16%, trades=213
- remove 10: return=67.60%, Sharpe=0.96, MDD=-21.16%, trades=208
- remove 15: return=43.45%, Sharpe=0.74, MDD=-21.16%, trades=203
- remove 20: return=16.27%, Sharpe=0.38, MDD=-25.64%, trades=198
### quiet_core
- remove 0: return=312.56%, Sharpe=1.77, MDD=-13.13%, trades=56
- remove 3: return=162.47%, Sharpe=1.39, MDD=-19.49%, trades=53
- remove 5: return=73.21%, Sharpe=0.99, MDD=-25.20%, trades=51
- remove 10: return=-16.71%, Sharpe=-0.51, MDD=-26.12%, trades=46
- remove 15: return=-33.07%, Sharpe=-1.17, MDD=-36.23%, trades=41
- remove 20: return=-41.23%, Sharpe=-1.57, MDD=-41.23%, trades=36
### quiet_electronics
- remove 0: return=213.97%, Sharpe=1.48, MDD=-13.99%, trades=48
- remove 3: return=99.75%, Sharpe=1.07, MDD=-19.27%, trades=45
- remove 5: return=40.94%, Sharpe=0.66, MDD=-27.38%, trades=43
- remove 10: return=-26.29%, Sharpe=-0.69, MDD=-28.70%, trades=38
- remove 15: return=-38.43%, Sharpe=-1.20, MDD=-38.80%, trades=33
- remove 20: return=-46.24%, Sharpe=-1.65, MDD=-46.24%, trades=28
### quiet_semiconductor
- remove 0: return=185.13%, Sharpe=1.22, MDD=-14.51%, trades=21
- remove 3: return=31.11%, Sharpe=0.54, MDD=-22.49%, trades=18
- remove 5: return=-6.18%, Sharpe=-0.02, MDD=-22.49%, trades=16
- remove 10: return=-40.36%, Sharpe=-1.47, MDD=-40.36%, trades=11
- remove 15: return=-43.00%, Sharpe=-1.48, MDD=-43.00%, trades=6
- remove 20: return=-14.51%, Sharpe=-0.63, MDD=-14.51%, trades=1
### quiet_liq100m
- remove 0: return=172.99%, Sharpe=1.38, MDD=-14.15%, trades=34
- remove 3: return=73.68%, Sharpe=0.95, MDD=-19.95%, trades=31
- remove 5: return=22.55%, Sharpe=0.48, MDD=-24.94%, trades=29
- remove 10: return=-27.29%, Sharpe=-0.90, MDD=-31.48%, trades=24
- remove 15: return=-37.45%, Sharpe=-1.51, MDD=-37.56%, trades=19
- remove 20: return=-42.39%, Sharpe=-1.71, MDD=-42.39%, trades=14
### quiet_no_large_black
- remove 0: return=348.73%, Sharpe=1.87, MDD=-12.08%, trades=50
- remove 3: return=185.48%, Sharpe=1.50, MDD=-12.33%, trades=47
- remove 5: return=88.40%, Sharpe=1.12, MDD=-18.56%, trades=45
- remove 10: return=-9.40%, Sharpe=-0.22, MDD=-19.55%, trades=40
- remove 15: return=-28.85%, Sharpe=-0.99, MDD=-33.95%, trades=35
- remove 20: return=-40.81%, Sharpe=-1.76, MDD=-40.81%, trades=30

## Year split（核心 variants）

### s1_baseline
- 2023: return=36.58%, Sharpe=3.41, MDD=-3.29%, active=6/6
- 2024: return=22.45%, Sharpe=1.03, MDD=-15.24%, active=12/12
- 2025: return=56.62%, Sharpe=1.51, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### quiet_core
- 2023: return=62.68%, Sharpe=2.81, MDD=-1.49%, active=6/6
- 2024: return=36.26%, Sharpe=1.09, MDD=-13.13%, active=12/12
- 2025: return=86.11%, Sharpe=1.89, MDD=-3.68%, active=8/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### quiet_electronics
- 2023: return=27.52%, Sharpe=1.70, MDD=-9.07%, active=5/6
- 2024: return=32.29%, Sharpe=0.95, MDD=-13.99%, active=12/12
- 2025: return=86.11%, Sharpe=1.89, MDD=-3.68%, active=8/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### quiet_semiconductor
- 2023: return=17.01%, Sharpe=1.11, MDD=-9.07%, active=3/6
- 2024: return=72.39%, Sharpe=1.34, MDD=-12.08%, active=10/12
- 2025: return=41.36%, Sharpe=1.12, MDD=-14.51%, active=4/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### quiet_liq100m
- 2023: return=33.57%, Sharpe=2.66, MDD=0.00%, active=5/6
- 2024: return=21.26%, Sharpe=0.73, MDD=-14.15%, active=10/12
- 2025: return=68.55%, Sharpe=1.63, MDD=-5.05%, active=5/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### quiet_no_large_black
- 2023: return=54.78%, Sharpe=2.36, MDD=-5.03%, active=6/6
- 2024: return=48.37%, Sharpe=1.36, MDD=-12.08%, active=12/12
- 2025: return=95.40%, Sharpe=2.07, MDD=-1.81%, active=7/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1

## Position-count / concentration variants

- `quiet_top4`: return=307.28%, Sharpe=1.75, MDD=-13.89%, trades=53, remove5 Sharpe=0.97
- `quiet_top6`: return=312.56%, Sharpe=1.77, MDD=-13.13%, trades=56, remove5 Sharpe=0.99
- `quiet_core`: return=312.56%, Sharpe=1.77, MDD=-13.13%, trades=56, remove5 Sharpe=0.99
- `quiet_top12`: return=312.56%, Sharpe=1.77, MDD=-13.13%, trades=56, remove5 Sharpe=0.99
- `quiet_indcap1`: return=327.40%, Sharpe=1.80, MDD=-14.15%, trades=47, remove5 Sharpe=1.03
- `quiet_indcap2`: return=310.96%, Sharpe=1.76, MDD=-13.46%, trades=55, remove5 Sharpe=0.98

## Interpretation

- Promotion gate: quiet digestion must outperform S1 on risk-adjusted return or drawdown **and** survive remove-winner / sector / liquidity checks. If not, it remains a sizing/filter hypothesis, not a replacement strategy.
- If `vol_low_only` and `narrow_only` are weaker than `quiet_core`, the interaction has a cleaner causal reading: low attention + narrow digestion is more informative than either condition alone.
- If `quiet_semiconductor` or `quiet_electronics` dominate while `quiet_non_electronics` is sparse/weak, the edge is still supply-chain regime-specific.
- If `quiet_liq100m` collapses, quiet digestion may be a low-liquidity artifact; if it survives, it is more institutionally credible.
- Daily OHLC still cannot model exact announcement timestamp, opening fill, limit-up queue priority, or intraday breakout.

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_deep_dive_variants.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_deep_dive_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_deep_dive_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_deep_dive_top_contributors.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/quiet_digestion_deep_dive_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_17_quiet_digestion_deep_dive_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/charts/phase3_17_quiet_digestion_nav_zh.png`
