#!/usr/bin/env python3
"""Fetch latest Taiwan monthly revenue summaries from official OpenAPI endpoints.

Scope:
- Free official JSON endpoints only.
- Writes normalized latest monthly revenue CSV/JSON under data/raw/openapi/.
- No trading, no deployment, no package installation.

Known limitation:
- OpenAPI monthly revenue contains `出表日期` and `資料年月`, but not per-company
  actual announcement timestamp. For event-study backtests, use a conservative
  signal date such as the first trading day after the monthly revenue deadline, or
  find a separate announcement timestamp source.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "openapi"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ENDPOINTS = {
    "listed": "https://openapi.twse.com.tw/v1/opendata/t187ap05_L",
    "otc": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O",
    "emerging": "https://www.tpex.org.tw/openapi/v1/t187ap05_R",
}

FIELD_MAP = {
    "出表日期": "report_date_roc",
    "資料年月": "revenue_month_roc",
    "公司代號": "stock_id",
    "公司名稱": "stock_name",
    "產業別": "industry",
    "營業收入-當月營收": "revenue_current_month",
    "營業收入-上月營收": "revenue_previous_month",
    "營業收入-去年當月營收": "revenue_same_month_last_year",
    "營業收入-上月比較增減(%)": "revenue_mom_pct",
    "營業收入-去年同月增減(%)": "revenue_yoy_pct",
    "累計營業收入-當月累計營收": "revenue_ytd",
    "累計營業收入-去年累計營收": "revenue_ytd_last_year",
    "累計營業收入-前期比較增減(%)": "revenue_ytd_yoy_pct",
    "備註": "note",
}

NUMERIC_FIELDS = {
    "revenue_current_month",
    "revenue_previous_month",
    "revenue_same_month_last_year",
    "revenue_mom_pct",
    "revenue_yoy_pct",
    "revenue_ytd",
    "revenue_ytd_last_year",
    "revenue_ytd_yoy_pct",
}


def fetch_json(url: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Hermes quant research)"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        raw = resp.read()
        content_type = resp.headers.get("content-type", "")
    if "json" not in content_type.lower():
        raise RuntimeError(f"Expected JSON from {url}, got {content_type}")
    return json.loads(raw.decode("utf-8-sig"))


def to_iso_from_roc_yyyymmdd(value: str) -> str:
    value = str(value).strip()
    if len(value) != 7 or not value.isdigit():
        return ""
    year = int(value[:3]) + 1911
    return f"{year:04d}-{int(value[3:5]):02d}-{int(value[5:7]):02d}"


def to_iso_month_from_roc_yyyymm(value: str) -> str:
    value = str(value).strip()
    if len(value) != 5 or not value.isdigit():
        return ""
    year = int(value[:3]) + 1911
    return f"{year:04d}-{int(value[3:5]):02d}"


def clean_number(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).replace(",", "").strip()
    if text in {"", "-", "--", "不適用", "NA", "N/A"}:
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def normalize_row(row: dict[str, Any], market: str) -> dict[str, Any]:
    out: dict[str, Any] = {"market": market}
    for zh, en in FIELD_MAP.items():
        val = row.get(zh)
        out[en] = clean_number(val) if en in NUMERIC_FIELDS else (str(val).strip() if val is not None else "")
    out["report_date"] = to_iso_from_roc_yyyymmdd(out.get("report_date_roc", ""))
    out["revenue_month"] = to_iso_month_from_roc_yyyymm(out.get("revenue_month_roc", ""))
    out["data_available_date"] = out["report_date"]  # OpenAPI report date, not actual company announcement date.
    out["announcement_date_quality"] = "report_date_only_not_company_timestamp"
    return out


def main() -> int:
    all_rows: list[dict[str, Any]] = []
    metadata = {"generated_at_epoch": int(time.time()), "endpoints": ENDPOINTS, "markets": {}}

    for market, url in ENDPOINTS.items():
        try:
            raw_rows = fetch_json(url)
            normalized = [normalize_row(row, market) for row in raw_rows]
            all_rows.extend(normalized)
            metadata["markets"][market] = {"ok": True, "row_count": len(normalized), "url": url}
        except Exception as exc:  # noqa: BLE001
            metadata["markets"][market] = {"ok": False, "error": repr(exc), "url": url}

    json_path = OUT_DIR / "latest_monthly_revenue_openapi.json"
    csv_path = OUT_DIR / "latest_monthly_revenue_openapi.csv"
    meta_path = OUT_DIR / "latest_monthly_revenue_openapi_metadata.json"

    json_path.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    fieldnames = [
        "market", "stock_id", "stock_name", "industry",
        "report_date_roc", "report_date", "revenue_month_roc", "revenue_month",
        "revenue_current_month", "revenue_previous_month", "revenue_same_month_last_year",
        "revenue_mom_pct", "revenue_yoy_pct", "revenue_ytd", "revenue_ytd_last_year", "revenue_ytd_yoy_pct",
        "note", "data_available_date", "announcement_date_quality",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(json.dumps({"rows": len(all_rows), "metadata": metadata, "outputs": [str(json_path), str(csv_path), str(meta_path)]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
