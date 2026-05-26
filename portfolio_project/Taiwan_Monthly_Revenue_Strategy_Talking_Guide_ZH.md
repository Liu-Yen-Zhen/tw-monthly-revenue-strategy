# 台股月營收驚喜策略研究作品集 — 導讀與講稿版

**用途：** 面試、作品集口頭報告、履歷專案說明  
**目標：** 幫助你知道每個部分要講什麼、講多久、被追問時如何回答  

---

## 0. 30 秒版本

### 你可以這樣講

我做的是一個台股月營收驚喜策略研究。台灣公司每月公布營收，所以比一般季度財報有更高頻的基本面更新。我研究市場是否會對連續性的營收 surprise 反應不足，導致公布後 10–20 個交易日有短期 repricing。

我不是只做高 Sharpe 回測，而是從官方資料建立 pipeline，設計 SUR-style surprise 因子，做 portfolio backtest，再做 walk-forward、sector survival、remove-winner、成本與執行時點檢查。最後保留一個 portfolio-grade 的電子 / 半導體供應鏈候選策略，但我不宣稱它已經 production-ready，因為 exact announcement timestamp、survivorship、execution fill 和 paper trading 還需要補強。

### 面試官聽到的重點

- 你從市場制度出發，不是 indicator mining。
- 你懂 data timing 和 look-ahead bias。
- 你懂 robustness，而不是只看漂亮績效。
- 你知道什麼時候不能 overclaim。

---

## 1. 專案動機要講什麼？

### 你要傳達的核心

台灣月營收制度是一個很適合量化研究的市場特徵。

### 建議講法

這個策略不是從技術指標開始，而是從台灣市場制度開始。台灣上市櫃公司每月公布營收，等於市場每個月都會收到一次基本面更新。我想測試的是：如果某些公司連續幾個月營收都超出預期，市場是否會延遲反應？這種延遲反應是否會反映在公布後 10–20 個交易日的股價漂移？

### 不要這樣講

- 「我發現營收成長高就會漲。」
- 「我用很多指標找出高 Sharpe。」
- 「這個策略一定有效。」

### 被追問：為什麼市場會反應不足？

可以回答：

月營收資料雖然公開，但解讀需要產業脈絡。例如電子供應鏈的月營收可能代表訂單、出貨、客戶需求或景氣循環變化。不是所有投資人都會在公告當下完整調整預期，因此可能產生短期 post-announcement drift。

---

## 2. 資料部分要講什麼？

### 你要傳達的核心

你知道資料時點比模型更重要。

### 建議講法

我使用台灣上市櫃月營收資料、每日市場資料，以及官方 raw daily JSON。研究中我特別區分 revenue month、data available date、signal date 和 trade date，避免把營收月份誤當成可以交易的時間。

目前最大的資料限制是，我的歷史月營收表還沒有完整的 company-level exact announcement timestamp，所以我不宣稱 same-day tradability。後面的 execution realism 是用 next-open / delayed entry proxy 來保守處理。

### 一定要講的關鍵字

- revenue month 不等於 signal date
- announcement timestamp
- data available date
- look-ahead bias
- next trading day conservative entry

### 被追問：你如何避免 look-ahead bias？

可以回答：

我沒有用 revenue month 當交易時間，而是使用 usable date proxy，並在後期用 delayed entry / next-open stress test。因為 exact timestamp 尚未完整，我把這點明確列為 limitation，而不是假裝已經解決。

---

## 3. 因子設計要講什麼？

### 你要傳達的核心

你測的是 surprise，不是單純 growth。

### 建議講法

我一開始測過 YoY、MoM、3-month growth、SUR-style surprise、產業調整 surprise 等。最後比較穩定的是 3M SUR persistence 加上 not-overheated momentum。這代表我想找的是持續性的營收驚喜，但排除股價已經過度反映的標的。

### 為什麼 SUR 比 raw YoY 好？

可以回答：

raw YoY 容易受到基期影響，也可能已經被市場預期。SUR-style surprise 比較接近「超出預期」的部分，較符合 post-announcement drift 的研究假說。

### 簡短公式式講法

```text
高 3M SUR persistence
+ 股價未過熱
+ 足夠流動性
+ 每月 Top N selection
= 月營收 surprise repricing candidate
```

---

## 4. 策略設定要講什麼？

### 你要傳達的核心

策略規則簡單、可解釋、有風控。

### 建議講法

最後保留的 incumbent 是 S1：使用 3M SUR persistence、排除過熱 momentum、流動性門檻 5,000 萬、每月選 Top 8，industry cap 3，持有 20 個交易日。這樣做是為了避免太集中在單一產業，也避免小型低流動性股票把績效灌高。

### 你可以展示的設定

```text
sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D
```

### 被追問：為什麼是 20D？

