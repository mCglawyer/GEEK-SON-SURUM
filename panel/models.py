import secrets
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone

class Rol(models.TextChoices):
    GENEL_MUDUR = 'Genel Müdür', 'Genel Müdür (Tam Yetkili)'
    MUDUR = 'Müdür', 'Bölge Müdürü'
    MAGAZA_MUDURU = 'Mağaza Müdürü', 'Mağaza Müdürü'
    OPERATOR = 'Operatör', 'Operatör (Tam Yetkili)'
    YATIRIMCI = 'Yatırımcı', 'Yatırımcı (Tam Yetkili)'
    SATIN_ALMA = 'Satın Alma', 'Satın Alma'
    SEVKIYAT = 'Sevkiyat', 'Sevkiyat'
    EGITMEN = 'Eğitmen', 'Eğitmen'
    SEF = 'Şef', 'Şube Şefi'
    MUTFAK_SORUMLUSU = 'Mutfak Sorumlusu', 'Mutfak Sorumlusu'
    MUTFAK_PERSONEL = 'Mutfak Personeli', 'Mutfak Personeli'
    PERSONEL = 'Personel', 'Personel'

class VardiyaTipi(models.TextChoices):
    SABAHCI = 'Sabahçı', 'Sabahçı'
    ARACI = 'Aracı', 'Aracı'
    AKSAMCI = 'Akşamcı', 'Akşamcı'
    MUTFAK_GOREVI = 'Mutfak Görevi', 'Mutfak Görevi (Şube Ataması)'
    IZINLI = 'İzinli', 'Haftalık İzin'
    YILLIK_IZIN = 'Yıllık İzin', 'Yıllık İzin'
    RAPORLU = 'Raporlu', 'Raporlu'
    DEVAMSIZ = 'Devamsız', 'Devamsız'

class OnayDurumu(models.TextChoices):
    TASLAK = 'Taslak', 'Taslak'
    ONAY_BEKLIYOR = 'Onay Bekliyor', 'Onay Bekliyor'
    ONAYLANDI = 'Onaylandı', 'Onaylandı'
    REDDEDILDI = 'Reddedildi', 'Reddedildi'

YONETIM_ROLLERI = [Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SEF]

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
    dogum_tarihi = models.DateField(null=True, blank=True, verbose_name="Doğum Tarihi")
    cinsiyet = models.CharField(max_length=1, choices=[('E', 'Erkek'), ('K', 'Kadın')],
                                blank=True, default='', verbose_name="Cinsiyet")
    profil_foto = models.ImageField(upload_to='profil/', null=True, blank=True, verbose_name="Profil Fotoğrafı")

    class Meta:
        verbose_name = "Personel"; verbose_name_plural = "Personeller"; ordering = ['ad_soyad']

    def __str__(self):
        return f"{self.ad_soyad} ({self.sube.ad if self.sube else 'Şubesiz'})"

    @staticmethod
    def benzersiz_kod_uret():
        while True:
            kod = f"{secrets.randbelow(1_000_000):06d}"
            if not Personel.objects.filter(giris_kodu=kod).exists():
                return kod

    def kodu_yenile(self):
        self.giris_kodu = self.benzersiz_kod_uret()
        self.save(update_fields=['giris_kodu'])

    def save(self, *args, **kwargs):

        if not self.giris_kodu:
            self.giris_kodu = self.benzersiz_kod_uret()
        super().save(*args, **kwargs)

        if self.user_id is None and self.rol in (Rol.PERSONEL, Rol.SEF, Rol.MAGAZA_MUDURU, Rol.MUTFAK_PERSONEL, Rol.MUTFAK_SORUMLUSU):
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
    atanan_sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='mutfak_gorevleri',
                                    verbose_name="Atanan Şube (Mutfak Personeli)")

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
    personel = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True, related_name='puantajlar')
    personel_ad_soyad_arsiv = models.CharField(max_length=160, blank=True, default='', verbose_name="Personel (arşiv)")
    sube_arsiv = models.ForeignKey('Sube', on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name="Şube (arşiv)")
    ay = models.DateField(verbose_name="Puantaj Ayı")
    calisilan_gun = models.IntegerField(default=0, verbose_name="Çalışılan Gün")
    eksik_gun = models.IntegerField(default=0, verbose_name="Eksik Gün")
    izinli_gun = models.IntegerField(default=0, verbose_name="İzinli Gün")
    yillik_gun = models.IntegerField(default=0, verbose_name="Yıllık İzin Gün")
    raporlu_gun = models.IntegerField(default=0, verbose_name="Raporlu Gün")
    manuel_duzenlendi = models.BooleanField(default=False, verbose_name="Manuel Düzenlendi mi?")
    guncelleme = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = "Puantaj"; verbose_name_plural = "Puantajlar"; ordering = ['-ay']
        constraints = [models.UniqueConstraint(fields=['personel', 'ay'], name='unique_personel_ay_puantaj')]

    def __str__(self):
        return f"{self.personel.ad_soyad} - {self.ay.strftime('%m/%Y')}"

