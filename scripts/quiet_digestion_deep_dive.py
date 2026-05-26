#!/usr/bin/env python3
"""Phase 3.17: quiet-digestion deep dive for Taiwan monthly-revenue SUR.

Research-only. No live trading, broker connection, or orders.

Causal question:
After a strong monthly-revenue SUR signal, does low abnormal turnover plus a
narrow entry-day range identify delayed repricing / quiet digestion, or is the
strong result mostly a sparse-sample / semiconductor / top-winner artifact?
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
OUT_VARIANTS = PROCESSED / "quiet_digestion_deep_dive_variants.csv"
OUT_REMOVE = PROCESSED / "quiet_digestion_deep_dive_remove_winners.csv"
OUT_YEARLY = PROCESSED / "quiet_digestion_deep_dive_yearly.csv"
OUT_CONTRIB = PROCESSED / "quiet_digestion_deep_dive_top_contributors.csv"
OUT_MONTHLY = PROCESSED / "quiet_digestion_deep_dive_monthly.csv"
OUT_REPORT = REPORTS / "phase3_17_quiet_digestion_deep_dive_report.md"
OUT_CHART = CHARTS / "phase3_17_quiet_digestion_nav_zh.png"

P316_PATH = ROOT / "scripts" / "price_volume_kline_interaction_research.py"
spec = importlib.util.spec_from_file_location("price_volume_kline_interaction_research", P316_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {P316_PATH}")
p316 = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(p316)
kl = p316.kl
pa = p316.pa
sur = p316.sur

HOLDING = 20
COST = 0.007
LIQ = 50_000_000
IND_CAP = 3
BASE_TOP_N = 8
ELECTRONICS = kl.ELECTRONICS
SEMICONDUCTOR = "半導體業"


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
    nav = peak = 1.0
    worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(monthly: list[float]) -> dict[str, Any]:
    if not monthly:
        return {"months": 0, "total_return": 0.0, "ann_return": None, "sharpe": None, "mdd": 0.0, "win_rate": None}
    total = compound(monthly)
    sd = statistics.stdev(monthly) if len(monthly) >= 2 else None
    return {
        "months": len(monthly),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(monthly)) - 1 if len(monthly) else None,
        "sharpe": statistics.mean(monthly) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(monthly),
        "win_rate": sum(1 for x in monthly if x > 0) / len(monthly),
    }


def select(scored: list[dict[str, Any]], name: str, pred: Callable[[dict[str, Any]], bool], top_n: int = BASE_TOP_N, ind_cap: int = IND_CAP) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        if pred(r):
            by_month[r["revenue_month"]].append(r)
    out: list[dict[str, Any]] = []
    for month in sorted(by_month):
        counts: dict[str, int] = defaultdict(int)
        selected = 0
        for r in sorted(by_month[month], key=lambda x: x["score_sur_core"], reverse=True):
            if counts[r["industry"]] >= ind_cap:
                continue
            r2 = dict(r)
            r2["recipe"] = name
            r2["score"] = r["score_sur_core"]
            out.append(r2)
            counts[r["industry"]] += 1
            selected += 1
            if selected >= top_n:
                break
    return out


def monthly_rows(trades: list[dict[str, Any]], recipes: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for recipe in recipes:
        by_month: dict[str, list[float]] = defaultdict(list)
        for r in trades:
            if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
                by_month[r["revenue_month"]].append(float(r["net_return"]))
        nav = 1.0
        for m in all_months:
            ret = statistics.mean(by_month[m]) if by_month.get(m) else 0.0
            nav *= 1 + ret
            out.append({"recipe": recipe, "revenue_month": m, "return": ret, "nav": nav, "positions": len(by_month[m])})
    return out


def summarize(trades: list[dict[str, Any]], recipes: list[str], counts: dict[str, int], all_months: list[str]) -> list[dict[str, Any]]:
    mrows = monthly_rows(trades, recipes, all_months)
    out: list[dict[str, Any]] = []
    for recipe in recipes:
        base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        monthly = [float(r["return"]) for r in mrows if r["recipe"] == recipe]
        mm = metrics(monthly)
        wins = [float(r["net_return"]) for r in base if float(r["net_return"]) > 0]
        losses = [float(r["net_return"]) for r in base if float(r["net_return"]) <= 0]
        out.append({
            "recipe": recipe,
            "months_cash_counted": len(all_months),
            "signals": counts.get(recipe, 0),
            "trades": len(base),
            "active_months": len({r["revenue_month"] for r in base}),
            "avg_positions_all_months": len(base) / len(all_months) if all_months else 0,
            "total_return": mm["total_return"],
            "ann_return": mm["ann_return"],
            "sharpe_cash_counted": mm["sharpe"],
            "mdd": mm["mdd"],
            "monthly_win_rate": mm["win_rate"],
            "trade_win_rate": len(wins) / len(base) if base else None,
            "avg_win": statistics.mean(wins) if wins else None,
            "avg_loss": statistics.mean(losses) if losses else None,
            "payoff_ratio": (statistics.mean(wins) / abs(statistics.mean(losses))) if wins and losses and statistics.mean(losses) != 0 else None,
        })
    return out


def remove_winners(trades: list[dict[str, Any]], recipes: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for recipe in recipes:
        base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        ranked = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
        for n in [0, 3, 5, 10, 15, 20]:
            kill = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in ranked[:n]}
            kept = [r for r in base if (r["revenue_month"], r["stock_id"], r["entry_date"]) not in kill]
            by_month: dict[str, list[float]] = defaultdict(list)
            for r in kept:
                by_month[r["revenue_month"]].append(float(r["net_return"]))
            mm = metrics([statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in all_months])
            out.append({"recipe": recipe, "remove_top_winners": n, "trades": len(kept), "total_return": mm["total_return"], "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"]})
    return out


def yearly(trades: list[dict[str, Any]], recipes: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    months_by_year: dict[str, list[str]] = defaultdict(list)
    for m in all_months:
        months_by_year[m[:4]].append(m)
    out: list[dict[str, Any]] = []
    for recipe in recipes:
        by_month: dict[str, list[float]] = defaultdict(list)
        for r in trades:
            if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
                by_month[r["revenue_month"]].append(float(r["net_return"]))
        for y, months in sorted(months_by_year.items()):
            mm = metrics([statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in months])
            out.append({"recipe": recipe, "year": y, "months_cash_counted": len(months), "active_months": sum(1 for m in months if by_month.get(m)), "return": mm["total_return"], "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"]})
    return out


def top_contributors(trades: list[dict[str, Any]], recipes: list[str], n: int = 20) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for recipe in recipes:
        base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        for rank, r in enumerate(sorted(base, key=lambda x: float(x["net_return"]), reverse=True)[:n], start=1):
            out.append({
                "recipe": recipe,
                "rank": rank,
                "revenue_month": r.get("revenue_month"),
                "stock_id": r.get("stock_id"),
                "stock_name": r.get("stock_name"),
                "industry": r.get("industry"),
                "entry_date": r.get("entry_date"),
                "exit_date": r.get("exit_date"),
                "net_return": r.get("net_return"),
                "sur_3m": r.get("sur_3m"),
                "abnormal_turnover": r.get("abnormal_turnover"),
                "entry_range_pct": r.get("entry_range_pct"),
                "pre_ret_20d": r.get("pre_ret_20d"),
                "avg_turnover_20d": r.get("avg_turnover_20d"),
            })
    return out


def maybe_chart(monthly: list[dict[str, Any]]) -> str | None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    CHARTS.mkdir(parents=True, exist_ok=True)
    recipes = ["s1_baseline", "quiet_core", "quiet_electronics", "quiet_semiconductor", "quiet_liq100m"]
    fig, ax = plt.subplots(figsize=(11, 6))
    for recipe in recipes:
        rows = [r for r in monthly if r["recipe"] == recipe]
        if not rows:
            continue
        ax.plot([r["revenue_month"] for r in rows], [r["nav"] for r in rows], label=recipe)
    ax.set_title("Phase 3.17 quiet digestion NAV")
    ax.set_ylabel("NAV")
    ax.tick_params(axis="x", rotation=60)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_CHART, dpi=160)
    plt.close(fig)
    return str(OUT_CHART)


def main() -> int:
    pa.HOLDINGS = [HOLDING]; pa.COST = COST; pa.BASE_TOP_N = BASE_TOP_N; pa.BASE_INDUSTRY_CAP = IND_CAP; pa.LIQ = LIQ
    sur.HOLDINGS = [HOLDING]; sur.COST = COST; sur.TOP_N = BASE_TOP_N; sur.INDUSTRY_CAP = IND_CAP; sur.MIN_AVG_TURNOVER_20D = LIQ

    scored, prices_by_stock, date_map, _counts = pa.build_scored()
    th = pa.thresholds(scored)
    audit = p316.attach_entry_ohlc(scored)
    all_months = sorted({r["revenue_month"] for r in scored})
    vol_low = th["abnormal_turnover"][0]
    vol_high = th["abnormal_turnover"][1]
    mom_low, mom_high = th["momentum_120_20"]

    base = lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= mom_high and r.get("entry_close_location") is not None
    vol_low_only = lambda r: base(r) and r["abnormal_turnover"] <= vol_low
    narrow_only = lambda r: base(r) and r["entry_range_pct"] <= audit["range_low"]
    quiet_core = lambda r: vol_low_only(r) and r["entry_range_pct"] <= audit["range_low"]
    no_supply = lambda r: r["entry_upper_shadow_ratio"] < audit["upper_hi"] and r["entry_close_location"] > audit["close_low"]
    supply = lambda r: r["entry_upper_shadow_ratio"] >= audit["upper_hi"] or r["entry_close_location"] <= audit["close_low"]
    large_black = lambda r: bool(r["entry_black_candle"]) and r["entry_body_ratio"] >= audit["body_hi"]

    specs: list[tuple[str, Callable[[dict[str, Any]], bool], int, int]] = [
        ("s1_baseline", base, 8, 3),
        ("vol_low_only", vol_low_only, 8, 3),
        ("narrow_only", narrow_only, 8, 3),
        ("quiet_core", quiet_core, 8, 3),
        ("quiet_electronics", lambda r: quiet_core(r) and r["industry"] in ELECTRONICS, 8, 3),
        ("quiet_non_electronics", lambda r: quiet_core(r) and r["industry"] not in ELECTRONICS, 8, 3),
        ("quiet_semiconductor", lambda r: quiet_core(r) and r["industry"] == SEMICONDUCTOR, 8, 3),
        ("quiet_no_semiconductor", lambda r: quiet_core(r) and r["industry"] != SEMICONDUCTOR, 8, 3),
        ("quiet_liq50_100m", lambda r: quiet_core(r) and 50_000_000 <= r["avg_turnover_20d"] < 100_000_000, 8, 3),
        ("quiet_liq100m", lambda r: quiet_core(r) and r["avg_turnover_20d"] >= 100_000_000, 8, 3),
        ("quiet_pullback20", lambda r: quiet_core(r) and r["pre_ret_20d"] <= 0, 8, 3),
        ("quiet_not_runup20", lambda r: quiet_core(r) and r["pre_ret_20d"] <= mom_high, 8, 3),
        ("quiet_no_supply", lambda r: quiet_core(r) and no_supply(r), 8, 3),
        ("quiet_supply_pressure", lambda r: quiet_core(r) and supply(r), 8, 3),
        ("quiet_no_large_black", lambda r: quiet_core(r) and not large_black(r), 8, 3),
        ("quiet_large_black", lambda r: quiet_core(r) and large_black(r), 8, 3),
        ("quiet_top4", quiet_core, 4, 3),
        ("quiet_top6", quiet_core, 6, 3),
        ("quiet_top12", quiet_core, 12, 3),
        ("quiet_indcap1", quiet_core, 8, 1),
        ("quiet_indcap2", quiet_core, 8, 2),
    ]

    signals: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    recipes: list[str] = []
    for name, pred, top_n, ind_cap in specs:
        sigs = select(scored, name, pred, top_n=top_n, ind_cap=ind_cap)
        signals.extend(sigs)
        counts[name] = len(sigs)
        recipes.append(name)

    trades = sur.build_trades(signals, prices_by_stock, date_map)
    variants = summarize(trades, recipes, counts, all_months)
    remove = remove_winners(trades, recipes, all_months)
    yrs = yearly(trades, recipes, all_months)
    contrib = top_contributors(trades, recipes)
    monthly = monthly_rows(trades, recipes, all_months)
    chart = maybe_chart(monthly)

    write_csv(OUT_VARIANTS, variants)
    write_csv(OUT_REMOVE, remove)
    write_csv(OUT_YEARLY, yrs)
    write_csv(OUT_CONTRIB, contrib)
    write_csv(OUT_MONTHLY, monthly)

    by = {r["recipe"]: r for r in variants}
    rremove: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for r in remove:
        rremove[r["recipe"]][int(r["remove_top_winners"])] = r

    focus = ["s1_baseline", "vol_low_only", "narrow_only", "quiet_core", "quiet_electronics", "quiet_non_electronics", "quiet_semiconductor", "quiet_no_semiconductor", "quiet_liq100m", "quiet_pullback20", "quiet_no_supply", "quiet_supply_pressure", "quiet_no_large_black", "quiet_large_black"]
    lines: list[str] = []
    lines += [
        "# Phase 3.17 quiet digestion deep dive\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 本輪假說\n\n",
        "月營收 SUR 強、但進場前成交值偏低且 entry day 日內區間偏窄，可能代表市場尚未擁擠、消息仍在被消化；後續 20D 若由延遲再定價推動，應該比單純低成交值或單純窄幅 K 線更穩。反過來，若效果只存在少數半導體大贏家或低流動性標的，則它只是 winner concentration / liquidity artifact。\n\n",
        "## Thresholds and coverage\n\n",
        f"- abnormal turnover low/high tercile = {vol_low:.4f} / {vol_high:.4f}\n",
        f"- entry range low tercile = {audit['range_low']:.4f}; upper-shadow high tercile = {audit['upper_hi']:.4f}; close-location low tercile = {audit['close_low']:.4f}; body high tercile = {audit['body_hi']:.4f}\n",
        f"- scored rows with entry OHLC matched = {audit['ohlc_matched']}/{len(scored)}\n\n",
        "## Variant summary（20D fixed exit, inactive months counted as cash）\n\n",
    ]
    for name in focus:
        r = by[name]
        lines.append(f"- `{name}`: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}, avg_pos={float(r['avg_positions_all_months']):.2f}, trades={r['trades']}, trade_win={pct(r['trade_win_rate'])}\n")

    lines.append("\n## Remove-winner stress（核心 variants）\n\n")
    for name in ["s1_baseline", "quiet_core", "quiet_electronics", "quiet_semiconductor", "quiet_liq100m", "quiet_no_large_black"]:
        lines.append(f"### {name}\n")
        for n in [0, 3, 5, 10, 15, 20]:
            r = rremove[name][n]
            lines.append(f"- remove {n}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, trades={r['trades']}\n")

    lines.append("\n## Year split（核心 variants）\n\n")
    for name in ["s1_baseline", "quiet_core", "quiet_electronics", "quiet_semiconductor", "quiet_liq100m", "quiet_no_large_black"]:
        lines.append(f"### {name}\n")
        for r in [x for x in yrs if x["recipe"] == name]:
            lines.append(f"- {r['year']}: return={pct(r['return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}\n")

    lines.append("\n## Position-count / concentration variants\n\n")
    for name in ["quiet_top4", "quiet_top6", "quiet_core", "quiet_top12", "quiet_indcap1", "quiet_indcap2"]:
        r = by[name]
        rw5 = rremove[name][5]
        lines.append(f"- `{name}`: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, trades={r['trades']}, remove5 Sharpe={num(rw5['sharpe_cash_counted'])}\n")

    lines += [
        "\n## Interpretation\n\n",
        "- Promotion gate: quiet digestion must outperform S1 on risk-adjusted return or drawdown **and** survive remove-winner / sector / liquidity checks. If not, it remains a sizing/filter hypothesis, not a replacement strategy.\n",
        "- If `vol_low_only` and `narrow_only` are weaker than `quiet_core`, the interaction has a cleaner causal reading: low attention + narrow digestion is more informative than either condition alone.\n",
        "- If `quiet_semiconductor` or `quiet_electronics` dominate while `quiet_non_electronics` is sparse/weak, the edge is still supply-chain regime-specific.\n",
        "- If `quiet_liq100m` collapses, quiet digestion may be a low-liquidity artifact; if it survives, it is more institutionally credible.\n",
        "- Daily OHLC still cannot model exact announcement timestamp, opening fill, limit-up queue priority, or intraday breakout.\n\n",
        "## Outputs\n\n",
    ]
    for p in [OUT_VARIANTS, OUT_REMOVE, OUT_YEARLY, OUT_CONTRIB, OUT_MONTHLY, OUT_REPORT]:
        lines.append(f"- `{p}`\n")
    if chart:
        lines.append(f"- `{chart}`\n")
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")

    print(json.dumps({
        "outputs": [str(OUT_VARIANTS), str(OUT_REMOVE), str(OUT_YEARLY), str(OUT_CONTRIB), str(OUT_MONTHLY), str(OUT_REPORT), chart],
        "key": {k: by[k] for k in ["s1_baseline", "quiet_core", "quiet_electronics", "quiet_semiconductor", "quiet_liq100m"]},
        "thresholds": {"vol_low": vol_low, "vol_high": vol_high, "range_low": audit["range_low"]},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
