# Industry-survivable roadmap — Taiwan monthly revenue SUR strategy

Research-only. This document defines the target for moving the current portfolio-grade v0.1 candidate toward an industry-survivable strategy. It does not authorize live trading.

## Current retained version

### Portfolio-grade v0.1 / S1 incumbent

- Strategy: Taiwan monthly revenue surprise + fundamental momentum + not-overheated price action.
- Config: `sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D`
- Current metrics:
  - Full-period Sharpe proxy: `2.40`
  - Train Sharpe, entry 2023-2024: `1.86`
  - 2025 OOS diagnostic Sharpe: `3.12`
  - MDD: `-7.9%`
  - Remove top-5 winners Sharpe: `1.77`
  - Remove top-10 winners Sharpe: `1.41`
- Status: worth preserving as interview/research portfolio version, but not yet industry-survivable.

## Industry-survivable definition

A strategy is not considered industry-survivable until it passes these gates:

1. **Data-timing gate**
   - Uses exact company-level announcement date/time when available.
   - Entry date respects after-close announcements, holidays, and next tradable date.
   - No revenue-month look-ahead and no current-universe look-ahead.

2. **Universe / survivorship gate**
   - Historical stock master includes listed, OTC, delisted, suspended, full-delivery, and renamed securities where possible.
   - Excludes ETFs/warrants/preferred/non-common instruments with documented rules.
   - Historical industry / listing status is handled or caveated.

3. **Execution realism gate**
   - Uses OHLC or better data, not close-only proxy, for stop/trailing feasibility.
   - Detects limit-up/limit-down, suspensions, no-trade days, and non-fill risk.
   - Applies realistic commission, tax, bid/ask spread, slippage, and capacity assumptions.
   - Tests order sizing as a percentage of ADV/turnover.

4. **OOS / model-selection gate**
   - Uses walk-forward selection: parameters selected only from prior data, then evaluated on future periods.
   - Reports stitched OOS performance separately from full-sample diagnostics.
   - Avoids promoting variants based on full-sample grid-search rank.

5. **Robustness gate**
   - Year-by-year and regime breakdown.
   - No-semiconductor / no-electronics stress.
   - Liquidity thresholds: 50m / 100m / 300m+ TWD ADV.
   - Remove top winners and top contributors.
   - Cost sensitivity at 0.5%, 0.7%, 1.0%, 1.5% round-trip assumptions.
   - Parameter stability around Top N, industry cap, holding days, exit rule.

6. **Paper-trading gate**
   - Logs every signal with timestamp, planned entry, feasible entry price, non-fill reason, estimated slippage, and daily PnL.
   - Runs for multiple revenue cycles before live consideration.
   - Validates operational feasibility rather than just alpha.

## Most likely challenges

- 2025 OOS may be AI / memory / electronics regime driven.
- Remove-winners decay shows right-tail dependence.
- Close-only trailing-stop proxy may overstate execution quality.
- Announcement timestamps are not yet exact per company.
- Survivorship / delisting handling needs hardening.
- Capacity could be limited if edge concentrates in lower-liquidity names.

## Research priorities

### Phase A — exact timing and tradability

- Build exact MOPS/TWSE/TPEx announcement-date table if available.
- Compare conservative proxy entry vs exact timestamp entry.
- Add OHLC / limit-up-down / suspension feasibility checks.

### Phase B — walk-forward OOS

- Train 2023, test 2024.
- Train 2023-2024, test 2025.
- Monthly rolling/expanding selection where only prior data selects the candidate.
- Report stitched OOS NAV and Sharpe.

### Phase C — concentration and sector survival

- Electronics-only, semiconductor-only, non-electronics, no-semiconductor tests.
- Industry-relative SUR ranking.
- Same-industry benchmark excess returns.

### Phase D — execution and capacity

- Cost sensitivity and slippage model.
- ADV participation caps: 1%, 3%, 5% of 20D turnover.
- Fill-risk adjustment for limit-up and low-volume names.

### Phase E — paper-trading workflow

- Generate monthly candidate list after real data release.
- Log feasibility and estimated fill price.
- Compare paper trades to backtest assumptions.

## Promotion rule

The current S1 remains portfolio-grade v0.1. A future version can be promoted to industry-survivable candidate only if it passes exact timing, walk-forward OOS, execution realism, and robustness gates without relying on a single sector/year/top-winner cluster.
