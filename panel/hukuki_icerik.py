# -*- coding: utf-8 -*-
"""
Hukuki sayfa içerikleri.

ÖNEMLİ: Bu metinler, bu sistemin işlediği gerçek verilere göre hazırlanmış
güçlü bir BAŞLANGIÇ TASLAĞIDIR; hukuki danışmanlık değildir. Yürürlüğe almadan
önce bir avukata/uyum danışmanına inceletin ve [köşeli parantez] içindeki
firmaya özel alanları doldurun.
"""

GUNCELLEME = "10.06.2026"
NOT = ("Bu metin, sistemin işlediği verilere göre hazırlanmış bir başlangıç "
       "taslağıdır ve hukuki danışmanlık yerine geçmez. Yürürlüğe almadan önce "
       "bir hukuk danışmanına inceletin ve [köşeli parantez] içindeki firmaya "
       "özel bilgileri doldurun.")

# Sistemin gerçekte işlediği veri kategorileri (tek yerden yönetilir)
_ISLENEN_VERILER = (
    "Kimlik bilgisi (ad-soyad), sisteme giriş için atanan benzersiz kullanıcı/giriş "
    "kodu, görev/rol ve bağlı olunan şube bilgisi; vardiya planı kayıtları, mola "
    "başlangıç/bitiş kayıtları ve aylık puantaj (çalışılan/izinli/raporlu/eksik gün) verileri."
)

