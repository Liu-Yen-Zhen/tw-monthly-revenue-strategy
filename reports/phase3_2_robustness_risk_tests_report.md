# Phase 3.2 穩健性與風控測試

本報告針對 Phase 3.1 的 cohort NAV 雛形做 one-at-a-time 穩健性測試。仍不是正式交易系統或投資建議。

## Baseline

Baseline = industry capped、Top 20、成本 0.7%、20D 均成交門檻 5,000 萬、進場前 20D 漲幅上限 30%。

## 持有 20 日 baseline

- 月份數：32
- 平均持股數：18.78
- 策略總報酬：62.51%
- 策略年化 proxy：19.97%
- 策略 Sharpe proxy：0.76
- 策略 MDD：-32.27%
- Excess 總報酬：38.62%
- Excess Sharpe proxy：0.82
- Excess MDD：-18.14%

### Top N 敏感度

- Top 10: strategy=64.89%, excess=39.53%, MDD=-36.68%, Sharpe=0.74
- Top 15: strategy=70.80%, excess=45.38%, MDD=-32.29%, Sharpe=0.81
- Top 20: strategy=62.51%, excess=38.62%, MDD=-32.27%, Sharpe=0.76

### 成本敏感度

- 成本 0.5%: strategy=73.11%, excess=38.62%, MDD=-30.98%
- 成本 0.7%: strategy=62.51%, excess=38.62%, MDD=-32.27%
- 成本 1.0%: strategy=47.77%, excess=38.62%, MDD=-34.16%

### 流動性門檻敏感度

- 20D 均成交 >= 5,000 萬: positions=18.78, strategy=62.51%, excess=38.62%, MDD=-32.27%
- 20D 均成交 >= 10,000 萬: positions=16.69, strategy=56.26%, excess=33.52%, MDD=-36.15%
- 20D 均成交 >= 30,000 萬: positions=11.88, strategy=95.48%, excess=67.58%, MDD=-34.60%

### 去掉歷史最大贏家

- remove top 0: strategy=62.51%, excess=38.62%, MDD=-32.27%, Sharpe=0.76
- remove top 5: strategy=38.38%, excess=17.86%, MDD=-32.32%, Sharpe=0.56
- remove top 10: strategy=19.28%, excess=0.67%, MDD=-34.74%, Sharpe=0.38

## 持有 40 日 baseline

- 月份數：32
- 平均持股數：18.78
- 策略總報酬：99.51%
- 策略年化 proxy：29.56%
- 策略 Sharpe proxy：0.87
- 策略 MDD：-49.80%
- Excess 總報酬：50.11%
- Excess Sharpe proxy：0.74
- Excess MDD：-39.81%

### Top N 敏感度

- Top 10: strategy=99.38%, excess=47.84%, MDD=-56.20%, Sharpe=0.79
- Top 15: strategy=103.18%, excess=52.61%, MDD=-52.52%, Sharpe=0.85
- Top 20: strategy=99.51%, excess=50.11%, MDD=-49.80%, Sharpe=0.87

### 成本敏感度

- 成本 0.5%: strategy=112.47%, excess=50.11%, MDD=-48.71%
- 成本 0.7%: strategy=99.51%, excess=50.11%, MDD=-49.80%
- 成本 1.0%: strategy=81.49%, excess=50.11%, MDD=-51.40%

### 流動性門檻敏感度

- 20D 均成交 >= 5,000 萬: positions=18.78, strategy=99.51%, excess=50.11%, MDD=-49.80%
- 20D 均成交 >= 10,000 萬: positions=16.69, strategy=89.48%, excess=42.76%, MDD=-51.29%
- 20D 均成交 >= 30,000 萬: positions=11.88, strategy=169.96%, excess=101.48%, MDD=-45.63%

### 去掉歷史最大贏家

- remove top 0: strategy=99.51%, excess=50.11%, MDD=-49.80%, Sharpe=0.87
- remove top 5: strategy=44.89%, excess=8.73%, MDD=-51.55%, Sharpe=0.56
- remove top 10: strategy=2.93%, excess=-23.76%, MDD=-54.24%, Sharpe=0.20

## 持有 60 日 baseline

- 月份數：32
- 平均持股數：18.78
- 策略總報酬：236.72%
- 策略年化 proxy：57.66%
- 策略 Sharpe proxy：1.24
- 策略 MDD：-57.45%
- Excess 總報酬：76.57%
- Excess Sharpe proxy：0.78
- Excess MDD：-55.28%

### Top N 敏感度

- Top 10: strategy=178.15%, excess=43.97%, MDD=-62.50%, Sharpe=0.92
- Top 15: strategy=200.23%, excess=55.59%, MDD=-58.55%, Sharpe=1.09
- Top 20: strategy=236.72%, excess=76.57%, MDD=-57.45%, Sharpe=1.24

### 成本敏感度

- 成本 0.5%: strategy=258.26%, excess=76.57%, MDD=-56.51%
- 成本 0.7%: strategy=236.72%, excess=76.57%, MDD=-57.45%
- 成本 1.0%: strategy=206.75%, excess=76.57%, MDD=-58.82%

### 流動性門檻敏感度

- 20D 均成交 >= 5,000 萬: positions=18.78, strategy=236.72%, excess=76.57%, MDD=-57.45%
- 20D 均成交 >= 10,000 萬: positions=16.69, strategy=225.58%, excess=71.21%, MDD=-58.01%
- 20D 均成交 >= 30,000 萬: positions=11.88, strategy=363.31%, excess=140.02%, MDD=-52.85%

### 去掉歷史最大贏家

- remove top 0: strategy=236.72%, excess=76.57%, MDD=-57.45%, Sharpe=1.24
- remove top 5: strategy=91.68%, excess=-1.94%, MDD=-56.89%, Sharpe=0.84
- remove top 10: strategy=16.83%, excess=-41.15%, MDD=-60.84%, Sharpe=0.33

## 初步解讀

- 如果 Top N、成本、流動性與移除大贏家後仍保有正 excess，代表訊號比較穩健。
- 如果移除 top winners 後迅速崩潰，代表策略更偏右尾捕捉，需要明確承認並用分散/風控管理。
- MDD 仍是主要問題；下一階段應測市場 regime filter 或降低曝險。
