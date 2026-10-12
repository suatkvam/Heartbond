# AI ile geliştirme

Metropolis boyunca neredeyse her oturumda agent'larla nasıl çalışılacağı konuşuldu. Buradaki notlar oradan.

## Önce temeller

Harpal: *"Solidify the fundamentals first so that when you are prompting, your prompts are much better and the output is less error prone."*

Bu, uzman olana kadar beklemek demek değil. Alan bilgisi, agent'ı yönlendirdiğin kontrol yüzeyi: kısıtları koymanı, yanlış bir soyutlamayı fark etmeni ve hata büyümeden çıktıyı düzeltmeni sağlıyor.

Port kaynak sayfası için şunu söyledi: *"Copy these for your agent... just glance at them as a human... do not stop being human."* Bağlamı agent'a yükle, ama önce mimariyi onaylayabilecek kadar kendin anla. Kulağa mantıklı gelen bir implementasyonu olduğu gibi kabul etme.

## Aşamalı çalışma düzeni

MetaMask plugin oturumunda anlatılan akış:

1. Diyagramlarla araştırma
2. Ürünün ne olacağını tanımlama
3. PRD üzerinde iterasyon
4. **Temiz bir context'te** implementasyon
5. **Başka bir temiz context'te** test
6. İnsan eliyle QA

Araştırma, ürün kararları, implementasyon ve testi ayırmak kozmetik bir tercih değil. Agent'ın mimari ipi kaybetmesini engelliyor.

Agora oturumunda anlatılan benzer akış:

1. **PRD:** Ürün neden var, başarı ve başarısızlık neye göre ölçülecek.
2. **Teknik tasarım:** Hangi entegrasyonların kullanılacağı somut olarak seçilir.
3. **İmplementasyon.**

Agent'ları rakip API'leri araştırmak ve varsayımlarına itiraz etmek için kullan. Ama çalışma alanını tutarlı tut ve kararları insan olarak sen ver.

## Kalıcı plan

Harpal'ın önerisi: plan mode ve fikri zorlayan bir soru-cevap skill'i ile fikri test et, sonra repoda kalıcı bir checklist oluştur. Böylece context dolduğunda yeni bir oturum ya da başka bir agent kaldığı yerden devam edebilir.

## Başarısızlık koşullarını önce yaz

Zincir üstü ürünlerde, implementasyondan önce başarısızlık koşullarını ve güvenlik açısından başarı kriterlerini tanımla. Böylece doğru davranışı ölçen bir test suite'i yazabilir ve agent'ın ürettiği kontrat kodunu açık beklentilere göre inceleyebilirsin. Gerçek para ya da production davranışı söz konusuysa kontratı okumak yine şart.

Envio'dan Denham: *"Agentic development now is really, really nicely coupled with test-driven development."* Agent handler'ları hızlıca yazabilir, ama bir refactor ya da model tarafından yapılan bir değişiklikten sonra handler'ın hâlâ zincirdeki davranışı doğru temsil ettiğini testler kanıtlar. Indexer'larda bu özellikle önemli: zararsız görünen bir yorum hatası, her kullanıcı için yanlış bir ürün görünümüne dönüşür.

## Agent'a doğru bağlamı ver

Web aramasının doğru dokümanı bulmasını umma. Göreve özel, güvenilir bağlam ver:

- **Monad docs MCP:** Agent'ı güncel Monad dokümantasyonuna yönlendiriyor.
- **Metropolis kaynak sayfası:** Olduğu gibi kopyalanıp agent'a verilebilir. Sponsor araçları, krediler, skill'ler, starter şablonları ve track'e özel referanslar içinde. Bu klasördeki `ek/resources-sayfasi.md` onun kopyası.
- **Sponsor MCP'leri ve skill'leri:** Alchemy, Envio, Uniswap, Morpho, Zerion, Dynamic kendi MCP server'larını veya agent skill'lerini sunuyor. Liste `07-kaynaklar.md` içinde.

Dynamic oturumundan: AI döneminde dokümantasyonun asıl okuyucusu çoğu zaman bir agent. Dynamic'in MCP'si güncel dokümanı düşük context maliyetiyle getiriyor, CLI'ı ise dashboard ayarlarını açıyor. İkisi birlikte, agent'ın modelin eski bilgisine ya da elle dashboard gezmeye güvenmeden stack'i kurmasını ve sorunları teşhis etmesini sağlıyor.

## Tasarım

Tasarım kalitesi agent'a devredilebilir, ama jenerik olmadan:

1. Somut bir tasarım sistemi ver: markdown olarak ya da istediğin etkileşim diline sahip ürünlerden ekran görüntüleriyle.
2. Agent'tan bunlardan tekrar kullanılabilir bir tasarım dosyası çıkarmasını iste.
3. Düzeltme gerektiğinde "daha güzel yap" gibi genel istekler yerine bileşen seviyesinde, belirli bir öğeyi hedefle.

## Güvenlik

**API key'ler.** Alchemy'den Uttam: *"Please make sure that you're using API key and storing it in .env... protect the API key, please."* Agent'la geliştirmek secret hijyenini gevşetmez. Key'leri commit edilen koda ve rastgele prompt metinlerine koyma; environment üzerinden ya da daha güçlü bir secret yönetimiyle ver. CLI ile kimliği doğrulanmış bir oturumu da ayrıcalıklı erişim olarak gör.

**Agent cüzdanları.** Port: *"No one's going out there and pasting private keys around anymore."* Uzun süre çalışan bir agent'ın kodda, shell geçmişinde ya da sunucuda duran ham bir private key'e değil, fonlaması ve yetkisi sınırlandırılmış bir imzalama sınırına ihtiyacı var. Otomasyonun zincir üstünde işlem yapması gerekiyorsa agent wallet daha güvenli yapı taşı.

Dynamic oturumundan izin modeli:

| İhtiyaç | Kullanılacak yapı |
|---|---|
| Bağımsız çalışan bir agent | Autonomous wallet |
| Backend otomasyonu | Server wallet |
| Kullanıcının, agent'ın kendi cüzdanından işlem yapmasına izin vermesi | Delegated access |

Delegasyon politika ile sınırlı, süreli ve iptal edilebilir olmalı.

**Agent'a güvenmenin yolu yasaklamak değil, denetlemek.** Uzmanlaşmış bir execution agent'ı bir işlem önersin; bekleyen işlem bir review webhook'una ya da kuralları uygulayan ve işlemi zincire gitmeden reddedebilen bir "personal CFO" agent'ına gitsin. Kod yazarken kullandığımız "üret + PR review" düzeninin aynısı.

## Bu notları AI'ına vermek

Klasörün tamamını ya da sadece ilgili dosyaları agent'ının çalışma alanına koy. Başlangıç için şöyle bir prompt kullanabilirsin:

```
metropolis-notlari/ klasöründe Monad Metropolis hackathon'u için notlar var.
Önce README.md, 01, 02 ve 03 numaralı dosyaları oku.

Fikrim: <bir-iki cümle>
Hedeflediğim track: <track>

1. Bu fikir 01 ve 03'teki kriterlere göre nerede zayıf? Açık sözlü ol.
2. 05-sponsor-notlari.md'ye bakarak hangi sponsor araçlarının ürünün
   çekirdeğinde anlamlı bir yeri olabileceğini söyle. Sadece rozet gibi
   duracak olanları ayrıca belirt.
3. Henüz kod yazma. Önce bana cevaplamam gereken soruları sor.
```

Teknik bir işe geçtiğinde `06-monad-teknik.md` ve ilgili sponsorun bölümünü, gerekirse `ek/resources-sayfasi.md` dosyasını ekle.
