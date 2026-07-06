import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0038_zayi_foto_aciklama'),
    ]

    operations = [
        migrations.AlterField(
            model_name='personel',
            name='rol',
            field=models.CharField(
                choices=[('Genel Müdür', 'Genel Müdür (Tam Yetkili)'), ('Müdür', 'Bölge Müdürü'),
                         ('Mağaza Müdürü', 'Mağaza Müdürü'), ('Operatör', 'Operatör (Tam Yetkili)'),
                         ('Yatırımcı', 'Yatırımcı (Tam Yetkili)'), ('Satın Alma', 'Satın Alma'),
                         ('Sevkiyat', 'Sevkiyat'), ('Eğitmen', 'Eğitmen'), ('Şef', 'Şube Şefi'),
                         ('Mutfak Sorumlusu', 'Mutfak Sorumlusu'), ('Mutfak Personeli', 'Mutfak Personeli'),
                         ('Personel', 'Personel')],
                default='Personel', max_length=20, verbose_name='Rol'),
        ),
        migrations.AlterField(
            model_name='vardiya',
            name='vardiya_tipi',
            field=models.CharField(
                choices=[('Sabahçı', 'Sabahçı'), ('Aracı', 'Aracı'), ('Akşamcı', 'Akşamcı'),
                         ('Mutfak Görevi', 'Mutfak Görevi (Şube Ataması)'),
                         ('İzinli', 'Haftalık İzin'), ('Yıllık İzin', 'Yıllık İzin'),
                         ('Raporlu', 'Raporlu'), ('Devamsız', 'Devamsız')],
                default='Sabahçı', max_length=20, verbose_name='Vardiya Tipi'),
        ),
        migrations.AddField(
            model_name='vardiya',
            name='atanan_sube',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='mutfak_gorevleri', to='panel.sube',
                                    verbose_name='Atanan Şube (Mutfak Personeli)'),
        ),
        migrations.CreateModel(
            name='MutfakZayi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('personel_ad_arsiv', models.CharField(blank=True, default='', max_length=160)),
                ('foto', models.FileField(upload_to='mutfak_zayi/%Y/%m/%d/', verbose_name='Görüntü')),
                ('aciklama', models.TextField(blank=True, default='', verbose_name='Açıklama')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('personel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mutfak_zayileri', to='panel.personel', verbose_name='Yükleyen')),
                ('sube', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mutfak_zayileri', to='panel.sube', verbose_name='Şube')),
            ],
            options={'verbose_name': 'Mutfak Zayi', 'verbose_name_plural': 'Mutfak Zayileri', 'ordering': ['-olusturma']},
        ),
        migrations.CreateModel(
            name='MutfakMaliyetKalemi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ad', models.CharField(max_length=120, unique=True, verbose_name='Ürün Adı')),
                ('kg_fiyat', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Kg Fiyatı (₺)')),
                ('guncelleme', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Maliyet Kalemi', 'verbose_name_plural': 'Maliyet Kalemleri', 'ordering': ['ad']},
        ),
        migrations.CreateModel(
            name='MutfakTarif',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ad', models.CharField(max_length=160, verbose_name='Tarif / Ürün Adı')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('guncelleme', models.DateTimeField(auto_now=True)),
                ('olusturan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mutfak_tarifleri', to='panel.personel')),
            ],
            options={'verbose_name': 'Tarif', 'verbose_name_plural': 'Tarifler', 'ordering': ['ad']},
        ),
        migrations.CreateModel(
            name='MutfakTarifKalemi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('miktar_gram', models.DecimalField(decimal_places=1, max_digits=10, verbose_name='Miktar (gram)')),
                ('tarif', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kalemler', to='panel.mutfaktarif')),
                ('urun', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='panel.mutfakmaliyetkalemi')),
            ],
            options={'verbose_name': 'Tarif Kalemi', 'verbose_name_plural': 'Tarif Kalemleri'},
        ),
    ]
