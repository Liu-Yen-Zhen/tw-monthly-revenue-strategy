#!/usr/bin/env python3
"""Exploratory proxy backtest for Taiwan monthly revenue momentum.

This is NOT a production backtest. It uses:
- MOPS static monthly revenue summaries without per-company announcement timestamps.
- Conservative proxy usable date = next month 11th mapped to next trading day.
- Official unadjusted exchange close prices, so dividends/corporate actions are not fully handled.

Purpose: quickly test whether cleaned monthly-revenue signals have enough directional signal to justify deeper work.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
REV_CSV = PROCESSED_DIR / "historical_monthly_revenue_mops_static.csv"
PRICE_CSV = PROCESSED_DIR / "daily_market_history_2023_present.csv"
TRADES_CSV = PROCESSED_DIR / "proxy_backtest_trades.csv"
SUMMARY_JSON = PROCESSED_DIR / "proxy_backtest_summary.json"
REPORT_MD = REPORT_DIR / "phase2_5_proxy_backtest_report.md"

EXCLUDED_INDUSTRIES = {"金融保險業"}
MIN_CURRENT_REV = 100_000
MIN_LAST_YEAR_REV = 100_000
MIN_AVG_TURNOVER_20D = 50_000_000
MAX_PRE_RET_20D = 0.30
MAX_PRE_RET_60D = 1.00
TOP_N = 20
ROUNDTRIP_COST = 0.007  # 0.7%, neutral Taiwan stock cost proxy.
HOLDING_DAYS = [20, 40, 60]
START_SIGNAL_MONTH = "2023-01"


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x: Any) -> float | None:
    try:
        if x is None or str(x).strip() == "": return None
        return float(x)
    except ValueError:
        return None


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8"); return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def percentile(vals: list[tuple[tuple[str, str], float]]) -> dict[tuple[str, str], float]:
    vals = sorted(vals, key=lambda x: x[1])
    n = len(vals)
    return {k: i / (n - 1) if n > 1 else 1.0 for i, (k, _v) in enumerate(vals)}


def build_revenue_panel(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_stock = defaultdict(list)
    for r in rows:
        key = (r["market"], r["stock_id"])
        by_stock[key].append(r)
    out = []
    for key, rs in by_stock.items():
        rs = sorted(rs, key=lambda r: r["revenue_month"])
        revs = [fnum(r["revenue_current_month"]) for r in rs]
        for i, r in enumerate(rs):
            cur = revs[i]
            if cur is None: continue
            r2 = dict(r)
            if i >= 14 and all(x is not None for x in revs[i-2:i+1]) and all(x is not None for x in revs[i-14:i-11]):
                recent_values = [float(x) for x in revs[i-2:i+1] if x is not None]
                last_values = [float(x) for x in revs[i-14:i-11] if x is not None]
                recent3 = sum(recent_values)
                last3 = sum(last_values)
                r2["revenue_3m_yoy_pct_calc"] = recent3 / last3 * 100 - 100 if last3 else None
            else:
                r2["revenue_3m_yoy_pct_calc"] = None
            out.append(r2)
    return out


def build_price_maps(rows: list[dict[str, Any]]):
    by_stock = defaultdict(list)
    all_dates = set()
    for r in rows:
        key = (r["market"], r["stock_id"])
        rec = {"date": r["trade_date"], "close": fnum(r["close"]), "turnover": fnum(r["turnover_value"])}
        if rec["close"] and rec["turnover"] is not None:
            by_stock[key].append(rec); all_dates.add(r["trade_date"])
    for k in list(by_stock): by_stock[k].sort(key=lambda x: x["date"])
    dates = sorted(all_dates)
    return by_stock, dates


def next_trading_date(dates: list[str], date_iso: str) -> str | None:
    for d in dates:
        if d >= date_iso: return d
    return None


def usable_to_entry_date(revenue_month: str, trading_dates: list[str]) -> str | None:
    y, m = map(int, revenue_month.split("-"))
    if m == 12: y2, m2 = y + 1, 1
    else: y2, m2 = y, m + 1
    return next_trading_date(trading_dates, f"{y2:04d}-{m2:02d}-11")


def idx_by_date(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {r["date"]: i for i, r in enumerate(rows)}


def mean(xs: list[float]) -> float | None:
    return statistics.mean(xs) if xs else None


def safe_ret(rows: list[dict[str, Any]], idx: int, lag: int) -> float | None:
    if idx - lag < 0: return None
    p0 = rows[idx - lag]["close"]; p1 = rows[idx]["close"]
    return p1 / p0 - 1 if p0 else None


def build_signals(rev_rows: list[dict[str, Any]], prices_by_stock: dict, trading_dates: list[str]) -> list[dict[str, Any]]:
    candidates_by_month = defaultdict(list)
    # preliminary eligible records with price features
    prelim = []
    for r in rev_rows:
        if r["revenue_month"] < START_SIGNAL_MONTH: continue
        if r["market"] not in {"listed", "otc"}: continue
        if r.get("industry") in EXCLUDED_INDUSTRIES: continue
        key = (r["market"], r["stock_id"])
        pr = prices_by_stock.get(key)
        if not pr: continue
        entry_date = usable_to_entry_date(r["revenue_month"], trading_dates)
        if not entry_date: continue
        imap = idx_by_date(pr)
        # if stock didn't trade exactly on entry date, find next stock-specific trade date
        stock_entry = next((x["date"] for x in pr if x["date"] >= entry_date), None)
        if not stock_entry or stock_entry not in imap: continue
        idx = imap[stock_entry]
        if idx < 61: continue
        yoy = fnum(r.get("revenue_yoy_pct"))
        mom = fnum(r.get("revenue_mom_pct"))
        ytd_yoy = fnum(r.get("revenue_ytd_yoy_pct"))
        rev3_raw = r.get("revenue_3m_yoy_pct_calc")
        rev3 = float(rev3_raw) if rev3_raw is not None else None
        cur = fnum(r.get("revenue_current_month"))
        base = fnum(r.get("revenue_same_month_last_year"))
        if None in {yoy, mom, cur, base, rev3}:
            continue
        assert yoy is not None and mom is not None and cur is not None and base is not None and rev3 is not None
        avg_turn20 = mean([x["turnover"] for x in pr[idx-20:idx] if x["turnover"] is not None])
        ret20 = safe_ret(pr, idx, 20); ret60 = safe_ret(pr, idx, 60)
        if avg_turn20 is None or ret20 is None or ret60 is None: continue
        reasons=[]
        if cur < MIN_CURRENT_REV: reasons.append("current_revenue_too_small")
        if base < MIN_LAST_YEAR_REV: reasons.append("last_year_base_too_small")
        if yoy <= 0: reasons.append("yoy_not_positive")
        if rev3 <= 0: reasons.append("rev_3m_yoy_not_positive")
        if mom <= -30: reasons.append("mom_too_negative")
        if ytd_yoy is not None and ytd_yoy <= -20: reasons.append("ytd_yoy_too_weak")
        if avg_turn20 < MIN_AVG_TURNOVER_20D: reasons.append("avg_turnover_20d_too_low")
        if ret20 > MAX_PRE_RET_20D: reasons.append("pre_return_20d_overheated")
        if ret60 > MAX_PRE_RET_60D: reasons.append("pre_return_60d_overheated")
        if reasons: continue
        prelim.append({**r, "entry_date": stock_entry, "price_idx": idx, "avg_turnover_20d": avg_turn20, "pre_ret_20d": ret20, "pre_ret_60d": ret60, "revenue_3m_yoy_pct_calc": rev3})

    # Rank within each revenue month to avoid look-ahead across months.
    by_month = defaultdict(list)
    for r in prelim: by_month[r["revenue_month"]].append(r)
    selected=[]
    for month, rows in by_month.items():
        yoy_rank = percentile([((r["market"], r["stock_id"]), fnum(r["revenue_yoy_pct"]) or 0) for r in rows])
        rev3_rank = percentile([((r["market"], r["stock_id"]), fnum(r["revenue_3m_yoy_pct_calc"]) or 0) for r in rows])
        mom_rank = percentile([((r["market"], r["stock_id"]), fnum(r["revenue_mom_pct"]) or 0) for r in rows])
        runup_rank = percentile([((r["market"], r["stock_id"]), -(r["pre_ret_20d"] or 0)) for r in rows])
        turn_rank = percentile([((r["market"], r["stock_id"]), math.log1p(r["avg_turnover_20d"])) for r in rows])
        scored=[]
        for r in rows:
            key=(r["market"],r["stock_id"])
            score=0.25*yoy_rank[key]+0.30*rev3_rank[key]+0.15*mom_rank[key]+0.15*runup_rank[key]+0.15*turn_rank[key]
            r2=dict(r); r2["proxy_signal_score"]=score; scored.append(r2)
        selected.extend(sorted(scored, key=lambda r:r["proxy_signal_score"], reverse=True)[:TOP_N])
    return selected


def build_trades(signals: list[dict[str, Any]], prices_by_stock: dict) -> list[dict[str, Any]]:
    trades=[]
    for s in signals:
        key=(s["market"],s["stock_id"]); pr=prices_by_stock[key]; idx=int(s["price_idx"]); entry_price=pr[idx]["close"]
        for h in HOLDING_DAYS:
            if idx+h >= len(pr): continue
            exit_rec=pr[idx+h]
            gross=exit_rec["close"]/entry_price-1
            net=gross-ROUNDTRIP_COST
            trades.append({
                "revenue_month": s["revenue_month"], "entry_date": s["entry_date"], "holding_days": h,
                "market": s["market"], "stock_id": s["stock_id"], "stock_name": s["stock_name"], "industry": s["industry"],
                "score": round(s["proxy_signal_score"],4), "revenue_yoy_pct": s["revenue_yoy_pct"], "revenue_3m_yoy_pct": round(s["revenue_3m_yoy_pct_calc"],4),
                "pre_ret_20d": round(s["pre_ret_20d"],6), "avg_turnover_20d": int(s["avg_turnover_20d"]),
                "entry_price": entry_price, "exit_date": exit_rec["date"], "exit_price": exit_rec["close"],
                "gross_return": round(gross,6), "net_return": round(net,6),
                "warning": "exploratory_proxy_backtest_unadjusted_prices_not_investment_advice",
            })
    return trades


def summarize(trades: list[dict[str, Any]]) -> dict[str, Any]:
    out={}
    for h in HOLDING_DAYS:
        rows=[r for r in trades if int(r["holding_days"])==h]
        rets=[float(r["net_return"]) for r in rows]
        if not rets: continue
        by_month=defaultdict(list)
        for r in rows: by_month[r["revenue_month"]].append(float(r["net_return"]))
        monthly=[statistics.mean(v) for k,v in sorted(by_month.items())]
        out[str(h)]={
            "trades": len(rows), "months": len(monthly), "avg_trade_net_return": statistics.mean(rets), "median_trade_net_return": statistics.median(rets),
            "win_rate": sum(1 for x in rets if x>0)/len(rets), "avg_monthly_cohort_net_return": statistics.mean(monthly),
            "positive_month_rate": sum(1 for x in monthly if x>0)/len(monthly), "best_month": max(monthly), "worst_month": min(monthly),
        }
    return out


def write_report(summary: dict[str, Any], trades: list[dict[str, Any]]) -> None:
    lines=["# Phase 2.5 探索性 Proxy 回測報告\n\n", "這不是正式回測，也不是交易建議。它使用保守 usable date proxy 與未調整收盤價，只用來判斷是否值得繼續研究。\n\n"]
    lines.append("## 設計\n\n")
    lines.append("- 月營收：MOPS 靜態歷史月營收彙總，2021-01 至 2026-04。\n")
    lines.append("- 價格：TWSE/TPEx 官方日行情，2023-01 至今，未調整價格。\n")
    lines.append("- 訊號可用日 proxy：營收月份次月 11 日後第一個交易日。\n")
    lines.append("- 每月最多 Top 20，等權 cohort。\n")
    lines.append("- 成本：來回 0.7%。\n")
    lines.append("- 持有期：20/40/60 個交易日。\n\n")
    lines.append("## 結果摘要\n\n")
    for h, s in summary.items():
        lines.append(f"### 持有 {h} 日\n")
        lines.append(f"- 交易數：{s['trades']}\n")
        lines.append(f"- 月份數：{s['months']}\n")
        lines.append(f"- 平均單筆淨報酬：{s['avg_trade_net_return']:.2%}\n")
        lines.append(f"- 中位數單筆淨報酬：{s['median_trade_net_return']:.2%}\n")
        lines.append(f"- 單筆勝率：{s['win_rate']:.2%}\n")
        lines.append(f"- 平均月 cohort 淨報酬：{s['avg_monthly_cohort_net_return']:.2%}\n")
        lines.append(f"- 月 cohort 正報酬率：{s['positive_month_rate']:.2%}\n")
        lines.append(f"- 最好/月最差 cohort：{s['best_month']:.2%} / {s['worst_month']:.2%}\n\n")
    lines.append("## 主要限制\n\n")
    lines.append("- 未用逐公司公告 timestamp。\n")
    lines.append("- 未處理除權息/現金股利/股票股利，長持有期報酬可能有偏差。\n")
    lines.append("- 未建立完整 portfolio NAV、重疊持倉、產業上限、非成交/漲跌停限制。\n")
    lines.append("- 未對 benchmark 計算超額報酬。\n")
    lines.append("- 若結果不好，可以早停；若結果好，也只代表值得做正式回測。\n")
    REPORT_MD.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    rev_rows=build_revenue_panel(read_csv(REV_CSV))
    price_rows=read_csv(PRICE_CSV)
    prices_by_stock, trading_dates=build_price_maps(price_rows)
    signals=build_signals(rev_rows, prices_by_stock, trading_dates)
    trades=build_trades(signals, prices_by_stock)
    write_csv(TRADES_CSV, trades)
    summary=summarize(trades)
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary, trades)
    print(json.dumps({"signals": len(signals), "trades": len(trades), "summary": summary, "outputs": [str(TRADES_CSV), str(SUMMARY_JSON), str(REPORT_MD)]}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
