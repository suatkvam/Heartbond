# UI Devir Belgesi — GPU SLA Escrow

> Frontend'i yazan arkadaş için. Bunu ve `shared/abi/GpuSlaEscrow.json` dosyasını
> kendi AI aracına da verebilirsin; ihtiyacın olan her şey burada.
> Değişiklikler `docs/INTERFACE_CHANGELOG.md` dosyasına yazılır, oraya bakman yeterli.

---

## 1. Proje bir dakikada

GPU kiralarken "makine çalıştı mı, çalışmadıysa param ne olacak?" sorusunun cevabı bugün
platformun kendi iç kararına bağlı. Bu kararı kimse dışarıdan denetleyemiyor.

Biz bunun yerine bir **akıllı kontrat (escrow)** yapıyoruz:

1. **Kiracı (renter)** kontratı oluşturuyor ve ücreti (MON) kontrata kilitliyor. Şartları
   da birlikte yazıyor: sağlayıcı adresi, "en az %75 çalışma süresi" gibi bir eşik ve süre.
2. Kiralama süresi eşit **slotlara** bölünüyor (demoda 4 × 30 sn). Her slot bitince bizim
   **oracle** servisimiz makineyi kontrol edip zincire "UP" ya da "DOWN" yazıyor.
3. Süre ve 30 sn'lik ek süre (grace) bitince **herhangi biri** `settle` butonuna basabiliyor.
   Kontrat hesaplıyor: UP slot sayısı eşiği geçiyorsa para sağlayıcıya, geçmiyorsa
   kiracıya iade.
4. 60 sn'lik **itiraz penceresi** açılıyor. Taraflar itiraz edebilir ama itiraz sadece
   kayda geçer, sonucu değiştirmez (bunu saklamıyoruz, açıkça söylüyoruz).
5. Pencere kapanınca **herhangi biri** `finalize` diyor. Para kazanan tarafın bakiyesine
   yazılıyor; o kişi `withdraw` ile çekiyor.

Demodaki "vay" anı: makineyi temsil eden Docker konteynerini canlı olarak `docker stop`
ile kapatıyoruz → slotlar DOWN oluyor → **üçüncü, ilgisiz bir cüzdan** settle'a basıyor →
para kiracıya iade ediliyor. Kimse kimseden izin almıyor.

**Dürüst sınır:** oracle'ı biz çalıştırıyoruz, yani veriye güven tek kaynaktan geliyor.
UI'da bunu gizlememiz gerekmiyor; "Reporter: team-held" gibi küçük bir etiket yeterli.

## 2. İş bölümü

| Konu | Kimde |
|---|---|
| `frontend/` klasörü, tasarım, tüm ekranlar | **sen** |
| Kontrat, oracle, deploy, testler, demo akışı | Sora |
| `shared/abi/GpuSlaEscrow.json` (ABI) | Sora üretir, sen okursun |
| `shared/deployments/monad-testnet.json` (adres, deploy bloğu) | Sora deploy ettikçe günceller |

