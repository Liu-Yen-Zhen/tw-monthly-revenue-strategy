# 01 — Methodology Report

## Research question

Can Taiwan monthly revenue disclosures create a tradable post-announcement drift signal, especially when revenue surprise is persistent and the stock is not already overextended?

## Market-structure motivation

Taiwan companies disclose monthly revenue, giving investors a higher-frequency fundamental signal than quarterly earnings alone. The hypothesis is not simply "high revenue growth is good." The more precise hypothesis is:

> Because monthly revenue surprise updates investors' expectations about near-term demand and supply-chain strength, and because some investors react with delay after official disclosure, stocks with persistent positive revenue surprise may continue repricing over the next 10–20 trading days.

This should be strongest when:

- surprise is persistent, not just one noisy month;
- price is not already overextended;
- the sector has a strong narrative / capital-flow channel, especially electronics and semiconductors;
- liquidity is sufficient for research-level tradability;
- the first feasible trade is after public data availability.

## Data used

The project uses local official / official-derived Taiwan data artifacts:

- Monthly revenue panel with `usable_date_proxy` and revenue fields.
- Daily market history with close and turnover value.
- Raw official daily JSON files, later parsed into normalized OHLC / limit research tables.

Important data caveat:

```text
announcement_date_quality = monthly_summary_no_company_timestamp
```

This means historical company-level exact announcement timestamps are not yet available in the current dataset. The project therefore uses conservative proxy timing and explicitly refuses to claim production-ready tradability.

## Factor construction

The core factor family includes:

- Revenue YoY / MoM.
- 3-month revenue growth / persistence.
- Standardized unexpected revenue / SUR-style surprise.
- Industry-adjusted surprise variants.
- Momentum and overextension filters.
- Abnormal turnover and daily OHLC/K-line diagnostics.

The final incumbent emphasizes:

```text
3M SUR persistence + not-overheated momentum
```

## Portfolio construction

The main S1 fixed-20 comparator uses:

```text
liquidity >= 50m TWD avg turnover
Top 8 names per month
industry cap = 3
holding period = 20 trading days
round-trip cost proxy = 0.7% in baseline tests
```

The portfolio-grade v0.1 incumbent from the broader search adds a trailing/stop-style proxy:

```text
sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D
```

## Research gates

The project deliberately uses promotion gates rather than simply chasing Sharpe:

1. Baseline factor must be coherent.
2. New signals must beat the incumbent under comparable assumptions.
3. Inactive months are counted as cash, not removed from Sharpe.
4. Remove-top-winners tests must be reported.
5. Year split and walk-forward OOS must be checked.
6. Electronics / semiconductor dependence must be tested.
7. Liquidity and cost sensitivity must be tested.
8. Execution realism must be audited before any production claim.
9. Paper-trading schema must exist before live consideration.

## Main research evolution

The project evolved through these layers:

- Phase 2: data feasibility and proxy backtest.
- Phase 3.1–3.5: portfolio NAV, robustness, multifactor, SUR tests.
- Phase 3.6–3.11: short-horizon SUR, execution rules, high-Sharpe search, signal quality search.
- Phase 3.12: walk-forward and sector survival.
- Phase 3.13–3.18: price/volume, K-line, quiet digestion, dynamic sizing.
- Phase 3.19–3.26: execution realism, delay sensitivity, OOS sector stress, paper-trading schema, normalized OHLC/limit parser.

## Final research interpretation

The strongest defensible interpretation is:

> A Taiwan electronics / semiconductor supply-chain monthly revenue surprise strategy with evidence of post-disclosure drift, but with meaningful right-tail, sector, data-timing, and execution constraints.

The project is strongest as a research process demonstration, not as a live trading claim.
