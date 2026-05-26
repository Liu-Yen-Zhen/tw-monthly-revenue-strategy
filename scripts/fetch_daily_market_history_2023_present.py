#!/usr/bin/env python3
"""Fetch official TWSE/TPEx all-stock daily market history for proxy research.

Research-only. Uses exchange daily all-market endpoints with local caching.
Default range starts 2023-01-01 to keep runtime/data size reasonable for MVP.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "market_history_daily"
PROCESSED_DIR = ROOT / "data" / "processed"
for p in [RAW_DIR, PROCESSED_DIR]:
    p.mkdir(parents=True, exist_ok=True)

START_DATE = dt.date(2023, 1, 1)
END_DATE = dt.date.today()
OUT_CSV = PROCESSED_DIR / "daily_market_history_2023_present.csv"
META_JSON = PROCESSED_DIR / "daily_market_history_2023_present_metadata.json"
USER_AGENT = "Mozilla/5.0 (Hermes quant research; read-only)"
REQUEST_SLEEP_SECONDS = 0.08


def fetch_json(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return None


def num(value: Any) -> float | None:
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", "", str(value)).replace(",", "").strip()
    if text in {"", "--", "-", "除息", "除權", "除權息", "X"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def cache_path(market: str, date_: dt.date) -> Path:
    p = RAW_DIR / market
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{date_.isoformat()}.json"


def fetch_twse(date_: dt.date) -> list[dict[str, Any]]:
    cp = cache_path("twse", date_)
    if cp.exists() and cp.stat().st_size > 50:
        data = json.loads(cp.read_text(encoding="utf-8"))
    else:
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={date_.strftime('%Y%m%d')}&type=ALLBUT0999&response=json"
        data = fetch_json(url)
        if not data or data.get("stat") != "OK":
            return []
        cp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        time.sleep(REQUEST_SLEEP_SECONDS)
    table = next((t for t in data.get("tables", []) if t.get("fields") and "證券代號" in t.get("fields", [])), None)
    if not table:
        return []
    rows = []
    fields = table["fields"]
    for arr in table.get("data", []):
        row = dict(zip(fields, arr))
        sid = str(row.get("證券代號", "")).strip()
        if not re.fullmatch(r"\d{4}", sid):
            continue
        close = num(row.get("收盤價")); turnover = num(row.get("成交金額"))
        if close is None or turnover is None:
            continue
        rows.append({"trade_date": date_.isoformat(), "market": "listed", "stock_id": sid, "stock_name": str(row.get("證券名稱", "")).strip(), "close": close, "turnover_value": int(turnover)})
    return rows


def fetch_tpex(date_: dt.date) -> list[dict[str, Any]]:
    cp = cache_path("tpex", date_)
    if cp.exists() and cp.stat().st_size > 50:
        data = json.loads(cp.read_text(encoding="utf-8"))
    else:
        url = f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={date_.strftime('%Y/%m/%d')}&type=EW&response=json"
        data = fetch_json(url)
        if not data or not data.get("tables"):
            return []
        cp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        time.sleep(REQUEST_SLEEP_SECONDS)
    table = data["tables"][0]
    fields = table.get("fields", [])
    rows = []
    for arr in table.get("data", []):
        row = dict(zip(fields, arr))
        sid = str(row.get("代號", "")).strip()
        if not re.fullmatch(r"\d{4}", sid):
            continue
        close = num(row.get("收盤 ")); turnover = num(row.get(" 成交金額(元)"))
        if close is None or turnover is None:
            continue
        rows.append({"trade_date": date_.isoformat(), "market": "otc", "stock_id": sid, "stock_name": str(row.get("名稱", "")).strip(), "close": close, "turnover_value": int(turnover)})
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8"); return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    rows: list[dict[str, Any]] = []
    trading_days = set()
    d = START_DATE
    while d <= END_DATE:
        if d.weekday() < 5:
            day_rows = fetch_twse(d) + fetch_tpex(d)
            if day_rows:
                rows.extend(day_rows); trading_days.add(d.isoformat())
        d += dt.timedelta(days=1)
    rows.sort(key=lambda r: (r["trade_date"], r["market"], r["stock_id"]))
    write_csv(OUT_CSV, rows)
    meta = {"start_date": START_DATE.isoformat(), "end_date": END_DATE.isoformat(), "rows": len(rows), "trading_days": len(trading_days), "output": str(OUT_CSV)}
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
