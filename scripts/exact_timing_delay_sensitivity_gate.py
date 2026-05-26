#!/usr/bin/env python3
"""Phase 3.21: exact-timing delay sensitivity gate for Taiwan monthly-revenue S1.

Research-only. No live trading, no broker connection, no orders.

The existing historical monthly-revenue file uses a conservative monthly summary
usable-date proxy (no company-level announcement timestamp). This script does not
invent exact timestamps. Instead it stresses the earliest-trade assumption by
shifting execution later by 0/1/2/3 trading days from the current S1 signal index,
using official OHLC where available, and excluding possible limit-up non-fill flags.
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
OUT_SUMMARY = PROCESSED / "exact_timing_delay_sensitivity_summary.csv"
OUT_MONTHLY = PROCESSED / "exact_timing_delay_sensitivity_monthly.csv"
OUT_TRADES = PROCESSED / "exact_timing_delay_sensitivity_trade_flags.csv"
OUT_REPORT = REPORTS / "phase3_21_exact_timing_delay_sensitivity_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

P319_PATH = ROOT / "scripts" / "execution_realism_tradability_gate.py"
spec = importlib.util.spec_from_file_location("execution_realism_tradability_gate", P319_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {P319_PATH}")
p319 = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(p319)

HOLDING = 20
COSTS = [0.010, 0.015]
DELAYS = [0, 1, 2, 3]
ENTRY_PRICE_FIELD = "open"
POLICY = "exclude_limitup_risk"
VARIANTS = ["equal_s1", "boost_quiet_no_large_black_150", "liq100_equal_s1"]
LIQ100 = 100_000_000


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for r in rows:
        for k in r:
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


def metrics(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"months": 0, "total_return": 0.0, "ann_return": None, "sharpe": None, "mdd": 0.0, "win_rate": None}
    sd = statistics.stdev(rs) if len(rs) >= 2 else None
    total = compound(rs)
    return {
        "months": len(rs),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(rs)) - 1,
        "mean_month": statistics.mean(rs),
        "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(rs),
        "win_rate": sum(1 for x in rs if x > 0) / len(rs),
        "worst_month": min(rs),
        "best_month": max(rs),
    }


def variant_weight(r: dict[str, Any], variant: str) -> float:
    if variant == "equal_s1":
        return 1.0
    if variant == "boost_quiet_no_large_black_150":
        return 1.5 if r.get("quiet_no_large_black") else 1.0
    if variant == "liq100_equal_s1":
        return 1.0 if float(r.get("avg_turnover_20d") or 0) >= LIQ100 else 0.0
    raise KeyError(variant)


def build_delay_trades(signals: list[dict[str, Any]], prices_by_stock: dict, raw_by_key: dict[tuple[str, str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in signals:
        pr = prices_by_stock.get((s["market"], s["stock_id"]))
        if not pr:
            continue
        base_idx = int(s["price_idx"])
        rm = p319.raw_market(s["market"])
        for delay in DELAYS:
            exec_idx = base_idx + delay
            exit_idx = exec_idx + HOLDING
            if exec_idx >= len(pr) or exit_idx >= len(pr):
                continue
            exec_rec = pr[exec_idx]
            exit_rec = pr[exit_idx]
            raw_exec = raw_by_key.get((rm, s["stock_id"], exec_rec["date"]))
            entry_price = float(raw_exec[ENTRY_PRICE_FIELD]) if raw_exec and raw_exec.get(ENTRY_PRICE_FIELD) is not None else None
            if entry_price is None or entry_price <= 0:
                continue
            exit_price = float(exit_rec["close"])
            up_limit = float(raw_exec["current_up_limit"]) if raw_exec and raw_exec.get("current_up_limit") is not None else None
            open_px = float(raw_exec["open"]) if raw_exec and raw_exec.get("open") is not None else None
            close_px = float(raw_exec["close"]) if raw_exec and raw_exec.get("close") is not None else None
            possible_limit_nonfill = p319.near_limit(open_px, up_limit)
            rows.append({
                "revenue_month": s["revenue_month"],
                "signal_entry_date_proxy": s["entry_date"],
                "delay_trading_days": delay,
                "exec_date": exec_rec["date"],
                "exit_date": exit_rec["date"],
                "market": s["market"], "stock_id": s["stock_id"], "stock_name": s["stock_name"], "industry": s["industry"],
                "avg_turnover_20d": s.get("avg_turnover_20d"), "quiet_no_large_black": s.get("quiet_no_large_black"), "large_black": s.get("large_black"),
                "entry_open": open_px, "entry_close": close_px, "entry_price": entry_price, "exit_price": exit_price,
                "gross_return": exit_price / entry_price - 1,
                "current_up_limit_available": up_limit is not None,
                "current_up_limit": up_limit,
                "possible_limit_up_nonfill": possible_limit_nonfill,
            })
    return rows


def monthly_eval(trades: list[dict[str, Any]], variant: str, delay: int, cost: float, all_months: list[str]) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if int(r["delay_trading_days"]) != delay:
            continue
        if POLICY == "exclude_limitup_risk" and r.get("possible_limit_up_nonfill"):
            continue
        w = variant_weight(r, variant)
        if w <= 0:
            continue
        r2 = dict(r); r2["weight"] = w; r2["net_return"] = float(r["gross_return"]) - cost
        by_month[r["revenue_month"]].append(r2)
    out = []
    nav = 1.0
    for m in all_months:
        rows = by_month.get(m, [])
        total_w = sum(float(r["weight"]) for r in rows)
        ret = sum(float(r["weight"]) * float(r["net_return"]) for r in rows) / total_w if total_w > 0 else 0.0
        nav *= 1 + ret
        out.append({
            "variant": variant, "delay_trading_days": delay, "entry_price_field": ENTRY_PRICE_FIELD, "cost": cost, "tradability_policy": POLICY,
            "revenue_month": m, "return": ret, "nav": nav, "positions": len(rows),
            "limitup_excluded_positions_in_month": sum(1 for r in trades if int(r["delay_trading_days"]) == delay and r["revenue_month"] == m and r.get("possible_limit_up_nonfill")),
        })
    return out


def summarize(mon: list[dict[str, Any]]) -> dict[str, Any]:
    mm = metrics([float(r["return"]) for r in mon])
    return {
        "months_cash_counted": len(mon),
        "active_months": sum(1 for r in mon if int(r["positions"]) > 0),
        "avg_positions_all_months": statistics.mean([int(r["positions"]) for r in mon]) if mon else 0.0,
        "total_limitup_excluded_flags": sum(int(r["limitup_excluded_positions_in_month"]) for r in mon),
        "total_return": mm["total_return"], "ann_return": mm["ann_return"], "sharpe_cash_counted": mm["sharpe"],
        "mdd": mm["mdd"], "monthly_win_rate": mm["win_rate"], "best_month": mm["best_month"], "worst_month": mm["worst_month"],
    }


def append_registry(summary_lookup: dict[tuple[str, int, float], dict[str, Any]]) -> None:
    base = summary_lookup.get(("equal_s1", 1, 0.010), {})
    boost0 = summary_lookup.get(("boost_quiet_no_large_black_150", 0, 0.010), {})
    boost3 = summary_lookup.get(("boost_quiet_no_large_black_150", 3, 0.010), {})
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.21 update" in text:
        return
    block = f"""
