import { describe, expect, it } from 'vitest'
import {
  backoffMs, chunkRanges, computePhase, fmtClock, isCompliant, nextAction, outcomeText, parseDemoProviders, payeeOf, phaseBanner, phaseDeadline,
  revertMessage, roleOf, sameStartCheck, slotRange, upNeeded, validateCreate, withdrawHints, type Rental,
} from './logic'

const ok = { provider: '0x2222222222222222222222222222222222222222', threshold: '75', interval: '30', slots: '4', delay: '20', price: '0.01' }
const self = '0x1111111111111111111111111111111111111111' as const
const RENTER = '0x1111111111111111111111111111111111111111' as const
const PROVIDER = '0x101c0000000000000000000000000000000003c6' as const
const STRANGER = '0x3333333333333333333333333333333333333333' as const
const rental = (patch: Partial<Rental> = {}): Rental => ({
  renter: RENTER, provider: PROVIDER, price: 10n ** 16n, threshold: 75n, interval: 30n, start: 100n, end: 220n, n_slots: 4n,
  up_count: 4n, reported_count: 4n, status: 3, proposed_at: 300n, compliant: true, renter_objected: false, provider_objected: false,
  spec_ref: '0x00', ...patch,
})

describe('validateCreate (SPEC C-rules)', () => {
  it('accepts the demo defaults', () => {
    const r = validateCreate(ok, self)
    expect(r.errors).toEqual([])
    expect(r.args?.value).toBe(10n ** 16n)
    expect(r.args?.delay).toBe(20n)
    expect(r.args?.start).toBeUndefined()
  })
  it('accepts every boundary', () => {
    expect(validateCreate({ ...ok, threshold: '1', interval: '86400', slots: '256', delay: '2592000' }, self).errors).toEqual([])
    expect(validateCreate({ ...ok, threshold: '100', interval: '1', slots: '1', delay: '0' }, self).errors).toEqual([])
  })
  it.each([
    ['threshold 0', { threshold: '0' }],
    ['threshold 101', { threshold: '101' }],
    ['interval 0', { interval: '0' }],
    ['interval 86401 (C-1.12)', { interval: '86401' }],
    ['slots 0', { slots: '0' }],
    ['slots 257 (C-1.9)', { slots: '257' }],
    ['delay 30 days + 1 (C-1.11)', { delay: '2592001' }],
    ['price 0', { price: '0' }],
    ['price not a number', { price: 'abc' }],
    ['zero provider', { provider: '0x0000000000000000000000000000000000000000' }],
    ['bad provider', { provider: '0x123' }],
    ['renter is provider', { provider: self }],
    ['negative / non-integer', { interval: '-5' }],
  ])('rejects %s', (_name, patch) => {
    const r = validateCreate({ ...ok, ...patch }, self)
    expect(r.errors.length).toBeGreaterThan(0)
    expect(r.args).toBeUndefined()
  })
  it('blocks a connected wallet that equals the provider with the role message', () => {
    expect(validateCreate({ ...ok, provider: self.toUpperCase().replace('0X', '0x') }, self).errors).toEqual([
      'Renter and provider must be different wallets (switch to the renter account)',
    ])
  })
  it('uses a shared start instead of the delay', () => {
    const r = validateCreate({ ...ok, delay: 'ignored' }, self, { start: 1234n })
    expect(r.errors).toEqual([])
    expect(r.args?.start).toBe(1234n)
    expect(r.args?.delay).toBeUndefined()
  })
  it('passes the shared-start reason through as an error', () => {
    const r = validateCreate(ok, self, { error: 'Rental #7 has already started' })
    expect(r.errors).toEqual(['Rental #7 has already started'])
    expect(r.args).toBeUndefined()
  })
})

describe('sameStartCheck', () => {
  it('accepts a start far enough ahead, on the boundary too', () => {
    expect(sameStartCheck({ start: 1100n }, '3', 1000)).toEqual({ start: 1100n })
    expect(sameStartCheck({ start: 1005n }, '3', 1000)).toEqual({ start: 1005n })
  })
  it('explains why not', () => {
    expect(sameStartCheck({ start: 1004n }, '3', 1000).error).toMatch(/starts in 4 s/)
    expect(sameStartCheck({ start: 1000n }, '3', 1000).error).toMatch(/already started/)
    expect(sameStartCheck({ start: 900n }, '3', 1000).error).toMatch(/already started/)
    expect(sameStartCheck(undefined, '9', 1000).error).toBe('Rental #9 was not found')
    expect(sameStartCheck({ start: 1100n }, '', 1000).error).toMatch(/Enter the rental number/)
    expect(sameStartCheck({ start: 1100n }, '0', 1000).error).toMatch(/Enter the rental number/)
  })
})

