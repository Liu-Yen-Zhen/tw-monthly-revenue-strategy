#!/usr/bin/env python3
"""Phase 3.5: standardized unexpected revenue (SUR) factor tests.

Research-only. No trading, no deployment, no package installation.

This script tests literature-inspired revenue-surprise features:
- SUR: standardized unexpected revenue from a simple seasonal trend model.
- Industry-adjusted SUR.
- Revenue acceleration.
- Quarter-to-date revenue YoY.
- Price trend / liquidity / abnormal-volume confirmation overlays.

It reuses official/free MOPS monthly revenue and TWSE/TPEx daily market history.
All results are proxy/cohort backtests, not live or paper-trading orders.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
REV_CSV = PROCESSED / "historical_monthly_revenue_mops_static.csv"
PRICE_CSV = PROCESSED / "daily_market_history_2023_present.csv"
OUT_SIGNALS = PROCESSED / "sur_factor_signals.csv"
OUT_TRADES = PROCESSED / "sur_factor_trades.csv"
OUT_SUMMARY = PROCESSED / "sur_factor_summary.json"
OUT_REPORT = REPORTS / "phase3_5_sur_factor_tests_report.md"

COST = 0.007
START_SIGNAL_MONTH = "2023-06"  # needs enough price lookback for 120-20 momentum and abnormal turnover
EXCLUDED_INDUSTRIES = {"金融保險業"}
MIN_CURRENT_REV = 100_000       # thousand TWD = 100m TWD
MIN_LAST_YEAR_REV = 100_000
MIN_AVG_TURNOVER_20D = 50_000_000
HOLDINGS = [20, 40, 60]
TOP_N = 15
INDUSTRY_CAP = 5

RECIPES = {
    "yoy_baseline": {
        "rev_yoy_rank": 0.25,
        "rev_3m_rank": 0.30,
        "rev_accel_rank": 0.15,
        "momentum_120_20_rank": 0.15,
        "liquidity_rank": 0.10,
        "anti_runup20_rank": 0.05,
    },
    "sur_core": {
        "sur_rank": 0.40,
        "sur_3m_rank": 0.20,
        "qtd_yoy_rank": 0.15,
        "rev_accel_rank": 0.15,
        "liquidity_rank": 0.10,
    },
    "industry_adjusted_sur": {
        "ind_adj_sur_rank": 0.35,
        "ind_adj_rev3_rank": 0.25,
        "sur_rank": 0.15,
        "momentum_120_20_rank": 0.15,
        "liquidity_rank": 0.10,
    },
    "sur_trend_liquidity": {
        "sur_rank": 0.25,
        "ind_adj_sur_rank": 0.20,
        "momentum_120_20_rank": 0.25,
        "abnormal_turnover_rank": 0.15,
        "liquidity_rank": 0.10,
        "anti_runup20_rank": 0.05,
    },
    "sur_balanced": {
        "sur_rank": 0.20,
        "ind_adj_sur_rank": 0.20,
        "sur_3m_rank": 0.15,
        "rev_accel_rank": 0.15,
        "momentum_120_20_rank": 0.15,
        "abnormal_turnover_rank": 0.10,
        "anti_runup20_rank": 0.05,
    },
}


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def fnum(x: Any) -> float | None:
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None


def mean(xs: list[float]) -> float | None:
    return statistics.mean(xs) if xs else None


def stdev(xs: list[float]) -> float | None:
    return statistics.stdev(xs) if len(xs) >= 2 else None


def median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def percentile(items: list[tuple[int, float]]) -> dict[int, float]:
    clean = [(i, v) for i, v in items if v is not None and not math.isnan(v)]
    clean.sort(key=lambda x: x[1])
    n = len(clean)
    out = {idx: 0.5 for idx, _ in items}
    if n == 0:
        return out
    for rank, (idx, _v) in enumerate(clean):
        out[idx] = rank / (n - 1) if n > 1 else 1.0
    return out


def month_in_quarter(revenue_month: str) -> int:
    m = int(revenue_month.split("-")[1])
    return (m - 1) % 3 + 1


def build_revenue_panel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_stock: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_stock[(r["market"], r["stock_id"])].append(r)

    panel: list[dict[str, Any]] = []
    for _key, rs in by_stock.items():
        rs = sorted(rs, key=lambda r: r["revenue_month"])
        revs = [fnum(r["revenue_current_month"]) for r in rs]
        yoy = [fnum(r.get("revenue_yoy_pct")) for r in rs]
        model_errors: list[float | None] = [None] * len(rs)
        raw_sur: list[float | None] = [None] * len(rs)

        for i, r in enumerate(rs):
            cur = revs[i]
            if cur is None:
                continue
            r2 = dict(r)

            # 3M cumulative YoY.
            if i >= 14 and all(x is not None for x in revs[i-2:i+1]) and all(x is not None for x in revs[i-14:i-11]):
                recent = sum(float(x) for x in revs[i-2:i+1] if x is not None)
                last = sum(float(x) for x in revs[i-14:i-11] if x is not None)
                r2["rev_3m_yoy"] = recent / last * 100 - 100 if last else None
            else:
                r2["rev_3m_yoy"] = None

            # Previous 3M cumulative YoY, for acceleration.
            if i >= 17 and all(x is not None for x in revs[i-5:i-2]) and all(x is not None for x in revs[i-17:i-14]):
                recent_prev = sum(float(x) for x in revs[i-5:i-2] if x is not None)
                last_prev = sum(float(x) for x in revs[i-17:i-14] if x is not None)
                prev3 = recent_prev / last_prev * 100 - 100 if last_prev else None
            else:
                prev3 = None
            r2["rev_accel_3m"] = (r2["rev_3m_yoy"] - prev3) if (r2["rev_3m_yoy"] is not None and prev3 is not None) else None

            # QTD YoY using months already observed in the quarter.
            qn = month_in_quarter(r["revenue_month"])
            if i >= 12 + qn - 1:
                cur_slice = revs[i-qn+1:i+1]
                last_slice = revs[i-12-qn+1:i-11]
                if len(cur_slice) == qn and len(last_slice) == qn and all(x is not None for x in cur_slice) and all(x is not None for x in last_slice):
                    cur_q = sum(float(x) for x in cur_slice if x is not None)
                    last_q = sum(float(x) for x in last_slice if x is not None)
                    r2["qtd_yoy"] = cur_q / last_q * 100 - 100 if last_q else None
                else:
                    r2["qtd_yoy"] = None
            else:
                r2["qtd_yoy"] = None

            # Simple seasonal-trend expected revenue model:
            # expected_t = revenue_{t-12} * (1 + average prior 3 months YoY / 100)
            rev_lag12 = revs[i-12] if i >= 12 else None
            if i >= 15 and rev_lag12 is not None and rev_lag12 > 0 and all(y is not None for y in yoy[i-3:i]):
                trend = statistics.mean(float(y) / 100 for y in yoy[i-3:i] if y is not None)
                expected = float(rev_lag12) * (1 + trend)
                if expected > 0:
                    err = cur / expected - 1
                    model_errors[i] = err
                    raw_sur[i] = err
                    prev_errs = [e for e in model_errors[max(0, i-24):i] if e is not None]
                    sd = stdev(prev_errs)
                    r2["sur"] = err / sd if sd and sd > 1e-9 else None
                else:
                    r2["sur"] = None
            else:
                r2["sur"] = None
            r2["raw_sur"] = raw_sur[i]

            # 3M average SUR, if recent values available.
            recent_sur = [raw_sur[j] for j in range(max(0, i-2), i+1)]
            prev_errs = [e for e in model_errors[max(0, i-24):i] if e is not None]
            sd = stdev(prev_errs)
            r2["sur_3m"] = statistics.mean(float(x) for x in recent_sur if x is not None) / sd if sd and all(x is not None for x in recent_sur) else None
            panel.append(r2)

    # Add industry-relative fields within each revenue month x industry.
    by_mi: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_m: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in panel:
        by_mi[(r["revenue_month"], r.get("industry", ""))].append(r)
        by_m[r["revenue_month"]].append(r)
    for rows2 in by_mi.values():
        med_sur = median([float(r["sur"]) for r in rows2 if r.get("sur") is not None])
        med_rev3 = median([float(r["rev_3m_yoy"]) for r in rows2 if r.get("rev_3m_yoy") is not None])
        for r in rows2:
            r["ind_adj_sur"] = float(r["sur"]) - med_sur if (r.get("sur") is not None and med_sur is not None) else None
            r["ind_adj_rev3"] = float(r["rev_3m_yoy"]) - med_rev3 if (r.get("rev_3m_yoy") is not None and med_rev3 is not None) else None
    return panel


def build_price_maps(rows: list[dict[str, Any]]):
    by_stock: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    all_dates = set()
    date_map: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    for r in rows:
        close = fnum(r.get("close")); turnover = fnum(r.get("turnover_value"))
        if close is None or turnover is None:
            continue
        key = (r["market"], r["stock_id"])
        rec = {"date": r["trade_date"], "close": close, "turnover": turnover}
        by_stock[key].append(rec)
        all_dates.add(r["trade_date"])
        date_map[r["trade_date"]][key] = close
    for k in list(by_stock):
        by_stock[k].sort(key=lambda x: x["date"])
    return by_stock, sorted(all_dates), date_map


def next_trading_date(dates: list[str], date_iso: str) -> str | None:
    for d in dates:
        if d >= date_iso:
            return d
    return None


def entry_date_for_revenue_month(revenue_month: str, trading_dates: list[str]) -> str | None:
    y, m = map(int, revenue_month.split("-"))
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return next_trading_date(trading_dates, f"{y2:04d}-{m2:02d}-11")


def return_lag(prices: list[dict[str, Any]], idx: int, lag: int) -> float | None:
    if idx - lag < 0:
        return None
    p0 = prices[idx - lag]["close"]; p1 = prices[idx]["close"]
    return p1 / p0 - 1 if p0 else None


def return_between(prices: list[dict[str, Any]], idx: int, start_lag: int, end_lag: int) -> float | None:
    if idx - start_lag < 0 or idx - end_lag < 0 or start_lag <= end_lag:
        return None
    p0 = prices[idx - start_lag]["close"]; p1 = prices[idx - end_lag]["close"]
    return p1 / p0 - 1 if p0 else None


def avg_turnover(prices: list[dict[str, Any]], idx: int, window: int) -> float | None:
    if idx - window < 0:
        return None
    return mean([float(x["turnover"]) for x in prices[idx-window:idx]])


def benchmark_return(date_map: dict[str, dict[tuple[str, str], float]], entry: str, exit_: str) -> float | None:
    a = date_map.get(entry); b = date_map.get(exit_)
    if not a or not b:
        return None
    vals = []
    for k in set(a).intersection(b):
        if a[k] > 0 and b[k] > 0:
            vals.append(b[k] / a[k] - 1 - COST)
    return statistics.mean(vals) if vals else None


def eligible_candidates(rev_rows: list[dict[str, Any]], prices_by_stock: dict, trading_dates: list[str]) -> list[dict[str, Any]]:
    out = []
    for r in rev_rows:
        if r["revenue_month"] < START_SIGNAL_MONTH:
            continue
        if r["market"] not in {"listed", "otc"} or r.get("industry") in EXCLUDED_INDUSTRIES:
            continue
        yoy = fnum(r.get("revenue_yoy_pct")); mom = fnum(r.get("revenue_mom_pct")); ytd = fnum(r.get("revenue_ytd_yoy_pct"))
        cur = fnum(r.get("revenue_current_month")); base = fnum(r.get("revenue_same_month_last_year"))
        rev3 = fnum(r.get("rev_3m_yoy")); sur = fnum(r.get("sur")); sur3 = fnum(r.get("sur_3m"))
        rev_accel = fnum(r.get("rev_accel_3m")); qtd = fnum(r.get("qtd_yoy")); ind_sur = fnum(r.get("ind_adj_sur")); ind_rev3 = fnum(r.get("ind_adj_rev3"))
        if any(x is None for x in [yoy, mom, ytd, cur, base, rev3, sur, sur3, rev_accel, qtd, ind_sur, ind_rev3]):
            continue
        assert yoy is not None and mom is not None and ytd is not None and cur is not None and base is not None and rev3 is not None
        assert sur is not None and sur3 is not None and rev_accel is not None and qtd is not None and ind_sur is not None and ind_rev3 is not None
        yoy = float(yoy); mom = float(mom); ytd = float(ytd); cur = float(cur); base = float(base); rev3 = float(rev3)
        sur = float(sur); sur3 = float(sur3); rev_accel = float(rev_accel); qtd = float(qtd); ind_sur = float(ind_sur); ind_rev3 = float(ind_rev3)
        if cur < MIN_CURRENT_REV or base < MIN_LAST_YEAR_REV or yoy <= 0 or rev3 <= 0 or sur <= -1.0 or mom <= -35 or ytd <= -25:
            continue

        key = (r["market"], r["stock_id"])
        pr = prices_by_stock.get(key)
        if not pr:
            continue
        proxy_entry = entry_date_for_revenue_month(r["revenue_month"], trading_dates)
        if not proxy_entry:
            continue
        entry = next((x["date"] for x in pr if x["date"] >= proxy_entry), None)
        if entry is None:
            continue
        imap = {x["date"]: i for i, x in enumerate(pr)}
        idx = imap.get(entry)
        if idx is None or idx < 121:
            continue
        avg20 = avg_turnover(pr, idx, 20); avg120 = avg_turnover(pr, idx, 120)
        run20 = return_lag(pr, idx, 20); mom60 = return_lag(pr, idx, 60); mom120_20 = return_between(pr, idx, 120, 20)
        if None in {avg20, avg120, run20, mom60, mom120_20}:
            continue
        assert avg20 is not None and avg120 is not None and run20 is not None and mom60 is not None and mom120_20 is not None
        if avg20 < MIN_AVG_TURNOVER_20D or run20 > 0.30 or mom60 > 1.20:
            continue
        out.append({
            "revenue_month": r["revenue_month"], "entry_date": entry, "market": r["market"], "stock_id": r["stock_id"],
            "stock_name": r["stock_name"], "industry": r.get("industry", ""),
            "rev_yoy": yoy, "rev_3m_yoy": rev3, "rev_mom": mom, "ytd_yoy": ytd,
            "sur": sur, "sur_3m": sur3, "ind_adj_sur": ind_sur, "ind_adj_rev3": ind_rev3,
            "rev_accel_3m": rev_accel, "qtd_yoy": qtd,
            "avg_turnover_20d": avg20, "avg_turnover_120d": avg120,
            "abnormal_turnover": avg20 / avg120 if avg120 else None,
            "pre_ret_20d": run20, "pre_ret_60d": mom60, "momentum_120_20": mom120_20,
            "price_idx": idx,
        })
    return out


def add_scores(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cands:
        by_month[c["revenue_month"]].append(c)
    for _month, rows in by_month.items():
        ranks = {
            "rev_yoy_rank": percentile([(i, r["rev_yoy"]) for i, r in enumerate(rows)]),
            "rev_3m_rank": percentile([(i, r["rev_3m_yoy"]) for i, r in enumerate(rows)]),
            "sur_rank": percentile([(i, r["sur"]) for i, r in enumerate(rows)]),
            "sur_3m_rank": percentile([(i, r["sur_3m"]) for i, r in enumerate(rows)]),
            "ind_adj_sur_rank": percentile([(i, r["ind_adj_sur"]) for i, r in enumerate(rows)]),
            "ind_adj_rev3_rank": percentile([(i, r["ind_adj_rev3"]) for i, r in enumerate(rows)]),
            "rev_accel_rank": percentile([(i, r["rev_accel_3m"]) for i, r in enumerate(rows)]),
            "qtd_yoy_rank": percentile([(i, r["qtd_yoy"]) for i, r in enumerate(rows)]),
            "momentum_120_20_rank": percentile([(i, r["momentum_120_20"]) for i, r in enumerate(rows)]),
            "abnormal_turnover_rank": percentile([(i, r["abnormal_turnover"]) for i, r in enumerate(rows)]),
            "liquidity_rank": percentile([(i, math.log1p(r["avg_turnover_20d"])) for i, r in enumerate(rows)]),
            "anti_runup20_rank": percentile([(i, -r["pre_ret_20d"]) for i, r in enumerate(rows)]),
        }
        for i, r in enumerate(rows):
            r2 = dict(r)
            for rank_name, rank_map in ranks.items():
                r2[rank_name] = rank_map[i]
            for recipe, weights in RECIPES.items():
                r2[f"score_{recipe}"] = sum(r2[k] * w for k, w in weights.items())
            out.append(r2)
    return out


def select_signals(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals = []
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        by_month[r["revenue_month"]].append(r)
    for recipe in RECIPES:
        for _month, rows in by_month.items():
            ind_counts: dict[str, int] = defaultdict(int)
            chosen = []
            for r in sorted(rows, key=lambda x: x[f"score_{recipe}"], reverse=True):
                if ind_counts[r["industry"]] >= INDUSTRY_CAP:
                    continue
                r2 = dict(r)
                r2["recipe"] = recipe
                r2["score"] = r[f"score_{recipe}"]
                chosen.append(r2)
                ind_counts[r["industry"]] += 1
                if len(chosen) >= TOP_N:
                    break
            signals.extend(chosen)
    return signals


def build_trades(signals: list[dict[str, Any]], prices_by_stock: dict, date_map: dict[str, dict[tuple[str, str], float]]) -> list[dict[str, Any]]:
    trades = []
    bench_cache = {}
    for s in signals:
        pr = prices_by_stock[(s["market"], s["stock_id"])]
        idx = int(s["price_idx"])
        entry_price = pr[idx]["close"]
        for h in HOLDINGS:
            if idx + h >= len(pr):
                continue
            exit_rec = pr[idx + h]
            bench_key = (s["entry_date"], exit_rec["date"])
            if bench_key not in bench_cache:
                bench_cache[bench_key] = benchmark_return(date_map, *bench_key)
            bench = bench_cache[bench_key]
            if bench is None:
                continue
            gross = exit_rec["close"] / entry_price - 1
            net = gross - COST
            trades.append({
                "recipe": s["recipe"], "revenue_month": s["revenue_month"], "entry_date": s["entry_date"], "holding_days": h,
                "market": s["market"], "stock_id": s["stock_id"], "stock_name": s["stock_name"], "industry": s["industry"],
                "score": round(s["score"], 6),
                "rev_yoy": round(s["rev_yoy"], 4), "rev_3m_yoy": round(s["rev_3m_yoy"], 4),
                "sur": round(s["sur"], 6), "sur_3m": round(s["sur_3m"], 6), "ind_adj_sur": round(s["ind_adj_sur"], 6),
                "rev_accel_3m": round(s["rev_accel_3m"], 4), "qtd_yoy": round(s["qtd_yoy"], 4),
                "momentum_120_20": round(s["momentum_120_20"], 6), "abnormal_turnover": round(s["abnormal_turnover"], 6),
                "pre_ret_20d": round(s["pre_ret_20d"], 6), "avg_turnover_20d": int(s["avg_turnover_20d"]),
                "entry_price": entry_price, "exit_date": exit_rec["date"], "exit_price": exit_rec["close"],
                "gross_return": round(gross, 8), "net_return": round(net, 8), "benchmark_net_return": round(bench, 8), "excess_return": round(net - bench, 8),
            })
    return trades


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
        "months": len(monthly), "total_return": total, "ann_return": (1 + total) ** (12 / len(monthly)) - 1,
        "mean_month": statistics.mean(monthly), "median_month": statistics.median(monthly), "win_rate": sum(1 for x in monthly if x > 0) / len(monthly),
        "sharpe_proxy": statistics.mean(monthly) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(monthly), "best_month": max(monthly), "worst_month": min(monthly),
    }


def summarize(trades: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for recipe in RECIPES:
        summary[recipe] = {}
        for h in HOLDINGS:
            rows = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == h]
            by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for r in rows:
                by_month[r["revenue_month"]].append(r)
            strat = [statistics.mean([float(x["net_return"]) for x in by_month[m]]) for m in sorted(by_month)]
            excess = [statistics.mean([float(x["excess_return"]) for x in by_month[m]]) for m in sorted(by_month)]
            summary[recipe][str(h)] = {
                "strategy": metrics(strat), "excess": metrics(excess),
                "avg_positions": statistics.mean([len(v) for v in by_month.values()]) if by_month else 0,
            }
    return summary


def pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(summary: dict[str, Any], counts: dict[str, Any]) -> None:
    lines = [
        "# Phase 3.5 SUR / 營收 Surprise 因子測試\n\n",
        "本階段把文獻中的 revenue surprise / PEAD 想法落地到台股月營收資料。仍為 proxy/cohort backtest，不是投資建議、實際持倉或交易系統。\n\n",
        "## 方法\n\n",
        "- SUR：`(actual revenue - expected revenue) / historical forecast-error volatility`。\n",
        "- expected revenue：去年同月營收乘上前三個月平均 YoY 趨勢。\n",
        "- Industry-adjusted SUR：公司 SUR 扣同月同產業 median SUR。\n",
        "- 加入 3M SUR、3M revenue acceleration、QTD revenue YoY。\n",
        "- 搭配 120-20D price momentum、20D/120D abnormal turnover、20D runup control、流動性與產業上限。\n",
        "- 每月 Top15，單一產業最多 5 檔，成本 0.7%。\n\n",
        "## 資料與候選數\n\n",
        f"- eligible candidates: {counts['eligible_candidates']}\n",
        f"- signals: {counts['signals']}\n",
        f"- trades: {counts['trades']}\n\n",
        "## 結果摘要\n\n",
    ]
    for recipe, by_h in summary.items():
        lines.append(f"## Recipe: {recipe}\n\n")
        for h in ["20", "40", "60"]:
            s = by_h[h]["strategy"]; e = by_h[h]["excess"]
            lines.append(
                f"- {h}D：strategy={pct(s.get('total_return'))}, excess={pct(e.get('total_return'))}, "
                f"ann={pct(s.get('ann_return'))}, Sharpe={num(s.get('sharpe_proxy'))}, "
                f"MDD={pct(s.get('mdd'))}, win={pct(s.get('win_rate'))}, avg_pos={num(by_h[h]['avg_positions'])}\n"
            )
        lines.append("\n")
    lines.append("## 每個持有期最佳 Excess\n\n")
    for h in ["20", "40", "60"]:
        best = max(summary, key=lambda r: summary[r][h]["excess"].get("total_return", -999))
        s = summary[best][h]["strategy"]; e = summary[best][h]["excess"]
        lines.append(f"- {h}D：{best}，strategy={pct(s.get('total_return'))}，excess={pct(e.get('total_return'))}，MDD={pct(s.get('mdd'))}，Sharpe={num(s.get('sharpe_proxy'))}\n")
    lines += [
        "\n## 解讀方向\n\n",
        "如果 SUR / industry-adjusted SUR 贏過 YoY baseline，代表 surprise normalization 有價值；如果 SUR 輸給 trend/liquidity recipe，代表台股月營收策略更需要市場確認與資金確認。\n",
        "下一步應接著做：不同 expected revenue 模型、SUR winsorization、industry-relative residual momentum，以及籌碼面資料攻關。\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    rev_rows = build_revenue_panel(read_csv(REV_CSV))
    prices_by_stock, trading_dates, date_map = build_price_maps(read_csv(PRICE_CSV))
    cands = eligible_candidates(rev_rows, prices_by_stock, trading_dates)
    scored = add_scores(cands)
    signals = select_signals(scored)
    keep_cols = [
        "recipe", "revenue_month", "entry_date", "market", "stock_id", "stock_name", "industry", "score",
        "rev_yoy", "rev_3m_yoy", "sur", "sur_3m", "ind_adj_sur", "ind_adj_rev3", "rev_accel_3m", "qtd_yoy",
        "momentum_120_20", "abnormal_turnover", "pre_ret_20d", "avg_turnover_20d",
    ]
    write_csv(OUT_SIGNALS, [{k: s[k] for k in keep_cols} for s in signals])
    trades = build_trades(signals, prices_by_stock, date_map)
    write_csv(OUT_TRADES, trades)
    summary = summarize(trades)
    counts = {"eligible_candidates": len(cands), "signals": len(signals), "trades": len(trades)}
    OUT_SUMMARY.write_text(json.dumps({"counts": counts, "summary": summary}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary, counts)
    print(json.dumps({**counts, "outputs": [str(OUT_SIGNALS), str(OUT_TRADES), str(OUT_SUMMARY), str(OUT_REPORT)]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
