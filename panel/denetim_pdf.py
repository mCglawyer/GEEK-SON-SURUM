import io
import os

from django.conf import settings
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image, Flowable, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .pdf_letterhead import build_pdf


def _fotograf_flowable(foto, max_w_mm=56, max_h_mm=48):
    """ImageFieldFile -> kutuya sığdırılmış (oran korunur), küçültülmüş Image. Sorun olursa None (PDF bozulmaz)."""
    if not foto:
        return None
    try:
        from PIL import Image as PILImage, ImageOps
        foto.open('rb')
        veri = foto.read()
        foto.close()
        pil = ImageOps.exif_transpose(PILImage.open(io.BytesIO(veri))).convert('RGB')
        pil.thumbnail((900, 900))
        cikti = io.BytesIO()
        pil.save(cikti, 'JPEG', quality=72)
        cikti.seek(0)
        w, h = pil.size
        oran = min(max_w_mm / w, max_h_mm / h)
        return Image(cikti, width=w * oran * mm, height=h * oran * mm)
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


def _yuzde(cevaplar):
    # boş bırakılan madde 0 puan sayılır
    return (sum(c.puan or 0 for c in cevaplar) / (len(cevaplar) * 5) * 100) if cevaplar else None


class _Cubuk(Flowable):
    """Yüzdeyi gösteren ince yatay çubuk."""
    def __init__(self, yuzde, genislik, renk):
        super().__init__()
        self.yuzde, self.genislik, self.renk, self.height, self.width = yuzde, genislik, renk, 4 * mm, genislik

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor('#E8EAF2'))
        c.roundRect(0, 0.8 * mm, self.genislik, 2.4 * mm, 1.2 * mm, stroke=0, fill=1)
        if self.yuzde:
            c.setFillColor(colors.HexColor(self.renk))
            c.roundRect(0, 0.8 * mm, max(self.genislik * min(self.yuzde, 100) / 100, 2.4 * mm), 2.4 * mm, 1.2 * mm, stroke=0, fill=1)


def _yuzde_renk(y):
    if y is None:
        return '#999999'
    return '#137333' if y >= 80 else ('#b26a00' if y >= 60 else '#b00020')


