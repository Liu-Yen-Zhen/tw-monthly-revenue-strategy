#!/usr/bin/env python3
"""Phase 3.7: short-horizon price-action filters for Taiwan monthly-revenue SUR strategy.

Research-only. No trading, deployment, package installation, or broker/API use.

This phase tests whether short-horizon 10/15/20D behavior improves by pairing
SUR/fundamental surprise with price-action filters:
- avoid overextended 120D-to-20D momentum,
- prefer middle momentum or underreaction,
- require high QTD revenue YoY / revenue acceleration / 3M SUR,
- compare industry caps and winner-dependence.
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
OUT_VARIANTS = PROCESSED / "price_action_filter_variants.csv"
OUT_YEARLY = PROCESSED / "price_action_filter_yearly.csv"
OUT_REMOVE = PROCESSED / "price_action_filter_remove_winners.csv"
OUT_INDUSTRY = PROCESSED / "price_action_filter_industry.csv"
OUT_LATEST = PROCESSED / "price_action_filter_latest_candidates.csv"
OUT_SUMMARY = PROCESSED / "price_action_filter_summary.json"
OUT_REPORT = REPORTS / "phase3_7_price_action_filter_report.md"

SUR_PATH = ROOT / "scripts" / "sur_factor_tests.py"
spec = importlib.util.spec_from_file_location("sur_factor_tests", SUR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {SUR_PATH}")
sur = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(sur)

HOLDINGS = [10, 15, 20]
COST = 0.007
BASE_TOP_N = 15
BASE_INDUSTRY_CAP = 5
LIQ = 50_000_000


def fnum(x: Any) -> float | None:
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None


def q(vals: list[float], p: float) -> float | None:
    vals = sorted(v for v in vals if v is not None and not math.isnan(v))
    if not vals:
        return None
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


def build_scored() -> tuple[list[dict[str, Any]], dict, dict[str, dict[tuple[str, str], float]], dict[str, Any]]:
    sur.HOLDINGS = HOLDINGS
    sur.COST = COST
    sur.TOP_N = BASE_TOP_N
    sur.INDUSTRY_CAP = BASE_INDUSTRY_CAP
    sur.MIN_AVG_TURNOVER_20D = LIQ
    rev_rows = sur.build_revenue_panel(sur.read_csv(sur.REV_CSV))
    prices_by_stock, trading_dates, date_map = sur.build_price_maps(sur.read_csv(sur.PRICE_CSV))
    cands = sur.eligible_candidates(rev_rows, prices_by_stock, trading_dates)
    scored = sur.add_scores(cands)
    return scored, prices_by_stock, date_map, {"eligible_candidates": len(cands), "scored": len(scored)}


def thresholds(scored: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    fields = ["pre_ret_20d", "momentum_120_20", "sur", "sur_3m", "qtd_yoy", "rev_accel_3m", "abnormal_turnover"]
    out: dict[str, tuple[float, float]] = {}
    for f in fields:
        vals = [float(r[f]) for r in scored if fnum(r.get(f)) is not None]
        a, b = q(vals, 1/3), q(vals, 2/3)
        if a is None or b is None:
            raise RuntimeError(f"missing threshold for {f}")
        out[f] = (a, b)
    return out


def select_custom(
    scored: list[dict[str, Any]],
    name: str,
    score_field: str,
    pred: Callable[[dict[str, Any], dict[str, tuple[float, float]]], bool],
    th: dict[str, tuple[float, float]],
    top_n: int = BASE_TOP_N,
    industry_cap: int = BASE_INDUSTRY_CAP,
    semiconductor_cap: int | None = None,
) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        if pred(r, th):
            by_month[r["revenue_month"]].append(r)
    signals: list[dict[str, Any]] = []
    for _month, rows in by_month.items():
        ind_counts: dict[str, int] = defaultdict(int)
        semi_count = 0
        for r in sorted(rows, key=lambda x: x[score_field], reverse=True):
            if ind_counts[r["industry"]] >= industry_cap:
                continue
            if semiconductor_cap is not None and r["industry"] == "半導體業" and semi_count >= semiconductor_cap:
                continue
            r2 = dict(r)
            r2["recipe"] = name
            r2["score"] = r[score_field]
            signals.append(r2)
            ind_counts[r["industry"]] += 1
            if r["industry"] == "半導體業":
                semi_count += 1
            if sum(1 for x in signals if x["recipe"] == name and x["revenue_month"] == r["revenue_month"]) >= top_n:
                break
    return signals


def monthly_returns(trades: list[dict[str, Any]], recipe: str, h: int, field: str) -> list[float]:
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in trades:
        if r["recipe"] == recipe and int(r["holding_days"]) == h:
            by_month[r["revenue_month"]].append(float(r[field]))
    return [statistics.mean(by_month[m]) for m in sorted(by_month)]


def summarize_variants(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        for h in HOLDINGS:
            rows = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == h]
            strat = metrics(monthly_returns(trades, recipe, h, "net_return"))
            excess = metrics(monthly_returns(trades, recipe, h, "excess_return"))
            months = strat.get("months", 0) or 0
            out.append({
                "recipe": recipe,
                "holding_days": h,
                "months": months,
                "trades": len(rows),
                "avg_positions": len(rows) / months if months else 0,
                "strategy_total_return": strat.get("total_return"),
                "strategy_ann_return": strat.get("ann_return"),
                "strategy_sharpe": strat.get("sharpe_proxy"),
                "strategy_mdd": strat.get("mdd"),
                "strategy_win_rate": strat.get("win_rate"),
                "excess_total_return": excess.get("total_return"),
                "excess_mdd": excess.get("mdd"),
                "excess_win_rate": excess.get("win_rate"),
            })
    return out


def yearly_rows(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        for h in HOLDINGS:
            by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
            for r in trades:
                if r["recipe"] == recipe and int(r["holding_days"]) == h:
                    by[(str(r["entry_date"])[:4], r["revenue_month"])].append(r)
            for y in sorted({yy for yy, _m in by}):
                months = sorted(m for yy, m in by if yy == y)
                strat = [statistics.mean(float(x["net_return"]) for x in by[(y, m)]) for m in months]
                excess = [statistics.mean(float(x["excess_return"]) for x in by[(y, m)]) for m in months]
                sm, em = metrics(strat), metrics(excess)
                out.append({
                    "recipe": recipe, "holding_days": h, "year": y, "months": len(months),
                    "strategy_return": sm.get("total_return"), "strategy_mdd": sm.get("mdd"), "strategy_win_rate": sm.get("win_rate"),
                    "excess_return": em.get("total_return"), "excess_mdd": em.get("mdd"), "excess_win_rate": em.get("win_rate"),
                })
    return out


def remove_winners_rows(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        for h in HOLDINGS:
            base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == h]
            sorted_rows = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
            for remove_n in [0, 5, 10, 20]:
                remove_keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:remove_n]}
                kept = [r for r in base if (r["revenue_month"], r["stock_id"], r["entry_date"]) not in remove_keys]
                by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for r in kept:
                    by_month[r["revenue_month"]].append(r)
                strat = [statistics.mean(float(x["net_return"]) for x in by_month[m]) for m in sorted(by_month)]
                excess = [statistics.mean(float(x["excess_return"]) for x in by_month[m]) for m in sorted(by_month)]
                sm, em = metrics(strat), metrics(excess)
                out.append({
                    "recipe": recipe, "holding_days": h, "remove_top_winners": remove_n, "trades": len(kept),
                    "strategy_total_return": sm.get("total_return"), "strategy_mdd": sm.get("mdd"), "strategy_sharpe": sm.get("sharpe_proxy"),
                    "excess_total_return": em.get("total_return"), "excess_mdd": em.get("mdd"),
                })
    return out


def industry_rows(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        for h in HOLDINGS:
            by: dict[str, list[float]] = defaultdict(list)
            for r in trades:
                if r["recipe"] == recipe and int(r["holding_days"]) == h:
                    by[r["industry"]].append(float(r["net_return"]))
            for ind, vals in by.items():
                if len(vals) >= 5:
                    out.append({
                        "recipe": recipe, "holding_days": h, "industry": ind, "trades": len(vals),
                        "avg_net_return": statistics.mean(vals), "median_net_return": statistics.median(vals),
                        "win_rate": sum(1 for v in vals if v > 0) / len(vals),
                    })
    return out


def latest_candidates(th: dict[str, tuple[float, float]], limit: int = 60) -> list[dict[str, Any]]:
    path = PROCESSED / "refined_revenue_candidates.csv"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            avg_turn = fnum(r.get("avg_turnover_20d")) or 0
            ret20 = fnum(r.get("ret_20d"))
            ret60 = fnum(r.get("ret_60d"))
            score = fnum(r.get("refined_signal_score"))
            if avg_turn < LIQ or str(r.get("passes_refined_filter", "")).lower() not in {"true", "1", "yes"}:
                continue
            # Practical current snapshot proxy: avoid very strong 20D runup; prefer 20D <= 10%.
            if ret20 is None or ret20 > 0.10:
                continue
            ytd_yoy = fnum(r.get("revenue_ytd_yoy_pct"))
            rev_mom = fnum(r.get("revenue_mom_pct"))
            rev_yoy = fnum(r.get("revenue_yoy_pct"))
            tags = []
            if ret20 <= th["pre_ret_20d"][0]: tags.append("deep_underreaction")
            if ytd_yoy is not None and ytd_yoy >= 60: tags.append("qtd_yoy_proxy_high")
            if rev_mom is not None and rev_mom >= 10: tags.append("mom_positive")
            rows.append({
                "market": r.get("market"), "stock_id": r.get("stock_id"), "stock_name": r.get("stock_name"), "industry": r.get("industry"),
                "revenue_month": r.get("revenue_month"), "latest_trade_date": r.get("latest_trade_date"), "latest_close": r.get("latest_close"),
                "refined_signal_score": score, "revenue_yoy_pct": rev_yoy, "revenue_mom_pct": rev_mom,
                "revenue_ytd_yoy_pct": ytd_yoy, "ret_20d": ret20, "ret_60d": ret60,
                "avg_turnover_20d": avg_turn, "phase37_tags": ";".join(tags),
            })
    rows.sort(key=lambda r: (r["refined_signal_score"] or -999, r["revenue_ytd_yoy_pct"] or -999, r["revenue_yoy_pct"] or -999), reverse=True)
    return rows[:limit]


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(variants: list[dict[str, Any]], remove_rows: list[dict[str, Any]], latest: list[dict[str, Any]], th: dict[str, tuple[float, float]], counts: dict[str, Any]) -> None:
    def row(recipe: str, h: int) -> dict[str, Any]:
        return next(r for r in variants if r["recipe"] == recipe and int(r["holding_days"]) == h)
    best_by_h = []
    for h in HOLDINGS:
        rows = [r for r in variants if int(r["holding_days"]) == h and r.get("excess_total_return") is not None]
        best_by_h.append(max(rows, key=lambda r: float(r["excess_total_return"])))
    lines = [
        "# Phase 3.7 短線價量濾網研究\n\n",
        "本階段仍是 research-only proxy/cohort backtest，不是實際持倉、paper order 或交易建議。\n\n",
        "## 研究問題\n\n",
        "SUR core 在 20D 較穩，但 10D/15D 需要更多確認。本階段測試：高 QTD YoY、營收加速度、3M SUR、排除過熱 momentum、underreaction 是否改善 10–20D。\n\n",
        "## Thresholds / terciles\n\n",
    ]
    for k, (a, b) in th.items():
        lines.append(f"- `{k}`: low <= {a:.4f}, high >= {b:.4f}\n")
    lines.append("\n## 每個持有期最佳 variant\n\n")
    for r in best_by_h:
        lines.append(f"- {r['holding_days']}D：`{r['recipe']}`，strategy={fmt_pct(r['strategy_total_return'])}，excess={fmt_pct(r['excess_total_return'])}，Sharpe={fmt_num(r['strategy_sharpe'])}，MDD={fmt_pct(r['strategy_mdd'])}，avg positions={float(r['avg_positions']):.1f}\n")
    lines.append("\n## 主要 variants\n\n")
    for recipe in ["base_sur_core", "mom_mid_only", "qtd_high_no_high_mom", "accel_high_no_high_mom", "sur3_high_no_high_mom", "qtd_or_accel_no_high_mom", "qtd_high_no_high_mom_semi2"]:
        lines.append(f"### {recipe}\n")
        for h in HOLDINGS:
            r = row(recipe, h)
            lines.append(f"- {h}D：strategy={fmt_pct(r['strategy_total_return'])}, excess={fmt_pct(r['excess_total_return'])}, Sharpe={fmt_num(r['strategy_sharpe'])}, MDD={fmt_pct(r['strategy_mdd'])}, win={fmt_pct(r['strategy_win_rate'])}, avg positions={float(r['avg_positions']):.1f}\n")
        lines.append("\n")
    lines.append("## Remove top winners：重點 variants\n\n")
    for recipe in ["base_sur_core", "qtd_high_no_high_mom", "accel_high_no_high_mom", "sur3_high_no_high_mom", "qtd_or_accel_no_high_mom"]:
        lines.append(f"### {recipe}\n")
        for h in [10, 20]:
            vals = [r for r in remove_rows if r["recipe"] == recipe and int(r["holding_days"]) == h and int(r["remove_top_winners"]) in {0, 10, 20}]
            for r in vals:
                lines.append(f"- {h}D remove {r['remove_top_winners']}：strategy={fmt_pct(r['strategy_total_return'])}，excess={fmt_pct(r['excess_total_return'])}，MDD={fmt_pct(r['strategy_mdd'])}\n")
        lines.append("\n")
    lines.append("## 最新候選名單：price-action filter proxy Top 20\n\n")
    for r in latest[:20]:
        lines.append(f"- {r['stock_id']} {r['stock_name']}｜{r['industry']}｜score={fmt_num(r['refined_signal_score'])}｜YoY={fmt_pct((r['revenue_yoy_pct'] or 0)/100)}｜YTD YoY={fmt_pct((r['revenue_ytd_yoy_pct'] or 0)/100)}｜20D={fmt_pct(r['ret_20d'])}｜60D={fmt_pct(r['ret_60d'])}｜20D均額={float(r['avg_turnover_20d'])/1e8:.2f}億｜{r['phase37_tags']}\n")
    lines += [
        "\n## 初步解讀\n\n",
        "- 若只看短線，排除過熱 momentum 比單純追高更重要。\n",
        "- 這一輪硬篩 `qtd_high_no_high_mom` / `accel_high_no_high_mom` 沒有勝過 baseline；它們持倉數較少且 remove-winners 後 edge 退化很快。\n",
        "- 目前較有研究價值的是 `sur3_high_no_high_mom`：保留 3M revenue surprise 持續性，同時避免過熱 momentum；它在 10D/15D/20D 都較接近 baseline，20D remove top winners 後仍有正 excess。\n",
        "- 加半導體 cap 可測試是否只是押單一電子景氣循環；若 cap 後明顯衰退，後續不能宣稱跨產業穩健。\n",
        "- 文獻線索：PEAD / revenue surprise / fundamental momentum 支持『基本面 surprise 後的延遲反應』，但 Taiwan monthly revenue 相關研究也提醒公告前權證/交易資訊可能提前反映，且 lottery-like extreme winners 會扭曲短線平均報酬。\n",
        "\n## 輸出檔案\n\n",
        f"- `{OUT_VARIANTS}`\n- `{OUT_YEARLY}`\n- `{OUT_REMOVE}`\n- `{OUT_INDUSTRY}`\n- `{OUT_LATEST}`\n- `{OUT_SUMMARY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    scored, prices_by_stock, date_map, counts = build_scored()
    th = thresholds(scored)

    filters: list[tuple[str, str, Callable[[dict[str, Any], dict[str, tuple[float, float]]], bool], int, int, int | None]] = [
        ("base_sur_core", "score_sur_core", lambda r, t: True, 15, 5, None),
        ("mom_mid_only", "score_sur_core", lambda r, t: t["momentum_120_20"][0] < r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, None),
        ("no_high_mom", "score_sur_core", lambda r, t: r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, None),
        ("underreact_pre_low", "score_sur_core", lambda r, t: r["pre_ret_20d"] <= t["pre_ret_20d"][0], 15, 5, None),
        ("qtd_high_no_high_mom", "score_sur_core", lambda r, t: r["qtd_yoy"] >= t["qtd_yoy"][1] and r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, None),
        ("accel_high_no_high_mom", "score_sur_core", lambda r, t: r["rev_accel_3m"] >= t["rev_accel_3m"][1] and r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, None),
        ("sur3_high_no_high_mom", "score_sur_core", lambda r, t: r["sur_3m"] >= t["sur_3m"][1] and r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, None),
        ("qtd_or_accel_no_high_mom", "score_sur_core", lambda r, t: (r["qtd_yoy"] >= t["qtd_yoy"][1] or r["rev_accel_3m"] >= t["rev_accel_3m"][1]) and r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, None),
        ("qtd_and_accel_no_high_mom", "score_sur_core", lambda r, t: r["qtd_yoy"] >= t["qtd_yoy"][1] and r["rev_accel_3m"] >= t["rev_accel_3m"][1] and r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, None),
        ("qtd_high_no_high_mom_top10", "score_sur_core", lambda r, t: r["qtd_yoy"] >= t["qtd_yoy"][1] and r["momentum_120_20"] <= t["momentum_120_20"][1], 10, 3, None),
        ("qtd_high_no_high_mom_semi2", "score_sur_core", lambda r, t: r["qtd_yoy"] >= t["qtd_yoy"][1] and r["momentum_120_20"] <= t["momentum_120_20"][1], 15, 5, 2),
    ]
    signals: list[dict[str, Any]] = []
    recipes = []
    signal_counts = {}
    for name, score_field, pred, top_n, industry_cap, semi_cap in filters:
        sigs = select_custom(scored, name, score_field, pred, th, top_n=top_n, industry_cap=industry_cap, semiconductor_cap=semi_cap)
        signals.extend(sigs)
        recipes.append(name)
        signal_counts[name] = len(sigs)
    trades = sur.build_trades(signals, prices_by_stock, date_map)
    variants = summarize_variants(trades, recipes)
    yearly = yearly_rows(trades, recipes)
    remove_rows = remove_winners_rows(trades, recipes)
    industries = industry_rows(trades, recipes)
    latest = latest_candidates(th)

    write_csv(OUT_VARIANTS, variants)
    write_csv(OUT_YEARLY, yearly)
    write_csv(OUT_REMOVE, remove_rows)
    write_csv(OUT_INDUSTRY, industries)
    write_csv(OUT_LATEST, latest)
    summary = {"counts": counts, "signal_counts": signal_counts, "thresholds": th, "holdings": HOLDINGS, "cost": COST, "liq": LIQ, "outputs": [str(OUT_VARIANTS), str(OUT_YEARLY), str(OUT_REMOVE), str(OUT_INDUSTRY), str(OUT_LATEST), str(OUT_SUMMARY), str(OUT_REPORT)]}
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(variants, remove_rows, latest, th, {**counts, "signal_counts": signal_counts})
    print(json.dumps({"variants": len(variants), "yearly": len(yearly), "remove": len(remove_rows), "industries": len(industries), "latest": len(latest), "outputs": summary["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
