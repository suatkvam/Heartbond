# Oturum notları (İngilizce orijinal)

Türkçe dosyaların dayandığı notların orijinal hali. Konuşmacı alıntıları tırnak içinde; geri kalanı notu tutan kişinin yorumu. Başlıklar sonradan eklendi.

## Açılış (Port ve Harpal)

Port: "This is not a usual hackathon." The useful implication is that a Metropolis entry should be judged against its path to continued use, not its demo-day theater. Start with a real user, a problem worth returning to, and a product reason to use Monad; technical novelty without that loop is not the target.

Harpal: "Solidify the fundamentals first so that when you are prompting, your prompts are much better and the output is less error prone." This is not an argument for delaying a build until you are an expert. It is an argument that domain knowledge is the control surface for agents: it lets you set constraints, recognize a wrong abstraction, and correct the output before the error compounds.

Port: "Do not try to re-invent the wheel. Check what is available on Monad right now and try to combine them in a way that can solve a problem." Sponsor research is therefore architectural reconnaissance, not prize hunting. Do it before committing to an idea, because existing infrastructure can remove an entire subsystem and reveal the distinct product layer that is actually worth building.

Harpal: "To unlock asking mentors feature, you have to post some progress update." The platform makes status reporting an input to the mentoring loop: a small update, a blocked/on-track state, and a relevant link provide the history a mentor needs to give targeted help. Treat updates as debugging context and a deliberate route to sponsor expertise, not as administrative work.

Port: "Copy these for your agent... just glance at them as a human... do not stop being human." The resource page is unusually valuable because it packages ecosystem tools and constraints as agent-ready context. The human still owns the decision: load the context into the agent, but first understand enough of it to approve the architecture rather than merely accepting a plausible implementation.

## Envio (Denham)

Denham from Envio: "Think of it as the layer between your front end and your smart contracts." An indexer is justified when a product needs historical activity, aggregation, or a purpose-built query surface, rather than an isolated current-state lookup. It should be designed as product data modeling, not as a generic copy of chain history.

Denham: "Often you use events to emit or logs to emit events. And that's kind of the better, more cost-effective way of getting data from on-chain." Build contracts with the future product view in mind: emit the events a user-facing feature will need, then index only the relevant events. Falling back to state reads for everything makes historical views slower, harder, and less intentional.

Denham: "We've got three files we care about." The important split is config, schema, and handler. Config defines the data boundary through contract, network, start block, and selected events; schema defines the GraphQL surface; the handler turns an event into product-specific state. These are design choices, not generator output to leave unexplored.

Denham: "Agentic development now is really, really nicely coupled with test-driven development." Agents can create handlers quickly, but tests prove the handler still represents the chain behavior after a refactor or a model-generated change. This is especially important for an indexer, where an apparently harmless interpretation error becomes an incorrect product view for every user.

## Alchemy (Uttam)

Uttam from Alchemy: "Agents can autonomously go and sign up for our services." Alchemy CLI is meaningful because it gives an agent a terminal-operable control plane for account-linked chain infrastructure, querying, and operational tasks, reducing browser-based setup. That makes it useful for the build loop, but it also means authentication deserves the same caution as any production credential.

Uttam: "Use WebSockets, not HTTP, not just Node RPC." For a real-time Monad surface, choose sustained subscriptions rather than repeatedly polling snapshots. The transport is a product decision: a live wallet, event monitor, or market interface needs timely push updates; a static or occasional lookup does not need the same operational complexity.

Uttam: "Please make sure that you're using API key and storing it in .env... protect the API key, please." Agent-first development does not weaken secret hygiene. Keep keys out of committed code and casual prompt text, inject them through environment or stronger secret management, and regard a CLI-authenticated session as privileged operational access.

## Agent cüzdanları (Port)

Port, on agent wallets: "No one's going out there and pasting private keys around anymore." The architectural takeaway is that a long-running agent needs a signing boundary with scoped funding and authentication, not a raw private key sitting in code, shell history, or a server. An agent wallet is the safer primitive when automation must take on-chain actions.

