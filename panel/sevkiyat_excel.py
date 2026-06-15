"""Onaylanan siparişi, orijinal BAR/TEMİZLİK talep formu şablonuna doldurup
xlsx olarak döndürür (fatura programına yüklemek için).

Şablon: panel/sevkiyat_sablon.xlsx
- Sheet1 (HAMMADDE): sol grup ürün B / talep E ; sağ grup ürün H / talep K
- Sheet2 (TEMİZLİK): ürün B / talep G
"""
import os
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell

SABLON = os.path.join(os.path.dirname(__file__), 'sevkiyat_sablon.xlsx')


def _nrm(s):
    return (s or '').strip().upper().replace('  ', ' ')


def _say(d):
    if d is None:
        return ''
    d = float(d)
    return str(int(d)) if d == int(d) else ('%.2f' % d)


def _yaz(ws, row, col, deger):
    """Hücreye güvenli yazar (merged ise atlar)."""
    c = ws.cell(row=row, column=col)
    if isinstance(c, MergedCell):
        return
    c.value = deger


def siparis_excel_bytes(talep):
    wb = load_workbook(SABLON)
    ws1 = wb['HAMMADDE TALEP FORMU']
    ws2 = wb['TEMİZLİK MALZ. TALEP FORMU']

    # Ürün adı -> (worksheet, talep_sütunu, satır) haritası
    harita = {}
    # Sheet1 sol grup: ürün B(2), talep E(5)
    for r in range(3, ws1.max_row + 1):
        ad = ws1.cell(r, 2).value
        if ad and str(ad).strip():
            harita[_nrm(ad)] = (ws1, 5, r)
    # Sheet1 sağ grup: ürün H(8), talep K(11)
    for r in range(3, ws1.max_row + 1):
        ad = ws1.cell(r, 8).value
        if ad and str(ad).strip():
            harita[_nrm(ad)] = (ws1, 11, r)
    # Sheet2: ürün B(2), talep G(7)
    for r in range(3, ws2.max_row + 1):
        ad = ws2.cell(r, 2).value
        if ad and str(ad).strip():
            harita[_nrm(ad)] = (ws2, 7, r)

    # Şube + tarih başlıkları (varsa etiketin yanına)
    try:
        _yaz(ws1, 1, 10, talep.sube.ad if talep.sube else '')          # I1 'ŞUBE ADI' -> J1
        _yaz(ws1, 1, 12, talep.olusturma.strftime('%d.%m.%Y'))         # K1 'TARİH' -> L1
    except Exception:
        pass

    ekler = []  # şablonda olmayan (özel) ürünler
    for k in talep.kalemler.all():
        miktar = (k.sevkiyat_miktar if k.sevkiyat_miktar is not None
                  else (k.satinalma_miktar if k.satinalma_miktar is not None else k.istenen_miktar))
        birim = k.sevkiyat_birim or k.satinalma_birim or k.istenen_birim
        deger = ('%s %s' % (_say(miktar), birim)).strip()
        yer = harita.get(_nrm(k.urun_ad))
        if yer:
            ws, col, row = yer
            _yaz(ws, row, col, deger)
        else:
            ekler.append((k.urun_ad, deger))

    # Özel ürünleri sağ gruptaki 'DİĞER' alanına (H78.., K78..) yaz
    if ekler:
        r = 78
        for ad, deger in ekler:
            if r > 86:
                break
            _yaz(ws1, r, 8, ad)
            _yaz(ws1, r, 11, deger)
            r += 1

    buf = BytesIO()
    wb.save(buf)
    pdf = buf.getvalue()
    buf.close()
    return pdf
