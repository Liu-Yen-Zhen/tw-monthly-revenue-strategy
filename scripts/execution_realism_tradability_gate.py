#!/usr/bin/env python3
"""Phase 3.19: execution-realism / exact-tradability gate for S1 variants.

Research-only. No live trading, no broker connection, no orders.

Focus:
- audit actual OHLC / next-limit coverage before using fields;
- compare S1 equal, quiet-digestion boost, and liquidity>=100m variants under
  entry-close vs next-day close/open proxies, higher costs, and limit-up non-fill flags;
- estimate portfolio capacity using 1%/3%/5% of avg_turnover_20d as an ADV proxy.
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
OUT_SUMMARY = PROCESSED / "execution_realism_tradability_summary.csv"
OUT_MONTHLY = PROCESSED / "execution_realism_tradability_monthly.csv"
OUT_AUDIT = PROCESSED / "execution_realism_tradability_audit.csv"
OUT_CAPACITY = PROCESSED / "execution_realism_tradability_capacity.csv"
OUT_TRADE_FLAGS = PROCESSED / "execution_realism_tradability_trade_flags.csv"
OUT_REPORT = REPORTS / "phase3_19_execution_realism_tradability_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

QD_PATH = ROOT / "scripts" / "quiet_digestion_dynamic_sizing.py"
spec = importlib.util.spec_from_file_location("quiet_digestion_dynamic_sizing", QD_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {QD_PATH}")
qd = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(qd)
pa = qd.pa
sur = qd.sur
p316 = qd.p316
kl = qd.kl

HOLDING = 20
BASE_COST = 0.007
LIQ50 = 50_000_000
LIQ100 = 100_000_000
TOP_N = 8
IND_CAP = 3
COSTS = [0.007, 0.010, 0.015]
ENTRY_MODES = ["entry_close", "next_close", "next_open"]
POLICIES = ["all", "exclude_limitup_risk"]
PARTICIPATIONS = [0.01, 0.03, 0.05]
ELECTRONICS = qd.ELECTRONICS
SEMICONDUCTOR = qd.SEMICONDUCTOR


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
        return {"months": 0, "total_return": 0.0, "ann_return": None, "mean_month": None, "sharpe": None, "mdd": 0.0, "win_rate": None}
    sd = statistics.stdev(monthly) if len(monthly) >= 2 else None
    total = compound(monthly)
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


def percentile(vals: list[float], p: float) -> float | None:
    vals = sorted(v for v in vals if math.isfinite(v))
    if not vals:
        return None
    i = (len(vals) - 1) * p
    lo, hi = math.floor(i), math.ceil(i)
    return vals[lo] if lo == hi else vals[lo] * (hi - i) + vals[hi] * (i - lo)


def variant_weight(row: dict[str, Any], variant: str) -> float:
    if variant == "equal_s1":
        return 1.0
    if variant == "boost_quiet_no_large_black_150":
        return 1.5 if row.get("quiet_no_large_black") else 1.0
    if variant == "liq100_equal_s1":
        return 1.0 if float(row.get("avg_turnover_20d", 0)) >= LIQ100 else 0.0
    if variant == "liq100_boost_quiet_no_large_black_150":
        if float(row.get("avg_turnover_20d", 0)) < LIQ100:
            return 0.0
        return 1.5 if row.get("quiet_no_large_black") else 1.0
    raise KeyError(variant)


def build_raw_lookup() -> tuple[dict[tuple[str, str], list[dict[str, Any]]], dict[tuple[str, str, str], dict[str, Any]], list[dict[str, Any]]]:
    ohlc_by_stock, audit = kl.load_ohlc()
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (market, stock), rows in ohlc_by_stock.items():
        for i, r in enumerate(rows):
            r = dict(r)
            # Current-day limit can be inferred from previous official row's 次日漲停價/跌停價.
            if i > 0:
                r["current_up_limit"] = rows[i - 1].get("next_up_limit")
                r["current_down_limit"] = rows[i - 1].get("next_down_limit")
            else:
                r["current_up_limit"] = None
                r["current_down_limit"] = None
            by_key[(market, stock, r["date"])] = r
    return ohlc_by_stock, by_key, audit


def raw_market(m: str) -> str:
    return {"otc": "tpex", "listed": "twse", "twse": "twse", "tpex": "tpex"}.get(m, m)


def make_signals() -> tuple[list[dict[str, Any]], dict, dict, list[str], dict[str, Any]]:
    pa.HOLDINGS = [HOLDING]; pa.COST = BASE_COST; pa.BASE_TOP_N = TOP_N; pa.BASE_INDUSTRY_CAP = IND_CAP; pa.LIQ = LIQ50
    sur.HOLDINGS = [HOLDING]; sur.COST = BASE_COST; sur.TOP_N = TOP_N; sur.INDUSTRY_CAP = IND_CAP; sur.MIN_AVG_TURNOVER_20D = LIQ50
    scored, prices_by_stock, date_map, _counts = pa.build_scored()
    th = pa.thresholds(scored)
    audit = p316.attach_entry_ohlc(scored)
    all_months = sorted({r["revenue_month"] for r in scored})
    vol_low = th["abnormal_turnover"][0]
    mom_high = th["momentum_120_20"][1]
    base_pred = lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= mom_high and r.get("entry_close_location") is not None
    signals = qd.select_s1(scored, base_pred)
    for s in signals:
        large_black = bool(s["entry_black_candle"]) and s["entry_body_ratio"] >= audit["body_hi"]
        quiet = s["abnormal_turnover"] <= vol_low and s["entry_range_pct"] <= audit["range_low"]
        s["quiet_core"] = quiet
        s["large_black"] = large_black
        s["quiet_no_large_black"] = quiet and not large_black
        s["is_electronics"] = s["industry"] in ELECTRONICS
        s["is_semiconductor"] = s["industry"] == SEMICONDUCTOR
    return signals, prices_by_stock, date_map, all_months, {"audit": audit, "vol_low": vol_low, "mom_high": mom_high, "thresholds": th}


def near_limit(price: float | None, up_limit: float | None) -> bool:
    if price is None or up_limit is None or up_limit <= 0:
        return False
    return price >= up_limit * 0.995


def enriched_trade_rows(signals: list[dict[str, Any]], prices_by_stock: dict, raw_by_key: dict[tuple[str, str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in signals:
        pr = prices_by_stock.get((s["market"], s["stock_id"]))
        if not pr:
            continue
        base_idx = int(s["price_idx"])
        for mode in ENTRY_MODES:
            exec_idx = base_idx if mode == "entry_close" else base_idx + 1
            exit_idx = exec_idx + HOLDING
            if exec_idx >= len(pr) or exit_idx >= len(pr):
                continue
            exec_rec = pr[exec_idx]
            exit_rec = pr[exit_idx]
            rm = raw_market(s["market"])
            raw_exec = raw_by_key.get((rm, s["stock_id"], exec_rec["date"]))
            entry_price: float | None
            if mode == "next_open":
                entry_price = float(raw_exec["open"]) if raw_exec and raw_exec.get("open") is not None else None
            else:
                entry_price = float(exec_rec["close"])
            if entry_price is None or entry_price <= 0:
                continue
            exit_price = float(exit_rec["close"])
            gross = exit_price / entry_price - 1
            up_limit = float(raw_exec["current_up_limit"]) if raw_exec and raw_exec.get("current_up_limit") is not None else None
            open_px = float(raw_exec["open"]) if raw_exec and raw_exec.get("open") is not None else None
            close_px = float(raw_exec["close"]) if raw_exec and raw_exec.get("close") is not None else None
            exec_px_for_flag = open_px if mode == "next_open" else close_px
            possible_limit_nonfill = near_limit(exec_px_for_flag, up_limit)
            rows.append({
                "revenue_month": s["revenue_month"], "signal_entry_date": s["entry_date"], "exec_date": exec_rec["date"], "exit_date": exit_rec["date"],
                "entry_mode": mode, "market": s["market"], "stock_id": s["stock_id"], "stock_name": s["stock_name"], "industry": s["industry"],
                "score": s["score"], "score_sur_core": s.get("score_sur_core"), "sur_3m": s.get("sur_3m"), "momentum_120_20": s.get("momentum_120_20"),
                "avg_turnover_20d": s.get("avg_turnover_20d"), "abnormal_turnover": s.get("abnormal_turnover"),
                "quiet_core": s.get("quiet_core"), "large_black": s.get("large_black"), "quiet_no_large_black": s.get("quiet_no_large_black"),
                "is_electronics": s.get("is_electronics"), "is_semiconductor": s.get("is_semiconductor"),
                "entry_price": entry_price, "exit_price": exit_price, "gross_return": gross,
                "raw_ohlc_available": raw_exec is not None and raw_exec.get("open") is not None and raw_exec.get("high") is not None and raw_exec.get("low") is not None,
                "current_up_limit_available": up_limit is not None,
                "exec_open": open_px, "exec_close": close_px, "current_up_limit": up_limit,
                "possible_limit_up_nonfill": possible_limit_nonfill,
            })
    return rows


def monthly_eval(trades: list[dict[str, Any]], variant: str, entry_mode: str, cost: float, policy: str, all_months: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if r["entry_mode"] != entry_mode:
            continue
        if policy == "exclude_limitup_risk" and r.get("possible_limit_up_nonfill"):
            continue
        w = variant_weight(r, variant)
        if w <= 0:
            continue
        r2 = dict(r); r2["weight_raw"] = w; r2["net_return"] = float(r["gross_return"]) - cost
        by_month[r["revenue_month"]].append(r2)
    monthly: list[dict[str, Any]] = []
    capacity: list[dict[str, Any]] = []
    nav = 1.0
    for m in all_months:
        rows = by_month.get(m, [])
        total_w = sum(float(r["weight_raw"]) for r in rows)
        if total_w > 0:
            ret = sum(float(r["weight_raw"]) * float(r["net_return"]) for r in rows) / total_w
        else:
            ret = 0.0
        nav *= 1 + ret
        limit_flags = sum(1 for r in rows if r.get("possible_limit_up_nonfill"))
        monthly.append({"variant": variant, "entry_mode": entry_mode, "cost": cost, "tradability_policy": policy, "revenue_month": m, "return": ret, "nav": nav, "positions": len(rows), "limitup_risk_positions": limit_flags})
        if total_w > 0:
            for p in PARTICIPATIONS:
                caps = []
                for r in rows:
                    norm_w = float(r["weight_raw"]) / total_w
                    adv = float(r.get("avg_turnover_20d") or 0)
                    if norm_w > 0 and adv > 0:
                        caps.append((adv * p) / norm_w)
                capacity.append({"variant": variant, "entry_mode": entry_mode, "cost": cost, "tradability_policy": policy, "revenue_month": m, "participation": p, "portfolio_capacity_ntd": min(caps) if caps else None})
    return monthly, capacity


def summarize_monthly(monthly: list[dict[str, Any]]) -> dict[str, Any]:
    mm = metrics([float(r["return"]) for r in monthly])
    active = sum(1 for r in monthly if int(r["positions"]) > 0)
    return {
        "months_cash_counted": len(monthly), "active_months": active,
        "avg_positions_all_months": statistics.mean([int(r["positions"]) for r in monthly]) if monthly else 0.0,
        "total_limitup_risk_positions_remaining": sum(int(r["limitup_risk_positions"]) for r in monthly),
        "total_return": mm["total_return"], "ann_return": mm["ann_return"], "mean_month": mm["mean_month"],
        "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"], "monthly_win_rate": mm["win_rate"],
        "best_month": mm.get("best_month"), "worst_month": mm.get("worst_month"),
    }


def capacity_summary(capacity_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple, list[float]] = defaultdict(list)
    for r in capacity_rows:
        val = r.get("portfolio_capacity_ntd")
        if val is None:
            continue
        key = (r["variant"], r["entry_mode"], r["cost"], r["tradability_policy"], r["participation"])
        groups[key].append(float(val))
    out = []
    for key, vals in sorted(groups.items()):
        variant, entry_mode, cost, policy, participation = key
        out.append({
            "variant": variant, "entry_mode": entry_mode, "cost": cost, "tradability_policy": policy, "participation": participation,
            "active_months_with_capacity": len(vals), "p10_capacity_ntd": percentile(vals, 0.10), "median_capacity_ntd": percentile(vals, 0.50), "min_capacity_ntd": min(vals),
        })
    return out


def append_registry(summary_by_focus: dict[tuple[str, str, float, str], dict[str, Any]]) -> None:
    key_eq = ("equal_s1", "entry_close", 0.007, "all")
    key_boost = ("boost_quiet_no_large_black_150", "entry_close", 0.007, "all")
    key_next = ("boost_quiet_no_large_black_150", "next_open", 0.010, "exclude_limitup_risk")
    eq = summary_by_focus.get(key_eq, {})
    boost = summary_by_focus.get(key_boost, {})
    nxt = summary_by_focus.get(key_next, {})
    block = f"""
