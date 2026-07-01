from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0021_egitimayar'),
    ]

    operations = [
        migrations.CreateModel(
            name='PushAbonelik',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.TextField(unique=True)),
                ('veri', models.TextField()),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('personel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='push_abonelikleri', to='panel.personel')),
            ],
        ),
    ]
