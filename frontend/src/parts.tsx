import { useState } from 'react'
import { formatEther, type Address } from 'viem'
import { txUrl } from './config'
import { useEvents, useOracle, type Ev, type TxState } from './hooks'
import { short } from './lib/logic'

/** pending -> confirmed -> failed, always with the explorer link once a hash exists. */
export function TxStatus({ tx, label }: { tx: TxState; label: string }) {
  if (tx.status === 'idle') return null
  const text = {
    signing: 'Cüzdanda onay bekleniyor…',
    pending: 'Gönderildi, onay bekleniyor…',
    confirmed: 'Onaylandı',
    failed: `Başarısız: ${tx.error ?? ''}`,
  }[tx.status]
  return (
    <div className={`tx ${tx.status}`}>
      <b>{label}</b> — {text}{' '}
      {tx.hash && <a href={txUrl(tx.hash)} target="_blank" rel="noreferrer" className="mono">{short(tx.hash)} ↗</a>}
    </div>
  )
}

const mon = (v: unknown) => `${formatEther(v as bigint)} MON`

function describe(e: Ev): string {
  const a = e.args
  switch (e.name) {
    case 'RentalCreated': return `Kiralama oluşturuldu — ${mon(a.price)}, eşik %${a.threshold}, ${a.n_slots} × ${a.interval} sn`
    case 'UptimeReported': return `Slot ${a.slot}: ${a.up ? 'UP' : 'DOWN'} — reporter ${short(a.reporter as string)}`
    case 'SettlementProposed': return `Settle: UP ${a.up_count}/${a.n_slots} → ${a.compliant ? 'eşik tuttu' : 'eşik tutmadı'}, ${mon(a.amount)} → ${short(a.payee as string)} — çağıran ${short(a.caller as string)}`
    case 'ObjectionRaised': return `İtiraz kaydı (${a.is_renter ? 'kiracı' : 'sağlayıcı'} ${short(a.by as string)}) — sonucu değiştirmez`
    case 'SettlementFinalized': return `Finalize: ${mon(a.amount)} → ${short(a.payee as string)} bakiyesine — çağıran ${short(a.caller as string)}`
    case 'Withdrawn': return `Withdraw: ${short(a.account as string)} ${mon(a.amount)} çekti (hesap bazlı, başka kiralamadan da olabilir)`
    default: return e.name
  }
}

/** Screen 5: per-rental event history from chunked getLogs, each row linked to the explorer. */
export function History({ id, parties }: { id: bigint; parties: Address[] }) {
  const { events, scanning, complete, lowest, error, scanOlder } = useEvents(id, parties)
  return (
    <section className="card">
      <h3>Olay geçmişi</h3>
      {events.length === 0 && <p className="muted">{scanning ? 'Loglar taranıyor…' : 'Henüz olay bulunamadı.'}</p>}
      <ul className="events">
        {events.map((e) => (
          <li key={`${e.tx}-${e.logIndex}`}>
            <span className="pill">{e.name}</span>
            <span>{describe(e)}</span>
            <a href={txUrl(e.tx)} target="_blank" rel="noreferrer" className="mono">blok {e.block.toString()} · {short(e.tx)} ↗</a>
          </li>
        ))}
      </ul>
      {error && <p className="err">Log okuma hatası: {error}</p>}
      {!complete && !scanning && lowest !== undefined && (
        <p className="muted">
          Blok {lowest.toString()} ve sonrası tarandı; kiralamanın oluşturulma olayı daha eski olabilir.{' '}
          <button onClick={scanOlder}>Daha eski blokları tara</button>
        </p>
      )}
    </section>
  )
}

/** Optional localhost panel (UI_HANDOFF §7). Renders nothing when the API is unreachable. */
export function OraclePanel({ id, nSlots }: { id: bigint; nSlots: number }) {
  const { reachable, tracked, slots, forceDown } = useOracle(id)
  const [demo, setDemo] = useState(false)
  if (!reachable) return null
  return (
    <section className="card">
      <h3>Oracle paneli <span className="pill">yerel · ekip tarafından çalıştırılıyor</span></h3>
      {tracked === false && (
        <p className="warnbox">Bu kiralama oracle tarafından izlenmiyor — slotlar boş kalacak, sonuç kiracıya iade olacak.</p>
      )}
      {tracked && (
        <>
          <table>
            <thead><tr><th>Slot</th><th>Probe</th><th>Rapor</th><th>Tx</th><th /></tr></thead>
            <tbody>
              {slots.slice(0, nSlots).map((s) => (
                <tr key={s.slot}>
                  <td>{s.slot}</td>
                  <td>{s.probesOk}/{s.probesTotal}{s.forcedDown && ' · force-down'}</td>
                  <td>{s.reported ? (s.up ? 'UP gönderildi' : 'DOWN gönderildi') : 'bekliyor'}</td>
                  <td>{s.txHash ? <a href={txUrl(s.txHash)} target="_blank" rel="noreferrer" className="mono">{short(s.txHash)} ↗</a> : '—'}</td>
                  <td>{demo && !s.reported && !s.forcedDown && <button onClick={() => forceDown([s.slot])}>Force-down</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">
            Panel bilgidir; kesin sonuç zincirdeki slotlardır.{' '}
            <label><input type="checkbox" checked={demo} onChange={(e) => setDemo(e.target.checked)} /> demo modu (yedek force-down)</label>{' '}
            {demo && <button onClick={() => forceDown(null)}>Force-down işaretlerini kaldır</button>}
          </p>
        </>
      )}
    </section>
  )
}
