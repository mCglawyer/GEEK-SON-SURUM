"""Tamamlanmış denetimlerin genel puanını yeni kurala göre yeniden hesaplar: boş bırakılan madde 0 puan sayılır."""
from django.db import migrations


def ileri(apps, schema_editor):
    Denetim = apps.get_model('panel', 'Denetim')
    for d in Denetim.objects.filter(tamamlandi=True).prefetch_related('cevaplar'):
        cev = list(d.cevaplar.all())
        if cev:
            d.toplam_puan = round(sum(c.puan or 0 for c in cev) / (len(cev) * 5) * 100, 1)
            d.save(update_fields=['toplam_puan'])


class Migration(migrations.Migration):
    dependencies = [('panel', '0074_temizlik_tuketime_tasi')]
    operations = [migrations.RunPython(ileri, migrations.RunPython.noop)]
