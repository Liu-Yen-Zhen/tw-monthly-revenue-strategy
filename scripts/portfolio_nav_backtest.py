#!/usr/bin/env python3
"""Phase 3.1 cohort portfolio NAV prototype for Taiwan monthly-revenue strategy.

Research-only. No trading, no deployment, no package installation.

This is a cohort/monthly NAV prototype, not a broker-accurate daily simulator:
- Each revenue_month cohort is an equal-weight portfolio of selected names.
- The cohort return is measured after a fixed holding period: 20/40/60 trading days.
- NAV compounds one cohort result per revenue month.
- Benchmark uses the enriched per-window equal-weight market benchmark already computed.
- Excess NAV compounds monthly cohort excess returns.

Why this prototype matters:
- It converts isolated trade averages into a portfolio-like NAV series.
- It exposes drawdowns, year returns, monthly consistency, and benchmark excess.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
ENRICHED_TRADES = PROCESSED / "proxy_backtest_trades_enriched.csv"
OUT_MONTHLY = PROCESSED / "portfolio_nav_monthly_cohorts.csv"
OUT_SUMMARY = PROCESSED / "portfolio_nav_summary.json"
OUT_REPORT = REPORTS / "phase3_1_portfolio_nav_report.md"
INDUSTRY_CAP_PER_MONTH = 6  # 30% of Top 20


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def f(x: Any) -> float | None:
    if x in (None, ""):
        return None
    try:
        return float(x)
    except Exception:
        return None


def mean(xs: list[float]) -> float | None:
    return statistics.mean(xs) if xs else None


def stdev(xs: list[float]) -> float | None:
    return statistics.stdev(xs) if len(xs) >= 2 else None


def max_drawdown(navs: list[float]) -> tuple[float, int]:
    peak = navs[0] if navs else 1.0
    max_dd = 0.0
    cur_duration = 0
    max_duration = 0
    for nav in navs:
        if nav >= peak:
            peak = nav
            cur_duration = 0
        else:
            dd = nav / peak - 1
            max_dd = min(max_dd, dd)
            cur_duration += 1
            max_duration = max(max_duration, cur_duration)
    return max_dd, max_duration


def compound(returns: list[float]) -> float:
    nav = 1.0
    for r in returns:
        nav *= 1 + r
    return nav - 1


def metric_summary(monthly_returns: list[float]) -> dict[str, Any]:
    if not monthly_returns:
        return {}
    navs = []
    nav = 1.0
    for r in monthly_returns:
        nav *= 1 + r
        navs.append(nav)
    total = nav - 1
    n = len(monthly_returns)
    ann = (nav ** (12 / n) - 1) if n else None
    vol = stdev(monthly_returns)
    sharpe = (statistics.mean(monthly_returns) / vol * math.sqrt(12)) if vol and vol > 0 else None
    mdd, dd_months = max_drawdown([1.0] + navs)
    calmar = (ann / abs(mdd)) if ann is not None and mdd < 0 else None
    wins = [r for r in monthly_returns if r > 0]
    losses = [r for r in monthly_returns if r <= 0]
    return {
        "months": n,
        "final_nav": nav,
        "total_return": total,
        "annualized_return": ann,
        "monthly_mean": statistics.mean(monthly_returns),
        "monthly_median": statistics.median(monthly_returns),
        "monthly_vol": vol,
        "monthly_win_rate": len(wins) / n,
        "avg_win": mean(wins),
        "avg_loss": mean(losses),
        "sharpe_proxy": sharpe,
        "max_drawdown": mdd,
        "max_drawdown_months": dd_months,
        "calmar_proxy": calmar,
        "best_month": max(monthly_returns),
        "worst_month": min(monthly_returns),
    }


def apply_industry_cap(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    for r in sorted(rows, key=lambda x: float(x["score"]), reverse=True):
        industry = r["industry"]
        if counts[industry] >= INDUSTRY_CAP_PER_MONTH:
            continue
        selected.append(r)
        counts[industry] += 1
    return selected


def build_monthly_rows(trades: list[dict[str, Any]], capped: bool) -> list[dict[str, Any]]:
    out = []
    for h in sorted({r["holding_days"] for r in trades}, key=int):
        by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in trades:
            if r["holding_days"] == h:
                by_month[r["revenue_month"]].append(r)
        nav_strategy = 1.0
        nav_benchmark = 1.0
        nav_excess = 1.0
        for month in sorted(by_month):
            rows = by_month[month]
            if capped:
                rows = apply_industry_cap(rows)
            net = [f(r["net_return"]) for r in rows]
            bench = [f(r["benchmark_net_return"]) for r in rows]
            excess = [f(r["excess_return"]) for r in rows]
            net_vals = [x for x in net if x is not None]
            bench_vals = [x for x in bench if x is not None]
            excess_vals = [x for x in excess if x is not None]
            if not net_vals or not bench_vals or not excess_vals:
                continue
            r_strategy = statistics.mean(net_vals)
            r_benchmark = statistics.mean(bench_vals)
            r_excess = statistics.mean(excess_vals)
            nav_strategy *= 1 + r_strategy
            nav_benchmark *= 1 + r_benchmark
            nav_excess *= 1 + r_excess
            industries = defaultdict(int)
            for r in rows:
                industries[r["industry"]] += 1
            top_industry, top_count = max(industries.items(), key=lambda kv: kv[1]) if industries else ("", 0)
            out.append({
                "variant": "industry_capped" if capped else "uncapped",
                "holding_days": h,
                "revenue_month": month,
                "entry_date_min": min(r["entry_date"] for r in rows),
                "exit_date_max": max(r["exit_date"] for r in rows),
                "positions": len(rows),
                "strategy_return": round(r_strategy, 8),
                "benchmark_return": round(r_benchmark, 8),
                "excess_return": round(r_excess, 8),
                "strategy_nav": round(nav_strategy, 8),
                "benchmark_nav": round(nav_benchmark, 8),
                "excess_nav": round(nav_excess, 8),
                "top_industry": top_industry,
                "top_industry_count": top_count,
                "top_industry_weight": round(top_count / len(rows), 4) if rows else "",
            })
    return out


def yearly_returns(rows: list[dict[str, Any]], variant: str, holding: str, field: str) -> dict[str, float]:
    by_year: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r["variant"] == variant and r["holding_days"] == holding:
            by_year[r["revenue_month"][:4]].append(float(r[field]))
    return {year: compound(vals) for year, vals in sorted(by_year.items())}


def summarize(monthly_rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for variant in sorted({r["variant"] for r in monthly_rows}):
        summary[variant] = {}
        for h in sorted({r["holding_days"] for r in monthly_rows if r["variant"] == variant}, key=int):
            rows = [r for r in monthly_rows if r["variant"] == variant and r["holding_days"] == h]
            strategy = [float(r["strategy_return"]) for r in rows]
            benchmark = [float(r["benchmark_return"]) for r in rows]
            excess = [float(r["excess_return"]) for r in rows]
            summary[variant][h] = {
                "strategy": metric_summary(strategy),
                "benchmark": metric_summary(benchmark),
                "excess": metric_summary(excess),
                "yearly_strategy_returns": yearly_returns(monthly_rows, variant, h, "strategy_return"),
                "yearly_benchmark_returns": yearly_returns(monthly_rows, variant, h, "benchmark_return"),
                "yearly_excess_returns": yearly_returns(monthly_rows, variant, h, "excess_return"),
            }
    return summary


def pct(x: Any) -> str:
    if x is None:
        return "NA"
    return f"{float(x):.2%}"


def write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# Phase 3.1 Portfolio/Cohort NAV 回測雛形\n\n",
        "這是 portfolio NAV 雛形，不是正式交易系統。它把每月選股 cohort 轉成可複利的 NAV 序列，並比較 benchmark NAV 與 excess NAV。\n\n",
        "## 方法\n\n",
        "- 每個 revenue_month 形成一個等權 cohort。\n",
        "- 分別測 20/40/60 交易日持有期。\n",
        "- 策略、benchmark、excess 都用月 cohort return 複利。\n",
        "- benchmark 為對應 entry/exit window 的上市+上櫃等權報酬，已扣 0.7% round-trip cost。\n",
        "- `industry_capped` 版本限制每月單一產業最多 6 檔。\n",
        "- 價格仍為未調整價格；結果只作研究判斷。\n\n",
    ]
    for variant in ["uncapped", "industry_capped"]:
        if variant not in summary:
            continue
        lines.append(f"## Variant: {variant}\n\n")
        for h in ["20", "40", "60"]:
            if h not in summary[variant]:
                continue
            s = summary[variant][h]
            strat = s["strategy"]
            bench = s["benchmark"]
            ex = s["excess"]
            lines += [
                f"### 持有 {h} 日\n\n",
                f"- 月份數：{strat.get('months')}\n",
                f"- 策略 final NAV：{strat.get('final_nav'):.4f}\n",
                f"- Benchmark final NAV：{bench.get('final_nav'):.4f}\n",
                f"- Excess NAV：{ex.get('final_nav'):.4f}\n",
                f"- 策略總報酬：{pct(strat.get('total_return'))}\n",
                f"- Benchmark 總報酬：{pct(bench.get('total_return'))}\n",
                f"- Excess 總報酬：{pct(ex.get('total_return'))}\n",
                f"- 策略年化 proxy：{pct(strat.get('annualized_return'))}\n",
                f"- 策略 Sharpe proxy：{strat.get('sharpe_proxy'):.2f}\n" if strat.get("sharpe_proxy") is not None else "- 策略 Sharpe proxy：NA\n",
                f"- 策略最大回撤：{pct(strat.get('max_drawdown'))}\n",
                f"- Excess 最大回撤：{pct(ex.get('max_drawdown'))}\n",
                f"- 月勝率：{pct(strat.get('monthly_win_rate'))}\n",
                f"- 最好 / 最差月：{pct(strat.get('best_month'))} / {pct(strat.get('worst_month'))}\n",
                "- 年度策略報酬：" + ", ".join(f"{y}={pct(v)}" for y, v in s["yearly_strategy_returns"].items()) + "\n",
                "- 年度 Excess 報酬：" + ", ".join(f"{y}={pct(v)}" for y, v in s["yearly_excess_returns"].items()) + "\n\n",
            ]
    lines += [
        "## 解讀重點\n\n",
        "- 這一步已經從單筆/單月平均報酬，升級成可複利 NAV 指標。\n",
        "- 若 60 日與產業上限版本仍優於 benchmark，代表月營收基本面動能值得正式化。\n",
        "- 但此版本仍不是正式級：尚未使用調整價、未做日級重疊持倉資金配置、未處理漲跌停/停牌/非成交。\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    trades = read_csv(ENRICHED_TRADES)
    monthly_rows = build_monthly_rows(trades, capped=False) + build_monthly_rows(trades, capped=True)
    monthly_rows.sort(key=lambda r: (r["variant"], int(r["holding_days"]), r["revenue_month"]))
    write_csv(OUT_MONTHLY, monthly_rows)
    summary = summarize(monthly_rows)
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary)
    print(json.dumps({"monthly_rows": len(monthly_rows), "outputs": [str(OUT_MONTHLY), str(OUT_SUMMARY), str(OUT_REPORT)]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
