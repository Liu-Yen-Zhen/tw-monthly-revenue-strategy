# 06 — Limitations and Next Steps

## Current limitations

### 1. Exact announcement timestamp is missing

The historical revenue data currently uses a monthly summary / usable-date proxy, not company-level exact announcement timestamps. This is the biggest remaining data-timing limitation.

### 2. Survivorship and universe completeness need stronger controls

A production-grade version should explicitly handle:

- delisted names;
- suspended names;
- full-delivery / special treatment stocks;
- listing changes;
- historical industry classifications;
- non-common instruments.

### 3. Execution model remains proxy-based

The project now has OHLC and TPEx next-limit fields, but still lacks:

- full order-book depth;
- opening auction queue position;
- partial fills;
- intraday volume distribution;
- true limit-up queue outcomes;
- broker-level implementation assumptions.

### 4. Sample length is short

The strongest research period is mainly 2023–2025. That is enough for a portfolio project but not enough to claim a durable structural anomaly.

### 5. Sector dependence is material

Results are meaningfully stronger in electronics / semiconductor supply-chain names. The project should be framed as sector-conditional, not broad-market.

### 6. Winner concentration remains important

Remove-winner tests often reduce Sharpe sharply. This suggests right-tail dependence and regime sensitivity.

## What would make it stronger as a portfolio project?

1. Turn the current documents into a polished public README.
2. Add a clean architecture diagram for the data pipeline.
3. Add one reproducible notebook or script that rebuilds the main robustness table.
4. Add a small sample paper-trading log using future 2026 revenue cycles.
5. Add a clear "what I learned / what I rejected" section.

## What would make it stronger as a trading strategy?

1. Obtain exact company-level monthly revenue announcement timestamps.
2. Extend historical sample if reliable official data is available.
3. Improve survivorship and historical universe membership handling.
4. Build a stricter execution simulator with limit-up/down, suspensions, and partial fills.
5. Run live paper trading for several cycles.
6. Re-run all promotion gates under those assumptions.

## Current recommendation

Stop expanding the signal grid for now. The highest-value next step is not more K-line mining or parameter search. It is:

> exact timing + paper trading + operational feasibility.
