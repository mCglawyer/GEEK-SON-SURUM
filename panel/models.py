import secrets
from django.db import models
from django.contrib.auth.models import User


# =========================================================================
# SEÇENEK LİSTELERİ
# =========================================================================
class Rol(models.TextChoices):
    GENEL_MUDUR = 'Genel Müdür', 'Genel Müdür (Tam Yetkili)'
    MUDUR = 'Müdür', 'Bölge Müdürü'
    OPERATOR = 'Operatör', 'Operatör (Tam Yetkili)'
    YATIRIMCI = 'Yatırımcı', 'Yatırımcı (Tam Yetkili)'
    SATIN_ALMA = 'Satın Alma', 'Satın Alma'
    SEVKIYAT = 'Sevkiyat', 'Sevkiyat'
    EGITMEN = 'Eğitmen', 'Eğitmen'
    SEF = 'Şef', 'Şube Şefi'
    PERSONEL = 'Personel', 'Personel'


class VardiyaTipi(models.TextChoices):
    SABAHCI = 'Sabahçı', 'Sabahçı'
    ARACI = 'Aracı', 'Aracı'
    AKSAMCI = 'Akşamcı', 'Akşamcı'
    IZINLI = 'İzinli', 'İzinli'
    RAPORLU = 'Raporlu', 'Raporlu'
    DEVAMSIZ = 'Devamsız', 'Devamsız'


class OnayDurumu(models.TextChoices):
    TASLAK = 'Taslak', 'Taslak'
    ONAY_BEKLIYOR = 'Onay Bekliyor', 'Onay Bekliyor'
    ONAYLANDI = 'Onaylandı', 'Onaylandı'
    REDDEDILDI = 'Reddedildi', 'Reddedildi'


# Yönetim rolleri (şifreyle giriş yapar); diğerleri (Personel) kod ile girer
YONETIM_ROLLERI = [Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SEF]


# =========================================================================
# MODELLER
# =========================================================================
class Sube(models.Model):
    ad = models.CharField(max_length=100, verbose_name="Şube Adı")
    depo_mu = models.BooleanField(
        default=False, verbose_name="Depo mu?",
        help_text="İşaretliyse bu şube vardiya planına dahil edilmez.")

    class Meta:
        verbose_name = "Şube"; verbose_name_plural = "Şubeler"; ordering = ['ad']

    def __str__(self):
        return self.ad


class Personel(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='personel', verbose_name="Kullanıcı Hesabı")
    ad_soyad = models.CharField(max_length=100, verbose_name="Ad Soyad")
    sube = models.ForeignKey(
        Sube, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='personeller', verbose_name="Şubesi")
    sorumlu_subeler = models.ManyToManyField(
        Sube, blank=True, related_name='bolge_mudurleri',
        verbose_name="Sorumlu olduğu şubeler (Bölge Müdürü)")
    rol = models.CharField(
        max_length=20, choices=Rol.choices, default=Rol.PERSONEL, verbose_name="Rol")
    egitmen = models.BooleanField(
        default=False, verbose_name="Eğitmen yetkisi",
        help_text="İşaretliyse bu kişi (rolü ne olursa olsun) soru yönetimi ve bilgi karnesine erişir.")
    giris_kodu = models.CharField(
        max_length=6, unique=True, null=True, blank=True,
        verbose_name="Giriş Kodu",
        help_text="Personel rolündekilerin sisteme giriş için kullandığı 6 haneli kod.")

    class Meta:
        verbose_name = "Personel"; verbose_name_plural = "Personeller"; ordering = ['ad_soyad']

    def __str__(self):
        return f"{self.ad_soyad} ({self.sube.ad if self.sube else 'Şubesiz'})"

    @staticmethod
    def benzersiz_kod_uret():
        """Kullanımda olmayan, rastgele 6 haneli bir kod üretir."""
        while True:
            kod = f"{secrets.randbelow(1_000_000):06d}"
            if not Personel.objects.filter(giris_kodu=kod).exists():
                return kod

    def kodu_yenile(self):
        self.giris_kodu = self.benzersiz_kod_uret()
        self.save(update_fields=['giris_kodu'])

    def save(self, *args, **kwargs):
        # Her personele benzersiz bir giriş kodu ata
        if not self.giris_kodu:
            self.giris_kodu = self.benzersiz_kod_uret()
        super().save(*args, **kwargs)
        # Personel veya Şef rolündeyse ve bağlı kullanıcı yoksa, kod ile giriş
        # için otomatik (şifresiz) bir kullanıcı hesabı oluştur
        if self.user_id is None and self.rol in (Rol.PERSONEL, Rol.SEF):
            u = User.objects.create(username=f"kod_{self.giris_kodu}")
            u.set_unusable_password()
            u.save()
            self.user = u
            super().save(update_fields=['user'])


