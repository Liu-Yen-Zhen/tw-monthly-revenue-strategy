#!/usr/bin/env python3
"""Phase 3.11: signal-quality search for Taiwan monthly-revenue SUR strategy.

Research-only. No live orders, no deployment, no broker/API use.

Goal: explore better selection signals while preserving prior good variants.
Compared against preserved incumbent S1 from reports/promising_strategy_registry.md:
  sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | sl8_trail12 20D

Focus:
- alternative factor recipes using existing point-in-time candidate features,
- simple winner-likelihood style filters,
- dynamic within-month weighting,
- robust objective that penalizes remove-top-winner dependence.
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
OUT_RESULTS = PROCESSED / "signal_quality_search_results.csv"
OUT_REMOVE = PROCESSED / "signal_quality_search_remove_winners.csv"
OUT_TOPTRADES = PROCESSED / "signal_quality_search_top_trades.csv"
OUT_SUMMARY = PROCESSED / "signal_quality_search_summary.json"
OUT_REPORT = REPORTS / "phase3_11_signal_quality_search_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

EX_PATH = ROOT / "scripts" / "execution_realism_tests.py"
spec = importlib.util.spec_from_file_location("execution_realism_tests", EX_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {EX_PATH}")
ex = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(ex)

LIQS = [50_000_000, 100_000_000]
TOP_NS = [6, 8, 10, 12]
IND_CAPS = [2, 3, 4]
SEMI_CAPS: list[int | None] = [None, 2, 3]
RULES = ["fixed", "trail10", "trail15", "sl8_trail12"]
MAX_HS = [15, 20]
WEIGHT_MODES = ["equal", "score_linear", "score_softmax", "score_x_liquidity", "score_x_abturn"]

# Weight recipes over rank features already computed by sur_factor_tests.add_scores.
RECIPES: dict[str, dict[str, float]] = {
    "incumbent_sur_core": {"sur_rank": 0.40, "sur_3m_rank": 0.20, "qtd_yoy_rank": 0.15, "rev_accel_rank": 0.15, "liquidity_rank": 0.10},
    "persistent_indadj": {"sur_3m_rank": 0.30, "ind_adj_sur_rank": 0.25, "ind_adj_rev3_rank": 0.20, "abnormal_turnover_rank": 0.15, "anti_runup20_rank": 0.10},
    "right_tail_confirmation": {"sur_3m_rank": 0.30, "sur_rank": 0.20, "abnormal_turnover_rank": 0.20, "momentum_120_20_rank": 0.15, "liquidity_rank": 0.10, "anti_runup20_rank": 0.05},
    "underreaction_quality": {"ind_adj_sur_rank": 0.25, "sur_3m_rank": 0.25, "anti_runup20_rank": 0.20, "abnormal_turnover_rank": 0.15, "qtd_yoy_rank": 0.10, "liquidity_rank": 0.05},
    "fundamental_persistence": {"sur_3m_rank": 0.30, "rev_3m_rank": 0.20, "qtd_yoy_rank": 0.20, "rev_accel_rank": 0.15, "ind_adj_rev3_rank": 0.10, "liquidity_rank": 0.05},
    "balanced_no_chase": {"sur_3m_rank": 0.22, "ind_adj_sur_rank": 0.18, "ind_adj_rev3_rank": 0.15, "abnormal_turnover_rank": 0.15, "anti_runup20_rank": 0.15, "qtd_yoy_rank": 0.10, "liquidity_rank": 0.05},
}

FILTERS = [
    "sur3_high_no_high_mom",       # incumbent gate
    "sur3_high_underreaction",     # persistent surprise + low/medium recent runup
    "ind_sur_high_no_high_mom",    # industry-adjusted surprise + no overextended 120-20 momentum
    "sur3_and_abturn_high",        # persistent surprise + abnormal turnover confirmation
    "quality_persist_gate",        # persistent surprise + QTD/rev accel above median
    "loose_all_positive",          # broad positive fundamental pool
]


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
        "months": len(rs), "total_return": total,
        "ann_return": (1 + total) ** (12 / len(rs)) - 1,
        "mean_month": statistics.mean(rs), "median_month": statistics.median(rs),
        "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd and sd > 1e-12 else None,
        "mdd": mdd(rs), "win_rate": sum(1 for x in rs if x > 0) / len(rs),
        "worst_month": min(rs), "best_month": max(rs),
    }


def score_row(r: dict[str, Any], recipe: str) -> float:
    return sum(float(r[k]) * w for k, w in RECIPES[recipe].items())


def pass_filter(r: dict[str, Any], th: dict[str, tuple[float, float]], filt: str) -> bool:
    if filt == "sur3_high_no_high_mom":
        return r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1]
    if filt == "sur3_high_underreaction":
        return r["sur_3m"] >= th["sur_3m"][1] and r["pre_ret_20d"] <= 0.12 and r["momentum_120_20"] <= th["momentum_120_20"][1]
    if filt == "ind_sur_high_no_high_mom":
        return r["ind_adj_sur"] > 0 and r["ind_adj_sur_rank"] >= 2/3 and r["momentum_120_20"] <= th["momentum_120_20"][1]
    if filt == "sur3_and_abturn_high":
        return r["sur_3m"] >= th["sur_3m"][1] and r["abnormal_turnover_rank"] >= 0.50 and r["pre_ret_20d"] <= 0.20
    if filt == "quality_persist_gate":
        return r["sur_3m"] >= th["sur_3m"][1] and r["qtd_yoy"] >= th["qtd_yoy"][0] and r["rev_accel_3m"] >= th["rev_accel_3m"][0]
    if filt == "loose_all_positive":
        return r["sur"] > 0 and r["sur_3m"] > 0 and r["rev_3m_yoy"] > 0 and r["pre_ret_20d"] <= 0.25
    raise ValueError(filt)


def select_custom(scored: list[dict[str, Any]], th: dict[str, tuple[float, float]], recipe: str, filt: str, top_n: int, industry_cap: int, semi_cap: int | None) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        if pass_filter(r, th, filt):
            r2 = dict(r)
            r2["recipe"] = recipe
            r2["score"] = score_row(r, recipe)
            by_month[r["revenue_month"]].append(r2)
    out: list[dict[str, Any]] = []
    for _m, rows in by_month.items():
        ind_counts: dict[str, int] = defaultdict(int)
        semi_count = 0
        chosen = 0
        for r in sorted(rows, key=lambda x: x["score"], reverse=True):
            if ind_counts[r["industry"]] >= industry_cap:
                continue
            if semi_cap is not None and r["industry"] == "半導體業" and semi_count >= semi_cap:
                continue
            out.append(r)
            ind_counts[r["industry"]] += 1
            if r["industry"] == "半導體業":
                semi_count += 1
            chosen += 1
            if chosen >= top_n:
                break
    return out


def monthly_weighted(trades: list[dict[str, Any]], field: str = "net_return", years: set[str] | None = None, remove_keys: set[tuple[str, str, str]] | None = None) -> tuple[list[float], int, float]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if years is not None and str(r["entry_date"])[:4] not in years:
            continue
        key = (r["revenue_month"], r["stock_id"], r["entry_date"])
        if remove_keys is not None and key in remove_keys:
            continue
        by_month[r["revenue_month"]].append(r)
    returns: list[float] = []
    total_positions = 0
    for m in sorted(by_month):
        rows = by_month[m]
        total_positions += len(rows)
        ws = [float(r.get("portfolio_weight", 1.0)) for r in rows]
        s = sum(ws)
        if s <= 0:
            ws = [1 / len(rows)] * len(rows)
        else:
            ws = [w / s for w in ws]
        returns.append(sum(w * float(r[field]) for w, r in zip(ws, rows)))
    avg_pos = total_positions / len(returns) if returns else 0
    return returns, total_positions, avg_pos


def apply_weights(trades: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        by_month[r["revenue_month"]].append(r)
    out: list[dict[str, Any]] = []
    for _m, rows in by_month.items():
        scores = [float(r["score"]) for r in rows]
        min_s, max_s = min(scores), max(scores)
        for r in rows:
            r2 = dict(r)
            z = (float(r["score"]) - min_s) / (max_s - min_s) if max_s > min_s else 1.0
            if mode == "equal":
                w = 1.0
            elif mode == "score_linear":
                w = 0.5 + z
            elif mode == "score_softmax":
                w = math.exp(2.0 * z)
            elif mode == "score_x_liquidity":
                w = (0.5 + z) * (0.5 + float(r.get("liquidity_rank", 0.5)))
            elif mode == "score_x_abturn":
                w = (0.5 + z) * (0.5 + float(r.get("abnormal_turnover_rank", 0.5)))
            else:
                raise ValueError(mode)
            r2["portfolio_weight"] = w
            out.append(r2)
    return out


def remove_winner_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    sorted_rows = sorted(trades, key=lambda r: float(r["net_return"]), reverse=True)
    out: dict[str, Any] = {}
    for n in [0, 5, 10, 20]:
        keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:n]}
        rs, _, _ = monthly_weighted(trades, remove_keys=keys)
        sm = metrics(rs)
        out[f"remove{n}_return"] = sm.get("total_return")
        out[f"remove{n}_sharpe"] = sm.get("sharpe")
        out[f"remove{n}_mdd"] = sm.get("mdd")
    return out


def contributor_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    by_stock: dict[str, float] = defaultdict(float)
    pos = 0.0
    for r in trades:
        v = float(r["net_return"]) * float(r.get("portfolio_weight", 1.0))
        if v > 0:
            by_stock[f"{r['stock_id']} {r['stock_name']}"] += v
            pos += v
    ranked = sorted(by_stock.items(), key=lambda x: x[1], reverse=True)
    return {
        "top1_name": ranked[0][0] if ranked else None,
        "top1_pos_contrib_share": ranked[0][1] / pos if pos and ranked else None,
        "top5_pos_contrib_share": sum(v for _k, v in ranked[:5]) / pos if pos else None,
    }


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def status_for(r: dict[str, Any]) -> str:
    s = r.get("sharpe")
    r5 = r.get("remove5_sharpe")
    train = r.get("train_sharpe")
    avg_pos = float(r.get("avg_positions") or 0)
    if s is not None and float(s) >= 2.5 and r5 is not None and float(r5) >= 1.8 and train is not None and float(train) >= 1.5 and avg_pos >= 5:
        return "promote_candidate"
    # Preserve variants that do not improve raw Sharpe but materially improve winner-removal robustness.
    if s is not None and float(s) >= 2.10 and r5 is not None and float(r5) >= 1.80 and train is not None and float(train) >= 1.50 and avg_pos >= 5:
        return "robustness_candidate"
    if s is not None and float(s) >= 2.35 and r5 is not None and float(r5) >= 1.6 and avg_pos >= 5:
        return "retain_candidate"
    if str(r.get("variant", "")) == "incumbent_sur_core|sur3_high_no_high_mom|top8|ind3|seminone|sl8_trail12|20|equal|liq50m":
        return "incumbent"
    return "rejected_for_now"


def write_report(rows: list[dict[str, Any]], remove_rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    promoted = [r for r in rows if r["status"] == "promote_candidate"]
    retained = [r for r in rows if r["status"] in {"promote_candidate", "retain_candidate", "robustness_candidate", "incumbent"}]
    best = rows[0]
    lines = [
        "# Phase 3.11 Signal-quality search\n\n",
        "目標：保留既有好策略，同時改選股訊號與月內權重，尋找更穩健的 Sharpe >2.5。仍是 research-only proxy backtest。\n\n",
        "## Preservation rule\n\n",
        f"- Promising strategy registry: `{REGISTRY}`\n",
        "- S1 incumbent 必須留存並作為比較基準，不因新搜尋被覆蓋。\n\n",
        "## Search summary\n\n",
        f"- tested variants: {len(rows)}\n",
        f"- promote candidates: {len(promoted)}\n",
        f"- retained candidates including incumbent: {len(retained)}\n",
        f"- best variant: `{best['variant']}`\n",
        f"- best Sharpe={fmt_num(best['sharpe'])}, return={fmt_pct(best['total_return'])}, MDD={fmt_pct(best['mdd'])}, remove5 Sharpe={fmt_num(best['remove5_sharpe'])}\n\n",
        "## Top 25 by Sharpe\n\n",
    ]
    for r in rows[:25]:
        lines.append(f"- {r['status']}｜Sharpe={fmt_num(r['sharpe'])}, return={fmt_pct(r['total_return'])}, MDD={fmt_pct(r['mdd'])}, trainS={fmt_num(r['train_sharpe'])}, testS={fmt_num(r['test_sharpe'])}, rm5S={fmt_num(r['remove5_sharpe'])}, rm10S={fmt_num(r['remove10_sharpe'])}, avgPos={fmt_num(r['avg_positions'])}, top5share={fmt_pct(r['top5_pos_contrib_share'])}｜`{r['variant']}`\n")
    lines.append("\n## Retained / marked variants\n\n")
    if not retained:
        lines.append("- No retained variants.\n")
    for r in retained[:30]:
        lines.append(f"- **{r['status']}**｜Sharpe={fmt_num(r['sharpe'])}, rm5S={fmt_num(r['remove5_sharpe'])}, return={fmt_pct(r['total_return'])}, MDD={fmt_pct(r['mdd'])}｜`{r['variant']}`\n")
    lines += [
        "\n## Interpretation\n\n",
        "- `promote_candidate` 需要 Sharpe>=2.5、remove5 Sharpe>=1.8、train Sharpe>=1.5、平均持股>=5。\n",
        "- `retain_candidate` 表示接近或改善但尚未可升級。\n",
        "- 若新訊號只提高 raw Sharpe 但 remove-winners 更差，仍不升級。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_RESULTS}`\n- `{OUT_REMOVE}`\n- `{OUT_TOPTRADES}`\n- `{OUT_SUMMARY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def append_registry(rows: list[dict[str, Any]]) -> None:
    retained = [r for r in rows if r["status"] in {"promote_candidate", "retain_candidate", "robustness_candidate"}]
    if not retained:
        note = "\n\n## Phase 3.11 update\n\n- Result: no new promoted/retained signal-quality variant exceeded the incumbent retention standard. S1 remains incumbent.\n"
    else:
        note = "\n\n## Phase 3.11 update\n\n"
        for i, r in enumerate(retained[:10], 1):
            note += f"### SQ{i} — {r['variant']}\n\n- Status: **{r['status']}**\n- Sharpe: `{fmt_num(r['sharpe'])}`; return: `{fmt_pct(r['total_return'])}`; MDD: `{fmt_pct(r['mdd'])}`; remove5 Sharpe: `{fmt_num(r['remove5_sharpe'])}`\n- Note: generated by Phase 3.11 signal-quality search; compare against S1 before promotion.\n\n"
    old = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry\n"
    marker = "## Phase 3.11 update"
    if marker in old:
        old = old.split(marker)[0].rstrip() + "\n"
    REGISTRY.write_text(old + note, encoding="utf-8")


def main() -> int:
    result_rows: list[dict[str, Any]] = []
    remove_rows: list[dict[str, Any]] = []
    top_trade_rows: list[dict[str, Any]] = []

    for liq in LIQS:
        scored, prices_by_stock, date_map, th = ex.build_universe(liq)
        for recipe in RECIPES:
            for filt in FILTERS:
                for top_n in TOP_NS:
                    for ind_cap in IND_CAPS:
                        if ind_cap > top_n:
                            continue
                        for semi_cap in SEMI_CAPS:
                            if semi_cap is not None and semi_cap > top_n:
                                continue
                            sigs = select_custom(scored, th, recipe, filt, top_n, ind_cap, semi_cap)
                            if not sigs:
                                continue
                            base_config = f"{recipe}|{filt}|top{top_n}|ind{ind_cap}|semi{semi_cap if semi_cap is not None else 'none'}|liq{liq//1_000_000}m"
                            raw_trades = ex.build_rule_trades(sigs, prices_by_stock, date_map, base_config, RULES, MAX_HS)
                            for rule in RULES:
                                for mh in MAX_HS:
                                    rule_rows = [r for r in raw_trades if r["exit_rule"] == rule and int(r["max_holding_days"]) == mh]
                                    if not rule_rows:
                                        continue
                                    for wm in WEIGHT_MODES:
                                        trades = apply_weights(rule_rows, wm)
                                        rs, ntr, avg_pos = monthly_weighted(trades)
                                        sm = metrics(rs)
                                        train = metrics(monthly_weighted(trades, years={"2023", "2024"})[0])
                                        test = metrics(monthly_weighted(trades, years={"2025"})[0])
                                        rem = remove_winner_metrics(trades)
                                        conc = contributor_stats(trades)
                                        robust_score = min(float(sm.get("sharpe") or -999), float(rem.get("remove5_sharpe") or -999) + 0.40, float(train.get("sharpe") or -999) + 0.30)
                                        variant = f"{recipe}|{filt}|top{top_n}|ind{ind_cap}|semi{semi_cap if semi_cap is not None else 'none'}|{rule}|{mh}|{wm}|liq{liq//1_000_000}m"
                                        row = {
                                            "variant": variant, "recipe": recipe, "filter": filt, "top_n": top_n, "industry_cap": ind_cap, "semiconductor_cap": semi_cap if semi_cap is not None else "none", "exit_rule": rule, "max_holding_days": mh, "weight_mode": wm, "liquidity_threshold": liq,
                                            "months": sm.get("months"), "trades": ntr, "avg_positions": avg_pos,
                                            "total_return": sm.get("total_return"), "ann_return": sm.get("ann_return"), "sharpe": sm.get("sharpe"), "mdd": sm.get("mdd"), "win_rate": sm.get("win_rate"), "worst_month": sm.get("worst_month"),
                                            "train_sharpe": train.get("sharpe"), "train_return": train.get("total_return"), "test_sharpe": test.get("sharpe"), "test_return": test.get("total_return"),
                                            **rem, **conc, "robust_score": robust_score,
                                        }
                                        row["status"] = status_for(row)
                                        result_rows.append(row)
                                        if row["status"] in {"promote_candidate", "retain_candidate", "incumbent"} or (row.get("sharpe") is not None and float(row["sharpe"]) >= 2.45):
                                            for n in [0, 5, 10, 20]:
                                                remove_rows.append({"variant": variant, "remove_top_winners": n, "return": rem[f"remove{n}_return"], "sharpe": rem[f"remove{n}_sharpe"], "mdd": rem[f"remove{n}_mdd"]})
                                            for tr in sorted(trades, key=lambda x: float(x["net_return"]), reverse=True)[:10]:
                                                top_trade_rows.append({"variant": variant, "revenue_month": tr["revenue_month"], "entry_date": tr["entry_date"], "exit_date": tr["exit_date"], "stock_id": tr["stock_id"], "stock_name": tr["stock_name"], "industry": tr["industry"], "net_return": tr["net_return"], "portfolio_weight": tr.get("portfolio_weight"), "score": tr.get("score"), "exit_rule": tr["exit_rule"]})
    result_rows.sort(key=lambda r: (float(r.get("sharpe") or -999), float(r.get("robust_score") or -999)), reverse=True)
    # Ensure incumbent status if exact preserved variant appears.
    for r in result_rows:
        if r["recipe"] == "incumbent_sur_core" and r["filter"] == "sur3_high_no_high_mom" and int(r["top_n"]) == 8 and int(r["industry_cap"]) == 3 and r["semiconductor_cap"] == "none" and r["exit_rule"] == "sl8_trail12" and int(r["max_holding_days"]) == 20 and r["weight_mode"] == "equal" and int(r["liquidity_threshold"]) == 50_000_000:
            r["status"] = "incumbent"
            break
    write_csv(OUT_RESULTS, result_rows)
    write_csv(OUT_REMOVE, remove_rows)
    write_csv(OUT_TOPTRADES, top_trade_rows)
    promoted = [r for r in result_rows if r["status"] == "promote_candidate"]
    retained = [r for r in result_rows if r["status"] in {"promote_candidate", "retain_candidate", "robustness_candidate", "incumbent"}]
    summary = {
        "tested_variants": len(result_rows),
        "promote_candidates": len(promoted),
        "retained_or_incumbent": len(retained),
        "best": result_rows[0] if result_rows else None,
        "outputs": [str(OUT_RESULTS), str(OUT_REMOVE), str(OUT_TOPTRADES), str(OUT_SUMMARY), str(OUT_REPORT), str(REGISTRY)],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result_rows, remove_rows, summary)
    append_registry(result_rows)
    print(json.dumps({"tested_variants": len(result_rows), "promote_candidates": len(promoted), "retained_or_incumbent": len(retained), "best_sharpe": result_rows[0].get("sharpe") if result_rows else None, "best_variant": result_rows[0].get("variant") if result_rows else None, "outputs": summary["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
