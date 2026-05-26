#!/usr/bin/env python3
"""Phase 3.24: OOS sector and winner stress for Phase 3.23 selected rules.

Research-only. No live trading, broker connection, or orders.
"""
from __future__ import annotations

import csv
import importlib.util
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, cast

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT_SECTOR = PROCESSED / "delay_walkforward_oos_sector_stress.csv"
OUT_REMOVE = PROCESSED / "delay_walkforward_oos_remove_winners.csv"
OUT_REPORT = REPORTS / "phase3_24_delay_walkforward_oos_sector_stress_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

P323_PATH = ROOT / "scripts" / "delay_walkforward_robust_selection_gate.py"
spec = importlib.util.spec_from_file_location("delay_walkforward_robust_selection_gate", P323_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {P323_PATH}")
p323 = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(p323)
p321 = p323.p321
p319 = p323.p319

COST = p323.COST
ELECTRONICS = set(p319.ELECTRONICS)
SEMICONDUCTOR = p319.SEMICONDUCTOR
REMOVE_NS = [0, 3, 5, 10]


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
    nav = peak = 1.0; worst = 0.0
    for r in rs:
        nav *= 1 + r; peak = max(peak, nav); worst = min(worst, nav / peak - 1)
    return worst


def metrics(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"return": 0.0, "sharpe": None, "mdd": 0.0, "win_rate": None}
    sd = statistics.stdev(rs) if len(rs) >= 2 else None
    return {"return": compound(rs), "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd else None, "mdd": mdd(rs), "win_rate": sum(1 for x in rs if x > 0) / len(rs)}


def select_by_month(trades: list[dict[str, Any]], variant: str, delay: int, months: list[str], pred: Callable[[dict[str, Any]], bool] | None = None, exclude: set[tuple[str, str, str, int]] | None = None) -> dict[str, list[dict[str, Any]]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if int(r["delay_trading_days"]) != delay or r["revenue_month"] not in months:
            continue
        if r.get("possible_limit_up_nonfill"):
            continue
        if pred is not None and not pred(r):
            continue
        key = (str(r["revenue_month"]), str(r["stock_id"]), str(r["exec_date"]), int(r["delay_trading_days"]))
        if exclude and key in exclude:
            continue
        w = p323.variant_weight(r, variant)
        if w <= 0:
            continue
        r2 = dict(r); r2["weight"] = w; r2["net_return"] = float(r["gross_return"]) - COST
        by_month[r["revenue_month"]].append(r2)
    return by_month


def summarize(by_month: dict[str, list[dict[str, Any]]], months: list[str]) -> dict[str, Any]:
    rs: list[float] = []
    pos: list[int] = []
    for m in months:
        rows = by_month.get(m, [])
        tw = sum(float(r["weight"]) for r in rows)
        ret = sum(float(r["weight"]) * float(r["net_return"]) for r in rows) / tw if tw > 0 else 0.0
        rs.append(ret); pos.append(len(rows))
    mm = metrics(rs)
    return {"months": len(months), "active_months": sum(1 for x in pos if x > 0), "avg_positions": statistics.mean(pos) if pos else 0.0, "return": mm["return"], "sharpe": mm["sharpe"], "mdd": mm["mdd"], "win_rate": mm["win_rate"]}


def contribution_keys(trades: list[dict[str, Any]], variant: str, delay: int, months: list[str]) -> list[tuple[tuple[str, str, str, int], float, dict[str, Any]]]:
    by_month = select_by_month(trades, variant, delay, months)
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


def selected_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with p323.OUT_SUMMARY.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if str(r.get("selected_by_train_robust_score")) == "True":
                rows.append(r)
    return rows


def append_registry(focus: list[dict[str, Any]]) -> None:
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.24 update" in text:
        return
    lines = ["\n## Phase 3.24 update\n\n"]
    lines.append("- Added OOS sector/no-semiconductor and remove-winner stress for Phase 3.23 robust-selected delay/sizing rules.\n")
    for f in focus:
        lines.append(f"- {f['split']} selected `{f['variant']}|delay={f['delay_trading_days']}`: OOS all Sharpe `{num(f['all_sharpe'])}`, no-semiconductor Sharpe `{num(f['no_semiconductor_sharpe'])}`, remove-top-5 Sharpe `{num(f['remove5_sharpe'])}`.\n")
    lines.append("- Registry status unchanged: the selected rules are retained as research-only timing/sizing diagnostics, not promoted, because OOS robustness remains sector/right-tail sensitive.\n")
    REGISTRY.write_text(text.rstrip() + "\n" + "".join(lines), encoding="utf-8")


def main() -> int:
    signals, prices_by_stock, _date_map, all_months, _ctx = p319.make_signals()
    _raw_by_stock, raw_by_key, _raw_audit = p319.build_raw_lookup()
    trades = p321.build_delay_trades(signals, prices_by_stock, raw_by_key)
    selected = selected_cases()

    sector_preds: list[tuple[str, Callable[[dict[str, Any]], bool] | None]] = [
        ("all", None),
        ("electronics_only", lambda r: r.get("industry") in ELECTRONICS),
        ("non_electronics", lambda r: r.get("industry") not in ELECTRONICS),
        ("semiconductor_only", lambda r: r.get("industry") == SEMICONDUCTOR),
        ("no_semiconductor", lambda r: r.get("industry") != SEMICONDUCTOR),
    ]
    sector_rows: list[dict[str, Any]] = []
    remove_rows: list[dict[str, Any]] = []
    focus: list[dict[str, Any]] = []

    for s in selected:
        split = s["split"]; variant = s["variant"]; delay = int(s["delay_trading_days"]); test_year = s["test_year"]
        test_months = [m for m in all_months if m[:4] == test_year]
        for label, pred in sector_preds:
            met = summarize(select_by_month(trades, variant, delay, test_months, pred=pred), test_months)
            sector_rows.append({"split": split, "test_year": test_year, "variant": variant, "delay_trading_days": delay, "sector_slice": label, **met})
        contribs = contribution_keys(trades, variant, delay, test_months)
        for n in REMOVE_NS:
            exclude = {k for k, _c, _r in contribs[:n]}
            met = summarize(select_by_month(trades, variant, delay, test_months, exclude=exclude), test_months)
            top_names = "; ".join([f"{r.get('stock_id')} {r.get('stock_name')} {k[0]} {c:.2%}" for k, c, r in contribs[:min(n, 3)]]) if n else ""
            remove_rows.append({"split": split, "test_year": test_year, "variant": variant, "delay_trading_days": delay, "remove_top_n_oos_winners": n, "top_removed_examples": top_names, **met})
        all_row = next(r for r in sector_rows if r["split"] == split and r["sector_slice"] == "all")
        nosemi = next(r for r in sector_rows if r["split"] == split and r["sector_slice"] == "no_semiconductor")
        rm5 = next(r for r in remove_rows if r["split"] == split and int(r["remove_top_n_oos_winners"]) == 5)
        focus.append({"split": split, "variant": variant, "delay_trading_days": delay, "all_sharpe": all_row["sharpe"], "no_semiconductor_sharpe": nosemi["sharpe"], "remove5_sharpe": rm5["sharpe"]})

    write_csv(OUT_SECTOR, sector_rows)
    write_csv(OUT_REMOVE, remove_rows)
    append_registry(focus)

    lines = [
        "# Phase 3.24 OOS sector and remove-winner stress for delay-aware rules\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because Phase 3.23 robust-selected rules beat same-delay equal S1 in two next-year tests, therefore the next gate is whether those OOS gains survive outside the dominant semiconductor/electronics exposure and after removing the largest OOS winners. If not, the rules are timing/sizing diagnostics, not promotable industry-survivable alpha.\n\n",
        "### 前因後果\n\n",
        "- Taiwan monthly-revenue SUR edge has repeatedly looked electronics/semiconductor supply-chain driven.\n",
        "- A rule selected with train remove-winner penalty can still fail if the next-year improvement is supplied by a few OOS winners or by semiconductor-only exposure.\n\n",
        "### 檢查\n\n",
        f"- Tested {len(selected)} Phase 3.23 selected split-specific rules; cost={COST:.1%}; delayed official open entry; limit-up-risk rows excluded.\n",
        "- OOS slices: all, electronics-only, non-electronics, semiconductor-only, no-semiconductor. OOS remove-top: 0/3/5/10 winners by weighted monthly contribution.\n\n",
        "### 結果\n\n",
    ]
    for s in selected:
        split = s["split"]
        lines.append(f"#### {split}: `{s['variant']} | delay={s['delay_trading_days']}`\n")
        for row in [r for r in sector_rows if r["split"] == split]:
            lines.append(f"- sector `{row['sector_slice']}`: return={pct(row['return'])}, Sharpe={num(row['sharpe'])}, MDD={pct(row['mdd'])}, active={row['active_months']}/{row['months']}, avg_pos={float(row['avg_positions']):.2f}\n")
        lines.append("- remove-winner OOS stress:\n")
        for row in [r for r in remove_rows if r["split"] == split]:
            lines.append(f"  - remove_top_{row['remove_top_n_oos_winners']}: return={pct(row['return'])}, Sharpe={num(row['sharpe'])}, MDD={pct(row['mdd'])}, avg_pos={float(row['avg_positions']):.2f}\n")
        lines.append("\n")
    lines += [
        "### 修正與結論\n\n",
        "- 修正了什麼：Phase 3.23 只確認 selected rules 在 headline OOS return/Sharpe 勝過 same-delay equal S1；本輪補上 OOS sector survival 與 OOS remove-winner stress。\n",
        "- 為什麼先前不夠好：train-side remove-winner penalty 不保證 test-side 不靠少數股票，也不保證非半導體可生存。\n",
        "- 修正後結論是否改變：不改變 promotion 結論。若 no-semiconductor 或 remove-top-5 後 Sharpe 顯著低於 all-slice，Phase 3.23 的改善應描述為 semiconductor/electronics delayed-repricing sizing diagnostic，而非 broad industry-survivable strategy。\n\n",
        "### 缺陷\n\n",
        "- OOS 年度只有 2024/2025；sector labels are static current labels。\n",
        "- remove-winner uses weighted monthly contribution proxy；沒有 full portfolio accounting with overlapping trades。\n",
        "- Exact announcement timestamps and actual limit-up queue fills are still missing。\n\n",
        "### 下一步\n\n",
        "1. 將 Phase 3.24 結果接到 exact timestamp sourcing plan；不要再擴 grid 追 Sharpe。\n",
        "2. 建立 2026 paper-trading schema：timestamp / planned entry / observed open / limit-up flag / non-fill reason / slippage。\n",
        "3. 若繼續研究 selected boost=200，必須先做 position-cap/turnover-cap，避免過度放大少數 quiet names。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_SECTOR}`\n",
        f"- `{OUT_REMOVE}`\n",
        f"- `{OUT_REPORT}`\n",
        f"- `{REGISTRY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