class Vardiya(models.Model):
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='vardiyalar')
    tarih = models.DateField(verbose_name="Vardiya Tarihi")
    vardiya_tipi = models.CharField(
        max_length=20, choices=VardiyaTipi.choices, default=VardiyaTipi.SABAHCI, verbose_name="Vardiya Tipi")
    notlar = models.TextField(blank=True, null=True, verbose_name="Personel Notu / Mazeret")
    durum = models.CharField(
        max_length=20, choices=OnayDurumu.choices, default=OnayDurumu.TASLAK, verbose_name="Onay Durumu")
    red_notu = models.TextField(blank=True, null=True, verbose_name="Red Notu")

    class Meta:
        verbose_name = "Vardiya"; verbose_name_plural = "Vardiyalar"; ordering = ['tarih']
        constraints = [models.UniqueConstraint(fields=['personel', 'tarih'], name='unique_personel_tarih_vardiya')]

    def __str__(self):
        return f"{self.personel.ad_soyad} - {self.tarih} - {self.vardiya_tipi} ({self.durum})"


class Mola(models.Model):
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='molalar')
    tarih = models.DateField(verbose_name="Mola Tarihi", blank=True, null=True)
    mola_tipi = models.CharField(max_length=20, default='1. Mola', verbose_name="Mola Tipi")
    baslangic_saati = models.TimeField(blank=True, null=True, verbose_name="Başlangıç Saati")
    bitis_saati = models.TimeField(blank=True, null=True, verbose_name="Bitiş Saati")

    class Meta:
        verbose_name = "Mola"; verbose_name_plural = "Molalar"; ordering = ['-tarih', '-baslangic_saati']

    def mola_suresi_dakika(self):
        if self.baslangic_saati and self.bitis_saati:
            t1 = self.baslangic_saati.hour * 60 + self.baslangic_saati.minute
            t2 = self.bitis_saati.hour * 60 + self.bitis_saati.minute
            diff = t2 - t1
            if diff < 0:
                diff += 1440
            return diff
        return 0

    def __str__(self):
        return f"{self.personel.ad_soyad} - {self.baslangic_saati}"


class Puantaj(models.Model):
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='puantajlar')
    ay = models.DateField(verbose_name="Puantaj Ayı")
    calisilan_gun = models.IntegerField(default=0, verbose_name="Çalışılan Gün")
    eksik_gun = models.IntegerField(default=0, verbose_name="Eksik Gün")
    izinli_gun = models.IntegerField(default=0, verbose_name="İzinli Gün")
    raporlu_gun = models.IntegerField(default=0, verbose_name="Raporlu Gün")
    manuel_duzenlendi = models.BooleanField(default=False, verbose_name="Manuel Düzenlendi mi?")

    class Meta:
        verbose_name = "Puantaj"; verbose_name_plural = "Puantajlar"; ordering = ['-ay']
        constraints = [models.UniqueConstraint(fields=['personel', 'ay'], name='unique_personel_ay_puantaj')]

    def __str__(self):
        return f"{self.personel.ad_soyad} - {self.ay.strftime('%m/%Y')}"


class KodKilit(models.Model):
    """Kod ile girişte kaba kuvvet (brute-force) denemelerini sınırlamak için."""
    ip = models.CharField(max_length=45, unique=True, verbose_name="IP Adresi")
    hatali_deneme = models.IntegerField(default=0)
    kilit_bitis = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Kod Giriş Kilidi"; verbose_name_plural = "Kod Giriş Kilitleri"

    def __str__(self):
        return f"{self.ip} ({self.hatali_deneme} hatalı)"


class Birim(models.TextChoices):
    ADET = 'adet', 'adet'
    ML = 'ml', 'ml'


class Zayi(models.Model):
    """Şube bazlı zayi (fire) kaydı. Personel/şef girer, yönetim görüntüler."""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='zayiler', verbose_name="Şube")
    giren = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='zayi_girisleri', verbose_name="Giren Personel")
    giren_ad = models.CharField(max_length=100, blank=True, verbose_name="Giren (ad)")
    urun_adi = models.CharField(max_length=120, verbose_name="Ürün Adı")
    miktar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Miktar")
    birim = models.CharField(max_length=10, choices=Birim.choices, default=Birim.ADET, verbose_name="Birim")
    olusturma = models.DateTimeField(auto_now_add=True, verbose_name="Girildiği An")

    class Meta:
        verbose_name = "Zayi"
        verbose_name_plural = "Zayiler"
        ordering = ['-olusturma']

    def __str__(self):
        return f"{self.urun_adi} - {self.miktar} {self.birim}"


