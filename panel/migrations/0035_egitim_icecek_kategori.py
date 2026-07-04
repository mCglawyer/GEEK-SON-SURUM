from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0034_puantaj_arsiv_kalici'),
    ]

    operations = [
        migrations.AlterField(
            model_name='egitimdokuman',
            name='kategori',
            field=models.CharField(
                choices=[('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon'), ('ICECEK', 'İçecek Hazırlama')],
                default='RECETE', max_length=20),
        ),
    ]
