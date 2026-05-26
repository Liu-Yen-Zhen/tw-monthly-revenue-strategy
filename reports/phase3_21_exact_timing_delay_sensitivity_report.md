# Phase 3.21 exact-timing delay sensitivity gate

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because the current historical monthly-revenue table has `monthly_summary_no_company_timestamp` rather than exact company-level announcement timestamps, therefore even the conservative 11th/next-trading-day signal may still mis-time first tradability. If S1 alpha is robust delayed repricing rather than same-day execution bias, performance should not collapse when execution is shifted later by 1–3 trading days using official opens and excluding possible limit-up non-fills.

### 前因後果

- Phase 3.19 corrected execution price and limit-up assumptions, but still used the existing signal date proxy.
- 本輪不硬編 exact timestamp；只做 delay sensitivity：從現有 S1 proxy signal index 延後 0/1/2/3 個交易日，以 official open 進場，20D close 出場，成本 1.0%/1.5%，排除 possible limit-up non-fill。

### 檢查

- Delay trades built: 872 rows across 4 delays; months cash-counted: 30.
- raw `twse` OHLC coverage=100.00%, next-limit coverage=0.00%.
- raw `tpex` OHLC coverage=100.00%, next-limit coverage=100.00%.

### 結果：1.0% cost / official open / exclude limit-up risk

#### equal_s1
- delay=0 trading days: return=150.44%, Sharpe=1.40, MDD=-20.66%, active=29/30, avg_pos=7.27, excluded_flags=0
- delay=1 trading days: return=99.78%, Sharpe=1.16, MDD=-26.21%, active=29/30, avg_pos=7.27, excluded_flags=0
- delay=2 trading days: return=133.01%, Sharpe=1.30, MDD=-28.63%, active=29/30, avg_pos=7.27, excluded_flags=0
- delay=3 trading days: return=123.66%, Sharpe=1.39, MDD=-19.38%, active=29/30, avg_pos=7.27, excluded_flags=0
#### boost_quiet_no_large_black_150
- delay=0 trading days: return=161.66%, Sharpe=1.46, MDD=-20.66%, active=29/30, avg_pos=7.27, excluded_flags=0
- delay=1 trading days: return=111.91%, Sharpe=1.24, MDD=-24.86%, active=29/30, avg_pos=7.27, excluded_flags=0
- delay=2 trading days: return=146.03%, Sharpe=1.37, MDD=-27.78%, active=29/30, avg_pos=7.27, excluded_flags=0
- delay=3 trading days: return=133.98%, Sharpe=1.45, MDD=-18.33%, active=29/30, avg_pos=7.27, excluded_flags=0
#### liq100_equal_s1
- delay=0 trading days: return=146.71%, Sharpe=1.28, MDD=-21.89%, active=29/30, avg_pos=5.63, excluded_flags=0
- delay=1 trading days: return=104.83%, Sharpe=1.08, MDD=-27.49%, active=29/30, avg_pos=5.63, excluded_flags=0
- delay=2 trading days: return=128.57%, Sharpe=1.17, MDD=-31.09%, active=29/30, avg_pos=5.63, excluded_flags=0
- delay=3 trading days: return=113.89%, Sharpe=1.19, MDD=-22.59%, active=29/30, avg_pos=5.63, excluded_flags=0

### 成本壓力：boost_quiet_no_large_black_150 at delay=1

- cost=1.0%: return=111.91%, Sharpe=1.24, MDD=-24.86%
- cost=1.5%: return=83.83%, Sharpe=1.03, MDD=-28.29%

### 修正與結論

- 修正了什麼：Phase 3.19 已確認 OHLC/limit 欄位並做 next-open proxy；本輪進一步把『exact announcement timestamp 不存在』轉成延後 0–3 交易日的 timing stress。
- 為什麼先前不夠好：只看 next-open 仍可能把公司實際公告日、公告時間、或資料取得延遲估得太樂觀。
- 修正後結論是否改變：沒有 promotion。delay=1 下 quiet boost 為 `111.91%` / Sharpe `1.24`，equal S1 為 `99.78%` / Sharpe `1.16`；delay=3 下 quiet boost 為 `133.98%` / Sharpe `1.45`。結果支持『訊號不是完全依賴當日 close』，但 Sharpe 仍在 research-candidate 區間，不足以升格 production。

### 缺陷

- Delay stress 不是 exact timestamp；公司可能在 10 日前後不同時間公告，真正 earliest tradable date 可能比 proxy 早或晚。
- Official open fill 仍沒有 opening auction queue、partial fill、order book depth、limit-up 排隊資料。
- 延後進場同時改變 exit date，仍是 fixed 20 trading-day close-price proxy。
- 現有樣本主要 2023–2025，可驗證年份不足。

### 下一步

1. 尋找 MOPS/TWSE 公司別月營收公告 timestamp 或至少公告日期欄位，重建 signal_date / earliest_trade_date。
2. 對 delay sensitivity 加入 remove-top-winners / sector survival，確認不是少數半導體供應鏈 winners 撐住。
3. 若 exact timestamp 取得後，多數 S1 trades 實際只能 delay>=2，則以 delay>=2 為新的 incumbent gate 重新跑 Phase 3.20。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/exact_timing_delay_sensitivity_summary.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/exact_timing_delay_sensitivity_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/exact_timing_delay_sensitivity_trade_flags.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_21_exact_timing_delay_sensitivity_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
