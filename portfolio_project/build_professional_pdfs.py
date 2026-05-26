from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle,
    KeepTogether, HRFlowable
)
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
import re

ROOT = Path('/Users/liuyenzhen/quant-research/tw_monthly_revenue')
PORT = ROOT / 'portfolio_project'
CHARTS = ROOT / 'reports' / 'charts'

pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
FONT = 'STSong-Light'
PAGE_W, PAGE_H = A4

NAVY = colors.HexColor('#0B1F3A')
BLUE = colors.HexColor('#2563EB')
CYAN = colors.HexColor('#0EA5E9')
SLATE = colors.HexColor('#334155')
MUTED = colors.HexColor('#64748B')
LIGHT = colors.HexColor('#F8FAFC')
CARD = colors.HexColor('#F1F5F9')
BORDER = colors.HexColor('#CBD5E1')
GREEN = colors.HexColor('#059669')
AMBER = colors.HexColor('#D97706')
RED = colors.HexColor('#DC2626')


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle('TitleZH', parent=s['Title'], fontName=FONT, fontSize=26, leading=33, textColor=NAVY, alignment=TA_CENTER, spaceAfter=10))
    s.add(ParagraphStyle('SubTitleZH', parent=s['BodyText'], fontName=FONT, fontSize=12, leading=17, textColor=SLATE, alignment=TA_CENTER, spaceAfter=16))
    s.add(ParagraphStyle('SectionZH', parent=s['Heading1'], fontName=FONT, fontSize=16, leading=21, textColor=NAVY, spaceBefore=12, spaceAfter=8))
    s.add(ParagraphStyle('H2ZH', parent=s['Heading2'], fontName=FONT, fontSize=12.5, leading=17, textColor=BLUE, spaceBefore=8, spaceAfter=5))
    s.add(ParagraphStyle('H3ZH', parent=s['Heading3'], fontName=FONT, fontSize=10.8, leading=15, textColor=SLATE, spaceBefore=5, spaceAfter=3))
    s.add(ParagraphStyle('BodyZH', parent=s['BodyText'], fontName=FONT, fontSize=9.3, leading=14.2, textColor=colors.HexColor('#1F2937'), wordWrap='CJK', spaceAfter=5))
    s.add(ParagraphStyle('SmallZH', parent=s['BodyText'], fontName=FONT, fontSize=8.2, leading=11.5, textColor=MUTED, wordWrap='CJK'))
    s.add(ParagraphStyle('BulletZH', parent=s['BodyText'], fontName=FONT, fontSize=9.2, leading=13.6, leftIndent=13, firstLineIndent=-8, spaceAfter=2.8, wordWrap='CJK'))
    s.add(ParagraphStyle('QuoteZH', parent=s['BodyText'], fontName=FONT, fontSize=10.2, leading=15, textColor=NAVY, leftIndent=10, rightIndent=10, backColor=colors.HexColor('#EFF6FF'), borderColor=colors.HexColor('#BFDBFE'), borderWidth=0.5, borderPadding=8, spaceBefore=5, spaceAfter=8, wordWrap='CJK'))
    s.add(ParagraphStyle('CodeZH', parent=s['Code'], fontName=FONT, fontSize=7.7, leading=10.3, textColor=colors.HexColor('#111827'), leftIndent=8, rightIndent=8, backColor=colors.HexColor('#F3F4F6'), borderPadding=6, spaceBefore=4, spaceAfter=6))
    s.add(ParagraphStyle('CardTitle', parent=s['BodyText'], fontName=FONT, fontSize=8.5, leading=10.5, textColor=MUTED, alignment=TA_CENTER))
    s.add(ParagraphStyle('CardValue', parent=s['BodyText'], fontName=FONT, fontSize=16, leading=20, textColor=NAVY, alignment=TA_CENTER))
    s.add(ParagraphStyle('CaptionZH', parent=s['BodyText'], fontName=FONT, fontSize=8, leading=10, textColor=MUTED, alignment=TA_CENTER, spaceAfter=9))
    return s

S = styles()


def esc(txt):
    txt = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    txt = re.sub(r'`([^`]+)`', r'<font backColor="#F3F4F6">\1</font>', txt)
    txt = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', txt)
    txt = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', txt)
    return txt


def para(text, style='BodyZH'):
    return Paragraph(esc(text), S[style])


