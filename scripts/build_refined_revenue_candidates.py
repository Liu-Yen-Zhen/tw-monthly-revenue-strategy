#!/usr/bin/env python3
"""Phase 2.3: Build refined monthly-revenue research candidates.

Research-only script. It:
- Downloads recent official TWSE/TPEx daily market snapshots with throttling.
- Computes 20/60-trading-day pre-snapshot returns and 20-day average turnover.
- Re-scores latest monthly revenue candidates after excluding obvious contaminants.

It does NOT trade, deploy, delete files, install packages, commit, or push.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "openapi"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
for p in [RAW_DIR, PROCESSED_DIR, REPORT_DIR]:
    p.mkdir(parents=True, exist_ok=True)

REVENUE_CSV = RAW_DIR / "latest_monthly_revenue_openapi.csv"
HIST_CSV = RAW_DIR / "recent_market_history_90d.csv"
REFINED_CSV = PROCESSED_DIR / "refined_revenue_candidates.csv"
REFINED_JSON = PROCESSED_DIR / "refined_revenue_candidates.json"
REPORT_MD = REPORT_DIR / "phase2_3_refined_candidate_report.md"

USER_AGENT = "Mozilla/5.0 (Hermes quant research; read-only)"

EXCLUDED_INDUSTRIES = {"金融保險業"}
MIN_CURRENT_REVENUE_THOUSAND = 100_000       # 1 億元；OpenAPI 月營收單位通常為千元。
MIN_LAST_YEAR_REVENUE_THOUSAND = 100_000    # 避免低基期 YoY 爆衝。
MIN_AVG_TURNOVER_20D = 50_000_000           # 5,000 萬元。
MAX_PRE_RETURN_20D = 0.30                   # 公告/出表後觀察時，20 日內已大漲超過 30% 先標記過熱。
MAX_PRE_RETURN_60D = 1.00                   # 60 日內翻倍先標記過熱。
LOOKBACK_CALENDAR_DAYS = 150                # 足夠覆蓋 90 個交易日附近。
TARGET_TRADING_DAYS = 90
REQUEST_SLEEP_SECONDS = 0.35


def fetch_json(url: str, retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=35) as resp:
                return json.loads(resp.read().decode("utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error!r}")


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


def fetch_twse_market(date_: dt.date) -> list[dict[str, Any]]:
    yyyymmdd = date_.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={yyyymmdd}&type=ALLBUT0999&response=json"
    data = fetch_json(url)
    if data.get("stat") != "OK":
        return []
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
        close = num(row.get("收盤價"))
        turnover = num(row.get("成交金額"))
        if close is None or turnover is None:
            continue
        rows.append({
            "trade_date": date_.isoformat(),
            "market": "listed",
            "stock_id": sid,
            "stock_name": str(row.get("證券名稱", "")).strip(),
            "close": close,
            "turnover_value": int(turnover),
            "volume_shares": int(num(row.get("成交股數")) or 0),
        })
    return rows


def fetch_tpex_market(date_: dt.date) -> list[dict[str, Any]]:
    url = f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={date_.strftime('%Y/%m/%d')}&type=EW&response=json"
    data = fetch_json(url)
    if data.get("stat") not in {"OK", None} and not data.get("tables"):
        return []
    if not data.get("tables"):
        return []
    table = data["tables"][0]
    fields = table.get("fields", [])
    rows = []
    for arr in table.get("data", []):
        row = dict(zip(fields, arr))
        sid = str(row.get("代號", "")).strip()
        if not re.fullmatch(r"\d{4}", sid):
            continue
        close = num(row.get("收盤 "))
        turnover = num(row.get(" 成交金額(元)"))
        if close is None or turnover is None:
            continue
        rows.append({
            "trade_date": date_.isoformat(),
            "market": "otc",
            "stock_id": sid,
            "stock_name": str(row.get("名稱", "")).strip(),
            "close": close,
            "turnover_value": int(turnover),
            "volume_shares": int(num(row.get("成交股數  ")) or 0),
        })
    return rows


def fetch_recent_market_history() -> list[dict[str, Any]]:
    today = dt.date.today()
    all_rows: list[dict[str, Any]] = []
    trading_dates: set[str] = set()
    for offset in range(LOOKBACK_CALENDAR_DAYS + 1):
        d = today - dt.timedelta(days=offset)
        if d.weekday() >= 5:
            continue
        day_rows = []
        try:
            day_rows.extend(fetch_twse_market(d))
            time.sleep(REQUEST_SLEEP_SECONDS)
            day_rows.extend(fetch_tpex_market(d))
            time.sleep(REQUEST_SLEEP_SECONDS)
        except Exception:
            continue
        if day_rows:
            all_rows.extend(day_rows)
            trading_dates.add(d.isoformat())
        if len(trading_dates) >= TARGET_TRADING_DAYS:
            break
    return all_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_float(row: dict[str, Any], key: str) -> float | None:
    try:
        text = str(row.get(key, "")).strip()
        return float(text) if text else None
    except ValueError:
        return None


def percentile_ranks(items: list[tuple[tuple[str, str], float]]) -> dict[tuple[str, str], float]:
    items = [(k, v) for k, v in items if v is not None and not math.isnan(v)]
    if not items:
        return {}
    items = sorted(items, key=lambda x: x[1])
    n = len(items)
    return {key: idx / (n - 1) if n > 1 else 1.0 for idx, (key, _value) in enumerate(items)}


def compute_price_features(history: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    by_stock: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in history:
        by_stock[(r["market"], r["stock_id"])].append(r)
    features = {}
    for key, rows in by_stock.items():
        rows = sorted(rows, key=lambda r: r["trade_date"])
        if len(rows) < 21:
            continue
        latest = rows[-1]
        close_latest = float(latest["close"])
        close_20 = float(rows[-21]["close"]) if len(rows) >= 21 else None
        close_60 = float(rows[-61]["close"]) if len(rows) >= 61 else None
        ret20 = close_latest / close_20 - 1 if close_20 and close_20 > 0 else None
        ret60 = close_latest / close_60 - 1 if close_60 and close_60 > 0 else None
        last20 = rows[-20:]
        turnovers = [int(float(r["turnover_value"])) for r in last20]
        features[key] = {
            "latest_trade_date": latest["trade_date"],
            "latest_close": close_latest,
            "ret_20d": ret20,
            "ret_60d": ret60,
            "avg_turnover_20d": statistics.mean(turnovers),
            "median_turnover_20d": statistics.median(turnovers),
            "latest_turnover": int(float(latest["turnover_value"])),
            "history_days": len(rows),
        }
    return features


def build_refined(revenues: list[dict[str, Any]], features: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    base = []
    for r in revenues:
        market = r.get("market", "")
        if market not in {"listed", "otc"}:
            continue
        sid = r.get("stock_id", "")
        key = (market, sid)
        f = features.get(key)
        if not f:
            continue
        industry = r.get("industry", "")
        yoy = as_float(r, "revenue_yoy_pct")
        mom = as_float(r, "revenue_mom_pct")
        ytd_yoy = as_float(r, "revenue_ytd_yoy_pct")
        cur_rev = as_float(r, "revenue_current_month")
        last_rev = as_float(r, "revenue_same_month_last_year")
        if None in {yoy, mom, cur_rev, last_rev}:
            continue
        exclusion = []
        if industry in EXCLUDED_INDUSTRIES:
            exclusion.append("excluded_industry_financial")
        if cur_rev < MIN_CURRENT_REVENUE_THOUSAND:
            exclusion.append("current_revenue_too_small")
        if last_rev < MIN_LAST_YEAR_REVENUE_THOUSAND:
            exclusion.append("last_year_base_too_small")
        if yoy <= 0:
            exclusion.append("yoy_not_positive")
        if mom <= -30:
            exclusion.append("mom_too_negative")
        if ytd_yoy is not None and ytd_yoy <= -20:
            exclusion.append("ytd_yoy_too_weak")
        if f["avg_turnover_20d"] < MIN_AVG_TURNOVER_20D:
            exclusion.append("avg_turnover_20d_too_low")
        if f["ret_20d"] is not None and f["ret_20d"] > MAX_PRE_RETURN_20D:
            exclusion.append("pre_return_20d_overheated")
        if f["ret_60d"] is not None and f["ret_60d"] > MAX_PRE_RETURN_60D:
            exclusion.append("pre_return_60d_overheated")
        base.append({
            "market": market,
            "stock_id": sid,
            "stock_name": r.get("stock_name", ""),
            "industry": industry,
            "revenue_month": r.get("revenue_month", ""),
            "report_date": r.get("report_date", ""),
            "revenue_current_month": cur_rev,
            "revenue_same_month_last_year": last_rev,
            "revenue_yoy_pct": yoy,
            "revenue_mom_pct": mom,
            "revenue_ytd_yoy_pct": ytd_yoy,
            **f,
            "exclusion_reasons": ";".join(exclusion),
            "passes_refined_filter": not exclusion,
        })

    eligible_for_rank = [r for r in base if r["passes_refined_filter"]]
    yoy_rank = percentile_ranks([((r["market"], r["stock_id"]), r["revenue_yoy_pct"]) for r in eligible_for_rank])
    mom_rank = percentile_ranks([((r["market"], r["stock_id"]), r["revenue_mom_pct"]) for r in eligible_for_rank])
    turnover_rank = percentile_ranks([((r["market"], r["stock_id"]), math.log1p(r["avg_turnover_20d"])) for r in eligible_for_rank])
    # Less pre-runup is better after passing overheating filters.
    runup_rank = percentile_ranks([((r["market",] if False else (r["market"], r["stock_id"])), -(r["ret_20d"] or 0.0)) for r in eligible_for_rank])
    industry_groups: dict[str, list[tuple[tuple[str, str], float]]] = defaultdict(list)
    for r in eligible_for_rank:
        industry_groups[r["industry"]].append(((r["market"], r["stock_id"]), r["revenue_yoy_pct"]))
    industry_rank = {}
    for vals in industry_groups.values():
        industry_rank.update(percentile_ranks(vals))

    out = []
    for r in base:
        key = (r["market"], r["stock_id"])
        if r["passes_refined_filter"]:
            score = (
                0.30 * yoy_rank.get(key, 0)
                + 0.25 * industry_rank.get(key, 0)
                + 0.15 * mom_rank.get(key, 0)
                + 0.15 * runup_rank.get(key, 0)
                + 0.10 * turnover_rank.get(key, 0)
                + 0.05 * (1.0 if (r["revenue_ytd_yoy_pct"] is not None and r["revenue_ytd_yoy_pct"] > 0) else 0.0)
            )
        else:
            score = -1.0
        r.update({
            "yoy_rank_pct_refined": round(100 * yoy_rank.get(key, 0), 2) if r["passes_refined_filter"] else "",
            "industry_yoy_rank_pct_refined": round(100 * industry_rank.get(key, 0), 2) if r["passes_refined_filter"] else "",
            "mom_rank_pct_refined": round(100 * mom_rank.get(key, 0), 2) if r["passes_refined_filter"] else "",
            "low_runup_rank_pct_refined": round(100 * runup_rank.get(key, 0), 2) if r["passes_refined_filter"] else "",
            "turnover_rank_pct_refined": round(100 * turnover_rank.get(key, 0), 2) if r["passes_refined_filter"] else "",
            "refined_signal_score": round(score, 4),
            "warning": "research_candidate_only_not_investment_advice_no_order",
        })
        out.append(r)
    return sorted(out, key=lambda r: r["refined_signal_score"], reverse=True)


def write_report(refined: list[dict[str, Any]], history: list[dict[str, Any]]) -> None:
    passed = [r for r in refined if r["passes_refined_filter"]]
    industry_counts = defaultdict(int)
    for r in passed:
        industry_counts[r["industry"]] += 1
    exclusion_counts = defaultdict(int)
    for r in refined:
        if r["exclusion_reasons"]:
            for reason in r["exclusion_reasons"].split(";"):
                exclusion_counts[reason] += 1
    dates = sorted({r["trade_date"] for r in history})
    top20 = passed[:20]

    lines = []
    lines.append("# Phase 2.3 研究級清理候選清單報告\n\n")
    lines.append("本報告只供研究與 paper trading 前置分析，不是投資建議，沒有任何下單。\n\n")
    lines.append("## 本階段做了什麼\n\n")
    lines.append("- 抓取近 90 個交易日左右的 TWSE/TPEx 官方日行情。\n")
    lines.append("- 計算 20/60 交易日報酬、20 日平均/中位數成交金額。\n")
    lines.append("- 排除金融業、低基期、低營收、低流動性、短期過熱標的。\n")
    lines.append("- 重新建立更保守的研究候選清單。\n\n")
    lines.append("## 資料覆蓋\n\n")
    lines.append(f"- 行情交易日數：{len(dates)}\n")
    lines.append(f"- 行情日期範圍：{dates[0] if dates else ''} 到 {dates[-1] if dates else ''}\n")
    lines.append(f"- 行情資料列數：{len(history)}\n")
    lines.append(f"- 可評估股票數：{len(refined)}\n")
    lines.append(f"- 通過研究級清理：{len(passed)}\n\n")
    lines.append("## 清理規則\n\n")
    lines.append(f"- 排除產業：{', '.join(sorted(EXCLUDED_INDUSTRIES))}\n")
    lines.append(f"- 當月營收 >= {MIN_CURRENT_REVENUE_THOUSAND:,} 千元\n")
    lines.append(f"- 去年同月營收 >= {MIN_LAST_YEAR_REVENUE_THOUSAND:,} 千元\n")
    lines.append("- YoY > 0\n")
    lines.append("- MoM > -30%\n")
    lines.append("- YTD YoY > -20%\n")
    lines.append(f"- 20 日平均成交金額 >= {MIN_AVG_TURNOVER_20D:,} 元\n")
    lines.append(f"- 20 日漲幅 <= {MAX_PRE_RETURN_20D:.0%}\n")
    lines.append(f"- 60 日漲幅 <= {MAX_PRE_RETURN_60D:.0%}\n\n")
    lines.append("## 排除原因統計\n\n")
    for reason, count in sorted(exclusion_counts.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {reason}: {count}\n")
    lines.append("\n## 通過候選產業分布 Top 15\n\n")
    for industry, count in sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
        lines.append(f"- {industry}: {count}\n")
    lines.append("\n## Top 20 研究候選\n\n")
    for i, r in enumerate(top20, 1):
        lines.append(
            f"{i}. {r['stock_id']} {r['stock_name']}｜{r['market']}｜{r['industry']}｜"
            f"score={r['refined_signal_score']}｜YoY={r['revenue_yoy_pct']:.2f}%｜MoM={r['revenue_mom_pct']:.2f}%｜"
            f"20D報酬={(r['ret_20d'] or 0):.2%}｜60D報酬={(r['ret_60d'] or 0):.2%}｜"
            f"20D均成交={int(r['avg_turnover_20d']):,}\n"
        )
    lines.append("\n## 解讀\n\n")
    lines.append("這份清單比上一版更接近研究可用，因為它不再只看單日成交金額與 headline YoY，而是加入了低基期、產業、流動性與價格是否已大漲的檢查。\n\n")
    lines.append("但它仍不是回測結果，也不是交易訊號。下一步需要取得歷史月營收序列或開始累積 point-in-time snapshots，並做 paper trading 追蹤。\n")
    REPORT_MD.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    history = fetch_recent_market_history()
    write_csv(HIST_CSV, history)
    revenues = read_csv(REVENUE_CSV)
    features = compute_price_features(history)
    refined = build_refined(revenues, features)
    write_csv(REFINED_CSV, refined)
    REFINED_JSON.write_text(json.dumps(refined, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(refined, history)
    passed = sum(1 for r in refined if r["passes_refined_filter"])
    print(json.dumps({
        "history_rows": len(history),
        "history_trading_days": len({r["trade_date"] for r in history}),
        "evaluated": len(refined),
        "passed_refined_filter": passed,
        "outputs": [str(HIST_CSV), str(REFINED_CSV), str(REPORT_MD)],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
