# Phase 3.26 official OHLC/limit parser from local raw JSON

Research-only；使用既有 local raw official JSON；沒有 live trading、broker、network、下單。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because Phase 3.25 found the processed daily CSV is close/turnover-only while raw official JSON may contain OHLC/limit fields, therefore parsing those raw files into a normalized table should reduce execution-realism blind spots before any further strategy promotion.

### 前因後果

- S1 and quiet/delay-aware variants are sensitive to entry timing, limit-up non-fill, and ADV capacity.
- Close-only processed data forces proxy exits/entries; normalized OHLC allows explicit next-open, intraday range, and limit-field audits where fields exist.

### 檢查

- Parsed `933` local raw JSON files under `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/raw/market_history_daily`.
- Normalized columns: trade_date, market, stock_id/name, open/high/low/close, turnover_value, shares_traded, next_limit_up/down, source_file.

### 結果

- `listed`: rows=58002, days=48 (2023-01-03→2026-01-08), complete_OHLC=57345, turnover=58002, next_limit_up=0, unique_stocks=1360.
- `otc`: rows=764248, days=814 (2023-01-03→2026-05-22), complete_OHLC=751228, turnover=764248, next_limit_up=764248, unique_stocks=1047.

### 修正與結論

- 修正了什麼：Phase 3.25 只做欄位 audit；本輪把 raw official JSON 實際正規化成可 join 的 OHLC/limit research table。
- 為什麼先前不夠好：只知道欄位存在仍不能直接用於 entry/open、range、capacity 與 limit-up non-fill 檢查。
- 修正後結論是否改變：不改變 promotion 結論，但改善後續 execution realism workflow。TPEx 可直接用 next-day limit 欄位；TWSE 在目前 local raw 樣本仍缺 next-day limit 欄位，必須標記為 missing/proxy。

### 缺陷

- Current local TWSE raw coverage is sparse relative to TPEx and parsed TWSE limit fields are absent.
- Parser keeps ETFs/bonds/common stocks; strategy universe filtering still must happen when joining to SUR signals.
- Official limit-up fields are next-day limits in TPEx files; matching to entry-day non-fill requires careful date alignment.

### 下一步

1. Join `official_daily_ohlc_limit_from_raw.csv` to Phase 3.19/3.21 trade flags and replace close-only proxy where raw open is available.
2. Add date alignment for TPEx next-day limit: previous file's next_limit_up should be the current trade day's limit-up reference.
3. Source/parse TWSE official limit-up/down fields or mark TWSE limit non-fill as unavailable in paper logs.

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/official_daily_ohlc_limit_from_raw.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/official_daily_ohlc_limit_from_raw_summary.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_26_official_ohlc_limit_parser_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
