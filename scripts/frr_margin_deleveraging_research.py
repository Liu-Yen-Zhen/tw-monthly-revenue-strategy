#!/usr/bin/env python3
"""Phase 4.1: FRR margin-deleveraging short-horizon research.

Research-only. Tests whether strong monthly-revenue surprise stocks with recent
margin deleveraging have better 10/15/20D outcomes. No broker, no orders.
"""
from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
SIGNALS = PROCESSED / "sur_factor_signals.csv"
MARGIN = PROCESSED / "daily_margin_balance.csv"
DAILY = PROCESSED / "official_daily_ohlc_limit_from_raw.csv"
OUT_TRADES = PROCESSED / "frr_margin_deleveraging_trades.csv"
OUT_VARIANTS = PROCESSED / "frr_margin_deleveraging_variants.csv"
OUT_YEARLY = PROCESSED / "frr_margin_deleveraging_yearly.csv"
OUT_REMOVE = PROCESSED / "frr_margin_deleveraging_remove_winners.csv"
OUT_SECTOR = PROCESSED / "frr_margin_deleveraging_sector.csv"
OUT_AUDIT = PROCESSED / "frr_margin_deleveraging_audit.csv"
OUT_REPORT = REPORTS / "phase4_1_frr_margin_deleveraging_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

HOLDINGS = [10, 15, 20]
DELAYS = [1, 2, 3]
COST = 0.010
LIQ50 = 50_000_000
LIQ100 = 100_000_000
LIQ200 = 200_000_000
TOP_N = 8
IND_CAP = 3


def fnum(x: Any) -> float | None:
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(x)
    except Exception:
        return None


def pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def q(vals: list[float], p: float) -> float | None:
    vals = sorted(v for v in vals if not math.isnan(v))
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
    nav = peak = 1.0
    worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"months": 0, "total_return": 0.0, "ann_return": None, "sharpe": None, "mdd": 0.0, "win_rate": None, "mean_month": None}
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
        "best_month": max(rs),
        "worst_month": min(rs),
    }


def build_price_maps(rows: list[dict[str, Any]]) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], dict[tuple[str, str, str], dict[str, Any]]]:
    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in rows:
        if not r.get("open") or not r.get("close"):
            continue
        k = (str(r["market"]), str(r["stock_id"]))
        rec = dict(r)
        rec["date"] = str(r["trade_date"])
        by[k].append(rec)
        key[(k[0], k[1], rec["date"])] = rec
    for k in by:
        by[k].sort(key=lambda r: r["date"])
    return by, key


def build_margin_features(rows: list[dict[str, Any]]) -> tuple[dict[tuple[str, str, str], dict[str, Any]], dict[str, Any]]:
    by: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        mb = fnum(r.get("margin_balance"))
        if mb is None:
            continue
        by[(str(r["market"]), str(r["stock_id"]))].append(dict(r))
    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for k, rs in by.items():
        rs.sort(key=lambda r: str(r["trade_date"]))
        for i, r in enumerate(rs):
            mb = fnum(r.get("margin_balance")) or 0.0
            prev5 = fnum(rs[i-5].get("margin_balance")) if i >= 5 else None
            prev10 = fnum(rs[i-10].get("margin_balance")) if i >= 10 else None
            margin_buy_5 = sum(fnum(x.get("margin_buy")) or 0.0 for x in rs[max(0, i-4):i+1])
            margin_sell_5 = sum(fnum(x.get("margin_sell")) or 0.0 for x in rs[max(0, i-4):i+1])
            cash_repay_5 = sum(fnum(x.get("margin_cash_repay")) or 0.0 for x in rs[max(0, i-4):i+1])
            feat = dict(r)
            feat["margin_balance_chg_5d"] = mb - prev5 if prev5 is not None else ""
            feat["margin_balance_pct_chg_5d"] = (mb / prev5 - 1) if prev5 and prev5 > 0 else ""
            feat["margin_balance_chg_10d"] = mb - prev10 if prev10 is not None else ""
            feat["margin_balance_pct_chg_10d"] = (mb / prev10 - 1) if prev10 and prev10 > 0 else ""
            feat["margin_sell_repay_5d"] = margin_sell_5 + cash_repay_5
            feat["margin_buy_5d"] = margin_buy_5
            feat["margin_deleveraging_intensity"] = ((margin_sell_5 + cash_repay_5 - margin_buy_5) / prev5) if prev5 and prev5 > 0 else ""
            out[(k[0], k[1], str(r["trade_date"]))] = feat
    audit = {"margin_stocks": len(by), "margin_feature_rows": len(out)}
    return out, audit


