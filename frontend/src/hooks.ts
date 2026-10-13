// The one data layer: every chain read, the tx sender, the log scan and the optional
// oracle API. Screens never call the RPC directly, so mock -> real is decided here.
import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { parseEventLogs, type Address, type Hex, type TransactionReceipt } from 'viem'
import { usePublicClient, useWalletClient } from 'wagmi'
import { ABI, ADDRESS, DEPLOY_BLOCK, MOCK, ORACLE_API, monad } from './config'
import { CHALLENGE_WINDOW, LOG_CHUNK, REPORT_GRACE, backoffMs, chunkRanges, computePhase, revertMessage, sameAddr, type Rental } from './lib/logic'

// ---------------------------------------------------------------- mock (UI_HANDOFF §9)
const MOCK_RENTAL: Rental = {
  renter: '0x1111111111111111111111111111111111111111',
  provider: '0x2222222222222222222222222222222222222222',
  price: 10_000_000_000_000_000n,
  threshold: 75n,
  interval: 30n,
  start: 1790000015n,
  end: 1790000135n,
  n_slots: 4n,
  up_count: 2n,
  reported_count: 4n,
  status: 2,
  proposed_at: 1790000170n,
  compliant: false,
  renter_objected: true,
  provider_objected: false,
  spec_ref: '0x5254582034303930203234474200000000000000000000000000000000000000',
}
const MOCK_SLOTS = [1, 1, 2, 2]
const MOCK_T0 = 1790000190 // 20 s into the challenge window when the page loads

const read = (pc: NonNullable<ReturnType<typeof usePublicClient>>, functionName: string, args: unknown[] = []) =>
  pc.readContract({ address: ADDRESS!, abi: ABI, functionName, args })

// ---------------------------------------------------------------- chain time
/** Chain time in seconds (latest block timestamp), interpolated between polls. Never the browser clock alone. */
export function useChainNow(): number {
  const pc = usePublicClient()
  const loaded = useRef(Date.now() / 1000)
  const { data: offset } = useQuery({
    queryKey: ['chain-offset'],
    enabled: !MOCK && !!pc,
    refetchInterval: 4000,
    queryFn: async () => Number((await pc!.getBlock()).timestamp) - Date.now() / 1000,
  })
  const [, tick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => tick((n) => n + 1), 1000)
    return () => clearInterval(t)
  }, [])
  if (MOCK) return Math.floor(MOCK_T0 + Date.now() / 1000 - loaded.current)
  return Math.floor(Date.now() / 1000 + (offset ?? 0))
}

// ---------------------------------------------------------------- reads
export type RentalView = { rental: Rental; slots: number[]; phase: number; preview: { compliant: boolean; payee: Address; amount: bigint } }

/** rentals + get_slots + phase + payout_preview for one id, refreshed every 4 s (the public RPC is rate-limited). */
export function useRental(id: bigint) {
  const pc = usePublicClient()
  const now = useChainNow()
  const q = useQuery({
    queryKey: ['rental', id.toString()],
    enabled: !MOCK && !!pc && id > 0n,
    refetchInterval: 4000,
    queryFn: async (): Promise<RentalView> => {
      const [rental, slots, phase, preview] = await Promise.all([
        read(pc!, 'rentals', [id]) as Promise<Rental>,
        read(pc!, 'get_slots', [id]) as Promise<readonly number[]>,
        read(pc!, 'phase', [id]) as Promise<number>,
        read(pc!, 'payout_preview', [id]) as Promise<readonly [boolean, Address, bigint]>, // unnamed outputs -> array
      ])
      return { rental: { ...rental, status: Number(rental.status) }, slots: slots.map(Number), phase: Number(phase), preview: { compliant: preview[0], payee: preview[1], amount: preview[2] } }
    },
  })
  if (MOCK) {
    const data: RentalView | undefined =
      id === 1n
        ? { rental: MOCK_RENTAL, slots: MOCK_SLOTS, phase: computePhase(MOCK_RENTAL, now), preview: { compliant: false, payee: MOCK_RENTAL.renter, amount: MOCK_RENTAL.price } }
        : undefined
    return { data, isLoading: false, error: null as Error | null, notFound: id !== 1n }
  }
  return { data: q.data, isLoading: q.isLoading, error: q.error, notFound: q.data?.phase === 0 }
}

