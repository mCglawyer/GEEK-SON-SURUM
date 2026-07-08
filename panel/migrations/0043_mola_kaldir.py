from django.db import migrations


class Migration(migrations.Migration):
    """
    Eski manuel mola sistemi (Personel/Şef ana sayfasındaki "1. molaya başla" butonu
    ve buna bağlı "Mola Süreleri" yönetici raporu) tamamen kaldırıldı.

    Artık TEK mola sistemi var: şube QR kodu ile başlatılan/bitirilen QR tabanlı
    mola sistemi (MolaOturum, SubeMolaToken, "Mola Takibi" sayfaları). Bu migration
    onu ETKİLEMEZ, sadece eski/paralel "Mola" modelini kaldırır.

    DİKKAT: Bu migration 'panel_mola' tablosunu ve içindeki TÜM geçmiş manuel mola
    kayıtlarını veritabanından SİLER. Devam etmeden önce gerekiyorsa Neon üzerinden
    yedek alın.
    """

    dependencies = [
        ('panel', '0042_mutfak_maliyet_birim'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Mola',
        ),
    ]
