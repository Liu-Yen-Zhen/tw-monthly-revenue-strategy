# Phase 2.1 月營收資料源攻關報告

本階段目標：在使用者沒有提供任何資料或 API token 的前提下，自行尋找免費、可程式化、可重複的台股月營收資料來源，並驗證能否支撐後續 MVP。

## 執行邊界

已遵守：

- 未實盤下單
- 未部署
- 未 git commit / git push
- 未刪除檔案
- 未安裝套件
- 未修改 Hermes repo 的 main branch
- 僅在獨立研究目錄 `/Users/liuyenzhen/quant-research/tw_monthly_revenue` 新增/更新研究檔案

## 新增/更新內容

新增：

- `scripts/fetch_latest_monthly_revenue_openapi.py`
- `data/raw/openapi/latest_monthly_revenue_openapi.json`
- `data/raw/openapi/latest_monthly_revenue_openapi.csv`
- `data/raw/openapi/latest_monthly_revenue_openapi_metadata.json`

更新：

- `scripts/probe_data_sources.py`
  - 補強 MOPS 安全阻擋頁判斷，避免 HTTP 200 被誤判為成功。

## 免費資料來源結論

### 1. TWSE OpenAPI：上市公司最新月營收

可用 endpoint：

```text
https://openapi.twse.com.tw/v1/opendata/t187ap05_L
```

驗證結果：成功。

本次抓到：

- 上市公司：1078 筆
- 資料年月：目前 endpoint 回傳的最新月份
- 欄位包含：
  - 出表日期
  - 資料年月
  - 公司代號
  - 公司名稱
  - 產業別
  - 當月營收
  - 上月營收
  - 去年當月營收
  - MoM
  - YoY
  - 累計營收
  - 累計 YoY
  - 備註

判斷：

> 可作為上市公司「最新月營收」的免費官方資料源。

限制：

> 不提供每家公司實際公告時間。`出表日期` 是資料表產製日期，不等於公司公告時間。

---

### 2. TPEx OpenAPI：上櫃公司最新月營收

可用 endpoint：

```text
https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O
```

驗證結果：成功。

本次抓到：

- 上櫃公司：887 筆

判斷：

> 可作為上櫃公司最新月營收的免費官方資料源。

限制同樣是：

> 沒有逐公司實際公告時間。

---

### 3. TPEx OpenAPI：興櫃公司最新月營收

可用 endpoint：

```text
https://www.tpex.org.tw/openapi/v1/t187ap05_R
```

驗證結果：成功。

本次抓到：

- 興櫃公司：349 筆

MVP 目前不建議納入興櫃，因為：

- 交易制度不同
- 流動性差異大
- 實盤可交易性較差

但資料源已確認可取得。

---

### 4. FinMind

目前環境沒有 `FINMIND_TOKEN`，測試回傳 HTTP 402。

判斷：

> 在沒有 token 的情況下，不把 FinMind 當作依賴。若未來可用，可作為交叉驗證或歷史資料加速器。

---

### 5. MOPS 月營收

MOPS 是權威來源，但目前 direct AJAX request 被安全性頁面阻擋。

更新後的探測腳本已能辨識：

```text
Security/anti-automation block page returned
```

判斷：

> 不建議把 MOPS direct AJAX 當成第一版自動化依賴。若要用 MOPS，需要 browser/session 流程、手動下載，或另外找官方靜態/歷史檔案來源。

---

## 目前已取得的實際資料

檔案：

```text
data/raw/openapi/latest_monthly_revenue_openapi.csv
```

總筆數：2314 筆

分市場：

- listed：1078
- otc：887
- emerging：349

標準化欄位：

