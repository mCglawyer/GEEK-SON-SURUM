"""Aylık operasyon raporu PDF üreticisi."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT

BRAND = colors.HexColor("#162AA3")
ZEBRA = colors.HexColor("#EEF1FB")
LINE = colors.HexColor("#E3E6EF")
MUTED = colors.HexColor("#6B7280")

_FONT = 'Helvetica'
_FONTB = 'Helvetica-Bold'


def _fonts():
    global _FONT, _FONTB
    adaylar = [
        '/usr/share/fonts/truetype/dejavu',
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'fonts'),
    ]
    for base in adaylar:
        try:
            pdfmetrics.registerFont(TTFont('DejaVu', os.path.join(base, 'DejaVuSans.ttf')))
            pdfmetrics.registerFont(TTFont('DejaVu-Bold', os.path.join(base, 'DejaVuSans-Bold.ttf')))
            _FONT, _FONTB = 'DejaVu', 'DejaVu-Bold'
            return
        except Exception:
            continue


def aylik_rapor_bytes(ay_etiket, satirlar, toplam=None):
    """satirlar: [ [sube, calisan_gun, izin, rapor, devamsiz, zayi, sevkiyat, sayim], ... ]"""
    _fonts()
    import io
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=16 * mm, bottomMargin=15 * mm,
                            title="Aylık Operasyon Raporu")
    st_h = ParagraphStyle('h', fontName=_FONTB, fontSize=16, textColor=BRAND, leading=20)
    st_s = ParagraphStyle('s', fontName=_FONT, fontSize=9.5, textColor=MUTED, leading=14)
    st_c = ParagraphStyle('c', fontName=_FONT, fontSize=7.5, leading=9)
    st_cw = ParagraphStyle('cw', fontName=_FONTB, fontSize=7.5, leading=9, textColor=colors.white)
    el = [Paragraph("GEEK COFFEE &amp; EATERY", st_h),
          Paragraph("Aylık Operasyon Raporu · %s" % ay_etiket, st_s),
          Spacer(1, 8)]
    baslik = ['Şube', 'Çalışan-gün', 'İzin', 'Rapor', 'Devamsız', 'Zayi', 'Sevkiyat', 'Sayım']
    rows = [[Paragraph(b, st_cw) for b in baslik]]
    for s in satirlar:
        rows.append([Paragraph(str(x), st_c) for x in s])
    if toplam:
        rows.append([Paragraph('<b>%s</b>' % x, st_c) for x in toplam])
    w = doc.width
    col = [w * 0.22, w * 0.14, w * 0.10, w * 0.10, w * 0.13, w * 0.10, w * 0.13, w * 0.08]
    t = Table(rows, colWidths=col, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), BRAND),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ('GRID', (0, 0), (-1, -1), 0.4, LINE),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]
    if toplam:
        style.append(('BACKGROUND', (0, -1), (-1, -1), ZEBRA))
        style.append(('LINEABOVE', (0, -1), (-1, -1), 0.8, BRAND))
    t.setStyle(TableStyle(style))
    el.append(t)
    el.append(Spacer(1, 10))
    el.append(Paragraph("Bu rapor otomatik olarak oluşturulmuştur · geekpanel.net", st_s))
    doc.build(el)
    return buf.getvalue()
