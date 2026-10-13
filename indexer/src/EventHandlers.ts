import { indexer } from 'envio'

const rentalKey = (chainId: number, id: bigint) => `${chainId}-${id}`
const activityId = (hash: string, logIndex: number) => `${hash}-${logIndex}`

indexer.onEvent({ contract: 'GpuSlaEscrow', event: 'RentalCreated' }, async ({ event, context }) => {
  const id = rentalKey(event.chainId, event.params.rental_id)
  const providerId = event.params.provider.toLowerCase()
  const provider = await context.Provider.get(providerId)
  context.Provider.set({
    id: providerId,
    rentals: (provider?.rentals ?? 0n) + 1n,
    compliantRentals: provider?.compliantRentals ?? 0n,
    totalSlots: (provider?.totalSlots ?? 0n) + event.params.n_slots,
    upSlots: provider?.upSlots ?? 0n,
    uptimePercent: provider?.uptimePercent ?? 0,
  })
  context.Rental.set({
    id,
    rentalNumber: event.params.rental_id,
    renter: event.params.renter.toLowerCase(),
    provider: providerId,
    price: event.params.price,
    threshold: event.params.threshold,
    interval: event.params.interval,
    start: event.params.start,
    end: event.params.end,
    nSlots: event.params.n_slots,
    status: 1,
    upCount: 0n,
    reportedCount: 0n,
    compliant: false,
    renterObjected: false,
    providerObjected: false,
    payee: undefined,
    outcomeAmount: undefined,
    proposedAt: undefined,
    createdAt: BigInt(event.block.timestamp),
    updatedAt: BigInt(event.block.timestamp),
    specRef: event.params.spec_ref,
  })
  context.Activity.set({
    id: activityId(event.transaction.hash, event.logIndex), name: 'RentalCreated', rental_id: id,
    account: undefined, renter: event.params.renter.toLowerCase(), provider: providerId,
    reporter: undefined, caller: undefined, by: undefined, isRenter: undefined,
    slot: undefined, up: undefined, amount: event.params.price, threshold: event.params.threshold,
    interval: event.params.interval, nSlots: event.params.n_slots, upCount: undefined, compliant: undefined,
    payee: undefined, block: BigInt(event.block.number), timestamp: BigInt(event.block.timestamp),
    txHash: event.transaction.hash, logIndex: event.logIndex,
  })
})

indexer.onEvent({ contract: 'GpuSlaEscrow', event: 'UptimeReported' }, async ({ event, context }) => {
  const id = rentalKey(event.chainId, event.params.rental_id)
  const rental = await context.Rental.getOrThrow(id)
  const provider = await context.Provider.getOrThrow(rental.provider)
  const reporterId = event.params.reporter.toLowerCase()
  const reporter = await context.Reporter.get(reporterId)
  const upCount = rental.upCount + (event.params.up ? 1n : 0n)
  const upSlots = provider.upSlots + (event.params.up ? 1n : 0n)
  context.Rental.set({ ...rental, upCount, reportedCount: rental.reportedCount + 1n, updatedAt: BigInt(event.block.timestamp) })
  context.Slot.set({
    id: `${id}-${event.params.slot}`,
    rental_id: id,
    index: event.params.slot,
    up: event.params.up,
    reporter: reporterId,
    txHash: event.transaction.hash,
    block: BigInt(event.block.number),
    timestamp: BigInt(event.block.timestamp),
  })
  context.Provider.set({
    ...provider,
    upSlots,
    uptimePercent: provider.totalSlots === 0n ? 0 : Number((upSlots * 10000n) / provider.totalSlots) / 100,
  })
  context.Reporter.set({ id: reporterId, reportsSent: (reporter?.reportsSent ?? 0n) + 1n })
  context.Activity.set({
    id: activityId(event.transaction.hash, event.logIndex), name: 'UptimeReported', rental_id: id,
    account: undefined, renter: undefined, provider: undefined, reporter: reporterId, caller: undefined,
    by: undefined, isRenter: undefined, slot: event.params.slot, up: event.params.up,
    amount: undefined, threshold: undefined, interval: undefined, nSlots: undefined, upCount: undefined,
    compliant: undefined, payee: undefined, block: BigInt(event.block.number), timestamp: BigInt(event.block.timestamp),
    txHash: event.transaction.hash, logIndex: event.logIndex,
  })
})

