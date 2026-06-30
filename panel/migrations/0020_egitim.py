from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0019_gsosyal'),
    ]

    operations = [
        migrations.CreateModel(
            name='EgitimDokuman',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kategori', models.CharField(choices=[('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon')], default='RECETE', max_length=20)),
                ('baslik', models.CharField(default='', max_length=160)),
                ('dosya', models.FileField(upload_to='egitim/')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('aktif', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['kategori', '-olusturma'],
            },
        ),
        migrations.CreateModel(
            name='EgitimSoru',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kategori', models.CharField(choices=[('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon')], default='RECETE', max_length=20)),
                ('metin', models.TextField(default='')),
                ('sik_a', models.CharField(default='', max_length=300)),
                ('sik_b', models.CharField(default='', max_length=300)),
                ('sik_c', models.CharField(blank=True, default='', max_length=300)),
                ('sik_d', models.CharField(blank=True, default='', max_length=300)),
                ('dogru', models.CharField(default='A', max_length=1)),
                ('aktif', models.BooleanField(default=True)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-olusturma'],
            },
        ),
        migrations.CreateModel(
            name='EgitimDurum',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tamamlandi', models.BooleanField(default=False)),
                ('gecti', models.BooleanField(default=False)),
                ('son_puan', models.IntegerField(default=0)),
                ('deneme', models.IntegerField(default=0)),
                ('sozlesme_onayli', models.BooleanField(default=False)),
                ('tarih', models.DateTimeField(auto_now=True)),
                ('personel', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='egitim_durum', to='panel.personel')),
            ],
        ),
    ]
