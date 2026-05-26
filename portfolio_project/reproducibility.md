# Reproducibility Guide

## Scope

This guide documents where the research artifacts live and how to reproduce the major outputs. It does not place trades, connect to a broker, or install packages.

## Important paths

```text
Project root:
/Users/liuyenzhen/quant-research/tw_monthly_revenue

Portfolio docs:
/Users/liuyenzhen/quant-research/tw_monthly_revenue/portfolio_project

Phase reports:
/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports

Charts:
/Users/liuyenzhen/quant-research/tw_monthly_revenue/reports/charts

Processed data:
/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed

Scripts:
/Users/liuyenzhen/quant-research/tw_monthly_revenue/scripts
```

## Core scripts

### Data and initial research

```text
scripts/fetch_historical_monthly_revenue_mops_static.py
scripts/fetch_daily_market_history_2023_present.py
scripts/run_proxy_backtest.py
scripts/portfolio_nav_backtest.py
```

### SUR and strategy research

```text
scripts/sur_factor_tests.py
scripts/short_horizon_sur_research.py
scripts/execution_realism_tests.py
scripts/high_sharpe_search.py
scripts/signal_quality_search.py
scripts/walkforward_sector_survival.py
```

### Price/volume and K-line research

```text
scripts/price_volume_kline_research.py
scripts/price_volume_sector_diagnostics.py
scripts/kline_ohlc_audit_research.py
scripts/price_volume_kline_interaction_research.py
scripts/quiet_digestion_deep_dive.py
scripts/quiet_digestion_dynamic_sizing.py
```

### Execution realism and paper-trading gates

```text
scripts/execution_realism_tradability_gate.py
scripts/dynamic_sizing_walkforward_gate.py
scripts/exact_timing_delay_sensitivity_gate.py
scripts/exact_timing_robustness_gate.py
scripts/delay_walkforward_robust_selection_gate.py
scripts/delay_walkforward_oos_sector_stress.py
scripts/exact_timing_paper_trading_schema_gate.py
scripts/build_official_daily_ohlc_limit_from_raw.py
```

## Recommended reproduction order

From project root:

```bash
python3 scripts/sur_factor_tests.py
python3 scripts/signal_quality_search.py
python3 scripts/walkforward_sector_survival.py
python3 scripts/quiet_digestion_dynamic_sizing.py
python3 scripts/execution_realism_tradability_gate.py
python3 scripts/dynamic_sizing_walkforward_gate.py
python3 scripts/exact_timing_delay_sensitivity_gate.py
python3 scripts/delay_walkforward_oos_sector_stress.py
python3 scripts/exact_timing_paper_trading_schema_gate.py
python3 scripts/build_official_daily_ohlc_limit_from_raw.py
```

## Key reports to inspect

```text
reports/promising_strategy_registry.md
reports/phase3_12_walkforward_sector_survival_report.md
reports/phase3_18_quiet_digestion_dynamic_sizing_report.md
reports/phase3_19_execution_realism_tradability_report.md
reports/phase3_20_dynamic_sizing_walkforward_report.md
reports/phase3_24_delay_walkforward_oos_sector_stress_report.md
reports/phase3_25_exact_timing_paper_trading_schema_report.md
reports/phase3_26_official_ohlc_limit_parser_report.md
```

## Key processed outputs

```text
data/processed/execution_realism_tradability_summary.csv
data/processed/dynamic_sizing_walkforward_summary.csv
data/processed/delay_walkforward_oos_sector_stress.csv
data/processed/delay_walkforward_oos_remove_winners.csv
data/processed/paper_trading_execution_log_schema.csv
data/processed/official_daily_ohlc_limit_from_raw.csv
```

## Verification commands

```bash
python3 -m py_compile scripts/*.py
```

For a lightweight file-presence check:

```bash
test -f reports/promising_strategy_registry.md
test -f portfolio_project/README.md
test -f data/processed/official_daily_ohlc_limit_from_raw.csv
```

## Reproducibility caveats

- Some reports depend on previously fetched local raw data.
- Current historical revenue timing is proxy-based, not exact timestamp-based.
- Raw TWSE local coverage is more limited than TPEx coverage in the current artifact set.
- Results are research diagnostics, not trading recommendations.
