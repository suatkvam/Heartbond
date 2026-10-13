// Pure rules shared by the screens. Mirrors docs/SPEC.md §3 and docs/UI_HANDOFF.md §4–§5.
import { formatEther, isAddress, parseEther, type Address, type Hex } from 'viem'

// Internal contract constants: not in the ABI, so they are fixed here (UI_HANDOFF §4).
export const MAX_SLOTS = 256
export const MAX_INTERVAL = 86_400
export const MAX_START_DELAY = 2_592_000
export const REPORT_GRACE = 10
export const CHALLENGE_WINDOW = 15
/** Monad reserve balance: a value spend that leaves less than this reverts. */
export const RESERVE_WEI = 10n * 10n ** 18n
/** A shared start must be at least this far ahead, or the creation tx cannot land before it (C-1.1). */
export const MIN_START_LEAD = 5

export type Rental = {
  renter: Address
  provider: Address
  price: bigint
  threshold: bigint
  interval: bigint
  start: bigint
  end: bigint
  n_slots: bigint
  up_count: bigint
  reported_count: bigint
  status: number
  proposed_at: bigint
  compliant: boolean
  renter_objected: boolean
  provider_objected: boolean
  spec_ref: Hex
}

export const PHASE = ['None', 'Scheduled', 'Running', 'Grace', 'Settleable', 'Challenge', 'Finalizable', 'Settled'] as const

/** Same derivation as the contract's phase() view; used for mock data and countdowns. */
export function computePhase(r: Pick<Rental, 'status' | 'start' | 'end' | 'proposed_at'>, now: number, grace = REPORT_GRACE, window = CHALLENGE_WINDOW): number {
  if (r.status === 0) return 0
  if (r.status === 3) return 7
  if (r.status === 2) return now < Number(r.proposed_at) + window ? 5 : 6
  if (now < Number(r.start)) return 1
  if (now < Number(r.end)) return 2
  if (now <= Number(r.end) + grace) return 3
  return 4
}

/** Unix second at which the current phase ends, or null if nothing is counting down. */
export function phaseDeadline(phase: number, r: Pick<Rental, 'start' | 'end' | 'proposed_at'>, grace = REPORT_GRACE, window = CHALLENGE_WINDOW): number | null {
  if (phase === 1) return Number(r.start)
  if (phase === 2) return Number(r.end)
  if (phase === 3) return Number(r.end) + grace + 1 // settle needs now > end + grace
  if (phase === 5) return Number(r.proposed_at) + window
  return null
}

/** 0:23, 12:05, 1:02:03, "3d 4h" — for countdowns. */
export function fmtClock(s: number): string {
  s = Math.max(0, Math.floor(s))
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  if (d) return `${d}d ${h}h`
  if (h) return `${h}:${pad(m)}:${pad(sec)}`
  return `${m}:${pad(sec)}`
}

/** Headline of the phase banner, with the live countdown where one runs. */
export function phaseBanner(phase: number, left: number | null): string {
  const t = fmtClock(left ?? 0)
  switch (phase) {
    case 1: return `Starts in ${t}`
    case 2: return `Running — rental ends in ${t}`
    case 3: return `Reporting closes in ${t}`
    case 4: return 'Ready to settle — anyone can call it'
    case 5: return `Challenge window ${t}`
    case 6: return 'Ready to finalize — anyone can call it'
    case 7: return 'Settled'
    default: return 'Rental not found'
  }
}

export type Role = 'renter' | 'provider' | 'third party' | 'not connected'
export const sameAddr = (a?: string, b?: string) => !!a && !!b && a.toLowerCase() === b.toLowerCase()
export const short = (a?: string) => (a ? `${a.slice(0, 6)}…${a.slice(-4)}` : '—')
export const mon = (v: bigint) => `${formatEther(v)} MON`
export const roleOf = (me: string | undefined, r: Pick<Rental, 'renter' | 'provider'>): Role =>
  !me ? 'not connected' : sameAddr(me, r.renter) ? 'renter' : sameAddr(me, r.provider) ? 'provider' : 'third party'

/** Compliance exactly as S-3: 100 * M >= threshold * N. */
export const isCompliant = (up: bigint, threshold: bigint, n: bigint) => 100n * up >= threshold * n
/** Smallest number of Up slots that passes. */
export const upNeeded = (threshold: bigint, n: bigint) => (threshold * n + 99n) / 100n

type Parties = Pick<Rental, 'renter' | 'provider' | 'price' | 'compliant'>
/** Who gets the escrow once the result is frozen by settle(). */
export const payeeOf = (r: Parties) => ({ role: (r.compliant ? 'provider' : 'renter') as 'provider' | 'renter', address: r.compliant ? r.provider : r.renter })

