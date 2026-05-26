#!/usr/bin/env python3
"""Phase 3.26: parse local official daily raw JSON into OHLC/limit research table.

Research-only. Uses existing local raw files only; no broker, no orders, no network.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DAILY_DIR = ROOT / "data" / "raw" / "market_history_daily"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT_CSV = PROCESSED / "official_daily_ohlc_limit_from_raw.csv"
OUT_SUMMARY = PROCESSED / "official_daily_ohlc_limit_from_raw_summary.csv"
OUT_REPORT = REPORTS / "phase3_26_official_ohlc_limit_parser_report.md"
REGISTRY = REPORTS / "promising_strategy_registry.md"

CODE_RE = re.compile(r"^[0-9A-Z]{4,8}$")
HTML_RE = re.compile(r"<[^>]+>")

FIELD_ALIASES = {
    "stock_id": ["代號", "證券代號"],
    "stock_name": ["名稱", "證券名稱"],
    "open": ["開盤", "開盤價"],
    "high": ["最高", "最高價"],
    "low": ["最低", "最低價"],
    "close": ["收盤", "收盤價"],
    "turnover_value": ["成交金額"],
    "shares_traded": ["成交股數", "成交股數  ", "成交股數(股)"],
    "next_limit_up": ["次日漲停價"],
    "next_limit_down": ["次日跌停價"],
}


def clean_text(x: Any) -> str:
    s = HTML_RE.sub("", str(x)).strip()
    return s.replace("\u3000", " ").strip()


def parse_num(x: Any) -> str:
    s = clean_text(x).replace(",", "")
    if s in {"", "--", "---", "除權", "除息", "除權息"}:
        return ""
    try:
        return str(float(s))
    except ValueError:
        return ""


def find_idx(fields: list[str], aliases: list[str]) -> int | None:
    norm = [clean_text(f).replace(" ", "") for f in fields]
    for alias in aliases:
        a = alias.replace(" ", "")
        for i, f in enumerate(norm):
            if a in f:
                return i
    return None


def table_mapping(fields: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for key, aliases in FIELD_ALIASES.items():
        idx = find_idx(fields, aliases)
        if idx is not None:
            mapping[key] = idx
    return mapping


def is_equity_like(row: list[Any], mapping: dict[str, int]) -> bool:
    idx = mapping.get("stock_id")
    if idx is None or idx >= len(row):
        return False
    code = clean_text(row[idx])
    if not CODE_RE.match(code):
        return False
    # Keep common stocks/ETFs/bonds in raw table; downstream joins decide universe.
    return any(k in mapping for k in ("open", "high", "low", "close"))


def parse_file(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    market = "listed" if path.parent.name == "twse" else "otc" if path.parent.name == "tpex" else path.parent.name
    trade_date = path.stem
    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [], [{"market": market, "trade_date": trade_date, "source_file": str(path), "parse_error": str(e), "rows": 0}]
    for ti, table in enumerate(obj.get("tables", [])):
        fields = [clean_text(f) for f in table.get("fields", [])]
        mapping = table_mapping(fields)
        data = table.get("data", [])
        emitted = 0
        for raw in data:
            if not isinstance(raw, list) or not is_equity_like(raw, mapping):
                continue
            def get_text(key: str) -> str:
                idx = mapping.get(key)
                return clean_text(raw[idx]) if idx is not None and idx < len(raw) else ""
            def get_num(key: str) -> str:
                idx = mapping.get(key)
                return parse_num(raw[idx]) if idx is not None and idx < len(raw) else ""
            row = {
                "trade_date": trade_date,
                "market": market,
                "stock_id": get_text("stock_id"),
                "stock_name": get_text("stock_name"),
                "open": get_num("open"),
                "high": get_num("high"),
                "low": get_num("low"),
                "close": get_num("close"),
                "turnover_value": get_num("turnover_value"),
                "shares_traded": get_num("shares_traded"),
                "next_limit_up": get_num("next_limit_up"),
                "next_limit_down": get_num("next_limit_down"),
                "has_ohlc": all(get_num(k) for k in ("open", "high", "low", "close")),
                "has_limit_fields": bool(mapping.get("next_limit_up") is not None and mapping.get("next_limit_down") is not None),
                "source_file": str(path),
            }
            rows.append(row); emitted += 1
        audits.append({
            "market": market,
            "trade_date": trade_date,
            "source_file": str(path),
            "table_index": ti,
            "title": clean_text(table.get("title", "")),
            "fields": " | ".join(fields),
            "mapped_columns": " | ".join(sorted(mapping)),
            "raw_rows": len(data),
            "parsed_rows": emitted,
        })
    return rows, audits


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


def summarize(rows: list[dict[str, Any]], audits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_mkt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_mkt[str(r["market"])].append(r)
    table_by_mkt = Counter(str(a.get("market")) for a in audits)
    parsed_table_by_mkt = Counter(str(a.get("market")) for a in audits if int(a.get("parsed_rows", 0) or 0) > 0)
    out: list[dict[str, Any]] = []
    for market, rs in sorted(by_mkt.items()):
        dates = sorted({str(r["trade_date"]) for r in rs})
        out.append({
            "market": market,
            "rows": len(rs),
            "trading_days": len(dates),
            "min_date": dates[0] if dates else "",
            "max_date": dates[-1] if dates else "",
            "tables_seen": table_by_mkt[market],
            "tables_with_parsed_rows": parsed_table_by_mkt[market],
            "rows_with_complete_ohlc": sum(1 for r in rs if r["has_ohlc"]),
            "rows_with_turnover_value": sum(1 for r in rs if r["turnover_value"]),
            "rows_with_next_limit_up": sum(1 for r in rs if r["next_limit_up"]),
            "rows_with_next_limit_down": sum(1 for r in rs if r["next_limit_down"]),
            "unique_stocks": len({str(r["stock_id"]) for r in rs}),
        })
    return out


def append_registry(summary: list[dict[str, Any]]) -> None:
    text = REGISTRY.read_text(encoding="utf-8") if REGISTRY.exists() else "# Promising strategy registry — Taiwan monthly revenue SUR\n"
    if "## Phase 3.26 update" in text:
        return
    bits = "; ".join(f"{r['market']} rows {r['rows']}, OHLC {r['rows_with_complete_ohlc']}, next-limit-up {r['rows_with_next_limit_up']}" for r in summary)
    add = f"""
