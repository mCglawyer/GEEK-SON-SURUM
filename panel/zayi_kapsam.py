"""Mutfak zayi — kim hangi şubelerin zayisini görür / girer.

Tek doğruluk kaynağı burasıdır: sayfa, rapor, Excel/PDF, menüdeki bağlantı ve
kayıt silme hep aynı kapsam fonksiyonunu kullanır; böylece bir rolün görüp
indirebildiği şubeler ile ekranda gördükleri asla birbirinden ayrışmaz.

Kural: yalnızca "Mutfağı var" işaretli (ve depo olmayan) şubeler kapsama girer.
"""
from .models import Rol, Sube, Vardiya, VardiyaTipi

# Zayiyi YAZABİLEN roller
ZAYI_GIRIS_ROLLERI = (Rol.MUTFAK_PERSONEL, Rol.MUTFAK_SORUMLUSU)

# Zayiyi GÖRÜP rapor (Excel / PDF) alabilen roller
ZAYI_RAPOR_ROLLERI = (
    Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI,
    Rol.MAGAZA_MUDURU, Rol.SEF, Rol.MUTFAK_SORUMLUSU,
)

# Her şubenin zayisini görenler (şube sınırı yok)
_TUM_SUBELER = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.MUTFAK_SORUMLUSU)


def mutfakli_subeler():
    return Sube.objects.filter(mutfak_var=True, depo_mu=False).order_by('ad')


def zayi_subeleri(personel):
    """Bu kişinin zayisini görebileceği (mutfaklı) şubeler — liste.

    Bölge Müdürü: sorumlu şubeleri. Mağaza Müdürü: sorumlu şubeleri varsa onlar,
    yoksa kendi şubesi (vardiya ekranlarındaki _yon_subeler ile aynı). Şef: kendi
    şubesi. Mutfak personeli: yalnızca kendi çalıştığı şube (aşağıda).
    """
    if personel is None:
        return []
    qs = mutfakli_subeler()
    if personel.rol in _TUM_SUBELER:
        return list(qs)
    if personel.rol == Rol.MUDUR:
        return list(qs.filter(id__in=personel.sorumlu_subeler.values_list('id', flat=True)))
    if personel.rol == Rol.MAGAZA_MUDURU:
        if personel.sorumlu_subeler.exists():
            return list(qs.filter(id__in=personel.sorumlu_subeler.values_list('id', flat=True)))
        return list(qs.filter(id=personel.sube_id)) if personel.sube_id else []
    if personel.rol == Rol.SEF:
        return list(qs.filter(id=personel.sube_id)) if personel.sube_id else []
    if personel.rol == Rol.MUTFAK_PERSONEL:
        sube = personel_giris_subesi(personel)
        return [sube] if sube else []
    return []


def personel_giris_subesi(personel, tarih=None):
    """Mutfak personelinin zayiyi yazacağı şube: bugünkü 'Mutfak Görevi' atamasının
    şubesi, yoksa kendi şubesi. Şubede mutfak işaretli değilse None döner."""
    from django.utils import timezone
    tarih = tarih or timezone.localdate()
    atama = (Vardiya.objects.filter(personel=personel, tarih=tarih,
                                    vardiya_tipi=VardiyaTipi.MUTFAK_GOREVI)
             .select_related('atanan_sube').first())
    sube = (atama.atanan_sube if atama and atama.atanan_sube_id else None) or personel.sube
    if sube is None or not sube.mutfak_var or sube.depo_mu:
        return None
    return sube


def zayi_menusu_gorunur(personel):
    """Menüde 'Mutfak Zayi' bağlantısı gösterilsin mi?
    Mutfakta çalışanlar her zaman görür (şube atanmamışsa sayfa nedenini açıklar).
    Diğer roller yalnızca kapsamlarında en az bir mutfaklı şube varsa görür."""
    if personel is None:
        return False
    if personel.rol in (Rol.MUTFAK_PERSONEL, Rol.MUTFAK_SORUMLUSU):
        return True
    if personel.rol not in ZAYI_RAPOR_ROLLERI:
        return False
    return bool(zayi_subeleri(personel))
