# Taiwan Monthly Revenue Surprise Strategy

> 台股月營收驚喜策略研究 — 從市場結構假說到 execution-aware validation

**作者:** 劉晏禎 (Liu Yen-Zhen) — miles891002@gmail.com
**性質:** 研究 / paper-trading 專案，非實盤交易系統，非投資建議

---

## 一句話介紹

研究台灣上市櫃公司「月營收公布制度」是否在公告後 10–20 個交易日造成可觀察的短線 post-disclosure drift，並用業界標準的 robustness gates 檢查策略是否值得進入 paper trading。

## 為什麼選這個題目

台灣的月營收揭露是全球少見的高頻基本面資訊：

- 比季報更頻繁，比新聞更結構化
- 反映供應鏈訂單、價格、出貨變化
- 是合法可觀察、可程式化驗證的官方公開資訊

如果市場參與者需要時間消化 surprise 持續性，repricing 可能不是一天完成，而是分布在公告後的 10–20 個交易日。

## 核心成果（V6 履歷附件版 Headline）

| 版本 | 設計 | Return | Sharpe | MDD |
|---|---|---|---|---|
| **S1 incumbent** | 3M SUR + no-overheated momentum + 20D | +167.5% | ≈2.40 | -7.9% |
| S1 fixed-20 comparator | 簡潔固定持有 benchmark | +161.9% | 1.55 | -21.2% |
| Quiet boost | quiet digestion sizing overlay | +174.4% | 1.62 | -21.2% |
| Conservative execution | next-open + 1.0% 成本 + non-fill stress | +111.9% | 1.24 | -24.9% |
| **FRR best first-pass** (diagnostic) | 融資去槓桿 + volume absorption | +251.4% | 1.55 | -17.6% |

> S1 是 portfolio-grade **v0.1 research candidate**，不是 production-ready alpha。FRR 有訊號但右尾依賴，只作為 S1 的 diagnostic layer。

## 研究紀律：這個專案展示什麼

- 從**市場結構假說**出發，而非指標 mining
- 用官方月營收建構 SUR-style factor，明確標示資料可得時間
- 從 proxy backtest 走到完整 robustness gates
- 保留 promising variants 而非用新版本覆蓋（promising strategy registry）
- 對 winner dependence / sector dependence / walk-forward OOS / liquidity / cost / execution realism 一個都不省
- **誠實不升級**（knowing when *not* to promote）——FRR 與 quiet digestion 都不被宣稱為獨立策略

## 主要作品集文件

完整作品集在 [`portfolio_project/`](portfolio_project/) 下：
- [`Taiwan_Monthly_Revenue_Strategy_Resume_Version_ZH_PRO_V6.pdf`](portfolio_project/Taiwan_Monthly_Revenue_Strategy_Resume_Version_ZH_PRO_V6.pdf) — **履歷附件 PDF**，封面 KPI、章節敘事、12 張圖表

### 研究紀錄與 markdown 文件

| 檔案 | 內容 |
|---|---|
| [`01_methodology_report.md`](portfolio_project/01_methodology_report.md) | 完整研究敘事與流程 |
| [`02_strategy_card.md`](portfolio_project/02_strategy_card.md) | 一頁策略卡 |
| [`03_research_timeline.md`](portfolio_project/03_research_timeline.md) | 階段演進史 |
| [`04_robustness_dashboard.md`](portfolio_project/04_robustness_dashboard.md) | Robustness 表格與解讀 |
| [`05_execution_and_paper_trading.md`](portfolio_project/05_execution_and_paper_trading.md) | Execution realism 與 paper-trading 計畫 |
| [`06_limitations_and_next_steps.md`](portfolio_project/06_limitations_and_next_steps.md) | 誠實限制與 roadmap |
| [`07_interview_qna.md`](portfolio_project/07_interview_qna.md) | 面試挑戰題與回答 |
| [`reproducibility.md`](portfolio_project/reproducibility.md) | 重現腳本與報告路徑 |

## Repository 結構

```text
.
├── README.md                  # 本檔
├── portfolio_project/         # 作品集文件（PDF / DOCX / markdown / charts）
├── reports/                   # 階段研究報告（phase2 → phase4.1）
├── scripts/                   # 各階段研究腳本
├── data/processed/            # FRR Phase 4.1 變體結果 CSV
└── .gitignore
```

## 已知限制（誠實聲明）

- **Exact timing**：缺公司級歷史公告 timestamp，不宣稱 same-day tradability
- **Survivorship / universe**：歷史 universe 與下市資料仍待補強
- **Winner dependence**：remove-winner 後 Sharpe 衰退
- **Sector concentration**：電子 / 半導體供應鏈依賴明顯，定位需限縮
- **Execution realism**：開盤跳空、漲停 non-fill、流動性容量需 paper trading 驗證

對外建議說法：

> 一個台股月營收 surprise 的 portfolio-grade quant research project，候選策略具有吸引人的 proxy 結果，但仍需 exact announcement timestamps、強化 universe 控制、execution simulation 與 paper-trading 驗證後，才可能宣稱接近實盤。

## 接下來

- Paper trading schema 已建立（`08_paper_trading_template.md`、`paper_trading_log_template.csv`）
- 下一步是停止追求更高 full-sample Sharpe，改以 paper trading 驗證 operational feasibility

## License & Disclaimer

僅供研究、學術討論與作品集展示使用。本專案：

- 不下單、不連券商 API、不持有任何資產
- 結果為歷史 / proxy diagnostics，受資料時間、survivorship、成交、容量、regime 風險影響
- **非投資建議**

如需轉載或引用研究內容，請聯絡作者：miles891002@gmail.com
