import io
import os

from django.conf import settings
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .pdf_letterhead import letterhead_callback, HEADER_ALAN_MM, FOOTER_ALAN_MM


def _fontlar():
    base = os.path.join(settings.BASE_DIR, 'static', 'fonts')
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', os.path.join(base, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVu-Bold', os.path.join(base, 'DejaVuSans-Bold.ttf')))
        return 'DejaVu', 'DejaVu-Bold'
    except Exception:
        return 'Helvetica', 'Helvetica-Bold'


def _esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


DURUM_METIN = {'tamam': '✓ Tamamlandı', 'devam': '● Devam Ediyor', 'yapilmadi': '✗ Yapılmadı'}
DURUM_RENK = {'tamam': '#137333', 'devam': '#b26a00', 'yapilmadi': '#b00020'}


def insaat_pdf_uret(proje, maddeler):
    font, fontb = _fontlar()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=HEADER_ALAN_MM * mm, bottomMargin=FOOTER_ALAN_MM * mm,
                            title="Insaat Denetim Formu")
    styles = getSampleStyleSheet()
    h = ParagraphStyle('h', parent=styles['Normal'], fontName=fontb, fontSize=14, textColor=colors.HexColor('#162AA3'))
    normal = ParagraphStyle('n', parent=styles['Normal'], fontName=font, fontSize=8, leading=9.5)
    small = ParagraphStyle('s', parent=styles['Normal'], fontName=font, fontSize=7, leading=8.5, textColor=colors.HexColor('#555555'))
    cellb = ParagraphStyle('cb', parent=normal, fontName=fontb, textColor=colors.white)

    el = []
    el.append(Paragraph('İnşaat Denetim Formu', h))
    el.append(Spacer(1, 4))

    tarih = timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')
    sorumlu = proje.sorumlu.ad_soyad if proje.sorumlu else '—'
    toplam = len(maddeler)
    tamam = sum(1 for m in maddeler if m.durum == 'tamam')
    yuzde = round(tamam * 100 / toplam) if toplam else 0

    el.append(Paragraph('Proje / Şube: <b>%s</b>' % _esc(proje.ad), normal))
    el.append(Paragraph('Sorumlu Bölge Müdürü: %s' % _esc(sorumlu), normal))
    el.append(Paragraph('Tarih: %s' % tarih, normal))
    el.append(Paragraph('İlerleme: %d / %d madde tamamlandı (%%%d)' % (tamam, toplam, yuzde), normal))
    if proje.tamamlandi:
        el.append(Paragraph('<b>Durum: PROJE TAMAMLANDI</b>', normal))
    el.append(Spacer(1, 5))

    kategori_adlari = [('urun', 'Ürün ve Ekipman'), ('insaat', 'İnşaat Süreci')]
    kat_h = ParagraphStyle('kh', parent=normal, fontName=fontb, fontSize=10, textColor=colors.HexColor('#162AA3'))

    for kod, kad in kategori_adlari:
        grup = [m for m in maddeler if getattr(m, 'kategori', 'urun') == kod]
        el.append(Spacer(1, 5))
        el.append(Paragraph(kad, kat_h))
        el.append(Spacer(1, 2))
        data = [[Paragraph('#', cellb), Paragraph('Görev', cellb), Paragraph('Durum', cellb), Paragraph('Not', cellb)]]
        for i, m in enumerate(grup, 1):
            data.append([Paragraph(str(i), normal), Paragraph(_esc(m.metin), normal),
                         Paragraph(DURUM_METIN.get(m.durum, m.durum), normal),
                         Paragraph(_esc(m.aciklama or ''), small)])
        if not grup:
            data.append([Paragraph('—', normal), Paragraph('Bu kategoride madde yok.', normal),
                         Paragraph('', normal), Paragraph('', normal)])
        tbl = Table(data, colWidths=[9 * mm, 79 * mm, 33 * mm, 53 * mm], repeatRows=1)
        ts = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#162AA3')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]
        for r, m in enumerate(grup, 1):
            ts.append(('TEXTCOLOR', (2, r), (2, r), colors.HexColor(DURUM_RENK.get(m.durum, '#333333'))))
        tbl.setStyle(TableStyle(ts))
        el.append(tbl)
    el.append(Spacer(1, 14))

    imza = Table([
        [Paragraph('Bayi Sahibi (Ad Soyad):', normal), Paragraph('İmza:', normal)],
        [Paragraph('______________________________', normal), Paragraph('______________________________', normal)],
    ], colWidths=[90 * mm, 84 * mm])
    imza.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    el.append(imza)

    cb = letterhead_callback(font=font)
    doc.build(el, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()
