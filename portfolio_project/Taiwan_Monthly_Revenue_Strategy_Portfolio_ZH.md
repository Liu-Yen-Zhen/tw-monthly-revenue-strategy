# 台股月營收驚喜策略研究作品集

**副標題：** 從市場制度假說到執行可行性驗證的台股量化研究  
**範圍：** 研究 / 模擬交易用途；非投資建議、非實盤交易系統。

---

## 0. 一句話摘要

本專案研究台灣上市櫃公司每月公布營收後，市場是否會對「連續性的營收驚喜」反應不足，進而在公布後 10–20 個交易日出現短期漂移。研究結果顯示：最有說服力的版本不是廣義台股萬用策略，而是偏向 **電子 / 半導體供應鏈的月營收驚喜與基本面動能策略**。目前適合作為研究作品集，但尚不能宣稱為 production-ready alpha。

---

## 1. 專案定位

### 1.1 這份作品集想展示什麼？

這份作品集展示的不只是「找到一個高 Sharpe 回測」，而是一個完整的量化研究流程：

- 從台灣市場制度出發，而不是堆疊技術指標。
- 使用官方 / 官方衍生資料建立月營收研究資料集。
- 建構 SUR-style revenue surprise 因子。
- 從簡單 proxy backtest 逐步推進到 robustness gates。
- 保留 promising variants，而不是每次搜尋都覆蓋前一個好策略。
- 測試 OOS、winner dependence、sector dependence、流動性、成本、進場時點、漲停無法成交風險。
- 誠實說明目前還不能稱為實盤策略的原因。

### 1.2 最終研究定位

推薦對外說法：

> 這是一個台股月營收驚喜與短期公布後漂移的量化研究作品集。核心候選策略在 proxy backtest 中有吸引力，但仍需 exact announcement timestamp、完整 survivorship control、execution simulation 與 paper-trading validation，才能往實盤研究推進。

不建議說法：

- 「這是 production-ready alpha」
- 「這是可以直接上線的台股交易系統」
- 「保證 Sharpe 2+」
- 「這是廣義全市場台股策略」

---

## 2. 核心市場假說

### 2.1 為什麼台灣月營收值得研究？

台灣上市櫃公司每月公布營收。相較於季度財報，月營收提供了更高頻的基本面更新，特別適合研究：

- 市場是否立即消化新的營收資訊；
- 基本面 surprise 是否會延續；
- 電子 / 半導體供應鏈是否存在資訊反應延遲；
- 短期資金是否會在公布後逐步重新定價。

### 2.2 因果鏈

本專案的因果假說不是「營收成長高，所以股價會漲」這麼簡單，而是：

> 因為台灣公司每月公布營收，持續性的正向營收 surprise 會更新投資人對需求、訂單與供應鏈景氣的預期；如果市場沒有在公布後立即完全反映，則部分股票可能在接下來 10–20 個交易日出現後續 repricing。

這個效果應該在以下條件更明顯：

- surprise 具有連續性，而不是單月雜訊；
- 股價尚未過度反映；
- 產業具有明確景氣敘事，例如電子、半導體、AI / 記憶體 / 供應鏈；
- 流動性足以讓研究假設具備交易可行性；
- 進場時間在資料公開後，而不是偷看未公開資訊。

---

## 3. 資料與限制

### 3.1 使用資料

研究使用本地已建立的台灣官方 / 官方衍生資料：

- 月營收資料 panel；
- 每日市場資料，包括收盤價與成交金額；
- 原始官方 daily JSON；
- 後續解析出的 OHLC / 漲跌停研究表。

主要專案路徑：

```text
/Users/liuyenzhen/quant-research/tw_monthly_revenue
```

### 3.2 最大資料限制：exact timestamp 尚未完成

目前歷史月營收資料的公告時間品質為：

```text
announcement_date_quality = monthly_summary_no_company_timestamp
```

意思是：

- 目前還沒有每間公司精確公告時間；
- 無法完全判斷當天盤中 / 盤後公告；
- 無法最終證明最早可交易時間；
- 因此不能宣稱完全消除 data timing risk。

因此本研究後續使用 conservative delayed entry / next-open proxy，並明確保留這個限制。

---

## 4. 因子與策略設計

### 4.1 核心因子

研究測試過的因子包含：

- 月營收 YoY / MoM；
- 3 個月營收成長與持續性；
- SUR-style standardized unexpected revenue；
- 產業調整後 surprise；
- 股價動能與過熱濾網；
- 異常成交量；
- K 線 / OHLC 狀態，例如 narrow range、large black K。

最後保留的核心訊號是：

