# frontend/ — Heartbond web UI

_Heartbond — pay per heartbeat._ (Formerly the working title "GPU SLA Escrow"; the contract and
ABI keep the name `GpuSlaEscrow`.)

React + Vite + TypeScript, viem + wagmi, plain CSS. Monad Testnet (chain id 10143).
The interface contract for this UI is `../docs/UI_HANDOFF.md`; changes are logged in
`../docs/INTERFACE_CHANGELOG.md`.

The ABI and the deployed address are read at build time from
`../shared/abi/GpuSlaEscrow.json` and `../shared/deployments/monad-testnet.json`.
While that file has `"address": null` the app runs in **mock mode**: it shows the sample
rental from UI_HANDOFF §9 and sends no transaction.

## What is here

| Screen | Route | Notes |
|---|---|---|
| Connect wallet | header | Injected wallet (MetaMask); switches to / adds Monad Testnet |
| Rentals | `#/` | Newest 8 rentals with status, slot mini-tiles and outcome |
| Create rental | `#/create` | Every SPEC C-rule checked before sending; reserve-balance warning; start by delay or "same time as rental #N"; optional provider quick-picks |
| Rental detail | `#/rental/<id>` | Phase banner with countdown, slot tiles, uptime bar with threshold marker, outcome card, role badge and "who acts next" line, event history, optional oracle panel |
| Withdraw | `#/withdraw` | `credits(connected address)`, `withdraw()`, and a hint naming the account that holds the payout |

UI text is English. What the UI says and does not say: uptime data comes from team-run reporter keys (one trust
root); `settle` and `finalize` can be triggered by any wallet; an objection is only a record
(objection log) and never changes the payout.

## Run

```bash
cd frontend
npm install
cp .env.example .env.local   # optional; every value has a default
npm run dev                  # http://localhost:5173
```

Other commands:

```bash
npm run typecheck   # tsc --noEmit
npm test            # unit tests for the form rules, phase logic and revert messages
npm run build       # typecheck + production build into dist/
npm run preview     # serve dist/ locally
```

## Configuration (public values only)

No private key belongs in the frontend. All variables are optional.

| Variable | Default | Purpose |
|---|---|---|
| `VITE_RPC_URL` | `https://testnet-rpc.monad.xyz` | Read RPC |
| `VITE_EXPLORER_URL` | `https://testnet.monadscan.com` | Transaction and address links |
| `VITE_ESCROW_ADDRESS` | `address` in the shared deployment file | Contract address override |
| `VITE_DEPLOY_BLOCK` | `deployBlock` in the shared deployment file | Lower bound for the log scan |
| `VITE_ORACLE_API` | `http://localhost:8787` | Optional oracle control API |
| `VITE_DEMO_PROVIDERS` | unset | Demo address book for the Create form: `Node A=0x…,Node B=0x…` (public addresses only) |

After a deploy, `scripts/deploy.py` writes the address into the shared deployment file;
rebuild (or restart `npm run dev`) and the app leaves mock mode.

## Behaviour worth knowing

- **Time** comes from the latest block timestamp, not the browser clock. `start` for a new
  rental is the latest block timestamp plus the delay in the form (default 20 s).
- **Gas**: every transaction is simulated first, then sent with an explicit gas limit of
  estimate × 1.2 (Monad charges the gas limit).
- **Polling**: the open rental is read every 4 s, the list every 8 s, the block time every 4 s.
  The public RPC is rate-limited, so rentals that are not on screen are not queried.
- **Event history** is scanned once: backwards from the head in 100-block `eth_getLogs` chunks
  (the public RPC's limit) until the rental's `RentalCreated` event — 150 chunks per pass, then a
  "scan older blocks" button. After that only blocks added since the last scanned block are read,
  every 8 s. On RPC errors or 429 the scan backs off (2 s, 4 s, 8 s … 60 s) and the feed shows one
  quiet "RPC busy, retrying" indicator. `Withdrawn` carries no rental id, so withdrawals of the
  renter and the provider are listed. For rentals older than about an hour an indexer would be
  the better tool.
- **Oracle panel** appears only when `VITE_ORACLE_API` answers `/health`. The API listens on
  `127.0.0.1` only and allows only `http://localhost:*` origins, so the panel shows up when the
  UI is served from the machine that runs the oracle, and stays hidden on a hosted build. The
  chain stays the source of truth for slot colours.
- **Oracle allow-list**: the oracle reports only rentals whose renter wallet is on its
  allow-list and whose provider has a configured node. Add the wallet you create rentals with
  to `[renters] allow` in `oracle/config.toml` before creating one; otherwise the rental gets no
  reports and refunds.
- **Same start for two rentals** (demo): on the Create form choose "Start at the same time as
  rental #N". It works while that rental's start is at least 5 s ahead; otherwise the form says why.
- **Roles**: the provider is only an address and never has to connect. The connected wallet is
  the renter; if it equals the provider address the form blocks creation.
- **Design**: near-black flat cards with hairline borders; one accent (Monad purple `#836EF9`) for
  primary actions and the current slot / step; green, red and grey only for UP / DOWN / EMPTY and
  the outcome that follows from them. Inter for UI, JetBrains Mono for addresses, hashes, amounts,
  countdowns and slot numbers — both self-hosted through `@fontsource-variable/*`, so the page needs
  no font CDN. Animations (slot pulse, tile and feed transitions, skeletons) stop under
  `prefers-reduced-motion`.
- **Bundle**: libraries are split into `react`, `viem` and `wallet` chunks; the app chunk is ~40 kB.
- **Reserve balance**: the create form warns when paying the price would leave the wallet with
  less than 10 MON, because Monad then reverts the transaction.

## Deploy to Vercel

1. Import the repository in Vercel.
2. **Root Directory**: `frontend`. Keep "Include files outside the Root Directory in the Build
   Step" enabled (the default) — the build reads `../shared/`.
3. Framework preset: **Vite**. Build command `npm run build`, output directory `dist`,
   install command `npm install`.
4. Environment variables: none are required. Set `VITE_ESCROW_ADDRESS` / `VITE_DEPLOY_BLOCK`
   only to override the shared deployment file.
5. Deploy. Routes are hash-based (`#/rental/1`), so no rewrite rule is needed.

With the CLI: `cd frontend && npx vercel --prod` after linking the project with the same root
directory setting. The hosted build is built from whatever `shared/deployments/monad-testnet.json`
contains at that commit, so commit the deployment file first.
