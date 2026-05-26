#!/usr/bin/env python3
"""Phase 3.3 multi-factor extensions for Taiwan monthly-revenue strategy.

Research-only. No trading, no deployment, no package installation.

Goal: test whether adding non-fundamental factors improves the monthly-revenue strategy:
- price momentum / trend confirmation
- short-term run-up control
- volatility control
- liquidity / turnover strength
- industry cap

This rebuilds the eligible signal universe from historical revenue + official price history, then compares factor recipes.
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
OUT_SIGNALS = PROCESSED / "multifactor_signals.csv"
OUT_TRADES = PROCESSED / "multifactor_trades.csv"
OUT_SUMMARY = PROCESSED / "multifactor_summary.json"
OUT_REPORT = REPORTS / "phase3_3_multifactor_extension_report.md"

COST = 0.007
START_SIGNAL_MONTH = "2023-01"
EXCLUDED_INDUSTRIES = {"金融保險業"}
MIN_CURRENT_REV = 100_000
MIN_LAST_YEAR_REV = 100_000
MIN_AVG_TURNOVER_20D = 50_000_000
HOLDINGS = [20, 40, 60]
TOP_N = 15
INDUSTRY_CAP = 5  # for Top15, roughly 33% max per industry

RECIPES = {
    "fundamental_only": {
        "rev_yoy_rank": 0.25,
        "rev_3m_rank": 0.35,
        "mom_rank": 0.15,
        "liquidity_rank": 0.10,
        "anti_runup20_rank": 0.15,
    },
    "trend_confirmed": {
        "rev_yoy_rank": 0.18,
        "rev_3m_rank": 0.27,
        "mom_rank": 0.10,
        "momentum60_rank": 0.25,
        "anti_runup20_rank": 0.10,
        "liquidity_rank": 0.10,
    },
    "risk_controlled": {
        "rev_yoy_rank": 0.20,
        "rev_3m_rank": 0.30,
        "mom_rank": 0.10,
        "low_vol60_rank": 0.20,
        "anti_runup20_rank": 0.10,
        "liquidity_rank": 0.10,
    },
    "liquidity_momentum": {
        "rev_3m_rank": 0.30,
        "momentum60_rank": 0.25,
        "liquidity_rank": 0.25,
        "low_vol60_rank": 0.10,
        "anti_runup20_rank": 0.10,
    },
    "quality_trend_risk": {
        "rev_yoy_rank": 0.15,
        "rev_3m_rank": 0.25,
        "mom_rank": 0.10,
        "momentum60_rank": 0.20,
        "low_vol60_rank": 0.15,
        "liquidity_rank": 0.10,
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


def percentile(items: list[tuple[int, float]]) -> dict[int, float]:
    items = sorted(items, key=lambda x: x[1])
    n = len(items)
    return {idx: (i / (n - 1) if n > 1 else 1.0) for i, (idx, _v) in enumerate(items)}


def build_revenue_panel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_stock: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_stock[(r["market"], r["stock_id"])].append(r)
    out = []
    for _key, rs in by_stock.items():
        rs = sorted(rs, key=lambda r: r["revenue_month"])
        revs = [fnum(r["revenue_current_month"]) for r in rs]
        for i, r in enumerate(rs):
            cur = revs[i]
            if cur is None:
                continue
            r2 = dict(r)
            if i >= 14 and all(x is not None for x in revs[i-2:i+1]) and all(x is not None for x in revs[i-14:i-11]):
                recent = sum(float(x) for x in revs[i-2:i+1] if x is not None)
                last = sum(float(x) for x in revs[i-14:i-11] if x is not None)
                r2["rev_3m_yoy"] = recent / last * 100 - 100 if last else None
            else:
                r2["rev_3m_yoy"] = None
            out.append(r2)
    return out


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
    if m == 12:
        y2, m2 = y + 1, 1
    else:
        y2, m2 = y, m + 1
    return next_trading_date(trading_dates, f"{y2:04d}-{m2:02d}-11")


def return_lag(prices: list[dict[str, Any]], idx: int, lag: int) -> float | None:
    if idx - lag < 0:
        return None
    p0 = prices[idx - lag]["close"]; p1 = prices[idx]["close"]
    return p1 / p0 - 1 if p0 else None


def volatility(prices: list[dict[str, Any]], idx: int, window: int) -> float | None:
    if idx - window < 1:
        return None
    rets = []
    for j in range(idx - window + 1, idx + 1):
        p0 = prices[j - 1]["close"]; p1 = prices[j]["close"]
        if p0:
            rets.append(p1 / p0 - 1)
    return stdev(rets)


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
        cur = fnum(r.get("revenue_current_month")); base = fnum(r.get("revenue_same_month_last_year")); rev3 = fnum(r.get("rev_3m_yoy"))
        if None in {yoy, mom, cur, base, rev3}:
            continue
        assert yoy is not None and mom is not None and ytd is not None and cur is not None and base is not None and rev3 is not None
        if cur < MIN_CURRENT_REV or base < MIN_LAST_YEAR_REV or yoy <= 0 or rev3 <= 0 or mom <= -30 or ytd <= -20:
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
        if idx is None or idx < 61:
            continue
        avg_turn20 = mean([x["turnover"] for x in pr[idx-20:idx]])
        mom20 = return_lag(pr, idx, 20); mom60 = return_lag(pr, idx, 60)
        vol20 = volatility(pr, idx, 20); vol60 = volatility(pr, idx, 60)
        if None in {avg_turn20, mom20, mom60, vol20, vol60}:
            continue
        assert avg_turn20 is not None and mom20 is not None and mom60 is not None and vol20 is not None and vol60 is not None
        if avg_turn20 < MIN_AVG_TURNOVER_20D or mom20 > 0.30 or mom60 > 1.00:
            continue
        out.append({
            "revenue_month": r["revenue_month"], "entry_date": entry, "market": r["market"], "stock_id": r["stock_id"],
            "stock_name": r["stock_name"], "industry": r.get("industry", ""),
            "rev_yoy": yoy, "rev_3m_yoy": rev3, "rev_mom": mom, "ytd_yoy": ytd,
            "avg_turnover_20d": avg_turn20, "pre_ret_20d": mom20, "pre_ret_60d": mom60,
            "vol20": vol20, "vol60": vol60, "price_idx": idx,
        })
    return out


def add_scores(cands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in cands:
        by_month[c["revenue_month"]].append(c)
    for month, rows in by_month.items():
        ranks = {
            "rev_yoy_rank": percentile([(i, r["rev_yoy"]) for i, r in enumerate(rows)]),
            "rev_3m_rank": percentile([(i, r["rev_3m_yoy"]) for i, r in enumerate(rows)]),
            "mom_rank": percentile([(i, r["rev_mom"]) for i, r in enumerate(rows)]),
            "liquidity_rank": percentile([(i, math.log1p(r["avg_turnover_20d"])) for i, r in enumerate(rows)]),
            "anti_runup20_rank": percentile([(i, -r["pre_ret_20d"]) for i, r in enumerate(rows)]),
            "momentum60_rank": percentile([(i, r["pre_ret_60d"]) for i, r in enumerate(rows)]),
            "low_vol60_rank": percentile([(i, -r["vol60"]) for i, r in enumerate(rows)]),
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
    for recipe in RECIPES:
        by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in scored:
            by_month[r["revenue_month"]].append(r)
        for month, rows in by_month.items():
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
                "score": round(s["score"], 6), "rev_yoy": round(s["rev_yoy"], 4), "rev_3m_yoy": round(s["rev_3m_yoy"], 4),
                "pre_ret_20d": round(s["pre_ret_20d"], 6), "pre_ret_60d": round(s["pre_ret_60d"], 6), "vol60": round(s["vol60"], 8),
                "avg_turnover_20d": int(s["avg_turnover_20d"]), "entry_price": entry_price, "exit_date": exit_rec["date"], "exit_price": exit_rec["close"],
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
            summary[recipe][str(h)] = {"strategy": metrics(strat), "excess": metrics(excess), "avg_positions": statistics.mean([len(v) for v in by_month.values()]) if by_month else 0}
    return summary


def pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# Phase 3.3 多因子擴充測試\n\n",
        "這次在月營收基本面訊號之外，加入技術面、流動性與風險因子。仍為 proxy/cohort backtest，不是投資建議或正式交易系統。\n\n",
        "## 測試的非基本面因子\n\n",
        "- 60D 價格動能：趨勢確認。\n",
        "- 20D 前置漲幅反向排序：避免短期過熱。\n",
        "- 60D 波動度反向排序：偏好較穩定標的。\n",
        "- 20D 平均成交金額：流動性與市場關注。\n",
        "- 產業上限：Top15 中單一產業最多 5 檔。\n\n",
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
    # best by excess total for each holding
    lines.append("## 每個持有期的最佳 Excess\n\n")
    for h in ["20", "40", "60"]:
        best = max(summary, key=lambda r: summary[r][str(h)]["excess"].get("total_return", -999))
        e = summary[best][str(h)]["excess"]; s = summary[best][str(h)]["strategy"]
        lines.append(f"- {h}D：{best}，strategy={pct(s.get('total_return'))}，excess={pct(e.get('total_return'))}，MDD={pct(s.get('mdd'))}，Sharpe={num(s.get('sharpe_proxy'))}\n")
    lines += [
        "\n## 解讀\n\n",
        "若加入趨勢/流動性/風險因子後，excess 與 MDD 改善，代表策略不應只依賴基本面營收排名；如果結果變差，代表月營收訊號本身較重要，其他因子只適合當風控而非排序主軸。\n",
        "下一階段可加入籌碼面：外資/投信買賣超、融資融券、借券與集保分散，測試營收改善是否需要資金確認。\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    rev_rows = build_revenue_panel(read_csv(REV_CSV))
    prices_by_stock, trading_dates, date_map = build_price_maps(read_csv(PRICE_CSV))
    cands = eligible_candidates(rev_rows, prices_by_stock, trading_dates)
    scored = add_scores(cands)
    signals = select_signals(scored)
    signal_rows = []
    keep_cols = ["recipe", "revenue_month", "entry_date", "market", "stock_id", "stock_name", "industry", "score", "rev_yoy", "rev_3m_yoy", "rev_mom", "pre_ret_20d", "pre_ret_60d", "vol60", "avg_turnover_20d"]
    for s in signals:
        signal_rows.append({k: s[k] for k in keep_cols})
    write_csv(OUT_SIGNALS, signal_rows)
    trades = build_trades(signals, prices_by_stock, date_map)
    write_csv(OUT_TRADES, trades)
    summary = summarize(trades)
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary)
    print(json.dumps({"eligible_candidates": len(cands), "signals": len(signals), "trades": len(trades), "outputs": [str(OUT_SIGNALS), str(OUT_TRADES), str(OUT_SUMMARY), str(OUT_REPORT)]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
