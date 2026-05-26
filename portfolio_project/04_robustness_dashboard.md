# 04 — Robustness Dashboard

## Promotion rule

A variant is not promoted just because full-sample Sharpe improves. It must survive:

- year split;
- walk-forward OOS;
- remove-top-winners;
- electronics / semiconductor / no-semiconductor slices;
- liquidity thresholds;
- cost stress;
- execution timing stress.

## Core comparison

### S1 fixed-20 comparator

- Return: `161.9%`.
- Sharpe: `1.55`.
- MDD: `-21.2%`.
- Active months: `29/30`.
- Average positions: `7.27`.

### Quiet boost dynamic sizing

`boost_quiet_no_large_black_150`:

- Return: `174.4%`.
- Sharpe: `1.62`.
- MDD: `-21.2%`.
- Monthly win rate: `76.7%`.

Interpretation: modest improvement, but not enough for promotion because MDD did not improve materially.

## Remove-winner stress

### Equal S1

- Remove 0: Sharpe `1.55`.
- Remove 5: Sharpe `1.16`.
- Remove 10: Sharpe `0.96`.
- Remove 20: Sharpe `0.38`.

### Quiet boost

- Remove 0: Sharpe `1.62`.
- Remove 5: Sharpe `1.22`.
- Remove 10: Sharpe `1.04`.
- Remove 20: Sharpe `0.48`.

Interpretation: quiet boost modestly improves remove-winner profile but does not eliminate top-winner dependence.

## Execution realism stress

Conservative proxy:

```text
next_open + 1.0% all-in cost + exclude possible limit-up risk
```

Results:

- Equal S1: return `99.8%`, Sharpe `1.16`, MDD `-26.2%`.
- Quiet boost: return `111.9%`, Sharpe `1.24`, MDD `-24.9%`.

Interpretation: a large portion of headline quality is sensitive to entry timing / execution assumptions.

## Walk-forward dynamic sizing

### Train 2023 → Test 2024

- Selected rule: `boost_quiet_no_large_black_125`.
- Selected OOS: return `14.45%`, Sharpe `0.74`.
- Equal S1 OOS: return `12.91%`, Sharpe `0.67`.

### Train 2023–2024 → Test 2025

- Selected rule: `boost_quiet_no_large_black_200`.
- Selected OOS: return `40.50%`, Sharpe `1.17`.
- Equal S1 OOS: return `35.45%`, Sharpe `1.08`.

Interpretation: OOS improvement exists but is small and based on only two splits.

## Sector and winner concentration

### 2025 selected OOS rule

- All: Sharpe `1.17`.
- Semiconductor-only: Sharpe `2.59`.
- No-semiconductor: Sharpe `0.31`.
- Remove-top-5: Sharpe `0.37`.

### 2024 selected OOS rule

- All: Sharpe `0.76`.
- Semiconductor-only: Sharpe `1.52`.
- No-semiconductor: Sharpe `-0.56`.
- Remove-top-5: Sharpe `-0.50`.

Interpretation: the edge is strongly tied to semiconductor / electronics and a small number of winners. This is the central reason not to call it broad, production-ready alpha.

## Capacity proxy

Using monthly portfolio capital capped by participation × average 20D turnover value:

### Equal S1

- ADV 1% median capacity: about `5.2m TWD`.
- ADV 3% median capacity: about `15.6m TWD`.
- ADV 5% median capacity: about `26.1m TWD`.

### Liquidity >= 100m S1

- ADV 1% median capacity: about `7.6m TWD`.
- ADV 3% median capacity: about `22.8m TWD`.
- ADV 5% median capacity: about `38.0m TWD`.

Interpretation: liquidity >= 100m helps capacity, but does not automatically improve alpha quality.
