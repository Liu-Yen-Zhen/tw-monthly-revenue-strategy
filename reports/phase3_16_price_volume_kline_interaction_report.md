# Phase 3.16 price/volume × K-line interaction diagnostics

Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。

## 本輪假說

月營收 SUR 後，成交值擴張本身不是 alpha；若放量同時收盤位置不弱、沒有長上影，才代表需求吸收供給並延續再定價。若放量伴隨長上影/弱收盤/大黑 K，則比較像事件擁擠或供給壓力，後續 20D 應較脆弱。

## Thresholds and data coverage

- abnormal turnover low/high tercile = 0.7705 / 1.3921
- entry upper-shadow high tercile = 0.3457; close-location low tercile = 0.2222; range low tercile = 0.0290; body high tercile = 0.6559
- scored rows with entry close/OHLC matched = 2002/2002 / 2002/2002

## Variant summary（20D fixed exit, inactive months counted as cash）

- `s1_fixed20_ohlc_baseline`: return=161.94%, Sharpe=1.55, MDD=-21.16%, active=29/30, avg_pos=7.27, trades=218
- `vol_high_no_supply`: return=183.77%, Sharpe=1.14, MDD=-24.45%, active=19/30, avg_pos=1.53, trades=46
- `vol_high_supply_pressure`: return=139.47%, Sharpe=1.57, MDD=-17.17%, active=27/30, avg_pos=2.43, trades=73
- `vol_low_quiet_digestion`: return=312.56%, Sharpe=1.77, MDD=-13.13%, active=26/30, avg_pos=1.87, trades=56
- `vol_high_no_supply_electronics`: return=100.93%, Sharpe=0.92, MDD=-24.28%, active=18/30, avg_pos=1.40, trades=42
- `vol_high_no_supply_non_electronics`: return=37.29%, Sharpe=0.56, MDD=-15.22%, active=4/30, avg_pos=0.23, trades=7
- `vol_high_no_supply_not_hot20d`: return=181.79%, Sharpe=1.14, MDD=-24.45%, active=19/30, avg_pos=1.50, trades=45
- `vol_high_large_black`: return=23.10%, Sharpe=0.56, MDD=-12.01%, active=8/30, avg_pos=0.57, trades=17

## Remove-winner stress