```text
3M SUR persistence + not-overheated momentum
```

也就是：

- 找持續性營收 surprise；
- 避免已經過度上漲、可能提前反映的股票。

### 4.2 主要候選策略 S1

目前保留的 portfolio-grade v0.1 incumbent：

```text
sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D
```

解讀：

- 使用 3M SUR persistence；
- 排除過熱 momentum；
- 20 日持有期；
- 流動性門檻 5,000 萬台幣；
- 每期最多 8 檔；
- 產業上限 3 檔；
- 加入 stop / trailing 類 proxy，但仍需注意這是 close-price proxy，不是完整可執行模擬。

---

## 5. 主要結果摘要

### 5.1 S1 portfolio-grade v0.1 proxy

觀察到的 proxy 指標：

- Sharpe proxy：約 `2.40`
- Total return：約 `+167.5%`
- Maximum drawdown：約 `-7.9%`
- Train Sharpe：約 `1.86`
- 2025 test Sharpe：約 `3.12`
- Remove top-5 winners Sharpe：約 `1.77`
- Remove top-10 winners Sharpe：約 `1.41`

解讀：

這個版本足以作為研究作品集的核心候選策略，但不能直接稱為實盤策略。主要原因是：

- right-tail dependence 仍明顯；
- 2025 可能受到電子 / AI / 記憶體 regime 影響；
- stop / trailing 還是 proxy；
- exact announcement timing 尚未完整解決。

### 5.2 S1 fixed-20 comparator

固定 20 日版本的基準：

- Return：`161.9%`
- Sharpe：`1.55`
- MDD：`-21.2%`
- Active months：`29/30`
- Average positions：`7.27`

這個版本較容易解釋，適合作為 benchmark。

### 5.3 Quiet digestion dynamic sizing

後續研究發現一個可解釋的狀態：

```text
高 3M SUR + 未過熱 momentum + 低異常成交量 + 窄幅 K 線
```

稱為 quiet digestion。直覺是：

> 好的月營收公布後，股價沒有爆量追高，而是低量整理，可能代表市場仍在消化基本面資訊。

但 standalone quiet digestion 交易次數少、winner dependence 明顯，因此最後沒有被提升為替代策略，而是測試為 S1 的 sizing overlay。

最佳 sizing proxy：

```text
boost_quiet_no_large_black_150
```

結果：

- Equal S1 fixed-20 Sharpe：`1.55`
- Quiet boost Sharpe：`1.62`
- Equal S1 return：`161.9%`
- Quiet boost return：`174.4%`
- MDD：幾乎不變，約 `-21.2%`

解讀：

quiet boost 有小幅改善，但不足以正式 promotion。

---

## 6. Robustness Dashboard

### 6.1 Promotion rule

本專案不因為 full-sample Sharpe 上升就提升策略。任何新版本必須通過：

- year split；
- walk-forward OOS；
- remove-top-winners；
- electronics / semiconductor / no-semiconductor slice；
- liquidity threshold；
- cost stress；
- execution timing stress。

### 6.2 Remove-winner stress

#### Equal S1

- Remove 0：Sharpe `1.55`
- Remove 5：Sharpe `1.16`
- Remove 10：Sharpe `0.96`
- Remove 20：Sharpe `0.38`

#### Quiet boost

- Remove 0：Sharpe `1.62`
- Remove 5：Sharpe `1.22`
- Remove 10：Sharpe `1.04`
- Remove 20：Sharpe `0.48`

解讀：

quiet boost 稍微改善 winner-dependence，但沒有消除右尾依賴。

### 6.3 Walk-forward dynamic sizing

#### Train 2023 → Test 2024

- Selected rule：`boost_quiet_no_large_black_125`
- OOS return：`14.45%`
- OOS Sharpe：`0.74`
- Equal S1 OOS return：`12.91%`
- Equal S1 OOS Sharpe：`0.67`

#### Train 2023–2024 → Test 2025

- Selected rule：`boost_quiet_no_large_black_200`
- OOS return：`40.50%`
- OOS Sharpe：`1.17`
- Equal S1 OOS return：`35.45%`
- Equal S1 OOS Sharpe：`1.08`

解讀：

OOS 有改善，但幅度不大，而且只有兩個切分，不足以證明穩定 alpha。

### 6.4 Sector stress

2025 selected OOS rule：

- All：Sharpe `1.17`
- Semiconductor-only：Sharpe `2.59`
- No-semiconductor：Sharpe `0.31`
- Remove-top-5：Sharpe `0.37`

2024 selected OOS rule：

- All：Sharpe `0.76`
- Semiconductor-only：Sharpe `1.52`
- No-semiconductor：Sharpe `-0.56`
- Remove-top-5：Sharpe `-0.50`

