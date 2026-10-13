// The one data layer: every chain read, the tx sender, the log scan and the optional
// oracle API. Screens never call the RPC directly, so mock -> real is decided here.
import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { parseEventLogs, type Address, type Hex, type TransactionReceipt } from 'viem'
import { usePublicClient, useWalletClient } from 'wagmi'
import { ABI, ADDRESS, DEPLOY_BLOCK, MOCK, ORACLE_API, monad } from './config'
import { CHALLENGE_WINDOW, REPORT_GRACE, computePhase, revertMessage, sameAddr, type Rental } from './lib/logic'

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

/** rentals + get_slots + phase + payout_preview for one id, refreshed every 2 s (UI_HANDOFF §5). */
export function useRental(id: bigint) {
  const pc = usePublicClient()
  const now = useChainNow()
  const q = useQuery({
    queryKey: ['rental', id.toString()],
    enabled: !MOCK && !!pc && id > 0n,
    refetchInterval: 2000,
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
        ids.map(async (id) => {
          const [rental, phase] = await Promise.all([read(pc!, 'rentals', [id]) as Promise<Rental>, read(pc!, 'phase', [id]) as Promise<number>])
          return { id, rental, phase: Number(phase) }
        }),
      )
      return { total: Number(next - 1n), rows }
    },
  })
  if (MOCK) return { data: { total: 1, rows: [{ id: 1n, rental: MOCK_RENTAL, phase: computePhase(MOCK_RENTAL, now) }] }, isLoading: false, error: null as Error | null }
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
    if (MOCK) return void setTx({ status: 'failed', error: 'Mock modu: kontrat deploy edilmedi, işlem gönderilmedi' })
    if (!wallet || !pc) return void setTx({ status: 'failed', error: 'Önce cüzdan bağla' })
    let hash: Hex | undefined
    try {
      setTx({ status: 'signing' })
      const req = { address: ADDRESS!, abi: ABI, functionName, args, value, account: wallet.account }
      await pc.simulateContract(req) // surfaces the revert string before the wallet opens
      const gas = ((await pc.estimateContractGas(req)) * 12n) / 10n
      hash = await wallet.writeContract({ ...req, gas, chain: monad })
      setTx({ status: 'pending', hash })
      const receipt = await pc.waitForTransactionReceipt({ hash })
      if (receipt.status !== 'success') return void setTx({ status: 'failed', hash, error: 'İşlem zincirde revert etti' })
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
export type Ev = { name: string; args: Record<string, unknown>; block: bigint; tx: Hex; logIndex: number }
const CHUNK = 1000n // blocks per getLogs call
const MAX_BACK_CHUNKS = 60 // per run; the "scan older" button continues
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

/**
 * Events of one rental. Scans backwards from the head in 1000-block chunks until the
 * rental's RentalCreated is found (or the deploy block), then follows the head forwards.
 * Withdrawn has no rental id, so withdrawals of the two parties are shown.
 * ponytail: linear getLogs scan, one call per 1000 blocks (~5 min of chain time each);
 * switch to an indexer (e.g. Envio) if rentals older than a few hours must be browsed.
 */
export function useEvents(id: bigint, parties: Address[]) {
  const pc = usePublicClient()
  const [events, setEvents] = useState<Ev[]>([])
  const [state, setState] = useState<{ scanning: boolean; complete: boolean; lowest?: bigint; error?: string }>({ scanning: false, complete: false })
  const [more, setMore] = useState(0)
  const cursor = useRef<{ lo: bigint; hi: bigint; complete: boolean } | null>(null)
  const partyKey = parties.map((p) => p.toLowerCase()).join(',')

  useEffect(() => {
    cursor.current = null
    setEvents([])
    setState({ scanning: false, complete: false })
  }, [id])

  useEffect(() => {
    if (MOCK || !pc || id <= 0n) return
    let dead = false

    const fetchRange = async (from: bigint, to: bigint): Promise<Ev[]> => {
      const logs = await pc.getLogs({ address: ADDRESS!, fromBlock: from, toBlock: to })
      return parseEventLogs({ abi: ABI, logs })
        .map((l) => ({ name: l.eventName as string, args: l.args as unknown as Record<string, unknown>, block: l.blockNumber, tx: l.transactionHash, logIndex: l.logIndex }))
        .filter((e) => e.args.rental_id === id || (e.name === 'Withdrawn' && parties.some((p) => sameAddr(p, e.args.account as string))))
    }
    const merge = (found: Ev[]) =>
      found.length &&
      setEvents((old) => {
        const seen = new Set(old.map((e) => `${e.tx}-${e.logIndex}`))
        return [...old, ...found.filter((e) => !seen.has(`${e.tx}-${e.logIndex}`))].sort((a, b) => (a.block === b.block ? a.logIndex - b.logIndex : a.block < b.block ? -1 : 1))
      })

    const run = async () => {
      try {
        setState((s) => ({ ...s, scanning: true, error: undefined }))
        const head = await pc.getBlockNumber()
        if (!cursor.current) cursor.current = { lo: head + 1n, hi: head, complete: false }
        const c = cursor.current
        // forwards: new blocks since the last run
        while (!dead && c.hi < head) {
          const to = c.hi + CHUNK < head ? c.hi + CHUNK : head
          merge(await fetchRange(c.hi + 1n, to))
          c.hi = to
        }
        // backwards: until this rental's creation or the deploy block
        for (let n = 0; !dead && !c.complete && n < MAX_BACK_CHUNKS; n++) {
          if (c.lo <= DEPLOY_BLOCK) { c.complete = true; break }
          const to = c.lo - 1n
          const from = to - CHUNK + 1n > DEPLOY_BLOCK ? to - CHUNK + 1n : DEPLOY_BLOCK
          const found = await fetchRange(from, to)
          merge(found)
          c.lo = from
          if (found.some((e) => e.name === 'RentalCreated' && e.args.rental_id === id)) c.complete = true
          await sleep(120) // stay far below the public RPC rate limit
        }
        if (!dead) setState({ scanning: false, complete: c.complete, lowest: c.lo })
      } catch (e) {
        if (!dead) setState((s) => ({ ...s, scanning: false, error: (e as Error).message.split('\n')[0] }))
      }
    }
    run()
    const t = setInterval(run, 6000)
    return () => { dead = true; clearInterval(t) }
    // parties are compared by value through partyKey
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pc, id, partyKey, more])

  return { events, ...state, scanOlder: () => setMore((n) => n + 1) }
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