export type ListRow = { id: bigint; rental: Rental; phase: number; slots: number[] }

/** Newest rentals first; capped so the public RPC is not hammered (off-screen rentals are not queried). */
export function useRentalList(limit = 8) {
  const pc = usePublicClient()
  const now = useChainNow()
  const q = useQuery({
    queryKey: ['rental-list', limit],
    enabled: !MOCK && !!pc,
    refetchInterval: 8000,
    queryFn: async () => {
      const next = (await read(pc!, 'next_rental_id')) as bigint
      const ids: bigint[] = []
      for (let i = next - 1n; i >= 1n && ids.length < limit; i--) ids.push(i)
      const rows = await Promise.all(
        ids.map(async (id): Promise<ListRow> => {
          const [rental, phase, slots] = await Promise.all([
            read(pc!, 'rentals', [id]) as Promise<Rental>,
            read(pc!, 'phase', [id]) as Promise<number>,
            read(pc!, 'get_slots', [id]) as Promise<readonly number[]>,
          ])
          return { id, rental: { ...rental, status: Number(rental.status) }, phase: Number(phase), slots: slots.map(Number) }
        }),
      )
      return { total: Number(next - 1n), rows }
    },
  })
  if (MOCK) return { data: { total: 1, rows: [{ id: 1n, rental: MOCK_RENTAL, phase: computePhase(MOCK_RENTAL, now), slots: MOCK_SLOTS }] as ListRow[] }, isLoading: false, error: null as Error | null }
  return { data: q.data, isLoading: q.isLoading, error: q.error }
}

export function useCredits(account?: Address) {
  const pc = usePublicClient()
  return useQuery({
    queryKey: ['credits', account],
    enabled: !MOCK && !!pc && !!account,
    refetchInterval: 4000,
    queryFn: async () => (await read(pc!, 'credits', [account])) as bigint,
  })
}

/** credits() of several accounts at once (who still has something to withdraw). */
export function useCreditsOf(accounts: Address[]) {
  const pc = usePublicClient()
  const key = accounts.map((a) => a.toLowerCase()).sort().join(',')
  return useQuery({
    queryKey: ['credits-of', key],
    enabled: !MOCK && !!pc && accounts.length > 0,
    refetchInterval: 6000,
    queryFn: async () => Object.fromEntries(await Promise.all(accounts.map(async (a) => [a.toLowerCase(), (await read(pc!, 'credits', [a])) as bigint] as const))),
  })
}

/** REPORT_GRACE / CHALLENGE_WINDOW from the contract (fixed in bytecode); SPEC values until loaded. */
export function useWindows() {
  const pc = usePublicClient()
  const { data } = useQuery({
    queryKey: ['windows'],
    enabled: !MOCK && !!pc,
    staleTime: Infinity,
    queryFn: async () => ({ grace: Number(await read(pc!, 'REPORT_GRACE')), window: Number(await read(pc!, 'CHALLENGE_WINDOW')) }),
  })
  return data ?? { grace: REPORT_GRACE, window: CHALLENGE_WINDOW }
}

// ---------------------------------------------------------------- writes
export type TxState = { status: 'idle' | 'signing' | 'pending' | 'confirmed' | 'failed'; hash?: Hex; error?: string }