class Kalibrasyon(models.Model):
    """Personel/şef tarafından anlık kameradan çekilip yüklenen günlük kalibrasyon görüntüsü."""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='kalibrasyonlar', verbose_name="Şube")
    giren = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='kalibrasyonlar', verbose_name="Yükleyen")
    giren_ad = models.CharField(max_length=100, blank=True, verbose_name="Yükleyen (ad)")
    foto = models.FileField(upload_to='kalibrasyon/%Y/%m/%d/', verbose_name="Görüntü")
    olusturma = models.DateTimeField(auto_now_add=True, verbose_name="Yüklendiği An")

    class Meta:
        verbose_name = "Kalibrasyon"
        verbose_name_plural = "Kalibrasyonlar"
        ordering = ['-olusturma']

    def __str__(self):
        return f"{self.sube} - {self.giren_ad} - {self.olusturma:%d.%m.%Y %H:%M}"


class Irsaliye(models.Model):
    """Sevkiyatçıların anlık kameradan çektiği ürün transfer / irsaliye görseli + açıklama.
    Şube bazlı değildir; transfer yönü açıklamada belirtilir."""
    giren = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='irsaliyeler', verbose_name="Yükleyen")
    giren_ad = models.CharField(max_length=100, blank=True, verbose_name="Yükleyen (ad)")
    foto = models.FileField(upload_to='irsaliye/%Y/%m/%d/', verbose_name="Görüntü")
    aciklama = models.TextField(verbose_name="Açıklama")
    olusturma = models.DateTimeField(auto_now_add=True, verbose_name="Yüklendiği An")

    class Meta:
        verbose_name = "İrsaliye / Transfer"
        verbose_name_plural = "İrsaliye / Transferler"
        ordering = ['-olusturma']

    def __str__(self):
        return f"{self.giren_ad} - {self.olusturma:%d.%m.%Y %H:%M}"


class StokUrun(models.Model):
    """Ay sonu stok sayımında sayılacak kalemler (katalog). Excel'den 'stok_yukle' ile yüklenir."""
    kategori = models.CharField(max_length=80, blank=True, verbose_name="Grup")
    ad = models.CharField(max_length=200, verbose_name="Ürün Adı")
    kapali_icerik = models.DecimalField(max_digits=12, decimal_places=2, default=1,
                                        verbose_name="Kapalı kutu içeriği (adet/ml/kg)")
    acik_carpan = models.DecimalField(max_digits=12, decimal_places=2, default=1,
                                      verbose_name="Açık kutu çarpanı")
    sira = models.PositiveIntegerField(default=0, verbose_name="Sıra")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Stok Kalemi (Katalog)"
        verbose_name_plural = "Stok Kalemleri (Katalog)"
        ordering = ['sira', 'ad']

    def __str__(self):
        return self.ad


class StokSayim(models.Model):
    """Bir şubenin bir aya ait stok sayımı (şube şefi girer)."""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='stok_sayimlari', verbose_name="Şube")
    ay = models.DateField(verbose_name="Ay (ayın 1'i)")
    giren = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='stok_sayimlari', verbose_name="Giren")
    giren_ad = models.CharField(max_length=100, blank=True, verbose_name="Giren (ad)")
    olusturma = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturma")
    guncelleme = models.DateTimeField(auto_now=True, verbose_name="Son Güncelleme")

    class Meta:
        verbose_name = "Stok Sayımı"
        verbose_name_plural = "Stok Sayımları"
        ordering = ['-ay']
        unique_together = [('sube', 'ay')]

    def __str__(self):
        return f"{self.sube} - {self.ay:%m.%Y}"


