from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0022_pushabonelik'),
    ]

    operations = [
        migrations.AddField(
            model_name='egitimdurum',
            name='son_cevaplar',
            field=models.TextField(blank=True, default=''),
        ),
    ]
