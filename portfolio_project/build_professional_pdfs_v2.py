from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

ROOT = Path('/Users/liuyenzhen/quant-research/tw_monthly_revenue')
PORT = ROOT / 'portfolio_project'
CHARTS = ROOT / 'reports' / 'charts'

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
FONT = 'STSong-Light'
PAGE_W, PAGE_H = A4

NAVY = colors.HexColor('#0F172A')
BLUE = colors.HexColor('#1D4ED8')
BLUE2 = colors.HexColor('#2563EB')
SKY = colors.HexColor('#0284C7')
GREEN = colors.HexColor('#047857')
AMBER = colors.HexColor('#B45309')
RED = colors.HexColor('#B91C1C')
SLATE = colors.HexColor('#334155')
MUTED = colors.HexColor('#64748B')
LIGHT = colors.HexColor('#F8FAFC')
CARD = colors.HexColor('#F1F5F9')
BORDER = colors.HexColor('#CBD5E1')
WHITE = colors.white


def make_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('CoverTitle', fontName=FONT, fontSize=27, leading=35, textColor=NAVY, alignment=TA_CENTER, spaceAfter=12))
    s.add(ParagraphStyle('CoverSub', fontName=FONT, fontSize=12.5, leading=18, textColor=SLATE, alignment=TA_CENTER, spaceAfter=8))
    s.add(ParagraphStyle('H1', fontName=FONT, fontSize=16.5, leading=22, textColor=NAVY, spaceBefore=11, spaceAfter=8))
    s.add(ParagraphStyle('H2', fontName=FONT, fontSize=12.5, leading=17, textColor=BLUE, spaceBefore=8, spaceAfter=5))
    s.add(ParagraphStyle('H3', fontName=FONT, fontSize=10.7, leading=15, textColor=SLATE, spaceBefore=5, spaceAfter=3))
    s.add(ParagraphStyle('Body', fontName=FONT, fontSize=9.35, leading=14.2, textColor=colors.HexColor('#111827'), wordWrap='CJK', spaceAfter=5))
    s.add(ParagraphStyle('Small', fontName=FONT, fontSize=8.1, leading=11.2, textColor=MUTED, wordWrap='CJK', spaceAfter=3))
    s.add(ParagraphStyle('BulletZH', fontName=FONT, fontSize=9.2, leading=13.8, leftIndent=14, firstLineIndent=-8, textColor=colors.HexColor('#111827'), wordWrap='CJK', spaceAfter=2.5))
    s.add(ParagraphStyle('Quote', fontName=FONT, fontSize=10, leading=15, leftIndent=8, rightIndent=8, textColor=NAVY, backColor=colors.HexColor('#EFF6FF'), borderColor=colors.HexColor('#93C5FD'), borderWidth=0.6, borderPadding=8, spaceAfter=8, wordWrap='CJK'))
    s.add(ParagraphStyle('CodeZH', fontName=FONT, fontSize=7.7, leading=10.2, textColor=colors.HexColor('#111827'), backColor=colors.HexColor('#F3F4F6'), borderPadding=6, leftIndent=8, rightIndent=8, spaceAfter=6))
    s.add(ParagraphStyle('CardTitle', fontName=FONT, fontSize=8.2, leading=10, textColor=MUTED, alignment=TA_CENTER))
    s.add(ParagraphStyle('CardValue', fontName=FONT, fontSize=15.2, leading=19, textColor=NAVY, alignment=TA_CENTER))
    s.add(ParagraphStyle('CardNote', fontName=FONT, fontSize=7.4, leading=9.5, textColor=MUTED, alignment=TA_CENTER))
    s.add(ParagraphStyle('Caption', fontName=FONT, fontSize=8, leading=10.3, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8))
    s.add(ParagraphStyle('TOC', fontName=FONT, fontSize=9.5, leading=14, textColor=SLATE, wordWrap='CJK'))
    return s

S = make_styles()


def esc(x: str) -> str:
    return str(x).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')


def P(text, style='Body'):
    return Paragraph(esc(text), S[style])


def section(title):
    return [Paragraph(esc(title), S['H1']), HRFlowable(width='100%', thickness=0.7, color=BORDER, spaceAfter=7)]


def bullet(items):
    return [Paragraph('• ' + esc(i), S['BulletZH']) for i in items]


