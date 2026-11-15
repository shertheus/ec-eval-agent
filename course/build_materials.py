"""Build course figures, editable SVG figures and AI-use form from recorded evidence.
Requires reportlab and python-docx in a document-authoring environment.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math,random

ROOT=Path(__file__).resolve().parents[1]
COURSE=ROOT/'course'

def make_input():
    out=COURSE/'demo-input';out.mkdir(exist_ok=True)
    rng=random.Random(20261115);x=[0.,0.,0.];rows=[]
    for t in range(320):
        x=[.3*x[0]+rng.gauss(0,1),.45*x[0]+.2*x[1]+rng.gauss(0,1),-.35*x[1]+.25*x[2]+rng.gauss(0,1)]
        if t>=200:rows.append(x)
    p=out/'roi_demo.csv'
    with p.open('w',newline='') as f:csv.writer(f).writerows([[f'{v:.9f}' for v in row] for row in rows])
    checksum=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'metadata.json').write_text(json.dumps(dict(source='synthetic VAR course demonstration; no human subject data',shape=[120,3],seed=20261115,burn_in=200,kind='timeseries',truth_supplied_to_importer=False,sha256=checksum),indent=2)+'\n')
    (out/'roi_demo.csv.sha256').write_text(checksum+'  roi_demo.csv\n')

def build_figures(out,font_path):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
    from reportlab.graphics import renderSVG
    pdfmetrics.registerFont(TTFont('CJK',font_path))
    pdfmetrics.registerFontFamily('CJK',normal='CJK',bold='CJK',italic='CJK',boldItalic='CJK')
    def label(d,x,y,text,size=10,color='#182A3A'):
        d.add(String(x,y,text,fontName='CJK',fontSize=size,fillColor=colors.HexColor(color),textAnchor='middle'))
    def box(d,x,y,w,h,lines):
        d.add(Rect(x,y,w,h,fillColor=colors.HexColor('#F2F6FA'),strokeColor=colors.HexColor('#A6B8C8'),strokeWidth=.7,rx=4,ry=4))
        for i,s in enumerate(lines):label(d,x+w/2,y+h/2+7-(i*16),s)
    def arrow(d,x1,y1,x2,y2):
        d.add(Line(x1,y1,x2,y2,strokeColor=colors.HexColor('#667B8E'),strokeWidth=1))
        a=math.atan2(y2-y1,x2-x1);pts=[x2,y2,x2-6*math.cos(a)+3*math.sin(a),y2-6*math.sin(a)-3*math.cos(a),x2-6*math.cos(a)-3*math.sin(a),y2-6*math.sin(a)+3*math.cos(a)]
        d.add(Polygon(pts,fillColor=colors.HexColor('#667B8E'),strokeColor=None))
    diagram=Drawing(490,265)
    box(diagram,0,203,155,50,['自然语言任务','Pi 与 11 个领域工具'])
    box(diagram,335,203,155,50,['固定脚本入口','CLI / HTTP API'])
    box(diagram,168,122,154,52,['FastAPI 与协议校验','数据  参数  种子  预算'])
    box(diagram,0,28,155,56,['SQLite 调度与文件存储','状态  日志  校验和'])
    box(diagram,168,28,154,56,['独立算法进程','gCastle / Granger / NGC'])
    box(diagram,335,28,155,56,['结果核验与交付','JSON  CSV  SVG  ZIP'])
    arrow(diagram,78,203,200,174);arrow(diagram,412,203,290,174)
    arrow(diagram,245,122,245,84);arrow(diagram,168,145,78,84);arrow(diagram,155,56,168,56);arrow(diagram,322,56,335,56)
    figures=COURSE/'figures';figures.mkdir(exist_ok=True)
    renderSVG.drawToFile(diagram,str(figures/'architecture.svg'))
    results=json.loads((ROOT/'examples/reports/system-eval/results.json').read_text())
    agg=json.loads((ROOT/'examples/reports/system-eval/aggregate.json').read_text())
    def latency():
        d=Drawing(490,315)
        for tick in [0,20,40,60,80]:
            x=70+tick*4.8;d.add(Line(x,25,x,285,strokeColor=colors.HexColor('#DDE4EB'),strokeWidth=.5));label(d,x,10,str(tick),8)
        for i in range(10):
            y=267-i*25;tid=f'T{i+1:02d}';label(d,27,y,tid,9)
            for arm,dy,c in [('script',0,'#879CAD'),('agent',-9,'#246B9A')]:
                r=next(r for r in results if r['task']==tid and r['arm']==arm)
                d.add(Rect(70,y+dy,4.8*r['wall_seconds'],6,fillColor=colors.HexColor(c),strokeColor=None))
        label(d,130,302,'固定脚本（灰）',9);label(d,330,302,'Pi Agent（蓝）',9);label(d,470,10,'秒',8)
        return d
    chart=latency();renderSVG.drawToFile(chart,str(figures/'task-latency.svg'))
    rate=Drawing(490,175)
    label(rate,180,153,'固定脚本（灰）',9);label(rate,350,153,'Pi Agent（蓝）',9)
    for i,(key,name) in enumerate([('completed','任务完成'),('protocol_correct','协议正确'),('evidence_complete','证据完整')]):
        y=120-i*42;label(rate,50,y,name,10)
        for arm,dy,c in [('script',0,'#879CAD'),('agent',-12,'#246B9A')]:
            d=agg[arm][key];rate.add(Rect(115,y+dy,280*d/10,8,fillColor=colors.HexColor(c),strokeColor=None));label(rate,423,y+dy,str(d)+'/10',9)
    label(rate,250,3,'每个入口 10 项任务，含预期拒绝与超时处理',9)
    renderSVG.drawToFile(rate,str(figures/'task-outcomes.svg'))
    # SVG contains editable text; browser fallback resolves CJK fonts.
    for path in figures.glob('*.svg'):
        s=path.read_text().replace('font-family: CJK','font-family: Arial Unicode MS').replace('font-family="CJK"','font-family="Arial Unicode MS"');path.write_text(s)

def build_docx(out):
    from docx import Document
    from docx.shared import Inches,Pt,RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
    doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.27);sec.page_height=Inches(11.69);sec.top_margin=sec.bottom_margin=Inches(.65);sec.left_margin=sec.right_margin=Inches(.55)
    for st in ['Normal','Title','Heading 1','Heading 2']:
        style=doc.styles[st];style.font.name='Arial Unicode MS';style.font.color.rgb=RGBColor(0,0,0);style._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Arial Unicode MS')
    for st in doc.styles:
        for border in list(st._element.iter(qn('w:pBdr'))):border.getparent().remove(border)
        for fonts in st._element.iter(qn('w:rFonts')):
            for key in list(fonts.attrib):
                if 'theme' in key.lower():del fonts.attrib[key]
    doc.styles['Normal'].font.size=Pt(10);doc.styles['Normal'].paragraph_format.space_after=Pt(7)
    doc.add_paragraph('AI 使用声明表',style='Title')
    doc.add_paragraph('课程  人工智能技术科研应用实践\n项目  EC Eval Agent 脑连接自动评测系统\n姓名：________________    学号：________________')
    doc.add_paragraph('请核对下列已发生的辅助环节，填写采纳程度和实际人工核验操作。签署后，将同一份内容放入正式 PDF 附录。')
    headers=['环节','工具与版本','用途','提示词要点','采纳程度','人工核验方式']
    rows=[['开发与调试','Codex\n模型待本人核对','生成和修改后端、Pi 扩展、测试、Docker','Pi、gCastle、脑连接评测、Docker 交付','已纳入代码；本人确认：____','自动测试已完成；本人核验：____________'],['系统运行','Pi 1.5.0\ndeepseek-latest-flash','调用领域工具执行任务','固定数据、参数、种子和预算','实测记录已保存；本人确认：____','本人核对协议和结果：____________'],['数据与图表','Codex\nPython 脚本','汇总实测 JSON 并制图','使用真实记录与可复算指标','技术材料；本人采纳：____','本人复算与检查：____________'],['技术文档','Codex\nanti-defensive-writing','技术说明、选型比较与语言整理','按规范组织证据、删除空泛表述','初稿；本人修改：____','本人核对技术解释：____________'],['文献检索','Codex 网页检索','核对来源元数据与摘要','算法、工具调用、系统评测','候选清单；本人引用：____','本人阅读和定位原文：____________']]
    table=doc.add_table(rows=1,cols=6);table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
    widths=[.55,.95,1.15,1.25,1.1,1.15]
    for i,h in enumerate(headers):table.rows[0].cells[i].text=h
    for row in rows:
        cells=table.add_row().cells
        for i,value in enumerate(row):cells[i].text=value
    for ri,row in enumerate(table.rows):
        for i,cell in enumerate(row.cells):
            cell.width=Inches(widths[i]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=cell._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                v=OxmlElement('w:'+edge);v.set(qn('w:val'),'single');v.set(qn('w:sz'),'4');v.set(qn('w:color'),'D9D9D9');b.append(v)
            pr.append(b)
            if ri==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EFF5');pr.append(sh)
            for para in cell.paragraphs:
                para.paragraph_format.space_after=Pt(4);para.paragraph_format.space_before=Pt(4)
                for run in para.runs:run.font.size=Pt(9)
    header=OxmlElement('w:tblHeader');table.rows[0]._tr.get_or_add_trPr().append(header)
    doc.add_paragraph('AI 生成内容占全文比例（估计）：________ %')
    doc.add_paragraph('使用 AI 生成图表：□ 否  □ 是（注明：________________________）')
    doc.add_paragraph('开源档位自评：□ 复现级  □ 工具级  □ 系统级  □ 不适用')
    doc.add_paragraph('诚信声明：本报告的分析、结论与对策均由本人独立完成，所有引用真实可查；如有不实，愿承担学术不端责任。')
    doc.add_paragraph('签名：________________    日期：________________')
    for para in list(doc.paragraphs)+[p for t in doc.tables for row in t.rows for cell in row.cells for p in cell.paragraphs]:
        for run in para.runs:
            run.font.name='Arial Unicode MS';run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Arial Unicode MS')
    out.mkdir(parents=True,exist_ok=True);doc.save(out/'AI使用声明表_待本人核验签署.docx')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['input','figures','docx'],required=True);p.add_argument('--output',type=Path,default=Path('course-delivery'));p.add_argument('--font',default='/System/Library/Fonts/Supplemental/Arial Unicode.ttf');a=p.parse_args()
    if a.kind=='input':make_input()
    elif a.kind=='figures':build_figures(a.output,a.font)
    else:build_docx(a.output)
