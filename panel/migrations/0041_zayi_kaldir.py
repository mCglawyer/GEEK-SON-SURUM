from django.db import migrations


class Migration(migrations.Migration):
    """
    Genel "Zayi" (şube fire/zayi) sistemi tamamen kaldırıldı.
    Mutfak Zayi (MutfakZayi) sistemi bundan etkilenmez, o ayrı bir modeldir ve kalır.

    DİKKAT: Bu migration 'panel_zayi' tablosunu ve içindeki TÜM geçmiş zayi kayıtlarını
    (varsa yüklenmiş fotoğraflarla birlikte metadata) veritabanından SİLER.
    Fiziksel fotoğraf dosyaları (media/zayi/...) bu migration ile silinmez, sadece
    veritabanı tablosu düşer. Devam etmeden önce gerekiyorsa Neon üzerinden yedek alın.
    """

    dependencies = [
        ('panel', '0040_eksik_kolonlari_onar'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Zayi',
        ),
    ]