describe('phase (same edges as the contract view)', () => {
  const r = { status: 1, start: 100n, end: 220n, proposed_at: 0n }
  it('walks Active phases on both sides of each edge', () => {
    expect(computePhase(r, 99)).toBe(1)
    expect(computePhase(r, 100)).toBe(2)
    expect(computePhase(r, 219)).toBe(2)
    expect(computePhase(r, 220)).toBe(3)
    expect(computePhase(r, 250)).toBe(3) // end + REPORT_GRACE inclusive
    expect(computePhase(r, 251)).toBe(4)
  })
  it('walks Proposed / Settled', () => {
    const p = { ...r, status: 2, proposed_at: 300n }
    expect(computePhase(p, 359)).toBe(5)
    expect(computePhase(p, 360)).toBe(6)
    expect(computePhase({ ...p, status: 3 }, 1)).toBe(7)
    expect(computePhase({ ...p, status: 0 }, 1)).toBe(0)
  })
  it('gives the countdown target per phase', () => {
    expect(phaseDeadline(1, r)).toBe(100)
    expect(phaseDeadline(2, r)).toBe(220)
    expect(phaseDeadline(3, r)).toBe(251)
    expect(phaseDeadline(5, { ...r, proposed_at: 300n })).toBe(360)
    expect(phaseDeadline(4, r)).toBeNull()
  })
})

describe('banner and clock', () => {
  it('formats countdowns', () => {
    expect(fmtClock(23)).toBe('0:23')
    expect(fmtClock(0)).toBe('0:00')
    expect(fmtClock(-3)).toBe('0:00')
    expect(fmtClock(725)).toBe('12:05')
    expect(fmtClock(3723)).toBe('1:02:03')
    expect(fmtClock(3 * 86400 + 4 * 3600 + 5)).toBe('3d 4h')
  })
  it('writes the phase headline', () => {
    expect(phaseBanner(1, 12)).toBe('Starts in 0:12')
    expect(phaseBanner(3, 23)).toBe('Reporting closes in 0:23')
    expect(phaseBanner(4, null)).toBe('Ready to settle — anyone can call it')
    expect(phaseBanner(5, 41)).toBe('Challenge window 0:41')
    expect(phaseBanner(6, null)).toBe('Ready to finalize — anyone can call it')
    expect(phaseBanner(7, null)).toBe('Settled')
  })
  it('gives the time range of a slot', () => {
    expect(slotRange(100n, 30n, 0)).toEqual({ from: 100, to: 130 })
    expect(slotRange(100n, 30n, 3)).toEqual({ from: 190, to: 220 })
  })
})

describe('roles, outcome and next action', () => {
  it('names the connected wallet role', () => {
    const r = rental()
    expect(roleOf(RENTER, r)).toBe('renter')
    expect(roleOf(PROVIDER.toLowerCase(), r)).toBe('provider')
    expect(roleOf(STRANGER, r)).toBe('third party')
    expect(roleOf(undefined, r)).toBe('not connected')
  })
  it('names payee and outcome', () => {
    expect(payeeOf(rental())).toEqual({ role: 'provider', address: PROVIDER })
    expect(payeeOf(rental({ compliant: false }))).toEqual({ role: 'renter', address: RENTER })
    expect(outcomeText(rental(), true)).toBe('Provider paid 0.01 MON')
    expect(outcomeText(rental({ compliant: false }), true)).toBe('Renter refunded 0.01 MON')
    expect(outcomeText(rental(), false)).toBe('Proposed: provider will be paid 0.01 MON')
    expect(outcomeText(rental({ compliant: false }), false)).toBe('Proposed: renter will be refunded 0.01 MON')
  })
  it('says who acts next', () => {
    expect(nextAction(4, rental())).toBe('Any wallet can settle.')
    expect(nextAction(6, rental())).toBe('Any wallet can finalize.')
    expect(nextAction(5, rental())).toMatch(/objection \(record only\)/)
    expect(nextAction(7, rental(), RENTER)).toBe('Connect as the provider 0x101c…03c6 to withdraw.')
    expect(nextAction(7, rental(), PROVIDER)).toBe('You are the payee — withdraw on the Withdraw page.')
    expect(nextAction(7, rental({ compliant: false }), STRANGER)).toBe('Connect as the renter 0x1111…1111 to withdraw.')
  })
  it('never promises adjudication', () => {
    for (let p = 0; p <= 7; p++) expect(`${nextAction(p, rental())} ${phaseBanner(p, 5)}`).not.toMatch(/dispute|trustless/i)
  })
})