HUKUKI_SAYFALAR = {
    "kvkk": {
        "baslik": "KVKK Aydınlatma Metni",
        "guncelleme": GUNCELLEME,
        "not": NOT,
        "bolumler": [
            {"baslik": "1. Veri Sorumlusu",
             "paragraflar": [
                "6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK) m.10 kapsamında, "
                "kişisel verileriniz veri sorumlusu sıfatıyla [Firma Ünvanı] "
                "(\u201cŞirket\u201d) tarafından işlenmektedir.",
                "Adres: [Firma Adresi] · İletişim: [E-posta / KEP adresi] · "
                "Telefon: [Telefon]."]},
            {"baslik": "2. İşlenen Kişisel Veriler",
             "paragraflar": [_ISLENEN_VERILER]},
            {"baslik": "3. İşleme Amaçları",
             "paragraflar": [
                "Verileriniz; personel ve vardiya planlamasının yapılması, mola "
                "sürelerinin takibi, aylık puantajın hesaplanması, iş organizasyonunun "
                "yürütülmesi ve ilgili mevzuattan doğan yükümlülüklerin yerine "
                "getirilmesi amaçlarıyla işlenir."]},
            {"baslik": "4. İşlemenin Hukuki Sebebi (KVKK m.5)",
             "paragraflar": [
                "Verileriniz; bir iş sözleşmesinin kurulması veya ifasıyla doğrudan "
                "ilgili olması, Şirketin hukuki yükümlülüğünü yerine getirebilmesi ve "
                "meşru menfaati hukuki sebeplerine dayanılarak işlenir."]},
            {"baslik": "5. Aktarım",
             "paragraflar": [
                "Kişisel verileriniz, yalnızca yukarıdaki amaçlarla sınırlı olmak ve "
                "mevzuata uygun davranmak kaydıyla; barındırma/altyapı hizmeti alınan "
                "tedarikçiler ile yetkili kamu kurumlarına aktarılabilir. Bunun dışında "
                "üçüncü kişilerle paylaşılmaz."]},
            {"baslik": "6. Saklama Süresi",
             "paragraflar": [
                "Verileriniz, işleme amacının gerektirdiği ve ilgili mevzuatta öngörülen "
                "süreler boyunca saklanır; sürenin sona ermesiyle silinir, yok edilir "
                "veya anonim hale getirilir."]},
            {"baslik": "7. Haklarınız (KVKK m.11)",
             "paragraflar": [
                "Kişisel verilerinizin işlenip işlenmediğini öğrenme; işlenmişse buna "
                "ilişkin bilgi talep etme; işlenme amacını ve amaca uygun kullanılıp "
                "kullanılmadığını öğrenme; eksik/yanlış işlenmişse düzeltilmesini, "
                "şartlar oluştuğunda silinmesini isteme ve işlemenin yalnızca otomatik "
                "sistemlerle analizi sonucu aleyhinize bir sonucun çıkmasına itiraz etme "
                "haklarına sahipsiniz."]},
            {"baslik": "8. Başvuru",
             "paragraflar": [
                "Haklarınıza ilişkin taleplerinizi [E-posta / KEP adresi] üzerinden "
                "Şirkete iletebilirsiniz. Başvurular mevzuatta öngörülen süre içinde "
                "sonuçlandırılır."]},
        ],
    },
    "kullanim_kosullari": {
        "baslik": "Kullanım Koşulları",
        "guncelleme": GUNCELLEME,
        "not": NOT,
        "bolumler": [
            {"baslik": "1. Taraflar ve Kapsam",
             "paragraflar": [
                "Bu koşullar, [Firma Ünvanı] tarafından sağlanan personel yönetim "
                "sisteminin (\u201cSistem\u201d) kullanımını düzenler. Sisteme giriş yapan "
                "her kullanıcı bu koşulları kabul etmiş sayılır."]},
            {"baslik": "2. Hesap ve Giriş Kodu",
             "paragraflar": [
                "Sisteme erişim, kullanıcıya atanan benzersiz giriş kodu ile sağlanır. "
                "Giriş kodunun gizliliğinden ve kodla yapılan tüm işlemlerden kullanıcı "
                "sorumludur. Kodun başkalarıyla paylaşılması yasaktır.",
                "Kodun yetkisiz kişilerce öğrenildiğinden şüphelenilmesi halinde durum "
                "derhal yöneticinize bildirilmeli ve kodun yenilenmesi talep edilmelidir."]},
            {"baslik": "3. Uygun Kullanım",
             "paragraflar": [
                "Sistem yalnızca iş amaçlı ve kullanıcının yetkisi dahilindeki işlemler "
                "için kullanılır. Yetkisiz erişim, başkası adına işlem yapma veya sistemin "
                "işleyişini bozmaya yönelik girişimler yasaktır."]},
            {"baslik": "4. Sorumluluğun Sınırlandırılması",
             "paragraflar": [
                "Sistem \u201colduğu gibi\u201d sunulur. Kullanıcının koşullara aykırı "
                "davranışından doğan zararlardan Şirket sorumlu tutulamaz."]},
            {"baslik": "5. Değişiklikler",
             "paragraflar": [
                "Şirket, bu koşulları güncelleme hakkını saklı tutar. Güncel sürüm bu "
                "sayfada yayımlanır."]},
        ],
    },
    "gizlilik": {
        "baslik": "Gizlilik Politikası",
        "guncelleme": GUNCELLEME,
        "not": NOT,
        "bolumler": [
            {"baslik": "1. Toplanan Bilgiler",
             "paragraflar": [
                "Sistem, yalnızca personel yönetimi için gerekli olan şu verileri toplar: "
                + _ISLENEN_VERILER]},
            {"baslik": "2. Bilgilerin Kullanımı",
             "paragraflar": [
                "Toplanan veriler yalnızca vardiya planlama, mola takibi ve puantaj "
                "hesaplama amaçlarıyla kullanılır; pazarlama amacıyla kullanılmaz ve "
                "amacı dışında üçüncü taraflarla paylaşılmaz."]},
            {"baslik": "3. Oturum ve Çerezler",
             "paragraflar": [
                "Sistem, oturumunuzun açık kalması için yalnızca zorunlu oturum "
                "çerezlerini kullanır. Reklam veya izleme amaçlı çerez kullanılmaz."]},
            {"baslik": "4. Güvenlik",
             "paragraflar": [
                "Veriler, yetkisiz erişime karşı makul teknik ve idari tedbirlerle "
                "korunur ve yalnızca yetkili kullanıcılar tarafından, rolleri "
                "kapsamında erişilebilir."]},
            {"baslik": "5. İletişim",
             "paragraflar": [
                "Gizlilikle ilgili sorularınız için: [E-posta / KEP adresi]."]},
        ],
    },
}
