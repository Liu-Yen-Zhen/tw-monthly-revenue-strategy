# Phase 3.7 短線價量濾網研究

本階段仍是 research-only proxy/cohort backtest，不是實際持倉、paper order 或交易建議。

## 研究問題

SUR core 在 20D 較穩，但 10D/15D 需要更多確認。本階段測試：高 QTD YoY、營收加速度、3M SUR、排除過熱 momentum、underreaction 是否改善 10–20D。

## Thresholds / terciles

- `pre_ret_20d`: low <= -0.0317, high >= 0.0714
- `momentum_120_20`: low <= 0.0080, high >= 0.2880
- `sur`: low <= -0.0909, high >= 0.5212
- `sur_3m`: low <= -0.0079, high >= 0.4965
- `qtd_yoy`: low <= 14.8368, high >= 35.7038
- `rev_accel_3m`: low <= -1.2863, high >= 14.0720
- `abnormal_turnover`: low <= 0.7705, high >= 1.3921

## 每個持有期最佳 variant

- 10D：`qtd_high_no_high_mom_top10`，strategy=54.69%，excess=34.62%，Sharpe=0.99，MDD=-12.36%，avg positions=8.6
- 15D：`base_sur_core`，strategy=90.36%，excess=68.29%，Sharpe=1.21，MDD=-21.39%，avg positions=15.0
- 20D：`base_sur_core`，strategy=141.03%，excess=112.11%，Sharpe=1.40，MDD=-20.22%，avg positions=15.0

## 主要 variants

### base_sur_core
- 10D：strategy=45.95%, excess=26.46%, Sharpe=0.92, MDD=-13.24%, win=62.07%, avg positions=15.0
- 15D：strategy=90.36%, excess=68.29%, Sharpe=1.21, MDD=-21.39%, win=68.97%, avg positions=15.0
- 20D：strategy=141.03%, excess=112.11%, Sharpe=1.40, MDD=-20.22%, win=72.41%, avg positions=15.0

### mom_mid_only
- 10D：strategy=42.44%, excess=23.60%, Sharpe=0.89, MDD=-12.76%, win=62.07%, avg positions=14.4
- 15D：strategy=64.64%, excess=45.66%, Sharpe=0.96, MDD=-20.45%, win=65.52%, avg positions=14.4
- 20D：strategy=70.98%, excess=51.66%, Sharpe=0.88, MDD=-31.34%, win=68.97%, avg positions=14.4

### qtd_high_no_high_mom
- 10D：strategy=35.52%, excess=17.91%, Sharpe=0.73, MDD=-12.86%, win=62.07%, avg positions=11.2
- 15D：strategy=26.30%, excess=11.49%, Sharpe=0.52, MDD=-20.79%, win=62.07%, avg positions=11.2
- 20D：strategy=37.13%, excess=21.05%, Sharpe=0.59, MDD=-28.35%, win=68.97%, avg positions=11.2

### accel_high_no_high_mom
- 10D：strategy=35.76%, excess=17.48%, Sharpe=0.84, MDD=-13.54%, win=62.07%, avg positions=11.4
- 15D：strategy=56.35%, excess=37.16%, Sharpe=0.99, MDD=-19.45%, win=79.31%, avg positions=11.4
- 20D：strategy=83.75%, excess=62.41%, Sharpe=1.02, MDD=-24.30%, win=68.97%, avg positions=11.4

### sur3_high_no_high_mom
- 10D：strategy=52.81%, excess=31.99%, Sharpe=1.14, MDD=-14.00%, win=62.07%, avg positions=11.4
- 15D：strategy=84.82%, excess=61.82%, Sharpe=1.32, MDD=-19.37%, win=72.41%, avg positions=11.4
- 20D：strategy=128.59%, excess=101.01%, Sharpe=1.37, MDD=-23.18%, win=75.86%, avg positions=11.4

### qtd_or_accel_no_high_mom
- 10D：strategy=45.41%, excess=26.04%, Sharpe=0.97, MDD=-11.56%, win=62.07%, avg positions=13.6
- 15D：strategy=62.06%, excess=42.78%, Sharpe=1.05, MDD=-19.87%, win=65.52%, avg positions=13.6
- 20D：strategy=78.67%, excess=58.22%, Sharpe=1.01, MDD=-25.03%, win=68.97%, avg positions=13.6

