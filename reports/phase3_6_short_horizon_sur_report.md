# Phase 3.6 短線 SUR 策略研究：5/10/15/20D

本階段聚焦使用者提到的 10–20 天內短線交易可能性。仍為 proxy/cohort backtest，不是實際持倉、paper order 或交易建議。

## Baseline 設定

- Recipe：主要看 `sur_core`，並與 `sur_balanced`、`industry_adjusted_sur`、`yoy_baseline` 比較。
- Top 15，單一產業最多 5 檔。
- 20D 平均成交金額門檻 5,000 萬。
- round-trip cost 0.7%。
- 持有期：5D / 10D / 15D / 20D。

## Baseline sur_core 結果

- 5D：strategy=25.23%, excess=26.79%, ann=9.42%, Sharpe=0.75, MDD=-7.58%, win=53.33%
- 10D：strategy=45.95%, excess=26.46%, ann=16.94%, Sharpe=0.92, MDD=-13.24%, win=62.07%
- 15D：strategy=90.36%, excess=68.29%, ann=30.52%, Sharpe=1.21, MDD=-21.39%, win=68.97%
- 20D：strategy=141.03%, excess=112.11%, ann=43.91%, Sharpe=1.40, MDD=-20.22%, win=72.41%

## 每個持有期最佳 recipe/config

- 5D：top10 / sur_core，strategy=42.27%，excess=44.18%，MDD=-7.23%，Sharpe=1.07
- 10D：top10 / sur_core，strategy=69.36%，excess=47.22%，MDD=-14.36%，Sharpe=1.11
- 15D：top10 / sur_core，strategy=96.22%，excess=73.29%，MDD=-22.35%，Sharpe=1.24
- 20D：baseline / sur_core，strategy=141.03%，excess=112.11%，MDD=-20.22%，Sharpe=1.40

## Remove top winners 壓力測試：baseline sur_core

### 5D
- remove top 0：strategy=25.23%，excess=26.79%，MDD=-7.58%
- remove top 5：strategy=13.59%，excess=14.96%，MDD=-8.65%
- remove top 10：strategy=6.00%，excess=7.17%，MDD=-8.65%
- remove top 20：strategy=-4.21%，excess=-3.14%，MDD=-9.81%

### 10D
- remove top 0：strategy=45.95%，excess=26.46%，MDD=-13.24%
- remove top 5：strategy=28.30%，excess=10.77%，MDD=-14.16%
- remove top 10：strategy=17.87%，excess=1.61%，MDD=-15.29%
- remove top 20：strategy=1.34%，excess=-12.94%，MDD=-19.79%

### 15D
- remove top 0：strategy=90.36%，excess=68.29%，MDD=-21.39%
- remove top 5：strategy=62.86%，excess=43.09%，MDD=-21.39%
- remove top 10：strategy=41.36%，excess=23.80%，MDD=-21.39%
- remove top 20：strategy=18.72%，excess=3.65%，MDD=-21.39%

### 20D
- remove top 0：strategy=141.03%，excess=112.11%，MDD=-20.22%
- remove top 5：strategy=108.16%，excess=82.56%，MDD=-20.22%
- remove top 10：strategy=80.32%，excess=57.92%，MDD=-21.48%
- remove top 20：strategy=47.37%，excess=28.32%，MDD=-21.48%

## 年度拆解：baseline sur_core 10D / 20D

- 10D 2023：strategy=-9.73%，excess=-10.29%，win=20.00%，MDD=-9.73%
- 10D 2024：strategy=11.04%，excess=5.58%，win=66.67%，MDD=-13.24%
- 10D 2025：strategy=45.61%，excess=33.52%，win=75.00%，MDD=-4.69%
- 20D 2023：strategy=9.29%，excess=0.85%，win=60.00%，MDD=-5.88%
- 20D 2024：strategy=30.16%，excess=22.65%，win=75.00%，MDD=-14.20%
- 20D 2025：strategy=69.43%，excess=71.49%，win=75.00%，MDD=-20.22%

## 短線交易解讀重點

- 5D/10D 可用來觀察公告後短期資訊擴散，但成本與滑價會更重要。
- 10D/15D/20D 若能維持 positive excess 且 MDD 明顯低於 40D/60D，才比較接近短線 paper trading 候選。
- 若 remove top winners 後 excess 快速消失，代表短線仍是右尾捕捉，不適合重倉單檔。
- 下一步短線最需要加入籌碼資料：外資/投信買賣超、融資融券、異常成交量與法人確認。

## 輸出檔案

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/short_horizon_sur_variants.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/short_horizon_sur_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/short_horizon_sur_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/short_horizon_sur_summary.json`
