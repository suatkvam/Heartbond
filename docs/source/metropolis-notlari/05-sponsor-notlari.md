# Sponsor notları

Sponsor oturumlarından çıkan notlar. Her bölümde önce aracın ne olduğu, sonra oturumda öne çıkan noktalar, en sonda ilgili bounty ve linkler var. İhtiyacın olan bölümü tek başına AI'ına verebilirsin.

Oturum notu olmayan sponsorlar (Privy, Perpl, Mera, Hunyuan, KIMI, Qwen) için bounty açıklamaları `02-trackler-ve-bountyler.md`, dokümanları `07-kaynaklar.md` içinde.

İçindekiler:

- Veri ve altyapı: [Envio](#envio) · [Alchemy](#alchemy) · [QuickNode](#quicknode) · [Zerion](#zerion) · [Nansen](#nansen)
- Cüzdan ve hesap: [Dynamic](#dynamic) · [MetaMask Agent Wallet](#metamask-agent-wallet)
- Trading ve piyasalar: [Kuru](#kuru) · [Launchpad'ler](#launchpadler)
- Zincirler arası ve off-chain: [Aurora Intents](#aurora-intents) · [Chainlink CRE](#chainlink-cre)
- Güven, ödeme, debug: [Cleanverse](#cleanverse) · [Agora](#agora) · [Tenderly](#tenderly)

---

## Envio

Zincir üstü event'leri indexleyip GraphQL ile sorgulanabilir hale getiren indexer. Ürünleri: HyperIndex (indexer framework), HyperSync (ham veri motoru, hızlı backfill), HyperRPC (hızlı, sadece okuma RPC).

Denham: *"Think of it as the layer between your front end and your smart contracts."*

- **Ne zaman indexer lazım:** Ürün geçmiş aktiviteye, toplulaştırılmış veriye ya da ürüne özel bir sorgu yüzeyine ihtiyaç duyuyorsa. Tek seferlik anlık bir state okuması için gerekmez. Indexer'ı zincir geçmişinin jenerik bir kopyası olarak değil, ürünün veri modeli olarak tasarla.
- **Kontratı indexer'ı düşünerek yaz.** *"Often you use events to emit or logs to emit events. And that's kind of the better, more cost-effective way of getting data from on-chain."* Kullanıcıya dönük bir özelliğin ihtiyaç duyacağı event'leri emit et, sonra sadece ilgili event'leri indexle. Her şey için state okumaya düşmek geçmiş görünümlerini yavaş ve zor yapar.
- **Üç dosya:** *"We've got three files we care about."*
  - **config:** kontrat, network, başlangıç bloğu ve seçilen event'ler. Verinin sınırını belirler.
  - **schema:** GraphQL yüzeyini belirler.
  - **handler:** bir event'i ürüne özel state'e dönüştürür.
  Bunlar tasarım kararları. Generator'ın ürettiği haliyle bırakıp geçme.
- **Test yaz.** Agent handler'ı hızlıca yazar, ama handler'ın zincirdeki davranışı hâlâ doğru temsil ettiğini testler kanıtlar.

Bounty: Best Use of Envio ($1,000, All tracks).
Linkler: [HyperIndex overview](https://docs.envio.dev/docs/HyperIndex/overview) · [Quickstart with AI](https://docs.envio.dev/docs/HyperIndex/quickstart-with-ai) · [Monad'da indexleme](https://docs.envio.dev/docs/HyperIndex/monad) · [Envio ile transfer bildirim botu](https://docs.monad.xyz/guides/indexers/tg-bot-using-envio) · [Envio agent skill'leri](https://docs.envio.dev/blog/ai-agents-acting-onchain-indexer)

---

## Alchemy

RPC, cüzdan altyapısı (Smart Wallets, gas sponsorship, EIP-7702), webhook'lar ve CLI.

- **Alchemy CLI:** Uttam: *"Agents can autonomously go and sign up for our services."* Agent'a hesapla bağlantılı zincir altyapısı, sorgular ve operasyonel işler için terminalden çalıştırılabilen bir kontrol yüzeyi veriyor; tarayıcıda kurulum yapma ihtiyacını azaltıyor. Aynı sebeple CLI'daki kimlik doğrulamasını production credential'ı gibi korumak gerekiyor.
- **Gerçek zamanlı veri için WebSocket.** *"Use WebSockets, not HTTP, not just Node RPC."* Canlı bir cüzdan, event monitörü ya da piyasa arayüzü için sürekli abonelik kullan, tekrar tekrar snapshot çekme. Statik ya da ara sıra yapılan bir sorgu için bu karmaşıklığa gerek yok. Transport seçimi bir ürün kararı.
- **API key'i `.env`'de tut.** *"Please make sure that you're using API key and storing it in .env... protect the API key, please."*

Bounty: Best Projects using Alchemy ($1,000 kredi, All tracks).
Linkler: [Monad API quickstart](https://www.alchemy.com/docs/reference/monad-api-quickstart) · [Alchemy CLI](https://www.alchemy.com/docs/alchemy-cli) · [MCP Server](https://www.alchemy.com/docs/alchemy-mcp-server) · [Agent Skills](https://www.alchemy.com/docs/alchemy-agent-skills) · [Gas sponsorship](https://www.alchemy.com/docs/wallets/transactions/sponsor-gas/overview) · [EIP-7702 işlemleri](https://www.alchemy.com/docs/wallets/transactions/using-eip-7702)

---

## QuickNode

RPC, Webhooks ve Streams. Metropolis katılımcılarına Build Plan üç ay ücretsiz (bkz. `07-kaynaklar.md`).

- **Neyi izleyeceğine karar vermenin kuralı:** Yokluğu kullanıcıyı hemen kızdıracak zincir event'ini izle. Cüzdan için gelen ve giden işlemler, DEX için decode edilmiş swap'lar ve onaylar. Gerçek zamanlı trading kararı sunmayan bir analitik dashboard gecikmeyi tolere edebilir.
- **Webhooks:** Bir kontrat ya da cüzdandan güncel event'lere ihtiyaç varsa en az karmaşık push yöntemi. İzlenecek adresi ve event hash'ini ayarla, teslimatı bir endpoint'e yönlendir, gelen güvenlik metadata'sını uygulamada doğrula. Birçok MVP bildirim ve aktivite akışı için kendi abonelik döngünü yazmana gerek bırakmıyor.
- **Streams:** Bildirim değil bir ETL pipeline'ı gerektiğinde kullanılır. Seçilen bloktan geriye doldurabilir (backfill), canlı bloklarla devam eder, ham receipt'leri JavaScript veya Go ile filtreleyip dönüştürür, mesajları batch'ler ve doğrudan veritabanına, data lake'e ya da endpoint'e gönderir.
- **Streams ayarları bilinçli seçilmeli:** latest-block gecikmesi hız ile kesinlik arasında bir tercih; retry ve timeout ayarları hedef sistem çöktüğünde veriyi korur; sınırlı bir blok aralığı yanlışlıkla tüm zinciri indexlemeni engeller.

Linkler: [Monad quickstart](https://www.quicknode.com/docs/monad/quickstart) · [Streams](https://www.quicknode.com/docs/streams) · [Webhooks](https://www.quicknode.com/docs/webhooks/getting-started) · [Monad rehberleri](https://www.quicknode.com/guides/tags/monad)

---

## Zerion

Luan: *"We are not an RPC provider. We are not here to give you raw on-chain data."*

Zerion ham erişimin bir üst katmanında duruyor: işlemleri parse ediyor, fiyat ekliyor, spam'i etiketliyor, token ve DeFi pozisyonlarını yorumluyor. Kullanıcının anlayabileceği cüzdan davranışı gösteren bir ürün için kullan; sadece ham bir zincir okuması gerekiyorsa gerek yok.

- **Parametreler ürün kararıdır.** *"Usually it's the parameters that people get wrong a lot."* Görünüm sadece Monad mı olacak, sadece basit varlıklar mı yoksa karmaşık DeFi pozisyonları da mı dahil, çöp token'lar gizlenecek mi? Bunları açıkça seç. "Kayıp" görünen bir işlem, gözden kaçmış bir filtre yüzünden dışarıda kalmış olabilir.
- **Zerion'un kendi cüzdanı referans uygulama.** *"At least 90% or 99% of what you see here on the web app is going to be coming from public API."* Bir portföy özelliğini sıfırdan icat etmeden önce hangi UI kalıplarının, veri yorumlarının ve spam yönetiminin mümkün olduğunu oradan inceleyebilirsin.
- **Wallet webhook'ları:** Seçili adreslere abone olup parse edilmiş canlı aktiviteyi alırsın; ham RPC üzerinden polling sistemi kurman gerekmez.

Perk: API Builder tier bir ay ücretsiz.
Linkler: [API introduction](https://developers.zerion.io/introduction) · [Zerion CLI + Agent Skills](https://developers.zerion.io/build-with-ai/zerion-cli) · [zerion-ai GitHub](https://github.com/zeriontech/zerion-ai)

---

## Nansen

Nansen'in değeri transferleri görmesi değil, onlara kimlik ve davranış bağlamı eklemesi. Sorulacak soru "bu 0x adresi ne yaptı?" değil; "bu bir market maker mı, yeni bir cüzdan mı, whale mi, tanınmış biri mi, ilişkili bir karşı taraf mı ve kullanıcı bunu neden umursamalı?"

- **Ham graf gürültülü.** James'in cüzdan ilişki görselleştiricisi ancak borsaları ve smart contract'ları eleyebildiğinde, doğrudan transferleri ortak protokol etkileşimlerinden ayırabildiğinde ve geriye kalan insan ilişkilerini gösterebildiğinde işe yarar hale geldi.
- **Token akışını segmente göre yorumla.** Her şeyi "smart money" diye tek bir skora indirme. Yeni cüzdanlardan, whale'lerden, tanınmış kişilerden ve kârlı trader'lardan gelen giriş-çıkışlar çok farklı hikayeler anlatır. İyi bir ürün segmenti gösterir.
- **API, CLI ve MCP aynı verinin üç erişim yolu:**
  - API: uygulamanın yaptığı istekler için.
  - CLI: agent'ın çalışma alanında tüm sorgu yüzeyine ihtiyacı olduğunda.
  - MCP: kullanıcının canlı zincir bağlamına doğal dille soru sorması gerektiğinde.
- **Jenerik bir analitik dashboard'dan uzak dur.** Oturumdaki örnekler: cüzdan uyumluluğu, zincir üstü yıllık özet ("wrap"), görsel işlem haritaları. Hepsi zor veriyi sosyal, açıklayıcı ya da paylaşılabilir bir deneyime çeviriyor.

Bounty: Best use of Nansen ($5,000 havuz, All tracks). Şart: Nansen ürünün çekirdeğinde olmalı, opsiyonel bir veri rozeti gibi değil.

---

## Dynamic

Kimlik doğrulama, embedded ve agent wallet'lar, imzalama.

- **Headless SDK:** Onboarding cüzdan sağlayıcısının varsayılan UI'ına değil, uygulamaya uymalı. Cüzdanın ne zaman oluşturulacağına, onayın ne zaman gösterileceğine ve her adımın ürünün kendi akışına nasıl oturacağına sen karar veriyorsun.
- **Dynamic CLI:** Dashboard'u agent'ın kullanabileceği bir yapılandırma yüzeyine çeviriyor. Onaylanmış bir kimlik doğrulamasından sonra ayarları programatik olarak kontrol edip değiştirebiliyor. "Kod doğru ama dashboard'da bir toggle, zincir ayarı ya da cüzdan seçeneği unutulmuş" hatasını azaltıyor.
- **MCP:** Güncel dokümanı düşük context maliyetiyle getiriyor.
- **Agent cüzdanları için izin modeli** (autonomous / server / delegated) ve "personal CFO" denetim düzeni için bkz. `04-ai-ile-gelistirme.md`.

Bounty: Best Use of Dynamic ($5,000, All tracks). Deploy edilmiş, demo'su yapılabilir bir uygulama isteniyor.

---

## MetaMask Agent Wallet

- **Plugin'ler agent wallet'ı bir yetenek platformuna çeviriyor.** Bir plugin deterministik trading kuralları, ENS çözümleme, yeni bir perpetuals venue'su ya da copy-trading mantığı ekleyebilir. Sonra npm paketi olarak yayınlanır ve diğer agent'lar kurar; her projede yeniden yazılmaz.
- **Güvenlik sınırı kesin.** Plugin'ler cüzdan state'ini okuyabilir, public client'ı kullanabilir, piyasa verisi alabilir ve işlem isteği gönderebilir. Agent wallet politikalarını değiştiremez ya da atlayamaz. Yürütme yine MetaMask'in policy engine'inden ve MFA yolundan geçer.
- **İzinler manifest'te beyan edilir** ve kurulum sırasında gösterilir. Salt okuma bir plugin, sonraki bir sürümde sessizce işlem yetkisi kazanmamalı. Kullanıcı, amacının ötesinde yetki isteyen bir kurulumu reddedebilir.
- **Gerçek bir trading/execution yapı taşından başla.** Venue'yu, stratejiyi, veri kaynağını ya da kontrat akışını önce kendin anla. Sonra plugin skill'i ve planning mode ile girdileri, hata yollarını, izinleri ve politika varsayımlarını agent'a net şekilde ifade et.

Bounty: Best Agent Wallet Plugin ($2,500, Onchain Finance & Trading).

---

## Kuru

Monad üzerinde tamamen zincir üstü order book (CLOB) DEX'i ve aggregator.

**Kuru altyapı, bitmiş trading ürünü değil.** Zincir üstü order book'lar, likidite, piyasa verisi, trigger emirleri, relay üzerinden işlem iletimi ve ücret mekaniklerini sağlıyor. Kullanıcı içgörüsü, dağıtım ve kullanıcıya yeni bir trading deneyimini denemesi için sebep veren arayüz senin işin.

- **Farklılaşma, az hizmet alan bir kitleden gelir.** Bölgeye özel regülasyona uygun bir front-end, yerel on-ramp, yapılandırılmış finansal ürünler ya da agentic bir asistan, jenerik bir terminalin ulaşamadığı kullanıcılara ulaşabilir.
- **Geçmiş veri ve canlı stream farklı katmanlar.** Geçmiş veri API'si ürünü emirler, işlemler, bakiyeler ve piyasa bağlamıyla başlatır. Düşük gecikmeli stream'ler canlı order book, mid fiyat, kullanıcı bakiyeleri ve otomasyon için. İkisini karıştıran bir front-end ya yavaş ya da gereksiz pahalı olur.
- **Mobil performans önemli.** Fazla state ve büyük payload titreme (jitter) yaratır.
- **Relay bir ürün yapı taşı.** Gas'ı sponsorluyor ve yürütmeyi tekrar deniyor; böylece yeni bir kullanıcıdan trade yapmadan önce EOA'sına MON yüklemesini istemek zorunda kalmıyorsun.
- **Subaccount'lar ve delegated signer izinleri.** Bir kullanıcı bir yöneticiye ya da stratejiye trade yetkisi verip, çekim yetkisini, miktarı ya da kapsamı ayrıca kısıtlayabilir. Private key paylaşmaktan çok daha iyi bir portföy yönetimi mimarisi.
- **Portfolio-manager demo'su:** Passkey tabanlı bir Mera cüzdanı + EIP-7702 uyumlu delegated kontrat + relayer. Değerli sahip hesabını, harcanabilir bir trading credential'ından ayırıyor; günlük limitleri kontrat mantığında uyguluyor; cihazda geniş çekim yetkisi bırakmadan gas'sız yürütme sağlıyor.
- **Yeni piyasa bounty'si bir token listelemekle ilgili değil.** Yeni bir spot ya da sonuç (outcome) piyasası yaratan bir wrapper, o piyasanın neden bir kitlesi olduğunun açıklaması ve likiditeye giden inandırıcı bir yol. Prediction market'ler bir örnek: ikili veya çok sonuçlu paylar spot order book altyapısı üzerinde temsil edilebilir.
- **Yeni bir piyasanın ilk trader'ları kurucunun spesifik içgörüsünden gelir.** O varlığı, sporu, bölgeyi ya da stratejiyi zaten trade eden insanlarla başla; bugün neyi trade edemediklerini sor; likiditeyi jenerik bir kullanıcı edinme problemi saymadan önce ürünü kullanıp kullanmadıklarını test et.

Bounty'ler: Build the Next Consumer Trading App on Kuru ($5,000) ve Bring New Assets and Markets to Kuru ($5,000), ikisi de Onchain Finance & Trading.
Linkler: [Kuru Docs](https://docs.kuru.io/) · [Kuru SDK (npm)](https://www.npmjs.com/package/@kuru-labs/kuru-sdk) · [kuru-terminal (gerçek zamanlı indexleme referansı)](https://github.com/monad-developers/kuru-terminal)

---

## Launchpad'ler

Launchpad'ler birden fazla oturumda konuşuldu. Buradaki notlar onların birleşimi.

- **Launchpad'ler "toplulukların topluluğu" yaratır.** Normal bir uygulama tek bir kullanıcı topluluğu büyütür. Bir launchpad, birçok yaratıcının kendi token topluluğunu platformun çatısı altında kurmasını sağlar; dağıtım ürünün kendisi haline gelir.
- **Aynı meme coin mekaniğini Monad'a taşımak yetmez.** PumpFun basit viral coin toplulukları yaratıyor. Pawns ise coin'leri hisse senetleriyle eşleyip ücretlerin bir kısmını yönlendirerek topluluk tezini değiştiriyor. Asıl soru: sadece bu launch süreci ve gelir tasarımı sayesinde var olabilecek topluluk ne?
- **Ücret dağılımı temel tasarım aracı.** Rakibin marjı senin ürün alanın. Ücretlerin tamamını platform buyback'ine yönlendirmek yerine bir varlığa, bir katılımcı grubuna, bir kamu yararına ya da başka programatik bir hedefe yönlendirmek, topluluklara oluşmak ve kalmak için ayırt edici bir sebep verir.
- **Launchpad'e güven kısmen mekanik, kısmen anlatı.** Net ve tanınabilir launch özellikleri kullanıcıya köken güveni verir. Ücretlerin nereye gittiğini ve platformun neden böyle tasarlandığını açıkça anlatan bir kurucu, platformun tutarlı davranacağına inanmak için sebep verir.
- **İlk adım gözlem.** Rakip launchpad'leri kullan, kullanıcıların tekrar eden şikayetlerine bak, hangi yeni topluluk ya da teşvik modelinin gerçek bir boşluğu doldurduğuna karar ver, sonra inşa et. Tezi olmayan jenerik bir launchpad mevcut ağ etkilerini yenemez.

Monad'daki mevcut oyuncu ve araçlar için: [Nad.fun](https://github.com/naddotfun), [Doppler](https://docs.doppler.lol), [Zora Coins](https://docs.zora.co/coins). Daha fazlası `ek/resources-sayfasi.md` içinde "Next-gen Launchpads for New Asset Classes" başlığında.

---

## Aurora Intents

NEAR Intents altyapısıyla çalışıyor. Zincirler arası bir isteği köprüler ve onaylardan oluşan bir diziden, beyan edilmiş bir sonuca çeviriyor: kullanıcı hangi varlığın nerede olması gerektiğini söylüyor, routing ve yürütme detaylarını (hataya açık cüzdan ve zincir değiştirmelerini) intent altyapısı hallediyor.

**Ürünü son duruma göre seç:**

| İstenen sonuç | Ürün |
|---|---|
| Uygulamadaki bir hesabı fonlamak | Intents Deposits |
| Kendi UX'inin içinde kalan zincirler arası varlık dönüşümü | Swap API |
| Fonlanan hedefin hemen bir kontrat eylemi yapması (lending pozisyonuna girmek, vault'a yatırmak vb.) | Intents Connect |

- **Intents Connect** zincirler arası hareketi hedef zincirdeki composability ile tek işlemde birleştiriyor. Kullanıcı EVM ya da EVM olmayan bir zincirden varlık getirip doğrudan bir Monad protokol pozisyonunda bitirebilir.
- **Kalıcı deposit adresleri** bir ürün yapı taşı. Uygulama seçilen bir hedef hesap için sabit bir fonlama adresi atayabilir; tekrarlayan yüklemeler normal bir hesap işlemi gibi hissettirir.
- **Bounty için sadece zincirler arası bir çağrı yetmez.** Değerlendirme kriterleri: gerçek settlement ve iade (refund) yönetimi, net UX, teknik kalite, kaynak zincir desteği, Intents Connect için kontrat uyumluluğu ve doğrulamayı kolaylaştıran çıktılar (public repo, teknik demo, pitch videosu, mümkünse canlı link).

Bounty: Bring Any-Chain Liquidity to Monad ($5,000, All tracks).

---

## Chainlink CRE

Chainlink Runtime Environment. Tasarımın birimini kontrattan workflow'a taşıyor.

- **Workflow'dan düşün.** İşi tetikleyecek event'le başla, gereken off-chain bilgiyi ya da servisi belirle, kullanıcıya verilen sözü tamamlayan zincir üstü callback'i tanımla. Solidity kontratı bu yoldaki doğrulanmış adımlardan biri; uygulamanın tamamının yaşadığı yer değil.
- **Hava durumu demo'su:** Bir EVM log'u workflow'u tetikledi, CRE harici bir hava durumu API'sini çağırdı, sonra korumalı bir callback sonucu zincire yazdı. Böylece API çağrıları, credential'lar ya da doğrulanamayan tek bir sunucu kontratın içine girmeden harici sistemler bağlanabiliyor.
- **Önemli olan sadece HTTP isteği atabilmesi değil.** Merkeziyetsiz bir oracle ağı, zincire yazmadan önce harici çağrı ve off-chain hesaplama üzerinde konsensüse varıyor. Entegrasyon katmanı kendi doğrulama modeli olan bir güven bileşeni oluyor; kullanıcıdan körü körüne güvenmesi istenen bir backend değil.
- **Simülasyon bir geliştirme aşaması.** Tetikleyiciyi, harici isteği ve beklenen sonucu zincire yazma maliyeti ödemeden kanıtlar. Davranış doğru olunca broadcast gerçek callback'i yapar. Hackathon için simülasyon kaydı, deploy yolu bitmemişken bile inandırıcı bir demo olabilir.
- **Forward kontrat düzeni:** Geliştirmede workflow yerel bir forward'a yazar; deploy'da gerçek adres verilir ve state değiştiren callback sadece workflow çıktısına açık hale getirilir. Demo kolaylığı, yazma yolunu yanlışlıkla açık bırakmaya dönüşmez.
- **CRE en çok ürünün temel vaadi sistem sınırını aştığında değerli.** Harici veri, zamanlanmış işlemler, zincir üstü event'e tepki ve sistemler arası eylemler, kullanıcının ne blockchain'in ne de klasik bir backend'in tek başına sağlayamayacağı bir sonuca ihtiyacı olduğunda tek bir workflow'da birleşir.

Bounty: Best workflow with CRE ($3,000, All tracks). Build, simulate ya da deploy yeterli; workflow projede orkestrasyon katmanı olarak kullanılmalı.

---

## Cleanverse

Kimlik doğrulama (CVI) ve regülasyona uygun varlıklar (CVA).

- **İki yarım, tek karar.** Doğrulanmış kimlik ve uyumlu varlık aynı transfer kararının iki parçası. Cüzdana bağlı credential tier, grup, ülke, geçerlilik ve durum gibi özellikleri sağlar; varlık transferi settlement'tan önce ilgili kuralı uygular. Transfer kapısı olmayan kimlik parayı serbest bırakır; kimliği olmayan varlık kuralı kimin katıldığını bilemez.
- **Kontrol değerin hareket ettiği yolda olmalı.** CVA token'ı kontrolü transfer hook'unda yapabilir. Bir iş kontratı ise deposit, swap, çekim ya da settlement'ta bakiyeyi veya state'i değiştirmeden önce ilgili taraflar için `complianceVerify` çağırmalı. Front-end kontrolü ve onboarding onayı iyi UX'tir ama uygulama (enforcement) değildir.
- **Sadece onboarding'de doğrulamak yetmez.** Alıcı cüzdan hiç doğrulanmamış olabilir, credential'ın süresi dolmuş ya da pasif olmuş olabilir, tier veya ülke uygunluğu değişmiş olabilir. Transfer anında tekrar kontrol etmek, geçmişteki kayıt olayını değil güncel kuralı belirleyici yapar.
- **Reddedilen transfer anlaşılır bir durum olmalı.** Zincir üstü reddin sebebini göster (credential yok, süresi dolmuş, pasif, tier yetersiz, ülke izinli değil) ve kullanıcıyı doğru düzeltme adımına yönlendir.
- **Silme testi.** Kimlik mantığını silince varlık hâlâ hareket edebiliyorsa, compliance sonradan eklenmiş opsiyonel bir katman demektir. Güçlü bir tasarımda kontrat seviyesindeki kuralın etrafından dolaşan alternatif bir yol yoktur ve bu, seyahat kuralı (travel rule) ödemeleri, izinli DeFi ya da RWA settlement gibi gerçek bir regüle akışla eşleşir.
- **En küçük MVP:** Validator adresini sakla, kontratı API üzerinden kaydet, minimum tier gibi basit bir Rule V2 belirle ve tek bir kapılı eylem oluştur. İki cüzdanla test et: biri kuralı sağlıyor, biri sağlamıyor. Factory'lere, çıkarılan varlıklara ya da wrapper'lara geçmeden önce hem ürün vaadini hem kontrat kuralını gösterir.

Bounty: Best Integration of Cleanverse Verified Identity & Assets ($2,000, Trust, Identity & AI Infrastructure).

---

## Agora

AUSD: Monad üzerinde 1:1 USD stablecoin.

- **AUSD sadece bir bakiye daha değil.** Düşük ücretli ve değeri öngörülebilir bir dolar rayı; dolar cinsinden fiyatlayan, tutan, settle eden ve kotasyon veren ürünleri mümkün kılıyor. Ödemeler, yüksek frekanslı transferler ve trading çiftleri tasarım alanı haline geliyor.
- **On-ramp ilk kullanıcı yolculuğu, sonradan eklenecek bir entegrasyon değil.** Kullanıcı fiat ile, USDC ile, başka bir stablecoin ile ya da hiç cüzdan bilgisi olmadan gelebilir. Kontratın çalışması ödeme problemini çözmez; Web2'den gelen biri için bakiyeyi edinmek, fonlamak ve ona güvenmek anlaşılır olmalı.
- **Instant settlement kontratı** hackathon için ana AUSD dönüşüm yapı taşı. Ödeme ya da trading arayüzü tasarlamadan önce approval'larını ve giriş-çıkış akışını anla. Testnet'te eşlenen token USDC değil CTK; cilalı bir demo bu testnet detayını gizlemek isteyebilir, ama kullanıcının gerçekte ne yaptığını gizlememeli.
- **Likidite olmayabilir.** Agora'nın route API'si bu durumda anlamlı bir yedek yol: USDC ya da potansiyel olarak fiat kabul eden bir adres/vault rotası sağlıyor ve operasyonel bir gecikmeyle mint edilmiş AUSD döndürüyor. UI anlık tamamlanma ile bu yavaş rotayı ayırt etmeli; yoksa kullanıcı geciken işlemin kaybolduğunu düşünür.
- Pending/revert/iade durumlarını nasıl göstereceğin için bkz. `03-fikirden-urune.md` > "Güven gerektiren durumlar".

Bounty'ler: Best Cross-Border Payments App ($10,000, Consumer Products & Payments) ve Best Mobile Trading App ($10,000, Onchain Finance & Trading). İkisi de Mera ile giriş istiyor; trading olanı Perpl üzerinden işlem istiyor.

---

## Tenderly

Simülasyon, debug, sanal test ağları ve alert'ler. Metropolis katılımcılarına Pro tier ücretsiz (yaklaşık $7,200 değerinde).

- **Simulator:** Anlaşılmaz bir revert'ü incelenebilir bir yürütmeye çeviriyor. Bir adresi taklit edebilir (impersonate), state override uygulayabilir, gerçek bir kontrat fonksiyonunu çağırıp trace'i görebilirsin. Debugger başarısız işlemi tam olarak hangi kaynak satırının, storage değerinin ve `require` koşulunun ürettiğine bağlıyor.
- **State override soruyu değiştiriyor:** "Bu neden imkansız?" yerine "Hangi koşulda başarılı olur?" Wrapped-MON örneğinde istenen çekim miktarının bakiyeyi aştığı görüldü; doğru miktar test edildi ya da bakiye override edilip başka senaryo denendi. Testnet'e dönmeden gerçek koşul izole ediliyor.
- **Simülasyonda kaynak kodu düzenlemek teşhis aracı.** Bir `require`'ı geçici olarak kaldırmak revert'e onun sebep olduğunu gösterir; kaldırılması gerektiğini göstermez. Sonraki adım ön koşulun mu, kullanıcı akışının mı, kontrat mantığının mı yanlış olduğuna karar vermek.
- **Virtual environment'lar:** Kalıcı, fork edilmiş bir Monad sandbox'ı. Blok seçebilir, faucet kullanabilir, kalıcı state değişiklikleri yapabilir, blok mine edip geri alabilir, zamanı ilerletebilir ve sanal bir RPC üzerinden etkileşebilirsin. Çok adımlı akışları canlı ağa dokunmadan prova etmek için.
- **Alert'ler:** Bir kontrat event'i ya da izlenen bir state, seçilen bir hedefe bildirim gönderebilir ya da serverless kod tetikleyebilir. Deposit, bakiye eşiği ya da bir olay tespit edildiğinde birinin dashboard'a bakmasını beklemeden doğrudan bir tepki akışı başlatılabilir.

Aynı günün üç oturumunu birleştiren not: Cleanverse bir varlığı kimin hareket ettirebileceğini ve bu kuralın nerede uygulandığını belirliyor; Agora para hareketini sıradan bir kullanıcı için kullanılabilir ve açıklanabilir kılıyor; Tenderly takıma doğru kalması gereken yolları test etme, inceleme ve otomatikleştirme imkanı veriyor.