## Zerion (Luan)

Luan from Zerion: "We are not an RPC provider. We are not here to give you raw on-chain data." Zerion belongs one layer above raw access: it parses transactions, attaches prices, labels spam, and interprets token and DeFi positions. Use it when the product needs wallet behavior that users can understand, rather than when you only need a raw chain read.

Luan: "Usually it's the parameters that people get wrong a lot." API filtering is product semantics, not request decoration. Decide explicitly whether a view is Monad-only, whether it includes simple assets or complex DeFi positions, and whether it hides trash. A transaction that appears missing may actually be excluded by an unexamined filter choice.

Luan: "At least 90% or 99% of what you see here on the web app is going to be coming from public API." Zerion's wallet is a working reference for the public API, so it can be used to inspect feasible UI patterns, data interpretation, and spam handling before inventing a portfolio feature from scratch. Its wallet webhooks are the deeper primitive: subscribe to selected addresses and receive parsed live activity without building a raw-RPC polling system.

## Metropolis formatı

The six-week Metropolis format is a product-validation window, not extra build time. Use it to put an early version in front of a real person, observe where they get stuck, and test whether they would choose the product again. A successful transaction alone does not prove a payments product works.

## Nansen

Nansen's value is not that it sees transfers; it attaches identity and behavioral context to them. The useful product question is not "what did this 0x address do?" but "was it a market maker, a fresh wallet, a whale, a public figure, or a related counterparty, and why should the user care?"

Wallet counterparty data can support relationship analysis, but the raw graph is noisy. James's visualizer became useful only after it could remove exchanges and smart contracts, distinguish direct transfers from shared protocol interactions, and expose the remaining human-relevant links.

Nansen's token flow data should be interpreted by tracked wallet segment, not reduced to "smart money." Inflows and outflows from fresh wallets, whales, public figures, and profitable traders can imply very different narratives, so a strong product exposes the segment rather than presenting an undifferentiated score.

API, CLI, and MCP are three access paths to the same Nansen data, not three separate features. Use an API for application requests, a CLI when the agent needs the full query surface in its workspace, and MCP when the user should be able to ask natural-language questions against live on-chain context.

The Nansen examples point away from another generic analytics dashboard. Wallet compatibility, an on-chain annual wrap, and visual transaction maps are useful because they turn difficult data into a social, explanatory, or shareable experience. The bounty requirement is that Nansen must be core to the product, not an optional data badge.

## Onboarding ve Dynamic

Onboarding is a value-to-friction ratio at the point of maximum abandonment risk. Every action a new user takes should either unlock immediate value or make them feel that they have made progress; a sequence of unexplained security and setup prompts is technically correct but product-destructive.

Design onboarding around the earliest "magic moment": the first action that proves the product's value. Remove or defer everything that does not get the user there. For a financial app, this might be a payment arriving instantly with no visible fee, not the moment the user finishes a form.

Dynamic's headless SDK is strategically important because onboarding should match the application, not the wallet provider's default UI. Builders control when a wallet is created, when a confirmation is shown, and how each step fits the product's own value exchange.

Dynamic CLI turns the dashboard into an agent-operable configuration surface. It can check and change settings programmatically after an authenticated approval, reducing the failure mode where the code is correct but a required dashboard toggle, chain setting, or wallet option was missed.

Agent wallets need a permission model, not just another wallet. Use an autonomous wallet for an independent agent, a server wallet for backend automation, and delegated access when a user permits an agent to act from their wallet. Delegation should be policy-bound, time-bound, and revocable.

The best answer to agent-wallet trust is often an adversarial layer rather than a blanket ban. Let a specialized execution agent propose an action, then pass the pending transaction to a review webhook or "personal CFO" agent that applies rules and can reject it before it lands. This mirrors the productive coding pattern of generation plus PR review.

For AI-era DevEx, documentation must be optimized for a proxy reader. Dynamic's MCP fetches current documentation at low context cost, while the CLI exposes configuration. Together they let an agent implement and diagnose a stack without relying on stale model knowledge or manual dashboard navigation.