class KodKilit(models.Model):
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
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='zayiler', verbose_name="Şube")
    giren = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='zayi_girisleri', verbose_name="Giren Personel")
    giren_ad = models.CharField(max_length=100, blank=True, verbose_name="Giren (ad)")
    urun_adi = models.CharField(max_length=120, verbose_name="Ürün Adı")
    miktar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Miktar")
    birim = models.CharField(max_length=10, choices=Birim.choices, default=Birim.ADET, verbose_name="Birim")
    aciklama = models.CharField(max_length=300, blank=True, default='', verbose_name="Açıklama")
    foto = models.FileField(upload_to='zayi/%Y/%m/%d/', null=True, blank=True, verbose_name="Fotoğraf")
    olusturma = models.DateTimeField(auto_now_add=True, verbose_name="Girildiği An")

    class Meta:
        verbose_name = "Zayi"
        verbose_name_plural = "Zayiler"
        ordering = ['-olusturma']

    def __str__(self):
        return f"{self.urun_adi} - {self.miktar} {self.birim}"

class Kalibrasyon(models.Model):
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
    talep = models.ForeignKey(SevkiyatTalep, on_delete=models.CASCADE, related_name='kalemler')
    urun = models.ForeignKey(Urun, on_delete=models.SET_NULL, null=True, blank=True)
    urun_ad = models.CharField(max_length=160, default='')
    kategori = models.CharField(max_length=80, blank=True, default='')
    form = models.CharField(max_length=10, blank=True, default='')
    koli_icerigi = models.PositiveIntegerField(default=1)

    istenen_miktar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    istenen_birim = models.CharField(max_length=10, default=SevkiyatBirim.ADET)

    satinalma_miktar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    satinalma_birim = models.CharField(max_length=10, blank=True, default='')

    sevkiyat_miktar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sevkiyat_birim = models.CharField(max_length=10, blank=True, default='')

    hazirlandi = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.urun_ad} {self.istenen_miktar} {self.istenen_birim}"

class SiparisHareket(models.Model):
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
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='gunluk_sorular')
    sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True)
    sube_ad = models.CharField(max_length=120, blank=True)
    soru = models.ForeignKey(KahveSoru, on_delete=models.SET_NULL, null=True)
    tarih = models.DateField()
    baslangic = models.DateTimeField(null=True, blank=True)
    secilen = models.CharField(max_length=1, blank=True)
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
    baslik = models.CharField(max_length=150)
    icerik = models.TextField()
    yayinlayan_ad = models.CharField(max_length=120, blank=True, default='')
    hedef_rol = models.CharField(max_length=20, blank=True, default='')
    hedef_sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    aktif = models.BooleanField(default=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-olusturma']

    def __str__(self):
        return self.baslik[:40]


class GSosyalGonderi(models.Model):
    yazan = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='gsosyal_gonderiler')
    yazan_ad = models.CharField(max_length=120, default='')
    metin = models.TextField(blank=True, default='')
    gorsel = models.ImageField(upload_to='gsosyal/', null=True, blank=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-olusturma']

    def __str__(self):
        return '%s · %s' % (self.yazan_ad, self.metin[:30])


class GSosyalTepki(models.Model):
    gonderi = models.ForeignKey(GSosyalGonderi, on_delete=models.CASCADE, related_name='tepkiler')
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='gsosyal_tepkiler')
    emoji = models.CharField(max_length=8, default='👍')
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('gonderi', 'personel')


