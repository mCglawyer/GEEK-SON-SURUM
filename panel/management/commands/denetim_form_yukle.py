# -*- coding: utf-8 -*-
"""
Geek Coffee Shop Şube Denetim Formu'ndaki tüm bölüm ve maddeleri sisteme yükler.
Tek seferlik kurulum içindir; tekrar çalıştırılırsa var olan bölüm/madde
isimleriyle eşleşenleri atlar (get_or_create), yinelenen kayıt oluşturmaz.

Kullanım:
    python manage.py denetim_form_yukle
"""
from django.core.management.base import BaseCommand

from panel.models import DenetimBolum, DenetimMadde

FORM = [
    ("A. Genel Dış Görünüş", [
        "Şubenin dış cephesi uzaktan bakıldığında temiz ve düzenli görünüyor mu?",
        "Şubenin genel görünümü Geek Coffee Shop marka standartlarını yansıtıyor mu?",
        "Dış cephede boya çatlağı, sıva dökülmesi veya deformasyon bulunuyor mu?",
        "Cephede rutubet veya nem izi bulunuyor mu?",
        "Dış cephede izinsiz afiş, sticker veya reklam mevcut mu?",
        "Dış cephe renkleri standart kurumsal renklerle uyumlu mu?",
        "Cephe camlarında kırık veya çatlak bulunuyor mu?",
        "Kurumsal görünümü bozacak herhangi bir unsur mevcut mu?",
    ]),
    ("B. Tabela Denetimi — Logo", [
        "Logo temiz", "Solma yok", "Çatlak yok", "Harf eksik değil",
        "Kurumsal ölçüler korunmuş", "Aydınlatma çalışıyor", "Gece görünürlüğü yeterli",
        "Elektrik kabloları görünmüyor", "Vida ve montajlar sağlam", "Eğrilik bulunmuyor",
    ]),
    ("C. Camlar — Ön Camlar", [
        "Parmak izi bulunmuyor", "Yağ lekesi yok", "Su izi yok", "Toz yok",
        "Bant kalıntısı yok", "Sticker düzgün uygulanmış", "Çizik bulunmuyor",
        "Kırık bulunmuyor", "İç ve dış yüzey temiz", "Köşeler temiz",
    ]),
    ("D. Giriş Kapısı", [
        "Kapı rahat açılıyor", "Kapanma hızı uygun", "Hidrolik sistemi çalışıyor",
        "Kapı kolu sağlam", "Cam temiz", "Kilit düzgün çalışıyor", "Kapı fitilleri sağlam",
        "Girişte engel yok", "Eşik temiz", "Pas bulunmuyor", "Boya deformasyonu yok",
        "Parmak izi bulunmuyor",
    ]),
    ("E. Giriş Alanı — Paspas (varsa)", [
        "Temiz", "Düz duruyor", "Koku yapmıyor", "Yıpranmamış", "Kaymıyor",
    ]),
    ("E. Giriş Alanı — Giriş Zemini", [
        "Temiz", "Kaygan değil", "Çatlak yok", "Çukur yok", "Sakız bulunmuyor",
        "Sigara izmariti bulunmuyor", "Yaprak birikimi yok", "Yağ lekesi yok",
    ]),
    ("F. Dış Oturma Alanı — Masa Kontrolü", [
        "Sallanmıyor", "Temiz", "Çizik minimum", "Vida gevşek değil", "Sakız yok",
        "Bardak izi yok", "Kenarlar sağlam", "Ayaklar sağlam",
    ]),
    ("F. Dış Oturma Alanı — Sandalyeler", [
        "Temiz", "Sallanmıyor", "Ayakları sağlam", "Kumaş temiz", "Minder sağlam",
        "Çatlak yok", "Pas bulunmuyor",
    ]),
    ("G. Şemsiye / Tente", [
        "Temiz", "Açılıyor", "Kapanıyor", "Kumaş yırtık değil", "Logo görünür",
        "Su almıyor", "Mekanizma sağlam",
    ]),
    ("H. Aydınlatma", [
        "Tabela ışıkları", "Bahçe ışıkları", "Giriş lambaları", "Acil çıkış ışıkları",
        "Dekoratif aydınlatmalar", "Ampul eksik değil", "Yanıp sönen lamba yok",
    ]),
    ("I. Bahçe ve Çevre Düzeni", [
        "Saksılar temiz", "Bitkiler canlı", "Kurumuş bitki yok", "Sulama yapılmış",
        "Çöp bulunmuyor", "Yaprak birikimi yok", "Zararlı ot yok", "Kötü koku yok",
        "Haşere belirtisi yok",
    ]),
    ("J. Çöp Alanları", [
        "Çöp kutusu temiz", "Kapak sağlam", "Poşet mevcut", "Taşma yok", "Koku yok",
        "Düzenli boşaltılıyor", "Misafir alanından görünmüyor",
    ]),
    ("K. Güvenlik", [
        "Güvenlik kamerası çalışıyor", "Kamera görüş açısı uygun", "Kamera temiz",
        "Acil çıkış önü açık", "Yangın dolabı veya tüpü görünür", "Yangın tüpü erişilebilir",
        "Elektrik panosu kilitli", "Dış kablolar güvenli",
    ]),
    ("L. Kurumsal Görseller", [
        "Açılış saatleri güncel", "QR Menü görünür", "Kampanyalar güncel",
        "Kurumsal afişler temiz", "Eski kampanya afişi bulunmuyor", "Menü panosu temiz",
        "Yazım hatası yok", "Fiyatlar güncel",
    ]),
    ("A2. Kişisel Görünüm — Üniforma", [
        "Kurumsal forma eksiksiz", "Forma temiz ve ütülü",
        "Forma yırtık, sökük veya deformasyon içermiyor", "Kurumsal önlük temiz",
        "Önlük cepleri düzenli", "Yedek önlüğü mevcut", "Kurumsal görünüm korunuyor",
    ]),
    ("A2. Kişisel Görünüm — Ayakkabı", [
        "Siyah ve kurumsal standarda uygun", "Temiz", "Bağcıkları düzgün",
        "Taban aşınmamış", "Kaymaz özellikte",
    ]),
    ("A2. Kişisel Görünüm — Saç ve Sakal", [
        "Saç temiz", "Saç toplama kurallarına uygun", "Yüzü kapatmıyor",
        "Sakal düzenli", "Günlük bakım yapılmış",
    ]),
    ("A2. Kişisel Görünüm — El ve Tırnak Hijyeni", [
        "Tırnak kısa", "Tırnak temiz", "Oje bulunmuyor", "Yapay tırnak yok",
        "Eller temiz", "Kesik veya yara uygun şekilde kapatılmış",
    ]),
    ("A2. Kişisel Görünüm — Takılar", [
        "Saat kurallara uygun", "Yüzük kurallara uygun", "Bileklik bulunmuyor",
        "Büyük küpe kullanılmıyor", "Hijyen açısından risk oluşturan aksesuar yok",
    ]),
    ("A2. Kişisel Görünüm — Kişisel Bakım", [
        "Ağız hijyeni uygun", "Ter kokusu bulunmuyor", "Yoğun parfüm kullanılmamış",
        "Genel görünüm profesyonel",
    ]),
    ("B2. Vardiya Disiplini", [
        "Mesaiye zamanında başlamış", "Vardiya değişimi prosedüre uygun yapılmış",
        "Görev alanını eksiksiz teslim almış", "Açılış/Kapanış checklistini tamamlamış",
        "Molalarını prosedüre uygun kullanıyor", "Görev alanını izinsiz terk etmiyor",
        "Telefon kullanımı kurallara uygun", "Vardiya boyunca aktif çalışıyor",
    ]),
    ("C2. Operasyon Disiplini", [
        "Boş kaldığında görev beklemiyor", "Temizlik ihtiyacını kendisi fark ediyor",
        "Malzeme eksiklerini bildiriyor", "Çalışma alanını sürekli düzenli tutuyor",
        "Kirli ekipmanı bekletmiyor", "Kullanılan ekipmanı yerine koyuyor",
        "Çöp doluluk oranını takip ediyor", "İş bitiminde alanını hazır bırakıyor",
    ]),
    ("D2. Misafir Karşılama", [
        "Misafir 10 saniye içinde fark edildi", "Göz teması kuruldu",
        "Gülümseyerek karşılandı", "\u201cHoş geldiniz\u201d ifadesi kullanıldı",
        "Yardım teklif edildi", "Sipariş sırasında sabırlı davranıldı",
        "Misafir dinlendi", "Teşekkür edildi", "Uğurlama yapıldı",
    ]),
    ("E2. İletişim Becerisi", [
        "Türkçeyi doğru kullanıyor", "Ses tonu uygun", "Diksiyonu anlaşılır",
        "Saygılı hitap ediyor", "Misafir sözünü kesmiyor", "Sorulara net cevap veriyor",
        "Olumsuz ifade kullanmıyor", "Beden dili olumlu", "Göz teması kuruyor",
        "Güler yüzünü koruyor",
    ]),
    ("F2. Satış Becerisi", [
        "Menüye hakim", "Ürün önerisi yapabiliyor", "Alternatif ürün sunabiliyor",
        "Büyük boy öneriyor", "Yan ürün öneriyor", "Kampanyaları biliyor",
        "Misafirin ihtiyacını analiz ediyor", "Satışı zorlamıyor",
        "Premium ürünleri tanıtıyor",
    ]),
    ("G2. Ürün Bilgisi — Espresso", [
        "Gramajı biliyor", "Shot süresini biliyor", "Tadım özelliklerini biliyor",
        "Kullanılan çekirdeği biliyor",
    ]),
    ("G2. Ürün Bilgisi — Süt", [
        "Süt sıcaklığını biliyor", "Köpük yapısını biliyor", "Laktozsuz seçenekleri biliyor",
    ]),
    ("G2. Ürün Bilgisi — Menü", [
        "Tüm sıcak içecekleri biliyor", "Tüm soğuk içecekleri biliyor",
        "Signature ürünleri biliyor", "Tatlıları biliyor", "Alerjen bilgisine hakim",
    ]),
    ("H2. Reçete Bilgisi", [
        "Doğru gramaj", "Doğru şurup miktarı", "Doğru süt miktarı", "Doğru bardak",
        "Doğru sunum", "Doğru garnitür", "Doğru servis",
    ]),
    ("I2. Kahve Bilgisi", [
        "Arabica nedir?", "Robusta nedir?", "Espresso nedir?", "Cappuccino-Latte farkı?",
        "Flat White nedir?", "Cortado nedir?", "Filtre kahve nasıl hazırlanır?",
        "Demleme yöntemleri?", "Kavurma dereceleri?", "Kahve saklama koşulları?",
    ]),
    ("J2. Ekipman Bilgisi", [
        "Espresso makinesini doğru kullanıyor", "Grinder ayarını biliyor",
        "Blender kullanımına hakim", "Pitcher seçimini doğru yapıyor",
        "Tamper basıncını biliyor", "Günlük bakım prosedürünü biliyor",
    ]),
    ("K2. Temizlik Alışkanlığı", [
        "Çalışırken temizliğini sürdürüyor", "Süt buhar çubuğunu her kullanım sonrası siliyor",
        "Portafiltreyi temiz bırakıyor", "Tezgah temiz", "Bezler temiz",
        "Kimyasalları doğru kullanıyor", "Çapraz bulaşmaya dikkat ediyor",
    ]),
    ("L2. Ekip Çalışması", [
        "Yardım teklif ediyor", "Yardım istiyor", "Saygılı iletişim kuruyor",
        "Çatışma oluşturmuyor", "İş paylaşımı yapıyor", "Yoğunlukta destek oluyor",
    ]),
    ("M2. Stres Yönetimi", [
        "Panik yapmıyor", "Hızlı düşünüyor", "Öncelik sırası oluşturuyor",
        "Misafire olumsuz davranmıyor", "Hata yaptığında çözüm üretiyor",
    ]),
    ("N2. Kurum Kültürü", [
        "Geek Coffee Shop değerlerini biliyor", "Prosedürlere uyuyor",
        "Kurumsal dili kullanıyor", "Marka temsil bilinci yüksek", "Gelişime açık",
        "Eğitimlere istekli",
    ]),
    ("O. Yöneticilere Özel (Şef / Şube Sorumlusu)", [
        "Vardiya planlaması doğru", "Görev dağılımı dengeli", "Ekibi motive ediyor",
        "Kriz yönetebiliyor", "Geri bildirim veriyor", "Eğitim planlıyor",
        "Stokları takip ediyor", "Fireleri kontrol ediyor", "Maliyet bilinci yüksek",
        "Operasyonu sürekli gözlemliyor",
    ]),
    ("A3. Espresso İstasyonu ve Çalışma Alanı", [
        "Bar istasyonu temiz ve düzenlidir", "Çalışma alanında gereksiz ekipman bulunmaz",
        "Ürün yerleşimi operasyon akışına uygundur", "Tezgâh kuru ve hijyeniktir",
        "Bardak ve ekipmanlar kolay erişilebilir durumdadır", "Çöp kutuları dolu değildir",
        "Kullanılan bezler temiz ve doğru alanda kullanılmaktadır",
    ]),
    ("B3. Espresso Makinesi Denetimi", [
        "Makinenin dış yüzeyi temizdir", "Grup başlıkları temizdir", "Portafiltreler temizdir",
        "Buhar çubukları her kullanım sonrası temizlenmektedir",
        "Basınç göstergeleri normal çalışmaktadır", "Günlük backflush işlemi yapılmıştır",
        "Su sızıntısı veya arıza bulunmamaktadır", "Günlük bakım kayıt altına alınmıştır",
    ]),
    ("C3. Grinder ve Kalibrasyon", [
        "Grinder temizdir", "Hazne temiz ve yabancı madde içermez",
        "Öğütüm ayarı güncel kalibrasyona uygundur", "İlk shot kontrolü yapılmıştır",
        "Kahve gramajı reçeteye uygundur", "Öğütülen kahvede topaklanma bulunmamaktadır",
        "Öğütüm sırasında anormal ses yoktur",
    ]),
    ("D3. Su Sistemi ve Filtrasyon", [
        "Su filtresi kullanım süresi takip edilmektedir", "Filtre değişim tarihleri kayıtlıdır",
        "Su kaçağı bulunmamaktadır", "Su basıncı uygundur",
        "Su tadı ve kokusunda anormallik yoktur",
    ]),
    ("E3. Bar Düzeni ve Ergonomi", [
        "Sütler doğru dolapta muhafaza edilmektedir", "Şuruplar düzenli yerleştirilmiştir",
        "Pitcherler temiz ve ulaşılabilir durumdadır", "Tamper ve aksesuarlar eksiksizdir",
        "Çalışma akışı personelin verimli hareket etmesini sağlamaktadır",
        "Kaygan zemin bulunmamaktadır",
    ]),
    ("F3. Günlük Bakım Prosedürleri", [
        "Espresso makinesi temizlenmiştir", "Grinder temizliği yapılmıştır",
        "Blenderlar temizlenmiştir", "Bar tezgâhı dezenfekte edilmiştir",
        "Damlalıklar boşaltılmıştır", "Çöp alanları temizlenmiştir",
        "Günlük bakım formu doldurulmuştur",
    ]),
    ("G3. Haftalık ve Aylık Bakımlar", [
        "Derin makine temizliği yapılmıştır", "Grinder iç temizliği yapılmıştır",
        "Su filtresi kontrol edilmiştir", "Buz makinesi temizlenmiştir",
        "Dolap contaları temizlenmiştir", "Bakım kayıtları güncel",
    ]),
]


class Command(BaseCommand):
    help = "Şube Denetim Formu'ndaki tüm bölüm ve maddeleri sisteme yükler (tekrar çalıştırılabilir)."

    def handle(self, *args, **options):
        bolum_sayisi, madde_sayisi = 0, 0
        for bolum_sira, (bolum_ad, maddeler) in enumerate(FORM, 1):
            bolum, olusturuldu = DenetimBolum.objects.get_or_create(
                ad=bolum_ad, defaults={'sira': bolum_sira})
            if olusturuldu:
                bolum_sayisi += 1
            for madde_sira, madde_metin in enumerate(maddeler, 1):
                _, olusturuldu = DenetimMadde.objects.get_or_create(
                    bolum=bolum, metin=madde_metin, defaults={'sira': madde_sira})
                if olusturuldu:
                    madde_sayisi += 1

        self.stdout.write(self.style.SUCCESS(
            f"Bitti: {bolum_sayisi} yeni bölüm, {madde_sayisi} yeni madde eklendi. "
            f"Toplam bölüm: {DenetimBolum.objects.count()}, toplam madde: {DenetimMadde.objects.count()}."))
