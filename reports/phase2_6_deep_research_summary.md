# Phase 2.6 深入研究總結：歷史資料、價格管線與探索性 Proxy 回測

本階段在不依賴付費資料、也不要求使用者提供資料的前提下，完成三件事：

1. 攻關免費官方歷史月營收資料。
2. 建立 2023 至今的官方日行情資料快取。
3. 跑一個保守但仍不正式的探索性 proxy 回測，用來判斷是否值得進入正式回測工程。

本報告不是投資建議，也不是交易訊號。

## 執行邊界

已遵守：

- 未實盤下單
- 未部署
- 未 git commit / git push
- 未刪除檔案
- 未安裝套件
- 未修改 Hermes repo 的 main branch
- 僅在 `/Users/liuyenzhen/quant-research/tw_monthly_revenue` 新增/更新研究檔案

## 1. 歷史月營收資料攻關結果

原本 TWSE/TPEx OpenAPI 只能取得最新月營收 snapshot，不足以回測。這次找到可用的官方靜態來源：

```text
https://doc.twse.com.tw/nas/t21/{market}/t21sc03_{roc_year}_{month}_0.html
https://doc.twse.com.tw/nas/t21/{market}/t21sc03_{roc_year}_{month}.html
```

其中：

- `market=sii`：上市
- `market=otc`：上櫃
- ROC year：例如 112 = 2023

已成功抓取：

- 期間：2021-01 到 2026-04
- 市場：上市 + 上櫃
- 總資料列：106,785
- 上市：57,303
- 上櫃：49,482
- 成功 market-month 數：120

產出：

- `scripts/fetch_historical_monthly_revenue_mops_static.py`
- `data/processed/historical_monthly_revenue_mops_static.csv`
- `data/processed/historical_monthly_revenue_mops_static.json`
- `data/processed/historical_monthly_revenue_mops_static_metadata.json`
- `reports/phase2_4_historical_revenue_source_report.md`

### 重要限制

這個來源是月營收彙總檔，沒有逐公司公告 timestamp。

因此它可以支撐：

- 歷史探索
- proxy backtest
- 3M / 12M 營收因子計算
- 每月統一訊號日策略

但還不能支撐：

- 精準公告後第 1 天進場的 event study
- 逐公司公告時間差分析

目前使用的保守 proxy：

```text
revenue_month 的次月 11 日後第一個交易日作為訊號可用日
```

## 2. 歷史日行情資料管線

已建立 2023 至今的官方日行情資料快取。

來源：

- TWSE：`MI_INDEX`
- TPEx：`otc`

已取得：

- 期間：2023-01-01 到 2026-05-22
- 交易日數：814
- 行情資料列：715,136

產出：

- `scripts/fetch_daily_market_history_2023_present.py`
- `data/processed/daily_market_history_2023_present.csv`
- `data/processed/daily_market_history_2023_present_metadata.json`
- raw cache：`data/raw/market_history_daily/`

### 限制

- 價格為未調整收盤價。
- 尚未處理現金股利、股票股利、減資、分割等 corporate actions。
- 尚未處理漲跌停無法成交、停牌、處置股。

## 3. 探索性 Proxy 回測

已建立：

- `scripts/run_proxy_backtest.py`
- `data/processed/proxy_backtest_trades.csv`
- `data/processed/proxy_backtest_summary.json`
- `reports/phase2_5_proxy_backtest_report.md`

### 回測設計

這是探索性，不是正式回測。

條件：

- 月營收資料：MOPS 靜態歷史月營收，2021-01 到 2026-04。
- 價格資料：官方日行情，2023-01 至今。
- 訊號可用日：次月 11 日後第一個交易日。
- 每月最多 Top 20。
- 成本：來回 0.7%。
- 持有期：20 / 40 / 60 個交易日。
- 排除：金融保險業、低基期、低營收、低流動性、公告前短期過熱。
- 加入：3M 營收 YoY、單月 YoY、MoM、20 日平均成交金額、20/60 日前置漲幅。

### 探索性結果

可產生 signals：660

交易筆數：

- 20 日：640
- 40 日：640
- 60 日：640