def callout(title, text, color=BLUE):
    tbl = Table([[Paragraph(f'<b>{esc(title)}</b><br/>{esc(text)}', S['Body'])]], colWidths=[16.8*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EFF6FF')),
        ('BOX',(0,0),(-1,-1),0.8,color),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    return tbl


def kpi(cards, cols=4):
    rows=[]
    for i in range(0, len(cards), cols):
        row=[]
        for title, val, note, color in cards[i:i+cols]:
            row.append([Paragraph(esc(title), S['CardTitle']), Spacer(1,2), Paragraph(f'<font color="{color.hexval()}">{esc(val)}</font>', S['CardValue']), Paragraph(esc(note), S['CardNote'])])
        while len(row)<cols:
            row.append('')
        rows.append(row)
    t=Table(rows, colWidths=[16.8/cols*cm]*cols, hAlign='CENTER')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),WHITE),('BOX',(0,0),(-1,-1),0.7,BORDER),('INNERGRID',(0,0),(-1,-1),0.7,BORDER),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    return t


def chart(filename, caption, max_h=8.9*cm):
    p=CHARTS/filename
    if not p.exists():
        return [P(f'缺圖：{filename}', 'Small')]
    img=Image(str(p))
    scale=min(16.7*cm/img.imageWidth, max_h/img.imageHeight, 1)
    img.drawWidth=img.imageWidth*scale
    img.drawHeight=img.imageHeight*scale
    return [img, Paragraph(esc(caption), S['Caption'])]


def pro_table(headers, rows, widths=None):
    data=[[Paragraph(f'<b>{esc(h)}</b>', S['Small']) for h in headers]]
    for r in rows:
        data.append([Paragraph(esc(c), S['Small']) for c in r])
    if widths is None:
        widths=[16.8/len(headers)*cm]*len(headers)
    t=Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),WHITE),
        ('BACKGROUND',(0,1),(-1,-1),colors.HexColor('#FFFFFF')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE, LIGHT]),
        ('BOX',(0,0),(-1,-1),0.6,BORDER),('INNERGRID',(0,0),(-1,-1),0.4,BORDER),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
    ]))
    return t


def cover(title, subtitle, version_label, summary, chips):
    st=[Spacer(1,1.8*cm)]
    st.append(Paragraph(title, S['CoverTitle']))
    st.append(Paragraph(subtitle, S['CoverSub']))
    st.append(HRFlowable(width='70%', thickness=1.2, color=BLUE2, hAlign='CENTER', spaceBefore=5, spaceAfter=18))
    st.append(callout(version_label, summary, BLUE2))
    st.append(Spacer(1,0.35*cm))
    chip_row=[Paragraph(esc(c), S['Small']) for c in chips]
    t=Table([chip_row], colWidths=[4.0*cm]*len(chip_row), hAlign='CENTER')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),CARD),('BOX',(0,0),(-1,-1),0.5,BORDER),('INNERGRID',(0,0),(-1,-1),0.5,WHITE),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)
    ]))
    st.append(t)
    st.append(Spacer(1,6.0*cm))
    st.append(Paragraph('Research / Paper-Trading Only ｜ 非投資建議 ｜ 非實盤交易系統', S['Small']))
    st.append(PageBreak())
    return st


def toc(items):
    st=section('目錄')
    rows=[]
    for i, item in enumerate(items,1):
        rows.append([f'{i:02d}', item])
    st.append(pro_table(['章節','內容'], rows, widths=[2.2*cm,14.6*cm]))
    st.append(PageBreak())
    return st


