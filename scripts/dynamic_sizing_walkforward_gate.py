#!/usr/bin/env python3
"""Phase 3.20: walk-forward / train-test gate for quiet-digestion dynamic sizing.

Research-only. No live trading, broker connection, or orders.

Purpose: avoid full-sample overfitting. Candidate sizing rules are selected on past
entry-date/revenue-year data, then evaluated on the next year with cash months counted.
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
OUT_SUMMARY = PROCESSED / "dynamic_sizing_walkforward_summary.csv"
OUT_MONTHLY = PROCESSED / "dynamic_sizing_walkforward_monthly.csv"
OUT_REPORT = REPORTS / "phase3_20_dynamic_sizing_walkforward_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

P319_PATH = ROOT / "scripts" / "execution_realism_tradability_gate.py"
spec = importlib.util.spec_from_file_location("execution_realism_tradability_gate", P319_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {P319_PATH}")
p319 = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(p319)

COST = 0.010
ENTRY_MODE = "next_open"
POLICY = "exclude_limitup_risk"
LIQ100 = 100_000_000
CANDIDATES = [
    "equal_s1",
    "boost_quiet_no_large_black_125",
    "boost_quiet_no_large_black_150",
    "boost_quiet_no_large_black_200",
    "downweight_large_black_050",
    "exclude_large_black",
    "liq100_equal_s1",
    "liq100_boost_quiet_no_large_black_150",
]
SPLITS = [
    ("train_2023_test_2024", ["2023"], "2024"),
    ("train_2023_2024_test_2025", ["2023", "2024"], "2025"),
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for r in rows:
        for k in r.keys():
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
    nav = peak = 1.0; worst = 0.0
    for r in rs:
        nav *= 1 + r; peak = max(peak, nav); worst = min(worst, nav / peak - 1)
    return worst


def metrics(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"months": 0, "return": 0.0, "sharpe": None, "mdd": 0.0, "win_rate": None}
    sd = statistics.stdev(rs) if len(rs) >= 2 else None
    return {"months": len(rs), "return": compound(rs), "mean": statistics.mean(rs), "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd else None, "mdd": mdd(rs), "win_rate": sum(1 for x in rs if x > 0) / len(rs)}


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
        if not liq100:
            return 0.0
        return 1.50 if qnlb else 1.0
    raise KeyError(variant)


def monthly_returns(trades: list[dict[str, Any]], variant: str, months: list[str]) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if r["entry_mode"] != ENTRY_MODE:
            continue
        if POLICY == "exclude_limitup_risk" and r.get("possible_limit_up_nonfill"):
            continue
        if r["revenue_month"] not in months:
            continue
        w = variant_weight(r, variant)
        if w <= 0:
            continue
        r2 = dict(r); r2["weight"] = w; r2["net_return"] = float(r["gross_return"]) - COST
        by_month[r["revenue_month"]].append(r2)
    out = []
    nav = 1.0
    for m in months:
        rows = by_month.get(m, [])
        tw = sum(float(r["weight"]) for r in rows)
        ret = sum(float(r["weight"]) * float(r["net_return"]) for r in rows) / tw if tw > 0 else 0.0
        nav *= 1 + ret
        out.append({"variant": variant, "revenue_month": m, "return": ret, "nav": nav, "positions": len(rows)})
    return out


def score_for_selection(mm: dict[str, Any], avg_pos: float) -> float:
    # Prefer Sharpe, but penalize very sparse variants to avoid selecting tiny slices.
    sh = float(mm["sharpe"] if mm.get("sharpe") is not None else -99)
    penalty = 0.25 if avg_pos < 4 else 0.0
    return sh - penalty


def main() -> int:
    signals, prices_by_stock, _date_map, all_months, _ctx = p319.make_signals()
    _raw_by_stock, raw_by_key, _raw_audit = p319.build_raw_lookup()
    trades = p319.enriched_trade_rows(signals, prices_by_stock, raw_by_key)

    summary: list[dict[str, Any]] = []
    monthly_all: list[dict[str, Any]] = []
    for split_name, train_years, test_year in SPLITS:
        train_months = [m for m in all_months if m[:4] in train_years]
        test_months = [m for m in all_months if m[:4] == test_year]
        candidate_rows = []
        for v in CANDIDATES:
            train = monthly_returns(trades, v, train_months)
            test = monthly_returns(trades, v, test_months)
            monthly_all.extend([{**r, "split": split_name, "sample": "train"} for r in train])
            monthly_all.extend([{**r, "split": split_name, "sample": "test"} for r in test])
            trm = metrics([float(r["return"]) for r in train])
            tem = metrics([float(r["return"]) for r in test])
            avg_pos_train = statistics.mean([int(r["positions"]) for r in train]) if train else 0.0
            avg_pos_test = statistics.mean([int(r["positions"]) for r in test]) if test else 0.0
            candidate_rows.append({
                "split": split_name, "variant": v, "train_years": "+".join(train_years), "test_year": test_year,
                "train_months": len(train_months), "test_months": len(test_months),
                "train_return": trm["return"], "train_sharpe": trm["sharpe"], "train_mdd": trm["mdd"], "train_avg_pos": avg_pos_train,
                "test_return": tem["return"], "test_sharpe": tem["sharpe"], "test_mdd": tem["mdd"], "test_avg_pos": avg_pos_test,
                "selection_score": score_for_selection(trm, avg_pos_train),
            })
        selected = max(candidate_rows, key=lambda r: float(r["selection_score"]))
        equal = next(r for r in candidate_rows if r["variant"] == "equal_s1")
        for r in candidate_rows:
            r["selected_by_train"] = r["variant"] == selected["variant"]
            r["test_excess_return_vs_equal"] = float(r["test_return"]) - float(equal["test_return"])
            r["test_sharpe_delta_vs_equal"] = (float(r["test_sharpe"]) if r["test_sharpe"] is not None else 0.0) - (float(equal["test_sharpe"]) if equal["test_sharpe"] is not None else 0.0)
            summary.append(r)

    write_csv(OUT_SUMMARY, summary)
    write_csv(OUT_MONTHLY, monthly_all)

    selected_rows = [r for r in summary if r.get("selected_by_train")]
    equal_rows = [r for r in summary if r["variant"] == "equal_s1"]
    pass_count = sum(1 for s in selected_rows if float(s["test_return"]) > float(next(e for e in equal_rows if e["split"] == s["split"])["test_return"]) and (s["test_sharpe"] or -99) >= (next(e for e in equal_rows if e["split"] == s["split"])["test_sharpe"] or -99))

    lines = [
        "# Phase 3.20 dynamic sizing walk-forward gate\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because quiet-digestion sizing was discovered on the full sample, therefore it may be an overfit right-tail amplifier. If it is robust information, a sizing rule selected using past years should improve the next year versus equal-weight S1 under the same conservative execution proxy.\n\n",
        "### 前因後果\n\n",
        f"- 使用 Phase 3.19 conservative proxy: `{ENTRY_MODE}`, cost `{COST:.1%}`, policy `{POLICY}`。\n",
        "- 每個 split 只用 train years 在 candidate sizing rules 中選擇，然後在下一年 test；inactive months counted as cash。\n\n",
        "### 檢查與結果\n\n",
    ]
    for s in selected_rows:
        eq = next(e for e in equal_rows if e["split"] == s["split"])
        lines.append(f"#### {s['split']}\n")
        lines.append(f"- train selected: `{s['variant']}` (train return={pct(s['train_return'])}, Sharpe={num(s['train_sharpe'])}, MDD={pct(s['train_mdd'])}, avg_pos={float(s['train_avg_pos']):.2f})\n")
        lines.append(f"- selected OOS {s['test_year']}: return={pct(s['test_return'])}, Sharpe={num(s['test_sharpe'])}, MDD={pct(s['test_mdd'])}, avg_pos={float(s['test_avg_pos']):.2f}\n")
        lines.append(f"- equal S1 OOS {eq['test_year']}: return={pct(eq['test_return'])}, Sharpe={num(eq['test_sharpe'])}, MDD={pct(eq['test_mdd'])}, avg_pos={float(eq['test_avg_pos']):.2f}\n")
        lines.append(f"- OOS delta vs equal: return={pct(s['test_excess_return_vs_equal'])}, Sharpe delta={num(s['test_sharpe_delta_vs_equal'])}\n")
    lines += [
        "\n### 修正與結論\n\n",
        "- 修正了什麼：Phase 3.18/3.19 的 quiet boost 仍是 full-sample rule；本輪改成 train-selected / next-year OOS 檢查。\n",
        "- 為什麼先前不夠好：full-sample Sharpe 小幅提高可能只是在同一批 winners 上加權，不能證明未來可用。\n",
        f"- 修正後結論是否改變：{pass_count}/{len(selected_rows)} 個 walk-forward split 同時在 OOS return 與 Sharpe 贏 equal S1。若未穩定通過，quiet boost 仍不得 promotion；S1 equal 保持 incumbent。\n",
        "- 若 selected rule 只是 liq100 或 exclude/downweight 類型，代表 sizing signal 可能在訓練期補償 drawdown，而非穩定 alpha。\n\n",
        "### 缺陷\n\n",
        "- 只有 2023–2025 三個 revenue-year，walk-forward split 很少；這是防 overfit gate，不是充分 OOS 證明。\n",
        "- 仍使用 monthly revenue available-date proxy 與 official open/close proxy，未含真實 intraday order-book fills。\n",
        "- Candidate set 很小且手工設計；不能宣稱已找到最優 sizing。\n\n",
        "### 下一步\n\n",
        "1. 補 exact announcement timestamp 後重跑 Phase 3.19/3.20。\n",
        "2. 若資料延伸到更多年份，改成 rolling 2-year train / 1-year test，並把 selection objective 加入 remove-winner penalty。\n",
        "3. 若 quiet boost OOS 不穩，保留為 narrative diagnostic，不用作 sizing。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_SUMMARY}`\n",
        f"- `{OUT_MONTHLY}`\n",
        f"- `{OUT_REPORT}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")

    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.20 update" not in text:
        block = ["\n## Phase 3.20 update\n\n",
                 "- Added train-selected / next-year OOS gate for dynamic sizing under the Phase 3.19 conservative proxy (`next_open`, 1.0% cost, exclude limit-up risk).\n"]
        for s in selected_rows:
            eq = next(e for e in equal_rows if e["split"] == s["split"])
            block.append(f"- `{s['split']}` selected `{s['variant']}`; OOS return/Sharpe `{pct(s['test_return'])}` / `{num(s['test_sharpe'])}` vs equal S1 `{pct(eq['test_return'])}` / `{num(eq['test_sharpe'])}`.\n")
        block.append("- Registry status unchanged: S1 remains incumbent; quiet/dynamic sizing remains research-only unless future exact-timing and expanded-year OOS gates pass.\n")
        REGISTRY.write_text(text.rstrip() + "\n" + "".join(block), encoding="utf-8")

    print(json.dumps({"outputs": [str(OUT_SUMMARY), str(OUT_MONTHLY), str(OUT_REPORT)], "selected": selected_rows, "pass_count": pass_count}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
