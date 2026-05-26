#!/usr/bin/env python3
"""Phase 3.8: execution-realism tests for 3M SUR persistence strategy.

Research-only. No trading, no deployment, no package installation, no broker/API use.

This phase starts from the Phase 3.7 finding that `sur3_high_no_high_mom`
(3M revenue surprise persistence + avoid overextended momentum) is the most
interesting short-horizon extension. It tests close-price proxy exit rules:
- fixed 10/15/20D holds,
- stop-loss and take-profit rules,
- trailing stop rules,
- liquidity thresholds and semiconductor caps.

Caveat: available historical price data has close and turnover only, not full
OHLC/order-book/limit-up-down flags. Execution realism here is still a proxy.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, cast

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT_RULES = PROCESSED / "execution_realism_exit_rules.csv"
OUT_YEARLY = PROCESSED / "execution_realism_yearly.csv"
OUT_REMOVE = PROCESSED / "execution_realism_remove_winners.csv"
OUT_LIQ = PROCESSED / "execution_realism_liquidity_semicap.csv"
OUT_SUMMARY = PROCESSED / "execution_realism_summary.json"
OUT_REPORT = REPORTS / "phase3_8_execution_realism_report.md"

SUR_PATH = ROOT / "scripts" / "sur_factor_tests.py"
spec = importlib.util.spec_from_file_location("sur_factor_tests", SUR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {SUR_PATH}")
sur = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(sur)

COST = 0.007
BASE_LIQ = 50_000_000
HOLDINGS = [10, 15, 20]


def fnum(x: Any) -> float | None:
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None


def q(vals: list[float], p: float) -> float:
    vals = sorted(vals)
    i = (len(vals) - 1) * p
    lo, hi = math.floor(i), math.ceil(i)
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - i) + vals[hi] * (i - lo)


def compound(rs: list[float]) -> float:
    nav = 1.0
    for r in rs:
        nav *= 1 + r
    return nav - 1


def mdd(rs: list[float]) -> float:
    nav = 1.0
    peak = 1.0
    worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(monthly: list[float]) -> dict[str, Any]:
    if not monthly:
        return {}
    sd = statistics.stdev(monthly) if len(monthly) >= 2 else None
    total = compound(monthly)
    return {
        "months": len(monthly),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(monthly)) - 1,
        "mean_month": statistics.mean(monthly),
        "median_month": statistics.median(monthly),
        "win_rate": sum(1 for x in monthly if x > 0) / len(monthly),
        "sharpe_proxy": statistics.mean(monthly) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(monthly),
        "best_month": max(monthly),
        "worst_month": min(monthly),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def build_universe(liq: int) -> tuple[list[dict[str, Any]], dict, dict[str, dict[tuple[str, str], float]], dict[str, tuple[float, float]]]:
    sur.COST = COST
    sur.HOLDINGS = HOLDINGS
    sur.MIN_AVG_TURNOVER_20D = liq
    rev_rows = sur.build_revenue_panel(sur.read_csv(sur.REV_CSV))
    prices_by_stock, trading_dates, date_map = sur.build_price_maps(sur.read_csv(sur.PRICE_CSV))
    cands = sur.eligible_candidates(rev_rows, prices_by_stock, trading_dates)
    scored = sur.add_scores(cands)
    th: dict[str, tuple[float, float]] = {}
    for field in ["momentum_120_20", "sur_3m", "qtd_yoy", "rev_accel_3m"]:
        vals = [float(r[field]) for r in scored if fnum(r.get(field)) is not None]
        th[field] = (q(vals, 1 / 3), q(vals, 2 / 3))
    return scored, prices_by_stock, date_map, th


def select_signals(
    scored: list[dict[str, Any]],
    th: dict[str, tuple[float, float]],
    recipe: str,
    top_n: int = 15,
    industry_cap: int = 5,
    semiconductor_cap: int | None = None,
) -> list[dict[str, Any]]:
    def pred(r: dict[str, Any]) -> bool:
        if recipe == "base_sur_core":
            return True
        if recipe == "sur3_high_no_high_mom":
            return r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1]
        raise ValueError(recipe)

    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        if pred(r):
            by_month[r["revenue_month"]].append(r)
    signals: list[dict[str, Any]] = []
    for month, rows in by_month.items():
        ind_counts: dict[str, int] = defaultdict(int)
        semi_count = 0
        chosen = 0
        for r in sorted(rows, key=lambda x: x["score_sur_core"], reverse=True):
            if ind_counts[r["industry"]] >= industry_cap:
                continue
            if semiconductor_cap is not None and r["industry"] == "半導體業" and semi_count >= semiconductor_cap:
                continue
            r2 = dict(r)
            r2["recipe"] = recipe
            r2["score"] = r["score_sur_core"]
            signals.append(r2)
            chosen += 1
            ind_counts[r["industry"]] += 1
            if r["industry"] == "半導體業":
                semi_count += 1
            if chosen >= top_n:
                break
    return signals


def benchmark_return(date_map: dict[str, dict[tuple[str, str], float]], entry: str, exit_: str) -> float | None:
    a = date_map.get(entry); b = date_map.get(exit_)
    if not a or not b:
        return None
    vals = []
    for k in set(a).intersection(b):
        if a[k] > 0 and b[k] > 0:
            vals.append(b[k] / a[k] - 1 - COST)
    return statistics.mean(vals) if vals else None


def exit_idx_for_rule(pr: list[dict[str, Any]], idx: int, rule: str, max_h: int) -> tuple[int, str, float]:
    entry = float(pr[idx]["close"])
    peak = entry
    stop = None
    take = None
    trail = None
    if rule == "fixed":
        return min(idx + max_h, len(pr) - 1), "time", 0.0
    if rule == "sl8_fixed":
        stop = -0.08
    elif rule == "sl12_fixed":
        stop = -0.12
    elif rule == "tp15_fixed":
        take = 0.15
    elif rule == "tp25_fixed":
        take = 0.25
    elif rule == "sl8_tp20":
        stop, take = -0.08, 0.20
    elif rule == "sl10_tp25":
        stop, take = -0.10, 0.25
    elif rule == "trail10":
        trail = 0.10
    elif rule == "trail15":
        trail = 0.15
    elif rule == "sl8_trail12":
        stop, trail = -0.08, 0.12
    else:
        raise ValueError(rule)
    end = min(idx + max_h, len(pr) - 1)
    for j in range(idx + 1, end + 1):
        close = float(pr[j]["close"])
        ret = close / entry - 1
        peak = max(peak, close)
        dd_from_peak = close / peak - 1
        if stop is not None and ret <= stop:
            return j, "stop", ret
        if take is not None and ret >= take:
            return j, "take_profit", ret
        if trail is not None and dd_from_peak <= -trail and peak > entry:
            return j, "trailing_stop", ret
    return end, "time", float(pr[end]["close"]) / entry - 1


def build_rule_trades(signals: list[dict[str, Any]], prices_by_stock: dict, date_map: dict[str, dict[tuple[str, str], float]], config: str, rules: list[str], max_hs: list[int]) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    bench_cache: dict[tuple[str, str], float | None] = {}
    for s in signals:
        pr = prices_by_stock[(s["market"], s["stock_id"])]
        idx = int(s["price_idx"])
        if idx >= len(pr) - 1:
            continue
        entry_price = float(pr[idx]["close"])
        for max_h in max_hs:
            if idx + max_h >= len(pr):
                continue
            for rule in rules:
                exit_idx, reason, _rule_ret = exit_idx_for_rule(pr, idx, rule, max_h)
                exit_rec = pr[exit_idx]
                bench_key = (s["entry_date"], exit_rec["date"])
                if bench_key not in bench_cache:
                    bench_cache[bench_key] = benchmark_return(date_map, *bench_key)
                bench = bench_cache[bench_key]
                if bench is None:
                    continue
                gross = float(exit_rec["close"]) / entry_price - 1
                net = gross - COST
                trades.append({
                    "config": config, "recipe": s["recipe"], "exit_rule": rule, "max_holding_days": max_h,
                    "revenue_month": s["revenue_month"], "entry_date": s["entry_date"], "exit_date": exit_rec["date"], "actual_holding_days": exit_idx - idx,
                    "exit_reason": reason, "market": s["market"], "stock_id": s["stock_id"], "stock_name": s["stock_name"], "industry": s["industry"],
                    "score": round(float(s["score"]), 6), "sur_3m": round(float(s["sur_3m"]), 6), "momentum_120_20": round(float(s["momentum_120_20"]), 6),
                    "qtd_yoy": round(float(s["qtd_yoy"]), 4), "rev_accel_3m": round(float(s["rev_accel_3m"]), 4),
                    "pre_ret_20d": round(float(s["pre_ret_20d"]), 6), "avg_turnover_20d": int(s["avg_turnover_20d"]),
                    "entry_price": entry_price, "exit_price": float(exit_rec["close"]),
                    "gross_return": round(gross, 8), "net_return": round(net, 8), "benchmark_net_return": round(bench, 8), "excess_return": round(net - bench, 8),
                })
    return trades


def monthly_returns(trades: list[dict[str, Any]], config: str, rule: str, max_h: int, field: str) -> list[float]:
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in trades:
        if r["config"] == config and r["exit_rule"] == rule and int(r["max_holding_days"]) == max_h:
            by_month[r["revenue_month"]].append(float(r[field]))
    return [statistics.mean(by_month[m]) for m in sorted(by_month)]


def summarize_rules(trades: list[dict[str, Any]], configs: list[str], rules: list[str], max_hs: list[int]) -> list[dict[str, Any]]:
    out = []
    for config in configs:
        for rule in rules:
            for max_h in max_hs:
                rows = [r for r in trades if r["config"] == config and r["exit_rule"] == rule and int(r["max_holding_days"]) == max_h]
                strat = metrics(monthly_returns(trades, config, rule, max_h, "net_return"))
                excess = metrics(monthly_returns(trades, config, rule, max_h, "excess_return"))
                months = strat.get("months", 0) or 0
                reason_counts = defaultdict(int)
                for r in rows:
                    reason_counts[r["exit_reason"]] += 1
                out.append({
                    "config": config, "exit_rule": rule, "max_holding_days": max_h, "months": months,
                    "trades": len(rows), "avg_positions": len(rows) / months if months else 0,
                    "avg_actual_holding_days": statistics.mean([int(r["actual_holding_days"]) for r in rows]) if rows else None,
                    "strategy_total_return": strat.get("total_return"), "strategy_ann_return": strat.get("ann_return"), "strategy_sharpe": strat.get("sharpe_proxy"),
                    "strategy_mdd": strat.get("mdd"), "strategy_win_rate": strat.get("win_rate"),
                    "excess_total_return": excess.get("total_return"), "excess_mdd": excess.get("mdd"), "excess_win_rate": excess.get("win_rate"),
                    "stop_count": reason_counts.get("stop", 0), "take_profit_count": reason_counts.get("take_profit", 0),
                    "trailing_stop_count": reason_counts.get("trailing_stop", 0), "time_exit_count": reason_counts.get("time", 0),
                })
    return out


def yearly_rows(trades: list[dict[str, Any]], configs: list[str], selected: list[tuple[str, int]]) -> list[dict[str, Any]]:
    out = []
    for config in configs:
        for rule, max_h in selected:
            by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for r in trades:
                if r["config"] == config and r["exit_rule"] == rule and int(r["max_holding_days"]) == max_h:
                    by[(str(r["entry_date"])[:4], r["revenue_month"])].append(r)
            for y in sorted({yy for yy, _m in by}):
                months = sorted(m for yy, m in by if yy == y)
                strat = [statistics.mean(float(x["net_return"]) for x in by[(y, m)]) for m in months]
                excess = [statistics.mean(float(x["excess_return"]) for x in by[(y, m)]) for m in months]
                sm, em = metrics(strat), metrics(excess)
                out.append({"config": config, "exit_rule": rule, "max_holding_days": max_h, "year": y, "months": len(months),
                            "strategy_return": sm.get("total_return"), "strategy_mdd": sm.get("mdd"), "strategy_win_rate": sm.get("win_rate"),
                            "excess_return": em.get("total_return"), "excess_mdd": em.get("mdd"), "excess_win_rate": em.get("win_rate")})
    return out


def remove_winners_rows(trades: list[dict[str, Any]], configs: list[str], selected: list[tuple[str, int]]) -> list[dict[str, Any]]:
    out = []
    for config in configs:
        for rule, max_h in selected:
            base = [r for r in trades if r["config"] == config and r["exit_rule"] == rule and int(r["max_holding_days"]) == max_h]
            sorted_rows = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
            for remove_n in [0, 5, 10, 20]:
                keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:remove_n]}
                kept = [r for r in base if (r["revenue_month"], r["stock_id"], r["entry_date"]) not in keys]
                by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for r in kept:
                    by_month[r["revenue_month"]].append(r)
                strat = [statistics.mean(float(x["net_return"]) for x in by_month[m]) for m in sorted(by_month)]
                excess = [statistics.mean(float(x["excess_return"]) for x in by_month[m]) for m in sorted(by_month)]
                sm, em = metrics(strat), metrics(excess)
                out.append({"config": config, "exit_rule": rule, "max_holding_days": max_h, "remove_top_winners": remove_n, "trades": len(kept),
                            "strategy_total_return": sm.get("total_return"), "strategy_mdd": sm.get("mdd"), "strategy_sharpe": sm.get("sharpe_proxy"),
                            "excess_total_return": em.get("total_return"), "excess_mdd": em.get("mdd")})
    return out


def liquidity_semicap_tests(rules: list[str]) -> list[dict[str, Any]]:
    out = []
    for liq in [50_000_000, 100_000_000, 300_000_000]:
        scored, prices_by_stock, date_map, th = build_universe(liq)
        for semi_cap in [None, 5, 3, 2]:
            label = f"liq{liq//1_000_000}m_semicap{semi_cap if semi_cap is not None else 'none'}"
            sigs = select_signals(scored, th, "sur3_high_no_high_mom", 15, 5, semi_cap)
            trades = build_rule_trades(sigs, prices_by_stock, date_map, label, ["fixed"], [20])
            summary = summarize_rules(trades, [label], ["fixed"], [20])[0]
            summary["liquidity_threshold"] = liq
            summary["semiconductor_cap"] = semi_cap if semi_cap is not None else "none"
            out.append(summary)
    return out


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(rule_rows: list[dict[str, Any]], yearly: list[dict[str, Any]], remove_rows: list[dict[str, Any]], liq_rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    def find(config: str, rule: str, h: int) -> dict[str, Any]:
        return next(r for r in rule_rows if r["config"] == config and r["exit_rule"] == rule and int(r["max_holding_days"]) == h)
    best10 = max([r for r in rule_rows if r["config"] == "sur3_high_no_high_mom" and int(r["max_holding_days"]) == 10], key=lambda r: float(r["excess_total_return"] or -999))
    best20 = max([r for r in rule_rows if r["config"] == "sur3_high_no_high_mom" and int(r["max_holding_days"]) == 20], key=lambda r: float(r["excess_total_return"] or -999))
    lines = [
        "# Phase 3.8 3M SUR persistence + execution realism\n\n",
        "本階段仍是 research-only proxy/cohort backtest，不是實際持倉、paper order 或交易建議。價格資料只有 close/turnover，沒有 OHLC、逐筆、漲跌停與委託簿，因此停損/停利/追蹤停損都是 close-price proxy。\n\n",
        "## 研究問題\n\n",
        "Phase 3.7 顯示 `sur3_high_no_high_mom` 是較有價值的短線延伸。本階段測試固定持有與停利/停損/trailing stop，並測流動性門檻與半導體 cap。\n\n",
        "## 最佳 exit-rule snapshot\n\n",
        f"- sur3 10D 最佳：`{best10['exit_rule']}`，strategy={fmt_pct(best10['strategy_total_return'])}，excess={fmt_pct(best10['excess_total_return'])}，Sharpe={fmt_num(best10['strategy_sharpe'])}，MDD={fmt_pct(best10['strategy_mdd'])}，avg actual days={fmt_num(best10['avg_actual_holding_days'])}\n",
        f"- sur3 20D 最佳：`{best20['exit_rule']}`，strategy={fmt_pct(best20['strategy_total_return'])}，excess={fmt_pct(best20['excess_total_return'])}，Sharpe={fmt_num(best20['strategy_sharpe'])}，MDD={fmt_pct(best20['strategy_mdd'])}，avg actual days={fmt_num(best20['avg_actual_holding_days'])}\n\n",
        "## sur3_high_no_high_mom：主要 exit rules\n\n",
    ]
    for rule in ["fixed", "sl8_fixed", "sl12_fixed", "tp15_fixed", "tp25_fixed", "sl8_tp20", "sl10_tp25", "trail10", "trail15", "sl8_trail12"]:
        lines.append(f"### {rule}\n")
        for h in HOLDINGS:
            r = find("sur3_high_no_high_mom", rule, h)
            lines.append(f"- {h}D max：strategy={fmt_pct(r['strategy_total_return'])}, excess={fmt_pct(r['excess_total_return'])}, Sharpe={fmt_num(r['strategy_sharpe'])}, MDD={fmt_pct(r['strategy_mdd'])}, win={fmt_pct(r['strategy_win_rate'])}, avg days={fmt_num(r['avg_actual_holding_days'])}, stop/tp/trail/time={r['stop_count']}/{r['take_profit_count']}/{r['trailing_stop_count']}/{r['time_exit_count']}\n")
        lines.append("\n")
    lines.append("## Liquidity / semiconductor cap：sur3 fixed 20D\n\n")
    for r in liq_rows:
        lines.append(f"- liq={int(r['liquidity_threshold'])//1_000_000}m, semi_cap={r['semiconductor_cap']}：strategy={fmt_pct(r['strategy_total_return'])}, excess={fmt_pct(r['excess_total_return'])}, Sharpe={fmt_num(r['strategy_sharpe'])}, MDD={fmt_pct(r['strategy_mdd'])}, avg positions={float(r['avg_positions']):.1f}\n")
    lines.append("\n## Remove top winners：sur3 fixed vs stop/take\n\n")
    for rule, h in [("fixed", 20), ("trail15", 20), ("sl8_tp20", 20), ("trail10", 20), ("fixed", 10)]:
        lines.append(f"### {rule} {h}D\n")
        for r in [x for x in remove_rows if x["config"] == "sur3_high_no_high_mom" and x["exit_rule"] == rule and int(x["max_holding_days"]) == h]:
            lines.append(f"- remove {r['remove_top_winners']}：strategy={fmt_pct(r['strategy_total_return'])}, excess={fmt_pct(r['excess_total_return'])}, MDD={fmt_pct(r['strategy_mdd'])}\n")
        lines.append("\n")
    lines += [
        "## 初步解讀\n\n",
        "- 固定 20D 仍是重要 exit baseline；但 `trail15` / `trail10` 這輪值得升級成候選，因為它們保留大部分右尾，同時降低 MDD / 提升 Sharpe。\n",
        "- 10D 若加入 stop/take，沒有明顯解決 remove-winners 後 edge 消失的問題；10D 還是不適合作為主策略，只適合觀察 aggressive sleeve。\n",
        "- 提高流動性門檻與半導體 cap 是必要 robustness：如果 300m 或 semi cap 後仍可接受，才更接近 paper-trading 候選。\n",
        "- 由於只有 close-price proxy，下一步若要更接近實盤，需要補日內/OHLC、漲跌停與成交可得性資料。\n",
        "\n## 輸出檔案\n\n",
        f"- `{OUT_RULES}`\n- `{OUT_YEARLY}`\n- `{OUT_REMOVE}`\n- `{OUT_LIQ}`\n- `{OUT_SUMMARY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    rules = ["fixed", "sl8_fixed", "sl12_fixed", "tp15_fixed", "tp25_fixed", "sl8_tp20", "sl10_tp25", "trail10", "trail15", "sl8_trail12"]
    scored, prices_by_stock, date_map, th = build_universe(BASE_LIQ)
    configs = ["base_sur_core", "sur3_high_no_high_mom"]
    all_trades: list[dict[str, Any]] = []
    signal_counts = {}
    for config in configs:
        sigs = select_signals(scored, th, config)
        signal_counts[config] = len(sigs)
        all_trades.extend(build_rule_trades(sigs, prices_by_stock, date_map, config, rules, HOLDINGS))
    rule_rows = summarize_rules(all_trades, configs, rules, HOLDINGS)
    selected = [("fixed", 10), ("fixed", 20), ("trail15", 20), ("sl8_tp20", 20), ("trail10", 20)]
    yearly = yearly_rows(all_trades, configs, selected)
    remove_rows = remove_winners_rows(all_trades, configs, selected)
    liq_rows = liquidity_semicap_tests(["fixed"])
    write_csv(OUT_RULES, rule_rows)
    write_csv(OUT_YEARLY, yearly)
    write_csv(OUT_REMOVE, remove_rows)
    write_csv(OUT_LIQ, liq_rows)
    summary = {"thresholds": th, "signal_counts": signal_counts, "rules": rules, "holdings": HOLDINGS, "cost": COST, "outputs": [str(OUT_RULES), str(OUT_YEARLY), str(OUT_REMOVE), str(OUT_LIQ), str(OUT_SUMMARY), str(OUT_REPORT)]}
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(rule_rows, yearly, remove_rows, liq_rows, summary)
    print(json.dumps({"rule_rows": len(rule_rows), "yearly_rows": len(yearly), "remove_rows": len(remove_rows), "liq_rows": len(liq_rows), "outputs": summary["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
