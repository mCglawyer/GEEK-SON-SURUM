import secrets
import unicodedata
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
    mutfak_var = models.BooleanField(
        default=False, verbose_name="Mutfağı var",
        help_text="İşaretliyse bu şubede mutfak zayi kaydı tutulur ve mutfak zayi sayfası bu şube için açılır.")
    google_yorum_url = models.URLField(
        max_length=500, blank=True, default='', verbose_name="Google yorum bağlantısı",
        help_text="Müşteri değerlendirmesinde 8 ve üzeri puan verenler bu adrese yönlendirilir.")
    FIYAT_GRUBU = [('MERKEZ', 'Merkez şube'), ('FRANCHISE', 'Franchise şube')]
    fiyat_grubu = models.CharField(
        max_length=10, choices=FIYAT_GRUBU, default='MERKEZ', verbose_name="Fiyat grubu",
        help_text="Tüketim & maliyet hesabında ürün fiyatı bu gruba göre seçilir.")

    menulux_id = models.PositiveIntegerField(
        null=True, blank=True, unique=True, verbose_name="Menulux şube no",
        help_text="Menulux portalındaki şube (CustomerID) numarası. Satış raporlarında yetki kapsamı için kullanılır.")

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
    manuel_giris_yetkisi = models.BooleanField(
        default=False, verbose_name="Manuel Mola/Mesai Girişi Yetkisi",
        help_text="İşaretliyse: Şef/Mağaza Müdürü rolündeyse kendi şubesindeki personel için, "
                  "diğer rollerde ise kendi adına, kamera QR olmadan manuel mola/mesai başlatıp bitirebilir.")
    geri_bildirim_yetkilisi = models.BooleanField(
        default=False, verbose_name="Geri Bildirim Görüntüleme Yetkisi",
        help_text="İşaretliyse (genelde tek bir Bölge Müdürü için kullanılır): Genel Müdür/Operatör "
                  "dışında bu kişi de Geri Bildirim Yönetimi sayfasına erişebilir.")

    menu_yetkilisi = models.BooleanField(
        default=False, verbose_name="QR Menü Yönetimi Yetkisi",
        help_text="İşaretliyse (genelde Bölge Müdürü için): Genel Müdür/Operatör/Yatırımcı dışında bu kişi de "
                  "QR Menü Yönetimi sayfalarına erişebilir. Ekip sayfasından verilir/alınır.")

    denetim_goruntuleyici = models.BooleanField(
        default=False, verbose_name="Denetim Sonuçlarını Görüntüleme Yetkisi",
        help_text="İşaretliyse (Bölge Müdürü için): sorumlu olduğu şubelerin tamamlanmış denetim sonuçlarını ve PDF "
                  "raporlarını görür. Ekip sayfasından verilir/alınır.")

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
        ad = self.personel.ad_soyad if self.personel else (self.personel_ad_soyad_arsiv or 'Ayrılan Personel')
        return f"{ad} - {self.ay.strftime('%m/%Y')}"

class KodKilit(models.Model):
    ip = models.CharField(max_length=45, unique=True, verbose_name="IP Adresi")
    hatali_deneme = models.IntegerField(default=0)
    kilit_bitis = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Kod Giriş Kilidi"; verbose_name_plural = "Kod Giriş Kilitleri"

    def __str__(self):
        return f"{self.ip} ({self.hatali_deneme} hatalı)"

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
    # Tüketim & maliyet: bu sayım kaleminin sevkiyat kataloğundaki karşılığı. Gelen mal buradan sayıma çevrilir.
    sevkiyat_urun = models.ForeignKey('Urun', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                                      verbose_name="Sevkiyat kataloğundaki karşılığı")
    sevkiyat_carpan = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True, verbose_name="Sevkiyat birimi → sayım birimi",
        help_text="Sevkiyat kataloğundaki 1 taban birim (1 adet/şişe/paket) sayımda kaç birim eder? Boşsa 'kapalı kutu içeriği' kullanılır.")
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


class GSosyalGorsel(models.Model):
    """Bir Geek Crew paylaşımına ait, ızgara (grid) halinde gösterilen birden
    fazla görselden biri. Eski paylaşımlar tekil `GSosyalGonderi.gorsel`
    alanını kullanmayı sürdürür; yeni paylaşımlar bu tabloya (en fazla 4
    adet) kaydedilir."""
    gonderi = models.ForeignKey(GSosyalGonderi, on_delete=models.CASCADE, related_name='gorseller')
    gorsel = models.ImageField(upload_to='gsosyal/')
    sira = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sira', 'id']


class GSosyalTepki(models.Model):
    gonderi = models.ForeignKey(GSosyalGonderi, on_delete=models.CASCADE, related_name='tepkiler')
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='gsosyal_tepkiler')
    emoji = models.CharField(max_length=8, default='👍')
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('gonderi', 'personel')


class EgitimDokuman(models.Model):
    KATEGORI = [('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon'), ('ICECEK', 'İçecek Hazırlama'),
                ('TARIHCE', 'Geek Tarihçesi'), ('HIJYEN', 'Hijyen/Temizlik Standartları'),
                ('SERVIS', 'Müşteri İlişkileri/Servis Eğitimi')]
    kategori = models.CharField(max_length=20, choices=KATEGORI, default='RECETE')
    baslik = models.CharField(max_length=160, default='')
    dosya = models.FileField(upload_to='egitim/')
    sube = models.ForeignKey(Sube, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='egitim_dokumanlari', verbose_name="Şube (boş=tüm şubeler)")
    olusturma = models.DateTimeField(auto_now_add=True)
    aktif = models.BooleanField(default=True)
    kapak = models.ImageField(upload_to='egitim/kapak/', null=True, blank=True, verbose_name="Video Kapak Resmi")

    class Meta:
        ordering = ['kategori', '-olusturma']

    @property
    def is_video(self):
        ad = (self.dosya.name or '').lower()
        return ad.endswith(('.mp4', '.webm', '.mov', '.m4v', '.ogv'))