可以回答：

我有測過 10–20D。10D 比較像事件交易，容易依賴少數右尾贏家；20D 在解釋上比較符合公布後逐步 repricing，也比較穩定。因此我把 fixed 20D 當 benchmark。

---

## 5. 績效結果要怎麼講？

### 你要傳達的核心

講結果，但不要過度推銷。

### 建議講法

S1 在 portfolio-grade proxy 裡 Sharpe 大約 2.40，總報酬約 167.5%，MDD 約 -7.9%。但我不把它直接當成 production alpha，因為 remove-winner 後 Sharpe 下降，且 2025 表現可能受到電子、AI、記憶體等 regime 影響。

### 履歷版可以寫

- Built Taiwan monthly-revenue SUR strategy with proxy Sharpe around 2.4.
- Added robustness tests: OOS, sector survival, remove-winner, liquidity, cost, execution timing.
- Reframed candidate as electronics / semiconductor supply-chain repricing, not broad-market alpha.

### 被追問：Sharpe 2.4 可以信嗎？

可以回答：

我會把它視為 proxy diagnostic，而不是 production claim。因為它還需要 exact timestamp、survivorship、execution fill 和 paper trading 驗證。我比較重視的是它在多個 robustness check 下還有研究價值，而不是單一 Sharpe 數字。

---

## 6. 圖表要怎麼講？

## 6.1 NAV / Drawdown 圖

### 要講什麼

這張圖用來說明策略整體路徑，而不是只看最後報酬。

### 建議講法

這張圖我會看三件事：第一，NAV 是否只靠單一月份拉起來；第二，drawdown 是否集中在特定 regime；第三，回撤後是否能恢復。S1 的路徑有吸引力，但仍然需要搭配 remove-winner 和 sector analysis，避免被少數大贏家誤導。

---

## 6.2 月報酬 IS/OOS 圖

### 要講什麼

這張圖用來說明 train / test period 的表現差異。

### 建議講法

我不只看 full-sample，而是拆 train 和 OOS。2025 OOS 看起來強，但我會保守解讀，因為它可能和當年的 AI / 半導體 regime 有關。所以後面我做了 sector survival 和 no-semiconductor stress。

---

## 6.3 Sharpe vs MDD scatter

### 要講什麼

這張圖展示你不是只挑最高 Sharpe。

### 建議講法

我用這張圖看不同策略變體在 return quality 和 drawdown 之間的 trade-off。不是 Sharpe 最高就直接選，還要看 remove-winner、交易數、產業集中與執行可行性。

---

## 6.4 Remove-winners decay

### 要講什麼

這張圖很重要，顯示策略是否靠少數大贏家。

### 建議講法

如果移除前幾名大贏家後 Sharpe 快速下降，代表策略有 right-tail dependence。這不是完全不能接受，因為很多趨勢 / event-driven 策略本來就靠右尾，但必須誠實揭露，並控制部位與風險。

---

## 6.5 Sector survival

### 要講什麼

這張圖用來決定策略定位。

### 建議講法

Sector survival 顯示策略在半導體 / 電子比較強，no-semiconductor 後明顯變弱。所以我沒有把它定位成全市場台股策略，而是定位成電子 / 半導體供應鏈月營收 surprise repricing。

---

## 7. Quiet digestion 要怎麼講？

### 你要傳達的核心

這是有因果解釋的 extension，但沒有被過度提升。

### 建議講法

後面我研究 price-volume / K-line，不是為了做技術分析，而是想知道月營收 surprise 後市場如何消化資訊。quiet digestion 指的是高 SUR、股價未過熱、低異常成交量、窄幅整理。直覺是好消息公布後沒有爆量追高，市場可能還在消化。

但 standalone quiet digestion 交易數偏少，而且 remove-winner 後會衰退，所以我沒有把它提升為主策略，只把它保留為 S1 的 sizing hypothesis。

### 被追問：這是不是技術分析？

可以回答：

我不是用 K 線名稱挖 alpha，而是把價格 / 成交量當成市場消化基本面 surprise 的狀態變數。每個 price-volume condition 都要接回月營收 repricing 的因果鏈，否則不 promotion。

---

## 8. Execution realism 要怎麼講？

### 你要傳達的核心

你知道回測和能交易是兩回事。

### 建議講法

我後期加入 next-open、next-close、延遲 0/1/2/3 天、成本 0.7% / 1.0% / 1.5%、漲停無法成交 proxy。保守假設下 Sharpe 會下降，例如 next-open + 1.0% cost + exclude limit-up risk 後，quiet boost Sharpe 約 1.24。這代表策略仍有研究價值，但不能直接宣稱 production-ready。

### 被追問：如果績效下降，為什麼還值得做？

可以回答：