class EgitimDokuman(models.Model):
    KATEGORI = [('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon'), ('ICECEK', 'İçecek Hazırlama')]
    kategori = models.CharField(max_length=20, choices=KATEGORI, default='RECETE')
    baslik = models.CharField(max_length=160, default='')
    dosya = models.FileField(upload_to='egitim/')
    sube = models.ForeignKey(Sube, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='egitim_dokumanlari', verbose_name="Şube (boş=tüm şubeler)")
    olusturma = models.DateTimeField(auto_now_add=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ['kategori', '-olusturma']

    @property
    def is_video(self):
        ad = (self.dosya.name or '').lower()
        return ad.endswith(('.mp4', '.webm', '.mov', '.m4v', '.ogv'))


class EgitimSoru(models.Model):
    KATEGORI = [('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon')]
    kategori = models.CharField(max_length=20, choices=KATEGORI, default='RECETE')
    metin = models.TextField(default='')
    sik_a = models.CharField(max_length=300, default='')
    sik_b = models.CharField(max_length=300, default='')
    sik_c = models.CharField(max_length=300, default='', blank=True)
    sik_d = models.CharField(max_length=300, default='', blank=True)
    dogru = models.CharField(max_length=1, default='A')
    sube = models.ForeignKey(Sube, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='egitim_sorulari', verbose_name="Şube (boş=tüm şubeler)")
    aktif = models.BooleanField(default=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-olusturma']


class EgitimDurum(models.Model):
    personel = models.OneToOneField(Personel, on_delete=models.CASCADE, related_name='egitim_durum')
    tamamlandi = models.BooleanField(default=False)
    gecti = models.BooleanField(default=False)
    son_puan = models.IntegerField(default=0)
    deneme = models.IntegerField(default=0)
    son_sorular = models.TextField(default='', blank=True)
    son_cevaplar = models.TextField(default='', blank=True)
    sozlesme_onayli = models.BooleanField(default=False)
    tarih = models.DateTimeField(auto_now=True)


class EgitimAyar(models.Model):
    acik = models.BooleanField(default=False)
    acik_subeler = models.ManyToManyField(Sube, blank=True, related_name='egitim_acik')
    guncelleme = models.DateTimeField(auto_now=True)


class PushAbonelik(models.Model):
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='push_abonelikleri')
    endpoint = models.TextField(unique=True)
    veri = models.TextField()
    olusturma = models.DateTimeField(auto_now_add=True)


class MolaQRAyar(models.Model):
    acik = models.BooleanField(default=False)
    guncelleme = models.DateTimeField(auto_now=True)


class SubeMolaToken(models.Model):
    sube = models.OneToOneField(Sube, on_delete=models.CASCADE, related_name='mola_token')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    olusturma = models.DateTimeField(auto_now_add=True)


class MolaOturum(models.Model):
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='mola_oturumlari')
    sube = models.ForeignKey(Sube, null=True, blank=True, on_delete=models.SET_NULL, related_name='mola_oturumlari')
    sure_dk = models.IntegerField(default=45)
    baslangic = models.DateTimeField()
    bitis = models.DateTimeField(null=True, blank=True)
    kullanilan_dk = models.IntegerField(null=True, blank=True, verbose_name="Kullanılan Süre (dk)")
    uyarildi = models.BooleanField(default=False)

    class Meta:
        ordering = ['-baslangic']


class InsaatProje(models.Model):
    ad = models.CharField(max_length=160, verbose_name="Yeni Şube / Proje Adı")
    sorumlu = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='insaat_projeleri', verbose_name="Sorumlu Bölge Müdürü")
    olusturan = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='olusturdugu_insaat')
    tamamlandi = models.BooleanField(default=False, verbose_name="Proje Tamamlandı")
    olusturma = models.DateTimeField(auto_now_add=True)
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-olusturma']

    def __str__(self):
        return self.ad


class InsaatMaddeDurum(models.TextChoices):
    YAPILMADI = 'yapilmadi', 'Yapılmadı'
    DEVAM = 'devam', 'Devam Ediyor'
    TAMAM = 'tamam', 'Tamamlandı'


class InsaatKategori(models.TextChoices):
    URUN = 'urun', 'Ürün ve Ekipman'
    SUREC = 'insaat', 'İnşaat Süreci'


