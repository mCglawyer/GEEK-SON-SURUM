from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panel", "0070_menu_subeler")]

    operations = [
        migrations.AddField(
            model_name="personel", name="menu_yetkilisi",
            field=models.BooleanField(default=False, verbose_name="QR Menü Yönetimi Yetkisi",
                                      help_text="İşaretliyse (genelde Bölge Müdürü için): Genel Müdür/Operatör/Yatırımcı dışında bu kişi de QR Menü Yönetimi sayfalarına erişebilir. Ekip sayfasından verilir/alınır."),
        ),
    ]
