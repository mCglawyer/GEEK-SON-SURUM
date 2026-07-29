from django.db import migrations


class Migration(migrations.Migration):
    """Kullanıcı karar değiştirdi: kimlik hiç kimseye (Operatör dahil)
    gösterilmeyecek. Bunu sadece arayüzde gizlemek yerine, veritabanı
    şemasından tamamen kaldırıyoruz ki 'kaydedilmiyor' iddiası gerçek olsun."""

    dependencies = [
        ('panel', '0050_geribildirim_gonderen_yetkilisi'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='geribildirim',
            name='gonderen',
        ),
    ]
