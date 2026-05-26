# Phase 3.8 3M SUR persistence + execution realism

本階段仍是 research-only proxy/cohort backtest，不是實際持倉、paper order 或交易建議。價格資料只有 close/turnover，沒有 OHLC、逐筆、漲跌停與委託簿，因此停損/停利/追蹤停損都是 close-price proxy。

## 研究問題

Phase 3.7 顯示 `sur3_high_no_high_mom` 是較有價值的短線延伸。本階段測試固定持有與停利/停損/trailing stop，並測流動性門檻與半導體 cap。

## 最佳 exit-rule snapshot

- sur3 10D 最佳：`fixed`，strategy=52.81%，excess=31.99%，Sharpe=1.14，MDD=-14.00%，avg actual days=10.00
- sur3 20D 最佳：`trail15`，strategy=145.74%，excess=105.04%，Sharpe=1.75，MDD=-13.90%，avg actual days=19.18

## sur3_high_no_high_mom：主要 exit rules

### fixed
- 10D max：strategy=52.81%, excess=31.99%, Sharpe=1.14, MDD=-14.00%, win=62.07%, avg days=10.00, stop/tp/trail/time=0/0/0/331
- 15D max：strategy=84.82%, excess=61.82%, Sharpe=1.32, MDD=-19.37%, win=72.41%, avg days=15.00, stop/tp/trail/time=0/0/0/331
- 20D max：strategy=128.59%, excess=101.01%, Sharpe=1.37, MDD=-23.18%, win=75.86%, avg days=20.00, stop/tp/trail/time=0/0/0/331

### sl8_fixed
- 10D max：strategy=45.02%, excess=27.30%, Sharpe=1.05, MDD=-12.10%, win=62.07%, avg days=9.54, stop/tp/trail/time=44/0/0/287
- 15D max：strategy=72.28%, excess=47.54%, Sharpe=1.34, MDD=-10.84%, win=68.97%, avg days=13.76, stop/tp/trail/time=65/0/0/266
- 20D max：strategy=120.69%, excess=89.54%, Sharpe=1.60, MDD=-12.39%, win=72.41%, avg days=17.67, stop/tp/trail/time=88/0/0/243

### sl12_fixed
- 10D max：strategy=52.01%, excess=31.21%, Sharpe=1.12, MDD=-14.93%, win=62.07%, avg days=9.91, stop/tp/trail/time=13/0/0/318
- 15D max：strategy=88.28%, excess=60.44%, Sharpe=1.44, MDD=-14.48%, win=72.41%, avg days=14.66, stop/tp/trail/time=29/0/0/302
- 20D max：strategy=138.38%, excess=101.88%, Sharpe=1.53, MDD=-16.22%, win=79.31%, avg days=19.11, stop/tp/trail/time=45/0/0/286

### tp15_fixed
- 10D max：strategy=35.59%, excess=18.45%, Sharpe=0.95, MDD=-14.60%, win=62.07%, avg days=9.62, stop/tp/trail/time=0/33/0/298
- 15D max：strategy=60.65%, excess=41.18%, Sharpe=1.13, MDD=-19.37%, win=65.52%, avg days=13.94, stop/tp/trail/time=0/61/0/270
- 20D max：strategy=85.69%, excess=62.98%, Sharpe=1.29, MDD=-17.04%, win=75.86%, avg days=17.85, stop/tp/trail/time=0/88/0/243

### tp25_fixed
- 10D max：strategy=45.33%, excess=25.52%, Sharpe=1.09, MDD=-14.00%, win=62.07%, avg days=9.91, stop/tp/trail/time=0/11/0/320
- 15D max：strategy=79.77%, excess=55.57%, Sharpe=1.30, MDD=-19.37%, win=72.41%, avg days=14.68, stop/tp/trail/time=0/23/0/308
- 20D max：strategy=121.50%, excess=93.00%, Sharpe=1.42, MDD=-20.68%, win=72.41%, avg days=19.22, stop/tp/trail/time=0/42/0/289

