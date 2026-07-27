from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0047_gsosyal_gorseller_ve_haberler'),
    ]

    operations = [
        migrations.AddField(
            model_name='ilginhaber',
            name='sektor_ilgili',
            field=models.BooleanField(default=False, verbose_name='Gıda/Kahve Sektörüyle İlgili'),
        ),
    ]