class EgitimFavori(models.Model):
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='egitim_favorileri')
    dokuman = models.ForeignKey(EgitimDokuman, on_delete=models.CASCADE, related_name='favorileyenler')
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('personel', 'dokuman')]
        verbose_name = "Academy Favorisi"
        verbose_name_plural = "Academy Favorileri"

    def __str__(self):
        return '%s → %s' % (self.personel.ad_soyad, self.dokuman.baslik)


class EgitimSoru(models.Model):
    KATEGORI = [('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon')]
    TUR = [('coktan_secmeli', 'Çoktan Seçmeli'), ('acik_uclu', 'Açık Uçlu (Yazılı Cevap)')]
    kategori = models.CharField(max_length=20, choices=KATEGORI, default='RECETE')
    tur = models.CharField(max_length=20, choices=TUR, default='coktan_secmeli', verbose_name="Soru Türü")
    metin = models.TextField(default='')
    sik_a = models.CharField(max_length=300, default='', blank=True)
    sik_b = models.CharField(max_length=300, default='', blank=True)
    sik_c = models.CharField(max_length=300, default='', blank=True)
    sik_d = models.CharField(max_length=300, default='', blank=True)
    dogru = models.CharField(max_length=1, default='A', blank=True)
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
    inceleme_bekliyor = models.BooleanField(default=False, verbose_name="Yazılı sorular inceleme bekliyor")
    son_puan = models.IntegerField(default=0)
    deneme = models.IntegerField(default=0)
    son_sorular = models.TextField(default='', blank=True)
    son_cevaplar = models.TextField(default='', blank=True)
    sozlesme_onayli = models.BooleanField(default=False)
    tarih = models.DateTimeField(auto_now=True)


