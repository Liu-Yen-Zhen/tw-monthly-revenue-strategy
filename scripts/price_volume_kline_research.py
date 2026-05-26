#!/usr/bin/env python3
"""Phase 3.13: price/volume confirmation research for Taiwan monthly-revenue SUR.

Research-only proxy backtest. No live trading, no broker connection, no orders.

Question: after a monthly-revenue SUR signal, does close/turnover-confirmed
attention (volume expansion), quiet digestion, or simple post-announcement
close momentum improve the S1 research candidate's robustness?

Data limitation: current official daily market history has close and turnover
value only; no OHLC, intraday, limit-up/limit-down, or executable volume-at-price.
Therefore all K-line/ATR/candlestick conclusions are deferred and explicitly
labeled as missing-data gates.
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
CHARTS = REPORTS / "charts"
OUT_VARIANTS = PROCESSED / "price_volume_kline_variants.csv"
OUT_YEARLY = PROCESSED / "price_volume_kline_yearly.csv"
OUT_REMOVE = PROCESSED / "price_volume_kline_remove_winners.csv"
OUT_SECTOR = PROCESSED / "price_volume_kline_sector.csv"
OUT_TOPTRADES = PROCESSED / "price_volume_kline_top_trades.csv"
OUT_SUMMARY = PROCESSED / "price_volume_kline_summary.json"
OUT_REPORT = REPORTS / "phase3_13_price_volume_kline_research_report.md"

PA_PATH = ROOT / "scripts" / "price_action_filter_tests.py"
spec = importlib.util.spec_from_file_location("price_action_filter_tests", PA_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {PA_PATH}")
pa = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(pa)
sur = pa.sur

HOLDING = 20
COST = 0.007
LIQ = 50_000_000
TOP_N = 8
IND_CAP = 3


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def q(vals: list[float], p: float) -> float:
    vals = sorted(v for v in vals if v is not None and not math.isnan(v))
    if not vals:
        raise RuntimeError("empty quantile input")
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
    nav = peak = 1.0
    worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(monthly: list[float]) -> dict[str, Any]:
    if not monthly:
        return {"months": 0}
    sd = statistics.stdev(monthly) if len(monthly) >= 2 else None
    total = compound(monthly)
    return {
        "months": len(monthly),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(monthly)) - 1,
        "mean_month": statistics.mean(monthly),
        "median_month": statistics.median(monthly),
        "win_rate": sum(1 for x in monthly if x > 0) / len(monthly),
        "sharpe": statistics.mean(monthly) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(monthly),
        "best_month": max(monthly),
        "worst_month": min(monthly),
    }


def select_custom(scored: list[dict[str, Any]], name: str, pred: Callable[[dict[str, Any]], bool], top_n: int = TOP_N, industry_cap: int = IND_CAP) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        if pred(r):
            by_month[r["revenue_month"]].append(r)
    out: list[dict[str, Any]] = []
    for month, rows in by_month.items():
        ind_counts: dict[str, int] = defaultdict(int)
        selected = 0
        for r in sorted(rows, key=lambda x: x["score_sur_core"], reverse=True):
            if ind_counts[r["industry"]] >= industry_cap:
                continue
            r2 = dict(r)
            r2["recipe"] = name
            r2["score"] = r["score_sur_core"]
            out.append(r2)
            ind_counts[r["industry"]] += 1
            selected += 1
            if selected >= top_n:
                break
    return out


def monthly_returns(trades: list[dict[str, Any]], recipe: str) -> list[float]:
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in trades:
        if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
            by_month[r["revenue_month"]].append(float(r["net_return"]))
    return [statistics.mean(by_month[m]) for m in sorted(by_month)]


def summarize(trades: list[dict[str, Any]], recipes: list[str], signal_counts: dict[str, int]) -> list[dict[str, Any]]:
    rows = []
    for recipe in recipes:
        rs = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        mm = metrics(monthly_returns(trades, recipe))
        rows.append({
            "recipe": recipe,
            "holding_days": HOLDING,
            "months": mm.get("months"),
            "signals": signal_counts.get(recipe, 0),
            "trades": len(rs),
            "avg_positions": len(rs) / mm["months"] if mm.get("months") else 0,
            "total_return": mm.get("total_return"),
            "ann_return": mm.get("ann_return"),
            "sharpe": mm.get("sharpe"),
            "mdd": mm.get("mdd"),
            "win_rate": mm.get("win_rate"),
            "best_month": mm.get("best_month"),
            "worst_month": mm.get("worst_month"),
        })
    return rows


def yearly_rows(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        by: dict[tuple[str, str], list[float]] = defaultdict(list)
        for r in trades:
            if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
                by[(str(r["entry_date"])[:4], r["revenue_month"])].append(float(r["net_return"]))
        for year in sorted({y for y, _m in by}):
            monthly = [statistics.mean(by[(year, m)]) for m in sorted(m for y, m in by if y == year)]
            mm = metrics(monthly)
            out.append({"recipe": recipe, "year": year, "months": mm.get("months"), "return": mm.get("total_return"), "sharpe": mm.get("sharpe"), "mdd": mm.get("mdd"), "win_rate": mm.get("win_rate")})
    return out


def remove_rows(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
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
            monthly = [statistics.mean(by_month[m]) for m in sorted(by_month)]
            mm = metrics(monthly)
            out.append({"recipe": recipe, "remove_top_winners": n, "trades": len(kept), "total_return": mm.get("total_return"), "sharpe": mm.get("sharpe"), "mdd": mm.get("mdd"), "win_rate": mm.get("win_rate")})
    return out


def sector_rows(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
    out = []
    modes = {
        "all": lambda r: True,
        "electronics_only": lambda r: r.get("industry") in {"半導體業", "電子零組件業", "電腦及週邊設備業", "光電業", "通信網路業", "電子通路業", "其他電子業", "資訊服務業"},
        "non_electronics": lambda r: r.get("industry") not in {"半導體業", "電子零組件業", "電腦及週邊設備業", "光電業", "通信網路業", "電子通路業", "其他電子業", "資訊服務業"},
        "semiconductor_only": lambda r: r.get("industry") == "半導體業",
        "no_semiconductor": lambda r: r.get("industry") != "半導體業",
    }
    for recipe in recipes:
        for mode, pred in modes.items():
            by_month: dict[str, list[float]] = defaultdict(list)
            trades_n = 0
            for r in trades:
                if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING and pred(r):
                    by_month[r["revenue_month"]].append(float(r["net_return"]))
                    trades_n += 1
            monthly = [statistics.mean(by_month[m]) for m in sorted(by_month)]
            mm = metrics(monthly)
            out.append({"recipe": recipe, "sector_mode": mode, "months": mm.get("months"), "trades": trades_n, "avg_positions": trades_n / mm["months"] if mm.get("months") else 0, "total_return": mm.get("total_return"), "sharpe": mm.get("sharpe"), "mdd": mm.get("mdd"), "win_rate": mm.get("win_rate")})
    return out


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(variants: list[dict[str, Any]], yearly: list[dict[str, Any]], remove: list[dict[str, Any]], sectors: list[dict[str, Any]], thresholds: dict[str, float], outputs: list[str]) -> None:
    order = ["s1_sur3_no_high_mom", "s1_plus_vol_expansion", "s1_plus_vol_mid", "s1_plus_vol_low", "s1_quiet_underreaction", "s1_post5d_close_mom"]
    by_name = {r["recipe"]: r for r in variants}
    lines = [
        "# Phase 3.13 價量 / K 線狀態研究\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 本輪假說\n\n",
        "月營收 SUR 後，若股價/成交值顯示市場開始重新定價，可能提高後續 20D 勝率；但若成交值過度擴張，也可能代表短線擁擠與已反映。因此先測 close/turnover 可驗證的三種狀態：成交值擴張、成交值未擴張/量縮整理、低 20D run-up 的 quiet underreaction。\n\n",
        "## Data audit / 限制\n\n",
        "- `daily_market_history_2023_present.csv` 只有 `trade_date, market, stock_id, stock_name, close, turnover_value`。\n",
        "- 因此本輪不能嚴格測 K 線長上影、長黑、ATR 壓縮、盤中突破、漲跌停 non-fill；這些需要 OHLC、成交量股數、漲跌停價與公告時間。\n",
        "- 本輪 volume proxy 使用進場日前 20D/120D 成交值比 (`abnormal_turnover`)；它比較像公告前後可觀察的注意力/擁擠 proxy，不是盤中放量突破。\n",
        "- `s1_post5d_close_mom` 為避免 look-ahead，先觀察 proxy entry 後 5 個收盤，若 5D close momentum 高於中位數，才把進場日延後到第 5 個交易日；仍只是 close-price proxy。\n\n",
        "## Thresholds\n\n",
    ]
    for k, v in thresholds.items():
        lines.append(f"- `{k}` = {v:.4f}\n")
    lines.append("\n## Variant summary（20D fixed exit proxy）\n\n")
    for name in order:
        r = by_name[name]
        lines.append(f"- `{name}`: return={fmt_pct(r['total_return'])}, Sharpe={fmt_num(r['sharpe'])}, MDD={fmt_pct(r['mdd'])}, win={fmt_pct(r['win_rate'])}, avg positions={float(r['avg_positions']):.2f}, trades={r['trades']}\n")
    lines.append("\n## Remove top winners stress\n\n")
    for name in order[:5]:
        vals = [r for r in remove if r["recipe"] == name and int(r["remove_top_winners"]) in {0, 5, 10, 20}]
        lines.append(f"### {name}\n")
        for r in vals:
            lines.append(f"- remove {r['remove_top_winners']}: return={fmt_pct(r['total_return'])}, Sharpe={fmt_num(r['sharpe'])}, MDD={fmt_pct(r['mdd'])}, trades={r['trades']}\n")
    lines.append("\n## Year split / OOS-like sanity\n\n")
    for name in order[:5]:
        vals = [r for r in yearly if r["recipe"] == name]
        lines.append(f"### {name}\n")
        for r in vals:
            lines.append(f"- {r['year']}: return={fmt_pct(r['return'])}, Sharpe={fmt_num(r['sharpe'])}, MDD={fmt_pct(r['mdd'])}, win={fmt_pct(r['win_rate'])}\n")
    lines.append("\n## Sector context\n\n")
    for name in ["s1_sur3_no_high_mom", "s1_plus_vol_expansion", "s1_quiet_underreaction"]:
        vals = [r for r in sectors if r["recipe"] == name]
        lines.append(f"### {name}\n")
        for r in vals:
            lines.append(f"- {r['sector_mode']}: return={fmt_pct(r['total_return'])}, Sharpe={fmt_num(r['sharpe'])}, MDD={fmt_pct(r['mdd'])}, avg positions={float(r['avg_positions']):.2f}\n")
    lines += [
        "\n## Interpretation\n\n",
        "- 成交值擴張不是免費午餐：若 high abnormal turnover 的 Sharpe/MDD 或 remove-winner 結果沒有優於 S1 proxy，就代表公告前/公告附近大量成交可能已反映 surprise，不能把『放量』簡化成追價確認。\n",
        "- quiet underreaction 若改善 MDD 或 remove-winner 後存活，前因後果較合理：基本面 surprise 已出現，但價格與成交值尚未過熱，後續由延遲反應與法人/散戶再平衡推動。\n",
        "- 若 sector split 顯示 electronics/semiconductor 顯著優於 non-electronics，應繼續把策略定位為 electronics / semiconductor supply-chain revenue surprise，而不是全市場價量 alpha。\n",
        "- K 線型態研究暫不推進到 candlestick mining；沒有 OHLC 時，長上影/長黑/ATR breakout 都會變成錯誤精度。\n\n",
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
    pre_low, pre_high = th["pre_ret_20d"]

    # Build simple close-only post-announcement 5D momentum feature. This is not an executable intraday test.
    for r in scored:
        pr = prices_by_stock.get((r["market"], r["stock_id"]))
        idx = int(r["price_idx"])
        if pr and idx + 5 < len(pr):
            r["post5d_close_ret"] = float(pr[idx + 5]["close"]) / float(pr[idx]["close"]) - 1
        else:
            r["post5d_close_ret"] = None
    post5_vals = [float(r["post5d_close_ret"]) for r in scored if r.get("post5d_close_ret") is not None]
    post5_mid = q(post5_vals, 0.50)

    filters: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("s1_sur3_no_high_mom", lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1]),
        ("s1_plus_vol_expansion", lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1] and r["abnormal_turnover"] >= ab_high),
        ("s1_plus_vol_mid", lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1] and ab_low < r["abnormal_turnover"] < ab_high),
        ("s1_plus_vol_low", lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1] and r["abnormal_turnover"] <= ab_low),
        ("s1_quiet_underreaction", lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1] and r["abnormal_turnover"] <= ab_high and r["pre_ret_20d"] <= pre_high),
        ("s1_post5d_close_mom", lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1] and r.get("post5d_close_ret") is not None and r["post5d_close_ret"] >= post5_mid),
    ]

    signals: list[dict[str, Any]] = []
    signal_counts: dict[str, int] = {}
    recipes = []
    for name, pred in filters:
        sigs = select_custom(scored, name, pred)
        if name == "s1_post5d_close_mom":
            # Make this variant tradable in principle: observe 5 close-to-close sessions after
            # the proxy revenue entry date, then enter on that fifth-session close proxy.
            # This is still close-price proxy, not an executable intraday simulation.
            delayed = []
            for r in sigs:
                pr = prices_by_stock.get((r["market"], r["stock_id"]))
                idx = int(r["price_idx"])
                if pr and idx + 5 < len(pr):
                    r2 = dict(r)
                    r2["original_entry_date"] = r["entry_date"]
                    r2["entry_date"] = pr[idx + 5]["date"]
                    r2["price_idx"] = idx + 5
                    delayed.append(r2)
            sigs = delayed
        signals.extend(sigs)
        signal_counts[name] = len(sigs)
        recipes.append(name)

    trades = sur.build_trades(signals, prices_by_stock, date_map)
    variants = summarize(trades, recipes, signal_counts)
    yearly = yearly_rows(trades, recipes)
    remove = remove_rows(trades, recipes)
    sectors = sector_rows(trades, recipes)
    top_trades = sorted([
        {"recipe": r["recipe"], "revenue_month": r["revenue_month"], "entry_date": r["entry_date"], "stock_id": r["stock_id"], "stock_name": r["stock_name"], "industry": r["industry"], "net_return": r["net_return"], "sur_3m": r.get("sur_3m"), "abnormal_turnover": r.get("abnormal_turnover"), "pre_ret_20d": r.get("pre_ret_20d")}
        for r in trades if int(r["holding_days"]) == HOLDING
    ], key=lambda x: float(x["net_return"]), reverse=True)[:60]

    write_csv(OUT_VARIANTS, variants)
    write_csv(OUT_YEARLY, yearly)
    write_csv(OUT_REMOVE, remove)
    write_csv(OUT_SECTOR, sectors)
    write_csv(OUT_TOPTRADES, top_trades)
    thresholds = {"abnormal_turnover_low_tercile": ab_low, "abnormal_turnover_high_tercile": ab_high, "pre_ret_20d_low_tercile": pre_low, "pre_ret_20d_high_tercile": pre_high, "post5d_close_ret_median": post5_mid, "sur_3m_high_tercile": th["sur_3m"][1], "momentum_120_20_high_tercile": th["momentum_120_20"][1]}
    outputs = [str(OUT_VARIANTS), str(OUT_YEARLY), str(OUT_REMOVE), str(OUT_SECTOR), str(OUT_TOPTRADES), str(OUT_SUMMARY), str(OUT_REPORT)]
    summary = {"counts": counts, "thresholds": thresholds, "filters": recipes, "signal_counts": signal_counts, "cost": COST, "liquidity_min": LIQ, "outputs": outputs, "data_limitations": ["daily data has close and turnover_value only", "no OHLC", "no intraday", "no limit-up/down fill simulation"]}
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(variants, yearly, remove, sectors, thresholds, outputs)
    print(json.dumps({"variants": len(variants), "yearly": len(yearly), "remove": len(remove), "sectors": len(sectors), "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
