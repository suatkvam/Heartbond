# Product Requirements Document

Last updated: 2026-10-13 — latest decision: D-13

Decisions are logged in `docs/DECISIONS.md` and cited here as `(D-xx)`. Points marked **(Decision)** without an identifier predate that log (see §27). Exact rule IDs for the build live in `docs/SPEC.md`.

## 1. Product Overview

**Product name:** GPU SLA Escrow (working title)

**One-line description:** An on-chain escrow contract that pays a GPU provider or refunds a renter based on uptime data (uptime only — no performance metric in the MVP, §9.4) attested by a small set of team-controlled reporter keys (one trust root, D-02), with settlement permissionlessly triggerable (not gated by a platform) and finalized on a fixed timeout rather than human arbitration.

**Problem:** among the GPU rental marketplaces researched (§2, §4), SLA compliance, where it exists at all, is determined only by each platform's own private, non-portable process — no independently auditable, portable on-chain settlement record was found. This is a statement about what the research covered, not a claim that no such mechanism exists on any platform anywhere (several platforms were not researched deeply enough to rule it out, §4).

**Target user:** ML researchers / indie developers who rent GPUs on marketplaces (vast.ai, RunPod-class), and third-party GPU node operators who list hardware on such marketplaces.

**Proposed solution:** An on-chain escrow that holds rental payment, accepts uptime reports only from a fixed set of team-held reporter addresses (D-02), and lets anyone trigger a deterministic settlement computation once the rental period ends — followed by a fixed challenge window in which either party can log an on-chain objection, after which the computed outcome finalizes regardless of that objection and the payee withdraws the funds (D-01).

**Scope change from the original idea (Decision):** `gpu-rental-market.md` describes a "Permissionless Onchain GPU Rental Market"; this PRD deliberately narrows that to an SLA escrow/settlement primitive — no listing, matching, or price transparency — because price fragmentation (§2 Problem B) is a separate problem this product does not solve.

**Hackathon context:** Monad Metropolis, a six-week hackathon judged on whether a project has a real user, a recurring problem and a product reason to be on Monad (source: `docs/source/metropolis-notlari/01-metropolis-nedir.md`). Main track: **Trust, Identity & AI Infrastructure** (D-09). Team of two: the owner builds contract, oracle, tests, deploy and docs; a teammate builds the UI (CLAUDE.md). Author has no physical GPU hardware. The MVP is scoped so the on-chain escrow/settlement logic is real (deployed and executed on Monad Testnet). The GPU workload is mocked; uptime comes from a real HTTP health probe of a Docker container the team runs as a stand-in for a GPU node (D-04), reported by team-held keys (see §8, §10, §20 step 10).

### Precise claims — what "permissionless," "automated," and "no human intervention" actually mean here

These terms appear in the original idea and are easy to overclaim. This PRD fixes their meaning for this product:

- **"Permissionless" applies to *triggering* settlement, not to *verifying* SLA data.** Anyone — not just the platform, renter, or provider — can call `settle()`, which computes and freezes the payout once conditions are met, and, separately, `finalize()`, which credits that already-frozen payout to the payee after the fixed challenge window (§9.1, §11); the payee then withdraws it (D-01). These are two distinct, separately-callable steps, not one combined action. Nobody needs anyone's permission to make either transaction happen. This is the only sense in which the MVP is permissionless.
- **The oracle is emphatically not permissionless or trustless.** A fixed set of one to eight addresses, all controlled by the team, is the sole source of uptime data for MVP (§10, D-02). Anything any of those addresses reports is treated as true by the contract. Several keys remove the single-nonce bottleneck; they do not add a second trust root. This is functionally a centralized trust root, publicly recorded rather than privately held — see §13 for what value that narrower claim (auditable record vs. independent verification) actually provides.
- **"Automated" means the payout computation involves no human discretion once triggered** — the outcome is a deterministic function of on-chain data (§9). It does **not** mean no human (or bot) ever needs to send a transaction — someone still has to call `settle()`/`finalize()`, and the payee has to call `withdraw()` (D-01), exactly as with any smart contract. There is no background process that fires itself.
- **"No human intervention" describes the absence of a human judge deciding who's right.** It does not describe the absence of a human sending transactions, and it does not describe a dispute-resolution process — see §11, which replaces the term "dispute resolution" with a more accurate name for what the timeout mechanism actually does.

---

## 2. Problem Definition

This PRD treats two things that were previously bundled together as **separate problems with separate evidence** — conflating them was the single largest logical gap in the earlier draft.

### Problem A (primary — what this product addresses): no independently auditable SLA enforcement

**Four distinct layers, kept separate throughout this PRD (their conflation was a recurring source of overclaiming in earlier drafts):**

1. **Verification** — confirming what actually happened on the GPU (ground truth). This product does **not** do this trustlessly; it relies on one trusted oracle (§10).
2. **Recording** — writing a claim about what happened on-chain. This product does this: the oracle's reports are stored on-chain, tied to a rental ID, immutable once written (§9).
3. **Settlement** — deterministically computing a payout from the recorded claims and executing it. This product does this (§9, §12).
4. **Auditability** — the ability for any party, after the fact, to inspect the recorded claims and the settlement computation and confirm the payout followed the rule. This product provides this for layers 2 and 3, not for layer 1.

Every claim in this PRD about "auditable," "verified," or "SLA enforcement" refers to layers 2–4 unless explicitly stated otherwise. No claim in this PRD should be read as asserting trustless verification of layer 1.

**Verified:** vast.ai's own documentation describes its host-quality system as "fully automated and powered by proprietary algorithms" (uptime, DLPerf benchmark score, hardware-config checks). This is the most detailed documented verification system found in this research pass, and it is private and non-portable: neither renter nor provider nor any third party can independently audit the scoring logic or its historical inputs. Source: docs.vast.ai/host/understanding-verification.md.

**Research 2026-10-13 (sourced, not independently re-verified) — where published SLA terms exist, the platform itself is the judge:**
- RunPod's Terms of Service state it "does not make any specific uptime warranties with respect to the Community Cloud Offerings" and is "not a party to any interaction between compute consumer and any Host"; credits are non-refundable. A 99.99% uptime SLA is mentioned only for enterprise agreements (runpod.io/legal/terms-of-service, docs.runpod.io/accounts-billing/billing).
- Vast.ai's billing docs: "After spending credits, there are absolutely no refunds" (docs.vast.ai/guides/reference/billing). Vast.ai replied to 2025 reviews that it issues credits "in line with a new policy" whose text was not found.
- Lambda "reserves the right to award credits at its sole discretion" (lambda.ai/legal/terms-of-service).
- CoreWeave's Terms of Service (dated 2022-06-30) **do** publish uptime targets and tiered credits, but the customer must submit logs within 10 days and "CoreWeave will make a determination in good faith based on its system logs" (docs.coreweave.com/policies/terms-of-service). This corrects the earlier draft, which said CoreWeave publishes no SLA. A newer CoreWeave service-levels page exists (docs.coreweave.com/observability/service-levels-and-limits) and was not read; check it before quoting CoreWeave in the pitch.
- TensorDock publishes rule-based downtime compensation (5×–10× the hourly rate per hour down, measured by a quorum of at least four monitoring servers) and debits the host (docs.tensordock.com/legal-information/downtime-compensation, updated 2024-06-27). Compute Exchange's standard terms set a 99.5% uptime SLA with 10/25/50% service credits as "Sole Remedy" (compute.exchange/compute-service-terms). SF Compute refunds downtime pro rata, "as measured by the Company" (sfcompute.com/legal/sla).

So rule-based downtime remedies already exist (TensorDock, Compute Exchange, SF Compute, CoreWeave). What none of these documents is a record or settlement that a party outside the platform can audit or trigger: the platform measures, judges and pays.

**Not verified (research gap, not confirmed absence):** Nosana's failure/timeout handling and Golem's deposit scheme were not read in full. io.net, Akash, Spheron and Fluence were researched on 2026-10-13 (§4).

### Problem B (context only — this product does NOT solve this): GPU rental price fragmentation

**Verified (2026-09-26), refreshed by research 2026-10-13:** Same-class GPU (H100) on-demand pricing spans from about $1.71 to $11.07 per GPU-hour across 57 providers (median $3.49), e.g. Vast.ai from $1.73, RunPod from $2.59, Lambda from $3.29, CoreWeave from $6.16 (getdeploying.com/gpus/nvidia-h100, updated 2026-10-12). Silicon Data's indices show roughly a 2.5× gap between neocloud (~$2.85) and hyperscaler (~$7.16) H100 rates (silicondata.com, reading date not shown). Comparison aggregators (cloud-gpus.com, getdeploying.com) and CME compute futures settled against Silicon Data indices (trading planned from 2026-10-05, CME SER#9785) show the fragmentation is a recognized problem.

**Why this is listed but out of scope:** price fragmentation and SLA-trust are two different problems. This product does not standardize or compare prices — it only affects settlement of an already-agreed rental. Price data is included here solely as supporting context for one hypothesis in §17 (that some of the observed price premium reflects a willingness to pay for trust), not as a problem this product claims to fix. Treating "prices vary" as a justification for "therefore we need an SLA escrow" would be an unproven causal leap — this PRD does not make that leap.

### Interpretation, explicitly separated from the facts above

**Hypothesis, not evidence:** that some fraction of the price premium paid for Secure Cloud / CoreWeave / Lambda over budget marketplaces reflects willingness to pay to avoid SLA/trust risk specifically (as opposed to better raw infrastructure, enterprise support, or compliance needs, which are equally plausible explanations for the same price gap). No evidence gathered in this research distinguishes between these explanations.

**Public complaints, not validated user research (research 2026-10-13):** dated Trustpilot reviews from 2025–2026 describe the target user's situation directly. Renters report instances taken offline or GPUs removed while still being charged, and refunds handled case by case through support (Vast.ai, 2025-11-29 to 2026-06-16, trustpilot.com/review/vast.ai pages 2 and 4; RunPod, 2026-09-23 and 2026-10-01, trustpilot.com/review/runpod.io). Hosts report the mirror image: a verification process called "opaque and arbitrary" and a reliability score that drops when a machine is restarted for security patches (Vast.ai, 2026-01-15). Reddit threads with similar titles exist but could not be read (dates unverified). Reviews are self-selected; they show the pain exists, not how common it is or whether these users would accept a single-trust-root escrow (§22, §24).

**Assumption, two sources that disagree:** GPU-as-a-Service market estimated at $8.21B (2025) → $26.62B (2030) by MarketsandMarkets (press release 2025-03-27) and at $4.37B (2025) → $14.4B (2033) by Grand View Research (press release 2026-06-11). The two disagree by about 2× on the 2025 base; the earlier single-source figure (Precedence Research, $4.96B → $37.10B by 2035) is a third, different estimate. Directional context only, not a claim this product will capture any of that market.

---

## 3. Target Users

**Primary user — Renter:** ML researchers, indie developers, small AI teams renting GPUs by the hour for training/inference. On the platforms researched (§2, §4), their recourse if a rented GPU underperforms or goes down is limited to that platform's own internal support/verification process — this PRD does not claim this holds for every GPU marketplace, only for the ones documented in §4.

**Secondary user — Provider:** GPU node operators who list idle hardware on marketplaces today. They want to be paid according to a rule anyone can check, rather than depending on one platform's internal, non-portable scoring to vouch for them.

**User context:** On the platforms researched (§4), both sides transact through a centralized marketplace that privately determines whether an SLA was met, with no independently auditable, portable record of that determination. This PRD does not claim every GPU marketplace works this way — only that no researched platform was confirmed to offer such a record.

**Jobs-to-be-done:**
- Renter: "When I rent a GPU, I want the payout to follow a rule I can verify, without depending on the platform's internal judgment call."
- Provider: "I want to be paid according to an auditable rule, not a private score I can't inspect."

**Evidence of the pain (public reviews, not interviews):** see §2 — renters charged for unreachable instances with case-by-case refunds, and hosts calling the platform's verification "opaque and arbitrary". Whether these users would switch is unvalidated (§24, D-08).

**Note:** the author has no GPU hardware to supply, so the MVP demo represents the provider side with a Docker container the team runs and probes (D-04), not a real onboarded operator (§8, §17 cold-start risk).

---

## 4. Existing Solutions

