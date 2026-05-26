#!/usr/bin/env python3
"""Phase 3.12: walk-forward OOS + sector survival stress.

Research-only. No live trading, no broker/API, no deployment.

Purpose:
- Preserve S1 portfolio-grade v0.1 as the incumbent.
- Test whether parameter selection survives a more realistic walk-forward protocol.
- Stress whether results are electronics/semiconductor-regime dependent.

Important limitation: still uses the existing conservative monthly-revenue usable-date
proxy and close-price execution proxy. Exact announcement timestamps and OHLC/limit
checks remain future gates.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
OUT_WF = PROCESSED / "walkforward_sector_oos.csv"
OUT_CAND = PROCESSED / "walkforward_candidate_pool.csv"
OUT_SECTOR = PROCESSED / "sector_survival_stress.csv"
OUT_MONTHLY = PROCESSED / "walkforward_oos_monthly.csv"
OUT_SUMMARY = PROCESSED / "walkforward_sector_summary.json"
OUT_REPORT = REPORTS / "phase3_12_walkforward_sector_survival_report.md"
OUT_CHART = CHARTS / "phase3_12_walkforward_oos_nav_zh.png"
OUT_SECTOR_CHART = CHARTS / "phase3_12_sector_survival_zh.png"

EX_PATH = ROOT / "scripts" / "execution_realism_tests.py"
spec = importlib.util.spec_from_file_location("execution_realism_tests", EX_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load {EX_PATH}")
ex = cast(Any, importlib.util.module_from_spec(spec))
spec.loader.exec_module(ex)

# Compact candidate pool: not every grid permutation; enough to test whether selection generalizes.
LIQS = [50_000_000, 100_000_000]
TOP_NS = [6, 8, 10, 12]
IND_CAPS = [2, 3, 4]
SEMI_CAPS: list[int | None] = [None, 2, 3]
RECIPES = ["base_sur_core", "sur3_high_no_high_mom"]
RULES = ["fixed", "trail10", "trail15", "sl8_trail12"]
MAX_HS = [15, 20]

INCUMBENT = {
    "recipe": "sur3_high_no_high_mom",
    "filter_recipe": "sur3_high_no_high_mom",
    "liq": 50_000_000,
    "top_n": 8,
    "industry_cap": 3,
    "semi_cap": None,
    "rule": "sl8_trail12",
    "max_h": 20,
}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def compound(rs: list[float]) -> float:
    nav = 1.0
    for r in rs:
        nav *= 1 + r
    return nav - 1


def mdd(rs: list[float]) -> float:
    nav = 1.0; peak = 1.0; worst = 0.0
    for r in rs:
        nav *= 1 + r
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1)
    return worst


def metrics(rs: list[float]) -> dict[str, Any]:
    if not rs:
        return {"months": 0}
    sd = statistics.stdev(rs) if len(rs) >= 2 else None
    total = compound(rs)
    return {
        "months": len(rs),
        "total_return": total,
        "ann_return": (1 + total) ** (12 / len(rs)) - 1,
        "mean_month": statistics.mean(rs),
        "median_month": statistics.median(rs),
        "sharpe": statistics.mean(rs) / sd * math.sqrt(12) if sd and sd > 1e-12 else None,
        "mdd": mdd(rs),
        "win_rate": sum(1 for x in rs if x > 0) / len(rs),
        "worst_month": min(rs),
        "best_month": max(rs),
    }


def monthly_returns(trades: list[dict[str, Any]], years: set[str] | None = None, sector_mode: str = "all", remove_keys: set[tuple[str, str, str]] | None = None) -> tuple[list[float], dict[str, float], dict[str, int]]:
    by: dict[str, list[float]] = defaultdict(list)
    entry_year_by_month: dict[str, str] = {}
    counts: dict[str, int] = defaultdict(int)
    for r in trades:
        entry_year = str(r["entry_date"])[:4]
        if years is not None and entry_year not in years:
            continue
        if not sector_keep(r.get("industry", ""), sector_mode):
            continue
        key = (r["revenue_month"], r["stock_id"], r["entry_date"])
        if remove_keys is not None and key in remove_keys:
            continue
        m = r["revenue_month"]
        entry_year_by_month[m] = entry_year
        by[m].append(float(r["net_return"]))
        counts[m] += 1
    return [statistics.mean(by[m]) for m in sorted(by)], {m: statistics.mean(by[m]) for m in sorted(by)}, counts


def sector_keep(industry: str, mode: str) -> bool:
    is_semi = industry == "半導體業"
    is_elec = ("電子" in industry) or ("半導體" in industry) or ("資訊" in industry)
    if mode == "all":
        return True
    if mode == "electronics_only":
        return is_elec
    if mode == "non_electronics":
        return not is_elec
    if mode == "no_semiconductor":
        return not is_semi
    if mode == "semiconductor_only":
        return is_semi
    raise ValueError(mode)


def remove_winner_sharpe(trades: list[dict[str, Any]], years: set[str] | None, n: int, sector_mode: str = "all") -> float | None:
    base = [r for r in trades if (years is None or str(r["entry_date"])[:4] in years) and sector_keep(r.get("industry", ""), sector_mode)]
    sorted_rows = sorted(base, key=lambda r: float(r["net_return"]), reverse=True)
    keys = {(r["revenue_month"], r["stock_id"], r["entry_date"]) for r in sorted_rows[:n]}
    rs, _by, _counts = monthly_returns(trades, years, sector_mode, keys)
    return metrics(rs).get("sharpe")


def variant_id(params: dict[str, Any]) -> str:
    semi = params["semi_cap"] if params["semi_cap"] is not None else "none"
    return f"{params['recipe']}|liq{params['liq']//1_000_000}m|top{params['top_n']}|ind{params['industry_cap']}|semi{semi}|{params['rule']}|{params['max_h']}D"


def build_candidate_pool() -> dict[str, dict[str, Any]]:
    pool: dict[str, dict[str, Any]] = {}
    for liq in LIQS:
        scored, prices_by_stock, date_map, th = ex.build_universe(liq)
        for recipe in RECIPES:
            for top_n in TOP_NS:
                for ind_cap in IND_CAPS:
                    if ind_cap > top_n:
                        continue
                    for semi_cap in SEMI_CAPS:
                        if semi_cap is not None and semi_cap > top_n:
                            continue
                        sigs = ex.select_signals(scored, th, recipe, top_n=top_n, industry_cap=ind_cap, semiconductor_cap=semi_cap)
                        if not sigs:
                            continue
                        base = {"recipe": recipe, "liq": liq, "top_n": top_n, "industry_cap": ind_cap, "semi_cap": semi_cap}
                        raw = ex.build_rule_trades(sigs, prices_by_stock, date_map, "tmp", RULES, MAX_HS)
                        for rule in RULES:
                            for max_h in MAX_HS:
                                rows = [dict(r) for r in raw if r["exit_rule"] == rule and int(r["max_holding_days"]) == max_h]
                                if not rows:
                                    continue
                                params = {**base, "rule": rule, "max_h": max_h}
                                vid = variant_id(params)
                                for r in rows:
                                    r["variant"] = vid
                                pool[vid] = {"params": params, "trades": rows}
    return pool


def summarize_variant(vid: str, trades: list[dict[str, Any]], years: set[str] | None = None, sector_mode: str = "all") -> dict[str, Any]:
    rs, _by, counts = monthly_returns(trades, years, sector_mode)
    sm = metrics(rs)
    return {
        "variant": vid,
        "years": "+".join(sorted(years)) if years else "all",
        "sector_mode": sector_mode,
        "months": sm.get("months"),
        "trades": sum(counts.values()),
        "avg_positions": sum(counts.values()) / (sm.get("months") or 1),
        "total_return": sm.get("total_return"),
        "ann_return": sm.get("ann_return"),
        "sharpe": sm.get("sharpe"),
        "mdd": sm.get("mdd"),
        "win_rate": sm.get("win_rate"),
        "remove5_sharpe": remove_winner_sharpe(trades, years, 5, sector_mode),
        "remove10_sharpe": remove_winner_sharpe(trades, years, 10, sector_mode),
    }


def selection_score(row: dict[str, Any]) -> float:
    # Prefer train Sharpe, but penalize winner dependence, too few names, and drawdown.
    s = float(row.get("sharpe") or -999)
    r5 = float(row.get("remove5_sharpe") or -999)
    avg_pos = float(row.get("avg_positions") or 0)
    mdd_abs = abs(float(row.get("mdd") or 0))
    if row.get("months", 0) < 5 or avg_pos < 5:
        return -999
    return min(s, r5 + 0.40) - 0.25 * max(0.0, mdd_abs - 0.12) + 0.03 * min(avg_pos, 10)


def run_walkforward(pool: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    wf_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []
    splits = [({"2023"}, {"2024"}, "train2023_test2024"), ({"2023", "2024"}, {"2025"}, "train2023_2024_test2025")]
    incumbent_vid = "sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D"
    for train_years, test_years, split_name in splits:
        train_summaries = []
        for vid, obj in pool.items():
            row = summarize_variant(vid, obj["trades"], train_years)
            row["selection_score"] = selection_score(row)
            train_summaries.append(row)
        selected = max(train_summaries, key=lambda r: r["selection_score"])
        selected_vid = selected["variant"]
        for role, vid in [("walkforward_selected", selected_vid), ("incumbent_fixed", incumbent_vid)]:
            if vid not in pool:
                continue
            test = summarize_variant(vid, pool[vid]["trades"], test_years)
            train = summarize_variant(vid, pool[vid]["trades"], train_years)
            out = {
                "split": split_name,
                "role": role,
                "selected_variant": selected_vid,
                "variant": vid,
                "train_years": "+".join(sorted(train_years)),
                "test_years": "+".join(sorted(test_years)),
                "selection_score": selected.get("selection_score") if role == "walkforward_selected" else selection_score(train),
                "train_sharpe": train.get("sharpe"), "train_return": train.get("total_return"), "train_mdd": train.get("mdd"), "train_remove5_sharpe": train.get("remove5_sharpe"),
                "test_sharpe": test.get("sharpe"), "test_return": test.get("total_return"), "test_mdd": test.get("mdd"), "test_remove5_sharpe": test.get("remove5_sharpe"),
                "test_months": test.get("months"), "test_avg_positions": test.get("avg_positions"),
            }
            wf_rows.append(out)
            rs, by_m, counts = monthly_returns(pool[vid]["trades"], test_years)
            for m, r in by_m.items():
                monthly_rows.append({"split": split_name, "role": role, "variant": vid, "revenue_month": m, "month_return": r, "positions": counts[m]})
    return wf_rows, monthly_rows


def run_sector_stress(pool: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    vids = [
        "sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D",
        "sur3_high_no_high_mom|liq100m|top8|ind3|seminone|trail15|20D",
        "sur3_high_no_high_mom|liq50m|top8|ind3|seminone|fixed|20D",
    ]
    modes = ["all", "electronics_only", "non_electronics", "no_semiconductor", "semiconductor_only"]
    rows = []
    for vid in vids:
        if vid not in pool:
            continue
        for mode in modes:
            rows.append(summarize_variant(vid, pool[vid]["trades"], None, mode))
    return rows


def fmt_pct(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2%}"


def fmt_num(x: Any) -> str:
    return "NA" if x is None else f"{float(x):.2f}"


def write_report(wf_rows: list[dict[str, Any]], sector_rows: list[dict[str, Any]], cand_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase 3.12 Walk-forward OOS + sector survival stress\n\n",
        "目標：把 S1 portfolio-grade v0.1 往業界可存活策略推進。這一階段檢查：用過去資料選參數是否能在未來 OOS 存活，以及績效是否過度依賴電子/半導體。仍是 research-only proxy backtest。\n\n",
        "## Walk-forward OOS result\n\n",
    ]
    for r in wf_rows:
        lines.append(f"- {r['split']} / {r['role']}：test Sharpe={fmt_num(r['test_sharpe'])}, test return={fmt_pct(r['test_return'])}, test MDD={fmt_pct(r['test_mdd'])}, test rm5S={fmt_num(r['test_remove5_sharpe'])}, avg positions={fmt_num(r['test_avg_positions'])}\n  variant: `{r['variant']}`\n")
    lines.append("\n## Sector survival stress\n\n")
    for r in sector_rows:
        lines.append(f"- `{r['variant']}` / {r['sector_mode']}：Sharpe={fmt_num(r['sharpe'])}, return={fmt_pct(r['total_return'])}, MDD={fmt_pct(r['mdd'])}, rm5S={fmt_num(r['remove5_sharpe'])}, avg positions={fmt_num(r['avg_positions'])}\n")
    lines += [
        "\n## Interpretation\n\n",
        "- 若 walk-forward selected 不能穩定打敗 fixed incumbent，代表目前參數搜尋仍不適合宣稱為可泛化選模。\n",
        "- 若 non-electronics / no-semiconductor 大幅衰退，策略應重新定位為電子/AI supply-chain revenue surprise strategy，而非全市場普適 alpha。\n",
        "- 這一階段仍未處理 exact announcement timestamp、OHLC、漲跌停與成交可得性；那些是下一個 execution-realism gate。\n\n",
        "## Outputs\n\n",
        f"- `{OUT_WF}`\n- `{OUT_CAND}`\n- `{OUT_SECTOR}`\n- `{OUT_MONTHLY}`\n- `{OUT_SUMMARY}`\n- `{OUT_CHART}`\n- `{OUT_SECTOR_CHART}`\n",
    ]
    OUT_REPORT.write_text("".join(lines), encoding="utf-8")


def write_charts(monthly_rows: list[dict[str, Any]], sector_rows: list[dict[str, Any]]) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        from matplotlib import rcParams
        for fp in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"]:
            if Path(fp).exists():
                fm.fontManager.addfont(fp)
                rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
                break
        rcParams["axes.unicode_minus"] = False
    except Exception:
        return

    # Walk-forward stitched OOS NAV by role.
    by_role: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for r in monthly_rows:
        by_role[r["role"]].append((f"{r['split']}:{r['revenue_month']}", float(r["month_return"])))
    fig, ax = plt.subplots(figsize=(12, 5))
    for role, rows in by_role.items():
        rows = sorted(rows, key=lambda x: x[0])
        nav = 1.0; ys=[]; xs=[]
        for x, ret in rows:
            nav *= 1 + ret; xs.append(x.split(":")[-1]); ys.append(nav)
        ax.plot(xs, ys, marker="o", linewidth=2, label=role)
    ax.set_title("Phase 3.12：Walk-forward OOS 串接淨值")
    ax.set_ylabel("OOS NAV，初始=1")
    ax.grid(True, alpha=.3); ax.legend(); ax.tick_params(axis="x", rotation=60)
    fig.tight_layout(); fig.savefig(OUT_CHART, dpi=160); plt.close(fig)

    # Sector stress Sharpe bars for S1 only.
    s1 = "sur3_high_no_high_mom|liq50m|top8|ind3|seminone|sl8_trail12|20D"
    rows = [r for r in sector_rows if r["variant"] == s1]
    labels = [r["sector_mode"] for r in rows]
    vals = [float(r["sharpe"] or 0) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, vals, color=["#4C78A8", "#72B7B2", "#F58518", "#E45756", "#54A24B"][:len(vals)])
    ax.axhline(2.5, color="green", linestyle="--", label="Sharpe 2.5")
    ax.set_title("S1 sector survival stress：不同產業切片 Sharpe")
    ax.set_ylabel("Sharpe proxy")
    ax.grid(True, axis="y", alpha=.3); ax.legend(); ax.tick_params(axis="x", rotation=25)
    fig.tight_layout(); fig.savefig(OUT_SECTOR_CHART, dpi=160); plt.close(fig)


def main() -> int:
    pool = build_candidate_pool()
    cand_rows = []
    for vid, obj in pool.items():
        all_row = summarize_variant(vid, obj["trades"], None)
        all_row["selection_score_all"] = selection_score(all_row)
        cand_rows.append(all_row)
    cand_rows.sort(key=lambda r: r["selection_score_all"], reverse=True)
    wf_rows, monthly_rows = run_walkforward(pool)
    sector_rows = run_sector_stress(pool)
    write_csv(OUT_CAND, cand_rows)
    write_csv(OUT_WF, wf_rows)
    write_csv(OUT_MONTHLY, monthly_rows)
    write_csv(OUT_SECTOR, sector_rows)
    summary = {
        "candidate_variants": len(pool),
        "walkforward_rows": len(wf_rows),
        "sector_rows": len(sector_rows),
        "outputs": [str(OUT_WF), str(OUT_CAND), str(OUT_SECTOR), str(OUT_MONTHLY), str(OUT_SUMMARY), str(OUT_REPORT), str(OUT_CHART), str(OUT_SECTOR_CHART)],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(wf_rows, sector_rows, cand_rows)
    write_charts(monthly_rows, sector_rows)
    print(json.dumps({"candidate_variants": len(pool), "walkforward_rows": len(wf_rows), "sector_rows": len(sector_rows), "outputs": summary["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
