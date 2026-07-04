import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0035_egitim_icecek_kategori'),
    ]

    operations = [
        migrations.CreateModel(
            name='LavaboDenetim',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('giren_ad', models.CharField(blank=True, max_length=100, verbose_name='Yükleyen (ad)')),
                ('foto', models.FileField(upload_to='lavabo/%Y/%m/%d/', verbose_name='Görüntü')),
                ('olusturma', models.DateTimeField(auto_now_add=True, verbose_name='Yüklendiği An')),
                ('giren', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='lavabo_denetimleri', to='panel.personel', verbose_name='Yükleyen')),
                ('sube', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                          related_name='lavabo_denetimleri', to='panel.sube', verbose_name='Şube')),
            ],
            options={'verbose_name': 'Lavabo Denetimi', 'verbose_name_plural': 'Lavabo Denetimleri', 'ordering': ['-olusturma']},
        ),
    ]