## Phase 3.26 update

- Parsed existing local official daily raw JSON into `official_daily_ohlc_limit_from_raw.csv` for execution-realism research; no network/live trading.
- Coverage summary: {bits}.
- Correction/guardrail: TPEx raw files include next-day limit fields, while current local TWSE raw files provide OHLC but not next-day limit fields in the parsed tables; TWSE limit-up non-fill remains missing-data/proxy-only unless separately sourced.
- Registry status unchanged: S1 remains incumbent; quiet/delay-aware sizing diagnostics are not promoted.
"""
    REGISTRY.write_text(text.rstrip() + "\n" + add, encoding="utf-8")


def main() -> int:
    all_rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for path in sorted(RAW_DAILY_DIR.glob("*/*.json")):
        rows, aud = parse_file(path)
        all_rows.extend(rows); audits.extend(aud)
    summary = summarize(all_rows, audits)
    write_csv(OUT_CSV, all_rows)
    write_csv(OUT_SUMMARY, summary)
    append_registry(summary)

    lines = [
        "# Phase 3.26 official OHLC/limit parser from local raw JSON\n\n",
        "Research-only；使用既有 local raw official JSON；沒有 live trading、broker、network、下單。\n\n",
        "## 假說 → 前因後果 → 檢查 → 結果 → 缺陷 → 下一步\n\n",
        "### 假說\n\n",
        "Because Phase 3.25 found the processed daily CSV is close/turnover-only while raw official JSON may contain OHLC/limit fields, therefore parsing those raw files into a normalized table should reduce execution-realism blind spots before any further strategy promotion.\n\n",
        "### 前因後果\n\n",
        "- S1 and quiet/delay-aware variants are sensitive to entry timing, limit-up non-fill, and ADV capacity.\n",
        "- Close-only processed data forces proxy exits/entries; normalized OHLC allows explicit next-open, intraday range, and limit-field audits where fields exist.\n\n",
        "### 檢查\n\n",
        f"- Parsed `{len(list(RAW_DAILY_DIR.glob('*/*.json')))}` local raw JSON files under `{RAW_DAILY_DIR}`.\n",
        "- Normalized columns: trade_date, market, stock_id/name, open/high/low/close, turnover_value, shares_traded, next_limit_up/down, source_file.\n\n",
        "### 結果\n\n",
    ]
    for r in summary:
        lines.append(f"- `{r['market']}`: rows={r['rows']}, days={r['trading_days']} ({r['min_date']}→{r['max_date']}), complete_OHLC={r['rows_with_complete_ohlc']}, turnover={r['rows_with_turnover_value']}, next_limit_up={r['rows_with_next_limit_up']}, unique_stocks={r['unique_stocks']}.\n")
    lines += [
        "\n### 修正與結論\n\n",
        "- 修正了什麼：Phase 3.25 只做欄位 audit；本輪把 raw official JSON 實際正規化成可 join 的 OHLC/limit research table。\n",
        "- 為什麼先前不夠好：只知道欄位存在仍不能直接用於 entry/open、range、capacity 與 limit-up non-fill 檢查。\n",
        "- 修正後結論是否改變：不改變 promotion 結論，但改善後續 execution realism workflow。TPEx 可直接用 next-day limit 欄位；TWSE 在目前 local raw 樣本仍缺 next-day limit 欄位，必須標記為 missing/proxy。\n\n",
        "### 缺陷\n\n",
        "- Current local TWSE raw coverage is sparse relative to TPEx and parsed TWSE limit fields are absent.\n",
        "- Parser keeps ETFs/bonds/common stocks; strategy universe filtering still must happen when joining to SUR signals.\n",
        "- Official limit-up fields are next-day limits in TPEx files; matching to entry-day non-fill requires careful date alignment.\n\n",
        "### 下一步\n\n",
        "1. Join `official_daily_ohlc_limit_from_raw.csv` to Phase 3.19/3.21 trade flags and replace close-only proxy where raw open is available.\n",
        "2. Add date alignment for TPEx next-day limit: previous file's next_limit_up should be the current trade day's limit-up reference.\n",
        "3. Source/parse TWSE official limit-up/down fields or mark TWSE limit non-fill as unavailable in paper logs.\n\n",
        "## Outputs\n\n",
        f"- `{OUT_CSV}`\n",
        f"- `{OUT_SUMMARY}`\n",
        f"- `{OUT_REPORT}`\n",
        f"- `{REGISTRY}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
