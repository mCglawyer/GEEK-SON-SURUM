from django.db import migrations, models


class Migration(migrations.Migration):
    """Geek Academy için 3 yeni içerik kategorisi (Geek Tarihçesi, Hijyen/Temizlik
    Standartları, Müşteri İlişkileri/Servis Eğitimi) — mevcut RECETE/ORYANTASYON/
    ICECEK kategorilerinin yanına ekleniyor. Var olan hiçbir kayıt etkilenmiyor."""

    dependencies = [
        ('panel', '0054_musteri_degerlendirme'),
    ]

    operations = [
        migrations.AlterField(
            model_name='egitimdokuman',
            name='kategori',
            field=models.CharField(
                choices=[('RECETE', 'Reçete'), ('ORYANTASYON', 'Oryantasyon'), ('ICECEK', 'İçecek Hazırlama'),
                         ('TARIHCE', 'Geek Tarihçesi'), ('HIJYEN', 'Hijyen/Temizlik Standartları'),
                         ('SERVIS', 'Müşteri İlişkileri/Servis Eğitimi')],
                default='RECETE', max_length=20),
        ),
    ]
