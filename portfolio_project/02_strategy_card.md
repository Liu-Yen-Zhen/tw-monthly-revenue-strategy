# 02 — Strategy Card

## Strategy name

**Taiwan Monthly Revenue Surprise + Fundamental Momentum**

## Research status

- **Status:** Portfolio-grade research candidate / not production-ready.
- **Incumbent:** S1.
- **Live trading:** No.
- **Broker integration:** No.

## Core hypothesis

Because Taiwanese listed and OTC companies disclose monthly revenue, persistent positive revenue surprise can update expectations about near-term fundamentals. If the market underreacts after disclosure, especially in electronics / semiconductor supply chains, selected stocks may exhibit positive 10–20 trading-day drift.

## Universe

- Taiwan listed / OTC common-stock-like universe where official revenue and daily market data are available.
- Liquidity screen: typically `avg_turnover_20d >= 50m TWD`; `100m TWD` used as robustness comparator.
- ETFs, warrants, and non-common instruments should be excluded in production-grade research.

## Signal

Main S1 family:

```text
high 3M SUR persistence
+ not-overheated 120D-to-20D momentum
+ liquidity screen
+ monthly top-N ranking by SUR core score
```

Quiet-digestion sizing diagnostic:

```text
low abnormal turnover
+ narrow entry-day range
+ not large-black K
```

This diagnostic is used only as a research-only sizing hypothesis, not as a standalone promoted strategy.

## Portfolio construction

- Monthly rebalance / event-cycle selection after revenue data availability proxy.
- Top 8 names.
- Industry cap = 3.
- Fixed 20 trading-day holding period for main comparator.
- Trailing/stop proxy candidate retained as S1 portfolio-grade v0.1 but still requires execution validation.

## Key results

### S1 portfolio-grade v0.1 proxy

- Sharpe proxy: about `2.40`.
- Total return: about `167.5%`.
- MDD: about `-7.9%`.
- Remove-top-5 Sharpe: about `1.77`.

### S1 fixed-20 comparator

- Return: `161.9%`.
- Sharpe: `1.55`.
- MDD: `-21.2%`.

### Quiet-digestion sizing candidate

`boost_quiet_no_large_black_150`:

- Return: `174.4%`.
- Sharpe: `1.62`.
- MDD: `-21.2%`.
- Interpretation: modest sizing improvement, not enough for promotion.

### Conservative tradability proxy

`next_open + 1.0% cost + exclude possible limit-up risk`:

- Equal S1: return `99.8%`, Sharpe `1.16`, MDD `-26.2%`.
- Quiet boost: return `111.9%`, Sharpe `1.24`, MDD `-24.9%`.

## Why it is interesting

- Uses a Taiwan-specific recurring fundamental disclosure.
- Demonstrates a coherent PEAD / underreaction mechanism.
- Shows sector-specific behavior rather than pretending to be universal.
- Includes extensive negative results and failed promotion gates.

## Why it is not production-ready

- Current historical revenue table lacks company-level exact announcement timestamps.
- Survivorship / listing-status completeness still needs stronger controls.
- Execution realism still relies on OHLC / limit proxies rather than order-book fills.
- OOS evidence is short: mainly 2023–2025.
- Semiconductor and top-winner dependence remain material.
- Paper trading has not yet accumulated multiple cycles of real-time validation.
