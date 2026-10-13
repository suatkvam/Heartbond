import { useState } from 'react'
import { hexToString, parseEventLogs, stringToHex } from 'viem'
import { useAccount, useBalance, usePublicClient } from 'wagmi'
import { ABI, DEMO_PROVIDERS, MOCK, addrUrl, monad, txUrl } from './config'
import { useChainNow, useCredits, useCreditsOf, useEvents, useRental, useRentalList, useTx, useWindows } from './hooks'
import {
  RESERVE_WEI, fmtClock, isCompliant, mon, nextAction, outcomeText, payeeOf, phaseBanner, phaseDeadline, roleOf, sameAddr,
  sameStartCheck, short, upNeeded, validateCreate, withdrawHints, type CreateForm,
} from './lib/logic'
import { ActivityFeed, OraclePanel, Skeleton, Slots, Stepper, TxStatus, UptimeBar } from './parts'

const PHASE_LABEL = ['Not found', 'Scheduled', 'Running', 'Reporting grace', 'Ready to settle', 'Challenge window', 'Ready to finalize', 'Settled']
const Addr = ({ a }: { a: string }) => <a href={addrUrl(a)} target="_blank" rel="noreferrer" className="mono">{short(a)}</a>
const when = (ts: bigint | number) => new Date(Number(ts) * 1000).toLocaleString('en-GB')

/** Wallet connected and on Monad Testnet? Otherwise the reason actions are disabled. */
function useReady() {
  const { address, isConnected, chainId } = useAccount()
  const blocked = !isConnected ? 'Connect a wallet first' : chainId !== monad.id ? 'Switch the wallet to Monad Testnet' : MOCK ? 'No transactions in mock mode' : null
  return { address, blocked }
}