### s1_fixed20_ohlc_baseline
- remove 0: return=161.94%, Sharpe=1.55, MDD=-21.16%, trades=218
- remove 5: return=97.08%, Sharpe=1.16, MDD=-21.16%, trades=213
- remove 10: return=67.60%, Sharpe=0.96, MDD=-21.16%, trades=208
- remove 20: return=16.27%, Sharpe=0.38, MDD=-25.64%, trades=198
### vol_high_no_supply
- remove 0: return=183.77%, Sharpe=1.14, MDD=-24.45%, trades=46
- remove 5: return=29.52%, Sharpe=0.51, MDD=-24.45%, trades=41
- remove 10: return=-16.87%, Sharpe=-0.20, MDD=-26.81%, trades=36
- remove 20: return=-44.44%, Sharpe=-1.15, MDD=-44.44%, trades=26
### vol_high_supply_pressure
- remove 0: return=139.47%, Sharpe=1.57, MDD=-17.17%, trades=73
- remove 5: return=35.81%, Sharpe=0.66, MDD=-20.50%, trades=68
- remove 10: return=-7.80%, Sharpe=-0.04, MDD=-27.91%, trades=63
- remove 20: return=-45.33%, Sharpe=-1.14, MDD=-50.37%, trades=53
### vol_low_quiet_digestion
- remove 0: return=312.56%, Sharpe=1.77, MDD=-13.13%, trades=56
- remove 5: return=73.21%, Sharpe=0.99, MDD=-25.20%, trades=51
- remove 10: return=-16.71%, Sharpe=-0.51, MDD=-26.12%, trades=46
- remove 20: return=-41.23%, Sharpe=-1.57, MDD=-41.23%, trades=36
### vol_high_no_supply_electronics
- remove 0: return=100.93%, Sharpe=0.92, MDD=-24.28%, trades=42
- remove 5: return=13.43%, Sharpe=0.32, MDD=-24.28%, trades=37
- remove 10: return=-24.01%, Sharpe=-0.40, MDD=-36.54%, trades=32
- remove 20: return=-46.83%, Sharpe=-1.30, MDD=-46.83%, trades=22
### vol_high_no_supply_non_electronics
- remove 0: return=37.29%, Sharpe=0.56, MDD=-15.22%, trades=7
- remove 5: return=-20.60%, Sharpe=-0.63, MDD=-20.60%, trades=2
- remove 10: return=0.00%, Sharpe=NA, MDD=0.00%, trades=0
- remove 20: return=0.00%, Sharpe=NA, MDD=0.00%, trades=0
### vol_high_no_supply_not_hot20d
- remove 0: return=181.79%, Sharpe=1.14, MDD=-24.45%, trades=45
- remove 5: return=20.86%, Sharpe=0.42, MDD=-24.45%, trades=40
- remove 10: return=-28.08%, Sharpe=-0.53, MDD=-36.68%, trades=35
- remove 20: return=-44.65%, Sharpe=-1.17, MDD=-44.65%, trades=25
### vol_high_large_black
- remove 0: return=23.10%, Sharpe=0.56, MDD=-12.01%, trades=17
- remove 5: return=-28.40%, Sharpe=-0.78, MDD=-28.40%, trades=12
- remove 10: return=-40.57%, Sharpe=-1.44, MDD=-40.57%, trades=7
- remove 20: return=0.00%, Sharpe=NA, MDD=0.00%, trades=0

## Year split

### s1_fixed20_ohlc_baseline
- 2023: return=36.58%, Sharpe=3.41, MDD=-3.29%, active=6/6
- 2024: return=22.45%, Sharpe=1.03, MDD=-15.24%, active=12/12
- 2025: return=56.62%, Sharpe=1.51, MDD=-21.16%, active=11/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_high_no_supply
- 2023: return=30.96%, Sharpe=2.39, MDD=-1.98%, active=4/6
- 2024: return=82.88%, Sharpe=1.48, MDD=-17.78%, active=10/12
- 2025: return=18.49%, Sharpe=0.57, MDD=-24.45%, active=5/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_high_supply_pressure
- 2023: return=26.43%, Sharpe=2.42, MDD=-4.77%, active=6/6
- 2024: return=31.06%, Sharpe=1.24, MDD=-17.17%, active=11/12
- 2025: return=44.52%, Sharpe=1.54, MDD=-12.65%, active=10/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1
### vol_low_quiet_digestion
- 2023: return=62.68%, Sharpe=2.81, MDD=-1.49%, active=6/6
- 2024: return=36.26%, Sharpe=1.09, MDD=-13.13%, active=12/12
- 2025: return=86.11%, Sharpe=1.89, MDD=-3.68%, active=8/11
- 2026: return=0.00%, Sharpe=NA, MDD=0.00%, active=0/1

## Interpretation

- Promotion gate: a volume/K-line interaction must beat or clearly de-risk S1 fixed-20 and survive remove-top-winners; otherwise it remains diagnostic only.
- If `vol_high_no_supply` beats `vol_high_supply_pressure`, causal reading is demand absorption after revenue surprise. If it does not, entry-day K-line confirmation is not currently adding signal quality.
- Low average positions / few active months are treated as fragility, not Sharpe improvement.
- This remains daily OHLC proxy research: no intraday breakout, queue priority, exact announcement timestamp, or next-day limit non-fill simulation.

## Outputs

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_interaction_variants.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_interaction_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/price_volume_kline_interaction_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/phase3_16_price_volume_kline_interaction_report.md`