- `market`
- `stock_id`
- `stock_name`
- `industry`
- `report_date_roc`
- `report_date`
- `revenue_month_roc`
- `revenue_month`
- `revenue_current_month`
- `revenue_previous_month`
- `revenue_same_month_last_year`
- `revenue_mom_pct`
- `revenue_yoy_pct`
- `revenue_ytd`
- `revenue_ytd_last_year`
- `revenue_ytd_yoy_pct`
- `note`
- `data_available_date`
- `announcement_date_quality`

其中：

```text
announcement_date_quality = report_date_only_not_company_timestamp
```

代表這不是逐公司公告時間，只能作為保守 MVP 的資料可用時間 proxy。

## 對策略 MVP 的重要影響

### 可以做的

目前可以做：

1. 最新一期月營收橫截面分析。
2. 上市 + 上櫃 + 興櫃最新月營收資料整合。
3. YoY / MoM / 產業排名 / 營收加速度的資料 schema 驗證。
4. 未來每月定期保存 OpenAPI snapshot，從現在開始累積 point-in-time 資料。
5. 建立 paper trading 候選清單流程。

### 暫時不能嚴格做的

目前還不能嚴格做：

1. 多年歷史月營收事件回測。
2. 逐公司公告日事件研究。
3. 精確公告後第 1 / 3 / 5 日進場測試。
4. 完整避免 survivorship bias 的長期研究。

原因：

- OpenAPI 提供的是最新月營收彙總，不是完整歷史序列。
- 沒有逐公司公告 timestamp。
- 歷史下市櫃 universe 仍未補齊。

## 建議後續路線

### 路線 A：先做「從今天開始」的 point-in-time paper research

這是目前最穩、最乾淨的路線：

1. 每月保存 OpenAPI 月營收 snapshot。
2. 每次 snapshot 都保留抓取時間與原始資料。
3. 使用 report_date 作為資料可用日 proxy。
4. 產生候選清單。
5. 進行 paper trading。

優點：

- 完全避免回補歷史造成的未來函數。
- 資料來源免費且官方。
- 可以逐月累積真實可用資料。

缺點：

- 一開始沒有歷史回測，只能從現在累積。

### 路線 B：歷史 MVP 回測採保守近似

若要先做歷史探索，可用：

```text
每月 11 日或月營收截止日後第一個交易日
```

作為統一 signal date。

優點：

- 可以先驗證大方向。
- 不需要逐公司公告日。

缺點：

- 不是真正事件時間。
- 早公告公司的初期 drift 會被低估。
- 晚公告或修正資料仍可能有誤差。

### 路線 C：繼續攻關 MOPS/歷史資料

方向：

1. 找到可用的 MOPS 靜態歷史 HTML 檔。
2. 或用 browser/session 模式取得 MOPS AJAX。
3. 或尋找合法第三方整理資料源。
4. 或手動下載一小段歷史資料建立 MVP。

優點：

- 可做多年歷史研究。

缺點：

- 成本較高。
- 可能受反爬、格式變動、公告日缺失影響。

## 我目前的建議

我建議採雙軌：

1. **立即建立 OpenAPI snapshot pipeline**
   - 從現在開始，每月保存官方最新月營收資料。
   - 這是最乾淨的 paper trading 資料來源。

2. **同時做歷史資料攻關**
   - 使用 MOPS / 官方歷史檔 / 其他免費來源補歷史。
   - 歷史回測先標記為 exploratory，不作正式 alpha 結論。

## 本階段結論

在沒有任何使用者提供資料的情況下，已找到並驗證免費官方資料路線：

- 上市月營收：TWSE OpenAPI `t187ap05_L`
- 上櫃月營收：TPEx OpenAPI `mopsfin_t187ap05_O`
- 興櫃月營收：TPEx OpenAPI `t187ap05_R`
- 上市日線：TWSE `STOCK_DAY`
- 上櫃日線：TPEx `tradingStock`
- 調整價輔助：Yahoo chart endpoint

這已足夠支撐「從現在開始累積 snapshot + paper trading」的研究流程，但還不足以做嚴格多年歷史事件回測。
