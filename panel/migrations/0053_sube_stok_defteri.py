import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Sevkiyat onaylandığında depo/şube stok seviyelerini otomatik
    güncelleyecek gerçek bir stok defteri: SubeStok (güncel seviye) +
    StokHareket (denetim kaydı)."""

    dependencies = [
        ('panel', '0052_alter_denetim_id_alter_denetimbolum_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubeStok',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('birim', models.CharField(choices=[('ADET', 'ADET'), ('KOLİ', 'KOLİ'), ('KG', 'KG'), ('GRAM', 'GRAM'),
                                                     ('LİTRE', 'LİTRE'), ('ML', 'ML'), ('PAKET', 'PAKET'),
                                                     ('SET', 'SET'), ('KUTU', 'KUTU')],
                                          max_length=10, verbose_name='Birim')),
                ('miktar', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Mevcut Miktar')),
                ('guncelleme', models.DateTimeField(auto_now=True)),
                ('sube', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stok_seviyeleri',
                                           to='panel.sube', verbose_name='Şube')),
                ('urun', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sube_stoklari',
                                           to='panel.urun', verbose_name='Ürün')),
            ],
            options={
                'verbose_name': 'Şube Stok Seviyesi',
                'verbose_name_plural': 'Şube Stok Seviyeleri',
                'ordering': ['sube__ad', 'urun__ad'],
                'unique_together': {('sube', 'urun', 'birim')},
            },
        ),
        migrations.CreateModel(
            name='StokHareket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('urun_ad', models.CharField(default='', max_length=160)),
                ('yon', models.CharField(choices=[('Giriş', 'Giriş'), ('Çıkış', 'Çıkış')], max_length=10, verbose_name='Yön')),
                ('miktar', models.DecimalField(decimal_places=2, max_digits=12)),
                ('birim', models.CharField(max_length=10)),
                ('aciklama', models.CharField(blank=True, default='', max_length=200)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('sube', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stok_hareketleri',
                                           to='panel.sube', verbose_name='Şube')),
                ('urun', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+',
                                           to='panel.urun', verbose_name='Ürün')),
                ('talep', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='stok_hareketleri', to='panel.sevkiyattalep',
                                            verbose_name='İlgili Sevkiyat')),
            ],
            options={
                'verbose_name': 'Stok Hareketi',
                'verbose_name_plural': 'Stok Hareketleri',
                'ordering': ['-olusturma'],
            },
        ),
    ]
