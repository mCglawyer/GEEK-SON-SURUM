/* Geek Bilgi Yarışması — soru bankası: Spor. Satır biçimi: zorluk|soru|DOĞRU|yanlış|yanlış|yanlış|açıklama */
(function (g) {
  var GK = g.GeekKosu = g.GeekKosu || {};
  (GK.sorular = GK.sorular || []).push({ k: 'spor', ad: 'Spor', q: `
1|Futbolda bir takım sahada kaç oyuncuyla oynar?|11|9|10|12|Futbol maçında her takım sahada kaleci dahil 11 oyuncuyla yer alır.
1|Basketbolda bir sayı atmak için top nereye atılır?|Potaya|Kaleye|Ağa|Çembere ve pistin dışına|Basketbolda top, 3,05 metre yükseklikteki çemberden (pota) geçirilerek sayı yapılır.
1|Olimpiyat Oyunları kaç yılda bir yapılır?|4|2|3|5|Yaz Olimpiyatları dört yılda bir düzenlenir; antik çağdaki Olimpiyatlar da dört yılda bir yapılırdı.
1|Voleybol oyununda net üstünden top nasıl aşırılır?|Vurularak|Tekmelenerek|Atılarak|Yuvarlanarak|Voleybol, topu el ve kollarla ağın üzerinden rakip sahaya aktarmaya dayanır.
1|Tenis hangi aletle oynanır?|Raket|Sopa|Kürek|Bat|Tenis raketle oynanır; top ağın üzerinden rakip alana gönderilir.
1|Maraton koşusu yaklaşık kaç kilometredir?|42,195|21|10|50|Maraton 42,195 km'dir. Mesafe 1908 Londra Olimpiyatları'nda standartlaştı.
1|Futbolda oyun kaç dakika sürer (normal süre)?|90|60|80|120|Futbol maçı 2×45 dakikadır; uzatmalarda 2×15 dakika eklenir.
1|Yüzmede kolların aynı anda öne atıldığı, yunus hareketli stil hangisidir?|Kelebek|Sırtüstü|Kurbağalama|Serbest|Kelebek stilinde iki kol birlikte öne atılır ve bacaklar yunus gibi dalgalanır; en zorlu yüzme stillerinden biridir.
1|Güreşte Türkiye'nin en köklü geleneksel güreş türü hangisidir?|Yağlı güreş|Sumo|Boks|Judo|Kırkpınar Yağlı Güreşleri 1346'dan beri yapılan, dünyanın en eski spor organizasyonlarından biri olarak kabul edilir.
1|Basketbolun vazgeçilmez ligi NBA hangi ülkededir?|ABD|İspanya|Brezilya|Türkiye|NBA, ABD ve Kanada'daki takımlardan oluşan profesyonel basketbol ligidir.
1|Futbol Dünya Kupası kaç yılda bir yapılır?|4|2|3|5|FIFA Dünya Kupası dört yılda bir yapılır; ilk turnuva 1930'da Uruguay'da oynandı.
1|Hangi spor "buz üzerinde" sopayla oynanır?|Buz hokeyi|Golf|Kriket|Beyzbol|Buz hokeyi, paten ve sopayla oynanır; hedef diski rakip kaleye sokmaktır.
1|Bisiklet yarışlarının en ünlüsü olan "Tour de France" hangi ülkede yapılır?|Fransa|İtalya|İspanya|Belçika|Tour de France, 1903'ten beri yapılan etap yarışıdır.
1|Futbolda hakemin kırmızı kart göstermesi ne anlama gelir?|Oyuncunun oyundan atılması|Uyarı|Taç atışı|Penaltı|Kırmızı kart gören oyuncu sahadan çıkar ve takım eksik oynar.
1|Golf oyununda oyuncular topu neye sokmaya çalışır?|Deliğe|Ağa|Çembere|Kaleye|Golf'te amaç, topu en az vuruşla sırayla deliklere sokmaktır.
1|Hangi spor dalı "kayak" ile yapılır?|Alp disiplini|Dalış|Okçuluk|Eskrim|Kayak (ski), karlı yamaçlarda özel ayakkabı ve kayaklarla yapılır.
1|Okçulukta hedef nesnesine ne denir?|Hedef (puan tahtası)|Pota|Ağ|Delik|Okçuluk, ok ve yayla hedefe isabet ettirme sporudur.
1|Türkiye'de en çok takip edilen spor hangisidir?|Futbol|Golf|Beyzbol|Kriket|Futbol Türkiye'de en yaygın ve en çok izlenen spordur.
1|Satranç tahtasında kaç kare vardır?|64|36|81|100|Satranç tahtası 8×8 = 64 karedir; sırayla açık ve koyu renklidir.
1|Voleybolda bir takımda sahada kaç oyuncu vardır?|6|5|7|11|Voleybolda her takım sahada 6 oyuncuyla yer alır.
2|2002 Dünya Kupası'nda Türkiye kaçıncı oldu?|Üçüncü|İkinci|Birinci|Dördüncü|Türkiye, 2002'de Güney Kore'de oynanan turnuvada üçüncülük maçında Güney Kore'yi 3-2 yenerek üçüncü oldu.
2|Basketbolda üç sayılık çizgi dışından atılan basket kaç sayıdır?|3|2|1|4|Üç sayı çizgisinin dışından yapılan atış 3 sayı kazandırır.
2|Hangi spor Wimbledon turnuvasıyla özdeşleşir?|Tenis|Golf|Kriket|Ragbi|Wimbledon, Londra'da çim kortlarda oynanan en eski Grand Slam turnuvasıdır.
2|Formula 1'in en prestijli sokak pistlerinden biri olan Monte Carlo hangi ülkededir?|Monako|Fransa|İtalya|İspanya|Monako Grand Prix'i dar ve virajlı sokak pistiyle takvimin en prestijli yarışlarındandır.
2|Rekortmen sporcu Usain Bolt hangi dalda ünlüdür?|100 metre koşusu|Yüzme|Uzun atlama|Boks|Usain Bolt 100 m'de 9,58 sn ile dünya rekoru sahibidir (2009).
2|Michael Phelps hangi sporda rekortmendir?|Yüzme|Atletizm|Jimnastik|Boks|Phelps, Olimpiyat tarihinin en çok madalya kazanan sporcusudur (28 madalya, 23 altın).
2|Futbolda "hat-trick" ne demektir?|Bir oyuncunun bir maçta 3 gol atması|Üç sarı kart|Üç penaltı|Üç korner|Hat-trick, bir oyuncunun aynı maçta üç gol atmasıdır.
2|Galatasaray Spor Kulübü hangi yıl kurulmuştur?|1905|1903|1907|1923|Galatasaray 1905'te İstanbul'da kuruldu. Beşiktaş 1903'te, Fenerbahçe 1907'de kuruldu.
2|Basketbolda bir takım sahada kaç oyuncuyla oynar?|5|6|7|11|Basketbolda her takım sahada 5 oyuncuyla bulunur.
2|NBA'de efsane "Michael Jordan" hangi takımla altı şampiyonluk kazandı?|Chicago Bulls|Los Angeles Lakers|Boston Celtics|Miami Heat|Jordan, 1991–1993 ve 1996–1998'de Bulls ile altı NBA şampiyonluğu kazandı.
2|Hangi spor dalında "ace" terimi kullanılır?|Tenis|Futbol|Boks|Yüzme|Ace, tenis ve voleybolda rakibin dokunamadığı servis anlamına gelir.
2|Kırkpınar Yağlı Güreşleri hangi ilde yapılır?|Edirne|Konya|Sivas|Kayseri|Kırkpınar güreşleri Edirne'de Sarayiçi'nde her yıl yapılır.
2|2012 Londra Olimpiyatları hangi yıl yapılmıştır?|2012|2008|2016|2020|2012 Londra Olimpiyatları 27 Temmuz–12 Ağustos arasında yapıldı.
2|Hangi ülke en çok Dünya Kupası kazanmış futbol ülkesidir?|Brezilya|Almanya|İtalya|Arjantin|Brezilya beş kez (1958, 1962, 1970, 1994, 2002) kupayı kaldırdı.
2|Futbolda penaltı noktası kaleden kaç metre uzaktadır?|11|9|7|16|Penaltı noktası kale çizgisinin 11 metre (12 yarda) önündedir.
2|Atletizmde 4×100 metre bir ne tür yarıştır?|Bayrak yarışı|Engelli koşu|Maraton|Yürüyüş|4×100 m bayrak yarışında dört atlet sırayla koşar ve sopayı birbirine aktarır.
2|Hangi Türk sporcu Olimpiyatlarda halterde "Cep Herkülü" olarak bilinir?|Naim Süleymanoğlu|Halil Mutlu|Taner Sağır|Hamza Yerlikaya|Naim Süleymanoğlu 1988, 1992 ve 1996'da üç kez olimpiyat şampiyonu oldu.
2|Hangi spor "gol çizgisi" ve "pas" gibi terimler içerir?|Futbol|Boks|Yüzme|Eskrim|Gol çizgisi, pas, korner futbolda sık kullanılır.
2|Judo hangi ülkede doğmuştur?|Japonya|Çin|Kore|Tayland|Judo, 1882'de Jigoro Kano tarafından Japonya'da geliştirildi.
2|Hangi spor için "forehand" ve "backhand" terimleri kullanılır?|Tenis|Futbol|Voleybol|Yüzme|Tenis'te raketin ön yüzü forehand, arka yüzü backhand darbesi olarak adlandırılır.
2|Futbol Dünya Kupası'nın ilk şampiyonu hangi ülkedir?|Uruguay|Brezilya|İtalya|Arjantin|1930'da Uruguay hem ev sahibi hem de şampiyon oldu.
3|Türk milli takımı 2008 Avrupa Futbol Şampiyonası'nda hangi turda elendi?|Yarı final|Çeyrek final|Final|Grup aşaması|Türkiye 2008'de Almanya'ya yarı finalde 3-2 yenildi.
3|Fenerbahçe, Galatasaray ve Beşiktaş hangi şehir takımıdır?|İstanbul|Ankara|İzmir|Bursa|Üç büyük kulüp İstanbul'dadır. Fenerbahçe 1907, Galatasaray 1905, Beşiktaş 1903'te kuruldu.
3|Hakan Şükür'ün Dünya Kupası rekoru nedir?|Turnuva tarihindeki en hızlı gol|En çok gol|En genç oyuncu|En çok maç|Hakan Şükür, 2002'de Güney Kore karşısında 11. saniyede gol attı; Dünya Kupası'nın en hızlı golü olarak kayıtlara geçti.
3|Satrançta hangi taş sadece çapraz hareket eder?|Fil|Kale|At|Vezir|Fil çapraz hareket eder; kale düz, at "L" biçiminde gider.
3|Wimbledon'da hangi zemin kullanılır?|Çim|Toprak|Sert zemin|Halı|Wimbledon, geleneksel olarak çim kortlarda oynanır. Roland Garros ise toprak kortlardadır.
3|Grand Slam turnuvalarından Roland Garros hangi şehirdedir?|Paris|Londra|New York|Melbourne|Roland Garros (Fransa Açık) Paris'te toprak kortlarda oynanır.
3|Tenisin dört büyük Grand Slam turnuvasından biri değildir?|Dubai Açık|Wimbledon|ABD Açık|Avustralya Açık|Grand Slam'ler Avustralya Açık, Roland Garros, Wimbledon ve ABD Açık'tır.
3|Messi hangi ülkenin milli futbolcusudur?|Arjantin|Brezilya|İspanya|Portekiz|Lionel Messi Arjantin milli takımıyla 2022'de Dünya Kupası'nı kazandı.
3|Cristiano Ronaldo hangi ülke milli takımında oynar?|Portekiz|İspanya|Brezilya|İtalya|Ronaldo Portekiz milli takımıyla 2016'da Avrupa Şampiyonu oldu.
3|2008'de NBA'de "En Çok Gelişen Oyuncu" ödülünü alan Türk basketbolcu kimdir?|Hidayet Türkoğlu|Enes Kanter|Cedi Osman|Ersan İlyasova|Hidayet Türkoğlu 2008'de Orlando Magic formasıyla bu ödülü kazanan ilk Türk oyuncu oldu.
3|Formula 1'de rekor 7 kez dünya şampiyonu olan pilotlardan biri kimdir?|Michael Schumacher|Ayrton Senna|Fernando Alonso|Sebastian Vettel|Schumacher 1994–2004 arası 7 kez dünya şampiyonu oldu; Lewis Hamilton da 7 şampiyonlukla eşitledi.
3|Bir futbol sahasının ortasında hangi şekil bulunur?|Daire|Üçgen|Kare|Dikdörtgen|Orta saha çizgisinin ortasında başlama noktası ve etrafında 9,15 m yarıçaplı daire vardır.
3|Hokey sporunda oyuncular topu nasıl taşır?|Sopayla|Elle|Ayakla|Kafayla|Hokeyde (çim veya buz) oyuncular topu ya da diski sopayla yönlendirir.
3|Olimpiyat halkaları kaç tanedir?|5|4|6|7|Beş halka beş kıtayı simgeler; mavi, sarı, siyah, yeşil ve kırmızı renklidir.
3|Modern Olimpiyatlar hangi şehirde başladı (1896)?|Atina|Paris|Londra|Roma|İlk modern Olimpiyat Oyunları 1896'da Atina'da yapıldı; fikri Pierre de Coubertin gerçekleştirdi.
3|Basketbolu icat eden kişi kimdir?|James Naismith|Michael Jordan|Wilt Chamberlain|John Wooden|Naismith 1891'de ABD'de basketbolu icat etti; ilk oyunda şeftali sepetleri kullanıldı.
3|Voleybolun mucidi kimdir?|William G. Morgan|James Naismith|Walter Camp|Pierre de Coubertin|William Morgan 1895'te Massachusetts'te voleybolu "mintonette" adıyla geliştirdi.
3|Spor tarihinde ilk kez 10 numara alan Nadia Comaneci hangi sporda mükemmel puan aldı?|Jimnastik|Yüzme|Atletizm|Eskrim|Comaneci 1976 Montreal Olimpiyatları'nda barda 10 aldı; skorbord 10'u göstermediği için 1.00 yazdı.
3|Dünya Kupası'nı 1966'da kazanan ülke hangisidir?|İngiltere|Almanya|Brezilya|İtalya|İngiltere, ev sahibi olarak 1966'da Batı Almanya'yı yenip tek Dünya Kupası'nı aldı.
4|Türkiye Futbol Federasyonu'nun temeli hangi yıl atıldı?|1923|1900|1950|1960|Türkiye Futbol Federasyonu'nun kökeni 1923'te kurulan Türkiye Futbol Heyeti'ne uzanır.
4|İlk Avrupa Futbol Şampiyonası hangi yıl yapıldı?|1960|1930|1980|1992|İlk Avrupa Şampiyonası 1960'ta Fransa'da yapıldı; Sovyetler Birliği kazandı.
4|Avrupa'nın en prestijli kulüp kupası olan Şampiyonlar Ligi'ni en çok hangi kulüp kazanmıştır?|Real Madrid|Barcelona|Milan|Bayern Münih|Real Madrid, Avrupa Kupası/Şampiyonlar Ligi'ni rekor sayıda kez kazandı; ilk beş şampiyonluğu 1956–1960 arasında üst üste aldı.
4|Hangi ülke ragbide "All Blacks" ile tanınır?|Yeni Zelanda|Avustralya|Güney Afrika|İngiltere|Yeni Zelanda ragbi milli takımı siyah formasıyla "All Blacks" olarak tanınır; maç öncesi Haka dansı yaparlar.
4|Maradona'nın 1986 Dünya Kupası'ndaki "Tanrı'nın Eli" golü hangi takıma karşı atıldı?|İngiltere|Almanya|Brezilya|İtalya|Maradona, 1986 çeyrek finalinde İngiltere'ye karşı eliyle gol attı ve aynı maçta "yüzyılın golü"nü de kaydetti.
4|Pelé kaç kez Dünya Kupası kazanmıştır?|3|1|2|5|Pelé 1958, 1962 ve 1970'te Brezilya ile üç Dünya Kupası kazanan tek oyuncudur.
4|Muhammed Ali hangi sporun efsanesidir?|Boks|Güreş|Judo|Karate|Muhammed Ali "Yüzyılın sporcusu" sayılır; "Kelebek gibi uçar, arı gibi sokarım" sözüyle bilinir.
4|1954 Dünya Kupası finali "Bern Mucizesi" olarak anılır; kazanan hangi ülkedir?|Batı Almanya|Macaristan|Brezilya|Uruguay|Batı Almanya, favori Macaristan'ı 3-2 yendi.
4|Maraton rekoru sahibi, Kenyalı atlet olan ve ilk kez 2 saatin altında koşan sporcu kimdir?|Eliud Kipchoge|Mo Farah|Haile Gebrselassie|Paul Tergat|Kipchoge 2019'da özel koşulda maratonu 1:59:40'ta koştu; resmi rekoru ise ayrıca vardır.
4|Tüm zamanların en çok Grand Slam kazanan erkek tenisçileri arasında yer alan İsviçreli kimdir?|Roger Federer|Rafael Nadal|Andy Murray|Stan Wawrinka|Federer 20 Grand Slam şampiyonluğu kazandı.
4|Kırkpınar'ın başpehlivanı ödülü olarak ne verilir?|Altın kemer|Kupa|Madalya|Para|Başpehlivan'a altın kemer verilir; ayrıca üç kez üst üste kazanana kemer kalıcı olur.
4|Futbol kuralları ilk kez hangi ülkede yazıya döküldü?|İngiltere|Brezilya|Fransa|İtalya|1863'te Londra'da Football Association kuruldu ve kurallar yazıya geçirildi.
4|Hangi spor "ippon" terimini kullanır?|Judo|Karate|Eskrim|Tenis|İppon, judoda tam puan sayılan ve maçı bitiren hareket demektir.
4|1970'te Brezilya'ya kalıcı olarak verilen Dünya Kupası trofesinin adı nedir?|Jules Rimet Kupası|FIFA Altın Kupası|Coubertin Kupası|Pelé Kupası|Jules Rimet Kupası 1930–1970 arasında verildi; Brezilya üçüncü şampiyonluğuyla kupayı kalıcı olarak aldı. Bugünkü FIFA Dünya Kupası ise 1974'ten beri kullanılır.
4|Hangi ülke bisiklet sporunda "Giro d'Italia" turuna sahiptir?|İtalya|İspanya|Fransa|Belçika|Giro d'Italia 1909'dan beri yapılan, Mayıs ayında düzenlenen üç büyük etap yarışından biridir.
4|Türk sporcular ilk Olimpiyat altın madalyalarını hangi şehirdeki Oyunlar'da kazandı?|Berlin (1936)|Londra (1948)|Roma (1960)|Atina (1896)|Yaşar Erkan, 1936 Berlin Olimpiyatları'nda güreşte Türkiye'ye ilk olimpiyat altın madalyalarından birini kazandırdı.
4|Kadınlar voleybolunda "Sultanlar Ligi" adı verilen lig hangi ülkededir?|Türkiye|Brezilya|İtalya|Rusya|Türkiye Kadınlar Voleybol Ligi "Sultanlar Ligi" olarak tanınır; Türk kulüpleri Avrupa'da başarılar elde etmiştir.
4|Judoda en yüksek derece hangi renkle simgelenir (dan sistemi)?|Siyah kuşak (ve üstü)|Beyaz kuşak|Sarı kuşak|Yeşil kuşak|Siyah kuşak usta düzeyi simgeler; daha üst dan dereceleri kırmızı-beyaz ya da kırmızı olabilir.
4|NBA'de "Slam Dunk" ne demektir?|Topu doğrudan potaya basmak|Üç sayılık atış|Top çalma|Serbest atış|Smaç (dunk), topun elle yukarıdan doğrudan çemberden geçirilmesidir.
4|Modern eskrimde kullanılan üç silah hangileridir?|Flöre, epe, kılıç|Ok, yay, bıçak|Mızrak, kalkan, balta|Kılıç, bıçak, tüfek|Modern eskrimde üç silah flöre, epe ve kılıç (sabre) olarak ayrılır.
5|Uluslararası Futbol Federasyonları Birliği (FIFA) hangi yıl kuruldu?|1904|1930|1950|1895|FIFA, 21 Mayıs 1904'te Paris'te yedi Avrupa ülkesinin temsilcileriyle kuruldu; ilk Dünya Kupası 1930'da yapıldı.
5|En çok Olimpiyat altın madalyası olan ülke hangisidir?|ABD|Rusya/SSCB|Çin|Almanya|ABD yaz olimpiyatlarında tarihte en çok altın madalya kazanan ülkedir.
5|Bir tenis maçında 40-40 durumuna ne denir?|Düs (Deuce)|Love|Break|Ace|40-40'ta "deuce" denir; bir oyuncunun iki fark yapması gerekir.
5|Bir golf sahasında standart oyunda toplam kaç delik vardır?|18|9|12|24|Standart bir golf sahası 18 delikten oluşur.
5|Kriket hangi ülkede doğmuştur?|İngiltere|Hindistan|Avustralya|Pakistan|Kriket 16. yüzyılda İngiltere'de başladı; Hindistan, Pakistan ve Avustralya'da çok popülerdir.
5|Boks ringinde bir raunt normalde kaç dakikadır (profesyonel)?|3|1|5|10|Profesyonel boksta raunt 3 dakika, rauntlar arası 1 dakikadır.
5|Voleybolda libero oyuncunun görevi nedir?|Savunma ve karşılama uzmanı|Smaç vurmak|Servis atmak|Blok yapmak|Libero farklı renkli forma giyer, hücum etmez, savunma ve karşılamada oynar.
5|Dünya Kupası'nda tek turnuvada en çok gol atan oyuncu kimdir (13 gol, 1958)?|Just Fontaine|Pelé|Gerd Müller|Ronaldo|Fransa'dan Just Fontaine 1958'de 6 maçta 13 gol atarak rekor kırdı.
5|Hakem "ofsayt" bayrağını neye göre kaldırır?|Hücum oyuncusunun, topun ve sondan ikinci savunmacının konumuna göre|Topun yüksekliğine göre|Oyuncunun forma numarasına göre|Oyun süresine göre|Ofsayt, pas anında oyuncunun top ve sondan ikinci rakip oyuncudan daha ileride olmasına dayanır.
5|Sporda "Fair Play" kavramı neyi ifade eder?|Dürüst ve centilmence oyun|Gol atmayı|Süre kazanmayı|Takım seçimini|Fair play, kurallara ve rakibe saygıyı ifade eder; FIFA ve IOC bu ilkeyi ödüllendirir.
5|Kadınlar tenisinde en çok Grand Slam kazanan Avustralyalı kimdir?|Margaret Court|Serena Williams|Steffi Graf|Martina Navratilova|Margaret Court 24 Grand Slam tekler şampiyonluğu kazandı.
5|Spor tarihinde "Dream Team" kavramı hangi Olimpiyat'ta ünlendi?|1992 Barselona (ABD basketbol)|1996 Atlanta|1984 Los Angeles|2000 Sidney|1992'de NBA yıldızlarının ilk kez Olimpiyatlara katılmasıyla oluşan ABD basketbol takımına "Dream Team" denildi.
5|Futbolda Altın Top (Ballon d'Or) ödülünü ilk kazanan oyuncu kimdir?|Stanley Matthews|Pelé|Alfredo Di Stéfano|Johan Cruyff|İngiliz Stanley Matthews, 1956'da ilk Ballon d'Or'u kazandı.
` });
})(typeof window !== 'undefined' ? window : globalThis);
