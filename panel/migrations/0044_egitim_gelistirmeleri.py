import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Eğitim sistemi genişletmesi:
    - EgitimAyar: soru_sayisi / sure_sn / gecme_puan alanları eklendi (artık kod içinde
      sabit değil, Eğitmen/Operatör panelden değiştirebiliyor).
    - EgitimSoru: 'tur' alanı eklendi (Çoktan Seçmeli / Açık Uçlu). Açık uçlu sorularda
      şıklar boş kalabildiği için sik_a/sik_b/dogru artık zorunlu değil (blank=True).
    - EgitimDurum: 'inceleme_bekliyor' alanı eklendi — açık uçlu soru içeren bir deneme,
      eğitmen/operatör puanlayana kadar bu durumda kalır.
    - EgitimAcikCevap: yeni model — açık uçlu sorulara verilen yazılı cevapları ve
      puanlama bilgisini tutar.
    """

    dependencies = [
        ('panel', '0043_mola_kaldir'),
    ]

    operations = [
        migrations.AddField(
            model_name='egitimayar',
            name='soru_sayisi',
            field=models.PositiveIntegerField(default=10, verbose_name='Soru Sayısı'),
        ),
        migrations.AddField(
            model_name='egitimayar',
            name='sure_sn',
            field=models.PositiveIntegerField(default=20, verbose_name='Soru Başına Süre (sn)'),
        ),
        migrations.AddField(
            model_name='egitimayar',
            name='gecme_puan',
            field=models.PositiveIntegerField(default=6, verbose_name='Geçme İçin Gereken Doğru Sayısı'),
        ),
        migrations.AddField(
            model_name='egitimsoru',
            name='tur',
            field=models.CharField(
                choices=[('coktan_secmeli', 'Çoktan Seçmeli'), ('acik_uclu', 'Açık Uçlu (Yazılı Cevap)')],
                default='coktan_secmeli', max_length=20, verbose_name='Soru Türü'),
        ),
        migrations.AlterField(
            model_name='egitimsoru',
            name='sik_a',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AlterField(
            model_name='egitimsoru',
            name='sik_b',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AlterField(
            model_name='egitimsoru',
            name='dogru',
            field=models.CharField(blank=True, default='A', max_length=1),
        ),
        migrations.AddField(
            model_name='egitimdurum',
            name='inceleme_bekliyor',
            field=models.BooleanField(default=False, verbose_name='Yazılı sorular inceleme bekliyor'),
        ),
        migrations.CreateModel(
            name='EgitimAcikCevap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deneme_no', models.IntegerField(default=1)),
                ('cevap_metni', models.TextField(blank=True, default='')),
                ('puanlandi', models.BooleanField(default=False)),
                ('dogru_mu', models.BooleanField(blank=True, null=True)),
                ('puanlama_notu', models.CharField(blank=True, default='', max_length=300)),
                ('olusturma', models.DateTimeField(auto_now_add=True)),
                ('puanlama_tarihi', models.DateTimeField(blank=True, null=True)),
                ('personel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                               related_name='egitim_acik_cevaplari', to='panel.personel')),
                ('puanlayan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                related_name='+', to='panel.personel')),
                ('soru', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='+', to='panel.egitimsoru')),
            ],
            options={
                'verbose_name': 'Açık Uçlu Cevap',
                'verbose_name_plural': 'Açık Uçlu Cevaplar',
                'ordering': ['-olusturma'],
            },
        ),
    ]
