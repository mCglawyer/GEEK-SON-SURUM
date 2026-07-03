from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0030_insaatmadde_kategori'),
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
                         ('Personel', 'Personel')],
                default='Personel', max_length=20, verbose_name='Rol'),
        ),
        migrations.CreateModel(
            name='InsaatSablonMadde',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kategori', models.CharField(choices=[('urun', 'Ürün ve Ekipman'), ('insaat', 'İnşaat Süreci')], default='urun', max_length=12, verbose_name='Kategori')),
                ('metin', models.CharField(max_length=300, verbose_name='Görev')),
                ('sira', models.IntegerField(default=0)),
            ],
            options={'ordering': ['kategori', 'sira', 'id']},
        ),
    ]