/** simulate -> explicit gas (estimate x 1.2, Monad charges the limit) -> send -> wait for the receipt. */
export function useTx() {
  const pc = usePublicClient()
  const { data: wallet } = useWalletClient()
  const qc = useQueryClient()
  const [tx, setTx] = useState<TxState>({ status: 'idle' })

  async function send(functionName: string, args: unknown[] = [], value?: bigint): Promise<TransactionReceipt | undefined> {
    if (MOCK) return void setTx({ status: 'failed', error: 'Mock mode: the contract is not deployed, nothing was sent' })
    if (!wallet || !pc) return void setTx({ status: 'failed', error: 'Connect a wallet first' })
    let hash: Hex | undefined
    try {
      setTx({ status: 'signing' })
      const req = { address: ADDRESS!, abi: ABI, functionName, args, value, account: wallet.account }
      await pc.simulateContract(req) // surfaces the revert string before the wallet opens
      const gas = ((await pc.estimateContractGas(req)) * 12n) / 10n
      hash = await wallet.writeContract({ ...req, gas, chain: monad })
      setTx({ status: 'pending', hash })
      const receipt = await pc.waitForTransactionReceipt({ hash })
      if (receipt.status !== 'success') return void setTx({ status: 'failed', hash, error: 'The transaction reverted on-chain' })
      setTx({ status: 'confirmed', hash })
      qc.invalidateQueries()
      return receipt
    } catch (e) {
      setTx({ status: 'failed', hash, error: revertMessage(e) })
    }
  }
  return { tx, send, busy: tx.status === 'signing' || tx.status === 'pending' }
}

// ---------------------------------------------------------------- event history
export type Ev = { name: string; args: Record<string, unknown>; block: bigint; tx: Hex; logIndex: number; time?: number }
const POLL_MS = 8000 // how often new blocks are checked once the history is loaded
const MAX_BACK_CHUNKS = 150 // one backward pass = 15,000 blocks; the "scan older" button grants another
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))
type Cursor = { lo: bigint; hi: bigint; complete: boolean; budget: number }

/**
 * Events of one rental. History is scanned ONCE, backwards from the head in 100-block chunks
 * (the public RPC's eth_getLogs limit) until the rental's RentalCreated or the deploy block;
 * after that each poll only reads the blocks added since the last scanned block.
 * RPC errors / 429 back off exponentially and surface as one quiet `retrying` flag.
 * Withdrawn has no rental id, so withdrawals of the two parties are shown.
 * ponytail: linear getLogs scan (100 blocks ~ 30 s of chain time per call); switch to an
 * indexer (e.g. Envio) if rentals older than about an hour must be browsed.
 */