## Fikir doğrulama ve AI ile geliştirme (Harpal, Port)

Harpal's build sequence begins before coding: use plan mode and an adversarial questioning skill to pressure-test the idea, create a durable checklist in the repository, and preserve that plan so a new session or agent can continue after context runs out. Building is cheap; deciding what deserves to be built is the scarce work.

Idea validation should start from recurring user complaints, not founder intuition. Search X, Reddit, niche communities, and Discord for the same unresolved question or frustration; then contact those people for interviews or beta access. The complaint is evidence of a reachable initial user group, not merely inspiration.

Use each model's native information advantage. Harpal suggested Reddit's Ask AI to locate relevant communities, while Port pointed to Grok for current X discussion and Gemini for YouTube. The tool choice should follow where the evidence lives, rather than assuming a coding model is the best research surface.

Give coding agents authoritative, task-specific context rather than hoping web search finds it. Monad's docs MCP routes the agent to current documentation, and the Metropolis resource page can be copied wholesale so the agent can discover sponsor tools, credits, skills, starter templates, and track-specific references.

Design quality can be made agent-operable without becoming generic. Supply a concrete design system as markdown or screenshots from products with the desired interaction language, ask the agent to extract a reusable design file, then use component-level design mode to correct a precise element instead of issuing vague global styling requests.

For consumer products, small sensory details can improve perceived completion and trust. The payment-success sound example matters because it reinforces an important state transition; use sound selectively for consequential interactions, not as decoration across the whole interface.

## Aurora Intents

Aurora Intents reframes a cross-chain request from a sequence of bridges and confirmations into a declared outcome. The user says what asset should end up where; the intent infrastructure handles routing and execution details that otherwise create error-prone wallet and chain switching.

Choose Aurora's product by the terminal outcome. Intents Deposits is for funding an app account, Swap API is for a cross-chain asset conversion that remains part of your own UX, and Intents Connect is for a funded destination that must immediately execute a contract action such as entering a lending position or depositing into a vault.

Intents Connect is valuable because it joins cross-chain movement with destination-chain composability in one operation. A user can bring an asset from an EVM or non-EVM source and end in a Monad protocol position, allowing a Monad product to reach users and assets that would otherwise be outside its native ecosystem.

Persistent deposit addresses are a product primitive, not just an API detail. They let an app assign a stable place to fund a chosen destination account, which simplifies repeat top-ups and makes cross-chain funding feel more like a normal account operation.

For an Aurora bounty, a cross-chain call alone is insufficient. The review criteria include real settlement and refund handling, clear UX, technical quality, source-chain support, contract compatibility for Intents Connect, and artifacts that make the project easy to verify: a public repository, technical demo, pitch video, and live link where possible.

## Kuru

Kuru is infrastructure, not the finished trading product. It supplies fully on-chain order books, liquidity, market data, trigger orders, relay-backed transaction delivery, and fee mechanics; the Metropolis builder should own the user insight, distribution, and interface that gives someone a reason to use a new trading experience.

The clearest Kuru differentiation is a product built for an underserved audience rather than the same global crypto user. A region-specific compliant front end, local on-ramping, structured financial packaging, or an agentic assistant can access users that a generic terminal cannot reach, while making marketing and distribution less interchangeable with every other trading app.

Treat Kuru's historical data API and exchange streams as different layers of a trading interface. Historical data initializes the product with orders, trades, balances, and market context; low-latency streams support live books, mids, user balances, and trading automation. A front end that confuses them will either be slow or unnecessarily expensive.

For active trading, users trust the interface only when it behaves continuously. Live charts need low-latency reliable data, executions need clear confirmation, and mobile performance matters because excess state and payload size create jitter. An interface that looks uncertain about whether an order landed makes users feel unsafe even when the contracts are correct.

Kuru's relay is a product primitive, not merely an API detail. It sponsors gas and retries execution so an app can avoid asking a new user to fund an EOA with MON before taking a trading action. The most valuable use is to make a constrained, intentional flow feel synchronous and dependable.

