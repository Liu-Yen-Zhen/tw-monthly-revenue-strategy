#!/usr/bin/env python3
"""Phase 3.9: high-Sharpe search for Taiwan monthly-revenue SUR strategies.

Research-only. No trading, no deployment, no package installation, no broker/API use.

Goal from user: find a strategy with Sharpe > 2.5.

This script searches parameter combinations but reports anti-overfit diagnostics:
- full-period Sharpe proxy,
- train Sharpe (2023-2024) and test Sharpe (2025),
- minimum months / average positions,
- remove-top-winners stress,
- top-contributor concentration.

Caveat: monthly Sharpe proxy over a short 2023-2025 sample is fragile; a Sharpe
> 2.5 found by grid search is a candidate hypothesis, not validated alpha.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT_ALL = PROCESSED / "high_sharpe_search_all.csv"
OUT_PASS = PROCESSED / "high_sharpe_search_candidates.csv"
OUT_REMOVE = PROCESSED / "high_sharpe_search_remove_winners.csv"
OUT_TOPTRADES = PROCESSED / "high_sharpe_search_top_trades.csv"
OUT_SUMMARY = PROCESSED / "high_sharpe_search_summary.json"
OUT_REPORT = REPORTS / "phase3_9_high_sharpe_search_report.md"

EX_PATH = ROOT / "scripts" / "execution_realism_tests.py"
spec = importlib.util.spec_from_file_location("execution_realism_tests", EX_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {EX_PATH}")
ex = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(ex)

LIQS = [50_000_000, 100_000_000, 300_000_000]
RECIPES = ["base_sur_core", "sur3_high_no_high_mom"]
TOP_NS = [3, 5, 8, 10, 15]
INDUSTRY_CAPS = [1, 2, 3, 5]
SEMI_CAPS: list[int | None] = [None, 1, 2, 3]
RULES = ["fixed", "sl12_fixed", "sl10_tp25", "trail10", "trail15", "sl8_trail12"]
MAX_HS = [10, 15, 20]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def compound(rs: list[float]) -> float:
    nav = 1.0
    for r in rs:
        nav *= 1 + r
    return nav - 1


def mdd(rs: list[float]) -> float:
    nav = 1.0; peak = 1.0; worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"months": 0}
    sd = statistics.stdev(rs) if len(rs) >= 2 else None
    total = compound(rs)
    return {
        "months": len(rs),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(rs)) - 1,
        "mean_month": statistics.mean(rs),
        "median_month": statistics.median(rs),
        "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd and sd > 1e-12 else None,
        "mdd": mdd(rs),
        "win_rate": sum(1 for x in rs if x > 0) / len(rs),
        "worst_month": min(rs),
        "best_month": max(rs),
    }


def monthly_returns(trades: list[dict[str, Any]], field: str = "net_return", years: set[str] | None = None) -> list[float]:
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in trades:
        y = str(r["entry_date"])[:4]
        if years is not None and y not in years:
            continue
        by_month[r["revenue_month"]].append(float(r[field]))
    return [statistics.mean(by_month[m]) for m in sorted(by_month)]


def remove_winner_metric(trades: list[dict[str, Any]], remove_n: int) -> dict[str, Any]:
    sorted_rows = sorted(trades, key=lambda r: float(r["net_return"]), reverse=True)
    keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:remove_n]}
    kept = [r for r in trades if (r["revenue_month"], r["stock_id"], r["entry_date"]) not in keys]
    sm = metrics(monthly_returns(kept, "net_return"))
    em = metrics(monthly_returns(kept, "excess_return"))
    return {"remove_top_winners": remove_n, "trades": len(kept), "strategy_total_return": sm.get("total_return"), "strategy_sharpe": sm.get("sharpe"), "strategy_mdd": sm.get("mdd"), "excess_total_return": em.get("total_return"), "excess_sharpe": em.get("sharpe"), "excess_mdd": em.get("mdd")}


def top_contributor_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    # Contribution proxy: positive net_return by stock over all selected trades.
    by_stock: dict[str, float] = defaultdict(float)
    positives = 0.0
    for r in trades:
        v = float(r["net_return"])
        if v > 0:
            key = f"{r['stock_id']} {r['stock_name']}"
            by_stock[key] += v
            positives += v
    ranked = sorted(by_stock.items(), key=lambda x: x[1], reverse=True)
    top1 = ranked[0][1] / positives if positives and ranked else None
    top5 = sum(v for _k, v in ranked[:5]) / positives if positives else None
    return {"top1_pos_contrib_share": top1, "top5_pos_contrib_share": top5, "top1_name": ranked[0][0] if ranked else None}


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def run_search() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    pass_rows: list[dict[str, Any]] = []
    remove_rows: list[dict[str, Any]] = []
    top_trade_rows: list[dict[str, Any]] = []

    for liq in LIQS:
        scored, prices_by_stock, date_map, th = ex.build_universe(liq)
        for recipe in RECIPES:
            for top_n in TOP_NS:
                for ind_cap in INDUSTRY_CAPS:
                    if ind_cap > top_n:
                        continue
                    for semi_cap in SEMI_CAPS:
                        if semi_cap is not None and semi_cap > top_n:
                            continue
                        sigs = ex.select_signals(scored, th, recipe, top_n=top_n, industry_cap=ind_cap, semiconductor_cap=semi_cap)
                        if not sigs:
                            continue
                        config = f"{recipe}|liq{liq//1_000_000}m|top{top_n}|ind{ind_cap}|semi{semi_cap if semi_cap is not None else 'none'}"
                        trades = ex.build_rule_trades(sigs, prices_by_stock, date_map, config, RULES, MAX_HS)
                        for rule in RULES:
                            for max_h in MAX_HS:
                                rows = [r for r in trades if r["exit_rule"] == rule and int(r["max_holding_days"]) == max_h]
                                if not rows:
                                    continue
                                rs = monthly_returns(rows, "net_return")
                                exrs = monthly_returns(rows, "excess_return")
                                train = monthly_returns(rows, "net_return", {"2023", "2024"})
                                test = monthly_returns(rows, "net_return", {"2025"})
                                sm, em, trm, tem = metrics(rs), metrics(exrs), metrics(train), metrics(test)
                                months = sm.get("months", 0) or 0
                                avg_pos = len(rows) / months if months else 0
                                conc = top_contributor_stats(rows)
                                out = {
                                    "config": config, "recipe": recipe, "liquidity_threshold": liq, "top_n": top_n, "industry_cap": ind_cap, "semiconductor_cap": semi_cap if semi_cap is not None else "none",
                                    "exit_rule": rule, "max_holding_days": max_h, "months": months, "trades": len(rows), "avg_positions": avg_pos,
                                    "strategy_total_return": sm.get("total_return"), "strategy_ann_return": sm.get("ann_return"), "strategy_sharpe": sm.get("sharpe"), "strategy_mdd": sm.get("mdd"), "strategy_win_rate": sm.get("win_rate"), "worst_month": sm.get("worst_month"),
                                    "excess_total_return": em.get("total_return"), "excess_sharpe": em.get("sharpe"), "excess_mdd": em.get("mdd"),
                                    "train_2023_2024_sharpe": trm.get("sharpe"), "train_2023_2024_return": trm.get("total_return"), "train_months": trm.get("months"),
                                    "test_2025_sharpe": tem.get("sharpe"), "test_2025_return": tem.get("total_return"), "test_months": tem.get("months"),
                                    **conc,
                                }
                                all_rows.append(out)
                                sharpe = sm.get("sharpe")
                                # Candidate = hits target but not too tiny: full Sharpe >2.5, at least 24 months, avg >=3 names, positive test return.
                                if sharpe is not None and sharpe >= 2.5 and months >= 24 and avg_pos >= 3 and (tem.get("total_return") or -999) > 0:
                                    pass_rows.append(out)
                                    for n in [0, 5, 10, 20]:
                                        rr = remove_winner_metric(rows, n)
                                        remove_rows.append({"config": config, "exit_rule": rule, "max_holding_days": max_h, **rr})
                                    for r in sorted(rows, key=lambda x: float(x["net_return"]), reverse=True)[:20]:
                                        top_trade_rows.append({k: r[k] for k in ["config", "recipe", "exit_rule", "max_holding_days", "revenue_month", "entry_date", "exit_date", "actual_holding_days", "exit_reason", "stock_id", "stock_name", "industry", "net_return", "excess_return", "avg_turnover_20d", "sur_3m", "momentum_120_20"]})
    all_rows.sort(key=lambda r: (r["strategy_sharpe"] if r["strategy_sharpe"] is not None else -999), reverse=True)
    pass_rows.sort(key=lambda r: (r["strategy_sharpe"] if r["strategy_sharpe"] is not None else -999), reverse=True)
    return all_rows, pass_rows, remove_rows, top_trade_rows


def write_report(all_rows: list[dict[str, Any]], pass_rows: list[dict[str, Any]], remove_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase 3.9 High-Sharpe Search\n\n",
        "目標：尋找 Sharpe proxy > 2.5 的短線月營收/SUR 策略。仍是 research-only proxy backtest，不是交易建議。\n\n",
        "## 防過擬合規則\n\n",
        "- 全期 monthly Sharpe proxy > 2.5 只視為候選，不視為完成。\n",
        "- 同時檢查 2023-2024 train、2025 test、remove top winners、平均持股數、top contributor concentration。\n",
        "- 樣本只有 2023-2025，若靠 topN 很小或單一年度/單一大贏家達標，可信度要降級。\n\n",
        "## 搜尋結果摘要\n\n",
        f"- 搜尋組合數：{len(all_rows)}\n",
        f"- Sharpe > 2.5 且 months>=24、avg_positions>=3、2025 return>0 的候選數：{len(pass_rows)}\n\n",
        "## 全部組合 Sharpe Top 20\n\n",
    ]
    for r in all_rows[:20]:
        lines.append(f"- Sharpe={fmt_num(r['strategy_sharpe'])}, return={fmt_pct(r['strategy_total_return'])}, MDD={fmt_pct(r['strategy_mdd'])}, excess={fmt_pct(r['excess_total_return'])}, trainS={fmt_num(r['train_2023_2024_sharpe'])}, testS={fmt_num(r['test_2025_sharpe'])}, avg_pos={float(r['avg_positions']):.1f}｜{r['config']}｜{r['exit_rule']} {r['max_holding_days']}D｜top5share={fmt_pct(r['top5_pos_contrib_share'])}\n")
    lines.append("\n## 達標候選 Top 20\n\n")
    if not pass_rows:
        lines.append("- 沒有找到符合最低防過擬合條件的 Sharpe > 2.5 候選。\n")
    for r in pass_rows[:20]:
        lines.append(f"- Sharpe={fmt_num(r['strategy_sharpe'])}, return={fmt_pct(r['strategy_total_return'])}, MDD={fmt_pct(r['strategy_mdd'])}, win={fmt_pct(r['strategy_win_rate'])}, excess={fmt_pct(r['excess_total_return'])}, trainS={fmt_num(r['train_2023_2024_sharpe'])}, testS={fmt_num(r['test_2025_sharpe'])}, avg_pos={float(r['avg_positions']):.1f}, top1={r['top1_name']} ({fmt_pct(r['top1_pos_contrib_share'])}), top5share={fmt_pct(r['top5_pos_contrib_share'])}\n  `{r['config']} | {r['exit_rule']} {r['max_holding_days']}D`\n")
    if pass_rows:
        best = pass_rows[0]
        lines.append("\n## Best candidate remove-winners\n\n")
        rows = [r for r in remove_rows if r["config"] == best["config"] and r["exit_rule"] == best["exit_rule"] and int(r["max_holding_days"]) == int(best["max_holding_days"])]
        for r in rows:
            lines.append(f"- remove {r['remove_top_winners']}：strategy={fmt_pct(r['strategy_total_return'])}, Sharpe={fmt_num(r['strategy_sharpe'])}, excess={fmt_pct(r['excess_total_return'])}, excessSharpe={fmt_num(r['excess_sharpe'])}, MDD={fmt_pct(r['strategy_mdd'])}\n")
    lines += [
        "\n## 初步判讀原則\n\n",
        "- 若達標策略 train Sharpe 不高但 test Sharpe 很高，通常是 2025 regime / AI-memory 題材驅動，不可直接視為穩定策略。\n",
        "- 若 top5 positive contribution share 過高，代表 Sharpe 可能由少數股票貢獻；需要 remove-winners 後仍維持。\n",
        "- 下一步應針對候選做更嚴格 OOS / walk-forward、交易成本加倍、產業移除、日內可成交性測試。\n\n",
        "## 輸出檔案\n\n",
        f"- `{OUT_ALL}`\n- `{OUT_PASS}`\n- `{OUT_REMOVE}`\n- `{OUT_TOPTRADES}`\n- `{OUT_SUMMARY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    all_rows, pass_rows, remove_rows, top_trade_rows = run_search()
    write_csv(OUT_ALL, all_rows)
    write_csv(OUT_PASS, pass_rows)
    write_csv(OUT_REMOVE, remove_rows)
    write_csv(OUT_TOPTRADES, top_trade_rows)
    summary = {
        "searched_rows": len(all_rows),
        "candidate_rows": len(pass_rows),
        "objective": "monthly Sharpe proxy >= 2.5 with months>=24 avg_positions>=3 and positive 2025 return",
        "best": pass_rows[0] if pass_rows else (all_rows[0] if all_rows else None),
        "outputs": [str(OUT_ALL), str(OUT_PASS), str(OUT_REMOVE), str(OUT_TOPTRADES), str(OUT_SUMMARY), str(OUT_REPORT)],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(all_rows, pass_rows, remove_rows)
    print(json.dumps({"searched_rows": len(all_rows), "candidate_rows": len(pass_rows), "best_sharpe": all_rows[0].get("strategy_sharpe") if all_rows else None, "outputs": summary["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