解讀：

策略高度依賴電子 / 半導體與少數大贏家。這是不能把它稱為 broad-market production alpha 的核心原因。

---

## 7. 執行可行性與交易成本

### 7.1 為什麼 execution realism 很重要？

月營收策略是事件驅動策略。如果回測假設在資訊尚未公開前進場，或假設能用無法成交的價格成交，就會高估績效。

真正要回答的是：

> 研究者能不能在看到資料後產生訊號、送出訂單，並在合理價格成交？

### 7.2 已完成的 execution realism work

研究後期加入：

- next-open / next-close timing；
- 延遲 0/1/2/3 個交易日；
- 0.7%、1.0%、1.5% 成本；
- possible limit-up non-fill exclusion；
- OHLC / limit parser；
- ADV participation capacity proxy。

### 7.3 Conservative proxy 結果

在以下假設下：

```text
next_open + 1.0% cost + exclude possible limit-up risk
```

結果為：

- Equal S1：return `99.8%`，Sharpe `1.16`，MDD `-26.2%`
- Quiet boost：return `111.9%`，Sharpe `1.24`，MDD `-24.9%`

解讀：

保守執行假設下仍有正向結果，但不再是 headline high-Sharpe。這反而是專業研究應該呈現的結果。

---

## 8. 研究時間軸

### Phase 2：資料可行性與初步 proxy backtest

- 建立月營收資料來源與每日市場資料來源。
- 建立 historical monthly revenue panel。
- 發現 data timing 是核心風險。

### Phase 3.1–3.5：Portfolio NAV 與 SUR 因子

- 從 trade average 轉成 portfolio NAV。
- 加入 robustness / risk tests。
- 測試 SUR-style 與 industry-adjusted surprise。
- 發現 persistent 3M SUR 優於單月高成長。

### Phase 3.6–3.8：短期 horizon 與 exit rule

- 聚焦 10–20 trading days。
- 20D 比 10D 更穩健。
- 測試 stop / trailing proxies，但標記為 close-price proxy。

### Phase 3.9–3.12：高 Sharpe 搜尋、walk-forward、sector survival

- 廣泛搜尋未找到穩健 Sharpe > 2.5 的 production candidate。
- S1 保留為 incumbent。
- sector survival 顯示電子 / 半導體依賴。

### Phase 3.13–3.18：價格 / 成交量 / K 線與 quiet digestion

- 測試異常成交量、窄幅整理、large black K。
- volume expansion alone 不是穩定 alpha。
- quiet digestion 有因果解釋，但交易少且 winner-dependent。
- 最後只作為 sizing hypothesis。

### Phase 3.19–3.26：execution realism 與 paper-trading schema

- 加入 next-open、成本、漲停無法成交 proxy。
- 加入 delay-aware walk-forward selection。
- 建立 paper-trading execution schema。
- 解析官方 daily raw JSON 成 OHLC / limit research table。

---

## 9. Paper-Trading Plan

### 9.1 為什麼需要 paper trading？

回測證明的是歷史資料中的統計現象；paper trading 驗證的是操作可行性：

- 訊號是否真的能在資料公開後產生；
- 能否用合理價格進場；
- 是否常遇到漲停排不到；
- 實際滑價是否高於假設；
- backtest assumption 與 real-time operation 是否一致。

### 9.2 每月 paper-trading 必記錄欄位

```text
signal_id
stock_id
stock_name
revenue_month
data_observed_at
signal_generated_at
planned_entry_date
planned_entry_type
observed_open / high / low / close
limit_up_price
opened_at_limit_up
non_fill_reason
planned_notional
ADV_participation_pct
estimated_slippage
paper_fill_price
5D / 10D / 20D return
assumption_drift_note
```

### 9.3 Paper-trading acceptance criteria

在宣稱 production-adjacent 前，至少需要多個月度 cycle：

- timestamped signal generation；
- feasible paper fills；
- explicit non-fill accounting；
- stable cost / slippage assumption；
- actual paper PnL 與 backtest expectation 對照；
- no hidden same-day look-ahead assumption。

---

## 10. 限制與下一步

### 10.1 目前限制

1. **exact announcement timestamp 尚缺**  
   這是目前最大限制。

2. **survivorship / universe completeness 仍需加強**  
   production-grade 版本需要更完整處理下市、暫停交易、全額交割、產業分類變動等。

3. **execution model 仍是 proxy**  
   目前有 OHLC 與部分 limit 資料，但沒有完整 order book、auction queue、partial fill。

