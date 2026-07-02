import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0026_alter_vardiya_vardiya_tipi'),
    ]

    operations = [
        migrations.CreateModel(
            name='MolaQRAyar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acik', models.BooleanField(default=False)),
                ('guncelleme', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubeMolaToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('sube', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mola_token', to='panel.sube')),
            ],
        ),
        migrations.CreateModel(
            name='MolaOturum',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sure_dk', models.IntegerField(default=45)),
                ('baslangic', models.DateTimeField()),
                ('bitis', models.DateTimeField(blank=True, null=True)),
                ('uyarildi', models.BooleanField(default=False)),
                ('personel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mola_oturumlari', to='panel.personel')),
                ('sube', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mola_oturumlari', to='panel.sube')),
            ],
            options={'ordering': ['-baslangic']},
        ),
    ]
