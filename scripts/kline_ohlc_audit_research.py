#!/usr/bin/env python3
"""Phase 3.15: OHLC/K-line data audit and first causal K-line diagnostics.

Research-only. No live trading, no broker connection, no orders.

Goal: verify whether raw official daily files contain enough OHLC/limit fields to
move beyond close/turnover proxies, then test only interpretable entry-day K-line
states for the existing S1 universe:
- long upper shadow / weak close location => supply pressure after revenue repricing
- black/large down candle => failed repricing or distribution pressure
- narrow-range quiet day => possible digestion before delayed repricing

All tests are close/official-daily proxy diagnostics. They are not executable
intraday simulations and do not model limit-up/down non-fills.
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
RAW = ROOT / "data" / "raw" / "market_history_daily"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT_AUDIT = PROCESSED / "kline_ohlc_audit_summary.csv"
OUT_VARIANTS = PROCESSED / "kline_entry_state_variants.csv"
OUT_REMOVE = PROCESSED / "kline_entry_state_remove_winners.csv"
OUT_YEARLY = PROCESSED / "kline_entry_state_yearly.csv"
OUT_REPORT = REPORTS / "phase3_15_kline_ohlc_audit_report.md"

PA_PATH = ROOT / "scripts" / "price_action_filter_tests.py"
spec = importlib.util.spec_from_file_location("price_action_filter_tests", PA_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {PA_PATH}")
pa = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(pa)
sur = pa.sur

HOLDING = 20
COST = 0.007
LIQ = 50_000_000
TOP_N = 8
IND_CAP = 3
ELECTRONICS = {"半導體業", "電子零組件業", "電腦及週邊設備業", "光電業", "通信網路業", "電子通路業", "其他電子業", "資訊服務業"}


def parse_num(x: Any) -> float | None:
    if x is None:
        return None
    s = str(x).strip().replace(",", "")
    if not s or s in {"--", "---", "除權", "除息", "除權息"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def norm_code(x: Any) -> str:
    return str(x).strip()


def row_to_record(market: str, date: str, fields: list[str], row: list[Any]) -> dict[str, Any] | None:
    fmap = {f.strip(): i for i, f in enumerate(fields)}
    def get(*names: str) -> Any:
        for name in names:
            key = name.strip()
            if key in fmap and fmap[key] < len(row):
                return row[fmap[key]]
        return None

    stock_id = norm_code(get("證券代號", "代號"))
    if not stock_id or not stock_id[:1].isdigit():
        return None
    # Keep common-stock-like numeric ids only; ETFs/bonds are excluded by requiring 4 digits.
    if not (len(stock_id) == 4 and stock_id.isdigit()):
        return None
    close = parse_num(get("收盤價", "收盤"))
    open_ = parse_num(get("開盤價", "開盤"))
    high = parse_num(get("最高價", "最高"))
    low = parse_num(get("最低價", "最低"))
    value = parse_num(get("成交金額", "成交金額(元)", "成交金額(元)"))
    volume = parse_num(get("成交股數", "成交股數"))
    up_limit = parse_num(get("次日漲停價"))
    down_limit = parse_num(get("次日跌停價"))
    if close is None:
        return None
    return {
        "date": date, "market": market, "stock_id": stock_id,
        "open": open_, "high": high, "low": low, "close": close,
        "turnover_value": value, "volume": volume,
        "next_up_limit": up_limit, "next_down_limit": down_limit,
    }


def load_ohlc() -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    by_stock: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    audit: list[dict[str, Any]] = []
    for market in ["twse", "tpex"]:
        folder = RAW / market
        files = sorted(folder.glob("*.json")) if folder.exists() else []
        file_count = row_count = ohlc_count = limit_count = 0
        for path in files:
            file_count += 1
            date = path.stem
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for table in obj.get("tables", []):
                fields = table.get("fields") or []
                data = table.get("data") or []
                if not fields or not data:
                    continue
                for row in data:
                    rec = row_to_record(market, date, [str(f) for f in fields], row)
                    if rec is None:
                        continue
                    row_count += 1
                    if rec["open"] is not None and rec["high"] is not None and rec["low"] is not None:
                        ohlc_count += 1
                    if rec["next_up_limit"] is not None and rec["next_down_limit"] is not None:
                        limit_count += 1
                    by_stock[(market, rec["stock_id"])].append(rec)
        audit.append({
            "market": market, "raw_json_files": file_count, "common_stock_rows": row_count,
            "ohlc_rows": ohlc_count, "ohlc_coverage": ohlc_count / row_count if row_count else 0,
            "next_limit_rows": limit_count, "next_limit_coverage": limit_count / row_count if row_count else 0,
        })
    for key in by_stock:
        by_stock[key].sort(key=lambda r: r["date"])
    return by_stock, audit


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def q(vals: list[float], p: float) -> float:
    vals = sorted(v for v in vals if not math.isnan(v))
    i = (len(vals) - 1) * p
    lo, hi = math.floor(i), math.ceil(i)
    return vals[lo] if lo == hi else vals[lo] * (hi - i) + vals[hi] * (i - lo)


def compound(rs: list[float]) -> float:
    nav = 1.0
    for r in rs:
        nav *= 1 + r
    return nav - 1


def mdd(rs: list[float]) -> float:
    nav = peak = 1.0; worst = 0.0
    for r in rs:
        nav *= 1 + r; peak = max(peak, nav); worst = min(worst, nav / peak - 1)
    return worst


def metrics(monthly: list[float]) -> dict[str, Any]:
    if not monthly:
        return {"months": 0, "total_return": 0.0, "sharpe": None, "mdd": 0.0, "win_rate": None}
    sd = statistics.stdev(monthly) if len(monthly) >= 2 else None
    total = compound(monthly)
    return {"months": len(monthly), "total_return": total, "ann_return": (1 + total) ** (12 / len(monthly)) - 1,
            "sharpe": statistics.mean(monthly) / sd * math.sqrt(12) if sd else None,
            "mdd": mdd(monthly), "win_rate": sum(1 for x in monthly if x > 0) / len(monthly)}


def monthly_returns(trades: list[dict[str, Any]], recipe: str, all_months: list[str]) -> list[float]:
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in trades:
        if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
            by_month[r["revenue_month"]].append(float(r["net_return"]))
    return [statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in all_months]


def select(scored: list[dict[str, Any]], name: str, pred) -> list[dict[str, Any]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in scored:
        if pred(r):
            by_month[r["revenue_month"]].append(r)
    out = []
    for month in sorted(by_month):
        counts: dict[str, int] = defaultdict(int)
        selected = 0
        for r in sorted(by_month[month], key=lambda x: x["score_sur_core"], reverse=True):
            if counts[r["industry"]] >= IND_CAP:
                continue
            r2 = dict(r); r2["recipe"] = name; r2["score"] = r["score_sur_core"]
            out.append(r2); counts[r["industry"]] += 1; selected += 1
            if selected >= TOP_N:
                break
    return out


def summarize(trades: list[dict[str, Any]], recipes: list[str], signal_counts: dict[str, int], all_months: list[str]) -> list[dict[str, Any]]:
    rows = []
    for recipe in recipes:
        base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        mm = metrics(monthly_returns(trades, recipe, all_months))
        rows.append({"recipe": recipe, "months_cash_counted": len(all_months), "signals": signal_counts.get(recipe, 0),
                     "trades": len(base), "active_months": len({r["revenue_month"] for r in base}),
                     "avg_positions_all_months": len(base) / len(all_months) if all_months else 0,
                     "total_return": mm.get("total_return"), "ann_return": mm.get("ann_return"),
                     "sharpe_cash_counted": mm.get("sharpe"), "mdd": mm.get("mdd"), "win_rate": mm.get("win_rate")})
    return rows


def remove_winners(trades: list[dict[str, Any]], recipes: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    out = []
    for recipe in recipes:
        base = [r for r in trades if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING]
        ranked = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
        for n in [0, 5, 10, 20]:
            kill = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in ranked[:n]}
            kept = [r for r in base if (r["revenue_month"], r["stock_id"], r["entry_date"]) not in kill]
            by_month: dict[str, list[float]] = defaultdict(list)
            for r in kept:
                by_month[r["revenue_month"]].append(float(r["net_return"]))
            mm = metrics([statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in all_months])
            out.append({"recipe": recipe, "remove_top_winners": n, "trades": len(kept), "total_return": mm.get("total_return"), "sharpe_cash_counted": mm.get("sharpe"), "mdd": mm.get("mdd")})
    return out


def yearly(trades: list[dict[str, Any]], recipes: list[str], all_months: list[str]) -> list[dict[str, Any]]:
    months_by_year: dict[str, list[str]] = defaultdict(list)
    for m in all_months:
        months_by_year[m[:4]].append(m)
    out = []
    for recipe in recipes:
        by_month: dict[str, list[float]] = defaultdict(list)
        for r in trades:
            if r["recipe"] == recipe and int(r["holding_days"]) == HOLDING:
                by_month[r["revenue_month"]].append(float(r["net_return"]))
        for year, months in sorted(months_by_year.items()):
            mm = metrics([statistics.mean(by_month[m]) if by_month.get(m) else 0.0 for m in months])
            out.append({"recipe": recipe, "year": year, "months_cash_counted": len(months), "active_months": sum(1 for m in months if by_month.get(m)), "return": mm.get("total_return"), "sharpe_cash_counted": mm.get("sharpe"), "mdd": mm.get("mdd")})
    return out


def pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def main() -> int:
    pa.HOLDINGS = [HOLDING]; pa.COST = COST; pa.BASE_TOP_N = TOP_N; pa.BASE_INDUSTRY_CAP = IND_CAP; pa.LIQ = LIQ
    sur.HOLDINGS = [HOLDING]; sur.COST = COST; sur.TOP_N = TOP_N; sur.INDUSTRY_CAP = IND_CAP; sur.MIN_AVG_TURNOVER_20D = LIQ
    ohlc_by_stock, audit = load_ohlc()
    scored, prices_by_stock, date_map, counts = pa.build_scored()
    th = pa.thresholds(scored)
    all_months = sorted({r["revenue_month"] for r in scored})

    matched = 0; ohlc_matched = 0
    upper_vals = []; body_vals = []; range_vals = []; close_loc_vals = []
    market_to_raw = {"otc": "tpex", "listed": "twse", "twse": "twse", "tpex": "tpex"}
    for r in scored:
        raw_market = market_to_raw.get(r["market"], r["market"])
        key = (raw_market, r["stock_id"])
        rows = ohlc_by_stock.get(key, [])
        rec = next((x for x in rows if x["date"] == r["entry_date"]), None)
        if rec:
            matched += 1
            r.update({f"entry_{k}": rec.get(k) for k in ["open", "high", "low", "close", "volume", "next_up_limit", "next_down_limit"]})
            if rec.get("open") is not None and rec.get("high") is not None and rec.get("low") is not None:
                ohlc_matched += 1
                high = float(rec["high"]); low = float(rec["low"]); close = float(rec["close"]); open_ = float(rec["open"])
                rng = (high - low) / close if close else 0.0
                denom = high - low
                close_loc = (close - low) / denom if denom > 0 else 0.5
                upper = (high - max(open_, close)) / denom if denom > 0 else 0.0
                body = abs(close - open_) / denom if denom > 0 else 0.0
                black = close < open_
                r.update({"entry_range_pct": rng, "entry_close_location": close_loc, "entry_upper_shadow_ratio": upper, "entry_body_ratio": body, "entry_black_candle": black})
                range_vals.append(rng); close_loc_vals.append(close_loc); upper_vals.append(upper); body_vals.append(body)
            else:
                r.update({"entry_range_pct": None, "entry_close_location": None, "entry_upper_shadow_ratio": None, "entry_body_ratio": None, "entry_black_candle": None})

    for a in audit:
        scored_for_market = [r for r in scored if market_to_raw.get(r["market"], r["market"]) == a["market"]]
        a["scored_signals"] = len(scored_for_market)
        a["entry_date_rows_matched"] = len([r for r in scored_for_market if r.get("entry_close") is not None])
        a["entry_date_ohlc_matched"] = len([r for r in scored_for_market if r.get("entry_open") is not None and r.get("entry_high") is not None and r.get("entry_low") is not None])

    upper_hi = q(upper_vals, 0.67); close_low = q(close_loc_vals, 0.33); range_low = q(range_vals, 0.33); body_hi = q(body_vals, 0.67)
    base = lambda r: r["sur_3m"] >= th["sur_3m"][1] and r["momentum_120_20"] <= th["momentum_120_20"][1]
    has_ohlc = lambda r: r.get("entry_close_location") is not None
    filters = [
        ("s1_baseline_ohlc_available", lambda r: base(r) and has_ohlc(r)),
        ("kline_no_supply_pressure", lambda r: base(r) and has_ohlc(r) and r["entry_upper_shadow_ratio"] < upper_hi and r["entry_close_location"] > close_low),
        ("kline_supply_pressure", lambda r: base(r) and has_ohlc(r) and (r["entry_upper_shadow_ratio"] >= upper_hi or r["entry_close_location"] <= close_low)),
        ("kline_quiet_narrow_range", lambda r: base(r) and has_ohlc(r) and r["entry_range_pct"] <= range_low),
        ("kline_large_black", lambda r: base(r) and has_ohlc(r) and r["entry_black_candle"] and r["entry_body_ratio"] >= body_hi),
        ("kline_electronics_no_supply", lambda r: base(r) and has_ohlc(r) and r["industry"] in ELECTRONICS and r["entry_upper_shadow_ratio"] < upper_hi and r["entry_close_location"] > close_low),
        ("kline_nonelectronics_no_supply", lambda r: base(r) and has_ohlc(r) and r["industry"] not in ELECTRONICS and r["entry_upper_shadow_ratio"] < upper_hi and r["entry_close_location"] > close_low),
    ]
    signals = []; counts_by_recipe = {}; recipes = []
    for name, pred in filters:
        sigs = select(scored, name, pred)
        signals.extend(sigs); counts_by_recipe[name] = len(sigs); recipes.append(name)
    trades = sur.build_trades(signals, prices_by_stock, date_map)
    variants = summarize(trades, recipes, counts_by_recipe, all_months)
    remove = remove_winners(trades, recipes, all_months)
    yrs = yearly(trades, recipes, all_months)

    write_csv(OUT_AUDIT, audit)
    write_csv(OUT_VARIANTS, variants)
    write_csv(OUT_REMOVE, remove)
    write_csv(OUT_YEARLY, yrs)

    by = {r["recipe"]: r for r in variants}
    lines = [
        "# Phase 3.15 OHLC/K-line data audit and entry-state diagnostics\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 本輪假說\n\n",
        "月營收 SUR 後，若 entry-day K 線已出現長上影、弱收盤位置或大黑 K，可能代表好消息公布後的供給壓力/出貨，後續 20D 報酬應較差；反之，沒有明顯供給壓力或窄幅整理，較符合 surprise 尚在被消化的延遲再定價。\n\n",
        "## Data audit\n\n",
    ]
    for a in audit:
        lines.append(f"- `{a['market']}`: raw_files={a['raw_json_files']}, common_stock_rows={a['common_stock_rows']}, OHLC coverage={pct(a['ohlc_coverage'])}, next-limit coverage={pct(a['next_limit_coverage'])}, scored entry OHLC matched={a['entry_date_ohlc_matched']}/{a['scored_signals']}\n")
    lines += [
        f"- overall scored entry rows matched: close={matched}/{len(scored)}, OHLC={ohlc_matched}/{len(scored)}\n\n",
        "## Thresholds from available entry-day OHLC\n\n",
        f"- upper-shadow high tercile = {upper_hi:.4f}\n",
        f"- close-location low tercile = {close_low:.4f}\n",
        f"- range-pct low tercile = {range_low:.4f}\n",
        f"- body-ratio high tercile = {body_hi:.4f}\n\n",
        "## Variant summary（20D fixed exit, inactive months counted as cash）\n\n",
    ]
    for name in recipes:
        r = by[name]
        lines.append(f"- `{name}`: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}, avg_pos={float(r['avg_positions_all_months']):.2f}, trades={r['trades']}\n")
    lines.append("\n## Remove-winner stress\n\n")
    for name in recipes[:5]:
        vals = [r for r in remove if r["recipe"] == name]
        lines.append(f"### {name}\n")
        for r in vals:
            lines.append(f"- remove {r['remove_top_winners']}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, trades={r['trades']}\n")
    lines.append("\n## Year split\n\n")
    for name in recipes[:5]:
        lines.append(f"### {name}\n")
        for r in [x for x in yrs if x["recipe"] == name]:
            lines.append(f"- {r['year']}: return={pct(r['return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}\n")
    lines += [
        "\n## Interpretation\n\n",
        "- 這是第一輪真正使用 raw official OHLC 的 K-line audit；若 coverage 足夠，後續可以把 Phase 3.13 的『不能測 K 線』限制縮小為『可以測日線 OHLC，但仍不能測盤中突破與真實成交排隊』。\n",
        "- `kline_no_supply_pressure` 若優於 `kline_supply_pressure`，代表 K 線狀態可能是 fundamental surprise 後的供給壓力過濾器，而不是獨立 alpha。\n",
        "- 若 `kline_large_black` 很差，符合 failed repricing / distribution 的市場結構敘事；但樣本數與 remove-winner 必須過關才可升級。\n",
        "- 本輪仍未模擬公告時點、隔日開盤可成交性、漲跌停 non-fill 與 intraday slippage，因此不應升級為 production execution rule。\n\n",
        "## Outputs\n\n",
    ]
    for p in [OUT_AUDIT, OUT_VARIANTS, OUT_REMOVE, OUT_YEARLY, OUT_REPORT]:
        lines.append(f"- `{p}`\n")
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")
    print(json.dumps({"audit": audit, "thresholds": {"upper_hi": upper_hi, "close_low": close_low, "range_low": range_low, "body_hi": body_hi}, "outputs": [str(OUT_AUDIT), str(OUT_VARIANTS), str(OUT_REMOVE), str(OUT_YEARLY), str(OUT_REPORT)]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
