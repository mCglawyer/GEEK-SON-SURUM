import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Şube denetim sistemi: DenetimBolum, DenetimMadde, Denetim, DenetimCevap."""

    dependencies = [
        ('panel', '0045_manuel_giris'),
    ]

    operations = [
        migrations.CreateModel(
            name='DenetimBolum',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ad', models.CharField(max_length=200)),
                ('sira', models.PositiveIntegerField(default=0)),
                ('aktif', models.BooleanField(default=True)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Denetim Bölümü',
                'verbose_name_plural': 'Denetim Bölümleri',
                'ordering': ['sira', 'id'],
            },
        ),
        migrations.CreateModel(
            name='DenetimMadde',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metin', models.CharField(max_length=500)),
                ('sira', models.PositiveIntegerField(default=0)),
                ('aktif', models.BooleanField(default=True)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('bolum', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='maddeler', to='panel.denetimbolum')),
            ],
            options={
                'verbose_name': 'Denetim Maddesi',
                'verbose_name_plural': 'Denetim Maddeleri',
                'ordering': ['sira', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Denetim',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('baslangic', models.DateTimeField(auto_now_add=True)),
                ('bitis', models.DateTimeField(blank=True, null=True)),
                ('tamamlandi', models.BooleanField(default=False)),
                ('toplam_puan', models.FloatField(blank=True, null=True, verbose_name='Toplam Puan (yüzde)')),
                ('denetleyen', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                 related_name='+', to='panel.personel')),
                ('sube', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                          related_name='denetimler', to='panel.sube')),
            ],
            options={
                'verbose_name': 'Şube Denetimi',
                'verbose_name_plural': 'Şube Denetimleri',
                'ordering': ['-baslangic'],
            },
        ),
        migrations.CreateModel(
            name='DenetimCevap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puan', models.IntegerField(blank=True, null=True)),
                ('not_metni', models.CharField(blank=True, default='', max_length=500)),
                ('foto', models.ImageField(blank=True, null=True, upload_to='denetim/fotolar/')),
                ('denetim', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='cevaplar', to='panel.denetim')),
                ('madde', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='+', to='panel.denetimmadde')),
            ],
            options={
                'verbose_name': 'Denetim Cevabı',
                'verbose_name_plural': 'Denetim Cevapları',
                'ordering': ['id'],
            },
        ),
    ]
