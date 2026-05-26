# Phase 4.1 — FRR margin-deleveraging short-horizon research

Research-only. No live trading, no broker/API order routing, and no investment recommendation.

## Hypothesis

Because Taiwan short-horizon retail leverage can create forced supply, strong monthly-revenue surprise stocks that have already experienced margin deleveraging may rebound after the selling pressure is absorbed. The test enters only after the margin data is observable (next trading day open / delayed variants).

## Data audit

- Margin feature rows: `522458`; enriched SUR core rows: `375`; selected FRR signals: `180`; trades: `1350`.
- Thresholds: sur3_q70 `1.2464`, margin_pct_q35 `-3.00%`, deleveraging_q65 `0.0455`, abnormal_turnover_q60 `1.40`.

## Top first-pass rows

- `frr3_volume_absorption` delay `3` hold `20D`: return `251.44%`, Sharpe `1.55`, MDD `-17.62%`, trades `21`, active months `16`.
- `frr3_volume_absorption` delay `2` hold `20D`: return `223.77%`, Sharpe `1.43`, MDD `-18.99%`, trades `21`, active months `16`.
- `frr3_volume_absorption` delay `1` hold `20D`: return `179.08%`, Sharpe `1.39`, MDD `-16.56%`, trades `21`, active months `16`.
- `frr1_basic_deleveraging` delay `3` hold `20D`: return `184.77%`, Sharpe `1.32`, MDD `-22.25%`, trades `42`, active months `21`.
- `frr1_basic_deleveraging` delay `1` hold `20D`: return `159.39%`, Sharpe `1.26`, MDD `-18.69%`, trades `42`, active months `21`.
- `frr2_no_catch_falling_knife` delay `3` hold `10D`: return `78.71%`, Sharpe `1.18`, MDD `-15.18%`, trades `36`, active months `18`.
- `frr1_basic_deleveraging` delay `2` hold `20D`: return `157.71%`, Sharpe `1.16`, MDD `-27.50%`, trades `42`, active months `21`.
- `frr2_no_catch_falling_knife` delay `3` hold `20D`: return `132.55%`, Sharpe `1.13`, MDD `-17.75%`, trades `36`, active months `18`.
- `frr2_no_catch_falling_knife` delay `1` hold `20D`: return `90.36%`, Sharpe `0.94`, MDD `-17.96%`, trades `36`, active months `18`.
- `frr2_no_catch_falling_knife` delay `2` hold `20D`: return `94.98%`, Sharpe `0.89`, MDD `-25.74%`, trades `36`, active months `18`.

## Main candidate check: FRR-2 no-catch-falling-knife

- FRR-2 delay=1 hold=20D: return `90.36%`, Sharpe `0.94`, MDD `-17.96%`, trades `36`.
- Remove-top-10: return `-39.15%`, Sharpe `-1.03`, MDD `-39.15%`.

## Sector survival, delay=1, hold=20D

- `all`: return `90.36%`, Sharpe `0.94`, MDD `-17.96%`.
- `electronics`: return `38.75%`, Sharpe `0.54`, MDD `-32.13%`.
- `non_electronics`: return `59.02%`, Sharpe `0.85`, MDD `-17.62%`.
- `semiconductor`: return `94.34%`, Sharpe `0.93`, MDD `-14.23%`.
- `no_semiconductor`: return `30.67%`, Sharpe `0.51`, MDD `-28.50%`.

## Interpretation

- FRR should be judged as a causal timing/diagnostic layer, not a replacement for S1 unless it survives remove-winner and sector checks.
- If performance concentrates in electronics/semiconductor or collapses after removing top winners, classify it as research-only and retain S1 as incumbent.
- Margin data is public official data, but it is only tradable after publication; therefore delay=1/2/3 rows are more important than same-day logic.
