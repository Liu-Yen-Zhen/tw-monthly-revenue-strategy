#!/usr/bin/env python3
"""Phase 3.18: S1 + quiet-digestion dynamic sizing diagnostics.

Research-only. No live trading, broker connection, or orders.

Question: quiet digestion looked interesting as a sparse standalone slice. Does it
improve the *portfolio construction* of the S1 fixed-20 proxy when used as a
weighting / risk gate rather than as a replacement strategy?
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
OUT_VARIANTS = PROCESSED / "quiet_digestion_dynamic_sizing_variants.csv"
OUT_REMOVE = PROCESSED / "quiet_digestion_dynamic_sizing_remove_winners.csv"
OUT_YEARLY = PROCESSED / "quiet_digestion_dynamic_sizing_yearly.csv"
OUT_MONTHLY = PROCESSED / "quiet_digestion_dynamic_sizing_monthly.csv"
OUT_EXPOSURE = PROCESSED / "quiet_digestion_dynamic_sizing_exposure.csv"
OUT_REPORT = REPORTS / "phase3_18_quiet_digestion_dynamic_sizing_report.md"
OUT_CHART = CHARTS / "phase3_18_dynamic_sizing_nav_zh.png"

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
TOP_N = 8
IND_CAP = 3
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
        "ann_return": (1 + total) ** (12 / len(monthly)) - 1,
        "mean_month": statistics.mean(monthly),
        "sharpe": statistics.mean(monthly) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(monthly),
        "win_rate": sum(1 for x in monthly if x > 0) / len(monthly),
        "best_month": max(monthly),
        "worst_month": min(monthly),
    }


def select_s1(scored: list[dict[str, Any]], pred: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
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
            r2["recipe"] = "s1_universe"
            r2["score"] = r["score_sur_core"]
            out.append(r2)
            counts[r["industry"]] += 1
            selected += 1
            if selected >= TOP_N:
                break
    return out


def enrich_trade_flags(trades: list[dict[str, Any]], signals: list[dict[str, Any]]) -> None:
    sig_by_key = {(s["revenue_month"], s["stock_id"], s["entry_date"]): s for s in signals}
    for r in trades:
        s = sig_by_key.get((r["revenue_month"], r["stock_id"], r["entry_date"]))
        if not s:
            continue
        for k in ["quiet_core", "quiet_no_large_black", "large_black", "is_electronics", "is_semiconductor", "entry_range_pct", "entry_close_location", "entry_upper_shadow_ratio", "entry_body_ratio"]:
            r[k] = s.get(k)


def variant_weight(row: dict[str, Any], variant: str) -> float:
    q = bool(row.get("quiet_core"))
    qnlb = bool(row.get("quiet_no_large_black"))
    lb = bool(row.get("large_black"))
    liq100 = float(row.get("avg_turnover_20d", 0)) >= 100_000_000
    if variant == "equal_s1":
        return 1.0
    if variant == "boost_quiet_125":
        return 1.25 if q else 1.0
    if variant == "boost_quiet_150":
        return 1.50 if q else 1.0
    if variant == "boost_quiet_200":
        return 2.00 if q else 1.0
    if variant == "boost_quiet_no_large_black_150":
        return 1.50 if qnlb else 1.0
    if variant == "downweight_large_black_050":
        return 0.50 if lb else 1.0
    if variant == "exclude_large_black":
        return 0.0 if lb else 1.0
    if variant == "boost_quiet150_down_black050":
        return (1.50 if q else 1.0) * (0.50 if lb else 1.0)
    if variant == "boost_quiet150_exclude_black":
        return 0.0 if lb else (1.50 if q else 1.0)
    if variant == "boost_quiet_liq100_150":
        return 1.50 if (q and liq100) else 1.0
    raise KeyError(variant)


def monthly_eval(trades: list[dict[str, Any]], variant: str, all_months: list[str], remove_keys: set[tuple[str, str, str]] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if int(r["holding_days"]) != HOLDING:
            continue
        key = (r["revenue_month"], r["stock_id"], r["entry_date"])
        if remove_keys and key in remove_keys:
            continue
        rows_by_month[r["revenue_month"]].append(r)
    monthly: list[dict[str, Any]] = []
    exposure: list[dict[str, Any]] = []
    nav = 1.0
    for m in all_months:
        rows = rows_by_month.get(m, [])
        weighted_sum = total_w = quiet_w = black_w = elec_w = semi_w = 0.0
        active_rows = 0
        for r in rows:
            w = variant_weight(r, variant)
            if w <= 0:
                continue
            active_rows += 1
            total_w += w
            weighted_sum += w * float(r["net_return"])
            if r.get("quiet_core"):
                quiet_w += w
            if r.get("large_black"):
                black_w += w
            if r.get("is_electronics"):
                elec_w += w
            if r.get("is_semiconductor"):
                semi_w += w
        ret = weighted_sum / total_w if total_w > 0 else 0.0
        nav *= 1 + ret
        monthly.append({"variant": variant, "revenue_month": m, "return": ret, "nav": nav, "positions": active_rows, "gross_weight": total_w})
        exposure.append({
            "variant": variant, "revenue_month": m, "positions": active_rows, "gross_weight": total_w,
            "quiet_weight_share": quiet_w / total_w if total_w else 0.0,
            "large_black_weight_share": black_w / total_w if total_w else 0.0,
            "electronics_weight_share": elec_w / total_w if total_w else 0.0,
            "semiconductor_weight_share": semi_w / total_w if total_w else 0.0,
        })
    return monthly, exposure


def summarize_variant(trades: list[dict[str, Any]], variant: str, all_months: list[str]) -> dict[str, Any]:
    monthly, exposure = monthly_eval(trades, variant, all_months)
    mm = metrics([float(r["return"]) for r in monthly])
    active_months = sum(1 for r in monthly if int(r["positions"]) > 0)
    avg_pos = statistics.mean([int(r["positions"]) for r in monthly]) if monthly else 0.0
    return {
        "variant": variant,
        "months_cash_counted": len(all_months),
        "active_months": active_months,
        "avg_positions_all_months": avg_pos,
        "total_return": mm["total_return"],
        "ann_return": mm["ann_return"],
        "sharpe_cash_counted": mm["sharpe"],
        "mdd": mm["mdd"],
        "monthly_win_rate": mm["win_rate"],
        "best_month": mm["best_month"],
        "worst_month": mm["worst_month"],
        "avg_quiet_weight_share": statistics.mean([float(r["quiet_weight_share"]) for r in exposure]) if exposure else 0.0,
        "avg_large_black_weight_share": statistics.mean([float(r["large_black_weight_share"]) for r in exposure]) if exposure else 0.0,
        "avg_electronics_weight_share": statistics.mean([float(r["electronics_weight_share"]) for r in exposure]) if exposure else 0.0,
        "avg_semiconductor_weight_share": statistics.mean([float(r["semiconductor_weight_share"]) for r in exposure]) if exposure else 0.0,
    }


def remove_winner_rows(trades: list[dict[str, Any]], variants: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    base = [r for r in trades if int(r["holding_days"]) == HOLDING]
    # Rank by raw stock return to stay comparable to prior phases, not by chosen variant weight.
    ranked = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
    out: list[dict[str, Any]] = []
    for variant in variants:
        for n in [0, 3, 5, 10, 15, 20]:
            kill = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in ranked[:n]}
            monthly, _exp = monthly_eval(trades, variant, all_months, remove_keys=kill)
            mm = metrics([float(r["return"]) for r in monthly])
            out.append({"variant": variant, "remove_top_winners": n, "total_return": mm["total_return"], "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"], "remaining_trades": len(base) - n})
    return out


def yearly_rows(trades: list[dict[str, Any]], variants: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for variant in variants:
        monthly, _exp = monthly_eval(trades, variant, all_months)
        by_year: dict[str, list[float]] = defaultdict(list)
        active_by_year: dict[str, int] = defaultdict(int)
        for r in monthly:
            y = r["revenue_month"][:4]
            by_year[y].append(float(r["return"]))
            if int(r["positions"]) > 0:
                active_by_year[y] += 1
        for y, rs in sorted(by_year.items()):
            mm = metrics(rs)
            out.append({"variant": variant, "year": y, "months_cash_counted": len(rs), "active_months": active_by_year[y], "return": mm["total_return"], "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"]})
    return out


def maybe_chart(monthly: list[dict[str, Any]]) -> str | None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return None
    CHARTS.mkdir(parents=True, exist_ok=True)
    show = ["equal_s1", "boost_quiet_150", "boost_quiet_no_large_black_150", "exclude_large_black", "boost_quiet150_exclude_black"]
    fig, ax = plt.subplots(figsize=(11, 6))
    for variant in show:
        rows = [r for r in monthly if r["variant"] == variant]
        ax.plot([r["revenue_month"] for r in rows], [r["nav"] for r in rows], label=variant)
    ax.set_title("Phase 3.18 S1 + quiet digestion dynamic sizing NAV")
    ax.set_ylabel("NAV")
    ax.tick_params(axis="x", rotation=60)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_CHART, dpi=160)
    plt.close(fig)
    return str(OUT_CHART)


def main() -> int:
    pa.HOLDINGS = [HOLDING]; pa.COST = COST; pa.BASE_TOP_N = TOP_N; pa.BASE_INDUSTRY_CAP = IND_CAP; pa.LIQ = LIQ
    sur.HOLDINGS = [HOLDING]; sur.COST = COST; sur.TOP_N = TOP_N; sur.INDUSTRY_CAP = IND_CAP; sur.MIN_AVG_TURNOVER_20D = LIQ

    scored, prices_by_stock, date_map, _counts = pa.build_scored()
    th = pa.thresholds(scored)
    audit = p316.attach_entry_ohlc(scored)
    all_months = sorted({r["revenue_month"] for r in scored})
    vol_low = th["abnormal_turnover"][0]
    mom_high = th["momentum_120_20"][1]

    base_pred = lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= mom_high and r.get("entry_close_location") is not None
    signals = select_s1(scored, base_pred)
    for s in signals:
        large_black = bool(s["entry_black_candle"]) and s["entry_body_ratio"] >= audit["body_hi"]
        quiet = s["abnormal_turnover"] <= vol_low and s["entry_range_pct"] <= audit["range_low"]
        s["quiet_core"] = quiet
        s["large_black"] = large_black
        s["quiet_no_large_black"] = quiet and not large_black
        s["is_electronics"] = s["industry"] in ELECTRONICS
        s["is_semiconductor"] = s["industry"] == SEMICONDUCTOR

    trades = sur.build_trades(signals, prices_by_stock, date_map)
    enrich_trade_flags(trades, signals)
    variants = [
        "equal_s1",
        "boost_quiet_125",
        "boost_quiet_150",
        "boost_quiet_200",
        "boost_quiet_no_large_black_150",
        "downweight_large_black_050",
        "exclude_large_black",
        "boost_quiet150_down_black050",
        "boost_quiet150_exclude_black",
        "boost_quiet_liq100_150",
    ]
    summary = [summarize_variant(trades, v, all_months) for v in variants]
    remove = remove_winner_rows(trades, variants, all_months)
    yearly = yearly_rows(trades, variants, all_months)
    monthly_all: list[dict[str, Any]] = []
    exposure_all: list[dict[str, Any]] = []
    for v in variants:
        m, e = monthly_eval(trades, v, all_months)
        monthly_all.extend(m); exposure_all.extend(e)
    chart = maybe_chart(monthly_all)

    write_csv(OUT_VARIANTS, summary)
    write_csv(OUT_REMOVE, remove)
    write_csv(OUT_YEARLY, yearly)
    write_csv(OUT_MONTHLY, monthly_all)
    write_csv(OUT_EXPOSURE, exposure_all)

    by = {r["variant"]: r for r in summary}
    remap: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for r in remove:
        remap[r["variant"]][int(r["remove_top_winners"])] = r
    focus = ["equal_s1", "boost_quiet_150", "boost_quiet_no_large_black_150", "exclude_large_black", "boost_quiet150_exclude_black", "boost_quiet_liq100_150"]

    quiet_count = sum(1 for s in signals if s["quiet_core"])
    black_count = sum(1 for s in signals if s["large_black"])
    q_black_count = sum(1 for s in signals if s["quiet_core"] and s["large_black"])

    lines: list[str] = [
        "# Phase 3.18 S1 + quiet digestion dynamic sizing\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 本輪假說\n\n",
        "Phase 3.17 顯示 quiet digestion 作為 standalone slice 雖然報酬高，但樣本少且 remove-winner 脆弱。因此本輪不把它當替代策略，而是測它能否作為 S1 fixed-20 proxy 的動態加權 / 風險閘門：quiet digestion 代表延遲再定價，應可小幅加權；large black K 代表 failed repricing / 供給壓力，應降權或排除。\n\n",
        "## Signal coverage\n\n",
        f"- S1 selected signals/trades = {len(signals)} / {len(trades)}\n",
        f"- quiet_core signals = {quiet_count}; large_black signals = {black_count}; quiet_and_large_black = {q_black_count}\n",
        f"- abnormal turnover low tercile = {vol_low:.4f}; entry range low tercile = {audit['range_low']:.4f}; body high tercile = {audit['body_hi']:.4f}\n\n",
        "## Variant summary（20D fixed exit, inactive months counted as cash）\n\n",
    ]
    for v in variants:
        r = by[v]
        lines.append(f"- `{v}`: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}, avg_pos={float(r['avg_positions_all_months']):.2f}, quiet_w={pct(r['avg_quiet_weight_share'])}, black_w={pct(r['avg_large_black_weight_share'])}\n")

    lines.append("\n## Remove-winner stress（focus variants）\n\n")
    for v in focus:
        lines.append(f"### {v}\n")
        for n in [0, 3, 5, 10, 15, 20]:
            r = remap[v][n]
            lines.append(f"- remove {n}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}\n")

    lines.append("\n## Year split\n\n")
    for v in focus:
        lines.append(f"### {v}\n")
        for r in [x for x in yearly if x["variant"] == v]:
            lines.append(f"- {r['year']}: return={pct(r['return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}\n")

    lines += [
        "\n## Interpretation\n\n",
        "- Promotion gate: dynamic sizing should improve Sharpe or MDD without increasing top-winner dependence. A small full-sample improvement is not enough.\n",
        "- If quiet boosts improve return but worsen remove-winner results, quiet digestion is still a right-tail amplifier rather than robust sizing information.\n",
        "- If excluding large black K improves MDD and remove-winner stability, it can be retained as a risk gate candidate. If it only lifts full-sample return, keep it diagnostic.\n",
        "- This remains fixed-20 daily OHLC proxy research, not executable stop/limit/open-fill simulation.\n\n",
        "## Outputs\n\n",
    ]
    for p in [OUT_VARIANTS, OUT_REMOVE, OUT_YEARLY, OUT_MONTHLY, OUT_EXPOSURE, OUT_REPORT]:
        lines.append(f"- `{p}`\n")
    if chart:
        lines.append(f"- `{chart}`\n")
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")

    print(json.dumps({"outputs": [str(OUT_VARIANTS), str(OUT_REMOVE), str(OUT_YEARLY), str(OUT_MONTHLY), str(OUT_EXPOSURE), str(OUT_REPORT), chart], "key": {k: by[k] for k in focus}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
