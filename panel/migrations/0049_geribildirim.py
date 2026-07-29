import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0048_ilginhaber_sektor_ilgili'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeriBildirim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kategori', models.CharField(choices=[('Öneri', 'Öneri'), ('Şikayet', 'Şikayet'), ('Diğer', 'Diğer')],
                                              default='Öneri', max_length=20)),
                ('metin', models.TextField(default='')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('durum', models.CharField(choices=[('Yeni', 'Yeni'), ('İnceleniyor', 'İnceleniyor'), ('Çözüldü', 'Çözüldü')],
                                           default='Yeni', max_length=20)),
                ('yonetim_notu', models.TextField(blank=True, default='')),
                ('sube', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                           related_name='+', to='panel.sube')),
            ],
            options={
                'ordering': ['-olusturma'],
                'verbose_name': 'Geri Bildirim',
                'verbose_name_plural': 'Geri Bildirimler',
            },
        ),
    ]
