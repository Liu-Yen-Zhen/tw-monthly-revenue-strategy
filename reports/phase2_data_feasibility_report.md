# Phase 2 資料取得可行性報告：台股月營收驚喜策略

本報告為 Phase 2 最小安全版結果。目標是驗證資料來源可行性與主要風險，不進行策略回測、不最佳化參數、不下單。

## 執行邊界

已遵守限制：

- 未實盤下單
- 未部署
- 未 git commit / git push
- 未刪除檔案
- 未修改 Hermes repo 的 main branch
- 研究檔案放在獨立目錄：`/Users/liuyenzhen/quant-research/tw_monthly_revenue`

## 已建立內容

- `scripts/probe_data_sources.py`
  - 小型資料來源探測腳本。
  - 使用 Python 標準函式庫，未安裝套件。
  - 只做外部資料來源讀取與本機樣本輸出。

- `data/raw/probes/`
  - 儲存小型樣本回應。

- `reports/phase2_data_feasibility_report.md`
  - 本報告。

## 探測結果摘要

### 1. TWSE 日線價量

測試標的：`2330 台積電` 2024 年 1 月日成交資訊。

結果：可取得。

來源：

```text
https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20240101&stockNo=2330&response=json
```

可用欄位：

- 日期
- 成交股數
- 成交金額
- 開盤價
- 最高價
- 最低價
- 收盤價
- 漲跌價差
- 成交筆數

優點：

- 官方資料源。
- 適合上市股日線價量。

限制：

- 是未調整價格，不能直接處理除權息總報酬。
- 需要逐股票、逐月份抓取，批次效率需設計。
- 上櫃股需另外使用 TPEx 資料源。

判斷：

> 可作為正式日線資料主來源之一，但需要另外處理調整價與除權息。

---

### 2. Yahoo Finance 日線與調整價

測試標的：`2330.TW` 2024 年 1 月 chart endpoint。

結果：可取得。

來源：

```text
https://query1.finance.yahoo.com/v8/finance/chart/2330.TW
```

優點：

- 可取得 adjusted close。
- 使用方便。
- 適合 MVP 快速驗證報酬與除權息影響。

限制：

- 台股資料偶有缺漏或調整異常。
- 下市股資料不完整，容易有 survivorship bias。
- 不應作為正式研究唯一資料源。

判斷：

> 可作為 MVP 輔助價格資料，尤其用來初步比較調整價；正式研究仍需 TWSE/TPEx + 除權息資料驗證。

---

### 3. FinMind

測試資料：

- `TaiwanStockPrice`
- `TaiwanStockMonthRevenue`

結果：目前未通過，HTTP 402 Payment Required。

原因：

- 目前環境沒有 `FINMIND_TOKEN`。
- 該 API 或 dataset 可能需要 token / 權限 / 付費方案。

判斷：

> FinMind 仍是 MVP 很好的候選資料源，但目前環境無法直接使用。若提供 token，可再次驗證月營收欄位是否包含實際公告日；如果沒有公告日，只能作為營收月份資料，不能直接用於事件回測。

---

### 4. MOPS 月營收

測試 endpoint：

```text
https://mops.twse.com.tw/mops/web/ajax_t21sc03
```

結果：HTTP 200，但回傳內容為安全性阻擋頁面。

觀察：

- MOPS 是權威資料源。
- 直接程式 POST 可能被安全機制阻擋。
- 需要更完整的 session / cookie / browser-like 流程，或改用 TWSE/TPEx 彙總資料、官方下載檔、手動匯出、或其他合法資料源。

判斷：

> MOPS 是正式研究的權威來源，但自動化抓取需要額外處理。短期 MVP 不建議卡在 MOPS 反爬蟲細節，應先用可穩定取得的官方或替代來源驗證研究流程。

---

## 資料來源可行性結論

目前可立即使用：

1. **TWSE 日線價量**
   - 上市股可用。
   - 無調整價，需要除權息處理。

2. **Yahoo Finance 價格資料**
   - 可輔助 adjusted close。
   - 適合 MVP，不適合唯一正式來源。

目前需要補條件：

1. **FinMind**
   - 需要 token / 權限。
   - 若可用，會大幅加快 MVP。

2. **MOPS 月營收**
   - 權威但直接抓取受阻。
   - 需改用 browser/session 流程或官方下載替代方案。

仍待驗證：

1. TPEx 上櫃日線資料。
2. TWSE/TPEx 月營收彙總是否有穩定 JSON/CSV endpoint。
3. 月營收資料是否包含實際公告日與公告時間。
4. 歷史上市/下市 universe 是否能完整取得。
5. 除權息調整資料來源。

## 對策略設計的影響

### 1. 第一版不應直接宣稱正式回測

因為目前最大缺口是：

- 實際月營收公告日
- 調整價 / 除權息
- 下市股與歷史 universe

若缺這些資料，回測只能算 MVP / exploratory analysis。

### 2. MVP 可採保守訊號日期

如果暫時拿不到每家公司實際公告日，可先用：

```text
每月 11 日或月營收公告截止日後第一個交易日
```

作為統一 signal date。

這比使用營收月份月底安全，但會犧牲部分事件反應速度。

### 3. 價格資料建議雙軌

MVP：

- Yahoo adjusted close 快速計算報酬。
- TWSE 官方日線作成交量、成交值、OHLC 驗證。

正式版：

- TWSE/TPEx 原始價格 + 官方除權息事件，自行建立 total return price。

### 4. 月營收資料源是下一個關鍵

Phase 3 前必須決定：

- 提供 FinMind token；或
- 使用 MOPS/TWSE/TPEx 官方下載；或
- 先手動匯出小樣本；或
- 使用其他合法資料供應源。

## 建議下一步

建議進入 Phase 2.1：月營收資料源攻關。

優先順序：

1. 若你有 FinMind token，先用 FinMind 驗證欄位完整性。
2. 若沒有 token，尋找 TWSE/TPEx 月營收官方彙總 endpoint 或可下載檔。
3. 若官方自動化受阻，先建立小樣本手動下載流程，驗證 schema 與防未來函數規則。
4. 等月營收資料可穩定取得後，再進 Phase 3 資料清理。

## 本階段結論

Phase 2 最小探測結果顯示：

- 價格資料來源可行。
- 調整價可先用 Yahoo 輔助，但正式研究需驗證。
- FinMind 在目前環境不可用，缺 token / 權限。
- MOPS 權威但直接自動化請求被安全頁阻擋。
- 下一個瓶頸是月營收資料的穩定、合法、可重複取得，尤其是公告日欄位。
