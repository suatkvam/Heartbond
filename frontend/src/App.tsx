import { useEffect, useState } from 'react'
import { formatEther } from 'viem'
import { useAccount, useBalance, useConnect, useDisconnect, useSwitchChain } from 'wagmi'
import { ADDRESS, MOCK, addrUrl, monad } from './config'
import { short } from './lib/logic'
import { CreateScreen, DetailScreen, ListScreen, WithdrawScreen } from './screens'

function useHash() {
  const [hash, setHash] = useState(location.hash || '#/')
  useEffect(() => {
    const on = () => setHash(location.hash || '#/')
    addEventListener('hashchange', on)
    return () => removeEventListener('hashchange', on)
  }, [])
  return hash
}

/** Screen 1: connect an injected wallet (MetaMask) and switch / add Monad Testnet. */
function Wallet() {
  const { address, isConnected, chainId } = useAccount()
  const { connect, connectors, isPending, error } = useConnect()
  const { disconnect } = useDisconnect()
  const { switchChain, isPending: switching, error: switchError } = useSwitchChain()
  const { data: balance } = useBalance({ address, chainId: monad.id, query: { refetchInterval: 8000 } })

  if (!isConnected)
    return (
      <div className="wallet">
        <button className="primary" disabled={isPending} onClick={() => connect({ connector: connectors[0] })}>
          {isPending ? 'Connecting…' : 'Connect wallet (MetaMask)'}
        </button>
        {error && <span className="err">{error.message.split('\n')[0]}</span>}
      </div>
    )
  return (
    <div className="wallet">
      {chainId !== monad.id ? (
        <button className="warn" disabled={switching} onClick={() => switchChain({ chainId: monad.id })}>
          {switching ? 'Switching…' : 'Wrong network — switch to Monad Testnet'}
        </button>
      ) : (
        <span className="pill ok">Monad Testnet</span>
      )}
      <a href={addrUrl(address!)} target="_blank" rel="noreferrer" className="mono">{short(address)}</a>
      <span className="mono">{balance ? `${Number(formatEther(balance.value)).toFixed(4)} MON` : '… MON'}</span>
      <button onClick={() => disconnect()}>Disconnect</button>
      {switchError && <span className="err">{switchError.message.split('\n')[0]}</span>}
    </div>
  )
}

const LIVE_NOTICE_KEY = 'heartbond-live-demo-notice-dismissed'

function wasLiveNoticeDismissed() {
  try { return localStorage.getItem(LIVE_NOTICE_KEY) === 'true' }
  catch { return false }
}

function LiveDemoNotice({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="live-modal" role="dialog" aria-modal="true" aria-labelledby="live-notice-title" aria-describedby="live-notice-copy">
        <div className="live-modal-head">
          <span className="live-modal-mark" aria-hidden="true">!</span>
          <button className="modal-close" type="button" aria-label="Close live demo notice" onClick={onClose}>×</button>
        </div>
        <p className="eyebrow">Live demo · Monad Testnet</p>
        <h2 id="live-notice-title">Before you create a rental</h2>
        <div id="live-notice-copy" className="live-modal-copy">
          <p>This demo uses testnet MON only; it has no real value.</p>
          <p>Uptime reports come from the team-run oracle. It monitors only renter wallets on the allow-list and providers with a configured node.</p>
          <p>Ask the team for an authorized renter wallet and provider before testing. Rentals outside those settings receive no reports; unreported slots count as DOWN and settlement refunds the renter.</p>
          <p>Settle and finalize are permissionless. An objection is recorded but does not change the payout.</p>
        </div>
        <div className="live-modal-actions">
          <button className="primary" type="button" onClick={onClose}>I understand</button>
        </div>
      </section>
    </div>
  )
}

export function App() {
  const hash = useHash()
  const [showLiveNotice, setShowLiveNotice] = useState(() => !wasLiveNoticeDismissed())
  const [, route, param] = hash.split('/')
  let screen = <ListScreen />
  if (route === 'create') screen = <CreateScreen />
  else if (route === 'withdraw') screen = <WithdrawScreen />
  else if (route === 'rental' && /^\d+$/.test(param ?? '')) screen = <DetailScreen id={BigInt(param)} />

  // browser tab: page title · product name
  const page = route === 'create' ? 'Create rental' : route === 'withdraw' ? 'Withdraw' : route === 'rental' && param ? `Rental #${param}` : 'Rentals'
  function dismissLiveNotice() {
    try { localStorage.setItem(LIVE_NOTICE_KEY, 'true') } catch { /* storage may be disabled */ }
    setShowLiveNotice(false)
  }
  useEffect(() => {
    document.title = `${page} · Heartbond`
  }, [page])

  return (
    <div className="app">
      <header>
        <a className="brand" href="#/" aria-label="Heartbond — pay per heartbeat">
          <img src="/logo.png" alt="Heartbond — pay per heartbeat" />
        </a>
        <nav>
          <a href="#/" className={!route || route === 'rental' ? 'active' : ''}>Rentals</a>
          <a href="#/create" className={route === 'create' ? 'active' : ''}>Create rental</a>
          <a href="#/withdraw" className={route === 'withdraw' ? 'active' : ''}>Withdraw</a>
        </nav>
        <Wallet />
      </header>

      {MOCK && (
        <div className="notice">
          Mock data: the contract is not deployed yet (<code>address: null</code> in <code>shared/deployments/monad-testnet.json</code>).
          The screens run on sample data and no transaction is sent.
        </div>
      )}

      <main>{screen}</main>

      <footer>
        <p>
          Uptime data comes from reporter keys run by the team: one source of trust, no independent verification.
          Any wallet can trigger settle and finalize. An objection is only a record (objection log) and never changes the payout.
          Testnet MON only — no real value.
        </p>
        {ADDRESS && (
          <p>
            Contract: <a href={addrUrl(ADDRESS)} target="_blank" rel="noreferrer" className="mono">{ADDRESS}</a>
          </p>
        )}
        <p><button className="link live-note-trigger" type="button" onClick={() => setShowLiveNotice(true)}>Show live demo notice</button></p>
      </footer>
      {showLiveNotice && <LiveDemoNotice onClose={dismissLiveNotice} />}
    </div>
  )
}
