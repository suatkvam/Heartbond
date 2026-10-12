# Monad teknik notlar

Kod yazmaya başlamadan önce bilinmesi gerekenler. Ayrıntı için her başlıktaki resmi dokümana git.

## Temel bilgiler

- Tam Ethereum RPC uyumluluğu. Solidity, Foundry, Hardhat, Remix, viem/ethers olduğu gibi çalışıyor.
- 400ms blok süresi, 800ms finality. Arayüzünü bu performansa göre tasarlayabilirsin: uzun "pending" ekranlarına gerek kalmayan akışlar mümkün.
- Chain ID: mainnet `143`, testnet `10143`.

İlk okunacaklar:

- [Differences from Ethereum](https://docs.monad.xyz/developer-essentials/differences): Monad'a deploy ederken neyin değiştiği.
- [Developer essentials summary](https://docs.monad.xyz/developer-essentials/summary): Tüm "essentials" bölümü tek sayfada.
- [Monad for Developers](https://docs.monad.xyz/introduction/monad-for-developers)

## Gas ve bakiye

- [Gas pricing](https://docs.monad.xyz/developer-essentials/gas-pricing) ve [Opcode pricing](https://docs.monad.xyz/developer-essentials/opcode-pricing): Gas'ın nasıl fiyatlandırıldığı ve opcode bazında maliyetler. Ethereum'daki sezgilerin burada birebir geçerli olmayabilir.
- [Reserve balance](https://docs.monad.xyz/developer-essentials/reserve-balance): Paralel yürütme altında bakiye rezervasyonu. Native token bakiyesiyle ilgili mantık yazıyorsan oku.

## MIP-8: sayfalı storage

MIP-8 bir Solidity sözdizimi problemini değil, fiziksel bir storage darboğazını çözüyor. Diskten okumak hesaplamadan çok daha yavaş ve Monad'ın hızlı yürütmesi bu dengesizliği daha belirgin hale getiriyor. MIP-8 ile 128 slotluk bir sayfa, yaklaşık tek bir slot okuma maliyetine çekiliyor. Yani birbirine yakın state'e erişim ciddi şekilde ucuzluyor.

**Pratik kural değişiyor:** "Her slotu minimize et" yerine "sık kullanılan yolu optimize et."

- İlişkili standart slotlar zaten yan yana düşüyorsa kontrat bundan otomatik faydalanıyor.
- Aynı kullanıcıya göre key'lenmiş birkaç ayrı mapping'in varsa, bu alanları tek bir mapping'deki tek bir struct'ta toplamak yakınlığı artırır. Bu, bit seviyesinde akıllı paketleme yapmaktan hem daha basit hem genellikle daha güvenli.

```solidity
// Önce: aynı kullanıcı için üç ayrı mapping, üç ayrı yer
mapping(address => uint256) public balance;
mapping(address => uint64)  public lastAction;
mapping(address => uint32)  public level;

// Sonra: tek struct, yan yana slotlar
struct User {
    uint256 balance;
    uint64  lastAction;
    uint32  level;
}
mapping(address => User) public users;
```

**MIP-8 her state'i bedava yapmıyor.** Yeni oluşturulan bir slota yazmanın hâlâ maliyeti var. Kullanıcı başına ya da işlem başına state, global olarak erişilen bir alandan farklı değerlendirilmeli. Asıl fırsat: tekrar eden kullanıcı yolunu iyileştiriyorsa fazladan yakın bir slot harcamak, çünkü yakın erişimin cezası ciddi şekilde düştü.

**Uygulama tarafında yapman gereken bir şey yok.** Yeni opcode, compiler ya da özel Solidity gerekmiyor. Ama ölçüm yaparken Foundry'de Monad gas fiyatlamasını aç ki local testler ağın ekonomisini yansıtsın. Elle sayfa yerleşimi yönetmek ya da assembly'ye inmek sadece gerçekten performans kritik tasarımlar için (örneğin merkezi bir limit order book) mantıklı.

**Ürün tarafındaki anlamı** "her yere state ekle" değil. Daha önce çok pahalı olan tasarımları yeniden düşünmek: daha zengin AMM piyasa geçmişi ve dinamik ücret mantığı, daha uygulanabilir order book kontratları, daha derin state'e sahip zincir üstü oyunlar.

Protokol mühendisliği açısından ilginç bir not: Validator'lar bir süre hem eski hem sayfalı storage temsilini birlikte tuttu, yenisini güncel hale getirdi ve ücretlendirmeyi ancak doğru çalıştığı görüldükten sonra değiştirdi. Tüm validator'ları etkileyen bir storage değişikliği, uygulamalardan migration ya da kontrat yeniden yazımı istenmeden yapıldı.

## Hesaplar ve imzalama

- [EIP-7702](https://docs.monad.xyz/developer-essentials/eip-7702): EOA'lardan smart account'lar. Kuru oturumundaki portfolio-manager demo'su buna dayanıyordu: sahip hesabı ayrı, günlük limitli ve harcanabilir bir trading yetkisi ayrı (bkz. `05-sponsor-notlari.md` > Kuru).
- [Mera](https://docs.monad.xyz/guides/mera): Passkey tabanlı hesap katmanı. İki Monad Foundation bounty'si doğrudan Mera üzerine: hesap katmanının tamamen Mera olduğu bir UX ve PRF ile türetilmiş anahtar materyalinin cüzdan dışı yaratıcı kullanımı.
- **Passkey doğrulaması ve RIP-7212:** RIP-7212 (P256VERIFY precompile) P-256 doğrulamasını ~300,000 gas'tan ~3,450 gas'a indiriyor. Ancak bu bir L2 önerisi ve Cancun'un parçası değil. Kaynak sayfasının notu: Monad'da mevcut **olmadığını varsay ve doğrula**. Yedek olarak [Solidity P-256 verifier](https://github.com/getclave/eip-7212) her zincire deploy edilebilir; Monad'da pahalı Solidity yolu bile dolar cinsinden ucuz kalıyor. Güncel durum için [Precompiles](https://docs.monad.xyz/developer-essentials/precompiles) sayfasına bak.

## Agent'lar için standartlar

- [x402](https://docs.monad.xyz/guides/x402#what-is-x402): Agent'lar ve API'ler için HTTP üzerinden yerleşik ödeme.
- [ERC-8004](https://docs.monad.xyz/guides/erc-8004): Agent'lar için güvene dayanmayan (trustless) kimlik ve itibar. [Trust8004](https://www.8004.org/build), Monad dahil ağlardaki ERC-8004 agent'larını indexleyen ücretsiz bir API.

## Deploy ve doğrulama

- [Deploy a smart contract](https://docs.monad.xyz/guides/deploy-smart-contract/index): Foundry, Hardhat, Remix.
- [Verify a smart contract](https://docs.monad.xyz/guides/verify-smart-contract/index): Explorer'larda kaynak kodu doğrulama.
- [Tooling and infra](https://docs.monad.xyz/tooling-and-infra): RPC'ler, indexer'lar, oracle'lar ve diğer altyapı.
- [Cross-chain (CCIP + CCTP)](https://docs.monad.xyz/tooling-and-infra/cross-chain): Kontrat adresleri.
