#!/usr/bin/env python3
"""Phase 4.1: fetch official Taiwan daily margin balance data.

Research-only data collection. Downloads public TWSE/TPEx margin balance JSON for
trading dates already present in the local official daily OHLC table, normalizes
listed/OTC schemas, and writes a unified processed CSV.

No broker connection, no orders, no live trading.
"""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "margin_balance"
DAILY = PROCESSED / "official_daily_ohlc_limit_from_raw.csv"
OUT = PROCESSED / "daily_margin_balance.csv"
OUT_AUDIT = PROCESSED / "daily_margin_balance_audit.csv"

UA = "Mozilla/5.0 (research; public official data probe)"
CODE_RE = re.compile(r"^[0-9A-Z]{4,8}$")


def clean(x: Any) -> str:
    return str(x).replace("\u3000", " ").strip()


def num(x: Any) -> str:
    s = clean(x).replace(",", "")
    if s in {"", "--", "---", "-"}:
        return ""
    try:
        return str(float(s))
    except Exception:
        return ""


def tw_year(date: str) -> str:
    return f"{int(date[:4]) - 1911:03d}/{date[4:6]}/{date[6:8]}"


def fetch(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body)


def load_dates() -> dict[str, list[str]]:
    out: dict[str, set[str]] = {"listed": set(), "otc": set()}
    with DAILY.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m = r.get("market", "")
            d = r.get("trade_date", "")
            if m in out and d >= "20230101":
                out[m].add(d)
    return {k: sorted(v) for k, v in out.items()}


def parse_twse(date: str, obj: dict[str, Any], source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    # Table 1 is usually the per-security margin/short summary.
    for table in obj.get("tables", []):
        fields = [clean(f) for f in table.get("fields", [])]
        if "代號" not in fields or "今日餘額" not in fields or "現金償還" not in fields:
            continue
        data = table.get("data", [])
        for raw in data:
            if not isinstance(raw, list) or len(raw) < 15:
                continue
            sid = clean(raw[0])
            if not CODE_RE.match(sid) or not sid[:1].isdigit():
                continue
            rows.append({
                "trade_date": date,
                "market": "listed",
                "stock_id": sid,
                "stock_name": clean(raw[1]),
                "margin_buy": num(raw[2]),
                "margin_sell": num(raw[3]),
                "margin_cash_repay": num(raw[4]),
                "margin_prev_balance": num(raw[5]),
                "margin_balance": num(raw[6]),
                "margin_limit_next_day": num(raw[7]),
                "short_buy": num(raw[8]),
                "short_sell": num(raw[9]),
                "short_repay": num(raw[10]),
                "short_prev_balance": num(raw[11]),
                "short_balance": num(raw[12]),
                "short_limit_next_day": num(raw[13]),
                "margin_short_offset": num(raw[14]),
                "margin_usage_pct": "",
                "note": clean(raw[15]) if len(raw) > 15 else "",
                "source": source,
            })
        break
    return rows


def parse_tpex(date: str, obj: dict[str, Any], source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for table in obj.get("tables", []):
        fields = [clean(f) for f in table.get("fields", [])]
        if "代號" not in fields or "資餘額" not in fields:
            continue
        for raw in table.get("data", []):
            if not isinstance(raw, list) or len(raw) < 19:
                continue
            sid = clean(raw[0])
            if not CODE_RE.match(sid) or not sid[:1].isdigit():
                continue
            rows.append({
                "trade_date": date,
                "market": "otc",
                "stock_id": sid,
                "stock_name": clean(raw[1]),
                "margin_buy": num(raw[3]),
                "margin_sell": num(raw[4]),
                "margin_cash_repay": num(raw[5]),
                "margin_prev_balance": num(raw[2]),
                "margin_balance": num(raw[6]),
                "margin_limit_next_day": num(raw[9]),
                "short_buy": num(raw[12]),
                "short_sell": num(raw[11]),
                "short_repay": num(raw[13]),
                "short_prev_balance": num(raw[10]),
                "short_balance": num(raw[14]),
                "short_limit_next_day": num(raw[17]),
                "margin_short_offset": num(raw[18]),
                "margin_usage_pct": num(raw[8]),
                "note": clean(raw[19]) if len(raw) > 19 else "",
                "source": source,
            })
        break
    return rows


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


def main() -> int:
    dates = load_dates()
    all_rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for market, ds in dates.items():
        raw_dir = RAW / market
        raw_dir.mkdir(parents=True, exist_ok=True)
        for i, d in enumerate(ds, 1):
            path = raw_dir / f"{d}.json"
            status = ""
            try:
                if path.exists() and path.stat().st_size > 20:
                    obj = json.loads(path.read_text(encoding="utf-8"))
                    status = "cached"
                else:
                    if market == "listed":
                        url = f"https://www.twse.com.tw/exchangeReport/MI_MARGN?response=json&date={d}&selectType=ALL"
                    else:
                        url = f"https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php?l=zh-tw&o=json&d={tw_year(d)}"
                    obj = fetch(url)
                    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
                    status = "downloaded"
                    time.sleep(0.08)
                rows = parse_twse(d, obj, str(path)) if market == "listed" else parse_tpex(d, obj, str(path))
                all_rows.extend(rows)
                audit.append({"market": market, "trade_date": d, "status": status, "stat": obj.get("stat", ""), "rows": len(rows), "source_file": str(path)})
            except Exception as e:
                audit.append({"market": market, "trade_date": d, "status": "error", "error": repr(e), "rows": 0, "source_file": str(path)})
            if i % 100 == 0:
                print(f"{market}: {i}/{len(ds)} dates, rows={len(all_rows)}")
    all_rows.sort(key=lambda r: (r["trade_date"], r["market"], r["stock_id"]))
    write_csv(OUT, all_rows)
    write_csv(OUT_AUDIT, audit)
    print(f"wrote {OUT} rows={len(all_rows)}")
    print(f"wrote {OUT_AUDIT} rows={len(audit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