describe('withdrawHints', () => {
  const rows = [
    { id: 3n, rental: rental(), phase: 7 }, // provider is payee
    { id: 2n, rental: rental({ compliant: false }), phase: 7 }, // renter is payee
    { id: 1n, rental: rental(), phase: 5 }, // not finalized yet
  ]
  it('tells the non-payee party who should connect', () => {
    expect(withdrawHints(rows, RENTER)).toEqual([{ id: 3n, role: 'provider', address: PROVIDER, amount: 10n ** 16n }])
    expect(withdrawHints(rows, PROVIDER)).toEqual([{ id: 2n, role: 'renter', address: RENTER, amount: 10n ** 16n }])
  })
  it('says nothing to third parties or when not connected', () => {
    expect(withdrawHints(rows, STRANGER)).toEqual([])
    expect(withdrawHints(rows, undefined)).toEqual([])
  })
})

describe('parseDemoProviders', () => {
  it('reads label=address pairs and drops bad entries', () => {
    expect(parseDemoProviders(`Node A=${PROVIDER}, Node B = ${STRANGER},broken=0x12,,=`)).toEqual([
      { label: 'Node A', address: PROVIDER },
      { label: 'Node B', address: STRANGER },
    ])
  })
  it('accepts a bare address and an unset variable', () => {
    expect(parseDemoProviders(PROVIDER)).toEqual([{ label: '0x101c…03c6', address: PROVIDER }])
    expect(parseDemoProviders(undefined)).toEqual([])
    expect(parseDemoProviders('')).toEqual([])
  })
})

describe('compliance', () => {
  it('passes on the boundary 100*M == threshold*N', () => {
    expect(isCompliant(3n, 75n, 4n)).toBe(true)
    expect(isCompliant(2n, 75n, 4n)).toBe(false)
    expect(upNeeded(75n, 4n)).toBe(3n)
    expect(upNeeded(1n, 256n)).toBe(3n)
    expect(upNeeded(100n, 4n)).toBe(4n)
  })
})

describe('revertMessage', () => {
  it('maps contract strings', () => {
    expect(revertMessage(new Error('execution reverted: window open'))).toBe('The challenge window has not closed yet')
    expect(revertMessage({ shortMessage: 'The contract function "settle" reverted with the following reason:\ntoo early' })).toBe('Reporting has not closed yet')
    expect(revertMessage(new Error('start too far'))).toBe('Start can be at most 30 days ahead')
    expect(revertMessage(new Error('renter is provider'))).toMatch(/different wallets/)
  })
  it('maps wallet rejection and falls back', () => {
    expect(revertMessage(new Error('User rejected the request.'))).toBe('Transaction rejected in the wallet')
    expect(revertMessage(new Error('boom'))).toBe('Transaction failed')
  })
})

describe('log scan helpers', () => {
  it('splits a range into inclusive chunks of at most 100 blocks', () => {
    expect(chunkRanges(1n, 250n)).toEqual([[1n, 100n], [101n, 200n], [201n, 250n]])
    expect(chunkRanges(1n, 100n)).toEqual([[1n, 100n]])
    expect(chunkRanges(1n, 101n)).toEqual([[1n, 100n], [101n, 101n]])
    expect(chunkRanges(7n, 7n)).toEqual([[7n, 7n]])
    expect(chunkRanges(8n, 7n)).toEqual([]) // nothing new since the last scanned block
    for (const [lo, hi] of chunkRanges(5n, 12_345n)) expect(hi - lo + 1n).toBeLessThanOrEqual(100n)
  })
  it('backs off exponentially and caps at 60 s', () => {
    expect([1, 2, 3, 4, 5].map(backoffMs)).toEqual([2000, 4000, 8000, 16000, 32000])
    expect(backoffMs(6)).toBe(60_000)
    expect(backoffMs(50)).toBe(60_000)
  })
})