## Phase 3.19 update

- Execution-realism / exact-tradability gate added. This is still research-only: no live trading, no broker, no orders.
- Corrected limitation from Phase 3.18: prior conclusion used entry-close fixed-20 proxy and did not explicitly stress next-day open/close execution, higher costs, or possible limit-up non-fill. Phase 3.19 keeps the same S1/quiet variants but evaluates those frictions separately.
- Entry-close, 0.7% cost, all fills:
  - `equal_s1`: return `{pct(eq.get('total_return'))}`, Sharpe `{num(eq.get('sharpe_cash_counted'))}`, MDD `{pct(eq.get('mdd'))}`.
  - `boost_quiet_no_large_black_150`: return `{pct(boost.get('total_return'))}`, Sharpe `{num(boost.get('sharpe_cash_counted'))}`, MDD `{pct(boost.get('mdd'))}`.
- Conservative proxy to watch (`boost_quiet_no_large_black_150 | next_open | 1.0% cost | exclude_limitup_risk`): return `{pct(nxt.get('total_return'))}`, Sharpe `{num(nxt.get('sharpe_cash_counted'))}`, MDD `{pct(nxt.get('mdd'))}`.
- Registry status: S1 remains **incumbent / portfolio-grade v0.1 retained**. Quiet boost remains **research-only sizing hypothesis**, not promoted, until exact announcement timestamps, true intraday fillability, limit-up queue outcomes, and walk-forward sizing gates pass.
"""
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.19 update" not in text:
        REGISTRY.write_text(text.rstrip() + "\n" + block, encoding="utf-8")


def main() -> int:
    signals, prices_by_stock, date_map, all_months, ctx = make_signals()
    raw_by_stock, raw_by_key, raw_audit = build_raw_lookup()
    trades = enriched_trade_rows(signals, prices_by_stock, raw_by_key)
    variants = ["equal_s1", "boost_quiet_no_large_black_150", "liq100_equal_s1", "liq100_boost_quiet_no_large_black_150"]

    monthly_all: list[dict[str, Any]] = []
    capacity_all: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    for variant in variants:
        for mode in ENTRY_MODES:
            for cost in COSTS:
                for policy in POLICIES:
                    mon, cap = monthly_eval(trades, variant, mode, cost, policy, all_months)
                    monthly_all.extend(mon); capacity_all.extend(cap)
                    summary_row = {"variant": variant, "entry_mode": mode, "cost": cost, "tradability_policy": policy, **summarize_monthly(mon)}
                    summary.append(summary_row)

    # Audit at S1-signal/trade level; do not assume fields exist.
    audit_rows: list[dict[str, Any]] = []
    trade_by_mode = defaultdict(list)
    for r in trades:
        trade_by_mode[r["entry_mode"]].append(r)
    for mode in ENTRY_MODES:
        rs = trade_by_mode[mode]
        audit_rows.append({
            "scope": f"s1_trades_{mode}", "rows": len(rs),
            "raw_ohlc_available_rows": sum(1 for r in rs if r.get("raw_ohlc_available")),
            "raw_ohlc_coverage": (sum(1 for r in rs if r.get("raw_ohlc_available")) / len(rs)) if rs else 0,
            "current_up_limit_available_rows": sum(1 for r in rs if r.get("current_up_limit_available")),
            "current_up_limit_coverage": (sum(1 for r in rs if r.get("current_up_limit_available")) / len(rs)) if rs else 0,
            "possible_limit_up_nonfill_rows": sum(1 for r in rs if r.get("possible_limit_up_nonfill")),
        })
    for a in raw_audit:
        audit_rows.append({"scope": f"raw_{a['market']}", **a})

    cap_summary = capacity_summary(capacity_all)
    write_csv(OUT_SUMMARY, summary)
    write_csv(OUT_MONTHLY, monthly_all)
    write_csv(OUT_AUDIT, audit_rows)
    write_csv(OUT_CAPACITY, cap_summary)
    # keep compact trade flags only for review
    flag_fields = ["revenue_month", "signal_entry_date", "exec_date", "exit_date", "entry_mode", "market", "stock_id", "stock_name", "industry", "avg_turnover_20d", "quiet_no_large_black", "entry_price", "exit_price", "gross_return", "current_up_limit_available", "current_up_limit", "possible_limit_up_nonfill"]
    write_csv(OUT_TRADE_FLAGS, [{k: r.get(k) for k in flag_fields} for r in trades])

    by_key = {(r["variant"], r["entry_mode"], float(r["cost"]), r["tradability_policy"]): r for r in summary}
    append_registry(by_key)

    def row(v: str, mode: str, cost: float, pol: str) -> dict[str, Any]:
        return by_key[(v, mode, cost, pol)]

    focus_keys = [
        ("equal_s1", "entry_close", 0.007, "all"),
        ("boost_quiet_no_large_black_150", "entry_close", 0.007, "all"),
        ("liq100_equal_s1", "entry_close", 0.007, "all"),
        ("equal_s1", "next_open", 0.010, "exclude_limitup_risk"),
        ("boost_quiet_no_large_black_150", "next_open", 0.010, "exclude_limitup_risk"),
        ("liq100_equal_s1", "next_open", 0.010, "exclude_limitup_risk"),
    ]
    cap_lookup = {(r["variant"], r["entry_mode"], float(r["cost"]), r["tradability_policy"], float(r["participation"])): r for r in cap_summary}

    lines: list[str] = [
        "# Phase 3.19 execution realism / exact tradability gate\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because Taiwan monthly-revenue SUR repricing often occurs immediately after conservative data-availability dates, therefore prior entry-close proxy results may overstate implementability if the first tradable print is the next day open/close, if entry is near limit-up, or if realistic all-in costs are closer to 1.0%–1.5%. Quiet-digestion sizing should only survive if its small Phase 3.18 improvement persists after those execution frictions.\n\n",
        "### 前因後果\n\n",
        "- Phase 3.18 的 `boost_quiet_no_large_black_150` 只小幅改善 S1 full-sample Sharpe/return；這可能是 delayed repricing signal，也可能只是 entry-close / low-cost proxy bias。\n",
        "- 真實研究 gate 應先問：資料是否真的有 OHLC / limit 欄位？若有，用 next-day open/close 與 limit-up non-fill proxy 壓力測試；若無，必須標成 audit，不能硬編。\n\n",
        "### 檢查：欄位與可成交性 audit\n\n",
    ]
    for a in audit_rows:
        if str(a["scope"]).startswith("raw_"):
            lines.append(f"- `{a['scope']}`: raw_files={a.get('raw_json_files')}, common_stock_rows={a.get('common_stock_rows')}, OHLC coverage={pct(a.get('ohlc_coverage'))}, next-limit coverage={pct(a.get('next_limit_coverage'))}\n")
        else:
            lines.append(f"- `{a['scope']}`: rows={a['rows']}, OHLC coverage={pct(a['raw_ohlc_coverage'])}, current-up-limit coverage={pct(a['current_up_limit_coverage'])}, possible limit-up non-fill flags={a['possible_limit_up_nonfill_rows']}\n")

    lines += ["\n### 結果：核心比較（inactive months counted as cash）\n\n"]
    for k in focus_keys:
        r = by_key[k]
        lines.append(f"- `{k[0]} | {k[1]} | cost={k[2]:.1%} | {k[3]}`: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}, avg_pos={float(r['avg_positions_all_months']):.2f}, remaining_limit_flags={r['total_limitup_risk_positions_remaining']}\n")

    lines += ["\n### 成本壓力：boost_quiet_no_large_black_150（entry_close / all fills）\n\n"]
    for c in COSTS:
        r = row("boost_quiet_no_large_black_150", "entry_close", c, "all")
        lines.append(f"- cost={c:.1%}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}\n")
    lines += ["\n### Entry timing 壓力：boost_quiet_no_large_black_150（cost=1.0%, exclude limit-up risk）\n\n"]
    for mode in ENTRY_MODES:
        r = row("boost_quiet_no_large_black_150", mode, 0.010, "exclude_limitup_risk")
        lines.append(f"- {mode}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, avg_pos={float(r['avg_positions_all_months']):.2f}\n")
    lines += ["\n### Liquidity / capacity proxy\n\n", "Capacity is estimated as monthly portfolio capital capped by each position's `participation × avg_turnover_20d / normalized_weight`; this is a turnover-value proxy, not share-level order-book capacity.\n\n"]
    for k in [("equal_s1", "entry_close", 0.007, "all"), ("boost_quiet_no_large_black_150", "entry_close", 0.007, "all"), ("liq100_equal_s1", "entry_close", 0.007, "all")]:
        lines.append(f"#### {k[0]} | {k[1]} | cost={k[2]:.1%} | {k[3]}\n")
        for p in PARTICIPATIONS:
            c = cap_lookup.get((k[0], k[1], k[2], k[3], p), {})
            med = c.get("median_capacity_ntd")
            p10 = c.get("p10_capacity_ntd")
            lines.append(f"- ADV {p:.0%}: median capacity={med:,.0f} NTD, p10={p10:,.0f} NTD\n" if med is not None and p10 is not None else f"- ADV {p:.0%}: NA\n")

    eq = row("equal_s1", "entry_close", 0.007, "all")
    boost = row("boost_quiet_no_large_black_150", "entry_close", 0.007, "all")
    cons = row("boost_quiet_no_large_black_150", "next_open", 0.010, "exclude_limitup_risk")
    lines += [
        "\n### 修正與結論\n\n",
        "- 修正了什麼：Phase 3.18 只在 fixed-20 entry-close proxy 下討論 quiet sizing；本輪新增 OHLC/limit 欄位 audit、next-day open/close、limit-up non-fill exclusion、0.7%/1.0%/1.5% 成本與 ADV participation capacity proxy。\n",
        "- 為什麼先前不夠好：entry close + 單一成本沒有回答『營收公告後第一個可成交價格』與『漲停買不到』問題，也沒有把 liquidity>=100m 與資金容量分開看。\n",
        f"- 修正後結論是否改變：S1 仍是 incumbent；quiet boost 在原始 proxy 下為 `{pct(boost['total_return'])}` / Sharpe `{num(boost['sharpe_cash_counted'])}` vs S1 `{pct(eq['total_return'])}` / Sharpe `{num(eq['sharpe_cash_counted'])}`，但在更保守 `next_open + 1.0% cost + exclude limit-up risk` 下為 `{pct(cons['total_return'])}` / Sharpe `{num(cons['sharpe_cash_counted'])}`，因此仍只能保留為 research-only sizing hypothesis，不能 promotion。\n",
        "- Liquidity>=100m helps answer capacity but changes selection/exposure; it should remain robustness comparator, not automatically superior alpha.\n\n",
        "### 缺陷\n\n",
        "- `current_up_limit` 是由前一交易日官方 `次日漲停價` 推回，仍是 proxy；真實能否成交取決於盤中委託簿、排隊、撮合與公告時間。\n",
        "- Open fill assumes official open is accessible; no order-book, no opening auction imbalance, no partial-fill model.\n",
        "- `avg_turnover_20d` capacity proxy uses traded value, not shares/price-level depth；對小型股仍可能過度樂觀。\n",
        "- Monthly revenue available date仍用保守 11 日/next trading day proxy；尚未逐筆 exact announcement timestamp。\n\n",
        "### 下一步\n\n",
        "1. Phase 3.20: walk-forward / train-test dynamic sizing：只允許在 train 決定 quiet/large-black sizing rule，再看 test 是否維持。\n",
        "2. Exact timing gate：補 MOPS/TWSE announcement timestamp 或至少公司別公告日，重算 signal date / earliest trade date。\n",
        "3. Execution gate：若可取得 limit-up/down and OHLC 全期間資料，加入 open gap、停牌、漲停連續日、非成交量異常的 non-fill stress。\n\n",
        "## Outputs\n\n",
    ]
    for p in [OUT_SUMMARY, OUT_MONTHLY, OUT_AUDIT, OUT_CAPACITY, OUT_TRADE_FLAGS, OUT_REPORT, REGISTRY]:
        lines.append(f"- `{p}`\n")
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")

    print(json.dumps({"outputs": [str(OUT_SUMMARY), str(OUT_MONTHLY), str(OUT_AUDIT), str(OUT_CAPACITY), str(OUT_TRADE_FLAGS), str(OUT_REPORT)], "focus": {"equal_entry_close": eq, "boost_entry_close": boost, "boost_conservative": cons}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
