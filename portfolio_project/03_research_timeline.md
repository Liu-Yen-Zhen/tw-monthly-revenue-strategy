# 03 — Research Timeline

## Phase 2 — Data feasibility and proxy backtest

- Identified official / free Taiwan revenue and market data sources.
- Built historical monthly revenue panel and initial proxy backtest.
- Established that revenue timing must be handled conservatively.

## Phase 3.1–3.5 — Portfolio NAV and SUR factor research

- Moved from trade averages to cohort NAV diagnostics.
- Added robustness / risk tests and multifactor extensions.
- Tested SUR-style definitions and industry-adjusted variants.
- Learned that persistent 3M SUR is more promising than raw single-month growth alone.

## Phase 3.6–3.8 — Short-horizon and execution-rule exploration

- Focused on 10–20 trading-day horizons.
- Found 20D fixed horizon more defensible than over-aggressive 10D variants.
- Tested stop/trailing proxies, but labeled them close-price proxies rather than executable stops.

## Phase 3.9–3.11 — High-Sharpe search and signal-quality discipline

- Broad search did not find a robust Sharpe > 2.5 candidate that survived all gates.
- Preserved S1 as incumbent rather than overwriting it with fragile high-return variants.
- Established promising strategy registry.

## Phase 3.12 — Walk-forward and sector survival

- Walk-forward parameter selection did not beat fixed S1.
- Sector survival showed strong electronics / semiconductor dependence.
- Reframed strategy away from broad-market alpha and toward supply-chain revenue surprise.

## Phase 3.13–3.16 — Price/volume and K-line diagnostics

- Tested abnormal turnover, low-volume digestion, K-line supply pressure, and large black K diagnostics.
- Found volume expansion alone is not a free lunch.
- Found quiet digestion is interesting but sparse and winner-dependent.

## Phase 3.17–3.18 — Quiet digestion and dynamic sizing

- Deep-dived quiet digestion as low abnormal turnover plus narrow entry-day range.
- Concluded it is not a standalone replacement strategy.
- Tested it as S1 dynamic sizing.
- Best sizing rule modestly improved fixed-20 proxy but did not reduce MDD enough for promotion.

## Phase 3.19–3.24 — Execution realism and OOS stress

- Added next-open / next-close timing, cost stress, limit-up non-fill proxy, and ADV capacity proxy.
- Walk-forward dynamic sizing produced small OOS improvements.
- OOS sector stress showed improvements are still semiconductor / winner dependent.

## Phase 3.25–3.26 — Exact timing and paper-trading preparation

- Audited data and confirmed historical revenue table lacks exact company-level timestamps.
- Created paper-trading execution schema.
- Parsed raw official daily JSON into normalized OHLC / limit research table.

## Final status

The project is ready to package as a serious quant research portfolio piece. It is not ready to be marketed as a production trading system.
