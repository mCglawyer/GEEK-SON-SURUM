import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Academy favorileri (EgitimFavori) ve video kapak resmi alanı
    (EgitimDokuman.kapak) ekleniyor."""

    dependencies = [
        ('panel', '0055_academy_kategoriler'),
    ]

    operations = [
        migrations.AddField(
            model_name='egitimdokuman',
            name='kapak',
            field=models.ImageField(blank=True, null=True, upload_to='egitim/kapak/', verbose_name='Video Kapak Resmi'),
        ),
        migrations.CreateModel(
            name='EgitimFavori',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('dokuman', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='favorileyenler', to='panel.egitimdokuman')),
                ('personel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name='egitim_favorileri', to='panel.personel')),
            ],
            options={
                'verbose_name': 'Academy Favorisi',
                'verbose_name_plural': 'Academy Favorileri',
                'unique_together': {('personel', 'dokuman')},
            },
        ),
    ]