### Centralized GPU marketplaces and compute markets
- **vast.ai** — Peer marketplace; automated proprietary host-verification system (uptime %, DLPerf benchmark, hardware-config checks) scores host reliability. Limitation: verification algorithm is private and non-portable; not third-party auditable. Its verification docs say only that reliability "starts low on a new machine and grows the longer the machine stays online" and describe no formal appeal (docs.vast.ai/host/verification-stages; research 2026-10-13).
- **RunPod** — Per-second billing; Community vs Secure Cloud tiers (Secure priced about 30–45% higher). Terms disclaim uptime warranties for Community Cloud; a 99.99% SLA is mentioned for enterprise agreements only; credits are non-refundable (§2).
- **Lambda** — Credits "at its sole discretion"; no published on-demand uptime SLA found (§2).
- **CoreWeave** — Publishes uptime targets and tiered credits; the customer must provide logs and CoreWeave determines the outcome from its own system logs (§2). The provider judges its own SLA.
- **TensorDock** — The closest rule-based analogue among centralized platforms: downtime is counted when a quorum of at least four monitoring servers in different regions agree a host is offline; renters receive 5×–10× the hourly rate per hour down, debited from the host; disputes go to arbitration (docs.tensordock.com, downtime-compensation and supplier-hosting-agreement pages, 2024). The rule is published and multi-monitor, but TensorDock runs the monitors, keeps the record and executes the settlement.
- **Compute Exchange / SF Compute** — Standardized compute contracts. Compute Exchange: 99.5% uptime SLA, 10/25/50% service credits as "Sole Remedy" (compute.exchange/compute-service-terms). SF Compute: pro-rata hourly refunds for downtime "as measured by the Company" (sfcompute.com/legal/sla). CME compute futures (Silicon Data H100/B200 indices) settle in cash and carry no delivery or SLA terms (CME SER#9785, 2026-08-11).

### Decentralized / DePIN GPU networks (researched 2026-10-13; sourced, not independently re-verified)
- **Akash Network** — On-chain per-lease streaming escrow, paid per block. "uptime-guarantee" appears only as an example provider attribute; nothing ties payment to uptime, and no slashing, refund or dispute mechanism is documented. Outage advice: close the lease and redeploy (akash.network/docs/learn/core-concepts/providers-leases/).
- **io.net** — Per-device token stake in a smart contract, slashed for "inadequate service" or spoofing; appeals via support ticket. No uptime threshold or customer refund documented (io.net/docs/guides/staking/io-staking).
- **Spheron** — Providers must meet tier uptime levels; falling short slashes that era's liveness rewards on-chain. Penalizes provider rewards; not a per-lease refund to the renter (docs.spheron.network/providers/reward-details).
- **Fluence** — Proof-of-capacity submitted on-chain each 24-hour epoch; collateral slashed for missing proofs. Proves capacity, not per-rental uptime for a tenant (fluence.dev/docs/stake/overview).
- **Nosana** — Solana jobs program with a market vault and job timeout/expiration parameters; what happens on failure is not documented in the pages reached — **not researched in full.**
- **Golem** — Pay-as-you-go via provider debit notes accepted by the requestor; no escrow, SLA or dispute mechanism found; a deposit scheme exists but was not read — **not researched in full.**
- **Gensyn** — Verde, a refereed-delegation protocol for disputes about the *correctness* of ML training, not uptime (gensyn.ai/research, 2025-02-24).
- **Aethir** — Closest documented analog, and it **overlaps substantially** with this product's settlement idea.
  - **Verified (verification layer):** Checker nodes check "Liveness, Capacity, and Quality of Service" via "Heartbeat collection, Benchmark testing, Link data collection and analysis"; liveness "once every minute" (docs.aethir.com/checker-guide/what-is-the-checker-node/how-do-checker-nodes-work.md). Checkers are "Initially deployed by the Aethir, with plans for gradual decentralization" (docs.aethir.com/aethir-network/the-checker). Docs conflict on capacity-check frequency ("once a day" vs "every 15 minutes", proof-of-capacity-and-delivery page) — unresolved.
  - **Verified (settlement layer):** during disruptions "the full amount for the affected period is not settled" (OnDemand) (docs.aethir.com/aethir-cloud/aethir-cloud-host/rewards-and-service-fees-for-cloud-hosts/service-fees-for-cloud-host). Hosts face uptime-tiered penalties (10% service-fee penalty at 95–99% monthly uptime, up to full fee + staking fee and order termination below 70%); "Slashed amount will be transferred to a 'compensation' pool, which is used to compensate Aethir Tenants, for interrupted cloud services based on SLAs" (…/operational-requirements-for-cloud-hosts/slashing-mechanism.md). Research 2026-10-13: the host — not the tenant — has 3 days to appeal a penalty.
  - **Unverified (recording / auditability / triggering):** the 2024 whitepaper draft calls blockchain the "settlement layer" for orders, deliveries and fees but names no chain, contract or event, and does not say where Checker results are stored (resources.cryptocompare.com whitepaper PDF, research 2026-10-13). No reached doc states that check results or per-order settlement are recorded on-chain, auditable per rental by the tenant, disputable by the tenant, or triggerable by anyone other than Aethir's platform.
  - **Verdict: partial overlap** — Aethir already does SLA-conditional payment (verification + settlement) inside its own platform; the public per-rental record, permissionless trigger, and challenge window were not found in its public docs.

### Closest analogues outside GPU rental (research 2026-10-13)
- **Chainlink Staking v0.2 feed-downtime alert** — Deployed on Ethereum since late 2023: if the ETH/USD feed has no valid report for more than 3 hours, a staker can raise an alert and the feed's node operators are slashed (chain.link/economics/staking; chain.link/blog/chainlink-staking-v0-2-overview). This is permissionlessly triggered, on-chain liveness enforcement — it works because the liveness fact (no on-chain report) is checkable on-chain. It covers oracle feeds, not compute.
- **Academic witness models** — Blockchain-based cloud-SLA enforcement where paid "witnesses" or monitors report violations (e.g. TU Delft / UvA witness model; Dienbauer et al., arXiv 2609.10704, 2026). Same trust assumption as this MVP's reporters: someone off-chain observes and reports.

**Gap assessment (deliberately unresolved):** SLA-conditional payment itself is **not** a gap — Aethir, TensorDock, Compute Exchange and CoreWeave all document downtime remedies, and Spheron/Fluence slash providers on-chain. What was not found in any researched platform's public docs is the narrower combination: a **per-rental** uptime record on a public chain, settled to the renter or provider by a rule anyone can trigger. Nosana and Golem were not researched in full, and Aethir's on-chain footprint remains unverified. This PRD calls this a **plausible, unconfirmed gap**, not a proven one. Any pitch that states "no one does this" would be an unsupported claim given this research.

### Relevant building blocks
- **Chainlink CRE (Chainlink Runtime Environment)** — **Correction (research 2026-10-13):** CRE lists Monad Testnet as a supported network (CLI v1.30.0+), with a simulation forwarder and a production `KeystoneForwarder` for `monad-testnet` (docs.chain.link/cre/supported-networks and …/forwarder-directory, modified 2026-09-18). Caveat: a CLI release note (2026-08-13) describes the Monad Testnet addition as "for local simulation", so whether production deployment works there today is unconfirmed. A CRE workflow can make an HTTP request from every node of a DON, reach BFT consensus and write the result to a consumer contract (docs.chain.link/cre/capabilities/http). Deploying a workflow requires Chainlink's approval; simulation does not. Not used in the hackathon, neither as the reporter nor as a simulation demo (D-10); it is a Post-Hackathon option only (§25). Metropolis also runs a "Best workflow with CRE" bounty (`docs/source/metropolis-notlari/02-trackler-ve-bountyler.md`); with D-10 the team does not enter it.
- **Chainlink Automation / Functions** — not listed for Monad, and Chainlink has announced their deprecation (research 2026-10-13; sources disagree on the exact end dates, so none are quoted here) — cannot be used.
- **Chainlink L2 Sequencer Uptime Feeds** — reports an L2 sequencer's status; an architectural pattern only. Monad is an L1, and these feeds are not a general endpoint-uptime oracle. No general uptime/liveness oracle is listed on docs.monad.xyz/tooling-and-infra/oracles (price feeds and VRF only).
- **UMA Optimistic Oracle** — the closest existing *pattern* (assert → challenge window → bonded dispute → fallback) for automated settlement without a human arbitrator. Confirmed **not deployed on Monad** (rev 2026-09-27; not re-checked); UMA's own docs warn against permissionless use on unsupported chains due to bond-loss risk. The MVP borrows only the assert/window/default *shape* of this pattern conceptually (§11) — it is not a UMA integration and must never be described as one.
- GitHub search for existing "SLA escrow" / "pay-per-uptime" contract repositories returned no directly reusable reference implementation (re-checked 2026-10-13) — this component is purpose-built, though it is a standard escrow + threshold-check pattern, not novel cryptography.

---

## 5. Proposed Solution

The product is a smart contract (deployed on Monad Testnet) with three primitives:

1. **Escrow.** Renter's payment is locked in the contract at agreement creation (price, GPU spec reference, uptime threshold, rental start/end). **Asset (Decision):** the MVP uses native Monad Testnet currency (MON) only — no ERC-20 test token. The agreement-creation call is payable and the price **is** the `msg.value` sent with it — there is no separate price argument (D-05) — so "creation + escrow deposit" is one wallet transaction, not a separate approve-then-transfer sequence. This is testnet MON with no real monetary value (§15, §16).
2. **Reporter-attested settlement.** Any address in a fixed set of team-held reporter addresses (D-02) posts periodic uptime reports tied to a rental ID (exact rules in §9). Once the rental period ends and a fixed report grace period (§9.2) has passed, anyone — not only the platform, renter, or provider — can call a function that deterministically computes whether the accumulated uptime record meets the agreed threshold and proposes a payout split accordingly.
3. **Timeout finality with a non-binding objection log.** A fixed challenge window opens after the proposed outcome is computed. Either party may log an on-chain objection during that window. The objection is recorded as an event but does **not** change the outcome — there is no independent adjudicator in the MVP. At window expiry, anyone can call a finalize function that credits the originally computed payout to the payee, who then withdraws it (pull payment, D-01). This is the accurate description of what was previously (and inaccurately) called "dispute resolution" — see §11.

This does not replace GPU marketplaces — it is a payment/escrow primitive a marketplace, a broker, or two parties directly could choose to route payment through, in place of relying on a single platform's internal, non-portable scoring. Why this approach: it targets the plausible, unconfirmed gap observed in §2/§4 (Problem A) — the absence of an independently auditable settlement record among the platforms actually researched — without claiming to solve price fragmentation (Problem B), to provide trustless verification (see §13), or that this gap has been confirmed across every existing platform.

**User gains:** a settlement outcome computed from an on-chain record, inspectable by anyone after the fact, and triggerable without waiting on a platform's internal process — while being explicit that the underlying uptime data itself still comes from one trusted source in this MVP.

---

## 6. Core User Journey

```text
Renter and Provider agree off-chain on GPU spec, price, uptime threshold, duration
 ↓
Renter creates rental agreement on-chain, escrowing payment (Monad Testnet)
 ↓
Oracle service probes the provider's node health endpoint (a Docker stand-in in
the demo, D-04) and, from a team-held reporter key (D-02), posts one up/down
report on-chain per completed interval (§9)
 ↓
[Demo control: operator runs `docker stop` on the node for at least two slots
 (§20 arithmetic) to show the non-compliant payout path; a scripted force-down
 control is the backup (D-04)]
 ↓
After rental end + REPORT_GRACE (§9.2), ANYONE calls settle() — this is the permissionless
step: no platform, renter, or provider approval is required to trigger it
 ↓
Contract deterministically computes cumulative uptime % from stored reports
and proposes a payout split (§9); a fixed challenge window opens
 ↓
(Optional) Either party calls raiseObjection() during the window — this
records an event only; it does not alter the proposed outcome
 ↓
After the window closes, ANYONE calls finalize() — the proposed payout is credited
to the payee regardless of whether an objection was logged
 ↓
The payee (provider if compliant, renter if not) calls withdraw() to receive the
MON (pull payment, D-01)
 ↓
Renter/Provider see final settlement and full report/objection history on-chain
```

---

## 7. Feature Requirements

Acceptance criteria below specify exact inputs and expected outcomes, not just "correct behavior occurs."

| Feature | Description | User value | Priority | Acceptance Criteria | Dependencies |
|---|---|---|---|---|---|
| Rental agreement creation | Creates an on-chain record: renter, provider, price, uptime threshold (1–100%), start/end timestamps, report interval | Records the renter's agreed terms immutably on-chain. Provider consent is **not** captured on-chain in the MVP — only the renter signs (§15) | P0 | Given valid inputs where `start ≥ block.timestamp` (§9.2), `end > start`, `(end − start)` is a non-zero exact multiple of `interval`, `1 ≤ threshold ≤ 100`, `interval > 0`, `provider ≠ renter`, `provider ≠ address(0)`, `N = (end − start)/interval ≤ 256` (D-05), `start ≤ block.timestamp + 30 days` and `interval ≤ 86,400 s` (D-12), and `msg.value > 0`, a transaction creates a record with exactly those fields, `price = msg.value` (D-05, §5), `N = (end − start)/interval`, and status = Active. Given `start < block.timestamp`, `start ≥ end`, a duration that is not an exact multiple of `interval`, `threshold = 0` or `> 100`, `interval = 0`, `provider == renter`, `provider == address(0)`, `msg.value = 0`, `N > 256`, `start` more than 30 days ahead, or `interval > 86,400 s`, the transaction reverts. | Monad Testnet, wallet |
| Escrow deposit | Renter's payment (native MON, §5) locked in the contract via `msg.value` at creation | Removes reliance on platform custody of funds | P0 | Contract balance increases by exactly `msg.value` at creation, in one transaction; funds leave the contract by no path except `withdraw()` by an address that `finalize()` has credited (§9.1, D-01). | Rental agreement |
| Oracle uptime reporting | Any address in the fixed reporter set (1–8 team-held keys, D-02) posts one up/down report per completed interval slot, tied to a rental ID, until `end + REPORT_GRACE` (§9.2) | Makes the uptime record auditable, not just claimed | P0 | A report for slot index `k` is accepted only if all conditions in §9.3 hold: sender ∈ reporter set; rental status = Active; `block.timestamp ≤ end + REPORT_GRACE`; `k < N`; slot `k` has completed (`block.timestamp ≥ start + (k+1)·interval`); no report already exists for slot `k`. All other cases revert, including any report attempted strictly after `end + REPORT_GRACE`. | Rental agreement |
| Permissionless settlement trigger | Any address can call `settle()` once reporting has closed (`end + REPORT_GRACE` has strictly passed) | Removes any single named party's requirement to act — does not guarantee the call happens (§9.5) | P0 | `settle()` succeeds when called by any address after `block.timestamp > end + REPORT_GRACE`, and only once (status transitions Active → Proposed). Calling it at or before `end + REPORT_GRACE`, or when status ≠ Active, reverts. The computed `N`, `M`, compliance result, and proposed payout are identical no matter which address calls it or how much later than `end + REPORT_GRACE` it is called (§9.1, §9.4). | Oracle reporting, rental agreement |
| Deterministic payout computation | `settle()` computes `N = (end − start)/interval` (fixed at creation) and `M` = count of slots reported "up" (unreported slots count as "down") | Removes "wait for support" step and removes any discretion from the outcome | P0 | Compliance is `100 × M ≥ threshold × N` (§9.4; exact integer comparison, no fractional rounding). If compliant, proposed outcome = full payment to provider. If not, proposed outcome = full refund to renter (binary MVP split — see §8 for the proportional stretch goal). The boundary case `100×M == threshold×N` is compliant. Once computed, this result is frozen and cannot change (§9.1). | Permissionless settlement trigger |
| Challenge window + objection log | Fixed-duration window (`CHALLENGE_WINDOW`, a contract constant, §11) starting at `proposedAt = block.timestamp` when `settle()` succeeds; either party may call `raiseObjection()` during it | Gives both parties a public, on-chain place to record disagreement, without inventing a fake adjudicator | P0 | `raiseObjection()` succeeds only when status = Proposed and `block.timestamp < proposedAt + CHALLENGE_WINDOW` and called by the renter or provider of that specific rental; it emits an event and does not change the proposed outcome or contract state beyond setting that caller's own flag (`renterObjected` or `providerObjected`). **(Decision)** A second call by the same party reverts — one objection per party. Calling it after the window closes, or from any other address, reverts. | Deterministic payout computation |
| Permissionless finalization | Any address can call `finalize()` once `block.timestamp ≥ proposedAt + CHALLENGE_WINDOW` | Removes any single named party's requirement to act — does not guarantee the call happens (§9.5) | P0 | `finalize()` succeeds when called by any address once `block.timestamp ≥ proposedAt + CHALLENGE_WINDOW` and status = Proposed; it transitions status to Settled and then credits the payee's withdrawable balance with exactly the amount computed at `settle()` time, regardless of any objection flag; it sends no MON itself (D-01). Calling it before that time, or when status ≠ Proposed, reverts. | Challenge window + objection log |
| Withdrawal (pull payment) | The payee calls `withdraw()` to receive the MON that `finalize()` credited to it (D-01) | A recipient that rejects native MON can block only its own withdrawal, never finalization or anyone else's funds | P0 | `withdraw()` sends the caller's full credited balance and sets it to zero before sending; it reverts if the balance is zero or the transfer fails, and a failed transfer leaves every other balance and rental unaffected. A second `withdraw()` with nothing credited reverts. | Permissionless finalization |
| Health-probe uptime source | The oracle service probes the provider's node `GET /health` every 5 s during each slot; slot = up only if at least one probe ran in it and every probe that ran returned HTTP 200 within 2 s; a slot with no probe is reported down (D-04). Demo node: a Docker container | Replaces invented data with a real, observable health check (the reporter is still team-held, §10) | P0 | Stopping the container (`docker stop`) for a whole slot results in that slot being reported "down", reflected in the computed uptime % at `settle()` time; with the container running and probed, slots are reported "up"; a slot of a served rental in which the service ran no probe is reported "down" (a rental whose provider has no configured node is not reported at all, D-13, §10) | Oracle uptime reporting |
| Force-down backup control | Script action that makes the oracle report "down" for chosen slots regardless of probes (backup if Docker fails on stage, D-04) | Keeps the non-compliant path demonstrable if the live probe fails | P1 | Triggering it results in that slot being recorded "down," which is reflected in the computed uptime % at `settle()` time | Oracle uptime reporting |
| Minimal frontend | Wallet connect, create-agreement form, live status/report view | Makes the on-chain logic visible and demoable | P1 | A user can complete the full journey (§6) via the UI, including calling `settle()`/`finalize()` from a button (any connected wallet can click it — the UI does not gate who may call these) and `withdraw()` for the payee | Contract deployed, wallet |
| Event log / history view | On-chain events (`RentalCreated`, `UptimeReported`, `SettlementProposed`, `ObjectionRaised`, `SettlementFinalized`, `Withdrawn`) surfaced in UI | Lets anyone audit what happened, not just trust the outcome | P2 | Frontend lists events per rental in chronological order | Minimal frontend |
| Independent / staked reporter set | Reporters held by independent parties with consensus (e.g. staked reporters or a DON, §25), replacing the team-held keys | Removes the single point of trust in the uptime data itself | Future | — | Out of scope for hackathon |
| Real provider onboarding | Actual GPU node operators register and run real workloads | Makes the provider side real, not simulated | Future | — | Requires physical hardware / real operators |

---

## 8. MVP Definition

**Must Have**
- Escrow contract on Monad Testnet implementing: agreement creation, escrow deposit, reporter-restricted slot-indexed uptime reporting (fixed reporter set, D-02), permissionless `settle()` with the deterministic uptime-% computation in §9, a fixed challenge window with a non-binding `raiseObjection()`, permissionless `finalize()` that credits the payee, and `withdraw()` (pull payment, D-01).
- An oracle service, trusted and team-operated, that probes the demo node's health endpoint (D-04) and posts per-slot uptime reports from team-held reporter keys, one key per rental (D-02), only for rentals whose renter is on the service's allow-list and within a per-rental report budget (D-11).
- A Docker container standing in for the provider's GPU node, so a live `docker stop` makes slots "down" (two or more slots, §20) (D-04). The live demo and every rehearsal of it use these health-probe nodes (one container per provider, §20) on the team's WSL machine (D-10); the oracle service runs on the same machine (`docs/UI_HANDOFF.md` §7).
- Demo interface: minimal frontend (§7, P1) or the `cast`/script fallback — one of the two is required. Frontend scope: wallet connect, create agreement, watch reports arrive, call `settle()`/`finalize()`/`withdraw()`. If frontend implementation slips, fall back to a scripted CLI/`cast`-driven demo narrated over the block explorer (§20) rather than dropping the on-chain demo entirely.

**Should Have**
- Scripted force-down control as a backup to the Docker probe (D-04, §7 P1).
- Proportional (non-binary) refund based on how far uptime % fell short of threshold, instead of a binary full-pay/full-refund split.
- On-chain event history visible in the frontend.

**Could Have**
- A bonded objection (small stake at risk for raising a false or spam objection) — makes the objection log costlier to grief, still not a real adjudicator.
- Basic per-provider on-chain history counter (cumulative past compliant rentals).
- A non-gating `provider_ack` event the provider can emit for a rental, recording acknowledgement without blocking anything (D-07).

**Out of Scope (hackathon)**
- Real GPU hardware, real workload execution, real uptime monitoring of physical machines.
- Reporters held by independent parties, or staked reporter consensus. A Chainlink CRE reporter layer is also out of the hackathon scope, both as the reporter and as a simulation demo (D-10); it stays a Post-Hackathon option (§25).
- TEE-based (NVIDIA Confidential Computing) cryptographic proof of GPU work — not part of this hackathon MVP because the team does not have the required H100-class hardware with specific VBIOS/driver/CPU support (NVIDIA source, §26); not a claim that the technology is infeasible in general.
- Integration with UMA or Chainlink Automation/Functions — none is available on Monad (§4).
- Any actual dispute adjudication (human, DAO-vote, or algorithmic) — the MVP's "challenge window" is explicitly a non-binding objection log, not adjudication (§11).
- Reporter rotation or any admin function — the reporter set is fixed at deployment (D-02, §10). On-chain per-rental reporter assignment is also out of scope: any reporter may report any rental; the one-key-per-rental choice is a rule of the off-chain service only.
- Real two-sided marketplace / provider onboarding flow.
- On-chain provider acceptance that gates an agreement, and pre-start cancellation (§15 documents both as MVP limitations; D-07).

### 8.1 Hackathon Feasibility Verdict

**Can a sufficient MVP be built for the hackathon? Yes (Decision, based on scope).**
- The contract is a standard escrow with a three-state machine, one integer threshold check and a withdraw function; it has no external protocol dependencies (§13).
- The GPU side is mocked by design (a Docker container stands in for the node), so no hardware is required (§1, §20).
- Monad Testnet is EVM-compatible: "All opcodes as of the Fusaka fork are supported" (docs.monad.xyz/developer-essentials/summary, checked 2026-10-13). Vyper 0.4.3's default EVM target is Prague, which precedes Fusaka, so compilation should be compatible — an inference, not tested; the day-0 gate decides (D-03, §21).

**Context:** Metropolis is a six-week hackathon (`docs/source/metropolis-notlari/01-metropolis-nedir.md`); the team is two people, with the UI owned by the teammate (CLAUDE.md). The organizers advise using the six weeks to put an early version in front of real users rather than as extra build time. D-08 plans interviews only, not product use by real users; whether to go further is open (§23).

| Workstream | Rough effort (person-hours, Assumption) |
|---|---|
| Contract + tests (titanoboa/pytest, D-03; every revert in §7/§9.3, both demo runs in §20) | 8–12 |
| Oracle script as scoped in rev 2026-09-27 (per-slot transactions, force-down control, explicit tight gas limit) | 2–4 |
| Minimal frontend (§7 P1) | 6–10 |
| Demo prep: deploy, fund wallets, rehearse §20 twice, record backup video | 4–6 |
| **Total (rev 2026-09-27 scope)** | **~20–32** |
| Added since: withdraw (D-01), multi-key reporter service (D-02), Vyper day-0 gate (D-03), Docker health probe (D-04) | not estimated |

**Cut order if time runs short (first to go at the top):**
1. P2 event-history view
2. Could-Haves (bonded objection, per-provider counter)
3. Proportional refund (Should-Have)
4. Frontend — replaced by the `cast`/script fallback narrated over the block explorer (§20)

**Never cut:** the P0 contract behaviors (including `withdraw()`), an oracle service that can mark slots "down" (Docker probe, or the force-down backup if the probe fails), and the third-wallet `settle()`/`finalize()` step.

---

## 9. Settlement State Machine & SLA Measurement Model

This section exists because "cumulative uptime %" and "automatic settlement" were previously underspecified, and because the same rental must produce the same settlement outcome no matter who calls `settle()`/`finalize()` or when they call it. Every rule below is a deterministic, hackathon-appropriate policy choice — not a claim that it is the only correct design. Where a rule is a product decision rather than something derivable from research, it is labeled **(Decision)**.

### 9.1 State machine, defined without ambiguity

```text
Active → settle() → Proposed → challenge window elapses → finalize() → Settled
```

- **Active** (from creation until `settle()` succeeds):
  - Oracle uptime reports: **accepted**, subject to the slot-completion and timing rules in §9.3 — but **only while `block.timestamp ≤ end + REPORT_GRACE`** (Decision, see §9.2: reporting closes at a fixed instant, not at the moment `settle()` happens to be called).
  - `settle()`: **accepted** only once `block.timestamp > end + REPORT_GRACE`; reverts before that (see §9.2 for why this is a strict `>`, not `≥`).
  - `raiseObjection()`, `finalize()`: **reverts** — both require a later state.
- **Proposed** (from a successful `settle()` call until a successful `finalize()` call):
  - Oracle uptime reports: **reverts unconditionally.** Reporting was already closed at `end + REPORT_GRACE` (previous bullet), so by construction no report can arrive during this state either — this is stated twice, in both states, so the rule cannot be read as ambiguous.
  - The uptime record (`M`, `N`, computed %, compliant/non-compliant, proposed payout split) computed at `settle()` time is **frozen and immutable** for the rest of this rental's lifecycle. Nothing that happens afterward changes it.
  - `raiseObjection()`: **accepted**, only from that rental's renter or provider, only before the challenge window closes, at most once per party — a repeat call reverts (§11).
  - `settle()` again: **reverts** — it is callable exactly once per rental.
  - `finalize()`: **reverts** until the challenge window has closed; **accepted** afterward.
- **Settled** (terminal, after a successful `finalize()` call):
  - Oracle uptime reports, `settle()`, `raiseObjection()`, `finalize()`: **all revert unconditionally.** Nothing about this rental can change again.
  - The payee's credited amount stays in the contract until the payee calls `withdraw()` (D-01). Withdrawal is per address, not per rental, and is not a rental state transition.

**Direct answer to "can the oracle submit a new report after `settle()` is called?": no.** Reporting requires `block.timestamp ≤ end + REPORT_GRACE`; `settle()` requires `block.timestamp > end + REPORT_GRACE`. These conditions are mutually exclusive on the same timestamp, so there is no instant at which both a report and a `settle()` call could succeed — reporting and settlement never overlap in time. This is what guarantees the "same rental, different caller, different time, same result" property: by the time anyone can call `settle()`, the uptime record for that rental can no longer change, and `N`'s definition (§9.4) does not depend on when `settle()` is actually invoked, only on the rental's own fixed parameters.

### 9.2 Report interval, slots, and the rental-end cutoff

**(Decision)** Each rental agreement fixes a report interval at creation. The rental's duration is divided into slots of that interval, indexed 0, 1, 2, … from the rental's start timestamp. Slot `k` covers `[start + k·interval, start + (k+1)·interval)` — it **completes** at `start + (k+1)·interval`.

**(Decision) Duration must be an exact, non-zero multiple of the interval, enforced at creation:** agreement creation reverts unless `(end − start) > 0` and `(end − start) mod interval == 0`. This removes the "partial last slot" question entirely — there is no partial slot, because the only durations the contract will accept divide evenly into whole slots, and the last slot (`k = N−1`) therefore completes at exactly `start + N·interval = end`. It also guarantees `N ≥ 1` (see §9.4): `N = 0` is impossible, because a duration shorter than one interval is rejected at creation, not handled specially at settlement time.

**(Decision) A slot is only reportable once it has completed — not while it is still in progress or in the future.** A report for slot `k` requires `block.timestamp ≥ start + (k+1)·interval` (the slot has actually finished). Reporting a slot before it completes (whether currently running or entirely in the future) is rejected — this is the fix for the earlier draft's flaw, which allowed reporting a slot that was still running.

**(Decision — resolves the last-slot boundary) Reporting closes at `block.timestamp ≤ end + REPORT_GRACE` (inclusive); `settle()` requires `block.timestamp > end + REPORT_GRACE` (strict).** `REPORT_GRACE` is a single fixed contract constant, like `CHALLENGE_WINDOW` (§11) — the same for every rental, not changeable by any admin. Rationale: it is the smallest change that gives the last slot a real reporting window while keeping reporting and settlement non-overlapping and `N`/`M` time-invariant.

- **Why it is needed — Verified (docs.monad.xyz/developer-essentials/summary, re-checked 2026-10-13, D-06):** "`TIMESTAMP` is a second-granularity unix timestamp. Since blocks are every 300 ms, this means that 3-4 blocks will likely have the same timestamp."
- **Assumption (not measured):** without a grace period, the last slot (`k = N−1`, which completes exactly at `end`) could only be reported in blocks stamped exactly `end` — roughly a 1-second window. Public-RPC and mempool latency would plausibly make the oracle miss it, so the final slot would be scored "down" regardless of real uptime, systematically biasing against the provider. The previous draft's `block.timestamp == end` rule had exactly this flaw.
- **Why it keeps determinism:** every slot completes no later than `end`, so no new slot becomes reportable during the grace period — it only extends the deadline for slots that have already completed. Because `REPORT_GRACE` is a constant, `N` and `M` are fully fixed by the time `settle()` becomes callable (§9.1).
- **Rejected alternatives:** accepting reports until `settle()` is called (makes `M` depend on call timing); a per-agreement grace field (an extra parameter a constant makes unnecessary); shifting slot boundaries (changes semantics of every slot to fix one).

A report that misses `end + REPORT_GRACE` counts as "down" (§9.4), the same as any other missing report.

**Start-timestamp policy (Decision):** the creation function requires `start ≥ block.timestamp`, evaluated against the `block.timestamp` of the block in which the creation transaction actually executes — a rental cannot be created with a start already in the past at that execution time. Future-start rentals are allowed, but only up to 30 days ahead: creation reverts if `start > block.timestamp + 30 days`, and the interval is capped at one day (`interval ≤ 86,400 s`) (D-12). With at most 256 slots (D-05) a rental therefore ends at most 286 days after it is created, so `end + REPORT_GRACE` can never overflow and every rental becomes settleable (§15). This, combined with the completion-based reportability rule above (which only ever *adds* to `start`, never subtracts `start` from `block.timestamp`), removes any unsigned-timestamp-underflow risk: no computation in this model ever depends on `block.timestamp − start` being non-negative, because reportability is checked as `block.timestamp ≥ start + (k+1)·interval`, an addition-based comparison. A direct consequence, requiring no separate rule: no slot can ever be reported before `start + interval` has elapsed, so no report can ever be accepted before `start` itself — "reports before start" are structurally impossible, not merely disallowed by a separate check.

### 9.3 Oracle report acceptance — every edge case, resolved

A report for slot `k`, for rental `R`, is accepted **only if all of the following hold**; otherwise it reverts, with no exceptions:

| Condition | Rule |
|---|---|
| Sender | `msg.sender` is one of the reporter addresses fixed at deployment (§10, D-02). Any reporter may report any rental; which key reports which rental is a rule of the off-chain service, not of the contract |
| Rental exists and is Active | Reverts for a nonexistent rental ID, or one in `Proposed`/`Settled` state |
| Timing | `block.timestamp ≤ end + REPORT_GRACE` (§9.2) — reverts for any report attempted strictly after that |
| Slot validity | `k < N` (a real slot for this rental) |
| Slot completed | `block.timestamp ≥ start + (k+1)·interval` — the slot has actually finished; a currently-running or future slot reverts (§9.2) |
| Not already filled | Slot `k` has no existing report — a second report for the same `k` reverts (this is the complete answer to "duplicate slot": rejected, not overwritten) |

**Can the oracle backfill an earlier slot it missed?** Yes — explicitly. As long as slot `k` has completed, has no existing report, and `block.timestamp ≤ end + REPORT_GRACE`, the oracle may submit it at any point up to and including `end + REPORT_GRACE`, even long after that slot's own completion instant has passed. This is the deterministic answer to "can a skipped slot be filled later": yes, up to and including `end + REPORT_GRACE`, and never after.

**What happens to a slot the oracle never fills at all, by `end + REPORT_GRACE`?** It remains "down" permanently — see §9.4 (missing reports).

**Report after `end + REPORT_GRACE` (strictly after), after `settle()`, or after `finalize()`:** all three are the same case under this model — reporting requires `block.timestamp ≤ end + REPORT_GRACE`, and `settle()` can only ever be called strictly after that — so any report attempt from that point onward reverts on the timing condition alone, independent of the rental's Active/Proposed/Settled status. Both guards exist (§9.1 status check and this timing check) so the rule holds even if one were read in isolation.

### 9.4 Missing reports, and the `N`/`M` computation

**(Decision) Missing reports count as "down":** if the oracle never submits a report for slot `k` by the time `end + REPORT_GRACE` is reached, slot `k` is treated as "down" in the uptime computation. Multiple missing slots simply each count as down independently — there is no special aggregate handling. This favors the renter in ambiguous cases (silence is treated as non-performance) — a policy choice, not a neutral default, and not something providers can contest within the MVP (only logged as an objection after the fact, per §11).

**`N` (total slots) is fixed by the rental's own parameters, never by call timing:**

```text
N = (end − start) / interval
```

Because §9.2 requires this division to be exact, `N` is a fixed positive integer determined entirely at agreement-creation time. It does **not** depend on `block.timestamp` at all, and therefore does not depend on when `settle()` happens to be called or by whom — this is what guarantees identical results regardless of caller or call time.

**`M` (slots reported "up")** is the count of slots among `0..N−1` that have an "up" report recorded. Because reporting is closed at `end + REPORT_GRACE` (§9.2) and the record is frozen once `Proposed` (§9.1), `M` is likewise fixed and immutable by the time `settle()` can be called.

**Compliance check, defined to avoid division/precision ambiguity:** rather than comparing `M/N` to `threshold/100` as two separately-computed fractions (which risks integer-division precision loss or rounding disagreements between different implementations), this PRD defines the comparison via cross-multiplication, which is exact for integers and requires no rounding:

```text
compliant  ⇔  100 × M  ≥  threshold × N
```

This is mathematically equivalent to `M/N ≥ threshold/100` but avoids ever computing a fractional uptime value internally. Threshold is represented as a whole-number percentage, 1–100 inclusive (0 is rejected at creation, per §7). Boundary case: `100×M == threshold×N` is compliant (`≥`, not `>`) — a rental landing exactly on the threshold is a pass, not a miss.

**Payout from compliance:** compliant → full payment to provider; non-compliant → full refund to renter (binary MVP split; a proportional split based on how far `M/N` fell short is a Should-Have stretch item, §8, and is not part of the MVP computation above).

**Performance-score metric:** explicitly **not** part of the MVP, and not a Should-Have either — it is Future scope only (§25), unspecified beyond the one-line mention there. Only uptime (up/down per slot) is measured in the MVP and in the Should-Have proportional-refund stretch item (§8). Any mention elsewhere in this document of "performance" as something the MVP or Should-Have scope measures is an error and must not be assumed present in the MVP acceptance criteria (§7).

### 9.5 Who calls `settle()`, `finalize()` and `withdraw()`, and what happens if nobody does

**Who calls them:** any address, with no allowlist. This is the concrete meaning of "permissionless" in this product (§1): no single designated party (not the platform, not specifically the renter or the provider) is *required* to trigger these steps — the renter, the provider, or an unrelated third party (e.g. an operator-triggered script external to the contract) may each independently call them — none of these is required, and none of this implies the transaction happens without some external actor sending it. This does **not** mean execution is guaranteed or automatic (§1) — see the next paragraph.

**What happens if nobody ever calls them:** funds remain escrowed indefinitely. This is a known liveness limitation of the MVP, not a solved problem — the design relies on some external party (renter, provider, or an unrelated caller) actually choosing to submit the transaction; nothing in the contract guarantees this happens, and this PRD makes no claim about how likely or unlikely that is. A production version would likely want a keeper-incentive mechanism to guarantee execution; this MVP does not include one.

**`withdraw()` (D-01):** only the credited payee can withdraw its own balance, so after `finalize()` the payee — not a third party — must act. If the payee never calls it, the MON stays credited to that payee in the contract; nobody else can take it. If the payee is a contract that rejects native MON, only that payee's own withdrawal fails; `finalize()` and every other balance are unaffected (§15).

---

## 10. Oracle Trust Model

**Who controls the reporters (D-02):** a fixed set of one to eight Monad addresses, all held by the team, passed to the contract once at deployment. The set cannot be changed afterwards — there is no admin function and no rotation. Any address in the set is authorized to report any rental.

**Why several keys, and what they do not change (D-02):** all reports from one address share one nonce sequence: they execute in nonce order, and one stuck or failed transaction holds back every later report from that address. The off-chain service therefore sends each rental's reports from one key chosen deterministically per rental, so different rentals' reports use independent nonces and one rental's stuck transaction cannot delay another's; the report path writes only that rental's own storage. (Several transactions from one sender can also share a block; the benefit claimed is isolation, not that one key could not.) Monad's documentation describes optimistic parallel execution over storage reads and writes but says nothing about same-sender versus different-sender transactions and publishes no measured gain for this pattern (docs.monad.xyz/monad-arch/execution/parallel-execution, research 2026-10-13). The claim is therefore limited to independent nonces and separate per-account gas budgets under Monad's reserve-balance rule; no parallel-execution speedup is claimed. All keys are held by one team, so there is still **one trust root**. Required pitch line: "We removed the nonce bottleneck; the source of trust is still one team — the next step is an independent reporter set."

**What "the oracle submits" means, precisely:** the oracle service sends an ordinary EVM transaction — signed with one reporter key the same way any blockchain transaction is signed — calling the reporting function directly with a per-slot boolean up/down value for a specific rental ID. There is no separate off-chain attestation or signature scheme (no message signed off-chain for the contract to verify against a public key); authorization is simply that `msg.sender` is in the reporter set, checked by the contract on the transaction itself. Anywhere else in this document that says the oracle "signs" or "posts" a report, this transaction-signing meaning is what is intended.

**What "up" means (D-04):** the oracle service maps each provider address to a node URL and probes `GET /health` every 5 s during a slot. A slot is reported "up" only if at least one probe ran in that slot and every probe that ran returned HTTP 200 within 2 s; otherwise it is reported "down". For a rental the service serves, a slot in which no probe ran at all (service restarted, started late, or its loop stalled) is therefore reported "down", in line with the "missing report = down" policy (§9.4) (D-04, clarified 2026-10-13). Residual limitation: one successful probe is enough, so a slot in which the service ran only some of its expected probes is still reported "up" if all of those succeeded. In the demo the node is a Docker container the team runs; stopping it during a slot makes that slot "down". A scripted force-down control can override probes as a backup if Docker fails on stage. The health check is real; the GPU behind it is not, and the probe proves reachability of an endpoint, not that GPU work was done.

**What the contract trusts:** the contract trusts that a transaction from any reporter address is sufficient authorization to write uptime data for any rental. It does not verify anything about the real world — it has no way to know whether the reported GPU was actually up, or whether the reporter actually ran the probe. This is the core, explicitly disclosed trust assumption of the entire MVP.

**If a reporter reports incorrectly (by error or by intent):** the settlement outcome will be wrong in exactly the way the report was wrong — there is no independent check. The objection log (§11) records that someone disagreed but does not correct the outcome. This is the sharpest limitation of the MVP and must not be minimized in the demo narration (§20).

**Liveness failure, distinct from incorrect data:** if the oracle service fails to submit a report for a slot at all — regardless of whether the node was actually up — the "missing report = down" policy (§9.4) treats that slot as non-compliant. The same holds when the service ran no probe in a slot of a rental it serves: it reports that slot "down" (D-04; rentals it does not serve are covered below, D-13), and the on-chain record does not distinguish this from a probed failure. This is a deliberate MVP policy, not a bug: an oracle outage (service crash, network issue, key unavailable or out of gas) has a direct economic consequence for the provider, who loses payment for slots that were not attested even if the node never went down. The service retries each report until `end + REPORT_GRACE`, within the per-rental report budget (D-11); beyond that this is not mitigated in the MVP except by operational care during the demo (§21).

**Rentals whose provider has no node (D-13):** the service probes a rental only if its provider address has a node URL in the service's configuration. A rental naming any other provider is not probed and not reported at all — the service sends no "down" reports for it either. Unless a reporter key reports it outside the service (the contract accepts any reporter for any rental, §9.3), its slots stay unreported, which the contract counts as "down" (§9.4), so it settles as a refund to its renter; on-chain it then shows empty slots, not "down" reports. The renter gets no on-chain signal that the rental is unserved. This is how the service behaves today. The provider gate and the renter gate of D-11 are cumulative: a rental is reported only if it passes both.

**Which rentals the service reports (D-11):** creating a rental stays open to anyone — anyone can create a rental that names any provider, and the contract accepts a report for any rental from any reporter. The oracle service is narrower by choice: it reports only rentals whose renter address is on an allow-list in its configuration, and it sends at most 2 × `N` report transactions per rental (the report budget; `N` is the rental's slot count). Every report transaction the service sends for the rental counts against the budget, including a re-submission of a slot it already sent (a retry or a fee replacement). The budget is never below `N`: the first send of each slot is always allowed, and re-submissions share the other `N` transactions, so retries of one slot cannot stop a later slot from being sent once (D-11, clarified 2026-10-13). A rental created by a renter who is not on the list gets no reports at all, so every slot counts as "down" (§9.4) and it settles as a refund to its own renter. Once a rental's `N` re-submissions are used, no report is re-sent for it any more: a slot whose transaction is still not mined by `end + REPORT_GRACE` counts as "down", which can turn a rental the node served into a refund. The budget also bounds the retries of §10's liveness rule: the service retries until `end + REPORT_GRACE` or until the budget is spent, whichever comes first. Implemented in the oracle service on 2026-10-13 (SPEC H-8, H-9). This protects the team's reporter keys from paying gas for rentals the team did not agree to serve; it is a rule of the off-chain service, not of the contract, and it is one more way in which the reporting side is team-controlled.

**If a reporter key is compromised:** an attacker with **any one** of the reporter keys can post arbitrary uptime data for any active rental's unreported slots, in either direction (falsely up or falsely down), because the contract does not bind keys to rentals. More keys therefore mean more attack surface, not less. Hackathon-level mitigation: none beyond ordinary key hygiene (keys only in a git-ignored `.env`, testnet funds only). Production-level: key rotation, per-rental key binding, a multisig, or replacing team-held keys with an independent or staked reporter set (§8, §25).

**Replay/reordering:** closed structurally by the slot-index model (§9) — a report can only ever be accepted for one specific slot, once, so there is no "reorder" or "replay an old report as new" attack surface distinct from the stale/duplicate rules already specified. Two reporters racing on the same slot is the duplicate case: the first accepted report stands, the second reverts.

**Reporter rotation:** not supported in the MVP (D-02). Changing the reporter set would require a redeploy. Flagged as Future, not a silent gap.

**Per-rental reporter scoping on-chain:** not implemented — every reporter is authorized for every rental. A production version would likely scope authorization per rental (so a provider could nominate its own attestor, or a marketplace could run its own), but this adds complexity the MVP does not need to demonstrate the core escrow/settlement mechanic.

---

## 11. Timeout Finality with Non-Binding Objection Log (formerly "dispute resolution")

**Why the rename:** the original framing called this "dispute resolution." It is not — there is no independent adjudicator, no evidence review, and no mechanism by which raising an objection changes the outcome. Calling it dispute resolution would overclaim in exactly the way a technically literate judge would catch immediately. What follows is the accurate, narrower description.

**What it does:** after `settle()` computes a proposed outcome from the oracle's report record, a fixed challenge window opens. During that window, the renter or the provider (only) of that specific rental may call `raiseObjection()`, which emits an on-chain event recording that they disagreed with the outcome. It does not pause, alter, or re-evaluate anything.

**Window duration and timing, defined precisely (Decision):** the challenge window's length (`CHALLENGE_WINDOW`) is a single fixed constant built into the contract — the same duration for every rental, not a per-rental parameter and not adjustable by any governance or admin action, consistent with this MVP having no adjudication or configuration layer. When `settle()` succeeds, it records `proposedAt = block.timestamp` (which, per §9.2, is always `> end + REPORT_GRACE`). `finalize()` becomes valid once `block.timestamp ≥ proposedAt + CHALLENGE_WINDOW`, and reverts before that. The exact numeric value of `CHALLENGE_WINDOW` is an implementation parameter chosen for demo pacing; the demo value (60 s) is fixed in §20.

**Does settlement pause while "disputed"?** Funds are not credited until `finalize()` is called after the window closes, and not paid out until the payee calls `withdraw()` (D-01) — this is true whether or not an objection was raised. Raising an objection does not further delay this; the window length is fixed regardless.

**Who can object:** only the two named parties to that specific rental (not third parties, not the oracle), at most once each — a repeat call by the same party reverts (§7).

**Cost of objecting:** none in the MVP (no bond, no stake). This is a known griefing surface — an objection is free to raise and does nothing except emit an event, so the incentive to spam it is low, but so is the cost of doing so. A bonded objection is a Could-Have stretch item (§8) that would make frivolous objections costly without turning this into real adjudication.

**Can settlement happen without ever going through this window?** No — every rental passes through the Proposed state and its fixed window before `finalize()` is callable; the window is not skippable, only unobjected-to.

**What happens after the window, definitively:** `finalize()` credits the exact payout computed at `settle()` time to the payee (D-01). An objection having been raised has zero effect on this. This is the honest final answer to "what does the timeout resolve to": it resolves to whatever the oracle reported, always — the mechanism's only real function is to create a public record of disagreement, not to change outcomes.

**What this component is actually for, stated plainly:** it gives both parties a durable, on-chain place to register "I disagree with this outcome" for future reference (e.g., if they later want to stop using this oracle, or if a future version adds real adjudication that could consult this log) — it is a transparency feature, not a fairness mechanism, for the hackathon MVP.

---

## 12. Technical Architecture

- **Frontend (teammate-owned):** minimal web app (wallet connect via standard EVM wallet added to Monad Testnet, chain ID 10143; agreement creation form; live status/report/event view; buttons that call `settle()`/`finalize()`, callable by any connected wallet, and `withdraw()` for the payee). The contract↔UI interface (function names, events, view helpers such as a rental `phase`) is frozen and documented in `docs/UI_HANDOFF.md` and `docs/INTERFACE_CHANGELOG.md`; exact names and revert strings are in `docs/SPEC.md` (snake_case there, e.g. `raise_objection`).
- **Smart contract (Vyper 0.4.3, D-03; Solidity fallback with the same interface if the day-0 gate fails; Monad Testnet, chain ID 10143):**
  - `RentalAgreement` record: renter, provider, GPU spec reference, price, uptime threshold (whole-number percent, 1–100; 0 rejected at creation, §7), report interval, start/end timestamps, escrowed amount, status enum (`Active` → `Proposed` → `Settled`). The GPU spec reference is not used by settlement logic, acceptance criteria, or the demo (§6, §7, §20) — it is carried only as an off-chain-agreed descriptive field, with no storage format or mechanism specified here.
  - Escrow logic: native MON deposit via `msg.value` in the same payable creation call (§5) — no ERC-20 approval step; price = `msg.value` (D-05); at most 256 slots per rental (D-05); `start` at most 30 days ahead and `interval` at most 86,400 s (D-12); funds leave only through `withdraw()` of an amount `finalize()` credited (D-01).
  - Reporter-restricted reporting function: one boolean report per completed slot index per rental, from any address in the reporter set fixed at deployment (1–8 addresses, D-02, §10); writes only that rental's storage; rejects any report strictly after `end + REPORT_GRACE`, or for a not-yet-completed slot (§9.2, §9.3).
  - Contract constants: `REPORT_GRACE` (§9.2) and `CHALLENGE_WINDOW` (§11); demo values in §20.
  - `settle()`: permissionless, callable once `block.timestamp > end + REPORT_GRACE`; computes the compliance check per §9.4 from the now-frozen report record, records `proposedAt = block.timestamp`, and stores the proposed outcome immutably; opens the challenge window (§11).
  - `raiseObjection()`: callable only by that rental's renter or provider, only while `block.timestamp < proposedAt + CHALLENGE_WINDOW`; emits an event, sets only the caller's own objection flag; one objection per party (a repeat call reverts).
  - `finalize()`: permissionless, callable once `block.timestamp ≥ proposedAt + CHALLENGE_WINDOW`; sets Settled, then credits the proposed payout to the payee; makes no external call (D-01).
  - `withdraw()`: pays the caller its full credited balance, zeroing it before the transfer and guarded against reentrancy (D-01).
  - Events: `RentalCreated`, `UptimeReported`, `SettlementProposed`, `ObjectionRaised`, `SettlementFinalized`, `Withdrawn`.
- **Oracle service (off-chain, Python):** discovers rentals from `RentalCreated` events, probes each provider's node health endpoint during every slot (D-04), and after each slot completes submits one ordinary EVM transaction carrying up/down, signed with that rental's reporter key (D-02; standard transaction signing, not an off-chain attestation scheme — see §10), with an explicit tight gas limit, retrying until `end + REPORT_GRACE` within a per-rental report budget. It serves only rentals from allow-listed renters (D-11, §10). Includes a force-down backup control and logs every probe and transaction hash for the demo video. Team-operated, one trust root (§10); explicitly not a decentralized watcher network.
- **Demo node:** a Docker container exposing `GET /health`, standing in for the provider's GPU node (D-04). The containers run on the team's WSL machine and are the only uptime source for the live demo and its rehearsals (D-10); the force-down control stays as the backup (D-04).
- **Tooling:** Vyper 0.4.3 with titanoboa + pytest for contract development and tests (D-03); Viem ≥2.40.0 for frontend contract calls; Monad public RPC (`https://testnet-rpc.monad.xyz`) and faucets for testnet funds; a smoke-test script that deploys a minimal Vyper contract and measures block time on day 0 (D-03, D-06).
- **On-chain vs off-chain split:** On-chain = escrow, thresholds, per-slot uptime records, settlement/payout logic, challenge window, objection flags, event history. Off-chain = actual GPU workload (mocked entirely), the report-generation script, the UI/indexer.

---

## 13. Blockchain Architecture & Value Proposition

**What the MVP actually proves, stated at the correct strength:** with team-held reporter keys (one trust root, §10), this system does not provide independent verification of what happened on a GPU — it provides a public, tamper-evident *record* of what one trusted party reported, plus a settlement rule anyone can trigger and audit. An off-chain database with an API could reproduce the same threshold/timeout business logic, but it would not provide the same public, tamper-evident execution history and contract-controlled custody of escrowed funds — a database's operator could still quietly alter already-written records or withhold custody of escrowed funds in a way this contract's design does not permit. (The oracle can still steer the outcome by what it reports or omits, §10.)

**What blockchain provides here:**
- A tamper-evident public record of the oracle's per-slot reports, once written, immutable (§9.1).
- Fixed settlement rules (§9.4) that execute identically regardless of who calls them.
- Permissionless transaction triggering — no platform or counterparty gatekeeper for `settle()`/`finalize()` (§9.5).
- Custody of escrowed funds by contract logic rather than by a platform's internal ledger.
- A public transaction/event history any party can independently inspect after the fact.

**What blockchain does not provide here:**
- Real-world verification of actual GPU uptime — the contract only ever knows what the oracle told it (§10, layer 1 in §2).
- A trustless or decentralized oracle — the MVP's reporters are team-controlled keys (§10, D-02).
- Independent measurement of ground truth — nothing in the contract checks the oracle's claims against reality.
- Automatic transaction initiation — every state transition still requires some address to send a transaction; the chain does not act on its own (§1, §9.5).

**What would make the stronger claim (independent verification) true:** replacing the team-held keys with reporters run by independent parties (staked reporters, or a decentralized oracle network such as a Chainlink CRE workflow, which lists Monad Testnet — §4; a Post-Hackathon option, §25, D-10) where no single party's report is authoritative on its own. That is not part of this MVP.

**Is the added complexity worth it for the narrower claim alone?** Open, unvalidated question (§22, §23) — the author's own question in the original idea document is legitimate and this research does not resolve it either way.

### Why Monad specifically?

**Decision, stated plainly:** Monad is the hackathon's target chain. The design is a standard EVM escrow and would work on any EVM chain; **no technical superiority over other EVM chains is claimed.** Documented Monad properties that suit — but are not unique to — the per-slot reporting model:

- **Verified (re-checked 2026-10-13, D-06):** 300 ms blocks, finalized after two blocks (600 ms) (docs.monad.xyz/developer-essentials/summary; docs.monad.xyz/introduction/monad-for-developers). The releases page records the change from 400 ms blocks / 200M block gas to 300 ms / 150M in July 2026 (testnet ~2026-07-09). Some pages still show the older values — the faucet page ("400 ms block times and 800ms finality"), the changelog revision table, and the Metropolis notes — and must not be quoted. Each oracle report confirms well within a short demo slot, which is what makes the short demo intervals in §20 practical. Other fast L2s offer comparable latency.
- **Verified:** minimum base fee 100 MON-gwei; the docs' own example puts a 200k-gas transaction at 0.02 MON (docs.monad.xyz/developer-essentials/gas-pricing). **Estimate, not documented:** a single report transaction (~60–100k gas) should therefore cost on the order of 0.01 MON — affordable for one write per slot on testnet.
- **Verified constraint, not an advantage:** `block.timestamp` is second-granularity exactly as on Ethereum — "3-4 blocks will likely have the same timestamp" (docs.monad.xyz/developer-essentials/summary). Monad gives no finer on-chain time resolution; this is why the reporting cutoff uses a grace period (§9.2).
- **Separate reporter keys (D-02):** each sender has its own nonce sequence and its own in-flight gas budget, so a stuck report for one rental does not hold back reports for others. Monad's docs describe optimistic parallel execution but do not document a speedup for this pattern, so none is claimed (§10).
- **Verified operational gotchas:** gas is charged on the transaction's gas *limit*, not gas used (gas-pricing page) — the oracle must set tight gas limits; included-but-reverting transactions still pay gas. Reserve balance (docs.monad.xyz/developer-essentials/reserve-balance, research 2026-10-13): the default is 10 MON per account; a transaction reverts if its **value spend** would leave the sender below 10 MON, except an "emptying" transaction (undelegated sender with no other transaction in the previous 3 blocks). Zero-value transactions (reports, `settle()`, `finalize()`) are limited only by the in-flight gas budget, min(10 MON, balance). The renter's payable creation call is the one affected (§22); public RPC is rate-limited (~20–50 rps); the testnet was reset from genesis on 2025-12-16 (docs.monad.xyz/developer-essentials/testnets), so a reset before demo day is a real, not hypothetical, risk (§21).

**Network:** Monad Testnet, chain ID 10143, full Ethereum RPC compatibility, opcodes as of the Fusaka fork, 300 ms block time / 600 ms finality (docs.monad.xyz, checked 2026-10-13).

**On-chain:** rental agreement terms, escrow custody, per-slot uptime records, settlement/payout logic, challenge window, objection flags, full event history.

**Off-chain:** actual GPU workload execution (mocked), the demo node's health endpoint, the oracle service and its reporter keys, frontend/indexer.

**Wallet interaction:** standard EVM wallet (e.g. MetaMask-class) added to Monad Testnet via chain ID 10143 + public RPC; no custom wallet integration required.

**Testnet:** Monad Testnet (chain ID 10143), faucet at faucet.monad.xyz, RPC at testnet-rpc.monad.xyz.

**Gas/cost considerations:** per-tx gas limit 30M, block limit 150M, min base fee 100 MON-gwei (docs.monad.xyz/developer-essentials/summary, checked 2026-10-13). The gas-pricing page's base-fee section still says "target = 160M" (80% of the old 200M), while the summary says 120M — another stale value not to quote. Since MIP-8 (testnet 2026-08-12) storage is warmed in 128-slot pages, so keeping one rental's fields together in one struct is cheaper (implementation detail; `docs/source/metropolis-notlari/06-monad-teknik.md`).

**External protocol dependencies — explicitly none.** Chainlink Automation/Functions are not listed for Monad and are deprecated (§4); UMA's Optimistic Oracle was confirmed absent from its supported-network list (rev 2026-09-27). Chainlink CRE does list Monad Testnet (§4) but is not used in the hackathon in any form (D-10); it is a Post-Hackathon option (§25). All oracle and timeout logic here is purpose-built, not an integration with any of these. UMA's assert → window → default pattern is used only as a conceptual reference (§4, §11), never as an actual dependency — this must not be described as "built on UMA" or similar in any pitch material.

---

## 14. APIs & Integrations

| Integration | Purpose | Required for MVP | Source |
|---|---|---|---|
| Monad Testnet RPC | Contract deployment and calls | Yes | https://docs.monad.xyz/developer-essentials/testnet.md |
| Monad Faucet (plus third-party faucets) | Testnet MON for gas and escrow. Official per-request amount not found; Alchemy's faucet gives 1 MON per 24 h (research 2026-10-13) — see §21 funding risk | Yes | https://faucet.monad.xyz , https://www.alchemy.com/faucets/monad-testnet |
| Vyper 0.4.3 + titanoboa/pytest | Contract build and tests (D-03); Solidity toolchain only if the day-0 gate fails | Yes | https://docs.vyperlang.org/en/stable/release-notes.html , https://docs.monad.xyz/guides/evm-resources/other-languages/vyper |
| Python oracle service (web3.py, httpx) | Health probes and per-slot reports (D-02, D-04) | Yes | `docs/SPEC.md` §4 |
| Docker | Demo GPU-node stand-in exposing `/health` (D-04) | Yes | `docs/SPEC.md` §4 |
| Viem | Frontend-to-contract calls | Yes | https://docs.monad.xyz/developer-essentials/summary |
| EVM wallet (MetaMask-class) | User/renter/provider wallet, added via chain ID 10143 | Yes | https://docs.monad.xyz/tooling-and-infra/wallets/ |
| Monadscan / MonadVision | Block explorer for demo verification and source verification. MonadVision verifies through a Sourcify instance, Monadscan through an Etherscan-style API; neither page mentions Vyper, so Vyper verification is unverified until the day-0 gate (D-03) | No (nice-to-have for demo credibility; part of the day-0 gate) | https://docs.monad.xyz/tooling-and-infra/block-explorers |
| Chainlink CRE | Possible decentralized reporter layer (HTTP probe → DON consensus → on-chain write); lists Monad Testnet; deploy needs Chainlink approval, simulation does not | No — not used in the hackathon (D-10); Post-Hackathon option (§25) | https://docs.chain.link/cre/supported-networks |
| Envio (HyperIndex) | Possible indexer for the P2 event-history view; Metropolis "Best Use of Envio" bounty | No — open question (§23) | `docs/source/metropolis-notlari/05-sponsor-notlari.md` |
| Chainlink Automation/Functions / UMA Optimistic Oracle | Would provide decentralized triggering/adjudication | No — unavailable on Monad; Automation and Functions deprecated (§4) | https://docs.chain.link/chainlink-automation/overview/supported-networks , https://docs.uma.xyz/resources/network-addresses |

---

## 15. Security Considerations

Hackathon-scope disclosure, not a production audit. Each item states the MVP's actual behavior, not an idealized one.

- **Unauthorized withdrawal:** `finalize()` credits only the fixed, agreement-time-set payee (renter or provider), and `withdraw()` pays only the caller's own credited balance (D-01) — no function allows an arbitrary address to redirect payout. The caller of `finalize()` gains nothing by calling it (§9).
- **Double settlement / double refund:** guarded by the status enum — `settle()` requires `Active`, transitions to `Proposed`; `finalize()` requires `Proposed`, transitions to `Settled`. Each transition is one-way and each function is callable at most once per rental.
- **Report replay:** closed by the one-report-per-slot rule (§9.3) — an old submitted report cannot be reused for a new slot.
- **Stale / running / future-timestamped reports:** closed by the slot-completion rule in §9.2/§9.3 — a report is only valid for a slot that has already completed (`block.timestamp ≥ start + (k+1)·interval`); a report for a currently-running or future slot reverts.
- **Settlement before reporting closes:** `settle()` requires `block.timestamp > end + REPORT_GRACE` and reverts otherwise, including at exactly `end + REPORT_GRACE`, the last instant at which reports are accepted (§9.2).
- **Provider consent (MVP simplification):** only the renter signs creation, so a rental may name a provider who never agreed to it on-chain. Terms are assumed agreed off-chain (§6). The named provider cannot lose funds this way — only the renter's funds are escrowed — but the on-chain record proves the renter's commitment only, not mutual agreement. The limitation is stated proactively in the demo narration, and a non-gating `provider_ack` event is a Could-Have (D-07); a gating provider-accept step is Future scope (§25). **(Decision)** `renter == provider` is rejected at creation: otherwise the payout and objection roles collapse into one address and settlement demonstrates nothing.
- **Far-future or long rentals (bounded, D-12):** creation rejects a `start` more than 30 days ahead and an `interval` above one day, so with at most 256 slots a rental ends at most 286 days after creation and always becomes settleable (the reason for the bounds is in D-12). Remaining limitation: there is still no cancel path, so a renter's own escrow stays locked until the rental has ended and been settled and finalized — at the earliest 286 days plus the grace and challenge periods for the longest rental, and longer if nobody calls `settle()`/`finalize()` (§9.5). Nobody else's funds are affected. A pre-start cancel is Future scope (§25).
- **Settlement after expiry:** not a distinct risk — `settle()` remains callable any time after `end + REPORT_GRACE` (no expiry on the ability to call it), so a late call still succeeds and produces the same fixed result (§9.4).
- **Objection after the challenge window closes, or after finalization:** `raiseObjection()` requires status = `Proposed` and `block.timestamp < proposedAt + CHALLENGE_WINDOW` (§11); it reverts once the window has closed, and a fortiori once `finalize()` has run (status = `Settled`).
- **Dispute (objection) griefing:** free and unbonded in the MVP (§11) — accepted as a disclosed limitation; a bonded objection is a Could-Have mitigation (§8), not implemented in the MVP.
- **Reporter key compromise:** see §10 — compromise of **any one** reporter key allows false reports for any rental; no mitigation beyond key hygiene at hackathon scope (D-02).
- **Reporter gas griefing (known limitation, D-11):** creating a rental is open to anyone and costs as little as 1 wei, so a stranger could create many rentals with many short slots to make the oracle pay gas for reports — on Monad gas is charged on the gas limit (§13). The contract does not prevent this. The protection is in the oracle service: it reports only rentals from allow-listed renters and caps the report transactions per rental (§10). The cost of the protection is a second gate on who is served (the service already ignores rentals whose provider has no configured node): a rental from a renter outside the list is never reported and refunds its renter, whatever the node did. An allow-listed renter can still spend up to the budget of each rental it creates.
- **Stuck funds:** possible if nobody ever calls `settle()`/`finalize()` (§9.5) — a known liveness limitation, not solved with a keeper-incentive mechanism in the MVP. A recipient that rejects native MON can no longer lock a rental: `finalize()` makes no transfer, and such a recipient's own `withdraw()` fails without affecting `finalize()` or anyone else's balance (pull payment, D-01; this replaces the push-payment limitation of rev 2026-09-27). A payee that never withdraws leaves its own credit in the contract.
- **Reentrancy on payout:** `finalize()` sets status to `Settled` and makes no external call (D-01). `withdraw()` zeroes the caller's credit before transferring and is guarded against reentrancy, so a reentrant call finds nothing to withdraw.
- **Zero/invalid duration or threshold:** rejected at creation time per the acceptance criteria in §7 (all revert conditions listed there).
- **Incorrect payment amount:** the escrowed amount is exactly the `msg.value` sent at creation (D-05) and is not separately settable elsewhere in the contract.
- **Renter/provider role confusion:** both addresses are fixed at agreement creation and are not reassignable by any function.
- **Wallet/frontend risk:** standard EVM wallet-connect risks (phishing, malicious contract approval) apply; mitigated by verified contract source and standard wallet UX — no custom handling needed at hackathon scale.
- **Financial risk:** MVP uses testnet MON only — no real financial exposure. This must remain explicit in the demo; do not imply real-money readiness.

---

## 16. Legal / Regulatory Considerations

Not deeply researched (out of scope for a hackathon-stage assessment); flagging only what's evident:
- If this ever moves to real funds, escrowed-payment-with-automatic-payout mechanics may raise money-transmission or custody questions depending on jurisdiction — requires professional legal review before any production use.
- No KYC/AML flow is proposed or needed for the hackathon MVP (testnet-only, no real-value transfer).
- This PRD makes no legal claims and no legal conclusions; the above are flags for future review, not advice.

---

## 17. Business Model & Adoption Path (Hypothesis — not validated)

The product is currently defined as a payment/escrow *primitive*, not a marketplace. This section asks the adoption questions directly rather than assuming an adoption path exists.

- **Who is the first user?** Unknown / not validated. Candidate wedges, none tested: (a) a pair of individuals (a renter and a provider) who already trust each other's hardware/need but want a neutral payout rule instead of informal trust; (b) a marketplace or broker who integrates this as an optional payment rail for a subset of listings; (c) **speculation (research 2026-10-13):** small hosts selling directly without a platform to vouch for them; (d) **speculation:** agent-to-agent compute purchases, which today pay first with no documented remedy (e.g. io.net Agent Cloud enabled x402 payments on 2026-06-24 with no escrow or SLA described); (e) **speculation:** DePIN networks whose on-chain escrow has no downtime rule (Akash, §4). No public post explicitly asking for a third-party or on-chain SLA arbiter for compute was found.
- **Why would a renter use this directly instead of an existing marketplace?** Not established by any evidence gathered — this PRD does not assert a reason beyond the auditability claim in §13, which is itself unvalidated as something users want enough to switch for (§22).
- **Why would a provider use this?** Same caveat. Public host reviews complain that a platform's verification is "opaque and arbitrary" and that restarts for security patches lower the reliability score (§2), which suggests a published rule could matter to hosts — but these are self-selected reviews, not evidence that providers would switch.
- **Why would an existing marketplace (vast.ai, RunPod, etc.) adopt this?** Doing so would mean voluntarily giving up their own internal arbitration authority to a rule they don't control. No evidence was found that any marketplace has an incentive to do this, and it directly conflicts with their current business model (private scoring as a value-add / lock-in mechanism). This is flagged as a significant, unresolved adoption barrier, not a solved problem.
- **What is the friction to use this instead of native billing?** Requires both parties to hold a Monad-compatible wallet, fund it, and trust a smart contract instead of an established platform's payment processing — a real, non-trivial switching cost that this PRD does not claim to have a mitigation for.
- **First adoption wedge:** left as an explicit open question (§23), not invented. The pitch presents "who would actually use this" as the largest open question, not as a solved go-to-market plan (D-08). Before the demo the team interviews 3–5 people at 42 who rent GPUs (D-08, §24); one real quote is worth more than an invented market story. The Metropolis organizers' advice points the same way: start from the uncomfortable question of why the ideal customer would *not* use the product (`docs/source/metropolis-notlari/03-fikirden-urune.md`).

---

## 18. Differentiation

- **What is different (MVP-accurate claim):** the settlement rule and the oracle's reported uptime history are on-chain, inspectable by any party, and triggerable by any party — versus every researched competitor's verification and settlement being run by the platform itself (vast.ai's DLPerf/uptime scoring is private and non-portable; TensorDock's quorum-monitored compensation rule is published but TensorDock runs the monitors and the settlement; CoreWeave decides from its own logs, §4). This is a claim about auditable record-keeping and permissionless triggering, not about independent verification of ground truth (§13) — the MVP's trust root for the data itself is functionally comparable to vast.ai's (one party's word), just made public rather than private.
- **What problem the difference addresses:** the gap described in §2 (Problem A) — no independently auditable, per-rental settlement record was found in the researched public documentation of vast.ai, RunPod, Lambda, CoreWeave, TensorDock, Compute Exchange or SF Compute; Aethir documents SLA-conditional payment, but its public docs show no on-chain per-rental record or permissionless settlement (§4, unverified either way); Spheron and Fluence slash providers on-chain but do not settle a renter's payment per rental; Akash's per-lease escrow is on-chain but not uptime-conditional. Nosana and Golem were not researched in full, so this claim is scoped to what was actually checked, not to "every platform."
- **Why it matters (with the honest caveat):** only if users value a public, tamper-evident record and permissionless triggering enough to accept a team-held-reporter (single trust root) model in exchange — an unvalidated preference (§17, §22).
- **Explicit non-claim:** this PRD does not claim to be first, unique, or first to make GPU payment conditional on measured uptime. Aethir already documents Checker-based uptime monitoring, uptime-tiered fee penalties, withheld fees for disrupted periods, and a tenant compensation pool (§4, Verified). The narrower difference is *where the record and settlement live*: a per-rental uptime record on a public chain, a `settle()` anyone can call, and a challenge window — none of which were found in Aethir's public docs (Unverified absence). Pitch it as "Aethir does SLA-conditional payment inside its own platform; this makes the record and settlement public and permissionlessly triggerable" — never as "no one else does this." Note also that Aethir's Checkers are independent of the host and TensorDock uses a quorum of four monitors, while this MVP's reporters are team-controlled keys (§10) — on the verification layer, both are ahead.
- **Closest pattern to cite honestly:** Chainlink Staking v0.2's feed-downtime alert is deployed, on-chain, permissionlessly triggered liveness enforcement (§4) — for oracle feeds, where liveness is checkable on-chain. This product applies the permissionless-trigger idea to compute rentals, where liveness is not checkable on-chain and must be reported.

---

## 19. Success Criteria

- The full journey (§6) can be completed end-to-end on Monad Testnet: renter/provider/oracle each act in their own defined role (agreement creation and escrow by the renter, uptime reports by reporter-set addresses only, withdrawal by the credited payee) — while `settle()` and `finalize()` specifically are callable by any wallet, not only the renter, provider, or oracle. This distinction (fixed roles for creation/reporting, no role restriction for settlement triggering) is the precise scope of "permissionless" in this product (§1).
- Stopping the demo node with `docker stop` for at least two slots (with the §20 parameters) makes those slots "down" through the real health probe and changes the proposed outcome to a renter refund at `settle()` time (D-04); the force-down control produces the same result if Docker fails.
- The fully compliant run (§20 step 9) ends with the provider credited and able to withdraw the full price; with the §20 parameters it still passes if any one report is lost.
- After `finalize()`, the payee's `withdraw()` transfers exactly the credited amount, and a second `withdraw()` reverts (D-01).
- Reports for two different rentals are sent from two different reporter keys and land in the same block, visible on the explorer as two senders (D-02).
- A third wallet, unconnected to either the renter or provider, can successfully call `settle()`/`finalize()` — demonstrating the permissionless-triggering claim concretely, not just narrating it.
- The objection log can be demonstrated: `raiseObjection()` emits a visible event and is shown to have zero effect on the payout that `finalize()` credits.
- All key transactions (agreement creation, reporting, settlement proposal, objection, finalization, withdrawal) are visible and verifiable on a Monad block explorer during the demo.
- Demo is repeatable without manual contract redeployment between runs (fresh agreement IDs per run).

---

## 20. Demo Scenario

**Demo parameters (Decision):**
- `interval` = 30 s, `N` = 4, so the rental lasts 120 s.
- `threshold` = 75.
- `REPORT_GRACE` = 30 s and `CHALLENGE_WINDOW` = 60 s (contract constants, §9.2, §11).
- `start` = submit time + ~15 s, a buffer so `start ≥ block.timestamp` holds when the creation transaction executes.
- `price` = 0.01 testnet MON (no semantic role in the demo; kept small to lower faucet/reserve-balance funding needs, §22).

**Where it runs (D-10):** the Docker health-probe nodes (D-04) run on the team's WSL machine, for the live demo and for every rehearsal or simulation of it; the oracle service runs on the same machine (`docs/UI_HANDOFF.md` §7). Chainlink CRE is not part of the demo in any form.

**Provider nodes (D-13):** both demo provider addresses must be mapped to their nodes in the service's configuration before the rentals are created; a missing or mistyped address means no reports and a refund, with only a log line as warning.

**Renter allow-list (D-11):** the demo renter wallet must be on the oracle service's allow-list before step 2, or the rental gets no reports and refunds. A rental created from any other wallet during the demo (a judge's, for example) is not reported.

**Same `start` for both runs (consequence of D-02):** to show two rentals' reports from two keys in the same block, the compliant and non-compliant agreements are created with the same `start`, so their slots complete together, and with rental IDs that map to different keys.

**Separate nodes (consequence of D-04):** the oracle maps each provider address to one node, so the compliant run and the non-compliant run must use different provider addresses mapped to different containers if they overlap in time — otherwise `docker stop` would fail both runs.

**Arithmetic (compliance is `100×M ≥ 75×4 = 300`, §9.4):**
- **Compliant run:** all four slots reported up → `M = 4`, 400 ≥ 300, pass. If any one report is lost, `M = 3`, 300 ≥ 300, still a pass (boundary case). It fails only if two or more reports are lost.
- **Non-compliant run:** the node is stopped for at least two slots → `M ≤ 2`, 200 < 300, fail — and it still fails if an "up" report is also lost. One down slot would not be enough (300 ≥ 300 passes), which is why the demo stops the node for **two or more** slots. Because a slot is "up" only if at least one probe ran in it and every probe that ran succeeded (§10, D-04), a stop that starts mid-slot also makes that slot "down".

**Wall-clock per run:** ~15 s + 120 s + 30 s + 60 s ≈ 3.75 min, plus transaction latency and the payee's `withdraw()` — roughly 4 min. Two sequential runs ≈ 8–9 min; if the run-2 agreement is created right after run 1's, both overlap and total ≈ 5 min. **Load:** 8 oracle transactions over ~2 min, far below the public RPC's rate limit (§13).

```text
1. Open frontend, connect wallet (Monad Testnet)
2. Create a rental agreement: set price (sent as MON in the same transaction, §5), uptime threshold, duration, interval; escrow deposit executes
3. Oracle service probes the node's /health and posts a report for each slot once it completes (§9.2)
   — show the probe log and the reports arriving on-chain, two rentals reported by two different
   reporter keys in the same block (D-02)
4. Run `docker stop` on the node for at least two slots (backup: the force-down control, D-04)
   Narrate explicitly here: "The health check is real, but the node is our container, not a GPU,
   and the reporters are our own keys — that is the trusted part. Everything after this point —
   the computation, the payout decision, who can trigger it — is real and runs the same way
   regardless of who submitted the report."
   Also say first, before a judge asks: "Only the renter signs the agreement on-chain; the
   provider's consent is off-chain in this MVP." (D-07)
5. Strictly after end + REPORT_GRACE, have a THIRD, unrelated wallet (not renter, not provider) call settle() —
   this is the concrete demonstration of "permissionless": nobody needed permission to trigger it
6. Show the proposed outcome reflects the reduced uptime % correctly
7. Call raiseObjection() from the renter or provider wallet — show the event fires
   Narrate: "This records disagreement publicly. It does not change what happens next."
8. After the challenge window closes, the third wallet calls finalize() — show the credited
   payout matches the step-6 proposal exactly, regardless of the objection in step 7; then the
   payee (the renter here) calls withdraw() and receives the MON (D-01)
9. A fully compliant agreement with the same parameters, created right after step 2 with the same
   `start` and a different provider/node (or re-run afterwards); after end + REPORT_GRACE call settle(), then after CHALLENGE_WINDOW call
   finalize(), and the provider calls withdraw() to receive full payment, for contrast — the payout
   still requires these explicit calls, it does not happen on its own
10. Explain architecture: what's real (contract, escrow, settlement/finalization/withdrawal logic,
    permissionless triggering, the health probe, Monad Testnet execution) vs mocked or trusted (GPU
    hardware and workload, the container standing in for a GPU node, team-held reporter keys
    standing in for a future independent reporter set). Pitch line: "We removed the nonce
    bottleneck; the source of trust is still one team." (D-02)
```

**Fallback demo path (if frontend slips):** the same sequence driven via `cast`/Viem/web3.py script calls directly against the deployed contract, narrated over a Monad block explorer showing each transaction and event as it lands. This keeps the on-chain core of the demo intact even if the UI is incomplete.

---

## 21. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Team-held reporter keys mean the data itself is not independently verified, only the settlement rule is auditable; several keys do not change this (D-02) | Demo credibility — a technically literate judge will probe exactly this | Disclose explicitly and precisely in demo narration (§20) and throughout this PRD (§10, §13); never describe the oracle as trustless or decentralized; never claim a parallel-execution speedup from multiple keys (§10, §13) |
| "Timeout finality" could be mistaken for real dispute resolution if described loosely | Overclaiming risk if pitch language drifts from this PRD's terminology (§11) | Use "non-binding objection log" / "timeout finality," not "dispute resolution," consistently in all pitch material |
| No physical GPU / no real provider (cold-start marketplace problem) | Cannot demonstrate a real two-sided market | Scope demo entirely around the escrow/settlement primitive, not a live marketplace; explicitly out of scope for hackathon (§8) |
| No adoption path has been validated for why a marketplace or user would switch (§17) | Weak answer if a judge asks "who would actually use this"; Metropolis judges weigh a real user and continued use (`01-metropolis-nedir.md`) | Present it as the largest open question (D-08); interview 3–5 people at 42 who rent GPUs before the demo (§24) |
| No Automation/UMA-class service on Monad; Chainlink CRE is available but not adopted | Cannot reuse audited infra for settlement triggering or timeout logic in the MVP | Build the permissionless-trigger and timeout mechanism in-house; documented as a deliberate, disclosed simplification (§12, §13); CRE is a Post-Hackathon option only (D-10, §25) |
| Overclaiming novelty vs Aethir/TensorDock/vast.ai | Credibility risk if challenged by a judge who knows the space — Aethir documents uptime-conditional fee withholding and tenant compensation; TensorDock publishes a quorum-monitored compensation rule (§4) | Use the explicit non-claim in §18; never state or imply "no one else does this" or "first SLA-conditional GPU payment"; claim only the narrower public-record / permissionless-settlement difference |
| No Monad-specific product reason: §13 claims no technical superiority, and D-02 deliberately claims no parallel-execution speedup, while Metropolis judges ask for a product reason to be on Monad (`01-metropolis-nedir.md`) and the review warned that "low cost + fast finality" applies to any EVM L2 | A judging criterion currently has no strong answer | State it honestly rather than invent one; candidate answers (proposals, §23): cheap, fast per-slot writes make 30-second settlement slots affordable; separate keys with separate gas budgets under the reserve-balance rule. Owner to choose |
| Smart contract bug in escrow/settlement/finalization/withdrawal logic | Demo failure, fund lock during live demo | Use testnet-only funds; test the full `settle()`/`raiseObjection()`/`finalize()`/`withdraw()` sequence before demo; keep the demo path narrow and pre-tested |
| Vyper does not compile, deploy or verify cleanly on Monad (Monad's Vyper page is generic, with no Monad-specific deploy or verify steps; explorer Vyper support unconfirmed, §14) | Lost days late in the hackathon | Day-0 gate: a minimal Vyper contract must deploy, emit an event and verify; switch to Solidity with the same spec and ABI names if not fixed in ~2 h (D-03) |
| A Monad number in the pitch is stale or wrong (several Monad pages and the Metropolis notes still show 400 ms / 800 ms / 200M) | "They did not research" impression; judges may quote the older numbers from Monad's own pages | Quote every number with source URL and check date; re-check on demo day; measure block time with the smoke test (D-06); prepare a one-line answer: "Monad moved from 400 ms to 300 ms blocks in the July 2026 release; some pages still show the old value." |
| Market-size and competitor claims rely on partial research; market-size sources disagree by ~2× | Weak claims if fact-checked live | Cite sources with explicit evidence-level labels throughout (§2, §4); never state an unverified figure as fact; quote market size as a range from named sources or not at all |
| Objection griefing (free, unbonded) | Could be raised to appear as if there's a real dispute, even though it has zero effect | Demo explicitly shows the objection has no effect on payout (§20 step 7–8), preempting the misreading rather than hiding it |
| The oracle service is the only reporting process — a demo-day operational risk, distinct from the design-level trust-centralization risk above | If the service or Docker fails live, the demo blocks | Rehearse the exact demo transactions beforehand; keep the service and keys on a tested, reliable machine — the team's WSL machine, which also hosts the node containers (D-10), so that one host is a single point of failure for both runs: a sleeping or stalled host means no probes, and slots with no probe are reported "down" (§10); keep the machine awake during runs, and the recorded backup video is the only cover for host failure; force-down control as backup for Docker (D-04); keep every reporter key funded and monitored — each rental is reported from one fixed key (SPEC R-2, H-4), so an empty key stops its rentals' reports and there is no automatic failover to another key; have transaction hashes pre-recorded as backup narration. `REPORT_GRACE` (§9.2) and the demo threshold (§20) mean one lost report cannot flip the compliant run |
| Anyone can create rentals that name a served provider and make the oracle pay for reports (creation is permissionless and cheap; gas is charged on the limit) | Reporter keys drained; long report queues could make the service miss probes or reports for honest rentals | The service reports only rentals from allow-listed renters and caps report transactions per rental (D-11, §10); the demo renter wallets must be on the list before the run; with the demo's `N` = 4 the service can re-send only four times per rental, so a transaction stuck for more than about a minute can leave slots unreported — fallback: send the missing report by hand from a reporter key, which the contract accepts (§9.3); disclosed as a limitation (§15): rentals from other renters are not reported and refund the renter |
| Not enough testnet MON: the renter's payable creation call must leave ≥10 MON (or qualify as an "emptying" transaction) under the reserve-balance rule, while third-party faucets give about 1 MON per 12–24 h (§13, §14) | Creation reverts on stage | Measure faucet amounts on day 0; start funding the renter wallet in week 1, since >10 MON at ~1 MON/day takes weeks (social-account boosts on the official faucet, several faucets); rehearse creation from the actual demo wallet; deployer may double as the third wallet. The demo needs two provider addresses (one per node, §20) in addition to renter, third wallet and reporter keys |
| Monad Testnet unavailable/reset on demo day | Demo depends entirely on one external testnet being up; the testnet has been reset from genesis before (2025-12-16, §13) | Deploy well before demo day and re-verify (and redeploy if needed) shortly before; keep a recorded backup demo video as a last resort |
| Stuck funds if nobody ever calls settle()/finalize() (§9.5) | Known liveness limitation, unmitigated in the MVP | Documented (§9.5, §15); for the demo, the team itself can always call these functions since they are permissionless. The earlier risk of a rejecting recipient locking `finalize()` is removed by pull payment (D-01) |

---

## 22. Assumptions

- That auditable, permissionlessly-triggerable settlement is something renters/providers would value enough to accept a team-held-reporter (single trust root) model and switching costs (§17) — unvalidated; public reviews show the pain exists (§2), not that users would switch.
- That no researched network has an equivalent per-rental, permissionlessly settled SLA record — Akash, io.net, Spheron and Fluence were checked on 2026-10-13 (§4); Nosana and Golem only partially. Plausible, not confirmed.
- That a fixed, unrotatable set of team-held reporter keys (D-02) is an acceptable MVP simplification for a hackathon demo — reasonable for a demo, but this PRD is explicit that it must never be described as trustless or decentralized in pitch material (§1, §10).
- That the "missing report counts as down" policy (§9) is an acceptable default — it favors renters and has not been validated against provider expectations.
- Reserve balance (research 2026-10-13, §13): reporter, `settle()` and `finalize()` transactions send no value, so only the gas-budget part of the rule applies to them. The renter's payable creation call is a value spend: it reverts unless the renter keeps ≥10 MON afterwards or the call qualifies as an "emptying" transaction. Assumption: the renter wallet can be funded to that level, or the emptying exception reliably applies in the demo — rehearse it. Unverified: whether the rule applies to the escrow contract's own balance when `withdraw()` pays out; whether faucets give enough MON (third-party faucets give about 1 MON per 12–24 h; the official faucet's amount was not found) — measure on day 0 (§21).
- That Vyper 0.4.3 (default EVM target Prague) compiles to bytecode Monad accepts ("all opcodes as of the Fusaka fork are supported") and that a Monad explorer can verify Vyper source — an inference with no Vyper-on-Monad example found; decided by the day-0 gate (D-03).
- That `REPORT_GRACE` = 30 s is enough for the oracle's last report to land on the public RPC — not measured; validate during demo rehearsal (§8.1).
- That the demo node's `/health` endpoint is a fair stand-in for GPU-node liveness — it shows reachability of an endpoint, not that GPU work was done (§10, D-04).
- That GPU-as-a-Service market-size figures are roughly accurate — three estimates disagree (about $4.4B–$8.2B for 2025, §2); context only.

---

## 23. Open Questions

- Does an on-chain settlement record actually solve a problem users can't already solve by choosing a higher-priced, reputationally-vetted provider (CoreWeave/Lambda)? This is the core validity question for the whole idea and remains open.
- Do Nosana or Golem (only partly researched) already have an equivalent SLA-record/settlement mechanism? Akash, io.net, Spheron and Fluence were checked on 2026-10-13 and none showed a per-rental, permissionlessly settled record (§4).
- Does Aethir record Checker results or per-order settlement on-chain in a form a tenant can independently audit, and can a tenant dispute a result? Its public docs confirm Aethir-operated uptime checks and SLA-based fee withholding/compensation (§4); the whitepaper calls blockchain the settlement layer but names no contract or event, and only the host has a documented appeal. The answer decides whether the §18 differentiation holds.
- Who is the realistic first adopter, and what specifically would make them switch from native marketplace billing (§17)? Not answered by this research.
- Would real GPU node operators (not the author) be willing to accept team-controlled reporters attesting their uptime, in a post-hackathon version? Plausible objection: providers may distrust a renter-side-adjacent oracle as much as they currently distrust nothing in particular (today there's no third-party attestor at all).
- Is the "missing report = down" default (§9) the right one, or should it default to "up" (favoring providers) or require a minimum report count before any settlement is valid?
- **Monad product reason (review 2026-10-13):** judges ask why this is on Monad (§21). Candidate answers, none decided: cheap and fast per-slot writes make short settlement slots affordable; separate reporter keys with separate gas budgets. Or state openly that the design is chain-agnostic and Monad is the target chain.
- **Envio for the event-history view (proposal):** the P2 history view (§7) could be built on an Envio HyperIndex indexer of the contract's events ("Best Use of Envio" bounty, $1,000). Options: build it, keep the P2 view on direct RPC reads, or cut it (§8.1 cut order). The Metropolis notes' deletion test applies: a sponsor integration counts only if removing it breaks the product (`01-metropolis-nedir.md`).
- **Slot time base:** slots are defined on `block.timestamp` (seconds, 3–4 blocks share one value). Block numbers are finer, but Monad's block time changed twice in 2026 (§13). Keeping seconds is the current design; raised by research, not a change request.
- **Which competitors the pitch names:** research found more comparison points than the pitch can carry — Aethir, TensorDock, Spheron/Fluence, Akash, Chainlink Staking v0.2, Compute Exchange (§4). Which to show is the owner's call.
- **Recurring problem and usage interval (Metropolis judging):** judges look for a problem users return to and an active-user loop (`03-fikirden-urune.md`). Is a GPU rental a repeated interaction for the target user, and at what interval (per job, weekly)? Not answered; ask in the D-08 interviews.
- **Agent-to-agent compute purchases as a wedge (speculation):** x402-paid compute (e.g. io.net Agent Cloud) pays first with no documented remedy (§17). Worth one validation conversation; no evidence of demand yet.

---

## 24. Validation Plan

| Hypothesis | Validation Method | Expected Evidence | Success Condition |
|---|---|---|---|
| Renters/providers would value an auditable, permissionlessly-triggerable settlement record over a platform's private score | **Before the demo:** short interviews with 3–5 people at 42 who rent GPUs (D-08). After the hackathon: 5–10 ML developers and/or GPU hosts who've used vast.ai/RunPod, about their experience with SLA/refund handling. If no one at 42 rents GPUs, fall back to hosts and renters reached through public reviews and communities (§2) | Qualitative reports of frustration with current dispute handling, or explicit stated preference for an auditable rule | At least half describe a real incident or express a clear preference |
| A team-held-reporter MVP, described with this PRD's precise terminology, reads as honest rather than overclaiming to a technical audience | Present the demo narration (§20) to a test audience (e.g. a technical friend) before the actual demo | Feedback on whether "permissionless triggering, not trustless verification" lands clearly | No reviewer describes the framing as misleading |
| Aethir lacks a public, permissionless, per-rental on-chain SLA record/settlement. **Status: partially verified** — SLA-conditional payment exists (Verified, §4); the 2024 whitepaper names no contract or event for settlement (research 2026-10-13); on-chain recording and permissionless settlement still Unverified | Read the Aethir whitepaper and contracts (staking, Checker license NFT); ask Aethir directly whether Checker results or settlements are posted on-chain | Contract addresses and events, or an explicit statement | Confirmed absence of on-chain per-rental records and permissionless settlement (if present, §18 differentiation collapses and must be rewritten) |
| Other decentralized GPU networks lack this settlement mechanism (Akash, io.net, Spheron, Fluence checked 2026-10-13; Nosana, Golem open) | Deeper doc-diving into their technical/whitepaper docs, or direct outreach | Confirmed presence or absence of an equivalent mechanism | Clear yes/no answer replacing the current "unverified" status |
| A realistic first-adopter wedge exists (§17) | Informal conversation with 2–3 people who currently rent or provide GPUs on marketplaces (can overlap with the D-08 interviews), asking directly whether they'd route a rental through a third-party escrow contract | Direct answers about willingness and stated reasons | At least one concrete, non-hypothetical "yes, if X" response |

---

## 25. Future Roadmap

### Hackathon MVP
- Escrow + slot-indexed uptime record + permissionless `settle()`/`finalize()` + pull-payment `withdraw()` contract on Monad Testnet (D-01).
- Team-operated oracle service with a real health probe of a Docker node, reporting from a fixed set of team-held keys, with a force-down backup (D-02, D-04).
- Fixed challenge window with a non-binding objection log (§11).
- Minimal frontend covering the full core journey, with a scripted CLI fallback.

### Post-Hackathon
- Reporters run by independent parties (staked reporter set, or a decentralized oracle network such as a Chainlink CRE workflow), replacing the team-held keys (§8, §10). CRE is an option here only: it is not used in the hackathon, neither as the reporter nor as a simulation demo (D-10). Known points if it is taken up (§4): a CRE workflow can probe the health endpoint from every node of a DON, reach consensus and write through Chainlink's forwarder; deploying needs Chainlink's approval; whether production deploy works on Monad Testnet is unconfirmed; and the forwarder calls a report-receiving function, not `report_uptime`, so the contract needs a new entry point and an interface change.
- On-chain per-rental reporter scoping, and reporter rotation (D-02 fixes the set at deployment).
- Real GPU provider onboarding and node-agent software.
- TEE-based (NVIDIA Confidential Computing) or other cryptographic proof of actual GPU work — future work contingent on the team obtaining qualifying hardware and validating the approach, not a claim that this is infeasible for others with the right hardware.
- Bonded objections, to make the objection log costlier to grief (§8, Could Have → possible Future default).
- A provider bond: today only the renter's money is escrowed and the provider posts no bond that could be slashed for missed uptime. A slashable provider bond is a possible later scope item; it is not part of the hackathon and not in any decision beyond this note (D-09).
- A real adjudication layer (human, DAO-vote, or an audited optimistic-oracle protocol if one reaches Monad) — the MVP's objection log is explicitly not this.
- A performance-score metric alongside uptime (§9.4). (Proportional refund stays a §8 Should-Have; it moves here only if not delivered at the hackathon.)
- On-chain provider acceptance that gates agreements (beyond the Could-Have non-gating `provider_ack` event, D-07) and a pre-start cancel (§15; the start-delay bound is in the MVP since D-12).
- A keeper incentive so `settle()`/`finalize()` are called even if no party acts (§9.5).
- Per-provider on-chain history across multiple rentals.
- Legal/regulatory review if real funds are ever handled (§16).
- Concrete adoption-wedge validation (§17, §24) before any go-to-market claim is made.

---

## 26. Research Sources

- https://docs.monad.xyz (EVM compatibility, mainnet/testnet, performance)
- https://docs.monad.xyz/developer-essentials/testnet.md (testnet chain ID, RPC, faucet)
- https://docs.monad.xyz/developer-essentials/gas-pricing.md / opcode-pricing.md (gas model)
- https://docs.monad.xyz/developer-essentials/summary (tooling, wallets)
- https://docs.monad.xyz/tooling-and-infra/oracles.md (oracle providers on Monad)
- https://docs.chain.link/chainlink-automation/overview/supported-networks (Monad absent)
- https://docs.uma.xyz/resources/network-addresses (Monad absent)
- https://developer.nvidia.com/blog/confidential-computing-on-h100-gpus-for-secure-and-trustworthy-ai/ (TEE feasibility)
- https://docs.vast.ai/host/understanding-verification.md (vast.ai proprietary verification)
- https://www.runpod.io/pricing
- https://lambda.ai/service/gpu-cloud
- https://www.coreweave.com/pricing
- https://cloud-gpus.com/
- https://akash.network/docs/getting-started/core-concepts
- https://io.net/docs , https://io.net/
- https://learn.nosana.com/
- https://docs.golem.network/
- https://docs.aethir.com/
- https://docs.aethir.com/checker-guide/what-is-the-checker-node/how-do-checker-nodes-work.md
- https://docs.aethir.com/aethir-network/the-checker
- https://docs.aethir.com/aethir-network/the-checker/proof-of-capacity-and-delivery
- https://docs.aethir.com/aethir-cloud/aethir-cloud-host/operational-requirements-for-cloud-hosts/slashing-mechanism.md
- https://docs.aethir.com/aethir-cloud/aethir-cloud-host/rewards-and-service-fees-for-cloud-hosts/service-fees-for-cloud-host
- https://docs.monad.xyz/developer-essentials/summary (TIMESTAMP granularity, 300 ms blocks, finality)
- https://docs.monad.xyz/developer-essentials/gas-pricing (gas charged on gas limit, min base fee)
- https://docs.monad.xyz/developer-essentials/reserve-balance
- https://docs.monad.xyz/developer-essentials/testnets (testnet reset 2025-12-16)
- https://docs.monad.xyz/monad-arch/consensus/monad-bft
- https://docs.chain.link/data-feeds
- https://www.precedenceresearch.com/gpu-as-a-service-market
- https://hn.algolia.com/api/v1/search?query=vast.ai&tags=comment

### Added in revision 2026-10-13 (research pass; sourced, not independently re-verified)

Project sources (in this repository):
- `docs/DECISIONS.md` (D-01..D-08), `docs/SPEC.md` (§3, §4, §7, §8, §9), `docs/PLAN.md` (§1), `docs/REVIEW_2026-10-01.txt`, `docs/idea.md`
- `docs/source/metropolis-notlari/` — Metropolis notes: format and judging (`01-metropolis-nedir.md`), tracks and bounties (`02-trackler-ve-bountyler.md`), product validation (`03-fikirden-urune.md`), sponsor notes incl. Chainlink CRE, Envio, Tenderly (`05-sponsor-notlari.md`), Monad technical notes (`06-monad-teknik.md`), resources page copy (`ek/resources-sayfasi.md`). Note: their Monad numbers (400 ms / 800 ms) are stale (§13).

Monad:
- https://docs.monad.xyz/introduction/monad-for-developers (300 ms blocks, 600 ms finality)
- https://docs.monad.xyz/developer-essentials/changelog/releases (v0.15.0: 400 → 300 ms, 200M → 150M; MIP-8 activation)
- https://docs.monad.xyz/monad-arch/execution/parallel-execution (optimistic parallel execution)
- https://docs.monad.xyz/guides/evm-resources/other-languages/vyper
- https://docs.monad.xyz/tooling-and-infra/block-explorers (MonadVision/Sourcify, Monadscan)
- https://docs.vyperlang.org/en/stable/release-notes.html (Vyper 0.4.3 default EVM target Prague)
- https://www.alchemy.com/faucets/monad-testnet , https://faucet.quicknode.com/monad/testnet

Chainlink:
- https://docs.chain.link/cre/supported-networks (Monad Testnet listed, modified 2026-09-18)
- https://docs.chain.link/cre/guides/workflow/using-evm-client/forwarder-directory
- https://docs.chain.link/cre/capabilities/http (DON consensus over HTTP requests)
- https://docs.chain.link/cre/account/deploy-access (deploy needs approval)
- https://chain.link/economics/staking , https://chain.link/blog/chainlink-staking-v0-2-overview (feed-downtime alert and slashing)

Platforms and terms:
- https://www.runpod.io/legal/terms-of-service , https://docs.runpod.io/accounts-billing/billing
- https://docs.vast.ai/guides/reference/billing , https://docs.vast.ai/host/verification-stages
- https://lambda.ai/legal/terms-of-service
- https://docs.coreweave.com/policies/terms-of-service
- https://docs.tensordock.com/legal-information/downtime-compensation , https://docs.tensordock.com/legal-information/supplier-hosting-agreement
- https://compute.exchange/compute-service-terms
- https://sfcompute.com/legal/sla
- https://www.cmegroup.com/content/dam/cmegroup/notices/ser/2026/08/ser-9785.pdf
- https://akash.network/docs/learn/core-concepts/providers-leases/
- https://io.net/docs/guides/staking/io-staking
- https://docs.spheron.network/providers/reward-details
- https://fluence.dev/docs/stake/overview
- https://docs.nosana.com/protocols/jobs.html
- https://docs.golem.network/docs/golem/payments
- https://www.gensyn.ai/research/verde-a-verification-system-for-machine-learning-over-untrusted-nodes
- https://resources.cryptocompare.com/asset-management/15242/1718610172883.pdf (Aethir whitepaper draft, 2024)

Users, prices, market:
- https://www.trustpilot.com/review/vast.ai?page=2 , https://www.trustpilot.com/review/vast.ai?page=4
- https://www.trustpilot.com/review/runpod.io , https://www.trustpilot.com/review/runpod.io?page=3
- https://getdeploying.com/gpus/nvidia-h100 (updated 2026-10-12)
- https://www.silicondata.com/products/silicon-index?gpu=h100
- https://www.marketsandmarkets.com/PressReleases/gpu-as-a-service.asp
- Grand View Research GPU-as-a-Service press release, 2026-06-11 (via PR Newswire syndication)
- https://ourcryptotalk.com/news/io-net-agent-cloud-stripe-x402-payments (io.net x402, 2026-06-24)

Prior art:
- https://pure.uva.nl/ws/files/42160225/Blockchain_based_Witness_Model.pdf (witness model for cloud SLA)
- https://arxiv.org/abs/2609.10704 (penalty-aware blockchain cloud monitoring, 2026)

---

## 27. Changelog (revision 2026-09-27)

| ID | Change | Section(s) |
|---|---|---|
| T1 | Replaced the `block.timestamp == end` last-slot rule with a fixed `REPORT_GRACE` constant: reports accepted while `≤ end + REPORT_GRACE`, `settle()` only `> end + REPORT_GRACE` (Decision + rationale, R1 evidence). Demo parameters chosen so the compliant run tolerates one lost report. | §5, §6, §7, §9.1, §9.2, §9.3, §9.4, §11, §12, §15, §19, §20, §21, §22 |
| T2 | Provider consent documented as MVP simplification; "tamper-proof agreement" claim weakened to "renter's terms recorded"; `renter == provider` and `provider == address(0)` rejected at creation. Provider-accept moved to Future. | §7, §8, §15, §25 |
| T3 | §12 threshold range corrected from 0–100% to 1–100 (0 rejected). | §12 |
| T4 | One objection per party (per-party flags, repeat reverts); unbounded `start` / no cancel documented as known limitation; "up" defined as a simulated liveness heartbeat. | §7, §9.2, §10, §12, §15, §25 |
| T5 | Concrete demo values (interval 30 s, N = 4, threshold 75, `REPORT_GRACE` 30 s, `CHALLENGE_WINDOW` 60 s), compliance arithmetic for both runs, ~4 min per run; demo now forces **two** slots down (one would still pass at 75%). | §6, §7, §8, §11, §19, §20 |
| T6 | Proportional refund kept as §8 Should-Have only; §25 lists it only as a fallback if not delivered. | §25 |
| R1 | Verified Monad `TIMESTAMP` is second-granularity, 3–4 blocks share a value, 300 ms blocks; fed into T1. | §9.2, §13, §26 |
| R2 | Added "Why Monad specifically?" — Monad is the target chain; no technical superiority claimed; documented properties and gotchas (gas on limit, reserve balance, testnet reset) listed. | §13, §21, §22, §26 |
| R3 | Aethir researched in depth: SLA-conditional payment (uptime checks, fee withholding, tenant compensation) is Verified; on-chain per-rental record / permissionless settlement Unverified. Verdict: partial overlap. Differentiation narrowed accordingly. | §4, §18, §21, §23, §24, §26 |
| G1 | Added feasibility verdict (Yes), work breakdown (~20–32 person-hours, Assumption), cut order. | §8.1 |
| G2 | Added explicit scope-change statement (market → escrow primitive). | §1 |
| Review | Final-pass fixes: removed residual gas-superiority claim and unsourced "daily" Aethir inference; narrowed §1 problem statement and §13 database comparison; one-objection-per-party rule added to §9.1/§11; frontend-vs-`cast` Must-Have wording aligned with §7/§8.1; §15 creation-revert list points to §7; unresearched-competitor list unified (Akash, io.net, Nosana, Golem); cross-refs fixed (§2→§23, §1→§20 step 10, §8→§26); faucet funding flagged Unverified. | §1, §2, §4, §7, §8, §9.1, §11, §13, §15, §22, §23, §24 |
| Fixes | Demo price lowered from 1 to 0.01 testnet MON (§20, §22 funding); §15 documents that `finalize()` push-transfers native MON, so a rejecting recipient contract locks funds permanently (renter's own funds only; pull-payment added to §25 Future); §15 notes `finalize()` sets `Settled` before transferring (checks-effects-interactions), preventing reentrant double payout. | §15, §20, §22, §25 |
| Risk row | §21 "Stuck funds" risk row now also covers a recipient contract rejecting `finalize()`'s native MON transfer (points to §15; pull-payment Future scope, §25). | §21 |

## 28. Changelog (revision 2026-10-13)

Applies the decisions taken after the external review of 2026-10-01 (D-01..D-08, `docs/DECISIONS.md`) and a research pass of 2026-10-13. Rows from D-09 onward record later owner decisions. Research items are marked RS (the R-labels in §27 belong to the earlier revision).

| ID | Change | Section(s) |
|---|---|---|
| D-01 | Pull payment: `finalize()` credits, `withdraw()` pays; push-payment lock risk removed; reentrancy text updated | §1, §5, §6, §7, §8, §9.1, §9.5, §11, §12, §15, §19, §20, §21, §25 |
| D-02 | Fixed set of 1–8 team-held reporter keys replaces the single oracle address; one trust root stated; benefit stated as isolation of nonce sequences and gas budgets, no parallel-execution speedup claimed; any-one-key compromise disclosed; demo shows two keys' reports in one block (same `start`) | §1, §5, §6, §7, §8, §9.3, §10, §12, §13, §15, §18, §20, §21, §22, §25 |
| D-03 | Contract language Vyper 0.4.3 with day-0 gate and Solidity fallback (was Solidity/Foundry) | §8.1, §12, §14, §21, §22 |
| D-04 | Uptime from a real `/health` probe of a Docker node (at least one probe, all probes 200 within 2 s; a slot with no probe is down — clarified 2026-10-13); `docker stop` demo; force-down kept as backup; separate nodes for overlapping demo runs | §1, §3, §6, §7, §8, §10, §12, §19, §20, §21, §22 |
| D-05 | Price = `msg.value` (no separate argument); at most 256 slots | §5, §7, §12, §15 |
| D-06 | Monad numbers quoted with source and check date | §9.2, §13, §21 |
| D-07 | Provider consent stays off-chain, stated first in the demo; non-gating `provider_ack` event as Could-Have | §8, §15, §20, §25 |
| D-08 | Adoption presented as the largest open question; 3–5 interviews at 42 before the demo | §17, §21, §24 |
| RS1 | Monad numbers re-checked: 300 ms / 600 ms / 3–4 blocks per timestamp / 30M tx / 150M block gas are current; the reviewer's 400 ms / 800 ms / 200M come from stale pages (faucet, changelog table) and must not be quoted | §9.2, §13, §26 |
| RS2 | Chainlink CRE lists Monad Testnet (correction of "Chainlink not on Monad", which holds only for Automation/Functions, now deprecated); added as open question and building block (question since closed by D-10) | §4, §8, §13, §14, §21, §23, §25 |
| RS3 | Competitors extended: TensorDock, Compute Exchange, SF Compute, CoreWeave SLA (corrects "CoreWeave publishes no SLA"), Spheron, Fluence, io.net staking, Akash escrow, Gensyn; Chainlink Staking v0.2 and witness-model papers as analogues; gap assessment narrowed to "per-rental, permissionlessly settled record" | §2, §4, §18, §22, §23, §24 |
| RS4 | User evidence: dated Trustpilot reviews (renters and hosts) replace the single HN anecdote; prices refreshed (2026-10-12); market size now from two disagreeing sources | §2, §3, §17, §22 |
| RS5 | Reserve-balance rule detailed (value spend only; renter's creation call affected); faucet amounts; Vyper/explorer compatibility unverified | §13, §14, §21, §22 |
| RS6 | Metropolis context: six-week format, judging on real users and continued use, team of two; track choice and sponsor integrations (CRE, Envio) recorded as open questions (track choice since closed by D-09, CRE by D-10) | §1, §8.1, §17, §21, §23 |
| Review | Independent review fixes: zero-probe slot gap disclosed and opened as a question (since closed by the D-04 clarification); "no Monad product reason" risk row; CRE removed from the decided out-of-scope list (since reversed by D-10); no reporter-key failover (mitigation reworded); same-block demo restored; Chainlink deprecation dates removed; Vyper-guide wording; CoreWeave newer page flagged; CRE production caveat; funding timeline; deletion-test, provider-bond and recurring-use questions (provider-bond question since closed by D-09) | §4, §8, §8.1, §10, §13, §19, §20, §21, §23, §24, §25 |
| D-09 | Main track chosen: Trust, Identity & AI Infrastructure; the track question is closed; the missing provider bond is kept as a Post-Hackathon item | §1, §23, §25 |
| D-10 | Chainlink CRE not used in the hackathon, neither as reporter nor as simulation demo; the demo and its rehearsals run with the Docker health-probe nodes on the team's WSL machine (single-host risk added); CRE questions closed and CRE kept as a Post-Hackathon option | §4, §7, §8, §12, §13, §14, §20, §21, §23, §25 |
| D-11 | Rental creation stays open to anyone; the oracle service reports only rentals from allow-listed renters and caps report transactions per rental; reporter gas griefing recorded as a known limitation and a risk; budget semantics opened as a question, then closed by the clarification of 2026-10-13 (budget = 2 × N, re-submissions count, each slot's first send reserved) | §8, §10, §12, §15, §20, §21, §23 |
| D-12 | Creation bounds: `start` at most 30 days ahead, `interval` at most 86,400 s; unbounded-`end` overflow lock removed; far-future limitation rewritten | §7, §9.2, §12, §15, §25 |
| D-13 | A rental whose provider has no configured node is not probed and not reported; its slots stay unreported and count as "down"; zero-probe wording scoped to served rentals; demo precondition added | §7, §10, §20 |