export function useEvents(id: bigint, parties: Address[]) {
  const pc = usePublicClient()
  const [events, setEvents] = useState<Ev[]>([])
  const [state, setState] = useState<{ scanning: boolean; retrying: boolean; complete: boolean; lowest?: bigint }>({ scanning: false, retrying: false, complete: false })
  const [more, setMore] = useState(0)
  const cursor = useRef<Cursor | null>(null)
  const partyKey = parties.map((p) => p.toLowerCase()).join(',')

  useEffect(() => {
    cursor.current = null
    setEvents([])
    setState({ scanning: false, retrying: false, complete: false })
  }, [id])

  useEffect(() => {
    if (MOCK || !pc || id <= 0n || parties.length === 0) return
    let dead = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let failures = 0

    const fetchRange = async (from: bigint, to: bigint): Promise<Ev[]> => {
      const logs = await pc.getLogs({ address: ADDRESS!, fromBlock: from, toBlock: to })
      const found: Ev[] = parseEventLogs({ abi: ABI, logs })
        .map((l) => ({ name: l.eventName as string, args: l.args as unknown as Record<string, unknown>, block: l.blockNumber, tx: l.transactionHash, logIndex: l.logIndex }))
        .filter((e) => e.args.rental_id === id || (e.name === 'Withdrawn' && parties.some((p) => sameAddr(p, e.args.account as string))))
      // block timestamps for the activity feed: one read per block that holds a relevant event
      const blocks = [...new Set(found.map((e) => e.block))]
      const times = new Map(await Promise.all(blocks.map(async (b) => [b, Number((await pc.getBlock({ blockNumber: b })).timestamp)] as const)))
      return found.map((e) => ({ ...e, time: times.get(e.block) }))
    }
    const merge = (found: Ev[]) =>
      found.length &&
      setEvents((old) => {
        const seen = new Set(old.map((e) => `${e.tx}-${e.logIndex}`))
        return [...old, ...found.filter((e) => !seen.has(`${e.tx}-${e.logIndex}`))].sort((a, b) => (a.block === b.block ? a.logIndex - b.logIndex : a.block < b.block ? -1 : 1))
      })

    const step = async () => {
      try {
        const head = await pc.getBlockNumber()
        if (!cursor.current) cursor.current = { lo: head + 1n, hi: head, complete: false, budget: MAX_BACK_CHUNKS }
        const c = cursor.current
        // forwards: only the blocks added since the last scanned block
        for (const [from, to] of chunkRanges(c.hi + 1n, head)) {
          if (dead) return
          merge(await fetchRange(from, to))
          c.hi = to // advance per chunk, so a later failure never re-reads this range
        }
        // backwards: the one-time history pass, until this rental's creation or the deploy block
        if (!c.complete && c.budget > 0 && !dead) setState((s) => ({ ...s, scanning: true }))
        while (!dead && !c.complete && c.budget > 0) {
          if (c.lo <= DEPLOY_BLOCK) { c.complete = true; break }
          const to = c.lo - 1n
          const from = to - LOG_CHUNK + 1n > DEPLOY_BLOCK ? to - LOG_CHUNK + 1n : DEPLOY_BLOCK
          const found = await fetchRange(from, to)
          merge(found)
          c.lo = from
          c.budget--
          if (found.some((e) => e.name === 'RentalCreated' && e.args.rental_id === id)) c.complete = true
          await sleep(150) // stay far below the public RPC rate limit
        }
        failures = 0
        if (!dead) setState({ scanning: false, retrying: false, complete: c.complete, lowest: c.lo })
      } catch {
        failures++
        if (!dead) setState((s) => ({ ...s, scanning: false, retrying: true }))
      }
      if (!dead) timer = setTimeout(step, failures ? backoffMs(failures) : POLL_MS)
    }
    step()
    return () => { dead = true; clearTimeout(timer) }
    // parties are compared by value through partyKey
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pc, id, partyKey, more])

  /** Grants the backward pass another budget and resumes it now. */
  const scanOlder = () => {
    if (cursor.current) cursor.current.budget = MAX_BACK_CHUNKS
    setMore((n) => n + 1)
  }
  return { events, ...state, scanOlder }
}

// ---------------------------------------------------------------- oracle control API (optional, localhost)
const oracleGet = async (path: string) => {
  const r = await fetch(`${ORACLE_API}${path}`, { signal: AbortSignal.timeout(1500) })
  if (r.status === 404) return null
  if (!r.ok) throw new Error(`oracle ${r.status}`)
  return r.json()
}

export type OracleSlot = { slot: number; probesOk: number; probesTotal: number; forcedDown: boolean; reported: boolean; up: boolean; txHash: string | null }

/** reachable=false hides the panel. Never a source of truth: the chain is. */
export function useOracle(id?: bigint) {
  const health = useQuery({ queryKey: ['oracle-health'], retry: false, refetchInterval: 30_000, queryFn: () => oracleGet('/health') })
  const reachable = health.isSuccess && !!health.data
  const rental = useQuery({
    queryKey: ['oracle-rental', id?.toString()],
    enabled: reachable && id !== undefined,
    retry: false,
    refetchInterval: 3000,
    queryFn: () => oracleGet(`/rentals/${id}`) as Promise<{ rentalId: number; slots: OracleSlot[] } | null>,
  })
  const qc = useQueryClient()
  const forceDown = async (slots: number[] | null) => {
    await fetch(`${ORACLE_API}/rentals/${id}/force-down`, slots ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ slots }) } : { method: 'DELETE' })
    qc.invalidateQueries({ queryKey: ['oracle-rental'] })
  }
  return { reachable, tracked: rental.isSuccess ? rental.data !== null : undefined, slots: rental.data?.slots ?? [], forceDown }
}