/** "Provider paid 0.01 MON" / "Renter refunded 0.01 MON"; proposed wording until finalize has run. */
export function outcomeText(r: Parties, finalized: boolean): string {
  const amount = mon(r.price)
  if (r.compliant) return finalized ? `Provider paid ${amount}` : `Proposed: provider will be paid ${amount}`
  return finalized ? `Renter refunded ${amount}` : `Proposed: renter will be refunded ${amount}`
}

/** One line saying which account can do what next. */
export function nextAction(phase: number, r: Parties, me?: string): string {
  switch (phase) {
    case 1: return 'Nothing to do yet. The team-run oracle reports each slot after it completes.'
    case 2: return 'Nothing to do yet. The team-run oracle reports each slot after it completes.'
    case 3: return 'Last reports can still arrive. Settle opens for any wallet when reporting closes.'
    case 4: return 'Any wallet can settle.'
    case 5: return 'The renter or the provider can log an objection (record only). Any wallet can finalize when the window closes.'
    case 6: return 'Any wallet can finalize.'
    case 7: {
      const p = payeeOf(r)
      return sameAddr(me, p.address) ? 'You are the payee — withdraw on the Withdraw page.' : `Connect as the ${p.role} ${short(p.address)} to withdraw.`
    }
    default: return ''
  }
}

/** Finalized rentals where `me` is a party but the other party holds the credit. */
export function withdrawHints(rows: { id: bigint; rental: Rental; phase: number }[], me?: string) {
  if (!me) return []
  return rows
    .filter(({ rental, phase }) => phase === 7 && roleOf(me, rental) !== 'third party' && !sameAddr(me, payeeOf(rental).address))
    .map(({ id, rental }) => ({ id, ...payeeOf(rental), amount: rental.price }))
}

/** Time range of slot k: [start + k*interval, start + (k+1)*interval). */
export function slotRange(start: bigint, interval: bigint, k: number): { from: number; to: number } {
  const from = Number(start) + k * Number(interval)
  return { from, to: from + Number(interval) }
}

/** VITE_DEMO_PROVIDERS = "Node A=0xabc…,Node B=0xdef…" -> quick-pick entries. Invalid entries are dropped. Public addresses only. */
export function parseDemoProviders(raw: string | undefined): { label: string; address: Address }[] {
  return (raw ?? '')
    .split(',')
    .map((part) => {
      const i = part.lastIndexOf('=')
      return i < 0 ? { label: '', address: part.trim() } : { label: part.slice(0, i).trim(), address: part.slice(i + 1).trim() }
    })
    .filter((e) => isAddress(e.address))
    .map((e) => ({ label: e.label || short(e.address), address: e.address as Address }))
}

/** "Start at the same time as rental #N": usable only while that start is still far enough ahead. */
export function sameStartCheck(other: { start: bigint } | undefined, id: string, now: number): { start?: bigint; error?: string } {
  if (!/^\d+$/.test(id.trim()) || id.trim() === '0') return { error: 'Enter the rental number to share a start with' }
  if (!other) return { error: `Rental #${id.trim()} was not found` }
  const lead = Number(other.start) - now
  if (lead <= 0) return { error: `Rental #${id.trim()} has already started — a new rental cannot start in the past` }
  if (lead < MIN_START_LEAD) return { error: `Rental #${id.trim()} starts in ${lead} s — too late to get a transaction in before it` }
  return { start: other.start }
}

export type CreateForm = { provider: string; threshold: string; interval: string; slots: string; delay: string; price: string }
export type CreateArgs = { provider: Address; threshold: bigint; interval: bigint; slots: bigint; delay?: bigint; start?: bigint; value: bigint }

const int = (s: string) => (/^\d+$/.test(s.trim()) ? BigInt(s.trim()) : null)

/**
 * Client-side check of every SPEC C-rule, in the contract's order.
 * `delay` = seconds after the latest block; `fixed` replaces it with a start shared with another rental.
 */
