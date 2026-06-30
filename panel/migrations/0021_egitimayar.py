from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0020_egitim'),
    ]

    operations = [
        migrations.AddField(
            model_name='egitimdurum',
            name='son_sorular',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.CreateModel(
            name='EgitimAyar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acik', models.BooleanField(default=False)),
                ('guncelleme', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
