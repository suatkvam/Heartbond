import { describe, expect, it } from 'vitest'
import { computePhase, isCompliant, phaseDeadline, revertMessage, upNeeded, validateCreate } from './logic'

const ok = { provider: '0x2222222222222222222222222222222222222222', threshold: '75', interval: '30', slots: '4', delay: '20', price: '0.01' }
const self = '0x1111111111111111111111111111111111111111' as const

describe('validateCreate (SPEC C-rules)', () => {
  it('accepts the demo defaults', () => {
    const r = validateCreate(ok, self)
    expect(r.errors).toEqual([])
    expect(r.args?.value).toBe(10n ** 16n)
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
    expect(revertMessage(new Error('execution reverted: window open'))).toBe('İtiraz penceresi henüz kapanmadı')
    expect(revertMessage({ shortMessage: 'The contract function "settle" reverted with the following reason:\ntoo early' })).toBe('Raporlama süresi henüz bitmedi')
    expect(revertMessage(new Error('start too far'))).toBe('Başlangıç en fazla 30 gün sonrası olabilir')
  })
  it('maps wallet rejection and falls back', () => {
    expect(revertMessage(new Error('User rejected the request.'))).toBe('İşlem cüzdanda reddedildi')
    expect(revertMessage(new Error('boom'))).toBe('İşlem başarısız oldu')
  })
})
