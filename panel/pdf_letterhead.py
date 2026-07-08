"""
Tüm PDF çıktıları (İnşaat Denetim formu, Sevkiyat belgeleri, Aylık Operasyon Raporu)
için ortak antetli sayfa şablonu.

Davranış:
- 1. sayfa: üstte antet görseli (logo + web/e-posta/telefon/adres), altta da aynı
  iletişim bilgileri küçük punto ile tekrar edilir.
- 2. ve sonraki sayfalar: antet YOK — sadece içerik (liste, imza vb.) daha geniş
  bir alanda devam eder. Kullanıcı tercihi: çok sayfalı belgelerde 2. sayfada
  tekrar logo/iletişim bilgisi görünmesine gerek yok.

Kullanım (3 PDF üreticisinde de aynı):
    from .pdf_letterhead import build_pdf

    buf = io.BytesIO()
    build_pdf(buf, el, pagesize=A4, left_margin=14 * mm, right_margin=14 * mm,
              font=font, title="Başlık")
    return buf.getvalue()

Antet görseli (static/images/pdf/geek_antetli_baslik.png) kullanıcının sağladığı
"Geek Antetli" Word/PDF şablonundan alınmıştır: sol üstte logo, sağ üstte
web/e-posta/telefon/adres bilgileri.
"""
import os
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate

BRAND = colors.HexColor('#162AA3')
MUTED = colors.HexColor('#5b6472')
LINE = colors.HexColor('#d7dceb')

HEADER_IMG = os.path.join(settings.BASE_DIR, 'static', 'images', 'pdf', 'geek_antetli_baslik.png')
# Görselin doğal en/boy oranı (yükseklik / genişlik) — sayfa genişliğine göre
# orantılı çizebilmek için sabit olarak tutuluyor.
HEADER_ORAN = 248.0 / 1829.0

FOOTER_SATIRLAR = [
    "www.geekcoffeeshop.com   ·   geek@geekcoffeeshop.com   ·   0 (507) 683 61 47",
    "Osmangazi Mahallesi, Mona Roza Caddesi, No: 11/G, Şehitkamil/Gaziantep",
]

# 1. sayfada antet + alt bilgiye yer açmak için ayrılan alan (mm, sayı olarak).
HEADER_ALAN_MM = 34
FOOTER_ALAN_MM = 16

# 2. ve sonraki sayfalarda antet olmadığı için kullanılan sade kenar boşlukları (mm).
SONRAKI_UST_MM = 14
SONRAKI_ALT_MM = 14


def _letterhead_ciz(font, font_size):
    def _ciz(canvas, doc):
        canvas.saveState()
        page_w, page_h = doc.pagesize

        if os.path.exists(HEADER_IMG):
            header_w = page_w - doc.leftMargin - doc.rightMargin
            header_h = header_w * HEADER_ORAN
            x = doc.leftMargin
            y = page_h - 8 - header_h
            try:
                canvas.drawImage(HEADER_IMG, x, y, width=header_w, height=header_h,
                                 preserveAspectRatio=True, anchor='n', mask='auto')
            except Exception:
                pass

        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.6)
        cizgi_y = FOOTER_ALAN_MM * mm - 4
        canvas.line(doc.leftMargin, cizgi_y, page_w - doc.rightMargin, cizgi_y)

        canvas.setFont(font, font_size)
        canvas.setFillColor(MUTED)
        satir_y = cizgi_y - 8
        for satir in FOOTER_SATIRLAR:
            canvas.drawCentredString(page_w / 2.0, satir_y, satir)
            satir_y -= 8

        canvas.restoreState()
    return _ciz


def _bos(canvas, doc):
    pass


def build_pdf(buf, story, *, pagesize, left_margin, right_margin, font='Helvetica',
             font_size=6.6, title=''):
    """
    story: reportlab flowable listesi (Paragraph, Table, Spacer, ...).
    1. sayfa antetli (HEADER_ALAN_MM / FOOTER_ALAN_MM kenar boşluklarıyla) üretilir,
    2. ve sonraki sayfalar antetsiz/sade (SONRAKI_UST_MM / SONRAKI_ALT_MM ile) devam eder.
    """
    page_w, page_h = pagesize
    ic_genislik = page_w - left_margin - right_margin

    ilk_ust = HEADER_ALAN_MM * mm
    ilk_alt = FOOTER_ALAN_MM * mm
    sonraki_ust = SONRAKI_UST_MM * mm
    sonraki_alt = SONRAKI_ALT_MM * mm

    frame_ilk = Frame(left_margin, ilk_alt, ic_genislik, page_h - ilk_ust - ilk_alt,
                     id='ilk', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_sonraki = Frame(left_margin, sonraki_alt, ic_genislik, page_h - sonraki_ust - sonraki_alt,
                         id='sonraki', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc = BaseDocTemplate(buf, pagesize=pagesize, title=title,
                         leftMargin=left_margin, rightMargin=right_margin,
                         topMargin=ilk_ust, bottomMargin=ilk_alt)
    cb = _letterhead_ciz(font, font_size)
    doc.addPageTemplates([
        PageTemplate(id='Ilk', frames=[frame_ilk], onPage=cb),
        PageTemplate(id='Sonraki', frames=[frame_sonraki], onPage=_bos),
    ])
    tam_story = [NextPageTemplate('Sonraki')] + list(story)
    doc.build(tam_story)
    return doc
