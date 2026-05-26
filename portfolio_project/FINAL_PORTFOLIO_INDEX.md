# Final Portfolio Index — Taiwan Monthly Revenue Surprise Strategy

## Elevator pitch

This project tests whether Taiwan monthly revenue disclosures create post-announcement drift in equities with persistent positive revenue surprise. The research starts from a market-structure hypothesis, builds official-data pipelines, evaluates SUR-style signals, and then subjects the best candidate to walk-forward, sector, winner-dependence, cost, liquidity, timing, and paper-trading gates.

## Recommended reading order

1. [`README.md`](README.md) — project overview.
2. [`02_strategy_card.md`](02_strategy_card.md) — concise strategy summary.
3. [`04_robustness_dashboard.md`](04_robustness_dashboard.md) — main evidence and stress tests.
4. [`05_execution_and_paper_trading.md`](05_execution_and_paper_trading.md) — why it is not production-ready yet.
5. [`07_interview_qna.md`](07_interview_qna.md) — interview framing.
6. [`reproducibility.md`](reproducibility.md) — paths and scripts.

## Portfolio positioning

Use this project to demonstrate:

- causal hypothesis design: monthly revenue disclosure → delayed repricing;
- Taiwan market data familiarity;
- robust backtest discipline;
- honest rejection / non-promotion of fragile variants;
- execution-aware thinking;
- readiness to move from backtest to paper-trading audit.

## Do not overclaim

Recommended public wording:

> A portfolio-grade quant research project on Taiwan monthly revenue surprise and short-horizon post-disclosure drift, with an incumbent candidate showing attractive proxy results but still requiring exact announcement timestamps, stronger universe controls, execution simulation, and paper-trading validation before any live-trading claim.

Avoid saying:

- "production-ready alpha";
- "live trading system";
- "guaranteed Sharpe 2+";
- "broad-market Taiwan stock strategy".

## Key artifacts in this folder

### Final Word / PDF deliverables (V6 = current)

- `Taiwan_Monthly_Revenue_Strategy_Resume_Version_ZH_PRO_V6.docx` / `.pdf` — current resume-attachment version. Author block (劉晏禎 / miles891002@gmail.com) on cover; FRR best diagnostic chip added to cover KPI strip.
- `Taiwan_Monthly_Revenue_Strategy_Talking_Guide_ZH_PRO_V6.docx` / `.pdf` — current interview talking-guide. Includes 4 hardened challenge-style QnAs (look-ahead / data snooping, survivorship / universe, capacity / market impact, sector regime shift).

Historical versions retained for diff / comparison:

- `Taiwan_Monthly_Revenue_Strategy_Resume_Version_ZH_PRO_V5.*` / `Talking_Guide_ZH_PRO_V5.*` — anonymous-cover predecessor.
- `Taiwan_Monthly_Revenue_Strategy_Resume_Version_ZH_PRO_V3-V4.*` / `Talking_Guide_ZH_PRO_V3-V4.*` — earlier chart-enhanced iterations.
- `charts_v3/` — FRR Phase 4.1 charts used across V3–V6.

### Source markdown / templates

- `README.md`
- `01_methodology_report.md`
- `02_strategy_card.md`
- `03_research_timeline.md`
- `04_robustness_dashboard.md`
- `05_execution_and_paper_trading.md`
- `06_limitations_and_next_steps.md`
- `07_interview_qna.md`
- `08_paper_trading_template.md`
- `paper_trading_log_template.csv`
- `reproducibility.md`
- `INDEX.md`
- `FINAL_PORTFOLIO_INDEX.md`

## Linked source artifacts outside this folder

- `../reports/promising_strategy_registry.md`
- `../reports/phase3_12_walkforward_sector_survival_report.md`
- `../reports/phase3_18_quiet_digestion_dynamic_sizing_report.md`
- `../reports/phase3_19_execution_realism_tradability_report.md`
- `../reports/phase3_24_delay_walkforward_oos_sector_stress_report.md`
- `../reports/phase3_25_exact_timing_paper_trading_schema_report.md`
- `../reports/phase3_26_official_ohlc_limit_parser_report.md`
- `../reports/charts/s1_nav_drawdown_zh.png`
- `../reports/charts/phase3_12_walkforward_oos_nav_zh.png`
- `../reports/charts/phase3_18_dynamic_sizing_nav_zh.png`

## Final status

- Research portfolio: ready.
- Paper trading: template ready, future live cycles needed.
- Production/live trading: not ready and not claimed.
