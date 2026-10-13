# frontend/ — GPU SLA Escrow web UI

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
| Rentals | `#/` | Newest 8 rentals, read from the chain |
| Create rental | `#/create` | Every SPEC C-rule checked before sending; reserve-balance warning |
| Rental detail | `#/rental/<id>` | Slot timeline, uptime vs threshold, phase + countdown, phase-gated buttons, event history, optional oracle panel |
| Withdraw | `#/withdraw` | `credits(connected address)` and `withdraw()` |

What the UI says and does not say: uptime data comes from team-run reporter keys (one trust
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

After a deploy, `scripts/deploy.py` writes the address into the shared deployment file;
rebuild (or restart `npm run dev`) and the app leaves mock mode.

## Behaviour worth knowing

- **Time** comes from the latest block timestamp, not the browser clock. `start` for a new
  rental is the latest block timestamp plus the delay in the form (default 20 s).
- **Gas**: every transaction is simulated first, then sent with an explicit gas limit of
  estimate × 1.2 (Monad charges the gas limit).
- **Polling**: the open rental is read every 2 s, the list every 8 s, the block time every 4 s.
  The public RPC is rate-limited, so rentals that are not on screen are not queried.
- **Event history** scans logs backwards from the head in 1000-block chunks until the rental's
  `RentalCreated` event (60 chunks per run, then a "scan older blocks" button), and follows new
  blocks forwards. `Withdrawn` carries no rental id, so withdrawals of the renter and the
  provider are listed. For rentals older than a few hours an indexer would be the better tool.
- **Oracle panel** appears only when `VITE_ORACLE_API` answers `/health`. The API listens on
  `127.0.0.1` only and allows only `http://localhost:*` origins, so the panel shows up when the
  UI is served from the machine that runs the oracle, and stays hidden on a hosted build. The
  chain stays the source of truth for slot colours.
- **Oracle allow-list**: the oracle reports only rentals whose renter wallet is on its
  allow-list and whose provider has a configured node. Add the wallet you create rentals with
  to `[renters] allow` in `oracle/config.toml` before creating one; otherwise the rental gets no
  reports and refunds.
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
