from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Mutfak Maliyet Hesaplama modülüne birim desteği eklendi:
    - MutfakMaliyetKalemi.kg_fiyat -> fiyat (rename) + yeni 'birim' alanı (kg/litre/adet, varsayılan kg)
    - MutfakTarifKalemi.miktar_gram -> miktar (rename), anlamı artık ürünün birimine göre değişir
      (kg için gram, litre için ml, adet için tam sayı).

    Mevcut kayıtlar: rename işlemleri veri kaybetmez, sadece kolon adı değişir.
    Var olan tüm MutfakMaliyetKalemi kayıtları varsayılan olarak 'kg' birimine sahip olacak
    (zaten hepsi kg_fiyat ile girilmişti), bu yüzden mevcut tariflerin maliyet hesabı değişmez.
    """

    dependencies = [
        ('panel', '0041_zayi_kaldir'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mutfakmaliyetkalemi',
            old_name='kg_fiyat',
            new_name='fiyat',
        ),
        migrations.AlterField(
            model_name='mutfakmaliyetkalemi',
            name='fiyat',
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Birim Fiyatı (₺)'),
        ),
        migrations.AddField(
            model_name='mutfakmaliyetkalemi',
            name='birim',
            field=models.CharField(
                choices=[('kg', 'Kg (gram bazlı)'), ('litre', 'Litre (ml bazlı)'), ('adet', 'Adet (tam sayı)')],
                default='kg', max_length=10, verbose_name='Birim'),
        ),
        migrations.RenameField(
            model_name='mutfaktarifkalemi',
            old_name='miktar_gram',
            new_name='miktar',
        ),
        migrations.AlterField(
            model_name='mutfaktarifkalemi',
            name='miktar',
            field=models.DecimalField(decimal_places=1, max_digits=10, verbose_name='Miktar'),
        ),
    ]
