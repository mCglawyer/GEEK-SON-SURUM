import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Geek Crew: çoklu görsel (ızgara) desteği için GSosyalGorsel, ve
    slider için onay bekleyen/yayınlanan ilginç haberleri tutan IlginHaber."""

    dependencies = [
        ('panel', '0046_denetim_sistemi'),
    ]

    operations = [
        migrations.CreateModel(
            name='GSosyalGorsel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gorsel', models.ImageField(upload_to='gsosyal/')),
                ('sira', models.PositiveIntegerField(default=0)),
                ('gonderi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                              related_name='gorseller', to='panel.gsosyalgonderi')),
            ],
            options={
                'ordering': ['sira', 'id'],
            },
        ),
        migrations.CreateModel(
            name='IlginHaber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('baslik', models.CharField(default='', max_length=300)),
                ('link', models.URLField(blank=True, default='', max_length=500)),
                ('kaynak', models.CharField(blank=True, default='', max_length=120)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('onaylandi', models.BooleanField(default=False)),
                ('onay_tarihi', models.DateTimeField(blank=True, null=True)),
                ('onaylayan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                related_name='+', to='panel.personel')),
            ],
            options={
                'ordering': ['-olusturma'],
                'verbose_name': 'İlginç Haber',
                'verbose_name_plural': 'İlginç Haberler',
            },
        ),
    ]