indexer.onEvent({ contract: 'GpuSlaEscrow', event: 'SettlementProposed' }, async ({ event, context }) => {
  const id = rentalKey(event.chainId, event.params.rental_id)
  const rental = await context.Rental.getOrThrow(id)
  const provider = await context.Provider.getOrThrow(rental.provider)
  context.Rental.set({
    ...rental,
    status: 2,
    upCount: event.params.up_count,
    nSlots: event.params.n_slots,
    compliant: event.params.compliant,
    payee: event.params.payee.toLowerCase(),
    outcomeAmount: event.params.amount,
    proposedAt: event.params.proposed_at,
    updatedAt: BigInt(event.block.timestamp),
  })
  if (event.params.compliant) context.Provider.set({ ...provider, compliantRentals: provider.compliantRentals + 1n })
  context.Activity.set({
    id: activityId(event.transaction.hash, event.logIndex), name: 'SettlementProposed', rental_id: id,
    account: undefined, renter: undefined, provider: undefined, reporter: undefined, caller: event.params.caller.toLowerCase(),
    by: undefined, isRenter: undefined, slot: undefined, up: undefined, amount: event.params.amount,
    threshold: undefined, interval: undefined, nSlots: event.params.n_slots, upCount: event.params.up_count,
    compliant: event.params.compliant, payee: event.params.payee.toLowerCase(), block: BigInt(event.block.number),
    timestamp: BigInt(event.block.timestamp), txHash: event.transaction.hash, logIndex: event.logIndex,
  })
})

indexer.onEvent({ contract: 'GpuSlaEscrow', event: 'ObjectionRaised' }, async ({ event, context }) => {
  const id = rentalKey(event.chainId, event.params.rental_id)
  const rental = await context.Rental.getOrThrow(id)
  const key = `${event.transaction.hash}-${event.logIndex}`
  context.Objection.set({
    id: key,
    rental_id: id,
    by: event.params.by.toLowerCase(),
    isRenter: event.params.is_renter,
    txHash: event.transaction.hash,
    block: BigInt(event.block.number),
    timestamp: BigInt(event.block.timestamp),
  })
  context.Rental.set({
    ...rental,
    renterObjected: event.params.is_renter ? true : rental.renterObjected,
    providerObjected: event.params.is_renter ? rental.providerObjected : true,
    updatedAt: BigInt(event.block.timestamp),
  })
  context.Activity.set({
    id: key, name: 'ObjectionRaised', rental_id: id, account: undefined, renter: undefined, provider: undefined,
    reporter: undefined, caller: undefined, by: event.params.by.toLowerCase(), isRenter: event.params.is_renter,
    slot: undefined, up: undefined, amount: undefined, threshold: undefined, interval: undefined, nSlots: undefined,
    upCount: undefined, compliant: undefined, payee: undefined, block: BigInt(event.block.number),
    timestamp: BigInt(event.block.timestamp), txHash: event.transaction.hash, logIndex: event.logIndex,
  })
})

indexer.onEvent({ contract: 'GpuSlaEscrow', event: 'SettlementFinalized' }, async ({ event, context }) => {
  const id = rentalKey(event.chainId, event.params.rental_id)
  const rental = await context.Rental.getOrThrow(id)
  context.Rental.set({
    ...rental,
    status: 3,
    payee: event.params.payee.toLowerCase(),
    outcomeAmount: event.params.amount,
    updatedAt: BigInt(event.block.timestamp),
  })
  context.Activity.set({
    id: activityId(event.transaction.hash, event.logIndex), name: 'SettlementFinalized', rental_id: id,
    account: undefined, renter: undefined, provider: undefined, reporter: undefined, caller: event.params.caller.toLowerCase(),
    by: undefined, isRenter: undefined, slot: undefined, up: undefined, amount: event.params.amount,
    threshold: undefined, interval: undefined, nSlots: undefined, upCount: undefined, compliant: undefined,
    payee: event.params.payee.toLowerCase(), block: BigInt(event.block.number), timestamp: BigInt(event.block.timestamp),
    txHash: event.transaction.hash, logIndex: event.logIndex,
  })
})

indexer.onEvent({ contract: 'GpuSlaEscrow', event: 'Withdrawn' }, async ({ event, context }) => {
  const key = `${event.transaction.hash}-${event.logIndex}`
  context.Withdrawal.set({
    id: key,
    account: event.params.account.toLowerCase(),
    amount: event.params.amount,
    txHash: event.transaction.hash,
    block: BigInt(event.block.number),
    timestamp: BigInt(event.block.timestamp),
  })
  context.Activity.set({
    id: key, name: 'Withdrawn', rental_id: undefined, account: event.params.account.toLowerCase(),
    renter: undefined, provider: undefined, reporter: undefined, caller: undefined, by: undefined, isRenter: undefined,
    slot: undefined, up: undefined, amount: event.params.amount, threshold: undefined, interval: undefined,
    nSlots: undefined, upCount: undefined, compliant: undefined, payee: undefined, block: BigInt(event.block.number),
    timestamp: BigInt(event.block.timestamp), txHash: event.transaction.hash, logIndex: event.logIndex,
  })
})