Kuru subaccounts and delegated signer permissions enable a better portfolio-management architecture than sharing a private key. A user can authorize a manager or strategy to trade while separately restricting withdrawal capability, amount, or scope; the product becomes a controllable financial mandate rather than blind custody.

The portfolio-manager demo combined a passkey-based Mera wallet with an EIP-7702-compatible delegated contract and relayer. That pattern separates the valuable owner account from a disposable trading credential, applies daily limits in contract logic, and permits gas-sponsored execution without placing broad withdrawal authority on a local device.

Kuru's new-markets bounty is not mainly about listing another token. The deeper opportunity is a wrapper that creates a useful new spot market or outcome market, explains why that market has an audience, and has a credible path to liquidity. Prediction markets are one example because binary or multi-outcome shares can be represented on top of spot order-book infrastructure.

The first traders for a new market should come from the founder's specific insight, not broad promotion. Start with people already trading the relevant asset, sport, region, or strategy; interview them about what they cannot trade today; then test whether they will use the product before treating liquidity as a generic acquisition problem.

## QuickNode

QuickNode's monitoring rule is simple: instrument the chain event whose absence would make users angry immediately. A wallet needs incoming and outgoing transaction activity, a DEX needs decoded swaps and confirmations, and an analytics dashboard can tolerate a delay if it is not serving a real-time trading decision.

Webhooks are the lowest-complexity push mechanism when a product needs current events from a contract or wallet. Configure the watched address and event hash, point the delivery at an endpoint, and make the application verify the received security metadata. This replaces a custom client-side subscription loop for many MVP notification and activity-feed needs.

Streams is the right escalation when a product needs an ETL pipeline rather than a notification. It can backfill from a chosen block, continue with live blocks, filter and transform raw receipts in JavaScript or Go, batch messages, and deliver the shaped data directly to a database, data lake, or endpoint.

Streams also exposes operational choices that should be intentional: a latest-block delay trades speed for confidence, retry and timeout behavior protect against destination outages, and a bounded range prevents accidentally indexing an entire chain. These controls define the product's data contract, not just its infrastructure bill.

## MetaMask Agent Wallet

MetaMask Agent Wallet plugins turn a general agent wallet into a capability platform. A plugin can add deterministic trading rules, ENS resolution, a new perpetuals venue, or copy-trading logic, then be published as an npm package for other agents to install rather than rebuilt in every project.

The plugin security model has a hard boundary: plugins can read wallet state, use the public client, obtain market data, and submit transaction requests, but cannot modify or bypass agent-wallet policies. Execution still runs through MetaMask's policy engine and MFA path, so a useful plugin extends functionality without owning the user's risk controls.

Permissions are declared in the plugin manifest and presented during installation. This creates a reviewable contract between the plugin and the user: a read-only plugin should not silently gain transaction ability in a later version, and a user can reject an installation that asks for capabilities beyond the intended use.

Build an agent-wallet plugin from a real trading or execution primitive, not a vague instruction. First understand the venue, strategy, data source, or contract flow yourself; then use the plugin skill and planning mode to express precise inputs, error paths, permissions, and policy assumptions to the agent.

The agent workflow described in the stream is deliberately staged: research with diagrams, define the intended product, iterate on a PRD, implement in a fresh context, test in another fresh context, then perform human QA. Context hygiene is not cosmetic; separating research, product decisions, implementation, and testing keeps the agent from losing the architectural thread.

## Launchpad'ler

Launchpads are powerful because they can create a community of communities. A normal app grows one user community; a launchpad enables many creators to form distinct token communities under the platform's umbrella, turning distribution into the product's central compounding mechanism.

A new launchpad needs to enable a new kind of community, not merely move the same meme-coin mechanic to Monad. PumpFun makes simple viral coin communities; Pawns changes the community thesis by pairing coins with stocks and redirecting a portion of fees. The useful question is what community could exist only because of this launch process and revenue design.

Fee allocation is a core design lever. The incumbent's margin is potential product surface: instead of routing all fees to a platform buyback, a launchpad can direct them toward an asset, a participant group, a public good, or another programmatic destination that gives its communities a distinct reason to form and persist.

