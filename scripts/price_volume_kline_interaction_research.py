#!/usr/bin/env python3
"""Phase 3.16: causal price/volume x K-line interaction diagnostics.

Research-only. No live trading, broker connection, or orders.

Question: after Taiwan monthly-revenue SUR, is volume expansion helpful only when
entry-day OHLC shows genuine demand absorption (close not weak / no long upper
shadow), and harmful when paired with supply-pressure candles?
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
OUT_VARIANTS = PROCESSED / "price_volume_kline_interaction_variants.csv"
OUT_REMOVE = PROCESSED / "price_volume_kline_interaction_remove_winners.csv"
OUT_YEARLY = PROCESSED / "price_volume_kline_interaction_yearly.csv"
OUT_REPORT = REPORTS / "phase3_16_price_volume_kline_interaction_report.md"

KL_PATH = ROOT / "scripts" / "kline_ohlc_audit_research.py"
spec = importlib.util.spec_from_file_location("kline_ohlc_audit_research", KL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {KL_PATH}")
kl = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(kl)
pa = kl.pa
sur = kl.sur

HOLDING = 20
COST = 0.007
LIQ = 50_000_000
TOP_N = 8
IND_CAP = 3
ELECTRONICS = kl.ELECTRONICS


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def attach_entry_ohlc(scored: list[dict[str, Any]]) -> dict[str, Any]:
    ohlc_by_stock, audit = kl.load_ohlc()
    upper_vals: list[float] = []
    close_loc_vals: list[float] = []
    range_vals: list[float] = []
    body_vals: list[float] = []
    matched = ohlc_matched = 0
    market_to_raw = {"otc": "tpex", "listed": "twse", "twse": "twse", "tpex": "tpex"}
    for r in scored:
        raw_market = market_to_raw.get(r["market"], r["market"])
        rec = next((x for x in ohlc_by_stock.get((raw_market, r["stock_id"]), []) if x["date"] == r["entry_date"]), None)
        if not rec:
            continue
        matched += 1
        r.update({f"entry_{k}": rec.get(k) for k in ["open", "high", "low", "close", "volume", "next_up_limit", "next_down_limit"]})
        if rec.get("open") is None or rec.get("high") is None or rec.get("low") is None:
            continue
        ohlc_matched += 1
        high = float(rec["high"]); low = float(rec["low"]); close = float(rec["close"]); open_ = float(rec["open"])
        denom = high - low
        rng = (high - low) / close if close else 0.0
        close_loc = (close - low) / denom if denom > 0 else 0.5
        upper = (high - max(open_, close)) / denom if denom > 0 else 0.0
        body = abs(close - open_) / denom if denom > 0 else 0.0
        r.update({
            "entry_range_pct": rng,
            "entry_close_location": close_loc,
            "entry_upper_shadow_ratio": upper,
            "entry_body_ratio": body,
            "entry_black_candle": close < open_,
        })
        upper_vals.append(upper); close_loc_vals.append(close_loc); range_vals.append(rng); body_vals.append(body)
    return {
        "audit": audit,
        "matched": matched,
        "ohlc_matched": ohlc_matched,
        "upper_hi": kl.q(upper_vals, 0.67),
        "close_low": kl.q(close_loc_vals, 0.33),
        "range_low": kl.q(range_vals, 0.33),
        "body_hi": kl.q(body_vals, 0.67),
    }


def main() -> int:
    pa.HOLDINGS = [HOLDING]; pa.COST = COST; pa.BASE_TOP_N = TOP_N; pa.BASE_INDUSTRY_CAP = IND_CAP; pa.LIQ = LIQ
    sur.HOLDINGS = [HOLDING]; sur.COST = COST; sur.TOP_N = TOP_N; sur.INDUSTRY_CAP = IND_CAP; sur.MIN_AVG_TURNOVER_20D = LIQ

    scored, prices_by_stock, date_map, _counts = pa.build_scored()
    th = pa.thresholds(scored)
    all_months = sorted({r["revenue_month"] for r in scored})
    audit = attach_entry_ohlc(scored)
    vol_low = th["abnormal_turnover"][0]
    vol_high = th["abnormal_turnover"][1]
    mom_low, mom_high = th["momentum_120_20"]

    base = lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= mom_high and r.get("entry_close_location") is not None
    no_supply = lambda r: r["entry_upper_shadow_ratio"] < audit["upper_hi"] and r["entry_close_location"] > audit["close_low"]
    supply = lambda r: r["entry_upper_shadow_ratio"] >= audit["upper_hi"] or r["entry_close_location"] <= audit["close_low"]
    quiet = lambda r: r["entry_range_pct"] <= audit["range_low"]
    large_black = lambda r: bool(r["entry_black_candle"]) and r["entry_body_ratio"] >= audit["body_hi"]
    not_hot = lambda r: r["pre_ret_20d"] <= mom_high

    filters = [
        ("s1_fixed20_ohlc_baseline", lambda r: base(r)),
        ("vol_high_no_supply", lambda r: base(r) and r["abnormal_turnover"] >= vol_high and no_supply(r)),
        ("vol_high_supply_pressure", lambda r: base(r) and r["abnormal_turnover"] >= vol_high and supply(r)),
        ("vol_low_quiet_digestion", lambda r: base(r) and r["abnormal_turnover"] <= vol_low and quiet(r)),
        ("vol_high_no_supply_electronics", lambda r: base(r) and r["industry"] in ELECTRONICS and r["abnormal_turnover"] >= vol_high and no_supply(r)),
        ("vol_high_no_supply_non_electronics", lambda r: base(r) and r["industry"] not in ELECTRONICS and r["abnormal_turnover"] >= vol_high and no_supply(r)),
        ("vol_high_no_supply_not_hot20d", lambda r: base(r) and r["abnormal_turnover"] >= vol_high and no_supply(r) and not_hot(r)),
        ("vol_high_large_black", lambda r: base(r) and r["abnormal_turnover"] >= vol_high and large_black(r)),
    ]
    signals: list[dict[str, Any]] = []
    counts_by_recipe: dict[str, int] = {}
    recipes: list[str] = []
    for name, pred in filters:
        sigs = kl.select(scored, name, pred)
        signals.extend(sigs); counts_by_recipe[name] = len(sigs); recipes.append(name)
    trades = sur.build_trades(signals, prices_by_stock, date_map)
    variants = kl.summarize(trades, recipes, counts_by_recipe, all_months)
    remove = kl.remove_winners(trades, recipes, all_months)
    yrs = kl.yearly(trades, recipes, all_months)

    write_csv(OUT_VARIANTS, variants)
    write_csv(OUT_REMOVE, remove)
    write_csv(OUT_YEARLY, yrs)

    by = {r["recipe"]: r for r in variants}
    lines = [
        "# Phase 3.16 price/volume × K-line interaction diagnostics\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 本輪假說\n\n",
        "月營收 SUR 後，成交值擴張本身不是 alpha；若放量同時收盤位置不弱、沒有長上影，才代表需求吸收供給並延續再定價。若放量伴隨長上影/弱收盤/大黑 K，則比較像事件擁擠或供給壓力，後續 20D 應較脆弱。\n\n",
        "## Thresholds and data coverage\n\n",
        f"- abnormal turnover low/high tercile = {vol_low:.4f} / {vol_high:.4f}\n",
        f"- entry upper-shadow high tercile = {audit['upper_hi']:.4f}; close-location low tercile = {audit['close_low']:.4f}; range low tercile = {audit['range_low']:.4f}; body high tercile = {audit['body_hi']:.4f}\n",
        f"- scored rows with entry close/OHLC matched = {audit['matched']}/{len(scored)} / {audit['ohlc_matched']}/{len(scored)}\n\n",
        "## Variant summary（20D fixed exit, inactive months counted as cash）\n\n",
    ]
    for name in recipes:
        r = by[name]
        lines.append(f"- `{name}`: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}, avg_pos={float(r['avg_positions_all_months']):.2f}, trades={r['trades']}\n")
    lines.append("\n## Remove-winner stress\n\n")
    for name in recipes:
        vals = [r for r in remove if r["recipe"] == name]
        lines.append(f"### {name}\n")
        for r in vals:
            lines.append(f"- remove {r['remove_top_winners']}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, trades={r['trades']}\n")
    lines.append("\n## Year split\n\n")
    for name in recipes[:4]:
        lines.append(f"### {name}\n")
        for r in [x for x in yrs if x["recipe"] == name]:
            lines.append(f"- {r['year']}: return={pct(r['return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}\n")
    lines += [
        "\n## Interpretation\n\n",
        "- Promotion gate: a volume/K-line interaction must beat or clearly de-risk S1 fixed-20 and survive remove-top-winners; otherwise it remains diagnostic only.\n",
        "- If `vol_high_no_supply` beats `vol_high_supply_pressure`, causal reading is demand absorption after revenue surprise. If it does not, entry-day K-line confirmation is not currently adding signal quality.\n",
        "- Low average positions / few active months are treated as fragility, not Sharpe improvement.\n",
        "- This remains daily OHLC proxy research: no intraday breakout, queue priority, exact announcement timestamp, or next-day limit non-fill simulation.\n\n",
        "## Outputs\n\n",
    ]
    for p in [OUT_VARIANTS, OUT_REMOVE, OUT_YEARLY, OUT_REPORT]:
        lines.append(f"- `{p}`\n")
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")
    print(json.dumps({"outputs": [str(OUT_VARIANTS), str(OUT_REMOVE), str(OUT_YEARLY), str(OUT_REPORT)], "thresholds": {"vol_low": vol_low, "vol_high": vol_high, **{k: audit[k] for k in ["upper_hi", "close_low", "range_low", "body_hi"]}}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
