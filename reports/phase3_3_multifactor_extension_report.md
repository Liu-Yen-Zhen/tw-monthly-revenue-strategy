# Phase 3.3 多因子擴充測試

這次在月營收基本面訊號之外，加入技術面、流動性與風險因子。仍為 proxy/cohort backtest，不是投資建議或正式交易系統。

## 測試的非基本面因子

- 60D 價格動能：趨勢確認。
- 20D 前置漲幅反向排序：避免短期過熱。
- 60D 波動度反向排序：偏好較穩定標的。
- 20D 平均成交金額：流動性與市場關注。
- 產業上限：Top15 中單一產業最多 5 檔。

## 結果摘要

## Recipe: fundamental_only

- 20D：strategy=71.25%, excess=45.46%, ann=22.35%, Sharpe=0.82, MDD=-31.52%, win=65.62%, avg_pos=15.00
- 40D：strategy=79.43%, excess=34.41%, ann=24.51%, Sharpe=0.73, MDD=-53.16%, win=59.38%, avg_pos=15.00
- 60D：strategy=147.93%, excess=27.53%, ann=40.56%, Sharpe=0.92, MDD=-60.01%, win=59.38%, avg_pos=15.00

## Recipe: trend_confirmed

- 20D：strategy=82.24%, excess=53.21%, ann=25.24%, Sharpe=0.94, MDD=-26.36%, win=59.38%, avg_pos=15.00
- 40D：strategy=188.16%, excess=115.56%, ann=48.72%, Sharpe=1.22, MDD=-39.52%, win=62.50%, avg_pos=15.00
- 60D：strategy=341.14%, excess=129.18%, ann=74.47%, Sharpe=1.43, MDD=-43.84%, win=56.25%, avg_pos=15.00

## Recipe: risk_controlled

- 20D：strategy=43.67%, excess=21.62%, ann=14.55%, Sharpe=0.61, MDD=-37.99%, win=59.38%, avg_pos=15.00
- 40D：strategy=65.67%, excess=22.50%, ann=20.84%, Sharpe=0.68, MDD=-55.56%, win=46.88%, avg_pos=15.00
- 60D：strategy=192.17%, excess=49.98%, ann=49.49%, Sharpe=1.08, MDD=-62.54%, win=62.50%, avg_pos=15.00

## Recipe: liquidity_momentum

- 20D：strategy=84.41%, excess=55.81%, ann=25.80%, Sharpe=0.94, MDD=-26.76%, win=62.50%, avg_pos=15.00
- 40D：strategy=235.11%, excess=151.84%, ann=57.38%, Sharpe=1.31, MDD=-41.00%, win=62.50%, avg_pos=15.00
- 60D：strategy=702.46%, excess=327.57%, ann=118.35%, Sharpe=1.76, MDD=-39.72%, win=62.50%, avg_pos=15.00

## Recipe: quality_trend_risk

- 20D：strategy=95.90%, excess=65.66%, ann=28.68%, Sharpe=1.00, MDD=-26.00%, win=65.62%, avg_pos=15.00
- 40D：strategy=201.23%, excess=127.13%, ann=51.21%, Sharpe=1.24, MDD=-39.29%, win=56.25%, avg_pos=15.00
- 60D：strategy=434.51%, excess=180.29%, ann=87.49%, Sharpe=1.53, MDD=-40.73%, win=59.38%, avg_pos=15.00

## 每個持有期的最佳 Excess

- 20D：quality_trend_risk，strategy=95.90%，excess=65.66%，MDD=-26.00%，Sharpe=1.00
- 40D：liquidity_momentum，strategy=235.11%，excess=151.84%，MDD=-41.00%，Sharpe=1.31
- 60D：liquidity_momentum，strategy=702.46%，excess=327.57%，MDD=-39.72%，Sharpe=1.76

## 解讀

若加入趨勢/流動性/風險因子後，excess 與 MDD 改善，代表策略不應只依賴基本面營收排名；如果結果變差，代表月營收訊號本身較重要，其他因子只適合當風控而非排序主軸。
下一階段可加入籌碼面：外資/投信買賣超、融資融券、借券與集保分散，測試營收改善是否需要資金確認。