def resume_story():
    st=[]
    st+=cover('台股月營收驚喜策略研究作品集', 'Professional Portfolio Brief｜履歷附件版 V2', '研究定位', '本專案以台灣月營收公告制度為市場結構起點，建立 SUR-style 基本面 surprise 因子與完整 robustness workflow。最終保留 S1 作為 portfolio-grade v0.1 候選策略；它更像電子 / 半導體供應鏈 repricing candidate，而非 production-ready broad-market alpha。', ['Market Structure','Official Data','SUR Factor','OOS / Robustness'])
    st+=toc(['Executive Snapshot','Research Hypothesis','Data Pipeline & Timing Controls','Strategy Specification','Headline Results','Core Performance Charts','Robustness & Winner Dependence','Walk-forward and Sector Survival','Price-volume Extension','Execution Realism','Paper-trading Readiness','Limitations and Roadmap','Appendix: Resume Bullets'])

    st+=section('01｜Executive Snapshot')
    st.append(kpi([
        ('S1 Proxy Sharpe','≈ 2.40','portfolio-grade proxy',GREEN),('Total Return','+167.5%','historical proxy',GREEN),('Max Drawdown','-7.9%','proxy setup',AMBER),('2025 Test Sharpe','≈ 3.12','regime-sensitive',BLUE),
        ('Remove Top-5 Sharpe','≈ 1.77','winner stress',BLUE),('Remove Top-10 Sharpe','≈ 1.41','right-tail check',AMBER),('Horizon','20D','short-horizon drift',NAVY),('Status','Research candidate','not live-ready',AMBER)
    ],4))
    st.append(Spacer(1,8))
    st.append(callout('One-line takeaway','使用台灣月營收制度建立可解釋的基本面 surprise 策略，S1 具研究價值，但關鍵風險是 exact timing、sector concentration、winner dependence 與 execution feasibility。'))
    st+=bullet(['核心假說：月營收 surprise 可能造成公布後 10–20D delayed repricing。','核心訊號：3M SUR persistence + not-overheated momentum。','研究方法：先建立 baseline，再用 OOS、sector、remove-winner、cost、liquidity、execution timing gates 檢查。','結論語氣：portfolio-grade research candidate；不是 production-ready trading system。'])
    st.append(PageBreak())

    st+=section('02｜Research Hypothesis')
    st.append(Paragraph('市場制度到 alpha 假說', S['H2']))
    st.append(pro_table(['層次','內容','研究含義'],[
        ['Market structure','台灣公司每月公布營收','形成高頻基本面資訊事件'],
        ['Information update','連續性營收 surprise','更新投資人對需求、訂單、供應鏈景氣的預期'],
        ['Behavioral / flow channel','市場可能延遲反應','資金逐步重新定價，形成 post-disclosure drift'],
        ['Expected edge','公布後 10–20D 漂移','以短週期 portfolio backtest 驗證']
    ], widths=[3.4*cm,6.2*cm,7.2*cm]))
    st.append(Spacer(1,8))
    st.append(Paragraph('因果鏈', S['H2']))
    st.append(Paragraph('月營收公告制度 → 基本面 surprise → 投資人預期調整 → 延遲 repricing → 10–20D return drift', S['CodeZH']))
    st+=bullet(['此專案不是從 K 線或技術指標開始，而是從台灣市場制度開始。','策略是否有效，取決於 surprise 是否未被完全 pricing，以及是否能在資料公開後合理進場。'])
    st.append(PageBreak())

    st+=section('03｜Data Pipeline & Timing Controls')
    st.append(pro_table(['資料模組','內容','限制 / 控制'],[
        ['Monthly revenue','上市 / 上櫃公司月營收 panel','目前缺 company-level exact announcement timestamp'],
        ['Market data','每日收盤價、成交金額','早期研究為 close/turnover proxy'],
        ['Official raw JSON','官方 daily raw files','後續解析 OHLC / TPEx next-limit 欄位'],
        ['Processed execution table','official_daily_ohlc_limit_from_raw.csv','TWSE limit 欄位仍需補強']
    ], widths=[4.0*cm,6.0*cm,6.8*cm]))
    st.append(Spacer(1,8))
    st.append(callout('Anti-look-ahead principle','嚴格區分 revenue month、announcement / data-available date、signal date、trade date。由於 exact timestamp 尚未完整，本作品集不宣稱 same-day tradability。', RED))
    st+=bullet(['若 exact announcement time unknown，最保守應使用 next trading day 作為 earliest entry。','所有 stop / trailing 類結果都標記為 proxy，未宣稱為完整可執行模擬。'])
    st.append(PageBreak())

    st+=section('04｜Strategy Specification')
    st.append(kpi([('Signal','3M SUR','persistent surprise',BLUE),('Filter','No overheated momentum','avoid pre-priced names',BLUE),('Selection','Top 8','monthly rank',NAVY),('Risk Control','Industry cap = 3','concentration control',NAVY)],4))
    st.append(Spacer(1,8))
    st.append(Paragraph('S1 incumbent', S['H2']))
    st.append(Paragraph('sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D', S['CodeZH']))
    st.append(pro_table(['設計選擇','目的'],[
        ['3M SUR persistence','降低單月雜訊，捕捉連續性 surprise'],['Not-overheated momentum','避免股價已提前反映'],['Liquidity ≥ 50m TWD','降低不可交易小型股假象'],['Top 8 + industry cap','控制單月集中度'],['20D horizon','符合逐步 repricing 的短週期設定']
    ], widths=[5.2*cm,11.6*cm]))
    st.append(PageBreak())

    st+=section('05｜Headline Results and Interpretation')
    st.append(pro_table(['版本','Return','Sharpe','MDD','解讀'],[
        ['S1 portfolio-grade v0.1','+167.5%','≈2.40','-7.9%','核心保留候選；仍需 timing / execution gate'],
        ['S1 fixed-20 comparator','+161.9%','1.55','-21.2%','簡潔 benchmark，便於比較'],
        ['Quiet boost sizing','+174.4%','1.62','-21.2%','小幅改善，但不足以 promotion'],
        ['Conservative execution proxy','+111.9%','1.24','-24.9%','保守進場與成本後 quality 下降']
    ], widths=[4.8*cm,2.7*cm,2.5*cm,2.5*cm,4.3*cm]))
    st.append(callout('Interpretation discipline','結果足以支持研究價值，但不支持 production-ready 宣稱。最專業的說法是：portfolio-grade v0.1 candidate，下一步進入 exact timing 與 paper-trading validation。', AMBER))
    st.append(PageBreak())

    st+=section('06｜Core Performance Charts')
    st+=chart('s1_nav_drawdown_zh.png','圖 1｜S1 NAV 與 drawdown：用來檢查績效路徑、回撤深度與恢復狀態。')
    st+=chart('s1_monthly_returns_is_oos_zh.png','圖 2｜月報酬 IS/OOS：檢查樣本外表現是否只來自特定月份 / regime。')
    st.append(PageBreak())

    st+=section('07｜Robustness & Winner Dependence')
    st+=chart('signal_search_sharpe_mdd_scatter_zh.png','圖 3｜Strategy search Sharpe vs MDD：不是 Sharpe 最高就 promotion。')
    st+=chart('top_variants_sharpe_vs_remove5_zh.png','圖 4｜Top variants vs remove-top-5：檢查大贏家依賴。')
    st+=chart('remove_winners_sharpe_decay_zh.png','圖 5｜Remove-winners decay：right-tail dependence 是核心風險。')
    st.append(callout('Key readout','移除 top winners 後 Sharpe 下降，代表策略存在 right-tail dependence。這不必然否定策略，但必須在 sizing、risk control 與對外敘述中揭露。', AMBER))
    st.append(PageBreak())

    st+=section('08｜Walk-forward and Sector Survival')
    st+=chart('phase3_12_walkforward_oos_nav_zh.png','圖 6｜Walk-forward OOS NAV：固定 S1 並未被 train-selected rule 穩定擊敗。')
    st+=chart('phase3_12_sector_survival_zh.png','圖 7｜Sector survival：半導體 / 電子依賴明顯，no-semiconductor 轉弱。')
    st.append(pro_table(['切片','觀察','研究結論'],[
        ['All universe','S1 表現最佳','保留為 incumbent'],['Electronics / Semiconductor','表現較強','策略定位偏供應鏈 repricing'],['No-semiconductor','顯著轉弱','不可宣稱 broad-market alpha'],['Walk-forward selected','未穩定擊敗 S1','避免過度參數搜尋']
    ], widths=[4.2*cm,5.3*cm,7.3*cm]))
    st.append(PageBreak())

    st+=section('09｜Price-volume Extension: Quiet Digestion')
    st.append(P('後續 price-volume / K-line 研究不是技術指標 mining，而是把價格與成交量視為「市場如何消化基本面 surprise」的狀態變數。'))
    st.append(Paragraph('Quiet digestion = 高 3M SUR + 未過熱 momentum + 低異常成交量 + 窄幅 K 線', S['CodeZH']))
    st+=chart('phase3_17_quiet_digestion_nav_zh.png','圖 8｜Quiet digestion diagnostics：有因果解釋，但 standalone 交易數少、winner-dependent。')
    st+=chart('phase3_18_dynamic_sizing_nav_zh.png','圖 9｜Dynamic sizing：作為 S1 sizing overlay 有小幅改善，但 drawdown 未改善到足以 promotion。')
    st.append(PageBreak())

    st+=section('10｜Execution Realism')
    st.append(kpi([('Entry proxy','Next open','conservative',NAVY),('Cost stress','1.0%','all-in proxy',AMBER),('Limit-up risk','Excluded','non-fill stress',RED),('Quiet boost Sharpe','≈1.24','after friction',AMBER)],4))
    st.append(Spacer(1,8))
    st+=bullet(['保守 proxy 後績效仍為正，但 headline quality 大幅下降。','目前 OHLC / limit parser 已建立，但 exact timestamp 與 fill model 尚未 production-grade。','實務下一步是 paper trading，而非繼續擴大參數搜尋。'])
    st.append(PageBreak())

    st+=section('11｜Paper-trading Readiness')
    st.append(pro_table(['欄位群','應記錄內容'],[
        ['Timing','data_observed_at, signal_generated_at, planned_entry_date'],['Execution','planned_entry_type, open/high/low/close, limit_up_price, non_fill_reason'],['Sizing','planned_notional, ADV participation, estimated slippage'],['Outcome','paper_fill_price, 5D/10D/20D return, assumption_drift_note']
    ], widths=[4.2*cm,12.6*cm]))
    st.append(callout('Paper-trading purpose','Paper trading 不是直接證明 alpha，而是驗證 operational feasibility：真實資料更新、訊號生成、進場可行性、non-fill 與滑價是否符合回測假設。', GREEN))
    st.append(PageBreak())

    st+=section('12｜Limitations and Roadmap')
    st.append(pro_table(['限制','影響','下一步'],[
        ['Exact timestamp missing','無法最終證明 earliest tradable date','取得 company-level announcement timestamp'],['Survivorship controls','可能高估歷史績效','補完整 historical universe / delisting'],['Execution proxy','未含 order-book / auction queue','建立 paper fill 與 non-fill log'],['Short sample','2023–2025 regime risk','擴展期間並持續 OOS'],['Sector concentration','非 broad-market alpha','明確定位 electronics / semiconductor'],['Winner dependence','右尾依賴','sizing / remove-winner monitoring']
    ], widths=[4.0*cm,6.0*cm,6.8*cm]))
    st.append(PageBreak())

    st+=section('13｜Appendix: Resume Bullets')
    st.append(Paragraph('中文版', S['H2']))
    st+=bullet(['建立台股月營收 surprise 量化研究流程，使用官方月營收與市場資料，設計 3M SUR persistence + momentum overextension control 因子。','完成 portfolio-level backtest、walk-forward OOS、sector survival、remove-winner、成本、流動性與執行時點壓力測試。','保留一個 portfolio-grade 電子 / 半導體供應鏈 repricing 候選策略，同時明確揭露 exact timing、survivorship、execution fill 與 winner concentration 限制。'])
    st.append(Paragraph('English', S['H2']))
    st+=bullet(['Built an official-data Taiwan monthly-revenue surprise research pipeline with SUR-style fundamental factors, liquidity screens, and portfolio-level backtests.','Evaluated short-horizon post-disclosure drift via walk-forward OOS, sector survival, remove-winner, cost, liquidity, and execution-timing stress tests.','Identified a portfolio-grade electronics/semiconductor supply-chain repricing candidate while explicitly rejecting production-readiness due to timestamp, survivorship, execution, and concentration risks.'])
    return st


