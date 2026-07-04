from django.contrib.auth.hashers import make_password
from django.db import migrations


def backfill_kullanicilar(apps, schema_editor):
    Personel = apps.get_model('panel', 'Personel')
    User = apps.get_model('auth', 'User')
    for p in Personel.objects.filter(rol='Mağaza Müdürü', user__isnull=True):
        if not p.giris_kodu:
            continue
        uname = "kod_%s" % p.giris_kodu
        try:
            u = User.objects.filter(username=uname).first()
            if u is None:
                u = User.objects.create(username=uname, password=make_password(None))
            p.user = u
            p.save(update_fields=['user'])
        except Exception:
            pass


def geri_al(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0031_magaza_muduru_insaat_sablon'),
    ]

    operations = [
        migrations.RunPython(backfill_kullanicilar, geri_al),
    ]