### qtd_high_no_high_mom_semi2
- 10D：strategy=34.30%, excess=16.54%, Sharpe=0.71, MDD=-12.97%, win=55.17%, avg positions=9.9
- 15D：strategy=33.09%, excess=17.15%, Sharpe=0.61, MDD=-20.14%, win=62.07%, avg positions=9.9
- 20D：strategy=41.11%, excess=24.30%, Sharpe=0.62, MDD=-27.67%, win=65.52%, avg positions=9.9

## Remove top winners：重點 variants

### base_sur_core
- 10D remove 0：strategy=45.95%，excess=26.46%，MDD=-13.24%
- 10D remove 10：strategy=17.87%，excess=1.61%，MDD=-15.29%
- 10D remove 20：strategy=1.34%，excess=-12.94%，MDD=-19.79%
- 20D remove 0：strategy=141.03%，excess=112.11%，MDD=-20.22%
- 20D remove 10：strategy=80.32%，excess=57.92%，MDD=-21.48%
- 20D remove 20：strategy=47.37%，excess=28.32%，MDD=-21.48%

### qtd_high_no_high_mom
- 10D remove 0：strategy=35.52%，excess=17.91%，MDD=-12.86%
- 10D remove 10：strategy=6.30%，excess=-8.27%，MDD=-13.32%
- 10D remove 20：strategy=-8.65%，excess=-21.32%，MDD=-16.38%
- 20D remove 0：strategy=37.13%，excess=21.05%，MDD=-28.35%
- 20D remove 10：strategy=0.73%，excess=-11.69%，MDD=-30.78%
- 20D remove 20：strategy=-18.31%，excess=-28.90%，MDD=-35.28%

### accel_high_no_high_mom
- 10D remove 0：strategy=35.76%，excess=17.48%，MDD=-13.54%
- 10D remove 10：strategy=6.46%，excess=-8.53%，MDD=-13.54%
- 10D remove 20：strategy=-8.90%，excess=-21.94%，MDD=-17.95%
- 20D remove 0：strategy=83.75%，excess=62.41%，MDD=-24.30%
- 20D remove 10：strategy=22.97%，excess=7.55%，MDD=-31.00%
- 20D remove 20：strategy=-2.62%，excess=-15.41%，MDD=-33.51%

### sur3_high_no_high_mom
- 10D remove 0：strategy=52.81%，excess=31.99%，MDD=-14.00%
- 10D remove 10：strategy=19.93%，excess=2.87%，MDD=-14.00%
- 10D remove 20：strategy=3.04%，excess=-11.84%，MDD=-16.59%
- 20D remove 0：strategy=128.59%，excess=101.01%，MDD=-23.18%
- 20D remove 10：strategy=62.10%，excess=41.63%，MDD=-23.65%
- 20D remove 20：strategy=32.31%，excess=14.69%，MDD=-23.65%

### qtd_or_accel_no_high_mom
- 10D remove 0：strategy=45.41%，excess=26.04%，MDD=-11.56%
- 10D remove 10：strategy=16.67%，excess=0.38%，MDD=-11.56%
- 10D remove 20：strategy=1.04%，excess=-13.22%，MDD=-13.79%
- 20D remove 0：strategy=78.67%，excess=58.22%，MDD=-25.03%
- 20D remove 10：strategy=31.03%，excess=14.97%，MDD=-27.82%
- 20D remove 20：strategy=6.79%，excess=-6.88%，MDD=-29.17%

## 最新候選名單：price-action filter proxy Top 20

