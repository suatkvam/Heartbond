# Çalışma Planı — GPU SLA Escrow

## 1. Hakem geri bildirimine verdiğimiz kararlar

| # | Hakemin söylediği | Karar | Nerede |
|---|---|---|---|
| 1 | Tek oracle EOA'sı → tek nonce → "paralel EVM" argümanı boş | 1–8 reporter key (hepsi bizde), her kiralama `rental_id % n` ile kendi key'inden raporlanır, rapor yolunda global storage yazılmaz. Demoda 2 kiralamanın raporu 2 farklı göndericiden aynı blokta. **Pitch cümlesi:** "Nonce darboğazını kaldırdık, güven kaynağı hâlâ tek — sonraki adım bağımsız reporter seti." | SPEC R-1..R-3 |
| 2 | Monad rakamları yanlış olabilir (400/800/2–3/200M) | 01.10.2026'da canlı doküman (developer-essentials/summary) hâlâ **300 ms / 600 ms / 3–4 / 150M** diyor, yani PRD sayfayla tutarlı. Yine de: `smoke_test.py` blok süresini canlı ölçüyor; pitch'te her sayı kaynak + tarih ile yazılır, demo günü tekrar kontrol edilir. | SPEC §7 |
| 3 | Vyper + Monad test edilmemiş | Gün 0'da `Hello.vy` deploy + event + explorer doğrulaması. ~2 saatte çözülmezse Solidity'e geç (aynı SPEC, aynı ABI isimleri). | SPEC G-1..G-3 |
| 4 | Push payment → fon kilitlenebilir | **Şimdi** pull-payment'a geçtik: `finalize` sadece bakiye yazar, `withdraw` gönderir. | SPEC F-4, P-1..P-3 |
| 5 | Provider on-chain onay vermiyor | MVP'de değişmiyor; demo anlatımında ilk biz söylüyoruz. Vakit kalırsa Could-Have: sözleşmeyi bloke etmeyen `provider_ack` event'i. | SPEC §9, pitch QA |
| 6 | Adoption yolu açık | Pitch'te "en büyük açık soru" diye çerçeve; demodan önce 42'de GPU kiralayan 3–5 kişiyle kısa görüşme (PRD §24) → tek bir gerçek alıntı bile pitch'i güçlendirir. | pitch-factchecker |
| Demo | Force-down yerine `docker stop` | Oracle gerçek `/health` probe'u yapıyor; force-down yedek olarak kalıyor. | SPEC H-1..H-7 |

## 2. Gün 0 kontrol listesi (bugün / hackathon başlamadan)

- [ ] **Hackathon kuralı:** önceden yazılmış koda izin var mı? Yoksa sadece bu iskeleti
      (arayüz + dokümanlar) hazır tut, gövdeleri hackathon başlayınca yaz.
- [ ] Repo: `git init`, GitHub'a private push, arkadaşı ekle.
- [ ] `pip install -r requirements.txt` → `pytest -q tests/` → 5 geçer, 3 kırmızı (beklenen).
- [ ] Cüzdanlar: deployer, reporter1, reporter2, renter, provider, stranger. Faucet'in
      ne kadar verdiğini ölç — her EOA 10 MON reserve üstünde olmalı. Yetmiyorsa
      deployer = stranger yap.
- [ ] `.env` doldur → `python scripts/smoke_test.py` → çıktıyı (blok süresi, ortak timestamp) kaydet.
- [ ] `Hello.vy`'yi explorer'da doğrula (Sourcify/MonadVision ya da Monadscan, Vyper 0.4.3 seç).
- [ ] Arkadaşa §4'teki mesajı + `docs/UI_HANDOFF.md`'yi gönder.

## 3. Yapım sırası ("önce arayüz", arkadaş hiç beklemesin)

| Adım | İş | Kim | Bitince |
|---|---|---|---|
| 1 | `create_rental` gövdesi (C-1.*) | sen (`pair` modu) + test-engineer | **v0 deploy** → arkadaş gerçek kiralama oluşturabilir, slotlar boş görünür |
| 2 | `report_uptime` (O-*) + basit oracle (sabit UP) | sen + oracle-engineer | v0.2 deploy → arkadaş slotların dolduğunu görür |
| 3 | `settle`, `raise_objection`, `finalize`, `withdraw` (S/X/F/P) | sen + test-engineer | tüm demo akışı zincirde |
| 4 | Oracle: Docker probe, çoklu key, kontrol API'si | oracle-engineer | `docker stop` demo'su çalışır |
| 5 | security-reviewer → final deploy → interface-sync | ajanlar | adres dondu |
| 6 | Demo script, QA, README, 2 prova, yedek video | pitch-factchecker + sen | teslim |

Her deploy'dan sonra **interface-sync** çalışır, arkadaşa yapıştırılacak mesajı üretir.
Kesme sırası (PRD §8.1): event geçmişi → Could-Have'ler → oransal iade → frontend (cast/script yedeği).

## 4. Arkadaşa gönderilecek ilk mesaj

> Proje: GPU kiralamada "makine çalıştı mı" kararını platform yerine bir kontrata bırakıyoruz.
> Kiracı parayı kilitliyor, oracle her 30 sn'lik slot için UP/DOWN yazıyor, süre bitince
> herkes "settle" diyebiliyor, eşik tutarsa para sağlayıcıya, tutmazsa kiracıya.
> Senin işin sadece `frontend/`. Her şey `docs/UI_HANDOFF.md`'de: fonksiyonlar, `phase`
> değerine göre hangi buton, hata mesajları, ekran listesi, mock veri. ABI
> `shared/abi/GpuSlaEscrow.json`'da ve donduruldu. Deploy edene kadar mock'la çalış, ilk deploy
> `create_rental` biter bitmez gelecek. Değişiklikler `docs/INTERFACE_CHANGELOG.md`'de olur.
> AI kullanıyorsan bu iki dosyayı ona ver. Stack önerim: React + Vite + viem (≥2.40), istersen wagmi.

## 5. Claude Code'u kullanma

Repo kökünde `claude` → CLAUDE.md ve 6 ajan otomatik yüklenir. Örnek komutlar:
- "test-engineer ile C kurallarının eksik testlerini yaz"
- "contract-engineer: S-1..S-5'i anlat, ben yazacağım" (pair modu)
- "security-reviewer çalıştır, deploy edebilir miyiz?"
- "deploy ettim, adres 0x…, blok N — interface-sync çalıştır"
- "pitch-factchecker: QA.md'yi hakem notlarındaki 6 riskle hazırla"

Vakit daralırsa CLAUDE.md'de `CONTRACT_MODE: auto` yap.
