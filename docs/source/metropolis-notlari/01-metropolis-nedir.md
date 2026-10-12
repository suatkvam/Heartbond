# Metropolis nedir

Metropolis, Monad üzerinde ürün geliştirmek için yapılan altı haftalık bir hackathon. Kaynak sayfası: <https://hackathon.monad.xyz/resources>

## Jüri neye bakıyor

Açılışta Port'un ilk cümlesi şuydu: *"This is not a usual hackathon."*

Pratikteki anlamı şu: bir proje demo gününde ne kadar parlak göründüğüyle değil, sonrasında kullanılmaya devam edip etmeyeceğiyle değerlendiriliyor. Teknik olarak etkileyici ama kimsenin geri dönmeyeceği bir proje hedeflenen şey değil.

Başlamak için üç şeye ihtiyacın var:

1. Gerçek bir kullanıcı.
2. O kullanıcının tekrar tekrar yaşadığı bir problem.
3. Bunun neden Monad'da yapıldığına dair ürün tarafında bir gerekçe (hızlı ve ucuz settlement, order book'ların zincir üstünde çalışabilmesi vb.).

Altı hafta "daha çok kod yazma süresi" olarak düşünülmemeli. Asıl kullanımı: erken bir sürümü gerçek birinin önüne koymak, nerede takıldığını izlemek ve tekrar kullanıp kullanmayacağını görmek. Örneğin bir ödeme uygulamasında işlemin başarıyla gitmesi, ürünün çalıştığını tek başına kanıtlamaz.

## Tekerleği yeniden icat etme

Port: *"Do not try to re-invent the wheel. Check what is available on Monad right now and try to combine them in a way that can solve a problem."*

Sponsorları incelemek ödül avcılığı değil, mimari keşif. Bunu fikre bağlanmadan önce yap. Hazır bir altyapı bütün bir alt sistemi yazmaktan seni kurtarabilir ve asıl inşa etmen gereken katmanın ne olduğunu gösterir.

Başlamadan önce [Monad App Hub](https://app.monad.xyz/app-hub)'a ve [ekosistem dizinine](https://www.monad.xyz/ecosystem) bak. Yapmayı düşündüğün şey zaten var olabilir; o zaman ya farklılaşırsın ya da onun üstüne inşa edersin.

## Platform nasıl işliyor

- Önce bir proje oluşturuyorsun. Proje bir takıma ait. Tek kişilik takım da takım sayılıyor.
- Projeye **bir** ana track seçiyorsun. Ana track, projenin hangi kategoride değerlendirileceğini belirliyor.
- Üstüne istediğin kadar sponsor bounty'si ekleyebilirsin. Her bounty, gönderimde doldurman gereken alanları kendisi listeliyor.
- Bazı bounty'ler belirli bir track'e bağlı, bazıları "All tracks" etiketli. Track'e bağlı bir bounty'nin ana track'ten bağımsız değerlendirilip değerlendirilmediğini platformdan ya da sponsor kanalından teyit et.

### Progress update ve mentorlar

Harpal: *"To unlock asking mentors feature, you have to post some progress update."*

Mentora soru sorma özelliği, progress update paylaştıktan sonra açılıyor. Kısa bir güncelleme, "blocked / on track" durumu ve ilgili bir link, mentorun sana nokta atışı yardım edebilmesi için gereken geçmişi sağlıyor. Update'leri bürokrasi olarak değil, sponsor uzmanlarına ulaşmanın yolu olarak gör.

## Teslimde beklenenler

Aurora'nın değerlendirme kriterlerinden genellenebilecek temel set:

- Public repository
- Teknik demo
- Pitch videosu
- Mümkünse canlı link

Bunun dışında her sponsorun kendi kriterleri var. Gönderim formunda görünüyor.

## Sponsor entegrasyonu çekirdekte olmalı

Birden fazla sponsor (Nansen ve Cleanverse açıkça) aynı şeyi söyledi: sponsorun aracı ürünün merkezinde olmalı, sonradan eklenmiş bir rozet gibi durmamalı.

Basit bir test var: o entegrasyonu koddan silersen ürün gerçekten bozuluyor mu? Bozulmuyorsa entegrasyon süs olarak kalmış demektir ve jüri de bunu fark eder.
