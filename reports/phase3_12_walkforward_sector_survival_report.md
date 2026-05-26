# Phase 3.12 Walk-forward OOS + sector survival stress

目標：把 S1 portfolio-grade v0.1 往業界可存活策略推進。這一階段檢查：用過去資料選參數是否能在未來 OOS 存活，以及績效是否過度依賴電子/半導體。仍是 research-only proxy backtest。

## Walk-forward OOS result

- train2023_test2024 / walkforward_selected：test Sharpe=1.07, test return=27.14%, test MDD=-16.99%, test rm5S=0.15, avg positions=7.17
  variant: `sur3_high_no_high_mom|liq100m|top8|ind4|seminone|fixed|20D`
- train2023_test2024 / incumbent_fixed：test Sharpe=1.55, test return=27.46%, test MDD=-7.92%, test rm5S=0.28, avg positions=7.75
  variant: `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D`
- train2023_2024_test2025 / walkforward_selected：test Sharpe=1.63, test return=63.12%, test MDD=-19.11%, test rm5S=1.07, avg positions=12.00
  variant: `base_sur_core|liq50m|top12|ind4|semi3|fixed|20D`
- train2023_2024_test2025 / incumbent_fixed：test Sharpe=3.12, test return=79.39%, test MDD=-4.36%, test rm5S=1.74, avg positions=7.33
  variant: `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D`

## Sector survival stress

- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D` / all：Sharpe=2.40, return=167.51%, MDD=-7.92%, rm5S=1.77, avg positions=7.52
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D` / electronics_only：Sharpe=1.95, return=244.63%, MDD=-9.46%, rm5S=1.16, avg positions=4.62
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D` / non_electronics：Sharpe=1.44, return=92.47%, MDD=-11.91%, rm5S=0.73, avg positions=3.00
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D` / no_semiconductor：Sharpe=1.38, return=80.44%, MDD=-13.82%, rm5S=0.93, avg positions=5.25
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D` / semiconductor_only：Sharpe=2.20, return=313.30%, MDD=-11.54%, rm5S=1.07, avg positions=2.63
- `sur3_high_no_high_mom|liq100m|top8|ind3|seminone|trail15|20D` / all：Sharpe=2.21, return=250.55%, MDD=-13.88%, rm5S=1.81, avg positions=6.66
- `sur3_high_no_high_mom|liq100m|top8|ind3|seminone|trail15|20D` / electronics_only：Sharpe=2.39, return=441.90%, MDD=-16.04%, rm5S=1.79, avg positions=4.52
- `sur3_high_no_high_mom|liq100m|top8|ind3|seminone|trail15|20D` / non_electronics：Sharpe=0.62, return=35.03%, MDD=-18.67%, rm5S=-0.17, avg positions=2.21
- `sur3_high_no_high_mom|liq100m|top8|ind3|seminone|trail15|20D` / no_semiconductor：Sharpe=0.60, return=37.04%, MDD=-30.85%, rm5S=0.17, avg positions=4.31
- `sur3_high_no_high_mom|liq100m|top8|ind3|seminone|trail15|20D` / semiconductor_only：Sharpe=2.23, return=436.16%, MDD=-26.94%, rm5S=1.60, avg positions=2.62
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|fixed|20D` / all：Sharpe=1.58, return=161.94%, MDD=-21.16%, rm5S=1.18, avg positions=7.52
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|fixed|20D` / electronics_only：Sharpe=1.81, return=310.39%, MDD=-21.96%, rm5S=1.23, avg positions=4.62
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|fixed|20D` / non_electronics：Sharpe=0.71, return=49.47%, MDD=-32.76%, rm5S=0.24, avg positions=3.00
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|fixed|20D` / no_semiconductor：Sharpe=0.85, return=61.10%, MDD=-22.80%, rm5S=0.56, avg positions=5.25
- `sur3_high_no_high_mom|liq50m|top8|ind3|seminone|fixed|20D` / semiconductor_only：Sharpe=2.26, return=437.34%, MDD=-24.39%, rm5S=1.53, avg positions=2.63

## Interpretation

- 若 walk-forward selected 不能穩定打敗 fixed incumbent，代表目前參數搜尋仍不適合宣稱為可泛化選模。
- 若 non-electronics / no-semiconductor 大幅衰退，策略應重新定位為電子/AI supply-chain revenue surprise strategy，而非全市場普適 alpha。
- 這一階段仍未處理 exact announcement timestamp、OHLC、漲跌停與成交可得性；那些是下一個 execution-realism gate。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/walkforward_sector_oos.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/walkforward_candidate_pool.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/sector_survival_stress.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/walkforward_oos_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/walkforward_sector_summary.json`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/charts/phase3_12_walkforward_oos_nav_zh.png`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/charts/phase3_12_sector_survival_zh.png`
