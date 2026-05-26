# Phase 3.11 Signal-quality search

目標：保留既有好策略，同時改選股訊號與月內權重，尋找更穩健的 Sharpe >2.5。仍是 research-only proxy backtest。

## Preservation rule

- Promising strategy registry: `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
- S1 incumbent 必須留存並作為比較基準，不因新搜尋被覆蓋。

## Search summary

- tested variants: 103680
- promote candidates: 0
- retained candidates including incumbent: 4
- best variant: `incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|seminone|sl8_trail12|20|equal|liq50m`
- best Sharpe=2.40, return=167.51%, MDD=-7.92%, remove5 Sharpe=1.77

## Top 25 by Sharpe

- incumbent｜Sharpe=2.40, return=167.51%, MDD=-7.92%, trainS=1.86, testS=3.12, rm5S=1.77, rm10S=1.41, avgPos=7.52, top5share=21.32%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|seminone|sl8_trail12|20|equal|liq50m`
- retain_candidate｜Sharpe=2.40, return=167.51%, MDD=-7.92%, trainS=1.86, testS=3.12, rm5S=1.77, rm10S=1.41, avgPos=7.52, top5share=21.32%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|semi3|sl8_trail12|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.34, return=170.98%, MDD=-8.20%, trainS=1.63, testS=3.36, rm5S=1.75, rm10S=1.35, avgPos=7.66, top5share=20.42%｜`underreaction_quality|sur3_high_no_high_mom|top8|ind4|seminone|sl8_trail12|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.32, return=188.86%, MDD=-10.91%, trainS=1.72, testS=3.29, rm5S=1.64, rm10S=1.21, avgPos=6.90, top5share=26.37%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind4|seminone|trail10|20|equal|liq100m`
- rejected_for_now｜Sharpe=2.30, return=158.89%, MDD=-9.06%, trainS=1.69, testS=3.12, rm5S=1.68, rm10S=1.32, avgPos=7.52, top5share=20.78%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind4|semi3|sl8_trail12|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.29, return=164.96%, MDD=-11.51%, trainS=1.60, testS=3.32, rm5S=1.59, rm10S=1.25, avgPos=7.52, top5share=22.41%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|seminone|trail10|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.29, return=164.96%, MDD=-11.51%, trainS=1.60, testS=3.32, rm5S=1.59, rm10S=1.25, avgPos=7.52, top5share=22.41%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|semi3|trail10|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.25, return=151.17%, MDD=-8.70%, trainS=1.74, testS=2.92, rm5S=1.59, rm10S=1.29, avgPos=7.24, top5share=21.17%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind2|seminone|sl8_trail12|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.25, return=151.17%, MDD=-8.70%, trainS=1.74, testS=2.92, rm5S=1.59, rm10S=1.29, avgPos=7.24, top5share=21.17%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind2|semi2|sl8_trail12|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.25, return=151.17%, MDD=-8.70%, trainS=1.74, testS=2.92, rm5S=1.59, rm10S=1.29, avgPos=7.24, top5share=21.17%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind2|semi3|sl8_trail12|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.23, return=152.33%, MDD=-8.68%, trainS=1.76, testS=2.83, rm5S=1.63, rm10S=1.33, avgPos=7.31, top5share=21.11%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|semi2|sl8_trail12|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.23, return=190.19%, MDD=-10.91%, trainS=1.55, testS=3.47, rm5S=1.58, rm10S=1.07, avgPos=6.66, top5share=27.24%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind4|semi3|trail10|20|equal|liq100m`
- rejected_for_now｜Sharpe=2.23, return=234.17%, MDD=-13.88%, trainS=1.70, testS=2.96, rm5S=1.71, rm10S=1.51, avgPos=6.90, top5share=23.73%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind4|seminone|trail15|20|equal|liq100m`
- rejected_for_now｜Sharpe=2.23, return=205.06%, MDD=-12.41%, trainS=1.69, testS=2.95, rm5S=1.40, rm10S=1.00, avgPos=5.76, top5share=23.61%｜`right_tail_confirmation|sur3_high_no_high_mom|top6|ind2|seminone|trail10|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.23, return=205.06%, MDD=-12.41%, trainS=1.69, testS=2.95, rm5S=1.40, rm10S=1.00, avgPos=5.76, top5share=23.61%｜`right_tail_confirmation|sur3_high_no_high_mom|top6|ind2|semi2|trail10|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.23, return=205.06%, MDD=-12.41%, trainS=1.69, testS=2.95, rm5S=1.40, rm10S=1.00, avgPos=5.76, top5share=23.61%｜`right_tail_confirmation|sur3_high_no_high_mom|top6|ind2|semi3|trail10|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.23, return=165.62%, MDD=-12.07%, trainS=1.34, testS=3.62, rm5S=1.58, rm10S=1.21, avgPos=7.66, top5share=21.56%｜`underreaction_quality|sur3_high_no_high_mom|top8|ind4|seminone|trail10|20|equal|liq50m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|seminone|trail15|20|score_linear|liq100m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|seminone|trail15|20|score_x_liquidity|liq100m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|seminone|trail15|20|score_x_abturn|liq100m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|semi2|trail15|20|score_linear|liq100m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|semi2|trail15|20|score_x_liquidity|liq100m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|semi2|trail15|20|score_x_abturn|liq100m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|semi3|trail15|20|score_linear|liq100m`
- rejected_for_now｜Sharpe=2.22, return=316.96%, MDD=-15.25%, trainS=1.48, testS=3.43, rm5S=1.77, rm10S=1.37, avgPos=6.24, top5share=28.33%｜`right_tail_confirmation|sur3_high_no_high_mom|top8|ind2|semi3|trail15|20|score_x_liquidity|liq100m`

## Retained / marked variants

- **incumbent**｜Sharpe=2.40, rm5S=1.77, return=167.51%, MDD=-7.92%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|seminone|sl8_trail12|20|equal|liq50m`
- **retain_candidate**｜Sharpe=2.40, rm5S=1.77, return=167.51%, MDD=-7.92%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|semi3|sl8_trail12|20|equal|liq50m`
- **robustness_candidate**｜Sharpe=2.21, rm5S=1.81, return=250.55%, MDD=-13.88%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|seminone|trail15|20|equal|liq100m`
- **robustness_candidate**｜Sharpe=2.21, rm5S=1.81, return=250.55%, MDD=-13.88%｜`incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|semi3|trail15|20|equal|liq100m`

## Interpretation

- `promote_candidate` 需要 Sharpe>=2.5、remove5 Sharpe>=1.8、train Sharpe>=1.5、平均持股>=5。
- `retain_candidate` 表示接近或改善但尚未可升級。
- 若新訊號只提高 raw Sharpe 但 remove-winners 更差，仍不升級。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/signal_quality_search_results.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/signal_quality_search_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/signal_quality_search_top_trades.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/signal_quality_search_summary.json`
