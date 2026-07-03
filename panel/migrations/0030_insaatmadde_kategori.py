from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0029_insaat'),
    ]

    operations = [
        migrations.AddField(
            model_name='insaatmadde',
            name='kategori',
            field=models.CharField(choices=[('urun', 'Ürün ve Ekipman'), ('insaat', 'İnşaat Süreci')],
                                   default='urun', max_length=12, verbose_name='Kategori'),
        ),
    ]