// ------------------------------------------------------------------ list
export function ListScreen() {
  const { data, isLoading, error } = useRentalList()
  return (
    <section className="card">
      <div className="head"><h2>Rentals</h2><a className="button" href="#/create">Create rental</a></div>
      {isLoading && <div className="stack"><Skeleton h={44} /><Skeleton h={44} /><Skeleton h={44} /></div>}
      {error && !data && <p className="muted">RPC busy, retrying…</p>}
      {data && data.rows.length === 0 && (
        <div className="emptystate">
          <div className="slots sm">{[0, 0, 0, 0].map((_, i) => <span key={i} className="slot s0" />)}</div>
          <p>No rentals yet.</p>
          <a className="button primary" href="#/create">Create the first rental</a>
        </div>
      )}
      {data && data.rows.length > 0 && (
        <table>
          <thead><tr><th>#</th><th>Status</th><th>Slots</th><th>Uptime</th><th>Outcome</th><th>Renter</th><th>Provider</th><th>Price</th></tr></thead>
          <tbody>
            {data.rows.map(({ id, rental, phase, slots }) => (
              <tr key={id.toString()} className="row" onClick={() => (location.hash = `#/rental/${id}`)}>
                <td><a href={`#/rental/${id}`} className="mono">#{id.toString()}</a></td>
                <td><span className={`pill phase-${phase}`}>{PHASE_LABEL[phase]}</span></td>
                <td><Slots slots={slots} start={rental.start} interval={rental.interval} size="sm" /></td>
                <td className="mono">{rental.up_count.toString()}/{rental.n_slots.toString()} <span className="muted">needs {upNeeded(rental.threshold, rental.n_slots).toString()}</span></td>
                <td>{phase >= 5 ? <span className={rental.compliant ? 'oktext' : 'badtext'}>{outcomeText(rental, phase === 7)}</span> : <span className="muted">—</span>}</td>
                <td className="mono">{short(rental.renter)}</td>
                <td className="mono">{short(rental.provider)}</td>
                <td className="mono">{mon(rental.price)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {data && data.total > data.rows.length && <p className="muted">Showing the newest {data.rows.length} of {data.total}. Open an older one with <code>#/rental/&lt;id&gt;</code> in the address bar.</p>}
    </section>
  )
}

// ------------------------------------------------------------------ create
export function CreateScreen() {
  const { address, blocked } = useReady()
  const pc = usePublicClient()
  const now = useChainNow()
  const { data: balance } = useBalance({ address, chainId: monad.id })
  const { tx, send, busy } = useTx()
  const [f, setF] = useState<CreateForm>({ provider: '', threshold: '75', interval: '30', slots: '4', delay: '20', price: '0.01' })
  const [spec, setSpec] = useState('RTX 4090 24GB')
  const [mode, setMode] = useState<'delay' | 'same'>('delay')
  const [sameId, setSameId] = useState('')
  const set = (k: keyof CreateForm) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value })

  // "Start at the same time as rental #N" (two overlapping demo rentals)
  const other = useRental(mode === 'same' && /^\d+$/.test(sameId.trim()) ? BigInt(sameId.trim()) : 0n)
  const fixed = mode !== 'same' ? undefined : other.isLoading ? { error: `Loading rental #${sameId.trim()}…` } : sameStartCheck(other.notFound ? undefined : other.data?.rental, sameId, now)

  const { errors, args } = validateCreate(f, address, fixed)
  if (new TextEncoder().encode(spec).length > 32) errors.push('GPU description can be at most 32 bytes')
  const reserveRisk = !!args && !!balance && balance.value - args.value < RESERVE_WEI

  async function submit() {
    if (!args || !pc || errors.length) return
    // start comes from the chain: a shared start, or the latest block timestamp plus the delay (C-1.1)
    const start = args.start ?? (await pc.getBlock()).timestamp + args.delay!
    const end = start + args.interval * args.slots
    const receipt = await send('create_rental', [args.provider, args.threshold, args.interval, start, end, stringToHex(spec, { size: 32 })], args.value)
    if (!receipt) return
    const created = parseEventLogs({ abi: ABI, logs: receipt.logs, eventName: 'RentalCreated' })[0]
    const id = (created?.args as { rental_id?: bigint } | undefined)?.rental_id
    if (id !== undefined) location.hash = `#/rental/${id}`
  }

  return (
    <section className="card">
      <h2>Create rental</h2>
      <p className="muted">
        You are the <b>renter</b>: the connected wallet pays the price, which is locked in the contract in the same transaction.
        The <b>provider is just an address</b> that gets paid if uptime meets the threshold — the provider does not need to connect or sign anything.
      </p>

      <div className="form">
        <label className="wide">Provider address
          <input value={f.provider} onChange={set('provider')} placeholder="0x…" spellCheck={false} />
          {DEMO_PROVIDERS.length > 0 && (
            <span className="picks">
              Demo providers:{' '}
              {DEMO_PROVIDERS.map((p) => (
                <button key={p.address} type="button" disabled={sameAddr(p.address, address)} title={sameAddr(p.address, address) ? 'This is the connected wallet' : p.address} onClick={() => setF({ ...f, provider: p.address })}>
                  {p.label} · {short(p.address)}
                </button>
              ))}
            </span>
          )}
        </label>
        <label>Uptime threshold (%)<input value={f.threshold} onChange={set('threshold')} inputMode="numeric" /></label>
        <label>Price (MON)<input value={f.price} onChange={set('price')} inputMode="decimal" /></label>
        <label>Slot length (s, max 86,400)<input value={f.interval} onChange={set('interval')} inputMode="numeric" /></label>
        <label>Slot count (max 256)<input value={f.slots} onChange={set('slots')} inputMode="numeric" /></label>
        <label className="wide">GPU description (display only)<input value={spec} onChange={(e) => setSpec(e.target.value)} /></label>
      </div>

      <fieldset>
        <legend>Start</legend>
        <label className="inline">
          <input type="radio" checked={mode === 'delay'} onChange={() => setMode('delay')} /> Seconds after the latest block (max 30 days)
          <input className="narrow" value={f.delay} onChange={set('delay')} inputMode="numeric" disabled={mode !== 'delay'} />
        </label>
        <label className="inline">
          <input type="radio" checked={mode === 'same'} onChange={() => setMode('same')} /> Start at the same time as rental #
          <input className="narrow" value={sameId} onChange={(e) => setSameId(e.target.value)} inputMode="numeric" disabled={mode !== 'same'} placeholder="N" />
        </label>
        {mode === 'same' && fixed?.start !== undefined && (
          <p>Rental <span className="mono">#{sameId.trim()}</span> starts at {when(fixed.start)} — in {fmtClock(Number(fixed.start) - now)}. This rental will use the same start, so their slots complete together.</p>
        )}
      </fieldset>

      {args && (
        <p className="muted">
          Runs for {fmtClock(Number(args.interval * args.slots))}. To meet the threshold at least {upNeeded(args.threshold, args.slots).toString()} of {args.slots.toString()} slots must be reported UP;
          a slot with no report counts as DOWN.
        </p>
      )}
      {errors.length > 0 && <ul className="err">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
      {reserveRisk && (
        <p className="notice">
          Warning: after paying, your balance drops below 10 MON ({mon(balance!.value)} − {mon(args!.value)}). Monad's reserve-balance rule will most likely revert this transaction.
        </p>
      )}
      <p className="muted">The team-run oracle only reports rentals whose renter wallet is on its allow-list and whose provider has a configured node. Any other rental gets no reports and refunds the renter.</p>

      <div className="actions">
        <button className="primary" disabled={!!blocked || busy || errors.length > 0} onClick={submit}>
          {busy ? 'Sending…' : `Create and lock ${f.price || '0'} MON`}
        </button>
        {blocked && <span className="muted">{blocked}</span>}
      </div>
      <TxStatus tx={tx} label="create_rental" />
    </section>
  )
}

// ------------------------------------------------------------------ detail
export function DetailScreen({ id }: { id: bigint }) {
  const { address, blocked } = useReady()
  const { data, isLoading, error, notFound } = useRental(id)
  const now = useChainNow()
  const { grace, window } = useWindows()
  const { data: myCredits } = useCredits(address)
  const history = useEvents(id, data ? [data.rental.renter, data.rental.provider] : [])
  const settle = useTx(), object = useTx(), finalize = useTx()

  if (isLoading)
    return (
      <div className="stack">
        <Skeleton h={36} w={260} /><Skeleton h={56} />
        <div className="cols"><div className="stack"><Skeleton h={300} /><Skeleton h={120} /></div><Skeleton h={420} /></div>
      </div>
    )
  // a failed refresh keeps the last good data on screen; only a first load with no data is an error
  if (error && !data) return <section className="card"><p className="muted">RPC busy, retrying… <span className="mono small">{error.message.split('\n')[0]}</span></p></section>
  if (!data || notFound)
    return (
      <section className="card emptystate">
        <h2>Rental <span className="mono">#{id.toString()}</span> not found</h2>
        <p className="muted">No rental with this number exists on this contract.</p>
        <a className="button" href="#/">Back to rentals</a>
      </section>
    )

  const { rental: r, slots, phase, preview } = data
  const role = roleOf(address, r)
  const isParty = role === 'renter' || role === 'provider'
  const deadline = phaseDeadline(phase, r, grace, window)
  const left = deadline === null ? null : Math.max(0, deadline - now)
  const frozen = phase >= 5 // settle() already froze the result
  const pass = frozen ? r.compliant : isCompliant(r.up_count, r.threshold, r.n_slots)
  const alreadyObjected = (role === 'renter' && r.renter_objected) || (role === 'provider' && r.provider_objected)
  const liveIndex = phase === 2 ? Math.floor((now - Number(r.start)) / Number(r.interval)) : undefined
  const outcomeEvent = [...history.events].reverse().find((e) => e.name === (phase === 7 ? 'SettlementFinalized' : 'SettlementProposed'))
  const txBySlot = Object.fromEntries(history.events.filter((e) => e.name === 'UptimeReported').map((e) => [Number(e.args.slot), e.tx]))
  const payee = payeeOf(r)
  // headline without its clock, so the countdown can be set in mono
  const clock = left === null ? '' : fmtClock(left)
  const headline = phaseBanner(phase, left)
  const headText = clock && headline.endsWith(clock) ? headline.slice(0, -clock.length) : headline
  let spec = ''
  try { spec = hexToString(r.spec_ref, { size: 32 }) } catch { /* not text */ }

  return (
    <div className="stack">
      <div className="pagehead">
        <h1>Rental <span className="mono">#{id.toString()}</span></h1>
        <span className={`tag role-${role.replace(' ', '-')}`}>You: {role}</span>
        {spec && <span className="muted">{spec}</span>}
      </div>

      <Stepper phase={phase} left={left} />

      <div className="cols">
        <div className="stack">
          <section className="card hero">
            <div className="herohead">
              <div>
                <div className={clock ? 'label' : 'lead'}>{headText.trim()}{left === 0 && deadline !== null ? ' — waiting for the next block' : ''}</div>
                {clock && <div className="bignum mono">{clock}</div>}
              </div>
              <div className="right">
                <div className="label">Uptime</div>
                <div className={`bignum mono ${pass ? 'oktext' : 'badtext'}`}>{r.up_count.toString()}/{r.n_slots.toString()} UP</div>
              </div>
            </div>

            <Slots slots={slots} start={r.start} interval={r.interval} liveIndex={liveIndex} txBySlot={txBySlot} />
            <UptimeBar up={r.up_count} n={r.n_slots} threshold={r.threshold} pass={pass} />
            <p className="muted">
              Needs at least <span className="mono">{upNeeded(r.threshold, r.n_slots).toString()}/{r.n_slots.toString()}</span> UP ·{' '}
              <span className="mono">{r.reported_count.toString()}</span> reported ·{' '}
              <span className={pass ? 'oktext' : 'badtext'}>{pass ? 'threshold met' : 'threshold not met'}</span>
              {!frozen && ' so far — a slot with no report counts as DOWN'}
            </p>
            <p className="next">{nextAction(phase, r, address)}</p>

            <div className="actions">
              {phase === 4 && <button className="primary" disabled={!!blocked || settle.busy} onClick={() => settle.send('settle', [id])}>Settle</button>}
              {phase === 5 && isParty && (
                <button disabled={!!blocked || object.busy || alreadyObjected} onClick={() => object.send('raise_objection', [id])}>
                  {alreadyObjected ? 'Your objection is logged' : 'Log an objection (record only)'}
                </button>
              )}
              {phase === 6 && <button className="primary" disabled={!!blocked || finalize.busy} onClick={() => finalize.send('finalize', [id])}>Finalize</button>}
              {phase === 7 && (myCredits ?? 0n) > 0n && <a className="button primary" href="#/withdraw">Withdraw your {mon(myCredits!)}</a>}
              {blocked && phase >= 4 && phase <= 6 && <span className="muted">{blocked}</span>}
            </div>
            <TxStatus tx={settle.tx} label="settle" />
            <TxStatus tx={object.tx} label="raise_objection" />
            <TxStatus tx={finalize.tx} label="finalize" />
          </section>

          {frozen ? (
            <section className={`card outcome ${r.compliant ? 'ok' : 'bad'}`}>
              <div className="label">{phase === 7 ? 'Outcome' : 'Proposed outcome'}</div>
              <div className="bignum">{outcomeText(r, phase === 7).replace('Proposed: ', '')}</div>
              <p className="muted">
                {payee.role === 'provider' ? 'Provider' : 'Renter'} <Addr a={payee.address} />
                {phase === 7 ? ' holds this as a credit in the contract until it withdraws.' : ' is credited when anyone finalizes after the challenge window.'}
                {outcomeEvent && (
                  <> {phase === 7 ? 'Finalized' : 'Settled'} by <Addr a={outcomeEvent.args.caller as string} /> · <a href={txUrl(outcomeEvent.tx)} target="_blank" rel="noreferrer">view on Monadscan ↗</a></>
                )}
              </p>
              {(r.renter_objected || r.provider_objected) && (
                <p className="muted">
                  Objection log: {[r.renter_objected && 'renter objected', r.provider_objected && 'provider objected'].filter(Boolean).join(', ')} — a record only, it does not change the outcome.
                </p>
              )}
            </section>
          ) : (
            <section className="card">
              <div className="label">If settled with the record so far</div>
              <p className="preview"><span className="mono">{mon(preview.amount)}</span> → {preview.compliant ? 'provider' : 'renter (refund)'} <Addr a={preview.payee} /></p>
            </section>
          )}

          <section className="card">
            <dl className="facts">
              <div><dt>Renter · pays</dt><dd><Addr a={r.renter} /></dd></div>
              <div><dt>Provider · paid if uptime holds</dt><dd><Addr a={r.provider} /></dd></div>
              <div><dt>Price</dt><dd className="mono">{mon(r.price)}</dd></div>
              <div><dt>Threshold</dt><dd className="mono">{r.threshold.toString()}%</dd></div>
              <div><dt>Slots</dt><dd className="mono">{r.n_slots.toString()} × {r.interval.toString()} s</dd></div>
              <div><dt>Start</dt><dd className="mono">{when(r.start)}</dd></div>
              <div><dt>End</dt><dd className="mono">{when(r.end)}</dd></div>
            </dl>
          </section>

          <OraclePanel id={id} nSlots={slots.length} />
        </div>

        <ActivityFeed {...history} mock={MOCK} />
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ withdraw
export function WithdrawScreen() {
  const { address, blocked } = useReady()
  const { data: credits, isLoading } = useCredits(address)
  const { data: list } = useRentalList()
  const { tx, send, busy } = useTx()
  // Rentals where the connected wallet is a party but the other party was paid.
  const hints = withdrawHints(list?.rows ?? [], address)
  const { data: held } = useCreditsOf(hints.map((h) => h.address))
  const open = hints.filter((h) => !held || (held[h.address.toLowerCase()] ?? 0n) > 0n)

  return (
    <section className="card">
      <h2>Withdraw</h2>
      <p className="muted">Finalize does not send MON; it credits the payee inside the contract. Only the credited account can withdraw its own credit (pull payment).</p>
      {!address && <p>Connect a wallet to see its credit.</p>}
      {address && (
        <div className="creditbox">
          <span className="label">Credit of <Addr a={address} /></span>
          {MOCK ? <span className="bignum mono">—</span> : isLoading || credits === undefined ? <Skeleton h={52} w={220} /> : <span className="bignum mono">{mon(credits)}</span>}
        </div>
      )}
      <div className="actions">
        <button className="primary" disabled={!!blocked || busy || !credits} onClick={() => send('withdraw')}>{busy ? 'Sending…' : 'Withdraw'}</button>
        {blocked && <span className="muted">{blocked}</span>}
        {!blocked && credits === 0n && <span className="muted">Nothing to withdraw for this wallet.</span>}
      </div>
      <TxStatus tx={tx} label="withdraw" />

      {address && !credits && open.length > 0 && (
        <div className="notice">
          <b>Looking for a payout?</b> This wallet has no credit, but it is a party to:
          <ul>
            {open.map((h) => (
              <li key={h.id.toString()}>
                <a href={`#/rental/${h.id}`}>Rental #{h.id.toString()}</a> — {h.role === 'provider' ? 'the provider was paid' : 'the renter was refunded'} {mon(h.amount)}.
                Connect as the {h.role} <Addr a={h.address} /> to withdraw.
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
