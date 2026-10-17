/* Geek Bilgi Yarışması — soru bankası: Genel Kültür. Satır biçimi: zorluk|soru|DOĞRU|yanlış|yanlış|yanlış|açıklama */
(function (g) {
  var GK = g.GeekKosu = g.GeekKosu || {};
  (GK.sorular = GK.sorular || []).push({ k: 'genel', ad: 'Genel Kültür', q: `
1|Bir haftada kaç gün vardır?|7|5|6|8|Hafta yedi günden oluşur; bu düzen eski Babil takvimine dayanır.
1|Bir saat kaç dakikadır?|60|100|30|90|Saat 60 dakikaya, dakika 60 saniyeye bölünür; bu düzen Sümer ve Babil'in altmışlık sayı sisteminden gelir.
1|Gökkuşağının ilk rengi hangisidir?|Kırmızı|Mavi|Yeşil|Sarı|Gökkuşağı renkleri dıştan içe kırmızı, turuncu, sarı, yeşil, mavi, lacivert, mor olarak sıralanır.
1|Türkçede alfabemizde kaç harf vardır?|29|26|32|28|Türk alfabesi 29 harften oluşur; 1928'deki Harf Devrimi ile Latin alfabesi temel alınarak oluşturuldu.
1|Hangi ay 28 veya 29 gün çeker?|Şubat|Mart|Nisan|Ocak|Şubat normal yıllarda 28, artık yıllarda 29 gündür.
1|Hangi renk trafik ışığında "dur" anlamına gelir?|Kırmızı|Yeşil|Sarı|Mavi|Kırmızı ışık durmayı, yeşil geçişi, sarı dikkat etmeyi bildirir.
1|Bir üçgenin iç açılarının toplamı kaç derecedir?|180|90|360|270|Öklid geometrisinde her üçgenin iç açılarının toplamı 180 derecedir.
1|Hangi sayı tek sayıdır?|7|8|12|20|Tek sayılar 2'ye tam bölünmez; 7 bunlardan biridir.
1|"Merhaba" demenin İngilizcesi nedir?|Hello|Goodbye|Thanks|Sorry|"Hello" selamlaşmak için kullanılan en yaygın İngilizce sözcüktür.
1|Bir futbol topu genellikle hangi biçimdedir?|Küre|Küp|Silindir|Piramit|Futbol topu küre biçimindedir; yüzeyi genellikle beşgen ve altıgen parçalardan oluşur.
2|Kaç tane kıta vardır (en yaygın kabul edilen sayıya göre)?|7|5|6|9|Asya, Afrika, Kuzey Amerika, Güney Amerika, Antarktika, Avrupa ve Avustralya/Okyanusya olarak 7 kıta sayılır.
2|Roma rakamlarıyla X sayısı kaçı gösterir?|10|5|50|100|Roma rakamlarında I=1, V=5, X=10, L=50, C=100, D=500, M=1000'dir.
2|Pi sayısı yaklaşık kaçtır?|3,14|2,72|1,61|9,81|Pi, bir çemberin çevresinin çapına oranıdır ve yaklaşık 3,14159'dur.
2|Sıfır hangi uygarlıkta ilk kez bir sayı olarak kullanılmıştır?|Hint|Roma|Eski Yunan|Viking|Sıfır kavramı Hindistan'da gelişti ve Arap matematikçiler aracılığıyla Avrupa'ya yayıldı.
2|Dünyada en çok konuşulan anadil hangisidir?|Mandarin Çincesi|İngilizce|İspanyolca|Hintçe|Anadil olarak en çok konuşulan dil Mandarin'dir; İngilizce ise ikinci dil olarak en yaygın dildir.
2|Hicri takvim neye dayanır?|Ay'ın hareketine|Güneş'in hareketine|Yıldızların konumuna|Mevsimlere|Hicri takvim kameri (ay) yıla dayanır; yaklaşık 354 gündür. Bu yüzden bayramlar her yıl miladi takvimde yaklaşık 11 gün erken kutlanır.
2|Zeus hangi mitolojinin baş tanrısıdır?|Yunan|Mısır|Roma|Viking|Zeus Olimpos tanrılarının başıdır; Roma karşılığı Jüpiter'dir.
2|Hangi ay 31 gün çeker?|Temmuz|Haziran|Eylül|Nisan|Temmuz ve Ağustos art arda gelen iki 31 günlük aydır.
2|Hangi renkler karıştırıldığında yeşil elde edilir (boyada)?|Mavi ve sarı|Kırmızı ve mavi|Kırmızı ve sarı|Siyah ve beyaz|Mavi ve sarı pigmentler karıştırılınca yeşil oluşur.
2|Hangi sayı asaldır?|13|15|21|27|Asal sayı yalnızca 1'e ve kendisine bölünebilir; 13 asaldır, diğerleri böyle değildir.
2|Bir kilogram kaç gramdır?|1000|100|10|10000|Kilogram metrik sistemde kütle birimidir ve 1000 grama eşittir; "kilo" Yunanca "bin" anlamına gelir.
3|Sokrates'in öğrencisi olan ve Akademi'yi kuran filozof kimdir?|Platon|Aristoteles|Diogenes|Epikuros|Platon, Sokrates'in öğrencisi ve Aristoteles'in öğretmenidir.
3|"Düşünüyorum, öyleyse varım" sözü kime aittir?|Descartes|Kant|Nietzsche|Spinoza|René Descartes 17. yüzyılda "Cogito, ergo sum" ifadesini ortaya koydu.
3|Hangi dil dünyada en çok ülkede resmî dildir?|İngilizce|Fransızca|İspanyolca|Arapça|İngilizce 50'den fazla ülkede resmî dildir.
3|Hangi kültürde "Diwali" ışık festivali kutlanır?|Hindu|Budist|Hristiyan|Yahudi|Diwali, kötülüğe karşı iyiliğin zaferini simgeleyen Hindu ışık festivalidir.
3|Norveç efsanelerinde Thor hangi gücün tanrısıdır?|Gök gürültüsü|Deniz|Güneş|Ölüm|Thor, çekicini kullanan Viking mitolojisinin gök gürültüsü tanrısıdır.
3|Fibonacci dizisinin ilk sayıları hangisidir?|1, 1, 2, 3, 5, 8|1, 2, 4, 8, 16|2, 4, 6, 8|1, 3, 5, 7|Fibonacci dizisinde her sayı kendinden önceki iki sayının toplamıdır.
3|Hangi hayvan Çin takviminde 12 hayvandan biri değildir?|Kedi|Ejderha|Fare|Maymun|Çin zodyağı: fare, öküz, kaplan, tavşan, ejderha, yılan, at, koyun, maymun, horoz, köpek, domuz. Kedi yer almaz.
3|Dünyanın en eski yazılı destanlarından biri hangisidir?|Gılgamış Destanı|Odysseia|İlyada|Mahabharata|Gılgamış Destanı yaklaşık MÖ 2000'lere dayanır ve Mezopotamya'da çivi yazısıyla yazıldı.
3|UNESCO'nun açılımında "U" harfi neyi simgeler?|United (Birleşmiş)|Universal|Union|Utility|UNESCO "Birleşmiş Milletler Eğitim, Bilim ve Kültür Örgütü"dür.
3|Birleşmiş Milletler'in genel merkezi hangi şehirdedir?|New York|Cenevre|Paris|Brüksel|BM genel merkezi 1952'den beri New York'tadır; Cenevre'de de büyük bir ofisi vardır.
3|Nobel ödülleri hangi ülkede verilir (Barış hariç)?|İsveç|Norveç|Danimarka|Finlandiya|Nobel Barış Ödülü Oslo'da (Norveç), diğer ödüller Stockholm'de (İsveç) verilir.
3|Nobel ödüllerini başlatan Alfred Nobel hangi buluşuyla bilinir?|Dinamit|Telefon|Radyo|Barut|Alfred Nobel 1867'de dinamiti patentledi; servetini ödüllere bırakmıştır.
4|Türkiye'nin 29 Ekim'de kutladığı bayram nedir?|Cumhuriyet Bayramı|Zafer Bayramı|Çocuk Bayramı|Gençlik Bayramı|29 Ekim 1923'te Cumhuriyet'in ilanı her yıl bu tarihte kutlanır.
4|Felsefede "Mağara Alegorisi"ni kim anlatır?|Platon|Aristoteles|Kant|Nietzsche|Platon, "Devlet" adlı eserinde gerçeklik ve bilgi üzerine mağara alegorisini anlatır.
4|Matematikte bir çemberin alanı hangi formülle bulunur?|πr²|2πr|πd|r²/2|Çemberin alanı π × yarıçap² iken çevresi 2πr'dir.
4|Pisagor teoremi neyi anlatır?|Dik üçgende a²+b²=c²|Üçgenin açılarını|Çemberi|Küp hacmini|Pisagor teoremi dik üçgende iki kısa kenarın karelerinin toplamının hipotenüsün karesine eşit olduğunu söyler.
4|"Altın oran" yaklaşık kaçtır?|1,618|3,14|2,718|1,414|Altın oran φ ≈ 1,618'dir; doğada ve sanatta sıkça anılır.
4|Meksika'da "Ölüler Günü" kutlaması hangi geleneğin parçasıdır?|Atalar ve ölenleri anma|Hasat bayramı|Bağımsızlık günü|Yeni yıl|Día de los Muertos, ölen yakınları renkli sunaklar, yemekler ve şekerli kafataslarıyla anan bir Meksika geleneğidir.
4|Hangi dil Latince kökenli değildir?|Macarca|İspanyolca|İtalyanca|Fransızca|Macarca Fin-Ugor dil ailesindendir; diğerleri Roman dillerindendir.
4|Sanskritçe hangi dil ailesine yakın bir antik dildir?|Hint-Avrupa|Sami|Türk|Fin-Ugor|Sanskritçe Hint-Avrupa dil ailesindendir; Latince ve Yunanca ile akrabadır.
5|Schrödinger hangi alanda Nobel kazanmıştır?|Fizik|Kimya|Edebiyat|Tıp|Erwin Schrödinger 1933'te Nobel Fizik Ödülü'nü Paul Dirac ile paylaştı.
5|Gordion Düğümü'nü kılıçla kesen komutan kimdir?|Büyük İskender|Cengiz Han|Jül Sezar|Napolyon|Efsaneye göre düğümü çözen Asya'ya hükmedecekti; İskender kılıcıyla keserek bunu çözdü.
5|Euler sayısı e yaklaşık kaçtır?|2,718|3,14|1,618|0,577|e doğal logaritmanın tabanıdır; yaklaşık 2,71828'dir.
5|Dünya Sağlık Örgütü'nün merkezi hangi şehirdedir?|Cenevre|Paris|New York|Londra|WHO'nun genel merkezi İsviçre'nin Cenevre şehrindedir.
5|Aristoteles'in öğrencisi olan ve geniş bir imparatorluk kuran hükümdar kimdir?|Büyük İskender|Hannibal|Jül Sezar|Mısır Firavunu Ramses|Aristoteles, Makedonya Kralı II. Philippos'un daveti üzerine genç İskender'e öğretmenlik yaptı.
` });
})(typeof window !== 'undefined' ? window : globalThis);
