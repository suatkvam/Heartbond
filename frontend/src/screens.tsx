import { useState } from 'react'
import { formatEther, hexToString, parseEventLogs, stringToHex } from 'viem'
import { useAccount, useBalance, usePublicClient } from 'wagmi'
import { ABI, MOCK, addrUrl, monad } from './config'
import { useChainNow, useCredits, useRental, useRentalList, useTx, useWindows } from './hooks'
import { PHASE, PHASE_TR, RESERVE_WEI, fmtSeconds, isCompliant, phaseDeadline, sameAddr, short, upNeeded, validateCreate, type CreateForm } from './lib/logic'
import { History, OraclePanel, TxStatus } from './parts'

const mon = (v: bigint) => `${formatEther(v)} MON`
const Addr = ({ a }: { a: string }) => <a href={addrUrl(a)} target="_blank" rel="noreferrer" className="mono">{short(a)}</a>

/** Wallet connected and on Monad Testnet? Otherwise the reason actions are disabled. */
function useReady() {
  const { address, isConnected, chainId } = useAccount()
  const blocked = !isConnected ? 'Önce cüzdan bağla' : chainId !== monad.id ? "Cüzdanı Monad Testnet'e geçir" : MOCK ? 'Mock modunda işlem gönderilmez' : null
  return { address, blocked }
}