class EgitimAcikCevap(models.Model):
    """Açık uçlu (yazılı) sorulara verilen cevaplar ve eğitmen/operatör puanlaması."""
    personel = models.ForeignKey(Personel, on_delete=models.CASCADE, related_name='egitim_acik_cevaplari')
    soru = models.ForeignKey(EgitimSoru, on_delete=models.CASCADE, related_name='+')
    deneme_no = models.IntegerField(default=1)
    cevap_metni = models.TextField(default='', blank=True)
    puanlandi = models.BooleanField(default=False)
    dogru_mu = models.BooleanField(null=True, blank=True)
    puanlayan = models.ForeignKey(Personel, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    puanlama_notu = models.CharField(max_length=300, default='', blank=True)
    olusturma = models.DateTimeField(auto_now_add=True)
    puanlama_tarihi = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-olusturma']
        verbose_name = "Açık Uçlu Cevap"; verbose_name_plural = "Açık Uçlu Cevaplar"

    def __str__(self):
        return f"{self.personel.ad_soyad} - {self.soru_id} (deneme {self.deneme_no})"


class EgitimAyar(models.Model):
    acik = models.BooleanField(default=False)
    acik_subeler = models.ManyToManyField(Sube, blank=True, related_name='egitim_acik')
    soru_sayisi = models.PositiveIntegerField(default=10, verbose_name="Soru Sayısı")
    sure_sn = models.PositiveIntegerField(default=20, verbose_name="Soru Başına Süre (sn)")
    gecme_puan = models.PositiveIntegerField(default=6, verbose_name="Geçme İçin Gereken Doğru Sayısı")
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
    # QR okutulduğu an mola başlar; 15/45 seçimi sonradan yapılabilir. Seçilmezse 45 dk geçerlidir.
    sure_secildi = models.BooleanField(default=True)
    baslangic = models.DateTimeField()
    bitis = models.DateTimeField(null=True, blank=True)
    kullanilan_dk = models.IntegerField(null=True, blank=True, verbose_name="Kullanılan Süre (dk)")
    uyarildi = models.BooleanField(default=False)
    manuel_mi = models.BooleanField(default=False, verbose_name="Manuel Girildi")
    manuel_giren = models.ForeignKey(Personel, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='+', verbose_name="Manuel Girişi Yapan")
    manuel_not = models.CharField(max_length=200, blank=True, default='')

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
    ve ayrıldığı ayın puantajı, o ana kadarki fiili vardiyalarından hesaplanıp donuk olarak kaydedilir.
    Bu işlem yalnızca bir arşivleme/kayıt kolaylığıdır; herhangi bir sebeple hata verirse
    personelin silinmesini ENGELLEMEMELİDİR, bu yüzden tamamı korumalı çalıştırılır."""
    try:
        Puantaj.objects.filter(personel=instance).update(
            personel_ad_soyad_arsiv=instance.ad_soyad, sube_arsiv=instance.sube_id)
    except Exception:
        pass
    try:
        MesaiKayit.objects.filter(personel=instance).update(personel_ad_arsiv=instance.ad_soyad)
    except Exception:
        pass
    try:
        MutfakZayi.objects.filter(personel=instance).update(personel_ad_arsiv=instance.ad_soyad)
    except Exception:
        pass

    try:
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
    except Exception:
        pass


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
    manuel_mi = models.BooleanField(default=False, verbose_name="Manuel Girildi")
    manuel_giren = models.ForeignKey(Personel, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='+', verbose_name="Manuel Girişi Yapan")
    manuel_not = models.CharField(max_length=200, blank=True, default='')

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


class MaliyetBirim(models.TextChoices):
    KG = 'kg', 'Kg (gram bazlı)'
    LITRE = 'litre', 'Litre (ml bazlı)'
    ADET = 'adet', 'Adet (tam sayı)'


class MutfakMaliyetKalemi(models.Model):
    """Fiyatı tanımlı ham madde (domates, biber, süt, kase vb.)."""
    ad = models.CharField(max_length=120, unique=True, verbose_name="Ürün Adı")
    birim = models.CharField(max_length=10, choices=MaliyetBirim.choices, default=MaliyetBirim.KG,
                             verbose_name="Birim")
    fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Birim Fiyatı (₺)",
                                help_text="Kg için ₺/kg, Litre için ₺/litre, Adet için ₺/adet.")
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Maliyet Kalemi"; verbose_name_plural = "Maliyet Kalemleri"; ordering = ['ad']

    def __str__(self):
        return f"{self.ad} ({self.fiyat} ₺/{self.birim})"


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
            toplam += k.maliyet
        return round(toplam, 2)


class MutfakTarifKalemi(models.Model):
    tarif = models.ForeignKey(MutfakTarif, on_delete=models.CASCADE, related_name='kalemler')
    urun = models.ForeignKey(MutfakMaliyetKalemi, on_delete=models.CASCADE, related_name='+')
    miktar = models.DecimalField(max_digits=10, decimal_places=1, verbose_name="Miktar",
                                 help_text="Kg için gram, Litre için ml, Adet için tam sayı girin.")

    class Meta:
        verbose_name = "Tarif Kalemi"; verbose_name_plural = "Tarif Kalemleri"

    @property
    def maliyet(self):
        fiyat = float(self.urun.fiyat)
        miktar = float(self.miktar)
        if self.urun.birim == MaliyetBirim.ADET:
            return round(fiyat * miktar, 2)
        # KG ve LITRE için miktar küçük birimde (gram / ml) girilir, 1000'e bölünür.
        return round(fiyat * (miktar / 1000.0), 2)

    @property
    def miktar_etiketi(self):
        if self.urun.birim == MaliyetBirim.KG:
            return "g"
        if self.urun.birim == MaliyetBirim.LITRE:
            return "ml"
        return "adet"

    def __str__(self):
        return f"{self.tarif.ad} - {self.urun.ad} ({self.miktar} {self.miktar_etiketi})"


class DenetimBolum(models.Model):
    """Şube denetim formunun bir bölümü (ör. 'A. Genel Dış Görünüş')."""
    ad = models.CharField(max_length=200)
    sira = models.PositiveIntegerField(default=0)
    aktif = models.BooleanField(default=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sira', 'id']
        verbose_name = "Denetim Bölümü"
        verbose_name_plural = "Denetim Bölümleri"

    def __str__(self):
        return self.ad


class DenetimMadde(models.Model):
    """Bir bölüme ait tek bir denetim maddesi (0-5 puanlanır)."""
    bolum = models.ForeignKey(DenetimBolum, on_delete=models.CASCADE, related_name='maddeler')
    metin = models.CharField(max_length=500)
    sira = models.PositiveIntegerField(default=0)
    aktif = models.BooleanField(default=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sira', 'id']
        verbose_name = "Denetim Maddesi"
        verbose_name_plural = "Denetim Maddeleri"

    def __str__(self):
        return f"{self.bolum.ad} — {self.metin[:60]}"


class Denetim(models.Model):
    """Bir şubede yapılan tek bir denetim oturumu."""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='denetimler')
    denetleyen = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    baslangic = models.DateTimeField(auto_now_add=True)
    bitis = models.DateTimeField(null=True, blank=True)
    tamamlandi = models.BooleanField(default=False)
    toplam_puan = models.FloatField(null=True, blank=True, verbose_name="Toplam Puan (yüzde)")

    class Meta:
        ordering = ['-baslangic']
        verbose_name = "Şube Denetimi"
        verbose_name_plural = "Şube Denetimleri"

    def __str__(self):
        return f"{self.sube.ad} - {self.baslangic:%d.%m.%Y}"


class DenetimCevap(models.Model):
    """Bir denetimdeki tek bir maddeye verilen cevap (0-5 puan + not + isteğe bağlı fotoğraf)."""
    denetim = models.ForeignKey(Denetim, on_delete=models.CASCADE, related_name='cevaplar')
    madde = models.ForeignKey(DenetimMadde, on_delete=models.CASCADE, related_name='+')
    puan = models.IntegerField(null=True, blank=True)
    not_metni = models.CharField(max_length=500, default='', blank=True)
    foto = models.ImageField(upload_to='denetim/fotolar/', null=True, blank=True)

    class Meta:
        ordering = ['id']
        verbose_name = "Denetim Cevabı"
        verbose_name_plural = "Denetim Cevapları"

    def __str__(self):
        return f"Denetim #{self.denetim_id} — {self.madde_id}"

    def tum_fotolar(self):
        """Eski tek fotoğraf alanı + sonradan eklenen çoklu fotoğraflar (ImageFieldFile listesi)."""
        liste = [self.foto] if self.foto else []
        liste += [f.foto for f in self.fotolar.all() if f.foto]
        return liste


class DenetimFoto(models.Model):
    """Bir denetim maddesine eklenen ek fotoğraf (madde başına birden çok)."""
    cevap = models.ForeignKey(DenetimCevap, on_delete=models.CASCADE, related_name='fotolar')
    foto = models.ImageField(upload_to='denetim/fotolar/')
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        verbose_name = "Denetim Fotoğrafı"
        verbose_name_plural = "Denetim Fotoğrafları"


class IlginHaber(models.Model):
    """Geek Crew sayfasındaki 'ironik/ilginç haber' slider'ı için, RSS
    kaynaklarından otomatik çekilen ama yönetim onayından geçmeden slider'da
    görünmeyen haber adayları."""
    baslik = models.CharField(max_length=300, default='')
    link = models.URLField(max_length=500, blank=True, default='')
    kaynak = models.CharField(max_length=120, blank=True, default='')
    olusturma = models.DateTimeField(auto_now_add=True)
    onaylandi = models.BooleanField(default=False)
    sektor_ilgili = models.BooleanField(default=False, verbose_name="Gıda/Kahve Sektörüyle İlgili")
    onaylayan = models.ForeignKey(Personel, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    onay_tarihi = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-olusturma']
        verbose_name = "İlginç Haber"
        verbose_name_plural = "İlginç Haberler"

    def __str__(self):
        return self.baslik[:60]


class GeriBildirimKategori(models.TextChoices):
    ONERI = 'Öneri', 'Öneri'
    SIKAYET = 'Şikayet', 'Şikayet'
    DIGER = 'Diğer', 'Diğer'


class GeriBildirimDurum(models.TextChoices):
    YENI = 'Yeni', 'Yeni'
    INCELENIYOR = 'İnceleniyor', 'İnceleniyor'
    COZULDU = 'Çözüldü', 'Çözüldü'


class GeriBildirim(models.Model):
    """Personelin isim vermeden ilettiği öneri/şikayet. BİLEREK hiçbir kimlik
    alanı (personel FK, IP, vb.) tutulmaz — anonimliği koruma amacı budur.
    Hangi şubeyle ilgili olduğu, kişinin kendi seçtiği (isteğe bağlı) bir
    alandır; sistem tarafından otomatik doldurulmaz."""
    kategori = models.CharField(max_length=20, choices=GeriBildirimKategori.choices,
                                default=GeriBildirimKategori.ONERI)
    metin = models.TextField(default='')
    sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    olusturma = models.DateTimeField(auto_now_add=True)
    durum = models.CharField(max_length=20, choices=GeriBildirimDurum.choices,
                             default=GeriBildirimDurum.YENI)
    yonetim_notu = models.TextField(default='', blank=True)

    class Meta:
        ordering = ['-olusturma']
        verbose_name = "Geri Bildirim"
        verbose_name_plural = "Geri Bildirimler"

    def __str__(self):
        return '%s · %s' % (self.kategori, self.metin[:40])


class SubeDegerlendirmeToken(models.Model):
    """Bir şubenin, masalara/girişe konacak müşteri değerlendirme QR'ının
    linkindeki gizli anahtarı. Personel QR'larından farklı olarak süresiz
    ve tekrar tekrar kullanılabilir — dilenirse yönetim ekranından
    yenilenip eski QR geçersiz kılınabilir."""
    sube = models.OneToOneField(Sube, on_delete=models.CASCADE, related_name='degerlendirme_token')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Değerlendirme QR - %s" % self.sube


class MusteriDegerlendirme(models.Model):
    """Müşterinin QR okutup doldurduğu, isim istenmeyen (anonim) şube
    değerlendirmesi."""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='degerlendirmeler', verbose_name="Şube")
    uc_kelime = models.CharField(max_length=200, blank=True, default='', verbose_name="Üç Kelime")
    ilk_izlenim = models.CharField(max_length=300, blank=True, default='', verbose_name="İlk İzlenim")
    favori_gorsel = models.CharField(max_length=300, blank=True, default='', verbose_name="Favori Görsel")
    favori_lezzet = models.CharField(max_length=300, blank=True, default='', verbose_name="Favori Lezzet")
    servis = models.CharField(max_length=300, blank=True, default='', verbose_name="Servis")
    atmosfer = models.CharField(max_length=300, blank=True, default='', verbose_name="Atmosfer")
    deger_mi = models.CharField(max_length=300, blank=True, default='', verbose_name="Değer mi?")
    bir_sey_degisse = models.CharField(max_length=300, blank=True, default='', verbose_name="Bir Şey Değişse")
    tekrar = models.CharField(max_length=300, blank=True, default='', verbose_name="Tekrar Gelir mi?")
    puan = models.PositiveSmallIntegerField(default=0, verbose_name="Puan (/10)")
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-olusturma']
        verbose_name = "Müşteri Değerlendirmesi"
        verbose_name_plural = "Müşteri Değerlendirmeleri"

    def __str__(self):
        return '%s — %s/10 (%s)' % (self.sube, self.puan, self.olusturma.strftime('%d.%m.%Y'))


# ------------------------------------------------------------------
# QR Menü Yönetimi (Geek + Baga)
# CSV sütunları ve marka şemaları için bkz. panel/menu_sema.py
# ------------------------------------------------------------------
class MenuMarka(models.Model):
    """Yalnızca iki marka vardır: Geek ve Baga (migration ile oluşturulur)."""
    kod = models.SlugField(max_length=20, unique=True, verbose_name="Kod")
    ad = models.CharField(max_length=80, verbose_name="Marka Adı")
    sira = models.PositiveIntegerField(default=0)
    son_yayin = models.DateTimeField(null=True, blank=True, verbose_name="Son Başarılı CSV Yayını")
    son_yayin_hata = models.CharField(max_length=400, blank=True, default='', verbose_name="Son Yayın Hatası")
    # QR sitesi açılış (kampanya) görseli ayarları — görseller MenuAcilisGorsel'de
    acilis_aktif = models.BooleanField(default=True, verbose_name="Açılış görseli gösterilsin")
    acilis_sure_sn = models.PositiveSmallIntegerField(default=5, verbose_name="Her görsel kaç saniye görünsün")
    acilis_atlanabilir = models.BooleanField(default=True, verbose_name="Dokununca geçilebilsin")
    acilis_gunde_bir = models.BooleanField(default=False, verbose_name="Aynı müşteriye günde bir kez göster")
    acilis_son_yayin = models.DateTimeField(null=True, blank=True, verbose_name="Açılış Görseli Son Yayın")
    acilis_yayin_hata = models.CharField(max_length=400, blank=True, default='', verbose_name="Açılış Yayın Hatası")

    class Meta:
        ordering = ['sira', 'id']
        verbose_name = "Menü Markası"
        verbose_name_plural = "Menü Markaları"

    def __str__(self):
        return self.ad


class MenuAcilisGorsel(models.Model):
    """QR sitesi açılırken gösterilen kampanya/karşılama görselleri (sırayla, her biri marka süresi kadar)."""
    marka = models.ForeignKey(MenuMarka, on_delete=models.CASCADE, related_name='acilis_gorselleri')
    gorsel = models.ImageField(upload_to='menu/acilis/', verbose_name="Görsel")
    baslik = models.CharField(max_length=80, blank=True, default='', verbose_name="Ad (yalnızca panelde görünür)")
    aktif = models.BooleanField(default=True, verbose_name="Yayında")
    baslangic = models.DateField(null=True, blank=True, verbose_name="Başlangıç tarihi")
    bitis = models.DateField(null=True, blank=True, verbose_name="Bitiş tarihi")
    sira = models.PositiveIntegerField(default=0)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sira', 'id']
        verbose_name = "QR Açılış Görseli"
        verbose_name_plural = "QR Açılış Görselleri"

    def __str__(self):
        return "%s — %s" % (self.marka.ad, self.baslik or self.gorsel.name)

    def url(self):
        try:
            return self.gorsel.url
        except Exception:
            return ''


class MenuKategori(models.Model):
    """Kategori KODU QR sitesinde sabittir (değişmez); görünen ad değişebilir."""
    marka = models.ForeignKey(MenuMarka, on_delete=models.CASCADE, related_name='kategoriler')
    kod = models.SlugField(max_length=40, verbose_name="Kategori Kodu")
    ad = models.CharField(max_length=80, verbose_name="Ad (TR)")
    ad_en = models.CharField(max_length=80, blank=True, default='', verbose_name="Ad (EN)")
    sira = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sira', 'id']
        unique_together = [('marka', 'kod')]
        verbose_name = "Menü Kategorisi"
        verbose_name_plural = "Menü Kategorileri"

    def __str__(self):
        return "%s / %s" % (self.marka.ad, self.ad)


class MenuAlerjen(models.Model):
    """Markanın alerjen listesi. sistem=True: QR sitesinin CSV'de sütun olarak okuduğu alerjenler
    (silinemez, yalnızca menüden kaldırılabilir/geri alınabilir). sistem=False: panelden eklenenler
    (CSV'nin son sütunlarında gider)."""
    marka = models.ForeignKey(MenuMarka, on_delete=models.CASCADE, related_name='alerjenler')
    kod = models.SlugField(max_length=40)
    ad = models.CharField(max_length=60, verbose_name="Ad (TR)")
    ad_en = models.CharField(max_length=60, blank=True, default='', verbose_name="Ad (EN)")
    aktif = models.BooleanField(default=True, verbose_name="Menüde kullanılıyor")
    sistem = models.BooleanField(default=False)
    sira = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sira', 'id']
        unique_together = [('marka', 'kod')]
        verbose_name = "Menü Alerjeni"
        verbose_name_plural = "Menü Alerjenleri"

    def __str__(self):
        return "%s / %s" % (self.marka.ad, self.ad)


class MenuSube(models.Model):
    """QR menüde müşterinin seçtiği şube. Operasyonel Sube kaydından bağımsızdır (depo vb. karışmasın)."""
    marka = models.ForeignKey(MenuMarka, on_delete=models.CASCADE, related_name='menu_subeleri')
    kod = models.SlugField(max_length=40, verbose_name="Kod")
    ad = models.CharField(max_length=80, verbose_name="Şube adı")
    sira = models.PositiveIntegerField(default=0)
    aktif = models.BooleanField(default=True, verbose_name="QR menüde seçilebilsin")

    class Meta:
        ordering = ['sira', 'ad', 'id']
        unique_together = [('marka', 'kod')]
        verbose_name = "QR Menü Şubesi"
        verbose_name_plural = "QR Menü Şubeleri"

    def __str__(self):
        return self.ad


class MenuUrun(models.Model):
    marka = models.ForeignKey(MenuMarka, on_delete=models.CASCADE, related_name='urunler')
    kategori = models.ForeignKey(MenuKategori, on_delete=models.PROTECT, related_name='urunler')
    kod = models.SlugField(max_length=80, verbose_name="Ürün Kodu")
    urun_adi = models.CharField(max_length=160, verbose_name="Ürün Adı (TR)")
    urun_adi_en = models.CharField(max_length=160, blank=True, default='', verbose_name="Ürün Adı (EN)")
    fiyat = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Fiyat (₺)")
    aciklama = models.TextField(blank=True, default='', verbose_name="Açıklama (TR)")
    aciklama_en = models.TextField(blank=True, default='', verbose_name="Açıklama (EN)")
    # Yalnızca Baga'da kullanılır
    icerik = models.TextField(blank=True, default='', verbose_name="İçerik (TR)")
    icerik_en = models.TextField(blank=True, default='', verbose_name="İçerik (EN)")
    kalori = models.PositiveIntegerField(null=True, blank=True, verbose_name="Kalori (kcal)")
    protein = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name="Protein (g)")
    # Alerjenler (Geek 11, Baga ilk 4'ünü kullanır: sut/yumurta/gluten/soya)
    sut = models.BooleanField(default=False, verbose_name="Süt")
    yumurta = models.BooleanField(default=False, verbose_name="Yumurta")
    gluten = models.BooleanField(default=False, verbose_name="Gluten")
    sert_kabuklu_yemis = models.BooleanField(default=False, verbose_name="Sert kabuklu yemiş")
    yer_fistigi = models.BooleanField(default=False, verbose_name="Yer fıstığı")
    susam = models.BooleanField(default=False, verbose_name="Susam")
    soya = models.BooleanField(default=False, verbose_name="Soya")
    hardal = models.BooleanField(default=False, verbose_name="Hardal")
    sirke_tursu = models.BooleanField(default=False, verbose_name="Sirke / turşu")
    balik = models.BooleanField(default=False, verbose_name="Balık")
    koruyucu_madde = models.BooleanField(default=False, verbose_name="Koruyucu madde")
    # Panelden eklenen ek alerjenlerin kodları (MenuAlerjen.kod, sistem=False)
    ek_alerjenler = models.JSONField(default=list, blank=True, verbose_name="Ek alerjenler")
    vegan = models.BooleanField(default=False, verbose_name="Vegan")
    sube_notu = models.TextField(blank=True, default='', verbose_name="Şube Notu (TR)")
    sube_notu_en = models.TextField(blank=True, default='', verbose_name="Şube Notu (EN)")
    # Panelden yüklenen fotoğraf (R2). Yoksa gorsel_harici (eski Drive linki) kullanılır.
    gorsel = models.ImageField(upload_to='menu/', null=True, blank=True, verbose_name="Fotoğraf")
    gorsel_harici = models.CharField(max_length=600, blank=True, default='', verbose_name="Harici Görsel Linki")
    sira = models.PositiveIntegerField(default=0)
    aktif = models.BooleanField(default=True, verbose_name="Menüde Göster")
    # Boş = tüm şubelerde satılır. Doluysa ürün bu şubelerin QR menüsünde GÖRÜNMEZ.
    gizli_subeler = models.ManyToManyField('MenuSube', blank=True, related_name='gizli_urunler',
                                           verbose_name="Satılmadığı şubeler")
    olusturma = models.DateTimeField(auto_now_add=True)
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['kategori__sira', 'sira', 'id']
        unique_together = [('marka', 'kod')]
        verbose_name = "Menü Ürünü"
        verbose_name_plural = "Menü Ürünleri"

    def __str__(self):
        return "%s — %s" % (self.marka.ad, self.urun_adi)

    def gorsel_url(self):
        """CSV'ye ve önizlemeye yazılacak tam görsel adresi."""
        if self.gorsel:
            try:
                return self.gorsel.url
            except Exception:
                pass
        return self.gorsel_harici or ''


# --- Mutfak zayi (yazılı kayıt) --------------------------------------------------

class ZayiBirim(models.TextChoices):
    GR = 'gr', 'gr'
    KG = 'kg', 'kg'
    ML = 'ml', 'ml'
    LT = 'lt', 'lt'
    ADET = 'adet', 'adet'


# birim -> (taban birime çarpan, ölçü türü). Toplama sadece aynı türde yapılır:
# gr/kg birlikte, ml/lt birlikte, adet kendi başına. Gram ile mililitre toplanmaz.
ZAYI_BIRIM_OLCU = {
    'gr': (1, 'agirlik'), 'kg': (1000, 'agirlik'),
    'ml': (1, 'hacim'), 'lt': (1000, 'hacim'),
    'adet': (1, 'adet'),
}


def zayi_urun_anahtar(ad):
    """Ürün adını gruplamak için normalleştirir (büyük/küçük harf, fazla boşluk, İ/ı)."""
    s = ' '.join((ad or '').split())
    s = s.replace('İ', 'i').replace('I', 'ı').lower()
    return unicodedata.normalize('NFC', s)[:120]


def zayi_urun_baslik(anahtar):
    """'pesto sos' -> 'Pesto Sos' (Türkçe i/ı kurallarıyla)."""
    kelimeler = []
    for w in (anahtar or '').split(' '):
        if not w:
            continue
        f = 'İ' if w[0] == 'i' else ('I' if w[0] == 'ı' else w[0].upper())
        kelimeler.append(f + w[1:])
    return ' '.join(kelimeler)


class MutfakZayiKalemi(models.Model):
    """Günlük elle girilen mutfak zayi satırı (ör. Domates 100 gr)."""
    sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='zayi_kalemleri', verbose_name="Şube")
    sube_ad_arsiv = models.CharField(max_length=100, blank=True, default='')
    personel = models.ForeignKey(Personel, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='zayi_kalemleri', verbose_name="Giren")
    personel_ad_arsiv = models.CharField(max_length=160, blank=True, default='')
    tarih = models.DateField(db_index=True, verbose_name="Zayi Tarihi")
    urun = models.CharField(max_length=120, verbose_name="Ürün")
    urun_anahtar = models.CharField(max_length=120, db_index=True, editable=False, default='')
    miktar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Miktar")
    birim = models.CharField(max_length=8, choices=ZayiBirim.choices, verbose_name="Birim")
    olcu = models.CharField(max_length=8, editable=False, default='')
    taban_miktar = models.DecimalField(max_digits=14, decimal_places=2, editable=False, default=0,
                                       help_text="gr / ml / adet cinsinden")
    aciklama = models.CharField(max_length=500, blank=True, default='', verbose_name="Açıklama")
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mutfak Zayi Kalemi"; verbose_name_plural = "Mutfak Zayi Kalemleri"
        ordering = ['-tarih', '-olusturma']
        indexes = [models.Index(fields=['sube', 'tarih'], name='zayikalem_sube_tarih')]

    def save(self, *args, **kwargs):
        self.urun = ' '.join((self.urun or '').split())[:120]
        self.urun_anahtar = zayi_urun_anahtar(self.urun)
        carpan, olcu = ZAYI_BIRIM_OLCU.get(self.birim, (1, 'adet'))
        self.olcu = olcu
        self.taban_miktar = (self.miktar or 0) * carpan
        if self.sube_id and not self.sube_ad_arsiv:
            self.sube_ad_arsiv = self.sube.ad
        if self.personel_id and not self.personel_ad_arsiv:
            self.personel_ad_arsiv = self.personel.ad_soyad
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tarih:%d.%m.%Y} {self.sube_ad_arsiv} {self.urun} {self.miktar} {self.birim}"


