# Phase 3.9 High-Sharpe Search

目標：尋找 Sharpe proxy > 2.5 的短線月營收/SUR 策略。仍是 research-only proxy backtest，不是交易建議。

## 防過擬合規則

- 全期 monthly Sharpe proxy > 2.5 只視為候選，不視為完成。
- 同時檢查 2023-2024 train、2025 test、remove top winners、平均持股數、top contributor concentration。
- 樣本只有 2023-2025，若靠 topN 很小或單一年度/單一大贏家達標，可信度要降級。

## 搜尋結果摘要

- 搜尋組合數：8208
- Sharpe > 2.5 且 months>=24、avg_positions>=3、2025 return>0 的候選數：0

## 全部組合 Sharpe Top 20

- Sharpe=2.40, return=167.51%, MDD=-7.92%, excess=110.28%, trainS=1.86, testS=3.12, avg_pos=7.5｜sur3_high_no_high_mom|liq50m|top8|ind3|seminone｜sl8_trail12 20D｜top5share=21.32%
- Sharpe=2.40, return=167.51%, MDD=-7.92%, excess=110.28%, trainS=1.86, testS=3.12, avg_pos=7.5｜sur3_high_no_high_mom|liq50m|top8|ind3|semi3｜sl8_trail12 20D｜top5share=21.32%
- Sharpe=2.31, return=166.94%, MDD=-11.71%, excess=113.38%, trainS=1.69, testS=3.28, avg_pos=9.2｜sur3_high_no_high_mom|liq50m|top10|ind5|seminone｜trail10 20D｜top5share=19.67%
- Sharpe=2.30, return=180.86%, MDD=-10.91%, excess=120.78%, trainS=1.68, testS=3.29, avg_pos=7.0｜sur3_high_no_high_mom|liq100m|top8|ind5|seminone｜trail10 20D｜top5share=26.79%
- Sharpe=2.30, return=158.89%, MDD=-9.06%, excess=103.26%, trainS=1.69, testS=3.12, avg_pos=7.5｜sur3_high_no_high_mom|liq50m|top8|ind5|semi3｜sl8_trail12 20D｜top5share=20.78%
- Sharpe=2.29, return=159.45%, MDD=-8.26%, excess=107.92%, trainS=1.80, testS=2.93, avg_pos=9.2｜sur3_high_no_high_mom|liq50m|top10|ind5|seminone｜sl8_trail12 20D｜top5share=19.20%
- Sharpe=2.29, return=164.96%, MDD=-11.51%, excess=110.32%, trainS=1.60, testS=3.32, avg_pos=7.5｜sur3_high_no_high_mom|liq50m|top8|ind3|seminone｜trail10 20D｜top5share=22.41%
- Sharpe=2.29, return=164.96%, MDD=-11.51%, excess=110.32%, trainS=1.60, testS=3.32, avg_pos=7.5｜sur3_high_no_high_mom|liq50m|top8|ind3|semi3｜trail10 20D｜top5share=22.41%
- Sharpe=2.25, return=151.17%, MDD=-8.70%, excess=99.80%, trainS=1.74, testS=2.92, avg_pos=7.2｜sur3_high_no_high_mom|liq50m|top8|ind2|seminone｜sl8_trail12 20D｜top5share=21.17%
- Sharpe=2.25, return=151.17%, MDD=-8.70%, excess=99.80%, trainS=1.74, testS=2.92, avg_pos=7.2｜sur3_high_no_high_mom|liq50m|top8|ind2|semi2｜sl8_trail12 20D｜top5share=21.17%
- Sharpe=2.25, return=151.17%, MDD=-8.70%, excess=99.80%, trainS=1.74, testS=2.92, avg_pos=7.2｜sur3_high_no_high_mom|liq50m|top8|ind2|semi3｜sl8_trail12 20D｜top5share=21.17%
- Sharpe=2.25, return=216.08%, MDD=-12.84%, excess=149.73%, trainS=1.74, testS=2.92, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind3|seminone｜sl10_tp25 20D｜top5share=22.04%
- Sharpe=2.25, return=216.08%, MDD=-12.84%, excess=149.73%, trainS=1.74, testS=2.92, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind3|semi3｜sl10_tp25 20D｜top5share=22.04%
- Sharpe=2.25, return=215.98%, MDD=-12.84%, excess=149.03%, trainS=1.74, testS=2.92, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind5|semi3｜sl10_tp25 20D｜top5share=22.04%
- Sharpe=2.23, return=152.33%, MDD=-8.68%, excess=99.23%, trainS=1.76, testS=2.83, avg_pos=7.3｜sur3_high_no_high_mom|liq50m|top8|ind3|semi2｜sl8_trail12 20D｜top5share=21.11%
- Sharpe=2.23, return=190.19%, MDD=-10.91%, excess=129.27%, trainS=1.55, testS=3.47, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind5|semi3｜trail10 20D｜top5share=27.24%
- Sharpe=2.21, return=250.55%, MDD=-13.88%, excess=179.26%, trainS=1.60, testS=3.07, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind3|seminone｜trail15 20D｜top5share=23.90%
- Sharpe=2.21, return=250.55%, MDD=-13.88%, excess=179.26%, trainS=1.60, testS=3.07, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind3|semi3｜trail15 20D｜top5share=23.90%
- Sharpe=2.21, return=201.66%, MDD=-10.91%, excess=138.99%, trainS=1.55, testS=3.28, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind3|seminone｜trail10 20D｜top5share=26.81%
- Sharpe=2.21, return=201.66%, MDD=-10.91%, excess=138.99%, trainS=1.55, testS=3.28, avg_pos=6.7｜sur3_high_no_high_mom|liq100m|top8|ind3|semi3｜trail10 20D｜top5share=26.81%

## 達標候選 Top 20

- 沒有找到符合最低防過擬合條件的 Sharpe > 2.5 候選。

## 初步判讀原則

- 若達標策略 train Sharpe 不高但 test Sharpe 很高，通常是 2025 regime / AI-memory 題材驅動，不可直接視為穩定策略。
- 若 top5 positive contribution share 過高，代表 Sharpe 可能由少數股票貢獻；需要 remove-winners 後仍維持。
- 下一步應針對候選做更嚴格 OOS / walk-forward、交易成本加倍、產業移除、日內可成交性測試。

## 輸出檔案

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/high_sharpe_search_all.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/high_sharpe_search_candidates.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/high_sharpe_search_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/high_sharpe_search_top_trades.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/high_sharpe_search_summary.json`