def cover(title, subtitle, version, chips):
    data = []
    story = [Spacer(1, 2.2*cm)]
    story.append(Paragraph(title, S['TitleZH']))
    story.append(Paragraph(subtitle, S['SubTitleZH']))
    story.append(HRFlowable(width='65%', thickness=1.4, color=BLUE, spaceBefore=3, spaceAfter=18, hAlign='CENTER'))
    story.append(Paragraph(version, S['QuoteZH']))
    row = []
    for c in chips:
        row.append(Paragraph(c, S['SmallZH']))
    t = Table([row], colWidths=[4.2*cm]*len(row), hAlign='CENTER')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CARD), ('BOX', (0,0), (-1,-1), 0.5, BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.white), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)
    ]))
    story.append(Spacer(1, 0.4*cm))
    story.append(t)
    story.append(Spacer(1, 6.8*cm))
    story.append(Paragraph('Research / Paper-Trading Only｜非投資建議｜非實盤交易系統', S['SmallZH']))
    story.append(PageBreak())
    return story


def kpi_cards(cards, cols=4):
    row = []
    for title, val, color in cards:
        cell = [Paragraph(title, S['CardTitle']), Spacer(1, 3), Paragraph(f'<font color="{color.hexval()}">{esc(val)}</font>', S['CardValue'])]
        row.append(cell)
    data = [row[i:i+cols] for i in range(0, len(row), cols)]
    col_widths = [16.8/cols*cm]*cols
    table = Table(data, colWidths=col_widths, hAlign='CENTER')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white), ('BOX', (0,0), (-1,-1), 0.7, BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.7, BORDER), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 9), ('BOTTOMPADDING', (0,0), (-1,-1), 9),
        ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    return table


def bullet(items):
    return [Paragraph('• ' + esc(x), S['BulletZH']) for x in items]


def chart(path, caption, max_h=9.3*cm):
    p = CHARTS / path
    if not p.exists():
        return [para(f'[缺圖：{path}]', 'SmallZH')]
    img = Image(str(p))
    max_w = 16.8*cm
    scale = min(max_w/img.imageWidth, max_h/img.imageHeight, 1)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    return [img, Paragraph(caption, S['CaptionZH'])]


