#!/usr/bin/env python3
"""Phase 3.22: robustness checks for Phase 3.21 exact-timing delay sensitivity.

Research-only. No live trading, broker connection, or orders.

Adds remove-top-winners and sector survival diagnostics to the exact-timing delay
stress. This checks whether timing-delay resilience is broad enough to be useful,
or just another expression of a few electronics / semiconductor right-tail winners.
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
OUT_REMOVE = PROCESSED / "exact_timing_robustness_remove_winners.csv"
OUT_SECTOR = PROCESSED / "exact_timing_robustness_sector.csv"
OUT_REPORT = REPORTS / "phase3_22_exact_timing_robustness_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

P321_PATH = ROOT / "scripts" / "exact_timing_delay_sensitivity_gate.py"
spec = importlib.util.spec_from_file_location("exact_timing_delay_sensitivity_gate", P321_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {P321_PATH}")
p321 = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(p321)
p319 = p321.p319

COST = 0.010
DELAYS = [1, 3]
VARIANTS = ["equal_s1", "boost_quiet_no_large_black_150"]
REMOVE_NS = [0, 5, 10, 20]
ELECTRONICS = set(p319.ELECTRONICS)
SEMICONDUCTOR = p319.SEMICONDUCTOR


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
        return {"months": 0, "total_return": 0.0, "sharpe": None, "mdd": 0.0, "win_rate": None}
    sd = statistics.stdev(rs) if len(rs) >= 2 else None
    return {
        "months": len(rs),
        "total_return": compound(rs),
        "mean_month": statistics.mean(rs),
        "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd else None,
        "mdd": mdd(rs),
        "win_rate": sum(1 for x in rs if x > 0) / len(rs),
    }


def selected_trades(trades: list[dict[str, Any]], variant: str, delay: int, sector_pred: Callable[[dict[str, Any]], bool] | None = None, exclude_keys: set[tuple[str, str, str, int]] | None = None) -> dict[str, list[dict[str, Any]]]:
    by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in trades:
        if int(r["delay_trading_days"]) != delay:
            continue
        if r.get("possible_limit_up_nonfill"):
            continue
        if sector_pred is not None and not sector_pred(r):
            continue
        key = (str(r["revenue_month"]), str(r["stock_id"]), str(r["exec_date"]), int(r["delay_trading_days"]))
        if exclude_keys and key in exclude_keys:
            continue
        w = float(p321.variant_weight(r, variant))
        if w <= 0:
            continue
        r2 = dict(r); r2["weight"] = w; r2["net_return"] = float(r["gross_return"]) - COST
        by_month[r["revenue_month"]].append(r2)
    return by_month


def monthly_from_trades(by_month: dict[str, list[dict[str, Any]]], all_months: list[str]) -> tuple[list[float], float]:
    returns: list[float] = []
    positions: list[int] = []
    for m in all_months:
        rows = by_month.get(m, [])
        tw = sum(float(r["weight"]) for r in rows)
        ret = sum(float(r["weight"]) * float(r["net_return"]) for r in rows) / tw if tw > 0 else 0.0
        returns.append(ret); positions.append(len(rows))
    return returns, (statistics.mean(positions) if positions else 0.0)


def contribution_keys(trades: list[dict[str, Any]], variant: str, delay: int, all_months: list[str]) -> list[tuple[tuple[str, str, str, int], float, dict[str, Any]]]:
    by_month = selected_trades(trades, variant, delay)
    out: list[tuple[tuple[str, str, str, int], float, dict[str, Any]]] = []
    for m in all_months:
        rows = by_month.get(m, [])
        tw = sum(float(r["weight"]) for r in rows)
        if tw <= 0:
            continue
        for r in rows:
            contrib = float(r["weight"]) / tw * float(r["net_return"])
            key = (str(r["revenue_month"]), str(r["stock_id"]), str(r["exec_date"]), int(r["delay_trading_days"]))
            out.append((key, contrib, r))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def summarize_case(trades: list[dict[str, Any]], all_months: list[str], variant: str, delay: int, sector_name: str = "all", sector_pred: Callable[[dict[str, Any]], bool] | None = None, exclude_keys: set[tuple[str, str, str, int]] | None = None) -> dict[str, Any]:
    by_month = selected_trades(trades, variant, delay, sector_pred=sector_pred, exclude_keys=exclude_keys)
    rs, avg_pos = monthly_from_trades(by_month, all_months)
    mm = metrics(rs)
    return {
        "variant": variant,
        "delay_trading_days": delay,
        "cost": COST,
        "sector_slice": sector_name,
        "months_cash_counted": len(all_months),
        "active_months": sum(1 for m in all_months if by_month.get(m)),
        "avg_positions_all_months": avg_pos,
        "total_return": mm["total_return"],
        "sharpe_cash_counted": mm["sharpe"],
        "mdd": mm["mdd"],
        "monthly_win_rate": mm["win_rate"],
    }


def append_registry(focus: dict[str, dict[str, Any]]) -> None:
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.22 update" in text:
        return
    block = f"""
