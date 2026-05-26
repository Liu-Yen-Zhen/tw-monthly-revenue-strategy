# Phase 3.25 exact-timing audit and paper-trading schema

Research-only；沒有 live trading、沒有 broker、沒有下單；本輪只新增 scripts/reports/data/processed 研究產出。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because Phase 3.19–3.24 showed S1/quiet/delay-aware variants lose headline quality after conservative execution, sector, and remove-winner gates, therefore the highest-value next step is not another parameter grid but an exact-timing and paper-fill audit. If exact company-level timestamps and observable fillability are missing, the strategy should remain an interview/research portfolio piece rather than production alpha.

### 前因後果

- Monthly revenue surprise alpha depends on when information becomes public and whether crowded surprise names can actually be bought after disclosure.
- Phase 3.24 showed selected boost/delay rules remain semiconductor/right-tail sensitive, so better Sharpe-chasing would likely overfit unless the operational data gate is solved first.

### 檢查

- Audited revenue columns: `market_code, market, revenue_month, usable_date_proxy, stock_id, stock_name, industry, revenue_current_month, revenue_previous_month, revenue_same_month_last_year, revenue_mom_pct, revenue_yoy_pct, revenue_ytd, revenue_ytd_last_year, revenue_ytd_yoy_pct, note, unit, announcement_date_quality, source_url, raw_cache_path`.
- Audited processed daily columns: `trade_date, market, stock_id, stock_name, close, turnover_value`.
- Audited raw official daily JSON OHLC/limit field presence: tpex: files 885, tables 885, open tables 885, limit-up tables 885; twse: files 48, tables 480, open tables 48, limit-up tables 0.
- Created a paper-trading execution-log schema and 2026 checklist for signal timestamp, planned entry, observed OHLC, limit-up non-fill flags, ADV capacity, slippage, and deviations from backtest.

### 結果

- Historical revenue table rows audited: `106785`; announcement quality: `monthly_summary_no_company_timestamp:106785`. This confirms current historical data is monthly-summary/proxy timing, not exact company timestamp data.
- Processed daily market table has close and turnover only; it does **not** preserve open/high/low/limit fields needed for executable fill validation.
- Raw official daily JSON files contain OHLC broadly in the audited equity tables; TPEx raw tables also expose next-day limit-up/down fields, while the current local TWSE raw sample does **not** expose next-day limit fields in the same way. Future scripts should parse raw JSON into an OHLC/limit processed table where fields exist, and explicitly mark missing TWSE limit fields rather than assuming them.
- Phase 3.24 robustness context retained:
  - `train_2023_2024_test_2025`: all Sharpe 1.17; semi-only 2.59; no-semi 0.31; remove-top-5 Sharpe 0.37.
  - `train_2023_test_2024`: all Sharpe 0.76; semi-only 1.52; no-semi -0.56; remove-top-5 Sharpe -0.50.

### 修正與結論

- 修正了什麼：先前 Phase 3.19–3.24 已用 next-open/delay/limit-up exclusion 做保守 proxy，但仍可能讓人誤以為 exact tradability 已過關；本輪明確 audit 欄位並建立 paper-trading schema。
- 為什麼先前不夠好：`usable_date_proxy` + official open proxy 不能替代 company-level announcement timestamp、實際排隊成交、暫停交易/撮合狀態與盤中可成交量。
- 修正後結論是否改變：promotion 結論不變且更保守。S1 保留為 portfolio-grade v0.1；quiet/delay-aware boost 僅是 research-only timing/sizing diagnostic，不升級。

### 缺陷

- 本輪不連外抓新 MOPS timestamp；只是基於現有 local artifacts 做 data audit/schema。
- Raw JSON 欄位存在不代表所有歷史列都已正規化，仍需建立 official OHLC/limit processed table 並 join 到 signal/execution dates。
- Paper schema 不是 alpha 證據；至少需要多個 2026 月營收發布週期的實際 paper fills 才能評估 operational feasibility。

### 下一步

1. 寫 raw official daily JSON → processed OHLC/limit table parser，保留 open/high/low/close/成交金額/次日漲跌停價。
2. 對 2026 最新月營收候選做 paper-trading log：data_available_at、planned_entry、observed_open、limit-up flag、non-fill reason、ADV cap。
3. 若 exact timestamp source 無法穩定取得，報告中固定使用 conservative next-trading-day-after-observed-data rule，不宣稱可當日交易。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/exact_timing_paper_trading_data_audit.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/paper_trading_execution_log_schema.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/paper_trading_execution_checklist_2026.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_25_exact_timing_paper_trading_schema_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