export function validateCreate(f: CreateForm, self?: Address, fixed?: { start?: bigint; error?: string }): { errors: string[]; args?: CreateArgs } {
  const errors: string[] = []
  const threshold = int(f.threshold), interval = int(f.interval), slots = int(f.slots), delay = int(f.delay)
  let value: bigint | null = null
  try { value = parseEther(f.price.trim() || '0') } catch { value = null }

  if (fixed) { if (fixed.error || fixed.start === undefined) errors.push(fixed.error ?? 'Shared start is not available') } // C-1.1
  else if (delay === null) errors.push('Start delay must be a whole number of seconds') // C-1.1
  if (slots === null || slots < 1n) errors.push('Slot count must be at least 1') // C-1.2
  if (interval === null || interval < 1n) errors.push('Slot length must be at least 1 s') // C-1.3 (C-1.4 holds by construction)
  if (threshold === null || threshold < 1n || threshold > 100n) errors.push('Threshold must be a whole number from 1 to 100') // C-1.5
  const p = f.provider.trim()
  if (!isAddress(p) || /^0x0{40}$/i.test(p)) errors.push('Provider address is not valid') // C-1.6
  else if (self && p.toLowerCase() === self.toLowerCase()) errors.push('Renter and provider must be different wallets (switch to the renter account)') // C-1.7
  if (value === null || value <= 0n) errors.push('Price must be greater than 0') // C-1.8
  if (slots !== null && slots > BigInt(MAX_SLOTS)) errors.push(`Slot count can be at most ${MAX_SLOTS}`) // C-1.9
  if (!fixed && delay !== null && delay > BigInt(MAX_START_DELAY)) errors.push('Start can be at most 30 days ahead') // C-1.11
  if (interval !== null && interval > BigInt(MAX_INTERVAL)) errors.push('Slot length can be at most 86,400 s (1 day)') // C-1.12

  if (errors.length) return { errors }
  return { errors, args: { provider: p as Address, threshold: threshold!, interval: interval!, slots: slots!, delay: fixed ? undefined : delay!, start: fixed?.start, value: value! } }
}

/** Monad's public RPC rejects eth_getLogs over more than 100 blocks. */
export const LOG_CHUNK = 100n

/** Inclusive [from, to] block ranges of at most `size` blocks covering from..to, in ascending order. */
export function chunkRanges(from: bigint, to: bigint, size: bigint = LOG_CHUNK): [bigint, bigint][] {
  const out: [bigint, bigint][] = []
  for (let lo = from; lo <= to; lo += size) out.push([lo, lo + size - 1n < to ? lo + size - 1n : to])
  return out
}

/** Wait before retry n (1-based) after RPC errors / 429: 2 s, 4 s, 8 s … capped at 60 s. */
export const backoffMs = (failures: number) => Math.min(60_000, 1000 * 2 ** Math.max(1, failures))

// Contract revert string -> message shown to the user (UI_HANDOFF §4, in English).
const REVERTS: Record<string, string> = {
  'start in past': 'The start time has passed — try again',
  'end before start': 'Duration settings are not valid',
  'zero interval': 'Duration settings are not valid',
  'not multiple': 'Duration settings are not valid',
  'too many slots': 'Duration settings are not valid',
  'start too far': 'Start can be at most 30 days ahead',
  'interval too long': 'Slot length can be at most 86,400 s (1 day)',
  'bad threshold': 'Threshold must be between 1 and 100',
  'zero provider': 'Provider address is not valid',
  'renter is provider': 'Renter and provider must be different wallets (switch to the renter account)',
  'no value': 'Price cannot be 0',
  'not active': 'This rental is already settled (or no such rental exists)',
  'too early': 'Reporting has not closed yet',
  'not proposed': 'Settle first / already finalized',
  'window closed': 'The challenge window has closed',
  'not a party': 'Only the renter or the provider can log an objection',
  'already objected': 'You already logged an objection',
  'window open': 'The challenge window has not closed yet',
  'nothing to withdraw': 'Nothing to withdraw',
  'transfer failed': 'The payment could not be sent to the receiving address (it rejects MON). The credit is still there',
}

/** Turns any thrown wallet / RPC error into one user-facing line. */
export function revertMessage(err: unknown): string {
  const text = [(err as { shortMessage?: string })?.shortMessage, (err as Error)?.message, String(err)].filter(Boolean).join(' | ')
  // Longest key first, so a short key never shadows a longer match.
  for (const key of Object.keys(REVERTS).sort((a, b) => b.length - a.length)) if (text.includes(key)) return REVERTS[key]
  if (/user rejected|user denied|rejected the request/i.test(text)) return 'Transaction rejected in the wallet'
  if (/chain mismatch|does not match the target chain/i.test(text)) return 'Wallet is on the wrong network — switch to Monad Testnet'
  if (/insufficient funds|reserve/i.test(text)) return 'Insufficient balance (mind the Monad 10 MON reserve rule)'
  return (err as { shortMessage?: string })?.shortMessage || 'Transaction failed'
}
