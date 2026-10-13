import { useState } from 'react'
import { txUrl } from './config'
import { useOracle, type Ev, type TxState, type useEvents } from './hooks'
import { PHASE, fmtClock, mon, short, slotRange } from './lib/logic'

const hhmmss = (ts: number) => new Date(ts * 1000).toLocaleTimeString('en-GB')

/** Placeholder block for loading states — a screen is never blank. */
export const Skeleton = ({ h = 20, w = '100%' }: { h?: number; w?: number | string }) => <div className="skel" style={{ height: h, width: w }} aria-hidden />

/** pending -> confirmed -> failed, always with the explorer link once a hash exists. */
export function TxStatus({ tx, label }: { tx: TxState; label: string }) {
  if (tx.status === 'idle') return null
  const text = {
    signing: 'Waiting for confirmation in the wallet…',
    pending: 'Sent, waiting for confirmation…',
    confirmed: 'Confirmed',
    failed: `Failed: ${tx.error ?? ''}`,
  }[tx.status]
  return (
    <div className={`tx ${tx.status}`}>
      <span className="mono">{label}</span> <span>{text}</span>
      {tx.hash && <a href={txUrl(tx.hash)} target="_blank" rel="noreferrer" className="mono">{short(tx.hash)} ↗</a>}
    </div>
  )
}

/** Horizontal phase stepper; the current step carries the live countdown. */
export function Stepper({ phase, left }: { phase: number; left: number | null }) {
  return (
    <ol className="stepper" aria-label="Rental phase">
      {PHASE.slice(1).map((name, i) => {
        const n = i + 1
        const state = n < phase ? 'done' : n === phase ? 'current' : 'todo'
        return (
          <li key={name} className={state} aria-current={state === 'current' ? 'step' : undefined}>
            <span className="dot" />
            <span className="name">{name}</span>
            {state === 'current' && left !== null && <span className="mono clock">{fmtClock(left)}</span>}
          </li>
        )
      })}
    </ol>
  )
}

const SLOT_LABEL = ['EMPTY', 'UP', 'DOWN']

/**
 * Slot tiles. `hero` is the status-page bar on the rental page (number, state, tooltip with the
 * time range and the report tx; the running slot pulses); `sm` is the mini strip in the list.
 */
export function Slots({ slots, start, interval, size = 'hero', liveIndex, txBySlot = {} }: {
  slots: number[]; start: bigint; interval: bigint; size?: 'hero' | 'sm'; liveIndex?: number; txBySlot?: Record<number, string>
}) {
  return (
    <div className={`slots ${size}`}>
      {slots.map((s, k) => {
        const { from, to } = slotRange(start, interval, k)
        const live = k === liveIndex && s === 0
        const cls = `slot s${s}${live ? ' live' : ''}`
        if (size === 'sm') return <span key={k} className={cls} title={`Slot ${k}: ${SLOT_LABEL[s]}`} />
        const tx = txBySlot[k]
        const body = (
          <>
            <span className="num mono">{k}</span>
            <span className="state">{live ? 'RUNNING' : SLOT_LABEL[s]}</span>
            <span className="tip" role="tooltip">
              <b>Slot {k}</b> · {live ? 'running' : SLOT_LABEL[s]}
              <span className="mono">{hhmmss(from)} – {hhmmss(to)}</span>
              <span className="mono">{tx ? `tx ${short(tx)} ↗` : s === 0 ? 'no report yet' : 'report tx not loaded'}</span>
            </span>
          </>
        )
        return tx ? (
          <a key={k} className={cls} href={txUrl(tx)} target="_blank" rel="noreferrer">{body}</a>
        ) : (
          <div key={k} className={cls}>{body}</div>
        )
      })}
    </div>
  )
}

/** M/N bar with the threshold marker. */
export function UptimeBar({ up, n, threshold, pass }: { up: bigint; n: bigint; threshold: bigint; pass: boolean }) {
  return (
    <div className="bar" role="img" aria-label={`${up} of ${n} slots up, threshold ${threshold}%`}>
      <div className={pass ? 'fill ok' : 'fill bad'} style={{ width: `${(Number(up) / Number(n)) * 100}%` }} />
      <div className="mark" style={{ left: `${Number(threshold)}%` }}><span className="mono">threshold {threshold.toString()}%</span></div>
    </div>
  )
}

