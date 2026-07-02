from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0027_mola_qr'),
    ]

    operations = [
        migrations.AddField(
            model_name='molaoturum',
            name='kullanilan_dk',
            field=models.IntegerField(blank=True, null=True, verbose_name='Kullanılan Süre (dk)'),
        ),
    ]
