#!/usr/bin/env python3
"""Phase 3 enhanced diagnostics for the Taiwan monthly revenue proxy backtest.

Research-only. No trading, no deployment, no package installation.
Adds diagnostics that are required before treating the proxy result seriously:
- equal-weight tradable-universe benchmark for each entry/exit window
- excess return vs benchmark
- yearly breakdown
- industry breakdown
- single-name contribution concentration
- payoff structure
- a simple industry-capped variant based on the existing Top-20 signals
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
TRADES_CSV = PROCESSED / "proxy_backtest_trades.csv"
PRICE_CSV = PROCESSED / "daily_market_history_2023_present.csv"
OUT_ENRICHED = PROCESSED / "proxy_backtest_trades_enriched.csv"
OUT_SUMMARY = PROCESSED / "enhanced_proxy_analysis_summary.json"
OUT_REPORT = REPORTS / "phase3_enhanced_proxy_analysis_report.md"
ROUNDTRIP_COST = 0.007
INDUSTRY_CAP_PER_MONTH = 6  # 30% of Top 20


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def f(x: Any) -> float:
    return float(x)


def mean(xs: list[float]) -> float | None:
    return statistics.mean(xs) if xs else None


def median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def ret_summary(xs: list[float]) -> dict[str, Any]:
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x <= 0]
    avg_win = mean(wins)
    avg_loss = mean(losses)
    win_rate = len(wins) / len(xs) if xs else None
    return {
        "n": len(xs),
        "mean": mean(xs),
        "median": median(xs),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": abs(avg_win / avg_loss) if avg_win is not None and avg_loss not in (None, 0) else None,
        "best": max(xs) if xs else None,
        "worst": min(xs) if xs else None,
    }


def build_price_index(price_rows: list[dict[str, Any]]):
    date_map: dict[str, dict[tuple[str, str], float]] = defaultdict(dict)
    for r in price_rows:
        try:
            close = float(r["close"])
        except Exception:
            continue
        date_map[r["trade_date"]][(r["market"], r["stock_id"])] = close
    return date_map


def benchmark_return(date_map: dict[str, dict[tuple[str, str], float]], entry: str, exit_: str) -> float | None:
    a = date_map.get(entry)
    b = date_map.get(exit_)
    if not a or not b:
        return None
    common = set(a).intersection(b)
    rets = []
    for k in common:
        if a[k] > 0 and b[k] > 0:
            rets.append(b[k] / a[k] - 1 - ROUNDTRIP_COST)
    return statistics.mean(rets) if rets else None


def enrich_trades(trades: list[dict[str, Any]], date_map: dict[str, dict[tuple[str, str], float]]) -> list[dict[str, Any]]:
    bench_cache: dict[tuple[str, str], float | None] = {}
    out = []
    for r in trades:
        key = (r["entry_date"], r["exit_date"])
        if key not in bench_cache:
            bench_cache[key] = benchmark_return(date_map, *key)
        bench = bench_cache[key]
        net = f(r["net_return"])
        r2 = dict(r)
        r2["benchmark_net_return"] = round(bench, 6) if bench is not None else ""
        r2["excess_return"] = round(net - bench, 6) if bench is not None else ""
        r2["entry_year"] = r["entry_date"][:4]
        out.append(r2)
    return out


def group_summary(rows: list[dict[str, Any]], key_fields: list[str], value_field: str) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for r in rows:
        v = r.get(value_field, "")
        if v == "" or v is None:
            continue
        groups[tuple(str(r[k]) for k in key_fields)].append(float(v))
    out = []
    for k, vals in sorted(groups.items()):
        s = ret_summary(vals)
        row = {field: k[i] for i, field in enumerate(key_fields)}
        row.update({kk: vv for kk, vv in s.items() if kk in {"n", "mean", "median", "win_rate", "best", "worst"}})
        out.append(row)
    return out


def contribution_summary(rows: list[dict[str, Any]], holding_days: str) -> dict[str, Any]:
    filtered = [r for r in rows if r["holding_days"] == holding_days]
    by_stock: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for r in filtered:
        by_stock[(r["stock_id"], r["stock_name"], r["industry"])].append(float(r["net_return"]))
    contrib = []
    total = sum(float(r["net_return"]) for r in filtered)
    abs_total = sum(abs(float(r["net_return"])) for r in filtered)
    for (sid, name, ind), vals in by_stock.items():
        contrib.append({
            "stock_id": sid,
            "stock_name": name,
            "industry": ind,
            "trades": len(vals),
            "sum_net_return": sum(vals),
            "avg_net_return": statistics.mean(vals),
        })
    contrib.sort(key=lambda x: x["sum_net_return"], reverse=True)
    top10_sum = sum(x["sum_net_return"] for x in contrib[:10])
    bottom10_sum = sum(x["sum_net_return"] for x in contrib[-10:]) if contrib else 0
    return {
        "total_sum_net_return": total,
        "absolute_sum_net_return": abs_total,
        "top10_positive_sum": top10_sum,
        "top10_positive_share_of_total": top10_sum / total if total else None,
        "bottom10_sum": bottom10_sum,
        "top10": contrib[:10],
        "bottom10": list(reversed(contrib[-10:])),
    }


def industry_capped_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Use unique signals by revenue_month, stock, score for each holding-day separately.
    out = []
    for h in sorted({r["holding_days"] for r in rows}, key=int):
        by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            if r["holding_days"] == h:
                by_month[r["revenue_month"]].append(r)
        for _month, month_rows in by_month.items():
            counts: dict[str, int] = defaultdict(int)
            for r in sorted(month_rows, key=lambda x: float(x["score"]), reverse=True):
                if counts[r["industry"]] >= INDUSTRY_CAP_PER_MONTH:
                    continue
                out.append(r)
                counts[r["industry"]] += 1
    return out


def main() -> int:
    trades = read_csv(TRADES_CSV)
    price_rows = read_csv(PRICE_CSV)
    date_map = build_price_index(price_rows)
    enriched = enrich_trades(trades, date_map)
    write_csv(OUT_ENRICHED, enriched)

    summary: dict[str, Any] = {"by_holding": {}, "industry_capped_by_holding": {}}
    for h in sorted({r["holding_days"] for r in enriched}, key=int):
        rows = [r for r in enriched if r["holding_days"] == h]
        net = [float(r["net_return"]) for r in rows]
        excess = [float(r["excess_return"]) for r in rows if r.get("excess_return") not in ("", None)]
        monthly: dict[str, list[float]] = defaultdict(list)
        monthly_excess: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            monthly[r["revenue_month"]].append(float(r["net_return"]))
            if r.get("excess_return") not in ("", None):
                monthly_excess[r["revenue_month"]].append(float(r["excess_return"]))
        month_rets = [statistics.mean(v) for v in monthly.values()]
        month_excess = [statistics.mean(v) for v in monthly_excess.values()]
        summary["by_holding"][h] = {
            "trade_return": ret_summary(net),
            "trade_excess": ret_summary(excess),
            "monthly_cohort_return": ret_summary(month_rets),
            "monthly_cohort_excess": ret_summary(month_excess),
            "yearly_net": group_summary(rows, ["entry_year"], "net_return"),
            "yearly_excess": group_summary(rows, ["entry_year"], "excess_return"),
            "industry_net_top": sorted(group_summary(rows, ["industry"], "net_return"), key=lambda x: x["mean"] if x["mean"] is not None else -999, reverse=True)[:15],
            "contribution": contribution_summary(enriched, h),
        }

    capped = industry_capped_rows(enriched)
    for h in sorted({r["holding_days"] for r in capped}, key=int):
        rows = [r for r in capped if r["holding_days"] == h]
        monthly = defaultdict(list)
        monthly_excess = defaultdict(list)
        for r in rows:
            monthly[r["revenue_month"]].append(float(r["net_return"]))
            if r.get("excess_return") not in ("", None):
                monthly_excess[r["revenue_month"]].append(float(r["excess_return"]))
        summary["industry_capped_by_holding"][h] = {
            "trades": len(rows),
            "monthly_cohort_return": ret_summary([statistics.mean(v) for v in monthly.values()]),
            "monthly_cohort_excess": ret_summary([statistics.mean(v) for v in monthly_excess.values()]),
        }

    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary)
    print(json.dumps({"enriched_trades": len(enriched), "outputs": [str(OUT_ENRICHED), str(OUT_SUMMARY), str(OUT_REPORT)]}, ensure_ascii=False, indent=2))
    return 0


def pct(x: Any) -> str:
    if x is None:
        return "NA"
    return f"{float(x):.2%}"


def write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# Phase 3 強化診斷：Benchmark、年度、產業、單檔貢獻\n\n",
        "本報告延續探索性 proxy 回測，加入 benchmark excess、年度拆解、產業拆解、payoff structure 與單檔貢獻集中度。仍不是正式回測或投資建議。\n\n",
        "## 方法補充\n\n",
        "- Benchmark：每個 entry/exit window 使用當日可同時取得價格的上市+上櫃股票等權報酬，並同樣扣 0.7% round-trip cost。\n",
        "- Excess return：策略單筆淨報酬 - 對應 window benchmark 淨報酬。\n",
        "- Industry cap variant：在既有 Top 20 signal 中，每月單一產業最多保留 6 檔，約等於 30% 上限。\n",
        "- 價格仍為未調整收盤價；結果只作研究診斷。\n\n",
    ]
    for h in ["20", "40", "60"]:
        s = summary["by_holding"].get(h)
        if not s:
            continue
        tr = s["trade_return"]
        ex = s["trade_excess"]
        mc = s["monthly_cohort_return"]
        mex = s["monthly_cohort_excess"]
        lines += [
            f"## 持有 {h} 日\n\n",
            f"- 單筆平均淨報酬：{pct(tr['mean'])}\n",
            f"- 單筆中位數淨報酬：{pct(tr['median'])}\n",
            f"- 單筆勝率：{pct(tr['win_rate'])}\n",
            f"- 平均獲利 / 平均虧損：{pct(tr['avg_win'])} / {pct(tr['avg_loss'])}\n",
            f"- Payoff ratio：{tr['payoff_ratio']:.2f}\n" if tr.get("payoff_ratio") is not None else "- Payoff ratio：NA\n",
            f"- 單筆平均超額報酬：{pct(ex['mean'])}\n",
            f"- 單筆超額勝率：{pct(ex['win_rate'])}\n",
            f"- 月 cohort 平均淨報酬：{pct(mc['mean'])}\n",
            f"- 月 cohort 平均超額報酬：{pct(mex['mean'])}\n",
            f"- 月 cohort 超額為正比例：{pct(mex['win_rate'])}\n\n",
            "### 年度平均淨報酬\n\n",
        ]
        for row in s["yearly_net"]:
            lines.append(f"- {row['entry_year']}: mean={pct(row['mean'])}, median={pct(row['median'])}, win={pct(row['win_rate'])}, n={row['n']}\n")
        lines.append("\n### 單檔貢獻集中度\n\n")
        c = s["contribution"]
        lines.append(f"- Top 10 正貢獻合計 / 總合計：{c['top10_positive_share_of_total']:.2f}\n" if c.get("top10_positive_share_of_total") is not None else "- Top 10 正貢獻合計 / 總合計：NA\n")
        lines.append("- Top contributors:\n")
        for x in c["top10"][:5]:
            lines.append(f"  - {x['stock_id']} {x['stock_name']}｜{x['industry']}｜sum={pct(x['sum_net_return'])}｜avg={pct(x['avg_net_return'])}｜n={x['trades']}\n")
        lines.append("\n")
    lines.append("## 產業上限變體\n\n")
    for h, s in summary["industry_capped_by_holding"].items():
        lines.append(f"- {h} 日：trades={s['trades']}，月 cohort 平均淨報酬={pct(s['monthly_cohort_return']['mean'])}，平均超額={pct(s['monthly_cohort_excess']['mean'])}，超額為正比例={pct(s['monthly_cohort_excess']['win_rate'])}\n")
    lines += [
        "\n## 解讀\n\n",
        "這份診斷的核心用途是檢查原本正報酬是否只是市場 beta、單一年份、單一產業或少數股票造成。若 benchmark excess、年度拆解和產業上限後仍維持正值，才值得投入正式 portfolio NAV 回測。\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