def add_features(signals: list[dict[str, Any]], prices_by_stock: dict, margin_by_key: dict) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    enriched: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for s in signals:
        if s.get("recipe") != "sur_core":
            continue
        k = (str(s["market"]), str(s["stock_id"]))
        pr = prices_by_stock.get(k)
        if not pr:
            continue
        dates = [r["date"] for r in pr]
        try:
            idx = dates.index(str(s["entry_date"]))
        except ValueError:
            continue
        m = margin_by_key.get((k[0], k[1], str(s["entry_date"])))
        if not m:
            audit.append({"stock_id": s["stock_id"], "entry_date": s["entry_date"], "reason": "missing_margin_on_entry_date"})
            continue
        r = dict(s)
        r["price_idx"] = idx
        for fld in ["margin_balance", "margin_usage_pct", "margin_balance_chg_5d", "margin_balance_pct_chg_5d", "margin_balance_chg_10d", "margin_balance_pct_chg_10d", "margin_sell_repay_5d", "margin_buy_5d", "margin_deleveraging_intensity"]:
            r[fld] = m.get(fld, "")
        # Price stabilization features available at signal close (entry_date close), then trade from next open.
        start10 = max(0, idx - 9)
        lows10: list[float] = []
        for x in pr[start10:idx+1]:
            lx = fnum(x.get("low"))
            if lx is not None:
                lows10.append(lx)
        close = fnum(pr[idx].get("close"))
        prev_close = fnum(pr[idx-1].get("close")) if idx >= 1 else None
        low = fnum(pr[idx].get("low"))
        r["no_new_10d_low"] = bool(low is not None and lows10 and low > min(lows10[:-1] or lows10))
        r["close_up_1d"] = bool(close is not None and prev_close is not None and close > prev_close)
        enriched.append(r)
    return enriched, audit


def thresholds(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "sur3_q70": q([float(r["sur_3m"]) for r in rows if fnum(r.get("sur_3m")) is not None], 0.70) or 0.0,
        "margin_pct_q35": q([float(r["margin_balance_pct_chg_5d"]) for r in rows if fnum(r.get("margin_balance_pct_chg_5d")) is not None], 0.35) or -0.03,
        "delev_q65": q([float(r["margin_deleveraging_intensity"]) for r in rows if fnum(r.get("margin_deleveraging_intensity")) is not None], 0.65) or 0.0,
        "abturn_q60": q([float(r["abnormal_turnover"]) for r in rows if fnum(r.get("abnormal_turnover")) is not None], 0.60) or 1.0,
    }


def pred(name: str, r: dict[str, Any], th: dict[str, float]) -> bool:
    sur3 = fnum(r.get("sur_3m"))
    mp5 = fnum(r.get("margin_balance_pct_chg_5d"))
    delev = fnum(r.get("margin_deleveraging_intensity"))
    liq = fnum(r.get("avg_turnover_20d")) or 0.0
    pre20 = fnum(r.get("pre_ret_20d")) or 0.0
    if sur3 is None or mp5 is None or delev is None:
        return False
    base = sur3 >= th["sur3_q70"] and (mp5 <= th["margin_pct_q35"] or delev >= th["delev_q65"]) and liq >= LIQ50 and pre20 > -0.20
    if name == "frr1_basic_deleveraging":
        return base
    if name == "frr2_no_catch_falling_knife":
        return base and bool(r.get("no_new_10d_low"))
    if name == "frr3_volume_absorption":
        abt = fnum(r.get("abnormal_turnover")) or 0.0
        return base and abt >= th["abturn_q60"]
    if name == "frr5_conservative_liq100":
        return base and bool(r.get("no_new_10d_low")) and liq >= LIQ100
    if name == "frr5_capacity_liq200":
        return base and bool(r.get("no_new_10d_low")) and liq >= LIQ200
    raise KeyError(name)


