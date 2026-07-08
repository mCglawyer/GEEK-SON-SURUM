"""
Tüm PDF çıktıları (İnşaat Denetim formu, Sevkiyat belgeleri, Aylık Operasyon Raporu)
için ortak antetli sayfa şablonu.

Kullanım:
    from .pdf_letterhead import letterhead_callback, HEADER_ALAN_MM, FOOTER_ALAN_MM

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=HEADER_ALAN_MM * mm, bottomMargin=FOOTER_ALAN_MM * mm, ...)
    cb = letterhead_callback()
    doc.build(el, onFirstPage=cb, onLaterPages=cb)

Antet görseli (static/images/pdf/geek_antetli_baslik.png) kullanıcının sağladığı
"Geek Antetli" Word/PDF şablonundan alınmıştır: sol üstte logo, sağ üstte
web/e-posta/telefon/adres bilgileri. Alt bilgi (footer) aynı iletişim bilgilerini
küçük punto ile her sayfanın altında tekrarlar, böylece belge tek başına
yazdırılıp dolaşsa bile iletişim bilgileri kaybolmaz.
"""
import os
from django.conf import settings
from reportlab.lib import colors

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

# Üstte antet görseline ve altta iletişim satırlarına yer açmak için
# SimpleDocTemplate'e verilecek önerilen kenar boşlukları (mm cinsinden, sayı olarak).
HEADER_ALAN_MM = 34
FOOTER_ALAN_MM = 16


def letterhead_callback(font='Helvetica', font_size=6.6):
    """
    doc.build(..., onFirstPage=cb, onLaterPages=cb) için kullanılacak çizim
    fonksiyonunu üretir. Her sayfanın üstüne antet görselini, altına da
    iletişim bilgilerini (ince bir çizgiyle ayrılmış) çizer.
    """
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
        cizgi_y = doc.bottomMargin - 4
        canvas.line(doc.leftMargin, cizgi_y, page_w - doc.rightMargin, cizgi_y)

        canvas.setFont(font, font_size)
        canvas.setFillColor(MUTED)
        satir_y = cizgi_y - 8
        for satir in FOOTER_SATIRLAR:
            canvas.drawCentredString(page_w / 2.0, satir_y, satir)
            satir_y -= 8

        canvas.restoreState()
    return _ciz