Trust in a launchpad is partly mechanical and partly narrative. Clear, identifiable launch traits can give users origin confidence, while a founder who publicly explains where fees go and why the platform is designed that way gives users a coherent reason to believe the product will act consistently.

The right first step for a launchpad is observation, not code generation. Use competing launchpads, inspect the user discourse and recurring complaints, decide which new community or incentive model solves a real gap, and only then build. A generic launchpad with no thesis is unlikely to overcome existing network effects.

## Chainlink CRE

Chainlink CRE changes the unit of design from a contract to a workflow. Start with the event that should trigger work, the off-chain information or service required, and the on-chain callback that completes the user promise. The Solidity contract is one verified action in that path, rather than the place where the entire application must live.

The weather demo exposed a useful boundary: an EVM log triggered the workflow, CRE called an external weather API, then a protected callback wrote the result on-chain. This model lets a builder connect external systems without putting API calls, credentials, or an unverifiable single server inside a smart contract.

CRE's important property is not merely that it can make HTTP requests. A decentralized oracle network reaches consensus over the external call and the workflow's off-chain computation before producing the chain write. That makes the integration layer a trust component with its own verification model, rather than a backend the product asks users to trust blindly.

Use simulation as a product-development stage, not a lesser version of the workflow. It can prove the trigger, external request, and expected result without paying for an on-chain write; once the behavior is right, broadcast performs the real callback and makes the state visible to the application. For a hackathon, a simulation recording can be a credible demonstration while the deployment path remains unfinished.

The forward-contract pattern separates a safe local simulation from production authority. The workflow can emit to a local forward in development, while deployment supplies the actual address and restricts the state-setting callback to the workflow output. That keeps the demo convenient without accidentally leaving the write path open.

CRE is more valuable when the product's central promise crosses a system boundary. External data, scheduled operations, on-chain event response, and cross-system actions belong in one workflow when the user needs a result that neither the blockchain nor a conventional backend can establish alone.

## Go-to-market (Daniela)

Daniela's GTM framework begins with an uncomfortable question: why would the ideal customer not use the product? The answer often reveals the real adoption obstacle, which should be neutralized in the headline and product promise rather than hidden behind a feature list.

Positioning should acknowledge the strongest competitor instead of pretending it is weak. Identify why it wins, find the specific thing it fails to deliver for a defined user, and make that gap the basis for differentiation. A claim such as "regulated" only works if the intended users actually value regulation enough to change behavior.

Partner discovery is a distribution design exercise. Specify what a partner contributes, the numerical pipeline or audience outcome expected, and the route into that relationship. A generic ecosystem partnership is not a go-to-market plan; a workshop or campaign that reaches a known group of builders can be.

Business-development discovery should end with a warm-intro map, not a list of logos. Name the person, where they can be reached, what value can be offered before asking for anything, and what they can unlock. Combining that with ICP, competitor, and partner work creates a launch narrative grounded in actual routes to users.

## Product-market fit ve retention (Pareen)

Product-market fit should be measured against the cost of the behavior being requested. If signing, payment, or a wallet connection is the hard step, the value proposition must justify it. The fast test is not a canvas: would a skeptical builder use the product themselves, and would an unprimed person say yes after seeing it without being told to be supportive?

Pareen's definition of an active user is a completed core loop with an action and a reward, not a visit, registration, or wallet connection. For a DEX, buying an asset and receiving it is a meaningful loop; for a content product, a certain amount of consumption may be the threshold. The right activity interval follows the user's existing habit, whether daily, weekly, monthly, or less frequent.

Retention targets must match the behavior being served. A DCA product can reasonably pursue a monthly user because salary and investment behavior are monthly; a product aimed at daily traders has to win a daily habit against the place they already trade. Calling every product a DAU product hides that difference and creates false failure signals.

The first customer research should be unusually narrow and high quality. For a launchpad, speak to people who have actually launched meaningful tokens, ask what made their current platform insufficient, cross-check the answer with others, then build the one missing mechanic. Broad category cloning skips the evidence that could make a new product worth switching to.

