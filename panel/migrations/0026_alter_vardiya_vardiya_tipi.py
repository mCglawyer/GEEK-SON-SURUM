from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0025_egitim_sube'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vardiya',
            name='vardiya_tipi',
            field=models.CharField(
                choices=[('Sabahçı', 'Sabahçı'), ('Aracı', 'Aracı'), ('Akşamcı', 'Akşamcı'),
                         ('İzinli', 'Haftalık İzin'), ('Yıllık İzin', 'Yıllık İzin'),
                         ('Raporlu', 'Raporlu'), ('Devamsız', 'Devamsız')],
                default='Sabahçı', max_length=20, verbose_name='Vardiya Tipi'),
        ),
    ]
