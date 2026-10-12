# Fikirden ürüne

Harpal, Pareen, Daniela ve sponsor oturumlarından ürün tarafıyla ilgili notlar. Kod yazmaya başlamadan önce okunması en faydalı dosya bu.

## Fikri doğrulamak

**Şikayetten başla, sezgiden değil.** X, Reddit, niş topluluklar ve Discord'da aynı çözülmemiş soruyu ya da aynı sıkıntıyı tekrar tekrar dile getiren insanları ara. Bulduğunda o kişilere yaz: görüşme iste ya da beta erişimi teklif et. Tekrarlanan şikayet, ulaşılabilir bir ilk kullanıcı grubu olduğunun kanıtı.

**Araştırmayı verinin olduğu yerde yap.** Harpal, ilgili toplulukları bulmak için Reddit'in kendi "Ask AI" özelliğini önerdi. Port, X'teki güncel tartışmalar için Grok'u, YouTube içeriği için Gemini'yi önerdi. Kod yazan model her zaman en iyi araştırma aracı değil.

**Önce karar ver, sonra inşa et.** Harpal'ın sıralaması: plan mode'da ve fikri zorlayan sorular soran bir skill ile fikri test et, repoda kalıcı bir checklist oluştur. Kod yazmak ucuz; neyin yazılmaya değer olduğuna karar vermek pahalı olan kısım.

**Kategoriyi klonlama, eksik mekaniği bul.** Launchpad örneği: gerçekten anlamlı token çıkarmış insanlarla konuş, mevcut platformlarında neyin yetersiz kaldığını sor, cevabı başkalarıyla çapraz kontrol et, sonra o tek eksik mekaniği inşa et.

**Rakip platformları kullanarak başla.** Özellikle launchpad gibi ağ etkisi güçlü kategorilerde ilk adım kod üretmek değil, gözlem: rakipleri kullan, kullanıcıların nerede şikayet ettiğine bak, hangi yeni topluluk veya teşvik modelinin gerçek bir boşluğu doldurduğuna karar ver.

## Ağın yoksa

Tek başına çalışan ve tanıdığı olmayan biri, uzmanların cevap vermesi için bir sebep yaratabilir: araştırmayı önce yapmak. Kategoriyi, birkaç açık olmayan tespit içeren bir analiz yayınlayacak kadar derin çalış. Sonra o analizi, kısa bir görüşme için net bir soruyla birlikte gönder.

"Launchpad yapıyorum" mesajı kolayca görmezden gelinir. Ciddi bir anlayış ve spesifik bir soru içeren mesaj gelinmez.

## Aktif kullanıcı ve retention (Pareen)

**Aktif kullanıcı = tamamlanmış bir çekirdek döngü.** Siteyi ziyaret etmek, kayıt olmak ya da cüzdan bağlamak aktif kullanıcı yapmaz. Bir eylem ve bir ödül gerekir. DEX için: bir varlık al ve eline geçsin. İçerik ürünü için: belli miktarda tüketim.

**Aktiflik aralığı, kullanıcının mevcut alışkanlığına göre belirlenir.** DCA ürünü için aylık kullanıcı makul bir hedef, çünkü maaş ve yatırım davranışı aylık. Günlük trader'lara yönelik bir ürün ise, o kişilerin zaten trade yaptığı yere karşı günlük bir alışkanlık kazanmak zorunda. Her ürünü "DAU ürünü" saymak, olmayan başarısızlık sinyalleri üretir.

**Döngüyü küçült.** Özellik dolu bir platform, kurucuya anlatacak daha çok şey, kullanıcıya kaybolacak daha çok yer verir. Küçük bir eylem-ödül döngüsü, kişiyi geri getiren tetikleyiciyi, eylemi, ödülü ve değişen durumu görünür kılar.

**İlk 500 tekrar eden kullanıcı operasyon işidir, launch videosu işi değil.** Elle onboarding, küçük bir kullanıcı grubu, doğrudan cevaplar ve hızlı iterasyon. Kullanıcılar geri bildirimlerinin hızla görünür değişikliğe dönüştüğünü gördükçe kurucuya güvenir; referans da ancak ondan sonra gelir.