class StokSayimKalem(models.Model):
    sayim = models.ForeignKey(StokSayim, on_delete=models.CASCADE, related_name='kalemler')
    urun = models.ForeignKey(StokUrun, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    urun_ad = models.CharField(max_length=200, verbose_name="Ürün Adı")
    kategori = models.CharField(max_length=80, blank=True, verbose_name="Grup")
    kapali_icerik = models.DecimalField(max_digits=12, decimal_places=2, default=1, verbose_name="Kapalı içerik")
    acik_carpan = models.DecimalField(max_digits=12, decimal_places=2, default=1, verbose_name="Açık çarpan")
    kapali_adet = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Kapalı kutu adedi")
    acik_miktar = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Açık kutu miktarı")
    aciklama = models.CharField(max_length=300, blank=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Stok Sayım Kalemi"
        verbose_name_plural = "Stok Sayım Kalemleri"
        ordering = ['id']

    @property
    def toplam(self):
        return (self.kapali_adet * self.kapali_icerik) + (self.acik_miktar * self.acik_carpan)

    def __str__(self):
        return f"{self.urun_ad}: {self.toplam}"


class SevkiyatBirim(models.TextChoices):
    ADET = 'ADET', 'ADET'
    KOLI = 'KOLİ', 'KOLİ'
    KG = 'KG', 'KG'
    GRAM = 'GRAM', 'GRAM'
    LITRE = 'LİTRE', 'LİTRE'
    ML = 'ML', 'ML'
    PAKET = 'PAKET', 'PAKET'
    SET = 'SET', 'SET'
    KUTU = 'KUTU', 'KUTU'


class SevkiyatForm(models.TextChoices):
    HAMMADDE = 'HAMMADDE', 'Hammadde'
    TEMIZLIK = 'TEMIZLIK', 'Temizlik'


class Urun(models.Model):
    """Sevkiyat ürün kataloğu (Excel'den 'katalog_yukle' ile yüklenir)."""
    form = models.CharField(max_length=10, choices=SevkiyatForm.choices,
                            default=SevkiyatForm.HAMMADDE, verbose_name="Form")
    kategori = models.CharField(max_length=80, verbose_name="Kategori")
    ad = models.CharField(max_length=160, verbose_name="Ürün Adı")
    koli_icerigi = models.PositiveIntegerField(default=1, verbose_name="İçerik (üst birimdeki taban birim adedi)")
    birim = models.CharField(max_length=10, choices=SevkiyatBirim.choices,
                             default=SevkiyatBirim.ADET, verbose_name="Taban Birim")
    ust_birim = models.CharField(max_length=10, choices=SevkiyatBirim.choices, blank=True,
                                 default=SevkiyatBirim.KOLI,
                                 verbose_name="Üst Birim (koli/paket/set; boş = yok)")
    sira = models.PositiveIntegerField(default=0, verbose_name="Sıra")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Ürün (Katalog)"
        verbose_name_plural = "Ürünler (Katalog)"
        ordering = ['form', 'sira', 'ad']

    def __str__(self):
        return f"{self.ad} ({self.birim})"


class SevkiyatDurumu(models.TextChoices):
    TALEP = 'Talep', 'Satın Almada'
    SEVKIYATTA = 'Sevkiyatta', 'Sevkiyatta'
    ONAY_BEKLIYOR = 'Onay Bekliyor', 'Çıkış Onayı Bekliyor'
    ONAYLANDI = 'Onaylandı', 'Onaylandı'
    REDDEDILDI = 'Reddedildi', 'Reddedildi (Düzeltmede)'
    TESLIM = 'Teslim Edildi', 'Teslim Edildi'


class SevkiyatTalep(models.Model):
    """Şube şefinin katalogdan oluşturduğu sipariş."""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='sevkiyat_talepleri', verbose_name="Şube")
    olusturan = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='sevkiyat_talepleri', verbose_name="Oluşturan")
    olusturan_ad = models.CharField(max_length=100, blank=True)
    durum = models.CharField(max_length=20, choices=SevkiyatDurumu.choices,
                             default=SevkiyatDurumu.TALEP, verbose_name="Durum")
    not_metni = models.CharField(max_length=400, blank=True, verbose_name="Şef Notu")
    red_notu = models.CharField(max_length=400, blank=True, default='', verbose_name="Red Açıklaması")
    satin_alan_ad = models.CharField(max_length=100, blank=True, default='')
    sevkiyatci_ad = models.CharField(max_length=100, blank=True, default='')
    onaylayan_ad = models.CharField(max_length=100, blank=True, default='')
    olusturma = models.DateTimeField(auto_now_add=True, verbose_name="Sipariş Tarihi")
    satin_alma_tarih = models.DateTimeField(null=True, blank=True)
    sevkiyat_tarih = models.DateTimeField(null=True, blank=True)
    onay_tarih = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Sevkiyat Siparişi"
        verbose_name_plural = "Sevkiyat Siparişleri"
        ordering = ['-olusturma']

    def __str__(self):
        return f"#{self.id} {self.sube} - {self.durum}"


