import assert from 'node:assert/strict'
import test from 'node:test'
import { createTestIndexer, TestHelpers } from 'envio'
import '../src/EventHandlers.ts'

const [renter, provider, reporter] = TestHelpers.Addresses.mockAddresses
const base = 70661775
const addr = (value: string) => value.toLowerCase()
const h = (n: number) => `0x${n.toString(16).padStart(64, '0')}`

test('derives a compliant payout and a refunded rental from contract events', async () => {
  const indexer = createTestIndexer()
  const simulate = [
    { contract: 'GpuSlaEscrow', event: 'RentalCreated', block: { number: base, timestamp: 100 }, transaction: { hash: h(1) }, params: { rental_id: 1n, renter, provider, price: 1000n, threshold: 75n, interval: 30n, start: 100n, end: 220n, n_slots: 4n, spec_ref: h(99) } },
    { contract: 'GpuSlaEscrow', event: 'RentalCreated', block: { number: base + 1, timestamp: 101 }, transaction: { hash: h(2) }, params: { rental_id: 2n, renter, provider, price: 2000n, threshold: 75n, interval: 30n, start: 100n, end: 220n, n_slots: 4n, spec_ref: h(99) } },
    ...[0n, 1n, 2n].map((slot, i) => ({ contract: 'GpuSlaEscrow', event: 'UptimeReported', block: { number: base + 2 + i, timestamp: 130 + i }, transaction: { hash: h(3 + i) }, params: { rental_id: 1n, slot, up: true, reporter } })),
    { contract: 'GpuSlaEscrow', event: 'UptimeReported', block: { number: base + 5, timestamp: 134 }, transaction: { hash: h(6) }, params: { rental_id: 2n, slot: 0n, up: true, reporter } },
    { contract: 'GpuSlaEscrow', event: 'SettlementProposed', block: { number: base + 6, timestamp: 300 }, transaction: { hash: h(7) }, params: { rental_id: 1n, up_count: 3n, n_slots: 4n, compliant: true, payee: provider, amount: 1000n, proposed_at: 300n, caller: renter } },
    { contract: 'GpuSlaEscrow', event: 'SettlementFinalized', block: { number: base + 7, timestamp: 360 }, transaction: { hash: h(8) }, params: { rental_id: 1n, payee: provider, amount: 1000n, caller: renter } },
    { contract: 'GpuSlaEscrow', event: 'SettlementProposed', block: { number: base + 8, timestamp: 300 }, transaction: { hash: h(9) }, params: { rental_id: 2n, up_count: 1n, n_slots: 4n, compliant: false, payee: renter, amount: 2000n, proposed_at: 300n, caller: provider } },
    { contract: 'GpuSlaEscrow', event: 'SettlementFinalized', block: { number: base + 9, timestamp: 360 }, transaction: { hash: h(10) }, params: { rental_id: 2n, payee: renter, amount: 2000n, caller: provider } },
  ] as unknown as NonNullable<Parameters<ReturnType<typeof createTestIndexer>['process']>[0]['chains'][10143]>['simulate']

  await indexer.process({ chains: { 10143: { startBlock: base, endBlock: base + 9, simulate } } })

  const compliant = await indexer.Rental.get('10143-1')
  const refunded = await indexer.Rental.get('10143-2')
  assert.equal(compliant?.status, 3)
  assert.equal(compliant?.compliant, true)
  assert.equal(compliant?.payee, addr(provider))
  assert.equal(compliant?.outcomeAmount, 1000n)
  assert.equal(refunded?.status, 3)
  assert.equal(refunded?.compliant, false)
  assert.equal(refunded?.payee, addr(renter))
  assert.equal(refunded?.outcomeAmount, 2000n)
  assert.equal((await indexer.Provider.get(addr(provider)))?.compliantRentals, 1n)
  assert.equal((await indexer.Reporter.get(addr(reporter)))?.reportsSent, 4n)
})
