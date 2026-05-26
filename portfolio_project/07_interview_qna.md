# 07 — Interview Q&A

## Q1. What is the core idea?

Taiwan companies disclose monthly revenue, which provides a recurring high-frequency fundamental update. The strategy tests whether stocks with persistent positive revenue surprise experience delayed repricing after public disclosure, especially in electronics and semiconductor supply chains.

## Q2. Why use 3M SUR instead of raw revenue growth?

Raw growth can already be priced in and can be noisy. 3M SUR persistence tries to capture a more stable surprise component: repeated upside relative to recent expectation / baseline rather than a single impressive YoY print.

## Q3. How did you avoid look-ahead bias?

The project separates revenue month from usable date and uses conservative data-availability proxies. Later phases explicitly stress next-open / delayed entries and acknowledge that exact company-level timestamps are still missing, so the project does not claim production-ready timing.

## Q4. What was the best-performing strategy?

The preserved portfolio-grade v0.1 candidate is S1:

```text
sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D
```

It had a proxy Sharpe around `2.40`, return around `167.5%`, and MDD around `-7.9%` in the earlier portfolio-grade proxy setup.

## Q5. Why not just promote the highest Sharpe variant?

Because many high-return variants were fragile after remove-winner tests, sector survival checks, or execution realism. The project uses promotion gates rather than full-sample Sharpe ranking.

## Q6. What did price/volume and K-line research add?

It showed that volume expansion alone is not a reliable alpha. Quiet digestion — low abnormal turnover plus narrow entry-day range — had an interpretable delayed-repricing story, but as a standalone slice it was sparse and winner-dependent. It was therefore tested as a sizing diagnostic inside S1 rather than promoted as a replacement.

## Q7. What is the biggest weakness?

Exact company-level announcement timestamps are missing in the current historical revenue dataset. That prevents a final answer on same-day tradability and exact no-look-ahead timing.

## Q8. Is the strategy broad-market?

No. The evidence points to electronics / semiconductor supply-chain dependence. That is not necessarily bad, but it must be stated honestly.

## Q9. What happened under conservative execution assumptions?

Under `next_open + 1.0% cost + exclude possible limit-up risk`, quiet boost dropped to return `111.9%`, Sharpe `1.24`, and MDD `-24.9%`. This is still interesting but no longer a headline high-Sharpe result.

## Q10. What would you do next?

I would stop expanding the parameter grid and instead:

1. obtain exact announcement timestamps;
2. run real-time paper trading for 2026 revenue cycles;
3. log feasible fills and non-fills;
4. re-run promotion gates with actual timing and tradability;
5. only then consider whether it deserves production research.

## Q11. What does this project demonstrate about your research style?

It demonstrates that I can start from a market-structure hypothesis, build a systematic research pipeline, generate and reject variants, test robustness, preserve promising candidates, and avoid overstating results when operational constraints remain unresolved.
