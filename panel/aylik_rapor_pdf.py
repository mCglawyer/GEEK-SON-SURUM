import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                KeepTogether, HRFlowable)
from reportlab.lib.styles import ParagraphStyle

from .pdf_letterhead import letterhead_callback, HEADER_ALAN_MM, FOOTER_ALAN_MM

BRAND = colors.HexColor("#162AA3")
BRAND_050 = colors.HexColor("#EEF1FB")
ZEBRA = colors.HexColor("#F4F6FB")
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

def _dk(m):
    m = int(m or 0)
    if m >= 60:
        return "%dsa %ddk" % (m // 60, m % 60)
    return "%ddk" % m

def aylik_rapor_bytes(ay_etiket, subeler_veri, genel=None):
    _fonts()
    import io
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=HEADER_ALAN_MM * mm, bottomMargin=FOOTER_ALAN_MM * mm,
                            title="Aylık Operasyon Raporu")
    st_s = ParagraphStyle('s', fontName=_FONT, fontSize=9.5, textColor=MUTED, leading=14)
    st_sb = ParagraphStyle('sb', fontName=_FONTB, fontSize=12, textColor=BRAND, leading=15)
    st_oz = ParagraphStyle('oz', fontName=_FONT, fontSize=8.5, textColor=MUTED, leading=12)
    st_c = ParagraphStyle('c', fontName=_FONT, fontSize=8, leading=10)
    st_cw = ParagraphStyle('cw', fontName=_FONTB, fontSize=8, leading=10, textColor=colors.white)
    st_ct = ParagraphStyle('ct', fontName=_FONTB, fontSize=8, leading=10, textColor=BRAND)

    el = [Paragraph("Aylık Operasyon Raporu · %s" % ay_etiket, st_s)]
    if genel:
        el.append(Spacer(1, 3))
        el.append(Paragraph(
            "Genel: Çalışan-gün <b>%s</b> · İzin <b>%s</b> · Rapor <b>%s</b> · Devamsız <b>%s</b> · "
            "Sevkiyat <b>%s</b>" % (
                genel.get('calisan', 0), genel.get('izin', 0), genel.get('rapor', 0),
                genel.get('devamsiz', 0), genel.get('sevkiyat', 0)), st_oz))
    el.append(Spacer(1, 6))

    baslik = ['Personel', 'Çalışılan gün', 'İzin', 'Rapor', 'Devamsız', 'Mola (adet)', 'Mola (süre)']
    w = doc.width
    col = [w * 0.30, w * 0.15, w * 0.09, w * 0.09, w * 0.12, w * 0.12, w * 0.13]

    for sv in subeler_veri:
        oz = sv.get('ozet', {})
        bas = [
            Paragraph(sv['ad'], st_sb),
            HRFlowable(width="100%", thickness=1, color=LINE, spaceBefore=3, spaceAfter=3),
            Paragraph("Sevkiyat: <b>%s</b>　·　Stok sayımı: <b>%s</b>" % (
                oz.get('sevkiyat', 0), oz.get('sayim', '-')), st_oz),
            Spacer(1, 3),
        ]
        rows = [[Paragraph(b, st_cw) for b in baslik]]
        for p in sv['personeller']:
            rows.append([
                Paragraph(p['ad'], st_c),
                Paragraph(str(p['calisan']), st_c), Paragraph(str(p['izin']), st_c),
                Paragraph(str(p['rapor']), st_c), Paragraph(str(p['devamsiz']), st_c),
                Paragraph(str(p['mola_say']), st_c), Paragraph(_dk(p['mola_dk']), st_c),
            ])
        t = sv.get('toplam', {})
        rows.append([
            Paragraph('TOPLAM', st_ct),
            Paragraph(str(t.get('calisan', 0)), st_ct), Paragraph(str(t.get('izin', 0)), st_ct),
            Paragraph(str(t.get('rapor', 0)), st_ct), Paragraph(str(t.get('devamsiz', 0)), st_ct),
            Paragraph(str(t.get('mola_say', 0)), st_ct), Paragraph(_dk(t.get('mola_dk', 0)), st_ct),
        ])
        tbl = Table(rows, colWidths=col, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, ZEBRA]),
            ('BACKGROUND', (0, -1), (-1, -1), BRAND_050),
            ('LINEABOVE', (0, -1), (-1, -1), 0.7, BRAND),
            ('GRID', (0, 0), (-1, -1), 0.3, LINE),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))

        el.append(KeepTogether(bas + [tbl] if len(sv['personeller']) <= 12 else bas))
        if len(sv['personeller']) > 12:
            el.append(tbl)
        el.append(Spacer(1, 12))

    el.append(Paragraph("Bu rapor otomatik olarak oluşturulmuştur · geekpanel.net", st_s))
    cb = letterhead_callback(font=_FONT)
    doc.build(el, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()
