import io
import os

from django.conf import settings
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .pdf_letterhead import build_pdf


def _fotograf_flowable(cevap, max_genislik_mm=70):
    """Bir DenetimCevap.foto alanını (yerel disk ya da R2 fark etmez) PDF'e
    gömülebilecek bir Image flowable'a çevirir. Herhangi bir sorun olursa None döner
    (PDF üretimi asla bu yüzden bozulmaz)."""
    if not cevap.foto:
        return None
    try:
        from PIL import Image as PILImage
        cevap.foto.open('rb')
        veri = cevap.foto.read()
        cevap.foto.close()
        pil_img = PILImage.open(io.BytesIO(veri))
        genislik_px, yukseklik_px = pil_img.size
        genislik_mm = max_genislik_mm
        yukseklik_mm = genislik_mm * (yukseklik_px / genislik_px)
        return Image(io.BytesIO(veri), width=genislik_mm * mm, height=yukseklik_mm * mm)
    except Exception:
        return None


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


def _puan_renk(puan):
    if puan is None:
        return '#999999'
    if puan >= 4:
        return '#137333'
    if puan >= 3:
        return '#b26a00'
    return '#b00020'


def denetim_pdf_uret(denetim, cevaplar):
    """cevaplar: select_related('madde', 'madde__bolum') ile çekilmiş DenetimCevap listesi."""
    font, fontb = _fontlar()
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    h = ParagraphStyle('h', parent=styles['Normal'], fontName=fontb, fontSize=14, textColor=colors.HexColor('#162AA3'))
    normal = ParagraphStyle('n', parent=styles['Normal'], fontName=font, fontSize=8, leading=9.5)
    small = ParagraphStyle('s', parent=styles['Normal'], fontName=font, fontSize=7, leading=8.5, textColor=colors.HexColor('#555555'))
    cellb = ParagraphStyle('cb', parent=normal, fontName=fontb, textColor=colors.white)
    kat_h = ParagraphStyle('kh', parent=normal, fontName=fontb, fontSize=10, textColor=colors.HexColor('#162AA3'))

    el = []
    el.append(Paragraph('Şube Denetim Raporu', h))
    el.append(Spacer(1, 4))

    tarih = timezone.localtime(denetim.baslangic).strftime('%d.%m.%Y %H:%M')
    denetleyen = denetim.denetleyen.ad_soyad if denetim.denetleyen else '—'
    puan_metni = ('%.0f / 100' % denetim.toplam_puan) if denetim.toplam_puan is not None else 'Hesaplanmadı'

    el.append(Paragraph('Şube: <b>%s</b>' % _esc(denetim.sube.ad), normal))
    el.append(Paragraph('Denetleyen: %s' % _esc(denetleyen), normal))
    el.append(Paragraph('Tarih: %s' % tarih, normal))
    el.append(Paragraph('Genel Puan: <b>%s</b>' % puan_metni, normal))
    el.append(Spacer(1, 5))

    # Bölüme göre grupla (cevaplar zaten madde.bolum.sira, madde.sira sırasıyla gelir)
    gruplar = {}
    sira_listesi = []
    for c in cevaplar:
        bolum = c.madde.bolum
        if bolum.id not in gruplar:
            gruplar[bolum.id] = {'ad': bolum.ad, 'cevaplar': []}
            sira_listesi.append(bolum.id)
        gruplar[bolum.id]['cevaplar'].append(c)

    for bolum_id in sira_listesi:
        grup = gruplar[bolum_id]
        el.append(Spacer(1, 5))
        el.append(Paragraph(_esc(grup['ad']), kat_h))
        el.append(Spacer(1, 2))
        data = [[Paragraph('Madde', cellb), Paragraph('Puan', cellb), Paragraph('Not', cellb)]]
        for c in grup['cevaplar']:
            puan_str = str(c.puan) if c.puan is not None else '—'
            data.append([Paragraph(_esc(c.madde.metin), normal),
                         Paragraph(puan_str, normal),
                         Paragraph(_esc(c.not_metni or ''), small)])
        tbl = Table(data, colWidths=[110 * mm, 18 * mm, 46 * mm], repeatRows=1)
        ts = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#162AA3')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]
        for r, c in enumerate(grup['cevaplar'], 1):
            ts.append(('TEXTCOLOR', (1, r), (1, r), colors.HexColor(_puan_renk(c.puan))))
        tbl.setStyle(TableStyle(ts))
        el.append(tbl)

        fotolu_cevaplar = [c for c in grup['cevaplar'] if c.foto]
        if fotolu_cevaplar:
            el.append(Spacer(1, 4))
            for c in fotolu_cevaplar:
                foto_el = _fotograf_flowable(c)
                if foto_el is None:
                    continue
                el.append(Paragraph(_esc(c.madde.metin), small))
                el.append(Spacer(1, 2))
                el.append(foto_el)
                el.append(Spacer(1, 6))

    build_pdf(buf, el, pagesize=A4, left_margin=14 * mm, right_margin=14 * mm,
             font=font, title="Sube Denetim Raporu")
    return buf.getvalue()
