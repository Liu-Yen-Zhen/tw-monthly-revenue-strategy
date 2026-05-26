# Phase 3.13 價量 / K 線狀態研究

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 本輪假說

月營收 SUR 後，若股價/成交值顯示市場開始重新定價，可能提高後續 20D 勝率；但若成交值過度擴張，也可能代表短線擁擠與已反映。因此先測 close/turnover 可驗證的三種狀態：成交值擴張、成交值未擴張/量縮整理、低 20D run-up 的 quiet underreaction。

## Data audit / 限制

- `daily_market_history_2023_present.csv` 只有 `trade_date, market, stock_id, stock_name, close, turnover_value`。
- 因此本輪不能嚴格測 K 線長上影、長黑、ATR 壓縮、盤中突破、漲跌停 non-fill；這些需要 OHLC、成交量股數、漲跌停價與公告時間。
- 本輪 volume proxy 使用進場日前 20D/120D 成交值比 (`abnormal_turnover`)；它比較像公告前後可觀察的注意力/擁擠 proxy，不是盤中放量突破。
- `s1_post5d_close_mom` 為避免 look-ahead，先觀察 proxy entry 後 5 個收盤，若 5D close momentum 高於中位數，才把進場日延後到第 5 個交易日；仍只是 close-price proxy。

## Thresholds

- `abnormal_turnover_low_tercile` = 0.7705
- `abnormal_turnover_high_tercile` = 1.3921
- `pre_ret_20d_low_tercile` = -0.0317
- `pre_ret_20d_high_tercile` = 0.0714
- `post5d_close_ret_median` = 0.0035
- `sur_3m_high_tercile` = 0.4965
- `momentum_120_20_high_tercile` = 0.2880

## Variant summary（20D fixed exit proxy）

- `s1_sur3_no_high_mom`: return=161.94%, Sharpe=1.58, MDD=-21.16%, win=75.86%, avg positions=7.52, trades=218
- `s1_plus_vol_expansion`: return=236.67%, Sharpe=1.65, MDD=-27.79%, win=70.37%, avg positions=4.26, trades=115
- `s1_plus_vol_mid`: return=79.56%, Sharpe=0.89, MDD=-23.15%, win=65.52%, avg positions=4.55, trades=132
- `s1_plus_vol_low`: return=138.74%, Sharpe=1.24, MDD=-28.76%, win=72.41%, avg positions=4.07, trades=118
- `s1_quiet_underreaction`: return=88.45%, Sharpe=0.96, MDD=-27.20%, win=62.07%, avg positions=5.66, trades=164
- `s1_post5d_close_mom`: return=109.27%, Sharpe=1.16, MDD=-27.21%, win=71.43%, avg positions=5.50, trades=154

## Remove top winners stress

### s1_sur3_no_high_mom
- remove 0: return=161.94%, Sharpe=1.58, MDD=-21.16%, trades=218
- remove 5: return=97.08%, Sharpe=1.18, MDD=-21.16%, trades=213
- remove 10: return=67.60%, Sharpe=0.98, MDD=-21.16%, trades=208
- remove 20: return=16.27%, Sharpe=0.39, MDD=-25.64%, trades=198
### s1_plus_vol_expansion
- remove 0: return=236.67%, Sharpe=1.65, MDD=-27.79%, trades=115
- remove 5: return=70.66%, Sharpe=0.93, MDD=-27.79%, trades=110
- remove 10: return=29.01%, Sharpe=0.54, MDD=-27.79%, trades=105
- remove 20: return=-18.42%, Sharpe=-0.19, MDD=-34.71%, trades=95
### s1_plus_vol_mid
- remove 0: return=79.56%, Sharpe=0.89, MDD=-23.15%, trades=132
- remove 5: return=32.95%, Sharpe=0.54, MDD=-24.23%, trades=127
- remove 10: return=1.41%, Sharpe=0.16, MDD=-24.74%, trades=122
- remove 20: return=-33.80%, Sharpe=-0.57, MDD=-37.55%, trades=112
### s1_plus_vol_low
- remove 0: return=138.74%, Sharpe=1.24, MDD=-28.76%, trades=118
- remove 5: return=85.57%, Sharpe=0.93, MDD=-34.24%, trades=113
- remove 10: return=56.40%, Sharpe=0.74, MDD=-34.24%, trades=108
- remove 20: return=-30.53%, Sharpe=-0.56, MDD=-41.89%, trades=98
### s1_quiet_underreaction
- remove 0: return=88.45%, Sharpe=0.96, MDD=-27.20%, trades=164
- remove 5: return=48.93%, Sharpe=0.70, MDD=-32.75%, trades=159
- remove 10: return=25.98%, Sharpe=0.50, MDD=-34.08%, trades=154
- remove 20: return=-4.95%, Sharpe=0.03, MDD=-38.73%, trades=144