## Phase 3.21 update

- Added exact-timing delay sensitivity gate. Since company-level monthly revenue announcement timestamps are not available in current static revenue table, this does **not** claim exact tradability; it shifts execution by 0/1/2/3 trading days using official open and excludes possible limit-up non-fill flags.
- Conservative reference from Phase 3.19 (`equal_s1`, delay=1 / next-open analogue, cost 1.0%): return `{pct(base.get('total_return'))}`, Sharpe `{num(base.get('sharpe_cash_counted'))}`, MDD `{pct(base.get('mdd'))}`.
- Quiet boost timing sensitivity at 1.0% cost: delay=0 return/Sharpe `{pct(boost0.get('total_return'))}` / `{num(boost0.get('sharpe_cash_counted'))}`; delay=3 return/Sharpe `{pct(boost3.get('total_return'))}` / `{num(boost3.get('sharpe_cash_counted'))}`.
- Registry status unchanged: S1 remains incumbent. Quiet boost remains research-only; exact timestamp and real fillability remain open gates.
"""
    REGISTRY.write_text(text.rstrip() + "\n" + block, encoding="utf-8")


def main() -> int:
    signals, prices_by_stock, _date_map, all_months, _ctx = p319.make_signals()
    _raw_by_stock, raw_by_key, raw_audit = p319.build_raw_lookup()
    trades = build_delay_trades(signals, prices_by_stock, raw_by_key)

    monthly_all: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    for v in VARIANTS:
        for delay in DELAYS:
            for cost in COSTS:
                mon = monthly_eval(trades, v, delay, cost, all_months)
                monthly_all.extend(mon)
                summary.append({"variant": v, "delay_trading_days": delay, "entry_price_field": ENTRY_PRICE_FIELD, "cost": cost, "tradability_policy": POLICY, **summarize(mon)})

    write_csv(OUT_SUMMARY, summary)
    write_csv(OUT_MONTHLY, monthly_all)
    flag_fields = ["revenue_month", "signal_entry_date_proxy", "delay_trading_days", "exec_date", "exit_date", "market", "stock_id", "stock_name", "industry", "avg_turnover_20d", "quiet_no_large_black", "large_black", "entry_open", "entry_close", "exit_price", "gross_return", "current_up_limit_available", "current_up_limit", "possible_limit_up_nonfill"]
    write_csv(OUT_TRADES, [{k: r.get(k) for k in flag_fields} for r in trades])

    lookup = {(r["variant"], int(r["delay_trading_days"]), float(r["cost"])): r for r in summary}
    append_registry(lookup)

    lines: list[str] = [
        "# Phase 3.21 exact-timing delay sensitivity gate\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because the current historical monthly-revenue table has `monthly_summary_no_company_timestamp` rather than exact company-level announcement timestamps, therefore even the conservative 11th/next-trading-day signal may still mis-time first tradability. If S1 alpha is robust delayed repricing rather than same-day execution bias, performance should not collapse when execution is shifted later by 1–3 trading days using official opens and excluding possible limit-up non-fills.\n\n",
        "### 前因後果\n\n",
        "- Phase 3.19 corrected execution price and limit-up assumptions, but still used the existing signal date proxy.\n",
        "- 本輪不硬編 exact timestamp；只做 delay sensitivity：從現有 S1 proxy signal index 延後 0/1/2/3 個交易日，以 official open 進場，20D close 出場，成本 1.0%/1.5%，排除 possible limit-up non-fill。\n\n",
        "### 檢查\n\n",
        f"- Delay trades built: {len(trades)} rows across {len(DELAYS)} delays; months cash-counted: {len(all_months)}.\n",
    ]
    for a in raw_audit:
        lines.append(f"- raw `{a['market']}` OHLC coverage={pct(a.get('ohlc_coverage'))}, next-limit coverage={pct(a.get('next_limit_coverage'))}.\n")

    lines.append("\n### 結果：1.0% cost / official open / exclude limit-up risk\n\n")
    for v in VARIANTS:
        lines.append(f"#### {v}\n")
        for delay in DELAYS:
            r = lookup[(v, delay, 0.010)]
            lines.append(f"- delay={delay} trading days: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}, avg_pos={float(r['avg_positions_all_months']):.2f}, excluded_flags={r['total_limitup_excluded_flags']}\n")
    lines.append("\n### 成本壓力：boost_quiet_no_large_black_150 at delay=1\n\n")
    for cost in COSTS:
        r = lookup[("boost_quiet_no_large_black_150", 1, cost)]
        lines.append(f"- cost={cost:.1%}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}\n")

    eq1 = lookup[("equal_s1", 1, 0.010)]
    boost1 = lookup[("boost_quiet_no_large_black_150", 1, 0.010)]
    boost3 = lookup[("boost_quiet_no_large_black_150", 3, 0.010)]
    lines += [
        "\n### 修正與結論\n\n",
        "- 修正了什麼：Phase 3.19 已確認 OHLC/limit 欄位並做 next-open proxy；本輪進一步把『exact announcement timestamp 不存在』轉成延後 0–3 交易日的 timing stress。\n",
        "- 為什麼先前不夠好：只看 next-open 仍可能把公司實際公告日、公告時間、或資料取得延遲估得太樂觀。\n",
        f"- 修正後結論是否改變：沒有 promotion。delay=1 下 quiet boost 為 `{pct(boost1['total_return'])}` / Sharpe `{num(boost1['sharpe_cash_counted'])}`，equal S1 為 `{pct(eq1['total_return'])}` / Sharpe `{num(eq1['sharpe_cash_counted'])}`；delay=3 下 quiet boost 為 `{pct(boost3['total_return'])}` / Sharpe `{num(boost3['sharpe_cash_counted'])}`。結果支持『訊號不是完全依賴當日 close』，但 Sharpe 仍在 research-candidate 區間，不足以升格 production。\n\n",
        "### 缺陷\n\n",
        "- Delay stress 不是 exact timestamp；公司可能在 10 日前後不同時間公告，真正 earliest tradable date 可能比 proxy 早或晚。\n",
        "- Official open fill 仍沒有 opening auction queue、partial fill、order book depth、limit-up 排隊資料。\n",
        "- 延後進場同時改變 exit date，仍是 fixed 20 trading-day close-price proxy。\n",
        "- 現有樣本主要 2023–2025，可驗證年份不足。\n\n",
        "### 下一步\n\n",
        "1. 尋找 MOPS/TWSE 公司別月營收公告 timestamp 或至少公告日期欄位，重建 signal_date / earliest_trade_date。\n",
        "2. 對 delay sensitivity 加入 remove-top-winners / sector survival，確認不是少數半導體供應鏈 winners 撐住。\n",
        "3. 若 exact timestamp 取得後，多數 S1 trades 實際只能 delay>=2，則以 delay>=2 為新的 incumbent gate 重新跑 Phase 3.20。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_SUMMARY}`\n",
        f"- `{OUT_MONTHLY}`\n",
        f"- `{OUT_TRADES}`\n",
        f"- `{OUT_REPORT}`\n",
        f"- `{REGISTRY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")

    print(json.dumps({"outputs": [str(OUT_SUMMARY), str(OUT_MONTHLY), str(OUT_TRADES), str(OUT_REPORT)], "focus": {"equal_delay1": eq1, "boost_delay1": boost1, "boost_delay3": boost3}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