成本後結果：

#### 持有 20 日

- 平均單筆淨報酬：1.83%
- 中位數單筆淨報酬：-0.43%
- 單筆勝率：48.28%
- 平均月 cohort 淨報酬：1.83%
- 月 cohort 正報酬率：59.38%
- 最好 / 最差月 cohort：18.90% / -21.44%

#### 持有 40 日

- 平均單筆淨報酬：2.71%
- 中位數單筆淨報酬：-1.66%
- 單筆勝率：44.38%
- 平均月 cohort 淨報酬：2.71%
- 月 cohort 正報酬率：56.25%
- 最好 / 最差月 cohort：26.74% / -26.46%

#### 持有 60 日

- 平均單筆淨報酬：4.48%
- 中位數單筆淨報酬：-1.32%
- 單筆勝率：46.72%
- 平均月 cohort 淨報酬：4.48%
- 月 cohort 正報酬率：65.63%
- 最好 / 最差月 cohort：37.91% / -15.87%

## 4. 初步解讀

結果值得繼續研究，但不能直接解讀為策略有效。

### 正向訊號

1. 20/40/60 日平均淨報酬皆為正。
2. 60 日持有期表現最好，較像基本面動能，而不是單純公告日短反應。
3. 月 cohort 正報酬率在 60 日達 65.63%。
4. 成本已先扣 0.7%，不是零成本假設。
5. 使用了低基期、流動性、前置漲幅過熱等基本清理。

### 警訊

1. 中位數單筆報酬為負，代表績效可能依賴少數大贏家。
2. 勝率不到 50%，需要檢查 payoff structure。
3. 最差月 cohort 仍可到 -15% 至 -26%，風險不低。
4. 未調整價格可能低估或扭曲持有期報酬。
5. 沒有 benchmark，無法知道是否只是台股/電子股多頭 beta。
6. 沒有產業上限，可能仍是半導體/電子循環暴露。

## 5. 目前最重要結論

月營收驚喜/基本面動能方向值得繼續，因為探索性 proxy backtest 沒有立即證偽，而且 60 日持有期看起來比 20 日更強。

但這更像：

```text
月營收基本面動能策略
```

而不是嚴格的：

```text
公告後短期漂移策略
```

換句話說，目前資料支持的方向比較像：

> 營收改善後，股價可能在 1–3 個月內繼續反映基本面趨勢。

而不是：

> 公告隔天立刻有可交易 drift。

## 6. 下一步需要做什麼

下一步應進入正式 Phase 3/4 前的強化：

1. 加入 benchmark：加權指數、上市/上櫃等權、產業等權。
2. 建立真正 portfolio NAV，而不是只看月 cohort 平均報酬。
3. 加入產業上限，例如單一產業最多 30%。
4. 做單檔貢獻度，檢查是否靠少數股票拉高平均。
5. 處理調整價格或至少加入除權息事件標記。
6. 做年度分解：2023、2024、2025、2026 分開看。
7. 做參數敏感度：Top 10/20/30、成本 0.5/0.7/1.0%、流動性門檻 5,000 萬/1 億/3 億。
8. 檢查是否只是半導體/電子產業 beta。

## 7. 需要權限或額外確認的點

目前沒有遇到需要你立即授權的 blocker。

但如果要進一步做到正式級別，會有幾個可能需要確認的事項：

1. 是否允許建立更大的日行情資料庫，例如 2015 至今。這會產生更大檔案與較多官方請求。
2. 是否允許設定每月自動 snapshot job。這會建立排程任務。
3. 是否允許安裝分析套件，例如 pandas、numpy、matplotlib、duckdb，以提升研究效率。
4. 是否允許之後建立 git repo 或 commit 研究版本。現在尚未做。

## 本階段結論

已經從「找資料」推進到「免費官方資料可支撐初步 proxy backtest」。

目前最重要結論：

> 這個策略沒有被第一輪探索性回測否定，且 60 日基本面動能方向比短期 20 日漂移更值得深入。

但正式結論仍需 benchmark、調整價、產業風控、單檔貢獻、年度分解與完整 NAV 回測後才能下判斷。
