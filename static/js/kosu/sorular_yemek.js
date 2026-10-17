/* Geek Bilgi Yarışması — soru bankası: Yemek & Mutfak. Satır biçimi: zorluk|soru|DOĞRU|yanlış|yanlış|yanlış|açıklama */
(function (g) {
  var GK = g.GeekKosu = g.GeekKosu || {};
  (GK.sorular = GK.sorular || []).push({ k: 'yemek', ad: 'Yemek & Mutfak', q: `
1|Pizza hangi ülkenin mutfağıyla özdeşleşmiştir?|İtalya|Japonya|Meksika|Hindistan|Modern pizza, 19. yüzyılda Napoli'de ünlendi. Margherita pizza İtalyan bayrağının renklerini taşır.
1|Suşi hangi ülkenin yemeğidir?|Japonya|Çin|Tayland|Kore|Suşi, sirkeli pirinç ve genellikle çiğ balık ya da deniz ürünleriyle yapılan geleneksel bir Japon yemeğidir.
1|Taco hangi ülkenin mutfağında yer alır?|Meksika|İspanya|Arjantin|Peru|Taco, mısır veya buğday tortillasına sarılan malzemelerle yapılan Meksika yemeğidir.
1|Hamburger'in ana malzemelerinden biri nedir?|Köfte (kıyma)|Pirinç|Balık yumurtası|Tofu|Hamburgerde iki ekmek arasında ızgara kıyma köftesi bulunur.
1|Baklava hangi ülkede çok meşhurdur?|Türkiye|Japonya|Brezilya|Finlandiya|Baklava ince yufka, ceviz veya fıstık ve şerbetle yapılan bir tatlıdır; Gaziantep baklavası ünlüdür.
1|Çay Türkiye'de hangi bardakla servis edilir?|İnce belli bardak|Kupa|Şarap kadehi|Plastik şişe|Türk çayı geleneksel olarak ince belli bardakta, tavşan kanı koyulukta servis edilir.
1|Ayran neyin karışımıdır?|Yoğurt, su ve tuz|Süt ve şeker|Su ve nane|Meyve suyu ve buz|Ayran, yoğurdun su ve tuzla çalkalanmasıyla yapılan geleneksel bir içecektir.
1|Hangi meyve sarı renklidir ve ekşidir?|Limon|Çilek|Üzüm|Erik|Limon ekşi tadıyla tanınır ve C vitamini bakımından zengindir.
1|Çikolatanın ana hammaddesi nedir?|Kakao|Kahve|Vanilya|Fındık|Çikolata, kakao ağacının çekirdeklerinden yapılır.
1|Peynirin yapımında hangi içecek kullanılır?|Süt|Su|Çay|Meyve suyu|Peynir sütün mayalanıp pıhtılaştırılmasıyla yapılır.
1|Ekmek hangi tahılın unundan yapılır (en yaygın)?|Buğday|Pirinç|Mısır|Fındık|Türkiye'de ekmeğin çoğu buğday unuyla yapılır.
1|Balıklar hangi ortamda yaşar?|Suda|Çölde|Ormanda|Buzul üzerinde|Balıklar solungaçlarıyla sudaki oksijeni kullanarak solunum yapar.
1|Kahvaltıda genellikle ne tüketilir?|Peynir, zeytin, yumurta|Pilav ve bamya|Kebap ve ayran|Baklava|Türk kahvaltısı peynir, zeytin, yumurta, reçel ve çay içerir.
1|Mercimek çorbası hangi baklagilden yapılır?|Mercimek|Nohut|Fasulye|Bezelye|Mercimek çorbası, Türk mutfağının en sevilen çorbalarındandır.
1|Dondurma hangi mevsimde en çok tüketilir?|Yaz|Kış|Sonbahar|İlkbahar|Dondurma sıcak havalarda ferahlatıcı olduğu için en çok yazın tercih edilir.
1|Hangi içecek kafein içermez?|Su|Çay|Kahve|Kola|Su hiç kafein içermez; çay, kahve ve kola ise az ya da çok kafein içerir.
1|Patates hangi bitkinin kökünden (yumrusundan) elde edilir?|Patates bitkisi|Havuç|Turp|Sarımsak|Patates yer altı yumrusudur; dünyada en çok tüketilen sebzelerdendir.
1|Hangisi bir tatlıdır?|Sütlaç|Mantı|Lahmacun|Pide|Sütlaç; süt, pirinç ve şekerle pişirilen tatlıdır.
1|Domates, biber ve patlıcan hangi gruba girer?|Sebzeler|Baklagiller|Tahıllar|Mantarlar|Bunlar sebze olarak bilinir (botanik olarak meyvedirler).
1|Süt hangi hayvandan elde edilir (en yaygın olarak)?|İnek|Aslan|Kartal|Kurbağa|İnek sütü dünyada en yaygın tüketilen süttür; koyun ve keçi sütü de kullanılır.
2|Lahmacun hangi bölgemizin yemeğidir?|Güneydoğu Anadolu|Karadeniz|Ege|Trakya|Lahmacun ince hamur üzerine baharatlı kıyma sürülerek pişirilir; Gaziantep ve Şanlıurfa'da ünlüdür.
2|İskender kebap hangi şehirle özdeşleşmiştir?|Bursa|Adana|Hatay|Gaziantep|İskender kebap 19. yüzyılda Bursa'da İskender Efendi tarafından yapılmaya başlandı.
2|Hamsi hangi bölgenin en sevilen balığıdır?|Karadeniz|Ege|Akdeniz|Marmara|Hamsi Karadeniz mutfağında kızartma, pilav ve ekmeğe kadar birçok tarifte kullanılır.
2|Mantı genellikle hangi sosla servis edilir?|Yoğurt ve tereyağlı sos|Çikolata sosu|Bal|Soya sosu|Türk mantısı yoğurt, sarımsak ve tereyağında yakılmış pul biberle servis edilir.
2|Menemen hangi malzemelerle yapılır?|Yumurta, domates, biber|Pirinç, fasulye|Un, süt|Süzme yoğurt, nane|Menemen kahvaltıda sevilen yumurtalı bir yemektir; soğanlı-soğansız tartışması meşhurdur.
2|Sushi'de yeşil renkli, acı bir sos olarak kullanılan baharat hangisidir?|Wasabi|Hardal|Zencefil|Susam|Wasabi, Japon turpudan yapılır ve sert, burun yakan bir tadı vardır.
2|Hangi içecek fermente üzümden yapılır?|Şarap|Ayran|Limonata|Süt|Şarap, üzüm suyunun mayalanmasıyla elde edilir; alkollü bir içecektir.
2|Türk mutfağında tarhana neyle yapılır?|Yoğurt, un, sebzeler|Pirinç, bal|Süt, kakao|Yağ, tuz|Tarhana, fermente edilmiş yoğurt-un hamurunun kurutulmasıyla yapılır; çorbası kışın sevilir.
2|Pastırma hangi etten yapılır?|Sığır|Tavuk|Balık|Kuzu başı|Pastırma, sığır etinin çemenle kaplanıp kurutulmasıyla elde edilir; Kayseri pastırması ünlüdür.
2|Zeytinyağlı yemekler genelde nasıl servis edilir?|Soğuk|Çok sıcak|Donmuş|Kızartılmış|Zeytinyağlı yemekler ılık ya da soğuk servis edilir; enginar, dolma, barbunya klasikleridir.
2|Hangisi bir süt ürünüdür?|Kaymak|Mercimek|Bulgur|Bal|Kaymak, sütün yağının toplanmasıyla elde edilir.
2|Tavuk göğsü tatlısı hangi malzemeyle yapılır?|Tavuk göğsü, süt, şeker|Sadece süt|Un ve yumurta|Peynir|Tavuk göğsü, lifleri çıkarılana kadar haşlanır ve sütlü bir tatlıya dönüştürülür; Osmanlı saray mutfağı kökenlidir.
2|Çiğ köfte geleneksel olarak neyle yapılır?|Bulgur ve çiğ et (şimdi etsiz)|Pirinç ve tavuk|Mercimek ve balık|Makarna ve peynir|Şanlıurfa'da geleneksel çiğ köfte çiğ et ve bulgurla yapılırdı; günümüzde sağlık nedeniyle çoğunlukla etsiz yapılır.
2|Fındık üretiminde dünyada ilk sırada hangi ülke yer alır?|Türkiye|İtalya|ABD|Çin|Türkiye, dünya fındık üretiminin yarısından fazlasını karşılar; ürün özellikle Karadeniz kıyısında yetişir.
2|Crocus çiçeğinin tepeciklerinden elde edilen, dünyanın en pahalı baharatı olarak bilinen baharat hangisidir?|Safran|Kimyon|Zerdeçal|Karabiber|Safran, yüz binlerce çiçekten bir kilo ürün verdiği için çok pahalıdır.
2|Pide hangi bölgenin yemeğidir (Karadeniz'de en meşhur)?|Karadeniz|Marmara|Güneydoğu|Ege|Karadeniz pideleri kayık biçimiyle kaşarlı, kıymalı ve yumurtalı çeşitleriyle bilinir.
2|Türk lokumu hangi malzemelerle yapılır?|Şeker, nişasta, su|Süt, yumurta|Un, yağ|Peynir, bal|Lokum şeker şurubu ve nişasta ile kaynatılarak yapılır; fıstık, ceviz, gül ve limon gibi aromalar eklenebilir.
2|Avokado hangi kıtada ilk kez yetiştirilmiştir?|Orta Amerika|Asya|Avrupa|Afrika|Avokado Meksika ve çevresinde binlerce yıl önce yetiştirildi.
2|Bulgur hangi tahıldan elde edilir?|Buğday|Pirinç|Arpa|Mısır|Bulgur haşlanıp kurutulan ve kırılan buğdaydır; pilav ve köfte yapımında kullanılır.
2|Pizza için kullanılan klasik peynir hangisidir?|Mozzarella|Beyaz peynir|Lor|Tulum|Mozzarella eriyince uzaması ve hafif tadıyla pizzanın klasik peynirdir.
2|Kruvasan hangi ülkenin pastanelerinde ünlenmiştir?|Fransa|Almanya|İtalya|Rusya|Kruvasan Avusturya kökenli "kipferl"den uyarlanarak Fransa'da ünlendi.
3|Hangi ülke "Paella" yemeğiyle bilinir?|İspanya|İtalya|Portekiz|Yunanistan|Paella, Valensiya kökenli safranlı pirinç yemeğidir; deniz ürünleri veya tavuk ve tavşan eti eklenir.
3|Kimchi hangi ülkenin geleneksel yemeğidir?|Kore|Çin|Japonya|Vietnam|Kimchi, baharatlı fermente lahana ve sebzelerle yapılan Kore yemeğidir.
3|Fransız mutfağında "Ratatouille" nedir?|Sebze yemeği|Tatlı|Çorba|İçecek|Ratatouille, patlıcan, kabak, biber ve domatesle yapılan Provence kökenli sebze yemeğidir.
3|Mozzarella peyniri ilk hangi hayvanın sütünden yapılırdı?|Manda|İnek|Koyun|Keçi|Orijinal mozzarella di bufala, manda sütünden yapılır.
3|Hangi Japon içeceği pirinçten fermente edilerek elde edilir?|Sake|Matcha|Ramune|Kombu çayı|Sake, pirinç mayalanarak elde edilen geleneksel bir Japon içkisidir.
3|"Umami" hangi tat çeşididir?|Tatlı, tuzlu, ekşi, acıdan ayrı beşinci tat|Acı|Ekşi|Tatlı|Umami, glutamat gibi bileşiklerin verdiği "lezzetli" tat olarak tanımlanır; Kikunae Ikeda 1908'de keşfetti.
3|Baklagillerden hangisi hummusun ana malzemesidir?|Nohut|Mercimek|Fasulye|Bakla|Humus; nohut, tahin, limon ve sarımsakla yapılan Orta Doğu mezesidir.
3|Gazozun ana gazı nedir?|Karbondioksit|Oksijen|Azot|Helyum|Gazlı içeceklerde suya karbondioksit çözülür; açılınca kabarcıklar çıkar.
3|Çay bitkisi (Camellia sinensis) hangi coğrafyada ilk yetiştirildi?|Çin|Brezilya|Avustralya|Kanada|Çay, Çin'de binlerce yıl önce içecek olarak kullanılmaya başlandı.
3|İtalyan mutfağında "tiramisu" hangi malzemeleri içerir?|Kahve, mascarpone, kedi dili bisküvi|Çikolata, portakal|Bal, ceviz|Süt, pirinç|Tiramisu "beni yukarı çek" anlamına gelir; kahveli kedi dili bisküvi ve mascarpone kremasıyla yapılır.
3|Hangi yemek Gürcü mutfağından gelen peynirli ekmeğe verilen addır?|Haçapuri|Pirojki|Börek|Pide|Haçapuri, peynirli Gürcü ekmeğidir; Acara usulüne yumurta eklenir.
3|Paella'da pirinç hangi baharatla sarı renk alır?|Safran|Kırmızı biber|Kimyon|Nane|Safran paella'ya hem renk hem aroma verir.
3|Fransız mutfağında tatlı krepin adı nedir?|Crêpe|Tarte|Éclair|Macaron|Crêpe, ince krep demektir; Bretagne bölgesinde yaygındır.
3|Macarons hangi malzemelerle yapılan bir kurabiyedir?|Badem unu ve yumurta akı|Un ve süt|Bal ve ceviz|Peynir ve yağ|Macaron, iki badem unu bisküvisinin krema ile birleşmesiyle oluşur; Fransız pastane kültürünün simgesidir.
3|"Gazpacho" soğuk bir çorbadır; hangi ülkenin yemeğidir?|İspanya|Meksika|Fransa|İtalya|Gazpacho, domates, salatalık, biber ve zeytinyağıyla yapılan soğuk İspanyol çorbasıdır.
3|Hangi yağ Akdeniz mutfağının temelidir?|Zeytinyağı|Hindistan cevizi yağı|Palmiye yağı|Mısır yağı|Zeytinyağı Akdeniz diyetinin temel yağıdır; kalp sağlığı için olumlu etkileri bilinir.
3|Hangi hayvan "Foie gras" yapımında kullanılır?|Kaz veya ördek|Tavuk|Koyun|Balık|Foie gras, kaz veya ördek karaciğeridir; Fransız mutfağında lüks sayılır, üretimi etik açıdan tartışmalıdır.
3|Fransızcada "chef" kelimesi ne anlama gelir?|Baş, lider|Aşçı yardımcısı|Garson|Tabak|"Chef" Fransızca "baş, lider" demektir; mutfağı yöneten kişiyi anlatır.
3|Mantar hangi canlı grubundandır?|Fungi (mantarlar âlemi)|Bitkiler|Hayvanlar|Bakteriler|Mantarlar ayrı bir âlemdir; bitki ya da hayvan değildir.
3|Tarçın hangi bitkinin kabuğundan elde edilir?|Tarçın ağacı|Zencefil|Vanilya|Biberiye|Tarçın, Cinnamomum cinsi ağaçların iç kabuğundan elde edilir.
3|Su dışında dünyada en çok tüketilen içecek hangisidir?|Çay|Kola|Süt|Meyve suyu|Su dışında en çok tüketilen içecek çaydır; hemen her kıtada günlük yaşamın parçasıdır.
3|Soya fasulyesinden yapılan peynir benzeri gıda nedir?|Tofu|Tahin|Pekmez|Kaymak|Tofu, soya sütünün pıhtılaştırılmasıyla yapılır; Asya mutfağının önemli bir parçasıdır.
4|Köri (curry) hangi mutfağın simgesidir?|Hint mutfağı|Japon mutfağı|İtalyan mutfağı|Fransız mutfağı|Köri, baharat karışımlarıyla yapılan soslu yemeklerin genel adıdır; Hindistan, Tayland ve Japonya'da farklı versiyonları vardır.
4|Wagyu eti hangi ülkeye aittir?|Japonya|ABD|Arjantin|Avustralya|Wagyu, yoğun yağ damarlanması ile bilinen Japon sığır cinsidir.
4|Tahin helvası hangi iki ana malzemeyle yapılır?|Tahin ve şeker|Un ve süt|Pirinç ve bal|Peynir ve yumurta|Tahin helvası susam ezmesi (tahin) ve şekerle yapılan, Orta Doğu ve Anadolu mutfağında sevilen bir tatlıdır.
4|"Dolma" kelimesi ne anlama gelir?|Doldurulmuş|Pişirilmiş|Kızartılmış|Haşlanmış|Dolma, "doldurmak" fiilinden gelir; yaprak ve sebzeler pirinç veya kıyma ile doldurulur.
4|Safran'ın ana üretici ülkesi hangisidir?|İran|Türkiye|Mısır|Fransa|İran dünya safran üretiminin büyük kısmını karşılar. Türkiye'de Safranbolu adını bu bitkiden alır.
4|Fransız mutfağında "Béchamel" nedir?|Süt ve unla yapılan beyaz sos|Domates sosu|Soya sosu|Tatlı sos|Béchamel (beşamel), tereyağı, un ve sütle yapılan ana sostur.
4|Pestonun ana malzemesi hangi otdur?|Fesleğen|Nane|Dereotu|Maydanoz|Pesto, fesleğen, çam fıstığı, parmesan ve zeytinyağından yapılan Ceneviz (Cenova) soslu ezmedir.
4|Meksika mutfağında "guacamole" neyden yapılır?|Avokado|Domates|Biber|Fasulye|Guacamole, ezilmiş avokado, limon, soğan ve kişnişle yapılan sostur.
4|Hangi çay türü fermente edilmiş siyah çaydır?|Earl Grey|Matcha|Yeşil çay|Beyaz çay|Siyah çay tam fermente edilmiş yapraklardan yapılır; Earl Grey bergamot aroması katılmış siyah çaydır.
4|Matcha hangi ülkenin geleneksel yeşil çay tozudur?|Japonya|Çin|Hindistan|Kore|Matcha, gölgede yetiştirilen çay yapraklarının toz haline getirilmesiyle yapılır; Japon çay seremonisinde kullanılır.
4|"Aperitif" ne zaman içilir?|Yemekten önce|Yemekten sonra|Gece yarısı|Kahvaltıda|Aperitif, iştah açmak için yemekten önce içilen içecektir.
4|Hangi ülke "Poutine" yemeğini ortaya çıkarmıştır?|Kanada|ABD|İngiltere|Avustralya|Poutine; patates kızartması, peynir lorları ve sosla yapılan Quebec kökenli Kanada yemeğidir.
4|Tapas nedir?|İspanya'da küçük porsiyonlu mezeler|İtalyan makarna çeşidi|Japon tatlısı|Fransız ekmeği|Tapas, İspanya'da bar ve meyhanelerde servis edilen küçük porsiyonlardır.
4|Hangi tahıl "Quinoa" olarak bilinir ve And Dağları kökenlidir?|Kinoa|Arpa|Yulaf|Çavdar|Kinoa, And Dağları'nda binlerce yıldır yetiştirilen, protein açısından zengin bir tohumdur.
4|Zencefilin kökünün kullanıldığı Japon turşusu hangisidir?|Gari|Takuan|Natto|Miso|Gari, suşi yanında servis edilen turşu zencefildir.
4|Natto nedir?|Fermente soya fasulyesi|Pirinç keki|Deniz yosunu|Soya sütü|Natto, Japon mutfağında kendine has kokusu ve yapışkan dokusuyla bilinen fermente soya fasulyesidir.
4|"Pierogi" hangi ülkenin hamur işidir?|Polonya|Rusya|Almanya|İtalya|Pierogi, patates, peynir veya etle doldurulan Polonya mantısıdır.
4|Paprika hangi ülkenin mutfağında çok önemlidir?|Macaristan|Fransa|Mısır|Norveç|Paprika, Macar gulaşının temel baharatıdır; Macaristan'ın simge baharatıdır.
5|Parmesan peyniri hangi bölgenin korumalı ürünüdür?|Parma/Reggio Emilia (İtalya)|Roma|Torino|Napoli|Parmigiano Reggiano, İtalya'da belirli bölgelerde, en az 12 ay olgunlaştırılan sert bir peynirdir.
5|Şampanya adı verilen köpüklü şarap hangi bölgede üretilir?|Champagne (Fransa)|Bordeaux|Toskana|Katalonya|Yalnızca Fransa'nın Champagne bölgesindeki köpüklü şaraplar "şampanya" adını taşıyabilir.
5|Viyana'nın ünlü çikolatalı pastası Sachertorte'yi kim yaptı?|Franz Sacher|Auguste Escoffier|Marie-Antoine Carême|Paul Bocuse|Sachertorte, 1832'de Franz Sacher tarafından yapıldı; çikolatalı kek ve kayısı reçelinden oluşur.
5|Umami tadını verdiği bilinen amino asit nedir?|Glutamik asit|Laktik asit|Folik asit|Sitrik asit|Glutamik asit ve tuzları (glutamat) et suyu, domates ve peynirde bulunur ve umami tadını verir.
5|Dünyanın en pahalı mantarlarından biri olan "trüf" hangi ortamda yetişir?|Toprak altında|Ağaç gövdesinde|Denizde|Çölde|Trüf mantarı meşe ve ceviz ağaçlarının köklerinde toprak altında yetişir; eğitilmiş köpeklerle bulunur.
5|Çikolata kaç yıl önce Mayalar tarafından acı bir içecek olarak içiliyordu (yaklaşık)?|2.000–3.000 yıl|100 yıl|500 yıl|20 yıl|Kakao Orta Amerika'da Mayalar ve Aztekler tarafından binlerce yıl önce içecek olarak tüketiliyordu.
5|Gluten hangi tahıl proteinidir?|Buğday|Pirinç|Mısır|Kinoa|Gluten buğday, arpa ve çavdarda bulunur; çölyak hastalarının kaçınması gerekir.
5|Hangi besin "kazein" proteini içerir?|Süt|Yumurta|Bal|Pirinç|Kazein süt proteinidir; peynir yapımında pıhtılaşan kısımdır.
5|"Michelin yıldızı" neyi değerlendirir?|Restoranların kalitesini|Otel odalarını|Lastik kalitesini|Müze bileti|Michelin Rehberi 1900'de lastik üreticisi Michelin tarafından çıkarıldı; restoranlara yıldız verir.
5|Vitamin B12 için en iyi kaynaklar hangi gıdalardır?|Et ve süt ürünleri|Elma|Pirinç|Marul|B12 başlıca hayvansal gıdalarda bulunur; vejetaryenlerin takviye alması gerekebilir.
5|Soğuk sıkım zeytinyağı ne demektir?|Isıtılmadan, mekanik olarak elde edilen yağ|Dondurulmuş yağ|Buzlu yağ|Kızartmada kullanılan yağ|Soğuk sıkım, zeytinin düşük sıcaklıkta sıkılmasıyla aroma ve besin değerinin korunmasıdır.
5|Hangi ülke dünyanın en büyük zeytinyağı üreticisidir?|İspanya|İtalya|Yunanistan|Tunus|İspanya dünya zeytinyağı üretiminde yaklaşık yarısını tek başına karşılar.
5|"Karamelizasyon" nedir?|Şekerin ısıyla kahverengileşmesi|Sütün kesilmesi|Etin donması|Suyun kaynaması|Karamelizasyon, şekerin yaklaşık 170 °C'de yüksek ısıyla bozulup kahverengileşmesidir.
5|"Maillard tepkimesi" hangi sonucu doğurur?|Kızartma ve kavurmada kahverengi renk ve aroma|Donma|Fermantasyon|Mayalanma|Maillard tepkimesinde amino asitler ve şekerler tepkimeye girer; ekmek kabuğu, kavrulmuş kahve ve kızarmış et lezzeti bu yolla oluşur.
5|Dünyanın en baharatlı biberlerinden "Carolina Reaper" hangi ölçekle değerlendirilir?|Scoville|Richter|Celsius|Beaufort|Scoville ölçeği, biberin acılığını (kapsaisin düzeyini) ölçer.
` });
})(typeof window !== 'undefined' ? window : globalThis);
