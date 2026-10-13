// Pure rules shared by the screens. Mirrors docs/SPEC.md §3 and docs/UI_HANDOFF.md §4–§5.
import { isAddress, parseEther, type Address, type Hex } from 'viem'

// Internal contract constants: not in the ABI, so they are fixed here (UI_HANDOFF §4).
export const MAX_SLOTS = 256
export const MAX_INTERVAL = 86_400
export const MAX_START_DELAY = 2_592_000
export const REPORT_GRACE = 30
export const CHALLENGE_WINDOW = 60
/** Monad reserve balance: a value spend that leaves less than this reverts. */
export const RESERVE_WEI = 10n * 10n ** 18n

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
export const PHASE_TR = [
  'Bulunamadı',
  'Planlandı',
  'Çalışıyor',
  'Son raporlar bekleniyor',
  'Settle edilebilir',
  'İtiraz penceresi',
  'Finalize edilebilir',
  'Tamamlandı',
]

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

/** Compliance exactly as S-3: 100 * M >= threshold * N. */
export const isCompliant = (up: bigint, threshold: bigint, n: bigint) => 100n * up >= threshold * n
/** Smallest number of Up slots that passes. */
export const upNeeded = (threshold: bigint, n: bigint) => (threshold * n + 99n) / 100n

export type CreateForm = { provider: string; threshold: string; interval: string; slots: string; delay: string; price: string }
export type CreateArgs = { provider: Address; threshold: bigint; interval: bigint; slots: bigint; delay: bigint; value: bigint }

const int = (s: string) => (/^\d+$/.test(s.trim()) ? BigInt(s.trim()) : null)

/** Client-side check of every SPEC C-rule, in the contract's order. `delay` = seconds after the latest block. */
export function validateCreate(f: CreateForm, self?: Address): { errors: string[]; args?: CreateArgs } {
  const errors: string[] = []
  const threshold = int(f.threshold), interval = int(f.interval), slots = int(f.slots), delay = int(f.delay)
  let value: bigint | null = null
  try { value = parseEther(f.price.trim() || '0') } catch { value = null }

  if (delay === null) errors.push('Başlangıç gecikmesi (sn) tam sayı olmalı') // C-1.1
  if (slots === null || slots < 1n) errors.push('Slot sayısı en az 1 olmalı') // C-1.2
  if (interval === null || interval < 1n) errors.push('Slot süresi en az 1 sn olmalı') // C-1.3 (C-1.4 holds by construction)
  if (threshold === null || threshold < 1n || threshold > 100n) errors.push('Eşik 1–100 arası tam sayı olmalı') // C-1.5
  const p = f.provider.trim()
  if (!isAddress(p) || /^0x0{40}$/i.test(p)) errors.push('Sağlayıcı adresi geçersiz') // C-1.6
  else if (self && p.toLowerCase() === self.toLowerCase()) errors.push('Sağlayıcı, kiracı cüzdanla aynı olamaz') // C-1.7
  if (value === null || value <= 0n) errors.push("Ücret 0'dan büyük olmalı") // C-1.8
  if (slots !== null && slots > BigInt(MAX_SLOTS)) errors.push(`Slot sayısı en fazla ${MAX_SLOTS} olabilir`) // C-1.9
  if (delay !== null && delay > BigInt(MAX_START_DELAY)) errors.push('Başlangıç en fazla 30 gün sonrası olabilir') // C-1.11
  if (interval !== null && interval > BigInt(MAX_INTERVAL)) errors.push('Slot süresi en fazla 86 400 sn (1 gün) olabilir') // C-1.12

  if (errors.length) return { errors }
  return { errors, args: { provider: p as Address, threshold: threshold!, interval: interval!, slots: slots!, delay: delay!, value: value! } }
}

// Contract revert string -> message shown to the user (UI_HANDOFF §4).
const REVERTS: Record<string, string> = {
  'start in past': 'Başlangıç zamanı geçti, tekrar dene',
  'end before start': 'Süre ayarları geçersiz',
  'zero interval': 'Süre ayarları geçersiz',
  'not multiple': 'Süre ayarları geçersiz',
  'too many slots': 'Süre ayarları geçersiz',
  'start too far': 'Başlangıç en fazla 30 gün sonrası olabilir',
  'interval too long': 'Slot süresi en fazla 86 400 sn (1 gün) olabilir',
  'bad threshold': 'Eşik 1–100 arası olmalı',
  'zero provider': 'Sağlayıcı adresi geçersiz',
  'renter is provider': 'Sağlayıcı adresi geçersiz',
  'no value': 'Ücret 0 olamaz',
  'not active': 'Bu kiralama zaten settle edilmiş (ya da böyle bir id yok)',
  'too early': 'Raporlama süresi henüz bitmedi',
  'not proposed': 'Önce settle gerekiyor / zaten finalize edildi',
  'window closed': 'İtiraz süresi doldu',
  'not a party': 'Sadece kiracı veya sağlayıcı itiraz edebilir',
  'already objected': 'Zaten itiraz ettin',
  'window open': 'İtiraz penceresi henüz kapanmadı',
  'nothing to withdraw': 'Çekilecek bakiye yok',
  'transfer failed': 'Ödeme alıcı adrese gönderilemedi (alıcı MON kabul etmiyor). Bakiye duruyor',
}

/** Turns any thrown wallet / RPC error into one user-facing line. */
export function revertMessage(err: unknown): string {
  const text = [(err as { shortMessage?: string })?.shortMessage, (err as Error)?.message, String(err)].filter(Boolean).join(' | ')
  // Longest key first, so "not active" never shadows a longer match.
  for (const key of Object.keys(REVERTS).sort((a, b) => b.length - a.length)) if (text.includes(key)) return REVERTS[key]
  if (/user rejected|user denied|rejected the request/i.test(text)) return 'İşlem cüzdanda reddedildi'
  if (/chain mismatch|does not match the target chain/i.test(text)) return "Cüzdan yanlış ağda — Monad Testnet'e geç"
  if (/insufficient funds|reserve/i.test(text)) return 'Bakiye yetersiz (Monad 10 MON rezerv kuralına dikkat)'
  return (err as { shortMessage?: string })?.shortMessage || 'İşlem başarısız oldu'
}

export const short = (a?: string) => (a ? `${a.slice(0, 6)}…${a.slice(-4)}` : '—')
export const sameAddr = (a?: string, b?: string) => !!a && !!b && a.toLowerCase() === b.toLowerCase()
export function fmtSeconds(s: number): string {
  if (s <= 0) return '0 sn'
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60)
  return [d && `${d} g`, h && `${h} sa`, m && `${m} dk`, `${sec} sn`].filter(Boolean).join(' ')
}
