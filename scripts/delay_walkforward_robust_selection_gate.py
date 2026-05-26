#!/usr/bin/env python3
"""Phase 3.23: delay-aware walk-forward selection with remove-winner penalty.

Research-only. No live trading, broker connection, or orders.

Motivation: Phase 3.20 selected dynamic sizing on train-year Sharpe under a
next-open proxy, while Phase 3.22 showed exact-timing variants remain highly
winner-dependent. This gate selects only using past years, delayed official-open
execution, limit-up-risk exclusion, and an explicit remove-top-winners penalty.
"""
from __future__ import annotations

import csv
import importlib.util
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT_SUMMARY = PROCESSED / "delay_walkforward_robust_selection_summary.csv"
OUT_MONTHLY = PROCESSED / "delay_walkforward_robust_selection_monthly.csv"
OUT_CONTRIB = PROCESSED / "delay_walkforward_robust_selection_contrib.csv"
OUT_REPORT = REPORTS / "phase3_23_delay_walkforward_robust_selection_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

P321_PATH = ROOT / "scripts" / "exact_timing_delay_sensitivity_gate.py"
spec = importlib.util.spec_from_file_location("exact_timing_delay_sensitivity_gate", P321_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {P321_PATH}")
p321 = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(p321)
p319 = p321.p319

COST = 0.010
DELAYS = [1, 2, 3]
LIQ100 = 100_000_000
REMOVE_NS = [0, 5, 10]
SPLITS = [
    ("train_2023_test_2024", ["2023"], "2024"),
    ("train_2023_2024_test_2025", ["2023", "2024"], "2025"),
]
VARIANTS = [
    "equal_s1",
    "boost_quiet_no_large_black_125",
    "boost_quiet_no_large_black_150",
    "boost_quiet_no_large_black_200",
    "downweight_large_black_050",
    "exclude_large_black",
    "liq100_equal_s1",
    "liq100_boost_quiet_no_large_black_150",
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def compound(rs: list[float]) -> float:
    nav = 1.0
    for r in rs:
        nav *= 1 + r
    return nav - 1


def mdd(rs: list[float]) -> float:
    nav = peak = 1.0
    worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"months": 0, "return": 0.0, "sharpe": None, "mdd": 0.0, "win_rate": None, "mean": 0.0}
    sd = statistics.stdev(rs) if len(rs) >= 2 else None
    return {
        "months": len(rs),
        "return": compound(rs),
        "mean": statistics.mean(rs),
        "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(rs),
        "win_rate": sum(1 for x in rs if x > 0) / len(rs),
    }


def variant_weight(r: dict[str, Any], variant: str) -> float:
    qnlb = bool(r.get("quiet_no_large_black"))
    lb = bool(r.get("large_black"))
    liq100 = float(r.get("avg_turnover_20d") or 0) >= LIQ100
    if variant == "equal_s1":
        return 1.0
    if variant == "boost_quiet_no_large_black_125":
        return 1.25 if qnlb else 1.0
    if variant == "boost_quiet_no_large_black_150":
        return 1.50 if qnlb else 1.0
    if variant == "boost_quiet_no_large_black_200":
        return 2.00 if qnlb else 1.0
    if variant == "downweight_large_black_050":
        return 0.50 if lb else 1.0
    if variant == "exclude_large_black":
        return 0.0 if lb else 1.0
    if variant == "liq100_equal_s1":
        return 1.0 if liq100 else 0.0
    if variant == "liq100_boost_quiet_no_large_black_150":
        return (1.50 if qnlb else 1.0) if liq100 else 0.0
    raise KeyError(variant)


def selected_rows(trades: list[dict[str, Any]], variant: str, delay: int, months: list[str], exclude_keys: set[tuple[str, str, str, int]] | None = None) -> dict[str, list[dict[str, Any]]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if int(r["delay_trading_days"]) != delay or r["revenue_month"] not in months:
            continue
        if r.get("possible_limit_up_nonfill"):
            continue
        key = (str(r["revenue_month"]), str(r["stock_id"]), str(r["exec_date"]), int(r["delay_trading_days"]))
        if exclude_keys and key in exclude_keys:
            continue
        w = variant_weight(r, variant)
        if w <= 0:
            continue
        r2 = dict(r); r2["weight"] = w; r2["net_return"] = float(r["gross_return"]) - COST
        by_month[r["revenue_month"]].append(r2)
    return by_month


def monthly_returns(trades: list[dict[str, Any]], variant: str, delay: int, months: list[str], exclude_keys: set[tuple[str, str, str, int]] | None = None) -> list[dict[str, Any]]:
    by_month = selected_rows(trades, variant, delay, months, exclude_keys)
    out: list[dict[str, Any]] = []
    nav = 1.0
    for m in months:
        rows = by_month.get(m, [])
        tw = sum(float(r["weight"]) for r in rows)
        ret = sum(float(r["weight"]) * float(r["net_return"]) for r in rows) / tw if tw > 0 else 0.0
        nav *= 1 + ret
        out.append({"variant": variant, "delay_trading_days": delay, "revenue_month": m, "return": ret, "nav": nav, "positions": len(rows), "cost": COST, "policy": "exclude_limitup_risk"})
    return out


def contribution_keys(trades: list[dict[str, Any]], variant: str, delay: int, months: list[str]) -> list[tuple[tuple[str, str, str, int], float, dict[str, Any]]]:
    by_month = selected_rows(trades, variant, delay, months)
    out: list[tuple[tuple[str, str, str, int], float, dict[str, Any]]] = []
    for m in months:
        rows = by_month.get(m, [])
        tw = sum(float(r["weight"]) for r in rows)
        if tw <= 0:
            continue
        for r in rows:
            contrib = float(r["weight"]) / tw * float(r["net_return"])
            key = (str(r["revenue_month"]), str(r["stock_id"]), str(r["exec_date"]), int(r["delay_trading_days"]))
            out.append((key, contrib, r))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def summarize_monthly(rows: list[dict[str, Any]]) -> dict[str, Any]:
    mm = metrics([float(r["return"]) for r in rows])
    return {
        "months": len(rows),
        "active_months": sum(1 for r in rows if int(r["positions"]) > 0),
        "avg_positions": statistics.mean([int(r["positions"]) for r in rows]) if rows else 0.0,
        "return": mm["return"],
        "sharpe": mm["sharpe"],
        "mdd": mm["mdd"],
        "win_rate": mm["win_rate"],
    }


def robust_score(base: dict[str, Any], rm5: dict[str, Any], rm10: dict[str, Any]) -> float:
    sh = float(base["sharpe"] if base.get("sharpe") is not None else -99)
    sh5 = float(rm5["sharpe"] if rm5.get("sharpe") is not None else -99)
    sh10 = float(rm10["sharpe"] if rm10.get("sharpe") is not None else -99)
    avg_pos = float(base.get("avg_positions") or 0)
    sparse_penalty = 0.35 if avg_pos < 4 else 0.0
    dd_penalty = max(0.0, abs(float(base.get("mdd") or 0)) - 0.25) * 2.0
    # Conservative: reward original Sharpe, but force the selected rule to care about
    # post-winner-removal behavior before seeing the next-year test set.
    return 0.50 * sh + 0.35 * sh5 + 0.15 * sh10 - sparse_penalty - dd_penalty


def append_registry(selected: list[dict[str, Any]]) -> None:
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.23 update" in text:
        return
    lines = ["\n## Phase 3.23 update\n\n"]
    lines.append("- Added delay-aware walk-forward selection with train-only remove-top-5/10-winner penalty; cost 1.0%, official-open delayed execution, possible limit-up non-fills excluded.\n")
    for s in selected:
        lines.append(f"- {s['split']}: selected `{s['variant']}|delay={s['delay_trading_days']}`; OOS return/Sharpe `{pct(s['test_return'])}` / `{num(s['test_sharpe'])}` vs equal_s1 same delay `{pct(s['equal_same_delay_test_return'])}` / `{num(s['equal_same_delay_test_sharpe'])}`.\n")
    lines.append("- Registry status unchanged: S1 remains incumbent; quiet/delay-aware sizing remains research-only because OOS gains are modest and Phase 3.22 winner/sector dependence is still unresolved.\n")
    REGISTRY.write_text(text.rstrip() + "\n" + "".join(lines), encoding="utf-8")


def main() -> int:
    signals, prices_by_stock, _date_map, all_months, _ctx = p319.make_signals()
    _raw_by_stock, raw_by_key, _raw_audit = p319.build_raw_lookup()
    trades = p321.build_delay_trades(signals, prices_by_stock, raw_by_key)

    summary: list[dict[str, Any]] = []
    monthly_all: list[dict[str, Any]] = []
    contrib_rows: list[dict[str, Any]] = []
    selected_rows_out: list[dict[str, Any]] = []

    for split_name, train_years, test_year in SPLITS:
        train_months = [m for m in all_months if m[:4] in train_years]
        test_months = [m for m in all_months if m[:4] == test_year]
        candidates: list[dict[str, Any]] = []
        for variant in VARIANTS:
            for delay in DELAYS:
                contribs = contribution_keys(trades, variant, delay, train_months)
                for rank, (key, contrib, r) in enumerate(contribs[:10], start=1):
                    contrib_rows.append({"split": split_name, "variant": variant, "delay_trading_days": delay, "rank": rank, "contribution": contrib, "revenue_month": key[0], "stock_id": key[1], "stock_name": r.get("stock_name"), "exec_date": key[2], "industry": r.get("industry")})
                remove_metrics: dict[int, dict[str, Any]] = {}
                test_mon = monthly_returns(trades, variant, delay, test_months)
                test_met = summarize_monthly(test_mon)
                for n in REMOVE_NS:
                    exclude = {k for k, _c, _r in contribs[:n]}
                    train_mon = monthly_returns(trades, variant, delay, train_months, exclude)
                    remove_metrics[n] = summarize_monthly(train_mon)
                    if n == 0:
                        monthly_all.extend([{**r, "split": split_name, "sample": "train"} for r in train_mon])
                        monthly_all.extend([{**r, "split": split_name, "sample": "test"} for r in test_mon])
                base = remove_metrics[0]
                rm5 = remove_metrics[5]
                rm10 = remove_metrics[10]
                score = robust_score(base, rm5, rm10)
                row = {
                    "split": split_name, "variant": variant, "delay_trading_days": delay, "train_years": "+".join(train_years), "test_year": test_year,
                    "train_return": base["return"], "train_sharpe": base["sharpe"], "train_mdd": base["mdd"], "train_avg_pos": base["avg_positions"],
                    "train_rm5_return": rm5["return"], "train_rm5_sharpe": rm5["sharpe"], "train_rm10_return": rm10["return"], "train_rm10_sharpe": rm10["sharpe"],
                    "selection_score": score,
                    "test_return": test_met["return"], "test_sharpe": test_met["sharpe"], "test_mdd": test_met["mdd"], "test_avg_pos": test_met["avg_positions"],
                }
                candidates.append(row)
        selected = max(candidates, key=lambda r: float(r["selection_score"]))
        for r in candidates:
            equal_same_delay = next(e for e in candidates if e["variant"] == "equal_s1" and int(e["delay_trading_days"]) == int(r["delay_trading_days"]))
            equal_d1 = next(e for e in candidates if e["variant"] == "equal_s1" and int(e["delay_trading_days"]) == 1)
            r["selected_by_train_robust_score"] = (r is selected)
            r["equal_same_delay_test_return"] = equal_same_delay["test_return"]
            r["equal_same_delay_test_sharpe"] = equal_same_delay["test_sharpe"]
            r["test_excess_return_vs_equal_same_delay"] = float(r["test_return"]) - float(equal_same_delay["test_return"])
            r["test_sharpe_delta_vs_equal_same_delay"] = (float(r["test_sharpe"]) if r["test_sharpe"] is not None else 0.0) - (float(equal_same_delay["test_sharpe"]) if equal_same_delay["test_sharpe"] is not None else 0.0)
            r["equal_delay1_test_return"] = equal_d1["test_return"]
            r["equal_delay1_test_sharpe"] = equal_d1["test_sharpe"]
            summary.append(r)
        selected_rows_out.append(selected)

    write_csv(OUT_SUMMARY, summary)
    write_csv(OUT_MONTHLY, monthly_all)
    write_csv(OUT_CONTRIB, contrib_rows)
    append_registry(selected_rows_out)

    lines: list[str] = [
        "# Phase 3.23 delay-aware walk-forward robust-selection gate\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because Phase 3.20 found small OOS gains for quiet dynamic sizing but Phase 3.22 showed severe remove-winner fragility, therefore a more credible sizing/timing rule should be selectable using only prior years after penalizing top-winner dependence and should still beat equal S1 in the next year under delayed official-open execution.\n\n",
        "### 前因後果\n\n",
        "- Monthly-revenue SUR repricing may persist for several days, but exact timestamp uncertainty means delay=1/2/3 trading days are more honest than assuming perfect first tradability.\n",
        "- Quiet-digestion boosts may simply overweight the same few OTC electronics winners; selection must therefore include train-only remove-top-5/10 winner stress before evaluating OOS.\n\n",
        "### 檢查\n\n",
        f"- Built delay trades from Phase 3.21: {len(trades)} rows; cost={COST:.1%}; official open entry; 20D close exit; possible limit-up non-fill flags excluded.\n",
        f"- Candidate grid: {len(VARIANTS)} sizing variants × delays {DELAYS}; split count={len(SPLITS)}.\n",
        "- Selection score = 0.50 × train Sharpe + 0.35 × train remove-top-5 Sharpe + 0.15 × train remove-top-10 Sharpe, with sparse-position / large-MDD penalties.\n\n",
        "### 結果\n\n",
    ]
    pass_count = 0
    for s in selected_rows_out:
        same_ret = float(s["equal_same_delay_test_return"])
        same_sh = s["equal_same_delay_test_sharpe"]
        pass_case = float(s["test_return"]) > same_ret and (s["test_sharpe"] or -99) >= (same_sh or -99)
        pass_count += int(pass_case)
        lines.append(f"#### {s['split']}\n")
        lines.append(f"- train-selected robust rule: `{s['variant']} | delay={s['delay_trading_days']}`; score={float(s['selection_score']):.2f}\n")
        lines.append(f"- train base: return={pct(s['train_return'])}, Sharpe={num(s['train_sharpe'])}, MDD={pct(s['train_mdd'])}, avg_pos={float(s['train_avg_pos']):.2f}\n")
        lines.append(f"- train remove-top-5 / remove-top-10 Sharpe: {num(s['train_rm5_sharpe'])} / {num(s['train_rm10_sharpe'])}\n")
        lines.append(f"- OOS selected: return={pct(s['test_return'])}, Sharpe={num(s['test_sharpe'])}, MDD={pct(s['test_mdd'])}, avg_pos={float(s['test_avg_pos']):.2f}\n")
        lines.append(f"- OOS equal_s1 same delay: return={pct(s['equal_same_delay_test_return'])}, Sharpe={num(s['equal_same_delay_test_sharpe'])}; delta return={pct(s['test_excess_return_vs_equal_same_delay'])}, delta Sharpe={num(s['test_sharpe_delta_vs_equal_same_delay'])}\n")
        lines.append(f"- Reference equal_s1 delay=1 OOS: return={pct(s['equal_delay1_test_return'])}, Sharpe={num(s['equal_delay1_test_sharpe'])}\n\n")
    lines += [
        "### 修正與結論\n\n",
        "- 修正了什麼：Phase 3.20 的 walk-forward selection only optimized train Sharpe under one next-open proxy；本輪把 delay=1/2/3 納入候選，且用 train-only remove-top-5/10 winners 懲罰來降低 right-tail overfit。\n",
        "- 為什麼先前不夠好：若不懲罰 winner dependence，dynamic sizing 可能只是事後加碼少數大贏家；若只看 delay=1，仍未反映 exact timestamp unknown 的進場延遲風險。\n",
        f"- 修正後結論是否改變：{pass_count}/{len(selected_rows_out)} splits 的 robust-selected rule 在 OOS return 與 Sharpe 同時勝過 same-delay equal S1。即使通過，因樣本只涵蓋 2023–2025 且 Phase 3.22 remove-winner/sector fragility 未解，結論仍是 **research-only sizing/timing hypothesis，不 promotion**；S1 equal remains incumbent。\n\n",
        "### 缺陷\n\n",
        "- 只有兩個 next-year OOS splits；2026 尚未形成完整年度 OOS。\n",
        "- Remove-winner penalty 在 train set 上計算，仍是 monthly contribution proxy，不是真實重疊持倉 PnL attribution。\n",
        "- Current sector/industry labels are static；沒有公司級公告 timestamp、order-book queue、limit-up fill evidence。\n\n",
        "### 下一步\n\n",
        "1. 尋找/保存 company-level monthly revenue exact announcement timestamps，將 delay proxy 換成真正 data-available timestamp gate。\n",
        "2. 把 Phase 3.23 selected rules 做 sector/no-semiconductor OOS stress；若只靠 semiconductor-only，不應做 broad strategy promotion。\n",
        "3. 對 2026 paper-trading log 加入 signal timestamp、planned vs observable entry、limit-up non-fill reason、slippage estimate。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_SUMMARY}`\n",
        f"- `{OUT_MONTHLY}`\n",
        f"- `{OUT_CONTRIB}`\n",
        f"- `{OUT_REPORT}`\n",
        f"- `{REGISTRY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