Kontrat henüz deploy edilmedi. O zamana kadar §9'daki mock veriyle çalış. ABI şimdiden
dondu (fonksiyon isimleri ve sıraları değişmeyecek, değişirse CHANGELOG'a BREAKING diye yazılır).

## 3. Zincir ayarı

- Ağ: **Monad Testnet**, chainId **10143**, RPC `https://testnet-rpc.monad.xyz`
- Faucet: https://faucet.monad.xyz · Explorer: https://testnet.monadvision.com, https://testnet.monadscan.com
- Kütüphane: **viem ≥ 2.40** (istersen wagmi ile). `viem/chains` içinde `monadTestnet`
  varsa onu kullan; yoksa:

```ts
import { defineChain } from 'viem'
export const monadTestnet = defineChain({
  id: 10143,
  name: 'Monad Testnet',
  nativeCurrency: { name: 'MON', symbol: 'MON', decimals: 18 },
  rpcUrls: { default: { http: ['https://testnet-rpc.monad.xyz'] } },
  blockExplorers: { default: { name: 'MonadVision', url: 'https://testnet.monadvision.com' } },
})
```

```ts
import abi from '../shared/abi/GpuSlaEscrow.json'
import dep from '../shared/deployments/monad-testnet.json' // { address, deployBlock, ... }
```

## 4. Yazma fonksiyonları (transaction)

İsimler Vyper'dan geldiği için `snake_case`. Tüm süreler **saniye** (unix), tüm tutarlar **wei**.

| Fonksiyon | Kim çağırır | Argümanlar | `value` | Hangi `phase`'te buton görünsün |
|---|---|---|---|---|
| `create_rental` | kiracı | `provider: address, threshold: uint256 (1–100), interval: uint256, start: uint256, end: uint256, spec_ref: bytes32` | ücret (wei) | her zaman (form) |
| `settle` | **herkes** | `rental_id` | — | 4 Settleable |
| `raise_objection` | sadece o kiralamanın kiracısı/sağlayıcısı, birer kez | `rental_id` | — | 5 Challenge |
| `finalize` | **herkes** | `rental_id` | — | 6 Finalizable |
| `withdraw` | bakiyesi olan herkes | — | — | `credits(account) > 0` |
| `report_uptime` | sadece oracle | — | — | **UI'da yok** |

**Form → argüman dönüşümü (create_rental):**
- `start` = **zincirdeki son bloğun timestamp'i + 15** (`getBlock()`), `Date.now()` değil
  (bilgisayar saati kayabilir; kontrat geçmiş start'ı reddeder).
- Kullanıcıya "slot süresi (sn)" ve "slot sayısı" sor → `end = start + interval * slotCount`.
  Böylece "süre interval'in katı olmalı" kuralı otomatik sağlanır. Slot sayısı ≤ 256.
- `threshold`: 1–100 tam sayı. Demo varsayılanları: interval 30, slot 4, threshold 75, ücret 0.01 MON.
- `spec_ref`: GPU tanımı ("RTX 4090 24GB" gibi) → `stringToHex(text, { size: 32 })`. Mantıkta kullanılmıyor, sadece gösterim.
- Dönen `rental_id`'yi `RentalCreated` event'inden ya da `next_rental_id() - 1`'den al.

**Gas:** Monad gas *limitini* tahsil eder, kullanılanı değil. `estimateContractGas` × 1.2 ile
açık bir `gas` ver; cüzdanın kafasına göre büyük limit koymasın.

**Revert mesajları** (ekranda Türkçe karşılığını göster):

| Kontrat mesajı | Kullanıcıya |
|---|---|
| `start in past` | Başlangıç zamanı geçti, tekrar dene |
| `end before start` / `zero interval` / `not multiple` / `too many slots` | Süre ayarları geçersiz |
| `bad threshold` | Eşik 1–100 arası olmalı |
| `zero provider` / `renter is provider` | Sağlayıcı adresi geçersiz |
| `no value` | Ücret 0 olamaz |
| `not active` | Bu kiralama zaten settle edilmiş |
| `too early` | Raporlama süresi henüz bitmedi |
| `not proposed` | Önce settle gerekiyor / zaten finalize edildi |
| `window closed` | İtiraz süresi doldu |
| `not a party` | Sadece kiracı veya sağlayıcı itiraz edebilir |
| `already objected` | Zaten itiraz ettin |
| `window open` | İtiraz penceresi henüz kapanmadı |
| `nothing to withdraw` | Çekilecek bakiye yok |

## 5. Okuma fonksiyonları (view, gas yok)

| Fonksiyon | Döner | Not |
|---|---|---|
| `rentals(id)` | struct: `renter, provider, price, threshold, interval, start, end, n_slots, up_count, reported_count, status, proposed_at, compliant, renter_objected, provider_objected, spec_ref` | Detay sayfasının ana verisi |
| `get_slots(id)` | `uint8[]` uzunluk `n_slots` — **0 boş, 1 UP, 2 DOWN** | Slot kutucukları |
| `phase(id)` | `uint8` (aşağıda) | Butonları buna göre aç/kapa |
| `payout_preview(id)` | `(compliant: bool, payee: address, amount: uint256)` | "Şu an settle edilse kime gider" — settle sonrası kesin sonuç |
| `credits(address)` | `uint256` wei | Withdraw butonu |
| `next_rental_id()` | `uint256` | Liste: id'ler `1 .. next_rental_id-1` |
| `REPORT_GRACE()` / `CHALLENGE_WINDOW()` | 30 / 60 | Geri sayımlar için |
| `is_reporter(address)` | `bool` | Oracle panelinde gösterim |

`status`: 0 None · 1 Active · 2 Proposed · 3 Settled

**`phase(id)` değerleri — UI'ın ana anahtarı:**

| Değer | Ad | Ne zaman | Gösterilecek |
|---|---|---|---|
| 0 | None | id yok | "Bulunamadı" |
| 1 | Scheduled | şimdi < start | "Başlamasına X sn" |
| 2 | Running | start ≤ şimdi < end | slotlar dolmaya başlar |
| 3 | Grace | end ≤ şimdi ≤ end+30 | "Son raporlar bekleniyor" |
| 4 | Settleable | Active ve şimdi > end+30 | **Settle** butonu (herkese açık) |
| 5 | Challenge | settle sonrası 60 sn | sonuç + **İtiraz Et** (sadece taraflara) |
| 6 | Finalizable | pencere kapandı | **Finalize** butonu (herkese açık) |
| 7 | Settled | bitti | sonuç; kazanana **Withdraw** |

Geri sayımlar: Scheduled→`start`, Running→`end`, Grace→`end+30`, Challenge→`proposed_at+60`.
Zamanı zincirden al (son blok timestamp'i), tarayıcı saatinden değil.

**Yenileme:** her 2 sn'de bir aktif kiralama için `rentals`, `get_slots`, `phase` oku.
Public RPC hız sınırlı (~20–50 istek/sn): ekranda olmayan kiralamaları sorgulama.

## 6. Event'ler (geçmiş görünümü — P2, en son yapılır)

| Event | Alanlar (indexed olanlar *) |
|---|---|
| `RentalCreated` | rental_id*, renter*, provider*, price, threshold, interval, start, end, n_slots, spec_ref |
| `UptimeReported` | rental_id*, slot, up, reporter* |
| `SettlementProposed` | rental_id*, up_count, n_slots, compliant, payee*, amount, proposed_at, caller |
| `ObjectionRaised` | rental_id*, by*, is_renter |
| `SettlementFinalized` | rental_id*, payee*, amount, caller |
| `Withdrawn` | account*, amount |

`getLogs`'u `deployBlock`'tan başlat, parça parça (ör. 5.000 blok) iste. Bloklar ~300 ms,
yani 1 saat ≈ 12.000 blok. Her satırda explorer'a tx linki koy — demoda jüri buna tıklıyor.
`caller` alanı önemli: settle/finalize'ı **kimin** çağırdığını göster (üçüncü cüzdan anı).

## 7. Oracle kontrol API'si (HTTP, opsiyonel panel)

Oracle servisi Sora'nın makinesinde çalışır: `http://localhost:8787`. **UI bu API olmadan
da çalışmalı** — doğruluk kaynağı zincir. Bu API sadece demo panelini zenginleştirir.

| Metot | Yol | Gövde | Döner |
|---|---|---|---|
| GET | `/health` | — | `{ ok, chainId, contract, reporters: [{ address, balanceMon }] }` |
| GET | `/nodes` | — | `[{ provider, url, lastProbe: { ok, at, latencyMs } }]` |
| GET | `/rentals` | — | izlenen kiralamalar: `[{ rentalId, provider, slots: [...] }]` |
| GET | `/rentals/{id}` | — | `{ rentalId, slots: [{ slot, probesOk, probesTotal, forcedDown, reported, up, txHash }] }` |
| POST | `/rentals/{id}/force-down` | `{ "slots": [2, 3] }` | `{ ok: true }` — yedek kontrol |
| DELETE | `/rentals/{id}/force-down` | — | `{ ok: true }` |

`at` ISO-8601, `txHash` henüz gönderilmediyse `null`. CORS localhost için açık.
Panel fikri: node durumu (yeşil/kırmızı nokta, son probe), slot başına "5/6 probe OK",
tx hash linki. Force-down butonu sadece "demo modu" açıkken görünsün.

## 8. Ekranlar (öncelik sırasıyla)

1. **Bağlan** — cüzdan bağla, yanlış ağdaysa Monad Testnet'e geçir. Bağlı adres + MON bakiyesi.
2. **Kiralama oluştur** — §4 formu. Demo varsayılanları dolu gelsin.
3. **Kiralama detayı** (en önemli ekran):
   - üstte taraflar (renter/provider kısaltılmış adres) + "Sen: kiracı / sağlayıcı / üçüncü taraf" rozeti
   - 4 slot kutusu: gri boş · yeşil UP · kırmızı DOWN; "UP 3/4 — eşik %75" çubuğu
   - büyük phase etiketi + geri sayım
   - bağlama göre tek bir ana buton (Settle / İtiraz Et / Finalize / Withdraw)
   - `payout_preview`: "Şu an settle edilirse: 0.01 MON → sağlayıcı"
   - itiraz bayrakları: "Kiracı itiraz etti ✓ — sonucu değiştirmez"
4. **Kiralama listesi** — id, durum, taraflar; tıklayınca detay.
5. *(P2)* **Geçmiş** — §6 event'leri zaman sırasıyla.
6. *(opsiyonel)* **Oracle paneli** — §7.

Demo sırasında 3 cüzdan aynı anda açık olacak (kiracı, sağlayıcı, üçüncü kişi), o yüzden
"Sen kimsin" rozeti ve büyük, okunaklı butonlar ekranda iyi görünür.

## 9. Mock veri (kontrat deploy edilene kadar)

```json
{
  "rental": {
    "renter": "0x1111111111111111111111111111111111111111",
    "provider": "0x2222222222222222222222222222222222222222",
    "price": "10000000000000000", "threshold": 75, "interval": 30,
    "start": 1790000015, "end": 1790000135, "n_slots": 4,
    "up_count": 2, "reported_count": 4, "status": 2, "proposed_at": 1790000170,
    "compliant": false, "renter_objected": true, "provider_objected": false,
    "spec_ref": "0x5254582034303930203234474200000000000000000000000000000000000000"
  },
  "slots": [1, 1, 2, 2],
  "phase": 5,
  "payout_preview": [false, "0x1111111111111111111111111111111111111111", "10000000000000000"]
}
```

Okuma katmanını tek bir dosyada topla (`useRental(id)` gibi) ki mock'tan gerçeğe geçiş
tek satır olsun.