def select_signals(rows: list[dict[str, Any]], recipes: list[str], th: dict[str, float]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for recipe in recipes:
        by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            if pred(recipe, r, th):
                by_month[str(r["revenue_month"])].append(r)
        for month, rs in by_month.items():
            ind_count: dict[str, int] = defaultdict(int)
            selected = 0
            def score(x: dict[str, Any]) -> float:
                return (fnum(x.get("sur_3m")) or 0) + 0.5 * (fnum(x.get("margin_deleveraging_intensity")) or 0) - 0.2 * max(0, fnum(x.get("pre_ret_20d")) or 0)
            for r in sorted(rs, key=score, reverse=True):
                ind = str(r.get("industry", ""))
                if ind_count[ind] >= IND_CAP:
                    continue
                r2 = dict(r); r2["variant"] = recipe; r2["frr_score"] = score(r)
                out.append(r2)
                ind_count[ind] += 1; selected += 1
                if selected >= TOP_N:
                    break
    return out


def build_trades(signals: list[dict[str, Any]], prices_by_stock: dict) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    for s in signals:
        pr = prices_by_stock.get((s["market"], s["stock_id"]))
        if not pr:
            continue
        idx = int(s["price_idx"])
        for delay in DELAYS:
            eidx = idx + delay
            if eidx >= len(pr):
                continue
            entry = pr[eidx]
            entry_open = fnum(entry.get("open"))
            entry_close = fnum(entry.get("close"))
            limit_up = fnum(entry.get("next_limit_up"))  # proxy field availability varies; diagnostic only.
            possible_limit_nonfill = bool(limit_up is not None and entry_open is not None and abs(entry_open / limit_up - 1) < 0.003)
            if entry_open is None or entry_open <= 0:
                continue
            for h in HOLDINGS:
                xidx = eidx + h
                if xidx >= len(pr):
                    continue
                exit_rec = pr[xidx]
                exit_px = fnum(exit_rec.get("close"))
                if exit_px is None or exit_px <= 0:
                    continue
                trades.append({
                    "variant": s["variant"], "revenue_month": s["revenue_month"], "signal_date": s["entry_date"], "delay_trading_days": delay,
                    "exec_date": entry["date"], "exit_date": exit_rec["date"], "holding_days": h,
                    "market": s["market"], "stock_id": s["stock_id"], "stock_name": s["stock_name"], "industry": s["industry"],
                    "sur_3m": s.get("sur_3m"), "pre_ret_20d": s.get("pre_ret_20d"), "avg_turnover_20d": s.get("avg_turnover_20d"),
                    "margin_balance_pct_chg_5d": s.get("margin_balance_pct_chg_5d"), "margin_deleveraging_intensity": s.get("margin_deleveraging_intensity"),
                    "no_new_10d_low": s.get("no_new_10d_low"), "abnormal_turnover": s.get("abnormal_turnover"),
                    "entry_open": entry_open, "entry_close": entry_close, "exit_close": exit_px,
                    "possible_limit_up_nonfill": possible_limit_nonfill,
                    "gross_return": exit_px / entry_open - 1,
                    "net_return": exit_px / entry_open - 1 - COST,
                })
    return trades


def monthly_returns(trades: list[dict[str, Any]], variant: str, h: int, delay: int, months: list[str], subset: str = "all") -> list[float]:
    by: dict[str, list[float]] = defaultdict(list)
    for r in trades:
        if r["variant"] != variant or int(r["holding_days"]) != h or int(r["delay_trading_days"]) != delay:
            continue
        ind = str(r.get("industry", ""))
        if subset == "electronics" and "電子" not in ind and ind != "半導體業":
            continue
        if subset == "non_electronics" and ("電子" in ind or ind == "半導體業"):
            continue
        if subset == "semiconductor" and ind != "半導體業":
            continue
        if subset == "no_semiconductor" and ind == "半導體業":
            continue
        by[str(r["revenue_month"])].append(float(r["net_return"]))
    return [statistics.mean(by[m]) if by.get(m) else 0.0 for m in months]


def summarize(trades: list[dict[str, Any]], recipes: list[str], months: list[str]) -> list[dict[str, Any]]:
    out = []
    for v in recipes:
        for delay in DELAYS:
            for h in HOLDINGS:
                rows = [r for r in trades if r["variant"] == v and int(r["delay_trading_days"]) == delay and int(r["holding_days"]) == h]
                mm = metrics(monthly_returns(trades, v, h, delay, months))
                out.append({"variant": v, "delay_trading_days": delay, "holding_days": h, "cost": COST, "months_cash_counted": len(months), "active_months": len({r["revenue_month"] for r in rows}), "trades": len(rows), "avg_positions_all_months": len(rows) / len(months) if months else 0, "total_return": mm["total_return"], "ann_return": mm["ann_return"], "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"], "monthly_win_rate": mm["win_rate"], "best_month": mm.get("best_month"), "worst_month": mm.get("worst_month")})
    return out