# ----------------------------------------------------------------------------
# Temizlik malzemesi tüketimi: ay başı sayım + haftalık ilave (sevkiyattan) − ay sonu sayım
# ----------------------------------------------------------------------------
class TemizlikUrun(models.Model):
    ad = models.CharField(max_length=200, verbose_name="Ürün Adı")
    birim = models.CharField(max_length=20, default='ADET', verbose_name="Birim")
    koli_icerigi = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name="Koli içeriği")
    hacim = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                verbose_name="Bir adetin kapasitesi",
                                help_text="Sıvı/toz ürünlerde bir kabın içeriği (örn. 500). Boşsa açık kap girişi çıkmaz.")
    hacim_birim = models.CharField(max_length=5, blank=True, default='', verbose_name="Kapasite birimi")
    urun = models.ForeignKey('Urun', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                             verbose_name="Sevkiyat kataloğundaki karşılığı",
                             help_text="Boş bırakılırsa sevkiyattaki ürün adıyla eşleştirilir.")
    sira = models.PositiveIntegerField(default=0, verbose_name="Sıra")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Temizlik Ürünü"
        verbose_name_plural = "Temizlik Ürünleri"
        ordering = ['sira', 'ad']

    def __str__(self):
        return self.ad


class TemizlikSayim(models.Model):
    TUR = [('ILK', 'İlk stok (ay başı)'), ('SON', 'Son stok (ay sonu)')]
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='temizlik_sayimlari', verbose_name="Şube")
    ay = models.DateField(verbose_name="Ay (ayın 1'i)")
    tur = models.CharField(max_length=4, choices=TUR, verbose_name="Sayım türü")
    tarih = models.DateField(verbose_name="Sayım tarihi")
    giren = models.ForeignKey('Personel', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='+', verbose_name="Giren")
    giren_ad = models.CharField(max_length=100, blank=True, verbose_name="Giren (ad)")
    olusturma = models.DateTimeField(auto_now_add=True)
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Temizlik Sayımı"
        verbose_name_plural = "Temizlik Sayımları"
        ordering = ['-ay', 'sube', 'tur']
        constraints = [models.UniqueConstraint(fields=['sube', 'ay', 'tur'], name='temizlik_sayim_tekil')]

    def __str__(self):
        return f"{self.sube} · {self.ay:%m.%Y} · {self.get_tur_display()}"