## Year split / OOS-like sanity

### s1_sur3_no_high_mom
- 2023: return=24.45%, Sharpe=2.78, MDD=-3.29%, win=80.00%
- 2024: return=21.10%, Sharpe=0.99, MDD=-15.24%, win=66.67%
- 2025: return=73.80%, Sharpe=1.74, MDD=-21.16%, win=83.33%
### s1_plus_vol_expansion
- 2023: return=24.01%, Sharpe=2.30, MDD=-4.77%, win=80.00%
- 2024: return=45.05%, Sharpe=1.71, MDD=-16.85%, win=63.64%
- 2025: return=87.17%, Sharpe=1.59, MDD=-27.79%, win=72.73%
### s1_plus_vol_mid
- 2023: return=8.61%, Sharpe=0.98, MDD=-5.97%, win=40.00%
- 2024: return=-2.29%, Sharpe=0.06, MDD=-23.15%, win=66.67%
- 2025: return=69.20%, Sharpe=1.47, MDD=-21.27%, win=75.00%
### s1_plus_vol_low
- 2023: return=44.90%, Sharpe=3.40, MDD=-0.43%, win=80.00%
- 2024: return=25.94%, Sharpe=0.95, MDD=-11.17%, win=66.67%
- 2025: return=30.83%, Sharpe=0.85, MDD=-25.89%, win=75.00%
### s1_quiet_underreaction
- 2023: return=22.08%, Sharpe=2.67, MDD=-3.20%, win=80.00%
- 2024: return=4.45%, Sharpe=0.29, MDD=-14.43%, win=58.33%
- 2025: return=47.80%, Sharpe=1.09, MDD=-24.18%, win=58.33%

## Sector context

### s1_sur3_no_high_mom
- all: return=161.94%, Sharpe=1.58, MDD=-21.16%, avg positions=7.52
- electronics_only: return=230.62%, Sharpe=1.65, MDD=-21.16%, avg positions=6.24
- non_electronics: return=107.75%, Sharpe=1.60, MDD=-7.10%, avg positions=1.68
- semiconductor_only: return=437.34%, Sharpe=2.26, MDD=-24.39%, avg positions=2.63
- no_semiconductor: return=61.10%, Sharpe=0.85, MDD=-22.80%, avg positions=5.25
### s1_plus_vol_expansion
- all: return=236.67%, Sharpe=1.65, MDD=-27.79%, avg positions=4.26
- electronics_only: return=209.09%, Sharpe=1.61, MDD=-27.02%, avg positions=3.62
- non_electronics: return=56.26%, Sharpe=0.92, MDD=-29.09%, avg positions=1.40
- semiconductor_only: return=242.47%, Sharpe=1.61, MDD=-27.08%, avg positions=1.89
- no_semiconductor: return=111.74%, Sharpe=1.05, MDD=-27.79%, avg positions=2.93
### s1_quiet_underreaction
- all: return=88.45%, Sharpe=0.96, MDD=-27.20%, avg positions=5.66
- electronics_only: return=107.12%, Sharpe=1.00, MDD=-29.29%, avg positions=4.96
- non_electronics: return=-39.88%, Sharpe=-0.84, MDD=-45.11%, avg positions=1.47
- semiconductor_only: return=242.81%, Sharpe=1.75, MDD=-17.76%, avg positions=2.54
- no_semiconductor: return=57.13%, Sharpe=0.74, MDD=-36.44%, avg positions=3.68

## Interpretation

- 成交值擴張不是免費午餐：若 high abnormal turnover 的 Sharpe/MDD 或 remove-winner 結果沒有優於 S1 proxy，就代表公告前/公告附近大量成交可能已反映 surprise，不能把『放量』簡化成追價確認。
- quiet underreaction 若改善 MDD 或 remove-winner 後存活，前因後果較合理：基本面 surprise 已出現，但價格與成交值尚未過熱，後續由延遲反應與法人/散戶再平衡推動。
- 若 sector split 顯示 electronics/semiconductor 顯著優於 non-electronics，應繼續把策略定位為 electronics / semiconductor supply-chain revenue surprise，而不是全市場價量 alpha。
- K 線型態研究暫不推進到 candlestick mining；沒有 OHLC 時，長上影/長黑/ATR breakout 都會變成錯誤精度。

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_variants.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_sector.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_top_trades.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_summary.json`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_13_price_volume_kline_research_report.md`
