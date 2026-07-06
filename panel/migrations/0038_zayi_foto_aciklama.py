from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0037_profil_dogumgunu_mesai_qr'),
    ]

    operations = [
        migrations.AddField(
            model_name='zayi',
            name='aciklama',
            field=models.CharField(blank=True, default='', max_length=300, verbose_name='Açıklama'),
        ),
        migrations.AddField(
            model_name='zayi',
            name='foto',
            field=models.FileField(blank=True, null=True, upload_to='zayi/%Y/%m/%d/', verbose_name='Fotoğraf'),
        ),
    ]
