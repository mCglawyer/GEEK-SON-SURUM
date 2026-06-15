"""Sevkiyat belgeleri için PDF üretimi (Yükleme Belgesi + Teslim Fişi).

Pillow gerektirmez: logo yerine markalı metin başlık kullanılır.
Türkçe karakterler için DejaVu TTF gömülür (static/fonts).
"""
import os
from io import BytesIO

from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

BRAND = colors.HexColor('#162AA3')
INK = colors.HexColor('#1f2430')
MUTED = colors.HexColor('#5b6472')
LINE = colors.HexColor('#d7dceb')
ZEBRA = colors.HexColor('#eef1fb')

_FONTS_OK = None


def _fonts():
    global _FONTS_OK
    if _FONTS_OK is not None:
        return _FONTS_OK
    base = os.path.join(settings.BASE_DIR, 'static', 'fonts')
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', os.path.join(base, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVu-Bold', os.path.join(base, 'DejaVuSans-Bold.ttf')))
        _FONTS_OK = True
    except Exception:
        _FONTS_OK = False
    return _FONTS_OK


def _say(d):
    if d is None:
        return '—'
    d = float(d)
    return str(int(d)) if d == int(d) else ('%.2f' % d)


def sevkiyat_pdf_bytes(talep, tip):
    """tip: 'yukleme' (Yükleme Belgesi) veya 'fis' (Teslim Fişi)."""
    ok = _fonts()
    font = 'DejaVu' if ok else 'Helvetica'
    fontb = 'DejaVu-Bold' if ok else 'Helvetica-Bold'

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title=f"Sevkiyat #{talep.id}")
    base = getSampleStyleSheet()['Normal']
    st_marka = ParagraphStyle('marka', parent=base, fontName=fontb, fontSize=13, leading=16, textColor=BRAND)
    st_baslik = ParagraphStyle('baslik', parent=base, fontName=fontb, fontSize=18, leading=23,
                               textColor=INK, spaceBefore=1, spaceAfter=4)
    st_sub = ParagraphStyle('sub', parent=base, fontName=font, fontSize=9, leading=12, textColor=MUTED)

    baslik = 'YÜKLEME BELGESİ' if tip == 'yukleme' else 'TESLİM FİŞİ'
    el = [
        Paragraph('GEEK COFFEE &amp; EATERY', st_marka),
        Paragraph(baslik, st_baslik),
        Paragraph('Personel Yönetim Sistemi · Sevkiyat', st_sub),
        Spacer(1, 8 * mm),
    ]

    bilgi = [
        ['Şube:', talep.sube.ad if talep.sube else '—', 'Belge No:', '#%s' % talep.id],
        ['Talep Tarihi:', talep.olusturma.strftime('%d.%m.%Y %H:%M'), 'Oluşturan:', talep.olusturan_ad or '—'],
    ]
    if talep.satin_alma_tarih:
        bilgi.append(['Satın Alma:', talep.satin_alan_ad or '—', 'Tarih:',
                      talep.satin_alma_tarih.strftime('%d.%m.%Y %H:%M')])
    if tip == 'fis' and talep.sevkiyat_tarih:
        bilgi.append(['Sevkiyat:', talep.sevkiyatci_ad or '—', 'Tarih:',
                      talep.sevkiyat_tarih.strftime('%d.%m.%Y %H:%M')])
    bt = Table(bilgi, colWidths=[28 * mm, 56 * mm, 28 * mm, 56 * mm])
    bt.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font), ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), fontb), ('FONTNAME', (2, 0), (2, -1), fontb),
        ('TEXTCOLOR', (0, 0), (-1, -1), INK),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    el.append(bt)
    el.append(Spacer(1, 6 * mm))

    rows = [['#', 'Ürün', 'İstenen', 'Son', 'Birim']]
    for i, k in enumerate(talep.kalemler.all(), 1):
        son = k.sevkiyat_miktar if k.sevkiyat_miktar is not None else (
            k.satinalma_miktar if k.satinalma_miktar is not None else k.istenen_miktar)
        bir = k.sevkiyat_birim or k.satinalma_birim or k.istenen_birim
        rows.append([str(i), k.urun_ad, _say(k.istenen_miktar), _say(son), bir])
    kt = Table(rows, colWidths=[12 * mm, 84 * mm, 26 * mm, 26 * mm, 22 * mm], repeatRows=1)
    kt.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font), ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, 0), fontb),
        ('BACKGROUND', (0, 0), (-1, 0), BRAND), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (2, 0), (4, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    el.append(kt)

    if talep.not_metni:
        el.append(Spacer(1, 4 * mm))
        el.append(Paragraph('Not: %s' % talep.not_metni, st_sub))

    el.append(Spacer(1, 16 * mm))
    if tip == 'yukleme':
        sol, sag = 'Teslim Eden (Satın Alma)', 'Teslim Alan (Sevkiyat)'
    else:
        sol, sag = 'Teslim Eden (Sevkiyat)', 'Teslim Alan (Şube Şefi)'
    imza = Table([['', ''], ['', ''], [sol, sag]], colWidths=[88 * mm, 88 * mm])
    imza.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font), ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TEXTCOLOR', (0, 2), (-1, 2), MUTED),
        ('LINEABOVE', (0, 2), (0, 2), 0.7, INK), ('LINEABOVE', (1, 2), (1, 2), 0.7, INK),
        ('TOPPADDING', (0, 2), (-1, 2), 6),
    ]))
    el.append(imza)

    if tip == 'yukleme':
        el.append(Spacer(1, 6 * mm))
        el.append(Paragraph('Bu belge yüklenecek ürünleri gösterir; "Verilen" adetler esas alınır.', st_sub))

    doc.build(el)
    pdf = buf.getvalue()
    buf.close()
    return pdf