function describe(e: Ev): string {
  const a = e.args
  switch (e.name) {
    case 'RentalCreated': return `${mon(a.price as bigint)} locked · threshold ${a.threshold}% · ${a.n_slots}×${a.interval}s`
    case 'UptimeReported': return `slot ${a.slot} ${a.up ? 'UP' : 'DOWN'} · reporter ${short(a.reporter as string)}`
    case 'SettlementProposed': return `${a.up_count}/${a.n_slots} up · ${a.compliant ? 'threshold met' : 'threshold missed'} · by ${short(a.caller as string)}`
    case 'ObjectionRaised': return `${a.is_renter ? 'renter' : 'provider'} ${short(a.by as string)} · record only`
    case 'SettlementFinalized': return `${mon(a.amount as bigint)} credited to ${short(a.payee as string)} · by ${short(a.caller as string)}`
    case 'Withdrawn': return `${short(a.account as string)} withdrew ${mon(a.amount as bigint)} (account-wide)`
    default: return ''
  }
}
const evClass = (e: Ev) => (e.name === 'UptimeReported' ? (e.args.up ? 'up' : 'down') : e.name === 'RentalCreated' ? '' : 'accent')

/** Terminal-like live list of the rental's on-chain events, newest at the bottom. */
export function ActivityFeed({ events, scanning, retrying, complete, lowest, scanOlder, mock }: ReturnType<typeof useEvents> & { mock: boolean }) {
  return (
    <aside className="card feed">
      <div className="feedhead">
        <h3>On-chain activity</h3>
        <span className={`live ${scanning || retrying ? 'on' : ''}`}>{mock ? 'mock' : retrying ? 'RPC busy, retrying' : scanning ? 'syncing' : 'live'}</span>
      </div>
      <div className="term" aria-live="polite">
        {events.length === 0 && !mock && scanning && (<><Skeleton h={14} w="85%" /><Skeleton h={14} w="70%" /><Skeleton h={14} w="78%" /></>)}
        {events.length === 0 && !mock && !scanning && !retrying && <p className="empty">No events found for this rental yet.</p>}
        {events.length === 0 && !mock && !scanning && retrying && <p className="empty">Waiting for the RPC…</p>}
        {mock && <p className="empty">No chain in mock mode. After a deploy, every report, settle, objection, finalize and withdraw appears here as it lands.</p>}
        {events.map((e) => (
          <a key={`${e.tx}-${e.logIndex}`} className={`line ${evClass(e)}`} href={txUrl(e.tx)} target="_blank" rel="noreferrer">
            <span className="t">{e.time ? hhmmss(e.time) : `#${e.block}`}</span>
            <span className="ev">{e.name}</span>
            <span className="d">{describe(e)}</span>
            <span className="h">{short(e.tx)} ↗</span>
          </a>
        ))}
      </div>
      {!mock && !complete && !scanning && !retrying && lowest !== undefined && (
        <p className="muted small">Scanned from block <span className="mono">{lowest.toString()}</span>. <button className="link" onClick={scanOlder}>Scan older blocks</button></p>
      )}
    </aside>
  )
}

/** Optional localhost panel (UI_HANDOFF §7). Renders nothing when the API is unreachable. */
export function OraclePanel({ id, nSlots }: { id: bigint; nSlots: number }) {
  const { reachable, tracked, slots, forceDown } = useOracle(id)
  const [demo, setDemo] = useState(false)
  if (!reachable) return null
  return (
    <section className="card">
      <div className="feedhead"><h3>Oracle</h3><span className="tag">local · run by the team</span></div>
      {tracked === false && (
        <p className="notice">This rental is not monitored by the oracle — its slots will stay empty and it will refund the renter.</p>
      )}
      {tracked === undefined && <Skeleton h={72} />}
      {tracked && (
        <>
          <table>
            <thead><tr><th>Slot</th><th>Probes</th><th>Report</th><th>Tx</th><th /></tr></thead>
            <tbody>
              {slots.slice(0, nSlots).map((s) => (
                <tr key={s.slot}>
                  <td className="mono">{s.slot}</td>
                  <td className="mono">{s.probesOk}/{s.probesTotal}{s.forcedDown && ' · force-down'}</td>
                  <td>{s.reported ? (s.up ? 'UP sent' : 'DOWN sent') : 'waiting'}</td>
                  <td>{s.txHash ? <a href={txUrl(s.txHash)} target="_blank" rel="noreferrer" className="mono">{short(s.txHash)} ↗</a> : '—'}</td>
                  <td>{demo && !s.reported && !s.forcedDown && <button onClick={() => forceDown([s.slot])}>Force down</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted small">
            Informational only; the slots on-chain are the result.{' '}
            <label className="inline"><input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} /> demo mode (backup force-down)</label>{' '}
            {demo && <button onClick={() => forceDown(null)}>Clear force-down marks</button>}
          </p>
        </>
      )}
    </section>
  )
}