4. **樣本期間偏短**  
   強研究期間主要是 2023–2025，足以作為作品集，但不足以宣稱長期穩定 alpha。

5. **sector dependence 明顯**  
   必須把策略定位為電子 / 半導體供應鏈相關，而不是全市場通用。

6. **winner concentration 明顯**  
   remove-winner 測試後 Sharpe 下降，代表 right-tail / regime sensitivity。

### 10.2 下一步優先順序

最高價值的下一步不是再做更多 K 線或參數搜尋，而是：

1. 取得 exact company-level announcement timestamps；
2. 建立更完整 historical universe / survivorship controls；
3. 使用真實 paper-trading cycle 驗證進場可行性；
4. 記錄 non-fill、slippage、limit-up queue risk；
5. 重新跑所有 promotion gates。

---

## 11. 面試問答準備

### Q1. 這個策略的核心想法是什麼？

台灣公司每月公布營收，這是高頻基本面更新。策略測試市場是否會對持續性正向月營收 surprise 反應不足，導致公布後 10–20 個交易日有後續 repricing。

### Q2. 為什麼不用單純 YoY 高成長？

高 YoY 可能早已被市場預期，也可能只是 base effect。SUR-style 因子更接近「超出預期的營收變化」，3M persistence 則降低單月雜訊。

### Q3. 如何避免 look-ahead bias？

研究中明確區分 revenue month、usable date、signal date、trade date。因為 exact timestamp 尚未完整，後期使用 next-open / delayed entry 等保守 proxy，不宣稱 same-day tradability。

### Q4. 最好的策略是哪個？

目前保留的 incumbent 是：

```text
sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D
```

它在 proxy 測試中 Sharpe 約 `2.40`，return 約 `167.5%`，MDD 約 `-7.9%`。

### Q5. 為什麼不直接上線？

因為 exact announcement timestamp、survivorship、execution fill、limit-up non-fill、sector concentration、winner dependence 都還沒完全通過 production gate。

### Q6. 這是全市場策略嗎？

不是。證據顯示它更像電子 / 半導體供應鏈的月營收 surprise repricing 策略。這不一定是缺點，但必須誠實描述。

### Q7. 你從這個專案學到什麼？

我學到：好的量化研究不是追最高 Sharpe，而是從市場結構提出假說，建立資料，設計反 look-ahead 規則，測試 robustness，保留 promising variants，並誠實拒絕尚未通過 gate 的策略。

---

## 12. Reproducibility

主要作品集資料夾：

```text
/Users/liuyenzhen/quant-research/tw_monthly_revenue/portfolio_project
```

主要研究報告：

```text
reports/promising_strategy_registry.md
reports/phase3_12_walkforward_sector_survival_report.md
reports/phase3_18_quiet_digestion_dynamic_sizing_report.md
reports/phase3_19_execution_realism_tradability_report.md
reports/phase3_24_delay_walkforward_oos_sector_stress_report.md
reports/phase3_25_exact_timing_paper_trading_schema_report.md
reports/phase3_26_official_ohlc_limit_parser_report.md
```

主要腳本：

```text
scripts/sur_factor_tests.py
scripts/signal_quality_search.py
scripts/walkforward_sector_survival.py
scripts/quiet_digestion_dynamic_sizing.py
scripts/execution_realism_tradability_gate.py
scripts/dynamic_sizing_walkforward_gate.py
scripts/exact_timing_delay_sensitivity_gate.py
scripts/delay_walkforward_oos_sector_stress.py
scripts/exact_timing_paper_trading_schema_gate.py
scripts/build_official_daily_ohlc_limit_from_raw.py
```

主要圖表：

```text
reports/charts/s1_nav_drawdown_zh.png
reports/charts/phase3_12_walkforward_oos_nav_zh.png
reports/charts/phase3_18_dynamic_sizing_nav_zh.png
```

---

## 13. 最終結論

這份研究目前最適合的定位是：

> 一個完整、誠實、具市場結構邏輯的台股月營收量化研究作品集。

它的優點是：

- 假說清楚；
- 研究流程完整；
- 使用台灣市場特有資訊；
- 有明確 benchmark 與 candidate registry；
- 有 robustness / OOS / sector / execution realism；
- 不誇大 live-readiness。

它尚未完成的地方是：

- exact announcement timestamp；
- production-grade universe / survivorship；
- 更完整 execution simulation；
- 多個月度 paper-trading cycle。

因此最專業的結論是：

> S1 是值得保留的 portfolio-grade v0.1 候選策略，但不是 production-ready trading system。下一階段應停止擴大參數搜尋，優先投入 exact timing、paper trading 與執行可行性驗證。
