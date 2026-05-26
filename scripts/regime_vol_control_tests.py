#!/usr/bin/env python3
"""Phase 3.10: regime filters + volatility control for high-Sharpe SUR strategy.

Research-only. No live orders, no deployment, no broker/API use.

Starting point: best Phase 3.9 high-Sharpe candidate that did not quite reach
Sharpe > 2.5:

    sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | no semicap
    exit_rule=sl8_trail12 | max_holding_days=20

This script tests whether simple, causal, ex-ante market/sector regime filters and
portfolio exposure scaling can push the strategy above Sharpe 2.5 without becoming
obviously overfit. Skipped regime months are counted as 0% cash returns so Sharpe
is not inflated by dropping bad months from the sample.

Important caveats:
- Close-price proxy only; no OHLC/order-book/limit-up-down execution simulation.
- Market/sector regime proxies are equal-weight baskets from available TWSE/TPEx
  historical close data, not production-grade indexes.
- Short 2023-2025 sample; results are hypotheses for further validation.
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
OUT_RESULTS = PROCESSED / "regime_vol_control_results.csv"
OUT_MONTHLY = PROCESSED / "regime_vol_control_monthly.csv"
OUT_REMOVE = PROCESSED / "regime_vol_control_remove_winners.csv"
OUT_SUMMARY = PROCESSED / "regime_vol_control_summary.json"
OUT_REPORT = REPORTS / "phase3_10_regime_vol_control_report.md"

EX_PATH = ROOT / "scripts" / "execution_realism_tests.py"
spec = importlib.util.spec_from_file_location("execution_realism_tests", EX_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {EX_PATH}")
ex = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(ex)

# Baseline candidate from Phase 3.9.
BASE_LIQ = 50_000_000
BASE_RECIPE = "sur3_high_no_high_mom"
BASE_TOP_N = 8
BASE_INDUSTRY_CAP = 3
BASE_SEMI_CAP = None
BASE_RULE = "sl8_trail12"
BASE_MAX_H = 20


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
    nav = 1.0
    peak = 1.0
    worst = 0.0
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
        "months": len(rs),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(rs)) - 1,
        "mean_month": statistics.mean(rs),
        "median_month": statistics.median(rs),
        "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd and sd > 1e-12 else None,
        "mdd": mdd(rs),
        "win_rate": sum(1 for x in rs if x > 0) / len(rs),
        "worst_month": min(rs),
        "best_month": max(rs),
    }


def percentile(vals: list[float], p: float) -> float | None:
    vals = sorted(vals)
    if not vals:
        return None
    i = (len(vals) - 1) * p
    lo, hi = math.floor(i), math.ceil(i)
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - i) + vals[hi] * (i - lo)


def build_daily_regime_series(scored: list[dict[str, Any]], date_map: dict[str, dict[tuple[str, str], float]]) -> dict[str, dict[str, float]]:
    """Build equal-weight daily market and electronic/semiconductor basket features.

    Returns map date -> features known by that date. Feature values used for an
    entry on date D are computed up to the previous trading day.
    """
    industry_by_key: dict[tuple[str, str], str] = {}
    for r in scored:
        industry_by_key[(r["market"], r["stock_id"])] = r["industry"]
    elec_keys = {k for k, ind in industry_by_key.items() if ("電子" in ind or "半導體" in ind or "資訊" in ind)}
    semi_keys = {k for k, ind in industry_by_key.items() if ind == "半導體業"}

    dates = sorted(date_map)
    market_ret: list[float] = [0.0]
    elec_ret: list[float] = [0.0]
    semi_ret: list[float] = [0.0]
    for i in range(1, len(dates)):
        prev = date_map[dates[i - 1]]
        cur = date_map[dates[i]]
        keys = set(prev).intersection(cur)
        def avg_ret(subset: set[tuple[str, str]] | None = None) -> float:
            use = keys if subset is None else keys.intersection(subset)
            vals = [cur[k] / prev[k] - 1 for k in use if prev[k] > 0 and cur[k] > 0]
            return statistics.mean(vals) if vals else 0.0
        market_ret.append(avg_ret(None))
        elec_ret.append(avg_ret(elec_keys))
        semi_ret.append(avg_ret(semi_keys))

    def levels(rets: list[float]) -> list[float]:
        out = [1.0]
        for r in rets[1:]:
            out.append(out[-1] * (1 + r))
        return out
    mkt_lv, elec_lv, semi_lv = levels(market_ret), levels(elec_ret), levels(semi_ret)

    out: dict[str, dict[str, float]] = {}
    vol20_history: list[float] = []
    for i, d in enumerate(dates):
        # For entry on d, use information through i-1.
        end = i - 1
        feat: dict[str, float] = {}
        if end >= 0:
            for w in [20, 60, 120]:
                if end - w >= 0:
                    feat[f"mkt_ret_{w}"] = mkt_lv[end] / mkt_lv[end - w] - 1
                    feat[f"elec_ret_{w}"] = elec_lv[end] / elec_lv[end - w] - 1
                    feat[f"semi_ret_{w}"] = semi_lv[end] / semi_lv[end - w] - 1
                    feat[f"elec_rel_{w}"] = feat[f"elec_ret_{w}"] - feat[f"mkt_ret_{w}"]
                    feat[f"semi_rel_{w}"] = feat[f"semi_ret_{w}"] - feat[f"mkt_ret_{w}"]
            if end - 19 >= 0:
                vol20 = statistics.stdev(market_ret[end - 19:end + 1]) * math.sqrt(252)
                feat["mkt_vol20_ann"] = vol20
                if len(vol20_history) >= 20:
                    med = percentile(vol20_history, 0.50)
                    p75 = percentile(vol20_history, 0.75)
                    p66 = percentile(vol20_history, 0.66)
                    if med is not None:
                        feat["vol20_hist_median"] = med
                    if p75 is not None:
                        feat["vol20_hist_p75"] = p75
                    if p66 is not None:
                        feat["vol20_hist_p66"] = p66
                vol20_history.append(vol20)
        out[d] = feat
    return out


def regime_pass(name: str, feat: dict[str, float]) -> bool:
    if name == "all_months":
        return True
    if name == "mkt60_pos":
        return feat.get("mkt_ret_60", -999) > 0
    if name == "mkt20_or_60_pos":
        return feat.get("mkt_ret_20", -999) > 0 or feat.get("mkt_ret_60", -999) > 0
    if name == "mkt60_pos_and_elec_rel60_pos":
        return feat.get("mkt_ret_60", -999) > 0 and feat.get("elec_rel_60", -999) > 0
    if name == "mkt60_pos_and_semi_rel60_pos":
        return feat.get("mkt_ret_60", -999) > 0 and feat.get("semi_rel_60", -999) > 0
    if name == "not_high_vol_p75":
        return feat.get("mkt_vol20_ann", 999) <= feat.get("vol20_hist_p75", -999)
    if name == "mkt60_pos_not_high_vol_p75":
        return feat.get("mkt_ret_60", -999) > 0 and feat.get("mkt_vol20_ann", 999) <= feat.get("vol20_hist_p75", -999)
    if name == "mkt60_pos_not_high_vol_p66":
        return feat.get("mkt_ret_60", -999) > 0 and feat.get("mkt_vol20_ann", 999) <= feat.get("vol20_hist_p66", -999)
    if name == "mkt20_or_60_pos_not_high_vol_p75":
        return (feat.get("mkt_ret_20", -999) > 0 or feat.get("mkt_ret_60", -999) > 0) and feat.get("mkt_vol20_ann", 999) <= feat.get("vol20_hist_p75", -999)
    if name == "elec_rel60_pos_not_high_vol_p75":
        return feat.get("elec_rel_60", -999) > 0 and feat.get("mkt_vol20_ann", 999) <= feat.get("vol20_hist_p75", -999)
    raise ValueError(name)


def exposure_series(monthly_base: list[float], regime_active: list[bool], mode: str) -> list[float]:
    exp: list[float] = []
    realized: list[float] = []
    for i, active in enumerate(regime_active):
        if not active:
            e = 0.0
        elif mode == "full":
            e = 1.0
        elif mode == "half_when_prev_loss":
            e = 0.5 if i >= 1 and realized[-1] < 0 else 1.0
        elif mode == "dd_degear_5pct":
            nav = 1.0
            peak = 1.0
            for r in realized:
                nav *= 1 + r
                peak = max(peak, nav)
            dd = nav / peak - 1 if peak else 0.0
            e = 0.5 if dd < -0.05 else 1.0
        elif mode.startswith("targetvol"):
            # targetvol_4_cap1, targetvol_5_cap15, etc. Monthly-vol target, using prior 6 realized months.
            parts = mode.split("_")
            target = float(parts[1]) / 100.0
            cap_token = parts[2].replace("cap", "")
            cap = float(cap_token) / 10.0 if cap_token in {"15", "20"} else float(cap_token)
            hist = realized[max(0, len(realized) - 6):]
            if len(hist) >= 3:
                sd = statistics.stdev(hist)
                e = min(cap, max(0.25, target / sd)) if sd > 1e-12 else 1.0
            else:
                e = 1.0
        else:
            raise ValueError(mode)
        exp.append(e)
        realized.append(e * monthly_base[i])
    return exp


def build_base_trades() -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    scored, prices_by_stock, date_map, th = ex.build_universe(BASE_LIQ)
    sigs = ex.select_signals(scored, th, BASE_RECIPE, top_n=BASE_TOP_N, industry_cap=BASE_INDUSTRY_CAP, semiconductor_cap=BASE_SEMI_CAP)
    trades = ex.build_rule_trades(sigs, prices_by_stock, date_map, "phase3_10_base", [BASE_RULE], [BASE_MAX_H])
    regime = build_daily_regime_series(scored, date_map)
    return trades, regime


def monthly_from_trades(trades: list[dict[str, Any]], all_months: list[str], active_months: set[str] | None = None, remove_keys: set[tuple[str, str, str]] | None = None) -> tuple[list[float], list[int]]:
    by_month: dict[str, list[float]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    for r in trades:
        m = r["revenue_month"]
        if active_months is not None and m not in active_months:
            continue
        key = (r["revenue_month"], r["stock_id"], r["entry_date"])
        if remove_keys is not None and key in remove_keys:
            continue
        by_month[m].append(float(r["net_return"]))
        counts[m] += 1
    returns = [statistics.mean(by_month[m]) if by_month[m] else 0.0 for m in all_months]
    pos_counts = [counts[m] for m in all_months]
    return returns, pos_counts


def evaluate_variant(trades: list[dict[str, Any]], regime_map: dict[str, dict[str, float]], regime_name: str, exposure_mode: str, all_months: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[float], list[bool], list[float]]:
    # Decide active months by ex-ante regime at that month's entry date. All trades in this candidate share entry_date per revenue month.
    entry_by_month = {r["revenue_month"]: r["entry_date"] for r in trades}
    active_months: set[str] = set()
    active_flags: list[bool] = []
    for m in all_months:
        feat = regime_map.get(entry_by_month[m], {})
        active = regime_pass(regime_name, feat)
        active_flags.append(active)
        if active:
            active_months.add(m)
    base_rs, pos_counts = monthly_from_trades(trades, all_months, active_months)
    exp = exposure_series(base_rs, active_flags, exposure_mode)
    rs = [r * e for r, e in zip(base_rs, exp)]
    sm = metrics(rs)
    # Split by entry-date year, consistent with Phase 3.9. Revenue month 2024-11 can enter in 2024,
    # while 2024-12 enters in 2025; using revenue-month year would blur OOS diagnostics.
    train = metrics([r for m, r in zip(all_months, rs) if entry_by_month[m][:4] in {"2023", "2024"}])
    test = metrics([r for m, r in zip(all_months, rs) if entry_by_month[m][:4] == "2025"])
    active_count = sum(active_flags)
    row = {
        "variant": f"{regime_name}|{exposure_mode}",
        "regime": regime_name,
        "exposure_mode": exposure_mode,
        "months": sm.get("months"),
        "active_months": active_count,
        "active_ratio": active_count / len(all_months),
        "avg_positions_all_months": sum(pos_counts) / len(pos_counts),
        "avg_positions_active_months": (sum(pos_counts) / active_count if active_count else 0),
        "avg_exposure": statistics.mean(exp),
        "max_exposure": max(exp) if exp else 0,
        "total_return": sm.get("total_return"),
        "ann_return": sm.get("ann_return"),
        "sharpe": sm.get("sharpe"),
        "mdd": sm.get("mdd"),
        "win_rate": sm.get("win_rate"),
        "worst_month": sm.get("worst_month"),
        "train_sharpe": train.get("sharpe"),
        "train_return": train.get("total_return"),
        "test_sharpe": test.get("sharpe"),
        "test_return": test.get("total_return"),
    }
    monthly_rows = []
    for m, r, b, a, e, c in zip(all_months, rs, base_rs, active_flags, exp, pos_counts):
        monthly_rows.append({"variant": row["variant"], "revenue_month": m, "active": a, "exposure": e, "base_month_return_after_regime": b, "scaled_month_return": r, "positions": c, "entry_date": entry_by_month[m]})
    return row, monthly_rows, rs, active_flags, exp


def remove_winners_for_variant(trades: list[dict[str, Any]], regime_map: dict[str, dict[str, float]], regime: str, exposure_mode: str, all_months: list[str]) -> list[dict[str, Any]]:
    out = []
    sorted_rows = sorted(trades, key=lambda r: float(r["net_return"]), reverse=True)
    for n in [0, 5, 10, 20]:
        keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:n]}
        # Rebuild with removed trades but same regime/exposure logic. Exposure uses post-removal monthly stream.
        entry_by_month = {r["revenue_month"]: r["entry_date"] for r in trades}
        active_flags = [regime_pass(regime, regime_map.get(entry_by_month[m], {})) for m in all_months]
        active_months = {m for m, a in zip(all_months, active_flags) if a}
        base_rs, pos_counts = monthly_from_trades(trades, all_months, active_months, keys)
        exp = exposure_series(base_rs, active_flags, exposure_mode)
        rs = [r * e for r, e in zip(base_rs, exp)]
        sm = metrics(rs)
        out.append({
            "variant": f"{regime}|{exposure_mode}",
            "remove_top_winners": n,
            "trades_left": sum(pos_counts),
            "total_return": sm.get("total_return"),
            "sharpe": sm.get("sharpe"),
            "mdd": sm.get("mdd"),
            "win_rate": sm.get("win_rate"),
        })
    return out


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(rows: list[dict[str, Any]], remove_rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    baseline = next(r for r in rows if r["variant"] == "all_months|full")
    best = rows[0]
    candidates = [r for r in rows if r.get("sharpe") is not None and float(r["sharpe"]) >= 2.5]
    robust_candidates = [r for r in candidates if (r.get("train_sharpe") is not None and float(r["train_sharpe"]) >= 1.5 and r.get("test_return") is not None and float(r["test_return"]) > 0 and float(r.get("active_ratio") or 0) >= 0.5 and float(r.get("avg_positions_active_months") or 0) >= 5)]
    lines = [
        "# Phase 3.10 Regime filter + volatility control\n\n",
        "目標：以 Phase 3.9 最佳候選為基準，測試簡單 ex-ante regime filter 與 portfolio exposure control 是否能把 monthly Sharpe proxy 穩健推到 >2.5。仍是 research-only proxy backtest，不是交易建議。\n\n",
        "## Baseline\n\n",
        f"- variant: `{baseline['variant']}`\n",
        f"- return={fmt_pct(baseline['total_return'])}, ann={fmt_pct(baseline['ann_return'])}, Sharpe={fmt_num(baseline['sharpe'])}, MDD={fmt_pct(baseline['mdd'])}, win={fmt_pct(baseline['win_rate'])}\n",
        f"- train Sharpe={fmt_num(baseline['train_sharpe'])}, 2025 test Sharpe={fmt_num(baseline['test_sharpe'])}\n\n",
        "## Search result\n\n",
        f"- tested variants: {len(rows)}\n",
        f"- raw Sharpe > 2.5 variants: {len(candidates)}\n",
        f"- stricter robust candidates: {len(robust_candidates)}\n",
        f"- best variant: `{best['variant']}` with Sharpe={fmt_num(best['sharpe'])}, return={fmt_pct(best['total_return'])}, MDD={fmt_pct(best['mdd'])}\n\n",
        "## Top 20 variants\n\n",
    ]
    for r in rows[:20]:
        lines.append(f"- Sharpe={fmt_num(r['sharpe'])}, return={fmt_pct(r['total_return'])}, MDD={fmt_pct(r['mdd'])}, active={r['active_months']}/{r['months']}, avgExp={fmt_num(r['avg_exposure'])}, maxExp={fmt_num(r['max_exposure'])}, trainS={fmt_num(r['train_sharpe'])}, testS={fmt_num(r['test_sharpe'])}｜`{r['variant']}`\n")
    lines.append("\n## Strict robust candidates\n\n")
    if not robust_candidates:
        lines.append("- 沒有通過較嚴格條件的 robust Sharpe > 2.5 候選。\n")
    for r in robust_candidates[:20]:
        lines.append(f"- Sharpe={fmt_num(r['sharpe'])}, return={fmt_pct(r['total_return'])}, MDD={fmt_pct(r['mdd'])}, active={r['active_months']}/{r['months']}, avg positions active={fmt_num(r['avg_positions_active_months'])}, trainS={fmt_num(r['train_sharpe'])}, testS={fmt_num(r['test_sharpe'])}｜`{r['variant']}`\n")
    if candidates:
        best_c = candidates[0]
        lines.append("\n## Best Sharpe>2.5 remove-winners\n\n")
        for r in [x for x in remove_rows if x["variant"] == best_c["variant"]]:
            lines.append(f"- remove {r['remove_top_winners']}：return={fmt_pct(r['total_return'])}, Sharpe={fmt_num(r['sharpe'])}, MDD={fmt_pct(r['mdd'])}\n")
    lines += [
        "\n## Interpretation rules\n\n",
        "- regime filter 跳過月份以 0% cash return 計入，避免只計 active months 而高估 Sharpe。\n",
        "- 若 Sharpe >2.5 只由低 active_ratio 或高 leverage cap 產生，不能視為穩健達標。\n",
        "- target-vol 使用歷史已實現策略月報酬，屬 portfolio-level exposure proxy；不是實際融資或槓桿交易建議。\n",
        "- 下一步若有候選，仍需 walk-forward、成本加倍、no-electronics/no-semiconductor stress、OHLC/漲跌停可成交性檢查。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_RESULTS}`\n- `{OUT_MONTHLY}`\n- `{OUT_REMOVE}`\n- `{OUT_SUMMARY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    trades, regime_map = build_base_trades()
    all_months = sorted({r["revenue_month"] for r in trades})
    regimes = [
        "all_months",
        "mkt60_pos",
        "mkt20_or_60_pos",
        "mkt60_pos_and_elec_rel60_pos",
        "mkt60_pos_and_semi_rel60_pos",
        "not_high_vol_p75",
        "mkt60_pos_not_high_vol_p75",
        "mkt60_pos_not_high_vol_p66",
        "mkt20_or_60_pos_not_high_vol_p75",
        "elec_rel60_pos_not_high_vol_p75",
    ]
    exposure_modes = [
        "full",
        "half_when_prev_loss",
        "dd_degear_5pct",
        "targetvol_3_cap1",
        "targetvol_4_cap1",
        "targetvol_5_cap1",
        "targetvol_4_cap15",
        "targetvol_5_cap15",
        "targetvol_6_cap15",
    ]
    rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    series_by_variant: dict[str, list[float]] = {}
    for reg in regimes:
        for mode in exposure_modes:
            row, mrows, rs, _active, _exp = evaluate_variant(trades, regime_map, reg, mode, all_months)
            rows.append(row)
            monthly_rows.extend(mrows)
            series_by_variant[row["variant"]] = rs
    rows.sort(key=lambda r: (r["sharpe"] if r["sharpe"] is not None else -999), reverse=True)

    # Remove-winner diagnostics for baseline, top 5 variants, and all variants with Sharpe>=2.5.
    selected_variants = {"all_months|full"}
    selected_variants.update(r["variant"] for r in rows[:5])
    selected_variants.update(r["variant"] for r in rows if r.get("sharpe") is not None and float(r["sharpe"]) >= 2.5)
    remove_rows: list[dict[str, Any]] = []
    for v in sorted(selected_variants):
        reg, mode = v.split("|", 1)
        remove_rows.extend(remove_winners_for_variant(trades, regime_map, reg, mode, all_months))

    write_csv(OUT_RESULTS, rows)
    write_csv(OUT_MONTHLY, monthly_rows)
    write_csv(OUT_REMOVE, remove_rows)
    robust_candidates = [r for r in rows if r.get("sharpe") is not None and float(r["sharpe"]) >= 2.5 and r.get("train_sharpe") is not None and float(r["train_sharpe"]) >= 1.5 and r.get("test_return") is not None and float(r["test_return"]) > 0 and float(r.get("active_ratio") or 0) >= 0.5 and float(r.get("avg_positions_active_months") or 0) >= 5]
    summary = {
        "base_config": {
            "liq": BASE_LIQ,
            "recipe": BASE_RECIPE,
            "top_n": BASE_TOP_N,
            "industry_cap": BASE_INDUSTRY_CAP,
            "semiconductor_cap": BASE_SEMI_CAP,
            "exit_rule": BASE_RULE,
            "max_holding_days": BASE_MAX_H,
        },
        "months": len(all_months),
        "trades": len(trades),
        "tested_variants": len(rows),
        "sharpe_gt_2_5": sum(1 for r in rows if r.get("sharpe") is not None and float(r["sharpe"]) >= 2.5),
        "robust_candidates": len(robust_candidates),
        "best": rows[0] if rows else None,
        "outputs": [str(OUT_RESULTS), str(OUT_MONTHLY), str(OUT_REMOVE), str(OUT_SUMMARY), str(OUT_REPORT)],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(rows, remove_rows, summary)
    print(json.dumps({"tested_variants": len(rows), "sharpe_gt_2_5": summary["sharpe_gt_2_5"], "robust_candidates": len(robust_candidates), "best_sharpe": rows[0].get("sharpe") if rows else None, "best_variant": rows[0].get("variant") if rows else None, "outputs": summary["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
