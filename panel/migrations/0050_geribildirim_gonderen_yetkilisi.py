import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0049_geribildirim'),
    ]

    operations = [
        migrations.AddField(
            model_name='personel',
            name='geri_bildirim_yetkilisi',
            field=models.BooleanField(default=False, verbose_name='Geri Bildirim Görüntüleme Yetkisi',
                                      help_text=('İşaretliyse (genelde tek bir Bölge Müdürü için kullanılır): '
                                                 'Genel Müdür/Operatör dışında bu kişi de Geri Bildirim '
                                                 'Yönetimi sayfasına erişebilir.')),
        ),
        migrations.AddField(
            model_name='geribildirim',
            name='gonderen',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='+', to='panel.personel',
                                    verbose_name='Gönderen (sadece Operatör görebilir)'),
        ),
    ]
