from django.db import migrations

SQL = """
DO $$
BEGIN
    -- panel_puantaj: personel_ad_soyad_arsiv
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='panel_puantaj' AND column_name='personel_ad_soyad_arsiv'
    ) THEN
        ALTER TABLE panel_puantaj ADD COLUMN personel_ad_soyad_arsiv varchar(160) NOT NULL DEFAULT '';
    END IF;

    -- panel_puantaj: sube_arsiv_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='panel_puantaj' AND column_name='sube_arsiv_id'
    ) THEN
        ALTER TABLE panel_puantaj ADD COLUMN sube_arsiv_id bigint NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='panel_puantaj' AND constraint_name='panel_puantaj_sube_arsiv_id_fk'
    ) THEN
        ALTER TABLE panel_puantaj ADD CONSTRAINT panel_puantaj_sube_arsiv_id_fk
            FOREIGN KEY (sube_arsiv_id) REFERENCES panel_sube(id) ON DELETE SET NULL;
    END IF;

    -- panel_puantaj: guncelleme (0033)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='panel_puantaj' AND column_name='guncelleme'
    ) THEN
        ALTER TABLE panel_puantaj ADD COLUMN guncelleme timestamp with time zone NULL;
    END IF;

    -- panel_mesaikayit: personel_ad_arsiv (0037)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='panel_mesaikayit') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='panel_mesaikayit' AND column_name='personel_ad_arsiv'
        ) THEN
            ALTER TABLE panel_mesaikayit ADD COLUMN personel_ad_arsiv varchar(160) NOT NULL DEFAULT '';
        END IF;
    END IF;

    -- panel_mutfakzayi: personel_ad_arsiv (0039)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='panel_mutfakzayi') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='panel_mutfakzayi' AND column_name='personel_ad_arsiv'
        ) THEN
            ALTER TABLE panel_mutfakzayi ADD COLUMN personel_ad_arsiv varchar(160) NOT NULL DEFAULT '';
        END IF;
    END IF;

    -- panel_personel: profil alanlari (0037)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='panel_personel' AND column_name='dogum_tarihi'
    ) THEN
        ALTER TABLE panel_personel ADD COLUMN dogum_tarihi date NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='panel_personel' AND column_name='cinsiyet'
    ) THEN
        ALTER TABLE panel_personel ADD COLUMN cinsiyet varchar(1) NOT NULL DEFAULT '';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='panel_personel' AND column_name='profil_foto'
    ) THEN
        ALTER TABLE panel_personel ADD COLUMN profil_foto varchar(100) NULL;
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0039_mutfak_sistemi'),
    ]

    operations = [
        migrations.RunSQL(sql=SQL, reverse_sql=migrations.RunSQL.noop),
    ]