// ------------------------------------------------------------------ list
export function ListScreen() {
  const { data, isLoading, error } = useRentalList()
  return (
    <section className="card">
      <h2>Kiralamalar</h2>
      {isLoading && <p className="muted">Yükleniyor…</p>}
      {error && <p className="err">Okuma hatası: {error.message.split('\n')[0]}</p>}
      {data && data.rows.length === 0 && <p className="muted">Henüz kiralama yok. <a href="#/create">İlkini oluştur</a>.</p>}
      {data && data.rows.length > 0 && (
        <table>
          <thead><tr><th>#</th><th>Durum</th><th>Kiracı</th><th>Sağlayıcı</th><th>Ücret</th><th>UP</th></tr></thead>
          <tbody>
            {data.rows.map(({ id, rental, phase }) => (
              <tr key={id.toString()} className="row" onClick={() => (location.hash = `#/rental/${id}`)}>
                <td><a href={`#/rental/${id}`}>{id.toString()}</a></td>
                <td><span className={`pill phase-${phase}`}>{PHASE_TR[phase]}</span></td>
                <td className="mono">{short(rental.renter)}</td>
                <td className="mono">{short(rental.provider)}</td>
                <td>{mon(rental.price)}</td>
                <td>{rental.up_count.toString()}/{rental.n_slots.toString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {data && data.total > data.rows.length && <p className="muted">En yeni {data.rows.length} kiralama gösteriliyor (toplam {data.total}). Eskiler için adres çubuğuna <code>#/rental/&lt;id&gt;</code> yaz.</p>}
    </section>
  )
}

// ------------------------------------------------------------------ create
export function CreateScreen() {
  const { address, blocked } = useReady()
  const pc = usePublicClient()
  const { data: balance } = useBalance({ address, chainId: monad.id })
  const { tx, send, busy } = useTx()
  const [f, setF] = useState<CreateForm>({ provider: '', threshold: '75', interval: '30', slots: '4', delay: '20', price: '0.01' })
  const [spec, setSpec] = useState('RTX 4090 24GB')
  const set = (k: keyof CreateForm) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value })

  const { errors, args } = validateCreate(f, address)
  const specBytes = new TextEncoder().encode(spec).length
  if (specBytes > 32) errors.push('GPU tanımı en fazla 32 bayt olabilir')
  const duration = args ? Number(args.interval * args.slots) : 0
  const reserveRisk = !!args && !!balance && balance.value - args.value < RESERVE_WEI

  async function submit() {
    if (!args || !pc || errors.length) return
    // start is derived from the latest block, not the browser clock (C-1.1)
    const start = (await pc.getBlock()).timestamp + args.delay
    const end = start + args.interval * args.slots
    const receipt = await send('create_rental', [args.provider, args.threshold, args.interval, start, end, stringToHex(spec, { size: 32 })], args.value)
    if (!receipt) return
    const created = parseEventLogs({ abi: ABI, logs: receipt.logs, eventName: 'RentalCreated' })[0]
    const id = (created?.args as { rental_id?: bigint } | undefined)?.rental_id
    if (id !== undefined) location.hash = `#/rental/${id}`
  }

  return (
    <section className="card">
      <h2>Kiralama oluştur</h2>
      <p className="muted">Ücret aynı işlemde kontrata kilitlenir (<code>msg.value</code>). Sağlayıcının onayı zincirde yok; şartlar zincir dışında konuşulmuş sayılır.</p>
      <div className="form">
        <label>Sağlayıcı adresi<input value={f.provider} onChange={set('provider')} placeholder="0x…" spellCheck={false} /></label>
        <label>Uptime eşiği (%)<input value={f.threshold} onChange={set('threshold')} inputMode="numeric" /></label>
        <label>Slot süresi (sn, en fazla 86 400)<input value={f.interval} onChange={set('interval')} inputMode="numeric" /></label>
        <label>Slot sayısı (en fazla 256)<input value={f.slots} onChange={set('slots')} inputMode="numeric" /></label>
        <label>Başlangıç: son bloktan kaç sn sonra (en fazla 30 gün)<input value={f.delay} onChange={set('delay')} inputMode="numeric" /></label>
        <label>Ücret (MON)<input value={f.price} onChange={set('price')} inputMode="decimal" /></label>
        <label>GPU tanımı (yalnızca gösterim)<input value={spec} onChange={(e) => setSpec(e.target.value)} /></label>
      </div>

      {args && <p className="muted">Toplam süre {fmtSeconds(duration)}; eşiği tutmak için en az {upNeeded(args.threshold, args.slots).toString()}/{args.slots.toString()} slot UP olmalı. Raporlanmayan slot DOWN sayılır.</p>}
      {errors.length > 0 && <ul className="err">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
      {reserveRisk && (
        <p className="warnbox">
          Uyarı: ödeme sonrası bakiyen 10 MON'un altına düşüyor ({mon(balance!.value)} − {mon(args!.value)}). Monad rezerv bakiyesi kuralı yüzünden işlem büyük olasılıkla revert eder.
        </p>
      )}
      <p className="muted">Oracle yalnızca izin listesindeki kiracı cüzdanları ve tanımlı sağlayıcı node'ları için rapor gönderir; diğer kiralamalar raporsuz kalır ve kiracıya iade ile biter.</p>

      <button className="primary" disabled={!!blocked || busy || errors.length > 0} onClick={submit} title={blocked ?? ''}>
        {busy ? 'Gönderiliyor…' : `Oluştur ve ${f.price || '0'} MON kilitle`}
      </button>
      {blocked && <span className="muted"> {blocked}</span>}
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
  const settle = useTx(), object = useTx(), finalize = useTx()

  if (isLoading) return <section className="card"><p className="muted">Yükleniyor…</p></section>
  if (error) return <section className="card"><p className="err">Okuma hatası: {error.message.split('\n')[0]}</p></section>
  if (!data || notFound) return <section className="card"><h2>Kiralama #{id.toString()}</h2><p>Bulunamadı.</p></section>

  const { rental: r, slots, phase, preview } = data
  const isRenter = sameAddr(address, r.renter), isProvider = sameAddr(address, r.provider)
  const role = isRenter ? 'kiracı' : isProvider ? 'sağlayıcı' : address ? 'üçüncü taraf' : 'bağlı değil'
  const deadline = phaseDeadline(phase, r, grace, window)
  const left = deadline === null ? null : Math.max(0, deadline - now)
  const need = upNeeded(r.threshold, r.n_slots)
  const frozen = phase >= 5 // settle() already froze the result
  const compliant = frozen ? r.compliant : isCompliant(r.up_count, r.threshold, r.n_slots)
  const alreadyObjected = (isRenter && r.renter_objected) || (isProvider && r.provider_objected)
  let spec = ''
  try { spec = hexToString(r.spec_ref, { size: 32 }) } catch { /* not text */ }

  return (
    <>
      <section className="card">
        <h2>Kiralama #{id.toString()} <span className="pill">Sen: {role}</span></h2>
        <div className="grid">
          <div><small>Kiracı</small><Addr a={r.renter} /></div>
          <div><small>Sağlayıcı</small><Addr a={r.provider} /></div>
          <div><small>Ücret</small>{mon(r.price)}</div>
          <div><small>Eşik</small>%{r.threshold.toString()}</div>
          <div><small>Slot</small>{r.n_slots.toString()} × {r.interval.toString()} sn</div>
          {spec && <div><small>GPU</small>{spec}</div>}
        </div>

        <div className="phase">
          <span className={`pill big phase-${phase}`}>{PHASE_TR[phase]} <small>({phase} · {PHASE[phase]})</small></span>
          {left !== null && <span className="countdown">{left > 0 ? `${fmtSeconds(left)} kaldı` : 'süre doldu, sonraki blok bekleniyor…'}</span>}
        </div>

        <div className="slots">
          {slots.map((s, k) => {
            const live = phase === 2 && now >= Number(r.start) + k * Number(r.interval) && now < Number(r.start) + (k + 1) * Number(r.interval)
            return <div key={k} className={`slot s${s}${live ? ' live' : ''}`} title={`Slot ${k}`}>{k}<small>{['boş', 'UP', 'DOWN'][s]}</small></div>
          })}
        </div>
        <div className="bar"><div className={compliant ? 'fill ok' : 'fill bad'} style={{ width: `${(Number(r.up_count) / Number(r.n_slots)) * 100}%` }} /><div className="mark" style={{ left: `${Number(r.threshold)}%` }} /></div>
        <p>
          UP <b>{r.up_count.toString()}/{r.n_slots.toString()}</b> (raporlanan {r.reported_count.toString()}) — eşik %{r.threshold.toString()}, en az {need.toString()} slot gerekli →{' '}
          <b className={compliant ? 'oktext' : 'badtext'}>{compliant ? 'eşik tutuyor' : 'eşik tutmuyor'}</b>
          {!frozen && ' (şu anki kayıt; raporlanmayan slot DOWN sayılır)'}
        </p>

        {phase !== 0 && (
          <p className="preview">
            {frozen ? 'Kesinleşen sonuç' : 'Şu an settle edilirse'}: <b>{mon(preview.amount)}</b> → {preview.compliant ? 'sağlayıcı' : 'kiracı (iade)'} <Addr a={preview.payee} />
          </p>
        )}

        {(r.renter_objected || r.provider_objected) && (
          <p className="muted">
            {r.renter_objected && 'Kiracı itiraz etti ✓ '}{r.provider_objected && 'Sağlayıcı itiraz etti ✓ '}— itiraz yalnızca kayda geçer (objection log), sonucu değiştirmez.
          </p>
        )}

        <div className="actions">
          {phase === 4 && (
            <button className="primary" disabled={!!blocked || settle.busy} onClick={() => settle.send('settle', [id])}>Settle (herkes çağırabilir)</button>
          )}
          {phase === 5 && (isRenter || isProvider) && (
            <button disabled={!!blocked || object.busy || alreadyObjected} onClick={() => object.send('raise_objection', [id])}>
              {alreadyObjected ? 'İtirazın kayıtlı' : 'İtiraz Et (yalnızca kayıt, sonucu değiştirmez)'}
            </button>
          )}
          {phase === 5 && !isRenter && !isProvider && <span className="muted">İtiraz penceresi açık — yalnızca kiracı veya sağlayıcı itiraz kaydı bırakabilir.</span>}
          {phase === 6 && (
            <button className="primary" disabled={!!blocked || finalize.busy} onClick={() => finalize.send('finalize', [id])}>Finalize (herkes çağırabilir)</button>
          )}
          {phase === 7 && (myCredits ?? 0n) > 0n && <a className="button primary" href="#/withdraw">Withdraw — {mon(myCredits!)} bakiyen var</a>}
          {phase === 7 && !((myCredits ?? 0n) > 0n) && <span className="muted">Tamamlandı. Ödeme alan taraf Withdraw ekranından çeker.</span>}
          {blocked && (phase === 4 || phase === 5 || phase === 6) && <span className="muted">{blocked}</span>}
        </div>
        <TxStatus tx={settle.tx} label="settle" />
        <TxStatus tx={object.tx} label="raise_objection" />
        <TxStatus tx={finalize.tx} label="finalize" />
      </section>

      <OraclePanel id={id} nSlots={slots.length} />
      {!MOCK && <History id={id} parties={[r.renter, r.provider]} />}
    </>
  )
}

// ------------------------------------------------------------------ withdraw
export function WithdrawScreen() {
  const { address, blocked } = useReady()
  const { data: credits, isLoading } = useCredits(address)
  const { tx, send, busy } = useTx()
  return (
    <section className="card">
      <h2>Withdraw</h2>
      <p className="muted">Finalize ödemeyi göndermez, alıcının kontrattaki bakiyesine yazar. Bakiyeyi yalnızca sahibi çeker (pull payment).</p>
      {!address && <p>Bakiyeni görmek için cüzdan bağla.</p>}
      {address && (
        <p className="big">
          <Addr a={address} /> bakiyesi: <b>{MOCK ? '— (mock)' : isLoading || credits === undefined ? '…' : mon(credits)}</b>
        </p>
      )}
      <button className="primary" disabled={!!blocked || busy || !credits} onClick={() => send('withdraw')}>
        {busy ? 'Gönderiliyor…' : 'Withdraw'}
      </button>
      {blocked && <span className="muted"> {blocked}</span>}
      {!blocked && credits === 0n && <span className="muted"> Çekilecek bakiye yok.</span>}
      <TxStatus tx={tx} label="withdraw" />
    </section>
  )
}
