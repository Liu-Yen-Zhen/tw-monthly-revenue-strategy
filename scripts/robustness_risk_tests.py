#!/usr/bin/env python3
"""Phase 3.2 robustness and risk-control diagnostics.

Research-only. No trading, no deployment, no package installation.
Uses enriched proxy trades and recomputes monthly cohort NAV under several variants:
- Top N: 10/15/20
- Round-trip cost: 0.5%/0.7%/1.0%
- 20D average turnover threshold: 50m/100m/300m TWD
- pre-entry 20D runup cap: 15%/30%
- removing largest historical winners

This is still a proxy/cohort backtest, not a daily portfolio simulator.
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
TRADES = PROCESSED / "proxy_backtest_trades_enriched.csv"
OUT_SUMMARY = PROCESSED / "robustness_risk_tests_summary.json"
OUT_VARIANTS = PROCESSED / "robustness_risk_tests_variants.csv"
OUT_REPORT = REPORTS / "phase3_2_robustness_risk_tests_report.md"
BASE_COST = 0.007
INDUSTRY_CAP = 6


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def fl(x: Any) -> float:
    return float(x)


def compound(rs: list[float]) -> float:
    nav = 1.0
    for r in rs:
        nav *= 1 + r
    return nav - 1


def max_drawdown(rs: list[float]) -> float:
    nav = 1.0; peak = 1.0; mdd = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        mdd = min(mdd, nav / peak - 1)
    return mdd


def sharpe(rs: list[float]) -> float | None:
    if len(rs) < 2:
        return None
    sd = statistics.stdev(rs)
    return statistics.mean(rs) / sd * math.sqrt(12) if sd else None


def metric(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"months": 0}
    wins = [r for r in rs if r > 0]
    return {
        "months": len(rs),
        "total_return": compound(rs),
        "annualized_return": (1 + compound(rs)) ** (12 / len(rs)) - 1,
        "mean_month": statistics.mean(rs),
        "median_month": statistics.median(rs),
        "win_rate": len(wins) / len(rs),
        "max_drawdown": max_drawdown(rs),
        "sharpe_proxy": sharpe(rs),
        "best_month": max(rs),
        "worst_month": min(rs),
    }


def largest_winners(trades: list[dict[str, Any]], holding: str, n: int) -> set[str]:
    contrib: dict[str, float] = defaultdict(float)
    for r in trades:
        if r["holding_days"] == holding:
            contrib[r["stock_id"]] += fl(r["net_return"])
    return {sid for sid, _ in sorted(contrib.items(), key=lambda kv: kv[1], reverse=True)[:n]}


def select_month(rows: list[dict[str, Any]], top_n: int, industry_cap: bool) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda r: fl(r["score"]), reverse=True)
    selected = []
    ind_count: dict[str, int] = defaultdict(int)
    for r in rows:
        if industry_cap and ind_count[r["industry"]] >= INDUSTRY_CAP:
            continue
        selected.append(r)
        ind_count[r["industry"]] += 1
        if len(selected) >= top_n:
            break
    return selected


def run_variant(trades: list[dict[str, Any]], *, holding: str, top_n: int, cost: float, min_turnover: float, max_pre20: float, industry_cap: bool, remove_winners: int) -> dict[str, Any]:
    banned = largest_winners(trades, holding, remove_winners) if remove_winners else set()
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if r["holding_days"] != holding:
            continue
        if r["stock_id"] in banned:
            continue
        if fl(r["avg_turnover_20d"]) < min_turnover:
            continue
        if fl(r["pre_ret_20d"]) > max_pre20:
            continue
        by_month[r["revenue_month"]].append(r)
    strat_rs = []
    excess_rs = []
    position_counts = []
    for month in sorted(by_month):
        selected = select_month(by_month[month], top_n, industry_cap)
        if not selected:
            continue
        # original net_return = gross - 0.7%; benchmark_net_return also has 0.7% cost.
        strat_vals = [fl(r["gross_return"]) - cost for r in selected]
        bench_vals = [(fl(r["benchmark_net_return"]) + BASE_COST - cost) for r in selected if r.get("benchmark_net_return") not in ("", None)]
        if not strat_vals or not bench_vals:
            continue
        strat = statistics.mean(strat_vals)
        bench = statistics.mean(bench_vals)
        strat_rs.append(strat)
        excess_rs.append(strat - bench)
        position_counts.append(len(selected))
    m = metric(strat_rs); e = metric(excess_rs)
    return {
        "holding_days": holding,
        "top_n": top_n,
        "cost": cost,
        "min_turnover": min_turnover,
        "max_pre20": max_pre20,
        "industry_cap": industry_cap,
        "remove_winners": remove_winners,
        "avg_positions": statistics.mean(position_counts) if position_counts else 0,
        "strategy_total_return": m.get("total_return"),
        "strategy_ann_return": m.get("annualized_return"),
        "strategy_sharpe": m.get("sharpe_proxy"),
        "strategy_mdd": m.get("max_drawdown"),
        "strategy_win_rate": m.get("win_rate"),
        "excess_total_return": e.get("total_return"),
        "excess_ann_return": e.get("annualized_return"),
        "excess_sharpe": e.get("sharpe_proxy"),
        "excess_mdd": e.get("max_drawdown"),
        "excess_win_rate": e.get("win_rate"),
        "months": m.get("months"),
    }


def fmt_pct(x: Any) -> str:
    if x is None or x == "":
        return "NA"
    return f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    if x is None or x == "":
        return "NA"
    return f"{float(x):.2f}"


def main() -> int:
    trades = read_csv(TRADES)
    variants = []
    # One-at-a-time sensitivity around current preferred: industry-capped Top20, cost 0.7%, min turnover 50m, max pre20 30%.
    specs = []
    for holding in ["20", "40", "60"]:
        for top_n in [10, 15, 20]:
            specs.append((holding, top_n, 0.007, 50_000_000, 0.30, True, 0, "top_n"))
        for cost in [0.005, 0.007, 0.010]:
            specs.append((holding, 20, cost, 50_000_000, 0.30, True, 0, "cost"))
        for turnover in [50_000_000, 100_000_000, 300_000_000]:
            specs.append((holding, 20, 0.007, turnover, 0.30, True, 0, "turnover"))
        for pre20 in [0.15, 0.30]:
            specs.append((holding, 20, 0.007, 50_000_000, pre20, True, 0, "runup"))
        for rem in [0, 5, 10]:
            specs.append((holding, 20, 0.007, 50_000_000, 0.30, True, rem, "remove_winners"))
        specs.append((holding, 20, 0.007, 50_000_000, 0.30, False, 0, "industry_cap_toggle"))
        specs.append((holding, 20, 0.007, 50_000_000, 0.30, True, 0, "industry_cap_toggle"))
    seen = set()
    for holding, top_n, cost, turnover, pre20, cap, rem, family in specs:
        key = (holding, top_n, cost, turnover, pre20, cap, rem)
        if key in seen:
            continue
        seen.add(key)
        row = run_variant(trades, holding=holding, top_n=top_n, cost=cost, min_turnover=turnover, max_pre20=pre20, industry_cap=cap, remove_winners=rem)
        row["family"] = family
        variants.append(row)
    # stringify for CSV
    csv_rows = []
    for r in variants:
        csv_rows.append({k: (round(v, 8) if isinstance(v, float) else v) for k, v in r.items()})
    write_csv(OUT_VARIANTS, csv_rows)
    summary = {"variants": variants}
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(variants)
    print(json.dumps({"variants": len(variants), "outputs": [str(OUT_VARIANTS), str(OUT_SUMMARY), str(OUT_REPORT)]}, ensure_ascii=False, indent=2))
    return 0


def find_variant(vars: list[dict[str, Any]], holding: str, **kwargs: Any) -> dict[str, Any] | None:
    for v in vars:
        if v["holding_days"] != holding:
            continue
        ok = True
        for k, val in kwargs.items():
            if v[k] != val:
                ok = False; break
        if ok:
            return v
    return None


def write_report(vars: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase 3.2 穩健性與風控測試\n\n",
        "本報告針對 Phase 3.1 的 cohort NAV 雛形做 one-at-a-time 穩健性測試。仍不是正式交易系統或投資建議。\n\n",
        "## Baseline\n\n",
        "Baseline = industry capped、Top 20、成本 0.7%、20D 均成交門檻 5,000 萬、進場前 20D 漲幅上限 30%。\n\n",
    ]
    for h in ["20", "40", "60"]:
        base = find_variant(vars, h, top_n=20, cost=0.007, min_turnover=50_000_000, max_pre20=0.30, industry_cap=True, remove_winners=0)
        if not base:
            continue
        lines += [
            f"## 持有 {h} 日 baseline\n\n",
            f"- 月份數：{base['months']}\n",
            f"- 平均持股數：{fmt_num(base['avg_positions'])}\n",
            f"- 策略總報酬：{fmt_pct(base['strategy_total_return'])}\n",
            f"- 策略年化 proxy：{fmt_pct(base['strategy_ann_return'])}\n",
            f"- 策略 Sharpe proxy：{fmt_num(base['strategy_sharpe'])}\n",
            f"- 策略 MDD：{fmt_pct(base['strategy_mdd'])}\n",
            f"- Excess 總報酬：{fmt_pct(base['excess_total_return'])}\n",
            f"- Excess Sharpe proxy：{fmt_num(base['excess_sharpe'])}\n",
            f"- Excess MDD：{fmt_pct(base['excess_mdd'])}\n\n",
            "### Top N 敏感度\n\n",
        ]
        for n in [10, 15, 20]:
            v = find_variant(vars, h, top_n=n, cost=0.007, min_turnover=50_000_000, max_pre20=0.30, industry_cap=True, remove_winners=0)
            if v:
                lines.append(f"- Top {n}: strategy={fmt_pct(v['strategy_total_return'])}, excess={fmt_pct(v['excess_total_return'])}, MDD={fmt_pct(v['strategy_mdd'])}, Sharpe={fmt_num(v['strategy_sharpe'])}\n")
        lines.append("\n### 成本敏感度\n\n")
        for c in [0.005, 0.007, 0.010]:
            v = find_variant(vars, h, top_n=20, cost=c, min_turnover=50_000_000, max_pre20=0.30, industry_cap=True, remove_winners=0)
            if v:
                lines.append(f"- 成本 {c:.1%}: strategy={fmt_pct(v['strategy_total_return'])}, excess={fmt_pct(v['excess_total_return'])}, MDD={fmt_pct(v['strategy_mdd'])}\n")
        lines.append("\n### 流動性門檻敏感度\n\n")
        for t in [50_000_000, 100_000_000, 300_000_000]:
            v = find_variant(vars, h, top_n=20, cost=0.007, min_turnover=t, max_pre20=0.30, industry_cap=True, remove_winners=0)
            if v:
                lines.append(f"- 20D 均成交 >= {int(t/10_000):,} 萬: positions={fmt_num(v['avg_positions'])}, strategy={fmt_pct(v['strategy_total_return'])}, excess={fmt_pct(v['excess_total_return'])}, MDD={fmt_pct(v['strategy_mdd'])}\n")
        lines.append("\n### 去掉歷史最大贏家\n\n")
        for rem in [0, 5, 10]:
            v = find_variant(vars, h, top_n=20, cost=0.007, min_turnover=50_000_000, max_pre20=0.30, industry_cap=True, remove_winners=rem)
            if v:
                lines.append(f"- remove top {rem}: strategy={fmt_pct(v['strategy_total_return'])}, excess={fmt_pct(v['excess_total_return'])}, MDD={fmt_pct(v['strategy_mdd'])}, Sharpe={fmt_num(v['strategy_sharpe'])}\n")
        lines.append("\n")
    lines += [
        "## 初步解讀\n\n",
        "- 如果 Top N、成本、流動性與移除大贏家後仍保有正 excess，代表訊號比較穩健。\n",
        "- 如果移除 top winners 後迅速崩潰，代表策略更偏右尾捕捉，需要明確承認並用分散/風控管理。\n",
        "- MDD 仍是主要問題；下一階段應測市場 regime filter 或降低曝險。\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
