import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Müşteri değerlendirme (QR ile) sistemi: şube başına bir QR token
    ve gönderilen değerlendirmeler. Projenin gerçek migration zinciri
    0053_sube_stok_defteri'de kaldığı için (0054_menulux_iskelet hiç
    eklenmemiş), bu migration doğrudan 0053'e bağımlı."""

    dependencies = [
        ('panel', '0053_sube_stok_defteri'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubeDegerlendirmeToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('sube', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='degerlendirme_token', to='panel.sube')),
            ],
        ),
        migrations.CreateModel(
            name='MusteriDegerlendirme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uc_kelime', models.CharField(blank=True, default='', max_length=200, verbose_name='Üç Kelime')),
                ('ilk_izlenim', models.CharField(blank=True, default='', max_length=300, verbose_name='İlk İzlenim')),
                ('favori_gorsel', models.CharField(blank=True, default='', max_length=300, verbose_name='Favori Görsel')),
                ('favori_lezzet', models.CharField(blank=True, default='', max_length=300, verbose_name='Favori Lezzet')),
                ('servis', models.CharField(blank=True, default='', max_length=300, verbose_name='Servis')),
                ('atmosfer', models.CharField(blank=True, default='', max_length=300, verbose_name='Atmosfer')),
                ('deger_mi', models.CharField(blank=True, default='', max_length=300, verbose_name='Değer mi?')),
                ('bir_sey_degisse', models.CharField(blank=True, default='', max_length=300, verbose_name='Bir Şey Değişse')),
                ('tekrar', models.CharField(blank=True, default='', max_length=300, verbose_name='Tekrar Gelir mi?')),
                ('puan', models.PositiveSmallIntegerField(default=0, verbose_name='Puan (/10)')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('sube', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='degerlendirmeler',
                                           to='panel.sube', verbose_name='Şube')),
            ],
            options={
                'verbose_name': 'Müşteri Değerlendirmesi',
                'verbose_name_plural': 'Müşteri Değerlendirmeleri',
                'ordering': ['-olusturma'],
            },
        ),
    ]