def yearly(trades: list[dict[str, Any]], recipes: list[str]) -> list[dict[str, Any]]:
    out = []
    years = sorted({str(r["exec_date"])[:4] for r in trades})
    for v in recipes:
        for delay in DELAYS:
            for h in HOLDINGS:
                for y in years:
                    months = sorted({r["revenue_month"] for r in trades if str(r["exec_date"]).startswith(y)})
                    rs = monthly_returns([r for r in trades if str(r["exec_date"]).startswith(y)], v, h, delay, months)
                    mm = metrics(rs)
                    out.append({"variant": v, "delay_trading_days": delay, "holding_days": h, "year": y, "months": len(months), "total_return": mm["total_return"], "sharpe": mm["sharpe"], "mdd": mm["mdd"]})
    return out


def remove_winners(trades: list[dict[str, Any]], recipes: list[str], months: list[str]) -> list[dict[str, Any]]:
    out = []
    for v in recipes:
        for delay in [1]:
            for h in [20]:
                base = [r for r in trades if r["variant"] == v and int(r["delay_trading_days"]) == delay and int(r["holding_days"]) == h]
                sorted_trades = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
                for n in [0, 5, 10, 20]:
                    remove = {(r["stock_id"], r["exec_date"], r["holding_days"], r["variant"]) for r in sorted_trades[:n]}
                    kept = [r for r in base if (r["stock_id"], r["exec_date"], r["holding_days"], r["variant"]) not in remove]
                    rs = monthly_returns(kept, v, h, delay, months)
                    mm = metrics(rs)
                    out.append({"variant": v, "delay_trading_days": delay, "holding_days": h, "remove_top_n": n, "kept_trades": len(kept), "total_return": mm["total_return"], "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"]})
    return out


def sector_rows(trades: list[dict[str, Any]], recipes: list[str], months: list[str]) -> list[dict[str, Any]]:
    out=[]
    for v in recipes:
        for subset in ["all", "electronics", "non_electronics", "semiconductor", "no_semiconductor"]:
            rs = monthly_returns(trades, v, 20, 1, months, subset=subset)
            mm = metrics(rs)
            out.append({"variant": v, "subset": subset, "delay_trading_days": 1, "holding_days": 20, "total_return": mm["total_return"], "sharpe_cash_counted": mm["sharpe"], "mdd": mm["mdd"]})
    return out


def append_registry(best: dict[str, Any], remove: dict[str, Any]) -> None:
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 4.1 update" in text:
        return
    block = f"""
## Phase 4.1 update

- Tested FRR (`strong monthly-revenue surprise + recent margin deleveraging`) as a short-horizon research strategy using official TWSE/TPEx margin balances.
- Best first-pass FRR row: `{best.get('variant')}` delay `{best.get('delay_trading_days')}`, hold `{best.get('holding_days')}D`, return `{pct(best.get('total_return'))}`, Sharpe `{num(best.get('sharpe_cash_counted'))}`, MDD `{pct(best.get('mdd'))}`.
- Remove-top-10 stress for FRR-2 20D delay=1: return `{pct(remove.get('total_return'))}`, Sharpe `{num(remove.get('sharpe_cash_counted'))}`, MDD `{pct(remove.get('mdd'))}`.
- Registry status: S1 remains incumbent. FRR is retained as a **research-only timing/diagnostic candidate** unless it beats S1 under delay, remove-winner, sector, and liquidity gates.
"""
    REGISTRY.write_text(text.rstrip() + "\n" + block, encoding="utf-8")