## Phase 3.22 update

- Added remove-winner and sector-survival diagnostics to Phase 3.21 exact-timing delay stress.
- Quiet boost delay=1 after remove-top-10 winners: return `{pct(focus['boost_d1_rm10'].get('total_return'))}`, Sharpe `{num(focus['boost_d1_rm10'].get('sharpe_cash_counted'))}`, MDD `{pct(focus['boost_d1_rm10'].get('mdd'))}`.
- Quiet boost delay=3 after remove-top-10 winners: return `{pct(focus['boost_d3_rm10'].get('total_return'))}`, Sharpe `{num(focus['boost_d3_rm10'].get('sharpe_cash_counted'))}`, MDD `{pct(focus['boost_d3_rm10'].get('mdd'))}`.
- Sector survival remains a gate: exact-timing robustness must be interpreted through electronics / semiconductor concentration, not promoted as broad-market alpha.
"""
    REGISTRY.write_text(text.rstrip() + "\n" + block, encoding="utf-8")


def main() -> int:
    signals, prices_by_stock, _date_map, all_months, _ctx = p319.make_signals()
    _raw_by_stock, raw_by_key, _raw_audit = p319.build_raw_lookup()
    trades = p321.build_delay_trades(signals, prices_by_stock, raw_by_key)

    remove_rows: list[dict[str, Any]] = []
    top_contrib_notes: dict[tuple[str, int], list[tuple[tuple[str, str, str, int], float, dict[str, Any]]]] = {}
    for variant in VARIANTS:
        for delay in DELAYS:
            contribs = contribution_keys(trades, variant, delay, all_months)
            top_contrib_notes[(variant, delay)] = contribs[:5]
            for n in REMOVE_NS:
                exclude = {k for k, _c, _r in contribs[:n]}
                row = summarize_case(trades, all_months, variant, delay, exclude_keys=exclude)
                row["remove_top_n_winners"] = n
                top_sum = sum(c for _k, c, _r in contribs[:n]) if n > 0 else 0.0
                row["removed_contribution_sum_monthly_return_points"] = top_sum
                remove_rows.append(row)

    sector_preds: list[tuple[str, Callable[[dict[str, Any]], bool] | None]] = [
        ("all", None),
        ("electronics_only", lambda r: r.get("industry") in ELECTRONICS),
        ("non_electronics", lambda r: r.get("industry") not in ELECTRONICS),
        ("semiconductor_only", lambda r: r.get("industry") == SEMICONDUCTOR),
        ("no_semiconductor", lambda r: r.get("industry") != SEMICONDUCTOR),
    ]
    sector_rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        for delay in DELAYS:
            for name, pred in sector_preds:
                sector_rows.append(summarize_case(trades, all_months, variant, delay, sector_name=name, sector_pred=pred))

    write_csv(OUT_REMOVE, remove_rows)
    write_csv(OUT_SECTOR, sector_rows)

    rem_lookup = {(r["variant"], int(r["delay_trading_days"]), int(r["remove_top_n_winners"])): r for r in remove_rows}
    sec_lookup = {(r["variant"], int(r["delay_trading_days"]), r["sector_slice"]): r for r in sector_rows}
    focus = {
        "boost_d1_rm10": rem_lookup[("boost_quiet_no_large_black_150", 1, 10)],
        "boost_d3_rm10": rem_lookup[("boost_quiet_no_large_black_150", 3, 10)],
    }
    append_registry(focus)

    lines: list[str] = [
        "# Phase 3.22 exact-timing robustness: remove-winners and sector survival\n\n",
        "Research-only proxy backtest；沒有 live trading、沒有 broker、沒有下單。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because Phase 3.21 found S1/quiet-boost did not collapse under 1–3 trading-day execution delay, therefore the next question is whether that resilience survives when the largest winners or the dominant electronics/semiconductor exposure are removed. If it fails these gates, delay robustness is a narrative support, not production robustness.\n\n",
        "### 前因後果\n\n",
        "- Monthly-revenue SUR alpha has repeatedly shown right-tail and Taiwan electronics / semiconductor supply-chain dependence.\n",
        "- 本輪用 Phase 3.21 的 official-open、1.0% cost、exclude limit-up risk 設定，只檢查 delay=1 與 delay=3，並做 remove-top-5/10/20 winners 與 sector slices。\n\n",
        "### 檢查\n\n",
        f"- Built robustness diagnostics from {len(trades)} delay-trade rows; cash months counted={len(all_months)}.\n",
        "- Top-winner removal ranks trade-level monthly return contribution after variant weights, not raw stock returns.\n\n",
        "### 結果：remove top winners\n\n",
    ]
    for variant in VARIANTS:
        for delay in DELAYS:
            lines.append(f"#### {variant} | delay={delay}\n")
            for n in REMOVE_NS:
                r = rem_lookup[(variant, delay, n)]
                lines.append(f"- remove_top_{n}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, avg_pos={float(r['avg_positions_all_months']):.2f}\n")
            lines.append("- top contributors: ")
            bits = []
            for _key, contrib, tr in top_contrib_notes[(variant, delay)][:3]:
                bits.append(f"{tr['stock_id']} {tr.get('stock_name')} {tr['revenue_month']} contrib={pct(contrib)}")
            lines.append("; ".join(bits) + "\n")

    lines.append("\n### 結果：sector survival\n\n")
    for variant in VARIANTS:
        for delay in DELAYS:
            lines.append(f"#### {variant} | delay={delay}\n")
            for sector in ["all", "electronics_only", "non_electronics", "semiconductor_only", "no_semiconductor"]:
                r = sec_lookup[(variant, delay, sector)]
                lines.append(f"- {sector}: return={pct(r['total_return'])}, Sharpe={num(r['sharpe_cash_counted'])}, MDD={pct(r['mdd'])}, active={r['active_months']}/{r['months_cash_counted']}, avg_pos={float(r['avg_positions_all_months']):.2f}\n")

    b1 = rem_lookup[("boost_quiet_no_large_black_150", 1, 10)]
    b3 = rem_lookup[("boost_quiet_no_large_black_150", 3, 10)]
    ne = sec_lookup[("boost_quiet_no_large_black_150", 1, "non_electronics")]
    nos = sec_lookup[("boost_quiet_no_large_black_150", 1, "no_semiconductor")]
    lines += [
        "\n### 修正與結論\n\n",
        "- 修正了什麼：Phase 3.21 只看 timing delay 後的 headline return/Sharpe；本輪加入 remove-winner 與 sector survival，避免把少數 right-tail winners 誤讀成 robust exact-timing edge。\n",
        "- 為什麼先前不夠好：延後進場不崩潰仍可能只是幾筆大贏家或半導體供應鏈 exposure 撐住。\n",
        f"- 修正後結論是否改變：不改變 promotion 結論。quiet boost delay=1 remove-top-10 後為 `{pct(b1['total_return'])}` / Sharpe `{num(b1['sharpe_cash_counted'])}`；delay=3 remove-top-10 後為 `{pct(b3['total_return'])}` / Sharpe `{num(b3['sharpe_cash_counted'])}`。non-electronics delay=1 為 `{pct(ne['total_return'])}` / Sharpe `{num(ne['sharpe_cash_counted'])}`，no-semiconductor delay=1 為 `{pct(nos['total_return'])}` / Sharpe `{num(nos['sharpe_cash_counted'])}`。因此 timing resilience 可作為 S1 narrative support，但仍不是 industry-survivable promotion。\n\n",
        "### 缺陷\n\n",
        "- Remove-winner contribution uses monthly weighted contribution proxy；真實 portfolio PnL attribution with overlapping holdings / cash drag still simplified。\n",
        "- Sector classifications are current/static labels, not fully historical；semiconductor supply-chain names outside the formal semiconductor industry may still dominate。\n",
        "- Still no exact company announcement timestamp or order-book fill evidence。\n\n",
        "### 下一步\n\n",
        "1. Exact timestamp sourcing remains the highest-priority gate.\n",
        "2. If delay>=2 becomes the realistic timing assumption, rerun Phase 3.20 walk-forward selection under delay=2/3 plus remove-winner penalty.\n",
        "3. Add historical sector / supply-chain tags to separate formal semiconductor from broader electronics exposure.\n\n",
        "## Outputs\n\n",
        f"- `{OUT_REMOVE}`\n",
        f"- `{OUT_SECTOR}`\n",
        f"- `{OUT_REPORT}`\n",
        f"- `{REGISTRY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")

    print(json.dumps({"outputs": [str(OUT_REMOVE), str(OUT_SECTOR), str(OUT_REPORT)], "focus": focus}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
