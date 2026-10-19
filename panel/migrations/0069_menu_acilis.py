from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("panel", "0068_oyunskor_mod"),
    ]

    operations = [
        migrations.AddField(model_name="menumarka", name="acilis_aktif",
                            field=models.BooleanField(default=True, verbose_name="Açılış görseli gösterilsin")),
        migrations.AddField(model_name="menumarka", name="acilis_sure_sn",
                            field=models.PositiveSmallIntegerField(default=5, verbose_name="Her görsel kaç saniye görünsün")),
        migrations.AddField(model_name="menumarka", name="acilis_atlanabilir",
                            field=models.BooleanField(default=True, verbose_name="Dokununca geçilebilsin")),
        migrations.AddField(model_name="menumarka", name="acilis_gunde_bir",
                            field=models.BooleanField(default=False, verbose_name="Aynı müşteriye günde bir kez göster")),
        migrations.AddField(model_name="menumarka", name="acilis_son_yayin",
                            field=models.DateTimeField(blank=True, null=True, verbose_name="Açılış Görseli Son Yayın")),
        migrations.AddField(model_name="menumarka", name="acilis_yayin_hata",
                            field=models.CharField(blank=True, default="", max_length=400, verbose_name="Açılış Yayın Hatası")),
        migrations.CreateModel(
            name="MenuAcilisGorsel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gorsel", models.ImageField(upload_to="menu/acilis/", verbose_name="Görsel")),
                ("baslik", models.CharField(blank=True, default="", max_length=80, verbose_name="Ad (yalnızca panelde görünür)")),
                ("aktif", models.BooleanField(default=True, verbose_name="Yayında")),
                ("baslangic", models.DateField(blank=True, null=True, verbose_name="Başlangıç tarihi")),
                ("bitis", models.DateField(blank=True, null=True, verbose_name="Bitiş tarihi")),
                ("sira", models.PositiveIntegerField(default=0)),
                ("olusturma", models.DateTimeField(auto_now_add=True)),
                ("marka", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acilis_gorselleri", to="panel.menumarka")),
            ],
            options={"verbose_name": "QR Açılış Görseli", "verbose_name_plural": "QR Açılış Görselleri", "ordering": ["sira", "id"]},
        ),
    ]
