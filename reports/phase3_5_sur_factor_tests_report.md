# Phase 3.5 SUR / 營收 Surprise 因子測試

本階段把文獻中的 revenue surprise / PEAD 想法落地到台股月營收資料。仍為 proxy/cohort backtest，不是投資建議、實際持倉或交易系統。

## 方法

- SUR：`(actual revenue - expected revenue) / historical forecast-error volatility`。
- expected revenue：去年同月營收乘上前三個月平均 YoY 趨勢。
- Industry-adjusted SUR：公司 SUR 扣同月同產業 median SUR。
- 加入 3M SUR、3M revenue acceleration、QTD revenue YoY。
- 搭配 120-20D price momentum、20D/120D abnormal turnover、20D runup control、流動性與產業上限。
- 每月 Top15，單一產業最多 5 檔，成本 0.7%。

## 資料與候選數

- eligible candidates: 2002
- signals: 2250
- trades: 6525

## 結果摘要

## Recipe: yoy_baseline

- 20D：strategy=36.81%, excess=20.15%, ann=13.85%, Sharpe=0.58, MDD=-38.53%, win=58.62%, avg_pos=15.00
- 40D：strategy=115.11%, excess=62.65%, ann=37.29%, Sharpe=1.00, MDD=-51.99%, win=62.07%, avg_pos=15.00
- 60D：strategy=341.33%, excess=135.03%, ann=84.84%, Sharpe=1.54, MDD=-50.32%, win=65.52%, avg_pos=15.00

## Recipe: sur_core

- 20D：strategy=141.03%, excess=112.11%, ann=43.91%, Sharpe=1.40, MDD=-20.22%, win=72.41%, avg_pos=15.00
- 40D：strategy=344.17%, excess=236.17%, ann=85.33%, Sharpe=1.83, MDD=-27.02%, win=72.41%, avg_pos=15.00
- 60D：strategy=884.76%, excess=433.79%, ann=157.65%, Sharpe=1.94, MDD=-33.77%, win=75.86%, avg_pos=15.00

## Recipe: industry_adjusted_sur

- 20D：strategy=105.63%, excess=80.85%, ann=34.76%, Sharpe=1.18, MDD=-22.14%, win=68.97%, avg_pos=15.00
- 40D：strategy=205.77%, excess=129.18%, ann=58.80%, Sharpe=1.48, MDD=-31.21%, win=65.52%, avg_pos=15.00
- 60D：strategy=440.52%, excess=187.19%, ann=101.02%, Sharpe=1.91, MDD=-34.87%, win=68.97%, avg_pos=15.00

## Recipe: sur_trend_liquidity

- 20D：strategy=64.17%, excess=44.40%, ann=22.77%, Sharpe=0.82, MDD=-21.50%, win=58.62%, avg_pos=15.00
- 40D：strategy=189.59%, excess=116.66%, ann=55.27%, Sharpe=1.32, MDD=-30.44%, win=65.52%, avg_pos=15.00
- 60D：strategy=455.95%, excess=197.77%, ann=103.37%, Sharpe=1.67, MDD=-42.90%, win=68.97%, avg_pos=15.00

## Recipe: sur_balanced

- 20D：strategy=128.66%, excess=99.25%, ann=40.81%, Sharpe=1.36, MDD=-17.89%, win=72.41%, avg_pos=15.00
- 40D：strategy=305.59%, excess=202.68%, ann=78.49%, Sharpe=1.77, MDD=-22.47%, win=72.41%, avg_pos=15.00
- 60D：strategy=839.42%, excess=408.23%, ann=152.68%, Sharpe=1.87, MDD=-32.49%, win=72.41%, avg_pos=15.00

## 每個持有期最佳 Excess

- 20D：sur_core，strategy=141.03%，excess=112.11%，MDD=-20.22%，Sharpe=1.40
- 40D：sur_core，strategy=344.17%，excess=236.17%，MDD=-27.02%，Sharpe=1.83
- 60D：sur_core，strategy=884.76%，excess=433.79%，MDD=-33.77%，Sharpe=1.94

## 解讀方向

如果 SUR / industry-adjusted SUR 贏過 YoY baseline，代表 surprise normalization 有價值；如果 SUR 輸給 trend/liquidity recipe，代表台股月營收策略更需要市場確認與資金確認。
下一步應接著做：不同 expected revenue 模型、SUR winsorization、industry-relative residual momentum，以及籌碼面資料攻關。
