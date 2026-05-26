# Phase 3.4 文獻啟發與新策略 Ideas

本階段目標：參考 earnings drift、revenue surprise、fundamental momentum、price momentum、volume/liquidity、institutional flow、attention 與 limits-to-arbitrage 相關文獻，發想可落地到台股月營收研究的下一批策略。

本報告不是投資建議，也沒有任何下單或部署。

## 一、最相關的文獻方向

### 1. Post-Earnings-Announcement Drift / Earnings Momentum

代表文獻：

- Ball & Brown (1968), *An Empirical Evaluation of Accounting Income Numbers*。
- Foster, Olsen & Shevlin (1984), *Earnings Releases, Anomalies, and the Behavior of Security Returns*。
- Bernard & Thomas (1989, 1990), PEAD 系列研究。
- Livnat & Mendenhall (2006), analyst forecast vs time-series forecast surprise。

核心啟發：

- 市場對財報/盈餘資訊常常反應不足。
- surprise 的定義比單純成長率重要。
- 若能把月營收轉成 standardized unexpected revenue，比單看 YoY 更像真正的 earnings surprise。

台股落地想法：

- 建立 `SUR = (actual revenue - expected revenue) / forecast_error_volatility`。
- expected revenue 可用季節性模型、過去 12 個月同月 YoY、3M trend、industry median。
- 測試 high SUR 是否比 high YoY 更穩。

### 2. Revenue Surprise / Sales Surprise

代表文獻：

- Jegadeesh & Livnat (2006), *Revenue Surprises and Stock Returns*。

核心啟發：

- revenue surprise 本身對未來報酬有解釋力。
- revenue surprise 有 earnings surprise 以外的增量資訊。

台股落地想法：

- 台灣月營收制度很適合做 high-frequency revenue surprise。
- 不應只看單月 YoY，而要看 actual revenue relative to expected revenue。
- 可測：單月 SUR、3M SUR、QTD SUR、industry-adjusted SUR。

### 3. Price Momentum / Residual Momentum

代表文獻：

- Jegadeesh & Titman (1993), cross-sectional momentum。
- Chan, Jegadeesh & Lakonishok (1996), earnings momentum 與 price momentum。
- Asness, Moskowitz & Pedersen (2013), value and momentum everywhere。
- Blitz, Huij & Martens (2011), residual momentum。

核心啟發：

- 價格動能與基本面動能相關，但不是完全相同。
- residual momentum 可能比 raw momentum 更乾淨。
- 台股產業集中，industry-relative / residual momentum 特別重要。

台股落地想法：

- 加入 6-1 / 12-1 price momentum。
- 加入 industry-relative momentum。
- 嘗試 market/industry residual momentum，避免策略只是半導體 beta。

### 4. Volume / Liquidity / Attention

代表文獻：

- Lee & Swaminathan (2000), price momentum and trading volume。
- Gervais, Kaniel & Mingelgrin (2001), high-volume return premium。
- Amihud (2002), illiquidity and stock returns。
- Barber & Odean (2008), attention-driven retail buying。
- Da, Engelberg & Gao (2011), search volume and attention。

核心啟發：

- 成交量/週轉率可同時代表注意力、資金確認與過熱。
- 高成交量不是一定好，要區分：健康放量 vs 投機過熱。
- attention-driven buying 可能短期續漲、中期反轉。

台股落地想法：

- 加 abnormal turnover：20D 成交金額 / 120D 成交金額。
- 加 post-revenue turnover shock。
- 測 high revenue surprise + positive return + abnormal volume 是否更強。
- 也測 extreme volume spike 是否代表 crowded trade、未來反轉。

### 5. Institutional Flow / Margin / Limits to Arbitrage

代表文獻：

- Nofsinger & Sias (1999), institutional herding。
- Sias (2004), institutional demand persistence。
- Lou (2012), flow-based return predictability。
- Barber & Odean (2008), retail attention。
- Shleifer & Vishny (1997), limits to arbitrage。
- Pontiff (2006), costly arbitrage and idiosyncratic risk。
- Miller (1977), short-sale constraints and overpricing。

核心啟發：

- 法人買賣超可能是資訊，也可能是 price pressure。
- 融資增加可視為散戶槓桿/attention proxy。
- 若外資買、融資也買，可能是追價或共同確認；若外資買、融資未過熱，可能更乾淨。
- short-sale constraints 與高異質波動會讓 mispricing 延續。

台股落地想法：

- 加外資/投信買賣超確認。
- 加融資增減作為散戶過熱或槓桿風險。
- 加券資比、借券/融券資料若可取得。
- 測 foreign buy + revenue surprise vs margin buy + revenue surprise。

## 二、下一批可測策略 Ideas