A solo builder without a network can create a reason for experts to respond by doing the research first. Study the category deeply enough to publish an analysis with a few non-obvious insights, then send that work with a precise request for a short conversation. "I am building a launchpad" is easy to ignore; evidence of serious understanding and a specific question is not.

The first 500 repeat users are an operating problem, not a launch-video problem. Pareen's prescription is hands-on onboarding, a small user group, direct replies, and immediate iteration. The product earns referral only after early users have seen feedback turn into visible changes quickly enough to trust the founder's attention.

Early retention improves when the product is reduced to the smallest repeatable action-reward loop. A feature-dense platform gives a founder more things to explain and users more ways to get lost. A small loop makes it possible to identify the trigger, action, reward, and changed state that should bring someone back.

Once a product has early users, the cadence should reverse the default builder habit: spend most of the week speaking with users and iterating, reserve a constrained block for implementation, then return to users. More than 10 to 20 percent of time spent coding can be a warning that features are accumulating ahead of evidence.

## MIP-8

MIP-8 attacks a physical storage bottleneck rather than a Solidity syntax problem. Disk reads are far slower than computation, and Monad's fast execution makes that imbalance matter more. By fetching a 128-slot page for roughly the cost of fetching one slot, MIP-8 makes adjacent state materially cheaper to access.

The practical storage rule shifts from "minimize every slot" to "optimize the hot path." Contracts benefit automatically when related standard slots already land together, but a contract with several mappings keyed by the same user can improve locality by storing those fields in one struct in one mapping. That is a simpler and often safer design than clever bit-level packing.

MIP-8 does not make all state free. Writing a newly created slot still has a cost, and per-user or per-trade state should be judged differently from a globally accessed field. The important opportunity is to spend an extra nearby slot when it makes the recurring user path better, because the normal penalty for adjacent access has dropped sharply.

The migration itself is a protocol-engineering lesson. Validators maintained both the existing and paged storage representations, caught the new representation up, and switched charging only after it was operating correctly. A storage-layout change that affects every validator was introduced without asking applications to migrate or rewrite their contracts.

Developers do not need new opcodes, compilers, or special Solidity to receive MIP-8 benefits. For measurements, however, enable Monad gas pricing in Foundry so local tests reflect the network's economics. Consider hand-managed page layout or assembly only for a genuinely performance-critical design, such as a central limit order book, where the added complexity is justified.

The product implication of cheaper adjacent storage is not "add state everywhere." It is to reconsider designs that were previously too costly: richer AMM market history and dynamic fee logic, more viable order-book contracts, and on-chain games with deeper state. The deciding question remains the same as the retention session: which specific user becomes happier because this state exists?

## Cleanverse

Cleanverse's core claim is architectural: verified identity and compliant assets are two halves of one transfer decision. A wallet-bound credential supplies attributes such as tier, group, country, validity, and status; the asset transfer enforces the applicable rule before settlement. Identity without a transfer gate leaves money movable, while an asset rule without identity cannot determine who is participating.

The compliance check belongs on the path where value moves. A CVA token can run it inside its transfer hook, while a business contract should call `complianceVerify` for the relevant parties before changing balances or state in a deposit, swap, withdrawal, or settlement. A frontend check and onboarding approval are useful UX, but neither is enforcement.

Onboarding-only verification is structurally insufficient because counterparties and credentials change after signup. A receiving wallet may never have been verified, an existing credential may expire or become inactive, and a user's tier or country eligibility may change. Rechecking at transfer time makes the current rule, rather than a historical signup event, authoritative.

A rejected compliant transfer should be a legible product state, not a generic failure. Surface the reason that maps to the on-chain rejection, such as no credential, expiry, inactive status, insufficient tier, or disallowed country, then direct the affected user to the right onboarding or remediation step. Hiding the reason turns compliance into unexplained friction.

The useful test for a Cleanverse bounty project is deletion. If removing the identity logic still allows the asset to move, compliance was bolted on as an optional layer. A strong design has no alternate code path around the contract-level rule and pairs that invariant with a real regulated flow such as travel-rule payments, permissioned DeFi, or RWA settlement.

