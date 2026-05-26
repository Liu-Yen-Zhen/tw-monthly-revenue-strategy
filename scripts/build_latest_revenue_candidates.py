#!/usr/bin/env python3
"""Fetch latest TWSE/TPEx market snapshots and build a first monthly-revenue candidate list.

This is research-only:
- No orders.
- No deployment.
- No package installation.
- Uses official free endpoints and local CSV/JSON outputs.

Inputs:
- data/raw/openapi/latest_monthly_revenue_openapi.csv

Outputs:
- data/raw/openapi/latest_market_snapshot.csv/json
- data/processed/latest_revenue_candidates.csv/json
- reports/latest_revenue_candidate_summary.md
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
import statistics
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "openapi"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
for p in [RAW_DIR, PROCESSED_DIR, REPORT_DIR]:
    p.mkdir(parents=True, exist_ok=True)

REVENUE_CSV = RAW_DIR / "latest_monthly_revenue_openapi.csv"
MARKET_CSV = RAW_DIR / "latest_market_snapshot.csv"
MARKET_JSON = RAW_DIR / "latest_market_snapshot.json"
CANDIDATE_CSV = PROCESSED_DIR / "latest_revenue_candidates.csv"
CANDIDATE_JSON = PROCESSED_DIR / "latest_revenue_candidates.json"
SUMMARY_MD = REPORT_DIR / "latest_revenue_candidate_summary.md"

USER_AGENT = "Mozilla/5.0 (Hermes quant research; read-only)"


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8-sig"))


def num(value: Any) -> float | None:
    if value is None:
        return None
    text = re.sub(r"<[^>]+>", "", str(value)).replace(",", "").strip()
    if text in {"", "--", "-", "除息", "除權", "除權息"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def find_recent_trading_date(max_back: int = 10) -> tuple[str, str]:
    today = dt.date.today()
    last_error = ""
    for i in range(max_back + 1):
        d = today - dt.timedelta(days=i)
        twse_date = d.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={twse_date}&type=ALLBUT0999&response=json"
        try:
            data = fetch_json(url)
            if data.get("stat") == "OK" and data.get("tables"):
                table = next((t for t in data["tables"] if t.get("fields") and "證券代號" in t.get("fields", [])), None)
                if table and table.get("data"):
                    return d.strftime("%Y-%m-%d"), twse_date
            last_error = data.get("stat", "unknown")
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
    raise RuntimeError(f"No recent TWSE trading day found; last_error={last_error}")


def fetch_twse_market(yyyymmdd: str) -> list[dict[str, Any]]:
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={yyyymmdd}&type=ALLBUT0999&response=json"
    data = fetch_json(url)
    table = next(t for t in data["tables"] if t.get("fields") and "證券代號" in t.get("fields", []))
    fields = table["fields"]
    rows = []
    for arr in table["data"]:
        row = dict(zip(fields, arr))
        stock_id = str(row.get("證券代號", "")).strip()
        if not re.fullmatch(r"\d{4}", stock_id):
            continue
        rows.append({
            "market": "listed",
            "stock_id": stock_id,
            "stock_name_market": str(row.get("證券名稱", "")).strip(),
            "trade_date": f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}",
            "open": num(row.get("開盤價")),
            "high": num(row.get("最高價")),
            "low": num(row.get("最低價")),
            "close": num(row.get("收盤價")),
            "volume_shares": int(num(row.get("成交股數")) or 0),
            "turnover_value": int(num(row.get("成交金額")) or 0),
            "trade_count": int(num(row.get("成交筆數")) or 0),
            "source": "TWSE_MI_INDEX",
        })
    return rows


def fetch_tpex_market(iso_date: str) -> list[dict[str, Any]]:
    yyyy, mm, dd = iso_date.split("-")
    url = f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={yyyy}/{mm}/{dd}&type=EW&response=json"
    data = fetch_json(url)
    table = data["tables"][0]
    fields = table["fields"]
    rows = []
    for arr in table["data"]:
        row = dict(zip(fields, arr))
        stock_id = str(row.get("代號", "")).strip()
        if not re.fullmatch(r"\d{4}", stock_id):
            continue
        rows.append({
            "market": "otc",
            "stock_id": stock_id,
            "stock_name_market": str(row.get("名稱", "")).strip(),
            "trade_date": iso_date,
            "open": num(row.get("開盤 ")),
            "high": num(row.get("最高 ")),
            "low": num(row.get("最低")),
            "close": num(row.get("收盤 ")),
            "volume_shares": int(num(row.get("成交股數  ")) or 0),
            "turnover_value": int(num(row.get(" 成交金額(元)")) or 0),
            "trade_count": int(num(row.get(" 成交筆數 ")) or 0),
            "source": "TPEX_OTC",
        })
    return rows


def read_revenue_rows() -> list[dict[str, Any]]:
    with REVENUE_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def percentile_ranks(values: list[tuple[str, float]]) -> dict[str, float]:
    if not values:
        return {}
    sorted_vals = sorted(values, key=lambda x: x[1])
    n = len(sorted_vals)
    out = {}
    for idx, (key, _value) in enumerate(sorted_vals):
        out[key] = idx / (n - 1) if n > 1 else 1.0
    return out


def as_float(row: dict[str, Any], key: str) -> float | None:
    try:
        text = str(row.get(key, "")).strip()
        return float(text) if text != "" else None
    except ValueError:
        return None


def build_candidates(revenues: list[dict[str, Any]], market_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    market_map = {(r["market"], r["stock_id"]): r for r in market_rows}
    universe = []
    for r in revenues:
        if r["market"] not in {"listed", "otc"}:
            continue
        sid = r["stock_id"]
        if not re.fullmatch(r"\d{4}", sid):
            continue
        yoy = as_float(r, "revenue_yoy_pct")
        mom = as_float(r, "revenue_mom_pct")
        revenue = as_float(r, "revenue_current_month")
        ytd_yoy = as_float(r, "revenue_ytd_yoy_pct")
        m = market_map.get((r["market"], sid))
        if yoy is None or mom is None or revenue is None or m is None:
            continue
        turnover = m.get("turnover_value") or 0
        universe.append({**r, **{f"m_{k}": v for k, v in m.items()}, "yoy": yoy, "mom": mom, "revenue": revenue, "ytd_yoy": ytd_yoy, "turnover_value": turnover})

    yoy_rank = percentile_ranks([((r["market"], r["stock_id"]), r["yoy"]) for r in universe])
    mom_rank = percentile_ranks([((r["market"], r["stock_id"]), r["mom"]) for r in universe])
    turnover_rank = percentile_ranks([((r["market"], r["stock_id"]), math.log1p(max(0, r["turnover_value"]))) for r in universe])

    industry_groups: dict[str, list[tuple[tuple[str, str], float]]] = {}
    for r in universe:
        industry_groups.setdefault(r.get("industry", ""), []).append(((r["market"], r["stock_id"]), r["yoy"]))
    industry_yoy_rank = {}
    for vals in industry_groups.values():
        industry_yoy_rank.update(percentile_ranks(vals))

    candidates = []
    for r in universe:
        key = (r["market"], r["stock_id"])
        # Simple, interpretable MVP score. Not optimized.
        score = (
            0.40 * yoy_rank.get(key, 0)
            + 0.25 * industry_yoy_rank.get(key, 0)
            + 0.15 * mom_rank.get(key, 0)
            + 0.10 * (1.0 if (r["ytd_yoy"] is not None and r["ytd_yoy"] > 0) else 0.0)
            + 0.10 * turnover_rank.get(key, 0)
        )
        liquidity_pass_50m = r["turnover_value"] >= 50_000_000
        positive_growth_quality = r["yoy"] > 0 and r["mom"] > -30 and (r["ytd_yoy"] is None or r["ytd_yoy"] > -20)
        candidates.append({
            "market": r["market"],
            "stock_id": r["stock_id"],
            "stock_name": r.get("stock_name", ""),
            "industry": r.get("industry", ""),
            "revenue_month": r.get("revenue_month", ""),
            "report_date": r.get("report_date", ""),
            "trade_date": r.get("m_trade_date", ""),
            "revenue_current_month": r["revenue"],
            "revenue_yoy_pct": r["yoy"],
            "revenue_mom_pct": r["mom"],
            "revenue_ytd_yoy_pct": r["ytd_yoy"],
            "close": r.get("m_close"),
            "turnover_value": r["turnover_value"],
            "yoy_rank_pct": round(100 * yoy_rank.get(key, 0), 2),
            "industry_yoy_rank_pct": round(100 * industry_yoy_rank.get(key, 0), 2),
            "mom_rank_pct": round(100 * mom_rank.get(key, 0), 2),
            "turnover_rank_pct": round(100 * turnover_rank.get(key, 0), 2),
            "signal_score": round(score, 4),
            "liquidity_pass_50m": liquidity_pass_50m,
            "positive_growth_quality": positive_growth_quality,
            "selected_mvp_candidate": liquidity_pass_50m and positive_growth_quality,
            "warning": "research_candidate_only_not_investment_advice_no_order",
        })
    return sorted(candidates, key=lambda r: r["signal_score"], reverse=True)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    iso_date, yyyymmdd = find_recent_trading_date()
    market_rows = fetch_twse_market(yyyymmdd) + fetch_tpex_market(iso_date)
    MARKET_JSON.write_text(json.dumps(market_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(MARKET_CSV, market_rows)

    revenues = read_revenue_rows()
    candidates = build_candidates(revenues, market_rows)
    CANDIDATE_JSON.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(CANDIDATE_CSV, candidates)

    selected = [r for r in candidates if r["selected_mvp_candidate"]]
    top20 = selected[:20]
    industry_counts = {}
    for r in selected:
        industry_counts[r["industry"]] = industry_counts.get(r["industry"], 0) + 1
    industry_lines = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:15]

    md = []
    md.append("# 最新月營收候選清單研究摘要\n")
    md.append("本報告是研究用候選清單，不是投資建議，也沒有任何下單動作。\n")
    md.append(f"- 行情日期：{iso_date}\n")
    md.append(f"- 月營收資料筆數：{len(revenues)}\n")
    md.append(f"- 行情資料筆數：{len(market_rows)}\n")
    md.append(f"- 通過 MVP 成長與流動性初篩：{len(selected)}\n")
    md.append("\n## MVP 初篩規則\n")
    md.append("- 市場：上市 + 上櫃，不含興櫃。\n")
    md.append("- 股票代號：4 位數普通股樣式。\n")
    md.append("- 成長品質初篩：YoY > 0、MoM > -30%、YTD YoY 不低於 -20%。\n")
    md.append("- 流動性初篩：最新交易日成交金額 >= 5,000 萬元。\n")
    md.append("- 分數：YoY 全市場排名、產業內 YoY 排名、MoM 排名、YTD 是否正成長、成交金額排名的簡單加權。未最佳化。\n")
    md.append("\n## Top 20 研究候選\n")
    for i, r in enumerate(top20, 1):
        md.append(
            f"{i}. {r['stock_id']} {r['stock_name']}｜{r['market']}｜{r['industry']}｜"
            f"score={r['signal_score']}｜YoY={r['revenue_yoy_pct']:.2f}%｜MoM={r['revenue_mom_pct']:.2f}%｜"
            f"YTD YoY={r['revenue_ytd_yoy_pct']}%｜成交金額={int(r['turnover_value']):,}\n"
        )
    md.append("\n## 候選產業分布 Top 15\n")
    for industry, count in industry_lines:
        md.append(f"- {industry}: {count}\n")
    md.append("\n## 重要限制\n")
    md.append("- 目前只有最新一期 OpenAPI snapshot，尚非多年歷史回測。\n")
    md.append("- 月營收 OpenAPI 沒有逐公司公告 timestamp，只能用 report_date 作保守 proxy。\n")
    md.append("- 這份分數未納入公告前漲幅、3M 累計營收、除權息調整、處置股、法人籌碼與估值。\n")
    md.append("- 候選清單只用來協助後續研究和 paper trading，不代表買賣建議。\n")
    SUMMARY_MD.write_text("".join(md), encoding="utf-8")

    print(json.dumps({
        "trade_date": iso_date,
        "market_rows": len(market_rows),
        "revenue_rows": len(revenues),
        "candidates": len(candidates),
        "selected_mvp_candidates": len(selected),
        "outputs": [str(MARKET_CSV), str(CANDIDATE_CSV), str(SUMMARY_MD)],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