### Idea A：Standardized Unexpected Revenue, SUR

假設：

因為市場對營收 surprise 反應不足，所以標準化後的 unexpected revenue 比 YoY 更能預測未來報酬。

訊號：

```text
SUR = (Revenue_t - ExpectedRevenue_t) / Std(ForecastError)
```

ExpectedRevenue 可從：

- 去年同月 × 最近 3M YoY trend
- 過去 12 個月 seasonal model
- industry median adjusted growth

落地資料：已具備歷史月營收。

優先級：高。

### Idea B：Industry-Adjusted Revenue Momentum

假設：

台股電子/半導體循環很強，raw revenue growth 可能只是產業 beta；相對產業更強的公司更有 alpha。

訊號：

```text
IndustryAdjustedRevenue = Firm 3M Revenue YoY - Industry Median 3M Revenue YoY
```

可擴充：

- industry-adjusted SUR
- industry rank percentile
- sector-neutral Top N

落地資料：已具備產業欄位與歷史月營收。

優先級：高。

### Idea C：Revenue Acceleration + Price Trend Confirmation

假設：

基本面改善若被市場確認，price momentum 會同步出現；這比單看基本面更可靠。

訊號：

```text
Score = rank(revenue acceleration)
      + rank(3M revenue YoY)
      + rank(6-1 price momentum)
      - rank(last 20D runup)
```

這和 Phase 3.3 的結果一致：trend / liquidity 加入後明顯改善。

落地資料：已具備日行情。

優先級：高。

### Idea D：Revenue Surprise + Abnormal Volume Confirmation

假設：

營收 surprise 若伴隨異常成交量，代表資訊開始擴散與資金確認；但極端成交量可能代表過熱。

訊號：

```text
AbnormalVolume = avg_turnover_20d / avg_turnover_120d
```

測試：

- moderate abnormal volume 是否最好。
- extreme abnormal volume 是否反轉。
- revenue surprise + positive 5D return + volume confirmation。

落地資料：需要 120D 日行情，已可從官方價格資料計算。

優先級：高。

### Idea E：Residual Momentum within Revenue Winners

假設：

高營收動能股票若同時有 market/industry residual momentum，代表不是單純被市場或產業帶動。

訊號：

```text
residual_return = stock_return - market_return - industry_return
ResidualMomentum = cumulative residual return over 60/120D
```

落地資料：需要用已抓日行情計算 market/industry equal-weight return。

優先級：中高。

### Idea F：Revenue + Institutional Confirmation

假設：

營收改善若伴隨外資/投信買超，資訊擴散更可信；若只有融資快速增加，可能是散戶過熱。

訊號：

```text
Score = revenue_surprise
      + price_momentum
      + foreign_buy_intensity
      + investment_trust_buy_intensity
      - margin_financing_spike
```

資料需求：

- 三大法人買賣超
- 融資融券

優先級：高，但需先確認免費官方資料 endpoint。

### Idea G：Revenue Turnaround Sleeve

假設：

某些公司長期下跌後，營收 YoY 由負轉正，且價格站回均線，可能形成 turnaround。

訊號：

```text
Revenue YoY crosses from negative to positive
+ revenue acceleration positive
+ price crosses above 120D MA
+ volume confirmation
```

這和原本 momentum sleeve 不同，可能捕捉景氣循環轉折。

優先級：中。

## 三、我建議下一步測試順序

### Phase 3.5：營收 surprise 正規化

先做：

1. SUR。
2. industry-adjusted SUR。
3. revenue acceleration。
4. QTD revenue growth。

原因：這是最直接承接 revenue surprise / PEAD 文獻，也不需要額外資料。

### Phase 3.6：市場面進一步擴充

再做：

1. 6-1 / 12-1 price momentum。
2. industry-relative momentum。
3. abnormal volume。
4. residual momentum。

原因：Phase 3.3 已顯示 trend + liquidity 有效，值得細化。

### Phase 3.7：籌碼面資料攻關

最後找：

1. 三大法人買賣超。
2. 融資融券。
3. 借券 / 融券。
4. 外資持股或法人持股。

原因：如果免費官方 endpoint 可穩定取得，這可能是下一個重要提升來源。

## 四、目前結論

文獻方向支持目前的策略演進：

```text
月營收基本面動能
→ 營收 surprise / standardized unexpected revenue
→ 產業調整
→ 價格趨勢確認
→ 成交量/流動性確認
→ 法人/融資籌碼確認
```

目前最值得優先測的不是再調 Top N，而是：

1. 把 YoY 改成 SUR。
2. 把 raw revenue growth 改成 industry-adjusted revenue surprise。
3. 加 abnormal volume。
4. 加 residual momentum。
5. 攻關法人/融資官方資料。
