import { defineChain, type Abi, type Address } from 'viem'
import { createConfig, http } from 'wagmi'
import { injected } from 'wagmi/connectors'
import abiJson from '../../shared/abi/GpuSlaEscrow.json'
import deployment from '../../shared/deployments/monad-testnet.json'
import { parseDemoProviders } from './lib/logic'

const env = import.meta.env

export const ABI = abiJson as Abi
export const RPC_URL: string = env.VITE_RPC_URL || 'https://testnet-rpc.monad.xyz'
export const EXPLORER: string = env.VITE_EXPLORER_URL || 'https://testnet.monadscan.com'
export const ORACLE_API: string = env.VITE_ORACLE_API || 'http://localhost:8787'
export const INDEXER_URL: string | undefined = env.VITE_INDEXER_URL?.trim() || undefined

const dep = deployment as { address: string | null; deployBlock: number | null }
export const ADDRESS = (env.VITE_ESCROW_ADDRESS || dep.address || undefined) as Address | undefined
export const DEPLOY_BLOCK = BigInt(env.VITE_DEPLOY_BLOCK || dep.deployBlock || 0)
/** No deployed address yet -> the UI runs on the mock data from docs/UI_HANDOFF.md §9. */
export const MOCK = !ADDRESS

export const monad = defineChain({
  id: 10143,
  name: 'Monad Testnet',
  nativeCurrency: { name: 'MON', symbol: 'MON', decimals: 18 },
  rpcUrls: { default: { http: [RPC_URL] } },
  blockExplorers: { default: { name: 'Monadscan', url: EXPLORER } },
  testnet: true,
})

export const wagmiConfig = createConfig({
  chains: [monad],
  connectors: [injected()],
  // Batch concurrent contract reads (e.g. the Rentals list) into one JSON-RPC request.
  transports: { [monad.id]: http(RPC_URL, { batch: { batchSize: 50, wait: 10 } }) },
})

/** Optional demo address book for the Create form: "label=0xaddress,label=0xaddress". Public addresses only. */
export const DEMO_PROVIDERS = parseDemoProviders(env.VITE_DEMO_PROVIDERS)

export const txUrl = (hash: string) => `${EXPLORER}/tx/${hash}`
export const addrUrl = (a: string) => `${EXPLORER}/address/${a}`