def guide_story():
    st=[]
    st+=cover('台股月營收驚喜策略研究作品集', 'Professional Talking Guide｜面試導讀版 V2', '使用方式', '這份文件是你面試 / 口頭報告時的講稿與防守手冊。每個章節包含：要傳達的核心、建議講法、可能追問、回答方式，以及圖表該怎麼講。', ['Interview Pitch','Chart Talk Track','Q&A Defense','Resume Bullets'])
    st+=toc(['30 秒與 3 分鐘版本','專案動機','資料與 anti-look-ahead','因子與策略設計','結果怎麼講','九張圖表講法','Robustness 防守','Execution realism 防守','Paper trading 下一步','履歷 bullet 與收尾'])
    st+=section('01｜30 秒與 3 分鐘版本')
    st.append(callout('30 秒版本','我做的是台股月營收驚喜策略研究。台灣公司每月公布營收，我研究市場是否會對連續性的營收 surprise 反應不足，造成公布後 10–20 個交易日 repricing。我建立官方資料 pipeline、SUR-style 因子、portfolio backtest，並做 OOS、sector、remove-winner、成本與執行時點檢查。最後保留一個 portfolio-grade 電子 / 半導體供應鏈候選策略，但不宣稱 production-ready。'))
    st.append(pro_table(['時間','講什麼'],[['0:00–0:30','市場制度與研究問題'],['0:30–1:00','資料、因子與 anti-look-ahead'],['1:00–1:40','S1 策略與 headline results'],['1:40–2:20','Robustness：remove-winner / sector / OOS'],['2:20–2:50','Execution realism：成本、進場、non-fill'],['2:50–3:00','下一步：exact timestamp + paper trading']], widths=[3.2*cm,13.6*cm]))
    st.append(PageBreak())

    topics=[
        ('02｜專案動機','台灣月營收制度是一個可系統化測試的高頻基本面事件。','這個策略不是從技術指標開始，而是從台灣市場制度開始。台灣公司每月公布營收，我想測試連續性 surprise 是否造成公布後 10–20D repricing。','為什麼市場會反應不足？','月營收公開不代表所有人會立即完整解讀；供應鏈資料需要產業脈絡，資金可能逐步重新定價。'),
        ('03｜資料與 anti-look-ahead','資料時點比模型更重要。','我區分 revenue month、data available date、signal date、trade date；因 exact timestamp 尚未完整，所以用 next-open / delayed entry proxy，不宣稱 same-day tradability。','你如何避免 look-ahead bias？','我沒有用 revenue month 當交易時間，而是用 usable-date proxy 與 delayed entry stress，並把 timestamp 缺口列為 limitation。'),
        ('04｜因子與策略設計','測的是 surprise，不是單純 growth。','我測過 YoY、MoM、3M growth、SUR-style surprise、industry-adjusted surprise。最後較穩定的是 3M SUR persistence + not-overheated momentum。','為什麼 SUR 比 YoY 好？','YoY 可能只是基期或已被預期；SUR 更接近超出預期的部分，符合 post-announcement drift。'),
        ('05｜結果怎麼講','講結果，但不要 overclaim。','S1 proxy Sharpe 約 2.4、return 約 167.5%、MDD 約 -7.9%。但我視為 research candidate，不是 production claim。','Sharpe 2.4 可以信嗎？','它是 proxy diagnostic；我更重視它在 robustness checks 下是否仍有研究價值。exact timestamp、survivorship、execution fill 還要補。')
    ]
    for title, core, say, q, ans in topics:
        st+=section(title)
        st.append(kpi([('要傳達的核心',core,'',BLUE)],1)); st.append(Spacer(1,6))
        st.append(Paragraph('建議講法', S['H2'])); st.append(P(say))
        st.append(Paragraph('可能追問與回答', S['H2'])); st.append(callout(q, ans, AMBER))
        st.append(PageBreak())

    st+=section('06｜九張圖表講法')
    chart_talk=[
        ['S1 NAV / Drawdown','看績效路徑、回撤與恢復，不只看終點報酬。'],['Monthly returns IS/OOS','說明 OOS 不能過度解讀，2025 可能有 AI / 半導體 regime。'],['Sharpe vs MDD scatter','不是 Sharpe 最高就選，還要看穩健性與可交易性。'],['Top variants vs remove-top-5','檢查是否靠少數大贏家。'],['Remove winners decay','right-tail dependence 是核心風險，要揭露。'],['Walk-forward OOS NAV','train-selected rule 未穩定擊敗固定 S1，避免 overfit。'],['Sector survival','策略定位應是電子 / 半導體供應鏈，不是全市場。'],['Quiet digestion NAV','有因果解釋，但 standalone sparse。'],['Dynamic sizing NAV','作為 sizing overlay 小幅改善，但未達 promotion。']]
    st.append(pro_table(['圖表','講法'], chart_talk, widths=[5.0*cm,11.8*cm]))
    st.append(PageBreak())

    st+=section('07｜Robustness 防守')
    st.append(callout('如果被問：是不是 overfit？','回答：我用 walk-forward OOS、remove-winner、sector survival、cost、liquidity、execution timing stress 來防守。更重要的是，當新變體沒有穩定勝過 S1，我沒有 promotion，而是保留 S1 作為 incumbent。', BLUE))
    st.append(callout('如果被問：靠半導體是不是太集中？','回答：這是策略定位，不是要隱藏的缺點。結果顯示它更像電子 / 半導體供應鏈月營收 repricing，因此我不把它包裝成 broad-market alpha。', BLUE))
    st.append(callout('如果被問：remove-winner 後衰退怎麼辦？','回答：代表 right-tail dependence，需要在 sizing、風控與 paper trading 中持續監控。很多 event-driven 策略本來依賴右尾，但不能忽略。', BLUE))
    st.append(PageBreak())

    st+=section('08｜Execution realism 防守')
    st.append(P('這一段是最能展現成熟度的地方。不要只講績效，要主動講「回測和能交易是兩回事」。'))
    st+=bullet(['我加入 next-open、next-close、延遲 0/1/2/3 天、0.7% / 1.0% / 1.5% 成本、漲停無法成交 proxy。','保守假設下 Sharpe 下降，例如 quiet boost 約 1.24，代表仍有研究價值，但不能 production-ready。','下一步是 exact announcement timestamp 與 paper-trading fill log。'])
    st.append(callout('如果被問：績效下降還值得做嗎？','值得。研究價值不是最漂亮的回測，而是知道 alpha 在哪些假設下存在、在哪些假設下消失。保守假設下仍為正，但 quality 下降，說明下一步要做 operational validation。', AMBER))
    st.append(PageBreak())

    st+=section('09｜Paper trading 下一步')
    st.append(pro_table(['要記錄','目的'],[['data_observed_at / signal_generated_at','驗證沒有 look-ahead'],['planned entry / actual open-high-low-close','驗證可進場價格'],['limit-up / non-fill reason','處理漲停排不到風險'],['ADV participation / slippage','驗證容量與成本'],['5D / 10D / 20D outcome','比較 paper PnL 與 backtest assumption'],['assumption_drift_note','記錄模型假設與真實操作落差']], widths=[6.0*cm,10.8*cm]))
    st.append(PageBreak())

    st+=section('10｜履歷 bullet 與收尾')
    st.append(Paragraph('履歷 bullets', S['H2']))
    st+=bullet(['建立台股月營收 surprise 量化研究流程，使用官方月營收與市場資料，設計 3M SUR persistence + momentum overextension control 因子。','完成 portfolio-level backtest、walk-forward OOS、sector survival、remove-winner、成本、流動性與執行時點壓力測試。','保留一個 portfolio-grade 電子 / 半導體供應鏈 repricing 候選策略，同時明確揭露 exact timing、survivorship、execution fill 與 winner concentration 限制。'])
    st.append(callout('收尾句','這個專案最大的價值不是單一 Sharpe，而是完整研究流程：從市場制度提出假說，建立資料與因子，做 portfolio backtest，再逐步檢查 OOS、sector、winner、流動性、成本和執行可行性。最後保留一個值得 paper trading 的候選策略，但不 overclaim。', GREEN))
    return st