Start a Cleanverse MVP with the smallest complete failure-and-success pair. Store the validator address, register the contract through the API, set a minimal Rule V2 such as a minimum tier, and create one gated action. Test two wallets: one that meets the rule and one that does not. That demonstrates both the product promise and the contract invariant before expanding to factories, issued assets, or wrappers.

## Agora

Agora's stablecoin opportunity is not merely using AUSD as another balance. A 1:1 USD rail on Monad can support products that price, hold, settle, and quote in dollars while benefiting from low fees. Payments, high-frequency transfers, and trading pairs become product design surfaces when the base asset has predictable value and inexpensive movement.

For an Agora product, on-ramping is the first user journey, not a follow-up integration. A user may arrive with fiat, USDC, another stablecoin, or no wallet knowledge at all. The product has not solved payments simply because a contract works; it must make obtaining, funding, and trusting the balance feel understandable to someone coming from Web2.

The instant settlement contract is the primary AUSD conversion primitive for the hackathon. Builders should understand its approvals and the in-and-out flow before designing a payment or trading interface. On testnet, the paired token is CTK rather than USDC, so a polished demo may need to conceal that test-only detail without obscuring what the user is actually doing.

Instant settlement also creates an operational edge case: liquidity can be unavailable. Agora's route API is a meaningful fallback rather than an afterthought, providing an address or vault route that can accept USDC or potentially fiat and return minted AUSD with an operational delay. The UI should distinguish instant completion from this slower route instead of letting users infer that a delayed transaction disappeared.

Pending, reverted, and reversed actions are trust-critical states. Show that a transaction is processing, make the on-chain activity inspectable, explain what failed in concise language, and explicitly reassure users when funds are safe and returning. A product that only has a happy-path screen leaves users to interpret financial ambiguity as loss.

The Agora session also described a practical agent workflow: begin with a product requirement document that establishes why the product exists and how success or failure will be judged; follow with a technical design that chooses the concrete integrations; then implement. Use agents to research competing APIs and challenge assumptions, but keep a coherent workspace and human-owned decisions across the work.

For on-chain products, define failure conditions and security success criteria before implementation. That makes it possible to build a test suite that evaluates the right behavior and to review generated smart-contract code against explicit expectations. Reading the contract remains necessary when real funds or production behavior are at stake.

## Tenderly

Tenderly's simulator is useful because it turns an opaque revert into an inspectable execution. A builder can impersonate an address, apply state overrides, invoke a real contract function, and see the resulting trace. The debugger then connects a failed transaction to the exact source line, storage value, and require condition that produced it.

State overrides change the debugging question from "why is this impossible?" to "what condition would make this succeed?" In the wrapped-MON example, the builder could see that the requested withdrawal exceeded the balance, test the corrected amount, or override the balance to explore a different scenario. That isolates the real condition before any testnet iteration.

Editing source code in the simulation can accelerate hypothesis testing, but it is a diagnostic tool rather than a reason to weaken production checks. Temporarily removing a require statement demonstrates that the check caused the revert; it does not establish that the check should be removed. The next step is to decide whether the precondition, user flow, or contract logic is wrong.

Virtual environments extend one-off simulation into a persistent forked Monad sandbox. Builders can choose a block, use a faucet, make lasting state changes, mine or revert blocks, move time, and interact through a virtual RPC. This makes it possible to rehearse multi-step flows and reproduce chain context without touching the live network.

Tenderly alerts connect observability to action. A contract event or monitored state can send a notification to a chosen destination, or trigger serverless code through Vectory. That creates a direct path from detected deposits, balance thresholds, or incidents to a response workflow instead of relying on someone to notice a dashboard manually.

## Cleanverse + Agora + Tenderly birlikte

The Day 5 sessions fit together as an application reliability stack. Cleanverse defines who may move an asset and where that rule is enforced; Agora makes the money movement usable and explainable to a mainstream user; Tenderly gives the team a way to test, inspect, and automate the paths that must remain correct.