### sl8_tp20
- 10D max：strategy=35.76%, excess=19.41%, Sharpe=0.97, MDD=-12.10%, win=62.07%, avg days=9.38, stop/tp/trail/time=44/19/0/268
- 15D max：strategy=66.66%, excess=41.42%, Sharpe=1.35, MDD=-10.84%, win=68.97%, avg days=13.22, stop/tp/trail/time=65/37/0/229
- 20D max：strategy=102.64%, excess=72.57%, Sharpe=1.69, MDD=-10.32%, win=68.97%, avg days=16.46, stop/tp/trail/time=86/55/0/190

### sl10_tp25
- 10D max：strategy=46.34%, excess=26.29%, Sharpe=1.14, MDD=-12.76%, win=62.07%, avg days=9.74, stop/tp/trail/time=22/11/0/298
- 15D max：strategy=86.30%, excess=57.03%, Sharpe=1.53, MDD=-12.85%, win=72.41%, avg days=14.08, stop/tp/trail/time=43/23/0/265
- 20D max：strategy=139.06%, excess=100.82%, Sharpe=1.77, MDD=-12.16%, win=79.31%, avg days=17.88, stop/tp/trail/time=59/42/0/230

### trail10
- 10D max：strategy=42.88%, excess=25.62%, Sharpe=1.03, MDD=-14.17%, win=62.07%, avg days=9.73, stop/tp/trail/time=0/0/30/301
- 15D max：strategy=72.08%, excess=48.31%, Sharpe=1.34, MDD=-14.32%, win=72.41%, avg days=14.09, stop/tp/trail/time=0/0/68/263
- 20D max：strategy=140.29%, excess=94.77%, Sharpe=1.96, MDD=-11.99%, win=75.86%, avg days=17.80, stop/tp/trail/time=0/0/103/228

### trail15
- 10D max：strategy=47.94%, excess=29.36%, Sharpe=1.07, MDD=-15.39%, win=62.07%, avg days=9.94, stop/tp/trail/time=0/0/10/321
- 15D max：strategy=80.31%, excess=59.49%, Sharpe=1.33, MDD=-17.23%, win=72.41%, avg days=14.73, stop/tp/trail/time=0/0/30/301
- 20D max：strategy=145.74%, excess=105.04%, Sharpe=1.75, MDD=-13.90%, win=79.31%, avg days=19.18, stop/tp/trail/time=0/0/49/282

### sl8_trail12
- 10D max：strategy=44.79%, excess=27.34%, Sharpe=1.08, MDD=-11.92%, win=62.07%, avg days=9.49, stop/tp/trail/time=40/0/7/284
- 15D max：strategy=71.53%, excess=45.63%, Sharpe=1.41, MDD=-10.09%, win=72.41%, avg days=13.60, stop/tp/trail/time=60/0/21/250
- 20D max：strategy=130.18%, excess=86.54%, Sharpe=1.93, MDD=-9.40%, win=75.86%, avg days=17.20, stop/tp/trail/time=76/0/39/216

## Liquidity / semiconductor cap：sur3 fixed 20D

