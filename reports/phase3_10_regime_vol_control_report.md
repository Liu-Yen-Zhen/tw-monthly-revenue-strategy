# Phase 3.10 Regime filter + volatility control

目標：以 Phase 3.9 最佳候選為基準，測試簡單 ex-ante regime filter 與 portfolio exposure control 是否能把 monthly Sharpe proxy 穩健推到 >2.5。仍是 research-only proxy backtest，不是交易建議。

## Baseline

- variant: `all_months|full`
- return=167.51%, ann=50.25%, Sharpe=2.40, MDD=-7.92%, win=79.31%
- train Sharpe=1.86, 2025 test Sharpe=3.12

## Search result

- tested variants: 90
- raw Sharpe > 2.5 variants: 0
- stricter robust candidates: 0
- best variant: `all_months|full` with Sharpe=2.40, return=167.51%, MDD=-7.92%

## Top 20 variants

- Sharpe=2.40, return=167.51%, MDD=-7.92%, active=29/29, avgExp=1.00, maxExp=1.00, trainS=1.86, testS=3.12｜`all_months|full`
- Sharpe=2.32, return=148.73%, MDD=-7.92%, active=29/29, avgExp=0.93, maxExp=1.00, trainS=1.82, testS=2.97｜`all_months|targetvol_5_cap1`
- Sharpe=2.28, return=132.51%, MDD=-7.38%, active=29/29, avgExp=0.87, maxExp=1.00, trainS=1.81, testS=2.90｜`all_months|targetvol_4_cap1`
- Sharpe=2.28, return=113.48%, MDD=-6.52%, active=29/29, avgExp=0.79, maxExp=1.00, trainS=1.82, testS=2.87｜`all_months|targetvol_3_cap1`
- Sharpe=2.28, return=154.99%, MDD=-7.92%, active=29/29, avgExp=0.91, maxExp=1.00, trainS=1.66, testS=3.12｜`all_months|dd_degear_5pct`
- Sharpe=2.21, return=170.89%, MDD=-9.00%, active=29/29, avgExp=1.10, maxExp=1.50, trainS=1.70, testS=2.85｜`all_months|targetvol_6_cap15`
- Sharpe=2.21, return=114.00%, MDD=-7.92%, active=29/29, avgExp=0.90, maxExp=1.00, trainS=1.58, testS=3.06｜`all_months|half_when_prev_loss`
- Sharpe=2.17, return=127.87%, MDD=-7.74%, active=29/29, avgExp=0.92, maxExp=1.50, trainS=1.70, testS=2.76｜`all_months|targetvol_4_cap15`
- Sharpe=2.17, return=147.34%, MDD=-8.50%, active=29/29, avgExp=1.02, maxExp=1.50, trainS=1.68, testS=2.79｜`all_months|targetvol_5_cap15`
- Sharpe=1.91, return=102.51%, MDD=-7.92%, active=26/29, avgExp=0.90, maxExp=1.00, trainS=1.61, testS=2.27｜`mkt20_or_60_pos|full`
- Sharpe=1.88, return=99.52%, MDD=-7.92%, active=26/29, avgExp=0.87, maxExp=1.00, trainS=1.57, testS=2.23｜`mkt20_or_60_pos|targetvol_5_cap1`
- Sharpe=1.84, return=89.32%, MDD=-7.27%, active=26/29, avgExp=0.80, maxExp=1.00, trainS=1.54, testS=2.19｜`mkt20_or_60_pos|targetvol_4_cap1`
- Sharpe=1.83, return=77.84%, MDD=-6.30%, active=26/29, avgExp=0.70, maxExp=1.00, trainS=1.58, testS=2.11｜`mkt20_or_60_pos|targetvol_3_cap1`
- Sharpe=1.79, return=93.03%, MDD=-7.92%, active=26/29, avgExp=0.81, maxExp=1.00, trainS=1.41, testS=2.27｜`mkt20_or_60_pos|dd_degear_5pct`
- Sharpe=1.77, return=112.51%, MDD=-8.83%, active=26/29, avgExp=1.00, maxExp=1.50, trainS=1.48, testS=2.09｜`mkt20_or_60_pos|targetvol_6_cap15`
- Sharpe=1.76, return=68.68%, MDD=-3.24%, active=15/29, avgExp=0.51, maxExp=1.50, trainS=1.35, testS=2.25｜`mkt60_pos_and_semi_rel60_pos|targetvol_4_cap15`
- Sharpe=1.75, return=68.54%, MDD=-3.29%, active=15/29, avgExp=0.52, maxExp=1.00, trainS=1.33, testS=2.27｜`mkt60_pos_and_semi_rel60_pos|full`
- Sharpe=1.75, return=68.54%, MDD=-3.29%, active=15/29, avgExp=0.52, maxExp=1.00, trainS=1.33, testS=2.27｜`mkt60_pos_and_semi_rel60_pos|dd_degear_5pct`
- Sharpe=1.75, return=86.71%, MDD=-7.33%, active=26/29, avgExp=0.83, maxExp=1.50, trainS=1.53, testS=1.98｜`mkt20_or_60_pos|targetvol_4_cap15`
- Sharpe=1.75, return=68.32%, MDD=-3.29%, active=15/29, avgExp=0.52, maxExp=1.00, trainS=1.33, testS=2.27｜`mkt60_pos_and_semi_rel60_pos|targetvol_5_cap1`

## Strict robust candidates

- 沒有通過較嚴格條件的 robust Sharpe > 2.5 候選。

## Interpretation rules

- regime filter 跳過月份以 0% cash return 計入，避免只計 active months 而高估 Sharpe。
- 若 Sharpe >2.5 只由低 active_ratio 或高 leverage cap 產生，不能視為穩健達標。
- target-vol 使用歷史已實現策略月報酬，屬 portfolio-level exposure proxy；不是實際融資或槓桿交易建議。
- 下一步若有候選，仍需 walk-forward、成本加倍、no-electronics/no-semiconductor stress、OHLC/漲跌停可成交性檢查。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/regime_vol_control_results.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/regime_vol_control_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/regime_vol_control_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/regime_vol_control_summary.json`