class InsaatMadde(models.Model):
    proje = models.ForeignKey(InsaatProje, on_delete=models.CASCADE, related_name='maddeler')
    kategori = models.CharField(max_length=12, choices=InsaatKategori.choices,
                                default=InsaatKategori.URUN, verbose_name="Kategori")
    metin = models.CharField(max_length=300, verbose_name="Görev")
    durum = models.CharField(max_length=12, choices=InsaatMaddeDurum.choices,
                             default=InsaatMaddeDurum.YAPILMADI)
    aciklama = models.TextField(blank=True, default='', verbose_name="Not")
    sira = models.IntegerField(default=0)
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sira', 'id']

    def __str__(self):
        return self.metin


class InsaatSablonMadde(models.Model):
    """Yeni projelere otomatik eklenecek varsayılan denetim maddeleri."""
    kategori = models.CharField(max_length=12, choices=InsaatKategori.choices,
                                default=InsaatKategori.URUN, verbose_name="Kategori")
    metin = models.CharField(max_length=300, verbose_name="Görev")
    sira = models.IntegerField(default=0)

    class Meta:
        ordering = ['kategori', 'sira', 'id']

    def __str__(self):
        return self.metin


@receiver(pre_delete, sender=Personel)
def _personel_silinmeden_once_puantaj_arsivle(sender, instance, **kwargs):
    """Personel silindiğinde: geçmiş manuel puantaj kayıtları korunur (ad/şube arşive kopyalanır)
    ve ayrıldığı ayın puantajı, o ana kadarki fiili vardiyalarından hesaplanıp donuk olarak kaydedilir."""
    Puantaj.objects.filter(personel=instance).update(
        personel_ad_soyad_arsiv=instance.ad_soyad, sube_arsiv=instance.sube_id)
    MesaiKayit.objects.filter(personel=instance).update(personel_ad_arsiv=instance.ad_soyad)
    MutfakZayi.objects.filter(personel=instance).update(personel_ad_arsiv=instance.ad_soyad)

    bugun = timezone.localdate()
    ay_ilk = bugun.replace(day=1)
    if bugun.month == 12:
        ay_son = bugun.replace(year=bugun.year + 1, month=1, day=1)
    else:
        ay_son = bugun.replace(month=bugun.month + 1, day=1)

    mevcut = Puantaj.objects.filter(personel=instance, ay=ay_ilk).first()
    if mevcut and mevcut.manuel_duzenlendi:
        mevcut.personel_ad_soyad_arsiv = instance.ad_soyad
        mevcut.sube_arsiv = instance.sube
        mevcut.save(update_fields=['personel_ad_soyad_arsiv', 'sube_arsiv'])
        return

    s = instance.vardiyalar.filter(tarih__gte=ay_ilk, tarih__lt=ay_son).exclude(durum=OnayDurumu.REDDEDILDI)
    snapshot, _ = Puantaj.objects.update_or_create(
        personel=instance, ay=ay_ilk,
        defaults={
            'calisilan_gun': s.filter(vardiya_tipi__in=[VardiyaTipi.SABAHCI, VardiyaTipi.ARACI, VardiyaTipi.AKSAMCI, VardiyaTipi.MUTFAK_GOREVI]).count(),
            'eksik_gun': s.filter(vardiya_tipi=VardiyaTipi.DEVAMSIZ).count(),
            'izinli_gun': s.filter(vardiya_tipi=VardiyaTipi.IZINLI).count(),
            'yillik_gun': s.filter(vardiya_tipi=VardiyaTipi.YILLIK_IZIN).count(),
            'raporlu_gun': s.filter(vardiya_tipi=VardiyaTipi.RAPORLU).count(),
            'manuel_duzenlendi': True,
            'personel_ad_soyad_arsiv': instance.ad_soyad,
            'sube_arsiv': instance.sube,
        })
    # Bu satır Django'nun silme koleksiyonundan SONRA oluşturuldu; SET_NULL cascade'i
    # otomatik uygulanmaz. Bütünlük hatasını önlemek için FK'yi burada elle boşaltıyoruz.
    snapshot.personel = None
    snapshot.save(update_fields=['personel'])