def denetim_pdf_uret(denetim, cevaplar):
    """cevaplar: select_related('madde', 'madde__bolum') (+ prefetch 'fotolar') ile çekilmiş DenetimCevap listesi."""
    font, fontb = _fontlar()
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    BRAND, GRI, CIZGI = colors.HexColor('#162AA3'), colors.HexColor('#6B7280'), colors.HexColor('#E3E6EF')
    h = ParagraphStyle('h', parent=styles['Normal'], fontName=fontb, fontSize=17, leading=21, textColor=BRAND)
    alt = ParagraphStyle('alt', parent=styles['Normal'], fontName=font, fontSize=9, leading=12, textColor=GRI)
    normal = ParagraphStyle('n', parent=styles['Normal'], fontName=font, fontSize=8.4, leading=10.8)
    kalin = ParagraphStyle('k', parent=normal, fontName=fontb)
    small = ParagraphStyle('s', parent=normal, fontSize=7.6, leading=9.6, textColor=colors.HexColor('#444444'))
    cellb = ParagraphStyle('cb', parent=normal, fontName=fontb, textColor=colors.white)
    kat_h = ParagraphStyle('kh', parent=normal, fontName=fontb, fontSize=11, leading=14, textColor=BRAND)
    bolum_baslik = ParagraphStyle('bb', parent=kat_h, spaceBefore=10, spaceAfter=3)
    LEFT = 14 * mm
    W = A4[0] - 2 * LEFT

    yuzde = denetim.toplam_puan if denetim.toplam_puan is not None else _yuzde(cevaplar)
    tarih = timezone.localtime(denetim.baslangic).strftime('%d.%m.%Y %H:%M')
    bitis = timezone.localtime(denetim.bitis).strftime('%d.%m.%Y %H:%M') if denetim.bitis else '—'
    denetleyen = denetim.denetleyen.ad_soyad if denetim.denetleyen else '—'
    cevaplanan = sum(1 for c in cevaplar if c.puan is not None)

    el = [Paragraph('Şube Denetim Raporu', h), Paragraph(_esc(denetim.sube.ad), alt), Spacer(1, 6)]

    # özet kartı: sol bilgi, sağ genel puan
    bilgi = Table([[Paragraph('Denetleyen', small), Paragraph(_esc(denetleyen), kalin)],
                   [Paragraph('Başlangıç', small), Paragraph(tarih, normal)],
                   [Paragraph('Bitiş', small), Paragraph(bitis, normal)],
                   [Paragraph('Puanlanan madde', small), Paragraph('%d / %d' % (cevaplanan, len(cevaplar)), normal)]],
                  colWidths=[30 * mm, 70 * mm])
    bilgi.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    renk = _yuzde_renk(yuzde)
    puan_h = ParagraphStyle('ph', parent=normal, fontName=fontb, fontSize=26, leading=30, alignment=1, textColor=colors.HexColor(renk))
    puan_a = ParagraphStyle('pa', parent=small, alignment=1)
    puan_kutu = Table([[Paragraph('%s' % ('%.0f' % yuzde if yuzde is not None else '—'), puan_h)],
                       [Paragraph('Genel puan (100 üzerinden)', puan_a)]], colWidths=[W - 108 * mm])
    puan_kutu.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), .8, colors.HexColor(renk)),
                                   ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FC')),
                                   ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    ozet = Table([[bilgi, puan_kutu]], colWidths=[104 * mm, W - 104 * mm])
    ozet.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    el += [ozet, Spacer(1, 8)]

    # bölümlere göre grupla
    gruplar, sira_listesi = {}, []
    for c in cevaplar:
        b = c.madde.bolum
        if b.id not in gruplar:
            gruplar[b.id] = {'ad': b.ad, 'cevaplar': []}
            sira_listesi.append(b.id)
        gruplar[b.id]['cevaplar'].append(c)

    # bölüm puanları
    el.append(Paragraph('Bölüm puanları', kat_h))
    el.append(Spacer(1, 3))
    satirlar = []
    for bid in sira_listesi:
        y = _yuzde(gruplar[bid]['cevaplar'])
        satirlar.append([Paragraph(_esc(gruplar[bid]['ad']), normal), _Cubuk(y, 62 * mm, _yuzde_renk(y)),
                         Paragraph('<font color="%s"><b>%s</b></font>' % (_yuzde_renk(y), '%.0f' % y if y is not None else '—'), normal)])
    t = Table(satirlar, colWidths=[W - 82 * mm, 66 * mm, 16 * mm])
    t.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), .4, CIZGI), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                           ('ALIGN', (2, 0), (2, -1), 'RIGHT')]))
    el += [t, Spacer(1, 6)]

    # dikkat gerektirenler (puan 0-2)
    zayif = [c for c in cevaplar if c.puan is not None and c.puan <= 2]
    if zayif:
        el.append(Paragraph('Dikkat gerektiren maddeler (%d)' % len(zayif), kat_h))
        el.append(Spacer(1, 3))
        rows = [[Paragraph('Bölüm', cellb), Paragraph('Madde', cellb), Paragraph('Puan', cellb), Paragraph('Not', cellb)]]
        for c in sorted(zayif, key=lambda x: (x.puan, x.madde.bolum.sira)):
            rows.append([Paragraph(_esc(c.madde.bolum.ad), small), Paragraph(_esc(c.madde.metin), normal),
                         Paragraph('<font color="#b00020"><b>%d</b></font>' % c.puan, normal), Paragraph(_esc(c.not_metni or ''), small)])
        t = Table(rows, colWidths=[34 * mm, W - 34 * mm - 14 * mm - 52 * mm, 14 * mm, 52 * mm], repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b00020')),
                               ('LINEBELOW', (0, 0), (-1, -1), .4, CIZGI), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
        el += [t, Spacer(1, 6)]

    # ayrıntılı bölümler
    for bid in sira_listesi:
        grup = gruplar[bid]
        y = _yuzde(grup['cevaplar'])
        el.append(Paragraph('%s <font size="9" color="%s">· %s</font>' % (
            _esc(grup['ad']), _yuzde_renk(y), ('%%%.0f' % y) if y is not None else '—'), bolum_baslik))
        data = [[Paragraph('Madde', cellb), Paragraph('Puan', cellb), Paragraph('Not', cellb)]]
        for c in grup['cevaplar']:
            data.append([Paragraph(_esc(c.madde.metin), normal),
                         Paragraph('<font color="%s"><b>%s</b></font>' % (_puan_renk(c.puan), c.puan if c.puan is not None else '—'), normal),
                         Paragraph(_esc(c.not_metni or ''), small)])
        tbl = Table(data, colWidths=[W - 14 * mm - 52 * mm, 14 * mm, 52 * mm], repeatRows=1)
        ts = [('BACKGROUND', (0, 0), (-1, 0), BRAND), ('LINEBELOW', (0, 0), (-1, -1), .4, CIZGI),
              ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
              ('ALIGN', (1, 0), (1, -1), 'CENTER')]
        for r in range(2, len(data), 2):
            ts.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#F8F9FC')))
        tbl.setStyle(TableStyle(ts))
        el.append(tbl)

        # fotoğraflar: madde başlığı + satır başına 3 fotoğraf
        for c in grup['cevaplar']:
            imgs = [x for x in (_fotograf_flowable(f) for f in c.tum_fotolar()) if x is not None]
            if not imgs:
                continue
            el.append(Spacer(1, 5))
            kutu_w = W / 3
            for k in range(0, len(imgs), 3):
                satir = imgs[k:k + 3] + [''] * (3 - len(imgs[k:k + 3]))
                ft = Table([satir], colWidths=[kutu_w] * 3)
                ft.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
                parca = [ft] if k else [Paragraph('📷 ' .replace('📷 ', '') + _esc(c.madde.metin) + ' — fotoğraflar (%d)' % len(imgs), small), Spacer(1, 2), ft]
                el.append(KeepTogether(parca))
    build_pdf(buf, el, pagesize=A4, left_margin=LEFT, right_margin=LEFT, font=font, title="Şube Denetim Raporu")
    return buf.getvalue()
