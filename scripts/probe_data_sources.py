#!/usr/bin/env python3
"""Probe Taiwan monthly-revenue strategy data sources.

This script is intentionally read-only with respect to external services:
- It performs small GET/POST requests.
- It writes only local probe outputs under data/raw/probes/.
- It does not place orders, deploy, commit, push, or delete files.

Run:
    python3 scripts/probe_data_sources.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "probes"
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Hermes quant research probe; read-only)"


@dataclass
class ProbeResult:
    name: str
    url: str
    ok: bool
    status: Optional[int] = None
    content_type: Optional[str] = None
    bytes_saved: int = 0
    output_file: Optional[str] = None
    error: Optional[str] = None
    note: Optional[str] = None


def request_bytes(url: str, *, method: str = "GET", data: Optional[dict] = None, timeout: int = 20) -> tuple[int, str, bytes]:
    body = None
    headers = {"User-Agent": USER_AGENT}
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        headers["Referer"] = "https://mops.twse.com.tw/mops/web/t21sc03"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.headers.get("content-type", ""), resp.read()


def save_bytes(name: str, raw: bytes, suffix: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    path = OUT_DIR / f"{safe}{suffix}"
    path.write_bytes(raw)
    return str(path.relative_to(ROOT))


def probe(name: str, url: str, *, suffix: str = ".json", method: str = "GET", data: Optional[dict] = None, note: Optional[str] = None) -> ProbeResult:
    try:
        status, content_type, raw = request_bytes(url, method=method, data=data)
        output_file = save_bytes(name, raw, suffix)
        body_preview = raw[:2000].decode("utf-8", "ignore")
        blocked = "FOR SECURITY REASONS" in body_preview or "安全性考量" in body_preview
        return ProbeResult(
            name=name,
            url=url,
            ok=(200 <= status < 300) and not blocked,
            status=status,
            content_type=content_type,
            bytes_saved=len(raw),
            output_file=output_file,
            error="Security/anti-automation block page returned" if blocked else None,
            note=note,
        )
    except urllib.error.HTTPError as e:
        return ProbeResult(name=name, url=url, ok=False, status=e.code, error=f"HTTPError: {e.reason}", note=note)
    except Exception as e:  # noqa: BLE001 - probe script should record failures, not crash early
        return ProbeResult(name=name, url=url, ok=False, error=repr(e), note=note)


def main() -> int:
    finmind_token = os.environ.get("FINMIND_TOKEN")
    finmind_suffix = f"&token={urllib.parse.quote(finmind_token)}" if finmind_token else ""

    probes = [
        probe(
            "twse_2330_daily_202401",
            "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20240101&stockNo=2330&response=json",
            note="TWSE listed stock daily OHLCV. Official source; unadjusted prices; no adjusted close.",
        ),
        probe(
            "yahoo_2330_chart_202401",
            "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW?period1=1704067200&period2=1704758400&interval=1d&events=history%7Cdiv%7Csplit",
            note="Yahoo chart endpoint. Convenient adjusted close/dividends; must validate and watch survivorship bias.",
        ),
        probe(
            "finmind_2330_price_202401",
            "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id=2330&start_date=2024-01-01&end_date=2024-01-10" + finmind_suffix,
            note="FinMind price endpoint. May require token/subscription; useful MVP if accessible.",
        ),
        probe(
            "finmind_2330_month_revenue_2024q1",
            "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockMonthRevenue&data_id=2330&start_date=2024-01-01&end_date=2024-03-31" + finmind_suffix,
            note="FinMind monthly revenue endpoint. Need verify whether fields include actual announcement date vs revenue month.",
        ),
        probe(
            "mops_month_revenue_ajax_sii_113_01",
            "https://mops.twse.com.tw/mops/web/ajax_t21sc03",
            method="POST",
            data={"encodeURIComponent": "1", "step": "1", "firstin": "1", "off": "1", "TYPEK": "sii", "year": "113", "month": "1"},
            suffix=".html",
            note="MOPS official monthly revenue page. Direct POST may be blocked by anti-scraping/security rules; browser/session handling may be needed.",
        ),
        probe(
            "twse_openapi_latest_month_revenue_listed",
            "https://openapi.twse.com.tw/v1/opendata/t187ap05_L",
            note="TWSE OpenAPI latest listed-company monthly revenue summary. JSON; includes report date and revenue month, not per-company announcement timestamp.",
        ),
        probe(
            "tpex_openapi_latest_month_revenue_otc",
            "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O",
            note="TPEx OpenAPI latest OTC-company monthly revenue summary. JSON; includes report date and revenue month, not per-company announcement timestamp.",
        ),
        probe(
            "tpex_openapi_latest_month_revenue_emerging",
            "https://www.tpex.org.tw/openapi/v1/t187ap05_R",
            note="TPEx OpenAPI latest emerging-company monthly revenue summary. JSON; MVP excludes emerging stocks but endpoint is available.",
        ),
        probe(
            "tpex_6488_daily_202405",
            "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?code=6488&date=2024/05/01&id=&response=json",
            note="TPEx OTC stock daily OHLCV sample. Official source; unadjusted prices.",
        ),
    ]

    report = {
        "generated_at_epoch": int(time.time()),
        "root": str(ROOT),
        "finmind_token_present": bool(finmind_token),
        "results": [asdict(p) for p in probes],
    }
    report_path = OUT_DIR / "probe_results.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