def build_pdf(filename, story, title):
    out=PORT/filename
    def footer(canvas: Canvas, doc):
        canvas.saveState()
        canvas.setFillColor(LIGHT); canvas.rect(0, PAGE_H-1.0*cm, PAGE_W, 1.0*cm, fill=1, stroke=0)
        canvas.setFont(FONT,8); canvas.setFillColor(NAVY); canvas.drawString(1.45*cm, PAGE_H-0.62*cm, title)
        canvas.setFillColor(MUTED); canvas.drawRightString(PAGE_W-1.45*cm, PAGE_H-0.62*cm, 'Research / Paper-Trading Only')
        canvas.setFillColor(MUTED); canvas.drawString(1.45*cm,0.82*cm,'Taiwan Monthly Revenue Surprise Strategy')
        canvas.drawRightString(PAGE_W-1.45*cm,0.82*cm,f'Page {doc.page}')
        canvas.restoreState()
    doc=SimpleDocTemplate(str(out), pagesize=A4, rightMargin=1.55*cm, leftMargin=1.55*cm, topMargin=1.55*cm, bottomMargin=1.35*cm)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out

if __name__ == '__main__':
    r=build_pdf('Taiwan_Monthly_Revenue_Strategy_Resume_Version_ZH_PRO_V2.pdf', resume_story(), '履歷附件版 V2｜台股月營收驚喜策略')
    g=build_pdf('Taiwan_Monthly_Revenue_Strategy_Talking_Guide_ZH_PRO_V2.pdf', guide_story(), '面試導讀版 V2｜台股月營收驚喜策略')
    print(r, r.stat().st_size)
    print(g, g.stat().st_size)
