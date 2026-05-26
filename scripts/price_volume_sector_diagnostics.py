#!/usr/bin/env python3
"""Phase 3.14: sector-conditioned price/volume diagnostics for Taiwan monthly-revenue SUR.

Research-only proxy backtest. No live trading, no broker connection, no orders.

Purpose: test whether the Phase 3.13 volume-confirmation signal is a broad
confirmation effect or mostly an electronics/semiconductor supply-chain effect.
Only close and turnover_value are available, so this remains close/turnover proxy
research rather than executable OHLC/K-line simulation.
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
OUT_SUMMARY = PROCESSED / "price_volume_sector_diagnostics.csv"
OUT_REMOVE = PROCESSED / "price_volume_sector_remove_winners.csv"
OUT_YEARLY = PROCESSED / "price_volume_sector_yearly.csv"
OUT_REPORT = REPORTS / "phase3_14_price_volume_sector_diagnostics_report.md"

PV_PATH = ROOT / "scripts" / "price_volume_kline_research.py"
spec = importlib.util.spec_from_file_location("price_volume_kline_research", PV_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {PV_PATH}")
pv = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(pv)
sur = pv.sur
pa = pv.pa

HOLDING = 20
COST = 0.007
LIQ = 50_000_000
TOP_N = 8
IND_CAP = 3
ELECTRONICS = {"半導體業", "電子零組件業", "電腦及週邊設備業", "光電業", "通信網路業", "電子通路業", "其他電子業", "資訊服務業"}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    nav = peak = 1.0
    worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(monthly: list[float]) -> dict[str, Any]:
    if not monthly:
        return {"months": 0, "total_return": 0.0, "sharpe": None, "mdd": 0.0, "win_rate": None, "mean_month": None}
    sd = statistics.stdev(monthly) if len(monthly) >= 2 else None
    total = compound(monthly)
    return {
        "months": len(monthly),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(monthly)) - 1,
        "mean_month": statistics.mean(monthly),
        "sharpe": statistics.mean(monthly) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(monthly),
        "win_rate": sum(1 for x in monthly if x > 0) / len(monthly),
        "best_month": max(monthly),
        "worst_month": min(monthly),
    }


def monthly_returns(trades: list[dict[str, Any]], recipe: str, all_months: list[str]) -> list[float]:
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in trades:
        if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
            by_month[r["revenue_month"]].append(float(r["net_return"]))
    # Count inactive months as 0% cash return; do not compute active-month-only Sharpe.
    return [statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in all_months]


def select(scored: list[dict[str, Any]], name: str, pred: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        if pred(r):
            by_month[r["revenue_month"]].append(r)
    out: list[dict[str, Any]] = []
    for month in sorted(by_month):
        counts: dict[str, int] = defaultdict(int)
        selected = 0
        for r in sorted(by_month[month], key=lambda x: x["score_sur_core"], reverse=True):
            if counts[r["industry"]] >= IND_CAP:
                continue
            r2 = dict(r)
            r2["recipe"] = name
            r2["score"] = r["score_sur_core"]
            out.append(r2)
            counts[r["industry"]] += 1
            selected += 1
            if selected >= TOP_N:
                break
    return out


def summarize(trades: list[dict[str, Any]], recipes: list[str], signal_counts: dict[str, int], all_months: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        mm = metrics(monthly_returns(trades, recipe, all_months))
        out.append({
            "recipe": recipe,
            "months_cash_counted": mm["months"],
            "signals": signal_counts.get(recipe, 0),
            "trades": len(base),
            "active_months": len({r["revenue_month"] for r in base}),
            "avg_positions_all_months": len(base) / len(all_months) if all_months else 0,
            "total_return": mm.get("total_return"),
            "ann_return": mm.get("ann_return"),
            "sharpe_cash_counted": mm.get("sharpe"),
            "mdd": mm.get("mdd"),
            "win_rate_monthly_cash_counted": mm.get("win_rate"),
            "best_month": mm.get("best_month"),
            "worst_month": mm.get("worst_month"),
        })
    return out


def remove_winners(trades: list[dict[str, Any]], recipes: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        sorted_rows = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
        for n in [0, 5, 10, 20]:
            remove_keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:n]}
            kept = [r for r in base if (r["revenue_month"], r["stock_id"], r["entry_date"]) not in remove_keys]
            by_month: dict[str, list[float]] = defaultdict(list)
            for r in kept:
                by_month[r["revenue_month"]].append(float(r["net_return"]))
            monthly = [statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in all_months]
            mm = metrics(monthly)
            out.append({"recipe": recipe, "remove_top_winners": n, "trades": len(kept), "total_return": mm.get("total_return"), "sharpe_cash_counted": mm.get("sharpe"), "mdd": mm.get("mdd"), "win_rate_monthly_cash_counted": mm.get("win_rate")})
    return out


def yearly(trades: list[dict[str, Any]], recipes: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    out = []
    months_by_year: dict[str, list[str]] = defaultdict(list)
    for m in all_months:
        months_by_year[m[:4]].append(m)
    for recipe in recipes:
        by_month: dict[str, list[float]] = defaultdict(list)
        for r in trades:
            if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
                by_month[r["revenue_month"]].append(float(r["net_return"]))
        for year, months in sorted(months_by_year.items()):
            monthly = [statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in months]
            mm = metrics(monthly)
            out.append({"recipe": recipe, "year": year, "months_cash_counted": len(months), "active_months": sum(1 for m in months if by_month.get(m)), "return": mm.get("total_return"), "sharpe_cash_counted": mm.get("sharpe"), "mdd": mm.get("mdd")})
    return out


def pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(summary: list[dict[str, Any]], remove: list[dict[str, Any]], yearly_rows: list[dict[str, Any]], thresholds: dict[str, float], outputs: list[str]) -> None:
    by = {r["recipe"]: r for r in summary}
    order = [r["recipe"] for r in summary]
    lines = [
        "# Phase 3.14 價量確認的產業條件診斷\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 本輪假說\n\n",
        "Phase 3.13 顯示 high abnormal turnover 全期報酬較高，但 remove-winner 很脆弱。本輪檢查：成交值擴張是否只是半導體/電子供應鏈再定價的外顯狀態，而不是全市場有效的價量確認。\n\n",
        "## 前因後果 / 邏輯\n\n",
        "月營收 surprise 公布後，若法人與供應鏈投資人需要重新配置，電子/半導體鏈可能更容易出現成交值擴張與延續買盤；非電子族群若沒有同樣的產業敘事與資金池，放量可能只是事件日擁擠或短線出貨。因此同一個 abnormal turnover 條件必須分 electronics / non-electronics / semiconductor / no-semiconductor 檢查。\n\n",
        "## Data / anti-look-ahead\n\n",
        "- 使用既有 `daily_market_history_2023_present.csv`，只有 close 與 turnover_value；仍不能宣稱 K 線、ATR、長上影、長黑或盤中突破。\n",
        "- 進場仍使用月營收可用日後的 proxy entry；成交值條件使用 entry 前可觀察的 20D/120D turnover ratio。\n",
        "- 本輪所有 Sharpe 都把沒有訊號的月份列為 0% cash month，避免 active-month-only 高估。\n\n",
        "## Thresholds\n\n",
    ]
    for k, v in thresholds.items():
        lines.append(f"- `{k}` = {v:.4f}\n")
    lines.append("\n## Summary（20D fixed exit proxy, cash months counted）\n\n")
    for name in order:
        r = by[name]
        lines.append(f"- `{name}`: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active_months={r['active_months']}/{r['months_cash_counted']}, avg_pos_all_months={float(r['avg_positions_all_months']):.2f}, trades={r['trades']}\n")
    lines.append("\n## Remove-winner stress\n\n")
    for name in order:
        vals = [r for r in remove if r["recipe"] == name]
        lines.append(f"### {name}\n")
        for r in vals:
            lines.append(f"- remove {r['remove_top_winners']}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, trades={r['trades']}\n")
    lines.append("\n## Year split\n\n")
    for name in order:
        vals = [r for r in yearly_rows if r["recipe"] == name]
        lines.append(f"### {name}\n")
        for r in vals:
            lines.append(f"- {r['year']}: return={pct(r['return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}\n")
    lines += [
        "\n## Interpretation\n\n",
        "- 若 `vol_high_semiconductor` 明顯強於 `vol_high_no_semiconductor`，成交值擴張較像半導體供應鏈 repricing confirmation，而不是普遍技術面放量規則。\n",
        "- 若 `vol_high_non_electronics` 的 active months 少、MDD 大或 remove-winner 後崩壞，下一輪不應把非電子放量追價升級為 candidate。\n",
        "- 若 baseline 在 no-semiconductor 仍弱於 semiconductor，S1 的 interview framing 應繼續定位為 Taiwan electronics / semiconductor monthly-revenue surprise + fundamental momentum。\n",
        "- 目前資料仍不足以研究真正 K 線供給壓力；下一步要補 OHLC/limit-up-down 後再測 long upper shadow / long black candle。\n\n",
        "## Outputs\n\n",
    ]
    for p in outputs:
        lines.append(f"- `{p}`\n")
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    pa.HOLDINGS = [HOLDING]
    pa.COST = COST
    pa.BASE_TOP_N = TOP_N
    pa.BASE_INDUSTRY_CAP = IND_CAP
    pa.LIQ = LIQ
    sur.HOLDINGS = [HOLDING]
    sur.COST = COST
    sur.TOP_N = TOP_N
    sur.INDUSTRY_CAP = IND_CAP
    sur.MIN_AVG_TURNOVER_20D = LIQ

    scored, prices_by_stock, date_map, counts = pa.build_scored()
    th = pa.thresholds(scored)
    ab_low, ab_high = th["abnormal_turnover"]
    all_months = sorted({r["revenue_month"] for r in scored})

    base_pred = lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1]
    filters: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("baseline_s1_fixed20", lambda r: base_pred(r)),
        ("baseline_semiconductor", lambda r: base_pred(r) and r["industry"] == "半導體業"),
        ("baseline_no_semiconductor", lambda r: base_pred(r) and r["industry"] != "半導體業"),
        ("vol_high_electronics", lambda r: base_pred(r) and r["abnormal_turnover"] >= ab_high and r["industry"] in ELECTRONICS),
        ("vol_high_non_electronics", lambda r: base_pred(r) and r["abnormal_turnover"] >= ab_high and r["industry"] not in ELECTRONICS),
        ("vol_high_semiconductor", lambda r: base_pred(r) and r["abnormal_turnover"] >= ab_high and r["industry"] == "半導體業"),
        ("vol_high_no_semiconductor", lambda r: base_pred(r) and r["abnormal_turnover"] >= ab_high and r["industry"] != "半導體業"),
        ("vol_low_electronics", lambda r: base_pred(r) and r["abnormal_turnover"] <= ab_low and r["industry"] in ELECTRONICS),
        ("vol_low_non_electronics", lambda r: base_pred(r) and r["abnormal_turnover"] <= ab_low and r["industry"] not in ELECTRONICS),
    ]

    signals: list[dict[str, Any]] = []
    signal_counts: dict[str, int] = {}
    recipes: list[str] = []
    for name, pred in filters:
        sigs = select(scored, name, pred)
        signals.extend(sigs)
        signal_counts[name] = len(sigs)
        recipes.append(name)

    trades = sur.build_trades(signals, prices_by_stock, date_map)
    summary = summarize(trades, recipes, signal_counts, all_months)
    remove = remove_winners(trades, recipes, all_months)
    yr = yearly(trades, recipes, all_months)

    write_csv(OUT_SUMMARY, summary)
    write_csv(OUT_REMOVE, remove)
    write_csv(OUT_YEARLY, yr)
    thresholds = {"abnormal_turnover_low_tercile": ab_low, "abnormal_turnover_high_tercile": ab_high, "sur_3m_high_tercile": th["sur_3m"][1], "momentum_120_20_high_tercile": th["momentum_120_20"][1]}
    outputs = [str(OUT_SUMMARY), str(OUT_REMOVE), str(OUT_YEARLY), str(OUT_REPORT)]
    write_report(summary, remove, yr, thresholds, outputs)
    print(json.dumps({"summary_rows": len(summary), "remove_rows": len(remove), "yearly_rows": len(yr), "counts": counts, "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
