import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0036_lavabo_denetim'),
    ]

    operations = [
        migrations.AddField(
            model_name='personel',
            name='dogum_tarihi',
            field=models.DateField(blank=True, null=True, verbose_name='Doğum Tarihi'),
        ),
        migrations.AddField(
            model_name='personel',
            name='cinsiyet',
            field=models.CharField(blank=True, choices=[('E', 'Erkek'), ('K', 'Kadın')], default='', max_length=1, verbose_name='Cinsiyet'),
        ),
        migrations.AddField(
            model_name='personel',
            name='profil_foto',
            field=models.ImageField(blank=True, null=True, upload_to='profil/', verbose_name='Profil Fotoğrafı'),
        ),
        migrations.CreateModel(
            name='DogumGunuKutlama',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tarih', models.DateField()),
                ('personel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dogum_kutlamalari', to='panel.personel')),
            ],
        ),
        migrations.AddConstraint(
            model_name='dogumgunukutlama',
            constraint=models.UniqueConstraint(fields=('personel', 'tarih'), name='unique_dogum_kutlama'),
        ),
        migrations.CreateModel(
            name='SubeMesaiToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=32, unique=True)),
                ('sube', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mesai_token', to='panel.sube')),
            ],
        ),
        migrations.CreateModel(
            name='MesaiKayit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('personel_ad_arsiv', models.CharField(blank=True, default='', max_length=160)),
                ('giris', models.DateTimeField()),
                ('cikis', models.DateTimeField(blank=True, null=True)),
                ('personel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mesai_kayitlari', to='panel.personel')),
                ('sube', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mesai_kayitlari', to='panel.sube')),
            ],
            options={'ordering': ['-giris']},
        ),
    ]