- 5314 世紀*｜其他｜score=0.90｜YoY=138.62%｜YTD YoY=161.50%｜20D=-15.72%｜60D=-23.52%｜20D均額=3.77億｜deep_underreaction;qtd_yoy_proxy_high
- 2208 台船｜航運業｜score=0.89｜YoY=132.19%｜YTD YoY=40.98%｜20D=-9.95%｜60D=-22.55%｜20D均額=0.86億｜deep_underreaction;mom_positive
- 8271 宇瞻｜半導體業｜score=0.89｜YoY=360.82%｜YTD YoY=276.89%｜20D=1.13%｜60D=85.54%｜20D均額=8.20億｜qtd_yoy_proxy_high;mom_positive
- 6640 均華｜半導體業｜score=0.88｜YoY=142.34%｜YTD YoY=104.96%｜20D=-7.48%｜60D=82.06%｜20D均額=6.83億｜deep_underreaction;qtd_yoy_proxy_high;mom_positive
- 4739 康普｜化學工業｜score=0.88｜YoY=96.24%｜YTD YoY=115.46%｜20D=0.50%｜60D=42.05%｜20D均額=4.92億｜qtd_yoy_proxy_high;mom_positive
- 7750 新代｜電機機械｜score=0.87｜YoY=94.87%｜YTD YoY=63.77%｜20D=6.70%｜60D=95.90%｜20D均額=20.10億｜qtd_yoy_proxy_high;mom_positive
- 6907 雅特力-KY｜半導體業｜score=0.86｜YoY=121.66%｜YTD YoY=86.77%｜20D=-13.21%｜60D=88.37%｜20D均額=2.48億｜deep_underreaction;qtd_yoy_proxy_high;mom_positive
- 9945 潤泰新｜其他｜score=0.83｜YoY=58.78%｜YTD YoY=34.31%｜20D=-4.12%｜60D=-21.28%｜20D均額=1.74億｜deep_underreaction;mom_positive
- 7751 竑騰｜半導體業｜score=0.83｜YoY=67.20%｜YTD YoY=71.46%｜20D=-17.31%｜60D=98.36%｜20D均額=6.90億｜deep_underreaction;qtd_yoy_proxy_high
- 8021 尖點｜其他電子業｜score=0.83｜YoY=63.18%｜YTD YoY=54.21%｜20D=-10.50%｜60D=89.24%｜20D均額=27.72億｜deep_underreaction;mom_positive
- 1815 富喬｜電子零組件業｜score=0.83｜YoY=53.16%｜YTD YoY=40.48%｜20D=-0.93%｜60D=0.94%｜20D均額=40.16億｜
- 5498 凱崴｜電子零組件業｜score=0.83｜YoY=54.64%｜YTD YoY=50.29%｜20D=-13.47%｜60D=13.22%｜20D均額=5.33億｜deep_underreaction
- 3147 大綜｜資訊服務業｜score=0.82｜YoY=90.07%｜YTD YoY=9.46%｜20D=1.09%｜60D=11.71%｜20D均額=0.59億｜mom_positive
- 7744 崴寶｜電子零組件業｜score=0.82｜YoY=80.51%｜YTD YoY=69.42%｜20D=-8.58%｜60D=23.86%｜20D均額=1.06億｜deep_underreaction;qtd_yoy_proxy_high
- 3260 威剛｜半導體業｜score=0.81｜YoY=169.51%｜YTD YoY=165.39%｜20D=5.03%｜60D=38.94%｜20D均額=126.47億｜qtd_yoy_proxy_high
- 2382 廣達｜電腦及週邊設備業｜score=0.81｜YoY=120.71%｜YTD YoY=79.64%｜20D=-1.86%｜60D=11.46%｜20D均額=81.20億｜qtd_yoy_proxy_high
- 2207 和泰車｜汽車工業｜score=0.80｜YoY=30.03%｜YTD YoY=5.75%｜20D=-8.15%｜60D=-15.85%｜20D均額=2.03億｜deep_underreaction;mom_positive
- 7822 倍利科｜半導體業｜score=0.80｜YoY=77.97%｜YTD YoY=110.59%｜20D=-20.15%｜60D=NA｜20D均額=4.15億｜deep_underreaction;qtd_yoy_proxy_high
- 1305 華夏｜塑膠工業｜score=0.80｜YoY=43.35%｜YTD YoY=17.37%｜20D=-17.61%｜60D=4.64%｜20D均額=0.61億｜deep_underreaction;mom_positive
- 2347 聯強｜電子通路業｜score=0.79｜YoY=83.28%｜YTD YoY=49.73%｜20D=2.19%｜60D=22.59%｜20D均額=3.83億｜

## 初步解讀

- 若只看短線，排除過熱 momentum 比單純追高更重要。
- 這一輪硬篩 `qtd_high_no_high_mom` / `accel_high_no_high_mom` 沒有勝過 baseline；它們持倉數較少且 remove-winners 後 edge 退化很快。
- 目前較有研究價值的是 `sur3_high_no_high_mom`：保留 3M revenue surprise 持續性，同時避免過熱 momentum；它在 10D/15D/20D 都較接近 baseline，20D remove top winners 後仍有正 excess。
- 加半導體 cap 可測試是否只是押單一電子景氣循環；若 cap 後明顯衰退，後續不能宣稱跨產業穩健。
- 文獻線索：PEAD / revenue surprise / fundamental momentum 支持『基本面 surprise 後的延遲反應』，但 Taiwan monthly revenue 相關研究也提醒公告前權證/交易資訊可能提前反映，且 lottery-like extreme winners 會扭曲短線平均報酬。

## 輸出檔案

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_action_filter_variants.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_action_filter_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_action_filter_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_action_filter_industry.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_action_filter_latest_candidates.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_action_filter_summary.json`
