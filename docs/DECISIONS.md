# Decisions

Append-only log of project decisions. Newest last. Numbers are never reused or renumbered.
The PRD states what is true now; this log states why.

Decisions made before this log existed (PRD revision 2026-09-27) are marked **(Decision)**
inline in `docs/PRD.md` and listed in its §27 changelog. The entries below record the
decisions taken in response to the external review of 2026-10-01
(`docs/REVIEW_2026-10-01.txt`), as recorded in `docs/SPEC.md` §9 and `docs/PLAN.md` §1.

## D-01 — Pull payment: `finalize()` credits, `withdraw()` pays

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** `finalize()` no longer sends MON. It sets the rental to Settled and credits
  the payee's internal balance; the payee then calls `withdraw()` to receive it. A failing
  transfer reverts only that caller's own `withdraw()`.
- **Why:** Review item 4: with push payment, a recipient contract that rejects native MON
  makes `finalize()` revert forever and locks the escrow. The PRD (rev 2026-09-27) had
  disclosed this and deferred pull payment to Future; the review judged it a small change
  with a large credibility gain, so it moved into the MVP. Rejected: keeping push payment
  as a disclosed limitation. Source: SPEC §3 F-4, P-1..P-3; SPEC §9; PLAN §1 #4.
- **Affects:** PRD §5, §6, §7, §8, §9.1, §9.5, §11, §12, §15, §19, §20, §21, §25.

## D-02 — Fixed set of team-held reporter keys instead of one oracle address

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** The contract takes 1–8 reporter addresses at deployment, fixed forever (no
  admin, no rotation); any of them may report any rental's slots. The off-chain service
  sends each rental's reports from one key chosen deterministically per rental, and the
  report path writes only per-rental storage. All keys are held by the team: this removes
  the single-nonce bottleneck, not the single trust root, and the pitch must say so. The demo
  shows reports for two rentals from two different keys landing in the same block.
- **Why:** Review item 1: all reports from one EOA share one nonce sequence and are
  serialized, which undercuts any Monad-performance argument. Rejected: keeping one
  oracle address. Source: SPEC §3 R-1..R-3; SPEC §9; PLAN §1 #1.
- **Affects:** PRD §1, §5, §6, §7, §8, §9.3, §10, §12, §13, §15, §18, §19, §20, §21, §22, §25.
- **Clarified 2026-10-13:** Monad's documentation describes optimistic parallel execution
  over storage reads/writes but says nothing about same-sender versus different-sender
  transactions, and gives no measured gain for this pattern. The claim stays limited to
  "independent nonces and separate per-account gas budgets"; no parallel-execution speedup
  is claimed (research 2026-10-13, PRD §13).

## D-03 — Contract language: Vyper 0.4.3 with a day-0 gate, Solidity fallback

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** The contract is written in Vyper 0.4.3 and tested with titanoboa + pytest.
  On day 0 a minimal Vyper contract must deploy, emit an event and verify on a Monad
  explorer; if that cannot be fixed in about two hours, the team switches to Solidity with
  the same spec and the same ABI names.
- **Why:** Review item 3: Monad's guides cover Foundry, Hardhat and Remix, not Vyper, so
  Vyper + Monad is an untested assumption that must fail early, not on the last day. The
  owner prefers not to use Solidity unless required. Source: SPEC header, SPEC §8 G-1..G-3;
  PLAN §1 #3; CLAUDE.md "Stack".
- **Affects:** PRD §8.1, §12, §14, §21, §22.

## D-04 — Uptime from a real HTTP health probe of a Docker node; force-down kept as backup

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** The oracle service probes a demo GPU-node stand-in (a Docker container
  exposing `GET /health`) every 5 s during each slot. A slot is "up" only if every probe in
  that slot returned HTTP 200 within 2 s. The demo makes slots "down" with a live
  `docker stop`; the scripted force-down control remains as a backup if Docker fails on stage.
- **Why:** Review demo suggestion: a live `docker stop` moves the obvious objection from
  "the data is invented" to "the data comes from a real health check, only the reporter is
  single". Strict all-probes rule chosen because it is simple to explain. Source: SPEC §4
  H-1..H-7; SPEC §9; PLAN §1 "Demo".
- **Affects:** PRD §1, §3, §6, §7, §8, §10, §12, §19, §20, §21, §22.
- **Clarified 2026-10-13:** A slot is reported "up" only if at least one health probe ran in
  that slot and every probe that ran returned HTTP 200 within 2 s; a slot in which no probe
  ran is reported "down". This closes the zero-probe gap found in the review of 2026-10-13:
  as first worded, a slot with no probes satisfied "every probe succeeded" and would have
  been reported "up", the opposite of the "missing report = down" policy (PRD §9.4). The
  other options listed in the open question — requiring all expected probes to have run, or
  sending no report for such a slot — were not adopted (owner's decision; PRD §7, §10,
  formerly §23). `docs/SPEC.md` was absent when this was recorded, so rule H-3 was not
  updated; it must be aligned with this rule when the SPEC is available.

## D-05 — Creation interface: price is `msg.value`; at most 256 slots per rental

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** Agreement creation has no separate `price` argument: the price is exactly
  the MON sent with the call, which must be greater than zero. Creation reverts if the
  rental has more than 256 slots (`(end − start) / interval > 256`).
- **Why:** A separate price argument that must equal `msg.value` is redundant. Vyper loops
  must be bounded, so the slot count needs a cap. Source: SPEC §3 C-1.8, C-1.9; SPEC §9.
- **Affects:** PRD §5, §7, §12, §15.

## D-06 — Every Monad number is quoted with its source and the date checked

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** No Monad performance or gas number goes into the pitch, README or slides
  without its source URL and the date it was checked; the numbers are re-checked on demo
  day and the block time is measured with the smoke-test script.
- **Why:** Review item 2 warned that one wrong number reads as "they did not research".
  On 2026-10-01 the live summary page still said 300 ms / 600 ms / 3–4 blocks per
  timestamp / 150M block gas, which differs from the reviewer's numbers. Source: SPEC §7;
  PLAN §1 #2.
- **Affects:** PRD §9.2, §13, §21.
- **Clarified 2026-10-13:** Re-checked live: the summary and "Monad for Developers" pages
  say 300 ms blocks and 600 ms finality; the releases page records the change from 400 ms /
  200M to 300 ms / 150M in July 2026. The faucet page (400 ms / 800 ms), the changelog
  revision table and the Metropolis notes still show the older values; they must not be
  quoted.

## D-07 — Provider consent stays off-chain and is disclosed first in the demo

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** The MVP still has no on-chain provider acceptance; only the renter signs.
  The demo narration states this limitation proactively. A non-gating `provider_ack` event
  is a Could-Have if time allows.
- **Why:** Review item 5: without an on-chain consent step, "is this agreement really
  two-sided?" would catch the team unprepared. A gating accept step was not adopted for the
  MVP. Source: SPEC §9; PLAN §1 #5.
- **Affects:** PRD §8, §15, §20, §25.

## D-08 — Adoption is presented as the largest open question, with a small validation before the demo

- **Date:** 2026-10-01
- **Status:** Accepted
- **Decision:** The pitch frames "who would actually use this" as the biggest open
  question, not as a solved go-to-market story. Before the demo the team runs short
  interviews with 3–5 people at 42 who rent GPUs.
- **Why:** Review item 6: no validated answer exists to why a marketplace would give up its
  own arbitration or why users would switch; an invented go-to-market story would be less
  credible than an honest open question. Source: PLAN §1 #6.
- **Affects:** PRD §17, §21, §24.