class SevkiyatKalem(models.Model):
    """Siparişteki tek ürün satırı; her aşamada miktar/birim revize edilebilir."""
    talep = models.ForeignKey(SevkiyatTalep, on_delete=models.CASCADE, related_name='kalemler')
    urun = models.ForeignKey(Urun, on_delete=models.SET_NULL, null=True, blank=True)
    urun_ad = models.CharField(max_length=160, default='')
    kategori = models.CharField(max_length=80, blank=True, default='')
    form = models.CharField(max_length=10, blank=True, default='')
    koli_icerigi = models.PositiveIntegerField(default=1)
    # Şefin istediği
    istenen_miktar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    istenen_birim = models.CharField(max_length=10, default=SevkiyatBirim.ADET)
    # Satın almanın revizyonu
    satinalma_miktar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    satinalma_birim = models.CharField(max_length=10, blank=True, default='')
    # Sevkiyatın (stoğa göre) revizyonu
    sevkiyat_miktar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sevkiyat_birim = models.CharField(max_length=10, blank=True, default='')
    # Sevkiyat ekibinin hazırlık işareti (toplarken tik atılır → satır yeşile döner)
    hazirlandi = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.urun_ad} {self.istenen_miktar} {self.istenen_birim}"


class SiparisHareket(models.Model):
    """Sipariş hareket günlüğü (şef detaylı durum takibi için)."""
    talep = models.ForeignKey(SevkiyatTalep, on_delete=models.CASCADE, related_name='hareketler')
    mesaj = models.CharField(max_length=200)
    aciklama = models.CharField(max_length=400, blank=True)
    yapan_ad = models.CharField(max_length=100, blank=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['olusturma']

    def __str__(self):
        return f"#{self.talep_id} {self.mesaj}"


class KahveSoru(models.Model):
    """Günlük kahve kültürü soru bankası (4 şıklı)."""
    SIKLAR = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    kategori = models.CharField(max_length=40, blank=True)
    metin = models.TextField(verbose_name="Soru")
    sik_a = models.CharField(max_length=200)
    sik_b = models.CharField(max_length=200)
    sik_c = models.CharField(max_length=200)
    sik_d = models.CharField(max_length=200)
    dogru = models.CharField(max_length=1, choices=SIKLAR)
    aktif = models.BooleanField(default=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.metin[:60]

    def sik(self, harf):
        return {'A': self.sik_a, 'B': self.sik_b, 'C': self.sik_c, 'D': self.sik_d}.get(harf, '')

    @property
    def siklar(self):
        return [('A', self.sik_a), ('B', self.sik_b), ('C', self.sik_c), ('D', self.sik_d)]


class GunlukSoru(models.Model):
    """Bir kişiye belirli bir günde atanan soru ve verdiği cevap."""
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='gunluk_sorular')
    sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True)
    sube_ad = models.CharField(max_length=120, blank=True)  # şube anlık adı (snapshot)
    soru = models.ForeignKey(KahveSoru, on_delete=models.SET_NULL, null=True)
    tarih = models.DateField()
    baslangic = models.DateTimeField(null=True, blank=True)  # sorunun gösterildiği an (sayaç başı)
    secilen = models.CharField(max_length=1, blank=True)     # '' = boş bırakıldı
    dogru_mu = models.BooleanField(default=False)
    sure_doldu = models.BooleanField(default=False)
    cevaplandi = models.BooleanField(default=False)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tarih', 'personel']
        unique_together = ('personel', 'tarih')

    def __str__(self):
        return f"{self.personel_id} · {self.tarih}"


class SoruAyar(models.Model):
    """Günlük soru sisteminin genel açık/kapalı ayarı (tek satır)."""
    aktif = models.BooleanField(default=False, verbose_name="Günlük soru sistemi aktif")
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Soru Sistemi Ayarı"
        verbose_name_plural = "Soru Sistemi Ayarı"

    def __str__(self):
        return "Aktif" if self.aktif else "Pasif"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Bildirim(models.Model):
    """Uygulama içi bildirim. Bir olay olunca ilgili kişilere birer kayıt düşer."""
    alici = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='bildirimler')
    mesaj = models.CharField(max_length=200)
    link = models.CharField(max_length=200, blank=True, default='')
    tur = models.CharField(max_length=20, blank=True, default='')
    okundu = models.BooleanField(default=False)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-olusturma']
        indexes = [models.Index(fields=['alici', 'okundu'])]

    def __str__(self):
        return f'{self.alici_id}: {self.mesaj[:30]}'


class Duyuru(models.Model):
    """Yönetim duyurusu. Tüm şubelere veya seçili role/şubeye yayınlanır."""
    baslik = models.CharField(max_length=150)
    icerik = models.TextField()
    yayinlayan_ad = models.CharField(max_length=120, blank=True, default='')
    hedef_rol = models.CharField(max_length=20, blank=True, default='')   # '' = tüm roller
    hedef_sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    aktif = models.BooleanField(default=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-olusturma']

    def __str__(self):
        return self.baslik[:40]
