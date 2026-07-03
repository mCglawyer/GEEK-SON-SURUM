import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0028_molaoturum_kullanilan_dk'),
    ]

    operations = [
        migrations.CreateModel(
            name='InsaatProje',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ad', models.CharField(max_length=160, verbose_name='Yeni Şube / Proje Adı')),
                ('tamamlandi', models.BooleanField(default=False, verbose_name='Proje Tamamlandı')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('guncelleme', models.DateTimeField(auto_now=True)),
                ('olusturan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                related_name='olusturdugu_insaat', to='panel.personel')),
                ('sorumlu', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                              related_name='insaat_projeleri', to='panel.personel',
                                              verbose_name='Sorumlu Bölge Müdürü')),
            ],
            options={'ordering': ['-olusturma']},
        ),
        migrations.CreateModel(
            name='InsaatMadde',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metin', models.CharField(max_length=300, verbose_name='Görev')),
                ('durum', models.CharField(choices=[('yapilmadi', 'Yapılmadı'), ('devam', 'Devam Ediyor'), ('tamam', 'Tamamlandı')], default='yapilmadi', max_length=12)),
                ('aciklama', models.TextField(blank=True, default='', verbose_name='Not')),
                ('sira', models.IntegerField(default=0)),
                ('guncelleme', models.DateTimeField(auto_now=True)),
                ('proje', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maddeler', to='panel.insaatproje')),
            ],
            options={'ordering': ['sira', 'id']},
        ),
    ]
