# Kaynaklar

[hackathon.monad.xyz/resources](https://hackathon.monad.xyz/resources) sayfasının Türkçe özeti. Sayfanın tamamı İngilizce olarak `ek/resources-sayfasi.md` içinde.

## Ücretsiz perk'ler

Metropolis'e dahil, her takım için birer tane.

| Perk | Ne veriyor | Yaklaşık değer | Claim |
|---|---|---|---|
| Tenderly Pro | Debug, simülasyon, izleme | $7,200 | [Notion](https://www.notion.so/monad-foundation/Tenderly-Access-for-Metropolis-participants-3ce6367594f280539f27d268d05431cd) |
| QuickNode Build Plan | Üç ay ücretsiz | $147 | [Notion](https://www.notion.so/quicknode/Quicknode-Credits-for-Metropolis-Hackers-3cd15a82e84c8093b33af5fee0452ca9) |
| Zerion API Builder | Bir ay ücretsiz | $149 | [Notion](https://zerion.notion.site/Free-Zerion-API-Builder-Plan-3cead18255da810aa409ebdcceb05ed3) |

## Monad dokümantasyonu

Teknik başlıkların açıklamalı listesi `06-monad-teknik.md` içinde. Başlangıç noktası: [Differences from Ethereum](https://docs.monad.xyz/developer-essentials/differences).

## Starter şablonları

Hepsi Monad Foundation'dan.

**Farcaster miniapp:** [Genel bakış](https://docs.monad.xyz/templates/farcaster-miniapp) · [Başlangıç](https://docs.monad.xyz/templates/farcaster-miniapp/getting-started) · [OG görselleri](https://docs.monad.xyz/templates/farcaster-miniapp/generating-custom-og-images) · [Haptics](https://docs.monad.xyz/templates/farcaster-miniapp/haptics) · [Bildirimler](https://docs.monad.xyz/templates/farcaster-miniapp/sending-notifications) · [Yayınlama](https://docs.monad.xyz/templates/farcaster-miniapp/publishing-miniapp)

**Next.js PWA:** [Privy embedded wallet](https://docs.monad.xyz/templates/next-serwist-privy-embedded-wallet) · [Privy smart wallet](https://docs.monad.xyz/templates/next-serwist-privy-smart-wallet) · [0x + Privy](https://docs.monad.xyz/templates/next-serwist-0x-privy-embedded-wallet) · [thirdweb](https://docs.monad.xyz/templates/next-serwist-thirdweb)

**React Native:** [Privy embedded wallet](https://docs.monad.xyz/templates/react-native-privy-embedded-wallet) · [Privy + Pimlico sponsorlu işlemler](https://docs.monad.xyz/templates/react-native-privy-pimlico-sponsored-transactions) · [thirdweb embedded wallet](https://docs.monad.xyz/templates/react-native-thirdweb-embedded-wallet)

Agora bounty'leri mobil uygulama istediği için React Native şablonları o bounty'ler için doğal başlangıç.

## Protokol SDK'ları

| SDK | Ne için |
|---|---|
| [Aave v3 React kit](https://aave.com/docs/aave-v3/getting-started/react) | Aave v3 üzerine hook ve bileşenler |
| [Morpho SDKs](https://docs.morpho.org/developers/sdks/get-started/) | Vault ve piyasalar için TypeScript |
| [Euler SDK](https://docs.euler.finance/developers/sdk) | EVK vault'ları ve swap'lar |
| [Curvance SDK](https://docs.curvance.com/app/developer-docs/sdk) | Curvance protokolü |
| [Perpl SDK](https://docs.perpl.xyz/resources/for-developers/sdk) | Perpl perpetuals motoru |
| [Alchemy Smart Wallets SDK](https://www.alchemy.com/docs/wallets/quickstart) | Bundler, gas sponsorluğu, ERC-20 ile gas ödeme |
| [Alchemy CLI](https://www.alchemy.com/docs/alchemy-cli) | RPC, cüzdan ve webhook'lar tek binary'de, `--json` ile agent'a uygun |
| [Blend SDKs](https://docs.blend.money/build/sdk/overview) | Deposit, çekim ve yield hesapları |
| [Zerion CLI](https://developers.zerion.io/build-with-ai/zerion-cli) | Cüzdan analizi, imzalama, swap; JSON çıktı |
| [Kuru SDK](https://www.npmjs.com/package/@kuru-labs/kuru-sdk) | Emir yönetimi, margin hesapları, WebSocket ile gerçek zamanlı yürütme |
| [0x Swap API](https://0x.org/docs) | 150+ likidite kaynağından swap'ı uygulamana gömmek |

## MCP server'lar ve agent skill'leri

- **Alchemy:** [MCP Server](https://www.alchemy.com/docs/alchemy-mcp-server) (API key gerekmiyor) · [Agent Skills](https://www.alchemy.com/docs/alchemy-agent-skills) · [Agent kimlik doğrulama ve x402 ile ödeme](https://www.alchemy.com/docs/alchemy-for-agents)
- **Envio:** [Indexer skill'leri](https://docs.envio.dev/blog/ai-agents-acting-onchain-indexer) (14 skill)
- **Uniswap:** [AI Skills](https://developers.uniswap.org/docs/uniswap-ai/skills)
- **Morpho:** [Morpho Agents](https://docs.morpho.org/developers/agents/get-started/)
- **Zerion:** [Agent Skills](https://developers.zerion.io/build-with-ai/zerion-cli#skills) (6 skill)
- **Monad Agent Kit:** [GitHub](https://github.com/stakeme-team/monad-agent-kit): agent'ların Monad'da okuma ve işlem yapması için MCP araç seti.

## Diğer faydalı kaynaklar

- [EIPs For Designers](https://www.eipsfordesigners.com/): Her Ethereum/Monad standardının kullanıcının gördüğü ve yaptığı şeyi nasıl etkilediği. UX tasarlarken işe yarıyor.
- [Prediction markets guide](https://therealharpaljadeja.github.io/prediction-markets-guide/#home): Prediction market'lerin nasıl çalıştığı, on kısa görsel bölümde.
- [Monad App Hub](https://app.monad.xyz/app-hub) ve [ekosistem dizini](https://www.monad.xyz/ecosystem): Yapmayı düşündüğün şey zaten var mı, önce buraya bak.
- [Monad AI Blueprint](https://www.monad.xyz/announcements/introducing-monad-ai-blueprint): AI projeleri için altyapı kredisi veren Monad Foundation programı.

## Track'lere göre fikir listesi

Kaynak sayfası her track için somut fikirler ve her fikir için okuma listesi veriyor. Aşağıda sadece başlıklar var; linkler ve açıklamalar `ek/resources-sayfasi.md` içinde aynı başlıklar altında.

Bu listeler sayfada öne çıkan bir şeyi tekrar ediyor: birçok fikrin yanında başarısız olmuş öncüllerin post-mortem'leri de var (friend.tech, Loot, Goldfinch, Async Art, Kaito vb.). Bir fikre başlamadan önce o bölümdeki "neden olmadı" kaynaklarını oku.

**Onchain Finance & Trading**
SLA Insurance & Performance Bonds · Compute Spot Exchange · Social & Copy-Trading Interfaces · Parametric Insurance with Instant Settlement · Compute Structured Products · Tokenized Compute Yield · Cashflow-Backed Credit · Execution-Aware Trading Interfaces · Embedded Trading in Non-Trading Apps · Next-gen Launchpads for New Asset Classes · New Order Types via Better UI · Yield Stripping · Prediction Markets for Unpriced Outcomes · Mobile-First Trading for a Specific Segment · Continuous Liquidity for Illiquid Assets · Options on Non-Traditional Underlyings

**Consumer Products & Payments**
Income Share Agreements as a Consumer Product · Programmable Gifts That Unlock on Conditions · Accountability Pools · Micro-Insurance by the Minute · Savings Yield Gated by Behavioral Goals · Commitment Contracts with Real Money Stakes · Payments Embedded in Social Gestures · Salary Streaming at the Individual Level

**Social, Attention & Culture**
Algorithm Marketplace · Community-Governed Recommendation Engines · Card Rental & Lending Markets · Generative Art That Evolves · Player-Governed TCGs · Cross-Game Asset Interoperability · TCG Marketplace with Onchain Order Books · Early-Supporter Registries · Wallet-Seeded Social Graphs · Style as an Ownable Asset · AMMs for Long-Tail Collectibles · Attention Futures

**Trust, Identity & AI Infrastructure**
Expertise Licensing Marketplace · Data Labelling Networks for Physical AI · Content Passports · Onchain Skill Credentials · Personal Data Locker · Cross-Application AI Memory · Mobile-Native Proof of Personhood

## Ekosistem protokol dokümanları

Kaynak sayfasında şu protokoller için konsept ve entegrasyon rehberleri var: Aave, Alchemy, Blend, Curvance, Envio, Euler, Morpho, Pendle, Perpl, QuickNode, Uniswap, Zerion. Linkler `ek/resources-sayfasi.md` içinde "Ecosystem protocol resources" başlığında.
