import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panel", "0069_menu_acilis")]

    operations = [
        migrations.CreateModel(
            name="MenuSube",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kod", models.SlugField(max_length=40, verbose_name="Kod")),
                ("ad", models.CharField(max_length=80, verbose_name="Şube adı")),
                ("sira", models.PositiveIntegerField(default=0)),
                ("aktif", models.BooleanField(default=True, verbose_name="QR menüde seçilebilsin")),
                ("marka", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="menu_subeleri", to="panel.menumarka")),
            ],
            options={"verbose_name": "QR Menü Şubesi", "verbose_name_plural": "QR Menü Şubeleri",
                     "ordering": ["sira", "ad", "id"], "unique_together": {("marka", "kod")}},
        ),
        migrations.AddField(
            model_name="menuurun", name="gizli_subeler",
            field=models.ManyToManyField(blank=True, related_name="gizli_urunler", to="panel.menusube", verbose_name="Satılmadığı şubeler"),
        ),
    ]
