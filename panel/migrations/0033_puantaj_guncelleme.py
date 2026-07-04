import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0032_magaza_muduru_kullanici_backfill'),
    ]

    operations = [
        migrations.AddField(
            model_name='puantaj',
            name='guncelleme',
            field=models.DateTimeField(auto_now=True, null=True, blank=True),
        ),
    ]
