#!/usr/bin/env python3
"""Phase 3.6: short-horizon SUR research for 5/10/15/20 trading-day holds.

Research-only. No trading, no deployment, no package installation.

This script reuses Phase 3.5 SUR factor construction and evaluates whether the
monthly-revenue surprise strategy has usable short-horizon behavior for 10-20D style trading.
It tests:
- Holding windows: 5D, 10D, 15D, 20D.
- Top N: 10, 15, 20.
- Liquidity thresholds: 50m, 100m, 300m TWD average 20D traded value.
- Cost assumptions: 0.5%, 0.7%, 1.0% round-trip.
- Remove top winners stress test on the baseline.
- Year-by-year breakdown for 10D/20D.
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
OUT_VARIANTS = PROCESSED / "short_horizon_sur_variants.csv"
OUT_REMOVE = PROCESSED / "short_horizon_sur_remove_winners.csv"
OUT_YEARLY = PROCESSED / "short_horizon_sur_yearly.csv"
OUT_SUMMARY = PROCESSED / "short_horizon_sur_summary.json"
OUT_REPORT = REPORTS / "phase3_6_short_horizon_sur_report.md"

SUR_PATH = ROOT / "scripts" / "sur_factor_tests.py"
spec = importlib.util.spec_from_file_location("sur_factor_tests", SUR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {SUR_PATH}")
sur = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(sur)

HOLDINGS = [5, 10, 15, 20]
RECIPES_TO_REPORT = ["sur_core", "sur_balanced", "industry_adjusted_sur", "yoy_baseline"]
BASELINE = {"top_n": 15, "liq": 50_000_000, "cost": 0.007, "industry_cap": 5}


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


def cohort_returns(trades: list[dict[str, Any]], recipe: str, holding: int, field: str = "net_return") -> list[float]:
    rows = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == holding]
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_month[r["revenue_month"]].append(float(r[field]))
    return [statistics.mean(by_month[m]) for m in sorted(by_month)]


def summarize_trades(trades: list[dict[str, Any]], config_name: str, top_n: int, liq: int, cost: float) -> list[dict[str, Any]]:
    rows = []
    for recipe in RECIPES_TO_REPORT:
        for h in HOLDINGS:
            strat = metrics(cohort_returns(trades, recipe, h, "net_return"))
            excess = metrics(cohort_returns(trades, recipe, h, "excess_return"))
            trade_rows = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == h]
            rows.append({
                "config": config_name, "recipe": recipe, "holding_days": h,
                "top_n": top_n, "liquidity_threshold": liq, "cost": cost,
                "trades": len(trade_rows),
                "strategy_total_return": strat.get("total_return"),
                "strategy_ann_return": strat.get("ann_return"),
                "strategy_sharpe": strat.get("sharpe_proxy"),
                "strategy_mdd": strat.get("mdd"),
                "strategy_win_rate": strat.get("win_rate"),
                "excess_total_return": excess.get("total_return"),
                "excess_mdd": excess.get("mdd"),
                "excess_win_rate": excess.get("win_rate"),
            })
    return rows


def run_config(name: str, top_n: int, liq: int, cost: float, industry_cap: int = 5) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    # Monkeypatch the imported Phase 3.5 module; this is safe inside this script process.
    sur.HOLDINGS = HOLDINGS
    sur.TOP_N = top_n
    sur.INDUSTRY_CAP = industry_cap
    sur.MIN_AVG_TURNOVER_20D = liq
    sur.COST = cost
    rev_rows = sur.build_revenue_panel(sur.read_csv(sur.REV_CSV))
    prices_by_stock, trading_dates, date_map = sur.build_price_maps(sur.read_csv(sur.PRICE_CSV))
    cands = sur.eligible_candidates(rev_rows, prices_by_stock, trading_dates)
    scored = sur.add_scores(cands)
    signals = sur.select_signals(scored)
    trades = sur.build_trades(signals, prices_by_stock, date_map)
    counts = {"eligible_candidates": len(cands), "signals": len(signals), "trades": len(trades)}
    return trades, counts


def remove_winners_rows(trades: list[dict[str, Any]], recipe: str = "sur_core") -> list[dict[str, Any]]:
    out = []
    for h in HOLDINGS:
        base_rows = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == h]
        sorted_rows = sorted(base_rows, key=lambda r: float(r["net_return"]), reverse=True)
        for remove_n in [0, 5, 10, 20]:
            remove_keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:remove_n]}
            kept = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == h and (r["revenue_month"], r["stock_id"], r["entry_date"]) not in remove_keys]
            strat = metrics(cohort_returns(kept, recipe, h, "net_return"))
            excess = metrics(cohort_returns(kept, recipe, h, "excess_return"))
            out.append({
                "recipe": recipe, "holding_days": h, "remove_top_winners": remove_n, "trades": len(kept),
                "strategy_total_return": strat.get("total_return"), "strategy_mdd": strat.get("mdd"), "strategy_sharpe": strat.get("sharpe_proxy"),
                "excess_total_return": excess.get("total_return"), "excess_mdd": excess.get("mdd"),
            })
    return out


def yearly_rows(trades: list[dict[str, Any]], recipe: str = "sur_core") -> list[dict[str, Any]]:
    out = []
    for h in [10, 20]:
        rows = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == h]
        by_year_month: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            year = str(r["entry_date"])[:4]
            by_year_month[(year, r["revenue_month"])].append(r)
        years = sorted({y for y, _m in by_year_month})
        for y in years:
            months = sorted(m for yy, m in by_year_month if yy == y)
            strat = [statistics.mean(float(x["net_return"]) for x in by_year_month[(y, m)]) for m in months]
            excess = [statistics.mean(float(x["excess_return"]) for x in by_year_month[(y, m)]) for m in months]
            sm = metrics(strat); em = metrics(excess)
            out.append({
                "recipe": recipe, "holding_days": h, "year": y, "months": len(months),
                "strategy_return": sm.get("total_return"), "strategy_mdd": sm.get("mdd"), "strategy_win_rate": sm.get("win_rate"),
                "excess_return": em.get("total_return"), "excess_mdd": em.get("mdd"), "excess_win_rate": em.get("win_rate"),
            })
    return out


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(variant_rows: list[dict[str, Any]], remove_rows: list[dict[str, Any]], yearly: list[dict[str, Any]], counts: dict[str, Any]) -> None:
    baseline_rows = [r for r in variant_rows if r["config"] == "baseline" and r["recipe"] == "sur_core"]
    lines = [
        "# Phase 3.6 短線 SUR 策略研究：5/10/15/20D\n\n",
        "本階段聚焦使用者提到的 10–20 天內短線交易可能性。仍為 proxy/cohort backtest，不是實際持倉、paper order 或交易建議。\n\n",
        "## Baseline 設定\n\n",
        "- Recipe：主要看 `sur_core`，並與 `sur_balanced`、`industry_adjusted_sur`、`yoy_baseline` 比較。\n",
        "- Top 15，單一產業最多 5 檔。\n",
        "- 20D 平均成交金額門檻 5,000 萬。\n",
        "- round-trip cost 0.7%。\n",
        "- 持有期：5D / 10D / 15D / 20D。\n\n",
        "## Baseline sur_core 結果\n\n",
    ]
    for r in baseline_rows:
        lines.append(
            f"- {r['holding_days']}D：strategy={fmt_pct(r['strategy_total_return'])}, excess={fmt_pct(r['excess_total_return'])}, "
            f"ann={fmt_pct(r['strategy_ann_return'])}, Sharpe={fmt_num(r['strategy_sharpe'])}, MDD={fmt_pct(r['strategy_mdd'])}, win={fmt_pct(r['strategy_win_rate'])}\n"
        )
    lines.append("\n## 每個持有期最佳 recipe/config\n\n")
    for h in HOLDINGS:
        rows = [r for r in variant_rows if int(r["holding_days"]) == h]
        best = max(rows, key=lambda r: float(r["excess_total_return"] or -999))
        lines.append(
            f"- {h}D：{best['config']} / {best['recipe']}，strategy={fmt_pct(best['strategy_total_return'])}，"
            f"excess={fmt_pct(best['excess_total_return'])}，MDD={fmt_pct(best['strategy_mdd'])}，Sharpe={fmt_num(best['strategy_sharpe'])}\n"
        )
    lines.append("\n## Remove top winners 壓力測試：baseline sur_core\n\n")
    for h in HOLDINGS:
        lines.append(f"### {h}D\n")
        for r in [x for x in remove_rows if int(x["holding_days"]) == h]:
            lines.append(f"- remove top {r['remove_top_winners']}：strategy={fmt_pct(r['strategy_total_return'])}，excess={fmt_pct(r['excess_total_return'])}，MDD={fmt_pct(r['strategy_mdd'])}\n")
        lines.append("\n")
    lines.append("## 年度拆解：baseline sur_core 10D / 20D\n\n")
    for r in yearly:
        lines.append(f"- {r['holding_days']}D {r['year']}：strategy={fmt_pct(r['strategy_return'])}，excess={fmt_pct(r['excess_return'])}，win={fmt_pct(r['strategy_win_rate'])}，MDD={fmt_pct(r['strategy_mdd'])}\n")
    lines += [
        "\n## 短線交易解讀重點\n\n",
        "- 5D/10D 可用來觀察公告後短期資訊擴散，但成本與滑價會更重要。\n",
        "- 10D/15D/20D 若能維持 positive excess 且 MDD 明顯低於 40D/60D，才比較接近短線 paper trading 候選。\n",
        "- 若 remove top winners 後 excess 快速消失，代表短線仍是右尾捕捉，不適合重倉單檔。\n",
        "- 下一步短線最需要加入籌碼資料：外資/投信買賣超、融資融券、異常成交量與法人確認。\n\n",
        "## 輸出檔案\n\n",
        f"- `{OUT_VARIANTS}`\n- `{OUT_REMOVE}`\n- `{OUT_YEARLY}`\n- `{OUT_SUMMARY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    configs = [("baseline", BASELINE)]
    for top_n in [10, 20]:
        configs.append((f"top{top_n}", {**BASELINE, "top_n": top_n, "industry_cap": max(3, round(top_n / 3))}))
    for liq in [100_000_000, 300_000_000]:
        configs.append((f"liq{liq//1_000_000}m", {**BASELINE, "liq": liq}))
    for cost in [0.005, 0.010]:
        configs.append((f"cost{cost:.3f}", {**BASELINE, "cost": cost}))

    variant_rows: list[dict[str, Any]] = []
    counts_by_config = {}
    baseline_trades: list[dict[str, Any]] = []
    for name, cfg in configs:
        trades, counts = run_config(name, cfg["top_n"], cfg["liq"], cfg["cost"], cfg["industry_cap"])
        counts_by_config[name] = counts
        if name == "baseline":
            baseline_trades = trades
        variant_rows.extend(summarize_trades(trades, name, cfg["top_n"], cfg["liq"], cfg["cost"]))

    remove_rows = remove_winners_rows(baseline_trades, "sur_core")
    yearly = yearly_rows(baseline_trades, "sur_core")
    write_csv(OUT_VARIANTS, variant_rows)
    write_csv(OUT_REMOVE, remove_rows)
    write_csv(OUT_YEARLY, yearly)
    summary = {"counts_by_config": counts_by_config, "baseline": BASELINE, "holdings": HOLDINGS}
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(variant_rows, remove_rows, yearly, counts_by_config)
    print(json.dumps({"configs": len(configs), "variant_rows": len(variant_rows), "remove_rows": len(remove_rows), "yearly_rows": len(yearly), "outputs": [str(OUT_VARIANTS), str(OUT_REMOVE), str(OUT_YEARLY), str(OUT_SUMMARY), str(OUT_REPORT)]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