def callout(title, text, color=BLUE):
    tbl = Table([[Paragraph(f'<b>{esc(title)}</b><br/>{esc(text)}', S['BodyZH'])]], colWidths=[16.8*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 0.8, color),
        ('LEFTPADDING', (0,0), (-1,-1), 10), ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    return tbl


def section(title):
    return [Paragraph(title, S['SectionZH']), HRFlowable(width='100%', thickness=0.7, color=BORDER, spaceAfter=7)]


def resume_story():
    st = []
    st += cover('台股月營收驚喜策略研究作品集', '履歷附件版｜圖表加強｜Portfolio-ready Research Brief', '從台灣月營收制度出發，建立 SUR-style 基本面驚喜因子、portfolio backtest、OOS / sector / winner / execution robustness，保留一個 portfolio-grade 電子 / 半導體供應鏈 repricing candidate。', ['Market Structure', 'Official Data', 'SUR Factors', 'Execution-aware'])
    st += section('01｜Executive Snapshot')
    st.append(callout('核心定位', '這是一個研究作品集，不是實盤交易系統。最終候選策略 S1 具備研究價值，但仍需 exact timestamp、survivorship、execution fill 與 paper-trading validation。'))
    st.append(Spacer(1, 8))
    st.append(kpi_cards([
        ('S1 Proxy Sharpe', '≈ 2.40', GREEN), ('Total Return', '+167.5%', GREEN), ('Max Drawdown', '-7.9%', AMBER), ('2025 Test Sharpe', '≈ 3.12', BLUE),
        ('Remove Top-5 Sharpe', '≈ 1.77', BLUE), ('Holding Horizon', '20D', NAVY), ('Universe Lens', 'TW Equities', NAVY), ('Status', 'Portfolio-grade', AMBER),
    ], cols=4))
    st.append(Spacer(1, 8))
    st += bullet([
        '研究問題：月營收公布後，市場是否對持續性營收 surprise 反應不足？',
        '核心訊號：3M SUR persistence + not-overheated momentum。',
        '最終解讀：偏電子 / 半導體供應鏈的 repricing，而非廣義全市場 alpha。',
        '研究紀律：不只看 full-sample Sharpe，必須通過 OOS、remove-winner、sector、cost、execution gates。'
    ])
    st.append(PageBreak())

    st += section('02｜Hypothesis & Strategy Design')
    st.append(Paragraph('市場制度 → 基本面 surprise → 延遲反應 → 短期 repricing', S['H2ZH']))
    st.append(para('台灣上市櫃公司每月公布營收，使投資人每月都能收到高頻基本面更新。若連續性營收 surprise 未被市場即時完全反映，公布後 10–20 個交易日可能出現短期漂移。'))
    st.append(Spacer(1, 6))
    st.append(kpi_cards([
        ('Signal', '3M SUR', BLUE), ('Filter', 'No overheated mom', BLUE), ('Selection', 'Top 8 / month', NAVY), ('Risk Control', 'Industry cap = 3', NAVY),
    ], cols=4))
    st.append(Spacer(1, 7))
    st.append(Paragraph('S1 incumbent configuration', S['H2ZH']))
    st.append(Paragraph('sur3_high_no_high_mom | liq50m | top8 | industry_cap=3 | semi_cap=none | sl8_trail12 | 20D', S['CodeZH']))
    st += bullet([
        'SUR-style surprise 比 raw YoY 更接近「超出預期」的基本面變化。',
        'Not-overheated momentum 用來避免價格已提前反映。',
        'Industry cap 與 liquidity threshold 用來降低單一產業 / 低流動性錯覺。'
    ])
    st.append(PageBreak())

    st += section('03｜Core Performance')
    st += chart('s1_nav_drawdown_zh.png', '圖 1｜S1 NAV 與 drawdown：觀察累積報酬路徑與回撤恢復能力。')
    st += chart('s1_monthly_returns_is_oos_zh.png', '圖 2｜月報酬 IS/OOS：拆分樣本內與樣本外表現，避免只看 full-sample。')
    st.append(PageBreak())

    st += section('04｜Search Discipline & Winner Dependence')
    st += chart('signal_search_sharpe_mdd_scatter_zh.png', '圖 3｜策略搜尋 Sharpe vs MDD：高 Sharpe 不代表可 promotion。')
    st += chart('top_variants_sharpe_vs_remove5_zh.png', '圖 4｜Top variants 與 remove-top-5：檢查績效是否由少數贏家主導。')
    st += chart('remove_winners_sharpe_decay_zh.png', '圖 5｜Remove winners Sharpe decay：right-tail dependence 是核心風險之一。')
    st.append(callout('解讀', '一些變體在移除大贏家後快速衰退，因此不能只用 full-sample Sharpe 選策略。S1 被保留，是因為它在可解釋性、績效與穩健性之間較平衡。', AMBER))
    st.append(PageBreak())

    st += section('05｜Walk-forward & Sector Survival')
    st += chart('phase3_12_walkforward_oos_nav_zh.png', '圖 6｜Walk-forward OOS NAV：檢查 train-selected rule 是否能在未來期間維持。')
    st += chart('phase3_12_sector_survival_zh.png', '圖 7｜Sector survival：電子 / 半導體依賴明顯。')
    st.append(callout('研究定位修正', 'Sector stress 顯示策略不應被包裝成 broad-market Taiwan alpha；更準確的說法是「電子 / 半導體供應鏈月營收 surprise repricing candidate」。'))
    st.append(PageBreak())

    st += section('06｜Price-volume Extension: Quiet Digestion')
    st.append(para('後續 price-volume / K-line 研究不是技術指標 mining，而是檢查月營收 surprise 後市場如何消化資訊。Quiet digestion 指「高 SUR、未過熱、低異常成交量、窄幅整理」。'))
    st += chart('phase3_17_quiet_digestion_nav_zh.png', '圖 8｜Quiet digestion standalone diagnostics：有因果解釋，但交易數少且 winner-dependent。')
    st += chart('phase3_18_dynamic_sizing_nav_zh.png', '圖 9｜Dynamic sizing：作為 S1 sizing hypothesis 小幅改善，但不足以 promotion。')
    st.append(PageBreak())

    st += section('07｜Execution Realism & Next Step')
    st.append(kpi_cards([
        ('Conservative Entry', 'Next open', NAVY), ('Cost Stress', '1.0%', AMBER), ('Limit-up Risk', 'Excluded', RED), ('Quiet Boost Sharpe', '≈ 1.24', AMBER),
    ], cols=4))
    st.append(Spacer(1, 8))
    st += bullet([
        '保守假設：next_open + 1.0% cost + exclude possible limit-up risk。',
        '結果仍為正，但 headline quality 顯著下降。',
        '下一階段不應繼續擴大 grid search，而應做 exact timestamp、paper trading、fill feasibility。'
    ])
    st.append(callout('履歷一句話', 'Built a Taiwan monthly-revenue surprise research pipeline using official data, SUR-style fundamental factors, walk-forward / sector / winner / execution robustness tests; identified a portfolio-grade electronics/semiconductor repricing candidate while explicitly rejecting production-readiness.', GREEN))
    return st


def guide_story():
    st = []
    st += cover('台股月營收驚喜策略研究作品集', '導讀與面試講稿版｜每個部分該講什麼', '這份文件不是給 reviewer 的正式研究報告，而是給你面試 / 口頭簡報時使用：每一段都整理「要傳達的重點、建議講法、可能追問、回答方式」。', ['30 秒 Pitch', '3 分鐘架構', '追問回答', '履歷 bullet'])
    st += section('01｜30 秒 Pitch')
    st.append(callout('建議講法', '我做的是台股月營收驚喜策略研究。台灣公司每月公布營收，所以比季度財報有更高頻的基本面更新。我研究市場是否會對連續性的營收 surprise 反應不足，導致公布後 10–20 個交易日有短期 repricing。我不是只做高 Sharpe 回測，而是建立官方資料 pipeline、SUR 因子、portfolio backtest，並做 OOS、sector、remove-winner、成本與執行時點檢查。最後保留一個 portfolio-grade 電子 / 半導體供應鏈候選策略，但不宣稱 production-ready。'))
    st += bullet(['重點：市場制度出發，不是 indicator mining。', '重點：懂 data timing / look-ahead bias。', '重點：懂 robustness 與不 overclaim。'])
    st.append(PageBreak())

    sections = [
        ('02｜專案動機', '台灣月營收制度是一個可被系統化測試的高頻基本面事件。', '這個策略不是從技術指標開始，而是從台灣市場制度開始。台灣公司每月公布營收，我想測試連續性 surprise 是否造成公布後 10–20D repricing。', '為什麼市場會反應不足？', '月營收公開不代表所有人會立即完整解讀，尤其供應鏈資料需要產業脈絡，資金可能逐步重新定價。'),
        ('03｜資料與 anti-look-ahead', '資料時點比模型更重要。', '我區分 revenue month、data available date、signal date、trade date；因 exact timestamp 尚未完整，所以用 next-open / delayed entry proxy，不宣稱 same-day tradability。', '你如何避免 look-ahead bias？', '我沒有用 revenue month 交易，而用 usable-date proxy 和 delayed entry stress，並把 timestamp 缺口列為 limitation。'),
        ('04｜因子設計', '測的是 surprise，不是單純 growth。', '我比較 YoY、MoM、3M growth、SUR-style surprise、industry-adjusted surprise。最後較穩定的是 3M SUR persistence + not-overheated momentum。', '為什麼 SUR 比 YoY 好？', 'YoY 可能有基期效果或已被預期；SUR 更接近超出預期的部分，符合 post-announcement drift 假說。'),
        ('05｜策略設定', '規則簡單、可解釋、有集中度控制。', 'S1 使用 3M SUR persistence、排除過熱 momentum、liq50m、Top8、industry cap 3、20D holding。', '為什麼 20D？', '10D 較像短事件交易，容易靠右尾；20D 較符合逐步 repricing，也較穩定。'),
        ('06｜績效結果', '講結果，但不要過度推銷。', 'S1 proxy Sharpe 約 2.4、return 約 167.5%、MDD 約 -7.9%。但我視為 research candidate，不是 production claim。', 'Sharpe 2.4 可以信嗎？', '它是 proxy diagnostic；還需要 exact timestamp、survivorship、execution fill 與 paper trading。'),
        ('07｜Robustness', '證明你不是只挑漂亮回測。', '我做 remove-winner、walk-forward、sector survival、cost、liquidity、execution timing stress。部分版本 remove-winner 後衰退，因此不 promotion。', '如果靠少數大贏家怎麼辦？', '這代表 right-tail dependence，需要揭露並控制；不能只看 full-sample Sharpe。'),
        ('08｜Sector survival', '決定策略真正定位。', 'No-semiconductor 後表現明顯變弱，所以我把它定位成電子 / 半導體供應鏈 repricing，而不是全市場 alpha。', '產業集中是缺點嗎？', '不一定，但必須誠實定位，並在風控與 capacity 假設中反映。'),
        ('09｜Quiet digestion', '這是有因果解釋的 extension，但沒有 over-promote。', 'Quiet digestion 是好營收後低量窄幅整理，可能代表市場仍在消化資訊。但 standalone sparse 且 winner-dependent，所以只作為 sizing hypothesis。', '這是不是技術分析？', '不是用 K 線名稱挖 alpha，而是把價格 / 成交量當作基本面 surprise 後的市場消化狀態。'),
        ('10｜Execution realism', '回測和能交易是兩回事。', '我加入 next-open、延遲、成本、limit-up non-fill proxy。保守假設下 Sharpe 下降，因此不能稱 production-ready。', '績效下降還值得做嗎？', '值得，因為研究價值是知道 alpha 在哪些假設下存在或消失；下一步要 paper trading。'),
        ('11｜Paper trading', '下一步不是 overfit，而是驗證操作可行性。', '每月記錄 data_observed_at、signal_generated_at、planned entry、non-fill、slippage、paper fill、5D/10D/20D return 與 assumption drift。', 'paper trading 要證明什麼？', '它驗證 operational feasibility，不是單獨證明 alpha。')
    ]
    for title, core, say, q, ans in sections:
        st += section(title)
        st.append(kpi_cards([('要傳達的核心', core, BLUE)], cols=1))
        st.append(Spacer(1, 6))
        st.append(Paragraph('建議講法', S['H2ZH']))
        st.append(para(say))
        st.append(Paragraph('可能追問', S['H2ZH']))
        st.append(callout(q, ans, AMBER))
        st.append(Spacer(1, 4))
    st.append(PageBreak())
    st += section('12｜履歷 bullet 與簡報節奏')
    st.append(Paragraph('中文履歷 bullet', S['H2ZH']))
    st += bullet([
        '建立台股月營收 surprise 量化研究流程，使用官方月營收與市場資料，設計 3M SUR persistence + momentum overextension control 因子。',
        '完成 portfolio-level backtest、walk-forward OOS、sector survival、remove-winner、成本、流動性與執行時點壓力測試。',
        '保留一個 portfolio-grade 電子 / 半導體供應鏈 repricing 候選策略；同時明確揭露 exact timing、survivorship、execution fill 與 winner concentration 限制。'
    ])
    st.append(Paragraph('3 分鐘架構', S['H2ZH']))
    st += bullet(['0:00–0:30 專案動機', '0:30–1:00 資料與因子', '1:00–1:40 策略與結果', '1:40–2:20 Robustness', '2:20–2:50 Execution realism', '2:50–3:00 下一步'])
    st.append(callout('最後收尾', '這個專案最大的價值不是單一 Sharpe，而是完整研究流程：從市場制度提出假說、建立資料與因子、做 portfolio backtest，再逐步檢查 OOS、sector、winner、流動性、成本和執行可行性。最後保留一個值得 paper trading 的候選策略，但不 overclaim。', GREEN))
    return st


def build_pdf(filename, story, title):
    out = PORT / filename
    def footer(canvas: Canvas, doc):
        canvas.saveState()
        canvas.setFillColor(LIGHT)
        canvas.rect(0, PAGE_H-1.05*cm, PAGE_W, 1.05*cm, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont(FONT, 8)
        canvas.drawString(1.45*cm, PAGE_H-0.65*cm, title)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(PAGE_W-1.45*cm, PAGE_H-0.65*cm, 'Research / Paper-Trading Only')
        canvas.setFillColor(MUTED)
        canvas.drawString(1.45*cm, 0.85*cm, 'Taiwan Monthly Revenue Surprise Strategy')
        canvas.drawRightString(PAGE_W-1.45*cm, 0.85*cm, f'Page {doc.page}')
        canvas.restoreState()
    doc = SimpleDocTemplate(str(out), pagesize=A4, rightMargin=1.55*cm, leftMargin=1.55*cm, topMargin=1.55*cm, bottomMargin=1.35*cm)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out

if __name__ == '__main__':
    r = build_pdf('Taiwan_Monthly_Revenue_Strategy_Resume_Version_ZH_PRO.pdf', resume_story(), '履歷附件版｜台股月營收驚喜策略')
    g = build_pdf('Taiwan_Monthly_Revenue_Strategy_Talking_Guide_ZH_PRO.pdf', guide_story(), '導讀與面試講稿版｜台股月營收驚喜策略')
    print(r, r.stat().st_size)
    print(g, g.stat().st_size)