class LavaboDenetim(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='lavabo_denetimleri', verbose_name="Şube")
    giren = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='lavabo_denetimleri', verbose_name="Yükleyen")
    giren_ad = models.CharField(max_length=100, blank=True, verbose_name="Yükleyen (ad)")
    foto = models.FileField(upload_to='lavabo/%Y/%m/%d/', verbose_name="Görüntü")
    olusturma = models.DateTimeField(auto_now_add=True, verbose_name="Yüklendiği An")

    class Meta:
        verbose_name = "Lavabo Denetimi"
        verbose_name_plural = "Lavabo Denetimleri"
        ordering = ['-olusturma']

    def __str__(self):
        return f"{self.sube} - {self.giren_ad} - {self.olusturma:%d.%m.%Y %H:%M}"


class DogumGunuKutlama(models.Model):
    """Aynı gün birden fazla kutlama paylaşımı atılmasını önlemek için."""
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='dogum_kutlamalari')
    tarih = models.DateField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['personel', 'tarih'], name='unique_dogum_kutlama')]


class SubeMesaiToken(models.Model):
    sube = models.OneToOneField(Sube, on_delete=models.CASCADE, related_name='mesai_token')
    token = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return f"Mesai QR - {self.sube}"


class MesaiKayit(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='mesai_kayitlari')
    personel = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='mesai_kayitlari')
    personel_ad_arsiv = models.CharField(max_length=160, blank=True, default='')
    giris = models.DateTimeField()
    cikis = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-giris']

    def __str__(self):
        return f"{self.sube} - {self.personel_ad_arsiv or (self.personel.ad_soyad if self.personel else '')}"


class MutfakZayi(models.Model):
    """Mutfak personelinin canlı kamerayla yüklediği zayi (fire) kaydı."""
    personel = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='mutfak_zayileri', verbose_name="Yükleyen")
    personel_ad_arsiv = models.CharField(max_length=160, blank=True, default='')
    sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='mutfak_zayileri', verbose_name="Şube")
    foto = models.FileField(upload_to='mutfak_zayi/%Y/%m/%d/', verbose_name="Görüntü")
    aciklama = models.TextField(blank=True, default='', verbose_name="Açıklama")
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mutfak Zayi"; verbose_name_plural = "Mutfak Zayileri"
        ordering = ['-olusturma']

    def __str__(self):
        return f"{self.sube} - {self.personel_ad_arsiv} - {self.olusturma:%d.%m.%Y %H:%M}"


class MutfakMaliyetKalemi(models.Model):
    """Kg başına fiyatı tanımlı ham madde (domates, biber vb.)."""
    ad = models.CharField(max_length=120, unique=True, verbose_name="Ürün Adı")
    kg_fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Kg Fiyatı (₺)")
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Maliyet Kalemi"; verbose_name_plural = "Maliyet Kalemleri"; ordering = ['ad']

    def __str__(self):
        return f"{self.ad} ({self.kg_fiyat} ₺/kg)"


class MutfakTarif(models.Model):
    """Bir yemeğin/tarifin maliyet hesaplaması."""
    ad = models.CharField(max_length=160, verbose_name="Tarif / Ürün Adı")
    olusturan = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='mutfak_tarifleri')
    olusturma = models.DateTimeField(auto_now_add=True)
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tarif"; verbose_name_plural = "Tarifler"; ordering = ['ad']

    def __str__(self):
        return self.ad

    @property
    def toplam_maliyet(self):
        toplam = 0
        for k in self.kalemler.select_related('urun').all():
            toplam += float(k.urun.kg_fiyat) * (float(k.miktar_gram) / 1000.0)
        return round(toplam, 2)


class MutfakTarifKalemi(models.Model):
    tarif = models.ForeignKey(MutfakTarif, on_delete=models.CASCADE, related_name='kalemler')
    urun = models.ForeignKey(MutfakMaliyetKalemi, on_delete=models.CASCADE, related_name='+')
    miktar_gram = models.DecimalField(max_digits=10, decimal_places=1, verbose_name="Miktar (gram)")

    class Meta:
        verbose_name = "Tarif Kalemi"; verbose_name_plural = "Tarif Kalemleri"

    @property
    def maliyet(self):
        return round(float(self.urun.kg_fiyat) * (float(self.miktar_gram) / 1000.0), 2)

    def __str__(self):
        return f"{self.tarif.ad} - {self.urun.ad} ({self.miktar_gram} g)"