def write_report(summary: list[dict[str, Any]], remove: list[dict[str, Any]], sector: list[dict[str, Any]], audit: dict[str, Any], th: dict[str, float]) -> None:
    ranked = sorted(summary, key=lambda r: (float(r.get("sharpe_cash_counted") or -999), float(r.get("total_return") or -999)), reverse=True)
    top = ranked[:10]
    frr2 = next((r for r in summary if r["variant"] == "frr2_no_catch_falling_knife" and int(r["delay_trading_days"]) == 1 and int(r["holding_days"]) == 20), {})
    frr2_r10 = next((r for r in remove if r["variant"] == "frr2_no_catch_falling_knife" and int(r["remove_top_n"]) == 10), {})
    lines = [
        "# Phase 4.1 — FRR margin-deleveraging short-horizon research",
        "",
        "Research-only. No live trading, no broker/API order routing, and no investment recommendation.",
        "",
        "## Hypothesis",
        "",
        "Because Taiwan short-horizon retail leverage can create forced supply, strong monthly-revenue surprise stocks that have already experienced margin deleveraging may rebound after the selling pressure is absorbed. The test enters only after the margin data is observable (next trading day open / delayed variants).",
        "",
        "## Data audit",
        "",
        f"- Margin feature rows: `{audit.get('margin_feature_rows')}`; enriched SUR core rows: `{audit.get('enriched_rows')}`; selected FRR signals: `{audit.get('selected_signals')}`; trades: `{audit.get('trades')}`.",
        f"- Thresholds: sur3_q70 `{th['sur3_q70']:.4f}`, margin_pct_q35 `{th['margin_pct_q35']:.2%}`, deleveraging_q65 `{th['delev_q65']:.4f}`, abnormal_turnover_q60 `{th['abturn_q60']:.2f}`.",
        "",
        "## Top first-pass rows",
        "",
    ]
    for r in top:
        lines.append(f"- `{r['variant']}` delay `{r['delay_trading_days']}` hold `{r['holding_days']}D`: return `{pct(r['total_return'])}`, Sharpe `{num(r['sharpe_cash_counted'])}`, MDD `{pct(r['mdd'])}`, trades `{r['trades']}`, active months `{r['active_months']}`.")
    lines += [
        "",
        "## Main candidate check: FRR-2 no-catch-falling-knife",
        "",
        f"- FRR-2 delay=1 hold=20D: return `{pct(frr2.get('total_return'))}`, Sharpe `{num(frr2.get('sharpe_cash_counted'))}`, MDD `{pct(frr2.get('mdd'))}`, trades `{frr2.get('trades')}`.",
        f"- Remove-top-10: return `{pct(frr2_r10.get('total_return'))}`, Sharpe `{num(frr2_r10.get('sharpe_cash_counted'))}`, MDD `{pct(frr2_r10.get('mdd'))}`.",
        "",
        "## Sector survival, delay=1, hold=20D",
        "",
    ]
    for r in sector:
        if r["variant"] == "frr2_no_catch_falling_knife":
            lines.append(f"- `{r['subset']}`: return `{pct(r['total_return'])}`, Sharpe `{num(r['sharpe_cash_counted'])}`, MDD `{pct(r['mdd'])}`.")
    lines += [
        "",
        "## Interpretation",
        "",
        "- FRR should be judged as a causal timing/diagnostic layer, not a replacement for S1 unless it survives remove-winner and sector checks.",
        "- If performance concentrates in electronics/semiconductor or collapses after removing top winners, classify it as research-only and retain S1 as incumbent.",
        "- Margin data is public official data, but it is only tradable after publication; therefore delay=1/2/3 rows are more important than same-day logic.",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    prices_by_stock, _price_key = build_price_maps(read_csv(DAILY))
    margin_by_key, margin_audit = build_margin_features(read_csv(MARGIN))
    signals = read_csv(SIGNALS)
    enriched, missing_audit = add_features(signals, prices_by_stock, margin_by_key)
    th = thresholds(enriched)
    recipes = ["frr1_basic_deleveraging", "frr2_no_catch_falling_knife", "frr3_volume_absorption", "frr5_conservative_liq100", "frr5_capacity_liq200"]
    selected = select_signals(enriched, recipes, th)
    trades = build_trades(selected, prices_by_stock)
    months = sorted({str(r["revenue_month"]) for r in enriched})
    summary = summarize(trades, recipes, months)
    yearly_rows = yearly(trades, recipes)
    remove_rows = remove_winners(trades, recipes, months)
    sector = sector_rows(trades, recipes, months)
    audit = dict(margin_audit)
    audit.update({"sur_core_signals": len([s for s in signals if s.get("recipe") == "sur_core"]), "enriched_rows": len(enriched), "missing_margin_rows": len(missing_audit), "selected_signals": len(selected), "trades": len(trades)})
    write_csv(OUT_TRADES, trades)
    write_csv(OUT_VARIANTS, summary)
    write_csv(OUT_YEARLY, yearly_rows)
    write_csv(OUT_REMOVE, remove_rows)
    write_csv(OUT_SECTOR, sector)
    write_csv(OUT_AUDIT, [audit] + missing_audit[:200])
    write_report(summary, remove_rows, sector, audit, th)
    ranked = sorted(summary, key=lambda r: (float(r.get("sharpe_cash_counted") or -999), float(r.get("total_return") or -999)), reverse=True)
    frr2_r10 = next((r for r in remove_rows if r["variant"] == "frr2_no_catch_falling_knife" and int(r["remove_top_n"]) == 10), {})
    if ranked:
        append_registry(ranked[0], frr2_r10)
    print(f"wrote {OUT_REPORT}")
    print(f"best: {ranked[0] if ranked else {}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