**Kullanıcın olduktan sonra zamanını ters çevir.** Haftanın çoğunu kullanıcılarla konuşup iterasyon yaparak geçir, kodlama için sınırlı bir blok ayır, sonra kullanıcılara dön. Zamanın %10-20'sinden fazlası kodlamaya gidiyorsa, özellikler kanıttan önce birikiyor olabilir.

## Product-market fit

PMF, kullanıcıdan istediğin davranışın maliyetine göre ölçülmeli. İmzalamak, ödeme yapmak ya da cüzdan bağlamak zor adımsa, sunduğun değer bunu karşılamalı.

Hızlı test bir canvas doldurmak değil:

- Şüpheci bir geliştirici bu ürünü kendisi kullanır mı?
- Destek olması söylenmemiş, önceden bilgilendirilmemiş biri ürünü görünce "evet" der mi?

## Onboarding

**Onboarding, terk etme riskinin en yüksek olduğu anda değer/sürtünme oranıdır.** Yeni kullanıcının attığı her adım ya hemen bir değer açmalı ya da ilerlediğini hissettirmeli. Art arda gelen açıklamasız güvenlik ve kurulum ekranları teknik olarak doğru olabilir ama ürünü öldürür.

**"Magic moment" etrafında tasarla.** Ürünün değerini kanıtlayan ilk eylem ne? Oraya giden yolda olmayan her şeyi kaldır ya da ertele. Bir finans uygulamasında bu an, formun bitmesi değil, bir ödemenin görünür bir ücret olmadan anında gelmesi olabilir.

**Küçük duyusal detaylar güveni artırır.** Ödeme başarılı olduğunda çalan ses örneği, önemli bir durum geçişini pekiştirdiği için işe yarıyor. Sesi süs olarak her yere değil, sonucu olan etkileşimlere koy.

## Güven gerektiren durumlar

Agora oturumundan: bekleyen (pending), revert olan ve geri dönen işlemler, güvenin en kritik olduğu anlar.

- İşlemin işlendiğini göster.
- Zincir üstü aktiviteyi incelenebilir kıl (explorer linki vb.).
- Neyin başarısız olduğunu kısa ve anlaşılır dille açıkla.
- Para güvendeyse ve geri dönüyorsa bunu açıkça söyle.

Sadece "her şey yolunda" ekranı olan bir ürün, kullanıcının finansal belirsizliği kayıp olarak yorumlamasına yol açar.

Kuru oturumundan benzer bir not: aktif trading'de kullanıcı arayüze ancak sürekli ve tutarlı davrandığında güvenir. Emrin gerçekleşip gerçekleşmediği konusunda kararsız görünen bir arayüz, kontratlar doğru olsa bile kullanıcıya güvensiz hissettirir.

## Go-to-market (Daniela)

**Rahatsız edici soruyla başla:** İdeal müşteri bu ürünü neden kullanmaz? Cevap genellikle gerçek benimseme engelini gösterir. O engeli özellik listesinin arkasına saklama; başlıkta ve ürün vaadinde doğrudan ele al.

**En güçlü rakibi küçümseme.** Neden kazandığını belirle, belirli bir kullanıcı için neyi sağlayamadığını bul, farklılaşmayı o boşluğa kur. "Regüle" gibi bir iddia ancak hedef kullanıcı regülasyona davranışını değiştirecek kadar değer veriyorsa işe yarar.

**Partner keşfi bir dağıtım tasarımıdır.** Partnerin ne katacağını, beklenen sayısal sonucu (pipeline, kitle) ve o ilişkiye nasıl ulaşacağını belirt. "Ekosistem partnerliği" bir plan değil. Belirli bir geliştirici grubuna ulaşan bir workshop ya da kampanya bir plan.

**BD keşfi logo listesiyle değil, warm-intro haritasıyla bitmeli.** Kişinin adı, nereden ulaşılabileceği, bir şey istemeden önce ona ne değer sunabileceğin ve senin için neyi açabileceği.

## Bir ürünün neden var olduğunu sorgulamak

MIP-8 oturumunun sonunda söylenen ve her konuya uyan bir soru: *Bu state var olduğu için hangi kullanıcı daha mutlu oluyor?* Aynı soruyu her özellik, her entegrasyon ve her ekran için sorabilirsin.
