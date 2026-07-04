import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0033_puantaj_guncelleme'),
    ]

    operations = [
        migrations.AddField(
            model_name='puantaj',
            name='personel_ad_soyad_arsiv',
            field=models.CharField(blank=True, default='', max_length=160, verbose_name='Personel (arşiv)'),
        ),
        migrations.AddField(
            model_name='puantaj',
            name='sube_arsiv',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='panel.sube', verbose_name='Şube (arşiv)'),
        ),
        migrations.AlterField(
            model_name='puantaj',
            name='personel',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='puantajlar', to='panel.personel'),
        ),
    ]
