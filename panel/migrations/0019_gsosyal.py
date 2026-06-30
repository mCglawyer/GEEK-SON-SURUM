from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0018_duyuru'),
    ]

    operations = [
        migrations.CreateModel(
            name='GSosyalGonderi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yazan_ad', models.CharField(default='', max_length=120)),
                ('metin', models.TextField(blank=True, default='')),
                ('gorsel', models.ImageField(blank=True, null=True, upload_to='gsosyal/')),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('yazan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gsosyal_gonderiler', to='panel.personel')),
            ],
            options={
                'ordering': ['-olusturma'],
            },
        ),
        migrations.CreateModel(
            name='GSosyalTepki',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(default='👍', max_length=8)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('gonderi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tepkiler', to='panel.gsosyalgonderi')),
                ('personel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gsosyal_tepkiler', to='panel.personel')),
            ],
            options={
                'unique_together': {('gonderi', 'personel')},
            },
        ),
    ]
