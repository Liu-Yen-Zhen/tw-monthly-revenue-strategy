#!/usr/bin/env python3
"""Fetch historical Taiwan monthly revenue from official MOPS static NAS files.

Research-only script:
- Uses official static HTML files hosted by doc.twse.com.tw.
- Caches raw HTML and writes normalized CSV/JSON.
- Does not trade, deploy, delete, install packages, commit, or push.

Important limitation:
- Static t21sc03 monthly summary files do not include per-company announcement timestamps.
- `usable_date_proxy` is conservatively set to the first calendar day after the statutory deadline
  proxy (11th of following month); later research should map this to next trading day.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import json
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_HTML_DIR = ROOT / "data" / "raw" / "mops_static_monthly_revenue"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
for p in [RAW_HTML_DIR, PROCESSED_DIR, REPORT_DIR]:
    p.mkdir(parents=True, exist_ok=True)

OUT_CSV = PROCESSED_DIR / "historical_monthly_revenue_mops_static.csv"
OUT_JSON = PROCESSED_DIR / "historical_monthly_revenue_mops_static.json"
META_JSON = PROCESSED_DIR / "historical_monthly_revenue_mops_static_metadata.json"
REPORT_MD = REPORT_DIR / "phase2_4_historical_revenue_source_report.md"

BASE = "https://doc.twse.com.tw/nas/t21/{market}/t21sc03_{roc_year}_{month}{suffix}.html"
MARKETS = {"sii": "listed", "otc": "otc"}
START_YEAR = 2021
END_YEAR = dt.date.today().year
REQUEST_SLEEP_SECONDS = 0.20
USER_AGENT = "Mozilla/5.0 (Hermes quant research; read-only)"


class TableRowParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.in_cell = False
        self.cur = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self.row = []
        if tag.lower() in {"td", "th"}:
            self.in_cell = True
            self.cur = ""

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self.in_cell:
            text = html.unescape(" ".join(self.cur.split())).strip()
            self.row.append(text)
            self.in_cell = False
            self.cur = ""
        if tag.lower() == "tr" and self.row:
            self.rows.append(self.row)

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cur += data + " "


def roc_year(year: int) -> int:
    return year - 1911


def revenue_month_iso(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def usable_date_proxy(year: int, month: int) -> str:
    # Revenue for YYYY-MM is generally disclosed by around the 10th of following month.
    # Use 11th as conservative calendar proxy; trading-day alignment is done downstream.
    if month == 12:
        y, m = year + 1, 1
    else:
        y, m = year, month + 1
    return f"{y:04d}-{m:02d}-11"


def clean_num(value: str) -> float | None:
    text = str(value).replace(",", "").strip()
    if text in {"", "-", "--", "不適用", "NA", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def fetch_html(market: str, year: int, month: int) -> tuple[str | None, str | None, str | None]:
    roc = roc_year(year)
    cache_dir = RAW_HTML_DIR / market
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Many months have both suffix variants; _0 is the common industry-sectioned version.
    for suffix in ["_0", ""]:
        url = BASE.format(market=market, roc_year=roc, month=month, suffix=suffix)
        cache_path = cache_dir / f"t21sc03_{roc}_{month}{suffix}.html"
        if cache_path.exists() and cache_path.stat().st_size > 1000:
            raw = cache_path.read_bytes()
            return raw.decode("big5", "ignore"), str(cache_path), url
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
            if len(raw) < 1000:
                continue
            cache_path.write_bytes(raw)
            return raw.decode("big5", "ignore"), str(cache_path), url
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
        finally:
            time.sleep(REQUEST_SLEEP_SECONDS)
    return None, None, None


def parse_rows(text: str, market_code: str, market: str, year: int, month: int, source_url: str, cache_path: str) -> list[dict[str, Any]]:
    parser = TableRowParser()
    parser.feed(text)
    rows_out: list[dict[str, Any]] = []
    current_industry = ""
    for row in parser.rows:
        if len(row) == 2 and row[0].startswith("產業別："):
            current_industry = row[0].replace("產業別：", "").strip()
            continue
        if not row or not re.fullmatch(r"\d{4}", row[0].strip()):
            continue
        if len(row) < 10:
            continue
        note = row[10] if len(row) > 10 else ""
        rows_out.append({
            "market_code": market_code,
            "market": market,
            "revenue_month": revenue_month_iso(year, month),
            "usable_date_proxy": usable_date_proxy(year, month),
            "stock_id": row[0].strip(),
            "stock_name": row[1].strip(),
            "industry": current_industry,
            "revenue_current_month": clean_num(row[2]),
            "revenue_previous_month": clean_num(row[3]),
            "revenue_same_month_last_year": clean_num(row[4]),
            "revenue_mom_pct": clean_num(row[5]),
            "revenue_yoy_pct": clean_num(row[6]),
            "revenue_ytd": clean_num(row[7]),
            "revenue_ytd_last_year": clean_num(row[8]),
            "revenue_ytd_yoy_pct": clean_num(row[9]),
            "note": note,
            "unit": "thousand_twd",
            "announcement_date_quality": "monthly_summary_no_company_timestamp",
            "source_url": source_url,
            "raw_cache_path": cache_path,
        })
    return rows_out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    today = dt.date.today()
    all_rows: list[dict[str, Any]] = []
    fetch_log: list[dict[str, Any]] = []
    for year in range(START_YEAR, END_YEAR + 1):
        max_month = 12
        if year == today.year:
            # Most recent complete revenue month is usually prior month, but fetch attempts are cheap and cached.
            max_month = max(1, today.month - 1)
        for month in range(1, max_month + 1):
            for mops_market, normalized_market in MARKETS.items():
                text, cache_path, url = fetch_html(mops_market, year, month)
                if not text or not cache_path or not url:
                    fetch_log.append({"market_code": mops_market, "market": normalized_market, "year": year, "month": month, "ok": False, "rows": 0})
                    continue
                rows = parse_rows(text, mops_market, normalized_market, year, month, url, cache_path)
                all_rows.extend(rows)
                fetch_log.append({"market_code": mops_market, "market": normalized_market, "year": year, "month": month, "ok": True, "rows": len(rows), "url": url})

    all_rows.sort(key=lambda r: (r["revenue_month"], r["market"], r["stock_id"]))
    write_csv(OUT_CSV, all_rows)
    OUT_JSON.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "markets": MARKETS,
        "row_count": len(all_rows),
        "months_attempted": len(fetch_log),
        "months_successful": sum(1 for x in fetch_log if x["ok"]),
        "fetch_log": fetch_log,
        "outputs": [str(OUT_CSV), str(OUT_JSON)],
    }
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    month_count = len({(r["market"], r["revenue_month"]) for r in all_rows})
    latest_month = max((r["revenue_month"] for r in all_rows), default="")
    earliest_month = min((r["revenue_month"] for r in all_rows), default="")
    by_market: dict[str, int] = {}
    for r in all_rows:
        by_market[r["market"]] = by_market.get(r["market"], 0) + 1

    lines = [
        "# Phase 2.4 歷史月營收資料源攻關報告\n\n",
        "本報告驗證官方 MOPS 靜態 NAS 月營收檔是否可作為免費歷史月營收來源。\n\n",
        "## 結論\n\n",
        "- `doc.twse.com.tw/nas/t21/...` 靜態 HTML 檔可用。\n",
        "- 可取得上市與上櫃歷史月營收彙總。\n",
        "- 靜態彙總檔沒有逐公司公告 timestamp，因此正式事件回測仍需保守 usable date proxy 或另抓公司級公告頁。\n\n",
        "## 覆蓋範圍\n\n",
        f"- 起始月份：{earliest_month}\n",
        f"- 最新月份：{latest_month}\n",
        f"- 成功 market-month 數：{month_count}\n",
        f"- 總資料列數：{len(all_rows):,}\n",
    ]
    for market, count in sorted(by_market.items()):
        lines.append(f"- {market}: {count:,} rows\n")
    lines += [
        "\n## 產出\n\n",
        f"- `{OUT_CSV}`\n",
        f"- `{OUT_JSON}`\n",
        f"- `{META_JSON}`\n\n",
        "## 重要限制\n\n",
        "- 此資料可做歷史探索與 proxy backtest，但不能精準模擬每家公司公告後第 1 天進場。\n",
        "- `usable_date_proxy` 目前設為次月 11 日；後續需映射到下一個交易日。\n",
        "- 仍需處理下市櫃、處置股、除權息、歷史產業分類變動。\n",
    ]
    REPORT_MD.write_text("".join(lines), encoding="utf-8")

    print(json.dumps({
        "rows": len(all_rows),
        "earliest_month": earliest_month,
        "latest_month": latest_month,
        "successful_market_months": month_count,
        "by_market": by_market,
        "outputs": [str(OUT_CSV), str(META_JSON), str(REPORT_MD)],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
