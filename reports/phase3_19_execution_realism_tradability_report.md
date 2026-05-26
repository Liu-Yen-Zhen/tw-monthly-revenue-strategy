# Phase 3.19 execution realism / exact tradability gate

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步

### 假說

Because Taiwan monthly-revenue SUR repricing often occurs immediately after conservative data-availability dates, therefore prior entry-close proxy results may overstate implementability if the first tradable print is the next day open/close, if entry is near limit-up, or if realistic all-in costs are closer to 1.0%–1.5%. Quiet-digestion sizing should only survive if its small Phase 3.18 improvement persists after those execution frictions.

### 前因後果

- Phase 3.18 的 `boost_quiet_no_large_black_150` 只小幅改善 S1 full-sample Sharpe/return；這可能是 delayed repricing signal，也可能只是 entry-close / low-cost proxy bias。
- 真實研究 gate 應先問：資料是否真的有 OHLC / limit 欄位？若有，用 next-day open/close 與 limit-up non-fill proxy 壓力測試；若無，必須標成 audit，不能硬編。

### 檢查：欄位與可成交性 audit

- `s1_trades_entry_close`: rows=218, OHLC coverage=100.00%, current-up-limit coverage=100.00%, possible limit-up non-fill flags=2
- `s1_trades_next_close`: rows=218, OHLC coverage=100.00%, current-up-limit coverage=100.00%, possible limit-up non-fill flags=6
- `s1_trades_next_open`: rows=218, OHLC coverage=100.00%, current-up-limit coverage=100.00%, possible limit-up non-fill flags=0
- `raw_twse`: raw_files=48, common_stock_rows=47748, OHLC coverage=100.00%, next-limit coverage=0.00%
- `raw_tpex`: raw_files=885, common_stock_rows=667388, OHLC coverage=100.00%, next-limit coverage=100.00%

### 結果：核心比較（inactive months counted as cash）

- `equal_s1 | entry_close | cost=0.7% | all`: return=161.94%, Sharpe=1.55, MDD=-21.16%, active=29/30, avg_pos=7.27, remaining_limit_flags=2
- `boost_quiet_no_large_black_150 | entry_close | cost=0.7% | all`: return=174.35%, Sharpe=1.62, MDD=-21.16%, active=29/30, avg_pos=7.27, remaining_limit_flags=2
- `liq100_equal_s1 | entry_close | cost=0.7% | all`: return=162.89%, Sharpe=1.41, MDD=-23.09%, active=29/30, avg_pos=5.63, remaining_limit_flags=2
- `equal_s1 | next_open | cost=1.0% | exclude_limitup_risk`: return=99.78%, Sharpe=1.16, MDD=-26.21%, active=29/30, avg_pos=7.27, remaining_limit_flags=0
- `boost_quiet_no_large_black_150 | next_open | cost=1.0% | exclude_limitup_risk`: return=111.91%, Sharpe=1.24, MDD=-24.86%, active=29/30, avg_pos=7.27, remaining_limit_flags=0
- `liq100_equal_s1 | next_open | cost=1.0% | exclude_limitup_risk`: return=104.83%, Sharpe=1.08, MDD=-27.49%, active=29/30, avg_pos=5.63, remaining_limit_flags=0

### 成本壓力：boost_quiet_no_large_black_150（entry_close / all fills）

- cost=0.7%: return=174.35%, Sharpe=1.62, MDD=-21.16%
- cost=1.0%: return=152.14%, Sharpe=1.50, MDD=-21.46%
- cost=1.5%: return=118.92%, Sharpe=1.29, MDD=-21.96%

### Entry timing 壓力：boost_quiet_no_large_black_150（cost=1.0%, exclude limit-up risk）

- entry_close: return=134.91%, Sharpe=1.43, MDD=-21.46%, avg_pos=7.20
- next_close: return=130.28%, Sharpe=1.29, MDD=-27.56%, avg_pos=7.07
- next_open: return=111.91%, Sharpe=1.24, MDD=-24.86%, avg_pos=7.27

### Liquidity / capacity proxy

Capacity is estimated as monthly portfolio capital capped by each position's `participation × avg_turnover_20d / normalized_weight`; this is a turnover-value proxy, not share-level order-book capacity.

#### equal_s1 | entry_close | cost=0.7% | all
- ADV 1%: median capacity=5,216,448 NTD, p10=3,614,397 NTD
- ADV 3%: median capacity=15,649,345 NTD, p10=10,843,192 NTD
- ADV 5%: median capacity=26,082,242 NTD, p10=18,071,986 NTD
#### boost_quiet_no_large_black_150 | entry_close | cost=0.7% | all
- ADV 1%: median capacity=5,102,269 NTD, p10=3,193,210 NTD
- ADV 3%: median capacity=15,306,808 NTD, p10=9,579,629 NTD
- ADV 5%: median capacity=25,511,347 NTD, p10=15,966,048 NTD
#### liq100_equal_s1 | entry_close | cost=0.7% | all
- ADV 1%: median capacity=7,609,184 NTD, p10=5,125,891 NTD
- ADV 3%: median capacity=22,827,551 NTD, p10=15,377,673 NTD
- ADV 5%: median capacity=38,045,919 NTD, p10=25,629,454 NTD

### 修正與結論

- 修正了什麼：Phase 3.18 只在 fixed-20 entry-close proxy 下討論 quiet sizing；本輪新增 OHLC/limit 欄位 audit、next-day open/close、limit-up non-fill exclusion、0.7%/1.0%/1.5% 成本與 ADV participation capacity proxy。
- 為什麼先前不夠好：entry close + 單一成本沒有回答『營收公告後第一個可成交價格』與『漲停買不到』問題，也沒有把 liquidity>=100m 與資金容量分開看。
- 修正後結論是否改變：S1 仍是 incumbent；quiet boost 在原始 proxy 下為 `174.35%` / Sharpe `1.62` vs S1 `161.94%` / Sharpe `1.55`，但在更保守 `next_open + 1.0% cost + exclude limit-up risk` 下為 `111.91%` / Sharpe `1.24`，因此仍只能保留為 research-only sizing hypothesis，不能 promotion。
- Liquidity>=100m helps answer capacity but changes selection/exposure; it should remain robustness comparator, not automatically superior alpha.

### 缺陷

- `current_up_limit` 是由前一交易日官方 `次日漲停價` 推回，仍是 proxy；真實能否成交取決於盤中委託簿、排隊、撮合與公告時間。
- Open fill assumes official open is accessible; no order-book, no opening auction imbalance, no partial-fill model.
- `avg_turnover_20d` capacity proxy uses traded value, not shares/price-level depth；對小型股仍可能過度樂觀。
- Monthly revenue available date仍用保守 11 日/next trading day proxy；尚未逐筆 exact announcement timestamp。

### 下一步

1. Phase 3.20: walk-forward / train-test dynamic sizing：只允許在 train 決定 quiet/large-black sizing rule，再看 test 是否維持。
2. Exact timing gate：補 MOPS/TWSE announcement timestamp 或至少公司別公告日，重算 signal date / earliest trade date。
3. Execution gate：若可取得 limit-up/down and OHLC 全期間資料，加入 open gap、停牌、漲停連續日、非成交量異常的 non-fill stress。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_tradability_summary.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_tradability_monthly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_tradability_audit.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_tradability_capacity.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_tradability_trade_flags.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_19_execution_realism_tradability_report.md`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/promising_strategy_registry.md`
