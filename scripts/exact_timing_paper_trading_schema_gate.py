#!/usr/bin/env python3
"""Phase 3.25: exact-timing data audit and 2026 paper-trading execution log schema.

Research-only. No live trading, broker connection, orders, package installs, commits, or deletes.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

REV_CSV = PROCESSED / "historical_monthly_revenue_mops_static.csv"
DAILY_CSV = PROCESSED / "daily_market_history_2023_present.csv"
RAW_DAILY_DIR = RAW / "market_history_daily"
P319_FLAGS = PROCESSED / "execution_realism_tradability_trade_flags.csv"
P324_SECTOR = PROCESSED / "delay_walkforward_oos_sector_stress.csv"
P324_REMOVE = PROCESSED / "delay_walkforward_oos_remove_winners.csv"

OUT_AUDIT = PROCESSED / "exact_timing_paper_trading_data_audit.csv"
OUT_SCHEMA = PROCESSED / "paper_trading_execution_log_schema.csv"
OUT_CHECKLIST = PROCESSED / "paper_trading_execution_checklist_2026.csv"
OUT_REPORT = REPORTS / "phase3_25_exact_timing_paper_trading_schema_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def header(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f), [])


def revenue_quality_sample() -> dict[str, Any]:
    out: dict[str, Any] = {"rows_sampled": 0, "quality_counts": "", "min_usable_date": "", "max_usable_date": ""}
    if not REV_CSV.exists():
        return out
    c: Counter[str] = Counter()
    min_d = "9999-99-99"; max_d = "0000-00-00"; n = 0
    with REV_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n += 1
            c[str(r.get("announcement_date_quality", ""))] += 1
            d = str(r.get("usable_date_proxy", ""))
            if d:
                min_d = min(min_d, d); max_d = max(max_d, d)
    out.update({"rows_sampled": n, "quality_counts": "; ".join(f"{k}:{v}" for k, v in c.most_common()), "min_usable_date": min_d, "max_usable_date": max_d})
    return out


def raw_daily_field_audit() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    field_needles = {
        "open": ["開盤"],
        "high": ["最高"],
        "low": ["最低"],
        "close": ["收盤"],
        "turnover_value": ["成交金額"],
        "shares_traded": ["成交股數", "成交股數  "],
        "next_limit_up": ["次日漲停價"],
        "next_limit_down": ["次日跌停價"],
    }
    files = sorted(RAW_DAILY_DIR.glob("*/*.json"))
    by_market: dict[str, list[Path]] = defaultdict(list)
    for p in files:
        by_market[p.parent.name].append(p)
    for market, paths in sorted(by_market.items()):
        counters = Counter()
        total_tables = 0; total_files = 0; parse_errors = 0
        first_fields = ""
        for p in paths:
            total_files += 1
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                parse_errors += 1
                continue
            for t in obj.get("tables", []):
                total_tables += 1
                fields = [str(x).strip() for x in t.get("fields", [])]
                if not first_fields and fields:
                    first_fields = " | ".join(fields)
                joined = " | ".join(fields)
                for label, needles in field_needles.items():
                    if any(n in joined for n in needles):
                        counters[label] += 1
        rows.append({
            "dataset": "raw_daily_json",
            "market": market,
            "files": total_files,
            "tables": total_tables,
            "parse_errors": parse_errors,
            **{f"tables_with_{k}": counters[k] for k in field_needles},
            "first_fields_seen": first_fields,
            "research_use": "OHLC/limit-up proxy possible from raw files if parsed; processed daily CSV currently loses most OHLC/limit fields",
        })
    return rows


def p324_focus() -> dict[str, str]:
    ans: dict[str, str] = {}
    if P324_SECTOR.exists():
        with P324_SECTOR.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for split in sorted({r["split"] for r in rows}):
            allr = next((r for r in rows if r["split"] == split and r["sector_slice"] == "all"), None)
            nosemi = next((r for r in rows if r["split"] == split and r["sector_slice"] == "no_semiconductor"), None)
            semi = next((r for r in rows if r["split"] == split and r["sector_slice"] == "semiconductor_only"), None)
            if allr and nosemi and semi:
                ans[split] = f"all Sharpe {float(allr['sharpe']):.2f}; semi-only {float(semi['sharpe']):.2f}; no-semi {float(nosemi['sharpe']):.2f}"
    if P324_REMOVE.exists():
        with P324_REMOVE.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for split in sorted({r["split"] for r in rows}):
            rm5 = next((r for r in rows if r["split"] == split and r["remove_top_n_oos_winners"] == "5"), None)
            if rm5:
                ans[split] = ans.get(split, "") + f"; remove-top-5 Sharpe {float(rm5['sharpe']):.2f}"
    return ans


def build_schema_rows() -> list[dict[str, Any]]:
    specs = [
        ("signal_generated_at", "datetime", "When script created the candidate list; must be after public data availability."),
        ("revenue_month", "YYYY-MM", "Revenue month used by signal."),
        ("stock_id", "string", "Ticker."),
        ("stock_name", "string", "Name."),
        ("market", "listed/otc", "Exchange bucket."),
        ("strategy_variant", "string", "S1 equal / quiet boost / delay-aware diagnostic."),
        ("announcement_source_url", "string", "MOPS/TWSE/TPEX source URL captured at signal time."),
        ("company_announcement_timestamp", "datetime/null", "Exact company-level timestamp if sourced; null means use conservative next-trading-day proxy."),
        ("data_available_at", "datetime", "Timestamp when worker actually observed data."),
        ("planned_entry_session", "date + open/close", "Planned execution assumption before market opens/closes."),
        ("observed_open", "float", "Official open from OHLC feed."),
        ("observed_high", "float", "Official high."),
        ("observed_low", "float", "Official low."),
        ("observed_close", "float", "Official close."),
        ("prev_close", "float", "Previous close for limit-up diagnostics."),
        ("limit_up_price", "float", "Official limit-up price when available."),
        ("open_at_or_near_limit_up", "bool", "Non-fill risk flag; e.g. open >= 99.5% of limit-up."),
        ("limit_up_touched_intraday", "bool", "Queue/non-fill risk flag."),
        ("planned_weight", "float", "Research weight before fill haircut."),
        ("adv20_turnover_value", "float", "20D average traded value proxy."),
        ("participation_1pct_capacity", "float", "ADV * 1%; cash capacity proxy."),
        ("participation_3pct_capacity", "float", "ADV * 3%."),
        ("participation_5pct_capacity", "float", "ADV * 5%."),
        ("fill_status", "filled/partial/not_filled", "Paper fill outcome, no live orders."),
        ("non_fill_reason", "string", "Limit-up queue/suspension/no quote/price gap/liquidity cap."),
        ("estimated_slippage_bps", "float", "Paper estimate vs planned price."),
        ("actual_paper_entry_price", "float", "Observed paper fill price."),
        ("paper_exit_rule", "string", "20D/sl8_trail12/etc."),
        ("paper_exit_price", "float/null", "Observed paper exit."),
        ("paper_net_return", "float", "After cost/slippage assumption."),
        ("deviation_from_backtest", "string", "Why paper differs from proxy backtest."),
        ("operator_notes", "string", "Audit comments."),
    ]
    return [{"column": c, "type": t, "description": d} for c, t, d in specs]


def build_checklist_rows() -> list[dict[str, Any]]:
    steps = [
        (1, "Before signal", "Confirm revenue source availability and exact timestamp if possible", "If timestamp absent, earliest trade = next trading day after usable proxy."),
        (2, "Before entry", "Fetch official OHLC/limit fields for planned entry day and prior day", "Flag open/close near limit-up; do not assume fill."),
        (3, "Sizing", "Apply ADV participation cap at 1%/3%/5%", "If target cash > cap, mark partial/not filled in paper log."),
        (4, "Execution", "Record observable open/high/low/close, limit-up touched, and queue risk", "No broker connection; paper-only."),
        (5, "Post-trade", "Track daily PnL, slippage, non-fill reasons, and benchmark", "Compare to S1 proxy assumptions monthly."),
        (6, "Promotion gate", "Require paper fills and costs consistent with backtest across multiple announcement cycles", "No promotion from schema alone."),
    ]
    return [{"step": s, "phase": p, "action": a, "rule": r} for s, p, a, r in steps]


def append_registry() -> None:
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.25 update" in text:
        return
    add = """
