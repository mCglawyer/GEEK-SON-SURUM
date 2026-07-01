from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0023_egitimdurum_son_cevaplar'),
    ]

    operations = [
        migrations.AddField(
            model_name='puantaj',
            name='yillik_gun',
            field=models.IntegerField(default=0, verbose_name='Yıllık İzin Gün'),
        ),
    ]