- liq=50m, semi_cap=none：strategy=128.59%, excess=101.01%, Sharpe=1.37, MDD=-23.18%, avg positions=11.4
- liq=50m, semi_cap=5：strategy=128.59%, excess=101.01%, Sharpe=1.37, MDD=-23.18%, avg positions=11.4
- liq=50m, semi_cap=3：strategy=130.51%, excess=102.30%, Sharpe=1.38, MDD=-23.18%, avg positions=10.4
- liq=50m, semi_cap=2：strategy=130.53%, excess=101.99%, Sharpe=1.37, MDD=-23.18%, avg positions=9.7
- liq=100m, semi_cap=none：strategy=160.27%, excess=130.32%, Sharpe=1.44, MDD=-22.14%, avg positions=9.2
- liq=100m, semi_cap=5：strategy=160.27%, excess=130.32%, Sharpe=1.44, MDD=-22.14%, avg positions=9.2
- liq=100m, semi_cap=3：strategy=173.70%, excess=142.42%, Sharpe=1.50, MDD=-22.14%, avg positions=8.3
- liq=100m, semi_cap=2：strategy=147.85%, excess=119.28%, Sharpe=1.36, MDD=-22.14%, avg positions=7.7
- liq=300m, semi_cap=none：strategy=259.12%, excess=223.26%, Sharpe=1.50, MDD=-26.51%, avg positions=5.4
- liq=300m, semi_cap=5：strategy=259.12%, excess=223.26%, Sharpe=1.50, MDD=-26.51%, avg positions=5.4
- liq=300m, semi_cap=3：strategy=207.92%, excess=178.00%, Sharpe=1.29, MDD=-29.93%, avg positions=4.8
- liq=300m, semi_cap=2：strategy=239.89%, excess=206.51%, Sharpe=1.35, MDD=-25.18%, avg positions=4.4

## Remove top winners：sur3 fixed vs stop/take

### fixed 20D
- remove 0：strategy=128.59%, excess=101.01%, MDD=-23.18%
- remove 5：strategy=88.01%, excess=64.47%, MDD=-23.18%
- remove 10：strategy=62.10%, excess=41.63%, MDD=-23.65%
- remove 20：strategy=32.31%, excess=14.69%, MDD=-23.65%

### trail15 20D
- remove 0：strategy=145.74%, excess=105.04%, MDD=-13.90%
- remove 5：strategy=101.23%, excess=67.31%, MDD=-16.75%
- remove 10：strategy=71.02%, excess=42.26%, MDD=-16.75%
- remove 20：strategy=38.06%, excess=15.69%, MDD=-18.95%

### sl8_tp20 20D
- remove 0：strategy=102.64%, excess=72.57%, MDD=-10.32%
- remove 5：strategy=79.05%, excess=53.97%, MDD=-10.32%
- remove 10：strategy=60.54%, excess=37.74%, MDD=-10.32%
- remove 20：strategy=34.20%, excess=14.58%, MDD=-12.56%

### trail10 20D
- remove 0：strategy=140.29%, excess=94.77%, MDD=-11.99%
- remove 5：strategy=95.64%, excess=58.24%, MDD=-13.18%
- remove 10：strategy=64.29%, excess=33.16%, MDD=-13.18%
- remove 20：strategy=34.72%, excess=9.78%, MDD=-13.18%

### fixed 10D
- remove 0：strategy=52.81%, excess=31.99%, MDD=-14.00%
- remove 5：strategy=30.72%, excess=12.39%, MDD=-14.00%
- remove 10：strategy=19.93%, excess=2.87%, MDD=-14.00%
- remove 20：strategy=3.04%, excess=-11.84%, MDD=-16.59%

## 初步解讀

- 固定 20D 仍是重要 exit baseline；但 `trail15` / `trail10` 這輪值得升級成候選，因為它們保留大部分右尾，同時降低 MDD / 提升 Sharpe。
- 10D 若加入 stop/take，沒有明顯解決 remove-winners 後 edge 消失的問題；10D 還是不適合作為主策略，只適合觀察 aggressive sleeve。
- 提高流動性門檻與半導體 cap 是必要 robustness：如果 300m 或 semi cap 後仍可接受，才更接近 paper-trading 候選。
- 由於只有 close-price proxy，下一步若要更接近實盤，需要補日內/OHLC、漲跌停與成交可得性資料。

## 輸出檔案

- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_exit_rules.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_yearly.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_remove_winners.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_liquidity_semicap.csv`
- `/Users/liuyenzhen/quant-research/tw_monthly_revenue/data/processed/execution_realism_summary.json`