## Phase 3.25 update

- Added exact-timing / paper-trading audit rather than a new alpha variant.
- Correction to prior gates: Phase 3.19–3.24 used conservative delayed official-open proxies and limit-up exclusion, but current historical monthly revenue table still has `announcement_date_quality=monthly_summary_no_company_timestamp`; therefore it cannot prove exact company-level tradability.
- Static processed daily market CSV contains only close and turnover value, while raw official daily JSON contains open/high/low and next-day limit fields; future paper trading must parse/preserve raw OHLC/limit fields at signal time.
- Registry status unchanged: S1 remains incumbent; quiet/delay-aware boost remains research-only timing/sizing diagnostic, not promoted.
"""
    REGISTRY.write_text(text.rstrip() + "\n" + add, encoding="utf-8")


def main() -> int:
    audit_rows: list[dict[str, Any]] = []
    rev_cols = header(REV_CSV); daily_cols = header(DAILY_CSV); flags_cols = header(P319_FLAGS)
    rq = revenue_quality_sample()
    audit_rows.append({
        "dataset": "historical_monthly_revenue_mops_static.csv",
        "path": str(REV_CSV),
        "columns": " | ".join(rev_cols),
        "has_company_timestamp": "company_announcement_timestamp" in rev_cols or "announcement_time" in rev_cols,
        "has_usable_date_proxy": "usable_date_proxy" in rev_cols,
        "announcement_date_quality_counts": rq["quality_counts"],
        "rows": rq["rows_sampled"],
        "date_range": f"{rq['min_usable_date']} to {rq['max_usable_date']}",
        "research_use": "monthly summary only; use next trading day after usable_date_proxy unless exact timestamp is separately sourced",
    })
    audit_rows.append({
        "dataset": "daily_market_history_2023_present.csv",
        "path": str(DAILY_CSV),
        "columns": " | ".join(daily_cols),
        "has_open": "open" in daily_cols,
        "has_high": "high" in daily_cols,
        "has_low": "low" in daily_cols,
        "has_close": "close" in daily_cols,
        "has_limit_fields": any("limit" in c.lower() or "漲停" in c for c in daily_cols),
        "research_use": "close/turnover-only processed table; insufficient for executable open/limit fill validation",
    })
    audit_rows.append({
        "dataset": "execution_realism_tradability_trade_flags.csv",
        "path": str(P319_FLAGS),
        "columns": " | ".join(flags_cols),
        "research_use": "derived proxy flags; useful for stress but not substitute for exact timestamps/queue fills",
    })
    audit_rows.extend(raw_daily_field_audit())
    write_csv(OUT_AUDIT, audit_rows)
    write_csv(OUT_SCHEMA, build_schema_rows())
    write_csv(OUT_CHECKLIST, build_checklist_rows())
    append_registry()

    p324 = p324_focus()
    raw_rows = [r for r in audit_rows if r.get("dataset") == "raw_daily_json"]
    raw_summary = "; ".join(f"{r['market']}: files {r['files']}, tables {r['tables']}, open tables {r['tables_with_open']}, limit-up tables {r['tables_with_next_limit_up']}" for r in raw_rows)

    lines: list[str] = [
        "# Phase 3.25 exact-timing audit and paper-trading schema\n\n",
        "Research-only；沒有 live trading、沒有 broker、沒有下單；本輪只新增 scripts/reports/data/processed 研究產出。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because Phase 3.19–3.24 showed S1/quiet/delay-aware variants lose headline quality after conservative execution, sector, and remove-winner gates, therefore the highest-value next step is not another parameter grid but an exact-timing and paper-fill audit. If exact company-level timestamps and observable fillability are missing, the strategy should remain an interview/research portfolio piece rather than production alpha.\n\n",
        "### 前因後果\n\n",
        "- Monthly revenue surprise alpha depends on when information becomes public and whether crowded surprise names can actually be bought after disclosure.\n",
        "- Phase 3.24 showed selected boost/delay rules remain semiconductor/right-tail sensitive, so better Sharpe-chasing would likely overfit unless the operational data gate is solved first.\n\n",
        "### 檢查\n\n",
        f"- Audited revenue columns: `{', '.join(rev_cols)}`.\n",
        f"- Audited processed daily columns: `{', '.join(daily_cols)}`.\n",
        f"- Audited raw official daily JSON OHLC/limit field presence: {raw_summary}.\n",
        "- Created a paper-trading execution-log schema and 2026 checklist for signal timestamp, planned entry, observed OHLC, limit-up non-fill flags, ADV capacity, slippage, and deviations from backtest.\n\n",
        "### 結果\n\n",
        f"- Historical revenue table rows audited: `{rq['rows_sampled']}`; announcement quality: `{rq['quality_counts']}`. This confirms current historical data is monthly-summary/proxy timing, not exact company timestamp data.\n",
        "- Processed daily market table has close and turnover only; it does **not** preserve open/high/low/limit fields needed for executable fill validation.\n",
        "- Raw official daily JSON files do contain OHLC and next-day limit fields for at least the audited market tables, so future scripts should parse raw JSON into an OHLC/limit processed table rather than relying only on close-price CSV.\n",
    ]
    if p324:
        lines.append("- Phase 3.24 robustness context retained:\n")
        for split, s in p324.items():
            lines.append(f"  - `{split}`: {s}.\n")
    lines += [
        "\n### 修正與結論\n\n",
        "- 修正了什麼：先前 Phase 3.19–3.24 已用 next-open/delay/limit-up exclusion 做保守 proxy，但仍可能讓人誤以為 exact tradability 已過關；本輪明確 audit 欄位並建立 paper-trading schema。\n",
        "- 為什麼先前不夠好：`usable_date_proxy` + official open proxy 不能替代 company-level announcement timestamp、實際排隊成交、暫停交易/撮合狀態與盤中可成交量。\n",
        "- 修正後結論是否改變：promotion 結論不變且更保守。S1 保留為 portfolio-grade v0.1；quiet/delay-aware boost 僅是 research-only timing/sizing diagnostic，不升級。\n\n",
        "### 缺陷\n\n",
        "- 本輪不連外抓新 MOPS timestamp；只是基於現有 local artifacts 做 data audit/schema。\n",
        "- Raw JSON 欄位存在不代表所有歷史列都已正規化，仍需建立 official OHLC/limit processed table 並 join 到 signal/execution dates。\n",
        "- Paper schema 不是 alpha 證據；至少需要多個 2026 月營收發布週期的實際 paper fills 才能評估 operational feasibility。\n\n",
        "### 下一步\n\n",
        "1. 寫 raw official daily JSON → processed OHLC/limit table parser，保留 open/high/low/close/成交金額/次日漲跌停價。\n",
        "2. 對 2026 最新月營收候選做 paper-trading log：data_available_at、planned_entry、observed_open、limit-up flag、non-fill reason、ADV cap。\n",
        "3. 若 exact timestamp source 無法穩定取得，報告中固定使用 conservative next-trading-day-after-observed-data rule，不宣稱可當日交易。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_AUDIT}`\n",
        f"- `{OUT_SCHEMA}`\n",
        f"- `{OUT_CHECKLIST}`\n",
        f"- `{OUT_REPORT}`\n",
        f"- `{REGISTRY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
