import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("panel", "0066_anket_google_yorum"),
    ]

    operations = [
        migrations.CreateModel(
            name="OyunSkor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("skor", models.PositiveIntegerField()),
                ("sure_sn", models.PositiveIntegerField(default=0)),
                ("zaman", models.DateTimeField(auto_now_add=True)),
                ("personel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="oyun_skorlari", to="panel.personel")),
            ],
            options={
                "verbose_name": "Oyun skoru",
                "verbose_name_plural": "Oyun skorları",
                "ordering": ["-zaman"],
                "indexes": [
                    models.Index(fields=["zaman"], name="panel_oyuns_zaman_idx"),
                    models.Index(fields=["personel", "-skor"], name="panel_oyuns_pers_skor_idx"),
                ],
            },
        ),
    ]
