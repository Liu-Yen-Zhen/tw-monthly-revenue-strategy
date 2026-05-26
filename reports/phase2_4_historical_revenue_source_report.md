# Phase 2.4 歷史月營收資料源攻關報告

本報告驗證官方 MOPS 靜態 NAS 月營收檔是否可作為免費歷史月營收來源。

## 結論

- `doc.twse.com.tw/nas/t21/...` 靜態 HTML 檔可用。
- 可取得上市與上櫃歷史月營收彙總。
- 靜態彙總檔沒有逐公司公告 timestamp，因此正式事件回測仍需保守 usable date proxy 或另抓公司級公告頁。

## 覆蓋範圍

- 起始月份：2021-01
- 最新月份：2026-04
- 成功 market-month 數：120
- 總資料列數：106,785
- listed: 57,303 rows
- otc: 49,482 rows

## 產出

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/historical_monthly_revenue_mops_static.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/historical_monthly_revenue_mops_static.json`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/historical_monthly_revenue_mops_static_metadata.json`

## 重要限制

- 此資料可做歷史探索與 proxy backtest，但不能精準模擬每家公司公告後第 1 天進場。
- `usable_date_proxy` 目前設為次月 11 日；後續需映射到下一個交易日。
- 仍需處理下市櫃、處置股、除權息、歷史產業分類變動。