因為研究價值不只在最漂亮的回測，而在於知道 alpha 在哪些假設下仍存在、在哪些假設下消失。保守執行下仍為正，但 quality 下降，正好說明下一步要做 paper trading 和 exact timestamp。

---

## 9. Paper trading 要怎麼講？

### 你要傳達的核心

下一步不是再 overfit，而是驗證操作可行性。

### 建議講法

我認為下一階段不應該再擴大 grid search，而是進入 paper trading。每月記錄資料何時被觀察到、訊號何時生成、計畫進場日、是否漲停無法成交、估計滑價、paper fill price、5D/10D/20D return，以及和 backtest assumption 的差異。

### 被追問：paper trading 要證明什麼？

可以回答：

paper trading 不是證明 alpha，而是驗證 operational feasibility。也就是回測假設在真實資料更新節奏和交易制度下是否能被執行。

---

## 10. Limitations 要怎麼講？

### 你要傳達的核心

主動講限制，會比被問倒更專業。

### 建議講法

目前最大限制有六個：exact announcement timestamp 尚未完整、survivorship controls 需要補強、execution model 還不是 order-book level、樣本期間主要集中在 2023–2025、sector dependence 明顯、winner concentration 仍存在。

這些限制也是下一階段研究 roadmap。

### 被追問：最大風險是什麼？

可以回答：

最大風險是 data timing 和 execution feasibility。如果 exact timestamp 顯示很多訊號實際上無法在假設時間進場，策略績效可能被高估。因此我把 exact timing 和 paper trading 放在下一階段優先順序最前面。

---

## 11. 履歷上怎麼寫？

### 中文履歷 bullet

- 建立台股月營收 surprise 量化研究流程，使用官方月營收與市場資料，設計 3M SUR persistence + momentum overextension control 因子。
- 完成 portfolio-level backtest、walk-forward OOS、sector survival、remove-winner、成本、流動性與執行時點壓力測試。
- 保留一個 portfolio-grade 電子 / 半導體供應鏈 repricing 候選策略，proxy Sharpe 約 2.4；同時明確揭露 exact timing、survivorship、execution fill 與 winner concentration 限制。
- 建立 paper-trading log schema，用於後續驗證 real-time signal generation、non-fill、slippage 與 backtest assumption drift。

### 英文履歷 bullet

- Built an official-data Taiwan monthly-revenue surprise research pipeline with SUR-style fundamental factors, liquidity screens, and portfolio-level backtests.
- Evaluated short-horizon post-disclosure drift via walk-forward OOS, sector survival, remove-winner, cost, liquidity, and execution-timing stress tests.
- Identified a portfolio-grade electronics/semiconductor supply-chain repricing candidate with proxy Sharpe around 2.4, while explicitly rejecting production-readiness due to timestamp, survivorship, execution, and concentration risks.
- Designed a paper-trading schema to validate real-time signal generation, fill feasibility, slippage, non-fill events, and assumption drift.

---

## 12. 3 分鐘報告架構

### 0:00–0:30 專案動機

台灣月營收是高頻基本面資訊，研究公布後是否有 delayed repricing。

### 0:30–1:00 資料與因子

官方月營收 + 市場資料；SUR-style surprise；區分 revenue month 與 signal date。

### 1:00–1:40 策略與結果

S1：3M SUR persistence + not-overheated momentum + liquidity + top8 + industry cap。Proxy Sharpe 約 2.4，但只視為 research candidate。

### 1:40–2:20 Robustness

remove-winner、walk-forward、sector survival 顯示電子 / 半導體依賴與 right-tail dependence。

### 2:20–2:50 Execution realism

next-open、成本、limit-up non-fill proxy 後績效下降，因此不能 production-ready。

### 2:50–3:00 下一步

exact timestamp、paper trading、execution feasibility。

---

## 13. 10 分鐘報告架構

1. 市場制度與研究問題：1 分鐘
2. 資料與 anti-look-ahead 設計：1 分鐘
3. 因子設計：1 分鐘
4. S1 策略規則：1 分鐘
5. 主要績效圖：1.5 分鐘
6. Robustness / remove-winner：1 分鐘
7. Sector survival：1 分鐘
8. Quiet digestion extension：1 分鐘
9. Execution realism：1 分鐘
10. Limitations / next steps：0.5 分鐘

---

## 14. 最後收尾怎麼說？

### 建議收尾

這個專案最大的價值不是單一 Sharpe，而是完整研究流程。我從台灣月營收制度提出假說，建立資料與因子，做 portfolio backtest，再逐步檢查 OOS、sector、winner、流動性、成本和執行可行性。最後我保留一個值得 paper trading 的候選策略，但也明確知道它離 production-ready 還差 exact timestamp、survivorship 和 execution validation。這是我認為比較負責任的量化研究方式。
