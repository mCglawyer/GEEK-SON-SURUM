from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("panel", "0067_oyunskor"),
    ]

    operations = [
        migrations.AddField(
            model_name="oyunskor",
            name="mod",
            field=models.CharField(db_index=True, default="kosu", max_length=10),
        ),
    ]
