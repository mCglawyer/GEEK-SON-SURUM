"""QR menü alerjen listesi yönetimi (marka bazında)."""
from .menu_sema import ALERJEN_ETIKET, MARKALAR


def hazirla(marka):
    """Markanın sitede sütunu olan (sistem) alerjenlerini yoksa oluşturur."""
    from .models import MenuAlerjen
    mevcut = set(MenuAlerjen.objects.filter(marka=marka).values_list('kod', flat=True))
    for i, kod in enumerate(MARKALAR[marka.kod]['alerjenler'], 1):
        if kod not in mevcut:
            MenuAlerjen.objects.create(marka=marka, kod=kod, ad=ALERJEN_ETIKET.get(kod, kod),
                                       sistem=True, sira=i * 10)


def liste(marka):
    from .models import MenuAlerjen
    hazirla(marka)
    return list(MenuAlerjen.objects.filter(marka=marka))


def pasif_sistem(marka):
    """Menüden kaldırılmış sistem alerjenlerinin kodları."""
    from .models import MenuAlerjen
    return set(MenuAlerjen.objects.filter(marka=marka, sistem=True, aktif=False).values_list('kod', flat=True))


def aktif_ekler(marka):
    from .models import MenuAlerjen
    return list(MenuAlerjen.objects.filter(marka=marka, sistem=False, aktif=True))