class TemizlikSayimKalem(models.Model):
    sayim = models.ForeignKey(TemizlikSayim, on_delete=models.CASCADE, related_name='kalemler')
    urun = models.ForeignKey(TemizlikUrun, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    urun_ad = models.CharField(max_length=200, default='')
    miktar = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Miktar (taban birim)")
    koli = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Kapalı koli")
    adet = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Kapalı adet")
    acik = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                               verbose_name="Açık kaplarda kalan (kapasite birimi)")

    class Meta:
        verbose_name = "Temizlik Sayım Kalemi"
        verbose_name_plural = "Temizlik Sayım Kalemleri"


class TemizlikDuzeltme(models.Model):
    """İlave sütununa elle düzeltme: sevkiyat dışı gelen (+) ya da hatalı yazılan/iade edilen (−) miktar."""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='temizlik_duzeltmeleri')
    ay = models.DateField(verbose_name="Ay (ayın 1'i)")
    urun = models.ForeignKey(TemizlikUrun, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    urun_ad = models.CharField(max_length=200, default='')
    tarih = models.DateField(verbose_name="Tarih")
    miktar = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Miktar (+/−, taban birim)")
    aciklama = models.CharField(max_length=200, blank=True, verbose_name="Açıklama")
    giren = models.ForeignKey('Personel', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    giren_ad = models.CharField(max_length=100, blank=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Temizlik Düzeltmesi"
        verbose_name_plural = "Temizlik Düzeltmeleri"
        ordering = ['tarih', 'id']


class TemizlikAyar(models.Model):
    """Temizlik tüketim sisteminin tek satırlık ayarı: açık/kapalı + başlangıç tarihi."""
    aktif = models.BooleanField(default=False, verbose_name="Sistem açık",
                                help_text="Kapalıyken yalnızca Genel Müdür, Operatör ve Satın Alma görür.")
    baslangic = models.DateField(null=True, blank=True, verbose_name="Başlangıç tarihi",
                                 help_text="Bu tarihten önce gelen sevkiyatlar ilaveye sayılmaz; önceki aylara sayım girilemez.")
    guncelleyen = models.CharField(max_length=100, blank=True, verbose_name="Son değiştiren")
    guncelleme = models.DateTimeField(auto_now=True)
    son_sifirlama = models.DateTimeField(null=True, blank=True, verbose_name="Son sıfırlama")
    son_sifirlayan = models.CharField(max_length=100, blank=True, verbose_name="Sıfırlayan")

    class Meta:
        verbose_name = "Temizlik Sistemi Ayarı"
        verbose_name_plural = "Temizlik Sistemi Ayarı"

    def __str__(self):
        return "Temizlik sistemi: " + ("açık" if self.aktif else "kapalı")

    @classmethod
    def al(cls):
        """Tek ayar satırı; yoksa kapalı + gelecek ayın 1'i başlangıç olarak oluşturulur."""
        obj = cls.objects.order_by('id').first()
        if obj is None:
            import datetime
            bugun = datetime.date.today()
            ilk = (bugun.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
            obj = cls.objects.create(aktif=False, baslangic=ilk)
        return obj


class TemizlikFiyat(models.Model):
    """Ürünün birim fiyatı (geçmişli): adet / kg / litre başına TL."""
    BIRIM = [('ADET', 'Adet / paket başına'), ('KG', 'Kilogram başına'), ('LT', 'Litre başına')]
    urun = models.ForeignKey(TemizlikUrun, on_delete=models.CASCADE, related_name='fiyatlar')
    fiyat = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Fiyat (TL)")
    birim = models.CharField(max_length=4, choices=BIRIM, default='ADET', verbose_name="Fiyat birimi")
    gecerli = models.DateField(verbose_name="Geçerlilik başlangıcı")
    giren_ad = models.CharField(max_length=100, blank=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Temizlik Ürün Fiyatı"
        verbose_name_plural = "Temizlik Ürün Fiyatları"
        ordering = ['urun', '-gecerli']
        constraints = [models.UniqueConstraint(fields=['urun', 'gecerli'], name='temizlik_fiyat_tekil')]

    def __str__(self):
        return f"{self.urun} · {self.fiyat} TL/{self.birim.lower()} ({self.gecerli:%d.%m.%Y})"


class TuketimFiyat(models.Model):
    """Sevkiyat kataloğundaki ürünün TABAN BİRİM (1 adet/şişe/paket) başına alış fiyatı — tarihli.

    Öncelik: şubeye özel fiyat > şubenin fiyat grubu (Merkez/Franchise) fiyatı. Fiyat, geçerlilik tarihinden itibaren
    geçerlidir; ay ortasında değişirse mal teslim tarihindeki fiyatla değerlenir."""
    urun = models.ForeignKey('Urun', on_delete=models.CASCADE, related_name='tuketim_fiyatlari')
    grup = models.CharField(max_length=10, choices=Sube.FIYAT_GRUBU, blank=True, default='')
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, null=True, blank=True, related_name='tuketim_fiyatlari')
    fiyat = models.DecimalField(max_digits=14, decimal_places=4, verbose_name="Fiyat (TL / taban birim)")
    gecerli = models.DateField(verbose_name="Geçerlilik başlangıcı")
    giren_ad = models.CharField(max_length=100, blank=True)
    olusturma = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tüketim Ürün Fiyatı"
        verbose_name_plural = "Tüketim Ürün Fiyatları"
        ordering = ['urun', 'grup', 'sube', '-gecerli']

    def __str__(self):
        hedef = self.sube.ad if self.sube_id else self.get_grup_display()
        return f"{self.urun} · {hedef} · {self.fiyat} TL ({self.gecerli:%d.%m.%Y})"


class TuketimAyar(models.Model):
    """Bar tüketim & maliyet sisteminin tek satırlık ayarı."""
    aktif = models.BooleanField(default=False, verbose_name="Sistem açık",
                                help_text="Kapalıyken yalnızca Genel Müdür, Operatör ve Satın Alma görür.")
    baslangic = models.DateField(null=True, blank=True, verbose_name="İlk sayım ayı",
                                 help_text="Bu ayın sayımı ilk açılış stoğu olur; kullanım hesabı bir sonraki aydan başlar.")
    son_gun_ayda = models.BooleanField(default=True, verbose_name="Ayın son günü gelen sevkiyat o ayın sayılır",
                                       help_text="Sayım gün sonunda yapılıyorsa açık bırakın. Gün başında yapılıyorsa kapatın; "
                                                 "o gün gelen mal bir sonraki ayın sayılır.")
    guncelleyen = models.CharField(max_length=100, blank=True)
    guncelleme = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tüketim Sistemi Ayarı"
        verbose_name_plural = "Tüketim Sistemi Ayarı"

    @classmethod
    def al(cls):
        obj = cls.objects.order_by('id').first()
        if obj is None:
            obj = cls.objects.create(aktif=False)
        return obj


class KalibrasyonKontrol(models.Model):
    """Şube şefi / bölge müdürünün kalibrasyon görüntüsünü gördüğünü işaretlediği tik."""
    kalibrasyon = models.ForeignKey(Kalibrasyon, on_delete=models.CASCADE, related_name='kontroller')
    personel = models.ForeignKey('Personel', on_delete=models.CASCADE, related_name='+')
    ad = models.CharField(max_length=100, blank=True, verbose_name="Kontrol eden")
    rol = models.CharField(max_length=40, blank=True)
    zaman = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kalibrasyon Kontrolü"
        verbose_name_plural = "Kalibrasyon Kontrolleri"
        ordering = ['zaman']
        constraints = [models.UniqueConstraint(fields=['kalibrasyon', 'personel'], name='kalibrasyon_kontrol_tekil')]

    def __str__(self):
        return f"{self.ad} ✓ {self.kalibrasyon}"


class OturumKaydi(models.Model):
    """Bölge müdürlerinin uygulamaya giriş / açılış kaydı (günde kaç kez kullandığını görmek için)."""
    TUR = [('giris', 'Giriş (şifre/kod ile)'), ('acilis', 'Açılış (30 dk+ aradan sonra)')]
    personel = models.ForeignKey('Personel', on_delete=models.CASCADE, related_name='oturum_kayitlari')
    an = models.DateTimeField(default=timezone.now, db_index=True)
    tur = models.CharField(max_length=8, choices=TUR, default='giris')

    class Meta:
        verbose_name = "Oturum Kaydı"
        verbose_name_plural = "Oturum Kayıtları"
        ordering = ['-an']
        indexes = [models.Index(fields=['personel', 'an'])]

    def __str__(self):
        return f"{self.personel} · {self.an:%d.%m.%Y %H:%M} · {self.tur}"


class Anket(models.Model):
    """Geek Crew sayfasında operatörün paylaştığı anket. Herkes oy verir, sonuçları herkes görür."""
    soru = models.CharField(max_length=250, verbose_name="Soru")
    olusturan = models.ForeignKey('Personel', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    olusturma = models.DateTimeField(auto_now_add=True)
    aktif = models.BooleanField(default=True, verbose_name="Oy verilebilir")

    class Meta:
        ordering = ['-olusturma']
        verbose_name = "Anket"
        verbose_name_plural = "Anketler"

    def __str__(self):
        return self.soru[:60]


class AnketSecenek(models.Model):
    anket = models.ForeignKey(Anket, on_delete=models.CASCADE, related_name='secenekler')
    metin = models.CharField(max_length=120)
    sira = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sira', 'id']

    def __str__(self):
        return self.metin


class AnketOy(models.Model):
    anket = models.ForeignKey(Anket, on_delete=models.CASCADE, related_name='oylar')
    secenek = models.ForeignKey(AnketSecenek, on_delete=models.CASCADE, related_name='oylar')
    personel = models.ForeignKey('Personel', on_delete=models.CASCADE, related_name='+')
    zaman = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['anket', 'personel'], name='anket_oy_tekil')]


class OyunSkor(models.Model):
    """Geek Koşusu oyununda yapılan koşuların skorları."""
    personel = models.ForeignKey('Personel', on_delete=models.CASCADE, related_name='oyun_skorlari')
    skor = models.PositiveIntegerField()
    sure_sn = models.PositiveIntegerField(default=0)
    # Oyun modu: 'kosu' (Geek Koşusu) | 'arena' (Geek Arena). Eski kayıtlar koşudur.
    mod = models.CharField(max_length=10, default='kosu', db_index=True)
    zaman = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-zaman']
        indexes = [models.Index(fields=['zaman'], name='panel_oyuns_zaman_idx'), models.Index(fields=['personel', '-skor'], name='panel_oyuns_pers_skor_idx')]
        verbose_name = "Oyun skoru"
        verbose_name_plural = "Oyun skorları"

    def __str__(self):
        return f'{self.personel} · {self.skor}'


class MenuluxOnbellek(models.Model):
    """Menulux API yanıtlarının kısa süreli önbelleği (her ekran açılışında portala gitmemek için)."""
    anahtar = models.CharField(max_length=200, unique=True)
    veri = models.JSONField()
    olusturma = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Menulux önbelleği"; verbose_name_plural = "Menulux önbelleği"
