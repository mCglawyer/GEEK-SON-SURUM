import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Kamerası çalışmayan personel için manuel mola/mesai girişi özelliği:
    - Personel.manuel_giris_yetkisi: kişiye özel yetki bayrağı (Şef/Mağaza Müdürü'ne
      verilirse kendi şubesi adına, diğer rollerde kendi adına kullanılır).
    - MolaOturum / MesaiKayit: manuel_mi, manuel_giren, manuel_not alanları eklendi.
      Manuel girişler AYNI tablolara yazılır (ayrı bir sistem değil), sadece bu alanlarla
      işaretlenir — Mola Takibi/Mesai Kayıtları/Puantaj/Aylık Rapor otomatik kapsar.
    """

    dependencies = [
        ('panel', '0044_egitim_gelistirmeleri'),
    ]

    operations = [
        migrations.AddField(
            model_name='personel',
            name='manuel_giris_yetkisi',
            field=models.BooleanField(default=False, verbose_name='Manuel Mola/Mesai Girişi Yetkisi'),
        ),
        migrations.AddField(
            model_name='molaoturum',
            name='manuel_mi',
            field=models.BooleanField(default=False, verbose_name='Manuel Girildi'),
        ),
        migrations.AddField(
            model_name='molaoturum',
            name='manuel_giren',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='panel.personel', verbose_name='Manuel Girişi Yapan'),
        ),
        migrations.AddField(
            model_name='molaoturum',
            name='manuel_not',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='mesaikayit',
            name='manuel_mi',
            field=models.BooleanField(default=False, verbose_name='Manuel Girildi'),
        ),
        migrations.AddField(
            model_name='mesaikayit',
            name='manuel_giren',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='panel.personel', verbose_name='Manuel Girişi Yapan'),
        ),
        migrations.AddField(
            model_name='mesaikayit',
            name='manuel_not',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
