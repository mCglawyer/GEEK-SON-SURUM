import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0024_puantaj_yillik_gun'),
    ]

    operations = [
        migrations.AddField(
            model_name='egitimdokuman',
            name='sube',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='egitim_dokumanlari', to='panel.sube',
                                    verbose_name='Şube (boş=tüm şubeler)'),
        ),
        migrations.AddField(
            model_name='egitimsoru',
            name='sube',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='egitim_sorulari', to='panel.sube',
                                    verbose_name='Şube (boş=tüm şubeler)'),
        ),
        migrations.AddField(
            model_name='egitimayar',
            name='acik_subeler',
            field=models.ManyToManyField(blank=True, related_name='egitim_acik', to='panel.sube'),
        ),
    ]
