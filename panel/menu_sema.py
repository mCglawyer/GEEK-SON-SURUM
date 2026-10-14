"""QR Menü Yönetimi — marka şemaları (tek doğruluk kaynağı).

Geek ve Baga QR sitelerinin okuduğu CSV sütunları BİREBİR burada tanımlıdır.
Sütun sırası/adı değişirse QR sitelerindeki rowToProduct bozulur; bu yüzden
CSV üretimi, formlar ve import komutu hep bu dosyadan beslenir.
"""

# ---- Alerjen sütunları (QR sitesindeki CSV başlıklarıyla aynı) -------------
GEEK_ALERJENLER = [
    'sut', 'yumurta', 'gluten', 'sert_kabuklu_yemis', 'yer_fistigi', 'susam',
    'soya', 'hardal', 'sirke_tursu', 'balik', 'koruyucu_madde',
]
BAGA_ALERJENLER = ['sut', 'yumurta', 'gluten', 'soya']

# Panelde gösterilecek Türkçe etiketler
ALERJEN_ETIKET = {
    'sut': 'Süt', 'yumurta': 'Yumurta', 'gluten': 'Gluten',
    'sert_kabuklu_yemis': 'Sert kabuklu yemiş', 'yer_fistigi': 'Yer fıstığı',
    'susam': 'Susam', 'soya': 'Soya', 'hardal': 'Hardal',
    'sirke_tursu': 'Sirke / turşu', 'balik': 'Balık', 'koruyucu_madde': 'Koruyucu madde',
}


def _sutunlar(alerjenler, icerik):
    s = ['kod', 'kategori_kodu', 'kategori', 'kategori_en', 'urun_adi', 'urun_adi_en',
         'fiyat', 'aciklama', 'aciklama_en']
    if icerik:
        s += ['icerik', 'icerik_en']
    s += ['kalori', 'protein']
    s += list(alerjenler)
    s += ['vegan', 'sube_notu', 'sube_notu_en', 'gorsel_link']
    return s


# ---- Marka tanımları ---------------------------------------------------------
# kategoriler: QR sitesinde SABİT tanımlı (kod, TR ad, EN ad) — site kodundaki
# CATEGORIES dizisinin birebir kopyası. Sırası sitedeki sıradır.
MARKALAR = {
    'geek': {
        'ad': 'Geek Coffee & Eatery',
        'sira': 1,
        'alerjenler': GEEK_ALERJENLER,
        'icerik': False,
        'kategoriler': [
            ('kahvaltilar', 'Kahvaltılar', 'Breakfast'),
            ('sandvic', 'Sandviçler', 'Sandwiches'),
            ('tost', 'Tostlar', 'Toasts'),
            ('wrap', "Wrap'ler", 'Wraps'),
            ('bowl', "Bowl'lar", 'Bowls'),
            ('tatli', 'Tatlı Başlangıçlar', 'Desserts'),
            ('anayemek', 'Ana Yemekler', 'Main Dishes'),
            ('ekstralar', 'Ekstralar', 'Extras'),
            ('ekmekler', 'Ekmekler', 'Breads'),
        ],
        # Sitede eski kodlar yeni koda yönlendirilir (LEGACY_CATEGORY_REDIRECT)
        'eski_kod_yonlendirme': {'yumurta': 'kahvaltilar', 'wrapbowl': 'wrap'},
        'csv_url': ('https://docs.google.com/spreadsheets/d/e/2PACX-1vTK8tq5v7eL7vAdCEWDz-bDf74VLMTdnjoIrDVWiqNu9eJMbYTsXs5pKDJppT7obQ/'
                    'pub?gid=145688361&single=true&output=csv'),
    },
    'baga': {
        'ad': 'Baga Burger',
        'sira': 2,
        'alerjenler': BAGA_ALERJENLER,
        'icerik': True,   # icerik / icerik_en alanları yalnızca Baga'da var
        'kategoriler': [
            ('hamburgerler', 'Hamburgerler', 'Burgers'),
            ('atistirmalik', 'Atıştırmalık', 'Snacks'),
            ('tatlilar', 'Tatlılar', 'Desserts'),
            ('ekstralar', 'Ekstralar', 'Extras'),
        ],
        'eski_kod_yonlendirme': {},
        'csv_url': ('https://docs.google.com/spreadsheets/d/e/2PACX-1vRj0gmij-3_-oEzPdXZRowA5MDDpcfZDO3WvTSl155k_tOiy7qeON0pZkokWKAuxA/'
                    'pub?gid=1151038596&single=true&output=csv'),
    },
}

for _k, _m in MARKALAR.items():
    _m['kod'] = _k
    _m['sutunlar'] = _sutunlar(_m['alerjenler'], _m['icerik'])
    _m['sitede_kodlar'] = [k[0] for k in _m['kategoriler']]

assert len(MARKALAR['geek']['sutunlar']) == 26
assert len(MARKALAR['baga']['sutunlar']) == 21

# CSV'nin yayınlanacağı R2 yolu (medya.geekpanel.net/menu/geek.csv)
def csv_anahtari(marka_kod):
    return 'menu/%s.csv' % marka_kod


def sema(marka_kod):
    return MARKALAR[marka_kod]


# ---- Yetki -------------------------------------------------------------------
# Rol değerleri panel.models.Rol ile aynıdır (Genel Müdür, Operatör, Yatırımcı).
MENU_YETKILI_ROLLER = ('Genel Müdür', 'Operatör', 'Yatırımcı')
