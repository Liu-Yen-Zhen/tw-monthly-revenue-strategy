# 05 — Execution Realism and Paper-Trading Plan

## Why execution realism matters

Monthly revenue strategies are event-driven. A backtest can look attractive if it assumes entry at a price that was not actually tradable after information became public. The key question is not just "does the signal work?" but:

> Could a real researcher observe the data, generate the signal, submit the order, and get a plausible fill without look-ahead or unrealistic queue assumptions?

## Current execution-realism work completed

### OHLC / limit audit

- Raw official daily JSON files were parsed into a normalized OHLC / limit table.
- TPEx raw files include next-day limit-up/down fields.
- Current local TWSE raw sample has OHLC but lacks parsed next-day limit fields.

Output table:

```text
/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/official_daily_ohlc_limit_from_raw.csv
```

### Conservative entry timing

The project tested:

- entry close proxy;
- next close;
- next open;
- delay 0/1/2/3 trading days;
- possible limit-up non-fill exclusion;
- 0.7%, 1.0%, and 1.5% cost assumptions.

### Key conservative result

`boost_quiet_no_large_black_150 | next_open | 1.0% cost | exclude limit-up risk`:

- Return: `111.9%`.
- Sharpe: `1.24`.
- MDD: `-24.9%`.

This is still positive, but much less impressive than the entry-close proxy.

## Exact-timing gap

The current historical revenue table has:

```text
announcement_date_quality = monthly_summary_no_company_timestamp
```

This means:

- no exact company-level announcement timestamp;
- no reliable after-close / intraday classification;
- no exact earliest-tradable-date proof;
- no final look-ahead-bias closure.

## Paper-trading execution log design

Each future signal should log:

- `signal_id`
- `stock_id`
- `stock_name`
- `revenue_month`
- `data_available_at`
- `announcement_timestamp_source`
- `signal_generated_at`
- `planned_entry_date`
- `planned_entry_type` — open / close / VWAP proxy
- `observed_open`
- `observed_high`
- `observed_low`
- `observed_close`
- `limit_up_price`
- `opened_at_limit_up`
- `non_fill_reason`
- `planned_notional`
- `ADV_participation_pct`
- `estimated_slippage`
- `actual_paper_fill_price`
- `5D_return`
- `10D_return`
- `20D_return`
- `deviation_from_backtest_assumption`

## Paper-trading acceptance criteria

Before this project should be described as production-adjacent, it should accumulate multiple monthly revenue cycles with:

- timestamped signal generation;
- documented feasible entries;
- explicit non-fill cases;
- realized paper PnL under predefined assumptions;
- comparison against the historical proxy model;
- explanation for any assumption drift.

## Recommended paper-trading rule

Until exact timestamps are available:

> Use conservative next-trading-day-after-observed-data entry. Do not claim same-day tradability.
